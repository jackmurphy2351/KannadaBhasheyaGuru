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
from logic import get_sheet_client


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
