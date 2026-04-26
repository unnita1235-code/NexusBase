"""
NexusBase — Environment-based configuration.

All tunables are loaded from environment variables (or a .env file)
using pydantic-settings. This module is the single source of truth
for configuration across both the IngestionPipeline and QueryEngine.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── LLM / Embedding ──────────────────────────────────────
    openai_api_key: str
    embedding_model: str = "text-embedding-3-small"
    llm_model: str = "gpt-4o-mini"

    # ── HyDE LLM (Claude 3.5 Haiku) ──────────────────────────
    anthropic_api_key: str = ""
    hyde_model: str = "claude-3-5-haiku-20241022"

    # ── Grader LLM (Gemini 3 Flash) ────────────────────────────
    gemini_api_key: str = ""
    grader_model: str = "gemini-3.0-flash"
    router_model: str = "gemini-3.1-flash"  # Gemini 3.1 Flash for routing

    # ── Web Search Fallback ───────────────────────────────────
    tavily_api_key: str = ""

    # ── Database ──────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://nexus:nexus@localhost:5432/nexusbase"

    # ── RAG Tuning ────────────────────────────────────────────
    chunk_size: int = 512
    chunk_overlap: int = 64
    top_k: int = 5
    rrf_k: int = 60
    semantic_chunk_threshold: float = 0.8
    semantic_chunk_max_tokens: int = 1000

    # ── Vision Ingestion ──────────────────────────────────────
    use_vision_ingestion: bool = True
    vision_model: str = "gemini-3.1-pro"

    # ── Redis (Semantic Cache & Tasks) ────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    cache_similarity_threshold: float = 0.98


    # ── CRAG Scoring Weights ──────────────────────────────────
    # Score(doc) = w1 * CosineSim(q, doc) + w2 * KeywordMatch(q, doc)
    score_w1: float = 0.7   # weight for semantic (cosine similarity)
    score_w2: float = 0.3   # weight for keyword match
    max_rewrite_retries: int = 1  # max query rewrites before secondary fallback

    # ── Knowledge Graph (Neo4j) ───────────────────────────────
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "nexusbase"
    extractor_model: str = "gemini-3.1-pro"  # Gemini 3.1 Pro for entity extraction
    graph_traversal_max_hops: int = 3

    # ── Server ────────────────────────────────────────────────
    backend_port: int = 8000
    cors_origins: str = "http://localhost:3000,http://localhost:3005"

    @property
    def db_dsn(self) -> str:
        """Return a plain asyncpg DSN (without the +asyncpg dialect)."""
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://")

    @property
    def cors_origin_list(self) -> list[str]:
        """Split comma-separated CORS origins into a list."""
        return [o.strip() for o in self.cors_origins.split(",")]


# Singleton — import this everywhere
settings = Settings()  # type: ignore[call-arg]
