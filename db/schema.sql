-- Laborteknic presentation — agent knowledge base
-- Embeddings in entry_vecs (no FK — DuckDB re-embed pattern)

CREATE TABLE IF NOT EXISTS project (
    id            VARCHAR PRIMARY KEY,
    display_name  VARCHAR NOT NULL,
    repo_path     VARCHAR NOT NULL,
    repo_github   VARCHAR NOT NULL,
    live_url      VARCHAR NOT NULL,
    deploy_branch VARCHAR NOT NULL,
    stack         VARCHAR NOT NULL,
    updated_at    TIMESTAMP DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS constants (
    name     VARCHAR PRIMARY KEY,
    value    VARCHAR NOT NULL,
    meaning  VARCHAR
);

CREATE TABLE IF NOT EXISTS entries (
    id       VARCHAR PRIMARY KEY,
    kind     VARCHAR NOT NULL, -- fact, decision, runbook, pitfall, slide, brand, product
    title    VARCHAR NOT NULL,
    body     VARCHAR NOT NULL,
    tags     VARCHAR[] DEFAULT []
);

CREATE TABLE IF NOT EXISTS entry_vecs (
    entry_id  VARCHAR PRIMARY KEY,
    embedding FLOAT[384]
);
