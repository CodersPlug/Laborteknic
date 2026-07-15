"""
Parse Laborteknic/index.html and upsert every slide into the DuckDB.

Usage:
    python sync_presentation.py
    python sync_presentation.py --embed   # also refresh slide_vecs + HNSW
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import duckdb

from db import connect as db_connect

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
HTML = REPO / "index.html"
DB = ROOT / "laborteknic.duckdb"
SCHEMA = ROOT / "schema.sql"


def clean(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_slides(html: str) -> list[dict]:
    parts = re.split(r"(?=<section class=\"slide)", html)
    slides: list[dict] = []

    for p in parts:
        if not p.startswith('<section class="slide'):
            continue

        theme_m = re.search(r'data-theme="([^"]+)"', p)
        brows = [clean(b) for b in re.findall(r'<span class="eyebrow"[^>]*>(.*?)</span>', p, re.S)]
        titles = [clean(t) for t in re.findall(r'<h1 class="title"[^>]*>(.*?)</h1>', p, re.S)]
        titles += [clean(t) for t in re.findall(r'<h2 class="sd-title"[^>]*>(.*?)</h2>', p, re.S)]
        models = [clean(t) for t in re.findall(r'<h2 class="equip-model"[^>]*>(.*?)</h2>', p, re.S)]
        models += [clean(t) for t in re.findall(r'<h2 class="sub-brand"[^>]*>(.*?)</h2>', p, re.S)]
        leads = [clean(t) for t in re.findall(r'<p class="lead"[^>]*>(.*?)</p>', p, re.S)]
        bullets = [clean(t) for t in re.findall(r"<li[^>]*>(.*?)</li>", p, re.S) if clean(t)]
        assays = [clean(t) for t in re.findall(r'<div class="assay">(.*?)</div>', p, re.S)]
        panels = [
            clean(t)
            for t in re.findall(r'<div class="panel-item">.*?<img[^>]*>\s*([^<]+)</div>', p, re.S)
        ]
        pills = [clean(t) for t in re.findall(r'<span class="pill">(.*?)</span>', p, re.S)]
        tags = [clean(t) for t in re.findall(r'<span class="tag-pill">(.*?)</span>', p, re.S)]
        cartels = [clean(t) for t in re.findall(r'<div class="equip-cartel">(.*?)</div>', p, re.S)]
        specs = [clean(t) for t in re.findall(r'<div class="spec">(.*?)</div>', p, re.S)]

        cards = []
        for img, h, blurb in re.findall(
            r'<div class="card">\s*<img[^>]+src="([^"]+)"[^>]*>\s*'
            r'<div class="card-body">\s*<h3>(.*?)</h3>\s*<p>(.*?)</p>',
            p,
            re.S,
        ):
            cards.append(f"{clean(h)} — {clean(blurb)}")

        areas = []
        for img, cap, blurb in re.findall(
            r'<div class="area-card">\s*<img[^>]+src="([^"]+)".*?'
            r'<div class="area-cap">\s*<h3>(.*?)</h3>\s*<p>(.*?)</p>\s*</div>',
            p,
            re.S,
        ):
            areas.append(f"{clean(cap)} — {clean(blurb)}")

        stats = [
            f"{clean(n)} {clean(lab)}"
            for n, lab in re.findall(
                r'<div class="stat">\s*<div class="num">(.*?)</div>\s*<div class="label">(.*?)</div>',
                p,
                re.S,
            )
        ]

        imgs = re.findall(r'<img[^>]+src="([^"]+)"', p)
        cover_site = re.findall(r'cover-website">(.*?)<', p)

        idx = len(slides)
        title = titles[0] if titles else ""
        model = models[0] if models else ""
        eyebrow = brows[0] if brows else ""
        lead_text = " ".join(leads)
        if cover_site:
            lead_text = (lead_text + " " + cover_site[0]).strip()

        # Distribuidor lines from quiénes somos
        dist_bits = []
        for lab in re.findall(r'<span class="distributor-label">(.*?)</span>', p, re.S):
            dist_bits.append(clean(lab))
        if dist_bits:
            lead_text = (lead_text + " | " + " · ".join(dist_bits)).strip()

        body_parts = [
            f"Diapositiva {idx + 1}.",
            eyebrow,
            title,
            model,
            tags[0] if tags else "",
            cartels[0] if cartels else "",
            lead_text,
            " ".join(bullets),
            " ".join(specs),
            "Paneles: " + ", ".join(panels) if panels else "",
            "Ensayos: " + ", ".join(assays) if assays else "",
            "Áreas: " + "; ".join(areas) if areas else "",
            "Productos: " + "; ".join(cards) if cards else "",
            "Pills: " + ", ".join(pills) if pills else "",
            "Stats: " + "; ".join(stats) if stats else "",
        ]
        body_text = re.sub(r"\s+", " ", " ".join(x for x in body_parts if x)).strip()

        slides.append(
            dict(
                idx=idx,
                slide_n=idx + 1,
                theme=theme_m.group(1) if theme_m else "",
                eyebrow=eyebrow,
                title=title,
                model=model,
                tag=tags[0] if tags else "",
                cartel=cartels[0] if cartels else "",
                lead_text=lead_text,
                bullets=bullets,
                specs=specs,
                panels=panels,
                pills=pills,
                assays=assays,
                cards=cards,
                areas=areas,
                stats=stats,
                images=imgs,
                body_text=body_text,
            )
        )
    return slides


def ensure_schema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(SCHEMA.read_text())


def upsert_slides(con: duckdb.DuckDBPyConnection, slides: list[dict]) -> int:
    con.execute("DELETE FROM slides")
    con.execute("DELETE FROM slide_vecs")
    con.executemany(
        """
        INSERT INTO slides VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, current_timestamp
        )
        """,
        [
            (
                s["idx"],
                s["slide_n"],
                s["theme"],
                s["eyebrow"],
                s["title"],
                s["model"],
                s["tag"],
                s["cartel"],
                s["lead_text"],
                s["bullets"],
                s["specs"],
                s["panels"],
                s["pills"],
                s["assays"],
                s["cards"],
                s["areas"],
                s["stats"],
                s["images"],
                s["body_text"],
            )
            for s in slides
        ],
    )
    # Keep constants in sync with slide count
    con.execute(
        """
        INSERT OR REPLACE INTO constants VALUES (?, ?, ?)
        """,
        ["SLIDE_COUNT", str(len(slides)), "Total de diapos en index.html (sync_presentation)"],
    )
    return len(slides)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--embed", action="store_true", help="Re-embed slides after sync")
    args = parser.parse_args()

    html = HTML.read_text(encoding="utf-8")
    slides = extract_slides(html)
    if not slides:
        print("ERROR: no slides found in", HTML)
        sys.exit(1)

    con = db_connect()
    ensure_schema(con)
    n = upsert_slides(con, slides)
    con.close()
    print(f"Synced {n} slides from {HTML.relative_to(REPO)} → {DB.name}")

    for s in slides:
        extra = f" · {s['model']}" if s["model"] else ""
        print(f"  {s['slide_n']:2d}. {s['title']}{extra}")

    if args.embed:
        subprocess.check_call([sys.executable, str(ROOT / "embed.py")], cwd=str(ROOT))


if __name__ == "__main__":
    main()
