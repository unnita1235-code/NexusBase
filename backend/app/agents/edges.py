"""
NexusBase — LangGraph conditional edge logic (CRAG — Corrective RAG).
"""

from __future__ import annotations
import logging

from app.core.config import settings
from app.agents.state import GraphState

logger = logging.getLogger("rag.agents.edges")


def route_after_grading(state: GraphState) -> str:
    """
    Conditional edge after grade_documents.
    """
    web_search_needed = state.get("web_search_needed", False)
    retry_count = state.get("retry_count", 0)
    relevance_ratio = state.get("relevance_ratio", 0.0)
    max_retries = settings.max_rewrite_retries

    if not web_search_needed:
        logger.info(f"  Routing → generate (relevance_ratio={relevance_ratio:.0%})")
        return "generate"

    # 0% relevant — route to deep_research
    logger.info(f"  Routing → deep_research (0% relevant)")
    return "deep_research"


def route_semantic_query(state: GraphState) -> str:
    """
    Conditional edge after semantic_router.
    """
    route = state.get("route", "document")
    logger.info(f"  Routing → {route} (semantic router decision)")
    return route
