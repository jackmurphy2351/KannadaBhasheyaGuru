"""
The storage contract, rerun against a real Postgres.

Opt-in and deselected by default (``-m postgres``); needs
``VANI_TEST_DATABASE_URL`` pointing at a **throwaway** database — every test
drops all Vāṇi tables first. Never point it at the production database.

    VANI_TEST_DATABASE_URL=postgresql://... python -m pytest -m postgres -q

The SQLite-specific classes (schema pragmas, progress.json import, the
_migrate-patching durability test) are not rerun; the rest of test_storage and
test_auth run unchanged, which is the point: one API, two backends.
"""
import os
from datetime import timedelta

import pytest

import storage

pytestmark = pytest.mark.postgres

URL = os.environ.get("VANI_TEST_DATABASE_URL")
if not URL:
    pytest.skip("VANI_TEST_DATABASE_URL not set", allow_module_level=True)

from tests.test_storage import (  # noqa: E402,F401  (rerun under Postgres)
    TestAttempts, TestCards, TestDueQueries, TestEmailConfirmations,
    TestLoginFailures, TestMastery, TestProfileIsolation, TestReviewLog,
    TestSessions, TestUsers,
)
from tests.test_auth import (  # noqa: E402,F401
    TestAuthenticate, TestAuthenticateUnconfirmed, TestConfirmSignup,
    TestCreateUser, TestPasswordChanges, TestStartSignup,
    TestValidateSignupPassword, asha,
)
from tests.test_auth import TestSessions as _AuthSessions  # noqa: E402


class TestAuthSessions(_AuthSessions):
    # Inspects the SQLite file, which would pass vacuously here.
    test_raw_token_not_stored = None


_TABLES = ("cards", "reviews", "attempts", "mastery", "users", "sessions",
           "login_failures", "schema_meta", "email_confirmations")


@pytest.fixture(autouse=True)
def postgres(isolated_db):
    """Runs after conftest's isolated_db (which forces SQLite) and overrides it."""
    storage.configure(URL)
    with storage._get_pool().connection() as raw:
        raw.execute("DROP TABLE IF EXISTS " + ", ".join(_TABLES) + " CASCADE")
    storage._pg_migrated = False
    yield
    storage._pool.close()


def test_backend_is_postgres():
    assert storage.backend() == "postgres"
    storage.get_progress()
    assert storage.get_schema_version() == storage.SCHEMA_VERSION


def test_failed_write_rolls_back():
    storage.set_mastered("Negation", score="9/10")
    with pytest.raises(RuntimeError):
        with storage._connect() as conn:
            conn.execute("INSERT INTO mastery VALUES (?, ?, ?, ?)",
                         ("local", "Adverbs", "10/10", storage.to_iso(
                             storage.utcnow())))
            raise RuntimeError("simulated crash mid-write")
    assert storage.is_mastered("Negation")
    assert not storage.is_mastered("Adverbs")


def test_failed_first_call_does_not_mark_schema_migrated():
    with pytest.raises(RuntimeError):
        with storage._connect():
            raise RuntimeError("boom")
    assert storage._pg_migrated is False
    storage.get_progress()          # migrates for real now
    assert storage._pg_migrated is True


def test_identity_columns_autoincrement():
    now = storage.utcnow()
    storage.record_attempt("Negation", 7, 10, at=now)
    storage.record_attempt("Negation", 9, 10, at=now + timedelta(seconds=1))
    assert [a["score"] for a in storage.get_attempts("Negation")] == [9, 7]
