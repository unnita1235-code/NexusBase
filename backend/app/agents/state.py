from __future__ import annotations

from typing import TypedDict

from app.domain.rag import RetrievedChunk


class GraphState(TypedDict):
    """
    Shared state for the Customer Support AI Agent pipeline.
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
    route: str  # "analytical", "document", "summarization", or "ticket"
    retrieval_time_ms: int
    use_hyde: bool
    hyde_answer: str | None
    user_id: str | None
    ticket_history: list[dict]
