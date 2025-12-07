import os
import glob
import json
import re
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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
        TASK: Create a short, engaging email lesson about "{topic}".
        REQUIREMENTS:
        1. Use the provided context definitions/examples.
        2. Include 5 vocab words, 1 grammar rule, and 1 practice sentence.
        3. Output as clean HTML.
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
    prompt = f"""
    TASK: Generate exactly 10 simple sentences in English based on the topic "{topic}" 
    that the student must translate into Kannada.
    OUTPUT: JSON list of strings. Example: ["I go", "She eats"]
    """
    res = generate_content(prompt, context)
    data = clean_json(res)
    if data:
        return data
    return ["Error generating questions."]


def grade_answer_ai(question, answer, context):
    prompt = f"""
    English: "{question}"
    User Kannada: "{answer}"
    Task: Grade accuracy. Output JSON: {{ "is_correct": boolean, "feedback": "string", "correct_translation": "string" }}
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
    prompt = f"Write a short Kannada paragraph about {topic} in {p_style} style suitable for a learner."
    return generate_content(prompt, context)


def generate_comprehension_questions(text, context):
    prompt = f"""
    Analyze the following Kannada text:
    "{text}"

    1. Create 3 reading comprehension questions in Kannada based on this text.
    2. Provide the answers to these questions in Kannada.

    IMPORTANT FORMATTING INSTRUCTIONS:
    - Output the questions and answers in a clean, readable format.
    - Do NOT use JSON format. 
    - Do NOT use curly braces {{}} or dictionary keys like 'question':.
    - Do NOT escape unicode characters (e.g. print ಪ್ಯಾರಾಗ್ರಾಫ್‌ನಲ್ಲಿ, not ಪ್ಯಾರಾಗ್ರಾಫ್\u200cನಲ್ಲಿ).
    - Format it simply as:
      Q1: [Question text]
      A1: [Answer text]

      Q2: [Question text]
      A2: [Answer text]
    """
    return generate_content(prompt, context)