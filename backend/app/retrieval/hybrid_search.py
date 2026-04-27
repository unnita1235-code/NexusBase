"""
NexusBase — Hybrid Search (Semantic + Keyword + Weighted CRAG Scoring).

Part of the QueryEngine (rule §2, §3).
Implements:
  - Semantic search via pgvector cosine distance (<=>)
  - Keyword search via Postgres tsvector / tsquery
  - Reciprocal Rank Fusion (RRF) to merge results
  - Weighted scoring: Score(doc) = w1 * CosineSim + w2 * KeywordMatch

This module MUST NOT contain any document loading or embedding logic.
"""

from __future__ import annotations

import logging
from collections import defaultdict

from app.infrastructure.database import get_pool
from app.shared.models import RetrievedChunk
from app.core.config import settings

logger = logging.getLogger("rag.retrieval.hybrid_search")


async def semantic_search(
    query_embedding: list[float],
    allowed_levels: list[str],
    top_k: int = 5,
) -> list[dict]:
    """
    Semantic similarity search via pgvector cosine distance.

    Uses vector_cosine_ops (<=>) per enterprise-rag-standard §2.

    Args:
        query_embedding: The embedded query vector.
        allowed_levels: Access levels the caller may view (rule §1).
        top_k: Number of results to return.

    Returns:
        List of dicts with chunk data and cosine distance score.
    """
    pool = get_pool()
    embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

    sql = """
        SELECT
            chunk_id,
            source,
            content,
            access_level,
            page,
            embedding <=> $1::vector AS distance_score
        FROM document_chunks
        WHERE access_level = ANY($2)
        ORDER BY embedding <=> $1::vector
        LIMIT $3
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, embedding_str, allowed_levels, top_k)

    results = []
    for row in rows:
        results.append({
            "chunk_id": row["chunk_id"],
            "source": row["source"],
            "content": row["content"],
            "access_level": row["access_level"],
            "page": row["page"],
            "distance_score": float(row["distance_score"]),
        })

    logger.info(f"Semantic search returned {len(results)} result(s)")
    return results


async def keyword_search(
    query: str,
    allowed_levels: list[str],
    top_k: int = 5,
) -> list[dict]:
    """
    Full-text keyword search via Postgres tsvector / tsquery.

    Uses websearch_to_tsquery per enterprise-rag-standard §2.

    Args:
        query: Raw user query string.
        allowed_levels: Access levels the caller may view (rule §1).
        top_k: Number of results to return.

    Returns:
        List of dicts with chunk data and keyword rank score.
    """
    pool = get_pool()

    sql = """
        SELECT
            chunk_id,
            source,
            content,
            access_level,
            page,
            ts_rank(content_tsv, websearch_to_tsquery('english', $1)) AS keyword_score
        FROM document_chunks
        WHERE content_tsv @@ websearch_to_tsquery('english', $1)
          AND access_level = ANY($2)
        ORDER BY keyword_score DESC
        LIMIT $3
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, query, allowed_levels, top_k)

    results = []
    for row in rows:
        results.append({
            "chunk_id": row["chunk_id"],
            "source": row["source"],
            "content": row["content"],
            "access_level": row["access_level"],
            "page": row["page"],
            "keyword_score": float(row["keyword_score"]),
        })

    logger.info(f"Keyword search returned {len(results)} result(s)")
    return results


def reciprocal_rank_fusion(
    semantic_results: list[dict],
    keyword_results: list[dict],
    k: int = 60,
) -> list[RetrievedChunk]:
    """
    Merge semantic and keyword results using Reciprocal Rank Fusion (RRF).

    Formula: rrf_score(d) = Σ [ 1 / (k + rank_i(d)) ]

    Per enterprise-rag-standard §2, k defaults to 60.

    Args:
        semantic_results: Results from semantic search (ordered by distance).
        keyword_results: Results from keyword search (ordered by keyword_score).
        k: RRF constant (default 60).

    Returns:
        Merged and sorted list of RetrievedChunk objects.
    """
    # Build a map of chunk_id -> data + rrf score
    chunk_data: dict[str, dict] = {}
    rrf_scores: defaultdict[str, float] = defaultdict(float)

    # Score semantic results
    for rank, result in enumerate(semantic_results, start=1):
        cid = result["chunk_id"]
        rrf_scores[cid] += 1.0 / (k + rank)
        if cid not in chunk_data:
            chunk_data[cid] = result

    # Score keyword results
    for rank, result in enumerate(keyword_results, start=1):
        cid = result["chunk_id"]
        rrf_scores[cid] += 1.0 / (k + rank)
        if cid not in chunk_data:
            chunk_data[cid] = result

    # Sort by RRF score descending
    sorted_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)

    # Compute weighted scores: Score(doc) = w1 * CosineSim + w2 * KeywordMatch
    w1 = settings.score_w1
    w2 = settings.score_w2

    # Build final RetrievedChunk list
    merged: list[RetrievedChunk] = []
    for final_rank, cid in enumerate(sorted_ids, start=1):
        data = chunk_data[cid]
        cosine_sim = 1.0 - data.get("distance_score", 0.0)  # distance → similarity
        keyword_match = data.get("keyword_score", 0.0)
        weighted = w1 * cosine_sim + w2 * keyword_match

        merged.append(RetrievedChunk(
            rank=final_rank,
            chunk_id=cid,
            source=data["source"],
            content=data["content"],
            access_level=data["access_level"],
            distance_score=data.get("distance_score", 0.0),
            keyword_score=keyword_match,
            rrf_score=rrf_scores[cid],
            weighted_score=round(weighted, 4),
            page=data.get("page"),
        ))

    logger.info(
        f"RRF fusion merged {len(semantic_results)} semantic + "
        f"{len(keyword_results)} keyword → {len(merged)} unique chunk(s) "
        f"(w1={w1}, w2={w2})"
    )
    return merged


async def hybrid_search(
    query: str,
    query_embedding: list[float],
    allowed_levels: list[str],
    top_k: int = 5,
) -> list[RetrievedChunk]:
    """
    Full hybrid search pipeline: semantic + keyword + RRF fusion.

    Args:
        query: Raw user query string.
        query_embedding: Pre-computed query embedding vector.
        allowed_levels: Access levels the caller may view.
        top_k: Max results per sub-search.

    Returns:
        RRF-fused list of RetrievedChunk, sorted by rrf_score descending.
    """
    # Run both searches (could be parallelized with asyncio.gather)
    semantic_results = await semantic_search(query_embedding, allowed_levels, top_k)
    keyword_results = await keyword_search(query, allowed_levels, top_k)

    # Fuse via RRF
    fused = reciprocal_rank_fusion(
        semantic_results,
        keyword_results,
        k=settings.rrf_k,
    )

    # Trim to top_k
    return fused[:top_k]
