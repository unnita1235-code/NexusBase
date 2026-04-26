
import asyncio
from app.config import settings
from app.shared.db import init_pool, get_pool

async def apply_migration():
    await init_pool(settings.db_dsn)
    pool = get_pool()
    async with pool.acquire() as conn:
        print("Adding document_hash column...")
        try:
            await conn.execute("ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS document_hash text")
            print("Adding index idx_chunks_source_hash...")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_source_hash ON document_chunks (source, document_hash)")
            print("Migration successful.")
        except Exception as e:
            print(f"Migration failed: {e}")

if __name__ == "__main__":
    asyncio.run(apply_migration())
