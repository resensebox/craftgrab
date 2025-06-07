
import streamlit as st
from openai import OpenAI
from datetime import datetime, date
from fpdf import FPDF
import re

st.set_option('client.showErrorDetails', True)
st.set_page_config(page_title="This Day in History", layout="centered")

# --- API Keys and Client Setup ---

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- Google Sheets Logging Setup ---
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
if "GOOGLE_SERVICE_JSON" not in st.secrets:
    st.error("❌ GOOGLE_SERVICE_JSON is missing from Streamlit secrets.")
    st.stop()

import json
service_account_info = json.loads(st.secrets["GOOGLE_SERVICE_JSON"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
gs_client = gspread.authorize(creds)

def log_event(event_type, username):
    try:
        sheet = gs_client.open_by_key("15LXglm49XBJBzeavaHvhgQn3SakqLGeRV80PxPHQfZ4")
        ws = sheet.worksheet("LoginLogs")
        ws.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            event_type,
            username
        ])
    except Exception as e:
        st.warning(f"⚠️ Could not log event '{event_type}' for '{username}': {e}")


def save_new_user_to_sheet(username, password, email):
    try:
        sheet = gs_client.open_by_key("15LXglm49XBJBzeavaHvhgQn3SakqLGeRV80PxPHQfZ4")
        try:
            ws = sheet.worksheet("Users")
        except gspread.exceptions.WorksheetNotFound:
            ws = sheet.add_worksheet(title="Users", rows="100", cols="3")
            ws.append_row(["Username", "Password", "Email"])
        ws.append_row([username, password, email])
    except Exception as e:
        st.warning(f"⚠️ Could not register user '{username}': {e}")

def save_new_user_to_sheet(username, password, email):
    try:
        sheet = gs_client.open_by_key("15LXglm49XBJBzeavaHvhgQn3SakqLGeRV80PxPHQfZ4")
        try:
            ws = sheet.worksheet("Users")
        except gspread.exceptions.WorksheetNotFound:
            ws = sheet.add_worksheet(title="Users", rows="100", cols="3")
            ws.append_row(["Username", "Password", "Email"])
        ws.append_row([username, password, email])
    except Exception as e:
        st.warning(f"⚠️ Could not register user '{username}': {e}")

    try:
        sheet = gs_client.open_by_key("15LXglm49XBJBzeavaHvhgQn3SakqLGeRV80PxPHQfZ4")
        ws = sheet.worksheet("LoginLogs")
        ws.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            event_type,
            username
        ])
    except Exception as e:
        st.warning(f"⚠️ Could not log event '{event_type}' for '{username}': {e}")

if "OPENAI_API_KEY" not in st.secrets:
    st.error("❌ OPENAI_API_KEY is missing from Streamlit secrets.")
    st.stop()
client_ai = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- Session State Initialization ---
if 'is_authenticated' not in st.session_state:
    st.session_state['is_authenticated'] = False
if 'logged_in_username' not in st.session_state:
    st.session_state['logged_in_username'] = ""

# --- Dummy User Store (in production, use Google Sheets or database) ---
USERS = {"demo": "demo123"}


# --- This Day in History Logic ---
def get_this_day_in_history_facts(current_day, current_month, user_info, _ai_client, max_retries=2):
    current_date_str = f"{current_month:02d}-{current_day:02d}"
    prompt = f"""
    You are an assistant generating 'This Day in History' facts for {current_date_str}.
    Please provide:

    1. Event: [Title - Year]\n[Paragraph about event]
    2. Born on this Day: [Name]\n[Description]
    3. Fun Fact: [Line]
    4. Trivia Questions:\n1. Q? (Answer: A)\n2. Q? (Answer: A)\n3. Q? (Answer: A)
    """
    try:
        response = _ai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content.strip()

        event_match = re.search(r"Event:\s*(.*?)\n(.*?)(?=\n\nBorn on this Day:|\Z)", content, re.DOTALL)
        born_match = re.search(r"Born on this Day:\s*(.*?)(?=\n\nFun Fact:|\Z)", content, re.DOTALL)
        fun_fact_match = re.search(r"Fun Fact:\s*(.*?)(?=\n\nTrivia Questions:|\Z)", content, re.DOTALL)
        trivia_match = re.search(r"Trivia Questions:\s*(.*)", content, re.DOTALL)

        event_title = event_match.group(1).split(" - ")[0].strip() if event_match else "Unknown Event"
        event_article = event_match.group(2).strip() if event_match else "No article found."
        born_section = born_match.group(1).strip() if born_match else "No birth record found."
        fun_fact_section = fun_fact_match.group(1).strip() if fun_fact_match else "No fun fact found."
        trivia_lines = trivia_match.group(1).strip().split('\n') if trivia_match else []

        return {
            'event_title': event_title,
            'event_article': event_article,
            'born_section': born_section,
            'fun_fact_section': fun_fact_section,
            'trivia_section': trivia_lines
        }
    except Exception as e:
        st.error(f"Error generating history: {e}")
        return {
            'event_title': "History unavailable",
            'event_article': "Could not fetch history.",
            'born_section': "",
            'fun_fact_section': "",
            'trivia_section': []
        }

def generate_full_history_pdf(event_title, event_article, born_section, fun_fact_section, trivia_section, today_date_str, user_info):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 20)
    pdf.multi_cell(0, 10, f"This Day in History: {today_date_str}", align='C')
    pdf.ln(10)
    pdf.set_font("Arial", "B", 14)
    pdf.multi_cell(0, 10, "Significant Event:")
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 8, f"**{event_title}**\n{event_article}")
    pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.multi_cell(0, 10, "Born on this Day:")
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 8, born_section)
    pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.multi_cell(0, 10, "Fun Fact:")
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 8, fun_fact_section)
    pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.multi_cell(0, 10, "Trivia:")
    pdf.set_font("Arial", "", 12)
    for item in trivia_section:
        pdf.multi_cell(0, 8, item)
    pdf.ln(5)
    pdf.set_font("Arial", "I", 10)
    pdf.multi_cell(0, 5, f"Generated for {user_info['name']}", align='C')
    return pdf.output(dest='S').encode('latin-1')

# --- App UI ---
if st.session_state['is_authenticated']:
        st.sidebar.title("This Day in History")

        st.sidebar.markdown("---")
        if st.sidebar.button("🚪 Log Out"):
            st.session_state['is_authenticated'] = False
            st.session_state['logged_in_username'] = ""
            st.rerun()

    st.title("📅 This Day in History")
        today = datetime.today()
        day, month = today.day, today.month
        user_info = {
            'name': st.session_state['logged_in_username'],
            'jobs': '', 'hobbies': '', 'decade': '', 'life_experiences': '', 'college_chapter': ''
        }
        data = get_this_day_in_history_facts(day, month, user_info, client_ai)
        st.subheader(f"⭐ {data['event_title']}")
        st.write(data['event_article'])
        st.subheader("🎉 Born on this Day")
        st.write(data['born_section'])
        st.subheader("💡 Fun Fact")
        st.write(data['fun_fact_section'])
        st.subheader("🧠 Trivia")
        for q in data['trivia_section']:
    st.write(q)
        if st.button("📄 Download PDF"):
            pdf_bytes = generate_full_history_pdf(
                data['event_title'], data['event_article'], data['born_section'],
                data['fun_fact_section'], data['trivia_section'], today.strftime('%B %d'), user_info
            )
            st.download_button("Download History PDF", pdf_bytes, file_name="this_day_in_history.pdf")
else:
    st.title("Login to Access")
    login_tab, register_tab = st.tabs(["Log In", "Register"])
    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Log In"):
                if username in USERS and USERS[username] == password:
                    st.session_state['is_authenticated'] = True
                    st.session_state['logged_in_username'] = username
                    st.success(f"Welcome {username}!")
                    log_event("login", username)
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
    
# --- Demo Preview on Login Page ---
st.markdown("---")
st.subheader("📋 Example: This Day in History")
demo_user_info = {'name': 'Demo User', 'jobs': '', 'hobbies': '', 'decade': '', 'life_experiences': '', 'college_chapter': ''}
demo_data = get_this_day_in_history_facts(6, 6, demo_user_info, client_ai)

st.markdown(f"### ⭐ {demo_data['event_title']}")
st.write(demo_data['event_article'])

st.markdown("### 🎉 Born on this Day")
st.write(demo_data['born_section'])

st.markdown("### 💡 Fun Fact")
st.write(demo_data['fun_fact_section'])

st.markdown("### 🧠 Trivia")
for q in demo_data['trivia_section']:
    st.markdown(f"- {q}")

if st.button("📄 Download Demo PDF"):
    demo_pdf = generate_full_history_pdf(
        demo_data['event_title'], demo_data['event_article'],
        demo_data['born_section'], demo_data['fun_fact_section'],
        demo_data['trivia_section'], "June 6", demo_user_info
    )
    st.download_button("Download Example PDF", demo_pdf, file_name="example_this_day_history.pdf")


    with register_tab:
        with st.form("register_form"):
    new_username = st.text_input("New Username")
    new_email = st.text_input("Email")
    new_password = st.text_input("New Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")
    st.form_submit_button("Register"):
                if new_password == confirm_password:
                    save_new_user(new_username, new_password)
                    st.session_state['is_authenticated'] = True
                    st.session_state['logged_in_username'] = new_username
                    st.success("Account created!")
                    log_event("register", new_username)
                    st.rerun()
                else:
                    st.error("Passwords do not match.")

