"""
Layer 2 — Sarvam chat API tests (all network calls mocked).

Strategy:
  - generate_content / generate_chat_turn_ai: mock logic._sarvam_chat_client
  - All higher-level functions (generate_quiz, grade_answer_ai, etc.):
    mock logic.generate_content so we control what the AI "returns"
    and test only the parsing/error-handling around that call.
"""
import json
from unittest.mock import MagicMock, patch, call

import pytest

import config
import logic
from logic import (
    generate_content,
    generate_chat_turn_ai,
    generate_quiz,
    grade_answer_ai,
    critique_text_ai,
    generate_kannada_article_ai,
    generate_comprehension_questions,
    grade_reading_ai,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client(response_text: str) -> MagicMock:
    """Return a mock _sarvam_chat_client() result that emits response_text."""
    client = MagicMock()
    client.chat.completions.create.return_value.choices[0].message.content = response_text
    return client


FAKE_CONTEXT = "Grammar rule: subjects precede verbs."
CHAT_JSON = json.dumps({
    "kannada": "ನಮಸ್ಕಾರ! ಟಿಕೆಟ್ ತೋರಿಸಿ.",
    "english": "Hello! Show your ticket.",
    "errors": [],
})


# ===========================================================================
# generate_content
# ===========================================================================

class TestGenerateContent:

    def test_returns_response_text(self):
        with patch("logic._sarvam_chat_client", return_value=_make_client("Hello World")):
            assert generate_content("Say hello", FAKE_CONTEXT) == "Hello World"

    def test_uses_chat_model_by_default(self):
        mock_client = _make_client("ok")
        with patch("logic._sarvam_chat_client", return_value=mock_client):
            generate_content("prompt", FAKE_CONTEXT)
        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == config.SARVAM_CHAT_MODEL

    def test_uses_reading_model_when_flag_set(self):
        mock_client = _make_client("ok")
        with patch("logic._sarvam_chat_client", return_value=mock_client):
            generate_content("prompt", FAKE_CONTEXT, use_reading_model=True)
        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == config.SARVAM_READING_MODEL

    def test_injects_context_into_prompt(self):
        mock_client = _make_client("ok")
        with patch("logic._sarvam_chat_client", return_value=mock_client):
            generate_content("my_prompt", "UNIQUE_CONTEXT_STRING_XYZ")
        call_kwargs = mock_client.chat.completions.create.call_args
        messages = call_kwargs.kwargs["messages"]
        user_message_content = next(m["content"] for m in messages if m["role"] == "user")
        assert "UNIQUE_CONTEXT_STRING_XYZ" in user_message_content

    def test_includes_system_instruction(self):
        mock_client = _make_client("ok")
        with patch("logic._sarvam_chat_client", return_value=mock_client):
            generate_content("prompt", FAKE_CONTEXT)
        messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
        system_messages = [m for m in messages if m["role"] == "system"]
        assert len(system_messages) == 1
        assert config.SYSTEM_INSTRUCTION in system_messages[0]["content"]

    def test_api_exception_returns_error_string(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("timeout")
        with patch("logic._sarvam_chat_client", return_value=mock_client):
            result = generate_content("prompt", FAKE_CONTEXT)
        assert "API Error" in result

    def test_fallback_context_when_none_provided(self):
        mock_client = _make_client("ok")
        with patch("logic._sarvam_chat_client", return_value=mock_client):
            generate_content("prompt")  # no context_override
        messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
        user_content = next(m["content"] for m in messages if m["role"] == "user")
        assert "No specific context" in user_content


# ===========================================================================
# generate_chat_turn_ai
# ===========================================================================

class TestGenerateChatTurnAi:

    def _call(self, mock_client, *, user_message="ನನ್ನ ಹೆಸರು ಜಾನ್.", history=None,
              grammar_focus=None, role_key="The Train Conductor",
              lang_mode="Kannada (Script)"):
        grammar_focus = grammar_focus or config.GRAMMAR_GOALS[0]
        history = history or []
        with patch("logic._sarvam_chat_client", return_value=mock_client):
            return generate_chat_turn_ai(user_message, history, grammar_focus, role_key, lang_mode)

    def test_success_returns_expected_keys(self):
        client = _make_client(CHAT_JSON)
        result = self._call(client)
        assert set(result.keys()) >= {"bot_reply_kannada", "bot_reply_english_translation",
                                      "user_errors", "raw_text"}

    def test_success_extracts_kannada_reply(self):
        client = _make_client(CHAT_JSON)
        result = self._call(client)
        assert result["bot_reply_kannada"] == "ನಮಸ್ಕಾರ! ಟಿಕೆಟ್ ತೋರಿಸಿ."

    def test_success_extracts_english_translation(self):
        client = _make_client(CHAT_JSON)
        result = self._call(client)
        assert result["bot_reply_english_translation"] == "Hello! Show your ticket."

    def test_success_extracts_errors_list(self):
        chat_json_with_error = json.dumps({
            "kannada": "ಸರಿ",
            "english": "OK",
            "errors": [{"original": "ನಾನ್", "correction": "ನಾನು", "reason": "Typo"}],
        })
        client = _make_client(chat_json_with_error)
        result = self._call(client)
        assert len(result["user_errors"]) == 1
        assert result["user_errors"][0]["correction"] == "ನಾನು"

    def test_injects_character_card_into_system_prompt(self):
        mock_client = _make_client(CHAT_JSON)
        with patch("logic._sarvam_chat_client", return_value=mock_client):
            generate_chat_turn_ai(
                "ನಮಸ್ಕಾರ", [], config.GRAMMAR_GOALS[0],
                "The Shopkeeper", "Kannada (Script)"
            )
        messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
        system_text = next(m["content"] for m in messages if m["role"] == "system")
        # The Shopkeeper card text should be injected
        assert "Malleshwaram" in system_text

    def test_injects_grammar_focus_into_system_prompt(self):
        mock_client = _make_client(CHAT_JSON)
        grammar = config.GRAMMAR_GOALS[1]  # compound verbs
        with patch("logic._sarvam_chat_client", return_value=mock_client):
            generate_chat_turn_ai("msg", [], grammar, "The Doctor", "Kannada (Script)")
        messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
        system_text = next(m["content"] for m in messages if m["role"] == "system")
        assert grammar in system_text

    def test_roman_lang_mode_uses_aadumaatu_schema(self):
        mock_client = _make_client(CHAT_JSON)
        with patch("logic._sarvam_chat_client", return_value=mock_client):
            generate_chat_turn_ai(
                "msg", [], config.GRAMMAR_GOALS[0],
                "The Nosy Neighbor", "Kannada (Roman - Natural)"
            )
        messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
        system_text = next(m["content"] for m in messages if m["role"] == "system")
        # AADUMAATU_ROMAN schema contains a romanized example
        assert "Arey" in system_text or "naan" in system_text or "late aade" in system_text

    def test_script_lang_mode_uses_formal_schema(self):
        mock_client = _make_client(CHAT_JSON)
        with patch("logic._sarvam_chat_client", return_value=mock_client):
            generate_chat_turn_ai(
                "msg", [], config.GRAMMAR_GOALS[0],
                "The Train Conductor", "Kannada (Script)"
            )
        messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
        system_text = next(m["content"] for m in messages if m["role"] == "system")
        # FORMAL_SCRIPT schema uses Kannada script in the example
        assert "ನಮಸ್ಕಾರ" in system_text

    def test_appends_user_message_at_end_of_messages(self, sample_chat_history):
        mock_client = _make_client(CHAT_JSON)
        user_msg = "ಒಂದು ಟಿಕೆಟ್ ಕೊಡಿ."
        with patch("logic._sarvam_chat_client", return_value=mock_client):
            generate_chat_turn_ai(
                user_msg, sample_chat_history,
                config.GRAMMAR_GOALS[0], "The Train Conductor", "Kannada (Script)"
            )
        messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
        last_message = messages[-1]
        assert last_message["role"] == "user"
        assert last_message["content"] == user_msg

    def test_uses_json_object_response_format(self):
        mock_client = _make_client(CHAT_JSON)
        with patch("logic._sarvam_chat_client", return_value=mock_client):
            generate_chat_turn_ai("msg", [], config.GRAMMAR_GOALS[0],
                                  "The Doctor", "Kannada (Script)")
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["response_format"] == {"type": "json_object"}

    def test_missing_kannada_key_returns_error_dict(self):
        # If AI returns JSON without the mandatory "kannada" key
        bad_json = json.dumps({"english": "Hi", "errors": []})
        client = _make_client(bad_json)
        result = self._call(client)
        assert "error" in result

    def test_api_exception_returns_error_dict(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("connection reset")
        result = self._call(mock_client)
        assert "error" in result
        assert "connection reset" in result["error"]

    def test_malformed_json_returns_error_dict(self):
        client = _make_client("NOT JSON AT ALL {{")
        result = self._call(client)
        assert "error" in result


# ===========================================================================
# generate_quiz
# ===========================================================================

class TestGenerateQuiz:

    def test_returns_10_sentences(self):
        sentences = [f"Sentence {i}." for i in range(10)]
        with patch("logic.generate_content", return_value=json.dumps(sentences)):
            result = generate_quiz("Case Suffixes", FAKE_CONTEXT)
        assert len(result) == 10

    def test_returns_list_of_strings(self):
        sentences = [f"Sentence {i}." for i in range(10)]
        with patch("logic.generate_content", return_value=json.dumps(sentences)):
            result = generate_quiz("Verb Tenses", FAKE_CONTEXT)
        assert all(isinstance(s, str) for s in result)

    def test_topic_name_appears_in_prompt(self):
        with patch("logic.generate_content", return_value=json.dumps(["x"] * 10)) as mock_gen:
            generate_quiz("Compound Verbs", FAKE_CONTEXT)
        prompt_arg = mock_gen.call_args.args[0]
        assert "Compound Verbs" in prompt_arg

    def test_bad_json_returns_error_list(self):
        with patch("logic.generate_content", return_value="NOT JSON"):
            result = generate_quiz("Any Topic", FAKE_CONTEXT)
        assert isinstance(result, list)
        assert len(result) == 1
        assert "Error" in result[0]


# ===========================================================================
# grade_answer_ai
# ===========================================================================

class TestGradeAnswerAi:

    CORRECT_RESPONSE = json.dumps({
        "is_correct": True,
        "feedback": "Correct! Minor accent note.",
        "correct_translation": "ನಾನು ಮನೆಗೆ ಹೋಗುತ್ತೇನೆ.",
    })
    INCORRECT_RESPONSE = json.dumps({
        "is_correct": False,
        "feedback": "Wrong verb tense used.",
        "correct_translation": "ನಾನು ಮನೆಗೆ ಹೋಗುತ್ತೇನೆ.",
    })

    def test_correct_answer_is_correct_true(self):
        with patch("logic.generate_content", return_value=self.CORRECT_RESPONSE):
            result = grade_answer_ai("I go home.", "ನಾನು ಮನೆಗೆ ಹೋಗುತ್ತೇನೆ.", FAKE_CONTEXT)
        assert result["is_correct"] is True

    def test_incorrect_answer_is_correct_false(self):
        with patch("logic.generate_content", return_value=self.INCORRECT_RESPONSE):
            result = grade_answer_ai("I go home.", "ನಾನು ಮನೆ ಹೋಗುತ್ತೇನೆ.", FAKE_CONTEXT)
        assert result["is_correct"] is False

    def test_result_has_feedback_and_correct_translation(self):
        with patch("logic.generate_content", return_value=self.CORRECT_RESPONSE):
            result = grade_answer_ai("question", "answer", FAKE_CONTEXT)
        assert "feedback" in result
        assert "correct_translation" in result

    def test_question_and_answer_in_prompt(self):
        with patch("logic.generate_content", return_value=self.CORRECT_RESPONSE) as mock_gen:
            grade_answer_ai("I go home.", "ನಾನು ಹೋಗುತ್ತೇನೆ.", FAKE_CONTEXT)
        prompt = mock_gen.call_args.args[0]
        assert "I go home." in prompt
        assert "ನಾನು ಹೋಗುತ್ತೇನೆ." in prompt

    def test_bad_json_returns_fallback_dict(self):
        with patch("logic.generate_content", return_value="API down"):
            result = grade_answer_ai("q", "a", FAKE_CONTEXT)
        assert isinstance(result, dict)
        assert "is_correct" in result
        assert result["is_correct"] is False


# ===========================================================================
# critique_text_ai
# ===========================================================================

class TestCritiqueTextAi:

    CRITIQUE_RESPONSE = json.dumps({
        "analysis": [
            {"original": "ನಾನ್ ಹೋಗ್ತೇನೆ.", "corrected": "ನಾನು ಹೋಗುತ್ತೇನೆ.",
             "status": "IMPROVE", "feedback": "Informal form."},
        ],
        "overall_summary": "Good attempt. Focus on endings.",
    })

    def test_returns_analysis_list(self):
        with patch("logic.generate_content", return_value=self.CRITIQUE_RESPONSE):
            result = critique_text_ai("ನಾನ್ ಹೋಗ್ತೇನೆ.", "Formal", FAKE_CONTEXT)
        assert "analysis" in result
        assert isinstance(result["analysis"], list)

    def test_returns_overall_summary(self):
        with patch("logic.generate_content", return_value=self.CRITIQUE_RESPONSE):
            result = critique_text_ai("ನಾನ್ ಹೋಗ್ತೇನೆ.", "Formal", FAKE_CONTEXT)
        assert "overall_summary" in result

    def test_formal_style_injects_granthike_label(self):
        with patch("logic.generate_content", return_value=self.CRITIQUE_RESPONSE) as mock_gen:
            critique_text_ai("text", "Formal", FAKE_CONTEXT)
        prompt = mock_gen.call_args.args[0]
        assert "Granthike" in prompt or "Literary" in prompt

    def test_colloquial_style_injects_aadumaatu_label(self):
        with patch("logic.generate_content", return_value=self.CRITIQUE_RESPONSE) as mock_gen:
            critique_text_ai("text", "Colloquial", FAKE_CONTEXT)
        prompt = mock_gen.call_args.args[0]
        assert "Aadumaatu" in prompt or "Colloquial" in prompt

    def test_bad_json_returns_empty_dict(self):
        with patch("logic.generate_content", return_value="broken"):
            result = critique_text_ai("text", "Formal", FAKE_CONTEXT)
        assert result == {}


# ===========================================================================
# generate_kannada_article_ai
# ===========================================================================

class TestGenerateKannadaArticleAi:

    def test_returns_ai_output_directly(self):
        with patch("logic.generate_content", return_value="ಕನ್ನಡ ಪ್ಯಾರಾಗ್ರಾಫ್."):
            result = generate_kannada_article_ai("Travel", "Formal", FAKE_CONTEXT)
        assert result == "ಕನ್ನಡ ಪ್ಯಾರಾಗ್ರಾಫ್."

    def test_formal_style_maps_to_literary(self):
        with patch("logic.generate_content") as mock_gen:
            mock_gen.return_value = "ok"
            generate_kannada_article_ai("Travel", "Formal", FAKE_CONTEXT)
        prompt = mock_gen.call_args.args[0]
        assert "Literary" in prompt

    def test_colloquial_style_maps_to_colloquial(self):
        with patch("logic.generate_content") as mock_gen:
            mock_gen.return_value = "ok"
            generate_kannada_article_ai("Food", "Colloquial", FAKE_CONTEXT)
        prompt = mock_gen.call_args.args[0]
        assert "Colloquial" in prompt

    def test_topic_appears_in_prompt(self):
        with patch("logic.generate_content") as mock_gen:
            mock_gen.return_value = "ok"
            generate_kannada_article_ai("SpecialTopicName", "Formal", FAKE_CONTEXT)
        prompt = mock_gen.call_args.args[0]
        assert "SpecialTopicName" in prompt


# ===========================================================================
# generate_comprehension_questions
# ===========================================================================

class TestGenerateComprehensionQuestions:

    QA_JSON = json.dumps([
        {"question": "ಲೇಖಕರ ಹೆಸರೇನು?", "answer": "ರಾಮ."},
        {"question": "ಅವರು ಎಲ್ಲಿ ಹೋದರು?", "answer": "ಮೈಸೂರಿಗೆ."},
        {"question": "ಅವರು ಏನು ನೋಡಿದರು?", "answer": "ಅರಮನೆಯನ್ನು."},
    ])

    def test_returns_three_questions(self):
        with patch("logic.generate_content", return_value=self.QA_JSON):
            result = generate_comprehension_questions("article text", FAKE_CONTEXT)
        assert len(result) == 3

    def test_each_item_has_question_and_answer_keys(self):
        with patch("logic.generate_content", return_value=self.QA_JSON):
            result = generate_comprehension_questions("article text", FAKE_CONTEXT)
        for item in result:
            assert "question" in item
            assert "answer" in item

    def test_uses_reading_model(self):
        with patch("logic.generate_content") as mock_gen:
            mock_gen.return_value = self.QA_JSON
            generate_comprehension_questions("article text", FAKE_CONTEXT)
        assert mock_gen.call_args.kwargs.get("use_reading_model") is True

    def test_article_text_in_prompt(self):
        with patch("logic.generate_content") as mock_gen:
            mock_gen.return_value = self.QA_JSON
            generate_comprehension_questions("UNIQUE_ARTICLE_TEXT", FAKE_CONTEXT)
        prompt = mock_gen.call_args.args[0]
        assert "UNIQUE_ARTICLE_TEXT" in prompt

    def test_bad_json_returns_empty_list(self):
        with patch("logic.generate_content", return_value="not json"):
            result = generate_comprehension_questions("article text", FAKE_CONTEXT)
        assert result == []


# ===========================================================================
# grade_reading_ai
# ===========================================================================

class TestGradeReadingAi:

    PASS_RESPONSE = json.dumps({
        "is_correct": True,
        "feedback": "Well done.",
        "detailed_explanation": "The answer correctly identifies the subject.",
    })
    FAIL_RESPONSE = json.dumps({
        "is_correct": False,
        "feedback": "You copy-pasted the passage. Use your own words.",
        "detailed_explanation": "Verbatim copy detected.",
    })

    def test_correct_answer_returns_is_correct_true(self):
        with patch("logic.generate_content", return_value=self.PASS_RESPONSE):
            result = grade_reading_ai("question", "article", "answer", FAKE_CONTEXT)
        assert result["is_correct"] is True

    def test_copy_paste_answer_can_be_marked_incorrect(self):
        with patch("logic.generate_content", return_value=self.FAIL_RESPONSE):
            result = grade_reading_ai("question", "article", "article", FAKE_CONTEXT)
        assert result["is_correct"] is False

    def test_result_has_all_required_keys(self):
        with patch("logic.generate_content", return_value=self.PASS_RESPONSE):
            result = grade_reading_ai("q", "text", "answer", FAKE_CONTEXT)
        assert "is_correct" in result
        assert "feedback" in result
        assert "detailed_explanation" in result

    def test_uses_reading_model(self):
        with patch("logic.generate_content") as mock_gen:
            mock_gen.return_value = self.PASS_RESPONSE
            grade_reading_ai("q", "text", "a", FAKE_CONTEXT)
        assert mock_gen.call_args.kwargs.get("use_reading_model") is True

    def test_question_and_article_in_prompt(self):
        with patch("logic.generate_content") as mock_gen:
            mock_gen.return_value = self.PASS_RESPONSE
            grade_reading_ai("UNIQUE_QUESTION", "UNIQUE_ARTICLE", "user_answer", FAKE_CONTEXT)
        prompt = mock_gen.call_args.args[0]
        assert "UNIQUE_QUESTION" in prompt
        assert "UNIQUE_ARTICLE" in prompt

    def test_bad_json_returns_fallback_dict(self):
        with patch("logic.generate_content", return_value="oops"):
            result = grade_reading_ai("q", "text", "a", FAKE_CONTEXT)
        assert isinstance(result, dict)
        assert result["is_correct"] is False
        assert "detailed_explanation" in result
