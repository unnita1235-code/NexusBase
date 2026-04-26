"""
NexusBase — Async Redis Worker.

Processes heavy background jobs like Document Ingestion
off the main FastAPI event loop.
"""

from __future__ import annotations

import logging
from typing import Any

from arq.connections import RedisSettings
from app.config import settings

# Must import from pipeline
from app.ingestion.pipeline import ingest_document

logger = logging.getLogger("rag.worker")


async def run_ingestion_task(ctx: dict[str, Any], file_path: str, access_level: str, content_bytes: bytes) -> int:
    """
    Background task that executes the ingestion pipeline.
    """
    logger.info(f"Starting background ingestion for {file_path}")
    try:
        chunks_created = await ingest_document(
            file_path=file_path,
            access_level=access_level,
            content_bytes=content_bytes,
        )
        logger.info(f"Background ingestion finished for {file_path}. Created {chunks_created} chunks.")
        return chunks_created
    except Exception as e:
        logger.error(f"Background ingestion failed for {file_path}: {e}", exc_info=True)
        raise e


class WorkerSettings:
    """Settings for the ARQ worker."""
    # arq expects the redis url components or a RedisSettings object.
    # config.redis_url is like redis://localhost:6379/0
    # Let's extract host and port simply (assuming localhost for now or docker name)
    from urllib.parse import urlparse
    parsed = urlparse(settings.redis_url)
    
    redis_settings = RedisSettings(
        host=parsed.hostname or 'localhost',
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip('/')) if parsed.path else 0
    )
    
    functions = [run_ingestion_task]
    
    # Called when worker starts
    async def on_startup(ctx: dict[str, Any]):
        logger.info("ARQ Worker started.")
        
    # Called when worker shuts down
    async def on_shutdown(ctx: dict[str, Any]):
        logger.info("ARQ Worker shutting down.")

# To run the worker:
# arq worker.WorkerSettings
