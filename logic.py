import streamlit as st
import os
import glob
import json
import random
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
import storage


# --- HELPER FUNCTIONS ---

def clean_json(text):
    """Robustly extracts JSON from AI text."""
    # The model can return None/empty content (e.g. a null completion); treat
    # that as "no JSON" rather than crashing on .strip().
    if not text or not isinstance(text, str):
        return None
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
    # Use config.KNOWLEDGE_DIR. Beginner foundation docs are .md; legacy grammar
    # references are .txt — load both extensions.
    files = sorted(
        glob.glob(os.path.join(config.KNOWLEDGE_DIR, "*.txt"))
        + glob.glob(os.path.join(config.KNOWLEDGE_DIR, "*.md"))
    )
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
    """Helper to call Sarvam chat completions API.

    Retries up to 3 attempts: Sarvam transiently returns empty/null
    completions (finish_reason="length" with 0 visible chars — hidden tokens
    burn the whole budget) and a plain retry usually recovers. Returns the
    final empty string or "API Error: ..." only after all attempts fail."""
    model = config.SARVAM_READING_MODEL if use_reading_model else config.SARVAM_CHAT_MODEL
    client = _sarvam_chat_client()

    full_prompt = f"""
    [KNOWLEDGE BASE]
    {context_override if context_override else "No specific context."}

    [REQUEST]
    {user_prompt}
    """

    MAX_ATTEMPTS = 3
    result = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": config.SYSTEM_INSTRUCTION},
                    {"role": "user", "content": full_prompt},
                ],
                max_tokens=config.SARVAM_MAX_TOKENS,
            )
            # Sarvam can return a null completion (message.content is None);
            # coalesce to "" so downstream string handling never sees None.
            result = response.choices[0].message.content or ""
            if result.strip():
                return result
        except Exception as e:
            result = f"API Error: {e}"
    return result


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


# --- DETERMINISTIC MASTERY QUIZ ---
# The quiz is driven entirely by the fixed question bank in
# knowledge_base/quiz_bank.json. Correctness is decided first by
# deterministic string comparison (check_answer); answers that don't match
# any acceptable form get one constrained LLM equivalence check
# (judge_equivalence) before being marked wrong. The canonical answer is
# always authoritative — the LLM never supplies its own.

QUIZ_BANK_FILE = os.path.join(config.KNOWLEDGE_DIR, "quiz_bank.json")
QUIZ_ERROR_LOG = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "logs", "quiz_errors.log")
_DIFFICULTY_ORDER = {"easy": 0, "medium": 1, "hard": 2}
_ZW_RE = re.compile("[\u200c\u200d]")  # ZWNJ / ZWJ
# Punctuation incl. danda and every common quote style — quotation marks are
# presentation, not grammar, so their absence must never fail an answer.
_PUNCT_RE = re.compile("[.!?,;:।॥\"'“”‘’«»]")
# Token-level equivalences: the colloquial quotative ಅಂತ, its lengthened
# spoken form ಅಂತಾ, and the literary ಎಂದು are interchangeable in answers.
#  ಅಂತೆ is NOT folded — it is the hearsay marker
# ("apparently"), a different meaning.
#  ಎಂಬ is NOT folded — it is a literary form used only for naming proper
# nouns ("a novel called Parva"), never for reported speech, so it is not
# a general substitute for ಅಂತ/ಎಂದು. Where an ಎಂಬ answer might be valid
# (naming contexts), judge_equivalence decides contextually.
_TOKEN_EQUIV = {"ಅಂತಾ": "ಅಂತ", "ಎಂದು": "ಅಂತ"}


def _validate_quiz_bank(bank):
    """Enforce the bank's schema contract; raise ValueError naming the
    offending item id. Guarantees: unique ids, canonical == acceptable[0],
    every topic listed in the top-level 'topics' array."""
    topics = set(bank.get("topics") or [])
    seen_ids = set()
    for item in bank.get("items") or []:
        iid = item.get("id")
        if not iid or iid in seen_ids:
            raise ValueError(f"quiz_bank: missing or duplicate item id: {iid!r}")
        seen_ids.add(iid)
        acceptable = item.get("acceptable")
        if not acceptable or not isinstance(acceptable, list):
            raise ValueError(
                f"quiz_bank item '{iid}': 'acceptable' must be a non-empty list")
        if not item.get("canonical") or item["canonical"] != acceptable[0]:
            raise ValueError(
                f"quiz_bank item '{iid}': canonical must equal acceptable[0]")
        if item.get("topic") not in topics:
            raise ValueError(
                f"quiz_bank item '{iid}': topic {item.get('topic')!r} "
                f"not in top-level topics array")
    return bank


def _load_quiz_bank_from_disk(path=None):
    """Read and validate the bank. Pure (no Streamlit) for testability."""
    with open(path or QUIZ_BANK_FILE, "r", encoding="utf-8") as f:
        return _validate_quiz_bank(json.load(f))


def load_quiz_bank():
    """Return the validated quiz bank, loading it once per session."""
    if "quiz_bank" not in st.session_state:
        st.session_state["quiz_bank"] = _load_quiz_bank_from_disk()
    return st.session_state["quiz_bank"]


def get_quiz_topics():
    """Return quiz topics sourced from the bank itself (never Sheets), each
    annotated with its lesson doc(s), display level, and local mastery status.
    The dropdown and the question pool share one source so they cannot drift;
    config.QUIZ_TOPIC_DOCS is validated against the bank here."""
    bank = load_quiz_bank()
    missing = [t for t in bank["topics"] if t not in config.QUIZ_TOPIC_DOCS]
    extra = [t for t in config.QUIZ_TOPIC_DOCS if t not in bank["topics"]]
    if missing or extra:
        raise ValueError(
            f"config.QUIZ_TOPIC_DOCS out of sync with quiz bank "
            f"(unmapped: {missing}, stale: {extra})")
    topics = [{"name": t,
               "file": config.QUIZ_TOPIC_DOCS[t]["files"],
               "level": config.QUIZ_TOPIC_DOCS[t]["level"],
               "mastered": storage.is_mastered(t)}
              for t in bank["topics"]]
    topics.sort(key=lambda t: (t["level"] != "Core", t["name"]))  # Core first
    return topics


def build_quiz(topic, n=10, seed=None):
    """Sample n bank items for `topic` without replacement, ordered
    easy -> medium -> hard. If the topic has fewer than n items, return all.
    `seed` makes the sample reproducible for tests."""
    bank = load_quiz_bank()
    pool = [it for it in bank["items"] if it["topic"] == topic]
    if not pool:
        raise ValueError(f"No quiz items for topic {topic!r}")
    rng = random.Random(seed)
    chosen = rng.sample(pool, min(n, len(pool)))
    return sorted(chosen, key=lambda it: _DIFFICULTY_ORDER[it["difficulty"]])


def normalize_answer(s):
    """Deterministic normalization for answer comparison: NFC, strip
    ZWNJ/ZWJ, strip punctuation (incl. danda and quotes), collapse
    whitespace, and fold interchangeable quotative tokens (ಅಂತ/ಅಂತಾ/ಎಂದು)."""
    if not s:
        return ""
    s = unicodedata.normalize("NFC", s)
    s = _ZW_RE.sub("", s)
    s = _PUNCT_RE.sub("", s)
    tokens = [_TOKEN_EQUIV.get(t, t) for t in s.split()]
    return " ".join(tokens)


def check_answer(user_answer, item):
    """True iff the normalized answer matches any acceptable form.
    This is the SOLE decider of correctness — the LLM never grades."""
    norm = normalize_answer(user_answer)
    return any(norm == normalize_answer(a) for a in item["acceptable"])


def classify_answer(user_answer, item):
    """Three-tier result: 'exact' (matches canonical), 'variant' (matches
    another acceptable form), or 'incorrect'."""
    if normalize_answer(user_answer) == normalize_answer(item["canonical"]):
        return "exact"
    return "variant" if check_answer(user_answer, item) else "incorrect"


def judge_equivalence(user_answer, item, context):
    """Constrained yes/no LLM check for answers that failed the deterministic
    match: is the student's Kannada a valid alternative rendering of the same
    English sentence? The canonical answer is passed as authoritative ground
    truth and the model may NOT propose a different one — it only votes
    equivalent/not. Retries once; any persistent failure returns False so the
    answer falls through to the normal wrong-answer explanation (an API
    outage must never silently mark answers correct)."""
    if not normalize_answer(user_answer):
        return False
    prompt = f"""
    A student translated an English sentence into Kannada. Their answer did
    not exactly match our reference, but it may still be correct — Kannada
    allows many valid surface forms.

    English sentence: "{item['english']}"
    Reference answer (authoritative): "{item['canonical']}"
    Grammar point being tested: "{item['grammar_note']}"
    Student's answer: "{user_answer}"

    TASK: Decide ONLY whether the student's answer is a grammatically correct
    Kannada sentence that conveys the same meaning as the English sentence
    AND demonstrates the grammar point being tested.

    Treat ALL of these as fully acceptable, never as mistakes:
    - sandhi / contracted spoken forms (e.g. ಬರ್ತಾನೆ for ಬರುತ್ತಾನೆ,
      ಹೇಳಿದ್ನು for ಹೇಳಿದನು)
    - literary vs colloquial verb endings (ಹೇಳಿದ / ಹೇಳಿದನು)
    - ಅಂತ / ಅಂತಾ / ಎಂದು quotative variants
    - presence or absence of quotation marks or other punctuation
    - natural word-order variations
    - synonyms and loanword spelling variants that keep the meaning

    Mark NOT equivalent only for real errors: wrong tense, wrong person or
    gender agreement, wrong case suffix, missing required grammar (e.g. the
    quotative), or a different meaning.

    Do NOT output a corrected sentence. OUTPUT exactly one JSON object:
    {{"equivalent": true or false, "reason": "one short sentence"}}
    """
    raw, last_exc = "", None
    for _attempt in range(2):  # initial try + one retry
        try:
            raw = generate_content(prompt, context)
            if raw and not raw.startswith("API Error"):
                data = clean_json(raw)
                if isinstance(data, dict) and isinstance(
                        data.get("equivalent"), bool):
                    return data["equivalent"]
        except Exception as e:
            last_exc = e
    _log_quiz_error(item["id"], user_answer, raw, last_exc)
    return False


def _log_quiz_error(item_id, user_answer, raw_output, exc):
    """Append a JSON line to logs/quiz_errors.log. Never raises — a logging
    failure must not block showing the (already known) correct answer."""
    try:
        os.makedirs(os.path.dirname(QUIZ_ERROR_LOG), exist_ok=True)
        with open(QUIZ_ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "item_id": item_id,
                "user_answer": user_answer,
                "raw_output": raw_output,
                "exception": repr(exc) if exc else None,
            }, ensure_ascii=False) + "\n")
    except OSError:
        pass


def explain_mistake(user_answer, item, context):
    """Ask the LLM to explain why an already-judged-wrong answer is wrong.
    The canonical answer and grammar note are passed as authoritative ground
    truth — the model never re-grades and never proposes its own 'correct'
    answer. Retries once; on persistent failure returns a friendly fallback
    (never 'AI Error'/'Unknown') and logs the raw output to QUIZ_ERROR_LOG."""
    prompt = f"""
    A student translated this English sentence into Kannada, and the answer is
    WRONG. Correctness was already decided deterministically — do NOT re-grade.

    English sentence: "{item['english']}"
    Student's answer (incorrect): "{user_answer}"
    Correct answer: "{item['canonical']}"
    The correct answer above is authoritative; do not change, dispute, or
    replace it. Grammar note (authoritative): "{item['grammar_note']}"

    TASK: In 2-4 encouraging sentences, explain WHY the student's answer is
    wrong and what rule applies, citing the grammar note. You may only point
    out differences that ACTUALLY exist between the student's answer and the
    correct answer — quote the differing words verbatim from both sentences.
    Never attribute a word or word order to the student that is not in their
    answer. If you cannot identify the specific difference, just restate the
    grammar note. Do NOT output a different 'correct answer'. Do NOT say the
    student's answer is acceptable.
    OUTPUT: a JSON object exactly like {{"feedback": "your explanation"}}
    """
    raw, last_exc = "", None
    for _attempt in range(2):  # initial try + one retry
        try:
            raw = generate_content(prompt, context)
            # generate_content returns "API Error: ..." instead of raising.
            if raw and not raw.startswith("API Error"):
                data = clean_json(raw)
                feedback = data.get("feedback") if isinstance(data, dict) else None
                if feedback and feedback.strip():
                    return {"feedback": feedback.strip()}
        except Exception as e:
            last_exc = e
    _log_quiz_error(item["id"], user_answer, raw, last_exc)
    return {"feedback": (
        "I couldn't generate a detailed explanation right now. Compare your "
        "answer with the correct sentence above — the key grammar point: "
        f"{item['grammar_note']}"
    )}


def load_topic_doc(filename):
    """Return the markdown/text of one or more knowledge_base files, for the
    'read-then-quiz' lesson view and as scoped quiz context.

    `filename` may be a single string or a list of filenames (e.g. a shared
    verb-basics doc plus a tense-specific doc). Multiple files are concatenated
    with the same '--- SOURCE: name ---' header format as load_knowledge_base().
    Missing files are skipped; returns '' if nothing could be read."""
    filenames = [filename] if isinstance(filename, str) else list(filename)
    combined = ""
    for name in filenames:
        path = os.path.join(config.KNOWLEDGE_DIR, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except (FileNotFoundError, OSError):
            continue
        if len(filenames) > 1:
            combined += f"\n--- SOURCE: {name} ---\n"
        combined += text
    return combined


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
    1. MEANING: If the user conveys the correct meaning but has minor spelling or
       suffix mistakes, mark 'is_correct' as TRUE.
    2. REAL ERRORS ONLY: Flag only genuine, unambiguous mistakes — non-existent words,
       clearly wrong verb conjugations, missing obligatory particles, or definite
       misspellings. Do NOT flag a form merely because a different phrasing also exists.
       If the user's construction is grammatically valid Kannada, do not criticise it.
    3. VERIFY BEFORE FLAGGING: Before reporting any error, verify that your proposed
       correction is MORE correct or MORE standard than the user's form. If the user's
       form is equally valid or more formal than your alternative, do NOT flag it.
       Specifically, do not suggest Aadumaatu/colloquial alternatives to valid Granthika
       forms, or vice versa. If your correct_translation would be identical (or
       near-identical) to the user's answer, do not describe the user's form as
       'colloquial', 'informal', or 'non-standard' — treat it as fully correct.
    4. CORRECT ANSWERS: When is_correct is TRUE, keep feedback brief and encouraging —
       do NOT suggest alternative verb forms or phrasings. Set correct_translation to
       the standard Granthika Kannada script (Kannada Lipi, e.g. ನಾನು ಹೋಗುತ್ತೇನೆ) form
       of the user's answer — minor spelling normalisation only, no new structure.
       Never output Roman transliteration in correct_translation.
    5. CORRECTION: When is_correct is FALSE, provide the perfect, standard Granthika
       Kannada translation in 'correct_translation'.

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


def _norm_for_presence(s):
    """Lenient normalization for checking whether text reported by the model
    actually occurs in the user's message: NFC, strip ZWNJ/ZWJ, strip
    punctuation, collapse whitespace."""
    if not s or not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFC", s)
    s = _ZW_RE.sub("", s)
    s = _PUNCT_RE.sub("", s)
    return " ".join(s.split())


def _filter_hallucinated_errors(errors, user_message):
    """Deterministic guard against hallucinated corrections: the model
    sometimes 'corrects' words the user never wrote. Keep only error objects
    whose 'original' text actually occurs in the user's message; everything
    else is dropped before it can reach the UI or the error log.

    Matching is deliberately lenient so a genuine correction is never
    discarded over surface differences: NFC, zero-width chars and punctuation
    stripped, whitespace collapsed, plus a Roman-transliteration fallback for
    users who type Romanized Kannada while the model quotes the Kannada-script
    rendering of their words.

    Returns (kept, dropped). Malformed entries (non-dict, missing/empty
    'original') count as dropped; a non-list `errors` yields ([], [])."""
    if not isinstance(errors, list):
        return [], []
    msg_norm = _norm_for_presence(user_message)
    msg_folded = msg_norm.casefold()
    kept, dropped = [], []
    for err in errors:
        original = err.get("original") if isinstance(err, dict) else None
        orig_norm = _norm_for_presence(original)
        if orig_norm and orig_norm in msg_norm:
            kept.append(err)
            continue
        if orig_norm:
            translit = _norm_for_presence(
                toggle_script(original, "Kannada (Roman - Natural)"))
            if translit and translit.casefold() in msg_folded:
                kept.append(err)
                continue
        dropped.append(err)
    return kept, dropped


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
    _CUSTOM = "Custom Scenario"
    if role_key == _CUSTOM:
        role_text = (
            scenario.strip()
            or "You are a friendly, helpful Bengalurean. Converse naturally and authentically in Kannada."
        )
        scenario_text = "The learner's situation is fully described in the Active Roleplay Persona section below."
    else:
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

    MAX_ATTEMPTS = 3
    last_raw = ""
    last_finish = ""

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            # Call Sarvam chat completions with JSON mode
            client = _sarvam_chat_client()
            response = client.chat.completions.create(
                model=config.SARVAM_CHAT_MODEL,
                messages=messages,
                response_format={"type": "json_object"},
                max_tokens=config.SARVAM_MAX_TOKENS,
            )
            raw_text = response.choices[0].message.content or ""
            finish_reason = response.choices[0].finish_reason
            last_raw, last_finish = raw_text, finish_reason

            msg_summary = "\n".join(
                f"    [{i}] role={m['role']:9s} chars={len(m['content'])}"
                for i, m in enumerate(messages)
            )
            print(
                f"\n--- Chat Turn Diagnostics [attempt {attempt}/{MAX_ATTEMPTS}] ---\n"
                f"  model         : {config.SARVAM_CHAT_MODEL}\n"
                f"  finish_reason : {finish_reason}\n"
                f"  output chars  : {len(raw_text)}\n"
                f"  starts_with_{{: {raw_text.lstrip().startswith('{')}\n"
                f"  messages sent ({len(messages)}):\n{msg_summary}\n"
                f"  raw[:400]     : {raw_text[:400]}\n"
                f"-----------------------------\n"
            )

            data = clean_json(raw_text)
            if data and data.get("kannada"):
                user_errors, dropped = _filter_hallucinated_errors(
                    data.get("errors", []), user_message)
                if dropped:
                    print(
                        f"\n--- ⚠️ Dropped {len(dropped)} hallucinated error(s) "
                        f"(original not in user message) ---\n"
                        f"  {json.dumps(dropped, ensure_ascii=False)}\n---\n"
                    )
                return {
                    "bot_reply_kannada": data.get("kannada", ""),
                    "bot_reply_english_translation": data.get("english", ""),
                    "user_errors": user_errors,
                    "raw_text": raw_text,
                }

            # Parse failed — log and decide retry strategy
            parse_result = (
                "clean_json returned None"
                if data is None
                else f"dict parsed but 'kannada' key missing (keys: {list(data.keys())})"
            )
            print(
                f"\n--- ⚠️ Parse failed [attempt {attempt}/{MAX_ATTEMPTS}] ---\n"
                f"  finish_reason : {finish_reason}\n"
                f"  output chars  : {len(raw_text)}\n"
                f"  parse result  : {parse_result}\n"
            )

            if attempt < MAX_ATTEMPTS:
                # Retry with the same messages for all failure modes:
                # - empty response / finish_reason="length" with ~0 chars:
                #   Sarvam transiently burns the whole completion budget on
                #   hidden tokens; the same call usually works on retry.
                #   Raising max_tokens is NOT an option — the starter tier
                #   hard-caps it at 4096 (HTTP 400 above that).
                # - non-JSON text: appending Kannada correction text is too
                #   token-expensive; rely on the system prompt's JSON
                #   instruction instead
                print("  action        : retrying with same messages\n---\n")

        except Exception as e:
            if attempt == MAX_ATTEMPTS:
                return {"error": str(e)}
            print(f"\n--- ⚠️ API exception [attempt {attempt}/{MAX_ATTEMPTS}]: {e} — retrying ---\n")

    # All attempts exhausted
    final_data = clean_json(last_raw)
    parse_result_final = (
        "clean_json returned None"
        if final_data is None
        else f"dict parsed but 'kannada' key missing (keys: {list(final_data.keys())})"
    )
    msg_summary = "\n".join(
        f"    [{i}] role={m['role']:9s} chars={len(m['content'])}"
        for i, m in enumerate(messages)
    )
    print(
        f"\n--- 🚨 JSON PARSING FAILED after {MAX_ATTEMPTS} attempts 🚨 ---\n"
        f"  model         : {config.SARVAM_CHAT_MODEL}\n"
        f"  finish_reason : {last_finish}\n"
        f"  output chars  : {len(last_raw)}\n"
        f"  starts_with_{{: {last_raw.lstrip().startswith('{')}\n"
        f"  parse result  : {parse_result_final}\n"
        f"  final messages sent ({len(messages)}):\n{msg_summary}\n"
        f"  full raw output:\n{last_raw}\n"
        f"-----------------------------------\n"
    )
    return {
        "error": (
            f"Parsing failed after {MAX_ATTEMPTS} attempts "
            f"[finish_reason={last_finish}, chars={len(last_raw)}]."
            f"\n\nRaw output:\n\n{last_raw}"
        )
    }


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