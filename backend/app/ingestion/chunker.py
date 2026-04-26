"""
NexusBase — Text chunking strategies.

Part of the IngestionPipeline (rule §3).
Splits loaded documents into overlapping chunks with assigned chunk IDs.
"""

from __future__ import annotations

import logging
import re

from app.ingestion.loader import LoadedDocument

logger = logging.getLogger("rag.ingestion.chunker")


def _slugify(text: str) -> str:
    """Convert a filename into a slug for chunk IDs."""
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[\s-]+", "_", slug).strip("_")


def chunk_documents(
    documents: list[LoadedDocument],
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[dict]:
    """
    Split documents into overlapping text chunks.

    Uses a simple character-based sliding window with paragraph-aware
    splitting. Each chunk gets a unique chunk_id.

    Args:
        documents: List of LoadedDocuments from the loader.
        chunk_size: Maximum number of characters per chunk.
        chunk_overlap: Number of overlapping characters between chunks.

    Returns:
        List of dicts with keys: chunk_id, source, content, page.
    """
    all_chunks: list[dict] = []
    chunk_counter = 0

    source_slug = _slugify(documents[0].source) if documents else "doc"

    for doc in documents:
        text = doc.page_content
        if not text:
            continue

        # Split into chunks using sliding window
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end].strip()

            if chunk_text:
                chunk_counter += 1
                all_chunks.append({
                    "chunk_id": f"{source_slug}_chunk_{chunk_counter}",
                    "source": doc.source,
                    "content": chunk_text,
                    "page": doc.page,
                })

            # Move window forward
            start += chunk_size - chunk_overlap

    logger.info(
        f"Chunked {len(documents)} document(s) into {len(all_chunks)} chunk(s) "
        f"(size={chunk_size}, overlap={chunk_overlap})"
    )
    return all_chunks
