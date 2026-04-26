"""
NexusBase — POST /v1/ingest endpoint.

Accepts a file upload (PDF or Markdown) with an access_level field.
Delegates to the IngestionPipeline for processing.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, Form, UploadFile, HTTPException

from app.shared.models import AccessLevel, IngestResponse
from app.ingestion.pipeline import ingest_document

logger = logging.getLogger("rag.api.ingest")

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest(
    file: UploadFile = File(..., description="PDF or Markdown file to ingest"),
    access_level: str = Form(..., description="Access level: public, internal, confidential, restricted"),
):
    """
    Ingest a document into the NexusBase vector store.

    The file is chunked, validated (access_level is required per rule §1),
    embedded, and stored in Postgres/pgvector.
    """
    # Validate access_level early
    try:
        validated_level = AccessLevel(access_level)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid access_level: '{access_level}'. "
                f"Must be one of: public, internal, confidential, restricted"
            ),
        )

    # Validate file type
    filename = file.filename or "document"
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix not in ("pdf", "md", "markdown"):
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type: .{suffix}. Supported: .pdf, .md",
        )

    # Read file content
    content_bytes = await file.read()
    if not content_bytes:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")

    logger.info(f"Ingest request: {filename} ({len(content_bytes)} bytes, access_level={validated_level.value})")

    try:
        from arq import create_pool
        from worker import WorkerSettings
        
        # Connect to ARQ pool
        redis_pool = await create_pool(WorkerSettings.redis_settings)
        
        # Enqueue the job
        job = await redis_pool.enqueue_job(
            "run_ingestion_task",
            filename,
            validated_level.value,
            content_bytes,
        )
        
        if job:
            logger.info(f"Ingestion queued for {filename}. Job ID: {job.job_id}")
            return IngestResponse(
                chunks_created=0,
                source=filename,
                job_id=job.job_id,
                status="processing",
            )
        else:
            raise Exception("Failed to enqueue job.")

    except Exception as e:
        logger.error(f"Ingestion queuing failed: {e}")
        # Fallback to synchronous if Redis queue fails
        try:
            from app.ingestion.pipeline import ingest_document
            logger.warning("Falling back to synchronous ingestion.")
            chunks_created = await ingest_document(
                file_path=filename,
                access_level=validated_level.value,
                content_bytes=content_bytes,
            )
            return IngestResponse(
                chunks_created=chunks_created,
                source=filename,
                status="completed_sync",
            )
        except Exception as sync_e:
            raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(sync_e)}")
