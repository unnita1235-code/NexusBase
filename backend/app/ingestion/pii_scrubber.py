"""
NexusBase — PII Scrubber Module.

Provides regex-based detection and masking for sensitive data
(Emails, SSNs, API Keys) to prevent PII from reaching external LLMs
or the vector database.
"""

from __future__ import annotations

import re
import logging

logger = logging.getLogger("rag.ingestion.pii_scrubber")

# Regex patterns
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
SSN_REGEX = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
# Matches generic API keys, AWS keys, etc. (e.g., api_key="sk-...", AWS_ACCESS_KEY_ID=...)
API_KEY_REGEX = re.compile(r'(?i)(?:api_key|apikey|secret|token|password|access_key)[\w]*[\s:=]+["\']?([a-zA-Z0-9\-_]{16,})["\']?')


def scrub_text(text: str) -> tuple[str, dict[str, int]]:
    """
    Scan text for PII, replace it with redaction markers, and return stats.

    Args:
        text: The raw text string.

    Returns:
        A tuple of (masked_text, pii_counts).
        pii_counts is a dict mapping PII type (e.g., "EMAIL") to occurrences.
    """
    pii_counts: dict[str, int] = {"EMAIL": 0, "SSN": 0, "API_KEY": 0}
    masked_text = text

    # Scrub Emails
    def mask_email(match):
        pii_counts["EMAIL"] += 1
        return "[REDACTED_EMAIL]"
    masked_text = EMAIL_REGEX.sub(mask_email, masked_text)

    # Scrub SSNs
    def mask_ssn(match):
        pii_counts["SSN"] += 1
        return "[REDACTED_SSN]"
    masked_text = SSN_REGEX.sub(mask_ssn, masked_text)

    # Scrub API Keys
    def mask_api_key(match):
        pii_counts["API_KEY"] += 1
        # The regex matches the full string like `api_key="sk-..."` but capturing group 1 is the key.
        # We replace the key part, keeping the prefix intact.
        full_match = match.group(0)
        key_value = match.group(1)
        return full_match.replace(key_value, "[REDACTED_CREDENTIAL]")
    masked_text = API_KEY_REGEX.sub(mask_api_key, masked_text)

    total_pii = sum(pii_counts.values())
    if total_pii > 0:
        logger.info(f"PII detected & masked: {pii_counts}")

    return masked_text, pii_counts
