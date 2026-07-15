"""
Ingest Leo presentation feedback into DuckDB — NO design changes.

Usage:
  # Paste a batch (one comment per line, or blocks separated by ---)
  python ingest_feedback.py --batch 2026-07-15-am <<'EOF'
  Diapo 4: capitalize Congresos...
  ---
  Diapo 9: cartel 150 test/hora en A15
  EOF

  # Single comment
  python ingest_feedback.py --batch 2026-07-15-am --slide 9 --text "Agregar cartel 150 test/hora"

  # List pending
  python ingest_feedback.py --list
  python ingest_feedback.py --list --status pending
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent
DB = ROOT / "laborteknic.duckdb"
SCHEMA = ROOT / "schema.sql"


def connect():
    con = duckdb.connect(str(DB))
    con.execute(SCHEMA.read_text())
    return con


def guess_slide(text: str) -> tuple[int | None, str | None]:
    """Extract slide_n and a short ref from free text."""
    # Prefer explicit "Diapo #N" / "Diapo N" / "slide N"
    m = re.search(
        r"(?:diapo(?:sitiva)?|slide)\s*#?\s*(\d+)",
        text,
        re.I,
    )
    if m:
        n = int(m.group(1))
        return n, f"diapo {n}"
    # title hints (only if no explicit number)
    hints = [
        (r"\bportada\b|\bcover\b", None, "portada"),
        (r"qui[eé]nes\s+somos", 2, "Quiénes somos"),
        (r"instalaciones", 3, "instalaciones"),
        (r"eventos|exposiciones|congresos", 4, "eventos"),
        (r"austral\s*farma|socio\s+comercial", 5, "Austral Farma"),
        (r"\bbiosystems\b(?!\s*descrip)", 6, "BioSystems"),
        (r"qu[ií]mica\s+cl[ií]nica", 7, "Química Clínica"),
        (r"\bBTS\b", 8, "BTS"),
        (r"\bA15\b", 9, "A15"),
        (r"\bA25\b", 10, "A25"),
        (r"\bBA\s*200\b", 11, "BA 200"),
        (r"\bBA\s*400\b", 12, "BA 400"),
        (r"reactivos", 13, "Reactivos"),
        (r"ensayos\s+diferenciales", 14, "Ensayos diferenciales"),
        (r"autoinmunidad|elisa|inmunofluorescencia", 15, "Autoinmunidad"),
        (r"prevecal", 16, "Prevecal"),
        (r"\bsnibe\b|\bmaglumi\b", 17, "SNIBE"),
        (r"\btechlab\b", 18, "Techlab"),
        (r"\babbott\b|toxicol", 19, "Abbott"),
        (r"\bcierre\b|cerca del laboratorio", 20, "cierre"),
    ]
    for pat, n, ref in hints:
        if re.search(pat, text, re.I):
            return n, ref
    return None, None


def summarize(text: str) -> str:
    s = re.sub(r"\s+", " ", text).strip()
    return s if len(s) <= 160 else s[:157] + "…"


def next_batch_id(con) -> str:
    today = date.today().isoformat()
    n = con.execute(
        "SELECT count(DISTINCT batch_id) FROM feedback WHERE batch_id LIKE ?",
        [f"{today}%"],
    ).fetchone()[0]
    return f"{today}-{n + 1}"


def next_seq(con, batch_id: str) -> int:
    row = con.execute(
        "SELECT coalesce(max(seq), 0) FROM feedback WHERE batch_id = ?",
        [batch_id],
    ).fetchone()
    return int(row[0]) + 1


def split_comments(blob: str) -> list[str]:
    blob = blob.strip()
    if not blob:
        return []
    if "\n---" in blob or blob.startswith("---"):
        parts = re.split(r"\n\s*---\s*\n", blob)
        return [p.strip() for p in parts if p.strip()]
    # blank-line paragraphs
    paras = re.split(r"\n\s*\n", blob)
    if len(paras) > 1:
        return [p.strip() for p in paras if p.strip()]
    # one comment per non-empty line
    lines = [ln.strip() for ln in blob.splitlines() if ln.strip()]
    if len(lines) > 1 and all(len(ln) < 240 for ln in lines):
        return lines
    return [blob]


def ingest(con, batch_id: str, texts: list[str], slide_n: int | None = None) -> list[str]:
    ids = []
    seq = next_seq(con, batch_id)
    for text in texts:
        sn, ref = (slide_n, f"diapo {slide_n}") if slide_n is not None else guess_slide(text)
        fid = f"{batch_id}-{seq:03d}"
        con.execute(
            """
            INSERT INTO feedback
              (id, batch_id, seq, slide_n, slide_ref, status, raw_text, summary)
            VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
            """,
            [fid, batch_id, seq, sn, ref, text.strip(), summarize(text)],
        )
        ids.append(fid)
        print(f"  + {fid}  slide={sn or '—'}  {summarize(text)[:80]}")
        seq += 1
    return ids


def list_feedback(con, status: str | None = None):
    sql = "SELECT id, batch_id, slide_n, slide_ref, status, summary FROM feedback"
    params: list = []
    if status:
        sql += " WHERE status = ?"
        params.append(status)
    sql += " ORDER BY batch_id, seq"
    rows = con.execute(sql, params).fetchall()
    if not rows:
        print("No feedback.")
        return
    print(f"\n── feedback ({status or 'all'}): {len(rows)} ──\n")
    for fid, batch, sn, ref, st, summary in rows:
        loc = f"diapo {sn}" if sn else (ref or "global")
        print(f"  [{st}] {fid}  ({loc})")
        print(f"       {summary}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest presentation feedback (no design apply)")
    parser.add_argument("--batch", help="Batch id (default: YYYY-MM-DD-N)")
    parser.add_argument("--slide", type=int, help="Force slide number (1-based)")
    parser.add_argument("--text", help="Single comment text")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--status", default=None)
    args = parser.parse_args()

    con = connect()

    if args.list:
        list_feedback(con, args.status)
        con.close()
        return

    batch_id = args.batch or next_batch_id(con)

    if args.text:
        texts = [args.text]
    elif not sys.stdin.isatty():
        texts = split_comments(sys.stdin.read())
    else:
        print("Paste comments (end with Ctrl-D). Separate with blank lines or ---")
        texts = split_comments(sys.stdin.read())

    if not texts:
        print("Nothing to ingest.")
        con.close()
        sys.exit(1)

    print(f"Ingesting batch {batch_id} ({len(texts)} comments) — status=pending, no design apply")
    ids = ingest(con, batch_id, texts, slide_n=args.slide)
    con.close()
    print(f"Done: {len(ids)} feedback rows saved.")


if __name__ == "__main__":
    main()
