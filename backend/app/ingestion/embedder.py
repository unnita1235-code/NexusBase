"""
NexusBase — Embedding model wrapper (hardened).

Part of the IngestionPipeline (rule §3).
Wraps the OpenAI embeddings API for batch embedding of document chunks.

Hardening:
- Retry with exponential backoff (tenacity) on API failures
- Token truncation to model limit (8191 tokens)
- Per-batch error isolation — one failed batch doesn't kill the rest
"""

from __future__ import annotations

import logging

import tiktoken
from openai import OpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from app.core.config import settings

logger = logging.getLogger("rag.ingestion.embedder")

# Max tokens for text-embedding-3-small / text-embedding-ada-002
_MAX_EMBEDDING_TOKENS = 8191

# Lazy-init tokenizer
_tokenizer = None


def _get_tokenizer():
    """Get or create the tiktoken tokenizer."""
    global _tokenizer
    if _tokenizer is None:
        try:
            _tokenizer = tiktoken.encoding_for_model(settings.embedding_model)
        except Exception:
            _tokenizer = tiktoken.get_encoding("cl100k_base")
    return _tokenizer


def _truncate_text(text: str, max_tokens: int = _MAX_EMBEDDING_TOKENS) -> str:
    """Truncate text to fit within the embedding model's token limit."""
    tokenizer = _get_tokenizer()
    tokens = tokenizer.encode(text)
    if len(tokens) <= max_tokens:
        return text
    logger.warning(
        f"Truncating text from {len(tokens)} to {max_tokens} tokens "
        f"(lost {len(tokens) - max_tokens} tokens)"
    )
    return tokenizer.decode(tokens[:max_tokens])


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((Exception,)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _embed_batch(client: OpenAI, texts: list[str], model: str) -> list[list[float]]:
    """Embed a single batch with retry logic."""
    response = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in response.data]


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a batch of texts using OpenAI.

    Hardened with:
    - Token truncation (8191 max per text)
    - Exponential backoff retry (3 attempts)
    - Per-batch error isolation

    Args:
        texts: List of text strings to embed.

    Returns:
        List of embedding vectors (each a list of floats).
        Failed texts get zero-vectors to preserve index alignment.
    """
    if not texts:
        return []

    client = OpenAI(api_key=settings.openai_api_key)

    # Truncate all texts to token limit
    safe_texts = [_truncate_text(t) for t in texts]

    logger.info(f"Embedding {len(safe_texts)} text(s) with model={settings.embedding_model}")

    all_embeddings: list[list[float]] = []
    batch_size = 512
    failed_batches = 0

    for i in range(0, len(safe_texts), batch_size):
        batch = safe_texts[i : i + batch_size]
        try:
            batch_embeddings = _embed_batch(client, batch, settings.embedding_model)
            all_embeddings.extend(batch_embeddings)
        except Exception as e:
            failed_batches += 1
            logger.error(
                f"Embedding batch {i // batch_size + 1} failed after 3 retries: {e}. "
                f"Inserting zero-vectors for {len(batch)} texts."
            )
            # Insert zero-vectors to maintain alignment
            dims = 1536  # text-embedding-3-small dimension
            all_embeddings.extend([[0.0] * dims for _ in batch])

    if failed_batches > 0:
        logger.warning(
            f"Embedding completed with {failed_batches} failed batch(es). "
            f"Some chunks will have zero-vector embeddings."
        )

    if all_embeddings:
        logger.info(
            f"Generated {len(all_embeddings)} embedding(s), "
            f"dims={len(all_embeddings[0])}"
        )
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
    safe_query = _truncate_text(query)

    try:
        response = _embed_batch(client, [safe_query], settings.embedding_model)
        return response[0]
    except Exception as e:
        logger.error(f"Query embedding failed after retries: {e}")
        raise
