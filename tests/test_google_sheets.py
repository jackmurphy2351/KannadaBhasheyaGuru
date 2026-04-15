"""
Layer 2 — Google Sheets integration tests (all external calls mocked).

get_sheet_client() checks st.secrets then falls back to a local file.
We patch logic.st, logic.ServiceAccountCredentials, and logic.gspread
to prevent any actual Google API traffic.
"""
from unittest.mock import MagicMock, patch, call

import pytest

import config
import logic
from logic import get_sheet_client, get_quiz_data, update_mastery


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sheet_context(*, has_secrets: bool, mock_records: list | None = None):
    """
    Context manager stack that mocks all Google Sheets dependencies.

    Returns (mock_st, mock_creds_cls, mock_gspread, mock_sheet).
    """
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        with patch("logic.st") as mock_st, \
             patch("logic.ServiceAccountCredentials") as mock_creds_cls, \
             patch("logic.gspread") as mock_gspread:

            # Configure st.secrets
            if has_secrets:
                mock_st.secrets = {"gcp_service_account": {"type": "service_account",
                                                            "project_id": "test"}}
            else:
                mock_st.secrets = {}

            # Configure mock sheet
            mock_sheet = MagicMock()
            if mock_records is not None:
                mock_sheet.get_all_records.return_value = mock_records
            mock_gspread.authorize.return_value.open.return_value.sheet1 = mock_sheet

            yield mock_st, mock_creds_cls, mock_gspread, mock_sheet

    return _ctx()


# ===========================================================================
# get_sheet_client
# ===========================================================================

class TestGetSheetClient:

    def test_uses_json_keyfile_dict_when_secrets_present(self):
        with _sheet_context(has_secrets=True) as (_, mock_creds_cls, _, _):
            get_sheet_client()
        mock_creds_cls.from_json_keyfile_dict.assert_called_once()
        mock_creds_cls.from_json_keyfile_name.assert_not_called()

    def test_uses_local_file_when_secrets_absent(self):
        with _sheet_context(has_secrets=False) as (_, mock_creds_cls, _, _):
            get_sheet_client()
        mock_creds_cls.from_json_keyfile_name.assert_called_once()
        mock_creds_cls.from_json_keyfile_dict.assert_not_called()

    def test_local_file_uses_credentials_file_from_config(self):
        with _sheet_context(has_secrets=False) as (_, mock_creds_cls, _, _):
            get_sheet_client()
        call_args = mock_creds_cls.from_json_keyfile_name.call_args
        assert call_args.args[0] == config.CREDENTIALS_FILE

    def test_returns_sheet1(self):
        with _sheet_context(has_secrets=True) as (_, _, mock_gspread, mock_sheet):
            result = get_sheet_client()
        assert result is mock_sheet

    def test_opens_correct_sheet_name(self):
        with _sheet_context(has_secrets=True) as (_, _, mock_gspread, _):
            get_sheet_client()
        mock_gspread.authorize.return_value.open.assert_called_with(config.SHEET_NAME)

    def test_passes_correct_scopes_with_secrets(self):
        with _sheet_context(has_secrets=True) as (_, mock_creds_cls, _, _):
            get_sheet_client()
        call_args = mock_creds_cls.from_json_keyfile_dict.call_args
        scope = call_args.args[1]
        assert "https://spreadsheets.google.com/feeds" in scope
        assert "https://www.googleapis.com/auth/drive" in scope

    def test_passes_correct_scopes_with_local_file(self):
        with _sheet_context(has_secrets=False) as (_, mock_creds_cls, _, _):
            get_sheet_client()
        call_args = mock_creds_cls.from_json_keyfile_name.call_args
        scope = call_args.args[1]
        assert "https://spreadsheets.google.com/feeds" in scope
        assert "https://www.googleapis.com/auth/drive" in scope

    def test_secrets_dict_passed_to_keyfile_dict(self):
        with _sheet_context(has_secrets=True) as (_, mock_creds_cls, _, _):
            get_sheet_client()
        call_args = mock_creds_cls.from_json_keyfile_dict.call_args
        creds_dict = call_args.args[0]
        # dict() of the secrets entry should be passed
        assert creds_dict["type"] == "service_account"


# ===========================================================================
# get_quiz_data
# ===========================================================================

class TestGetQuizData:

    RECORDS = [
        {"Topic": "Case Suffixes",  "Status": "",         "Date Sent": ""},
        {"Topic": "Verb Tenses",    "Status": "Sent",     "Date Sent": "2024-01-01"},
        {"Topic": "Adjectives",     "Status": "Sent",     "Date Sent": "2024-01-03"},
        {"Topic": "Negation",       "Status": "Mastered", "Date Sent": "2024-01-05"},
    ]

    def test_returns_only_sent_topics(self):
        with _sheet_context(has_secrets=False, mock_records=self.RECORDS):
            _, topics = get_quiz_data("context")
        assert len(topics) == 2
        topic_names = [t["topic"] for t in topics]
        assert "Verb Tenses" in topic_names
        assert "Adjectives" in topic_names

    def test_excludes_empty_status_topics(self):
        with _sheet_context(has_secrets=False, mock_records=self.RECORDS):
            _, topics = get_quiz_data("context")
        topic_names = [t["topic"] for t in topics]
        assert "Case Suffixes" not in topic_names

    def test_excludes_mastered_topics(self):
        with _sheet_context(has_secrets=False, mock_records=self.RECORDS):
            _, topics = get_quiz_data("context")
        topic_names = [t["topic"] for t in topics]
        assert "Negation" not in topic_names

    def test_row_numbers_are_1_indexed_offset_by_header(self):
        # Sheet rows: header=1, first data=2, so record index 0 → row 2
        with _sheet_context(has_secrets=False, mock_records=self.RECORDS):
            _, topics = get_quiz_data("context")
        # "Verb Tenses" is record index 1 → row 3
        verb_topic = next(t for t in topics if t["topic"] == "Verb Tenses")
        assert verb_topic["row"] == 3

    def test_no_sent_topics_returns_empty_list(self):
        records = [
            {"Topic": "X", "Status": "", "Date Sent": ""},
            {"Topic": "Y", "Status": "Mastered", "Date Sent": "2024-01-01"},
        ]
        with _sheet_context(has_secrets=False, mock_records=records):
            _, topics = get_quiz_data("context")
        assert topics == []

    def test_exception_returns_none_and_empty_list(self):
        with patch("logic.get_sheet_client", side_effect=Exception("auth failed")):
            sheet, topics = get_quiz_data("context")
        assert sheet is None
        assert topics == []

    def test_returns_sheet_as_first_element(self):
        with _sheet_context(has_secrets=False, mock_records=self.RECORDS) as (_, _, _, mock_sheet):
            sheet, _ = get_quiz_data("context")
        assert sheet is mock_sheet


# ===========================================================================
# update_mastery
# ===========================================================================

class TestUpdateMastery:

    def test_writes_mastered_to_status_column(self):
        with _sheet_context(has_secrets=False) as (_, _, _, mock_sheet):
            with patch("logic.get_sheet_client", return_value=mock_sheet):
                update_mastery(5)
        mock_sheet.update_cell.assert_called_with(5, 2, "Mastered")

    def test_updates_correct_row(self):
        with _sheet_context(has_secrets=False) as (_, _, _, mock_sheet):
            with patch("logic.get_sheet_client", return_value=mock_sheet):
                update_mastery(7)
        call_args = mock_sheet.update_cell.call_args
        assert call_args.args[0] == 7  # row number

    def test_updates_column_2(self):
        with _sheet_context(has_secrets=False) as (_, _, _, mock_sheet):
            with patch("logic.get_sheet_client", return_value=mock_sheet):
                update_mastery(3)
        call_args = mock_sheet.update_cell.call_args
        assert call_args.args[1] == 2  # column index

    def test_value_is_exactly_mastered_string(self):
        with _sheet_context(has_secrets=False) as (_, _, _, mock_sheet):
            with patch("logic.get_sheet_client", return_value=mock_sheet):
                update_mastery(4)
        call_args = mock_sheet.update_cell.call_args
        assert call_args.args[2] == "Mastered"
