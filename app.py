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
        if "private_key" in creds_dict and "\n" in creds_dict["private_key"]:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\n", "\n")
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
                sheet.append_row([username, str(datetime.now())])
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
            sheet.append_row([f"LOGIN: {username}", str(datetime.now())])
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

# Ready to use `add_user()` and `verify_user()` in your Streamlit forms.

# Assuming these functions are defined elsewhere in your app.py
# If they are not, you will need to add their definitions.

# @st.cache_data is important for performance with Streamlit
@st.cache_data
def get_history_data(day, month, _ai_client): # Added underscore to _ai_client
    """
    Fetches historical events for a given day and month using the OpenAI API.
    The _ai_client parameter is not hashed by Streamlit's cache.
    """
    try:
        prompt = f"Tell me about historical events that happened on {month}/{day}. Provide the information in a concise, engaging, and informative manner, suitable for a 'This Day in History' app. Format the output as a JSON object with a single key 'events' which is a list of objects. Each object should have 'year', 'event', 'category' (e.g., 'Historical', 'Scientific', 'Cultural', 'Births', 'Deaths', 'Inventions'), and 'source' (if applicable, or 'AI Generated' if not). Aim for 5-7 significant events."

        response = _ai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides historical facts."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        history_json = json.loads(response.choices[0].message.content)
        return history_json.get('events', [])
    except Exception as e:
        logging.error(f"Error fetching history data from OpenAI: {e}")
        return []

@st.cache_data
def summarize_text(text, _ai_client): # Added underscore to _ai_client
    """
    Summarizes a given text using the OpenAI API.
    The _ai_client parameter is not hashed by Streamlit's cache.
    """
    try:
        prompt = f"Summarize the following text: {text}"
        response = _ai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes text."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Error summarizing text with OpenAI: {e}")
        return "Could not generate summary."

def send_email(to_email, subject, body):
    try:
        gmail_user = st.secrets["EMAIL_USERNAME"]
        gmail_password = st.secrets["EMAIL_PASSWORD"]

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = gmail_user
        msg['To'] = to_email

        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.ehlo()
        server.login(gmail_user, gmail_password)
        server.send_message(msg)
        server.close()
        logging.info(f"Email sent to {to_email}")
        return True
    except Exception as e:
        logging.error(f"Failed to send email: {e}")
        return False

# --- Database Initialization (only run once) ---
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_plain TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- User Authentication Flow ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("Welcome to This Day in History!")

    # Login / Register tabs
    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        st.subheader("Login")
        login_username = st.text_input("Username", key="login_username")
        login_password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login", key="login_button"):
            if verify_user(login_username, login_password):
                st.session_state['logged_in'] = True
                st.session_state['username'] = login_username
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid username or password.")

    with tab2:
        st.subheader("Register")
        new_username = st.text_input("New Username", key="new_username")
        new_password = st.text_input("New Password", type="password", key="new_password")
        if st.button("Register", key="register_button"):
            if add_user(new_username, new_password):
                st.success("Registration successful! Please log in.")
            else:
                st.error("Username already exists.")
else:
    # --- Main App Content (after login) ---
    st.title(f"This Day in History - Welcome, {st.session_state['username']}!")

    today = date.today()

    # Get history data using the modified function call
    # OpenAI client initialization moved to here
    ai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    output = get_history_data(today.day, today.month, ai_client)


    if output:
        st.subheader(f"Events on {today.strftime('%B %d')}:")
        for event in output:
            with st.container(border=True):
                st.markdown(f"### {event['year']}: {event['event']}")
                st.markdown(f"**Category:** {event['category']}")
                if 'source' in event:
                    st.markdown(f"**Source:** {event['source']}")
                else:
                    st.markdown(f"**Source:** AI Generated")

                if st.button(f"Summarize this event", key=f"summarize_{event['year']}_{event['event']}"):
                    summary = summarize_text(event['event'], ai_client) # Pass the ai_client
                    st.info(summary)
    else:
        st.info("No historical events found for this date, or there was an error fetching data.")

    # PDF Download Functionality
    def create_pdf(events, filename="This_Day_in_History.pdf"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="This Day in History", ln=True, align="C")
        pdf.ln(10)

        for event in events:
            pdf.multi_cell(0, 10, f"Year: {event['year']}\nEvent: {event['event']}\nCategory: {event['category']}\nSource: {event.get('source', 'AI Generated')}\n\n")
        pdf.output(filename)
        return filename

    if st.button("Download as PDF"):
        if output:
            pdf_file = create_pdf(output)
            with open(pdf_file, "rb") as f:
                st.download_button(
                    label="Click to Download PDF",
                    data=f.read(),
                    file_name=pdf_file,
                    mime="application/pdf"
                )
            os.remove(pdf_file) # Clean up the generated PDF file
        else:
            st.warning("No events to download.")

    # Email Sharing
    st.subheader("Share Today's Events")
    recipient_email = st.text_input("Recipient Email")
    if st.button("Send Email"):
        if output and recipient_email:
            email_body = f"Hello,\n\nHere are some historical events for {today.strftime('%B %d')}:\n\n"
            for event in output:
                email_body += f"- {event['year']}: {event['event']} (Category: {event['category']})\n"
            email_body += "\nEnjoy your day!"

            if send_email(recipient_email, "This Day in History", email_body):
                st.success("Email sent successfully!")
            else:
                st.error("Failed to send email. Please check your email configuration.")
        else:
            st.warning("Please enter a recipient email and ensure events are loaded.")

    # Logout Button
    if st.button("Logout"):
        st.session_state['logged_in'] = False
        st.session_state['username'] = None
        st.rerun()

