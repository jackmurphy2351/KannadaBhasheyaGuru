"""
Layer 1/2 — Deterministic Mastery Quiz tests (no live API calls).

Strategy:
  - Bank loading/validation: hit the pure helpers (_validate_quiz_bank,
    _load_quiz_bank_from_disk) directly — no Streamlit involved.
  - build_quiz / get_quiz_topics: seed st.session_state["quiz_bank"] with a
    tiny synthetic bank. Streamlit's bare-mode session_state is process-global,
    so the fixture MUST pop the key on teardown to avoid cross-test pollution.
  - explain_mistake: mock logic.generate_content (same convention as
    test_sarvam_chat.py) and point logic.QUIZ_ERROR_LOG at tmp_path.
  - Bank integrity: parametrized over every item of the real bank.
"""
import ast
import glob
import json
import os
import re
import unicodedata
from unittest.mock import patch

import pytest
import streamlit as st

import config
import logic
import storage
from logic import (
    build_quiz,
    check_answer,
    classify_answer,
    explain_mistake,
    get_quiz_topics,
    judge_equivalence,
    load_quiz_bank,
    normalize_answer,
)

# The real bank, loaded once at collection time for parametrization.
BANK = logic._load_quiz_bank_from_disk()
ITEMS = {it["id"]: it for it in BANK["items"]}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_fake_bank():
    """Tiny valid 2-topic bank for sampling/topic tests."""
    items = []
    for i, diff in enumerate(["easy", "easy", "medium", "medium", "hard"]):
        items.append({
            "id": f"a_{i}",
            "topic": "Topic A",
            "english": f"Sentence {i}.",
            "canonical": f"ಕನ್ನಡ {i}.",
            "acceptable": [f"ಕನ್ನಡ {i}.", f"ಕನ್ನಡ ರೂಪ {i}."],
            "difficulty": diff,
            "grammar_note": f"note {i}",
        })
    items.append({
        "id": "b_0",
        "topic": "Topic B",
        "english": "Other sentence.",
        "canonical": "ಬೇರೆ.",
        "acceptable": ["ಬೇರೆ."],
        "difficulty": "easy",
        "grammar_note": "note b",
    })
    return {"schema_version": 1, "topics": ["Topic A", "Topic B"], "items": items}


@pytest.fixture
def fake_bank():
    return _make_fake_bank()


@pytest.fixture
def seeded_session(fake_bank):
    """Pre-seed the session cache with the fake bank; always clean up."""
    st.session_state["quiz_bank"] = fake_bank
    yield fake_bank
    st.session_state.pop("quiz_bank", None)


@pytest.fixture
def quiz_log(tmp_path, monkeypatch):
    """Redirect the quiz error log to a temp file."""
    log_path = tmp_path / "quiz_errors.log"
    monkeypatch.setattr(logic, "QUIZ_ERROR_LOG", str(log_path))
    return log_path


# ===========================================================================
# Bank integrity (real bank)
# ===========================================================================

class TestBankIntegrity:

    def test_bank_has_200_items(self):
        assert len(BANK["items"]) == 200

    def test_bank_has_12_topics(self):
        assert len(BANK["topics"]) == 12

    def test_every_topic_has_at_least_10_items(self):
        for topic in BANK["topics"]:
            pool = [it for it in BANK["items"] if it["topic"] == topic]
            assert len(pool) >= 10, topic

    @pytest.mark.parametrize("item", BANK["items"], ids=lambda it: it["id"])
    def test_canonical_is_first_acceptable_and_self_passes(self, item):
        assert item["canonical"] == item["acceptable"][0]
        assert check_answer(item["canonical"], item) is True

    @pytest.mark.parametrize("item", BANK["items"], ids=lambda it: it["id"])
    def test_every_acceptable_form_passes(self, item):
        for form in item["acceptable"]:
            assert check_answer(form, item) is True

    def test_at_most_two_items_per_topic_overlap_lesson_docs(self):
        # Quiz sentences must test the learner beyond the lesson material:
        # at most 2 canonical answers per topic may appear verbatim in the
        # knowledge_base markdown.
        def squash(s):
            s = unicodedata.normalize("NFC", s)
            s = re.sub("[\"“”.!?,;:।॥]", "", s)
            return " ".join(s.split())

        docs = " ".join(
            open(p, encoding="utf-8").read()
            for p in glob.glob(os.path.join(config.KNOWLEDGE_DIR, "*.md")))
        docs = squash(docs)
        for topic in BANK["topics"]:
            hits = [it["id"] for it in BANK["items"]
                    if it["topic"] == topic and squash(it["canonical"]) in docs]
            assert len(hits) <= 2, f"{topic}: lesson-copied items {hits}"

    def test_no_duplicate_canonicals_across_bank(self):
        seen = {}
        for it in BANK["items"]:
            key = normalize_answer(it["canonical"])
            assert key not in seen, f"{it['id']} duplicates {seen.get(key)}"
            seen[key] = it["id"]


# ===========================================================================
# _validate_quiz_bank
# ===========================================================================

class TestValidateQuizBank:

    def test_valid_bank_passes_through(self, fake_bank):
        assert logic._validate_quiz_bank(fake_bank) is fake_bank

    def test_duplicate_id_raises(self, fake_bank):
        fake_bank["items"][1]["id"] = "a_0"
        with pytest.raises(ValueError, match="a_0"):
            logic._validate_quiz_bank(fake_bank)

    def test_missing_id_raises(self, fake_bank):
        del fake_bank["items"][0]["id"]
        with pytest.raises(ValueError, match="missing or duplicate"):
            logic._validate_quiz_bank(fake_bank)

    def test_empty_acceptable_raises(self, fake_bank):
        fake_bank["items"][2]["acceptable"] = []
        with pytest.raises(ValueError, match="a_2"):
            logic._validate_quiz_bank(fake_bank)

    def test_canonical_not_first_acceptable_raises(self, fake_bank):
        fake_bank["items"][3]["canonical"] = "ತಪ್ಪು."
        with pytest.raises(ValueError, match="a_3"):
            logic._validate_quiz_bank(fake_bank)

    def test_unknown_topic_raises(self, fake_bank):
        fake_bank["items"][4]["topic"] = "Nonexistent Topic"
        with pytest.raises(ValueError, match="a_4"):
            logic._validate_quiz_bank(fake_bank)


# ===========================================================================
# normalize_answer
# ===========================================================================

class TestNormalizeAnswer:

    def test_strips_zwnj_and_zwj(self):
        zw = "ಇಷ್ಟ\u200cವಿಲ್ಲ\u200d"  # ZWNJ mid-word, ZWJ trailing
        assert normalize_answer(zw) == normalize_answer("ಇಷ್ಟವಿಲ್ಲ")

    def test_period_and_danda_equivalent(self):
        assert normalize_answer("ಅವನು ಬರುವುದಿಲ್ಲ.") == normalize_answer("ಅವನು ಬರುವುದಿಲ್ಲ।")

    def test_strips_all_listed_punctuation(self):
        assert normalize_answer("ಹೌದು!?,;:॥") == "ಹೌದು"

    def test_collapses_whitespace(self):
        assert normalize_answer("  ನಾನು \t ಮನೆಗೆ\n ಹೋಗುತ್ತೇನೆ ") == "ನಾನು ಮನೆಗೆ ಹೋಗುತ್ತೇನೆ"

    def test_applies_nfc_normalization(self):
        # NFD decomposed 'é' must equal precomposed 'é' after NFC.
        assert normalize_answer("é") == normalize_answer("é")

    def test_empty_and_none_return_empty_string(self):
        assert normalize_answer("") == ""
        assert normalize_answer(None) == ""

    def test_quotation_marks_are_ignored(self):
        # Missing or different quote styles must never fail an answer.
        with_quotes = 'ರಾಹುಲ್ "ನಾನು ಬರುತ್ತೇನೆ" ಅಂತ ಹೇಳಿದ.'
        curly = "ರಾಹುಲ್ “ನಾನು ಬರುತ್ತೇನೆ” ಅಂತ ಹೇಳಿದ."
        without = "ರಾಹುಲ್ ನಾನು ಬರುತ್ತೇನೆ ಅಂತ ಹೇಳಿದ."
        assert normalize_answer(with_quotes) == normalize_answer(without)
        assert normalize_answer(curly) == normalize_answer(without)

    def test_quotative_variants_fold_together(self):
        # ಅಂತ / ಅಂತಾ / ಎಂದು are interchangeable quotatives.
        base = normalize_answer("ಅವಳು ಇಲ್ಲ ಅಂತ ಹೇಳಿದಳು.")
        assert normalize_answer("ಅವಳು ಇಲ್ಲ ಅಂತಾ ಹೇಳಿದಳು.") == base
        assert normalize_answer("ಅವಳು ಇಲ್ಲ ಎಂದು ಹೇಳಿದಳು.") == base

    def test_hearsay_ante_is_not_folded(self):
        # ಅಂತೆ means "apparently" (hearsay) — folding it into ಅಂತ would
        # collapse a real meaning distinction.
        assert "ಅಂತೆ" in normalize_answer("ಅವನು ಹೋದ ಅಂತೆ.")

    def test_emba_is_not_folded(self):
        # ಎಂಬ is naming-only (literary, for proper nouns) and is never a
        # reported-speech quotative — it must NOT fold into ಅಂತ.
        assert "ಎಂಬ" in normalize_answer('"ಪರ್ವ" ಎಂಬ ಕಾದಂಬರಿ.')
        assert (normalize_answer("ಪರ್ವ ಎಂಬ ಕಾದಂಬರಿ")
                != normalize_answer("ಪರ್ವ ಅಂತ ಕಾದಂಬರಿ"))

    def test_embudu_is_not_folded(self):
        # The nominalised ಎಂಬುದು is its own token and likewise untouched.
        assert "ಎಂಬುದು" in normalize_answer("ಅದು ನಿಜ ಎಂಬುದು ಸ್ಪಷ್ಟ.")

    def test_fused_sandhi_tokens_are_not_split(self):
        # Fused quotative sandhi (ಚೆನ್ನಾಗಿದೆ+ಅಂತ -> ಚೆನ್ನಾಗಿದೆಯಂತ) stays a
        # single token: accepting it is judge_equivalence's job, because
        # ವಂತ-final words (ಗುಣವಂತ, ಬಲವಂತ) make suffix splitting unsafe.
        assert "ಚೆನ್ನಾಗಿದೆಯಂತ" in normalize_answer("ಇದು ಚೆನ್ನಾಗಿದೆಯಂತ ಅನಿಸುತ್ತೆ.")


# ===========================================================================
# check_answer / classify_answer (regression cases from the grading bugs)
# ===========================================================================

class TestCheckAnswer:

    def test_neg_003_laundered_error_rejected(self):
        # 'ishta' must be negated with illa, not alla — this exact string was
        # previously marked correct AND echoed back as the standard form.
        assert check_answer("ನನಗೆ ಕಾಫಿ ಇಷ್ಟವಲ್ಲ", ITEMS["neg_003"]) is False

    def test_neg_006_wrong_past_negative_rejected(self):
        # 'hodalla' is not a valid past negative of hogu (should be hogalilla).
        assert check_answer("ನಾವು ನೆನ್ನೆ ಪಾರ್ಕಿಗೆ ಹೋದಲ್ಲ", ITEMS["neg_006"]) is False

    def test_neg_004_correct_answer_accepted(self):
        assert check_answer("ಅವನು ನಾಳೆ ಬರುವುದಿಲ್ಲ", ITEMS["neg_004"]) is True

    def test_neg_003_alternative_form_accepted(self):
        assert check_answer("ನನಗೆ ಕಾಫಿ ಇಷ್ಟ ಇಲ್ಲ", ITEMS["neg_003"]) is True

    def test_punctuation_difference_still_passes(self):
        assert check_answer("ನನಗೆ ಕಾಫಿ ಇಷ್ಟವಿಲ್ಲ", ITEMS["neg_003"]) is True


class TestScreenshotRegressions:
    """Exact user answers from the 2026-06-10 quiz screenshots, replayed
    against items mirroring the old bank entries that wrongly failed them."""

    @staticmethod
    def _item(canonical, *extra):
        return {"id": "shot", "english": "-", "canonical": canonical,
                "acceptable": [canonical, *extra],
                "difficulty": "easy", "grammar_note": "-"}

    def test_q1_added_quotes_accepted(self):
        item = self._item("ಅವಳು ಇಲ್ಲ ಅಂತ ಹೇಳಿದಳು.")
        assert classify_answer("ಅವಳು “ಇಲ್ಲ” ಅಂತ ಹೇಳಿದಳು.", item) == "exact"

    def test_q10_missing_quotes_accepted(self):
        item = self._item('"ಪರ್ವ" ಎಂಬ ಕಾದಂಬರಿ.')
        assert classify_answer("ಪರ್ವ ಎಂಬ ಕಾದಂಬರಿ", item) == "exact"

    def test_q2_emba_for_anta_goes_to_judge(self):
        # ಎಂಬ is a literary form used ONLY for naming proper nouns — never a
        # reported-speech quotative — so it must NOT auto-fold with ಅಂತ.
        # In a naming context like this it may still be acceptable, but only
        # the constrained judge decides; the deterministic layer says no.
        item = self._item("ಮೈಸೂರು ಪಾಕ್ ಅಂತ ಸ್ವೀಟ್.")
        assert classify_answer("ಮೈಸೂರು ಪಾಕ್ ಎಂಬ ಸ್ವೀಟ್", item) == "incorrect"
        good = json.dumps({"equivalent": True, "reason": "naming context"})
        with patch("logic.generate_content", return_value=good):
            assert judge_equivalence(
                "ಮೈಸೂರು ಪಾಕ್ ಎಂಬ ಸ್ವೀಟ್", item, "ctx") is True

    def test_anta_for_emba_goes_to_judge(self):
        # Mirror image: an ಅಂತ answer against an ಎಂಬ canonical is likewise
        # never an automatic match — it falls through to judge_equivalence.
        item = self._item('"ಕಾಂತಾರ" ಎಂಬ ಸಿನಿಮಾ.')
        assert classify_answer("ಕಾಂತಾರ ಅಂತ ಸಿನಿಮಾ", item) == "incorrect"

    def test_q5_fused_sandhi_goes_to_judge(self):
        # Deterministic layer must still say incorrect — the lenient accept
        # happens in judge_equivalence, whose prompt whitelists sandhi.
        item = self._item("ಇದು ಚೆನ್ನಾಗಿದೆ ಅಂತ ನನಗೆ ಅನಿಸುತ್ತೆ.",
                          "ಇದು ಚೆನ್ನಾಗಿದೆ ಅಂತ ನನಗೆ ಅನಿಸುತ್ತದೆ.")
        assert classify_answer(
            "ಇದು ಚೆನ್ನಾಗಿದೆಯಂತ ನನಗೆ ಅನಿಸುತ್ತದೆ.", item) == "incorrect"
        good = json.dumps({"equivalent": True, "reason": "sandhi variant"})
        with patch("logic.generate_content", return_value=good) as mock_gen:
            assert judge_equivalence(
                "ಇದು ಚೆನ್ನಾಗಿದೆಯಂತ ನನಗೆ ಅನಿಸುತ್ತದೆ.", item, "ctx") is True
        assert "sandhi" in mock_gen.call_args.args[0]


class TestClassifyAnswer:

    def test_canonical_is_exact(self):
        item = ITEMS["neg_003"]
        assert classify_answer(item["canonical"], item) == "exact"

    def test_alternative_acceptable_is_variant(self):
        assert classify_answer("ನನಗೆ ಕಾಫಿ ಇಷ್ಟ ಇಲ್ಲ", ITEMS["neg_003"]) == "variant"

    def test_wrong_answer_is_incorrect(self):
        assert classify_answer("ನನಗೆ ಕಾಫಿ ಇಷ್ಟವಲ್ಲ", ITEMS["neg_003"]) == "incorrect"


# ===========================================================================
# build_quiz
# ===========================================================================

class TestBuildQuiz:

    def test_same_seed_is_reproducible(self, seeded_session):
        assert build_quiz("Topic A", n=3, seed=42) == build_quiz("Topic A", n=3, seed=42)

    def test_returns_at_most_n_unique_items(self, seeded_session):
        quiz = build_quiz("Topic A", n=3, seed=1)
        assert len(quiz) == 3
        assert len({it["id"] for it in quiz}) == 3

    def test_all_items_from_requested_topic(self, seeded_session):
        quiz = build_quiz("Topic A", n=5, seed=1)
        assert all(it["topic"] == "Topic A" for it in quiz)

    def test_difficulty_is_non_decreasing(self, seeded_session):
        quiz = build_quiz("Topic A", n=5, seed=7)
        ranks = [logic._DIFFICULTY_ORDER[it["difficulty"]] for it in quiz]
        assert ranks == sorted(ranks)

    def test_small_topic_returns_whole_pool(self, seeded_session):
        quiz = build_quiz("Topic B", n=10, seed=1)
        assert len(quiz) == 1

    def test_unknown_topic_raises(self, seeded_session):
        with pytest.raises(ValueError, match="No quiz items"):
            build_quiz("Nope")

    def test_real_bank_difficulty_ramp(self):
        st.session_state["quiz_bank"] = BANK
        try:
            quiz = build_quiz("Negation", n=10, seed=3)
            ranks = [logic._DIFFICULTY_ORDER[it["difficulty"]] for it in quiz]
            assert len(quiz) == 10
            assert ranks == sorted(ranks)
        finally:
            st.session_state.pop("quiz_bank", None)


# ===========================================================================
# load_quiz_bank / get_quiz_topics
# ===========================================================================

class TestLoadQuizBank:

    def test_loads_from_disk_once_and_caches(self, fake_bank):
        st.session_state.pop("quiz_bank", None)
        try:
            with patch("logic._load_quiz_bank_from_disk",
                       return_value=fake_bank) as mock_load:
                assert load_quiz_bank() is fake_bank
                assert load_quiz_bank() is fake_bank
            mock_load.assert_called_once()
        finally:
            st.session_state.pop("quiz_bank", None)


class TestGetQuizTopics:

    REAL_DOCS_SUBSET = {
        "Topic A": {"files": ["a.md"], "level": "Core"},
        "Topic B": {"files": ["b.md"], "level": "Advanced"},
    }

    def test_topics_come_from_bank(self, seeded_session, monkeypatch):
        monkeypatch.setattr(config, "QUIZ_TOPIC_DOCS", self.REAL_DOCS_SUBSET)
        with patch("logic.storage.is_mastered", return_value=False):
            topics = get_quiz_topics()
        assert [t["name"] for t in topics] == ["Topic A", "Topic B"]  # Core first

    def test_topic_dict_shape(self, seeded_session, monkeypatch):
        monkeypatch.setattr(config, "QUIZ_TOPIC_DOCS", self.REAL_DOCS_SUBSET)
        with patch("logic.storage.is_mastered", return_value=True):
            t = get_quiz_topics()[0]
        assert t == {"name": "Topic A", "file": ["a.md"],
                     "level": "Core", "mastered": True}

    def test_out_of_sync_mapping_raises(self, seeded_session, monkeypatch):
        monkeypatch.setattr(config, "QUIZ_TOPIC_DOCS",
                            {"Topic A": {"files": ["a.md"], "level": "Core"}})
        with pytest.raises(ValueError, match="out of sync"):
            get_quiz_topics()

    def test_real_mapping_matches_real_bank(self):
        # The shipped config must map exactly the bank's 12 topics.
        assert set(config.QUIZ_TOPIC_DOCS) == set(BANK["topics"])


# ===========================================================================
# UI ↔ backend contract: every module attribute main.py references must
# exist. Guards against AttributeError crashes mid-quiz (e.g. main.py
# calling a logic function that was renamed or never defined).
# ===========================================================================

class TestMainModuleContract:

    MODULES = {"logic": logic, "config": config, "storage": storage}

    def test_main_py_references_only_existing_attributes(self):
        main_path = os.path.join(
            os.path.dirname(os.path.abspath(logic.__file__)), "main.py")
        with open(main_path, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        missing = [
            f"{node.value.id}.{node.attr} (main.py:{node.lineno})"
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id in self.MODULES
            and not hasattr(self.MODULES[node.value.id], node.attr)
        ]
        assert not missing, f"main.py references undefined attributes: {missing}"


# ===========================================================================
# Grading permutations over the ENTIRE bank — every topic, every item.
# A learner must never be failed for punctuation, quoting style,
# quotative register, or stray whitespace, on any question.
# ===========================================================================

class TestAllItemsGradingPermutations:

    @pytest.mark.parametrize("item", BANK["items"], ids=lambda it: it["id"])
    def test_surface_permutations_of_canonical_still_pass(self, item):
        can = item["canonical"]
        permutations = [
            can.rstrip(".!?"),                       # no final punctuation
            f'"{can}"',                              # quote-wrapped
            can.replace("ಅಂತ ", "ಎಂದು "),            # literary quotative
            can.replace("ಅಂತ ", "ಅಂತಾ "),            # lengthened quotative
            "  " + can.replace(" ", "  ") + "  ",    # whitespace noise
        ]
        for p in permutations:
            assert check_answer(p, item) is True, repr(p)

    @pytest.mark.parametrize("item", BANK["items"], ids=lambda it: it["id"])
    def test_unrelated_answer_never_passes(self, item):
        assert check_answer("ಸಂಪೂರ್ಣ ತಪ್ಪಾದ ಉತ್ತರ ಇದು", item) is False

    def test_full_quiz_builds_and_grades_for_every_topic(self):
        st.session_state["quiz_bank"] = BANK
        try:
            for topic in BANK["topics"]:
                quiz = build_quiz(topic, n=10, seed=11)
                assert len(quiz) == 10, topic
                ranks = [logic._DIFFICULTY_ORDER[it["difficulty"]] for it in quiz]
                assert ranks == sorted(ranks), topic
                for it in quiz:
                    assert classify_answer(it["canonical"], it) == "exact"
        finally:
            st.session_state.pop("quiz_bank", None)


# ===========================================================================
# judge_equivalence (constrained LLM fallback for non-matching answers)
# ===========================================================================

class TestJudgeEquivalence:

    ITEM = ITEMS["neg_003"]
    ANSWER = "ನನಗೆ ಕಾಫಿ ಅಂದರೆ ಇಷ್ಟ ಇಲ್ಲ"

    def test_true_verdict_accepted(self, quiz_log):
        good = json.dumps({"equivalent": True, "reason": "valid variant"})
        with patch("logic.generate_content", return_value=good) as mock_gen:
            assert judge_equivalence(self.ANSWER, self.ITEM, "ctx") is True
        assert mock_gen.call_count == 1

    def test_false_verdict_rejected(self, quiz_log):
        bad = json.dumps({"equivalent": False, "reason": "wrong meaning"})
        with patch("logic.generate_content", return_value=bad):
            assert judge_equivalence(self.ANSWER, self.ITEM, "ctx") is False

    def test_non_boolean_verdict_retries_then_fails_closed(self, quiz_log):
        # A malformed verdict must never count as acceptance.
        junk = json.dumps({"equivalent": "yes"})
        with patch("logic.generate_content",
                   side_effect=[junk, junk]) as mock_gen:
            assert judge_equivalence(self.ANSWER, self.ITEM, "ctx") is False
        assert mock_gen.call_count == 2
        assert quiz_log.exists()

    def test_api_error_fails_closed_and_logs(self, quiz_log):
        with patch("logic.generate_content",
                   side_effect=["API Error: boom", "API Error: boom"]):
            assert judge_equivalence(self.ANSWER, self.ITEM, "ctx") is False
        entry = json.loads(quiz_log.read_text(encoding="utf-8").strip())
        assert entry["item_id"] == "neg_003"

    def test_exception_does_not_propagate(self, quiz_log):
        with patch("logic.generate_content", side_effect=Exception("down")):
            assert judge_equivalence(self.ANSWER, self.ITEM, "ctx") is False

    def test_empty_answer_short_circuits_without_llm(self, quiz_log):
        with patch("logic.generate_content") as mock_gen:
            assert judge_equivalence("", self.ITEM, "ctx") is False
            assert judge_equivalence('"?!"', self.ITEM, "ctx") is False
        mock_gen.assert_not_called()

    def test_prompt_contains_ground_truth(self, quiz_log):
        good = json.dumps({"equivalent": True, "reason": "ok"})
        with patch("logic.generate_content", return_value=good) as mock_gen:
            judge_equivalence(self.ANSWER, self.ITEM, "ctx")
        prompt = mock_gen.call_args.args[0]
        assert self.ITEM["canonical"] in prompt
        assert self.ITEM["english"] in prompt
        assert self.ANSWER in prompt


# ===========================================================================
# explain_mistake
# ===========================================================================

class TestExplainMistake:

    ITEM = ITEMS["neg_003"]
    WRONG = "ನನಗೆ ಕಾಫಿ ಇಷ್ಟವಲ್ಲ"
    GOOD = json.dumps({"feedback": "alla negates identity; use illa here."})

    def test_returns_feedback_on_first_try(self, quiz_log):
        with patch("logic.generate_content", return_value=self.GOOD) as mock_gen:
            res = explain_mistake(self.WRONG, self.ITEM, "ctx")
        assert res == {"feedback": "alla negates identity; use illa here."}
        assert mock_gen.call_count == 1

    def test_retries_once_on_empty_response(self, quiz_log):
        with patch("logic.generate_content",
                   side_effect=["", self.GOOD]) as mock_gen:
            res = explain_mistake(self.WRONG, self.ITEM, "ctx")
        assert mock_gen.call_count == 2
        assert "illa" in res["feedback"]

    def test_api_error_string_treated_as_failure(self, quiz_log):
        with patch("logic.generate_content",
                   side_effect=["API Error: boom", self.GOOD]) as mock_gen:
            res = explain_mistake(self.WRONG, self.ITEM, "ctx")
        assert mock_gen.call_count == 2
        assert "illa" in res["feedback"]

    def test_double_failure_returns_friendly_fallback_and_logs(self, quiz_log):
        with patch("logic.generate_content",
                   side_effect=["NOT JSON", "API Error: boom"]):
            res = explain_mistake(self.WRONG, self.ITEM, "ctx")
        # Fallback cites the item's own grammar note, never AI Error/Unknown.
        assert self.ITEM["grammar_note"] in res["feedback"]
        assert "AI Error" not in res["feedback"]
        assert "Unknown" not in res["feedback"]
        # One JSON log line with id, answer, and raw model output.
        entry = json.loads(quiz_log.read_text(encoding="utf-8").strip())
        assert entry["item_id"] == "neg_003"
        assert entry["user_answer"] == self.WRONG
        assert entry["raw_output"] == "API Error: boom"

    def test_exception_does_not_propagate(self, quiz_log):
        with patch("logic.generate_content", side_effect=Exception("net down")):
            res = explain_mistake(self.WRONG, self.ITEM, "ctx")
        assert self.ITEM["grammar_note"] in res["feedback"]
        entry = json.loads(quiz_log.read_text(encoding="utf-8").strip())
        assert "net down" in entry["exception"]

    def test_prompt_contains_canonical_and_grammar_note(self, quiz_log):
        with patch("logic.generate_content", return_value=self.GOOD) as mock_gen:
            explain_mistake(self.WRONG, self.ITEM, "ctx")
        prompt = mock_gen.call_args.args[0]
        assert self.ITEM["canonical"] in prompt
        assert self.ITEM["grammar_note"] in prompt
        assert self.WRONG in prompt


# ===========================================================================
# Verbatim answer passing — the user's exact text (however messy) must reach
# the LLM prompt unaltered. Past bugs involved the model "correcting" text
# the user never wrote; the first defence is proving we never mutate input.
# ===========================================================================

ADVERSARIAL_ANSWERS = [
    'ಅವಳು "ಇಲ್ಲ" ಅಂತ ಹೇಳಿದಳು yesterday',          # straight quotes + English
    "it's {not} JSON: {\"kannada\": \"fake\"}",      # braces + JSON-like text
    "ನನಗೆ ಕಾಫಿ\nಇಷ್ಟ ಇಲ್ಲ\tnow",                    # newline + tab
    "back\\slash ಮತ್ತು ```json fence```",            # backslash + md fence
    "ನಾನು ‘ಬರ್ತೀನಿ’ — okay? 😅",                    # curly quotes + emoji
]


class TestVerbatimAnswerPassing:

    ITEM = ITEMS["neg_003"]

    @pytest.mark.parametrize("ans", ADVERSARIAL_ANSWERS)
    def test_judge_equivalence_receives_exact_answer(self, ans, quiz_log):
        verdict = json.dumps({"equivalent": False, "reason": "no"})
        with patch("logic.generate_content", return_value=verdict) as mock_gen:
            judge_equivalence(ans, self.ITEM, "ctx")
        assert ans in mock_gen.call_args.args[0]

    @pytest.mark.parametrize("ans", ADVERSARIAL_ANSWERS)
    def test_explain_mistake_receives_exact_answer(self, ans, quiz_log):
        good = json.dumps({"feedback": "ok"})
        with patch("logic.generate_content", return_value=good) as mock_gen:
            explain_mistake(ans, self.ITEM, "ctx")
        assert ans in mock_gen.call_args.args[0]
