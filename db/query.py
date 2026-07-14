"""
Laborteknic agent DB — query tool.

Usage:
  python query.py                              # summary
  python query.py --kind pitfall
  python query.py --search "deploy github pages"
  python query.py --search "A15 velocidad" --kind product
  python query.py add --kind decision --title "..." --body "..."
"""

import argparse
import subprocess
import sys
from pathlib import Path

from db import connect, DIM, MODEL

ROOT = Path(__file__).resolve().parent
EMBED = ROOT / "embed.py"


def summary(con):
    row = con.execute("SELECT display_name, live_url, deploy_branch, stack FROM project").fetchone()
    if row:
        print(f"\n── {row[0]} ──")
        print(f"  Live   : {row[1]}")
        print(f"  Branch : {row[2]}")
        print(f"  Stack  : {row[3]}")

    print("\n── CONSTANTS ──")
    for name, val, meaning in con.execute(
        "SELECT name, value, meaning FROM constants ORDER BY name"
    ).fetchall():
        print(f"  {name} = {val}")
        if meaning:
            print(f"    {meaning}")

    print("\n── ENTRIES BY KIND ──")
    for kind, n in con.execute(
        "SELECT kind, count(*) FROM entries GROUP BY kind ORDER BY kind"
    ).fetchall():
        print(f"  {kind}: {n}")


def list_kind(con, kind: str):
    print(f"\n── kind={kind} ──\n")
    rows = con.execute(
        "SELECT title, body, tags FROM entries WHERE kind = ? ORDER BY title",
        [kind],
    ).fetchall()
    if not rows:
        print("No entries.")
        return
    for title, body, tags in rows:
        print(f"  [{kind}] {title}")
        print(f"    {body[:280]}{'...' if len(body) > 280 else ''}")
        if tags:
            print(f"    tags: {', '.join(tags)}")
        print()


def semantic_search(con, query: str, kind: str | None = None, top: int = 5):
    from fastembed import TextEmbedding

    model = TextEmbedding(MODEL)
    vec = list(map(float, next(model.embed([query]))))

    clauses = ["1=1"]
    params: list = [vec]
    if kind:
        clauses.append("e.kind = ?")
        params.append(kind)

    label = [f'"{query}"', f"top {top}"]
    if kind:
        label.append(f"kind={kind}")
    print(f"\n── ACORN-1 search: {' | '.join(label)} ──\n")

    rows = con.execute(
        f"""
        SELECT e.kind, e.title, e.body,
               array_distance(v.embedding, ?::FLOAT[{DIM}]) AS dist
        FROM entry_vecs v
        JOIN entries e ON e.id = v.entry_id
        WHERE {' AND '.join(clauses)}
        ORDER BY dist
        LIMIT {top}
        """,
        params,
    ).fetchall()

    if not rows:
        print("No results.")
        return
    for k, title, body, dist in rows:
        print(f"  [{k}] {title}  (dist={dist:.3f})")
        print(f"    {body[:240]}{'...' if len(body) > 240 else ''}\n")


def add_entry(con, kind: str, title: str, body: str, tags: list[str] | None = None):
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:48]
    eid = f"{kind}-{slug}"
    con.execute(
        "INSERT OR REPLACE INTO entries VALUES (?, ?, ?, ?, ?)",
        [eid, kind, title, body, tags or []],
    )
    print(f"Upserted {eid}")
    con.close()
    subprocess.check_call([sys.executable, str(EMBED)], cwd=str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Laborteknic agent DuckDB")
    parser.add_argument("--kind", help="List or filter by kind")
    parser.add_argument("--search", help="Semantic search query")
    parser.add_argument("--top", type=int, default=5)
    sub = parser.add_subparsers(dest="cmd")
    add_p = sub.add_parser("add")
    add_p.add_argument("--kind", required=True)
    add_p.add_argument("--title", required=True)
    add_p.add_argument("--body", required=True)
    add_p.add_argument("--tag", action="append", default=[])

    args = parser.parse_args()
    con = connect()

    if args.cmd == "add":
        add_entry(con, args.kind, args.title, args.body, args.tag)
        return

    if args.search:
        semantic_search(con, args.search, kind=args.kind, top=args.top)
    elif args.kind:
        list_kind(con, args.kind)
    else:
        summary(con)

    con.close()


if __name__ == "__main__":
    main()
