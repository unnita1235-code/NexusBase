"""
NexusBase — Shared Pydantic models.

These models are used by both the IngestionPipeline and QueryEngine
to ensure a consistent data contract across the system boundary.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ─── Access Level Enum (rule §1) ─────────────────────────────

class AccessLevel(str, Enum):
    """Allowed access levels per enterprise-rag-standard §1."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


ACCESS_LEVEL_HIERARCHY: dict[AccessLevel, int] = {
    AccessLevel.PUBLIC: 0,
    AccessLevel.INTERNAL: 1,
    AccessLevel.CONFIDENTIAL: 2,
    AccessLevel.RESTRICTED: 3,
}


def allowed_levels_for(caller_level: AccessLevel) -> list[str]:
    """Return all access levels the caller is permitted to view."""
    caller_rank = ACCESS_LEVEL_HIERARCHY[caller_level]
    return [
        level.value
        for level, rank in ACCESS_LEVEL_HIERARCHY.items()
        if rank <= caller_rank
    ]


# ─── Chunk Models ────────────────────────────────────────────

class ChunkMetadata(BaseModel):
    """Metadata attached to every document chunk at ingestion time."""
    chunk_id: str
    source: str
    access_level: AccessLevel
    page: int | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentChunk(BaseModel):
    """A single chunk ready to be embedded and stored."""
    chunk_id: str
    source: str
    content: str
    access_level: AccessLevel
    page: int | None = None
    embedding: list[float] | None = None
    document_hash: str | None = None


class RetrievedChunk(BaseModel):
    """A chunk returned from the QueryEngine with scoring info."""
    rank: int
    chunk_id: str
    source: str
    content: str
    access_level: str
    distance_score: float = 0.0
    keyword_score: float = 0.0
    rrf_score: float = 0.0
    weighted_score: float = 0.0  # Score(doc) = w1*CosineSim + w2*KeywordMatch
    page: int | None = None
    is_external: bool = False


# ─── API Request / Response Models ───────────────────────────

class IngestRequest(BaseModel):
    """Form fields for the /v1/ingest endpoint (access_level is required)."""
    access_level: AccessLevel


class IngestResponse(BaseModel):
    """Response from /v1/ingest."""
    chunks_created: int = 0
    source: str
    job_id: str | None = None
    status: str = "completed"


class QueryRequest(BaseModel):
    """JSON body for /v1/query."""
    query: str
    access_level: AccessLevel = AccessLevel.INTERNAL
    top_k: int = 5
    use_hyde: bool = False


class QueryResponse(BaseModel):
    """Response from /v1/query."""
    answer: str
    chunks: list[RetrievedChunk]
    graph_path: list[str]
    relevance_ratio: float = 0.0  # fraction of chunks graded relevant (0.0–1.0)
    rewritten_query: str | None = None  # populated if query was rewritten
    query_type: str = "simple"  # "simple" or "multi_hop"
    graph_entities: list[str] = Field(default_factory=list)  # entities discovered
    graph_traversal_path: list[str] = Field(default_factory=list)  # Neo4j traversal path
    total_graded: int = 0
    total_relevant: int = 0
    retrieval_time_ms: int = 0


# ─── Settings Models ─────────────────────────────────────────

class SystemSetting(BaseModel):
    """A single configuration setting."""
    key: str
    value: str
    is_encrypted: bool = False
    updated_at: datetime | None = None

class SettingsUpdate(BaseModel):
    """Request body for updating multiple settings."""
    settings: list[SystemSetting]

class SettingsResponse(BaseModel):
    """Response from /v1/settings."""
    settings: list[SystemSetting]
