"""
NexusBase — Comprehensive Health Check Endpoints.

Provides granular health checks for every infrastructure dependency:
  /health        → basic liveness
  /health/db     → Postgres asyncpg pool
  /health/vector → pgvector extension
  /health/neo4j  → Neo4j Bolt connectivity
  /health/redis  → Redis PING
"""

from __future__ import annotations

import time
import logging

from fastapi import APIRouter

logger = logging.getLogger("rag.api.health")

router = APIRouter(tags=["Health"])


def _ms_since(start: float) -> int:
    """Return milliseconds elapsed since `start`."""
    return int((time.perf_counter() - start) * 1000)


# ── /health — Liveness ────────────────────────────────────────

@router.get("/health")
async def health_basic():
    """Basic liveness check — always returns OK if the process is running."""
    return {
        "status": "healthy",
        "service": "nexusbase",
        "version": "0.2.0",
    }


# ── /health/db — Postgres ────────────────────────────────────

@router.get("/health/db")
async def health_db():
    """Check Postgres connection by acquiring a connection and running SELECT 1."""
    start = time.perf_counter()
    try:
        from app.infrastructure.database import get_pool

        pool = get_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")

        if result == 1:
            return {
                "status": "healthy",
                "service": "postgres",
                "latency_ms": _ms_since(start),
                "details": "SELECT 1 OK",
                "pool_size": pool.get_size(),
                "pool_free": pool.get_idle_size(),
            }
        else:
            return {
                "status": "unhealthy",
                "service": "postgres",
                "latency_ms": _ms_since(start),
                "details": f"SELECT 1 returned {result}",
            }
    except Exception as e:
        logger.error(f"DB health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "postgres",
            "latency_ms": _ms_since(start),
            "details": str(e),
        }


# ── /health/vector — pgvector extension ──────────────────────

@router.get("/health/vector")
async def health_vector():
    """Verify the pgvector extension is installed and operational."""
    start = time.perf_counter()
    try:
        from app.infrastructure.database import get_pool

        pool = get_pool()
        async with pool.acquire() as conn:
            # Confirm vector type is usable
            result = await conn.fetchval("SELECT '[1,2,3]'::vector")

        return {
            "status": "healthy",
            "service": "pgvector",
            "latency_ms": _ms_since(start),
            "details": f"vector cast OK → {result}",
        }
    except Exception as e:
        logger.error(f"pgvector health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "pgvector",
            "latency_ms": _ms_since(start),
            "details": str(e),
        }


# ── /health/neo4j — Knowledge Graph ─────────────────────────

@router.get("/health/neo4j")
async def health_neo4j():
    """Check Neo4j Bolt connectivity."""
    start = time.perf_counter()
    try:
        from app.infrastructure.neo4j_client import get_driver

        driver = get_driver()
        if driver is None:
            return {
                "status": "unhealthy",
                "service": "neo4j",
                "latency_ms": _ms_since(start),
                "details": "Driver not initialized",
            }

        async with driver.session() as session:
            result = await session.run("RETURN 1 AS connected")
            record = await result.single()

        if record and record["connected"] == 1:
            return {
                "status": "healthy",
                "service": "neo4j",
                "latency_ms": _ms_since(start),
                "details": "RETURN 1 OK",
            }
        else:
            return {
                "status": "unhealthy",
                "service": "neo4j",
                "latency_ms": _ms_since(start),
                "details": "Unexpected query result",
            }
    except Exception as e:
        logger.error(f"Neo4j health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "neo4j",
            "latency_ms": _ms_since(start),
            "details": str(e),
        }


# ── /health/redis — Cache & Task Queue ───────────────────────

@router.get("/health/redis")
async def health_redis():
    """Check Redis connectivity via PING."""
    start = time.perf_counter()
    try:
        import redis as redis_lib

        from app.core.config import settings

        r = redis_lib.from_url(settings.redis_url, socket_connect_timeout=3)
        pong = r.ping()
        r.close()

        if pong:
            return {
                "status": "healthy",
                "service": "redis",
                "latency_ms": _ms_since(start),
                "details": "PING → PONG",
            }
        else:
            return {
                "status": "unhealthy",
                "service": "redis",
                "latency_ms": _ms_since(start),
                "details": "PING returned False",
            }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "redis",
            "latency_ms": _ms_since(start),
            "details": str(e),
        }
