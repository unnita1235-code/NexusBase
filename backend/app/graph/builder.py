"""
NexusBase — LangGraph state machine builder (CRAG — Corrective RAG).

Assembles the self-corrective RAG graph with query rewrite loop:

    retrieve → grade_documents ──→ generate                   (>0% relevant)
                                ├→ query_rewrite → retrieve   (0% relevant, retries left)
                                └→ secondary_search → generate (0% relevant, retries exhausted)

The compiled graph is exposed as `rag_graph` for use in the /v1/query endpoint.
"""

from __future__ import annotations

import logging

from langgraph.graph import StateGraph, END

from app.agents.state import GraphState
from app.graph.nodes import (
    semantic_router,
    sql_agent,
    summarize_document,
    retrieve,
    grade_documents,
    generate,
    web_search,
    deep_research,
    query_rewrite,
    secondary_search,
)
from app.graph.edges import route_after_grading, route_semantic_query

logger = logging.getLogger("rag.graph.builder")


def build_graph() -> StateGraph:
    """
    Construct and compile the CRAG (Corrective RAG) state machine.

    Graph topology:
        retrieve → grade_documents → generate            (if >0% relevant)
                                   → query_rewrite       (if 0% relevant, retries < max)
                                      → retrieve         (loop back)
                                   → secondary_search    (if 0% relevant, retries exhausted)
                                      → generate

    Returns:
        A compiled LangGraph that can be invoked with an initial GraphState.
    """
    graph = StateGraph(GraphState)

    # ── Add nodes ─────────────────────────────────────────────
    graph.add_node("semantic_router", semantic_router)
    graph.add_node("sql_agent", sql_agent)
    graph.add_node("summarize_document", summarize_document)
    graph.add_node("retrieve", retrieve)
    graph.add_node("grade_documents", grade_documents)
    graph.add_node("generate", generate)
    graph.add_node("web_search", web_search)
    graph.add_node("deep_research", deep_research)
    graph.add_node("query_rewrite", query_rewrite)
    graph.add_node("secondary_search", secondary_search)

    # ── Set entry point ───────────────────────────────────────
    graph.set_entry_point("semantic_router")

    # ── Edges ─────────────────────────────────────────────────

    # semantic_router → sql_agent | retrieve | summarize_document (conditional)
    graph.add_conditional_edges(
        "semantic_router",
        route_semantic_query,
        {
            "analytical": "sql_agent",
            "document": "retrieve",
            "summarization": "summarize_document",
        },
    )

    # sql_agent → END
    graph.add_edge("sql_agent", END)

    # summarize_document → END
    graph.add_edge("summarize_document", END)

    # retrieve → grade_documents (always)
    graph.add_edge("retrieve", "grade_documents")

    # grade_documents → generate | deep_research (conditional)
    graph.add_conditional_edges(
        "grade_documents",
        route_after_grading,
        {
            "generate": "generate",
            "deep_research": "deep_research",
        },
    )

    # deep_research → END (it synthesizes its own answer)
    graph.add_edge("deep_research", END)

    # query_rewrite → retrieve (loop back with rewritten query)
    graph.add_edge("query_rewrite", "retrieve")

    # secondary_search → generate (final fallback produces whatever it found)
    graph.add_edge("secondary_search", "generate")

    # generate → END
    graph.add_edge("generate", END)

    logger.info(
        "Semantic Router Graph compiled: "
        "router → [sql | summarize | retrieve → grade → [generate | rewrite | secondary]]"
    )
    return graph.compile()


# Singleton compiled graph
rag_graph = build_graph()
