"""
NexusBase — Knowledge Graph Pydantic models.

Data models for entities, relationships, and traversal results
used across the extraction pipeline and query-time traversal.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Entity(BaseModel):
    """An entity extracted from a document chunk by Gemini 3.1 Pro."""
    name: str                       # Canonical name (e.g., "Project Alpha")
    type: str                       # Person, Project, Department, Budget, Policy, etc.
    description: str = ""           # One-line description from context
    source_chunk_id: str = ""       # Provenance back to document_chunks
    access_level: str = "public"    # Inherited from parent chunk (rule §1)


class Relationship(BaseModel):
    """A relationship between two entities, extracted from a document chunk."""
    source_entity: str              # Entity name (from)
    target_entity: str              # Entity name (to)
    relation_type: str              # e.g., "AFFECTS", "MANAGES", "FUNDED_BY"
    description: str = ""           # Natural language description of the edge
    source_chunk_id: str = ""       # Provenance
    access_level: str = "public"    # Inherited from parent chunk


class ExtractionResult(BaseModel):
    """Output of the entity/relationship extraction for a single chunk."""
    entities: list[Entity] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    source_chunk_id: str = ""


class TraversalResult(BaseModel):
    """Output of a multi-hop graph traversal at query time."""
    entities: list[Entity] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    traversal_path: list[str] = Field(default_factory=list)
    related_chunk_ids: list[str] = Field(default_factory=list)
    hop_count: int = 0
