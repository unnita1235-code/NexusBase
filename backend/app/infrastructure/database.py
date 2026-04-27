"""
NexusBase — asyncpg database connection pool.

Provides a module-level pool that is created once during FastAPI
lifespan startup and closed on shutdown. All ingestion and retrieval
modules import `get_pool()` to obtain the shared pool.
"""

import asyncpg

_pool: asyncpg.Pool | None = None


async def init_pool(dsn: str, min_size: int = 2, max_size: int = 10) -> asyncpg.Pool:
    """Create and cache the connection pool. Fallback to Mock if connection fails."""
    global _pool
    try:
        _pool = await asyncpg.create_pool(dsn, min_size=min_size, max_size=max_size)
        
        # Register the pgvector type and create tables
        async with _pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            await conn.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
            
            # Users Table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    email TEXT UNIQUE NOT NULL,
                    hashed_password TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
            
            # Tickets Table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS tickets (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    priority TEXT NOT NULL DEFAULT 'medium',
                    sentiment TEXT NOT NULL DEFAULT 'neutral',
                    category TEXT NOT NULL DEFAULT 'general',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
            
            # Feedback Table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS feedback (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    ticket_id UUID REFERENCES tickets(id) ON DELETE CASCADE,
                    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                    rating INT NOT NULL CHECK (rating >= 1 AND rating <= 5),
                    comments TEXT,
                    corrected_response TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')

            # ── RAG Tables ──────────────────────────────────────────
            
            # Document Chunks Table (pgvector)
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS document_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    content TEXT NOT NULL,
                    access_level TEXT NOT NULL,
                    embedding VECTOR(1536),
                    page INTEGER,
                    document_hash TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
            
            # Chunk Entities Join Table (GraphRAG)
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS chunk_entities (
                    chunk_id TEXT REFERENCES document_chunks(chunk_id) ON DELETE CASCADE,
                    entity_name TEXT NOT NULL,
                    entity_type TEXT,
                    PRIMARY KEY (chunk_id, entity_name)
                )
            ''')
            
            # System Settings Table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    is_encrypted BOOLEAN DEFAULT FALSE,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')

            # Seed Initial Settings if empty
            count = await conn.fetchval("SELECT COUNT(*) FROM system_settings")
            if count == 0:
                from app.core.config import settings
                initial_settings = [
                    ("llm_model", settings.llm_model, False),
                    ("embedding_model", settings.embedding_model, False),
                    ("top_k", str(settings.top_k), False),
                    ("grader_model", settings.grader_model, False),
                ]
                for key, val, enc in initial_settings:
                    await conn.execute(
                        "INSERT INTO system_settings (key, value, is_encrypted) VALUES ($1, $2, $3)",
                        key, val, enc
                    )
    except Exception as e:
        print(f"!!! WARNING: Postgres connection failed ({e}). USING MOCK DB POOL !!!")
        from unittest.mock import AsyncMock
        _pool = AsyncMock(spec=asyncpg.Pool)
        _pool.acquire.return_value.__aenter__.return_value = AsyncMock(spec=asyncpg.Connection)
        
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
