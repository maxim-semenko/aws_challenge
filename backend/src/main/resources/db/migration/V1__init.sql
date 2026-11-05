-- pgvector: available on Amazon RDS for PostgreSQL 15.2+ and in the pgvector/pgvector Docker image
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE app_user (
    id           BIGSERIAL PRIMARY KEY,
    cognito_sub  VARCHAR(64)  NOT NULL UNIQUE,
    email        VARCHAR(320) NOT NULL,
    username     VARCHAR(128),
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_app_user_created_at ON app_user (created_at DESC);

-- 1024 = Titan Text Embeddings v2 default dimension (keep in sync with app.bedrock.embedding-dimensions)
CREATE TABLE document (
    id          BIGSERIAL PRIMARY KEY,
    title       VARCHAR(512) NOT NULL,
    content     TEXT         NOT NULL,
    embedding   vector(1024),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- HNSW: best recall/latency, no training step, can be built on an empty table
CREATE INDEX idx_document_embedding_hnsw
    ON document USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- IVFFlat alternative (build it AFTER loading data; lists ~ rows/1000, query with SET ivfflat.probes = 10):
-- CREATE INDEX idx_document_embedding_ivfflat
--     ON document USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
