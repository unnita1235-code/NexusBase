"""
NexusBase — asyncpg database connection pool.

Provides a module-level pool that is created once during FastAPI
lifespan startup and closed on shutdown. All ingestion and retrieval
modules import `get_pool()` to obtain the shared pool.
"""

import asyncpg

_pool: asyncpg.Pool | None = None


async def init_pool(dsn: str, min_size: int = 2, max_size: int = 10) -> asyncpg.Pool:
    """Create and cache the connection pool. Called once at startup."""
    global _pool
    _pool = await asyncpg.create_pool(dsn, min_size=min_size, max_size=max_size)

    # Register the pgvector type with every connection in the pool
    async with _pool.acquire() as conn:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

    return _pool


def get_pool() -> asyncpg.Pool:
    """Return the active connection pool. Raises if not initialised."""
    if _pool is None:
        raise RuntimeError(
            "Database pool not initialised. Call init_pool() during app startup."
        )
    return _pool


async def close_pool() -> None:
    """Gracefully close the pool. Called once at shutdown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
