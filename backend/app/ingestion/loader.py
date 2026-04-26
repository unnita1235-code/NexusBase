"""
NexusBase — Document loaders for PDF and Markdown files.

Part of the IngestionPipeline (rule §3).
Supports .pdf (via PyMuPDF/Vision) and .md (plain text) formats.
"""

from __future__ import annotations

import logging
from pathlib import Path

import fitz  # PyMuPDF

from app.config import settings

logger = logging.getLogger("rag.ingestion.loader")


class LoadedDocument:
    """A raw document with text content and metadata."""

    def __init__(self, page_content: str, source: str, page: int | None = None):
        self.page_content = page_content
        self.source = source
        self.page = page


def load_pdf(file_path: str | Path, content_bytes: bytes | None = None) -> list[LoadedDocument]:
    """
    Load a PDF and return one LoadedDocument per page.

    If vision ingestion is enabled in config, routes to the Gemini Vision
    loader to extract structured Markdown and visual descriptions.
    Otherwise, uses standard PyMuPDF text extraction.
    """
    source = Path(file_path).name
    documents: list[LoadedDocument] = []

    if settings.use_vision_ingestion:
        try:
            from app.ingestion.vision_loader import load_pdf_vision
            return load_pdf_vision(file_path, content_bytes)
        except Exception as e:
            logger.error(f"Vision loader failed, falling back to standard extraction: {e}")

    # Standard extraction using PyMuPDF (fitz)
    try:
        if content_bytes is not None:
            doc = fitz.open(stream=content_bytes, filetype="pdf")
        else:
            doc = fitz.open(file_path)
            
        for i, page in enumerate(doc):
            text = page.get_text()
            if text and text.strip():
                documents.append(LoadedDocument(
                    page_content=text.strip(),
                    source=source,
                    page=i + 1,
                ))
        doc.close()
    except Exception as e:
        logger.error(f"Failed to load PDF {source}: {e}")

    logger.info(f"Loaded {len(documents)} page(s) from PDF (Standard): {source}")
    return documents


def load_markdown(file_path: str | Path, content_bytes: bytes | None = None) -> list[LoadedDocument]:
    """
    Load a Markdown file and return a single LoadedDocument.
    """
    source = Path(file_path).name

    if content_bytes is not None:
        text = content_bytes.decode("utf-8")
    else:
        text = Path(file_path).read_text(encoding="utf-8")

    if not text.strip():
        logger.warning(f"Empty Markdown file: {source}")
        return []

    logger.info(f"Loaded Markdown file: {source}")
    return [LoadedDocument(page_content=text.strip(), source=source, page=None)]


def load_document(file_path: str | Path, content_bytes: bytes | None = None) -> list[LoadedDocument]:
    """
    Auto-detect format and load the document.

    Raises:
        ValueError: If the file format is not supported.
    """
    suffix = Path(file_path).suffix.lower()

    if suffix == ".pdf":
        return load_pdf(file_path, content_bytes)
    elif suffix in (".md", ".markdown"):
        return load_markdown(file_path, content_bytes)
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Supported: .pdf, .md")

