import streamlit as st
import os
import glob
import json
import re
import smtplib
import unicodedata
import base64
import requests
import io
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from indic_transliteration import sanscript

from openai import OpenAI
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Import settings from our new config file
import config


# --- HELPER FUNCTIONS ---

def clean_json(text):
    """Robustly extracts JSON from AI text."""
    try:
        text = text.strip()
        if text.startswith("```json"):
            text = text.replace("```json", "", 1)
        if text.startswith("```"):
            text = text.replace("```", "", 1)
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        return json.loads(text.strip())
    except json.JSONDecodeError:
        try:
            match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except:
            pass
        return None


def load_knowledge_base():
    """Reads all grammar text files into a single context string."""
    combined_text = ""
    # Use config.KNOWLEDGE_DIR
    files = glob.glob(os.path.join(config.KNOWLEDGE_DIR, "*.txt"))
    if not files:
        return ""
    for filename in files:
        with open(filename, 'r', encoding='utf-8') as f:
            combined_text += f"\n--- SOURCE: {os.path.basename(filename)} ---\n"
            combined_text += f.read()
    return combined_text


def get_sheet_client():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

    # 1. Try to load from Streamlit Cloud Secrets
    if "gcp_service_account" in st.secrets:
        # We need to convert the st.secrets object to a standard python dict
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

    # 2. Fallback to local file (for when you run on laptop)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name(config.CREDENTIALS_FILE, scope)

    client = gspread.authorize(creds)
    return client.open(config.SHEET_NAME).sheet1


def _sarvam_chat_client():
    """Returns an OpenAI-compatible client pointed at the Sarvam chat endpoint."""
    return OpenAI(
        api_key=config.SARVAM_API_KEY or config.get_secret("SARVAM_API_KEY"),
        base_url=config.SARVAM_CHAT_BASE_URL,
    )


def generate_content(user_prompt, context_override=None, use_reading_model=False):
    """Helper to call Sarvam chat completions API."""
    model = config.SARVAM_READING_MODEL if use_reading_model else config.SARVAM_CHAT_MODEL
    client = _sarvam_chat_client()

    full_prompt = f"""
    [KNOWLEDGE BASE]
    {context_override if context_override else "No specific context."}

    [REQUEST]
    {user_prompt}
    """

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": config.SYSTEM_INSTRUCTION},
                {"role": "user", "content": full_prompt},
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"API Error: {e}"


# --- TEXT & TRANSLATION HANDLERS ---

def humanize_transliteration(iast_text):
    """
    Converts strict academic IAST (e.g., 'grāṃthika')
    to natural colloquial spelling (e.g., 'granthika').
    """
    if not iast_text:
        return ""

    # 1. Normalize unicode characters (decomposes 'ā' into 'a' + macron)
    normalized = unicodedata.normalize('NFKD', iast_text)

    # 2. Filter out non-spacing mark characters (the dots and macrons)
    clean_text = "".join([c for c in normalized if not unicodedata.category(c).startswith('Mn')])

    # 3. Manual Fixes for specific IAST quirks
    clean_text = clean_text.replace("ṃ", "n")  # Anusvara -> n
    clean_text = clean_text.replace("ṛ", "ru")
    clean_text = clean_text.replace("r̥", "ru")

    return clean_text


def toggle_script(text, lang_mode):
    """
    Helper for dynamic content (like AI output).
    Handles both 'Natural' and 'Strict' Roman modes.
    """
    if not text:
        return ""

    # Check if we are in EITHER Roman mode ("Kannada (Roman - Natural)" or "Kannada (Roman - Strict)")
    if "Roman" in lang_mode:
        # Step 1: Get Strict Academic Transliteration (IAST)
        raw_iast = sanscript.transliterate(text, sanscript.KANNADA, sanscript.IAST)

        # Step 2: Check specifically for "Natural"
        if "Natural" in lang_mode:
            return humanize_transliteration(raw_iast)
        else:
            # If Strict (or unspecified Roman), return the raw IAST with diacritics
            return raw_iast

    return text


def get_ui_text(key, lang_mode):
    """
    Retrieves UI text based on the selected language mode.
    Modes: 'English', 'Kannada (Roman - Natural)', 'Kannada (Roman - Strict)', 'Kannada (Script)'
    """
    # 1. Default to English if key missing
    if key not in config.UI_TEXT:
        return key

    entry = config.UI_TEXT[key]

    # 2. Return English
    if lang_mode == "English":
        return entry["EN"]

    # 3. Return Kannada Script
    if lang_mode == "Kannada (Script)":
        return entry["KN"]

    # 4. Return Roman (Strict OR Natural)
    if "Roman" in lang_mode:
        raw_iast = sanscript.transliterate(entry["KN"], sanscript.KANNADA, sanscript.IAST)

        if "Natural" in lang_mode:
            return humanize_transliteration(raw_iast)
        else:
            return raw_iast

    return entry["EN"]


# --- FEATURE FUNCTIONS ---

def send_email_lesson(context):
    try:
        sheet = get_sheet_client()
        topic = None
        row_num = -1
        records = sheet.get_all_records()
        for i, row in enumerate(records):
            if row.get('Status') == '':
                topic = row.get('Topic')
                row_num = i + 2
                break

        if not topic:
            return "No new topics found."

        prompt = f"""
        TASK: Create an engaging email lesson about "{topic}".
        REQUIREMENTS:
        1. Use the provided context definitions/examples.
        2. Include content from **every** section (i.e., with markdown header level of '###') of the topic.
        3. End the email with 3 practice sentences demonstrating the major lessons of the topic.
        4. Output as clean HTML.
        """
        lesson_html = generate_content(prompt, context)

        msg = MIMEMultipart()
        msg['From'] = config.SENDER_EMAIL
        msg['To'] = config.RECEIVER_EMAIL
        msg['Subject'] = f"Kannada Lesson: {topic}"
        msg.attach(MIMEText(lesson_html, 'html'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(config.SENDER_EMAIL, config.SENDER_PASSWORD)
        server.sendmail(config.SENDER_EMAIL, config.RECEIVER_EMAIL, msg.as_string())
        server.quit()

        sheet.update_cell(row_num, 2, 'Sent')
        sheet.update_cell(row_num, 3, str(datetime.now()))
        return f"Email sent successfully regarding '{topic}'!"

    except Exception as e:
        return f"Error: {e}"


def get_quiz_data(context):
    try:
        sheet = get_sheet_client()
        records = sheet.get_all_records()
        topics = [{'topic': row.get('Topic'), 'row': i + 2} for i, row in enumerate(records) if
                  row.get('Status') == 'Sent']
        return sheet, topics
    except Exception as e:
        return None, []


def update_mastery(row_num):
    sheet = get_sheet_client()
    sheet.update_cell(row_num, 2, 'Mastered')


def generate_quiz(topic, context):
    # CHANGED: Reverted to 10 questions to save API quota
    prompt = f"""
    TASK: Generate exactly 10 simple sentences in English based on the topic "{topic}"
    that the student must translate into Kannada. The sentences should use a diverse range of vocabulary
    and should increase in length and complexity following this pattern:
    * First 3 sentences are easy (short and simple)
    * Middle 4 sentences are intermediate (longer, slightly more complex)
    * Final 3 sentences are hard (long and complex)
    OUTPUT: JSON list of strings. Example: ["I go", "She eats"]
    """
    res = generate_content(prompt, context)
    data = clean_json(res)
    if data:
        return data
    return ["Error generating questions."]


def generate_error_quiz(errors: list, context: str) -> list:
    """Generate 5 English sentences targeting the grammar patterns from the user's error log."""
    error_summary = "\n".join(
        f"- Used: '{e.get('original', '')}' → Correct: '{e.get('correction', '')}' "
        f"({e.get('reason', '')})"
        for e in errors
    )
    prompt = f"""
    A student made the following grammar errors during a Kannada conversation:
    {error_summary}

    TASK: Generate exactly 5 English sentences that specifically exercise the grammar
    patterns identified in the errors above. Each sentence should require the student
    to produce the correct grammatical structure they previously got wrong.
    OUTPUT: JSON list of 5 strings. Example: ["I go home.", "She is eating rice."]
    """
    res = generate_content(prompt, context)
    data = clean_json(res)
    if data and isinstance(data, list):
        return data[:5]
    return ["Error generating questions."]


def grade_answer_ai(question, answer, context):
    prompt = f"""
    English Source: "{question}"
    User Kannada: "{answer}"

    TASK: Grade the user's translation.

    RULES:
    1. MEANING: If the user conveys the correct meaning but has small spelling/suffix mistakes (e.g. writing 'ಬಾಟಲ್‌ದಲ್ಲಿ' instead of 'ಬಾಟಲಿನಲ್ಲಿ'), mark 'is_correct' as TRUE.
    2. PEDANTRY: You MUST explicitly point out every spelling or grammar mistake in the 'feedback', even if you marked it correct. Explain the rule (e.g. "You missed the 'in' connector before 'alli'").
    3. CORRECTION: Always provide the perfect, standard Kannada translation in 'correct_translation'.

    Output JSON: {{ "is_correct": boolean, "feedback": "string", "correct_translation": "string" }}
    """
    res = generate_content(prompt, context)
    data = clean_json(res)
    if data:
        return data
    return {"is_correct": False, "feedback": "AI Error", "correct_translation": "Unknown"}

def critique_text_ai(text, style, context):
    style_rule = "Strict Literary (Granthike)" if style == "Formal" else "Colloquial (Aadumaatu)"
    prompt = f"""
    Style: {style_rule}
    User Text: "{text}"
    Task: Analyze SENTENCE BY SENTENCE.
    Output JSON: {{ "analysis": [ {{ "original": "str", "corrected": "str", "status": "CORRECT/IMPROVE", "feedback": "str" }} ], "overall_summary": "str" }}
    """
    res = generate_content(prompt, context)
    data = clean_json(res)
    if data:
        return data
    return {}


def generate_kannada_article_ai(topic, style, context):
    p_style = "Literary" if style == "Formal" else "Colloquial"
    prompt = (f"Write a short Kannada paragraph about {topic} in {p_style} style suitable for a learner. "
              f"Do **not** return any text *besides* the paragraph itself. The paragraph should be "
              f"engaging and thought-provoking with a light-hearted tone.")
    return generate_content(prompt, context)


def generate_comprehension_questions(text, context):
    """Generates structured JSON Q&A so the UI can create input boxes."""
    prompt = f"""
    Analyze the following Kannada text:
    "{text}"

    TASK:
    1. Create 3 reading comprehension questions in Kannada.
    2. Provide the correct answer for each.

    OUTPUT FORMAT:
    Return a strictly valid JSON list of objects. 
    Example: [{{"question": "Question text here", "answer": "Answer text here"}}]
    """
    res = generate_content(prompt, context, use_reading_model=True)
    data = clean_json(res)
    if data:
        return data
    return []


def grade_reading_ai(question, text, answer, context):
    """Grades a single reading comprehension answer."""
    prompt = f"""
    Text: "{text}"
    Question: "{question}"
    User Answer: "{answer}"
    Task: Grade the user's answer for factual and grammatical accuracy based on the text. Require that the user respond in *full sentences*. If the user answers by copying and pasting verbatim text from the passage, grade their response as wrong and politely chide them for their laziness! 
    Output JSON: {{ "is_correct": boolean, "feedback": "string", "detailed_explanation": "string" }}
    """
    res = generate_content(prompt, context, use_reading_model=True)
    data = clean_json(res)
    if data:
        return data
    return {"is_correct": False, "feedback": "AI Error", "detailed_explanation": "Error"}


def generate_chat_turn_ai(user_message, chat_history, grammar_focus, role_key, lang_mode, scenario: str = ""):
    """
    Handles a single turn of the conversational chatbot using Sarvam chat completions.
    Uses json_object response_format for deterministic structured output parsed via clean_json().
    """
    # 1. Determine which strict instruction track to use based on UI toggle
    if "Roman" in lang_mode:
        track = config.CHAT_LANG_MODES["AADUMAATU_ROMAN"]
    else:
        track = config.CHAT_LANG_MODES["FORMAL_SCRIPT"]

    # 2. Prepare the dynamic system instruction
    role_text = config.CHARACTER_CARDS.get(role_key, "")
    scenario_text = (
        f"The learner is preparing for this real-world situation: {scenario.strip()}"
        if scenario and scenario.strip()
        else "No specific scenario — carry on a natural conversation in character."
    )
    system_instruction = config.CHAT_SYSTEM_PROMPT.replace(
        "[INJECT_JSON_SCHEMA_HERE]", track["schema"]
    ).replace(
        "[INJECT_LANG_INSTRUCTION_HERE]", track["instruction"]
    ).replace(
        "[INJECT_GRAMMAR_FOCUS_HERE]", grammar_focus
    ).replace(
        "[INJECT_SCENARIO_HERE]", scenario_text
    ).replace(
        "[INJECT_SELECTED_ROLE_HERE]", role_text
    )

    # 3. Build the messages array (system prompt + full history + new user turn)
    messages = [{"role": "system", "content": system_instruction}]
    for msg in chat_history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    try:
        # 4. Call Sarvam chat completions with JSON mode for deterministic structure
        client = _sarvam_chat_client()
        response = client.chat.completions.create(
            model=config.SARVAM_CHAT_MODEL,
            messages=messages,
            response_format={"type": "json_object"},
        )
        raw_text = response.choices[0].message.content
        finish_reason = response.choices[0].finish_reason

        print(
            f"\n--- Chat Turn Diagnostics ---\n"
            f"  finish_reason : {finish_reason}\n"
            f"  output chars  : {len(raw_text)}\n"
            f"  messages in   : {len(messages)}\n"
            f"  raw[:400]     : {raw_text[:400]}\n"
            f"-----------------------------\n"
        )

        # 5. Deterministic JSON parsing — no regex, no fallbacks
        data = clean_json(raw_text)
        if not data or not data.get("kannada"):
            print(f"\n--- 🚨 JSON PARSING FAILED 🚨 ---\nfull raw:\n{raw_text}\n---------------------------------\n")
            return {
                "error": (
                    f"Parsing failed "
                    f"[finish_reason={finish_reason}, chars={len(raw_text)}]."
                    f"\n\nRaw output:\n\n{raw_text}"
                )
            }

        return {
            "bot_reply_kannada": data.get("kannada", ""),
            "bot_reply_english_translation": data.get("english", ""),
            "user_errors": data.get("errors", []),
            "raw_text": raw_text,
        }

    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# SARVAM AI VOICE FUNCTIONS (STT + TTS)
# ============================================================================


def sarvam_speech_to_text(audio_bytes):
    """
    Sends recorded audio bytes to Sarvam STT REST API.
    Returns the transcribed Kannada text, or an error string.

    Args:
        audio_bytes: Raw WAV audio bytes from st.audio_input or mic_recorder.

    Returns:
        dict with keys: {"transcript": str, "language": str} or {"error": str}
    """
    api_key = config.SARVAM_API_KEY or config.get_secret("SARVAM_API_KEY")
    if not api_key:
        return {"error": "SARVAM_API_KEY not configured. Add it to your .env file."}

    url = f"{config.SARVAM_BASE_URL}/speech-to-text"
    headers = {
        "api-subscription-key": api_key,
    }

    # Wrap audio bytes in a file-like object for multipart upload
    files = {
        "file": ("recording.wav", io.BytesIO(audio_bytes), "audio/wav"),
    }
    data = {
        "model": config.SARVAM_STT_MODEL,
        "language_code": config.SARVAM_STT_LANGUAGE,
    }

    try:
        response = requests.post(url, headers=headers, files=files, data=data, timeout=30)
        response.raise_for_status()
        result = response.json()

        transcript = result.get("transcript", "").strip()
        if not transcript:
            return {"error": "Sarvam STT returned empty transcript. Speak louder or longer."}

        return {
            "transcript": transcript,
            "language": result.get("language_code", config.SARVAM_STT_LANGUAGE),
        }

    except requests.exceptions.HTTPError as e:
        error_body = ""
        try:
            error_body = e.response.json()
        except:
            error_body = e.response.text
        return {"error": f"Sarvam STT HTTP {e.response.status_code}: {error_body}"}
    except requests.exceptions.Timeout:
        return {"error": "Sarvam STT request timed out. Try a shorter recording (<30s)."}
    except Exception as e:
        return {"error": f"Sarvam STT error: {str(e)}"}


def sarvam_text_to_speech(text, speaker=None, pace=None):
    """
    Sends Kannada text to Sarvam TTS REST API and returns audio bytes.

    Args:
        text:    Kannada text string (max 2500 chars for bulbul:v3).
        speaker: Optional speaker name override (e.g., "kavitha", "amit").
        pace:    Optional speech pace override (0.5 to 2.0).

    Returns:
        dict with keys: {"audio_bytes": bytes} or {"error": str}
    """
    api_key = config.SARVAM_API_KEY or config.get_secret("SARVAM_API_KEY")
    if not api_key:
        return {"error": "SARVAM_API_KEY not configured. Add it to your .env file."}

    if not text or not text.strip():
        return {"error": "No text provided for TTS."}

    # Truncate to API limit (2500 chars for v3)
    text = text.strip()[:2500]

    url = f"{config.SARVAM_BASE_URL}/text-to-speech"
    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "target_language_code": config.SARVAM_TTS_LANGUAGE,
        "model": config.SARVAM_TTS_MODEL,
        "speaker": speaker or config.SARVAM_TTS_SPEAKER,
        "pace": pace or config.SARVAM_TTS_PACE,
        "speech_sample_rate": config.SARVAM_TTS_SAMPLE_RATE,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()

        audios = result.get("audios", [])
        if not audios:
            return {"error": "Sarvam TTS returned no audio data."}

        # Decode base64 audio → raw WAV bytes
        audio_bytes = base64.b64decode(audios[0])
        return {"audio_bytes": audio_bytes}

    except requests.exceptions.HTTPError as e:
        error_body = ""
        try:
            error_body = e.response.json()
        except:
            error_body = e.response.text
        return {"error": f"Sarvam TTS HTTP {e.response.status_code}: {error_body}"}
    except requests.exceptions.Timeout:
        return {"error": "Sarvam TTS request timed out. Text may be too long."}
    except Exception as e:
        return {"error": f"Sarvam TTS error: {str(e)}"}