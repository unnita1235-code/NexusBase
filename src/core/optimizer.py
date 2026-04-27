import os
import sys
import asyncio
import json
import logging
from typing import Any

import dspy
import asyncpg
import pandas as pd
from ragas.metrics import answer_relevancy
from langchain_openai import ChatOpenAI
from datasets import Dataset

# Add backend to sys.path for internal imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend")))

from app.config import settings
from app.shared.db import init_pool, get_pool
from app.graph.builder import rag_graph

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("optimizer")

# ─── DSPy Setup ──────────────────────────────────────────────

def setup_dspy():
    """Initialize DSPy with OpenAI settings."""
    lm = dspy.OpenAI(model=settings.llm_model, api_key=settings.openai_api_key)
    dspy.settings.configure(lm=lm)
    return lm

class RAGSignature(dspy.Signature):
    """
    Given a context and a question, generate a helpful and accurate answer.
    Always cite sources from the context.
    """
    context = dspy.InputField(desc="Relevant document chunks")
    question = dspy.InputField(desc="User's question")
    answer = dspy.OutputField(desc="Factual answer based on context")

class RAGModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.generate_answer = dspy.ChainOfThought(RAGSignature)

    def forward(self, question, context):
        return self.generate_answer(question=question, context=context)

# ─── Data Loading ───────────────────────────────────────────

async def fetch_training_data(limit: int = 50) -> list[dspy.Example]:
    """
    Fetch the 50 most recent successful queries from Postgres.
    Falls back to golden_queries.json if the database is unavailable.
    """
    examples = []
    
    try:
        await init_pool(settings.db_dsn)
        pool = get_pool()
        
        async with pool.acquire() as conn:
            # Check if query_logs table exists
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'query_logs'
                )
            """)
            
            if table_exists:
                logger.info("Fetching data from Postgres 'query_logs' table...")
                rows = await conn.fetch("""
                    SELECT query, answer, context 
                    FROM query_logs 
                    WHERE relevance_ratio > 0.8 
                    ORDER BY timestamp DESC 
                    LIMIT $1
                """, limit)
                
                for row in rows:
                    examples.append(dspy.Example(
                        question=row['query'],
                        context=row['context'],
                        answer=row['answer']
                    ).with_inputs('question', 'context'))
            else:
                logger.warning("'query_logs' table not found in Postgres.")
    except Exception as e:
        logger.error(f"Failed to fetch from Postgres: {e}")
    
    if not examples:
        logger.info("Falling back to evaluation/golden_queries.json...")
        golden_path = os.path.join("backend", "evaluation", "golden_queries.json")
        if os.path.exists(golden_path):
            with open(golden_path, "r") as f:
                data = json.load(f)
                for item in data[:limit]:
                    examples.append(dspy.Example(
                        question=item['question'],
                        context=item.get('ground_truth_context', ""), # Assuming context exists
                        answer=item['ground_truth']
                    ).with_inputs('question', 'context'))
    
    logger.info(f"Loaded {len(examples)} examples for training.")
    return examples

# ─── Metric ──────────────────────────────────────────────────

def evaluate_relevancy(example, pred, trace=None):
    """
    Metric to evaluate answer relevancy using Ragas logic.
    """
    # Simplified relevancy check for DSPy optimization loop
    # In a real scenario, we'd invoke Ragas here, but for the loop,
    # we can use a faster LLM-based check or cosine similarity.
    
    # We wrap the Ragas Answer Relevancy logic
    # Note: Ragas expects a dataset format
    try:
        # For DSPy's internal optimization, a quick boolean or scalar is better
        # Here we use a dspy.Predict based grader to simulate the metric
        grader = dspy.Predict("question, answer -> score: float")
        score = grader(question=example.question, answer=pred.answer).score
        return float(score) > 0.7
    except:
        return 0.0

# ─── Optimization Loop ───────────────────────────────────────

async def run_optimizer():
    print("\n" + "═"*80)
    print(" NexusBase — DSPy Prompt Optimizer")
    print("═"*80 + "\n")

    # 1. Setup
    setup_dspy()
    trainset = await fetch_training_data()
    
    if not trainset:
        print("Error: No training data found. Aborting.")
        return

    # 2. Initial Evaluation
    print(f"[1/3] Evaluating baseline performance...")
    rag = RAGModule()
    
    # We'll use a small subset for the baseline check to save time
    from dspy.evaluate import Evaluate
    evaluator = Evaluate(devset=trainset[:10], num_threads=1, display_progress=True, display_table=0)
    initial_score = evaluator(rag, metric=evaluate_relevancy)
    print(f"Baseline Score: {initial_score:.2f}")

    # 3. Optimization
    print(f"\n[2/3] Running BootstrapFewShotWithRandomSearch...")
    teleprompter = dspy.teleprompt.BootstrapFewShotWithRandomSearch(
        metric=evaluate_relevancy,
        max_bootstrapped_demos=4,
        max_labeled_demos=4,
        num_candidate_programs=8,
        num_threads=4
    )
    
    optimized_rag = teleprompter.compile(rag, trainset=trainset)

    # 4. Final Evaluation
    print(f"\n[3/3] Evaluating optimized performance...")
    final_score = evaluator(optimized_rag, metric=evaluate_relevancy)
    
    delta = final_score - initial_score
    print("\n" + "═"*80)
    print(f"Optimization Complete!")
    print(f"Initial Score: {initial_score:.2f}")
    print(f"Final Score:   {final_score:.2f}")
    print(f"Delta:         {delta:+.2f} ({ (delta/initial_score if initial_score > 0 else 0):.1%})")
    print("═"*80 + "\n")

    # Save the optimized program
    os.makedirs("src/core/compiled", exist_ok=True)
    optimized_rag.save("src/core/compiled/rag_optimized.json")
    print(f"Optimized program saved to src/core/compiled/rag_optimized.json")

if __name__ == "__main__":
    asyncio.run(run_optimizer())
