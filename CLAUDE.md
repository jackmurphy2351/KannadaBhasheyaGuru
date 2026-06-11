# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
streamlit run main.py
```

App runs at `http://localhost:8501`.

## Architecture

Four-file Python/Streamlit app:

- **`main.py`** — Streamlit UI (sidebar navigation, session state, custom CSS). Six modes: Home, Conversation Practice (Text + Voice Chat tabs), Send Email Lesson, Mastery Quiz, Writing Critique, Reading Comprehension.
- **`logic.py`** — All backend logic: Sarvam chat completions API calls, Sarvam STT/TTS REST calls, Google Sheets read/write, Gmail SMTP, quiz grading, text critique, transliteration.
- **`config.py`** — Centralized config: API key loading (Streamlit Secrets or `.env`), Sarvam model settings (incl. `SARVAM_MAX_TOKENS`), Sarvam voice options, UI translation strings (4 language modes), character personas, grammar topics, quiz topic→doc mapping.
- **`storage.py`** — Portable local-data layer (no Streamlit/Google deps). Persists quiz mastery to `data/progress.json`.

### Key Design Decisions

**LLM Output Parsing:** `generate_chat_turn_ai()` in `logic.py` uses `response_format={"type": "json_object"}` with the Sarvam chat completions API. The model returns a JSON object with `kannada`, `english`, and `errors` keys. `clean_json()` in `logic.py` parses it deterministically (handles markdown-fenced responses). The earlier plain-text `KANNADA:`/`ENGLISH:`/`ERRORS:` label approach was abandoned because sarvam-30b frequently dropped the labels; `json_object` mode is significantly more reliable.

**Anti-Hallucination Guard (chat errors):** The model has historically invented "corrections" for text the user never wrote. `_filter_hallucinated_errors()` in `logic.py` drops any reported error whose `original` does not actually occur in the user's message (lenient matching: NFC, punctuation/zero-width stripped, whitespace collapsed, plus a Roman-transliteration fallback for Roman-typed input). It runs inside `generate_chat_turn_ai()`, so Text Chat, Voice Chat, and the post-chat error quiz are all covered. Tests: `tests/test_hallucination_guards.py`.

**API Retries & Token Cap:** Sarvam transiently returns `finish_reason="length"` with zero visible output (hidden tokens consume the completion budget). Both `generate_chat_turn_ai()` and `generate_content()` retry up to 3 attempts with identical messages. `config.SARVAM_MAX_TOKENS = 4096` is the starter-tier hard cap — requests above it fail with HTTP 400, so never "fix" truncation by raising it.

**Deterministic Mastery Quiz:** Questions come from the fixed bank `knowledge_base/quiz_bank.json` (200 items, 12 topics; validated on load), not from the LLM and not from Google Sheets. Correctness is decided by `check_answer()` normalization against each item's `acceptable` forms; only non-matches get one constrained yes/no LLM check (`judge_equivalence`, fail-closed) — the LLM never supplies its own answer. Mastery persists locally via `storage.py`. Token folding in `normalize_answer()`: ಅಂತ/ಅಂತಾ/ಎಂದು are interchangeable quotatives; ಅಂತೆ (hearsay) and ಎಂಬ (naming-only, never reported speech — explicit user correction) must NEVER be folded.

**Voice Chat Always Uses Kannada Script:** The TTS API requires Kannada Script input, so voice chat mode forces `Kannada (Script)` internally regardless of the user's display preference.

**Knowledge Base Context:** The `knowledge_base/` directory holds grammar reference docs (`.md` foundation/lesson files plus legacy `.txt`) and `quiz_bank.json`. `load_knowledge_base()` injects all docs as LLM context for broad calls; the quiz scopes context to the selected topic's doc(s) via `load_topic_doc()`.

**4 Language Display Modes:** UI text and chat output can render as English, Kannada Script, Kannada Roman (Natural/colloquial), or Kannada Roman (Strict/IAST). The `toggle_script()` function and `indic-transliteration` library handle conversions.

### External Dependencies

| Service | Purpose | Notes |
|---|---|---|
| Sarvam AI chat (`sarvam-30b`) | Conversation, grading, quizzes, critiques | OpenAI-compatible endpoint; `json_object` mode for chat turns |
| Sarvam AI chat (`sarvam-105b`) | Reading comprehension | 128K context; used via `use_reading_model=True` flag in `generate_content()` |
| Sarvam AI STT | Audio → Kannada transcript | Max 30s/request, WAV input |
| Sarvam AI TTS | Kannada text → audio | Max 2500 chars/request, base64 WAV output |
| Google Sheets + Drive | Email-lesson schedule tracking | Requires `service_account.json` |
| Gmail SMTP | Email lesson delivery | Requires Gmail App Password |

### Credentials

Required in `.env` (local) or Streamlit Secrets (deployed):
- `SARVAM_API_KEY` (covers both chat completions and STT/TTS)
- `GOOGLE_SHEET_NAME`
- `GMAIL_USER` / `GMAIL_PASSWORD`
- `service_account.json` in project root (Google Cloud service account)

### Google Sheets Schema

The tracker sheet needs columns: `Topic`, `Status`, `Date Sent`. It is used only by the email-lesson flow: `send_email_lesson()` picks the first row with an empty `Status` and marks it `"Sent"`. Quiz mastery is NOT tracked in Sheets — it lives in `data/progress.json` via `storage.py`.

## Testing

```bash
python -m pytest -q          # full mocked suite (~1,077 tests, ~1.5s, no network)
python -m pytest -m live -q  # opt-in canaries against the real Sarvam API (costs credits)
```

Live tests (`tests/test_live_llm.py`) are deselected by default via `addopts = -m "not live"` in `pytest.ini`. They verify the real model never hallucinates corrections; do NOT assert on model *sensitivity* (whether it flags a given mistake) — that is nondeterministic on sarvam-30b.
