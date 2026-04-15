"""
Layer 2 — Email lesson end-to-end tests (all external calls mocked).

send_email_lesson() touches four external systems:
  1. Google Sheets (get_sheet_client + get_all_records + update_cell)
  2. Sarvam chat (generate_content → lesson HTML)
  3. Gmail SMTP (smtplib.SMTP)

All three are mocked so no real network calls occur.
"""
import smtplib
from email.parser import Parser
from unittest.mock import MagicMock, patch, call

import pytest

import config
import logic
from logic import send_email_lesson

FAKE_CONTEXT = "Grammar rule: subjects precede verbs."
FAKE_HTML = "<h1>Kannada Lesson: Case Suffixes</h1><p>Content here.</p>"


# ---------------------------------------------------------------------------
# Helper — standard mock setup for a successful email send
# ---------------------------------------------------------------------------

def _make_mock_sheet(records: list) -> MagicMock:
    sheet = MagicMock()
    sheet.get_all_records.return_value = records
    return sheet


def _standard_records():
    """Three rows: one unsent, one Sent, one Mastered."""
    return [
        {"Topic": "Case Suffixes", "Status": "",        "Date Sent": ""},
        {"Topic": "Verb Tenses",   "Status": "Sent",    "Date Sent": "2024-01-01"},
        {"Topic": "Negation",      "Status": "Mastered","Date Sent": "2024-01-05"},
    ]


# ===========================================================================
# send_email_lesson — topic selection
# ===========================================================================

class TestSendEmailTopicSelection:

    def test_picks_first_row_with_empty_status(self):
        sheet = _make_mock_sheet(_standard_records())
        with patch("logic.get_sheet_client", return_value=sheet), \
             patch("logic.generate_content", return_value=FAKE_HTML), \
             patch("logic.smtplib.SMTP") as mock_smtp_cls:
            mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
            result = send_email_lesson(FAKE_CONTEXT)
        assert "Case Suffixes" in result

    def test_skips_sent_and_mastered_rows(self):
        records = [
            {"Topic": "Done Topic", "Status": "Sent",     "Date Sent": "2024-01-01"},
            {"Topic": "New Topic",  "Status": "",         "Date Sent": ""},
        ]
        sheet = _make_mock_sheet(records)
        with patch("logic.get_sheet_client", return_value=sheet), \
             patch("logic.generate_content", return_value=FAKE_HTML), \
             patch("logic.smtplib.SMTP"):
            result = send_email_lesson(FAKE_CONTEXT)
        assert "New Topic" in result
        assert "Done Topic" not in result

    def test_no_unsent_topics_returns_no_topics_message(self):
        records = [
            {"Topic": "A", "Status": "Sent",     "Date Sent": "2024-01-01"},
            {"Topic": "B", "Status": "Mastered", "Date Sent": "2024-01-02"},
        ]
        sheet = _make_mock_sheet(records)
        with patch("logic.get_sheet_client", return_value=sheet):
            result = send_email_lesson(FAKE_CONTEXT)
        assert "No new topics" in result

    def test_empty_sheet_returns_no_topics_message(self):
        sheet = _make_mock_sheet([])
        with patch("logic.get_sheet_client", return_value=sheet):
            result = send_email_lesson(FAKE_CONTEXT)
        assert "No new topics" in result


# ===========================================================================
# send_email_lesson — content generation
# ===========================================================================

class TestSendEmailContentGeneration:

    def test_topic_name_is_in_generate_content_prompt(self):
        sheet = _make_mock_sheet(_standard_records())
        with patch("logic.get_sheet_client", return_value=sheet), \
             patch("logic.generate_content", return_value=FAKE_HTML) as mock_gen, \
             patch("logic.smtplib.SMTP"):
            send_email_lesson(FAKE_CONTEXT)
        prompt = mock_gen.call_args.args[0]
        assert "Case Suffixes" in prompt

    def test_context_is_passed_to_generate_content(self):
        sheet = _make_mock_sheet(_standard_records())
        with patch("logic.get_sheet_client", return_value=sheet), \
             patch("logic.generate_content", return_value=FAKE_HTML) as mock_gen, \
             patch("logic.smtplib.SMTP"):
            send_email_lesson(FAKE_CONTEXT)
        context_arg = mock_gen.call_args.args[1]
        assert context_arg == FAKE_CONTEXT


# ===========================================================================
# send_email_lesson — email construction & delivery
# ===========================================================================

class TestSendEmailDelivery:

    def _run_success(self, mock_smtp_instance):
        """Run send_email_lesson with standard mocks and a given smtp instance."""
        sheet = _make_mock_sheet(_standard_records())
        with patch("logic.get_sheet_client", return_value=sheet), \
             patch("logic.generate_content", return_value=FAKE_HTML), \
             patch("logic.smtplib.SMTP", return_value=mock_smtp_instance):
            return send_email_lesson(FAKE_CONTEXT)

    def test_email_is_sent_via_starttls(self):
        smtp = MagicMock()
        self._run_success(smtp)
        smtp.starttls.assert_called_once()

    def test_email_is_sent_with_configured_credentials(self):
        smtp = MagicMock()
        self._run_success(smtp)
        smtp.login.assert_called_with(config.SENDER_EMAIL, config.SENDER_PASSWORD)

    def test_email_is_sent_to_receiver(self):
        smtp = MagicMock()
        self._run_success(smtp)
        smtp.sendmail.assert_called_once()
        _, to_addr, _ = smtp.sendmail.call_args.args
        assert to_addr == config.RECEIVER_EMAIL

    def test_email_subject_contains_topic_name(self):
        smtp = MagicMock()
        self._run_success(smtp)
        _, _, raw_msg = smtp.sendmail.call_args.args
        parsed = Parser().parsestr(raw_msg)
        assert "Case Suffixes" in parsed["Subject"]

    def test_email_subject_contains_kannada_lesson(self):
        smtp = MagicMock()
        self._run_success(smtp)
        _, _, raw_msg = smtp.sendmail.call_args.args
        parsed = Parser().parsestr(raw_msg)
        assert "Kannada Lesson" in parsed["Subject"]

    def test_smtp_connection_is_closed_after_send(self):
        smtp = MagicMock()
        self._run_success(smtp)
        smtp.quit.assert_called_once()

    def test_successful_send_returns_success_message(self):
        smtp = MagicMock()
        result = self._run_success(smtp)
        assert "Email sent successfully" in result or "sent" in result.lower()


# ===========================================================================
# send_email_lesson — sheet updates
# ===========================================================================

class TestSendEmailSheetUpdate:

    def test_updates_status_to_sent(self):
        sheet = _make_mock_sheet(_standard_records())
        with patch("logic.get_sheet_client", return_value=sheet), \
             patch("logic.generate_content", return_value=FAKE_HTML), \
             patch("logic.smtplib.SMTP"):
            send_email_lesson(FAKE_CONTEXT)
        # update_cell(row, 2, 'Sent') — row 2 is the first unsent row (header=1, data starts at 2)
        sheet.update_cell.assert_any_call(2, 2, "Sent")

    def test_records_timestamp_in_date_column(self):
        sheet = _make_mock_sheet(_standard_records())
        with patch("logic.get_sheet_client", return_value=sheet), \
             patch("logic.generate_content", return_value=FAKE_HTML), \
             patch("logic.smtplib.SMTP"):
            send_email_lesson(FAKE_CONTEXT)
        # update_cell(row, 3, timestamp_string)
        all_calls = sheet.update_cell.call_args_list
        date_calls = [c for c in all_calls if c.args[1] == 3]
        assert len(date_calls) == 1
        # timestamp should be a non-empty string
        assert date_calls[0].args[2]

    def test_updates_correct_row_number(self):
        # "Case Suffixes" is record index 0 → sheet row 2 (1 header + 1)
        sheet = _make_mock_sheet(_standard_records())
        with patch("logic.get_sheet_client", return_value=sheet), \
             patch("logic.generate_content", return_value=FAKE_HTML), \
             patch("logic.smtplib.SMTP"):
            send_email_lesson(FAKE_CONTEXT)
        status_calls = [c for c in sheet.update_cell.call_args_list if c.args[1] == 2]
        assert status_calls[0].args[0] == 2  # row 2


# ===========================================================================
# send_email_lesson — error handling
# ===========================================================================

class TestSendEmailErrorHandling:

    def test_smtp_exception_returns_error_string(self):
        sheet = _make_mock_sheet(_standard_records())
        with patch("logic.get_sheet_client", return_value=sheet), \
             patch("logic.generate_content", return_value=FAKE_HTML), \
             patch("logic.smtplib.SMTP", side_effect=smtplib.SMTPException("connection refused")):
            result = send_email_lesson(FAKE_CONTEXT)
        assert "Error" in result

    def test_sheet_exception_returns_error_string(self):
        with patch("logic.get_sheet_client", side_effect=Exception("auth failed")):
            result = send_email_lesson(FAKE_CONTEXT)
        assert "Error" in result

    def test_error_does_not_raise_exception(self):
        with patch("logic.get_sheet_client", side_effect=RuntimeError("unexpected")):
            # Should return a string, not propagate the exception
            result = send_email_lesson(FAKE_CONTEXT)
        assert isinstance(result, str)
