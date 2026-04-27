"""
NexusBase — FastAPI application entry point.

Provides:
- Lifespan management (DB pool + Neo4j init / teardown)
- CORS middleware for the Next.js dashboard
- Request-ID logging middleware for observability
- Router registration for /v1/ingest, /v1/query, health checks
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.infrastructure.database import init_pool, close_pool
from app.core.logging_middleware import RequestIDMiddleware, RequestIDFilter
from app.infrastructure.neo4j_client import init_neo4j, close_neo4j
from app.core.exceptions import setup_exception_handlers
from app.api.v1_ingest import router as ingest_router
from app.api.v1_query import router as query_router
from app.api.v1_settings import router as settings_router
from app.api.health import router as health_router
from app.api.v1_auth import router as auth_router
from app.api.v1_tickets import router as tickets_router


# ── Logging configuration ─────────────────────────────────────
def _configure_logging() -> None:
    """Set up structured logging with request_id injection."""
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Console handler with request_id
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s │ %(levelname)-7s │ %(name)-35s │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    handler.addFilter(RequestIDFilter())

    # Avoid duplicate handlers on reload
    if not root.handlers:
        root.addHandler(handler)


_configure_logging()
logger = logging.getLogger("rag.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create DB pool + Neo4j driver. Shutdown: close both."""

    # ── Database pool ─────────────────────────────────────────
    try:
        await init_pool(settings.db_dsn)
        logger.info("✔ Postgres connection pool initialized")
    except Exception as e:
        logger.error(f"✖ Postgres connection failed: {e}")
        logger.error(
            "  Ensure DATABASE_URL is correct and Postgres is running. "
            "Hint: docker-compose up db"
        )
        # Non-fatal during testing if DB is down

    # ── Neo4j driver ──────────────────────────────────────────
    try:
        await init_neo4j(
            settings.neo4j_uri,
            (settings.neo4j_user, settings.neo4j_password),
        )
        logger.info("✔ Neo4j driver initialized")
    except Exception as e:
        # Non-fatal — GraphRAG features degrade gracefully
        logger.warning(f"⚠ Neo4j connection failed (non-fatal): {e}")
        logger.warning("  GraphRAG features will be unavailable until Neo4j is reachable")

    # ── Redis Cache ───────────────────────────────────────────
    try:
        from app.retrieval.semantic_cache import init_cache_index
        init_cache_index()
        logger.info("✔ Semantic Cache index initialized")
    except Exception as e:
        logger.warning(f"⚠ Redis cache initialization failed: {e}")

    logger.info("═" * 50)
    logger.info("  NexusBase v0.2.0 — ready to accept requests")
    logger.info("═" * 50)

    yield

    # ── Shutdown ──────────────────────────────────────────────
    logger.info("Shutting down NexusBase...")
    await close_neo4j()
    await close_pool()
    logger.info("Shutdown complete")


app = FastAPI(
    title="NexusBase",
    description="Enterprise-grade GraphRAG system with self-corrective retrieval",
    version="0.2.0",
    lifespan=lifespan,
)

# ── Exception Handlers ────────────────────────────────────────
setup_exception_handlers(app)

# ── Middleware (order matters: first added = outermost) ───────
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────
app.include_router(health_router, tags=["Health"])
app.include_router(auth_router, prefix="/v1/auth", tags=["Auth"])
app.include_router(tickets_router, prefix="/v1/tickets", tags=["Tickets"])
app.include_router(ingest_router, prefix="/v1", tags=["Ingestion"])
app.include_router(query_router, prefix="/v1", tags=["Query"])
app.include_router(settings_router, prefix="/v1", tags=["Settings"])
