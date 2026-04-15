"""
Layer 2 — Sarvam STT and TTS tests (all network calls mocked).

Both functions use requests.post internally. We patch logic.requests.post
to control responses without hitting the network.
"""
import base64
import json
from unittest.mock import MagicMock, patch, ANY

import pytest
import requests

import config
import logic
from logic import sarvam_speech_to_text, sarvam_text_to_speech

FAKE_WAV = b"RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_post_response(json_body: dict, status_code: int = 200) -> MagicMock:
    """Build a mock requests.Response that returns json_body on .json()."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body
    resp.raise_for_status.return_value = None  # no-op for success
    return resp


def _mock_http_error(status_code: int, body: dict | str) -> MagicMock:
    """Build a mock response that raises HTTPError on raise_for_status()."""
    resp = MagicMock()
    resp.status_code = status_code

    err = requests.exceptions.HTTPError()
    err.response = MagicMock()
    err.response.status_code = status_code
    if isinstance(body, dict):
        err.response.json.return_value = body
        err.response.text = json.dumps(body)
    else:
        err.response.json.side_effect = ValueError("not json")
        err.response.text = body
    resp.raise_for_status.side_effect = err
    return resp


# ===========================================================================
# sarvam_speech_to_text
# ===========================================================================

class TestSarvamSpeechToText:

    def test_success_returns_transcript(self):
        mock_resp = _mock_post_response({"transcript": "ನಮಸ್ಕಾರ", "language_code": "kn-IN"})
        with patch("logic.requests.post", return_value=mock_resp):
            result = sarvam_speech_to_text(FAKE_WAV)
        assert result["transcript"] == "ನಮಸ್ಕಾರ"

    def test_success_returns_language_code(self):
        mock_resp = _mock_post_response({"transcript": "ನಮಸ್ಕಾರ", "language_code": "kn-IN"})
        with patch("logic.requests.post", return_value=mock_resp):
            result = sarvam_speech_to_text(FAKE_WAV)
        assert result["language"] == "kn-IN"

    def test_success_result_has_no_error_key(self):
        mock_resp = _mock_post_response({"transcript": "ಸರಿ", "language_code": "kn-IN"})
        with patch("logic.requests.post", return_value=mock_resp):
            result = sarvam_speech_to_text(FAKE_WAV)
        assert "error" not in result

    def test_empty_transcript_returns_error(self):
        mock_resp = _mock_post_response({"transcript": "", "language_code": "kn-IN"})
        with patch("logic.requests.post", return_value=mock_resp):
            result = sarvam_speech_to_text(FAKE_WAV)
        assert "error" in result
        assert "empty" in result["error"].lower() or "transcript" in result["error"].lower()

    def test_whitespace_only_transcript_returns_error(self):
        mock_resp = _mock_post_response({"transcript": "   ", "language_code": "kn-IN"})
        with patch("logic.requests.post", return_value=mock_resp):
            result = sarvam_speech_to_text(FAKE_WAV)
        assert "error" in result

    def test_timeout_returns_error_dict(self):
        with patch("logic.requests.post", side_effect=requests.exceptions.Timeout()):
            result = sarvam_speech_to_text(FAKE_WAV)
        assert "error" in result
        assert "timed out" in result["error"].lower()

    def test_http_error_returns_error_dict(self):
        mock_resp = _mock_http_error(401, {"message": "Unauthorized"})
        with patch("logic.requests.post", return_value=mock_resp):
            result = sarvam_speech_to_text(FAKE_WAV)
        assert "error" in result
        assert "401" in result["error"]

    def test_missing_api_key_returns_error_without_network_call(self, monkeypatch):
        monkeypatch.setattr(config, "SARVAM_API_KEY", None)
        with patch("logic.requests.post") as mock_post:
            result = sarvam_speech_to_text(FAKE_WAV)
        assert "error" in result
        mock_post.assert_not_called()

    def test_sends_to_correct_endpoint(self):
        mock_resp = _mock_post_response({"transcript": "ಸರಿ", "language_code": "kn-IN"})
        with patch("logic.requests.post", return_value=mock_resp) as mock_post:
            sarvam_speech_to_text(FAKE_WAV)
        url = mock_post.call_args.args[0]
        assert url.endswith("/speech-to-text")

    def test_sends_correct_language_code(self):
        mock_resp = _mock_post_response({"transcript": "ಸರಿ", "language_code": "kn-IN"})
        with patch("logic.requests.post", return_value=mock_resp) as mock_post:
            sarvam_speech_to_text(FAKE_WAV)
        data_arg = mock_post.call_args.kwargs.get("data") or mock_post.call_args[1].get("data")
        assert data_arg["language_code"] == config.SARVAM_STT_LANGUAGE

    def test_general_exception_returns_error_dict(self):
        with patch("logic.requests.post", side_effect=ConnectionError("refused")):
            result = sarvam_speech_to_text(FAKE_WAV)
        assert "error" in result

    def test_language_code_falls_back_to_config_default(self):
        # When API doesn't return language_code, config default is used
        mock_resp = _mock_post_response({"transcript": "ಸರಿ"})
        with patch("logic.requests.post", return_value=mock_resp):
            result = sarvam_speech_to_text(FAKE_WAV)
        assert result.get("language") == config.SARVAM_STT_LANGUAGE


# ===========================================================================
# sarvam_text_to_speech
# ===========================================================================

class TestSarvamTextToSpeech:

    KANNADA_TEXT = "ನಮಸ್ಕಾರ, ಹೇಗಿದ್ದೀರಿ?"
    ENCODED_AUDIO = base64.b64encode(FAKE_WAV).decode()

    def test_success_returns_audio_bytes(self):
        mock_resp = _mock_post_response({"audios": [self.ENCODED_AUDIO]})
        with patch("logic.requests.post", return_value=mock_resp):
            result = sarvam_text_to_speech(self.KANNADA_TEXT)
        assert "audio_bytes" in result
        assert result["audio_bytes"] == FAKE_WAV

    def test_success_result_has_no_error_key(self):
        mock_resp = _mock_post_response({"audios": [self.ENCODED_AUDIO]})
        with patch("logic.requests.post", return_value=mock_resp):
            result = sarvam_text_to_speech(self.KANNADA_TEXT)
        assert "error" not in result

    def test_decodes_base64_correctly(self):
        payload_bytes = b"CUSTOM_AUDIO_BYTES"
        encoded = base64.b64encode(payload_bytes).decode()
        mock_resp = _mock_post_response({"audios": [encoded]})
        with patch("logic.requests.post", return_value=mock_resp):
            result = sarvam_text_to_speech(self.KANNADA_TEXT)
        assert result["audio_bytes"] == payload_bytes

    def test_empty_text_returns_error_without_network_call(self):
        with patch("logic.requests.post") as mock_post:
            result = sarvam_text_to_speech("")
        assert "error" in result
        mock_post.assert_not_called()

    def test_whitespace_only_text_returns_error(self):
        with patch("logic.requests.post") as mock_post:
            result = sarvam_text_to_speech("   ")
        assert "error" in result
        mock_post.assert_not_called()

    def test_text_truncated_to_2500_chars(self):
        long_text = "ಅ" * 3000
        mock_resp = _mock_post_response({"audios": [self.ENCODED_AUDIO]})
        with patch("logic.requests.post", return_value=mock_resp) as mock_post:
            sarvam_text_to_speech(long_text)
        payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        assert len(payload["text"]) == 2500

    def test_text_under_2500_chars_not_truncated(self):
        short_text = "ಅ" * 100
        mock_resp = _mock_post_response({"audios": [self.ENCODED_AUDIO]})
        with patch("logic.requests.post", return_value=mock_resp) as mock_post:
            sarvam_text_to_speech(short_text)
        payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        assert len(payload["text"]) == 100

    def test_custom_speaker_sent_in_payload(self):
        mock_resp = _mock_post_response({"audios": [self.ENCODED_AUDIO]})
        with patch("logic.requests.post", return_value=mock_resp) as mock_post:
            sarvam_text_to_speech(self.KANNADA_TEXT, speaker="amit")
        payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        assert payload["speaker"] == "amit"

    def test_custom_pace_sent_in_payload(self):
        mock_resp = _mock_post_response({"audios": [self.ENCODED_AUDIO]})
        with patch("logic.requests.post", return_value=mock_resp) as mock_post:
            sarvam_text_to_speech(self.KANNADA_TEXT, pace=1.5)
        payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        assert payload["pace"] == 1.5

    def test_default_speaker_used_when_not_specified(self):
        mock_resp = _mock_post_response({"audios": [self.ENCODED_AUDIO]})
        with patch("logic.requests.post", return_value=mock_resp) as mock_post:
            sarvam_text_to_speech(self.KANNADA_TEXT)
        payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        assert payload["speaker"] == config.SARVAM_TTS_SPEAKER

    def test_timeout_returns_error_dict(self):
        with patch("logic.requests.post", side_effect=requests.exceptions.Timeout()):
            result = sarvam_text_to_speech(self.KANNADA_TEXT)
        assert "error" in result
        assert "timed out" in result["error"].lower()

    def test_http_error_returns_error_dict(self):
        mock_resp = _mock_http_error(400, {"message": "Bad request"})
        with patch("logic.requests.post", return_value=mock_resp):
            result = sarvam_text_to_speech(self.KANNADA_TEXT)
        assert "error" in result
        assert "400" in result["error"]

    def test_empty_audios_list_returns_error(self):
        mock_resp = _mock_post_response({"audios": []})
        with patch("logic.requests.post", return_value=mock_resp):
            result = sarvam_text_to_speech(self.KANNADA_TEXT)
        assert "error" in result

    def test_missing_api_key_returns_error_without_network_call(self, monkeypatch):
        monkeypatch.setattr(config, "SARVAM_API_KEY", None)
        with patch("logic.requests.post") as mock_post:
            result = sarvam_text_to_speech(self.KANNADA_TEXT)
        assert "error" in result
        mock_post.assert_not_called()

    def test_sends_to_correct_endpoint(self):
        mock_resp = _mock_post_response({"audios": [self.ENCODED_AUDIO]})
        with patch("logic.requests.post", return_value=mock_resp) as mock_post:
            sarvam_text_to_speech(self.KANNADA_TEXT)
        url = mock_post.call_args.args[0]
        assert url.endswith("/text-to-speech")

    def test_sends_correct_language_code(self):
        mock_resp = _mock_post_response({"audios": [self.ENCODED_AUDIO]})
        with patch("logic.requests.post", return_value=mock_resp) as mock_post:
            sarvam_text_to_speech(self.KANNADA_TEXT)
        payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        assert payload["target_language_code"] == config.SARVAM_TTS_LANGUAGE
