import streamlit as st
import json
from fpdf import FPDF
from datetime import datetime, date
from openai import OpenAI
import os
import logging
import sqlite3
import gspread
from oauth22client.service_account import ServiceAccountCredentials
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

/* GLOBAL RESET */
body, .stApp {
    background-color: #f4f1f8 !important;
    color: #2b2b2b !important;
    font-family: 'Inter', sans-serif;
}

/* HEADINGS */
h1, h2, h3, h4, h5, h6, label {
    color: #3b2f5e !important;
    font-weight: bold;
    text-align: center;
}

/* BUTTONS */
.stButton > button {
    background-color: #f49d37 !important;
    color: #ffffff !important;
    font-weight: 600;
    font-size: 1em;
    padding: 0.7em 1.5em;
    border: none;
    border-radius: 8px;
    box-shadow: 2px 2px 4px rgba(0,0,0,0.1);
}
.stButton > button:hover {
    background-color: #d87f1f !important;
}

/* INPUT FIELDS */
input, textarea {
    background-color: white !important;
    color: #2b2b2b !important;
    border: 1px solid #ccc !important;
    border-radius: 8px !important;
    padding: 10px !important;
}

/* STREAMLIT TABS (Login/Register) */
div[data-baseweb="tab"] {
    color: #3b2f5e !important;
    font-weight: 600 !important;
}
div[data-baseweb="tab"]:not([aria-selected="true"]) {
    color: #7e7e7e !important;
}

/* INFO BOX FIX */
div[data-testid="stAlertInfo"] {
    background-color: #e0ecff !important;
    color: #1a1a1a !important;
    font-weight: 500;
    border-left: 6px solid #4299e1;
    border-radius: 6px;
    padding: 1rem;
}

/* SUCCESS BOX */
div[data-testid="stAlertSuccess"] {
    background-color: #e6f4ea !important;
    color: #1c4532 !important;
    border-left: 6px solid #38a169;
}

/* WARNING BOX */
div[data-testid="stAlertWarning"] {
    background-color: #fffaf0 !important;
    color: #744210 !important;
    border-left: 6px solid #ed8936;
}

/* ERROR BOX */
div[data-testid="stAlertError"] {
    background-color: #fff5f5 !important;
    color: #742a2a !important;
    border-left: 6px solid #e53e3e;
}

/* SIDEBAR */
section[data-testid="stSidebar"] {
    background-color: #e8ddf0 !important;
    color: #2b2b2b !important;
}
</style>
""", unsafe_allow_html=True)


# --- Google Sheets Configuration ---
GSHEET_USERS_ID = '15LXglm49XBJBzeavaHvhgQn3SakqLGeRV80PxPHQfZ4' # Replace with your actual Google Sheet ID

# --- Google Sheets Debugging ---
@st.cache_resource
def get_gsheet_client():
    """Authorizes and returns a gspread client."""
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
        return client
    except Exception as e:
        logging.error(f"Google Sheets auth failed: {e}")
        st.warning(f"Failed to authorize Google Sheets: {e}. Please check your GOOGLE_SERVICE_JSON secret and ensure the service account has edit access to your Google Sheet.")
        return None

# --- User Management Functions ---
def init_db():
    """Initializes the SQLite database for user storage."""
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

# Initialize the database on app startup
init_db()

def add_user(username, password):
    """Adds a new user to the SQLite database and logs to Google Sheets."""
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_plain) VALUES (?, ?)", (username, password))
        conn.commit()
        
        client = get_gsheet_client()
        if client:
            try:
                sheet = client.open_by_key(GSHEET_USERS_ID).worksheet("Users")
                sheet.append_row([username, password, str(datetime.now())])
                logging.info(f"User {username} registered and logged to Google Sheets with password.")
            except Exception as sheet_error:
                logging.error(f"Failed to log user to Google Sheet: {sheet_error}")
                st.error(f"Error logging user registration to Google Sheet: {sheet_error}")
        return True
    except sqlite3.IntegrityError:
        return False # Username already exists
    finally:
        conn.close()

def log_login(username):
    """Logs user login attempts to Google Sheets."""
    client = get_gsheet_client()
    if client:
        try:
            sheet = client.open_by_key(GSHEET_USERS_ID).worksheet("Logins") # Use a different sheet for logins
            sheet.append_row([username, str(datetime.now())])
            logging.info(f"Login by {username} logged to Google Sheets.")
        except Exception as sheet_error:
            logging.error(f"Failed to log login to Google Sheet: {sheet_error}")
            st.error(f"Error logging user login to Google Sheet: {sheet_error}")

def verify_user(username, password):
    """Verifies user credentials against the SQLite database."""
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT password_plain FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    if result and result[0] == password:
        log_login(username)
        return True
    return False

# --- OpenAI API Interaction ---
@st.cache_resource
def get_openai_client():
    """Initializes and returns the OpenAI client."""
    try:
        return OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    except KeyError:
        st.error("OpenAI API key not found in Streamlit secrets. Please add OPENAI_API_KEY to your secrets.toml file.")
        return None

@st.cache_data(show_spinner="Fetching historical events...")
def get_history_data(day, month, ai_client):
    """
    Fetches historical events for a given day and month using the OpenAI API.
    """
    if not ai_client:
        return []
    try:
        prompt = f"Tell me about historical events that happened on {month}/{day}. Provide the information in a concise, engaging, and informative manner, suitable for a 'This Day in History' app. Format the output as a JSON object with a single key 'events' which is a list of objects. Each object should have 'year', 'event', 'category' (e.g., 'Historical', 'Scientific', 'Cultural', 'Births', 'Deaths', 'Inventions'), and 'source' (if applicable, or 'AI Generated' if not). Aim for 5-7 significant events."

        response = ai_client.chat.completions.create(
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
    except json.JSONDecodeError:
        logging.error("OpenAI response was not a valid JSON.")
        st.error("Failed to parse historical events. Please try again.")
        return []
    except Exception as e:
        logging.error(f"Error fetching history data from OpenAI: {e}")
        st.error(f"An error occurred while fetching historical data: {e}")
        return []

@st.cache_data(show_spinner="Summarizing event...")
def summarize_text(text, ai_client):
    """
    Summarizes a given text using the OpenAI API.
    """
    if not ai_client:
        return "Summary service not available."
    try:
        prompt = f"Summarize the following text concisely: {text}"
        response = ai_client.chat.completions.create(
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
    """Sends an email using SMTP."""
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
    except KeyError:
        st.error("Email credentials not found in Streamlit secrets. Please add EMAIL_USERNAME and EMAIL_PASSWORD.")
        return False
    except Exception as e:
        logging.error(f"Failed to send email: {e}")
        return False

# --- Streamlit App Logic ---

# Initialize session state variables if not already present
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = None
if 'pdf_generated' not in st.session_state:
    st.session_state['pdf_generated'] = False
if 'email_sent' not in st.session_state:
    st.session_state['email_sent'] = False

# --- Authentication Section ---
if not st.session_state['logged_in']:
    st.title("Welcome to This Day in History!")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        st.subheader("Login")
        with st.form("login_form"):
            login_username = st.text_input("Username", key="login_username_input")
            login_password = st.text_input("Password", type="password", key="login_password_input")
            login_submit = st.form_submit_button("Login")

            if login_submit:
                if verify_user(login_username, login_password):
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = login_username
                    st.success("Logged in successfully!")
                    st.experimental_rerun() # Use rerun to update the entire app state
                else:
                    st.error("Invalid username or password.")

    with tab2:
        st.subheader("Register")
        with st.form("register_form"):
            new_username = st.text_input("New Username", key="new_username_input")
            new_password = st.text_input("New Password", type="password", key="new_password_input")
            register_submit = st.form_submit_button("Register")

            if register_submit:
                if add_user(new_username, new_password):
                    st.success("Registration successful! Please log in.")
                    # Optionally clear the registration fields after successful registration
                    st.session_state.new_username_input = "" 
                    st.session_state.new_password_input = ""
                else:
                    st.error("Username already exists.")
else:
    # --- Main App Content (after login) ---
    st.title(f"This Day in History - Welcome, {st.session_state['username']}!")

    today = date.today()
    ai_client = get_openai_client() # Get the cached OpenAI client

    output = []
    if ai_client:
        output = get_history_data(today.day, today.month, ai_client)
    else:
        st.warning("Cannot fetch historical events because OpenAI client failed to initialize.")

    if output:
        st.subheader(f"Events on {today.strftime('%B %d')}:")
        for i, event in enumerate(output):
            with st.container(border=True):
                st.markdown(f"### {event['year']}: {event['event']}")
                st.markdown(f"**Category:** {event['category']}")
                st.markdown(f"**Source:** {event.get('source', 'AI Generated')}")

                if st.button(f"Summarize this event", key=f"summarize_button_{i}"):
                    summary = summarize_text(event['event'], ai_client)
                    st.info(summary)
    else:
        st.info("No historical events found for this date, or there was an error fetching data.")

    st.markdown("---") # Separator

    # --- PDF Download Functionality ---
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

    st.subheader("Download & Share Events")
    
    col_pdf, col_email = st.columns(2)

    with col_pdf:
        if st.button("Generate PDF for Download"):
            if output:
                pdf_file = create_pdf(output)
                with open(pdf_file, "rb") as f:
                    st.download_button(
                        label="Click to Download PDF",
                        data=f.read(),
                        file_name=f"This_Day_in_History_{today.strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        key="download_pdf_button"
                    )
                os.remove(pdf_file) # Clean up the generated PDF file immediately
                st.session_state['pdf_generated'] = True
            else:
                st.warning("No events to download.")

    with col_email:
        with st.form("email_form"):
            recipient_email = st.text_input("Recipient Email", key="recipient_email_input")
            send_email_button = st.form_submit_button("Send Email")

            if send_email_button:
                if output and recipient_email:
                    email_body = f"Hello,\n\nHere are some historical events for {today.strftime('%B %d')}:\n\n"
                    for event in output:
                        email_body += f"- {event['year']}: {event['event']} (Category: {event['category']})\n"
                    email_body += f"\n--\nSent from This Day in History app by {st.session_state['username']}"

                    if send_email(recipient_email, f"This Day in History - {today.strftime('%B %d')}", email_body):
                        st.success("Email sent successfully!")
                        st.session_state['email_sent'] = True
                        st.session_state.recipient_email_input = "" # Clear email field
                    else:
                        st.error("Failed to send email. Please check your email configuration and try again.")
                else:
                    st.warning("Please enter a recipient email and ensure events are loaded before sending.")
    
    st.markdown("---") # Separator

    # Logout Button
    if st.button("Logout", help="Click to log out and return to the login screen."):
        st.session_state['logged_in'] = False
        st.session_state['username'] = None
        st.session_state['pdf_generated'] = False # Reset PDF state
        st.session_state['email_sent'] = False # Reset email state
        st.experimental_rerun() # Use rerun to clear the entire app state and show login
