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
/* Reset and base colors */
body, .stApp {
    background-color: #f4f1f8 !important;  /* Light lavender */
    color: #222 !important;  /* Dark text */
    font-family: 'Inter', sans-serif;
}

/* Headings */
h1, h2, h3, h4, h5, h6, label {
    color: #3b2f5e !important;  /* Deep purple */
    font-weight: bold;
    text-align: center;
}

/* Buttons */
.stButton > button {
    background-color: #f49d37 !important;  /* Orange */
    color: white !important;
    font-weight: 600;
    border: none;
    border-radius: 8px;
    padding: 0.7em 1.5em;
    box-shadow: 1px 1px 5px rgba(0,0,0,0.1);
    transition: background 0.2s ease-in-out;
}
.stButton > button:hover {
    background-color: #d87f1f !important;
    transform: translateY(-1px);
}

/* Input Fields */
input, textarea {
    background-color: white !important;
    color: #222 !important;
    border: 1px solid #ccc !important;
    border-radius: 8px !important;
    padding: 10px !important;
    box-shadow: none !important;
}
input:focus, textarea:focus {
    border-color: #9e7ac2 !important;
    outline: none !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #e8ddf0 !important;
    color: #2d2d2d !important;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] label {
    color: #3b2f5e !important;
}

/* Alert Boxes (info, success, warning, error) */
div[data-testid="stAlertInfo"] {
    background-color: #e0ecff !important;
    color: #1a3c66 !important;
    border-left: 6px solid #4299e1;
}
div[data-testid="stAlertSuccess"] {
    background-color: #e6f4ea !important;
    color: #276749 !important;
    border-left: 6px solid #38a169;
}
div[data-testid="stAlertWarning"] {
    background-color: #fff7e6 !important;
    color: #975a16 !important;
    border-left: 6px solid #ed8936;
}
div[data-testid="stAlertError"] {
    background-color: #ffe5e5 !important;
    color: #9b2c2c !important;
    border-left: 6px solid #f56565;
}

/* Tabs */
.css-1v0mbdj > div {
    background-color: #ffffff !important;
    border-radius: 8px;
    padding: 0.75em;
    color: #3b2f5e !important;
    font-weight: bold;
    border: 1px solid #d1c4e9;
}
.css-1v0mbdj > div[aria-selected="true"] {
    background-color: #f4e8ff !important;
    border-color: #9e7ac2;
}

/* Containers */
.card {
    background: #fff;
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.05);
}
</style>
""", unsafe_allow_html=True)



# --- Google Sheets Configuration ---
GSHEET_USERS_ID = '15LXglm49XBJBzeavaHvhgQn3SakqLGeRV80PxPHQfZ4'

# --- Google Sheets Debugging ---
def get_gsheet_client():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        # Load the JSON string from st.secrets and parse it into a dictionary
        creds_json_string = st.secrets["GOOGLE_SERVICE_JSON"]
        creds_dict = json.loads(creds_json_string) 
        
        # Replace escaped newlines if they are present in the private_key (after parsing)
        # This handles cases where secrets.toml might have \\n for literal newlines in the JSON string
        if "private_key" in creds_dict and "\\n" in creds_dict["private_key"]:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        logging.debug("Google Sheets client successfully authorized.")
        
        # Display the service account email for debugging permissions
        st.info(f"Google Sheets Service Account Email: {creds.service_account_email}. Please ensure this email has edit access to your Google Sheet.")
        
        return client
    except Exception as e:
        logging.error(f"Google Sheets auth failed: {e}")
        st.warning(f"Failed to authorize Google Sheets: {e}. Please check your GOOGLE_SERVICE_JSON secret and ensure the service account has access to the sheet.")
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
                # ✅ Now includes password in the sheet logging
                sheet.append_row([username, password, str(datetime.now())])
                logging.info(f"User {username} registered and logged to Google Sheets with password.")
                st.success(f"User '{username}' registered and logged to Google Sheet!")
            except Exception as sheet_error:
                logging.error(f"Failed to log user to Google Sheet: {sheet_error}")
                st.error(f"Error logging user registration to Google Sheet: {sheet_error}")
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
            st.success(f"Login by '{username}' logged to Google Sheet!")
        except Exception as sheet_error:
            logging.error(f"Failed to log login to Google Sheet: {sheet_error}")
            st.error(f"Error logging user login to Google Sheet: {sheet_error}")

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
# Ensure 'logged_in' is initialized to False for new sessions or if it's in an inconsistent state.
# This makes sure the login/register screen is shown on a fresh load.
if 'logged_in' not in st.session_state or st.session_state.get('username') is None:
    st.session_state['logged_in'] = False
    st.session_state['username'] = None # Clear username if not logged in

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
