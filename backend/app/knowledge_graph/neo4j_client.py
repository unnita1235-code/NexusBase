"""
NexusBase — Neo4j async driver wrapper.

Manages the Neo4j driver lifecycle (connect, query, close) for the
knowledge graph module. Uses the official neo4j Python async driver.

Connection is initialized during FastAPI lifespan and shared globally.
"""

from __future__ import annotations

import logging
from typing import Any

from neo4j import AsyncGraphDatabase, AsyncDriver

logger = logging.getLogger("rag.knowledge_graph.neo4j_client")

# ── Module-level singleton ────────────────────────────────────
_driver: AsyncDriver | None = None


async def init_neo4j(uri: str, auth: tuple[str, str]) -> None:
    """
    Initialize the Neo4j async driver singleton.

    Called during FastAPI lifespan startup.
    """
    global _driver
    _driver = AsyncGraphDatabase.driver(uri, auth=auth)

    # Verify connectivity
    try:
        async with _driver.session() as session:
            result = await session.run("RETURN 1 AS connected")
            record = await result.single()
            if record and record["connected"] == 1:
                logger.info(f"Neo4j connected: {uri}")
            else:
                logger.warning("Neo4j connection returned unexpected result")
    except Exception as e:
        logger.warning(f"Neo4j connection failed (non-fatal): {e}")
        logger.warning("GraphRAG features will be unavailable until Neo4j is reachable")


async def close_neo4j() -> None:
    """Close the Neo4j driver. Called during FastAPI lifespan shutdown."""
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None
        logger.info("Neo4j driver closed")


def get_driver() -> AsyncDriver | None:
    """Return the current Neo4j driver (may be None if not initialized)."""
    return _driver


async def run_query(
    cypher: str,
    params: dict[str, Any] | None = None,
    database: str = "neo4j",
) -> list[dict[str, Any]]:
    """
    Execute a Cypher query and return results as a list of dicts.

    Args:
        cypher: Cypher query string.
        params: Query parameters.
        database: Neo4j database name.

    Returns:
        List of record dictionaries. Returns empty list if driver unavailable.
    """
    if _driver is None:
        logger.warning("Neo4j driver not available — skipping query")
        return []

    try:
        async with _driver.session(database=database) as session:
            result = await session.run(cypher, params or {})
            records = await result.data()
            return records
    except Exception as e:
        logger.error(f"Neo4j query failed: {e}")
        return []


async def run_write(
    cypher: str,
    params: dict[str, Any] | None = None,
    database: str = "neo4j",
) -> None:
    """
    Execute a write Cypher query (MERGE, CREATE, SET, etc).

    Args:
        cypher: Cypher write query.
        params: Query parameters.
        database: Neo4j database name.
    """
    if _driver is None:
        logger.warning("Neo4j driver not available — skipping write")
        return

    try:
        async with _driver.session(database=database) as session:
            await session.run(cypher, params or {})
    except Exception as e:
        logger.error(f"Neo4j write failed: {e}")
