"""knowledge_base romanization convention.

Every run of Kannada script in a lesson doc must be followed by a
hand-written strict-IAST gloss — "ಮನೆಗೆ (*manege*)" — and that gloss must
spell what the script says. Learners who don't read script see only the
glosses, so a missing gloss hides content from them and a wrong one teaches
the wrong word (the old case-endings doc glossed ಜೊತೆ as "joteyalli").

Applies to every .md doc in knowledge_base/ (CONVERTED is the full glob).
"""
import glob
import os
import re
import unicodedata

import pytest

import config
import logic

CONVERTED = sorted(
    os.path.basename(p)
    for p in glob.glob(os.path.join(config.KNOWLEDGE_DIR, "*.md")))


def _read(name):
    with open(os.path.join(config.KNOWLEDGE_DIR, name), encoding="utf-8") as f:
        return f.read()


def _line(text, pos):
    return text.count("\n", 0, pos) + 1


_IGNORED = re.compile(r"[\s*.,!?;:'\"“”‘’()\-/…—–‌‍]")


def _norm(s):
    """Case, spacing and punctuation don't count; letters and diacritics do."""
    return _IGNORED.sub("", unicodedata.normalize("NFC", s).casefold())


@pytest.mark.parametrize("name", CONVERTED)
def test_every_kannada_run_has_a_roman_gloss(name):
    text = _read(name)
    missing = [f"L{_line(text, run.start())}: {run.group()}"
               for run, gloss in logic.kannada_runs(text) if gloss is None]
    assert not missing, (
        f"{name}: {len(missing)} Kannada run(s) without a '(*roman*)' gloss:\n"
        + "\n".join(missing))


@pytest.mark.parametrize("name", CONVERTED)
def test_roman_gloss_spells_the_script(name):
    text = _read(name)
    wrong = []
    for run, gloss in logic.kannada_runs(text):
        if gloss is None:
            continue  # reported by the coverage test
        script = run.group().replace("*", "")
        if _norm(gloss.group(1)) != _norm(logic.lesson_iast(script)):
            wrong.append(f"L{_line(text, run.start())}: {script} "
                         f"(*{gloss.group(1)}*) — expected "
                         f"'{logic.lesson_iast(script)}'")
    assert not wrong, (f"{name}: {len(wrong)} gloss(es) don't match the "
                       "script:\n" + "\n".join(wrong))


def test_converted_docs_exist():
    for name in CONVERTED:
        assert os.path.exists(os.path.join(config.KNOWLEDGE_DIR, name)), name


class TestRunsAndGlosses:
    def _pairs(self, text):
        return [(r.group(), g.group(1) if g else None)
                for r, g in logic.kannada_runs(text)]

    def test_sentence_with_gloss_after_full_stop(self):
        assert self._pairs("ರಾಮ ಬಂದ. (*Rāma banda.*) — Rama came.") == [
            ("ರಾಮ ಬಂದ", "Rāma banda.")]

    def test_bold_inside_and_around_a_run(self):
        assert self._pairs("ನಾನು **ಅವಳನ್ನ** ಕರೆದೆ (*nānu avaḷanna karede*)") == [
            ("ನಾನು **ಅವಳನ್ನ** ಕರೆದೆ", "nānu avaḷanna karede")]
        assert self._pairs("**ಮನೆಗೆ** (*manege*)") == [("ಮನೆಗೆ", "manege")]

    def test_plus_and_arrow_split_runs(self):
        assert [r for r, _ in self._pairs("ಮರ + ಅಲ್ಲಿ → ಮರದಲ್ಲಿ")] == [
            "ಮರ", "ಅಲ್ಲಿ", "ಮರದಲ್ಲಿ"]

    def test_suffix_hyphen_and_slash_list(self):
        assert self._pairs("-ನು / -ವು / -ಯು (*-nu / -vu / -yu*)") == [
            ("ನು / -ವು / -ಯು", "-nu / -vu / -yu")]

    def test_gloss_may_follow_a_trailing_hyphen(self):
        assert self._pairs("ನನ್- (*nan-*)") == [("ನನ್", "nan-")]

    def test_gloss_may_follow_an_ellipsis(self):
        assert self._pairs("ಮಳೆ ಬಂದ್ರೆ… (*maḷe bandre…*)") == [
            ("ಮಳೆ ಬಂದ್ರೆ", "maḷe bandre…")]

    def test_gloss_may_wrap_onto_the_next_line(self):
        assert self._pairs("→ **ನಿಂಗೆ**\n  (*niṅge*), and") == [("ನಿಂಗೆ", "niṅge")]
        assert self._pairs("ನಾನು ಹೋದೆ (*nānu\n  hōde*)") == [
            ("ನಾನು ಹೋದೆ", "nānu\n  hōde")]

    def test_runs_never_cross_lines_or_table_cells(self):
        assert [r for r, _ in self._pairs("| ಮನೆಗೆ | ಮರಕ್ಕೆ |\nಊರಿಗೆ")] == [
            "ಮನೆಗೆ", "ಮರಕ್ಕೆ", "ಊರಿಗೆ"]

    def test_missing_gloss_is_none(self):
        assert self._pairs("ಮನೆಗೆ — to the house") == [("ಮನೆಗೆ", None)]


class TestLessonIast:
    @pytest.mark.parametrize("script, roman", [
        ("ಮನೆಗೆ", "manege"),
        ("ಏನು", "ēnu"),
        ("ಒಂದು", "ondu"),
        ("ಓದು", "ōdu"),
        ("ಅವಳು", "avaḷu"),
        ("ಬೆಂಗಳೂರು", "beṅgaḷūru"),
        ("ತಿಂಡಿ", "tiṇḍi"),
        ("ತುಂಬಾ", "tumbā"),
        ("ಹೂಂ", "hūṃ"),
        ("ಮಾರ್ಕೆಟ್‌ಗೆ", "mārkeṭge"),
        ("ತೃತೀಯಾ", "tṛtīyā"),
    ])
    def test_doc_convention(self, script, roman):
        assert logic.lesson_iast(script) == roman

    def test_anna_and_aṇṇa_stay_distinct(self):
        assert logic.lesson_iast("ಅಣ್ಣ") != logic.lesson_iast("ಅನ್ನ")


class TestLessonForDisplay:
    ROMAN = "Kannada (Roman - Natural)"
    SCRIPT = "Kannada (Script)"

    def show(self, text):
        return logic.lesson_for_display(text, self.ROMAN)

    def test_script_readers_get_the_doc_unchanged(self):
        doc = "ರಾಮ ಬಂದ. (*Rāma banda.*) — Rama came."
        assert logic.lesson_for_display(doc, self.SCRIPT) == doc

    def test_sentence_shows_gloss_once_with_single_full_stop(self):
        assert self.show("ರಾಮ ಬಂದ. (*Rāma banda.*) — Rama came.") == (
            "*Rāma banda*. — Rama came.")

    def test_bold_stays_balanced(self):
        assert self.show("✅ **ಮನೆಗೆ** (*manege*).") == "✅ ***manege***."

    def test_suffix_hyphen_not_doubled(self):
        assert self.show("**-ಅನ್ನು** (*-annu*)") == "**-*annu***"

    def test_wrapped_gloss_is_joined(self):
        assert self.show("ನಾನು ಹೋದೆ (*nānu\n  hōde*)") == "*nānu hōde*"

    def test_diacritics_survive(self):
        # The strict gloss keeps ಅಣ್ಣ and ಅನ್ನ apart; Natural mode would not.
        assert self.show("ಅಣ್ಣ (*aṇṇa*), ಅನ್ನ (*anna*)") == "*aṇṇa*, *anna*"

    def test_unglossed_run_falls_back_to_transliteration(self):
        out = self.show("ಮನೆಗೆ — home; ಊರಿಗೆ (*ūrige*)")
        assert "ಮ" not in out and out.endswith("*ūrige*")

    def test_no_script_left_in_converted_docs(self):
        for name in CONVERTED:
            out = self.show(_read(name))
            assert not re.search("[ಀ-೿]", out), name
