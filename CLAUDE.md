# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
streamlit run main.py
```

App runs at `http://localhost:8501`.

## Architecture

Three-file Python/Streamlit app:

- **`main.py`** — Streamlit UI (sidebar navigation, session state, custom CSS). Six modes: Home, Conversation Practice (Text + Voice Chat tabs), Send Email Lesson, Mastery Quiz, Writing Critique, Reading Comprehension.
- **`logic.py`** — All backend logic: Sarvam chat completions API calls, Sarvam STT/TTS REST calls, Google Sheets read/write, Gmail SMTP, quiz grading, text critique, transliteration.
- **`config.py`** — Centralized config: API key loading (Streamlit Secrets or `.env`), Sarvam model settings, Sarvam voice options, UI translation strings (4 language modes), character personas, grammar topics.

### Key Design Decisions

**LLM Output Parsing:** `generate_chat_turn_ai()` in `logic.py` uses `response_format={"type": "json_object"}` with the Sarvam chat completions API. The model returns a JSON object with `kannada`, `english`, and `errors` keys. `clean_json()` in `logic.py` parses it deterministically (handles markdown-fenced responses). The earlier plain-text `KANNADA:`/`ENGLISH:`/`ERRORS:` label approach was abandoned because sarvam-30b frequently dropped the labels; `json_object` mode is significantly more reliable.

**Voice Chat Always Uses Kannada Script:** The TTS API requires Kannada Script input, so voice chat mode forces `Kannada (Script)` internally regardless of the user's display preference.

**Knowledge Base Context:** The `knowledge_base/` directory holds 12 grammar reference `.txt` files. `load_knowledge_base()` injects all of them into Gemini's context for every relevant call to enforce grammatical accuracy.

**4 Language Display Modes:** UI text and chat output can render as English, Kannada Script, Kannada Roman (Natural/colloquial), or Kannada Roman (Strict/IAST). The `toggle_script()` function and `indic-transliteration` library handle conversions.

### External Dependencies

| Service | Purpose | Notes |
|---|---|---|
| Sarvam AI chat (`sarvam-30b`) | Conversation, grading, quizzes, critiques | OpenAI-compatible endpoint; `json_object` mode for chat turns |
| Sarvam AI chat (`sarvam-105b`) | Reading comprehension | 128K context; used via `use_reading_model=True` flag in `generate_content()` |
| Sarvam AI STT | Audio → Kannada transcript | Max 30s/request, WAV input |
| Sarvam AI TTS | Kannada text → audio | Max 2500 chars/request, base64 WAV output |
| Google Sheets + Drive | Lesson tracking, mastery status | Requires `service_account.json` |
| Gmail SMTP | Email lesson delivery | Requires Gmail App Password |

### Credentials

Required in `.env` (local) or Streamlit Secrets (deployed):
- `SARVAM_API_KEY` (covers both chat completions and STT/TTS)
- `GOOGLE_SHEET_NAME`
- `GMAIL_USER` / `GMAIL_PASSWORD`
- `service_account.json` in project root (Google Cloud service account)

### Google Sheets Schema

The tracker sheet needs columns: `Topic`, `Status`, `Date Sent`. Status values used in code: `"Sent"` (quiz-eligible), `"Mastered"` (scored 90%+).
