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

# --- Theme Styling with Dark Mode Detection ---
st.markdown("""
<style>
:root {
    --text-color: #1a1a1a;
    --background-color: #e8f0fe;
    --input-bg: #ffffff;
    --button-bg: #4CAF50;
    --button-text: #ffffff;
}

.dark-theme {
    --text-color: #f2f2f2;
    --background-color: #1e1e1e;
    --input-bg: #2b2b2b;
    --button-bg: #6FBF73;
    --button-text: #ffffff;
}

body, .stApp {
    background-color: var(--background-color) !important;
    color: var(--text-color) !important;
    font-family: 'Inter', sans-serif;
}

h1, h2, h3, h4, h5, h6 {
    color: var(--text-color) !important;
    text-align: center;
    font-weight: 700;
    margin: 2rem auto 1.5rem;
    font-size: 2em;
}

.stButton>button {
    background-color: var(--button-bg);
    color: var(--button-text);
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
    background-color: var(--input-bg);
    color: var(--text-color);
    border-radius: 8px;
    padding: 10px;
    border: 1px solid #ccc;
    box-shadow: inset 0 1px 2px rgba(0,0,0,0.05);
}
.stTextInput>div>div>input:focus {
    border-color: var(--button-bg);
}

.stAlert, .stMarkdown {
    color: var(--text-color);
}

.stMarkdown code {
    color: var(--text-color);
    background-color: rgba(0,0,0,0.05);
    padding: 0.2em 0.4em;
    border-radius: 4px;
}
</style>

<script>
const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
if (isDark) {
    document.documentElement.classList.add("dark-theme");
}
</script>
""", unsafe_allow_html=True)

# --- OpenAI Init ---
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key and "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
if not api_key:
    st.error("❌ OPENAI_API_KEY is missing from environment or secrets.")
    st.stop()
try:
    client_ai = OpenAI(api_key=api_key)
except Exception as e:
    st.error(f"Failed to initialize OpenAI. Error: {e}")
    st.stop()

# --- Google Sheets ---
def get_gsheet_client():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_dict = st.secrets["GOOGLE_SERVICE_JSON"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        logging.error(f"Google Sheets client error: {e}")
        return None

# --- Database Setup ---
DB_NAME = 'users.db'
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_plain TEXT NOT NULL)''')
    conn.commit()
    conn.close()

init_db()

def add_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_plain) VALUES (?, ?)", (username, password))
        conn.commit()
        gsheet = get_gsheet_client()
        if gsheet:
            try:
                sheet = gsheet.open("This Day in History").worksheet("Users")
                sheet.append_row([username, str(datetime.now())])
            except Exception as e:
                logging.error(f"Failed to log user to Google Sheets: {e}")
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

def generate_full_history_pdf(event_title, event_article, born_section, fun_fact_section, trivia_section, today_str, name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 20)
    pdf.multi_cell(0, 10, f"This Day in History: {today_str}", align='C')
    pdf.ln(10)
    pdf.set_font("Arial", "B", 14)
    pdf.multi_cell(0, 10, "Significant Event:")
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 8, f"{event_title}\n{event_article}".encode('latin-1', 'replace').decode('latin-1'))
    pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.multi_cell(0, 10, "Famous Person Born Today:")
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 8, born_section.encode('latin-1', 'replace').decode('latin-1'))
    pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.multi_cell(0, 10, "Fun Fact:")
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 8, fun_fact_section.encode('latin-1', 'replace').decode('latin-1'))
    pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.multi_cell(0, 10, "Trivia Time! (with answers for the volunteer):")
    pdf.set_font("Arial", "", 12)
    for t in trivia_section:
        pdf.multi_cell(0, 8, t.encode('latin-1', 'replace').decode('latin-1'))
    pdf.set_font("Arial", "I", 10)
    pdf.multi_cell(0, 5, f"Generated for {name} by Mindful Libraries on {today_str}".encode('latin-1', 'replace').decode('latin-1'), align='C')
    return pdf.output(dest='S').encode('latin-1')

# --- Streamlit UI ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'show_login' not in st.session_state:
    st.session_state['show_login'] = True

st.header("🗓️ This Day in History!")

def login_form():
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

def register_form():
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

if not st.session_state.logged_in:
    if st.session_state.show_login:
        login_form()
        if st.sidebar.button("Don't have an account?"):
            st.session_state.show_login = False
            st.rerun()
    else:
        register_form()
        if st.sidebar.button("Already registered?"):
            st.session_state.show_login = True
            st.rerun()
    st.stop()

st.sidebar.success(f"Logged in as {st.session_state['username']}")
if st.sidebar.button("Log Out"):
    st.session_state.clear()
    st.rerun()

name = st.text_input("Enter Pair's Name:", "")
today = st.date_input("Select a date", value=date.today(), max_value=date.today())

if name:
    profile = {"name": name}
    prompt = f"""
    You are a historical assistant. Provide:
    1. A cultural or positive event from {today.month:02d}-{today.day:02d} (1900-1965)
    2. A famous birth (1850-1960) relevant to: {profile}
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

    st.text_area("Generated Summary", output, height=300)
    st.download_button("Download Summary PDF", generate_article_pdf(f"This Day in History - {today}", output), file_name="history_summary.pdf")
else:
    st.info("Please enter a name to begin.")
