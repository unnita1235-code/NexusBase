# Rule: enterprise-rag-standard

> Governing standards for all RAG (Retrieval-Augmented Generation) pipelines in this project.
> Every agent, pipeline, and query engine **must** comply with the rules below.

---

## 1. Security — Access-Level Metadata

**Every document chunk stored in the vector store must include an `access_level` metadata field.**

| Field | Type | Allowed Values | Required |
|---|---|---|---|
| `access_level` | `string` | `"public"`, `"internal"`, `"confidential"`, `"restricted"` | ✅ Yes |

### Enforcement Rules
- Chunks **without** an `access_level` field must be **rejected** at ingestion time and logged as errors.
- The `QueryEngine` must **filter results** by the caller's access level before returning any context to the LLM.
- Access levels follow a strict hierarchy: `public` < `internal` < `confidential` < `restricted`.

### Example Chunk Metadata
```json
{
  "chunk_id": "doc_42_chunk_7",
  "source": "internal-policy-v3.pdf",
  "access_level": "confidential",
  "page": 4,
  "created_at": "2026-04-26T00:00:00Z"
}
```

---

## 2. Quality — Hybrid Search (Semantic + Keyword)

**All retrieval operations must use Hybrid Search combining pgvector semantic search with Postgres full-text keyword search.**

### Semantic Search (pgvector)
- Use `vector_cosine_ops` as the distance operator on the embedding column.
- Index type: `ivfflat` or `hnsw` (HNSW preferred for production).
- Embedding column: `embedding vector(1536)` (adjust dimensions to match your model).

```sql
-- Semantic similarity via pgvector cosine distance
SELECT
    chunk_id,
    source,
    content,
    access_level,
    1 - (embedding <=> query_embedding) AS semantic_score
FROM document_chunks
WHERE access_level = ANY(:allowed_levels)
ORDER BY embedding <=> query_embedding
LIMIT :top_k;
```

### Keyword Search (tsvector / tsquery)
- Store a pre-computed `tsvector` column (e.g., `content_tsv tsvector`) updated via a trigger or at ingestion.
- Use `plainto_tsquery` or `websearch_to_tsquery` for robust user-query parsing.

```sql
-- Full-text keyword search via Postgres tsvector
SELECT
    chunk_id,
    source,
    content,
    access_level,
    ts_rank(content_tsv, query) AS keyword_score
FROM document_chunks,
     websearch_to_tsquery('english', :user_query) query
WHERE content_tsv @@ query
  AND access_level = ANY(:allowed_levels)
ORDER BY keyword_score DESC
LIMIT :top_k;
```

### Hybrid Fusion
- Results from both searches must be merged using **Reciprocal Rank Fusion (RRF)**:

```
rrf_score(d) = Σ [ 1 / (k + rank_i(d)) ]   where k = 60 (default)
```

- Final ranking is by descending `rrf_score`. Re-ranking with a cross-encoder is optional but recommended for `top_k > 10`.

---

## 3. Modularity — Separate IngestionPipeline from QueryEngine

**The `IngestionPipeline` and `QueryEngine` must be implemented as independent, decoupled modules.**

```
rag_system/
├── ingestion/
│   ├── __init__.py
│   ├── pipeline.py        # IngestionPipeline class
│   ├── chunker.py         # Text splitting strategies
│   ├── embedder.py        # Embedding model wrapper
│   └── validator.py       # Metadata & access_level validation
│
├── retrieval/
│   ├── __init__.py
│   ├── query_engine.py    # QueryEngine class
│   ├── hybrid_search.py   # Semantic + Keyword search + RRF fusion
│   └── reranker.py        # Optional cross-encoder re-ranking
│
└── shared/
    ├── db.py              # Database connection pool
    ├── models.py          # Shared Pydantic models / dataclasses
    └── config.py          # Environment-based configuration
```

### IngestionPipeline Contract
- **Input**: Raw documents (file path, URL, or text blob) + caller-provided `access_level`.
- **Responsibilities**: Load → Chunk → Validate metadata → Embed → Upsert to DB.
- **Must NOT** contain any query or ranking logic.

### QueryEngine Contract
- **Input**: User query string + caller's `access_level` (or list of allowed levels).
- **Responsibilities**: Embed query → Hybrid search → RRF fusion → (optional re-rank) → Return ranked `RetrievedChunk` list.
- **Must NOT** contain any document loading or embedding-storage logic.

---

## 4. Observability — Log Distance Score & Source Snippet

**Every retrieval call must emit structured logs to the terminal (stdout) for each returned chunk.**

### Required Log Fields per Chunk

| Field | Description |
|---|---|
| `rank` | Position in the final ranked list (1-indexed) |
| `chunk_id` | Unique identifier of the chunk |
| `source` | Original document source (filename / URL) |
| `access_level` | The chunk's access level |
| `distance_score` | Raw cosine distance from pgvector (`embedding <=> query_embedding`) |
| `rrf_score` | Final Reciprocal Rank Fusion score |
| `source_snippet` | First 200 characters of the chunk's content |

### Reference Implementation (Python)

```python
import logging

logger = logging.getLogger("rag.retrieval")

def log_retrieved_chunks(chunks: list[RetrievedChunk]) -> None:
    """Emit observability logs for every retrieved chunk."""
    logger.info("=" * 60)
    logger.info(f"Retrieved {len(chunks)} chunk(s)")
    logger.info("=" * 60)
    for chunk in chunks:
        logger.info(
            f"[Rank #{chunk.rank}] "
            f"chunk_id={chunk.chunk_id} | "
            f"source={chunk.source} | "
            f"access_level={chunk.access_level} | "
            f"distance_score={chunk.distance_score:.4f} | "
            f"rrf_score={chunk.rrf_score:.4f}"
        )
        logger.info(f"  Snippet: \"{chunk.content[:200].strip()}...\"")
    logger.info("=" * 60)
```

### Expected Terminal Output (example)

```
============================================================
Retrieved 3 chunk(s)
============================================================
[Rank #1] chunk_id=doc_12_chunk_3 | source=policy-2026.pdf | access_level=internal | distance_score=0.1023 | rrf_score=0.0312
  Snippet: "All employees must complete annual security training by Q1. Failure to comply will result in..."
[Rank #2] chunk_id=doc_07_chunk_9 | source=handbook-v2.pdf | access_level=public | distance_score=0.1891 | rrf_score=0.0291
  Snippet: "The onboarding process consists of three phases: orientation, role training, and 30-day check-in..."
[Rank #3] chunk_id=doc_31_chunk_1 | source=faq-internal.md | access_level=internal | distance_score=0.2204 | rrf_score=0.0278
  Snippet: "Frequently asked questions about IT access provisioning and VPN setup for remote workers..."
============================================================
```

---

## 5. Knowledge Graph — Graph-Based Context Priority (GraphRAG)

**For multi-hop queries, graph-based context takes priority over flat vector search.**

### Extraction Pipeline
- Every ingested chunk **must** be processed through the entity/relationship extractor (Step 6 of IngestionPipeline).
- Entities **inherit** `access_level` from their source chunk (rule §1).
- Relationships **must** include provenance (`source_chunk_id`) for audit trails.
- Entity names are canonicalized (title-cased, trimmed) for aggressive deduplication.

### Entity & Relationship Schema
```
Entity:
  name            — Canonical name (e.g., "Project Alpha")
  type            — Person, Project, Department, Budget, Policy, etc.
  description     — One-line description extracted from context
  source_chunk_id — Provenance back to document_chunks
  access_level    — Inherited from parent chunk

Relationship:
  source_entity   — Entity name (from)
  target_entity   — Entity name (to)
  relation_type   — e.g., "AFFECTS", "MANAGES", "FUNDED_BY"
  description     — Natural language description
  source_chunk_id — Provenance
  access_level    — Inherited from parent chunk
```

### Retrieval Priority (Graph-First for Multi-Hop)
1. **Query classification** — an LLM classifier determines if the query is `simple` or `multi_hop`.
2. **Graph traversal first** — for multi-hop queries, traverse the knowledge graph (1–3 hops) to discover connected entities and their source chunks.
3. **Targeted chunk retrieval** — fetch the specific chunks linked to graph traversal results from pgvector.
4. **Hybrid search fallback** — if graph traversal yields no results, fall back to standard hybrid search (rule §2).

```
Multi-hop query flow:
  classify → seed entities → Neo4j traversal (1..N hops)
    → collect chunk_ids → fetch from pgvector → grade → generate

Simple query flow (unchanged):
  embed → hybrid search (semantic + keyword + RRF) → grade → generate
```

### Observability (rule §4 extension)
Every graph traversal **must** log to the terminal:
- Seed entities used for traversal
- Traversal path (entities and relationship types visited)
- Hop count (max depth reached)
- Connected chunk_ids discovered

### Reference Terminal Output (graph traversal)
```
============================================================
GraphRAG Traversal (query_type=multi_hop)
============================================================
  Seed entities: ['Project Alpha', 'Q3 Budget']
  Traversal path: Project Alpha --[AFFECTS]--> Q3 Budget --[FUNDED_BY]--> Marketing Department
  Hop count: 2
  Connected chunks: 4 chunk(s)
    → doc_12_chunk_3
    → doc_07_chunk_9
    → doc_31_chunk_1
    → doc_45_chunk_2
============================================================
```

---

## Compliance Checklist

Before merging any RAG-related code, verify:

### §1 — Security
- [ ] Every ingested chunk has a validated `access_level` field
- [ ] `QueryEngine` filters chunks by caller's access level **before** returning results

### §2 — Quality
- [ ] Retrieval uses **both** pgvector (`vector_cosine_ops`) **and** tsvector for hybrid search
- [ ] Results are merged via Reciprocal Rank Fusion (RRF)

### §3 — Modularity
- [ ] `IngestionPipeline` and `QueryEngine` live in **separate modules** with no circular imports

### §4 — Observability
- [ ] Every retrieval call logs `distance_score` and `source_snippet` for each returned chunk

### §5 — Knowledge Graph (GraphRAG)
- [ ] Entity extraction runs on every ingested chunk (Step 6)
- [ ] Entities inherit `access_level` from their source chunk
- [ ] Multi-hop queries traverse the knowledge graph **before** vector search
- [ ] Graph traversal respects `access_level` at every node in the path
- [ ] Traversal path (seed entities, hops, chunk_ids) is logged to terminal
- [ ] Simple queries bypass graph traversal (no latency penalty)
