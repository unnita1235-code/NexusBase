"""
NexusBase — Query Classifier (simple vs multi-hop routing).

Per enterprise-rag-standard §5, multi-hop queries should traverse the
knowledge graph first, while simple lookup queries use standard hybrid search.

Uses Gemini 3 Flash (already configured as the grader) for fast classification.
"""

from __future__ import annotations

import json
import logging

import google.generativeai as genai

from app.config import settings

logger = logging.getLogger("rag.retrieval.query_classifier")

CLASSIFICATION_PROMPT = """You are a query complexity classifier for an enterprise RAG system.

Classify the user's query as either:
- "simple" — a direct lookup question that can be answered from a single document or topic
  Examples: "What is our vacation policy?", "How many sick days do we get?", "What is the deadline for Q4 reports?"

- "multi_hop" — a question that requires connecting information across multiple documents, entities, or topics
  Examples: "How does Project A affect the Q3 budget?", "Which team members who report to Sarah also work on the Alpha initiative?", "What policies govern the systems used by the marketing department?"

Also extract the key entity names mentioned in the query (people, projects, departments, budgets, etc.).

Respond with ONLY valid JSON:
{
  "query_type": "simple" or "multi_hop",
  "entities": ["Entity1", "Entity2"]
}"""


class QueryClassification:
    """Result of query classification."""

    def __init__(self, query_type: str, entities: list[str]):
        self.query_type = query_type  # "simple" or "multi_hop"
        self.entities = entities       # Extracted entity names


async def classify_query(query: str) -> QueryClassification:
    """
    Classify a query as simple or multi-hop and extract entity names.

    Args:
        query: The user's query string.

    Returns:
        QueryClassification with query_type and extracted entities.
    """
    if not settings.gemini_api_key:
        logger.warning("Gemini API key not configured — defaulting to 'simple'")
        return QueryClassification(query_type="simple", entities=[])

    try:
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.grader_model)  # Gemini 3 Flash — fast

        response = model.generate_content(
            [CLASSIFICATION_PROMPT, f"USER QUERY: {query}"],
            generation_config=genai.GenerationConfig(
                temperature=0,
                max_output_tokens=200,
                response_mime_type="application/json",
            ),
        )

        data = json.loads(response.text.strip())
        query_type = data.get("query_type", "simple")
        entities = [e.strip().title() for e in data.get("entities", []) if e.strip()]

        logger.info(f"Query classified: type={query_type}, entities={entities}")

        return QueryClassification(query_type=query_type, entities=entities)

    except Exception as e:
        logger.warning(f"Query classification failed: {e} — defaulting to 'simple'")
        return QueryClassification(query_type="simple", entities=[])
