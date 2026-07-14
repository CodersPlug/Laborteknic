"""
Build HNSW indexes (hnsw_acorn / ACORN-1) over entries AND slides.

Usage:
    python embed.py
    python embed.py --reindex
    python embed.py --rabitq
    python embed.py --slides-only
"""

import argparse
from fastembed import TextEmbedding

from db import connect, configure_hnsw, MODEL


def embed_texts(model: TextEmbedding, texts: list[str]) -> list[list[float]]:
    return [list(map(float, v)) for v in model.embed(texts)]


def generate_entry_embeddings(con, model: TextEmbedding) -> int:
    rows = con.execute("SELECT id, kind, title, body, tags FROM entries ORDER BY id").fetchall()
    if not rows:
        return 0
    texts = [
        f"{r[1]} {r[2]}. {r[3]}. tags: {', '.join(r[4] or [])}"
        for r in rows
    ]
    vecs = embed_texts(model, texts)
    con.execute("DELETE FROM entry_vecs")
    con.executemany(
        "INSERT INTO entry_vecs VALUES (?, ?)",
        [(r[0], v) for r, v in zip(rows, vecs)],
    )
    return len(rows)


def generate_slide_embeddings(con, model: TextEmbedding) -> int:
    rows = con.execute(
        "SELECT idx, slide_n, eyebrow, title, model, body_text FROM slides ORDER BY idx"
    ).fetchall()
    if not rows:
        return 0
    texts = [
        f"Diapo {r[1]}. {r[2]} {r[3]} {r[4]}. {r[5]}"
        for r in rows
    ]
    vecs = embed_texts(model, texts)
    con.execute("DELETE FROM slide_vecs")
    con.executemany(
        "INSERT INTO slide_vecs VALUES (?, ?)",
        [(r[0], v) for r, v in zip(rows, vecs)],
    )
    return len(rows)


def create_indexes(con, rabitq: bool = False) -> None:
    configure_hnsw(con)
    q = ", quantization = 'rabitq'" if rabitq else ""
    con.execute("DROP INDEX IF EXISTS hnsw_entries")
    con.execute(
        f"CREATE INDEX hnsw_entries ON entry_vecs USING HNSW (embedding) "
        f"WITH (metric = 'cosine', ef_construction = 128, M = 16{q})"
    )
    print(f"  Index hnsw_entries → entry_vecs{' [RaBitQ]' if rabitq else ''}")

    n_slides = con.execute("SELECT count(*) FROM slide_vecs").fetchone()[0]
    if n_slides:
        con.execute("DROP INDEX IF EXISTS hnsw_slides")
        con.execute(
            f"CREATE INDEX hnsw_slides ON slide_vecs USING HNSW (embedding) "
            f"WITH (metric = 'cosine', ef_construction = 128, M = 16{q})"
        )
        print(f"  Index hnsw_slides → slide_vecs{' [RaBitQ]' if rabitq else ''}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reindex", action="store_true")
    parser.add_argument("--rabitq", action="store_true")
    parser.add_argument("--slides-only", action="store_true")
    args = parser.parse_args()

    con = connect()
    if not args.reindex:
        print(f"Loading {MODEL}...")
        model = TextEmbedding(MODEL)
        if not args.slides_only:
            n = generate_entry_embeddings(con, model)
            print(f"  {n} entry embeddings")
        n_s = generate_slide_embeddings(con, model)
        print(f"  {n_s} slide embeddings")
    print("Creating HNSW indexes (ACORN-1)...")
    create_indexes(con, rabitq=args.rabitq)
    con.close()
    print("Done.")


if __name__ == "__main__":
    main()
