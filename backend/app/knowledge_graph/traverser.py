"""
NexusBase — Multi-hop graph traversal for query-time retrieval.

Per enterprise-rag-standard §5:
  - For multi-hop queries, traverse the knowledge graph to discover
    connected entities and their source chunks.
  - Access levels are checked at every node in the traversal path.
  - Traversal path is logged for observability.
"""

from __future__ import annotations

import logging

from app.config import settings
from app.shared.models import allowed_levels_for, AccessLevel
from app.knowledge_graph.models import Entity, Relationship, TraversalResult
from app.knowledge_graph.neo4j_client import run_query, get_driver

logger = logging.getLogger("rag.knowledge_graph.traverser")


async def traverse_graph(
    seed_entities: list[str],
    access_level: AccessLevel,
    max_hops: int | None = None,
) -> TraversalResult:
    """
    Perform multi-hop graph traversal from seed entities.

    Finds connected entities within max_hops distance, respecting
    access level permissions at every node.

    Args:
        seed_entities: Entity names to start traversal from.
        access_level: Caller's access level for filtering.
        max_hops: Maximum traversal depth (defaults to config value).

    Returns:
        TraversalResult with connected entities, relationships,
        traversal path, and related chunk_ids to fetch from pgvector.
    """
    if not seed_entities:
        return TraversalResult()

    driver = get_driver()
    if driver is None:
        logger.warning("Neo4j unavailable — returning empty traversal")
        return TraversalResult()

    hops = max_hops or settings.graph_traversal_max_hops
    allowed = allowed_levels_for(access_level)

    logger.info(
        f"Graph traversal: seeds={seed_entities}, "
        f"max_hops={hops}, allowed_levels={allowed}"
    )

    # ── 1. Find connected entities via variable-length paths ──
    entity_cypher = f"""
    MATCH path = (start:Entity)-[*1..{hops}]-(connected:Entity)
    WHERE start.name IN $seeds
      AND connected.access_level IN $allowed_levels
      AND ALL(n IN nodes(path) WHERE n.access_level IN $allowed_levels)
    WITH connected, min(length(path)) AS distance
    RETURN DISTINCT
        connected.name AS name,
        connected.type AS type,
        connected.description AS description,
        connected.access_level AS access_level,
        distance
    ORDER BY distance
    LIMIT 20
    """

    entity_records = await run_query(entity_cypher, {
        "seeds": seed_entities,
        "allowed_levels": allowed,
    })

    # ── 2. Find relationships between discovered entities ─────
    all_entity_names = list(seed_entities)
    entities: list[Entity] = []

    for record in entity_records:
        name = record.get("name", "")
        if name and name not in all_entity_names:
            all_entity_names.append(name)
        entities.append(Entity(
            name=name,
            type=record.get("type", "Unknown"),
            description=record.get("description", ""),
            access_level=record.get("access_level", "public"),
        ))

    rel_cypher = """
    MATCH (a:Entity)-[r:RELATES_TO]->(b:Entity)
    WHERE a.name IN $entity_names AND b.name IN $entity_names
      AND r.access_level IN $allowed_levels
    RETURN
        a.name AS source,
        b.name AS target,
        r.type AS relation_type,
        r.description AS description,
        r.access_level AS access_level,
        r.source_chunk_id AS source_chunk_id
    """

    rel_records = await run_query(rel_cypher, {
        "entity_names": all_entity_names,
        "allowed_levels": allowed,
    })

    relationships: list[Relationship] = []
    for record in rel_records:
        relationships.append(Relationship(
            source_entity=record.get("source", ""),
            target_entity=record.get("target", ""),
            relation_type=record.get("relation_type", "RELATES_TO"),
            description=record.get("description", ""),
            source_chunk_id=record.get("source_chunk_id", ""),
            access_level=record.get("access_level", "public"),
        ))

    # ── 3. Collect chunk IDs linked to discovered entities ────
    chunk_cypher = """
    MATCH (e:Entity)-[:EXTRACTED_FROM]->(c:Chunk)
    WHERE e.name IN $entity_names
      AND c.access_level IN $allowed_levels
    RETURN DISTINCT c.chunk_id AS chunk_id
    """

    chunk_records = await run_query(chunk_cypher, {
        "entity_names": all_entity_names,
        "allowed_levels": allowed,
    })

    related_chunk_ids = [r["chunk_id"] for r in chunk_records if r.get("chunk_id")]

    # ── 4. Build traversal path for observability ─────────────
    traversal_path: list[str] = []
    for entity_name in seed_entities:
        traversal_path.append(entity_name)
    for rel in relationships:
        traversal_path.append(f"--[{rel.relation_type}]-->")
        if rel.target_entity not in traversal_path:
            traversal_path.append(rel.target_entity)

    # Determine max hop count from entity distances
    max_distance = max(
        (r.get("distance", 0) for r in entity_records),
        default=0,
    )

    logger.info(
        f"  Traversal complete: {len(entities)} entities, "
        f"{len(relationships)} relationships, "
        f"{len(related_chunk_ids)} linked chunks, "
        f"max_hops_used={max_distance}"
    )

    return TraversalResult(
        entities=entities,
        relationships=relationships,
        traversal_path=traversal_path,
        related_chunk_ids=related_chunk_ids,
        hop_count=max_distance,
    )
