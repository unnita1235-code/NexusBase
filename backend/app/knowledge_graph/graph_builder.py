"""
NexusBase — Knowledge Graph Builder.

Upserts extracted entities and relationships into Neo4j and the
chunk_entities join table in Postgres.

Handles:
  - Entity MERGE (deduplicated by canonical name)
  - Relationship MERGE (with typed edges)
  - Chunk↔Entity provenance linkage
  - Postgres chunk_entities join table population
"""

from __future__ import annotations

import logging

from app.infrastructure.database import get_pool
from app.knowledge_graph.models import Entity, Relationship, ExtractionResult
from app.infrastructure.neo4j_client import run_write, get_driver

logger = logging.getLogger("rag.knowledge_graph.graph_builder")


# ── Neo4j Cypher Templates ────────────────────────────────────

MERGE_ENTITY = """
MERGE (e:Entity {name: $name})
SET e.type = $type,
    e.description = $description,
    e.access_level = $access_level
"""

MERGE_CHUNK_NODE = """
MERGE (c:Chunk {chunk_id: $chunk_id})
SET c.access_level = $access_level
"""

LINK_ENTITY_TO_CHUNK = """
MATCH (e:Entity {name: $entity_name})
MATCH (c:Chunk {chunk_id: $chunk_id})
MERGE (e)-[:EXTRACTED_FROM]->(c)
"""

MERGE_RELATIONSHIP = """
MATCH (a:Entity {name: $source})
MATCH (b:Entity {name: $target})
MERGE (a)-[r:RELATES_TO {type: $relation_type}]->(b)
SET r.description = $description,
    r.access_level = $access_level,
    r.source_chunk_id = $source_chunk_id
"""

# ── Postgres SQL ──────────────────────────────────────────────

INSERT_CHUNK_ENTITY_SQL = """
INSERT INTO chunk_entities (chunk_id, entity_name, entity_type)
VALUES ($1, $2, $3)
ON CONFLICT (chunk_id, entity_name) DO NOTHING
"""


async def upsert_extraction(result: ExtractionResult) -> int:
    """
    Upsert an extraction result into Neo4j and Postgres.

    Performs all operations atomically per chunk:
      1. Create/update entity nodes in Neo4j
      2. Create Chunk node and link entities to it
      3. Create/update relationship edges
      4. Insert into Postgres chunk_entities join table

    Args:
        result: The ExtractionResult from the extractor.

    Returns:
        Number of entities successfully upserted.
    """
    if not result.entities:
        return 0

    chunk_id = result.source_chunk_id
    upserted = 0

    # ── Neo4j upserts (graceful degradation) ──────────────────
    driver = get_driver()
    if driver is not None:
        try:
            # Create chunk node
            access_level = result.entities[0].access_level if result.entities else "public"
            await run_write(MERGE_CHUNK_NODE, {
                "chunk_id": chunk_id,
                "access_level": access_level,
            })

            # Upsert entities
            for entity in result.entities:
                await run_write(MERGE_ENTITY, {
                    "name": entity.name,
                    "type": entity.type,
                    "description": entity.description,
                    "access_level": entity.access_level,
                })

                # Link entity to chunk
                await run_write(LINK_ENTITY_TO_CHUNK, {
                    "entity_name": entity.name,
                    "chunk_id": chunk_id,
                })
                upserted += 1

            # Upsert relationships
            for rel in result.relationships:
                await run_write(MERGE_RELATIONSHIP, {
                    "source": rel.source_entity,
                    "target": rel.target_entity,
                    "relation_type": rel.relation_type,
                    "description": rel.description,
                    "access_level": rel.access_level,
                    "source_chunk_id": rel.source_chunk_id,
                })

            logger.info(
                f"  Neo4j: {len(result.entities)} entities, "
                f"{len(result.relationships)} relationships upserted for {chunk_id}"
            )
        except Exception as e:
            logger.error(f"  Neo4j upsert failed for {chunk_id}: {e}")
    else:
        logger.warning(f"  Neo4j unavailable — skipping graph upsert for {chunk_id}")

    # ── Postgres chunk_entities (always runs) ─────────────────
    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            for entity in result.entities:
                await conn.execute(
                    INSERT_CHUNK_ENTITY_SQL,
                    chunk_id,
                    entity.name,
                    entity.type,
                )
        logger.info(
            f"  Postgres: {len(result.entities)} chunk_entities inserted for {chunk_id}"
        )
    except Exception as e:
        logger.error(f"  Postgres chunk_entities insert failed for {chunk_id}: {e}")

    return upserted
