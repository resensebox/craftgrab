import streamlit as st
import json
from fpdf import FPDF
from datetime import datetime, date
from openai import OpenAI
import os
import logging
import sqlite3 # Import for SQLite database
# import bcrypt # Removed bcrypt

# --- Logging Setup ---
logging.basicConfig(filename='app_activity.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

st.set_option('client.showErrorDetails', True)
st.set_page_config(page_title="This Day in History", layout="centered")

# --- Database Setup (SQLite) ---
DB_NAME = 'users.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # CRITICAL SECURITY WARNING: Storing password as plain text (password_plain) is HIGHLY INSECURE.
    # This is for demonstration without bcrypt ONLY. NEVER use in production.
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_plain TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    logging.info("SQLite database initialized.")

def add_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # CRITICAL SECURITY WARNING: Storing password as plain text is HIGHLY INSECURE.
    # This is for demonstration without bcrypt ONLY. NEVER use in production.
    try:
        c.execute("INSERT INTO users (username, password_plain) VALUES (?, ?)", (username, password))
        conn.commit()
        logging.info(f"User '{username}' registered successfully (INSECURELY STORED PASSWORD).")
        return True
    except sqlite3.IntegrityError:
        logging.warning(f"Registration failed: Username '{username}' already exists.")
        return False # Username already exists
    finally:
        conn.close()

def verify_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # CRITICAL SECURITY WARNING: Comparing plain text password is HIGHLY INSECURE.
    # This is for demonstration without bcrypt ONLY. NEVER use in production.
    c.execute("SELECT password_plain FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    if result:
        stored_password = result[0]
        if password == stored_password: # Direct comparison of plain text passwords
            return True
    return False

# Initialize the database on app start
init_db()

# --- Custom CSS ---
st.markdown("""
<style>
body { background-color: #e8f0fe; font-family: 'Inter', sans-serif; } /* This sets the light blue background */
.stApp { background-color: #e8f0fe; } /* Ensure Streamlit's main app container also gets the color */
h1 { text-align: center; color: #333333; margin: 2rem auto 1.5rem; font-size: 2.5em; font-weight: 700; }
.stButton>button { background-color: #4CAF50; color: white; padding: 0.8em 2em; border: none; border-radius: 8px; font-weight: bold; box-shadow: 2px 2px 4px rgba(0,0,0,0.2); }
.stButton>button:hover { background-color: #45a049; transform: translateY(-2px); }
.stTextInput>div>div>input { border-radius: 8px; padding: 10px; border: 1px solid #ccc; box-shadow: inset 0 1px 2px rgba(0,0,0,0.05); }
.stTextInput>div>div>input:focus { border-color: #4CAF50; }
.stAlert { border-radius: 8px; background-color: #e6f7ff; border-color: #91d5ff; color: #004085; }
</style>
""", unsafe_allow_html=True)

# --- OpenAI Init ---
api_key = os.environ.get("OPENAI_API_KEY")

if not api_key and "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
    logging.info("Found OpenAI API key in st.secrets.")
else:
    logging.warning("OPENAI_API_KEY not found in environment or st.secrets.")

if not api_key:
    st.error("❌ OPENAI_API_KEY is missing from environment or secrets. Please set it up to use the app.")
    logging.critical("OpenAI API key missing, app stopped.")
    st.stop()

try:
    client_ai = OpenAI(api_key=api_key)
    logging.info("OpenAI client initialized successfully.")
except Exception as e:
    st.error(f"Failed to initialize OpenAI. Error: {e}")
    logging.critical(f"Failed to initialize OpenAI client: {e}")
    st.stop()

# --- PDF helpers ---
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

# --- AI fetch ---
@st.cache_data(ttl=86400)
def get_this_day_in_history(day, month, profile, _client):
    profile_str = ", ".join([f"{k}: {v}" for k, v in profile.items() if v])
    prompt = f"""
    You are a historical assistant. Provide:
    1. A positive/cultural event from {month:02d}-{day:02d} (1900-1965)
    2. A famous birth (1850-1960) relevant to: {profile_str}
    3. A fun fact for this date
    4. 3 trivia questions and answers, easy to recognize. The answers should be enclosed in parentheses.
    Format:
    Event: [Title] - [Year]
    [Approximately 150-200 words describing the event.]

    Born on this Day: [Name]
    [Approximately 50-100 words describing the person and their significance.]

    Fun Fact: [A concise and interesting fact about the date.]

    Trivia Questions:
    1. [Question 1]? (Answer: [Answer 1])
    2. [Question 2]? (Answer: [Answer 2])
    3. [Question 3]? (Answer: [Answer 3])
    """
    try:
        res = _client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
        logging.info(f"Successfully fetched AI data for {month:02d}-{day:02d}.")
        return res.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Error fetching AI data for {month:02d}-{day:02d}: {e}")
        return f"ERROR: {e}"

# --- Authentication Forms ---
def register_form():
    with st.sidebar.form("register_form"):
        st.header("Register New Account")
        new_username = st.text_input("New Username", key="reg_username")
        new_password = st.text_input("New Password", type="password", key="reg_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm_password")
        register_button = st.form_submit_button("Register")

        if register_button:
            if not new_username or not new_password or not confirm_password:
                st.error("Please fill in all fields.")
            elif new_password != confirm_password:
                st.error("Passwords do not match.")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters long.")
            else:
                if add_user(new_username, new_password):
                    st.success("Account created successfully! Please log in.")
                    # Log with security warning
                    logging.info(f"User '{new_username}' registered successfully (password stored insecurely).")
                    st.session_state['show_login'] = True # Switch to login after successful registration
                else:
                    st.error("Username already exists. Please choose a different one.")
                    logging.warning(f"Registration failed: Username '{new_username}' already exists.")

def login_form():
    with st.sidebar.form("login_form"):
        st.header("Login")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        login_button = st.form_submit_button("Log In")

        if login_button:
            if verify_user(username, password):
                st.session_state['logged_in'] = True
                st.session_state['username'] = username
                st.success(f"Welcome, {username}!")
                logging.info(f"User '{username}' logged in successfully.")
                st.rerun() # Rerun to hide login form and show app
            else:
                st.error("Incorrect username or password.")
                logging.warning(f"Failed login attempt for username: {username}")
    st.sidebar.markdown("---")

# --- Main App ---
st.header("🗓️ This Day in History!")

# Initialize session state for login/registration flow
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'show_login' not in st.session_state:
    st.session_state['show_login'] = True # Default to showing login form

# Display authentication forms
if not st.session_state['logged_in']:
    if st.session_state['show_login']:
        login_form()
        if st.sidebar.button("Don't have an account? Register Here"):
            st.session_state['show_login'] = False
            st.rerun()
    else:
        register_form()
        if st.sidebar.button("Already have an account? Log In Here"):
            st.session_state['show_login'] = True
            st.rerun()
    st.info("Please log in or register to use the This Day in History app.")
else:
    # App content when logged in
    st.sidebar.success(f"Logged in as {st.session_state['username']}")
    if st.sidebar.button("Log Out"):
        logging.info(f"User '{st.session_state['username']}' logged out.")
        st.session_state['logged_in'] = False
        st.session_state.pop('username', None)
        st.session_state.pop('parsed', None)
        st.session_state.pop('last_date', None)
        st.session_state['show_login'] = True # Go back to login form
        st.rerun()

    name = st.text_input("Enter Pair's Name:", "")
    today = st.date_input("Select a date", value=date.today(), max_value=date.today())

    day, month = today.day, today.month
    today_str = today.strftime('%B %d, %Y')
    profile = {"name": name, "jobs": "", "hobbies": "", "decade": "", "life_experiences": ""} # Consider adding more profile inputs in the UI

    if name:
        if 'last_date' not in st.session_state or st.session_state['last_date'] != today or 'parsed' not in st.session_state:
            with st.spinner("Getting today's facts..."):
                raw = get_this_day_in_history(day, month, profile, client_ai)
                if raw.startswith("ERROR"):
                    st.error(raw)
                    logging.error(f"Failed to retrieve history for {today_str} due to an AI error for user '{st.session_state['username']}'.")
                    st.stop()

                sections = raw.split("\n\n")
                parsed = {"event_title": "", "event_article": "", "born_section": "", "fun_fact": "", "trivia": []}
                for section in sections:
                    if section.startswith("Event:"):
                        first_line = section.split("\n")[0].replace("Event:", "").strip()
                        parsed["event_title"] = first_line.split(' - ')[0].strip() if ' - ' in first_line else first_line
                        parsed["event_article"] = "\n".join(section.split("\n")[1:]).strip()
                    elif section.startswith("Born on this Day:"):
                        parsed["born_section"] = section.replace("Born on this Day:", "").strip()
                    elif section.startswith("Fun Fact:"):
                        parsed["fun_fact"] = section.replace("Fun Fact:", "").strip()
                    elif section.startswith("Trivia Questions:"):
                        lines = section.replace("Trivia Questions:", "").strip().split("\n")
                        parsed["trivia"] = [line.strip() for line in lines if line.strip()]

                st.session_state['parsed'] = parsed
                st.session_state['last_date'] = today
                logging.info(f"Successfully parsed AI response for {today_str} for user '{st.session_state['username']}'.")

        parsed = st.session_state['parsed']

        st.markdown(f"### Today is: **{today_str}**")
        st.subheader("Significant Event:")
        st.markdown(f"**{parsed['event_title']}**")
        st.info(parsed['event_article'])
        if st.download_button("Download Article PDF", generate_article_pdf(parsed['event_title'], parsed['event_article']), file_name=f"{parsed['event_title'].replace(' ', '_')}_article.pdf"):
            logging.info(f"User '{st.session_state['username']}' downloaded article PDF: {parsed['event_title']}.")

        st.markdown("---")
        st.subheader("Famous Person Born Today:")
        name_guess = parsed['born_section'].split('\n')[0] if '\n' in parsed['born_section'] else parsed['born_section']
        st.image(f"https://placehold.co/150x150?text={name_guess}", width=150, caption=name_guess)
        st.markdown(parsed['born_section'])

        st.markdown("---")
        st.subheader("Fun Fact:")
        st.info(parsed['fun_fact'])

        st.markdown("---")
        st.subheader("Trivia Time!")
        for t in parsed['trivia']:
            st.markdown(t)

        st.markdown("---")
        st.subheader("Full Summary PDF")
        full_pdf = generate_full_history_pdf(parsed['event_title'], parsed['event_article'], parsed['born_section'], parsed['fun_fact'], parsed['trivia'], today_str, name)
        if st.download_button("Download Full PDF", full_pdf, file_name=f"This_Day_in_History_{today.strftime('%Y_%m_%d')}.pdf"):
            logging.info(f"User '{st.session_state['username']}' downloaded full summary PDF for {today_str}.")
    else:
        st.info("Enter a Pair's Name to begin generating history facts!")
