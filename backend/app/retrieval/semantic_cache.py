"""
NexusBase — Redis Semantic Cache.

Provides 'Zero-Latency' responses for repeated queries.
If a new query's embedding is >98% similar (cosine) to a cached query,
it returns the cached LangGraph output directly.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from redis_om import Field, HashModel, get_redis_connection
from redis_om.model.model import NotFoundError

from app.config import settings
from app.shared.models import QueryResponse, RetrievedChunk

logger = logging.getLogger("rag.retrieval.semantic_cache")

# Connect to Redis
try:
    redis_conn = get_redis_connection(url=settings.redis_url)
except Exception as e:
    logger.error(f"Failed to connect to Redis: {e}")
    redis_conn = None


class CachedQuery(HashModel):
    """Redis-OM model representing a semantic cache entry."""
    query: str = Field(index=True)
    access_level: str = Field(index=True)
    response_json: str
    
    # RediSearch Vector Field for Semantic Search
    # 1536 is the dimension for text-embedding-3-small
    query_embedding: list[float] = Field(
        index=True,
        algorithm="HNSW",
        datatype="FLOAT32",
        dims=1536,
        distance_metric="COSINE",
    )

    class Meta:
        database = redis_conn


def init_cache_index():
    """Create the RediSearch index if it doesn't exist."""
    if redis_conn is None:
        return
    try:
        from redis_om import Migrator
        Migrator().run()
        logger.info("Semantic Cache index initialized.")
    except Exception as e:
        logger.warning(f"Could not initialize Redis index: {e}")


def check_cache(query_embedding: list[float], access_level: str) -> Optional[QueryResponse]:
    """
    Check if a similar query exists in the cache.

    Args:
        query_embedding: The embedded query vector.
        access_level: The user's access level (strict match required).

    Returns:
        QueryResponse if found and similarity > threshold, else None.
    """
    if redis_conn is None:
        return None

    try:
        # Perform KNN vector search using Redis-OM query builder
        # Note: Redis-OM syntax for vector search:
        # We find the nearest neighbor and calculate similarity from the distance.
        # Cosine distance in RediSearch: 0.0 is exact match, 1.0 is orthogonal.
        # Similarity = 1.0 - distance.
        
        # We need to run a raw RediSearch query since redis-om's high-level API
        # has limited support for filtering + vector KNN simultaneously.
        # But for simplicity, we can use the low-level FT.SEARCH if needed,
        # or use find().sort_by() in redis-om.
        
        # Redis-OM query:
        results = CachedQuery.find(
            (CachedQuery.access_level == access_level)
        ).sort_by(
            "query_embedding",
            distance_metric="COSINE",
            vector=query_embedding
        ).page(0, 1)

        if not results:
            return None

        best_match = results[0]
        
        # Unfortunately, redis-om doesn't easily expose the distance score in the model object directly 
        # from a high-level find(). Let's compute cosine similarity manually for the top hit to verify.
        # Or, we can use a raw query. We'll do a manual numpy cosine check against the best match for exact thresholding.
        import numpy as np
        vec1 = np.array(query_embedding)
        vec2 = np.array(best_match.query_embedding)
        
        # Cosine similarity
        sim = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        
        if sim >= settings.cache_similarity_threshold:
            logger.info(f"Semantic Cache HIT! Similarity: {sim:.4f} >= {settings.cache_similarity_threshold}")
            data = json.loads(best_match.response_json)
            # Reconstruct Pydantic model
            return QueryResponse(**data)
            
        logger.info(f"Semantic Cache MISS. Highest similarity: {sim:.4f} < {settings.cache_similarity_threshold}")
        return None

    except Exception as e:
        logger.error(f"Semantic Cache check failed: {e}")
        return None


def store_cache(query: str, query_embedding: list[float], access_level: str, response: QueryResponse):
    """
    Store a new query and its response in the Semantic Cache.
    """
    if redis_conn is None:
        return

    try:
        logger.info("Storing query in Semantic Cache.")
        cached_entry = CachedQuery(
            query=query,
            access_level=access_level,
            query_embedding=query_embedding,
            response_json=response.model_dump_json()
        )
        cached_entry.save()
    except Exception as e:
        logger.error(f"Failed to store in Semantic Cache: {e}")
