import os
import sys
import asyncio
import json
import pandas as pd
from tabulate import tabulate
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision
from langchain_openai import ChatOpenAI

# Add the backend directory to sys.path so we can import 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from app.shared.db import init_pool, close_pool
from app.knowledge_graph.neo4j_client import init_neo4j, close_neo4j
from app.graph.builder import rag_graph

async def run_evaluation(limit: int = 50):
    print("\n" + "="*80)
    print("NexusBase RAG Evaluation Script (Ragas Framework)")
    print("="*80)

    # 1. Initialize DB and Graph
    print("\n[1/5] Initializing system connections...")
    await init_pool(settings.db_dsn)
    await init_neo4j(
        settings.neo4j_uri,
        (settings.neo4j_user, settings.neo4j_password),
    )

    # 2. Load Golden Dataset
    print(f"\n[2/5] Loading golden dataset from evaluation/golden_queries.json...")
    with open("evaluation/golden_queries.json", "r") as f:
        golden_data = json.load(f)
    
    if limit:
        golden_data = golden_data[:limit]
    
    print(f"Loaded {len(golden_data)} queries.")

    # 3. Run RAG Pipeline
    print(f"\n[3/5] Running RAG pipeline for {len(golden_data)} queries...")
    results = []
    
    for i, entry in enumerate(golden_data):
        question = entry["question"]
        ground_truth = entry["ground_truth"]
        
        print(f"  ({i+1}/{len(golden_data)}) Query: \"{question[:50]}...\"")
        
        initial_state = {
            "question": question,
            "active_query": question,
            "access_level": "public",
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
        }
        
        try:
            # Run the LangGraph
            state_result = await rag_graph.ainvoke(initial_state)
            
            answer = state_result.get("generation", "")
            # Collect context strings from retrieved chunks
            contexts = [doc.content for doc in state_result.get("documents", [])]
            
            results.append({
                "question": question,
                "answer": answer,
                "contexts": contexts,
                "ground_truth": ground_truth
            })
        except Exception as e:
            print(f"    Error processing query: {e}")
            continue

    # 4. Run Ragas Evaluation
    print(f"\n[4/5] Running Ragas metrics (Faithfulness, Relevancy, Precision)...")
    
    # Prepare dataset for Ragas
    dataset = Dataset.from_list(results)
    
    # Run evaluation
    # Note: Ragas uses OpenAI by default if no LLM is provided. 
    # We ensure our OpenAI key from settings is used.
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key
    
    # We use gpt-4o-mini for evaluation to be cost-effective yet accurate
    eval_llm = ChatOpenAI(model="gpt-4o-mini")
    
    score_result = evaluate(
        dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
            context_precision
        ],
        llm=eval_llm
    )
    
    # 5. Format and Output Scorecard
    print(f"\n[5/5] Final Scorecard:")
    print("="*80)
    
    df = score_result.to_pandas()
    
    # Calculate averages
    averages = df.select_dtypes(include=['number']).mean()
    
    # Prepare table data
    table_data = []
    for _, row in df.iterrows():
        table_data.append([
            row["question"][:40] + "...",
            f"{row['faithfulness']:.2f}",
            f"{row['answer_relevancy']:.2f}",
            f"{row['context_precision']:.2f}"
        ])
    
    # Add average row
    table_data.append(["-"*40, "-"*10, "-"*10, "-"*10])
    table_data.append([
        "AVERAGE SCORE",
        f"{averages['faithfulness']:.3f}",
        f"{averages['answer_relevancy']:.3f}",
        f"{averages['context_precision']:.3f}"
    ])

    print(tabulate(
        table_data, 
        headers=["Question", "Faithfulness", "Relevancy", "Precision"], 
        tablefmt="pretty"
    ))
    print("="*80 + "\n")

    # Cleanup
    await close_neo4j()
    await close_pool()

if __name__ == "__main__":
    # Check for limit argument
    limit_arg = 50
    if len(sys.argv) > 1:
        try:
            limit_arg = int(sys.argv[1])
        except ValueError:
            pass
            
    asyncio.run(run_evaluation(limit=limit_arg))
