"""
NexusBase — Audit & Observability Logger.

Provides three logging concerns:
1. PII audit logging (original) — persisted to SQLite
2. Query/retrieval observability — structured logs with request_id
3. Error tracking — full stack traces with context

All functions pull request_id from the logging middleware's ContextVar
for zero-config correlation across the entire request lifecycle.
"""

from __future__ import annotations

import sqlite3
import logging
import time
import traceback
from pathlib import Path
from typing import Any

from app.core.logging_middleware import request_id_ctx

logger = logging.getLogger("rag.shared.audit_logger")

DB_PATH = Path(__file__).parent.parent.parent.parent / "db" / "audit.db"


# ═══════════════════════════════════════════════════════════════
# 1. PII Audit Logging (SQLite — persisted)
# ═══════════════════════════════════════════════════════════════

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
    rid = request_id_ctx.get("-")
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
        logger.info(f"[{rid}] PII audit logged for {source_document}: {pii_counts}")
    except Exception as e:
        logger.error(f"[{rid}] Failed to write to PII audit log: {e}")


# ═══════════════════════════════════════════════════════════════
# 2. Query Observability Logging
# ═══════════════════════════════════════════════════════════════

def log_query_received(
    query: str,
    access_level: str,
    user_email: str | None = None,
    top_k: int = 5,
    use_hyde: bool = False,
) -> None:
    """Log an incoming query with full context."""
    rid = request_id_ctx.get("-")
    logger.info(
        f"[{rid}] ┌─ QUERY RECEIVED\n"
        f"         │ query     = \"{query}\"\n"
        f"         │ user      = {user_email or 'anonymous'}\n"
        f"         │ access    = {access_level}\n"
        f"         │ top_k     = {top_k}\n"
        f"         │ hyde      = {use_hyde}\n"
        f"         └─"
    )


def log_query_completed(
    query: str,
    answer_len: int,
    chunks_returned: int,
    graph_path: list[str],
    relevance_ratio: float,
    duration_ms: int,
) -> None:
    """Log query completion with performance metrics."""
    rid = request_id_ctx.get("-")
    path_str = " → ".join(graph_path) if graph_path else "N/A"
    logger.info(
        f"[{rid}] ┌─ QUERY COMPLETED\n"
        f"         │ query          = \"{query[:80]}...\"\n"
        f"         │ answer_length  = {answer_len} chars\n"
        f"         │ chunks         = {chunks_returned}\n"
        f"         │ relevance      = {relevance_ratio:.0%}\n"
        f"         │ graph_path     = {path_str}\n"
        f"         │ duration       = {duration_ms}ms\n"
        f"         └─"
    )


# ═══════════════════════════════════════════════════════════════
# 3. Retrieval Observability Logging
# ═══════════════════════════════════════════════════════════════

def log_retrieval_results(
    search_type: str,
    results_count: int,
    duration_ms: int,
    top_scores: list[float] | None = None,
) -> None:
    """Log retrieval search results with performance metrics."""
    rid = request_id_ctx.get("-")
    scores_str = ", ".join(f"{s:.4f}" for s in (top_scores or [])[:5])
    logger.info(
        f"[{rid}] ▸ RETRIEVAL [{search_type}] → "
        f"{results_count} results in {duration_ms}ms "
        f"(top scores: [{scores_str}])"
    )


# ═══════════════════════════════════════════════════════════════
# 4. Ingestion Observability Logging
# ═══════════════════════════════════════════════════════════════

def log_ingestion_started(
    source: str,
    file_size_bytes: int,
    access_level: str,
) -> None:
    """Log ingestion pipeline start."""
    rid = request_id_ctx.get("-")
    size_kb = file_size_bytes / 1024
    logger.info(
        f"[{rid}] ┌─ INGESTION STARTED\n"
        f"         │ source    = {source}\n"
        f"         │ size      = {size_kb:.1f} KB\n"
        f"         │ access    = {access_level}\n"
        f"         └─"
    )


def log_ingestion_completed(
    source: str,
    chunks_created: int,
    total_chunks: int,
    duration_ms: int,
) -> None:
    """Log ingestion pipeline completion."""
    rid = request_id_ctx.get("-")
    logger.info(
        f"[{rid}] ┌─ INGESTION COMPLETED\n"
        f"         │ source    = {source}\n"
        f"         │ chunks    = {chunks_created}/{total_chunks} stored\n"
        f"         │ duration  = {duration_ms}ms\n"
        f"         └─"
    )


# ═══════════════════════════════════════════════════════════════
# 5. Error Tracking
# ═══════════════════════════════════════════════════════════════

def log_error(
    component: str,
    message: str,
    error: Exception | None = None,
    context: dict[str, Any] | None = None,
) -> None:
    """
    Log an error with full stack trace and context.

    Args:
        component: Which part of the system failed (e.g., "ingestion.embedder")
        message: Human-readable error description
        error: The exception object (optional)
        context: Additional context dict (optional)
    """
    rid = request_id_ctx.get("-")
    ctx_str = ""
    if context:
        ctx_str = "\n".join(f"         │ {k} = {v}" for k, v in context.items())
        ctx_str = f"\n{ctx_str}"

    trace_str = ""
    if error:
        trace_str = f"\n         │ traceback:\n"
        for line in traceback.format_exception(type(error), error, error.__traceback__):
            for subline in line.strip().split("\n"):
                trace_str += f"         │   {subline}\n"

    error_line = ""
    if error:
        error_line = f"\n         │ error     = {type(error).__name__}: {error}"

    logger.error(
        f"[{rid}] ┌─ ERROR [{component}]\n"
        f"         │ message   = {message}"
        f"{error_line}"
        f"{ctx_str}"
        f"{trace_str}\n"
        f"         └─"
    )

