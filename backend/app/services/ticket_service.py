from uuid import UUID
from fastapi import Depends, HTTPException
from asyncpg import Pool
import google.generativeai as genai
import json

from app.domain.tickets import TicketCreate, TicketInDB, TicketResponse, TicketPriority, TicketSentiment
from app.infrastructure.database import get_pool
from app.core.config import settings

async def classify_ticket_content(title: str, description: str) -> dict:
    """Use Gemini to classify priority, sentiment, and category based on text."""
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.router_model)
    
    prompt = f"""You are an AI support agent classifier. 
Analyze the following support ticket and classify it into priority, sentiment, and category.

Title: {title}
Description: {description}

Categories: login_issue, billing, feature_request, bug_report, general_inquiry.
Priority: low, medium, high, critical.
Sentiment: positive, neutral, negative.

Return ONLY a valid JSON object:
{{"priority": "medium", "sentiment": "neutral", "category": "general_inquiry"}}
"""
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(temperature=0, response_mime_type="application/json")
        )
        return json.loads(response.text)
    except Exception:
        return {"priority": "medium", "sentiment": "neutral", "category": "general"}


async def create_ticket(ticket_in: TicketCreate, user_id: UUID, pool: Pool = Depends(get_pool)) -> TicketResponse:
    # Auto-classify the ticket using LLM
    classification = await classify_ticket_content(ticket_in.title, ticket_in.description)
    
    priority_str = classification.get("priority", "medium").lower()
    sentiment_str = classification.get("sentiment", "neutral").lower()
    category = classification.get("category", "general").lower()
    
    # ensure enums are valid
    try:
        priority = TicketPriority(priority_str)
    except ValueError:
        priority = TicketPriority.MEDIUM
        
    try:
        sentiment = TicketSentiment(sentiment_str)
    except ValueError:
        sentiment = TicketSentiment.NEUTRAL

    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            INSERT INTO tickets (user_id, title, description, priority, sentiment, category)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id, user_id, title, description, status, priority, sentiment, category, created_at, updated_at
        ''', user_id, ticket_in.title, ticket_in.description, priority.value, sentiment.value, category)
        
    return TicketResponse(**dict(row))

async def get_user_tickets(user_id: UUID, pool: Pool = Depends(get_pool)) -> list[TicketResponse]:
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM tickets WHERE user_id = $1 ORDER BY created_at DESC", user_id)
        return [TicketResponse(**dict(row)) for row in rows]
