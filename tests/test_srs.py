"""
Layer 1 — FSRS scheduling tests for srs.py.

Pure and offline: srs.py imports neither Streamlit, config, storage nor logic,
so these tests exercise the scheduler directly with an injected clock.
"""
import json
from datetime import datetime, timedelta, timezone

import pytest

from fsrs import Rating

import srs


NOW = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)


def _drill(tier, times, start=None):
    """Answer the same item `times` times at `tier`, always exactly when due."""
    state, now = None, start or NOW
    for _ in range(times):
        result = srs.review(state, tier, now=now)
        state, now = result["fsrs_json"], result["due"]
    return result


# ---------------------------------------------------------------------------
# Tier → rating
# ---------------------------------------------------------------------------

class TestTierMapping:

    def test_exact_map(self):
        assert srs.TIER_TO_RATING == {
            "incorrect": Rating.Again,
            "accepted": Rating.Hard,
            "variant": Rating.Good,
            "exact": Rating.Easy,
        }

    def test_covers_every_tier_the_quiz_produces(self):
        # classify_answer yields exact/variant/incorrect; the quiz UI promotes
        # an LLM-rescued answer to "accepted".
        assert set(srs.TIER_TO_RATING) == {
            "exact", "variant", "accepted", "incorrect"}

    @pytest.mark.parametrize("tier,value", [
        ("incorrect", 1), ("accepted", 2), ("variant", 3), ("exact", 4)])
    def test_rating_values(self, tier, value):
        assert int(srs.rating_for_tier(tier)) == value

    def test_accepted_is_rated_below_variant(self):
        # Needing the LLM judge to vouch for a phrasing is weaker evidence of
        # recall than matching a form the bank already lists.
        assert int(srs.rating_for_tier("accepted")) < \
            int(srs.rating_for_tier("variant"))

    @pytest.mark.parametrize("bad", ["", None, "correct", "Exact", "skipped"])
    def test_unknown_tier_raises(self, bad):
        with pytest.raises(KeyError):
            srs.rating_for_tier(bad)

    def test_review_rejects_unknown_tier(self):
        with pytest.raises(KeyError):
            srs.review(None, "bogus", now=NOW)


# ---------------------------------------------------------------------------
# Scheduling behavior
# ---------------------------------------------------------------------------

class TestScheduling:

    def test_new_item_is_scheduled_into_the_future(self):
        result = srs.review(None, "exact", now=NOW)
        assert result["due"] > NOW

    def test_returns_every_field_storage_needs(self):
        result = srs.review(None, "exact", now=NOW)
        assert set(result) >= {"fsrs_json", "due", "state", "stability",
                               "difficulty", "last_review", "rating"}

    def test_rating_is_reported_for_the_review_log(self):
        assert srs.review(None, "incorrect", now=NOW)["rating"] == 1

    def test_miss_reschedules_sooner_than_a_correct_answer(self):
        miss = srs.review(None, "incorrect", now=NOW)["due"]
        hit = srs.review(None, "exact", now=NOW)["due"]
        assert miss < hit

    def test_repeated_success_lengthens_intervals_monotonically(self):
        state, now, gaps = None, NOW, []
        for _ in range(6):
            result = srs.review(state, "exact", now=now)
            gaps.append(result["due"] - now)
            state, now = result["fsrs_json"], result["due"]
        assert gaps == sorted(gaps), gaps
        assert gaps[-1] > timedelta(days=7)

    def test_a_lapse_shortens_a_long_interval(self):
        mature = _drill("exact", 5)
        lapsed = srs.review(mature["fsrs_json"], "incorrect",
                            now=mature["due"])
        long_gap = mature["due"] - _drill("exact", 4)["due"]
        assert (lapsed["due"] - mature["due"]) < long_gap

    def test_missed_item_comes_back_within_the_hour(self):
        # The point of the feature: a miss must be re-drilled soon, not filed
        # away for a week.
        result = srs.review(None, "incorrect", now=NOW)
        assert result["due"] - NOW <= timedelta(hours=1)

    def test_easier_rating_never_schedules_sooner(self):
        dues = [srs.review(None, tier, now=NOW)["due"]
                for tier in ("incorrect", "accepted", "variant", "exact")]
        assert dues == sorted(dues)


# ---------------------------------------------------------------------------
# Serialization — the contract with the cards table
# ---------------------------------------------------------------------------

class TestSerialization:

    def test_fsrs_json_is_a_json_string(self):
        data = json.loads(srs.review(None, "exact", now=NOW)["fsrs_json"])
        assert isinstance(data, dict)
        assert "due" in data and "stability" in data

    def test_roundtrip_preserves_schedule(self):
        first = srs.review(None, "exact", now=NOW)
        reloaded = srs.load_card(first["fsrs_json"])
        assert reloaded.due == first["due"]

    def test_history_is_carried_across_a_reload(self):
        # Two reviews through a serialize/deserialize cycle must schedule the
        # same as two reviews in memory.
        a = srs.review(None, "exact", now=NOW)
        b = srs.review(a["fsrs_json"], "exact", now=a["due"])
        assert b["stability"] > a["stability"]

    def test_empty_state_starts_a_new_card(self):
        for empty in (None, ""):
            assert srs.review(empty, "exact", now=NOW)["due"] > NOW

    def test_last_review_is_the_review_time(self):
        assert srs.review(None, "exact", now=NOW)["last_review"] == NOW


# ---------------------------------------------------------------------------
# Time handling
# ---------------------------------------------------------------------------

class TestTimeHandling:

    def test_due_is_timezone_aware_utc(self):
        due = srs.review(None, "exact", now=NOW)["due"]
        assert due.tzinfo is not None
        assert due.utcoffset() == timedelta(0)

    def test_naive_now_is_treated_as_utc(self):
        aware = srs.review(None, "exact", now=NOW)["due"]
        naive = srs.review(None, "exact", now=NOW.replace(tzinfo=None))["due"]
        assert aware == naive

    def test_is_due_respects_the_clock(self):
        state = srs.review(None, "exact", now=NOW)
        assert srs.is_due(state["fsrs_json"], now=NOW) is False
        assert srs.is_due(state["fsrs_json"], now=state["due"]) is True

    def test_a_brand_new_card_is_due_immediately(self):
        assert srs.is_due(None, now=NOW) is True


class TestSchedulerConfig:

    def test_fuzzing_is_disabled_so_scheduling_is_reproducible(self):
        # With fuzzing on, FSRS randomizes each interval and the same answer at
        # the same moment yields a different due date on every call.
        assert srs.ENABLE_FUZZING is False
        dues = {srs.review(None, "exact", now=NOW)["due"] for _ in range(20)}
        assert len(dues) == 1

    def test_scheduler_is_reused(self):
        assert srs.get_scheduler() is srs.get_scheduler()

    def test_module_is_free_of_ui_and_storage_imports(self):
        # srs.py must stay importable without Streamlit; config imports it.
        import ast
        with open(srs.__file__, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        assert not imported & {"streamlit", "config", "storage", "logic"}
