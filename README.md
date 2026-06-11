# 🪔 Vāṇi

![Tests](https://img.shields.io/badge/tests-1077%20passing-brightgreen) ![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green)

**An AI-powered personalized language tutor for Kannada learners.**

Vāṇi (ವಾಣಿ) is a Python-based web application designed to assist students from the **total beginner through high-intermediate level** in mastering Kannada grammar and vocabulary. This app acts as a strict but encouraging teacher — using Sarvam AI for both language intelligence and native Kannada speech — to generate lessons, grade quizzes, critique writing, and hold voice conversations grounded in a curated Knowledge Base of grammar rules.

---

## ✨ Key Features

### 📧 Email Lessons
Automatically generates and emails structured lessons based on a learning schedule tracked in Google Sheets. Each lesson covers a grammar topic from the Knowledge Base and ends with practice sentences.

### 🏆 Mastery Quiz
A deterministic "read-then-quiz" engine. Each topic serves 10 questions of increasing difficulty sampled from a curated 200-item question bank (`knowledge_base/quiz_bank.json`), with the lesson doc readable inline before you start. Grading is deterministic first: answers are normalized (punctuation, quote styles, zero-width characters, interchangeable quotatives) and matched against each question's acceptable forms. Only a non-matching answer gets a single *constrained* LLM equivalence check — the bank's canonical answer is authoritative and the model may only vote yes/no, never invent its own "correct" answer. Scoring 90%+ marks the topic mastered in local progress storage (`data/progress.json`).

### 💬 Text Chat (Conversation Practice)
An immersive text-based chatbot powered by Sarvam AI (`sarvam-30b`). The student selects from **8 richly-detailed character personas** (shopkeeper, doctor, train conductor, nosy neighbor, landlord, auto driver, house cleaner, or a traditional priest) and a **grammar focus** (compound verbs, conditionals, etc.), then holds a freeform Kannada conversation. A **Custom Scenario** mode lets you write your own character card for any conversation partner you need to practice with.

After each conversation, a **post-session error log** surfaces every grammar mistake silently tracked during the chat. A "Practice These Errors" button then generates a targeted 5-question mini-quiz drilling exactly the patterns you got wrong.

A deterministic **anti-hallucination guard** filters every error the AI reports: any "correction" whose quoted original text does not actually appear in your message is dropped before it reaches the screen, so the model can never invent mistakes you didn't make. Chat turns also retry automatically (up to 3 attempts) when the API returns a truncated or empty response.

### 🎙️ Voice Chat (Conversation Practice)
A parallel voice-based conversation mode that chains three APIs together:

1. **Sarvam AI STT** (Speech-to-Text) — transcribes the student's spoken Kannada via the Saaras v3 model.
2. **Sarvam AI** (`sarvam-30b`) — generates an in-character conversational response (same personas and grammar focus as text chat).
3. **Sarvam AI TTS** (Text-to-Speech) — speaks the bot's Kannada reply aloud using the Bulbul v3 model with a selectable voice and adjustable speech pace.

The student configures a persona, grammar focus, AI voice, and speech pace, then records audio clips directly in the browser. The bot's spoken replies play back inline. Grammar errors are logged and displayed in a post-conversation review, just like text chat.

### ✍️ Writing Critique
Analyzes user-written Kannada text sentence-by-sentence, offering corrections in both **Formal (Granthike)** and **Colloquial (Aadumaatu)** styles. Students can paste their own text or request a writing prompt on a given topic.

### 📖 Reading Comprehension
Generates custom Kannada articles on demand (or accepts user-pasted text) and creates comprehension questions. The AI grades answers for factual accuracy and grammatical correctness, requiring full-sentence responses.

### 🌐 Multilingual UI
The entire interface can be toggled between four display modes: English, Kannada (Roman — Natural), Kannada (Roman — Strict/IAST), and Kannada (Script). All navigation labels, buttons, and descriptions are translated accordingly.

---

## ⚠️ Disclaimer

This tool uses Large Language Models (LLMs) to generate content. While instructed to adhere to strict grammar rules, the AI may occasionally produce errors or "hallucinations." Several defenses are built in — quiz correctness is decided deterministically against a fixed answer bank, and chat corrections are filtered so the model can only flag text you actually wrote — but generated explanations and conversation content remain LLM output. It is intended as a study aid, not a replacement for a human instructor.

---

## 🛠️ Technical Stack

| Component | Technology |
|-----------|------------|
| **Frontend** | [Streamlit](https://streamlit.io/) |
| **Conversational AI** | Sarvam AI `sarvam-30b` (chat, quizzes, lessons, grading) |
| **Reading Comprehension AI** | Sarvam AI `sarvam-105b` (128K context for accuracy) |
| **Speech-to-Text** | Sarvam AI Saaras v3 (REST API) |
| **Text-to-Speech** | Sarvam AI Bulbul v3 (REST API) |
| **Database** | Google Sheets (`gspread`) for the email-lesson schedule; local JSON (`storage.py`) for quiz mastery progress |
| **Audio Input** | Streamlit native `st.audio_input` (no third-party components) |
| **Test Suite** | pytest — 1,077 mocked tests across 7 modules (~1.5s) plus opt-in live-API canaries (`pytest -m live`) |
| **Environment** | Python 3.10+ |

---

## 📂 Project Structure

```
Kannada_Guru/
├── main.py                  # Streamlit UI — pages, tabs, and state management
├── logic.py                 # Backend: Sarvam chat completions, STT/TTS, quiz grading, email
├── config.py                # API keys, model settings, prompts, UI translations
├── storage.py               # Local progress store (quiz mastery → data/progress.json)
├── requirements.txt         # Python dependencies
├── pytest.ini               # Test runner config (live-API tests deselected by default)
├── tests/                   # Automated test suite (1,077 mocked tests + 12 live canaries)
│   ├── conftest.py                   # Shared fixtures
│   ├── test_utilities.py             # Pure unit tests (clean_json, transliteration, UI text)
│   ├── test_sarvam_chat.py           # Chat API: parsing, retries, verbatim-input contract
│   ├── test_mastery_quiz.py          # Quiz bank integrity + deterministic grading
│   ├── test_hallucination_guards.py  # Anti-hallucination error filtering
│   ├── test_live_llm.py              # Opt-in canaries against the real Sarvam API
│   ├── test_sarvam_voice.py          # STT/TTS tests (all network calls mocked)
│   ├── test_google_sheets.py         # Google Sheets integration tests
│   └── test_email.py                 # End-to-end email lesson flow tests
├── knowledge_base/          # Grammar modules (.md/.txt) used as AI context
│   ├── quiz_bank.json       # Curated 200-item quiz bank across 12 topics
│   └── ...                  # Lesson docs (case suffixes, verb tenses, negation, ...)
├── data/                    # Per-user progress state (NOT committed)
├── service_account.json     # Google Cloud credentials (NOT committed)
├── .env                     # API keys for local development (NOT committed)
├── .gitignore
├── .devcontainer/           # GitHub Codespaces configuration
└── README.md
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites

You will need credentials from three separate services:

| Service | What You Need | What It Powers |
|---------|--------------|----------------|
| **Sarvam AI** | API subscription key ([dashboard.sarvam.ai](https://dashboard.sarvam.ai)) | All text generation (chat, quizzes, lessons, grading) + Voice STT/TTS |
| **Google Cloud** | Service Account JSON with Sheets + Drive API access | Email-lesson schedule tracking |
| **Gmail** | App Password — not your regular login password ([Google's guide](https://support.google.com/accounts/answer/185833)) | Email lesson delivery |

You will also need a **Google Sheet** with columns: `Topic`, `Status`, `Date Sent` — populated with the grammar topics you want emailed to you. The service account must have edit access to this sheet. (The Mastery Quiz does not use Sheets; its progress is stored locally.)

### 2. Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/[YourUsername]/Kannada_Guru.git
cd Kannada_Guru
pip install -r requirements.txt
```

The dependencies are:

```
streamlit
openai>=1.0.0
gspread
oauth2client
python-dotenv
indic-transliteration
requests
```

`streamlit>=1.33` is required for the native `st.audio_input` widget used in voice chat.

### 3. Configuration

Create a `.env` file in the project root (**do not commit this file**):

```env
SARVAM_API_KEY=your_sarvam_api_key_here
GOOGLE_SHEET_NAME=Name_Of_Your_Google_Sheet
GMAIL_USER=your_email@gmail.com
GMAIL_PASSWORD=your_gmail_app_password
```

Place your Google Cloud `service_account.json` in the project root.

For **Streamlit Cloud** deployment, add these same values to `.streamlit/secrets.toml` or the Streamlit Cloud Secrets UI. The service account JSON goes under a `[gcp_service_account]` section — see `config.py` for the loading logic.

### 4. Running the App

```bash
streamlit run main.py
```

The app will be available at `http://localhost:8501`.

---

## 🧪 Testing

The main suite covers all backend logic without requiring real API credentials — all network calls (Sarvam chat, STT, TTS, Google Sheets, Gmail) are mocked.

```bash
pip install pytest
python -m pytest -q
```

**1,077 tests across 7 modules, completing in ~1.5 seconds:**

| Module | What It Tests |
|--------|--------------|
| `test_utilities.py` | `clean_json`, `toggle_script`, `humanize_transliteration`, `get_ui_text`, `load_knowledge_base` |
| `test_sarvam_chat.py` | Chat turns (parsing, persona/grammar injection, 3-attempt retry paths), answer grading, writing critique, reading comprehension, and a **verbatim-input contract**: adversarial user text (quotes, braces, newlines, emoji, mixed script) must reach the LLM prompt completely unaltered |
| `test_mastery_quiz.py` | Quiz bank schema and integrity (parametrized over all 200 items), answer normalization (quotative folding, punctuation, zero-width chars), deterministic grading, constrained LLM judge fail-closed behavior, explanation fallbacks |
| `test_hallucination_guards.py` | The anti-hallucination filter: fabricated "corrections" are dropped, genuine ones survive, including for Roman-typed input |
| `test_sarvam_voice.py` | STT/TTS success paths, error handling, timeouts, payload validation (2500-char truncation, custom speaker/pace) |
| `test_google_sheets.py` | Credential routing (Streamlit Secrets vs local file), topic filtering, sheet cell writes |
| `test_email.py` | Topic selection, HTML email construction, sheet status updates, SMTP/auth error handling |

### Live-API canaries (opt-in)

A small `@pytest.mark.live` layer probes the **real** Sarvam model for hallucinated corrections: grammatically perfect Kannada must come back with no errors flagged, and anything the model does flag must quote text that actually exists in the input. These tests cost API credits and are deselected by default (`addopts = -m "not live"` in `pytest.ini`):

```bash
python -m pytest -m live -q
```

Note: the Sarvam starter tier intermittently returns truncated/empty completions (`finish_reason=length`); the app retries these automatically, but live runs can still occasionally fail on consecutive API spikes.

---

## 🎙️ Voice Chat — How It Works

The voice chat feature lives under **Conversation Practice → 🎙️ Voice Chat** (a tab alongside the existing text chat). Here is the data flow for a single conversational turn:

```
┌─────────────────┐     WAV bytes      ┌──────────────────┐
│  Browser Mic     │ ─────────────────► │  Sarvam STT      │
│  (st.audio_input)│                    │  (Saaras v3)     │
└─────────────────┘                    └────────┬─────────┘
                                                │ Kannada text
                                                ▼
                                       ┌──────────────────┐
                                       │  Sarvam AI        │
                                       │  (sarvam-30b)     │
                                       └────────┬─────────┘
                                                │ Kannada reply
                                                ▼
                                       ┌──────────────────┐      base64 WAV     ┌──────────┐
                                       │  Sarvam TTS      │ ──────────────────► │  Browser │
                                       │  (Bulbul v3)     │                     │  st.audio│
                                       └──────────────────┘                     └──────────┘
```

**Key details:**

- Voice chat always sends Kannada Script (ಕನ್ನಡ ಲಿಪಿ) to the TTS, regardless of the sidebar language setting.
- The Sarvam STT REST API accepts recordings up to **30 seconds** — more than enough for conversational turns.
- The TTS accepts up to **2500 characters** per request; the code auto-truncates if needed.
- Grammar errors detected by Sarvam AI are silently logged during the conversation and displayed in a **post-conversation review screen** when the student ends the chat.
- The student can select from multiple TTS voices and adjust speech pace (0.5× to 2.0×) to match their listening level.

---

## 🔧 Adapting This Project for Another Language

This codebase is designed to be adapted for other Indic languages supported by Sarvam AI. Here is what you would need to change:

### Knowledge Base

Replace the `.txt` files in `knowledge_base/` with grammar guides for your target language. The AI uses these files as grounding context for all generation and grading tasks.

**Grammar file format matters.** The AI relies on consistent structure to extract rules accurately. Files should use markdown headers (`##`, `###`) to separate topics, tables with transliteration columns alongside the target script, and concrete worked examples with both native script and romanized forms. Flat prose without this structure significantly degrades the quality of corrections and quiz generation.

### config.py
- **`SYSTEM_INSTRUCTION`** — Rewrite the system prompt to reference your target language instead of Kannada.
- **`SARVAM_STT_LANGUAGE`** — Change `kn-IN` to the appropriate BCP-47 code (e.g., `ta-IN` for Tamil, `hi-IN` for Hindi). See the [Sarvam docs](https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe) for supported codes.
- **`SARVAM_TTS_LANGUAGE`** — Same change for TTS output language.
- **`SARVAM_TTS_SPEAKER`** — Pick a voice appropriate for the language. All Bulbul v3 voices work across all 11 supported languages, but some may sound more natural for certain languages.
- **`CHAT_SYSTEM_PROMPT`** and **`CHAT_LANG_MODES`** — Update the example formats and language style instructions.
- **`CHARACTER_CARDS`** — Rewrite personas to reflect culturally appropriate scenarios for the target language community.
- **`UI_TEXT`** — Add translations for the new language under a new key (e.g., `"TA"` for Tamil).

### logic.py
- **`toggle_script()`** and **`humanize_transliteration()`** — These use `indic-transliteration` with Kannada-specific settings. Update the `sanscript` source/target constants for your language.

### Sarvam AI Language Support
Sarvam's STT (Saaras v3) supports 22+ Indian languages. TTS (Bulbul v3) supports 10 Indian languages plus English. Check the [Sarvam documentation](https://docs.sarvam.ai/api-reference-docs/introduction) for the latest supported language list.

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.