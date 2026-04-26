"""
NexusBase — POST /v1/query endpoint.

Accepts a JSON query with access_level and invokes the LangGraph
self-corrective RAG state machine (CRAG + GraphRAG).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.shared.models import QueryRequest, QueryResponse
from app.graph.builder import rag_graph

logger = logging.getLogger("rag.api.query")

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Query the NexusBase GraphRAG system.

    Invokes the LangGraph state machine:
      classify → retrieve (graph/hybrid) → grade → generate (or corrective loop)

    Returns the generated answer, retrieved chunks with scores,
    graph path taken, and GraphRAG metadata for observability.
    """
    logger.info(
        f"Query request: \"{request.query}\" "
        f"(access_level={request.access_level.value}, top_k={request.top_k}, hyde={request.use_hyde})"
    )

    try:
        # Step 1: Embed query for Semantic Cache check
        from app.ingestion.embedder import embed_query
        from app.retrieval.semantic_cache import check_cache, store_cache
        
        query_embedding = embed_query(request.query)
        
        # Step 2: Check Semantic Cache (Zero-Latency Retrieval)
        cached_response = check_cache(query_embedding, request.access_level.value)
        if cached_response:
            # Indicate it was served from cache
            cached_response.graph_path.insert(0, "semantic_cache_hit")
            return cached_response

        # Step 3: Build initial state for CRAG + GraphRAG pipeline
        initial_state = {
            "question": request.query,
            "active_query": request.query,
            "access_level": request.access_level.value,
            "documents": [],
            "generation": "",
            "web_search_needed": False,
            "graph_path": [],
            "retry_count": 0,
            "relevance_ratio": 0.0,
            "rewritten_query": "",
            "total_graded": 0,
            "total_relevant": 0,
            "query_type": "",
            "graph_entities": [],
            "graph_traversal_path": [],
            "retrieval_time_ms": 0,
            "use_hyde": request.use_hyde,
            "hyde_answer": None,
        }

        # Invoke the CRAG + GraphRAG LangGraph state machine
        result = await rag_graph.ainvoke(initial_state)

        # Extract results
        answer = result.get("generation", "No answer generated.")
        chunks = result.get("documents", [])
        graph_path = result.get("graph_path", [])
        relevance_ratio = result.get("relevance_ratio", 0.0)
        rewritten_query = result.get("rewritten_query") or None
        query_type = result.get("query_type", "simple")
        graph_entities = result.get("graph_entities", [])
        graph_traversal_path = result.get("graph_traversal_path", [])
        total_graded = result.get("total_graded", 0)
        total_relevant = result.get("total_relevant", 0)
        retrieval_time_ms = result.get("retrieval_time_ms", 0)

        logger.info(f"Graph path: {' → '.join(graph_path)}")
        logger.info(
            f"Stats: query_type={query_type}, "
            f"relevance_ratio={relevance_ratio:.0%}, "
            f"graph_entities={len(graph_entities)}, "
            f"rewritten_query={rewritten_query or 'N/A'}"
        )

        response = QueryResponse(
            answer=answer,
            chunks=chunks,
            graph_path=graph_path,
            relevance_ratio=relevance_ratio,
            rewritten_query=rewritten_query if rewritten_query else None,
            query_type=query_type,
            graph_entities=graph_entities,
            graph_traversal_path=graph_traversal_path,
            total_graded=total_graded,
            total_relevant=total_relevant,
            retrieval_time_ms=retrieval_time_ms,
        )

        # Step 4: Store successful response in Semantic Cache
        if response.relevance_ratio > 0.0:  # Only cache if we actually found relevant docs
            store_cache(request.query, query_embedding, request.access_level.value, response)

        return response

    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
