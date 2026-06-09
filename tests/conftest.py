"""
Shared pytest fixtures for KannadaBhasheyaGuru test suite.
"""
import json
import base64
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# OpenAI / Sarvam chat response helpers
# ---------------------------------------------------------------------------

def _make_openai_response(content: str) -> MagicMock:
    """Build a minimal mock that matches openai.ChatCompletion structure."""
    mock = MagicMock()
    mock.choices[0].message.content = content
    return mock


@pytest.fixture
def make_openai_response():
    """Factory: create a mock OpenAI response with arbitrary text content."""
    return _make_openai_response


@pytest.fixture
def mock_sarvam_client(make_openai_response):
    """
    Factory: returns a configured mock _sarvam_chat_client() return value.

    Usage::

        client = mock_sarvam_client('{"kannada": "...", "english": "...", "errors": []}')
        with patch('logic._sarvam_chat_client', return_value=client):
            result = logic.generate_chat_turn_ai(...)
    """
    def _factory(response_content: str) -> MagicMock:
        client = MagicMock()
        client.chat.completions.create.return_value = make_openai_response(response_content)
        return client

    return _factory


# ---------------------------------------------------------------------------
# Fake audio bytes (minimal valid-ish WAV header)
# ---------------------------------------------------------------------------

FAKE_WAV_BYTES = b"RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
FAKE_WAV_B64 = base64.b64encode(FAKE_WAV_BYTES).decode()


@pytest.fixture
def fake_wav_bytes():
    return FAKE_WAV_BYTES


@pytest.fixture
def fake_wav_b64():
    return FAKE_WAV_B64


# ---------------------------------------------------------------------------
# Sample data fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_chat_history():
    return [
        {"role": "user", "content": "ನಮಸ್ಕಾರ"},
        {"role": "assistant", "content": json.dumps({
            "kannada": "ನಮಸ್ಕಾರ! ಹೇಗಿದ್ದೀರಿ?",
            "english": "Hello! How are you?",
            "errors": [],
        })},
    ]


@pytest.fixture
def sample_knowledge_base():
    return (
        "\n--- SOURCE: 1. case_suffixes_in_kannada.md ---\n"
        "Nominative: subject of sentence.\n"
        "Accusative: direct object.\n"
    )


@pytest.fixture
def mock_sheet():
    """A mock gspread Sheet object with configurable records."""
    sheet = MagicMock()
    sheet.get_all_records.return_value = [
        {"Topic": "Case Suffixes",  "Status": "",        "Date Sent": ""},
        {"Topic": "Verb Tenses",    "Status": "Sent",    "Date Sent": "2024-01-01"},
        {"Topic": "Negation",       "Status": "Mastered","Date Sent": "2024-01-05"},
    ]
    return sheet
