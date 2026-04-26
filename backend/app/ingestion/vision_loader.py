"""
NexusBase — Vision LLM PDF Loader.

Uses PyMuPDF to render PDF pages as images and passes them to
Gemini 3.1 Pro (Vision) to extract text, tables, and visual descriptions
of complex layouts (charts, graphs, etc) into structured Markdown.
"""

from __future__ import annotations

import logging
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image
import google.generativeai as genai

from app.config import settings
from app.ingestion.loader import LoadedDocument

logger = logging.getLogger("rag.ingestion.vision_loader")

VISION_PROMPT = """You are an advanced document parsing AI for an enterprise RAG system.
Your task is to convert the provided document page image into clean, structured Markdown.

Follow these strict rules:
1. **Text & Structure**: Extract all text exactly as it appears. Preserve headers (using #, ##), bullet points, and paragraphs.
2. **Tables**: Convert any tabular data into perfectly formatted Markdown tables. Do not lose any columns or rows.
3. **Visual Descriptions (CRITICAL)**: If there is a chart, graph, diagram, or significant image, you MUST write a detailed text description of it. 
   - Prefix the description with `> **Visual Description:** `
   - Describe the type of chart (e.g., bar chart, pie chart), the axes, key trends, and specific data points. 
   - This ensures the visual data becomes searchable in our vector database.
4. **Clean Output**: Do not include conversational filler like "Here is the markdown." Output ONLY the Markdown content.
"""

def load_pdf_vision(file_path: str | Path, content_bytes: bytes | None = None) -> list[LoadedDocument]:
    """
    Load a PDF using a Vision LLM to parse complex layouts and tables.

    Args:
        file_path: Path or filename of the PDF.
        content_bytes: If provided, read from bytes instead of disk.

    Returns:
        List of LoadedDocuments containing structured Markdown.
    """
    source = Path(file_path).name
    documents: list[LoadedDocument] = []

    if not settings.gemini_api_key:
        logger.error("Gemini API key missing. Cannot use vision loader.")
        raise ValueError("GEMINI_API_KEY is required for vision parsing.")

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.vision_model)

    try:
        if content_bytes is not None:
            doc = fitz.open(stream=content_bytes, filetype="pdf")
        else:
            doc = fitz.open(file_path)
    except Exception as e:
        logger.error(f"PyMuPDF failed to open {source}: {e}")
        raise ValueError(f"Failed to open PDF: {e}")

    logger.info(f"Starting vision parsing for {source} ({len(doc)} pages)...")

    for i, page in enumerate(doc):
        page_num = i + 1
        logger.info(f"  Parsing page {page_num}/{len(doc)} with {settings.vision_model}...")

        try:
            # Render page to a high-res pixmap (DPI 150 is usually enough for OCR/Vision)
            pix = page.get_pixmap(dpi=150)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Call Gemini Vision API
            response = model.generate_content(
                [VISION_PROMPT, img],
                generation_config=genai.GenerationConfig(
                    temperature=0.0,  # Zero temperature for deterministic extraction
                )
            )

            text = response.text.strip()
            
            if text:
                documents.append(LoadedDocument(
                    page_content=text,
                    source=source,
                    page=page_num,
                ))
        except Exception as e:
            logger.error(f"  Vision parsing failed for page {page_num}: {e}")
            # Fallback: Just extract raw text using PyMuPDF for this page
            raw_text = page.get_text().strip()
            if raw_text:
                documents.append(LoadedDocument(
                    page_content=raw_text,
                    source=source,
                    page=page_num,
                ))
            else:
                logger.warning(f"  Page {page_num} is empty and vision parse failed.")

    doc.close()
    
    logger.info(f"Vision parsing complete. Yielded {len(documents)} structured pages.")
    return documents
