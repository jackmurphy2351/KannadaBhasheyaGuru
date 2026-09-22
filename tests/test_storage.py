"""
Layer 1 — persistence tests for storage.py (SQLite, no network, no Streamlit).

Every test runs against a throwaway database: the autouse ``isolated_db``
fixture in conftest.py repoints storage.DB_FILE and storage.PROGRESS_FILE at
tmp_path, so nothing here can reach the developer's real progress.
"""
import json
import os
import sqlite3
from datetime import timedelta

import pytest

import storage


NOW = storage.utcnow()


def _iso(offset_seconds=0):
    return storage.to_iso(NOW + timedelta(seconds=offset_seconds))


# ---------------------------------------------------------------------------
# Schema & migration
# ---------------------------------------------------------------------------

class TestSchema:

    def test_database_is_created_lazily(self, isolated_db):
        assert not os.path.exists(storage.DB_FILE)
        storage.get_progress()
        assert os.path.exists(storage.DB_FILE)

    def test_schema_version_is_stamped(self):
        storage.get_progress()
        with sqlite3.connect(storage.DB_FILE) as conn:
            assert conn.execute("PRAGMA user_version").fetchone()[0] == \
                storage.SCHEMA_VERSION

    def test_migration_is_idempotent(self):
        storage.set_mastered("Negation", score="10/10")
        for _ in range(3):
            storage.get_progress()
        assert storage.is_mastered("Negation")

    def test_all_tables_exist(self):
        storage.get_progress()
        with sqlite3.connect(storage.DB_FILE) as conn:
            names = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"cards", "reviews", "attempts", "mastery"} <= names


class TestProgressJsonImport:

    def test_imports_legacy_mastery(self, isolated_db):
        with open(storage.PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump({"mastered": {
                "Negation": {"mastered_at": "2026-01-02T03:04:05",
                             "score": "9/10"}}}, f)
        assert storage.is_mastered("Negation")
        assert storage.get_progress()["mastered"]["Negation"]["score"] == "9/10"

    def test_import_does_not_delete_the_file(self, isolated_db):
        # The JSON file is the only backup of pre-migration progress.
        with open(storage.PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump({"mastered": {"Adverbs": {"score": "10/10"}}}, f)
        storage.get_progress()
        assert os.path.exists(storage.PROGRESS_FILE)

    def test_import_runs_only_once(self, isolated_db):
        with open(storage.PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump({"mastered": {"Adverbs": {"score": "10/10"}}}, f)
        storage.get_progress()
        storage.clear_mastered("Adverbs")
        storage.get_progress()          # would re-import if not version-gated
        assert not storage.is_mastered("Adverbs")

    def test_missing_file_is_not_an_error(self, isolated_db):
        assert storage.get_progress() == {"mastered": {}}

    def test_corrupt_file_is_not_an_error(self, isolated_db):
        with open(storage.PROGRESS_FILE, "w", encoding="utf-8") as f:
            f.write("{not json")
        assert storage.get_progress() == {"mastered": {}}

    def test_non_dict_mastered_is_ignored(self, isolated_db):
        with open(storage.PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump({"mastered": ["Negation"]}, f)
        assert storage.get_progress() == {"mastered": {}}


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

class TestTimeHelpers:

    def test_iso_roundtrip(self):
        assert storage.from_iso(storage.to_iso(NOW)) == NOW

    def test_iso_is_fixed_width_so_string_order_is_time_order(self):
        # SQL compares `due` as text; variable-width timestamps would sort wrong.
        stamps = [storage.to_iso(NOW + timedelta(microseconds=i))
                  for i in (0, 1, 1000, 999999)]
        assert len(set(len(s) for s in stamps)) == 1
        assert stamps == sorted(stamps)

    def test_naive_datetime_is_treated_as_utc(self):
        naive = NOW.replace(tzinfo=None)
        assert storage.to_iso(naive) == storage.to_iso(NOW)

    def test_none_passes_through(self):
        assert storage.to_iso(None) is None
        assert storage.from_iso(None) is None


# ---------------------------------------------------------------------------
# Mastery
# ---------------------------------------------------------------------------

class TestMastery:

    def test_unknown_topic_is_not_mastered(self):
        assert storage.is_mastered("Negation") is False

    def test_set_then_read(self):
        storage.set_mastered("Negation", score="9/10")
        assert storage.is_mastered("Negation") is True
        assert storage.get_progress()["mastered"]["Negation"]["score"] == "9/10"

    def test_set_is_idempotent_and_updates_score(self):
        storage.set_mastered("Negation", score="9/10")
        storage.set_mastered("Negation", score="10/10")
        mastered = storage.get_progress()["mastered"]
        assert len(mastered) == 1
        assert mastered["Negation"]["score"] == "10/10"

    def test_clear_removes_it(self):
        storage.set_mastered("Negation", score="9/10")
        storage.clear_mastered("Negation")
        assert storage.is_mastered("Negation") is False

    def test_clear_unknown_topic_is_a_noop(self):
        storage.clear_mastered("Nothing")  # must not raise


# ---------------------------------------------------------------------------
# Attempts
# ---------------------------------------------------------------------------

class TestAttempts:

    def test_empty_by_default(self):
        assert storage.get_attempts() == []

    def test_records_and_returns_newest_first(self):
        storage.record_attempt("Negation", 7, 10, at=NOW - timedelta(days=2))
        storage.record_attempt("Negation", 9, 10, at=NOW)
        scores = [a["score"] for a in storage.get_attempts()]
        assert scores == [9, 7]

    def test_filter_by_topic(self):
        storage.record_attempt("Negation", 7, 10)
        storage.record_attempt("Adverbs", 8, 10)
        assert [a["topic"] for a in storage.get_attempts(topic="Adverbs")] == \
            ["Adverbs"]

    def test_every_attempt_is_kept_not_overwritten(self):
        for score in (5, 6, 7):
            storage.record_attempt("Negation", score, 10)
        assert len(storage.get_attempts()) == 3

    def test_topic_stats_aggregate(self):
        storage.record_attempt("Negation", 5, 10)
        storage.record_attempt("Negation", 9, 10)
        stats = storage.get_topic_stats()["Negation"]
        assert stats["attempts"] == 2
        assert stats["best"] == 9


# ---------------------------------------------------------------------------
# Cards
# ---------------------------------------------------------------------------

class TestCards:

    def test_unknown_card_is_none(self):
        assert storage.get_card("neg_001") is None

    def test_upsert_then_get(self):
        storage.upsert_card("neg_001", "Negation", '{"a":1}', _iso(60),
                            state=1, stability=0.5, difficulty=5.0)
        card = storage.get_card("neg_001")
        assert card["item_id"] == "neg_001"
        assert card["topic"] == "Negation"
        assert json.loads(card["fsrs_json"]) == {"a": 1}

    def test_upsert_replaces_rather_than_duplicates(self):
        storage.upsert_card("neg_001", "Negation", "{}", _iso(60))
        storage.upsert_card("neg_001", "Negation", "{}", _iso(120))
        assert storage.get_card("neg_001")["due"] == _iso(120)
        assert len(storage.get_due_cards(now=NOW + timedelta(seconds=300))) == 1


class TestDueQueries:

    def setup_cards(self):
        storage.upsert_card("neg_001", "Negation", "{}", _iso(-60))   # overdue
        storage.upsert_card("neg_002", "Negation", "{}", _iso(0))     # exactly now
        storage.upsert_card("adv_001", "Adverbs", "{}", _iso(-30))    # overdue
        storage.upsert_card("adv_002", "Adverbs", "{}", _iso(3600))   # future

    def test_only_due_cards_are_returned(self):
        self.setup_cards()
        ids = [c["item_id"] for c in storage.get_due_cards(now=NOW)]
        assert set(ids) == {"neg_001", "neg_002", "adv_001"}

    def test_due_exactly_now_counts_as_due(self):
        self.setup_cards()
        ids = [c["item_id"] for c in storage.get_due_cards(now=NOW)]
        assert "neg_002" in ids

    def test_ordered_soonest_due_first(self):
        self.setup_cards()
        dues = [c["due"] for c in storage.get_due_cards(now=NOW)]
        assert dues == sorted(dues)

    def test_topic_filter(self):
        self.setup_cards()
        ids = [c["item_id"] for c in storage.get_due_cards(topic="Adverbs",
                                                           now=NOW)]
        assert ids == ["adv_001"]

    def test_limit(self):
        self.setup_cards()
        assert len(storage.get_due_cards(limit=2, now=NOW)) == 2

    def test_due_counts_by_topic_omits_empty_topics(self):
        self.setup_cards()
        assert storage.get_due_counts_by_topic(now=NOW) == \
            {"Negation": 2, "Adverbs": 1}

    def test_summary(self):
        self.setup_cards()
        summary = storage.get_srs_summary(now=NOW)
        assert summary["tracked"] == 4
        assert summary["due"] == 3
        assert summary["next_due"] == _iso(3600)

    def test_summary_with_nothing_tracked(self):
        summary = storage.get_srs_summary(now=NOW)
        assert summary == {"tracked": 0, "due": 0, "next_due": None}


# ---------------------------------------------------------------------------
# Review history
# ---------------------------------------------------------------------------

class TestReviewLog:

    def test_counts_start_at_zero(self):
        assert storage.get_review_counts("neg_001") == {"reps": 0, "lapses": 0}

    def test_reps_and_lapses_are_derived_from_history(self):
        # An FSRS Card carries no reps/lapses fields, so the reviews table is
        # the only source for these.
        for tier, rating in (("incorrect", 1), ("exact", 4), ("incorrect", 1),
                             ("variant", 3)):
            storage.log_review("neg_001", tier, rating, topic="Negation")
        assert storage.get_review_counts("neg_001") == {"reps": 4, "lapses": 2}

    def test_history_is_per_item(self):
        storage.log_review("neg_001", "exact", 4)
        storage.log_review("neg_002", "incorrect", 1)
        assert storage.get_review_counts("neg_001")["reps"] == 1


# ---------------------------------------------------------------------------
# Profile isolation — the seam a multi-user build grows through
# ---------------------------------------------------------------------------

class TestProfileIsolation:

    def test_mastery_is_per_profile(self):
        storage.set_mastered("Negation", score="10/10", profile_id="alice")
        assert storage.is_mastered("Negation", profile_id="alice") is True
        assert storage.is_mastered("Negation", profile_id="bob") is False

    def test_cards_are_per_profile(self):
        storage.upsert_card("neg_001", "Negation", "{}", _iso(-60),
                            profile_id="alice")
        assert len(storage.get_due_cards(now=NOW, profile_id="alice")) == 1
        assert storage.get_due_cards(now=NOW, profile_id="bob") == []

    def test_attempts_are_per_profile(self):
        storage.record_attempt("Negation", 9, 10, profile_id="alice")
        assert len(storage.get_attempts(profile_id="alice")) == 1
        assert storage.get_attempts(profile_id="bob") == []

    def test_same_item_id_under_two_profiles_does_not_collide(self):
        storage.upsert_card("neg_001", "Negation", '{"who":"alice"}', _iso(1),
                            profile_id="alice")
        storage.upsert_card("neg_001", "Negation", '{"who":"bob"}', _iso(2),
                            profile_id="bob")
        assert json.loads(storage.get_card("neg_001",
                                           profile_id="alice")["fsrs_json"]) \
            == {"who": "alice"}

    def test_default_profile_is_local(self):
        storage.set_mastered("Negation")
        assert storage.is_mastered("Negation",
                                   profile_id=storage.DEFAULT_PROFILE)


# ---------------------------------------------------------------------------
# Durability
# ---------------------------------------------------------------------------

class TestDurability:

    def test_data_survives_a_fresh_connection(self):
        storage.set_mastered("Negation", score="10/10")
        storage.upsert_card("neg_001", "Negation", "{}", _iso(-1))
        # Every public call opens and closes its own connection, so this is
        # already a reopen; assert explicitly that the bytes are on disk.
        assert storage.is_mastered("Negation")
        assert len(storage.get_due_cards(now=NOW)) == 1

    def test_writes_are_transactional(self, monkeypatch):
        storage.set_mastered("Negation", score="9/10")
        original = storage._migrate

        def boom(conn):
            original(conn)
            raise RuntimeError("simulated crash mid-write")

        monkeypatch.setattr(storage, "_migrate", boom)
        with pytest.raises(RuntimeError):
            storage.set_mastered("Adverbs", score="10/10")
        monkeypatch.setattr(storage, "_migrate", original)
        # The earlier record is intact and the failed one left no partial row.
        assert storage.is_mastered("Negation") is True
        assert storage.is_mastered("Adverbs") is False
