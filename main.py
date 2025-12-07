import streamlit as st
import random
import os
import glob

# Import our custom modules
import config
import logic


# --- STREAMLIT UI ---

def main():
    st.set_page_config(page_title="Kannada Bhasheya Guru", page_icon="🏫", layout="wide")

    st.title("🏫 Kannada Bhasheya Guru")
    st.markdown("---")

    # Load Context (Cached via Streamlit, but logic is in logic.py)
    if "context" not in st.session_state:
        with st.spinner("Loading Knowledge Base..."):
            # We call the function from logic.py
            st.session_state.context = logic.load_knowledge_base()

    # Sidebar Navigation
    st.sidebar.header("Navigation")
    mode = st.sidebar.radio("Choose Mode:",
                            ["Home", "Send Email Lesson", "Mastery Quiz", "Writing Critique", "Reading Comprehension"])

    # --- MODE: HOME ---
    if mode == "Home":
        st.subheader("Welcome back!")
        st.write("Select a module from the sidebar to begin your practice.")
        # Access config variable for directory
        file_count = len(glob.glob(os.path.join(config.KNOWLEDGE_DIR, '*.txt')))
        st.info(f"Loaded {file_count} grammar primers from your Knowledge Base.")

    # --- MODE: SEND LESSON ---
    elif mode == "Send Email Lesson":
        st.subheader("📧 Send Next Lesson")
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
        st.subheader("🏆 Mastery Quiz")

        if "quiz_questions" not in st.session_state:
            st.session_state.quiz_questions = []
            st.session_state.quiz_topic = ""
            st.session_state.quiz_sheet_row = 0
            st.session_state.quiz_score = 0
            st.session_state.current_q_index = 0

        # Step 1: Select Topic
        if not st.session_state.quiz_questions:
            sheet, topics = logic.get_quiz_data(st.session_state.context)
            if topics:
                topic_names = [t['topic'] for t in topics]
                selected_topic = st.selectbox("Select Topic:", topic_names)

                if st.button("Start Quiz"):
                    row = next(t['row'] for t in topics if t['topic'] == selected_topic)
                    with st.spinner("Generating questions..."):
                        qs = logic.generate_quiz(selected_topic, st.session_state.context)
                        st.session_state.quiz_questions = qs
                        st.session_state.quiz_topic = selected_topic
                        st.session_state.quiz_sheet_row = row
                        st.session_state.quiz_score = 0
                        st.session_state.current_q_index = 0
                        st.rerun()
            else:
                st.warning("No 'Sent' topics available or Error connecting.")

        # Step 2: Take Quiz
        else:
            q_idx = st.session_state.current_q_index
            total = len(st.session_state.quiz_questions)

            if q_idx < total:
                q = st.session_state.quiz_questions[q_idx]
                st.progress((q_idx / total))
                st.markdown(f"### Q{q_idx + 1}: {q}")

                user_ans = st.text_input("Your Translation:", key=f"q_{q_idx}")

                if st.button("Submit Answer"):
                    res = logic.grade_answer_ai(q, user_ans, st.session_state.context)

                    if res['is_correct']:
                        st.success(f"✅ Correct! {res['feedback']}")
                        st.session_state.quiz_score += 1
                    else:
                        st.error(f"❌ Incorrect.\n\nCorrect: **{res['correct_translation']}**\n\nTip: {res['feedback']}")

                    if st.button("Next Question"):
                        st.session_state.current_q_index += 1
                        st.rerun()
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
                    st.rerun()

    # --- MODE: WRITING CRITIQUE ---
    elif mode == "Writing Critique":
        st.subheader("✍️ Writing Critique")

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
        st.subheader("📖 Reading Comprehension / ಓದುವ ಗ್ರಹಿಕೆ")

        input_method = st.radio("Choose input method:", ("Paste Kannada Text", "Generate (AI)"))

        if input_method == "Paste Kannada Text":
            user_text = st.text_area("Paste Article Here:", height=200)
            if st.button("Load Text"):
                if len(user_text) > 5:
                    st.session_state['current_article'] = user_text
                    st.session_state.pop('qa_content', None)
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

        if 'current_article' in st.session_state and st.session_state['current_article']:
            st.markdown("### Current Article")
            st.info(st.session_state['current_article'])
            st.markdown("---")

            if st.button("Generate Comprehension Questions"):
                with st.spinner("Creating questions..."):
                    qa_response = logic.generate_comprehension_questions(st.session_state['current_article'],
                                                                         st.session_state.context)
                    st.session_state['qa_content'] = qa_response

            if 'qa_content' in st.session_state:
                st.markdown("### Comprehension Questions")
                st.markdown(st.session_state['qa_content'])


if __name__ == "__main__":
    main()