"""
NexusBase — LangGraph node functions (CRAG + GraphRAG).

Seven nodes in the self-corrective RAG state machine:
  1. retrieve          — Classify query + graph-first or hybrid retrieval
  2. grade_documents   — Gemini 3 Flash grades each chunk as relevant/irrelevant
  3. generate          — LLM generates answer from relevant context
  4. web_search        — Fallback to Tavily web search
  5. query_rewrite     — LLM rewrites the query for better retrieval
  6. secondary_search  — Search across secondary internal databases
"""

from __future__ import annotations
import json
import logging
import time

from openai import OpenAI
import google.generativeai as genai
from tavily import TavilyClient
import anthropic

from app.core.config import settings
from app.domain.rag import AccessLevel, RetrievedChunk
from app.retrieval import query_engine
from app.retrieval.query_classifier import classify_query
from app.retrieval.logger import log_graph_traversal
from app.agents.state import GraphState
from app.core.dynamic_config import get_config_value

logger = logging.getLogger("rag.agents.nodes")


# ─── Node 0: Semantic Router ─────────────────────────────────

async def semantic_router(state: GraphState) -> dict:
    """
    Classify the user query into one of three paths:
    analytical, document, or summarization.

    Constraint: Uses Gemini with strict JSON output.
    """
    logger.info("── Node: SEMANTIC_ROUTER ──")
    question = state["question"]

    api_key = await get_config_value("gemini_api_key", settings.gemini_api_key)
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(settings.router_model)

    prompt = f"""You are an expert query router for an enterprise RAG system.
Your task is to classify the user's question into exactly ONE of the following categories:

1. 'analytical': For questions requiring data analysis, counts, or structured database queries.
   Example: "How many users signed up last month?" or "What is the average order value?"

2. 'document': For questions requiring information retrieval from documents (PDFs, policies, manuals).
   Example: "What is the PTO policy?" or "How do I reset my password?"

3. 'summarization': For requests to summarize a specific document or long text provided in the prompt.
   Example: "Summarize the attached contract" or "Can you give me a summary of the 2024 roadmap?"

USER QUESTION: {question}

Respond with ONLY a JSON object in this format:
{{"route": "analytical" | "document" | "summarization"}}"""

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0,
                response_mime_type="application/json",
            ),
        )
        data = json.loads(response.text)
        route = data.get("route", "document")
    except Exception as e:
        logger.error(f"  Router failed: {e}. Defaulting to 'document'")
        route = "document"

    logger.info(f"  Decision: {route}")

    path = list(state.get("graph_path", []))
    path.append("semantic_router")

    return {"route": route, "graph_path": path}


# ─── Node: SQL Agent (Stub) ─────────────────────────────────

async def sql_agent(state: GraphState) -> dict:
    """
    Analytical path: processes structured data queries.
    """
    logger.info("── Node: SQL_AGENT ──")
    question = state["question"]

    api_key = await get_config_value("openai_api_key", settings.openai_api_key)
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": "You are a SQL Agent. Answer the user's analytical question based on your simulated database access."},
            {"role": "user", "content": question}
        ]
    )

    answer = response.choices[0].message.content.strip()
    path = list(state.get("graph_path", []))
    path.append("sql_agent")

    return {"generation": answer, "graph_path": path}


# ─── Node: Summarize Document (Stub) ───────────────────────

async def summarize_document(state: GraphState) -> dict:
    """
    Summarization path: directly summarizes text without searching.
    """
    logger.info("── Node: SUMMARIZE_DOCUMENT ──")
    question = state["question"]

    api_key = await get_config_value("openai_api_key", settings.openai_api_key)
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": "You are a summarization expert. Provide a concise summary of the document or topic requested."},
            {"role": "user", "content": question}
        ]
    )

    answer = response.choices[0].message.content.strip()
    path = list(state.get("graph_path", []))
    path.append("summarize_document")

    return {"generation": answer, "graph_path": path}


# ─── Node 1: Retrieve (GraphRAG-aware) ───────────────────────

async def retrieve(state: GraphState) -> dict:
    """
    Retrieve relevant document chunks — graph-first for multi-hop queries.
    """
    logger.info("── Node: RETRIEVE (GraphRAG) ──")
    start_time = time.perf_counter()

    active_query = state.get("active_query") or state["question"]
    access_level = AccessLevel(state["access_level"])
    retry_count = state.get("retry_count", 0)

    logger.info(f"  Query: \"{active_query}\"")

    # Classify the query (only on first attempt)
    query_type = state.get("query_type", "")
    graph_entities: list[str] = list(state.get("graph_entities", []))
    graph_traversal_path: list[str] = list(state.get("graph_traversal_path", []))

    if not query_type or retry_count == 0:
        classification = await classify_query(active_query)
        query_type = classification.query_type
        graph_entities = classification.entities

    if query_type == "multi_hop" and graph_entities:
        # Graph-first retrieval
        logger.info(f"  Multi-hop query → graph traversal (entities={graph_entities})")
        chunks, traversal = await query_engine.graph_search(
            query=active_query,
            access_level=access_level,
            classification=type("C", (), {
                "query_type": query_type,
                "entities": graph_entities,
            })(),
            top_k=settings.top_k,
            hyde_answer=state.get("hyde_answer"),
        )
        graph_traversal_path = traversal.traversal_path

        log_graph_traversal(
            seed_entities=graph_entities,
            traversal_path=traversal.traversal_path,
            hop_count=traversal.hop_count,
            connected_chunk_ids=traversal.related_chunk_ids,
            query_type=query_type,
        )
    else:
        # Standard hybrid search
        logger.info("  Simple query → standard hybrid search")
        chunks = await query_engine.search(
            query=active_query,
            access_level=access_level,
            top_k=settings.top_k,
            hyde_answer=state.get("hyde_answer"),
        )

    path = list(state.get("graph_path", []))
    path.append("retrieve")

    return {
        "documents": chunks,
        "graph_path": path,
        "query_type": query_type,
        "graph_entities": graph_entities,
        "graph_traversal_path": graph_traversal_path,
        "retrieval_time_ms": int((time.perf_counter() - start_time) * 1000),
    }


# ─── Node 2: Grade Documents (Gemini 3 Flash) ────────────────

async def grade_documents(state: GraphState) -> dict:
    """
    Use Gemini 3 Flash to grade each retrieved chunk as relevant or irrelevant.
    """
    logger.info("── Node: GRADE_DOCUMENTS (Gemini 3 Flash) ──")

    question = state.get("active_query") or state["question"]
    documents = state["documents"]

    api_key = await get_config_value("gemini_api_key", settings.gemini_api_key)
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(settings.grader_model)

    relevant_docs: list[RetrievedChunk] = []
    total = len(documents)

    default_prompt_template = (
        "You are a strict relevance grader for a RAG system.\n\n"
        "USER QUESTION: {question}\n\n"
        "DOCUMENT CHUNK:\n{chunk_content}\n\n"
        "Is this document chunk actually relevant to answering the user's question? "
        "Consider semantic relevance, not just keyword overlap.\n"
        "Respond with ONLY 'yes' or 'no'."
    )
    prompt_template = await get_config_value("grader_prompt", default_prompt_template)

    for doc in documents:
        try:
            prompt = prompt_template.format(question=question, chunk_content=doc.content[:500])
        except Exception:
            prompt = default_prompt_template.format(question=question, chunk_content=doc.content[:500])

        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0,
                    max_output_tokens=5,
                ),
            )
            grade = response.text.strip().lower()
        except Exception as e:
            logger.warning(f"  Gemini grading failed: {e}, defaulting to 'no'")
            grade = "no"

        if grade == "yes":
            relevant_docs.append(doc)
            logger.info(f"  ✓ RELEVANT: {doc.chunk_id}")
        else:
            logger.info(f"  ✗ IRRELEVANT: {doc.chunk_id}")

    relevance_ratio = len(relevant_docs) / total if total > 0 else 0.0
    web_search_needed = len(relevant_docs) == 0

    path = list(state.get("graph_path", []))
    path.append("grade_documents")

    return {
        "documents": relevant_docs,
        "web_search_needed": web_search_needed,
        "relevance_ratio": relevance_ratio,
        "total_graded": total,
        "total_relevant": len(relevant_docs),
        "graph_path": path,
    }


# ─── Node 3: Generate ────────────────────────────────────────

async def generate(state: GraphState) -> dict:
    """
    Generate a final answer using the LLM with relevant context.
    """
    logger.info("── Node: GENERATE ──")

    question = state["question"]
    documents = state["documents"]
    
    api_key = await get_config_value("openai_api_key", settings.openai_api_key)
    client = OpenAI(api_key=api_key)

    context_parts = []
    for doc in documents:
        source_label = f"[{doc.source}]" if hasattr(doc, "source") else ""
        content = doc.content if isinstance(doc, RetrievedChunk) else str(doc)
        context_parts.append(f"{source_label}\n{content}")

    context = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant context found."

    default_system_prompt = (
        "You are a helpful assistant that answers questions based on the provided context. "
        "If the context doesn't contain enough information, say so clearly. "
        "Always cite your sources by mentioning the document name."
    )
    system_prompt = await get_config_value("system_prompt", default_system_prompt)

    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"},
        ],
        temperature=0.3,
        max_tokens=1024,
    )

    answer = response.choices[0].message.content.strip()
    path = list(state.get("graph_path", []))
    path.append("generate")

    return {"generation": answer, "graph_path": path}


# ─── Node 4: Web Search Fallback ─────────────────────────────

async def web_search(state: GraphState) -> dict:
    """
    Fallback to Tavily web search.
    """
    logger.info("── Node: WEB_SEARCH ──")
    question = state.get("active_query") or state["question"]

    api_key = await get_config_value("tavily_api_key", settings.tavily_api_key)
    if not api_key:
        logger.warning("  Tavily API key not configured — skipping")
        path = list(state.get("graph_path", []))
        path.append("web_search")
        return {"graph_path": path}

    tavily = TavilyClient(api_key=api_key)
    results = tavily.search(query=question, max_results=3)

    web_chunks: list[RetrievedChunk] = []
    for i, result in enumerate(results.get("results", []), start=1):
        web_chunks.append(RetrievedChunk(
            rank=i,
            chunk_id=f"web_result_{i}",
            source=result.get("url", "web"),
            content=result.get("content", ""),
            access_level="public",
        ))

    combined = state.get("documents", []) + web_chunks
    path = list(state.get("graph_path", []))
    path.append("web_search")

    return {"documents": combined, "graph_path": path}


# ─── Node 5: Query Rewrite ─────────────────────────────────

async def query_rewrite(state: GraphState) -> dict:
    """
    Rewrite the user's query.
    """
    logger.info("── Node: QUERY_REWRITE ──")
    original_question = state["question"]
    current_query = state.get("active_query") or original_question
    retry = state.get("retry_count", 0)

    api_key = await get_config_value("openai_api_key", settings.openai_api_key)
    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": "You are a query optimizer. Rewrite the query to be more search-friendly."},
            {"role": "user", "content": f"Original: {original_question}\nFailed: {current_query}\nRewritten:"},
        ],
        temperature=0.5,
    )

    rewritten = response.choices[0].message.content.strip()
    path = list(state.get("graph_path", []))
    path.append("query_rewrite")

    return {
        "active_query": rewritten,
        "rewritten_query": rewritten,
        "retry_count": retry + 1,
        "graph_path": path,
    }


# ─── Node 6: Secondary Search ──────────────────────────────

async def secondary_search(state: GraphState) -> dict:
    """
    Search across secondary internal databases.
    """
    logger.info("── Node: SECONDARY_SEARCH ──")
    question = state["question"]
    active_query = state.get("active_query") or question
    access_level = AccessLevel(state["access_level"])

    from app.domain.rag import allowed_levels_for
    from app.ingestion.embedder import embed_query
    from app.retrieval.hybrid_search import semantic_search, keyword_search, reciprocal_rank_fusion

    allowed = allowed_levels_for(access_level)
    extended_top_k = settings.top_k * 3

    original_embedding = embed_query(question)
    semantic_original = await semantic_search(original_embedding, allowed, extended_top_k)
    keyword_original = await keyword_search(question, allowed, extended_top_k)

    fused = reciprocal_rank_fusion(list(semantic_original), list(keyword_original), k=settings.rrf_k)
    chunks = fused[: settings.top_k]

    path = list(state.get("graph_path", []))
    path.append("secondary_search")

    return {"documents": chunks, "graph_path": path}


# ─── Node 7: Deep Research (Stub) ───────────────────────────

async def deep_research(state: GraphState) -> dict:
    """
    Synthesize a final response when web results are available.
    """
    logger.info("── Node: DEEP_RESEARCH ──")
    return await generate(state)
