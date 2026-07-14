"""
Laborteknic agent DB — query tool.

Usage:
  python query.py                              # summary
  python query.py --slides                    # list all presentation slides
  python query.py --slide 9                   # one slide (1-based)
  python query.py --kind pitfall
  python query.py --search "deploy github pages"
  python query.py --search "A15" --in slides
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

    n_slides = con.execute("SELECT count(*) FROM slides").fetchone()[0]
    print(f"\n── PRESENTATION: {n_slides} slides ──")
    for sn, title, model in con.execute(
        "SELECT slide_n, title, model FROM slides ORDER BY idx"
    ).fetchall():
        extra = f" · {model}" if model else ""
        print(f"  {sn:2d}. {title}{extra}")

    print("\n── ENTRIES BY KIND ──")
    for kind, n in con.execute(
        "SELECT kind, count(*) FROM entries GROUP BY kind ORDER BY kind"
    ).fetchall():
        print(f"  {kind}: {n}")


def list_slides(con):
    print("\n── SLIDES ──\n")
    for r in con.execute(
        """
        SELECT slide_n, eyebrow, title, model, tag, cartel, lead_text,
               bullets, specs, panels, assays, cards, areas
        FROM slides ORDER BY idx
        """
    ).fetchall():
        sn, eyebrow, title, model, tag, cartel, lead, bullets, specs, panels, assays, cards, areas = r
        head = title + (f" · {model}" if model else "")
        print(f"{sn:2d}. [{eyebrow}] {head}")
        if tag or cartel:
            print(f"    {tag} {cartel}".strip())
        if lead:
            print(f"    {lead[:220]}{'...' if len(lead) > 220 else ''}")
        for b in bullets or []:
            print(f"    • {b}")
        for s in specs or []:
            print(f"    ▸ {s}")
        if panels:
            print(f"    Paneles: {', '.join(panels)}")
        if assays:
            print(f"    Ensayos: {', '.join(assays)}")
        for a in areas or []:
            print(f"    ▸ {a}")
        for c in cards or []:
            print(f"    ▸ {c}")
        print()


def show_slide(con, n: int):
    r = con.execute(
        """
        SELECT slide_n, eyebrow, title, model, tag, cartel, lead_text,
               bullets, specs, panels, pills, assays, cards, areas, stats, images, body_text
        FROM slides WHERE slide_n = ?
        """,
        [n],
    ).fetchone()
    if not r:
        print(f"No slide {n}")
        return
    (
        sn, eyebrow, title, model, tag, cartel, lead, bullets, specs,
        panels, pills, assays, cards, areas, stats, images, body,
    ) = r
    print(f"\n── Diapo {sn} ──")
    print(f"  {eyebrow}")
    print(f"  {title}" + (f" · {model}" if model else ""))
    if tag:
        print(f"  Tag: {tag}")
    if cartel:
        print(f"  Cartel: {cartel}")
    if lead:
        print(f"\n  {lead}")
    if bullets:
        print("\n  Bullets:")
        for b in bullets:
            print(f"    • {b}")
    if specs:
        print("\n  Specs:")
        for s in specs:
            print(f"    ▸ {s}")
    if panels:
        print(f"\n  Paneles: {', '.join(panels)}")
    if pills:
        print(f"\n  Pills: {', '.join(pills)}")
    if assays:
        print("\n  Ensayos:")
        for a in assays:
            print(f"    • {a}")
    if areas:
        print("\n  Áreas:")
        for a in areas:
            print(f"    • {a}")
    if cards:
        print("\n  Cards:")
        for c in cards:
            print(f"    • {c}")
    if stats:
        print(f"\n  Stats: {'; '.join(stats)}")
    if images:
        print("\n  Images:")
        for i in images:
            print(f"    {i}")


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


def semantic_search(con, query: str, kind: str | None = None, top: int = 5, target: str = "both"):
    from fastembed import TextEmbedding

    model = TextEmbedding(MODEL)
    vec = list(map(float, next(model.embed([query]))))

    label = [f'"{query}"', f"top {top}", f"in={target}"]
    if kind:
        label.append(f"kind={kind}")
    print(f"\n── ACORN-1 search: {' | '.join(label)} ──\n")

    results = []

    if target in ("both", "entries"):
        clauses = ["1=1"]
        params: list = [vec]
        if kind:
            clauses.append("e.kind = ?")
            params.append(kind)
        rows = con.execute(
            f"""
            SELECT 'entry' AS src, e.kind, e.title, e.body,
                   array_distance(v.embedding, ?::FLOAT[{DIM}]) AS dist
            FROM entry_vecs v
            JOIN entries e ON e.id = v.entry_id
            WHERE {' AND '.join(clauses)}
            ORDER BY dist
            LIMIT {top}
            """,
            params,
        ).fetchall()
        results.extend(rows)

    if target in ("both", "slides") and not kind:
        rows = con.execute(
            f"""
            SELECT 'slide' AS src,
                   'diapo ' || cast(s.slide_n AS VARCHAR),
                   coalesce(nullif(s.model, ''), s.title),
                   s.body_text,
                   array_distance(v.embedding, ?::FLOAT[{DIM}]) AS dist
            FROM slide_vecs v
            JOIN slides s ON s.idx = v.slide_idx
            ORDER BY dist
            LIMIT {top}
            """,
            [vec],
        ).fetchall()
        results.extend(rows)

    results.sort(key=lambda r: r[4])
    results = results[:top]

    if not results:
        print("No results.")
        return
    for src, k, title, body, dist in results:
        print(f"  [{src} | {k}] {title}  (dist={dist:.3f})")
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
    parser.add_argument("--in", dest="search_in", choices=["both", "slides", "entries"], default="both")
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--slides", action="store_true", help="List all presentation slides")
    parser.add_argument("--slide", type=int, help="Show one slide (1-based)")
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

    if args.slide is not None:
        show_slide(con, args.slide)
    elif args.slides:
        list_slides(con)
    elif args.search:
        semantic_search(con, args.search, kind=args.kind, top=args.top, target=args.search_in)
    elif args.kind:
        list_kind(con, args.kind)
    else:
        summary(con)

    con.close()


if __name__ == "__main__":
    main()
