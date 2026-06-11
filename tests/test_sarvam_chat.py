"""
Layer 2 — Sarvam chat API tests (all network calls mocked).

Strategy:
  - generate_content / generate_chat_turn_ai: mock logic._sarvam_chat_client
  - All higher-level functions (grade_answer_ai, critique_text_ai, etc.):
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

    def test_empty_response_retries_then_succeeds(self):
        # Sarvam's transient empty completion (finish_reason="length",
        # 0 chars) must be retried, not returned to the caller.
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [_resp(""), _resp("ಸರಿ")]
        with patch("logic._sarvam_chat_client", return_value=mock_client):
            result = generate_content("prompt", FAKE_CONTEXT)
        assert result == "ಸರಿ"
        assert mock_client.chat.completions.create.call_count == 2

    def test_none_content_retries_then_succeeds(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [_resp(None), _resp("ok")]
        with patch("logic._sarvam_chat_client", return_value=mock_client):
            assert generate_content("prompt", FAKE_CONTEXT) == "ok"

    def test_exception_then_success_recovers(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [
            Exception("timeout"), _resp("recovered")]
        with patch("logic._sarvam_chat_client", return_value=mock_client):
            assert generate_content("prompt", FAKE_CONTEXT) == "recovered"

    def test_persistently_empty_returns_empty_after_all_attempts(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [
            _resp(""), _resp(""), _resp("")]
        with patch("logic._sarvam_chat_client", return_value=mock_client):
            result = generate_content("prompt", FAKE_CONTEXT)
        assert result == ""
        assert mock_client.chat.completions.create.call_count == 3

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
        # The flagged 'original' must actually be in the user's message —
        # otherwise the hallucination guard (correctly) drops it.
        chat_json_with_error = json.dumps({
            "kannada": "ಸರಿ",
            "english": "OK",
            "errors": [{"original": "ನಾನ್", "correction": "ನಾನು", "reason": "Typo"}],
        })
        client = _make_client(chat_json_with_error)
        result = self._call(client, user_message="ನಾನ್ ಬರ್ತೀನಿ.")
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
        # Roman display modes inject the AADUMAATU (spoken/colloquial) track, not
        # the formal-script track. Assert on the full instruction phrases, which
        # are unique to each track string (bare words like "Aadumaatu" can also
        # appear in injected persona cards).
        assert "Spoken Kannada (Aadumaatu)" in system_text
        assert "Standard/Formal Kannada (Granthika)" not in system_text

    def test_script_lang_mode_uses_formal_schema(self):
        mock_client = _make_client(CHAT_JSON)
        with patch("logic._sarvam_chat_client", return_value=mock_client):
            generate_chat_turn_ai(
                "msg", [], config.GRAMMAR_GOALS[0],
                "The Train Conductor", "Kannada (Script)"
            )
        messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
        system_text = next(m["content"] for m in messages if m["role"] == "system")
        # Script mode injects the formal-script track, not the aadumaatu track.
        # Mirror the Roman test: assert on the full instruction phrases, which are
        # unique to each track string (bare words can also appear in persona cards).
        assert "Standard/Formal Kannada (Granthika)" in system_text
        assert "Spoken Kannada (Aadumaatu)" not in system_text

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
# generate_chat_turn_ai — retry robustness (MAX_ATTEMPTS = 3)
# Bad/empty/exceptional responses must NOT surface an error to the user
# until every attempt is exhausted; truncation (finish_reason="length")
# escalates max_tokens, observed live with Sarvam on 2026-06-11.
# ===========================================================================

def _resp(content, finish="stop"):
    """Mock one chat.completions.create() response with a finish_reason."""
    r = MagicMock()
    r.choices[0].message.content = content
    r.choices[0].finish_reason = finish
    return r


def _make_client_seq(*responses):
    """Client whose create() yields each response (or raises Exceptions) in order."""
    client = MagicMock()
    client.chat.completions.create.side_effect = [
        r if isinstance(r, Exception) else _resp(r) for r in responses
    ]
    return client


class TestChatTurnRetries:

    def _call(self, mock_client, *, user_message="ನನ್ನ ಹೆಸರು ಜಾನ್."):
        with patch("logic._sarvam_chat_client", return_value=mock_client):
            return generate_chat_turn_ai(
                user_message, [], config.GRAMMAR_GOALS[0],
                "The Train Conductor", "Kannada (Script)")

    def test_empty_first_response_retries_and_succeeds(self):
        client = _make_client_seq("", CHAT_JSON)
        result = self._call(client)
        assert result["bot_reply_kannada"] == "ನಮಸ್ಕಾರ! ಟಿಕೆಟ್ ತೋರಿಸಿ."
        assert client.chat.completions.create.call_count == 2

    def test_none_content_first_response_retries_and_succeeds(self):
        client = _make_client_seq(None, CHAT_JSON)
        result = self._call(client)
        assert "error" not in result
        assert client.chat.completions.create.call_count == 2

    def test_non_json_first_response_retries_and_succeeds(self):
        client = _make_client_seq("ಕ್ಷಮಿಸಿ, JSON ಅಲ್ಲ.", CHAT_JSON)
        result = self._call(client)
        assert "error" not in result
        assert client.chat.completions.create.call_count == 2

    def test_missing_kannada_key_first_response_retries_and_succeeds(self):
        bad = json.dumps({"english": "Hi", "errors": []})
        client = _make_client_seq(bad, CHAT_JSON)
        result = self._call(client)
        assert "error" not in result
        assert client.chat.completions.create.call_count == 2

    def test_api_exception_first_attempt_retries_and_succeeds(self):
        client = _make_client_seq(Exception("connection reset"), CHAT_JSON)
        result = self._call(client)
        assert "error" not in result
        assert client.chat.completions.create.call_count == 2

    def test_retry_resends_identical_messages(self):
        client = _make_client_seq("", CHAT_JSON)
        self._call(client)
        first, second = client.chat.completions.create.call_args_list
        assert first.kwargs["messages"] == second.kwargs["messages"]

    def test_length_truncation_retries_within_tier_cap(self):
        # Sarvam's starter tier rejects max_tokens > 4096 with HTTP 400, so a
        # truncated turn must retry at the SAME capped budget, never above it.
        client = MagicMock()
        client.chat.completions.create.side_effect = [
            _resp("", finish="length"), _resp(CHAT_JSON)]
        result = self._call(client)
        assert "error" not in result
        for c in client.chat.completions.create.call_args_list:
            assert c.kwargs["max_tokens"] == config.SARVAM_MAX_TOKENS

    def test_all_bad_responses_returns_diagnostic_error(self):
        client = _make_client_seq("junk one", "junk two", "junk three")
        result = self._call(client)
        assert "error" in result
        assert client.chat.completions.create.call_count == 3
        assert "junk three" in result["error"]  # final raw output surfaced

    def test_all_exceptions_returns_error_dict(self):
        client = _make_client_seq(
            Exception("boom1"), Exception("boom2"), Exception("boom3"))
        result = self._call(client)
        assert result == {"error": "boom3"}


# ===========================================================================
# Verbatim input contract — the user's exact text must reach the LLM
# unaltered (no stripping, escaping, or paraphrase), for every function
# that forwards user-typed content. Past hallucinated 'corrections' make
# this the first line of defence: the model must see what the user wrote.
# ===========================================================================

ADVERSARIAL_INPUTS = [
    'ಅವಳು "ಇಲ್ಲ" ಅಂತ ಹೇಳಿದಳು yesterday',          # straight quotes + English
    "it's {not} JSON: {\"kannada\": \"fake\"}",      # braces + JSON-like text
    "ನಾನು ಮನೆಗೆ\nಹೋಗ್ತೀನಿ\tnow",                    # newline + tab
    "back\\slash ಮತ್ತು ```json fence```",            # backslash + md fence
    "ನಾನು ‘ಬರ್ತೀನಿ’ — okay? 😅",                    # curly quotes + emoji
]


class TestVerbatimInputContract:

    @pytest.mark.parametrize("text", ADVERSARIAL_INPUTS)
    def test_chat_turn_last_message_is_exact_user_text(self, text):
        client = _make_client(CHAT_JSON)
        with patch("logic._sarvam_chat_client", return_value=client):
            generate_chat_turn_ai(text, [], config.GRAMMAR_GOALS[0],
                                  "The Doctor", "Kannada (Script)")
        messages = client.chat.completions.create.call_args.kwargs["messages"]
        assert messages[-1] == {"role": "user", "content": text}

    def test_chat_history_passed_unmodified_and_in_order(self):
        history = [
            {"role": "user", "content": ADVERSARIAL_INPUTS[0]},
            {"role": "assistant", "content": '{"kannada": "ಸರಿ {x}", "english": "ok"}'},
            {"role": "user", "content": ADVERSARIAL_INPUTS[2]},
        ]
        client = _make_client(CHAT_JSON)
        with patch("logic._sarvam_chat_client", return_value=client):
            generate_chat_turn_ai("ಸರಿ", history, config.GRAMMAR_GOALS[0],
                                  "The Doctor", "Kannada (Script)")
        messages = client.chat.completions.create.call_args.kwargs["messages"]
        # system + 3 history turns + new user message, history verbatim.
        assert messages[1:4] == history
        assert messages[-1]["content"] == "ಸರಿ"

    @pytest.mark.parametrize("text", ADVERSARIAL_INPUTS)
    def test_grade_answer_ai_receives_exact_answer(self, text):
        response = json.dumps({"is_correct": True, "feedback": "ok",
                               "correct_translation": "ಸರಿ"})
        with patch("logic.generate_content", return_value=response) as mock_gen:
            grade_answer_ai("I go home.", text, FAKE_CONTEXT)
        assert text in mock_gen.call_args.args[0]

    @pytest.mark.parametrize("text", ADVERSARIAL_INPUTS)
    def test_critique_text_ai_receives_exact_text(self, text):
        response = json.dumps({"analysis": [], "overall_summary": "ok"})
        with patch("logic.generate_content", return_value=response) as mock_gen:
            critique_text_ai(text, "Formal", FAKE_CONTEXT)
        assert text in mock_gen.call_args.args[0]

    @pytest.mark.parametrize("text", ADVERSARIAL_INPUTS)
    def test_grade_reading_ai_receives_exact_answer(self, text):
        response = json.dumps({"is_correct": True, "feedback": "ok",
                               "detailed_explanation": "ok"})
        with patch("logic.generate_content", return_value=response) as mock_gen:
            grade_reading_ai("question", "article", text, FAKE_CONTEXT)
        assert text in mock_gen.call_args.args[0]

    @pytest.mark.parametrize("text", ADVERSARIAL_INPUTS)
    def test_comprehension_questions_receive_exact_article(self, text):
        with patch("logic.generate_content", return_value="[]") as mock_gen:
            generate_comprehension_questions(text, FAKE_CONTEXT)
        assert text in mock_gen.call_args.args[0]


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
