"""
Copy local SQLite progress into the hosted Postgres database.

    VANI_DATABASE_URL=postgresql://... \\
        python scripts/migrate_sqlite_to_postgres.py --sqlite data/vani.db [--dry-run]

Copies mastery, attempts, cards, reviews and users (sessions are not copied —
sign in again on the hosted app). The whole copy is one transaction, and it is
idempotent: rows already present are skipped, so re-running after a partial
failure or by accident never duplicates anything.

The SQLite file is opened read-only and left untouched as a backup — the same
policy as the legacy progress.json.
"""

import argparse
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import storage  # noqa: E402

# Tables with a primary key: ON CONFLICT DO NOTHING makes re-runs safe.
_KEYED = {
    "users": ("profile_id", "username", "password_hash", "is_admin",
              "disabled", "created_at", "last_login_at"),
    "mastery": ("profile_id", "topic", "score", "mastered_at"),
    "cards": ("profile_id", "item_id", "topic", "due", "state", "stability",
              "difficulty", "last_review", "fsrs_json"),
}

# Append-only logs with surrogate ids, which are not copied (the target assigns
# its own). A row counts as already copied if its natural key is present.
_LOGS = {
    "attempts": (("profile_id", "topic", "score", "total", "taken_at"),
                 ("profile_id", "topic", "taken_at")),
    "reviews": (("profile_id", "item_id", "topic", "tier", "rating",
                 "reviewed_at"),
                ("profile_id", "item_id", "reviewed_at")),
}

TABLES = ("users", "mastery", "cards", "attempts", "reviews")


def _read(src, table, columns):
    exists = src.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' "
                         "AND name = ?", (table,)).fetchone()
    if not exists:        # e.g. a v1 database has no users table
        return []
    return src.execute(f"SELECT {', '.join(columns)} FROM {table}").fetchall()


def _count(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def copy_database(sqlite_path, dry_run=False):
    """Copy every table into the configured storage backend.

    Returns ``{table: (source_rows, target_before, target_after)}``. With
    ``dry_run`` the transaction is rolled back, so ``target_after`` shows what
    the copy *would* produce.
    """
    src = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
    report = {}

    class _Rollback(Exception):
        pass

    try:
        with storage._connect() as conn:
            for table in TABLES:
                if table in _KEYED:
                    columns = _KEYED[table]
                    sql = (f"INSERT INTO {table} ({', '.join(columns)}) "
                           f"VALUES ({', '.join('?' * len(columns))}) "
                           "ON CONFLICT DO NOTHING")
                    make_params = tuple
                else:
                    columns, key = _LOGS[table]
                    where = " AND ".join(f"{k} = ?" for k in key)
                    sql = (f"INSERT INTO {table} ({', '.join(columns)}) "
                           f"SELECT {', '.join('?' * len(columns))} "
                           f"WHERE NOT EXISTS (SELECT 1 FROM {table} "
                           f"WHERE {where})")
                    idx = [columns.index(k) for k in key]

                    def make_params(row, idx=idx):
                        return tuple(row) + tuple(row[i] for i in idx)

                rows = _read(src, table, columns)
                before = _count(conn, table)
                for row in rows:
                    conn.execute(sql, make_params(row))
                report[table] = (len(rows), before, _count(conn, table))
            if dry_run:
                raise _Rollback
    except _Rollback:
        pass
    finally:
        src.close()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--sqlite", default=storage.DB_FILE,
                        help="source database (default: %(default)s)")
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would be copied; change nothing")
    args = parser.parse_args(argv)

    url = os.environ.get("VANI_DATABASE_URL")
    if not url:
        sys.exit("Set VANI_DATABASE_URL to the target Postgres database.")
    if not os.path.exists(args.sqlite):
        sys.exit(f"No such file: {args.sqlite}")
    storage.configure(url)

    report = copy_database(args.sqlite, dry_run=args.dry_run)
    print(f"{'table':<10} {'source':>7} {'before':>7} {'after':>7}")
    for table, (source, before, after) in report.items():
        print(f"{table:<10} {source:>7} {before:>7} {after:>7}")
    print("DRY RUN — nothing written." if args.dry_run else "Done.")


if __name__ == "__main__":
    main()
