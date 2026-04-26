"""
NexusBase — LangGraph state definition (CRAG + GraphRAG).

Defines the shared GraphState TypedDict that flows through every node
in the self-corrective RAG state machine.

CRAG + GraphRAG flow:
  [classify query] → retrieve (graph-first or hybrid) → grade_documents →
    → generate            (if >0% relevant)
    → query_rewrite       (if 0% relevant, retries < max)
       → retrieve         (loop)
    → secondary_search    (if 0% relevant, retries exhausted)
       → generate
"""

from __future__ import annotations

from typing import TypedDict

from app.shared.models import RetrievedChunk


class GraphState(TypedDict):
    """
    Shared state for the CRAG + GraphRAG pipeline.

    Attributes:
        question: The user's original query.
        active_query: The current query (may be rewritten by the CRAG loop).
        access_level: Caller's access level string.
        documents: Retrieved chunks from the vector store.
        generation: The final generated answer.
        web_search_needed: Flag set by grade_documents if context is insufficient.
        graph_path: Ordered list of node names visited (for observability).
        retry_count: Number of query rewrite retries attempted.
        relevance_ratio: Fraction of chunks graded relevant (0.0–1.0).
        rewritten_query: The LLM-rewritten query (if rewrite occurred).
        total_graded: Total number of chunks that were graded.
        total_relevant: Number of chunks graded as relevant.
        query_type: "simple" or "multi_hop" (from query classifier).
        graph_entities: Entity names extracted from the query.
        graph_traversal_path: Neo4j traversal path for observability.
    """
    question: str
    active_query: str
    access_level: str
    documents: list[RetrievedChunk]
    generation: str
    web_search_needed: bool
    graph_path: list[str]
    retry_count: int
    relevance_ratio: float
    rewritten_query: str
    total_graded: int
    total_relevant: int
    query_type: str
    graph_entities: list[str]
    graph_traversal_path: list[str]
    route: str  # "analytical", "document", or "summarization"
    retrieval_time_ms: int
    use_hyde: bool
    hyde_answer: str | None
