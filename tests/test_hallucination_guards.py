"""
Anti-hallucination guard tests.

The chat model sometimes reports 'errors' quoting text the user never wrote
(hallucinated corrections). _filter_hallucinated_errors() is the deterministic
defence: an error survives only if its 'original' actually occurs in the
user's message. These tests cover the helper directly and its wiring inside
generate_chat_turn_ai (mocked client — no network).
"""
import json
from unittest.mock import MagicMock, patch

import pytest

import config
from logic import _filter_hallucinated_errors, generate_chat_turn_ai


def _err(original, correction="ಸರಿ", reason="r"):
    return {"original": original, "correction": correction, "reason": reason}


def _make_client(response_text):
    client = MagicMock()
    client.chat.completions.create.return_value.choices[0].message.content = response_text
    return client


# ===========================================================================
# _filter_hallucinated_errors — unit
# ===========================================================================

class TestFilterHallucinatedErrors:

    # Note the ZWNJ inside ಮಾರ್ಕೆಟ್‌ಗೆ — a realistic user-typed message.
    MSG = "ನಾನು ನಿನ್ನೆ ಮಾರ್ಕೆಟ್‌ಗೆ ಹೋಗಿದ್ದೆ."

    def test_present_original_kept(self):
        errs = [_err("ಹೋಗಿದ್ದೆ")]
        kept, dropped = _filter_hallucinated_errors(errs, self.MSG)
        assert kept == errs and dropped == []

    def test_absent_original_dropped(self):
        errs = [_err("ಬರುತ್ತೇನೆ")]  # nowhere in MSG
        kept, dropped = _filter_hallucinated_errors(errs, self.MSG)
        assert kept == [] and dropped == errs

    def test_mixed_list_keeps_only_genuine(self):
        genuine, fake = _err("ನಿನ್ನೆ"), _err("ನಾಳೆ ಹೋಗ್ತೀನಿ")
        kept, dropped = _filter_hallucinated_errors([fake, genuine], self.MSG)
        assert kept == [genuine] and dropped == [fake]

    def test_punctuation_and_quote_differences_still_kept(self):
        kept, _ = _filter_hallucinated_errors(
            [_err('"ಹೋಗಿದ್ದೆ."'), _err("“ನಿನ್ನೆ”!")], self.MSG)
        assert len(kept) == 2

    def test_zwnj_difference_still_kept(self):
        # Model quotes the word without the ZWNJ the user typed.
        kept, _ = _filter_hallucinated_errors([_err("ಮಾರ್ಕೆಟ್ಗೆ")], self.MSG)
        assert len(kept) == 1

    def test_multiword_original_with_whitespace_noise_kept(self):
        kept, _ = _filter_hallucinated_errors(
            [_err("ನಿನ್ನೆ ಮಾರ್ಕೆಟ್‌ಗೆ  ಹೋಗಿದ್ದೆ")], self.MSG)
        assert len(kept) == 1

    def test_english_word_flag_kept(self):
        # Flagging English words the user actually wrote is a genuine error.
        msg = "ನಾನು tomorrow ಬರ್ತೀನಿ."
        kept, _ = _filter_hallucinated_errors([_err("tomorrow", "ನಾಳೆ")], msg)
        assert len(kept) == 1

    def test_roman_user_message_kannada_original_kept(self):
        # Roman-typing users: the model may quote the Kannada-script rendering
        # of their words; the transliteration fallback must keep it.
        msg = "nanu market ge hogidde"
        kept, dropped = _filter_hallucinated_errors([_err("ಹೋಗಿದ್ದೆ")], msg)
        assert len(kept) == 1, dropped

    def test_kannada_original_absent_from_roman_message_dropped(self):
        msg = "nanu market ge hogidde"
        kept, dropped = _filter_hallucinated_errors([_err("ಬರುತ್ತೇನೆ")], msg)
        assert kept == [] and len(dropped) == 1

    def test_malformed_entries_dropped_without_raising(self):
        errs = ["not a dict", {"correction": "ಸರಿ"}, _err(""), _err(None), 42]
        kept, dropped = _filter_hallucinated_errors(errs, self.MSG)
        assert kept == [] and dropped == errs

    def test_non_list_errors_yield_empty(self):
        assert _filter_hallucinated_errors(None, self.MSG) == ([], [])
        assert _filter_hallucinated_errors("oops", self.MSG) == ([], [])
        assert _filter_hallucinated_errors({"original": "x"}, self.MSG) == ([], [])

    def test_empty_list_passes_through(self):
        assert _filter_hallucinated_errors([], self.MSG) == ([], [])

    def test_empty_user_message_drops_everything(self):
        kept, dropped = _filter_hallucinated_errors([_err("ಏನೋ")], "")
        assert kept == [] and len(dropped) == 1


# ===========================================================================
# generate_chat_turn_ai — guard wiring (end-to-end through the mocked client)
# ===========================================================================

class TestChatTurnGuardIntegration:

    USER_MSG = "ನಾನ್ ನಿನ್ನೆ ಸಿನಿಮಾ ನೋಡಿದೆ."

    def _turn(self, response_json):
        client = _make_client(response_json)
        with patch("logic._sarvam_chat_client", return_value=client):
            return generate_chat_turn_ai(
                self.USER_MSG, [], config.GRAMMAR_GOALS[0],
                "The Shopkeeper", "Kannada (Script)")

    def test_fabricated_error_is_filtered_out(self):
        response = json.dumps({
            "kannada": "ಸರಿ", "english": "OK",
            "errors": [_err("ನಾನು ಹೋಗುತ್ತಿದ್ದೇನೆ")],  # user never wrote this
        })
        result = self._turn(response)
        assert result["user_errors"] == []

    def test_genuine_error_survives_alongside_fabricated(self):
        genuine = _err("ನಾನ್", "ನಾನು", "colloquial shortening")
        fake = _err("ನಾವು ಬಂದೆವು", "ನಾವು ಬಂದಿದ್ದೇವೆ", "fabricated")
        response = json.dumps({
            "kannada": "ಸರಿ", "english": "OK", "errors": [genuine, fake],
        })
        result = self._turn(response)
        assert result["user_errors"] == [genuine]

    def test_raw_text_preserves_pre_guard_errors(self):
        # Diagnostics/live canaries need the unfiltered model output.
        fake = _err("ಎಲ್ಲಿಯೂ ಇಲ್ಲದ ಪದ")
        response = json.dumps({
            "kannada": "ಸರಿ", "english": "OK", "errors": [fake],
        })
        result = self._turn(response)
        assert result["user_errors"] == []
        assert json.loads(result["raw_text"])["errors"] == [fake]

    def test_non_list_errors_field_coerced_to_empty(self):
        response = json.dumps({
            "kannada": "ಸರಿ", "english": "OK", "errors": "ನಾನ್ is wrong",
        })
        result = self._turn(response)
        assert result["user_errors"] == []
