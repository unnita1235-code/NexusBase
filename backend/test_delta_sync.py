
import asyncio
import hashlib
import logging
from unittest.mock import patch, MagicMock
from pathlib import Path

from app.config import settings
from app.shared.db import init_pool, get_pool
from app.ingestion.pipeline import ingest_document

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_delta_sync")

async def test_delta_sync():
    # 1. Initialize DB pool
    await init_pool(settings.db_dsn)
    pool = get_pool()
    
    test_filename = "delta_test.md"
    test_path = Path(test_filename)
    test_content_v1 = b"Hello world. This is version 1."
    test_content_v2 = b"Hello world. This is version 2."
    
    # Mocking external calls
    with patch("app.ingestion.pipeline.get_embeddings") as mock_embed, \
         patch("app.ingestion.pipeline._extract_and_populate_graph") as mock_graph:
        
        # Mock embeddings to return dummy vectors of size 1536
        mock_embed.side_effect = lambda texts: [[0.1] * 1536 for _ in texts]
        mock_graph.return_value = None
        
        logger.info("--- Phase 1: Initial Ingestion ---")
        chunks1 = await ingest_document(test_filename, "public", content_bytes=test_content_v1)
        logger.info(f"Phase 1 created {chunks1} chunks.")
        
        # Verify hash in DB
        async with pool.acquire() as conn:
            hash1 = await conn.fetchval("SELECT document_hash FROM document_chunks WHERE source = $1 LIMIT 1", test_filename)
            count1 = await conn.fetchval("SELECT count(*) FROM document_chunks WHERE source = $1", test_filename)
            logger.info(f"DB Hash: {hash1[:8]}..., Chunk Count: {count1}")
            assert hash1 == hashlib.sha256(test_content_v1).hexdigest()
            assert count1 > 0

        logger.info("\n--- Phase 2: Duplicate Ingestion (Should Skip) ---")
        chunks2 = await ingest_document(test_filename, "public", content_bytes=test_content_v1)
        logger.info(f"Phase 2 created {chunks2} chunks (expected 0).")
        assert chunks2 == 0

        logger.info("\n--- Phase 3: Modified Ingestion (Should Update) ---")
        chunks3 = await ingest_document(test_filename, "public", content_bytes=test_content_v2)
        logger.info(f"Phase 3 created {chunks3} chunks.")
        
        async with pool.acquire() as conn:
            hash2 = await conn.fetchval("SELECT document_hash FROM document_chunks WHERE source = $1 LIMIT 1", test_filename)
            count2 = await conn.fetchval("SELECT count(*) FROM document_chunks WHERE source = $1", test_filename)
            logger.info(f"DB Hash: {hash2[:8]}..., Chunk Count: {count2}")
            assert hash2 == hashlib.sha256(test_content_v2).hexdigest()
            assert hash2 != hash1

    logger.info("\n--- Test Passed ---")

if __name__ == "__main__":
    asyncio.run(test_delta_sync())
