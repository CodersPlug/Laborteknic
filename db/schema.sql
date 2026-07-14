-- Laborteknic presentation — agent knowledge base
-- Embeddings in *_vecs tables (no FK — DuckDB re-embed pattern)

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

-- Full presentation content synced from index.html
CREATE TABLE IF NOT EXISTS slides (
    idx           INTEGER PRIMARY KEY,  -- 0-based, matches ?slide=N
    slide_n       INTEGER NOT NULL,     -- 1-based display number
    theme         VARCHAR,
    eyebrow       VARCHAR,
    title         VARCHAR,
    model         VARCHAR,              -- BTS, A15, etc.
    tag           VARCHAR,              -- Semiautomático / Automático
    cartel        VARCHAR,              -- e.g. 150 test/hora
    lead_text     VARCHAR,
    bullets       VARCHAR[],
    specs         VARCHAR[],
    panels        VARCHAR[],
    pills         VARCHAR[],
    assays        VARCHAR[],
    cards         VARCHAR[],            -- "Title — blurb"
    areas         VARCHAR[],            -- "Administración — epígrafe"
    stats         VARCHAR[],            -- "100+ países"
    images        VARCHAR[],
    body_text     VARCHAR NOT NULL,     -- flattened text for search/embedding
    synced_at     TIMESTAMP DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS slide_vecs (
    slide_idx  INTEGER PRIMARY KEY,
    embedding  FLOAT[384]
);
