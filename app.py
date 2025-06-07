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
import smtplib
from email.mime.text import MIMEText

# --- Logging Setup ---
logging.basicConfig(filename='app_activity.log', level=logging.DEBUG,
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

h1, h2, h3, h4, h5, h6, label {
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

# --- Google Sheets Configuration ---
GSHEET_USERS_ID = '15LXglm49XBJBzeavaHvhgQn3SakqLGeRV80PxPHQfZ4'

# --- Google Sheets Debugging ---
def get_gsheet_client():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_dict = st.secrets["GOOGLE_SERVICE_JSON"]
        if "private_key" in creds_dict and "\\n" in creds_dict["private_key"]:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        logging.debug("Google Sheets client successfully authorized.")
        return client
    except Exception as e:
        logging.error(f"Google Sheets auth failed: {e}")
        st.error(f"Google Sheets error: {e}")
        return None

# --- Updated add_user to log to specific Sheet ---
def add_user(username, password):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_plain) VALUES (?, ?)", (username, password))
        conn.commit()
        client = get_gsheet_client()
        if client:
            try:
                sheet = client.open_by_key(GSHEET_USERS_ID).worksheet("Users")
                sheet.append_row([username, str(datetime.now()), "REGISTER"])
                logging.info(f"User {username} registered and logged to Google Sheets.")
            except Exception as sheet_error:
                logging.error(f"Failed to log user to Google Sheet: {sheet_error}")
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# --- Add login logging ---
def log_login(username):
    client = get_gsheet_client()
    if client:
        try:
            sheet = client.open_by_key(GSHEET_USERS_ID).worksheet("Users")
            sheet.append_row([username, str(datetime.now()), "LOGIN"])
            logging.info(f"Login by {username} logged to Google Sheets.")
        except Exception as sheet_error:
            logging.error(f"Failed to log login to Google Sheet: {sheet_error}")

# --- Verify user login ---
def verify_user(username, password):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT password_plain FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    if result and result[0] == password:
        log_login(username)
        return True
    return False

# --- Generate PDF ---
def generate_article_pdf(title, content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.multi_cell(0, 10, title, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 8, content.encode('latin-1', 'replace').decode('latin-1'))
    return pdf.output(dest='S').encode('latin-1')

# --- Main App Logic ---
st.header("🗓️ This Day in History!")
name = st.text_input("Enter Pair's Name:", "")
today = st.date_input("Select a date", value=date.today(), max_value=date.today())

if name:
    @st.cache_data(ttl=86400)
    def get_history_data(day, month, ai_client):
        prompt = f"""
        You are a historical assistant. Provide:
        1. A cultural or positive event from {month:02d}-{day:02d} (1900-1965)
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
        2. [Q]? (Answer: [A])
        3. [Q]? (Answer: [A])
        """
        try:
            response = OpenAI(api_key=st.secrets["OPENAI_API_KEY"]).chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"Failed to fetch history: {e}")
            return None

    output = get_history_data(today.day, today.month, OpenAI(api_key=st.secrets["OPENAI_API_KEY"]))
    if output:
        sections = output.split("\n\n")
        parsed_data = {
            "Event": "",
            "Born on this Day": "",
            "Fun Fact": "",
            "Trivia Questions": []
        }
        current_section = None
        for line in output.split('\n'):
            line = line.strip()
            if line.startswith("Event:"):
                parsed_data["Event"] = line + "\n"
                current_section = "Event"
            elif line.startswith("Born on this Day:"):
                parsed_data["Born on this Day"] = line + "\n"
                current_section = "Born on this Day"
            elif line.startswith("Fun Fact:"):
                parsed_data["Fun Fact"] = line + "\n"
                current_section = "Fun Fact"
            elif line.startswith("Trivia Questions:"):
                current_section = "Trivia Questions"
            elif current_section == "Trivia Questions" and line and line[0].isdigit():
                parsed_data["Trivia Questions"].append(line)
            elif current_section:
                parsed_data[current_section] += line + "\n"

        if parsed_data["Event"]:
            st.markdown(f'<div class="card"><h3>Significant Event:</h3><p>{parsed_data["Event"].replace("\n", "<br>")}</p></div>', unsafe_allow_html=True)
        if parsed_data["Born on this Day"]:
            st.markdown(f'<div class="card"><h3>Famous Person Born Today:</h3><p>{parsed_data["Born on this Day"].replace("\n", "<br>")}</p></div>', unsafe_allow_html=True)
        if parsed_data["Fun Fact"]:
            st.markdown(f'<div class="card"><h3>Fun Fact:</h3><p>{parsed_data["Fun Fact"].replace("\n", "<br>")}</p></div>', unsafe_allow_html=True)
        if parsed_data["Trivia Questions"]:
            trivia_html = "<h3>Trivia Time!</h3><ul>"
            for q in parsed_data["Trivia Questions"]:
                trivia_html += f"<li>{q}</li>"
            trivia_html += "</ul>"
            st.markdown(f'<div class="card">{trivia_html}</div>', unsafe_allow_html=True)

        full_pdf_content = "\n\n".join([
            parsed_data["Event"],
            parsed_data["Born on this Day"],
            parsed_data["Fun Fact"],
            "Trivia Questions:\n" + "\n".join(parsed_data["Trivia Questions"])
        ])
        st.download_button("Download Summary PDF", generate_article_pdf(f"This Day in History - {today.strftime('%B %d, %Y')}", full_pdf_content), file_name=f"history_summary_{today.strftime('%Y%m%d')}.pdf")
else:
    st.info("Please enter a Pair's Name to begin.")
