"""
NexusBase — Entity & Relationship Extractor (Gemini 3.1 Pro).

Extracts structured entities and relationships from document chunks
using Gemini 3.1 Pro with JSON schema-constrained output.

Per enterprise-rag-standard §5:
  - Every ingested chunk is processed through this extractor.
  - Entities inherit access_level from their source chunk (rule §1).
  - Relationships include provenance (source_chunk_id) for audit trails.
"""

from __future__ import annotations

import json
import logging

import google.generativeai as genai

from app.config import settings
from app.knowledge_graph.models import Entity, Relationship, ExtractionResult

logger = logging.getLogger("rag.knowledge_graph.extractor")

# ── Extraction prompt ─────────────────────────────────────────

EXTRACTION_PROMPT = """You are a knowledge graph extraction engine for an enterprise RAG system.

Given a document chunk, extract ALL entities and relationships present in the text.

ENTITY TYPES (use these or infer new ones):
- Person, Organization, Department, Team
- Project, Product, Service, System
- Document, Policy, Regulation, Standard
- Budget, Revenue, Cost, Financial_Metric
- Date, Quarter, Timeline, Deadline
- Location, Region, Market
- Technology, Tool, Platform
- Process, Workflow, Procedure

RELATIONSHIP TYPES (use these or infer new ones):
- MANAGES, REPORTS_TO, WORKS_ON, LEADS
- AFFECTS, IMPACTS, DEPENDS_ON, RELATES_TO
- FUNDED_BY, ALLOCATES_TO, COSTS
- PRODUCES, CONSUMES, USES
- CREATED_ON, DUE_BY, SCHEDULED_FOR
- LOCATED_IN, BELONGS_TO, PART_OF
- IMPLEMENTS, COMPLIES_WITH, GOVERNS

RULES:
1. Extract EVERY meaningful entity, not just the obvious ones.
2. Canonicalize entity names: use proper casing, expand abbreviations.
3. Each relationship must have a clear source and target entity.
4. Description fields should be concise (1 sentence max).
5. If no entities or relationships are found, return empty arrays.

Respond with ONLY valid JSON in this exact format:
{
  "entities": [
    {"name": "Entity Name", "type": "EntityType", "description": "Brief description"}
  ],
  "relationships": [
    {"source_entity": "From Entity", "target_entity": "To Entity", "relation_type": "RELATION_TYPE", "description": "Brief description"}
  ]
}"""


def _canonicalize_name(name: str) -> str:
    """Normalize entity name for deduplication (aggressive strategy)."""
    return name.strip().title()


async def extract_entities(
    chunk_content: str,
    chunk_id: str,
    access_level: str,
) -> ExtractionResult:
    """
    Extract entities and relationships from a document chunk.

    Uses Gemini 3.1 Pro with structured JSON output for reliable extraction.

    Args:
        chunk_content: The text content of the chunk.
        chunk_id: The chunk's unique ID (for provenance).
        access_level: The chunk's access level (inherited by all extracted entities).

    Returns:
        ExtractionResult with entities and relationships.
    """
    logger.info(f"Extracting entities from chunk: {chunk_id}")

    if not settings.gemini_api_key:
        logger.warning("Gemini API key not configured — skipping extraction")
        return ExtractionResult(source_chunk_id=chunk_id)

    try:
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.extractor_model)

        user_content = f"DOCUMENT CHUNK (chunk_id={chunk_id}):\n\n{chunk_content}"

        response = model.generate_content(
            [EXTRACTION_PROMPT, user_content],
            generation_config=genai.GenerationConfig(
                temperature=0,
                max_output_tokens=2048,
                response_mime_type="application/json",
            ),
        )

        raw_text = response.text.strip()

        # Parse JSON response
        data = json.loads(raw_text)

        # Build Entity objects with provenance and access level
        entities: list[Entity] = []
        seen_names: set[str] = set()

        for raw_entity in data.get("entities", []):
            canonical = _canonicalize_name(raw_entity.get("name", ""))
            if not canonical or canonical in seen_names:
                continue
            seen_names.add(canonical)

            entities.append(Entity(
                name=canonical,
                type=raw_entity.get("type", "Unknown"),
                description=raw_entity.get("description", ""),
                source_chunk_id=chunk_id,
                access_level=access_level,
            ))

        # Build Relationship objects
        relationships: list[Relationship] = []
        for raw_rel in data.get("relationships", []):
            source = _canonicalize_name(raw_rel.get("source_entity", ""))
            target = _canonicalize_name(raw_rel.get("target_entity", ""))
            if not source or not target:
                continue

            relationships.append(Relationship(
                source_entity=source,
                target_entity=target,
                relation_type=raw_rel.get("relation_type", "RELATES_TO"),
                description=raw_rel.get("description", ""),
                source_chunk_id=chunk_id,
                access_level=access_level,
            ))

        logger.info(
            f"  Extracted {len(entities)} entities, "
            f"{len(relationships)} relationships from {chunk_id}"
        )

        return ExtractionResult(
            entities=entities,
            relationships=relationships,
            source_chunk_id=chunk_id,
        )

    except json.JSONDecodeError as e:
        logger.error(f"  Failed to parse Gemini JSON for {chunk_id}: {e}")
        return ExtractionResult(source_chunk_id=chunk_id)
    except Exception as e:
        logger.error(f"  Entity extraction failed for {chunk_id}: {e}")
        return ExtractionResult(source_chunk_id=chunk_id)
