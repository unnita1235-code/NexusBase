"""
NexusBase — LangGraph conditional edge logic (CRAG — Corrective RAG).

Routing after grade_documents implements the corrective loop:
  - If >0% relevant   → generate  (proceed with answer)
  - If 0% relevant    → query_rewrite  (if retries remaining)
  - If 0% relevant    → secondary_search  (if retries exhausted)
"""

from __future__ import annotations

import logging

from app.config import settings
from app.graph.state import GraphState

logger = logging.getLogger("rag.graph.edges")


def route_after_grading(state: GraphState) -> str:
    """
    Conditional edge after grade_documents.

    Implements the CRAG decision tree:
      1. If relevance_ratio > 0  → "generate"
      2. If relevance_ratio == 0 AND retry_count < max → "query_rewrite"
      3. If relevance_ratio == 0 AND retry_count >= max → "secondary_search"
    """
    web_search_needed = state.get("web_search_needed", False)
    retry_count = state.get("retry_count", 0)
    relevance_ratio = state.get("relevance_ratio", 0.0)
    max_retries = settings.max_rewrite_retries

    if not web_search_needed:
        logger.info(
            f"  Routing → generate "
            f"(relevance_ratio={relevance_ratio:.0%}, documents available)"
        )
        return "generate"

    # 0% relevant — decide between rewrite and secondary search
    if retry_count < max_retries:
        logger.info(
            f"  Routing → query_rewrite "
            f"(0% relevant, retry {retry_count + 1}/{max_retries})"
        )
        return "query_rewrite"
    else:
        logger.info(
            f"  Routing → secondary_search "
            f"(0% relevant, retries exhausted: {retry_count}/{max_retries})"
        )
        return "secondary_search"


def route_semantic_query(state: GraphState) -> str:
    """
    Conditional edge after semantic_router.
    Routes to analytical, document, or summarization path.
    """
    route = state.get("route", "document")
    logger.info(f"  Routing → {route} (semantic router decision)")
    return route
