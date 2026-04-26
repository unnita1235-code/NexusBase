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

from app.config import settings
from app.shared.models import AccessLevel, RetrievedChunk
from app.retrieval import query_engine
from app.retrieval.query_classifier import classify_query
from app.retrieval.logger import log_graph_traversal
from app.graph.state import GraphState

logger = logging.getLogger("rag.graph.nodes")


# ─── Node 0: Semantic Router ─────────────────────────────────

async def semantic_router(state: GraphState) -> dict:
    """
    Classify the user query into one of three paths:
    analytical, document, or summarization.

    Constraint: Uses Gemini with strict JSON output.
    """
    logger.info("── Node: SEMANTIC_ROUTER ──")
    question = state["question"]

    genai.configure(api_key=settings.gemini_api_key)
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

    client = OpenAI(api_key=settings.openai_api_key)
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

    client = OpenAI(api_key=settings.openai_api_key)
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

    Flow:
      1. Classify query (simple vs multi-hop)
      2. If multi_hop → traverse knowledge graph → targeted chunk fetch
      3. If simple → standard hybrid search
      4. Store graph metadata in state for observability
    """
    logger.info("── Node: RETRIEVE (GraphRAG) ──")
    start_time = time.perf_counter()

    active_query = state.get("active_query") or state["question"]
    access_level = AccessLevel(state["access_level"])
    retry_count = state.get("retry_count", 0)

    logger.info(f"  Query: \"{active_query}\"")

    # Classify the query (only on first attempt — retries skip classification)
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

        # Log the graph traversal (rule §5)
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


# ─── Node 0: HyDE (Hypothetical Document Embeddings) ──────────

async def hyde(state: GraphState) -> dict:
    """
    Generate a hypothetical answer to the user's question using Claude 3.5 Haiku.
    This hypothetical answer will be used for vector similarity search.
    """
    if not state.get("use_hyde"):
        return {}

    logger.info("── Node: HyDE (Claude 3.5 Haiku) ──")

    question = state["question"]
    
    if not settings.anthropic_api_key:
        logger.warning("  Anthropic API key not configured — skipping HyDE")
        return {}

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    
    prompt = (
        "You are an expert technical assistant. "
        "The user has a question for a RAG system. "
        "Write a detailed, factual, and hypothetical answer to this question. "
        "This answer will be used to improve document retrieval by matching the "
        "semantics of a 'perfect' answer.\n\n"
        f"QUESTION: {question}\n\n"
        "HYPOTHETICAL ANSWER:"
    )

    try:
        response = await client.messages.create(
            model=settings.hyde_model,
            max_tokens=500,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )
        # Handle the list of content blocks
        answer = "".join([block.text for block in response.content if hasattr(block, 'text')])
        logger.info(f"  HyDE generated ({len(answer)} chars)")
        
        path = list(state.get("graph_path", []))
        path.append("hyde")
        
        return {
            "hyde_answer": answer,
            "graph_path": path,
        }
    except Exception as e:
        logger.error(f"  HyDE generation failed: {e}")
        return {}


# ─── Node 2: Grade Documents (Gemini 3 Flash) ────────────────

async def grade_documents(state: GraphState) -> dict:
    """
    Use Gemini 3 Flash to grade each retrieved chunk as relevant or irrelevant.

    Computes the relevance_ratio = relevant / total.
    If relevance_ratio == 0.0 (0% relevant), sets web_search_needed = True
    to trigger the corrective path (query_rewrite or secondary_search).
    """
    logger.info("── Node: GRADE_DOCUMENTS (Gemini 3 Flash) ──")

    question = state.get("active_query") or state["question"]
    documents = state["documents"]

    # Configure Gemini
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.grader_model)

    relevant_docs: list[RetrievedChunk] = []
    total = len(documents)

    for doc in documents:
        prompt = (
            "You are a strict relevance grader for a RAG system.\n\n"
            f"USER QUESTION: {question}\n\n"
            f"DOCUMENT CHUNK:\n{doc.content[:500]}\n\n"
            "Is this document chunk actually relevant to answering the user's question? "
            "Consider semantic relevance, not just keyword overlap.\n"
            "Respond with ONLY 'yes' or 'no'."
        )

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
            logger.warning(f"  Gemini grading failed for {doc.chunk_id}: {e}, defaulting to 'no'")
            grade = "no"

        if grade == "yes":
            relevant_docs.append(doc)
            logger.info(
                f"  ✓ RELEVANT: {doc.chunk_id} "
                f"(weighted={doc.weighted_score:.4f}, rrf={doc.rrf_score:.4f})"
            )
        else:
            logger.info(f"  ✗ IRRELEVANT: {doc.chunk_id}")

    relevance_ratio = len(relevant_docs) / total if total > 0 else 0.0
    web_search_needed = len(relevant_docs) == 0  # 0% relevant → trigger correction

    path = list(state.get("graph_path", []))
    path.append("grade_documents")

    logger.info(
        f"  Grading complete: {len(relevant_docs)}/{total} relevant "
        f"({relevance_ratio:.0%}) | web_search_needed={web_search_needed}"
    )

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
    client = OpenAI(api_key=settings.openai_api_key)

    # Build context from documents
    context_parts = []
    for doc in documents:
        source_label = f"[{doc.source}]" if hasattr(doc, "source") else ""
        content = doc.content if isinstance(doc, RetrievedChunk) else str(doc)
        context_parts.append(f"{source_label}\n{content}")

    context = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant context found."

    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant that answers questions based on the provided context. "
                    "If the context doesn't contain enough information, say so clearly. "
                    "Always cite your sources by mentioning the document name."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Context:\n{context}\n\n"
                    f"Question: {question}\n\n"
                    "Answer:"
                ),
            },
        ],
        temperature=0.3,
        max_tokens=1024,
    )

    answer = response.choices[0].message.content.strip()
    logger.info(f"  Generated answer ({len(answer)} chars)")

    path = list(state.get("graph_path", []))
    path.append("generate")

    return {
        "generation": answer,
        "graph_path": path,
    }


# ─── Node 4: Web Search Fallback ─────────────────────────────

async def web_search(state: GraphState) -> dict:
    """
    Fallback to Tavily web search when internal documents are insufficient.

    Appends web results as synthetic RetrievedChunk objects so
    the generate node can consume them uniformly.
    """
    logger.info("── Node: WEB_SEARCH ──")

    question = state.get("active_query") or state["question"]

    if not settings.tavily_api_key:
        logger.warning("  Tavily API key not configured — skipping web search")
        path = list(state.get("graph_path", []))
        path.append("web_search")
        return {"graph_path": path}

    tavily = TavilyClient(api_key=settings.tavily_api_key)
    results = tavily.search(query=question, max_results=3)

    web_chunks: list[RetrievedChunk] = []
    for i, result in enumerate(results.get("results", []), start=1):
        web_chunks.append(RetrievedChunk(
            rank=i,
            chunk_id=f"web_result_{i}",
            source=result.get("url", "web"),
            content=result.get("content", ""),
            access_level="public",
            distance_score=0.0,
            rrf_score=0.0,
            weighted_score=0.0,
        ))
        logger.info(f"  Web result #{i}: {result.get('url', 'N/A')}")

    # Combine with any existing documents
    existing_docs = state.get("documents", [])
    combined = existing_docs + web_chunks

    path = list(state.get("graph_path", []))
    path.append("web_search")

    return {
        "documents": combined,
        "graph_path": path,
    }


# ─── Node 5: Query Rewrite (CRAG correction) ─────────────────

async def query_rewrite(state: GraphState) -> dict:
    """
    Rewrite the user's query to improve retrieval on the next attempt.

    Triggered when 0% of chunks are graded relevant. Uses the LLM
    to produce a semantically richer reformulation of the original query.
    Increments retry_count so the graph knows when to stop looping.
    """
    logger.info("── Node: QUERY_REWRITE ──")

    original_question = state["question"]
    current_query = state.get("active_query") or original_question
    retry = state.get("retry_count", 0)

    client = OpenAI(api_key=settings.openai_api_key)

    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a query optimizer for a RAG retrieval system. "
                    "The original query failed to retrieve relevant documents. "
                    "Rewrite the query to be more specific, use alternative terms, "
                    "expand abbreviations, and add context that might help match "
                    "relevant documents in the vector store.\n\n"
                    "Rules:\n"
                    "- Output ONLY the rewritten query, nothing else.\n"
                    "- Keep the same intent as the original question.\n"
                    "- Make it more descriptive and search-friendly.\n"
                    "- Do NOT add questions marks or extra formatting."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Original question: {original_question}\n"
                    f"Failed query (attempt #{retry + 1}): {current_query}\n\n"
                    "Rewritten query:"
                ),
            },
        ],
        temperature=0.5,
        max_tokens=200,
    )

    rewritten = response.choices[0].message.content.strip()

    logger.info(f"  Original: \"{current_query}\"")
    logger.info(f"  Rewritten: \"{rewritten}\"")
    logger.info(f"  Retry count: {retry} → {retry + 1}")

    path = list(state.get("graph_path", []))
    path.append("query_rewrite")

    return {
        "active_query": rewritten,
        "rewritten_query": rewritten,
        "retry_count": retry + 1,
        "graph_path": path,
    }


# ─── Node 6: Secondary Search (CRAG final fallback) ──────────

async def secondary_search(state: GraphState) -> dict:
    """
    Search across secondary internal databases when query rewrite
    also fails to produce relevant results.

    This is the last-resort fallback before generation. It performs
    a broader search with relaxed parameters (higher top_k, all
    access levels the caller can see) and a loosened keyword match.
    """
    logger.info("── Node: SECONDARY_SEARCH ──")

    question = state["question"]
    active_query = state.get("active_query") or question
    access_level = AccessLevel(state["access_level"])

    from app.shared.models import allowed_levels_for
    from app.ingestion.embedder import embed_query
    from app.retrieval.hybrid_search import semantic_search, keyword_search, reciprocal_rank_fusion

    allowed = allowed_levels_for(access_level)

    # Broader search: 3x top_k, using BOTH original and rewritten queries
    extended_top_k = settings.top_k * 3

    logger.info(f"  Broadened search: top_k={extended_top_k}, queries=[original, rewritten]")

    # Search with original question
    original_embedding = embed_query(question)
    semantic_original = await semantic_search(original_embedding, allowed, extended_top_k)
    keyword_original = await keyword_search(question, allowed, extended_top_k)

    # Also search with the rewritten query (if different)
    all_semantic = list(semantic_original)
    all_keyword = list(keyword_original)

    if active_query != question:
        rewrite_embedding = embed_query(active_query)
        semantic_rewrite = await semantic_search(rewrite_embedding, allowed, extended_top_k)
        keyword_rewrite = await keyword_search(active_query, allowed, extended_top_k)
        all_semantic.extend(semantic_rewrite)
        all_keyword.extend(keyword_rewrite)

    # Deduplicate by chunk_id before fusion (keep first occurrence)
    seen_ids: set[str] = set()
    deduped_semantic: list[dict] = []
    for r in all_semantic:
        if r["chunk_id"] not in seen_ids:
            seen_ids.add(r["chunk_id"])
            deduped_semantic.append(r)

    seen_ids.clear()
    deduped_keyword: list[dict] = []
    for r in all_keyword:
        if r["chunk_id"] not in seen_ids:
            seen_ids.add(r["chunk_id"])
            deduped_keyword.append(r)

    # Fuse and take top_k
    fused = reciprocal_rank_fusion(deduped_semantic, deduped_keyword, k=settings.rrf_k)
    chunks = fused[: settings.top_k]

    logger.info(f"  Secondary search returned {len(chunks)} chunk(s)")

    # Log the chunks
    from app.retrieval.logger import log_retrieved_chunks
    log_retrieved_chunks(chunks)

    path = list(state.get("graph_path", []))
    path.append("secondary_search")

    return {
        "documents": chunks,
        "graph_path": path,
    }
