# 🏫 Kannada Bhasheya Guru

**An AI-powered personalized language tutor for Kannada learners.**

Kannada Bhasheya Guru is a Python-based web application designed to assist students at the **high-beginner to high-intermediate level** in mastering Kannada grammar and vocabulary. This app acts as a strict but encouraging teacher — using Google Gemini for language intelligence and Sarvam AI for native Kannada speech — to generate lessons, grade quizzes, critique writing, and hold voice conversations grounded in a curated Knowledge Base of grammar rules.

---

## ✨ Key Features

### 📧 Email Lessons
Automatically generates and emails structured lessons based on a learning schedule tracked in Google Sheets. Each lesson covers a grammar topic from the Knowledge Base and ends with practice sentences.

### 🏆 Mastery Quiz
A dynamic quiz engine that generates 10 English sentences of increasing difficulty for a given topic. The student translates each sentence into Kannada, and the AI grades meaning, spelling, and grammar — updating the topic's "Mastery" status in Google Sheets when the student scores 90%+.

### 💬 Text Chat (Conversation Practice)
An immersive text-based chatbot powered by Google Gemini. The student selects a **character persona** (shopkeeper, doctor, nosy neighbor, etc.) and a **grammar focus** (compound verbs, conditionals, etc.), then holds a freeform Kannada conversation. The bot responds in-character, provides English translations, and silently logs every grammar error for a post-conversation review.

### 🎙️ Voice Chat (Conversation Practice)
A parallel voice-based conversation mode that chains three APIs together:

1. **Sarvam AI STT** (Speech-to-Text) — transcribes the student's spoken Kannada via the Saaras v3 model.
2. **Google Gemini** — generates an in-character conversational response (same personas and grammar focus as text chat).
3. **Sarvam AI TTS** (Text-to-Speech) — speaks the bot's Kannada reply aloud using the Bulbul v3 model with a selectable voice and adjustable speech pace.

The student configures a persona, grammar focus, AI voice, and speech pace, then records audio clips directly in the browser. The bot's spoken replies play back inline. Grammar errors are logged and displayed in a post-conversation review, just like text chat.

### ✍️ Writing Critique
Analyzes user-written Kannada text sentence-by-sentence, offering corrections in both **Formal (Granthike)** and **Colloquial (Aadumaatu)** styles. Students can paste their own text or request a writing prompt on a given topic.

### 📖 Reading Comprehension
Generates custom Kannada articles on demand (or accepts user-pasted text) and creates comprehension questions. The AI grades answers for factual accuracy and grammatical correctness, requiring full-sentence responses.

### 🌐 Multilingual UI
The entire interface can be toggled between four display modes: English, Kannada (Roman — Natural), Kannada (Roman — Strict/IAST), and Kannada (Script). All navigation labels, buttons, and descriptions are translated accordingly.

---

## 🛠️ Technical Stack

| Component | Technology |
|-----------|------------|
| **Frontend** | [Streamlit](https://streamlit.io/) |
| **Conversational AI** | Google Gemini 2.5 Flash (`google-generativeai`) |
| **Speech-to-Text** | Sarvam AI Saaras v3 (REST API) |
| **Text-to-Speech** | Sarvam AI Bulbul v3 (REST API) |
| **Database** | Google Sheets (`gspread`) |
| **Audio Input** | Streamlit native `st.audio_input` (no third-party components) |
| **Environment** | Python 3.10+ |

---

## 📂 Project Structure

```
Kannada_Guru/
├── main.py                  # Streamlit UI — pages, tabs, and state management
├── logic.py                 # Backend: Gemini calls, Sarvam STT/TTS, grading, email
├── config.py                # API keys, model settings, prompts, UI translations
├── requirements.txt         # Python dependencies
├── knowledge_base/          # Grammar modules (.txt files) used as AI context
│   ├── 1. case_suffixes_in_kannada.txt
│   ├── 2. adjectives_in_kannada.txt
│   ├── 3. verb_tenses_in_kannada.txt
│   ├── ...
│   └── 12. reported_speech_in_kannada.txt
├── service_account.json     # Google Cloud credentials (NOT committed)
├── .env                     # API keys for local development (NOT committed)
├── .gitignore
├── .devcontainer/           # GitHub Codespaces configuration
└── README.md
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites

You will need API keys/credentials from three services:

| Service | What You Need | What It Powers |
|---------|--------------|----------------|
| **Google AI Studio** | Gemini API key | All text generation (chat, quizzes, lessons, grading) |
| **Sarvam AI** | API subscription key ([dashboard.sarvam.ai](https://dashboard.sarvam.ai)) | Voice chat (STT + TTS) |
| **Google Cloud** | Service Account JSON with Sheets + Drive API access | Email lessons, quiz tracking, mastery updates |

You will also need a **Google Sheet** with columns: `Topic`, `Status`, `Date Sent` — populated with the grammar topics you want to study. The service account must have edit access to this sheet.

For email lessons, you need a **Gmail App Password** (not your regular password). See [Google's guide](https://support.google.com/accounts/answer/185833) to generate one.

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
google-generativeai
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
GEMINI_API_KEY=your_gemini_api_key_here
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
                                       │  Google Gemini    │
                                       │  (Chat session)   │
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
- Grammar errors detected by Gemini are silently logged during the conversation and displayed in a **post-conversation review screen** when the student ends the chat.
- The student can select from multiple TTS voices and adjust speech pace (0.5× to 2.0×) to match their listening level.

---

## 🔧 Adapting This Project for Another Language

This codebase is designed to be adapted for other Indic languages supported by both Gemini and Sarvam AI. Here is what you would need to change:

### Knowledge Base
Replace the `.txt` files in `knowledge_base/` with grammar guides for your target language. The AI uses these files as grounding context for all generation and grading tasks. The more structured and detailed your grammar files are, the better the AI's corrections will be.

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

## ⚠️ Disclaimer

This tool uses Large Language Models (LLMs) to generate content. While instructed to adhere to strict grammar rules, the AI may occasionally produce errors or "hallucinations." It is intended as a study aid, not a replacement for a human instructor.

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.