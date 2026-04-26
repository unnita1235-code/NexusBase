"""
NexusBase — Embedding model wrapper.

Part of the IngestionPipeline (rule §3).
Wraps the OpenAI embeddings API for batch embedding of document chunks.
"""

from __future__ import annotations

import logging

from openai import OpenAI

from app.config import settings

logger = logging.getLogger("rag.ingestion.embedder")


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a batch of texts using OpenAI.

    Args:
        texts: List of text strings to embed.

    Returns:
        List of embedding vectors (each a list of floats).
    """
    if not texts:
        return []

    client = OpenAI(api_key=settings.openai_api_key)

    logger.info(f"Embedding {len(texts)} text(s) with model={settings.embedding_model}")

    # OpenAI API accepts up to 2048 texts per batch
    all_embeddings: list[list[float]] = []
    batch_size = 512

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(
            model=settings.embedding_model,
            input=batch,
        )
        batch_embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(batch_embeddings)

    logger.info(f"Generated {len(all_embeddings)} embedding(s), dims={len(all_embeddings[0])}")
    return all_embeddings


def embed_query(query: str) -> list[float]:
    """
    Generate an embedding for a single query string.

    Args:
        query: The search query to embed.

    Returns:
        Embedding vector as a list of floats.
    """
    client = OpenAI(api_key=settings.openai_api_key)

    response = client.embeddings.create(
        model=settings.embedding_model,
        input=query,
    )
    return response.data[0].embedding
