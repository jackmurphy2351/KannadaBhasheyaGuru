"""
scripts/migrate_sqlite_to_postgres.py — the copy logic is backend-agnostic, so
it is exercised here SQLite → SQLite (the target being the isolated_db). The
Postgres suite reruns these against a real target.
"""
import importlib.util
import os
import sqlite3
from datetime import timedelta

import pytest

import auth
import storage

_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "scripts", "migrate_sqlite_to_postgres.py")
_spec = importlib.util.spec_from_file_location("migrate_sqlite_to_postgres",
                                               _PATH)
migrate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(migrate)

NOW = storage.utcnow()


@pytest.fixture
def source(tmp_path, monkeypatch):
    """A populated source database, built through storage itself, after which
    storage is pointed back at the (empty) target."""
    target = storage.DB_FILE
    src = str(tmp_path / "source.db")
    monkeypatch.setattr(storage, "DB_FILE", src)
    auth.create_user("asha", "correct horse battery", profile_id="local")
    storage.set_mastered("Negation", score="10/10", at=NOW)
    storage.record_attempt("Negation", 10, 10, at=NOW)
    storage.record_attempt("Negation", 7, 10, at=NOW - timedelta(days=1))
    storage.upsert_card("neg_001", "Negation", "{}", storage.to_iso(NOW))
    storage.log_review("neg_001", "incorrect", 1, topic="Negation", at=NOW)
    auth.issue_session("local")
    monkeypatch.setattr(storage, "DB_FILE", target)
    return src


def test_copies_everything_but_sessions(source):
    report = migrate.copy_database(source)
    assert {t: r[2] for t, r in report.items()} == {
        "users": 1, "mastery": 1, "cards": 1, "attempts": 2, "reviews": 1}
    assert storage.is_mastered("Negation")
    assert [a["score"] for a in storage.get_attempts()] == [10, 7]
    assert storage.get_review_counts("neg_001") == {"reps": 1, "lapses": 1}
    # The copied account still signs in and sees its progress.
    user = auth.authenticate("asha", "correct horse battery")
    assert storage.is_mastered("Negation", profile_id=user["profile_id"])
    assert storage.purge_expired_sessions(now=NOW + timedelta(days=365)) == 0


def test_rerun_is_idempotent(source):
    migrate.copy_database(source)
    report = migrate.copy_database(source)
    assert all(before == after for _, before, after in report.values())
    assert len(storage.get_attempts()) == 2


def test_dry_run_writes_nothing(source):
    report = migrate.copy_database(source, dry_run=True)
    assert report["attempts"] == (2, 0, 2)
    assert storage.get_attempts() == []
    assert storage.list_users() == []


def test_source_is_not_modified(source):
    before = os.path.getmtime(source)
    migrate.copy_database(source)
    assert os.path.getmtime(source) == before


def test_v1_source_without_users_table(tmp_path):
    src = str(tmp_path / "v1.db")
    with sqlite3.connect(src) as conn:
        conn.executescript(storage._SCHEMA_V1)
        conn.execute("INSERT INTO mastery VALUES ('local', 'Adverbs', '9/10', ?)",
                     (storage.to_iso(NOW),))
    report = migrate.copy_database(src)
    assert report["users"] == (0, 0, 0)
    assert storage.is_mastered("Adverbs")


def test_cli_refuses_without_target(monkeypatch, source):
    monkeypatch.delenv("VANI_DATABASE_URL", raising=False)
    with pytest.raises(SystemExit):
        migrate.main(["--sqlite", source])
