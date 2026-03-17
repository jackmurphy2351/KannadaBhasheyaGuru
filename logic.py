import streamlit as st
import os
import glob
import json
import re
import smtplib
import unicodedata
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from indic_transliteration import sanscript

import google.generativeai as genai
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


def generate_content(user_prompt, context_override=None):
    """Helper to call Gemini."""
    genai.configure(api_key=config.GENAI_API_KEY)

    model = genai.GenerativeModel(
        config.MODEL_NAME,
        system_instruction=config.SYSTEM_INSTRUCTION
    )

    full_prompt = f"""
    [KNOWLEDGE BASE]
    {context_override if context_override else "No specific context."}

    [REQUEST]
    {user_prompt}
    """

    try:
        response = model.generate_content(
            full_prompt,
            safety_settings=config.SAFETY_SETTINGS
        )
        return response.text
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
    res = generate_content(prompt, context)
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
    res = generate_content(prompt, context)
    data = clean_json(res)
    if data:
        return data
    return {"is_correct": False, "feedback": "AI Error", "detailed_explanation": "Error"}


def generate_chat_turn_ai(user_message, chat_history, grammar_focus, role_key, lang_mode):
    """
    Handles a single turn of the conversational chatbot.
    """
    import google.generativeai as genai
    import json

    # 1. Determine which strict instruction track to use based on UI toggle
    if "Script" in lang_mode:
        track = config.CHAT_LANG_MODES["FORMAL_SCRIPT"]
    else:
        track = config.CHAT_LANG_MODES["AADUMAATU_ROMAN"]

    # 2. Prepare the dynamic system instruction
    role_text = config.CHARACTER_CARDS.get(role_key, "")
    system_instruction = config.CHAT_SYSTEM_PROMPT.replace(
        "[INJECT_JSON_SCHEMA_HERE]", track["schema"]
    ).replace(
        "[INJECT_LANG_INSTRUCTION_HERE]", track["instruction"]
    ).replace(
        "[INJECT_GRAMMAR_FOCUS_HERE]", grammar_focus
    ).replace(
        "[INJECT_SELECTED_ROLE_HERE]", role_text
    )

    # 3. Configure the specific model instance
    genai.configure(api_key=config.GENAI_API_KEY)
    model = genai.GenerativeModel(
        config.MODEL_NAME,
        system_instruction=system_instruction,
        generation_config={"response_mime_type": "application/json"}  # Forces JSON output
    )

    # 4. Format the chat history for Gemini's start_chat method
    gemini_history = []
    for msg in chat_history:
        gemini_history.append({
            "role": msg["role"],
            "parts": [msg["content"]]
        })

    try:
        # 5. Initiate chat session with history and send message
        chat_session = model.start_chat(history=gemini_history)
        response = chat_session.send_message(user_message, safety_settings=config.SAFETY_SETTINGS)

        try:
            # Attempt to parse the JSON securely
            return json.loads(response.text)
        except json.JSONDecodeError as json_err:
            print("\n--- 🚨 BAD JSON RECEIVED FROM GEMINI 🚨 ---")
            print(response.text)
            print("-------------------------------------------\n")
            return {"error": "JSON Parsing failed. Check PyCharm terminal for raw output."}

    except Exception as e:
        return {"error": str(e)}