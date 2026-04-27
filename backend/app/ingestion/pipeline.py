"""
NexusBase — IngestionPipeline orchestrator (hardened).

Implements the full ingestion flow per enterprise-rag-standard §3 + §5:
    Load → Chunk → Validate → Embed → Upsert → Extract Entities (GraphRAG)

Hardening:
- Max file size guard (50 MB)
- Fallback from SemanticSplitter to character-based chunking
- Per-chunk retry on DB upsert (2 attempts)
- Structured audit logging with request_id

This module MUST NOT contain any query or ranking logic.
"""

from __future__ import annotations

import logging
import hashlib
import time
from pathlib import Path

from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

from app.core.config import settings
from app.infrastructure.database import get_pool
from app.ingestion.loader import load_document
from app.ingestion.validator import validate_chunks
from app.ingestion.embedder import get_embeddings
from app.core.audit_logger import (
    log_ingestion_started,
    log_ingestion_completed,
    log_error,
)

logger = logging.getLogger("rag.ingestion.pipeline")

# ── Constants ─────────────────────────────────────────────────
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

# SQL for upserting chunks into the database
UPSERT_SQL = """
    INSERT INTO document_chunks (chunk_id, source, content, access_level, embedding, page, document_hash)
    VALUES ($1, $2, $3, $4, $5::vector, $6, $7)
    ON CONFLICT (chunk_id) DO UPDATE SET
        content       = EXCLUDED.content,
        access_level  = EXCLUDED.access_level,
        embedding     = EXCLUDED.embedding,
        page          = EXCLUDED.page,
        document_hash = EXCLUDED.document_hash
"""


@retry(
    stop=stop_after_attempt(2),
    wait=wait_fixed(1),
    retry=retry_if_exception_type((Exception,)),
    reraise=True,
)
async def _upsert_chunk(conn, chunk: dict, doc_hash: str) -> None:
    """Upsert a single chunk with retry (2 attempts)."""
    embedding_str = "[" + ",".join(str(v) for v in chunk["embedding"]) + "]"
    await conn.execute(
        UPSERT_SQL,
        chunk["chunk_id"],
        chunk["source"],
        chunk["content"],
        chunk["access_level"],
        embedding_str,
        chunk.get("page"),
        doc_hash,
    )


def _try_semantic_split(documents):
    """Attempt semantic splitting, return None on failure."""
    try:
        from packages.ingestion.semantic_splitter import SemanticSplitter

        splitter = SemanticSplitter(
            threshold=settings.semantic_chunk_threshold,
            max_tokens=settings.semantic_chunk_max_tokens,
        )
        chunks = splitter.split_documents(documents)
        if chunks:
            logger.info(
                f"Semantic chunking produced {len(chunks)} chunk(s)"
            )
            return chunks
        logger.warning("Semantic chunking returned empty — falling back")
        return None
    except Exception as e:
        logger.warning(
            f"Semantic chunking failed: {e} — falling back to character-based"
        )
        return None


def _fallback_character_split(documents):
    """Character-based chunking as fallback."""
    from app.ingestion.chunker import chunk_documents

    chunks = chunk_documents(
        documents,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    logger.info(
        f"Fallback character chunking produced {len(chunks)} chunk(s) "
        f"(size={settings.chunk_size}, overlap={settings.chunk_overlap})"
    )
    return chunks


async def ingest_document(
    file_path: str | Path,
    access_level: str,
    content_bytes: bytes | None = None,
) -> int:
    """
    Run the full ingestion pipeline for a single document.

    Args:
        file_path: Path or filename of the document.
        access_level: Access level to assign to all chunks (rule §1).
        content_bytes: If provided, load from memory instead of disk.

    Returns:
        Number of chunks successfully ingested.

    Raises:
        ValueError: If access_level is invalid, file too large, or format unsupported.
    """
    start_time = time.perf_counter()
    source_name = Path(file_path).name

    logger.info(f"Starting ingestion: {file_path} (access_level={access_level})")

    # Step 0a: Read file bytes if needed
    if content_bytes is None:
        try:
            content_bytes = Path(file_path).read_bytes()
        except Exception as e:
            log_error(
                "ingestion.pipeline",
                f"Failed to read file: {file_path}",
                error=e,
            )
            return 0

    # Step 0b: File size guard
    if len(content_bytes) > MAX_FILE_SIZE_BYTES:
        size_mb = len(content_bytes) / (1024 * 1024)
        limit_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
        msg = (
            f"File too large: {source_name} is {size_mb:.1f} MB "
            f"(limit: {limit_mb:.0f} MB). Split the document and retry."
        )
        logger.error(msg)
        raise ValueError(msg)

    log_ingestion_started(source_name, len(content_bytes), access_level)

    # Step 0c: Delta Sync Check (SHA-256)
    doc_hash = hashlib.sha256(content_bytes).hexdigest()
    pool = get_pool()

    async with pool.acquire() as conn:
        existing_hash = await conn.fetchval(
            "SELECT document_hash FROM document_chunks WHERE source = $1 LIMIT 1",
            source_name,
        )
        if existing_hash == doc_hash:
            logger.info(
                f"Delta Sync [SKIP]: {source_name} is unchanged "
                f"(hash={doc_hash[:8]}...)"
            )
            return 0

        if existing_hash:
            logger.info(
                f"Delta Sync [UPDATE]: {source_name} changed. Purging old chunks."
            )
            # Purge chunks and their associated entities
            await conn.execute(
                "DELETE FROM chunk_entities WHERE chunk_id IN "
                "(SELECT chunk_id FROM document_chunks WHERE source = $1)",
                source_name,
            )
            await conn.execute(
                "DELETE FROM document_chunks WHERE source = $1", source_name
            )

    # Step 1: Load
    documents = load_document(file_path, content_bytes)
    if not documents:
        logger.warning(f"No content extracted from {file_path}")
        return 0

    # Step 2: Chunk (Semantic with character-based fallback)
    raw_chunks = _try_semantic_split(documents)
    if raw_chunks is None:
        raw_chunks = _fallback_character_split(documents)

    if not raw_chunks:
        logger.warning(f"No chunks produced from {file_path}")
        return 0

    # Step 3: Validate metadata (rule §1 — access_level required)
    validated_chunks = validate_chunks(raw_chunks, access_level)
    if not validated_chunks:
        logger.error(f"All chunks rejected during validation for {file_path}")
        return 0

    # Step 3.5: PII Scrubbing & Audit Logging
    from app.ingestion.pii_scrubber import scrub_text
    from app.shared.audit_logger import log_pii_detection

    total_pii_counts = {"EMAIL": 0, "SSN": 0, "API_KEY": 0}
    for chunk in validated_chunks:
        masked_content, counts = scrub_text(chunk["content"])
        chunk["content"] = masked_content
        for key, val in counts.items():
            total_pii_counts[key] += val

    if sum(total_pii_counts.values()) > 0:
        log_pii_detection(str(file_path), total_pii_counts)

    # Step 4: Embed (now on scrubbed text)
    texts = [chunk["content"] for chunk in validated_chunks]
    try:
        embeddings = get_embeddings(texts)
    except Exception as e:
        log_error(
            "ingestion.embedder",
            f"Embedding failed for {source_name}",
            error=e,
            context={"chunk_count": len(texts)},
        )
        return 0

    # Attach embeddings to chunks
    for chunk, embedding in zip(validated_chunks, embeddings):
        chunk["embedding"] = embedding

    # Step 5: Upsert to database (with per-chunk retry)
    pool = get_pool()
    inserted = 0
    failed = 0

    async with pool.acquire() as conn:
        for chunk in validated_chunks:
            try:
                await _upsert_chunk(conn, chunk, doc_hash)
                inserted += 1
            except Exception as e:
                failed += 1
                logger.error(
                    f"Failed to upsert chunk '{chunk['chunk_id']}' "
                    f"after 2 attempts: {e}"
                )

    duration_ms = int((time.perf_counter() - start_time) * 1000)
    log_ingestion_completed(source_name, inserted, len(validated_chunks), duration_ms)

    if failed > 0:
        logger.warning(
            f"Ingestion partial: {inserted}/{len(validated_chunks)} chunks stored, "
            f"{failed} failed"
        )

    # Step 6: Entity extraction + knowledge graph population (rule §5)
    # This step is NON-BLOCKING — if Neo4j or Gemini is unavailable,
    # chunks are still stored in pgvector (degraded mode).
    await _extract_and_populate_graph(validated_chunks, access_level)

    return inserted


async def _extract_and_populate_graph(
    chunks: list[dict],
    access_level: str,
) -> None:
    """
    Extract entities/relationships from chunks and populate the knowledge graph.

    This step runs after pgvector upsert and is non-fatal — any errors
    are logged but do not fail the ingestion pipeline.
    """
    from app.knowledge_graph.extractor import extract_entities
    from app.knowledge_graph.graph_builder import upsert_extraction

    total_entities = 0
    total_relationships = 0

    for chunk in chunks:
        try:
            result = await extract_entities(
                chunk_content=chunk["content"],
                chunk_id=chunk["chunk_id"],
                access_level=access_level,
            )

            if result.entities or result.relationships:
                upserted = await upsert_extraction(result)
                total_entities += len(result.entities)
                total_relationships += len(result.relationships)

        except Exception as e:
            logger.error(
                f"GraphRAG extraction failed for chunk '{chunk['chunk_id']}': {e}"
            )
            # Continue with next chunk — non-fatal

    logger.info(
        f"GraphRAG extraction complete: "
        f"{total_entities} entities, {total_relationships} relationships "
        f"across {len(chunks)} chunks"
    )
