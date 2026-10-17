"""
Learning tracks: learner.py (pure), its contract with config, and the logic.py
seams that consume it — prompt injection, Roman-script answers, placement.
"""
import itertools
import json
import os
from unittest.mock import MagicMock, patch

import pytest
import streamlit as st

import config
import learner
import logic
from learner import LearnerProfile


def _profile(level="intermediate", motivation="work", reads_script=True):
    return LearnerProfile(level, motivation, reads_script)


ALL_PROFILES = [
    LearnerProfile(lvl, mot, rs) for lvl, mot, rs in itertools.product(
        learner.LEVELS, learner.MOTIVATIONS, (True, False))]


# ===========================================================================
# prompt_block
# ===========================================================================

class TestPromptBlock:

    @pytest.mark.parametrize("p", ALL_PROFILES,
                             ids=lambda p: f"{p.level}-{p.motivation}-{p.reads_script}")
    def test_every_combination_names_level_target_and_motivation(self, p):
        block = learner.prompt_block(p)
        assert block.startswith("## Student Profile (The User)")
        assert f"CEFR {learner.LEVELS[p.level]['target_cefr']}" in block
        assert learner.LEVELS[p.level]["guidance"] in block
        assert learner.MOTIVATIONS[p.motivation]["guidance"] in block

    def test_intermediate_targets_b1(self):
        # Product decision: "short, uncomplicated sentences" is B1, not B2.
        assert learner.LEVELS["intermediate"]["target_cefr"] == "B1"
        assert "CEFR B1." in learner.prompt_block(_profile("intermediate"))

    def test_total_beginner_asks_for_very_simple_dialogue(self):
        block = learner.prompt_block(_profile("total_beginner"))
        assert "very short sentences" in block
        assert "two-person dialogue" in block
        assert "at most ONE error" in block

    def test_roman_reader_is_told_about_roman_input(self):
        block = learner.prompt_block(_profile(reads_script=False))
        assert "CANNOT read Kannada script" in block
        assert "Romanized" in block

    def test_script_reader_block_has_no_roman_instruction(self):
        assert "CANNOT" not in learner.prompt_block(_profile(reads_script=True))

    def test_work_motivation_asks_about_work(self):
        assert "what they do for work" in learner.prompt_block(
            _profile(motivation="work"))


# ===========================================================================
# Profile parsing, validation, display script
# ===========================================================================

class TestProfile:

    def test_from_row(self):
        p = LearnerProfile.from_row({"level": "beginner", "motivation": "fun",
                                     "reads_script": 0, "updated_at": "t"})
        assert p == LearnerProfile("beginner", "fun", False, "t")

    @pytest.mark.parametrize("row", [
        None, {}, {"level": "expert", "motivation": "fun", "reads_script": 1},
        {"level": "beginner", "motivation": "money", "reads_script": 1}])
    def test_from_row_rejects_missing_or_unknown(self, row):
        # A renamed level means answering the form again, not a crash.
        assert LearnerProfile.from_row(row) is None

    @pytest.mark.parametrize("args", [
        ("expert", "work", True), ("beginner", "money", True),
        ("beginner", "work", "yes"), ("beginner", "work", None)])
    def test_validate_rejects_anything_off_the_list(self, args):
        with pytest.raises(ValueError):
            learner.validate(*args)

    def test_validate_accepts_fixed_choices(self):
        learner.validate("advanced", "heritage", False)

    def test_content_script(self):
        assert learner.content_script(_profile(reads_script=True)) == "Kannada (Script)"
        assert learner.content_script(_profile(reads_script=False)) == \
            "Kannada (Roman - Natural)"


# ===========================================================================
# Topic visibility and ordering
# ===========================================================================

TOPICS = [{"name": n, "band": b} for n, b in [
    ("Greet", "total_beginner"), ("Neg", "beginner"), ("Conj", "intermediate"),
    ("Rel", "advanced")]]


class TestVisibleTopics:

    def _names(self, level, show_harder=False):
        return [t["name"] for t in learner.visible_topics(
            _profile(level), TOPICS, show_harder)]

    def test_total_beginner_sees_only_starter_topics(self):
        assert self._names("total_beginner") == ["Greet"]

    def test_total_beginner_cannot_reveal_harder_topics(self):
        assert self._names("total_beginner", show_harder=True) == ["Greet"]

    def test_own_band_first_then_easier_then_harder(self):
        assert self._names("intermediate") == ["Conj", "Neg", "Greet"]
        assert self._names("intermediate", show_harder=True) == \
            ["Conj", "Neg", "Greet", "Rel"]

    def test_advanced_sees_everything(self):
        assert set(self._names("advanced")) == {"Greet", "Neg", "Conj", "Rel"}

    def test_real_quiz_topics_all_have_a_valid_band(self):
        for name, d in config.QUIZ_TOPIC_DOCS.items():
            assert d["band"] in learner.LEVELS, name
        for name, d in config.LESSON_ONLY_DOCS.items():
            assert d["band"] in learner.LEVELS, name

    def test_every_band_has_at_least_one_quiz_topic(self):
        bands = {d["band"] for d in config.QUIZ_TOPIC_DOCS.values()}
        assert bands == set(learner.LEVELS)


class TestOrdering:

    def test_recommended_personas_first(self):
        names = learner.order_personas(_profile(motivation="work"),
                                       config.CHARACTER_CARDS)
        assert names[0] == "The New Colleague"
        assert sorted(names) == sorted(config.CHARACTER_CARDS)

    def test_writing_topics_reordered_not_filtered(self):
        topics = learner.order_writing_topics(
            _profile(motivation="friends_family"), config.WRITING_TOPICS)
        assert topics[0] == "Family (Kutumba)"
        assert sorted(topics) == sorted(config.WRITING_TOPICS)


# ===========================================================================
# learner.py <-> config contract (learner.py cannot import config)
# ===========================================================================

class TestConfigContract:

    def test_every_preferred_persona_exists(self):
        for key, m in learner.MOTIVATIONS.items():
            for name in m["personas"]:
                assert name in config.CHARACTER_CARDS, (key, name)

    def test_every_preferred_writing_topic_exists(self):
        for key, m in learner.MOTIVATIONS.items():
            for topic in m["writing_topics"]:
                assert topic in config.WRITING_TOPICS, (key, topic)

    def test_every_grammar_goal_key_exists(self):
        for key, lvl in learner.LEVELS.items():
            assert lvl["grammar_goals"][0] == "none", key
            for g in lvl["grammar_goals"]:
                assert g in config.GRAMMAR_GOAL_TEXT, (key, g)

    def test_grammar_goals_list_keeps_original_order(self):
        # Callers and tests index GRAMMAR_GOALS[0] (none) and [1] (compound).
        assert config.GRAMMAR_GOALS[0].startswith("No specific focus")
        assert "Compound Verbs" in config.GRAMMAR_GOALS[1]

    def test_every_lesson_doc_exists(self):
        for d in list(config.QUIZ_TOPIC_DOCS.values()) + \
                list(config.LESSON_ONLY_DOCS.values()):
            for f in d["files"]:
                assert os.path.exists(os.path.join(config.KNOWLEDGE_DIR, f)), f

    def test_get_lessons_covers_quiz_topics_and_lesson_only_docs(self):
        lessons = logic.get_lessons()
        assert {l["name"] for l in lessons} == \
            set(config.QUIZ_TOPIC_DOCS) | set(config.LESSON_ONLY_DOCS)
        assert all(l["quiz"] is None for l in lessons
                   if l["name"] in config.LESSON_ONLY_DOCS)


# ===========================================================================
# Prompt plumbing in logic.py
# ===========================================================================

CHAT_JSON = json.dumps({"kannada": "ನಮಸ್ಕಾರ", "english": "Hello", "errors": []})


def _client(text):
    client = MagicMock()
    client.chat.completions.create.return_value.choices[0].message.content = text
    return client


def _system_text(client):
    messages = client.chat.completions.create.call_args.kwargs["messages"]
    return next(m["content"] for m in messages if m["role"] == "system")


class TestChatPromptTailoring:

    def _system(self, learner_block=None):
        client = _client(CHAT_JSON)
        with patch("logic._sarvam_chat_client", return_value=client):
            logic.generate_chat_turn_ai(
                "ನಮಸ್ಕಾರ", [], config.GRAMMAR_GOALS[0], "The Shopkeeper",
                "Kannada (Script)", learner_block=learner_block)
        return _system_text(client)

    def test_no_block_keeps_the_original_profile(self):
        system = self._system()
        assert config.DEFAULT_STUDENT_PROFILE in system
        assert "[INJECT_STUDENT_PROFILE_HERE]" not in system

    def test_block_replaces_the_profile_section(self):
        block = learner.prompt_block(_profile("total_beginner", "friends_family",
                                              False))
        system = self._system(block)
        assert block in system
        assert "Striving for B2" not in system
        assert system.count("## Student Profile") == 1


class TestGenerateContentTailoring:

    def _system(self, **kwargs):
        client = _client("ok")
        with patch("logic._sarvam_chat_client", return_value=client):
            logic.generate_content("prompt", "ctx", **kwargs)
        return _system_text(client)

    def test_block_is_appended_to_system_instruction(self):
        system = self._system(learner_block="## Student Profile XYZ")
        assert system.startswith(config.SYSTEM_INSTRUCTION)
        assert "## Student Profile XYZ" in system

    def test_no_block_is_unchanged(self):
        assert self._system() == config.SYSTEM_INSTRUCTION

    @pytest.mark.parametrize("fn,args", [
        (logic.critique_text_ai, ("ನಾನು", "Formal", "ctx")),
        (logic.generate_kannada_article_ai, ("Work", "Formal", "ctx")),
        (logic.generate_comprehension_questions, ("ನಾನು", "ctx")),
        (logic.grade_reading_ai, ("q", "t", "a", "ctx")),
        (logic.grade_answer_ai, ("q", "a", "ctx")),
        (logic.generate_error_quiz, ([{"original": "x"}], "ctx")),
    ])
    def test_callers_forward_the_block(self, fn, args):
        with patch("logic.generate_content", return_value="{}") as gc:
            fn(*args, learner_block="BLOCK")
        assert gc.call_args.kwargs["learner_block"] == "BLOCK"

    def test_explain_mistake_forwards_the_block(self):
        item = {"id": "x", "english": "e", "canonical": "c", "grammar_note": "g"}
        with patch("logic.generate_content",
                   return_value='{"feedback": "f"}') as gc:
            logic.explain_mistake("u", item, "ctx", learner_block="BLOCK")
        assert gc.call_args.kwargs["learner_block"] == "BLOCK"

    def test_judge_is_never_tailored(self):
        # A correctness verdict must not depend on who the learner is.
        import inspect
        assert "learner_block" not in inspect.signature(
            logic.judge_equivalence).parameters

    def test_article_prompt_defers_form_to_the_profile(self):
        with patch("logic.generate_content", return_value="x") as gc:
            logic.generate_kannada_article_ai("Work", "Formal", "ctx",
                                              learner_block="BLOCK")
        assert "paragraph" not in gc.call_args.args[0]


# ===========================================================================
# Roman-script answers
# ===========================================================================

ITEM = {"id": "t", "topic": "T", "english": "I want coffee.",
        "canonical": "ನನಗೆ ಕಾಫಿ ಬೇಕು.",
        "acceptable": ["ನನಗೆ ಕಾಫಿ ಬೇಕು.", "ನಂಗೆ ಕಾಫಿ ಬೇಕು."],
        "difficulty": "easy", "grammar_note": "g",
        "common_errors": [{"form": "ನನಗೆ ಕಾಫಿ ಬೇಡ.", "means": "I don't want coffee."}]}


class TestRomanAnswers:

    @pytest.mark.parametrize("answer", [
        "nanage kaafi beku", "Nanage kāphi bēku.", "nange kafi beku",
        "NANAGE KAAPHI BEKU"])
    def test_roman_forms_match_as_variant(self, answer):
        assert logic.classify_answer(answer, ITEM) == "variant"

    def test_roman_never_counts_as_exact(self):
        # Romanization loses information: weaker evidence than a script match.
        assert logic.classify_answer("nanage kaafi beku", ITEM) != "exact"

    def test_script_answers_still_exact(self):
        assert logic.classify_answer("ನನಗೆ ಕಾಫಿ ಬೇಕು", ITEM) == "exact"

    def test_wrong_roman_answer_stays_incorrect(self):
        assert logic.classify_answer("nanage chaha beku", ITEM) == "incorrect"
        assert logic.classify_answer("avanu hodanu", ITEM) == "incorrect"

    def test_roman_common_error_is_caught_deterministically(self):
        assert logic.match_common_error("nanage kaafi beda", ITEM)["means"] == \
            "I don't want coffee."

    def test_script_answer_gets_no_roman_leniency(self):
        # ಟ vs ತ collapse in Roman; a script typist is held to script forms.
        item = dict(ITEM, canonical="ಕತ್ತು.", acceptable=["ಕತ್ತು."],
                    common_errors=[])
        assert logic.classify_answer("ಕಟ್ಟು.", item) == "incorrect"
        assert logic.classify_answer("kattu", item) == "variant"

    def test_empty_answer_is_incorrect(self):
        assert logic.classify_answer("", ITEM) == "incorrect"

    def test_quotative_folds_in_roman_but_hearsay_does_not(self):
        item = dict(ITEM, canonical="ಅವನು ಬರುತ್ತಾನೆ ಅಂತ.",
                    acceptable=["ಅವನು ಬರುತ್ತಾನೆ ಅಂತ."], common_errors=[])
        assert logic.classify_answer("avanu baruttaane endu", item) == "variant"
        assert logic.classify_answer("avanu baruttaane ante", item) == "incorrect"

    def test_every_real_bank_canonical_matches_its_own_romanization(self):
        bank = logic._load_quiz_bank_from_disk()
        for it in bank["items"]:
            roman = logic.toggle_script(it["canonical"], "Kannada (Roman - Natural)")
            assert logic.classify_answer(roman, it) == "variant", it["id"]


# ===========================================================================
# Placement
# ===========================================================================

class TestPlacement:

    @pytest.mark.parametrize("passed,level", [
        (0, "total_beginner"), (1, "beginner"), (2, "intermediate"),
        (3, "advanced"), (4, "advanced")])
    def test_placement_level(self, passed, level):
        assert learner.placement_level(passed) == level

    def test_band_passed_threshold(self):
        assert not learner.band_passed(1)
        assert learner.band_passed(2)

    def test_script_check(self):
        right = [i["answer"] for i in learner.SCRIPT_CHECK]
        assert learner.script_check_passed(right)
        assert not learner.script_check_passed(right[:-1] + [None])
        assert not learner.script_check_passed([])

    def test_script_check_answers_are_among_choices(self):
        for item in learner.SCRIPT_CHECK:
            assert item["answer"] in item["choices"]

    @pytest.fixture
    def bank(self):
        st.session_state["quiz_bank"] = logic._load_quiz_bank_from_disk()
        yield
        st.session_state.pop("quiz_bank", None)

    @pytest.mark.parametrize("band", list(learner.LEVELS))
    def test_every_band_yields_items_from_its_own_topics(self, bank, band):
        items = logic.build_placement_band(band, n=learner.PLACEMENT_PER_BAND,
                                           seed=1)
        assert len(items) == learner.PLACEMENT_PER_BAND
        for it in items:
            assert config.QUIZ_TOPIC_DOCS[it["topic"]]["band"] == band

    def test_placement_band_is_reproducible_with_a_seed(self, bank):
        a = logic.build_placement_band("beginner", seed=7)
        b = logic.build_placement_band("beginner", seed=7)
        assert [i["id"] for i in a] == [i["id"] for i in b]


class TestPlacementWiring:
    """Source guards on main.py, as in test_mastery_quiz: no Streamlit harness."""

    @staticmethod
    def _src():
        with open(os.path.join(os.path.dirname(__file__), "..", "main.py"),
                  encoding="utf-8") as f:
            return f.read()

    def test_placement_never_records_or_judges(self):
        src = self._src()
        call = src[src.index('render_quiz_runner("placement"'):]
        call = call[:call.index(")") + 1] + call[call.index(")") + 1:][:80]
        assert "record=False" in call and "judge=False" in call

    def test_recording_is_behind_the_record_flag(self):
        src = self._src()
        guard = src.index("if record:")
        assert guard < src.index(
            "logic.record_quiz_answer(item, tier, profile_id=current_profile())")

    def test_onboarding_gate_precedes_navigation(self):
        src = self._src()
        body = src[src.index("def main():"):]
        assert body.index("render_onboarding(lang_mode)") < \
            body.index("st.stop()", body.index("render_onboarding(lang_mode)")) < \
            body.index('st.sidebar.radio(')

    def test_no_mode_is_level_gated(self):
        # Product decision: total beginners keep Writing and Reading.
        src = self._src()
        assert '"Writing Critique": "NAV_WRITE"' in src
        assert '"Reading Comprehension": "NAV_READ"' in src
        assert "allowed_modes" not in src
