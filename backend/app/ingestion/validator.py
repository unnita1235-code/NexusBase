"""
NexusBase — Metadata & access_level validation.

Part of the IngestionPipeline (rule §1).
Rejects chunks that do not have a valid access_level metadata field.
"""

from __future__ import annotations

import logging

from app.shared.models import AccessLevel

logger = logging.getLogger("rag.ingestion.validator")

VALID_ACCESS_LEVELS = {level.value for level in AccessLevel}


def validate_chunks(
    chunks: list[dict],
    access_level: str,
) -> list[dict]:
    """
    Validate and attach access_level to each chunk.

    Per enterprise-rag-standard §1:
    - Chunks WITHOUT an access_level are REJECTED and logged as errors.
    - access_level must be one of: public, internal, confidential, restricted.

    Args:
        chunks: Raw chunk dicts from the chunker.
        access_level: The access level to assign (from the ingest request).

    Returns:
        List of validated chunk dicts with access_level attached.

    Raises:
        ValueError: If the provided access_level is not valid.
    """
    # Validate the provided access level
    if access_level not in VALID_ACCESS_LEVELS:
        raise ValueError(
            f"Invalid access_level: '{access_level}'. "
            f"Must be one of: {sorted(VALID_ACCESS_LEVELS)}"
        )

    validated: list[dict] = []
    rejected = 0

    for chunk in chunks:
        # Ensure required fields exist
        if not chunk.get("content"):
            logger.error(
                f"REJECTED chunk '{chunk.get('chunk_id', 'unknown')}': "
                f"empty content"
            )
            rejected += 1
            continue

        if not chunk.get("chunk_id"):
            logger.error(
                f"REJECTED chunk: missing chunk_id (source={chunk.get('source')})"
            )
            rejected += 1
            continue

        # Attach the validated access_level
        chunk["access_level"] = access_level
        validated.append(chunk)

    if rejected > 0:
        logger.warning(f"Rejected {rejected} chunk(s) during validation")

    logger.info(
        f"Validated {len(validated)} chunk(s) with access_level='{access_level}'"
    )
    return validated
