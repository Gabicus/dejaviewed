#!/usr/bin/env python3
"""Agent-friendly query helpers over data/entries.parquet + data/crosslinks.parquet.

Designed to be imported by skills or run as a CLI:
    python scripts/cms_context.py find "pliny"
    python scripts/cms_context.py tier S
    python scripts/cms_context.py related <entry_id>
    python scripts/cms_context.py favorites

All queries return dicts ready to JSON-serialize. Keep the surface small and
stable so skills can depend on it.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
ENTRIES = ROOT / "data" / "entries.parquet"
CROSSLINKS = ROOT / "data" / "crosslinks.parquet"


def _con():
    if not ENTRIES.exists():
        raise FileNotFoundError(f"{ENTRIES} not found — run `python scripts/cms.py migrate`")
    con = duckdb.connect(":memory:")
    con.execute(f"CREATE VIEW e AS SELECT * FROM read_parquet('{ENTRIES.as_posix()}')")
    if CROSSLINKS.exists():
        con.execute(f"CREATE VIEW x AS SELECT * FROM read_parquet('{CROSSLINKS.as_posix()}')")
    return con


def find(query: str, limit: int = 20) -> list[dict]:
    """Case-insensitive search across title/creator/summary/url."""
    con = _con()
    q = f"%{query.lower()}%"
    rows = con.execute(
        "SELECT id, title, creator, tier, type, url, summary "
        "FROM e "
        "WHERE lower(title) LIKE ? OR lower(creator) LIKE ? "
        "   OR lower(summary) LIKE ? OR lower(url) LIKE ? "
        "ORDER BY tier, title LIMIT ?",
        [q, q, q, q, limit],
    ).fetchall()
    cols = ["id", "title", "creator", "tier", "type", "url", "summary"]
    return [dict(zip(cols, r)) for r in rows]


def by_tier(tier: str, limit: int = 100) -> list[dict]:
    con = _con()
    rows = con.execute(
        "SELECT id, title, creator, type, url FROM e WHERE tier = ? ORDER BY title LIMIT ?",
        [tier.upper(), limit],
    ).fetchall()
    return [dict(zip(["id", "title", "creator", "type", "url"], r)) for r in rows]


def favorites(limit: int = 200) -> list[dict]:
    con = _con()
    rows = con.execute(
        "SELECT id, title, creator, tier, url FROM e WHERE favorited = TRUE "
        "ORDER BY tier, title LIMIT ?",
        [limit],
    ).fetchall()
    return [dict(zip(["id", "title", "creator", "tier", "url"], r)) for r in rows]


def related(entry_id: str, limit: int = 20) -> list[dict]:
    """Entries connected via crosslinks (any dim), aggregated by summed weight."""
    con = _con()
    if not CROSSLINKS.exists():
        return []
    rows = con.execute(
        "WITH paired AS ("
        "  SELECT b_id AS other, dim, weight FROM x WHERE a_id = ? "
        "  UNION ALL "
        "  SELECT a_id AS other, dim, weight FROM x WHERE b_id = ? "
        ") "
        "SELECT e.id, e.title, e.creator, e.tier, "
        "       sum(paired.weight) AS score, "
        "       string_agg(DISTINCT paired.dim, ',') AS dims "
        "FROM paired JOIN e ON e.id = paired.other "
        "GROUP BY e.id, e.title, e.creator, e.tier "
        "ORDER BY score DESC LIMIT ?",
        [entry_id, entry_id, limit],
    ).fetchall()
    return [dict(zip(["id", "title", "creator", "tier", "score", "dims"], r)) for r in rows]


def stats() -> dict:
    con = _con()
    out = {}
    out["total_entries"] = con.execute("SELECT count(*) FROM e").fetchone()[0]
    out["by_tier"] = dict(con.execute(
        "SELECT tier, count(*) FROM e GROUP BY tier ORDER BY tier").fetchall())
    out["by_type"] = dict(con.execute(
        "SELECT type, count(*) FROM e GROUP BY type ORDER BY 2 DESC").fetchall())
    out["favorited"] = con.execute(
        "SELECT count(*) FROM e WHERE favorited = TRUE").fetchone()[0]
    if CROSSLINKS.exists():
        out["total_crosslinks"] = con.execute("SELECT count(*) FROM x").fetchone()[0]
        out["by_dim"] = dict(con.execute(
            "SELECT dim, count(*) FROM x GROUP BY dim ORDER BY 2 DESC").fetchall())
    return out


def main(argv=None):
    p = argparse.ArgumentParser(prog="cms_context")
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("find"); f.add_argument("query"); f.add_argument("--limit", type=int, default=20)
    t = sub.add_parser("tier"); t.add_argument("tier"); t.add_argument("--limit", type=int, default=100)
    r = sub.add_parser("related"); r.add_argument("id"); r.add_argument("--limit", type=int, default=20)
    sub.add_parser("favorites")
    sub.add_parser("stats")
    args = p.parse_args(argv)
    result = {
        "find": lambda: find(args.query, args.limit),
        "tier": lambda: by_tier(args.tier, args.limit),
        "related": lambda: related(args.id, args.limit),
        "favorites": lambda: favorites(),
        "stats": lambda: stats(),
    }[args.cmd]()
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
