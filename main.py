import streamlit as st
import os
import glob
import random

# Import our custom modules
import config
import logic


# --- CUSTOM CSS FOR KARNATAKA THEME ---
def local_css():
    st.markdown(
        """
        <style>
        /* 1. MAIN THEME COLORS (Karnataka Flag: Yellow/Gold & Red) */
        :root {
            --karnataka-red: #D32F2F;
            --karnataka-gold: #FFD700;
        }

        /* 2. SIDEBAR RADIO BUTTONS -> FLUSH RECTANGLES */
        div.row-widget.stRadio > div {
            background-color: transparent;
        }

        div.row-widget.stRadio > div[role="radiogroup"] > label {
            background-color: white;
            padding: 15px;
            margin-bottom: 5px;
            border-radius: 0px; 
            border-left: 6px solid var(--karnataka-gold); 
            transition: all 0.3s ease;
            cursor: pointer;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        div.row-widget.stRadio > div[role="radiogroup"] > label:hover {
            background-color: var(--karnataka-red);
            color: var(--karnataka-gold) !important;
            border-left: 6px solid var(--karnataka-gold);
        }

        div.row-widget.stRadio > div[role="radiogroup"] > label > div {
            color: inherit;
            font-weight: 600;
            font-size: 16px;
        }

        /* 3. GENERAL HEADERS */
        h1, h2, h3 {
            color: var(--karnataka-red) !important;
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        }

        /* 4. BUTTONS */
        .stButton > button {
            background-color: var(--karnataka-red);
            color: white;
            border: none;
            border-radius: 4px;
        }
        .stButton > button:hover {
            background-color: #B71C1C;
            color: var(--karnataka-gold);
        }
        </style>
        """,
        unsafe_allow_html=True
    )


# --- STREAMLIT UI ---

def main():
    st.set_page_config(page_title="Kannada Bhasheya Guru", page_icon="🪔", layout="wide")
    local_css()

    # 1. Load Context
    if "context" not in st.session_state:
        with st.spinner("Loading Knowledge Base..."):
            st.session_state.context = logic.load_knowledge_base()

    # --- SIDEBAR SETTINGS (Language Toggle) ---

    # 1. Create a placeholder at the TOP of the sidebar
    settings_header = st.sidebar.empty()

    # 2. Render the Radio Button to get the current language choice
    lang_mode = st.sidebar.radio("App Language / ಭಾಷೆ:",
                                 [
                                     "English",
                                     "Kannada (Roman - Natural)",
                                     "Kannada (Roman - Strict)",
                                     "Kannada (Script)"
                                 ])

    # 3. Now that we have 'lang_mode', write the translated text
    settings_header.header(logic.get_ui_text("HDR_SETTINGS", lang_mode))

    st.sidebar.markdown("---")

    # UPDATED: Translate "NAVIGATION" Header
    st.sidebar.header(logic.get_ui_text("HDR_NAV", lang_mode))

    nav_options = {
        "Home": "NAV_HOME",
        "Send Email Lesson": "NAV_EMAIL",
        "Mastery Quiz": "NAV_QUIZ",
        "Writing Critique": "NAV_WRITE",
        "Reading Comprehension": "NAV_READ"
    }

    # UPDATED: Translate "Go to:" Label
    mode = st.sidebar.radio(
        logic.get_ui_text("LBL_GOTO", lang_mode),
        options=list(nav_options.keys()),
        format_func=lambda x: logic.get_ui_text(nav_options[x], lang_mode)
    )

    # --- MAIN APP TITLE (UPDATED) ---
    st.title(logic.get_ui_text("APP_TITLE", lang_mode))
    st.markdown("---")

    # --- MODE: HOME ---
    if mode == "Home":
        st.subheader(logic.get_ui_text("TITLE_HOME", lang_mode))
        st.markdown(logic.get_ui_text("WELCOME_MSG", lang_mode))

        file_count = len(glob.glob(os.path.join(config.KNOWLEDGE_DIR, '*.txt')))
        st.info(f"System Status: {file_count} grammar modules loaded.")

    # --- MODE: SEND LESSON ---
    elif mode == "Send Email Lesson":
        st.subheader(logic.get_ui_text("TITLE_EMAIL", lang_mode))
        st.write(logic.get_ui_text("DESC_EMAIL", lang_mode))

        if st.button(logic.get_ui_text("BTN_SEND", lang_mode)):
            with st.spinner("Compiling lesson..."):
                result = logic.send_email_lesson(st.session_state.context)
                if "Error" in result:
                    st.error(result)
                else:
                    st.success(result)

    # --- MODE: MASTERY QUIZ ---
    elif mode == "Mastery Quiz":
        st.subheader(logic.get_ui_text("TITLE_QUIZ", lang_mode))

        if "quiz_questions" not in st.session_state:
            st.session_state.quiz_questions = []
            st.session_state.quiz_history = []
            st.session_state.current_q_index = 0
            st.session_state.quiz_score = 0

        # State 1: Setup
        if not st.session_state.quiz_questions:
            sheet, topics = logic.get_quiz_data(st.session_state.context)
            if topics:
                topic_names = [t['topic'] for t in topics]
                st.write(logic.get_ui_text("LBL_TOPIC", lang_mode))
                selected_topic = st.selectbox("Topic", topic_names, label_visibility="collapsed")

                if st.button(logic.get_ui_text("BTN_START_QUIZ", lang_mode)):
                    row = next(t['row'] for t in topics if t['topic'] == selected_topic)
                    with st.spinner("Generating 10 questions..."):
                        qs = logic.generate_quiz(selected_topic, st.session_state.context)
                        st.session_state.quiz_questions = qs
                        st.session_state.quiz_topic = selected_topic
                        st.session_state.quiz_sheet_row = row
                        st.session_state.quiz_score = 0
                        st.session_state.current_q_index = 0
                        st.session_state.quiz_history = []
                        st.rerun()
            else:
                st.warning("No 'Sent' topics available.")

        # State 2: Active Quiz
        else:
            total = len(st.session_state.quiz_questions)

            # History
            if st.session_state.quiz_history:
                st.markdown("### Previous Answers")
                for i, item in enumerate(st.session_state.quiz_history):
                    display_q = logic.toggle_script(item['question'], lang_mode)
                    with st.expander(f"Q{i + 1}: {display_q}", expanded=False):
                        st.write(f"**Your Answer:** {item['user_answer']}")

                        feed = logic.toggle_script(item['feedback'], lang_mode)
                        corr = logic.toggle_script(item['correct_translation'], lang_mode)

                        if item['correct']:
                            st.success(feed)
                            # Show standard answer even if correct, so they can compare spelling
                            st.info(f"Standard Kannada: {corr}")
                        else:
                            st.error(feed)
                            st.write(f"**Correct:** {corr}")
                st.markdown("---")

            # Current Question
            if st.session_state.current_q_index < total:
                q_idx = st.session_state.current_q_index
                q_text = st.session_state.quiz_questions[q_idx]

                display_q = logic.toggle_script(q_text, lang_mode)

                st.progress(q_idx / total)
                st.markdown(f"### Q{q_idx + 1}: {display_q}")

                if len(st.session_state.quiz_history) == q_idx:
                    # --- INPUT PHASE ---
                    st.write(logic.get_ui_text("LBL_TRANS", lang_mode))
                    user_ans = st.text_input("Answer", key=f"input_{q_idx}", label_visibility="collapsed")

                    if st.button(logic.get_ui_text("BTN_SUBMIT", lang_mode)):
                        with st.spinner("Grading..."):
                            res = logic.grade_answer_ai(q_text, user_ans, st.session_state.context)

                            history_item = {
                                'question': q_text,
                                'user_answer': user_ans,
                                'correct': res['is_correct'],
                                'feedback': res['feedback'],
                                'correct_translation': res.get('correct_translation', '')
                            }
                            st.session_state.quiz_history.append(history_item)
                            if res['is_correct']: st.session_state.quiz_score += 1
                            st.rerun()
                else:
                    # --- RESULT PHASE (Indentation Fixed) ---
                    last_result = st.session_state.quiz_history[-1]
                    feed_text = logic.toggle_script(last_result['feedback'], lang_mode)
                    corr_text = logic.toggle_script(last_result['correct_translation'], lang_mode)

                    if last_result['correct']:
                        st.success(f"Correct! {feed_text}")
                        st.info(f"Standard Kannada: {corr_text}")
                    else:
                        st.error(f"Incorrect. {feed_text}")
                        st.write(f"**Correct Answer:** {corr_text}")

                    # LOGIC: Check if this is the last question
                    is_last_question = (st.session_state.current_q_index == total - 1)

                    if is_last_question:
                        btn_label = "See Results 🏁"
                    else:
                        btn_label = logic.get_ui_text("BTN_NEXT", lang_mode)

                    if st.button(btn_label):
                        st.session_state.current_q_index += 1
                        st.rerun()
            else:
                score = st.session_state.quiz_score
                st.markdown(f"## Score: {score}/{total}")
                if score >= (total * 0.9):
                    st.success("Topic Mastered! Sheet updated.")
                    logic.update_mastery(st.session_state.quiz_sheet_row)
                else:
                    st.warning("Not yet! Keep trying.")

                if st.button(logic.get_ui_text("BTN_BACK", lang_mode)):
                    st.session_state.quiz_questions = []
                    st.rerun()

    # --- MODE: WRITING CRITIQUE ---
    elif mode == "Writing Critique":
        st.subheader(logic.get_ui_text("TITLE_WRITE", lang_mode))

        col1, col2 = st.columns(2)
        with col1:
            st.write(logic.get_ui_text("LBL_STYLE", lang_mode))
            style = st.selectbox(
                "Style",
                ["Formal", "Colloquial"],
                label_visibility="collapsed",
                format_func=lambda x: logic.get_ui_text(f"OPT_{x}", lang_mode)
            )
        with col2:
            st.write(logic.get_ui_text("LBL_INPUT", lang_mode))
            method = st.radio(
                "Input",
                ["Paste Text", "Get Prompt"],
                label_visibility="collapsed",
                format_func=lambda x: logic.get_ui_text(f"OPT_{x}", lang_mode)
            )

        if method == "Get Prompt":
            st.write(logic.get_ui_text("LBL_TOPIC", lang_mode))
            topic = st.selectbox("Topic", config.WRITING_TOPICS, label_visibility="collapsed")
            if st.button(logic.get_ui_text("BTN_GEN_PROMPT", lang_mode)):
                with st.spinner("Generating..."):
                    prompt_res = logic.generate_content(f"Create a 1-sentence writing prompt regarding {topic}",
                                                        st.session_state.context)
                    st.info(logic.toggle_script(prompt_res, lang_mode))

        st.write(logic.get_ui_text("LBL_PASTE", lang_mode))
        user_text = st.text_area("User Text", height=150, label_visibility="collapsed")

        if st.button(logic.get_ui_text("BTN_ANALYZE", lang_mode)):
            if len(user_text) < 5:
                st.error("Text is too short.")
            else:
                with st.spinner("Analyzing..."):
                    res = logic.critique_text_ai(user_text, style, st.session_state.context)
                    if "overall_summary" in res:
                        st.info(logic.toggle_script(res.get('overall_summary'), lang_mode))
                        for item in res.get('analysis', []):
                            orig = logic.toggle_script(item.get('original', ''), lang_mode)
                            with st.expander(f"{orig[:40]}..."):
                                if item.get('status') != 'CORRECT':
                                    corr = logic.toggle_script(item.get('corrected'), lang_mode)
                                    feed = logic.toggle_script(item.get('feedback'), lang_mode)
                                    st.write(f"**Correction:** {corr}")
                                    st.write(f"**Feedback:** {feed}")
                                else:
                                    st.caption("Correct")

    # --- MODE: READING COMPREHENSION ---
    elif mode == "Reading Comprehension":
        st.subheader(logic.get_ui_text("TITLE_READ", lang_mode))

        st.write(logic.get_ui_text("LBL_INPUT", lang_mode))
        input_method = st.radio(
            "Method",
            ("Paste Kannada Text", "Generate (AI)"),
            label_visibility="collapsed",
            format_func=lambda x: logic.get_ui_text(f"OPT_{x}", lang_mode)
        )

        if input_method == "Paste Kannada Text":
            st.write(logic.get_ui_text("LBL_PASTE", lang_mode))
            user_text = st.text_area("Paste", height=200, label_visibility="collapsed")
            if st.button(logic.get_ui_text("BTN_LOAD", lang_mode)):
                if len(user_text) > 5:
                    st.session_state['current_article'] = user_text
                    st.session_state.pop('qa_content', None)
                    st.success("Loaded.")
                else:
                    st.warning("Please paste some text first.")

        elif input_method == "Generate (AI)":
            col1, col2 = st.columns(2)
            with col1:
                st.write(logic.get_ui_text("LBL_TOPIC", lang_mode))
                topic = st.selectbox("Topic", config.WRITING_TOPICS, key="rc_topic", label_visibility="collapsed")
            with col2:
                st.write(logic.get_ui_text("LBL_STYLE", lang_mode))
                style = st.selectbox(
                    "Style",
                    ["Formal", "Colloquial"],
                    key="rc_style",
                    label_visibility="collapsed",
                    format_func=lambda x: logic.get_ui_text(f"OPT_{x}", lang_mode)
                )

            if st.button(logic.get_ui_text("BTN_GEN_TEXT", lang_mode)):
                with st.spinner("Generating..."):
                    generated_text = logic.generate_kannada_article_ai(topic, style, st.session_state.context)
                    st.session_state['current_article'] = generated_text
                    st.session_state.pop('qa_content', None)
                    st.success("Generated.")

        if 'current_article' in st.session_state and st.session_state['current_article']:
            st.markdown("### Article")
            st.info(logic.toggle_script(st.session_state['current_article'], lang_mode))
            st.markdown("---")

            if st.button(logic.get_ui_text("BTN_GEN_QS", lang_mode)):
                with st.spinner("Creating questions..."):
                    qa_response = logic.generate_comprehension_questions(st.session_state['current_article'],
                                                                         st.session_state.context)
                    st.session_state['qa_content'] = qa_response

            if 'qa_content' in st.session_state and isinstance(st.session_state['qa_content'], list):
                if len(st.session_state['qa_content']) == 0:
                    st.error("Rate limit hit or no questions generated.")
                else:
                    st.markdown("### Questions")
                    for i, item in enumerate(st.session_state['qa_content']):
                        q_text = logic.toggle_script(item.get('question'), lang_mode)
                        st.markdown(f"**Q{i + 1}: {q_text}**")

                        user_ans = st.text_input(f"Answer {i + 1}", key=f"rc_answer_{i}", label_visibility="collapsed")

                        if st.button(logic.get_ui_text("BTN_CHECK", lang_mode) + f" {i + 1}", key=f"btn_check_{i}"):
                            if not user_ans:
                                st.warning("Write an answer first.")
                            else:
                                with st.spinner("Grading..."):
                                    res = logic.grade_reading_ai(item.get('question'),
                                                                 st.session_state['current_article'], user_ans,
                                                                 st.session_state.context)

                                    feed = logic.toggle_script(res['feedback'], lang_mode)
                                    expl = logic.toggle_script(res['detailed_explanation'], lang_mode)

                                    if res['is_correct']:
                                        st.success(f"Correct. {feed}")
                                    else:
                                        st.error(f"Incorrect. {feed}")

                                    with st.expander("Explanation"):
                                        st.write(expl)
                        st.markdown("---")


if __name__ == "__main__":
    main()