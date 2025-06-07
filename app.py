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
# This CSS sets up a light background with dark text for optimal contrast.
st.markdown("""
<style>
body, .stApp {
    background-color: #ffffff !important; /* White background */
    color: #000000 !important; /* Black text for general content */
    font-family: 'Inter', sans-serif;
    padding: 1rem;
}

h1, h2, h3, h4, h5, h6, label {
    color: #000000 !important; /* Black for all headings and labels */
    text-align: center;
    font-weight: 700;
    margin: 2rem auto 1.5rem;
    font-size: 2em;
}

.stButton>button {
    background-color: #4CAF50;
    color: white; /* White text for buttons */
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
    background-color: #ffffff; /* White background for input fields */
    color: #000000; /* Black text for input fields */
    border-radius: 8px;
    padding: 10px;
    border: 1px solid #ccc;
    box-shadow: inset 0 1px 2px rgba(0,0,0,0.05);
}

.stTextInput>div>div>input:focus {
    border-color: #4CAF50;
}

.card {
    background-color: #f8f9fa; /* Light grey background for cards */
    border-radius: 12px;
    padding: 20px;
    margin: 20px 0;
    box-shadow: 0 4px 8px rgba(0,0,0,0.05);
    border: 1px solid #e0e0e0;
}
.card h3 {
    font-size: 1.4em;
    margin-bottom: 0.5em;
    color: #000; /* Black text for card headings */
}
.card p {
    font-size: 1.1em;
    color: #333; /* Dark grey for card paragraph text */
    line-height: 1.6em;
    margin-bottom: 1em;
}
/* Ensure Streamlit's internal elements also pick up the default text color */
.stMarkdown, .stText, .stJson, .stCode, .stAlert p {
    color: #000000 !important; /* Black text for general Streamlit text elements */
}
</style>
""", unsafe_allow_html=True)

# --- Google Sheets Configuration ---
# Google Sheet ID for "Users" logging
GSHEET_USERS_ID = '15LXglm49XBJBzeavaHvhgQn3SakqLGeRV80PxPHQfZ4'

def get_gsheet_client():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        # Load credentials directly from st.secrets dictionary
        creds_dict = st.secrets["GOOGLE_SERVICE_JSON"]
        # Convert private_key for gspread if it's not already in the correct format
        # (Sometimes it comes with literal \n which needs to be interpreted)
        if "private_key" in creds_dict and "\\n" in creds_dict["private_key"]:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        logging.debug("Google Sheets client successfully authorized.")
        return client
    except KeyError:
        logging.error("GOOGLE_SERVICE_JSON not found in st.secrets.")
        st.error("Google Sheets setup error: 'GOOGLE_SERVICE_JSON' secret is missing. Please configure it.")
        return None
    except Exception as e:
        logging.error(f"Google Sheets auth failed: {e}")
        st.error(f"Google Sheets authentication error: {e}. Check your service account credentials.")
        return None

# --- Daily Email Export (placeholder) ---
def send_daily_email(subject, body, to_email):
    # This function remains a placeholder as per previous discussions, not fully implemented.
    # Requires SMTP_SERVER, SMTP_USER, SMTP_PASS environment variables or secrets.
    try:
        smtp_server = os.getenv("SMTP_SERVER") or st.secrets.get("SMTP_SERVER")
        smtp_user = os.getenv("SMTP_USER") or st.secrets.get("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS") or st.secrets.get("SMTP_PASS")

        if not all([smtp_server, smtp_user, smtp_pass]):
            logging.warning("SMTP credentials missing, cannot send daily email.")
            st.warning("Email service not configured. Daily emails won't be sent.")
            return

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = smtp_user
        msg['To'] = to_email

        with smtplib.SMTP_SSL(smtp_server, 465) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [to_email], msg.as_string())
        logging.info("Daily email sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send email: {e}")
        st.warning(f"Email send failed: {e}")

# --- Multi-date Comparison (placeholder setup) ---
if 'history_cache' not in st.session_state:
    st.session_state['history_cache'] = {}

# --- Initialize App Content (OpenAI & SQLite DB) ---
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key and "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
if not api_key:
    st.error("❌ OPENAI_API_KEY is missing from environment or secrets. Please set it up.")
    st.stop()
client_ai = OpenAI(api_key=api_key)

DB_NAME = 'users.db'
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # CRITICAL SECURITY WARNING: Storing password as plain text (password_plain) is HIGHLY INSECURE.
    # This is for demonstration without bcrypt ONLY. NEVER use in production.
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_plain TEXT NOT NULL)''')
    conn.commit()
    conn.close()
init_db()

def add_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        # CRITICAL SECURITY WARNING: Storing password as plain text is HIGHLY INSECURE.
        # This is for demonstration without bcrypt ONLY. NEVER use in production.
        c.execute("INSERT INTO users (username, password_plain) VALUES (?, ?)", (username, password))
        conn.commit()
        logging.info(f"User '{username}' registered successfully (password stored insecurely).")

        # --- Google Sheets Logging for Registration ---
        client = get_gsheet_client()
        if client:
            try:
                # Open by key for robustness, then select worksheet "Users"
                spreadsheet = client.open_by_key(GSHEET_USERS_ID) #
                worksheet = spreadsheet.worksheet("Users") #
                worksheet.append_row([username, str(datetime.now())]) #
                logging.info(f"User '{username}' registration logged to Google Sheet 'Users'.") #
            except gspread.exceptions.SpreadsheetNotFound:
                logging.error(f"Google Sheet with ID {GSHEET_USERS_ID} not found. Please ensure it exists and is shared correctly.")
                st.warning("Google Sheet not found for logging. User registered locally.")
            except gspread.exceptions.WorksheetNotFound:
                logging.error(f"Worksheet 'Users' not found in spreadsheet ID {GSHEET_USERS_ID}. Please ensure it exists.")
                st.warning("Google Sheet worksheet 'Users' not found. User registered locally.")
            except Exception as sheet_error:
                logging.error(f"Failed to write user '{username}' to Google Sheet: {sheet_error}")
                st.warning(f"Failed to log user to Google Sheet: {sheet_error}. User registered locally.")
        else:
            logging.warning("Google Sheets client not available, user registration not logged to GSheets.")
        return True
    except sqlite3.IntegrityError:
        logging.warning(f"Registration failed: Username '{username}' already exists in local DB.")
        return False
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
    return result and result[0] == password

# --- PDF Helper ---
def generate_article_pdf(title, content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.multi_cell(0, 10, title, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 8, content.encode('latin-1', 'replace').decode('latin-1'))
    return pdf.output(dest='S').encode('latin-1')

# --- Main Auth Flow ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'show_login' not in st.session_state:
    st.session_state['show_login'] = True

if not st.session_state.logged_in:
    st.header("Welcome to This Day in History!")
    if st.session_state.show_login:
        with st.sidebar.form("login"):
            st.subheader("Login")
            st.text_input("Username", key="login_user")
            st.text_input("Password", type="password", key="login_pass")
            if st.form_submit_button("Log In"):
                if verify_user(st.session_state.login_user, st.session_state.login_pass):
                    st.session_state.logged_in = True
                    st.session_state.username = st.session_state.login_user
                    logging.info(f"User '{st.session_state.username}' logged in successfully.")
                    st.rerun()
                else:
                    st.error("Incorrect username or password.")
                    logging.warning(f"Failed login attempt for username: {st.session_state.login_user}")
        if st.sidebar.button("Don't have an account? Register Here"):
            st.session_state.show_login = False
            st.rerun()
    else:
        with st.sidebar.form("register"):
            st.subheader("Register New Account")
            new_username = st.text_input("New Username", key="reg_user")
            new_password = st.text_input("New Password", type="password", key="reg_pass")
            confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")
            if st.form_submit_button("Register"):
                if not new_username or not new_password or not confirm_password:
                    st.error("Please fill in all fields.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters long.")
                else:
                    if add_user(new_username, new_password):
                        st.success("Registration successful. Please log in.")
                        st.session_state.show_login = True
                        st.rerun()
                    else:
                        st.error("Username already exists. Please choose a different one.")
        if st.sidebar.button("Already registered? Log In Here"):
            st.session_state.show_login = True
            st.rerun()
    st.stop() # Stop execution if not logged in

# --- Main App Logic (Displayed after successful login) ---
st.header("🗓️ This Day in History!")
st.sidebar.success(f"Logged in as {st.session_state['username']}")
if st.sidebar.button("Log Out"):
    logging.info(f"User '{st.session_state['username']}' logged out.")
    st.session_state.clear()
    st.rerun()

name = st.text_input("Enter Pair's Name:", "")
today = st.date_input("Select a date", value=date.today(), max_value=date.today())

if name:
    # Caching AI response for the current date to avoid re-calling OpenAI
    @st.cache_data(ttl=86400) # Cache for 24 hours
    def get_history_data(day, month, current_name, ai_client):
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
            response = ai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            logging.info(f"AI response fetched for {month:02d}-{day:02d}.")
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"AI API call failed for {month:02d}-{day:02d}: {e}")
            st.error(f"Failed to get history from AI: {e}")
            return None # Indicate failure

    # Call the cached function
    with st.spinner("Fetching today's history..."):
        output = get_history_data(today.day, today.month, name, client_ai)

    if output:
        # Parse the output into sections to display in cards
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
            elif current_section == "Trivia Questions" and line and line.startswith(tuple(f"{i}." for i in range(1, 4))):
                parsed_data["Trivia Questions"].append(line)
            elif current_section:
                # Append to the current section's description
                if current_section == "Event":
                    parsed_data["Event"] += line + "\n"
                elif current_section == "Born on this Day":
                    parsed_data["Born on this Day"] += line + "\n"
                elif current_section == "Fun Fact":
                    parsed_data["Fun Fact"] += line + "\n"

        # Display content in cards
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

        # Download button for the full summary PDF
        full_pdf_content = "\n\n".join([
            parsed_data["Event"],
            parsed_data["Born on this Day"],
            parsed_data["Fun Fact"],
            "Trivia Questions:\n" + "\n".join(parsed_data["Trivia Questions"])
        ])
        if st.download_button("Download Summary PDF", generate_article_pdf(f"This Day in History - {today.strftime('%B %d, %Y')}", full_pdf_content), file_name=f"history_summary_{today.strftime('%Y%m%d')}.pdf"):
            logging.info(f"User '{st.session_state['username']}' downloaded full summary PDF for {today.strftime('%B %d, %Y')}.")
else:
    st.info("Please enter a Pair's Name to begin generating history facts!")
