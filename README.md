# 🏫 Kannada Bhasheya Guru

**An AI-powered personalized language tutor for Kannada learners.**

Kannada Bhasheya Guru is a Python-based web application designed to assist students at the **high-beginner to high-intermediate level** in mastering Kannada grammar and vocabulary. 

Unlike generic translation tools, this app acts as a strict but encouraging teacher, using the Gemini API to generate lessons, grade quizzes, and critique writing based on a specific "Knowledge Base" of grammar rules provided by the user.

## ✨ Key Features

* **📧 Email Lessons:** Automatically generates and emails structured lessons based on a learning schedule tracked in Google Sheets.
* **🏆 Mastery Quiz:** A dynamic quiz engine that tests translation skills and tracks "Mastery" status for specific topics.
* **✍️ Writing Critique:** Analyzes user-written text sentence-by-sentence, offering corrections in both "Formal (Granthike)" and "Colloquial (Aadumaatu)" styles.
* **📖 Reading Comprehension:** Generates custom articles on demand (or accepts user text) and creates comprehension questions to test understanding.

## 🛠️ Technical Stack

* **Frontend:** [Streamlit](https://streamlit.io/)
* **AI Model:** Google Gemini 2.5 Flash (via `google-generativeai`)
* **Database:** Google Sheets (via `gspread`)
* **Environment:** Python 3.10+

## 🚀 Quick Start Guide

### 1. Prerequisites
You will need:
* A **Google Gemini API Key** (AI Studio).
* A **Google Cloud Service Account** JSON file with access to the Google Sheets API and Google Drive API.
* A Google Sheet with columns: `Topic`, `Status`, `Date Sent`.

### 2. Installation

Clone the repository:
```bash
git clone [https://github.com/](https://github.com/)[YourUsername]/Kannada_Guru.git
cd Kannada_Guru
```

Install dependencies:
```bash
pip install streamlit google-generativeai gspread oauth2client python-dotenv
```

### 3. Configuration
This app requires sensitive credentials. **Do not commit these to GitHub!**

Create a `.env` file in the root directory:
```Plaintext
SARVAM_API_KEY=your_api_key_here
GOOGLE_SHEET_NAME=Name_Of_Your_Google_Sheet
GMAIL_USER=your_email@gmail.com
GMAIL_PASSWORD=your_app_password
```

### 4. Running the App
Execute the following command in your terminal:
```bash
streamlit run main.py
```
## 📂 Project Structure
* `main.py`: The User Interface (Streamlit).
* `logic.py`: Backend logic, API handling, and educational algorithms.
* `config.py`: Configuration settings and environment variable loading.
* `knowledge_base/`: Folder containing .txt files with specific grammar rules.

## ⚠️ Disclaimer
This tool uses Large Language Models (LLMs) to generate content. While instructed to adhere to strict grammar rules, the AI may occasionally produce errors or "hallucinations." It is intended as a study aid, not a replacement for a human instructor.