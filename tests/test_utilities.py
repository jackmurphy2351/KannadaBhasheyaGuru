"""
Layer 1 — Pure unit tests.

All functions tested here have no external dependencies: no network,
no filesystem (except load_knowledge_base, which uses a tmp_path),
no Streamlit, no API keys required.
"""
import os
import pytest

import config
import logic
from logic import (
    clean_json,
    humanize_transliteration,
    toggle_script,
    get_ui_text,
    load_knowledge_base,
    load_topic_doc,
)


# ===========================================================================
# clean_json
# ===========================================================================

class TestCleanJson:

    def test_plain_dict(self):
        assert clean_json('{"a": 1, "b": "hello"}') == {"a": 1, "b": "hello"}

    def test_plain_list(self):
        assert clean_json('["one", "two", "three"]') == ["one", "two", "three"]

    def test_fenced_with_json_prefix(self):
        text = '```json\n{"key": "value"}\n```'
        assert clean_json(text) == {"key": "value"}

    def test_fenced_without_json_prefix(self):
        text = '```\n{"key": "value"}\n```'
        assert clean_json(text) == {"key": "value"}

    def test_fenced_list_with_json_prefix(self):
        text = '```json\n[{"q": "Question?", "a": "Answer."}]\n```'
        assert clean_json(text) == [{"q": "Question?", "a": "Answer."}]

    def test_json_embedded_in_prose(self):
        # Regex fallback path: JSON buried in surrounding text
        text = 'Here is the result: {"is_correct": true, "feedback": "Good"} end of output'
        result = clean_json(text)
        assert result == {"is_correct": True, "feedback": "Good"}

    def test_list_embedded_in_prose(self):
        text = 'The sentences are: ["I go", "She eats"] — enjoy!'
        result = clean_json(text)
        assert result == ["I go", "She eats"]

    def test_whitespace_only_input(self):
        assert clean_json("   ") is None

    def test_empty_string(self):
        assert clean_json("") is None

    def test_totally_invalid_text(self):
        assert clean_json("this is not json at all") is None

    def test_nested_json(self):
        text = '{"analysis": [{"original": "x", "corrected": "y", "status": "IMPROVE"}]}'
        result = clean_json(text)
        assert result["analysis"][0]["status"] == "IMPROVE"

    def test_extra_whitespace_around_json(self):
        assert clean_json('  \n  {"a": 1}  \n  ') == {"a": 1}

    def test_boolean_values_preserved(self):
        result = clean_json('{"is_correct": false, "score": 0}')
        assert result == {"is_correct": False, "score": 0}


# ===========================================================================
# humanize_transliteration
# ===========================================================================

class TestHumanizeTransliteration:

    def test_empty_string_returns_empty(self):
        assert humanize_transliteration("") == ""

    def test_none_like_empty_handled(self):
        # The function checks `if not iast_text` — falsy input returns ""
        assert humanize_transliteration("") == ""

    def test_plain_ascii_unchanged(self):
        assert humanize_transliteration("namaskara") == "namaskara"

    def test_macron_a_stripped(self):
        # ā (U+0101) → NFKD: a + combining macron → macron filtered → "a"
        assert humanize_transliteration("ā") == "a"

    def test_macron_u_stripped(self):
        # ū → NFKD: u + combining macron → "u"
        assert humanize_transliteration("ū") == "u"

    def test_word_with_macron(self):
        # nāma: n + ā + m + a → n + a + m + a
        assert humanize_transliteration("nāma") == "nama"

    def test_anusvara_base_char_preserved(self):
        # ṃ (U+1E43) → NFKD: m + combining dot below → dot filtered → "m"
        assert humanize_transliteration("ṃ") == "m"

    def test_complex_iast_word(self):
        # grāṃthika: g+r + ā(→a) + ṃ(→m) + t+h+i+k+a = "gramthika"
        assert humanize_transliteration("grāṃthika") == "gramthika"

    def test_mixed_case_preserved(self):
        # Uppercase letters should pass through unchanged
        result = humanize_transliteration("Nāma")
        assert result == "Nama"


# ===========================================================================
# toggle_script
# ===========================================================================

class TestToggleScript:

    def test_empty_input_returns_empty(self):
        assert toggle_script("", "Kannada (Roman - Natural)") == ""

    def test_english_mode_passes_through(self):
        # No "Roman" in "English" → text returned unchanged
        assert toggle_script("ನಮಸ್ಕಾರ", "English") == "ನಮಸ್ಕಾರ"

    def test_kannada_script_mode_passes_through(self):
        # No "Roman" in "Kannada (Script)" → text returned unchanged
        assert toggle_script("ನಮಸ್ಕಾರ", "Kannada (Script)") == "ನಮಸ್ಕಾರ"

    def test_roman_strict_produces_iast(self):
        # IAST strict output retains diacritics like ā
        result = toggle_script("ನಮಸ್ಕಾರ", "Kannada (Roman - Strict)")
        assert result == "namaskāra"

    def test_roman_natural_strips_diacritics(self):
        # Natural mode humanizes IAST → plain ASCII
        result = toggle_script("ನಮಸ್ಕಾರ", "Kannada (Roman - Natural)")
        assert result == "namaskara"

    def test_roman_strict_output_contains_no_kannada_codepoints(self):
        result = toggle_script("ನಮಸ್ಕಾರ", "Kannada (Roman - Strict)")
        assert all(ord(c) <= 0x024F for c in result), \
            f"Unexpected non-Latin char in: {result!r}"

    def test_roman_natural_output_is_plain_ascii(self):
        result = toggle_script("ನಮಸ್ಕಾರ", "Kannada (Roman - Natural)")
        assert result.isascii(), f"Expected plain ASCII, got: {result!r}"

    def test_roman_strict_differs_from_natural_for_long_vowels(self):
        # Strict keeps the macron; Natural strips it
        strict = toggle_script("ನಮಸ್ಕಾರ", "Kannada (Roman - Strict)")
        natural = toggle_script("ನಮಸ್ಕಾರ", "Kannada (Roman - Natural)")
        assert strict != natural


# ===========================================================================
# get_ui_text
# ===========================================================================

class TestGetUiText:

    def test_english_mode_returns_english(self):
        assert get_ui_text("NAV_HOME", "English") == "Home"

    def test_kannada_script_mode_returns_kannada(self):
        assert get_ui_text("NAV_HOME", "Kannada (Script)") == "ಮುಖಪುಟ"

    def test_roman_natural_mode_returns_nonempty_string(self):
        result = get_ui_text("NAV_HOME", "Kannada (Roman - Natural)")
        assert isinstance(result, str) and len(result) > 0

    def test_roman_strict_mode_returns_nonempty_string(self):
        result = get_ui_text("NAV_HOME", "Kannada (Roman - Strict)")
        assert isinstance(result, str) and len(result) > 0

    def test_roman_natural_is_plain_ascii(self):
        result = get_ui_text("NAV_HOME", "Kannada (Roman - Natural)")
        assert result.isascii()

    def test_missing_key_returns_key_itself(self):
        # Documented fallback: unknown key → return the key string
        assert get_ui_text("NONEXISTENT_KEY_XYZ", "English") == "NONEXISTENT_KEY_XYZ"

    def test_all_nav_keys_have_nonempty_english(self):
        nav_keys = ["NAV_HOME", "NAV_EMAIL", "NAV_QUIZ", "NAV_WRITE", "NAV_READ", "NAV_CHAT"]
        for key in nav_keys:
            assert get_ui_text(key, "English"), f"{key} returned empty in English mode"

    def test_all_nav_keys_have_nonempty_kannada_script(self):
        nav_keys = ["NAV_HOME", "NAV_EMAIL", "NAV_QUIZ", "NAV_WRITE", "NAV_READ", "NAV_CHAT"]
        for key in nav_keys:
            result = get_ui_text(key, "Kannada (Script)")
            assert result, f"{key} returned empty in Kannada (Script) mode"


# ===========================================================================
# load_knowledge_base
# ===========================================================================

class TestLoadKnowledgeBase:

    def test_reads_all_txt_files(self, tmp_path, monkeypatch):
        # Write 3 fake grammar files
        (tmp_path / "1. topic_a.txt").write_text("Content A", encoding="utf-8")
        (tmp_path / "2. topic_b.txt").write_text("Content B", encoding="utf-8")
        (tmp_path / "3. topic_c.txt").write_text("Content C", encoding="utf-8")

        monkeypatch.setattr(config, "KNOWLEDGE_DIR", str(tmp_path))
        result = load_knowledge_base()

        assert "Content A" in result
        assert "Content B" in result
        assert "Content C" in result

    def test_includes_source_file_headers(self, tmp_path, monkeypatch):
        (tmp_path / "grammar.txt").write_text("Rule 1", encoding="utf-8")
        monkeypatch.setattr(config, "KNOWLEDGE_DIR", str(tmp_path))

        result = load_knowledge_base()
        assert "--- SOURCE: grammar.txt ---" in result

    def test_empty_directory_returns_empty_string(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "KNOWLEDGE_DIR", str(tmp_path))
        assert load_knowledge_base() == ""

    def test_loads_txt_and_md_but_ignores_other_types(self, tmp_path, monkeypatch):
        # Beginner foundation docs are .md; legacy grammar refs are .txt — both
        # are loaded. Other file types (e.g. .py) are ignored.
        (tmp_path / "grammar.txt").write_text("Good content", encoding="utf-8")
        (tmp_path / "beginner.md").write_text("Markdown content", encoding="utf-8")
        (tmp_path / "notes.py").write_text("Also ignored", encoding="utf-8")
        monkeypatch.setattr(config, "KNOWLEDGE_DIR", str(tmp_path))

        result = load_knowledge_base()
        assert "Good content" in result
        assert "Markdown content" in result
        assert "Also ignored" not in result

    def test_returns_string_type(self, tmp_path, monkeypatch):
        (tmp_path / "a.txt").write_text("x", encoding="utf-8")
        monkeypatch.setattr(config, "KNOWLEDGE_DIR", str(tmp_path))
        assert isinstance(load_knowledge_base(), str)

    def test_real_knowledge_base_loads_all_modules(self):
        # Smoke check against the actual knowledge_base/ directory.
        # Does NOT hit any API — just reads local files. Counts both the legacy
        # .txt grammar references and the newer .md beginner foundation docs, so
        # the test stays correct as the curriculum grows.
        import glob
        import os
        expected = len(
            glob.glob(os.path.join(config.KNOWLEDGE_DIR, "*.txt"))
            + glob.glob(os.path.join(config.KNOWLEDGE_DIR, "*.md"))
        )
        result = load_knowledge_base()
        assert result, "load_knowledge_base() returned empty — check knowledge_base/ directory"
        assert expected >= 14, "Expected at least 14 grammar/foundation modules"
        assert result.count("--- SOURCE:") == expected, \
            f"Expected {expected} module files loaded from knowledge_base/"


class TestLoadTopicDoc:

    def test_single_string_returns_raw_content_no_header(self, tmp_path, monkeypatch):
        (tmp_path / "topic.md").write_text("Lesson body", encoding="utf-8")
        monkeypatch.setattr(config, "KNOWLEDGE_DIR", str(tmp_path))

        result = load_topic_doc("topic.md")
        assert result == "Lesson body"
        # A single doc needs no SOURCE header.
        assert "--- SOURCE:" not in result

    def test_list_concatenates_with_source_headers(self, tmp_path, monkeypatch):
        (tmp_path / "base.md").write_text("Shared base", encoding="utf-8")
        (tmp_path / "past.md").write_text("Past tense", encoding="utf-8")
        monkeypatch.setattr(config, "KNOWLEDGE_DIR", str(tmp_path))

        result = load_topic_doc(["base.md", "past.md"])
        assert "Shared base" in result
        assert "Past tense" in result
        assert "--- SOURCE: base.md ---" in result
        assert "--- SOURCE: past.md ---" in result
        # Order is preserved.
        assert result.index("Shared base") < result.index("Past tense")

    def test_missing_file_in_list_is_skipped(self, tmp_path, monkeypatch):
        (tmp_path / "base.md").write_text("Shared base", encoding="utf-8")
        monkeypatch.setattr(config, "KNOWLEDGE_DIR", str(tmp_path))

        result = load_topic_doc(["base.md", "does_not_exist.md"])
        assert "Shared base" in result
        assert "does_not_exist" not in result

    def test_missing_single_file_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "KNOWLEDGE_DIR", str(tmp_path))
        assert load_topic_doc("nope.md") == ""
