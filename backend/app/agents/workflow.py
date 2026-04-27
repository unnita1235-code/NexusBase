import logging
from langgraph.graph import StateGraph, END

from app.agents.state import GraphState

# To be implemented with correct nodes
from app.agents.nodes import (
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
from app.agents.edges import route_after_grading, route_semantic_query

logger = logging.getLogger("rag.agents.workflow")

def build_graph() -> StateGraph:
    graph = StateGraph(GraphState)

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

    graph.set_entry_point("semantic_router")

    graph.add_conditional_edges(
        "semantic_router",
        route_semantic_query,
        {
            "analytical": "sql_agent",
            "document": "retrieve",
            "summarization": "summarize_document",
            "ticket": "retrieve" # Fallback to standard for now
        },
    )

    graph.add_edge("sql_agent", END)
    graph.add_edge("summarize_document", END)
    graph.add_edge("retrieve", "grade_documents")

    graph.add_conditional_edges(
        "grade_documents",
        route_after_grading,
        {
            "generate": "generate",
            "deep_research": "deep_research",
        },
    )

    graph.add_edge("deep_research", END)
    graph.add_edge("query_rewrite", "retrieve")
    graph.add_edge("secondary_search", "generate")
    graph.add_edge("generate", END)

    return graph.compile()

rag_graph = build_graph()
