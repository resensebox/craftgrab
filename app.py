import streamlit as st
import json
from fpdf import FPDF
from datetime import datetime, date
from openai import OpenAI
import os
import logging
import sqlite3
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- Logging Setup ---
logging.basicConfig(filename='app_activity.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

st.set_option('client.showErrorDetails', True)
st.set_page_config(page_title="This Day in History", layout="centered")

# --- Theme Styling ---
st.markdown("""
<style>
body, .stApp {
    background-color: #ffffff !important;
    color: #000000 !important;
    font-family: 'Inter', sans-serif;
    padding: 1rem;
}

h1, h2, h3, h4, h5, h6 {
    color: #000000 !important;
    text-align: center;
    font-weight: 700;
    margin: 2rem auto 1.5rem;
    font-size: 2em;
}

.stButton>button {
    background-color: #4CAF50;
    color: white;
    padding: 0.8em 2em;
    border: none;
    border-radius: 8px;
    font-weight: bold;
    box-shadow: 2px 2px 4px rgba(0,0,0,0.2);
}
.stButton>button:hover {
    background-color: #45a049;
    transform: translateY(-2px);
}

.stTextInput>div>div>input {
    background-color: #ffffff;
    color: #000000;
    border-radius: 8px;
    padding: 10px;
    border: 1px solid #ccc;
    box-shadow: inset 0 1px 2px rgba(0,0,0,0.05);
}

.stTextInput>div>div>input:focus {
    border-color: #4CAF50;
}

.card {
    background-color: #f8f9fa;
    border-radius: 12px;
    padding: 20px;
    margin: 20px 0;
    box-shadow: 0 4px 8px rgba(0,0,0,0.05);
    border: 1px solid #e0e0e0;
}
.card h3 {
    font-size: 1.4em;
    margin-bottom: 0.5em;
    color: #000;
}
.card p {
    font-size: 1.1em;
    color: #333;
    line-height: 1.6em;
    margin-bottom: 1em;
}
</style>
""", unsafe_allow_html=True)

# --- Initialization ---
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key and "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
if not api_key:
    st.error("❌ OPENAI_API_KEY is missing.")
    st.stop()
client_ai = OpenAI(api_key=api_key)

DB_NAME = 'users.db'
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_plain TEXT NOT NULL)''')
    conn.commit()
    conn.close()
init_db()

# --- Google Sheets ---
def get_gsheet_client():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_dict = st.secrets["GOOGLE_SERVICE_JSON"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except:
        return None

def add_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_plain) VALUES (?, ?)", (username, password))
        conn.commit()
        client = get_gsheet_client()
        if client:
            sheet = client.open("This Day in History").worksheet("Users")
            sheet.append_row([username, str(datetime.now())])
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def verify_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT password_plain FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    return result and result[0] == password

# --- PDF Helpers ---
def generate_article_pdf(title, content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.multi_cell(0, 10, title, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 8, content.encode('latin-1', 'replace').decode('latin-1'))
    return pdf.output(dest='S').encode('latin-1')

# --- Auth Forms ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'show_login' not in st.session_state:
    st.session_state['show_login'] = True

if not st.session_state.logged_in:
    if st.session_state.show_login:
        with st.sidebar.form("login"):
            st.text_input("Username", key="login_user")
            st.text_input("Password", type="password", key="login_pass")
            if st.form_submit_button("Log In"):
                if verify_user(st.session_state.login_user, st.session_state.login_pass):
                    st.session_state.logged_in = True
                    st.session_state.username = st.session_state.login_user
                    st.rerun()
                else:
                    st.error("Incorrect username or password")
        if st.sidebar.button("Don't have an account?"):
            st.session_state.show_login = False
            st.rerun()
    else:
        with st.sidebar.form("register"):
            st.text_input("New Username", key="reg_user")
            st.text_input("New Password", type="password", key="reg_pass")
            st.text_input("Confirm Password", type="password", key="reg_confirm")
            if st.form_submit_button("Register"):
                if st.session_state.reg_pass == st.session_state.reg_confirm:
                    if add_user(st.session_state.reg_user, st.session_state.reg_pass):
                        st.success("Registration successful. Please log in.")
                        st.session_state.show_login = True
                        st.rerun()
                    else:
                        st.error("Username already exists.")
                else:
                    st.error("Passwords do not match.")
        if st.sidebar.button("Already registered?"):
            st.session_state.show_login = True
            st.rerun()
    st.stop()

# --- Main App ---
st.header("🗓️ This Day in History!")
st.sidebar.success(f"Logged in as {st.session_state['username']}")
if st.sidebar.button("Log Out"):
    st.session_state.clear()
    st.rerun()

name = st.text_input("Enter Pair's Name:", "")
today = st.date_input("Select a date", value=date.today(), max_value=date.today())

if name:
    prompt = f"""
    You are a historical assistant. Provide:
    1. A cultural or positive event from {today.month:02d}-{today.day:02d} (1900-1965)
    2. A famous birth (1850-1960)
    3. A fun fact
    4. 3 trivia Q&A

    Format:
    Event: [Title] - [Year]
    [Description]

    Born on this Day: [Name]
    [Description]

    Fun Fact: [Fact]

    Trivia Questions:
    1. [Q]? (Answer: [A])
    """
    try:
        response = client_ai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        output = response.choices[0].message.content
    except Exception as e:
        st.error(f"AI error: {e}")
        st.stop()

    for block in output.split("\n\n"):
        if block.strip():
            st.markdown(f'<div class="card">{block.replace("\n", "<br>")}</div>', unsafe_allow_html=True)

    st.download_button("Download Summary PDF", generate_article_pdf(f"This Day in History - {today}", output), file_name="history_summary.pdf")
else:
    st.info("Please enter a name to begin.")
