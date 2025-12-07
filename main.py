import streamlit as st
import random
import os
import glob

# Import our custom modules
import config
import logic


# --- STREAMLIT UI ---

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

        /* Style the individual labels to look like blocks */
        div.row-widget.stRadio > div[role="radiogroup"] > label {
            background-color: white;
            padding: 15px;
            margin-bottom: 5px;
            border-radius: 0px; /* Flush rectangles */
            border-left: 6px solid var(--karnataka-gold); /* Gold accent */
            transition: all 0.3s ease;
            cursor: pointer;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        /* HOVER STATE: Red Background, Gold Text */
        div.row-widget.stRadio > div[role="radiogroup"] > label:hover {
            background-color: var(--karnataka-red);
            color: var(--karnataka-gold) !important;
            border-left: 6px solid var(--karnataka-gold);
        }

        /* TEXT STYLING IN SIDEBAR */
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

        /* 4. BUTTONS (Primary Actions) */
        .stButton > button {
            background-color: var(--karnataka-red);
            color: white;
            border: none;
            border-radius: 4px;
        }
        .stButton > button:hover {
            background-color: #B71C1C; /* Darker red */
            color: var(--karnataka-gold);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

def main():
    st.set_page_config(page_title="Kannada Bhasheya Guru", layout="wide")

    # Inject the Red & Gold CSS
    local_css()

    st.title("Kannada Bhasheya Guru")
    st.markdown("---")

    # 1. Load Context
    if "context" not in st.session_state:
        with st.spinner("Loading Knowledge Base..."):
            st.session_state.context = logic.load_knowledge_base()

    # 2. Sidebar Navigation
    st.sidebar.header("Navigation")
    mode = st.sidebar.radio("Choose Mode:",
                            ["Home", "Send Email Lesson", "Mastery Quiz", "Writing Critique", "Reading Comprehension"])

    # --- MODE: HOME ---
    if mode == "Home":
        st.subheader("Overview")

        # Wry, dry-humoured text
        st.markdown("""
            Welcome. You are here because you want to learn Kannada, and presumably, you have realized that smiling and nodding is not a viable long-term communication strategy in Bengaluru.

            This application utilizes a Large Language Model to simulate a strict but arguably fair Kannada tutor. It does not sleep, it does not judge (much), and it will not ask you why you aren't married yet.

            **How to survive this tool:**

            * **Send Email Lesson:** For when you want to feel productive without actually doing anything.
            * **Mastery Quiz:** The machine will test your translation skills. It is pedantic. Accuracy matters.
            * **Writing Critique:** Paste your broken sentences here. The AI will dismantle them and show you the pieces.
            * **Reading Comprehension:** Read texts you barely understand and answer questions to prove you guessed correctly.

            Select a torture method from the sidebar to begin.
            """)

        # Access config variable for directory
        file_count = len(glob.glob(os.path.join(config.KNOWLEDGE_DIR, '*.txt')))
        st.info(f"System Status: {file_count} grammar modules loaded and ready.")

    # --- MODE: SEND LESSON ---
    elif mode == "Send Email Lesson":
        st.subheader("Send Next Lesson")
        st.write("This will check your Google Sheet for the next topic and email you a lesson.")
        if st.button("Generate & Send Lesson"):
            with st.spinner("Working..."):
                result = logic.send_email_lesson(st.session_state.context)
                if "Error" in result:
                    st.error(result)
                else:
                    st.success(result)

    # --- MODE: MASTERY QUIZ ---
    elif mode == "Mastery Quiz":
        st.subheader("Mastery Quiz")

        # --- SESSION STATE SAFETY CHECK ---
        # Ensure variables exist even if hot-reloading
        if "quiz_questions" not in st.session_state:
            st.session_state.quiz_questions = []
        if "quiz_history" not in st.session_state:
            st.session_state.quiz_history = []
        if "current_q_index" not in st.session_state:
            st.session_state.current_q_index = 0
        if "quiz_score" not in st.session_state:
            st.session_state.quiz_score = 0

        # State 1: Setup - Select Topic (Only if no questions loaded)
        if not st.session_state.quiz_questions:
            sheet, topics = logic.get_quiz_data(st.session_state.context)
            if topics:
                topic_names = [t['topic'] for t in topics]
                selected_topic = st.selectbox("Select Topic:", topic_names)

                if st.button("Start Quiz"):
                    row = next(t['row'] for t in topics if t['topic'] == selected_topic)
                    with st.spinner("Generating 10 questions..."):
                        # Ensure logic.py was updated to ask for 10 questions!
                        qs = logic.generate_quiz(selected_topic, st.session_state.context)
                        st.session_state.quiz_questions = qs
                        st.session_state.quiz_topic = selected_topic
                        st.session_state.quiz_sheet_row = row
                        st.session_state.quiz_score = 0
                        st.session_state.current_q_index = 0
                        st.session_state.quiz_history = []  # Reset history
                        st.rerun()
            else:
                st.warning("No 'Sent' topics available or Error connecting.")

        # State 2: Active Quiz
        else:
            total = len(st.session_state.quiz_questions)

            # --- DISPLAY HISTORY (Previous Questions) ---
            if st.session_state.quiz_history:
                st.markdown("### Previous Answers")
                for i, item in enumerate(st.session_state.quiz_history):
                    with st.expander(f"Q{i + 1}: {item['question']}", expanded=False):
                        st.write(f"**Your Answer:** {item['user_answer']}")
                        if item['correct']:
                            st.success(f"✅ {item['feedback']}")
                        else:
                            st.error(f"❌ {item['feedback']}")
                            st.write(f"**Correct:** {item['correct_translation']}")
                st.markdown("---")

            # --- CURRENT QUESTION LOGIC ---
            if st.session_state.current_q_index < total:
                q_idx = st.session_state.current_q_index
                q_text = st.session_state.quiz_questions[q_idx]

                # Progress Bar
                st.progress(q_idx / total)
                st.markdown(f"### Q{q_idx + 1}: {q_text}")

                # Check if we have ALREADY answered this specific question
                if len(st.session_state.quiz_history) == q_idx:
                    # -- INPUT PHASE --
                    user_ans = st.text_input("Your Translation:", key=f"input_{q_idx}")

                    if st.button("Submit Answer"):
                        with st.spinner("Grading..."):
                            res = logic.grade_answer_ai(q_text, user_ans, st.session_state.context)

                            # Save to history
                            history_item = {
                                'question': q_text,
                                'user_answer': user_ans,
                                'correct': res['is_correct'],
                                'feedback': res['feedback'],
                                'correct_translation': res.get('correct_translation', '')
                            }
                            st.session_state.quiz_history.append(history_item)

                            # Update score
                            if res['is_correct']:
                                st.session_state.quiz_score += 1

                            # Force rerun to switch to "Result Phase"
                            st.rerun()

                else:
                    # -- RESULT PHASE (Answered, waiting for Next) --
                    # Get the result from the last history item
                    last_result = st.session_state.quiz_history[-1]

                    if last_result['correct']:
                        st.success(f"✅ Correct! {last_result['feedback']}")
                    else:
                        st.error(
                            f"❌ Incorrect.\n\nCorrect: **{last_result['correct_translation']}**\n\nTip: {last_result['feedback']}")

                    if st.button("Next Question ➡️"):
                        st.session_state.current_q_index += 1
                        st.rerun()

            # --- QUIZ COMPLETE ---
            else:
                score = st.session_state.quiz_score
                st.markdown(f"## Quiz Complete! Score: {score}/{total}")

                if score >= (total * 0.9):
                    st.balloons()
                    st.success("🎉 PASSED! Topic marked as 'Mastered'.")
                    logic.update_mastery(st.session_state.quiz_sheet_row)
                else:
                    phrases = ["ಇನ್ನೂ ಪ್ರಯತ್ನಿಸಿ! (Innū prayatnisi!)", "ಉತ್ತಮವಾಗಿರಲಿ! (Mundina bāri uttamavāgirali!)"]
                    st.warning(random.choice(phrases))
                    st.write("Status remains 'Sent'. Study more and try again!")

                if st.button("Back to Menu"):
                    st.session_state.quiz_questions = []
                    st.session_state.quiz_history = []
                    st.rerun()

    # --- MODE: WRITING CRITIQUE ---
    elif mode == "Writing Critique":
        st.subheader("Writing Critique")

        col1, col2 = st.columns(2)
        with col1:
            style = st.selectbox("Style", ["Formal (Literary)", "Colloquial (Spoken)"])
        with col2:
            method = st.radio("Input Method", ["Paste Text", "Get Prompt"])

        if method == "Get Prompt":
            topic = st.selectbox("Topic", config.WRITING_TOPICS)
            if st.button("Generate Prompt"):
                with st.spinner("Generating prompt..."):
                    prompt_res = logic.generate_content(
                        f"Create a specific, 1-sentence creative writing prompt about {topic} for a learner. Do not include any preliminary text; just give the writing prompt and nothing else.",
                        st.session_state.context)
                    st.info(f"✨ PROMPT: {prompt_res}")

        user_text = st.text_area("Write/Paste your Kannada text here:", height=150)

        if st.button("Analyze Writing"):
            if len(user_text) < 5:
                st.error("Text is too short!")
            else:
                with st.spinner("Analyzing sentence-by-sentence..."):
                    res = logic.critique_text_ai(user_text, style.split()[0], st.session_state.context)
                    if "overall_summary" in res:
                        st.markdown("### 📝 Critique Report")
                        st.info(f"**Summary:** {res.get('overall_summary')}")
                        for item in res.get('analysis', []):
                            with st.expander(f"Sentence: {item.get('original', 'Unknown')[:30]}...", expanded=True):
                                if item.get('status') == 'CORRECT':
                                    st.caption("✅ Perfect")
                                else:
                                    st.error(f"❌ Needs Improvement")
                                    st.write(f"**Correction:** {item.get('corrected')}")
                                    st.write(f"**Feedback:** {item.get('feedback')}")
                    else:
                        st.warning("Could not analyze text.")

    # --- MODE: READING COMPREHENSION ---
    elif mode == "Reading Comprehension":
        st.subheader("Reading Comprehension / ಓದುವ ಗ್ರಹಿಕೆ")

        input_method = st.radio("Choose input method:", ("Paste Kannada Text", "Generate (AI)"))

        # Input Section
        if input_method == "Paste Kannada Text":
            user_text = st.text_area("Paste Article Here:", height=200)
            if st.button("Load Text"):
                if len(user_text) > 5:
                    st.session_state['current_article'] = user_text
                    st.session_state.pop('qa_content', None)  # Clear old questions
                    st.success("Text loaded successfully!")
                else:
                    st.warning("Please paste some text first.")

        elif input_method == "Generate (AI)":
            col1, col2 = st.columns(2)
            with col1:
                topic = st.selectbox("Topic", config.WRITING_TOPICS, key="rc_topic")
            with col2:
                style = st.selectbox("Style", ["Formal", "Colloquial"], key="rc_style")

            if st.button("Generate Text"):
                with st.spinner("Generating article..."):
                    generated_text = logic.generate_kannada_article_ai(topic, style, st.session_state.context)
                    st.session_state['current_article'] = generated_text
                    st.session_state.pop('qa_content', None)
                    st.success("Article generated!")

        # Display Article & Questions
        if 'current_article' in st.session_state and st.session_state['current_article']:
            st.markdown("### Current Article")
            st.info(st.session_state['current_article'])
            st.markdown("---")

            # Button to generate questions
            if st.button("Generate Comprehension Questions"):
                with st.spinner("Creating questions..."):
                    qa_response = logic.generate_comprehension_questions(st.session_state['current_article'],
                                                                         st.session_state.context)
                    st.session_state['qa_content'] = qa_response

            # Render the Questions (Iterate through the list)
            if 'qa_content' in st.session_state and isinstance(st.session_state['qa_content'], list):
                if len(st.session_state['qa_content']) == 0:
                    st.error(
                        "Error: The AI returned no questions. You may have hit the rate limit. Please try again later.")
                else:
                    st.markdown("### Comprehension Questions")

                    for i, item in enumerate(st.session_state['qa_content']):
                        st.markdown(f"**Q{i + 1}: {item.get('question')}**")

                        user_ans = st.text_input(f"Your Answer for Q{i + 1}:", key=f"rc_answer_{i}")

                        if st.button(f"Check Answer {i + 1}", key=f"btn_check_{i}"):
                            if not user_ans:
                                st.warning("Please write an answer first.")
                            else:
                                with st.spinner("Grading..."):
                                    res = logic.grade_reading_ai(
                                        item.get('question'),
                                        st.session_state['current_article'],
                                        user_ans,
                                        st.session_state.context
                                    )

                                    if res['is_correct']:
                                        st.success(f"✅ {res['feedback']}")
                                    else:
                                        st.error(f"❌ {res['feedback']}")

                                    with st.expander("📘 Deep Dive Explanation"):
                                        st.write(res['detailed_explanation'])
                    st.markdown("---")

            elif 'qa_content' in st.session_state:
                # Fallback if something goes wrong and it returns text instead of list
                st.error("Error: Questions were not generated in the correct format. Please try again.")


if __name__ == "__main__":
    main()