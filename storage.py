"""
Portable local-data layer for Vāṇi.

Deliberately backend-agnostic: this module has **no Streamlit, no Google and no
``logic``/``srs`` dependencies**. It owns persistence and nothing else, so the
same public API can later be re-pointed at Postgres (for a hosted multi-user
build) or at the SQLite that already ships inside iOS and Android, without
changing a single caller.

Storage is SQLite (``data/vani.db``) rather than JSON because every write here
happens mid-quiz: a torn write during a read-modify-write of one big JSON
document silently loses *all* progress, and SQLite gives transactional writes
and a real ``WHERE due <= ?`` query for free.

Everything is keyed by ``profile_id`` (default ``"local"``). There is one
profile today; the column exists so that multi-user support is a UI change
rather than a schema migration.

All timestamps are stored as fixed-width UTC ISO-8601 strings, so lexicographic
ordering in SQL is chronological ordering.
"""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

# Resolve paths relative to this file so behavior is independent of the current
# working directory (matters when packaged or launched from elsewhere).
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_BASE_DIR, "data")
DB_FILE = os.path.join(DATA_DIR, "vani.db")

# Legacy JSON store, imported once into the ``mastery`` table then left alone.
PROGRESS_FILE = os.path.join(DATA_DIR, "progress.json")

DEFAULT_PROFILE = "local"
SCHEMA_VERSION = 1


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------
def utcnow():
    """Current time as an aware UTC datetime."""
    return datetime.now(timezone.utc)


def to_iso(dt):
    """Serialize ``dt`` to fixed-width UTC ISO-8601.

    Fixed width matters: microseconds are always present, so string comparison
    in SQL (``due <= ?``) is chronological comparison. A naive datetime is
    assumed to already be UTC rather than silently taking the local zone.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="microseconds")


def from_iso(text):
    """Parse a stored timestamp back to an aware UTC datetime."""
    if not text:
        return None
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Connection / schema
# ---------------------------------------------------------------------------
_SCHEMA = """
CREATE TABLE IF NOT EXISTS cards (
    profile_id  TEXT NOT NULL,
    item_id     TEXT NOT NULL,
    topic       TEXT NOT NULL,
    due         TEXT NOT NULL,
    state       INTEGER,
    stability   REAL,
    difficulty  REAL,
    last_review TEXT,
    fsrs_json   TEXT NOT NULL,
    PRIMARY KEY (profile_id, item_id)
);
CREATE INDEX IF NOT EXISTS idx_cards_due ON cards (profile_id, due);
CREATE INDEX IF NOT EXISTS idx_cards_topic ON cards (profile_id, topic);

CREATE TABLE IF NOT EXISTS reviews (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id  TEXT NOT NULL,
    item_id     TEXT NOT NULL,
    topic       TEXT,
    tier        TEXT NOT NULL,
    rating      INTEGER NOT NULL,
    reviewed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reviews_item ON reviews (profile_id, item_id);

CREATE TABLE IF NOT EXISTS attempts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT NOT NULL,
    topic      TEXT NOT NULL,
    score      INTEGER NOT NULL,
    total      INTEGER NOT NULL,
    taken_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_attempts_topic ON attempts (profile_id, topic);

CREATE TABLE IF NOT EXISTS mastery (
    profile_id  TEXT NOT NULL,
    topic       TEXT NOT NULL,
    score       TEXT,
    mastered_at TEXT NOT NULL,
    PRIMARY KEY (profile_id, topic)
);
"""


@contextmanager
def _connect():
    """Yield a connection with the schema applied, committing on clean exit."""
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        # WAL lets a second Streamlit tab read while this one writes.
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _migrate(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _migrate(conn):
    """Create or upgrade the schema. Idempotent; safe to call on every open."""
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version >= SCHEMA_VERSION:
        return
    conn.executescript(_SCHEMA)
    if version == 0:
        _import_progress_json(conn)
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


def _import_progress_json(conn):
    """One-time import of the pre-SQLite ``data/progress.json`` mastery store.

    The file is read, never written or deleted — it stays as the only backup of
    progress made before this migration.
    """
    try:
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return
    mastered = data.get("mastered")
    if not isinstance(mastered, dict):
        return
    for topic, rec in mastered.items():
        rec = rec if isinstance(rec, dict) else {}
        conn.execute(
            "INSERT OR IGNORE INTO mastery "
            "(profile_id, topic, score, mastered_at) VALUES (?, ?, ?, ?)",
            (DEFAULT_PROFILE, topic, rec.get("score"),
             rec.get("mastered_at") or to_iso(utcnow())),
        )


def reset_for_tests():
    """Delete the database file. Tests only — never called by the app."""
    for suffix in ("", "-wal", "-shm"):
        try:
            os.remove(DB_FILE + suffix)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Mastery
# ---------------------------------------------------------------------------
def get_progress(profile_id=DEFAULT_PROFILE):
    """Return ``{"mastered": {topic: {"mastered_at", "score"}}}``."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT topic, score, mastered_at FROM mastery WHERE profile_id = ?",
            (profile_id,),
        ).fetchall()
    return {"mastered": {
        r["topic"]: {"mastered_at": r["mastered_at"], "score": r["score"]}
        for r in rows
    }}


def is_mastered(topic, profile_id=DEFAULT_PROFILE):
    """True if ``topic`` has been recorded as mastered."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM mastery WHERE profile_id = ? AND topic = ?",
            (profile_id, topic),
        ).fetchone()
    return row is not None


def set_mastered(topic, score=None, profile_id=DEFAULT_PROFILE, at=None):
    """Record ``topic`` as mastered (optionally with a score string)."""
    with _connect() as conn:
        conn.execute(
            "INSERT INTO mastery (profile_id, topic, score, mastered_at) "
            "VALUES (?, ?, ?, ?) ON CONFLICT(profile_id, topic) DO UPDATE SET "
            "score = excluded.score, mastered_at = excluded.mastered_at",
            (profile_id, topic, score, to_iso(at or utcnow())),
        )


def clear_mastered(topic, profile_id=DEFAULT_PROFILE):
    """Remove a mastery record so the topic can be re-tested. No-op if absent."""
    with _connect() as conn:
        conn.execute(
            "DELETE FROM mastery WHERE profile_id = ? AND topic = ?",
            (profile_id, topic),
        )


# ---------------------------------------------------------------------------
# Quiz attempts
# ---------------------------------------------------------------------------
def record_attempt(topic, score, total, profile_id=DEFAULT_PROFILE, at=None):
    """Append one completed quiz attempt."""
    with _connect() as conn:
        conn.execute(
            "INSERT INTO attempts (profile_id, topic, score, total, taken_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (profile_id, topic, int(score), int(total), to_iso(at or utcnow())),
        )


def get_attempts(topic=None, profile_id=DEFAULT_PROFILE):
    """Return attempts newest-first as dicts, optionally filtered by topic."""
    sql = ("SELECT topic, score, total, taken_at FROM attempts "
           "WHERE profile_id = ?")
    params = [profile_id]
    if topic is not None:
        sql += " AND topic = ?"
        params.append(topic)
    sql += " ORDER BY taken_at DESC, id DESC"
    with _connect() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def get_topic_stats(profile_id=DEFAULT_PROFILE):
    """Per-topic summary: attempt count, best score, and last attempt time."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT topic, COUNT(*) AS attempts, MAX(score) AS best, "
            "MAX(total) AS total, MAX(taken_at) AS last_attempt "
            "FROM attempts WHERE profile_id = ? GROUP BY topic",
            (profile_id,),
        ).fetchall()
    return {r["topic"]: dict(r) for r in rows}


# ---------------------------------------------------------------------------
# SRS cards
# ---------------------------------------------------------------------------
def get_card(item_id, profile_id=DEFAULT_PROFILE):
    """Return the stored card row as a dict, or None if the item is new."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM cards WHERE profile_id = ? AND item_id = ?",
            (profile_id, item_id),
        ).fetchone()
    return dict(row) if row else None


def upsert_card(item_id, topic, fsrs_json, due, state=None, stability=None,
                difficulty=None, last_review=None, profile_id=DEFAULT_PROFILE):
    """Insert or replace the FSRS state for one bank item.

    ``fsrs_json`` is the scheduler's own serialized card. It is stored whole so
    this schema does not have to track py-fsrs's field set, which has changed
    across releases; ``due`` and the rest are denormalized only because they
    are queried or displayed.
    """
    with _connect() as conn:
        conn.execute(
            "INSERT INTO cards (profile_id, item_id, topic, due, state, "
            "stability, difficulty, last_review, fsrs_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(profile_id, item_id) DO UPDATE SET "
            "topic = excluded.topic, due = excluded.due, "
            "state = excluded.state, stability = excluded.stability, "
            "difficulty = excluded.difficulty, "
            "last_review = excluded.last_review, "
            "fsrs_json = excluded.fsrs_json",
            (profile_id, item_id, topic, due, state, stability, difficulty,
             last_review, fsrs_json),
        )


def log_review(item_id, tier, rating, topic=None, profile_id=DEFAULT_PROFILE,
               at=None):
    """Append one graded answer to the immutable review history.

    This table, not the card, is the source of truth for counts: an FSRS card
    carries no reps/lapses fields, so those are derived here.
    """
    with _connect() as conn:
        conn.execute(
            "INSERT INTO reviews (profile_id, item_id, topic, tier, rating, "
            "reviewed_at) VALUES (?, ?, ?, ?, ?, ?)",
            (profile_id, item_id, topic, tier, int(rating),
             to_iso(at or utcnow())),
        )


def get_review_counts(item_id, profile_id=DEFAULT_PROFILE):
    """Return ``{"reps": n, "lapses": n}`` derived from review history."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS reps, "
            "SUM(CASE WHEN tier = 'incorrect' THEN 1 ELSE 0 END) AS lapses "
            "FROM reviews WHERE profile_id = ? AND item_id = ?",
            (profile_id, item_id),
        ).fetchone()
    return {"reps": row["reps"] or 0, "lapses": row["lapses"] or 0}


def get_due_cards(topic=None, limit=None, now=None, profile_id=DEFAULT_PROFILE):
    """Return due card rows, soonest-due first.

    A card is due when its stored ``due`` is at or before ``now``.
    """
    sql = "SELECT * FROM cards WHERE profile_id = ? AND due <= ?"
    params = [profile_id, to_iso(now or utcnow())]
    if topic is not None:
        sql += " AND topic = ?"
        params.append(topic)
    sql += " ORDER BY due ASC"
    if limit is not None:
        sql += " LIMIT ?"
        params.append(int(limit))
    with _connect() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def get_due_counts_by_topic(now=None, profile_id=DEFAULT_PROFILE):
    """Return ``{topic: due_count}``, omitting topics with nothing due."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT topic, COUNT(*) AS n FROM cards "
            "WHERE profile_id = ? AND due <= ? GROUP BY topic",
            (profile_id, to_iso(now or utcnow())),
        ).fetchall()
    return {r["topic"]: r["n"] for r in rows}


def get_srs_summary(now=None, profile_id=DEFAULT_PROFILE):
    """Return ``{"tracked", "due", "next_due"}`` for the Review dashboard."""
    stamp = to_iso(now or utcnow())
    with _connect() as conn:
        tracked = conn.execute(
            "SELECT COUNT(*) FROM cards WHERE profile_id = ?",
            (profile_id,),
        ).fetchone()[0]
        due = conn.execute(
            "SELECT COUNT(*) FROM cards WHERE profile_id = ? AND due <= ?",
            (profile_id, stamp),
        ).fetchone()[0]
        nxt = conn.execute(
            "SELECT MIN(due) FROM cards WHERE profile_id = ? AND due > ?",
            (profile_id, stamp),
        ).fetchone()[0]
    return {"tracked": tracked, "due": due, "next_due": nxt}
