"""
Portable local-data layer for Vāṇi.

Deliberately backend-agnostic: this module has **no Streamlit, no Google and no
``logic``/``srs`` dependencies**. It owns persistence and nothing else, so the
same public API can later be re-pointed at Postgres (for a hosted multi-user
build) or at the SQLite that already ships inside iOS and Android, without
changing a single caller.

Two backends share one SQL dialect-subset: **SQLite** at ``data/vani.db`` (local
dev and tests; the default) and **Postgres** when ``configure()`` is given a
database URL (the hosted build — Streamlit Community Cloud wipes its disk on
every reboot, so SQLite there would lose everyone's progress). SQL is written
once with ``?`` placeholders; the Postgres adapter translates them.

Storage is a database rather than JSON because every write here
happens mid-quiz: a torn write during a read-modify-write of one big JSON
document silently loses *all* progress, and SQLite gives transactional writes
and a real ``WHERE due <= ?`` query for free.

Everything is keyed by ``profile_id`` (default ``"local"``). A logged-in user's
``profile_id`` comes from the ``users`` table; ``"local"`` is the pre-login
profile, which an account can adopt by being created with that id.

All timestamps are stored as fixed-width UTC ISO-8601 strings, so lexicographic
ordering in SQL is chronological ordering.
"""

import atexit
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
SCHEMA_VERSION = 2

# Set by configure(). None means SQLite at DB_FILE.
_DATABASE_URL = None
_pool = None
_pg_migrated = False


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
_SCHEMA_V1 = """
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

# v2: accounts. ``profile_id`` is the key every progress table already uses, so
# a user's progress is just the rows under their profile_id — nothing else in
# the schema had to change. Usernames are stored normalized (see auth.py) and
# are separate from profile_id so a rename never re-keys progress.
_SCHEMA_V2 = """
CREATE TABLE IF NOT EXISTS users (
    profile_id    TEXT PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_admin      INTEGER NOT NULL DEFAULT 0,
    disabled      INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL,
    last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash   TEXT PRIMARY KEY,
    profile_id   TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    expires_at   TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_profile ON sessions (profile_id);

CREATE TABLE IF NOT EXISTS login_failures (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    username  TEXT NOT NULL,
    failed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_login_failures
    ON login_failures (username, failed_at);
"""


def configure(database_url=None):
    """Select the backend: a ``postgres://``/``postgresql://`` URL, or None
    for SQLite at ``DB_FILE``. Cheap to call on every Streamlit rerun — a
    repeat call with the same URL keeps the existing connection pool."""
    global _DATABASE_URL, _pool, _pg_migrated
    database_url = database_url or None
    if database_url == _DATABASE_URL:
        return
    if _pool is not None:
        _pool.close()
    _DATABASE_URL, _pool, _pg_migrated = database_url, None, False


def backend():
    """``"postgres"`` or ``"sqlite"``."""
    return "postgres" if _DATABASE_URL else "sqlite"


class _Row(dict):
    """A dict that also indexes by position, like ``sqlite3.Row`` — callers
    use both ``row["due"]`` and ``fetchone()[0]``."""

    def __init__(self, columns, values):
        super().__init__(zip(columns, values))
        self._values = values

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return super().__getitem__(key)


def _pg_row_factory(cursor):
    # description is None for statements with no result set — including the
    # pool's own health check, which silently never succeeds if this raises.
    columns = [c.name for c in cursor.description or ()]
    return lambda values: _Row(columns, values)


class _PgConn:
    """Adapts a psycopg connection to the slice of the sqlite3 API used here."""

    dialect = "postgres"

    def __init__(self, raw):
        self._raw = raw

    def execute(self, sql, params=()):
        return self._raw.execute(sql.replace("?", "%s"), params)

    def executescript(self, script):
        script = script.replace(
            "INTEGER PRIMARY KEY AUTOINCREMENT",
            "BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY")
        for statement in script.split(";"):
            if statement.strip():
                self._raw.execute(statement)


class _SqliteConn:
    dialect = "sqlite"

    def __init__(self, raw):
        self._raw = raw

    def execute(self, sql, params=()):
        return self._raw.execute(sql, params)

    def executescript(self, script):
        self._raw.executescript(script)


def _get_pool():
    global _pool
    if _pool is None:
        from psycopg_pool import ConnectionPool  # only needed when hosted
        # A pool, not a connection per call: every call here is a network
        # round trip, and a fresh TLS handshake per quiz answer adds up.
        # check= replaces connections the server dropped while idle (Neon
        # suspends idle compute).
        _pool = ConnectionPool(
            _DATABASE_URL, min_size=1, max_size=4, open=True,
            kwargs={"row_factory": _pg_row_factory},
            check=ConnectionPool.check_connection)
    return _pool


@atexit.register
def close():
    """Close the Postgres pool, if any. Registered at exit: an unclosed pool's
    worker threads otherwise stall interpreter shutdown for seconds apiece."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def _connect():
    """Yield a connection with the schema applied, committing on clean exit."""
    if _DATABASE_URL:
        yield from _connect_postgres()
    else:
        yield from _connect_sqlite()


def _connect_postgres():
    global _pg_migrated
    # The pool's context manager commits on clean exit, rolls back on error.
    migrating = not _pg_migrated
    with _get_pool().connection() as raw:
        conn = _PgConn(raw)
        if migrating:
            # Serialize migrations across app instances starting together.
            conn.execute("SELECT pg_advisory_xact_lock(7300531)")
            _migrate(conn)
        yield conn
    # Only once committed: the migration shares the caller's transaction, so
    # if the caller's work failed the schema changes were rolled back too.
    if migrating:
        _pg_migrated = True


def _connect_sqlite():
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    raw = sqlite3.connect(DB_FILE, check_same_thread=False)
    raw.row_factory = sqlite3.Row
    conn = _SqliteConn(raw)
    try:
        # WAL lets a second Streamlit tab read while this one writes.
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _migrate(conn)
        yield conn
        raw.commit()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()


def _integrity_errors():
    errors = (sqlite3.IntegrityError,)
    if _DATABASE_URL:
        import psycopg
        errors += (psycopg.IntegrityError,)
    return errors


def _migrate(conn):
    """Create or upgrade the schema. Idempotent; safe to call on every open.

    The version lives in a ``schema_meta`` table rather than SQLite's
    ``PRAGMA user_version`` so the same bookkeeping works on Postgres. Databases
    created before v2 only carry the pragma, so it is read as a fallback.
    """
    conn.execute("CREATE TABLE IF NOT EXISTS schema_meta "
                 "(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    version = _read_schema_version(conn)
    if version >= SCHEMA_VERSION:
        return
    if version < 1:
        conn.executescript(_SCHEMA_V1)
        _import_progress_json(conn)
    if version < 2:
        conn.executescript(_SCHEMA_V2)
    conn.execute(
        "INSERT INTO schema_meta (key, value) VALUES ('version', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (str(SCHEMA_VERSION),),
    )


def _read_schema_version(conn):
    row = conn.execute(
        "SELECT value FROM schema_meta WHERE key = 'version'").fetchone()
    if row is not None:
        return int(row[0])
    if conn.dialect == "sqlite":
        return conn.execute("PRAGMA user_version").fetchone()[0]
    return 0


def get_schema_version():
    """The schema version of the configured database (migrating it first)."""
    with _connect() as conn:
        return _read_schema_version(conn)


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
            "INSERT INTO mastery (profile_id, topic, score, mastered_at) "
            "VALUES (?, ?, ?, ?) ON CONFLICT DO NOTHING",
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


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
# Pure CRUD: hashing, normalization and policy live in auth.py, so this layer
# never sees a plaintext password or a raw session token.
_USER_COLUMNS = ("profile_id, username, password_hash, is_admin, disabled, "
                 "created_at, last_login_at")


def _user_row(row):
    if row is None:
        return None
    user = dict(row)
    user["is_admin"] = bool(user["is_admin"])
    user["disabled"] = bool(user["disabled"])
    return user


def create_user(profile_id, username, password_hash, is_admin=False, at=None):
    """Insert a user. Raises ``ValueError`` if the username or profile is taken."""
    try:
        with _connect() as conn:
            conn.execute(
                f"INSERT INTO users ({_USER_COLUMNS}) "
                "VALUES (?, ?, ?, ?, 0, ?, NULL)",
                (profile_id, username, password_hash, int(bool(is_admin)),
                 to_iso(at or utcnow())),
            )
    except _integrity_errors() as e:
        raise ValueError(
            f"username {username!r} or profile {profile_id!r} already exists"
        ) from e


def get_user(profile_id):
    """Return the user dict for ``profile_id``, or None."""
    with _connect() as conn:
        row = conn.execute(
            f"SELECT {_USER_COLUMNS} FROM users WHERE profile_id = ?",
            (profile_id,),
        ).fetchone()
    return _user_row(row)


def get_user_by_username(username):
    """Return the user dict for an already-normalized ``username``, or None."""
    with _connect() as conn:
        row = conn.execute(
            f"SELECT {_USER_COLUMNS} FROM users WHERE username = ?",
            (username,),
        ).fetchone()
    return _user_row(row)


def list_users():
    """All users, ordered by username."""
    with _connect() as conn:
        rows = conn.execute(
            f"SELECT {_USER_COLUMNS} FROM users ORDER BY username").fetchall()
    return [_user_row(r) for r in rows]


def set_password_hash(profile_id, password_hash):
    with _connect() as conn:
        conn.execute("UPDATE users SET password_hash = ? WHERE profile_id = ?",
                     (password_hash, profile_id))


def set_user_disabled(profile_id, disabled):
    with _connect() as conn:
        conn.execute("UPDATE users SET disabled = ? WHERE profile_id = ?",
                     (int(bool(disabled)), profile_id))


def touch_last_login(profile_id, at=None):
    with _connect() as conn:
        conn.execute("UPDATE users SET last_login_at = ? WHERE profile_id = ?",
                     (to_iso(at or utcnow()), profile_id))


# ---------------------------------------------------------------------------
# Sessions ("remember me")
# ---------------------------------------------------------------------------
def create_session(token_hash, profile_id, expires_at, at=None):
    stamp = to_iso(at or utcnow())
    with _connect() as conn:
        conn.execute(
            "INSERT INTO sessions (token_hash, profile_id, created_at, "
            "expires_at, last_seen_at) VALUES (?, ?, ?, ?, ?)",
            (token_hash, profile_id, stamp, to_iso(expires_at), stamp),
        )


def get_session(token_hash, now=None):
    """Return the unexpired session row for ``token_hash``, or None."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE token_hash = ? AND expires_at > ?",
            (token_hash, to_iso(now or utcnow())),
        ).fetchone()
    return dict(row) if row else None


def touch_session(token_hash, at=None):
    with _connect() as conn:
        conn.execute("UPDATE sessions SET last_seen_at = ? WHERE token_hash = ?",
                     (to_iso(at or utcnow()), token_hash))


def delete_session(token_hash):
    with _connect() as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))


def delete_sessions_for(profile_id, keep=None):
    """Revoke every session of ``profile_id`` except ``keep`` (a token hash)."""
    with _connect() as conn:
        conn.execute(
            "DELETE FROM sessions WHERE profile_id = ? AND token_hash != ?",
            (profile_id, keep or ""),
        )


def purge_expired_sessions(now=None):
    """Delete expired sessions; returns how many were removed."""
    with _connect() as conn:
        cur = conn.execute("DELETE FROM sessions WHERE expires_at <= ?",
                           (to_iso(now or utcnow()),))
        return cur.rowcount


# ---------------------------------------------------------------------------
# Login throttling
# ---------------------------------------------------------------------------
def record_login_failure(username, at=None):
    with _connect() as conn:
        conn.execute(
            "INSERT INTO login_failures (username, failed_at) VALUES (?, ?)",
            (username, to_iso(at or utcnow())),
        )


def count_recent_login_failures(username, since):
    """Failures for ``username`` at or after ``since``."""
    with _connect() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM login_failures "
            "WHERE username = ? AND failed_at >= ?",
            (username, to_iso(since)),
        ).fetchone()[0]


def clear_login_failures(username):
    with _connect() as conn:
        conn.execute("DELETE FROM login_failures WHERE username = ?",
                     (username,))
