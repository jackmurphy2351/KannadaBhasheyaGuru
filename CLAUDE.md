# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
streamlit run main.py
```

App runs at `http://localhost:8501`.

## Architecture

Python/Streamlit app:

- **`main.py`** — Streamlit UI (sidebar navigation, session state, custom CSS). Seven modes: Home, Conversation Practice (Text + Voice Chat tabs), Send Email Lesson, Mastery Quiz, Daily Review, Writing Critique, Reading Comprehension.
- **`logic.py`** — All backend logic: Sarvam chat completions API calls, Sarvam STT/TTS REST calls, Google Sheets read/write, Gmail SMTP, quiz grading, text critique, transliteration.
- **`config.py`** — Centralized config: API key loading (Streamlit Secrets or `.env`), Sarvam model settings (incl. `SARVAM_MAX_TOKENS`), Sarvam voice options, UI translation strings (4 language modes), character personas, grammar topics, quiz topic→doc mapping.
- **`storage.py`** — Portable persistence layer (no Streamlit/Google/`logic`/`config` deps). Accounts, sessions, login throttling, mastery, quiz attempts, SRS cards, review history. SQLite at `data/vani.db` by default; Postgres when `storage.configure(url)` is given one. Progress is keyed by `profile_id`; `"local"` is the pre-login profile.
- **`auth.py`** — Accounts and sessions (no Streamlit/`config`/`logic` deps): scrypt password hashing, throttled `authenticate()`, "remember me" session tokens.
- **`scripts/`** — `manage_users.py` (invite-only admin CLI) and `migrate_sqlite_to_postgres.py` (one-off copy of local progress into hosted Postgres).
- **`srs.py`** — FSRS scheduling (no Streamlit/`config`/`storage`/`logic` deps — `config` imports Streamlit, so importing it here would drag the UI into the scheduler).

### Key Design Decisions

**LLM Output Parsing:** `generate_chat_turn_ai()` in `logic.py` uses `response_format={"type": "json_object"}` with the Sarvam chat completions API. The model returns a JSON object with `kannada`, `english`, and `errors` keys. `clean_json()` in `logic.py` parses it deterministically (handles markdown-fenced responses). The earlier plain-text `KANNADA:`/`ENGLISH:`/`ERRORS:` label approach was abandoned because the then-current sarvam-30b frequently dropped the labels; `json_object` mode is significantly more reliable.

**Anti-Hallucination Guard (chat errors):** The model has historically invented "corrections" for text the user never wrote. `_filter_hallucinated_errors()` in `logic.py` drops any reported error whose `original` does not actually occur in the user's message (lenient matching: NFC, punctuation/zero-width stripped, whitespace collapsed, plus a Roman-transliteration fallback for Roman-typed input). It runs inside `generate_chat_turn_ai()`, so Text Chat, Voice Chat, and the post-chat error quiz are all covered. Tests: `tests/test_hallucination_guards.py`.

**Reasoning, Retries & Token Cap:** `sarvam-105b` is a reasoning model and reasoning tokens are billed as completion tokens, so with reasoning on they consume `SARVAM_MAX_TOKENS` before any visible answer is emitted — the documented cause of `finish_reason="length"` with zero output. `config.SARVAM_REASONING_EFFORT = None` disables it (measured: 238 completion tokens/3.0s → 7 tokens/0.4s on a trivial prompt) and is sent via `extra_body` so an explicit null reaches the wire — a bare `reasoning_effort=None` kwarg is indistinguishable from "unset" to the openai SDK. Both `generate_chat_turn_ai()` and `generate_content()` still retry up to 3 attempts with identical messages. `config.SARVAM_MAX_TOKENS = 4096` is the starter-tier hard cap (Pro is 16384) — requests above it fail with HTTP 400, so never "fix" truncation by raising it.

**Known Near-Misses (`common_errors`):** LLMs are non-deterministic; do not try to extract a reproducible verdict from one. The judge was accepting ಈ ಮನೆ ದೊಡ್ಡದು for adj_001 roughly two runs in three — a coin flip on correctness. An answer that must *always* be graded wrong belongs in the bank, not in a prompt: each item may carry an optional `common_errors` list of `{"form", "means"}`, where `means` is what the learner's sentence actually says. `match_common_error()` matches it through the same `normalize_answer()` path as a correct answer, so the verdict is stable, and `explain_common_error()` builds the feedback from stored text with no model call. A hit bypasses `judge_equivalence` and `explain_mistake` entirely. Validation rejects an entry that is also an `acceptable` form. Unknown wrong answers still go to the LLM judge as before.

**Spaced Repetition (FSRS):** Every submitted answer is persisted and rescheduled by `logic.record_quiz_answer()`, correct ones included — FSRS needs successes to lengthen intervals as much as misses to shorten them. The quiz's four grading tiers map straight onto FSRS's four ratings: `incorrect`→Again, `accepted`→Hard, `variant`→Good, `exact`→Easy. "accepted" sits below "variant" deliberately: needing the LLM judge to vouch for a phrasing is weaker evidence of recall than matching a form the bank lists. **Fuzzing is disabled** (`srs.ENABLE_FUZZING = False`) — FSRS otherwise randomizes each interval, which is pointless across a 200-item bank and would make the same answer at the same moment produce a different due date every call. An FSRS `Card` has no reps/lapses fields, so those are derived from the `reviews` table. Due items surface in the **Daily Review** mode via `logic.build_review_quiz()`; ids that no longer resolve against the bank are skipped, not raised on.

**Shared Quiz Runner:** `render_quiz_runner(prefix, ...)` in `main.py` serves both the Mastery Quiz and Daily Review, with session state namespaced by `prefix`. They were separate copies once, which is why the same "question rendered twice" bug had to be fixed twice. Do not fork it again.

**Deterministic Mastery Quiz:** Questions come from the fixed bank `knowledge_base/quiz_bank.json` (200 items, 12 topics; validated on load), not from the LLM and not from Google Sheets. Correctness is decided by `check_answer()` normalization against each item's `acceptable` forms; only non-matches that are not listed in `common_errors` get one constrained yes/no LLM check (`judge_equivalence`, which fails *closed* on a bad response but returns `None` when the API was unreachable — a network blip is not a verdict about the learner, so the quiz leaves the question open rather than grading it) — the LLM never supplies its own answer. Mastery, attempts and SRS state persist via `storage.py`. Token folding in `normalize_answer()`: ಅಂತ/ಅಂತಾ/ಎಂದು are interchangeable quotatives; ಅಂತೆ (hearsay) and ಎಂಬ (naming-only, never reported speech — explicit user correction) must NEVER be folded.

**Voice Chat Always Uses Kannada Script:** The TTS API requires Kannada Script input, so voice chat mode forces `Kannada (Script)` internally regardless of the user's display preference.

**Knowledge Base Context:** The `knowledge_base/` directory holds grammar reference docs (`.md` foundation/lesson files plus legacy `.txt`) and `quiz_bank.json`. `load_knowledge_base()` injects all docs as LLM context for broad calls; the quiz scopes context to the selected topic's doc(s) via `load_topic_doc()`.

**4 Language Display Modes:** UI text and chat output can render as English, Kannada Script, Kannada Roman (Natural/colloquial), or Kannada Roman (Strict/IAST). The `toggle_script()` function and `indic-transliteration` library handle conversions.

**Accounts & Sessions:** Invite-only — accounts come from `scripts/manage_users.py`; there is no sign-up page. `require_login()` in `main.py` gates everything (before any mode renders) and ends in `st.stop()` when nobody is signed in. Only the scrypt hash of a password (`scrypt$n$r$p$salt$key`, so cost can be raised later) and the SHA-256 of a session token are stored, so a leaked DB can't sign anyone in. Streamlit loses `st.session_state` on refresh, so "remember me" is a token in the `vani_session` cookie: read server-side from `st.context.cookies`, written by a zero-height `components.html` script *on the run after* sign-in (a component emitted in the same run as `st.rerun()` never executes — hence `_queue_cookie`/`_flush_cookie`). Revocation in the DB is what logs a token out; clearing the cookie is tidiness. `authenticate()` locks a username after 5 failures in 15 min and verifies against a dummy hash for unknown usernames (no timing-based username probing); the form shows one generic error. Sign-out clears every `st.session_state` key except `context`. **Send Email Lesson is admin-only** — it emails `GMAIL_USER` and advances the shared sheet.

**`profile_id` Must Be Threaded Explicitly:** `logic.get_quiz_topics`, `record_quiz_answer`, `build_review_quiz` and `get_review_summary` take a *required* keyword `profile_id`; `main.py` passes `current_profile()`. `storage.py` keeps `"local"` defaults so its own tests stay terse, which means a forgotten `profile_id` would silently read/write the wrong learner's deck — `tests/test_profile_threading.py` AST-walks `main.py` and `logic.py` and fails on any per-profile `storage.*` call without `profile_id`. New storage functions that are not per-profile must be added to its `_PROFILE_FREE` set.

**Storage Backends:** Streamlit Community Cloud wipes its disk on every reboot, so the hosted build must use Postgres (`DATABASE_URL` secret → `config.DATABASE_URL` → `storage.configure()` at the top of `main()`; unset → SQLite). SQL is written once with `?` placeholders; `_PgConn` translates to `%s` and `AUTOINCREMENT` DDL to identity columns. Postgres uses a module-level `psycopg_pool` (a TLS handshake per call would add up), closed at exit. Its `_pg_row_factory` must tolerate `cursor.description is None`: the pool's health check runs a result-less query, and if the factory raises there the pool silently never hands out a connection (a hang, not an error). The schema version lives in the `schema_meta` table (Postgres has no `PRAGMA user_version`; SQLite v1 databases are recognized via the pragma). Timestamps stay fixed-width ISO `TEXT` on both backends so `due <= ?` ordering is identical. The admin scripts read `VANI_DATABASE_URL`, deliberately not `DATABASE_URL`, so an app `.env` loaded in your shell never points admin commands at production.

### External Dependencies

| Service | Purpose | Notes |
|---|---|---|
| Sarvam AI chat (`sarvam-105b`) | Everything: conversation, grading, quizzes, critiques, reading comprehension | OpenAI-compatible endpoint at `/v1`; `json_object` mode for chat turns; reasoning disabled. **`sarvam-30b` and `sarvam-m` are retired — both now return HTTP 400.** |
| Sarvam AI STT | Audio → Kannada transcript | Max 30s/request, WAV input |
| Sarvam AI TTS | Kannada text → audio | Max 2500 chars/request, base64 WAV output |
| Google Sheets + Drive | Email-lesson schedule tracking | Requires `service_account.json` |
| Gmail SMTP | Email lesson delivery | Requires Gmail App Password |
| Postgres (e.g. Neon) | Hosted storage for accounts and progress | `DATABASE_URL`; optional locally (SQLite fallback) |

### Credentials

Required in `.env` (local) or Streamlit Secrets (deployed):
- `SARVAM_API_KEY` (covers both chat completions and STT/TTS)
- `GOOGLE_SHEET_NAME`
- `GMAIL_USER` / `GMAIL_PASSWORD`
- `DATABASE_URL` (hosted only; Postgres connection string)
- `service_account.json` in project root (Google Cloud service account)

### Google Sheets Schema

The tracker sheet needs columns: `Topic`, `Status`, `Date Sent`. It is used only by the email-lesson flow: `send_email_lesson()` picks the first row with an empty `Status` and marks it `"Sent"`. Quiz mastery is NOT tracked in Sheets — it lives in the storage database (`data/vani.db` locally, Postgres when hosted) via `storage.py`. The legacy `data/progress.json` is imported once on first open and then left alone as a backup.

## Testing

```bash
python -m pytest -q          # full mocked suite (~1,570 tests, ~7s, no network)
python -m pytest -m live -q  # opt-in canaries against the real Sarvam API (costs credits)
VANI_TEST_DATABASE_URL=postgresql://... python -m pytest -m postgres -q
                             # storage + auth contract on real Postgres (DROPS ALL TABLES — throwaway DB only)
```

An autouse `isolated_db` fixture in `tests/conftest.py` repoints `storage.DB_FILE`
and `storage.PROGRESS_FILE` at `tmp_path` for **every** test. Never remove it:
those paths resolve relative to the repo, so without it any test touching a
storage function reads and writes the developer's own progress. It also forces
the SQLite backend (`storage._DATABASE_URL = None`) so nothing that called
`storage.configure()` can point the mocked suite at a real Postgres.

Live tests (`tests/test_live_llm.py`) are deselected by default via `addopts = -m "not live"` in `pytest.ini`. They verify the real model never hallucinates corrections; do NOT assert on model *sensitivity* (whether it flags a given mistake) — that is nondeterministic.
