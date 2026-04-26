"""
NexusBase — FastAPI application entry point.

Provides:
- Lifespan management (DB pool + Neo4j init / teardown)
- CORS middleware for the Next.js dashboard
- Router registration for /v1/ingest and /v1/query
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.shared.db import init_pool, close_pool
from app.knowledge_graph.neo4j_client import init_neo4j, close_neo4j
from app.api.v1_ingest import router as ingest_router
from app.api.v1_query import router as query_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create DB pool + Neo4j driver. Shutdown: close both."""
    await init_pool(settings.db_dsn)
    await init_neo4j(
        settings.neo4j_uri,
        (settings.neo4j_user, settings.neo4j_password),
    )
    yield
    await close_neo4j()
    await close_pool()


app = FastAPI(
    title="NexusBase",
    description="Enterprise-grade GraphRAG system with self-corrective retrieval",
    version="0.2.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────
app.include_router(ingest_router, prefix="/v1", tags=["Ingestion"])
app.include_router(query_router, prefix="/v1", tags=["Query"])


@app.get("/health")
async def health():
    """Simple health check."""
    return {"status": "ok", "service": "nexusbase", "version": "0.2.0"}
