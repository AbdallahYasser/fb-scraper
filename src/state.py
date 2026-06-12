"""SQLite state store for resumable, dedup-safe scraping.

One row per post. Phase 1 (index) inserts posts as 'pending'; Phase 2 (fetch)
marks them 'done' (or 'failed') so re-runs skip finished work and retry failures.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    post_id       TEXT PRIMARY KEY,
    permalink     TEXT,
    date_str      TEXT,          -- human label as shown on FB ("7 May", "3h")
    date_iso      TEXT,          -- normalized YYYY-MM-DD for filtering/sorting
    has_photo     INTEGER DEFAULT 0,
    preview       TEXT,          -- full post text (from GraphQL) or a snippet
    status        TEXT DEFAULT 'pending',   -- pending | done | failed
    attempts      INTEGER DEFAULT 0,
    n_comments    INTEGER,
    note_path     TEXT,
    fetched_at    INTEGER,
    indexed_at    INTEGER
);
CREATE INDEX IF NOT EXISTS idx_status ON posts(status);
CREATE INDEX IF NOT EXISTS idx_date   ON posts(date_iso);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


def upsert_post(conn: sqlite3.Connection, post: dict) -> None:
    """Insert a newly-indexed post, or refresh its metadata WITHOUT touching its
    status/attempts (so we never re-do or lose progress on re-index)."""
    conn.execute(
        """
        INSERT INTO posts (post_id, permalink, date_str, date_iso, has_photo,
                           preview, indexed_at)
        VALUES (:post_id, :permalink, :date_str, :date_iso, :has_photo,
                :preview, :now)
        ON CONFLICT(post_id) DO UPDATE SET
            permalink = excluded.permalink,
            date_str  = COALESCE(excluded.date_str, posts.date_str),
            date_iso  = COALESCE(excluded.date_iso, posts.date_iso),
            has_photo = excluded.has_photo,
            preview   = COALESCE(excluded.preview, posts.preview)
        """,
        {**post, "now": int(time.time())},
    )
    conn.commit()


def get_pending(conn, since_iso: str | None = None, limit: int | None = None,
                newest_first: bool = True) -> list[sqlite3.Row]:
    """Posts not yet done (pending or failed), optionally on/after a date."""
    q = "SELECT * FROM posts WHERE status != 'done'"
    args: list = []
    if since_iso:
        q += " AND (date_iso IS NULL OR date_iso >= ?)"
        args.append(since_iso)
    q += f" ORDER BY date_iso {'DESC' if newest_first else 'ASC'}"
    if limit:
        q += " LIMIT ?"
        args.append(limit)
    return conn.execute(q, args).fetchall()


def mark(conn, post_id: str, status: str, *, note_path: str | None = None,
         n_comments: int | None = None) -> None:
    conn.execute(
        """UPDATE posts SET status=?, attempts=attempts+1, fetched_at=?,
                            note_path=COALESCE(?, note_path),
                            n_comments=COALESCE(?, n_comments)
           WHERE post_id=?""",
        (status, int(time.time()), note_path, n_comments, post_id),
    )
    conn.commit()


def stats(conn) -> dict:
    rows = conn.execute(
        "SELECT status, COUNT(*) c FROM posts GROUP BY status").fetchall()
    out = {r["status"]: r["c"] for r in rows}
    out["total"] = sum(out.values())
    return out
