"""
NexusBase — QueryEngine orchestrator (GraphRAG-aware).

Part of the retrieval subsystem (rule §3, §5).
Orchestrates:
  - Query classification (simple vs multi-hop)
  - For multi-hop: graph traversal → targeted chunk fetch
  - For simple: standard hybrid search
  - Log results → return

This module MUST NOT contain any document loading or embedding-storage logic.
"""

from __future__ import annotations

import logging

from app.shared.models import RetrievedChunk, AccessLevel, allowed_levels_for
from app.ingestion.embedder import embed_query
from app.retrieval.hybrid_search import hybrid_search, semantic_search, reciprocal_rank_fusion
from app.retrieval.logger import log_retrieved_chunks
from app.retrieval.query_classifier import classify_query, QueryClassification
from app.knowledge_graph.traverser import traverse_graph
from app.knowledge_graph.models import TraversalResult
from app.config import settings

logger = logging.getLogger("rag.retrieval.query_engine")


async def search(
    query: str,
    access_level: AccessLevel,
    top_k: int = 5,
    hyde_answer: str | None = None,
) -> list[RetrievedChunk]:
    """
    Execute a full hybrid search for the given query.

    Flow:
        1. Embed the query
        2. Determine allowed access levels for the caller (rule §1)
        3. Run hybrid search (semantic + keyword + RRF) (rule §2)
        4. Log results to terminal (rule §4)
        5. Return ranked chunks

    Args:
        query: User's search query.
        access_level: Caller's access level (filters results per rule §1).
        top_k: Number of results to return.

    Returns:
        List of RetrievedChunk sorted by rrf_score descending.
    """
    logger.info(f"Query: \"{query}\" | access_level={access_level.value} | top_k={top_k}")

    # Step 1: Embed the query (use HyDE answer if provided)
    search_text = hyde_answer if hyde_answer else query
    query_embedding = embed_query(search_text)

    # Step 2: Determine allowed levels
    allowed = allowed_levels_for(access_level)
    logger.info(f"Allowed access levels: {allowed}")

    # Step 3: Hybrid search
    chunks = await hybrid_search(
        query=query,
        query_embedding=query_embedding,
        allowed_levels=allowed,
        top_k=top_k,
    )

    # Step 4: Log results (rule §4)
    log_retrieved_chunks(chunks)

    return chunks


async def graph_search(
    query: str,
    access_level: AccessLevel,
    classification: QueryClassification,
    top_k: int = 5,
    hyde_answer: str | None = None,
) -> tuple[list[RetrievedChunk], TraversalResult]:
    """
    Graph-first retrieval for multi-hop queries (rule §5).

    Flow:
        1. Traverse the knowledge graph from seed entities
        2. Collect related chunk_ids from traversal
        3. If chunk_ids found: fetch those specific chunks from pgvector
        4. If no chunk_ids: fall back to standard hybrid search
        5. Log results with graph metadata

    Args:
        query: User's search query.
        access_level: Caller's access level.
        classification: Query classification with extracted entities.
        top_k: Number of results to return.

    Returns:
        Tuple of (ranked chunks, traversal result for observability).
    """
    logger.info(
        f"GraphRAG search: \"{query}\" | "
        f"entities={classification.entities} | "
        f"access_level={access_level.value}"
    )

    # Step 1: Traverse knowledge graph
    traversal = await traverse_graph(
        seed_entities=classification.entities,
        access_level=access_level,
    )

    # Step 2: Fetch chunks linked to graph traversal
    if traversal.related_chunk_ids:
        logger.info(
            f"  Graph traversal found {len(traversal.related_chunk_ids)} linked chunks — "
            f"fetching targeted results"
        )

        chunks = await _fetch_chunks_by_ids(
            chunk_ids=traversal.related_chunk_ids,
            query=query,
            access_level=access_level,
            top_k=top_k,
        )

        if chunks:
            log_retrieved_chunks(chunks)
            return chunks, traversal

    # Step 3: Fall back to standard hybrid search if graph yields nothing
    logger.info("  Graph traversal yielded no chunks — falling back to hybrid search")
    chunks = await search(query, access_level, top_k, hyde_answer=hyde_answer)
    return chunks, traversal


async def _fetch_chunks_by_ids(
    chunk_ids: list[str],
    query: str,
    access_level: AccessLevel,
    top_k: int,
) -> list[RetrievedChunk]:
    """
    Fetch specific chunks by ID and re-rank them against the query.

    Uses semantic search restricted to the given chunk_ids for relevance ranking.
    """
    from app.shared.db import get_pool

    allowed = allowed_levels_for(access_level)
    query_embedding = embed_query(query)
    embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

    pool = get_pool()

    # Fetch chunks by ID with cosine distance for ranking
    sql = """
        SELECT
            chunk_id,
            source,
            content,
            access_level,
            page,
            embedding <=> $1::vector AS distance_score
        FROM document_chunks
        WHERE chunk_id = ANY($2)
          AND access_level = ANY($3)
        ORDER BY embedding <=> $1::vector
        LIMIT $4
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, embedding_str, chunk_ids, allowed, top_k)

    chunks: list[RetrievedChunk] = []
    for rank, row in enumerate(rows, start=1):
        cosine_sim = 1.0 - float(row["distance_score"])
        chunks.append(RetrievedChunk(
            rank=rank,
            chunk_id=row["chunk_id"],
            source=row["source"],
            content=row["content"],
            access_level=row["access_level"],
            distance_score=float(row["distance_score"]),
            keyword_score=0.0,
            rrf_score=0.0,
            weighted_score=round(settings.score_w1 * cosine_sim, 4),
            page=row["page"],
        ))

    return chunks
