"""
NexusBase — PII Audit Logger.

Stores metadata about intercepted PII (Emails, SSNs, API Keys) in a local
SQLite database for admin review. Never stores raw sensitive data.
"""

from __future__ import annotations

import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger("rag.shared.audit_logger")

DB_PATH = Path(__file__).parent.parent.parent.parent / "db" / "audit.db"


def init_audit_db():
    """Ensure the SQLite database and table exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pii_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            source_document TEXT NOT NULL,
            pii_type TEXT NOT NULL,
            count INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()


# Initialize on module load
try:
    init_audit_db()
except Exception as e:
    logger.error(f"Failed to initialize PII audit database: {e}")


def log_pii_detection(source_document: str, pii_counts: dict[str, int]) -> None:
    """
    Log detected PII counts to the local SQLite audit DB.

    Args:
        source_document: The name of the file where PII was found.
        pii_counts: Dictionary mapping PII type to count (e.g., {"EMAIL": 2}).
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for pii_type, count in pii_counts.items():
            if count > 0:
                cursor.execute("""
                    INSERT INTO pii_audit_log (source_document, pii_type, count)
                    VALUES (?, ?, ?)
                """, (source_document, pii_type, count))
                
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to write to PII audit log: {e}")
