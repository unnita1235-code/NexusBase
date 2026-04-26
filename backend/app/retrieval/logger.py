"""
NexusBase — Retrieval observability logger.

Per enterprise-rag-standard §4, every retrieval call must log:
  - rank, chunk_id, source, access_level
  - distance_score, rrf_score, weighted_score
  - source_snippet (first 200 chars of content)

Per enterprise-rag-standard §5, graph traversals must log:
  - seed entities, traversal path, hop count, connected chunk_ids
"""

from __future__ import annotations

import logging

from app.shared.models import RetrievedChunk

logger = logging.getLogger("rag.retrieval")


def log_retrieved_chunks(chunks: list[RetrievedChunk]) -> None:
    """
    Emit structured observability logs for every retrieved chunk.

    This function MUST be called after every retrieval operation
    per enterprise-rag-standard §4.
    """
    logger.info("=" * 60)
    logger.info(f"Retrieved {len(chunks)} chunk(s)")
    logger.info("=" * 60)

    for chunk in chunks:
        logger.info(
            f"[Rank #{chunk.rank}] "
            f"chunk_id={chunk.chunk_id} | "
            f"source={chunk.source} | "
            f"access_level={chunk.access_level} | "
            f"distance_score={chunk.distance_score:.4f} | "
            f"rrf_score={chunk.rrf_score:.4f} | "
            f"weighted_score={chunk.weighted_score:.4f}"
        )
        snippet = chunk.content[:200].strip()
        logger.info(f'  Snippet: "{snippet}..."')

    logger.info("=" * 60)


def log_graph_traversal(
    seed_entities: list[str],
    traversal_path: list[str],
    hop_count: int,
    connected_chunk_ids: list[str],
    query_type: str,
) -> None:
    """
    Emit structured logs for a graph traversal operation.

    Per enterprise-rag-standard §5, every graph traversal must log
    its seed entities, path, hop count, and connected chunk_ids.
    """
    logger.info("=" * 60)
    logger.info(f"GraphRAG Traversal (query_type={query_type})")
    logger.info("=" * 60)
    logger.info(f"  Seed entities: {seed_entities}")
    logger.info(f"  Traversal path: {' '.join(traversal_path)}")
    logger.info(f"  Hop count: {hop_count}")
    logger.info(f"  Connected chunks: {len(connected_chunk_ids)} chunk(s)")
    for cid in connected_chunk_ids[:10]:
        logger.info(f"    → {cid}")
    if len(connected_chunk_ids) > 10:
        logger.info(f"    ... and {len(connected_chunk_ids) - 10} more")
    logger.info("=" * 60)
