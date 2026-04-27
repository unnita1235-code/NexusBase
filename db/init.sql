-- =============================================================
-- NexusBase — Database Initialization
-- =============================================================
-- This script runs automatically on first container startup
-- via /docker-entrypoint-initdb.d/

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================
-- document_chunks table
-- =============================================================
CREATE TABLE IF NOT EXISTS document_chunks (
    id              uuid            PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id        text            UNIQUE NOT NULL,
    source          text            NOT NULL,
    content         text            NOT NULL,
    access_level    text            NOT NULL
                                    CHECK (access_level IN ('public', 'internal', 'confidential', 'restricted')),
    embedding       vector(1536)    NOT NULL,
    content_tsv     tsvector        GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    page            integer,
    document_hash   text,
    created_at      timestamptz     NOT NULL DEFAULT now()
);

-- =============================================================
-- chunk_entities join table (GraphRAG §5)
-- =============================================================
-- Links document chunks to their extracted entities for SQL-side
-- lookups without requiring a Neo4j query.
CREATE TABLE IF NOT EXISTS chunk_entities (
    chunk_id        text            NOT NULL,
    entity_name     text            NOT NULL,
    entity_type     text            NOT NULL,
    created_at      timestamptz     NOT NULL DEFAULT now(),
    PRIMARY KEY (chunk_id, entity_name)
);

-- =============================================================
-- Indexes
-- =============================================================

-- HNSW index for fast cosine-distance vector search (rule §2)
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
    ON document_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- GIN index for full-text keyword search (rule §2)
CREATE INDEX IF NOT EXISTS idx_chunks_content_tsv
    ON document_chunks
    USING gin (content_tsv);

-- B-tree index for access_level filtering (rule §1)
CREATE INDEX IF NOT EXISTS idx_chunks_access_level
    ON document_chunks (access_level);

-- B-tree index for source lookups
CREATE INDEX IF NOT EXISTS idx_chunks_source
    ON document_chunks (source);

-- B-tree index for delta sync (source + hash)
CREATE INDEX IF NOT EXISTS idx_chunks_source_hash
    ON document_chunks (source, document_hash);

-- B-tree index for entity lookups by name (rule §5)
CREATE INDEX IF NOT EXISTS idx_chunk_entities_name
    ON chunk_entities (entity_name);

-- B-tree index for entity lookups by type
CREATE INDEX IF NOT EXISTS idx_chunk_entities_type
    ON chunk_entities (entity_type);

-- =============================================================
-- system_settings table
-- =============================================================
-- Stores dynamic configuration, prompts, and encrypted API keys.
CREATE TABLE IF NOT EXISTS system_settings (
    key             text            PRIMARY KEY,
    value           text            NOT NULL,
    is_encrypted    boolean         DEFAULT false,
    updated_at      timestamptz     NOT NULL DEFAULT now()
);

-- Seed initial settings from environment defaults
INSERT INTO system_settings (key, value, is_encrypted) VALUES
('chunk_size', '512', false),
('chunk_overlap', '64', false),
('system_prompt', 'You are a helpful assistant that answers questions based on the provided context. If the context doesn''t contain enough information, say so clearly. Always cite your sources by mentioning the document name.', false),
('grader_prompt', 'You are a strict relevance grader for a RAG system. Is this document chunk actually relevant to answering the user''s question? Consider semantic relevance, not just keyword overlap. Respond with ONLY ''yes'' or ''no''.', false)
ON CONFLICT (key) DO NOTHING;
