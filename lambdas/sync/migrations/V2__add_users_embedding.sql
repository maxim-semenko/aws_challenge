-- V2: pgvector extension, users.embedding and its HNSW index (spec 10 §Inputs, ADR-019; column list: spec 06 §Outputs).
-- PostgreSQL 14 syntax only (R-14); RDS 14.18 ships pgvector 0.8.0. The extension is called "vector"; creating it
-- needs rds_superuser (the proxy DB user has it). All three statements run in the runner's single transaction.
CREATE EXTENSION IF NOT EXISTS vector;
ALTER TABLE users ADD COLUMN embedding vector(1024);
CREATE INDEX users_embedding_hnsw_idx ON users USING hnsw (embedding vector_l2_ops);
