import streamlit as st
import json
from fpdf import FPDF
from datetime import datetime, date
import os
import logging
import sqlite3
import smtplib
from email.mime.text import MIMEText
import requests # For Gemini API
import base64 # For encoding image to base64 if needed for image understanding, not used here
import time # For simulating loading

# --- Logging Setup ---
logging.basicConfig(filename='app_activity.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

st.set_option('client.showErrorDetails', True)
st.set_page_config(page_title="History Hub", layout="wide", initial_sidebar_state="expanded")

# --- Database Setup (SQLite for Users) ---
DB_NAME = 'users.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False # Username already exists
    finally:
        conn.close()

def verify_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = c.fetchone()
    conn.close()
    return user is not None

# --- Gemini API Configuration ---
# Use an empty string for the API key; Canvas will provide it at runtime.
GEMINI_API_KEY = ""
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# --- Email Configuration ---
# For demonstration purposes. In a real app, use Streamlit secrets or environment variables.
# SMTP_SERVER = "smtp.gmail.com" # Example for Gmail
# SMTP_PORT = 587
# SMTP_USERNAME = "your_email@example.com"
# SMTP_PASSWORD = "your_email_password" # Use app-specific passwords for Gmail/Outlook

# --- Session State Initialization ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = None
if 'preferred_categories' not in st.session_state:
    st.session_state['preferred_categories'] = ['Historical', 'Births', 'Deaths', 'Holidays', 'Other'] # Default all
if 'all_categories' not in st.session_state:
    st.session_state['all_categories'] = ['Historical', 'Births', 'Deaths', 'Holidays', 'Other']

# --- Helper Functions ---

def display_message(message_type, text):
    """Displays a custom message with styling."""
    color_map = {
        'success': 'bg-green-100 text-green-700',
        'error': 'bg-red-100 text-red-700',
        'warning': 'bg-yellow-100 text-yellow-700',
        'info': 'bg-blue-100 text-blue-700'
    }
    st.markdown(f"""
    <div class="p-3 mb-4 rounded-lg flex items-center gap-2 text-sm font-medium {color_map.get(message_type, 'bg-gray-100 text-gray-700')}">
        {text}
    </div>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=3600*24) # Cache events for 24 hours
def get_historical_events_from_gemini(selected_date: date):
    """Fetches historical events for a given date using the Gemini API."""
    prompt = (
        f"Provide a list of significant historical events, births, deaths, and holidays for "
        f"{selected_date.strftime('%B %d')}. Categorize each event as 'Historical', 'Births', "
        f"'Deaths', 'Holidays', or 'Other'. Ensure the output is a JSON array of objects, "
        f"each with 'year' (string), 'event' (string), and 'category' (string) fields. "
        f"Example: [{{'year': '1944', 'event': 'D-Day landings.', 'category': 'Historical'}}] "
        f"Ensure the JSON is perfectly parseable and directly usable."
    )

    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "year": {"type": "STRING"},
                        "event": {"type": "STRING"},
                        "category": {"type": "STRING", "enum": st.session_state['all_categories']}
                    },
                    "required": ["year", "event", "category"]
                }
            }
        }
    }

    try:
        response = requests.post(f"{GEMINI_API_URL}?key={GEMINI_API_KEY}", headers=headers, json=payload)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        result = response.json()

        if result and 'candidates' in result and len(result['candidates']) > 0 and \
           'content' in result['candidates'][0] and 'parts' in result['candidates'][0]['content'] and \
           len(result['candidates'][0]['content']['parts']) > 0:
            json_text = result['candidates'][0]['content']['parts'][0]['text']
            events = json.loads(json_text)
            return events
        else:
            logging.error(f"Gemini API returned unexpected structure: {result}")
            display_message('error', 'Failed to get events: Unexpected API response.')
            return []
    except requests.exceptions.RequestException as e:
        logging.error(f"Gemini API request failed: {e}")
        display_message('error', f'Failed to fetch events from Gemini API: {e}')
        return []
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse Gemini API JSON response: {e}. Raw response: {response.text}")
        display_message('error', 'Failed to parse events. Please try again.')
        return []

def create_pdf(events, selected_date):
    """Generates a PDF from the list of events."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size = 12)
    pdf.cell(200, 10, txt = f"Historical Events for {selected_date.strftime('%B %d, %Y')}", ln = True, align = 'C')
    pdf.ln(10) # Add some space

    for event in events:
        pdf.set_font("Arial", 'B', 10) # Bold for year and category
        pdf.multi_cell(0, 5, f"{event['year']}: (Category: {event['category']})", align='L')
        pdf.set_font("Arial", '', 10) # Normal for event text
        pdf.multi_cell(0, 5, f"  {event['event']}", align='L')
        pdf.ln(3) # Small line break between events

    # Save to a temporary file
    filename = f"Events_{selected_date.strftime('%Y%m%d')}.pdf"
    pdf.output(filename)
    return filename

def send_email(recipient_email, subject, body):
    """Sends an email using SMTP."""
    # This requires SMTP server details. For security and simplicity in a demo,
    # it's often better to rely on mailto: links or a dedicated email service.
    # User needs to configure their own SMTP server and credentials.
    display_message('warning', "Email sending functionality requires SMTP server configuration. This is for demonstration. For production, consider secure alternatives like SendGrid/Mailgun or a proper backend service.")
    # Example placeholder:
    # try:
    #     msg = MIMEText(body)
    #     msg['Subject'] = subject
    #     msg['From'] = SMTP_USERNAME
    #     msg['To'] = recipient_email
    #
    #     with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
    #         server.starttls()
    #         server.login(SMTP_USERNAME, SMTP_PASSWORD)
    #         server.send_message(msg)
    #     return True
    # except Exception as e:
    #     logging.error(f"Failed to send email: {e}")
    #     return False
    return False # Placeholder for actual email sending


# --- UI Styling (Tailwind-like CSS for Streamlit) ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

html, body, .stApp {
    font-family: 'Inter', sans-serif;
    color: #2b2b2b;
    background-color: #f4f1f8; /* Light background */
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background-color: #36393f; /* Darker purple/gray like Slack sidebar */
    color: #ffffff;
    padding: 2rem 1.5rem;
    border-radius: 0 10px 10px 0; /* Rounded right corners */
    box-shadow: 2px 0 10px rgba(0, 0, 0, 0.1);
}

[data-testid="stSidebar"] .stButton > button {
    background-color: #663399; /* Medium purple for sidebar buttons */
    color: #ffffff;
    font-weight: 600;
    border: none;
    border-radius: 8px;
    padding: 0.7em 1em;
    width: 100%;
    text-align: left;
    transition: background-color 0.2s ease;
}

[data-testid="stSidebar"] .stButton > button:hover {
    background-color: #7b4aa7; /* Lighter purple on hover */
}

/* Date input in sidebar */
[data-testid="stSidebar"] input[type="date"] {
    background-color: #474a50; /* Darker input background */
    color: #ffffff;
    border: 1px solid #5a5d62;
    border-radius: 8px;
    padding: 0.5rem;
}

/* Checkbox styling in sidebar */
[data-testid="stSidebar"] .stCheckbox span {
    color: #ffffff;
}

[data-testid="stSidebar"] .stCheckbox label {
    display: flex;
    align-items: center;
    margin-bottom: 0.5rem;
}

[data-testid="stSidebar"] .stCheckbox input[type="checkbox"] {
    margin-right: 0.5rem;
}


/* Main content area */
.main .block-container {
    padding-top: 2rem;
    padding-right: 2rem;
    padding-left: 2rem;
    padding-bottom: 2rem;
    background-color: #f4f1f8; /* Light background */
}

h1, h2, h3, h4, h5, h6, label {
    color: #3b2f5e; /* Dark purple for headings */
    font-weight: bold;
}

/* Event cards (like chat messages) */
.event-card {
    background-color: #ffffff;
    border-radius: 12px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.05);
    padding: 1.5rem;
    margin-bottom: 1rem;
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    border: 1px solid #e0e0e0;
}

.event-card .year-avatar {
    flex-shrink: 0;
    width: 3.5rem;
    height: 3.5rem;
    border-radius: 50%;
    background-color: #663399; /* Purple avatar */
    color: #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    font-size: 1.1em;
}

.event-card .event-content p {
    margin: 0;
    color: #333333;
    font-size: 1.05em;
    line-height: 1.5;
}

.event-card .event-meta {
    display: flex;
    align-items: center;
    margin-top: 0.5rem;
    font-size: 0.85em;
    color: #666666;
}

.event-card .category-badge {
    padding: 0.25em 0.75em;
    border-radius: 9999px; /* Full rounded */
    font-weight: 600;
    font-size: 0.75em;
    white-space: nowrap;
}

/* Category colors */
.badge-historical { background-color: #ede9fe; color: #5b21b6; } /* Purple */
.badge-births { background-color: #d1fae5; color: #065f46; } /* Green */
.badge-deaths { background-color: #fee2e2; color: #991b1b; } /* Red */
.badge-holidays { background-color: #dbeafe; color: #1e40af; } /* Blue */
.badge-other { background-color: #e0e0e0; color: #4b5563; } /* Gray */


/* Buttons for PDF/Email */
.stButton > button {
    background-color: #f49d37; /* Orange for main actions */
    color: #ffffff;
    font-weight: 600;
    font-size: 1em;
    padding: 0.7em 1.5em;
    border: none;
    border-radius: 8px;
    box-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    transition: background-color 0.2s ease, transform 0.1s ease;
    display: inline-flex;
    align-items: center;
    gap: 0.5em;
}

.stButton > button:hover {
    background-color: #e08b29;
    transform: translateY(-1px);
}

.stButton > button:active {
    transform: translateY(1px);
}

/* Login screen styles */
.login-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    background-color: #f4f1f8;
}

.login-box {
    background-color: #ffffff;
    border-radius: 12px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
    padding: 3rem;
    width: 100%;
    max-width: 400px;
    text-align: center;
}

.login-box h2 {
    color: #663399; /* Purple for login heading */
    font-size: 2.2em;
    margin-bottom: 1.5rem;
}

.login-box input {
    width: 100%;
    padding: 0.8rem;
    margin-bottom: 1rem;
    border: 1px solid #cccccc;
    border-radius: 8px;
    font-size: 1em;
    transition: border-color 0.2s ease;
}

.login-box input:focus {
    border-color: #663399;
    outline: none;
    box-shadow: 0 0 0 2px rgba(102, 51, 153, 0.2);
}

.login-box button {
    width: 100%;
    padding: 0.8rem;
    background-color: #663399; /* Purple login button */
    color: #ffffff;
    font-weight: 600;
    border: none;
    border-radius: 8px;
    font-size: 1.1em;
    cursor: pointer;
    transition: background-color 0.2s ease;
}

.login-box button:hover {
    background-color: #7b4aa7;
}

/* General Link/Icon styles */
.icon-text {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
</style>
""", unsafe_allow_html=True)


# --- Login / Main App Flow ---

def login_page():
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<div class="login-box">', unsafe_allow_html=True)
    st.markdown('<h2>Welcome Back!</h2>', unsafe_allow_html=True)

    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Login", use_container_width=True):
            if verify_user(username, password):
                st.session_state['logged_in'] = True
                st.session_state['username'] = username
                st.rerun()
            else:
                display_message('error', "Invalid username or password.")
    with col2:
        if st.button("Sign Up", use_container_width=True):
            if username and password:
                if add_user(username, password):
                    display_message('success', "Account created! Please log in.")
                else:
                    display_message('warning', "Username already exists.")
            else:
                display_message('warning', "Please enter a username and password to sign up.")

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def main_app():
    # Sidebar
    with st.sidebar:
        st.markdown(f"""
            <div style="text-align: center; margin-bottom: 2rem;">
                <h1 style="color: white; font-size: 2.5em; margin-bottom: 0.5rem;">
                    <img src="https://api.iconify.design/lucide/history.svg?color=%23ffffff" width="32" height="32" style="display:inline-block; vertical-align: middle; margin-right: 0.5rem;" />
                    History Hub
                </h1>
                <p style="color: #ccc; font-size: 0.9em;">Hello, {st.session_state['username']}!</p>
            </div>
        """, unsafe_allow_html=True)

        selected_date = st.date_input("Select Date", datetime.today(), key="date_picker")

        st.markdown('<div style="margin-top: 1.5rem; margin-bottom: 1rem;">', unsafe_allow_html=True)
        if st.session_state.get('show_category_filter', False):
            if st.button("Categories  ▲", key="hide_categories_btn"):
                st.session_state['show_category_filter'] = False
        else:
            if st.button("Categories  ▼", key="show_categories_btn"):
                st.session_state['show_category_filter'] = True
        st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.get('show_category_filter', False):
            st.markdown('<div style="background-color: #474a50; padding: 1rem; border-radius: 8px;">', unsafe_allow_html=True)
            new_preferred_categories = []
            for category in st.session_state['all_categories']:
                if st.checkbox(category, value=category in st.session_state['preferred_categories'], key=f"cat_checkbox_{category}"):
                    new_preferred_categories.append(category)
            st.session_state['preferred_categories'] = new_preferred_categories
            st.markdown('</div>', unsafe_allow_html=True)


        st.markdown('<div style="margin-top: auto; padding-top: 2rem;">', unsafe_allow_html=True)
        if st.button("Logout", key="logout_btn"):
            st.session_state['logged_in'] = False
            st.session_state['username'] = None
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Main Content Area
    st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
            <h2 style="font-size: 2.5em; margin: 0; color: #3b2f5e;">
                Events for {selected_date.strftime('%B %d, %Y')}
            </h2>
            <div style="display: flex; gap: 1rem;">
                <button onclick="window.downloadPDF()" style="
                    background-color: #f49d37; color: #ffffff; font-weight: 600; font-size: 1em;
                    padding: 0.7em 1.5em; border: none; border-radius: 8px; box-shadow: 2px 2px 4px rgba(0,0,0,0.1);
                    transition: background-color 0.2s ease, transform 0.1s ease; display: inline-flex; align-items: center; gap: 0.5em;
                ">
                    <img src="https://api.iconify.design/lucide/calendar-days.svg?color=%23ffffff" width="20" height="20" />
                    Download PDF
                </button>
                <button onclick="window.sendEmail()" style="
                    background-color: #4CAF50; color: #ffffff; font-weight: 600; font-size: 1em;
                    padding: 0.7em 1.5em; border: none; border-radius: 8px; box-shadow: 2px 2px 4px rgba(0,0,0,0.1);
                    transition: background-color 0.2s ease, transform 0.1s ease; display: inline-flex; align-items: center; gap: 0.5em;
                ">
                    <img src="https://api.iconify.design/lucide/mail.svg?color=%23ffffff" width="20" height="20" />
                    Share via Email
                </button>
            </div>
        </div>
    """, unsafe_allow_html=True) # PDF/Email buttons are rendered as HTML to control styling more precisely

    # Fetch events
    events_placeholder = st.empty()
    with events_placeholder:
        with st.spinner("Fetching historical events..."):
            events = get_historical_events_from_gemini(selected_date)
            # Simulate a brief loading time for better UX
            time.sleep(1)

    filtered_events = [
        event for event in events
        if event.get('category') in st.session_state['preferred_categories']
    ]

    if not filtered_events:
        display_message('info', "No events found for this date or matching your selected categories.")
    else:
        for event in filtered_events:
            category_class = f"badge-{event.get('category', 'Other').lower()}"
            st.markdown(f"""
                <div class="event-card">
                    <div class="year-avatar">
                        {event.get('year', '?')[:4]}
                    </div>
                    <div class="event-content">
                        <p>{event.get('event', 'No event description.')}</p>
                        <div class="event-meta">
                            <span class="category-badge {category_class}">
                                {event.get('category', 'Other')}
                            </span>
                            <span style="margin-left: 0.5rem;">Year: {event.get('year', 'N/A')}</span>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

    # JavaScript for download/email actions, injected via Streamlit's experimental_singleton (or just a script)
    # This is a workaround as Streamlit buttons directly trigger Python callbacks, not easy JS calls.
    # For a real PDF download, it's simpler to prepare the PDF in Python and offer a download button.
    # For email, `mailto:` is the easiest if not using a backend.
    if filtered_events:
        pdf_file = create_pdf(filtered_events, selected_date)
        with open(pdf_file, "rb") as f:
            st.download_button(
                label="Click to Download PDF (Python)",
                data=f.read(),
                file_name=os.path.basename(pdf_file),
                mime="application/pdf",
                key="download_pdf_python_btn",
                help="Download the events as a PDF document."
            )
        os.remove(pdf_file) # Clean up the generated PDF file

        st.markdown(f"""
            <script>
                function sendEmailForEvents() {{
                    const subject = encodeURIComponent("This Day in History - {selected_date.strftime('%B %d, %Y')}");
                    let body = "Hello,\\n\\nHere are some historical events for {selected_date.strftime('%B %d')}:\\n\\n";
                    {''.join([f"body += '- {e.get('year', 'N/A')}: {e.get('event', '').replace('"', '\\"').replace("'", "\\'") } (Category: {e.get('category', 'Other')})\\n';" for e in filtered_events])}
                    body += "\\nEnjoy your day!";
                    const mailtoLink = `mailto:?subject=${{subject}}&body=${{encodeURIComponent(body)}}`;
                    window.open(mailtoLink, '_blank');
                }}
                window.sendEmail = sendEmailForEvents; // Expose to global scope for HTML button
            </script>
        """, unsafe_allow_html=True)
    else:
        # If no events, prevent download and email buttons from appearing
        st.markdown("<p style='visibility:hidden;'>No events to download/email</p>", unsafe_allow_html=True)


# --- Main App Execution ---
if __name__ == '__main__':
    init_db()
    if st.session_state['logged_in']:
        main_app()
    else:
        login_page()
