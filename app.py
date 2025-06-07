import streamlit as st
from openai import OpenAI
from datetime import datetime, date
from fpdf import FPDF
import re
import json
from gtts import gTTS
import io

st.set_option('client.showErrorDetails', True)
st.set_page_config(page_title="This Day in History", layout="centered")

# --- Google Sheets API Setup ---
import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
if "GOOGLE_SERVICE_JSON" not in st.secrets:
    st.error("❌ GOOGLE_SERVICE_JSON is missing from Streamlit secrets.")
    st.stop()

service_account_info = json.loads(st.secrets["GOOGLE_SERVICE_JSON"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
gs_client = gspread.authorize(creds)

def log_event(event_type, username):
    """Logs an event (e.g., login, registration) to the 'LoginLogs' worksheet."""
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
    """Saves new user credentials to the 'Users' worksheet."""
    try:
        sheet = gs_client.open_by_key("15LXglm49XBJBzeavaHvhgQn3SakqLGeRV80PxPHQfZ4")
        try:
            ws = sheet.worksheet("Users")
        except gspread.exceptions.WorksheetNotFound:
            ws = sheet.add_worksheet(title="Users", rows="100", cols="3")
            ws.append_row(["Username", "Password", "Email"]) # Add headers if new sheet
        ws.append_row([username, password, email])
        return True
    except Exception as e:
        st.warning(f"⚠️ Could not register user '{username}': {e}")
        return False

def get_users_from_sheet():
    """Retrieves all users from the 'Users' worksheet as a dictionary."""
    try:
        sheet = gs_client.open_by_key("15LXglm49XBJBzeavaHvhgQn3SakqLGeRV80PxPHQfZ4")
        ws = sheet.worksheet("Users")
        # Get all records as a list of dictionaries. head=1 makes the first row headers.
        users_data = ws.get_all_records(head=1)
        # Convert to a dictionary for easy lookup: {username: password}
        users_dict = {row['Username']: row['Password'] for row in users_data if 'Username' in row and 'Password' in row}
        return users_dict
    except gspread.exceptions.WorksheetNotFound:
        st.warning("⚠️ 'Users' worksheet not found. No registered users.")
        return {}
    except Exception as e:
        st.error(f"❌ Error retrieving users from Google Sheet: {e}")
        return {}

# --- OpenAI API Setup ---
if "OPENAI_API_KEY" not in st.secrets:
    st.error("❌ OPENAI_API_KEY is missing from Streamlit secrets.")
    st.stop()
client_ai = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- Session State Initialization ---
if 'is_authenticated' not in st.session_state:
    st.session_state['is_authenticated'] = False
if 'logged_in_username' not in st.session_state:
    st.session_state['logged_in_username'] = ""
if 'dementia_mode' not in st.session_state:
    st.session_state['dementia_mode'] = False
if 'audio_enabled' not in st.session_state:
    st.session_state['audio_enabled'] = False

# --- Text-to-Speech Function ---
def text_to_speech(text):
    """Converts text to speech audio bytes."""
    try:
        tts = gTTS(text=text, lang='en', slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp.getvalue()
    except Exception as e:
        st.error(f"Error generating audio: {e}")
        return None

# --- This Day in History Logic ---
def get_this_day_in_history_facts(current_day, current_month, user_info, _ai_client, preferred_decade=None, topic=None):
    """
    Generates 'This Day in History' facts using OpenAI API with specific content requirements.
    Incorporates customization options for decade and topic.
    """
    current_date_str = f"{current_month:02d}-{current_day:02d}"

    # Build prompt for event and born date ranges
    event_year_range = "between the years 1800 and 1960"
    born_year_range = "between 1800 and 1970"

    # Add topic customization to prompt if selected
    topic_clause = f" focusing on {topic}" if topic else ""

    prompt = f"""
    You are an assistant generating 'This Day in History' facts for {current_date_str}.
    Please provide:

    1. Event Article: Write a short article (around 200 words) about a famous historical event that happened on this day {event_year_range}{topic_clause}.
    2. Born on this Day Article: Write a brief article (around 150-200 words) about a well-known person born on this day {born_year_range}.
    3. Fun Fact: Provide one interesting and unusual fun fact that occurred on this day in history.
    4. Trivia Questions: Provide five trivia questions based on today’s date, spanning topics like history, famous birthdays, pop culture, or global events. For each question, provide the answer in parentheses.
    5. Did You Know?: Provide three "Did You Know?" facts related to nostalgic content (e.g., old prices, inventions, fashion facts) from past decades (e.g., 1930s-1970s).
    6. Memory Prompt: Provide one engaging question to encourage reminiscing and conversation (e.g., "Do you remember your first concert?", "What was your favorite childhood game?").

    Format your response clearly with these headings. Ensure articles are within the specified word counts.
    """
    try:
        response = _ai_client.chat.completions.create(
            model="gpt-3.5-turbo", # You might consider "gpt-4" for better quality if budget allows
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content.strip()

        # Regular expressions to parse the new sections
        event_article_match = re.search(r"1\. Event Article:\s*(.*?)(?=\n2\. Born on this Day Article:|\Z)", content, re.DOTALL)
        born_article_match = re.search(r"2\. Born on this Day Article:\s*(.*?)(?=\n3\. Fun Fact:|\Z)", content, re.DOTALL)
        fun_fact_match = re.search(r"3\. Fun Fact:\s*(.*?)(?=\n4\. Trivia Questions:|\Z)", content, re.DOTALL)
        trivia_match = re.search(r"4\. Trivia Questions:\s*(.*?)(?=\n5\. Did You Know?:|\Z)", content, re.DOTALL)
        did_you_know_match = re.search(r"5\. Did You Know:\?\s*(.*?)(?=\n6\. Memory Prompt:|\Z)", content, re.DOTALL)
        memory_prompt_match = re.search(r"6\. Memory Prompt:\s*(.*)", content, re.DOTALL)

        # Extract content, providing defaults if not found
        event_article = event_article_match.group(1).strip() if event_article_match else "No event article found."
        born_article = born_article_match.group(1).strip() if born_article_match else "No birth article found."
        fun_fact_section = fun_fact_match.group(1).strip() if fun_fact_match else "No fun fact found."
        trivia_lines = [q.strip() for q in trivia_match.group(1).strip().split('\n') if q.strip()] if trivia_match else []
        did_you_know_lines = [f.strip() for f in did_you_know_match.group(1).strip().split('\n') if f.strip()] if did_you_know_match else []
        memory_prompt_section = memory_prompt_match.group(1).strip() if memory_prompt_match else "No memory prompt found."

        return {
            'event_article': event_article,
            'born_article': born_article,
            'fun_fact_section': fun_fact_section,
            'trivia_section': trivia_lines,
            'did_you_know_section': did_you_know_lines,
            'memory_prompt_section': memory_prompt_section
        }
    except Exception as e:
        st.error(f"Error generating history: {e}")
        return {
            'event_article': "Could not fetch event history.",
            'born_article': "Could not fetch birth history.",
            'fun_fact_section': "Could not fetch fun fact.",
            'trivia_section': ["No trivia available."],
            'did_you_know_section': ["No 'Did You Know?' facts available."],
            'memory_prompt_section': "No memory prompt available."
        }

def generate_full_history_pdf(data, today_date_str, user_info, dementia_mode=False):
    """
    Generates a PDF of 'This Day in History' facts, with an optional dementia-friendly mode.
    """
    pdf = FPDF()
    pdf.add_page()

    if dementia_mode:
        pdf.set_font("Arial", "", 24) # Larger font, simple
        line_height = 15
        spacing = 10
    else:
        pdf.set_font("Arial", "B", 20)
        line_height = 10
        spacing = 5

    pdf.multi_cell(0, line_height, f"This Day in History: {today_date_str}", align='C')
    pdf.ln(spacing)

    # Event Article
    if not dementia_mode: pdf.set_font("Arial", "B", 14)
    pdf.multi_cell(0, line_height, "Significant Event:")
    if not dementia_mode: pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, line_height, data['event_article'])
    pdf.ln(spacing)

    # Born on this Day Article
    if not dementia_mode: pdf.set_font("Arial", "B", 14)
    pdf.multi_cell(0, line_height, "Born on this Day:")
    if not dementia_mode: pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, line_height, data['born_article'])
    pdf.ln(spacing)

    # Fun Fact
    if not dementia_mode: pdf.set_font("Arial", "B", 14)
    pdf.multi_cell(0, line_height, "Fun Fact:")
    if not dementia_mode: pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, line_height, data['fun_fact_section'])
    pdf.ln(spacing)

    # Trivia
    if not dementia_mode: pdf.set_font("Arial", "B", 14)
    pdf.multi_cell(0, line_height, "Trivia:")
    if not dementia_mode: pdf.set_font("Arial", "", 12)
    for item in data['trivia_section']:
        pdf.multi_cell(0, line_height, item)
    pdf.ln(spacing)

    # Did You Know?
    if data['did_you_know_section']:
        if not dementia_mode: pdf.set_font("Arial", "B", 14)
        pdf.multi_cell(0, line_height, "Did You Know?")
        if not dementia_mode: pdf.set_font("Arial", "", 12)
        for item in data['did_you_know_section']:
            pdf.multi_cell(0, line_height, item)
        pdf.ln(spacing)

    # Memory Prompt
    if data['memory_prompt_section']:
        if not dementia_mode: pdf.set_font("Arial", "B", 14)
        pdf.multi_cell(0, line_height, "Memory Prompt:")
        if not dementia_mode: pdf.set_font("Arial", "", 12)
        pdf.multi_cell(0, line_height, data['memory_prompt_section'])
        pdf.ln(spacing)

    if not dementia_mode:
        pdf.set_font("Arial", "I", 10)
        pdf.multi_cell(0, 5, f"Generated for {user_info['name']}", align='C')
        
    return pdf.output(dest='S').encode('latin-1')

# --- App UI ---
if st.session_state['is_authenticated']:
    st.sidebar.title("This Day in History")
    
    st.sidebar.markdown("---")
    st.sidebar.header("Settings")
    # Dementia-friendly mode toggle
    st.session_state['dementia_mode'] = st.sidebar.checkbox("Dementia-Friendly Mode", value=st.session_state['dementia_mode'])
    # Text-to-speech toggle
    st.session_state['audio_enabled'] = st.sidebar.checkbox("Enable Audio (Text-to-Speech)", value=st.session_state['audio_enabled'])

    # Customization Options
    st.sidebar.subheader("Content Customization")
    preferred_topic = st.sidebar.selectbox(
        "Preferred Topic for Events (Optional)",
        options=["None", "Sports", "Music", "Inventions", "Politics", "Science", "Arts"],
        index=0
    )
    # The prompt doesn't currently use preferred_decade or difficulty for trivia
    # You would need to further refine the prompt and potentially add more complex logic
    # preferred_decade = st.sidebar.selectbox("Preferred Decade for Events (Optional)", options=["None", "1800s", "1900s", "1910s", "1920s", "1930s", "1940s", "1950s", "1960s"], index=0)
    # trivia_difficulty = st.sidebar.select_slider("Trivia Difficulty", options=["Easy", "Medium", "Hard"])

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Log Out"):
        log_event("logout", st.session_state['logged_in_username']) # Log logout event
        st.session_state['is_authenticated'] = False
        st.session_state['logged_in_username'] = ""
        st.rerun()
    
    st.title("📅 This Day in History")

    # Apply dementia-friendly styling if enabled
    if st.session_state['dementia_mode']:
        st.markdown(
            """
            <style>
            body { font-family: 'Arial', sans-serif; font-size: 24px; line-height: 1.5; }
            h1, h2, h3, h4, h5, h6 { font-family: 'Arial', sans-serif; font-weight: bold; margin-top: 1em; margin-bottom: 0.5em; }
            p { margin-bottom: 1em; }
            </style>
            """,
            unsafe_allow_html=True
        )
        st.markdown("<p style='font-size:24px; font-weight:bold;'>Today's Daily Page</p>", unsafe_allow_html=True)


    today = datetime.today()
    day, month = today.day, today.month
    user_info = {
        'name': st.session_state['logged_in_username'],
        'jobs': '', 'hobbies': '', 'decade': '', 'life_experiences': '', 'college_chapter': ''
    }

    # Pass customization options to the data fetching function
    data = get_this_day_in_history_facts(day, month, user_info, client_ai, topic=preferred_topic if preferred_topic != "None" else None)

    # Display content
    st.subheader(f"✨ A Look Back at {today.strftime('%B %d')}")
    if st.session_state['audio_enabled']:
        audio_bytes = text_to_speech(f"A look back at {today.strftime('%B %d')}")
        if audio_bytes:
            st.audio(audio_bytes, format='audio/mp3')

    st.markdown("---")
    st.subheader("🗓️ Significant Event")
    st.write(data['event_article'])
    if st.session_state['audio_enabled']:
        audio_bytes = text_to_speech(data['event_article'])
        if audio_bytes:
            st.audio(audio_bytes, format='audio/mp3')

    st.markdown("---")
    st.subheader("🎂 Born on this Day")
    st.write(data['born_article'])
    if st.session_state['audio_enabled']:
        audio_bytes = text_to_speech(data['born_article'])
        if audio_bytes:
            st.audio(audio_bytes, format='audio/mp3')

    st.markdown("---")
    st.subheader("💡 Fun Fact")
    st.write(data['fun_fact_section'])
    if st.session_state['audio_enabled']:
        audio_bytes = text_to_speech(data['fun_fact_section'])
        if audio_bytes:
            st.audio(audio_bytes, format='audio/mp3')

    st.markdown("---")
    st.subheader("🧠 Test Your Knowledge!")
    for i, q in enumerate(data['trivia_section']):
        st.write(f"{q}")
        if st.session_state['audio_enabled']:
            audio_bytes = text_to_speech(q)
            if audio_bytes:
                st.audio(audio_bytes, format='audio/mp3', key=f"trivia_audio_{i}")

    st.markdown("---")
    st.subheader("🌟 Did You Know?")
    for i, fact in enumerate(data['did_you_know_section']):
        st.write(f"- {fact}")
        if st.session_state['audio_enabled']:
            audio_bytes = text_to_speech(fact)
            if audio_bytes:
                st.audio(audio_bytes, format='audio/mp3', key=f"dyk_audio_{i}")

    st.markdown("---")
    st.subheader("💬 Memory Lane Prompt")
    st.write(data['memory_prompt_section'])
    if st.session_state['audio_enabled']:
        audio_bytes = text_to_speech(data['memory_prompt_section'])
        if audio_bytes:
            st.audio(audio_bytes, format='audio/mp3')

    st.markdown("---")
    if st.button("📄 Download Daily Page PDF"):
        pdf_bytes = generate_full_history_pdf(
            data, today.strftime('%B %d, %Y'), user_info, st.session_state['dementia_mode']
        )
        st.download_button(
            "Download PDF", 
            pdf_bytes, 
            file_name=f"This_Day_in_History_{today.strftime('%Y%m%d')}.pdf",
            mime="application/pdf"
        )
    
    # --- Offline Access (Conceptual - requires local storage solution) ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("Offline Access")
    st.sidebar.info("Offline access for the past 7 days is a planned feature. For now, you can download PDFs to save content.")
    # Implement actual offline storage (e.g., SQLite, Streamlit's file_uploader for saving/loading)
    # or browser-based storage (which is more complex with Streamlit server-side rendering).
    # This often involves saving the generated `data` dictionary for each day.

    # --- Sharing/Email Option (Conceptual - requires external email service) ---
    st.sidebar.subheader("Share Daily Page")
    st.sidebar.info("Daily/weekly sharing via email is a planned feature. This would integrate with an email service.")
    # Implement email sending functionality using smtplib or a dedicated email API (e.g., SendGrid, Mailgun).
    # This would likely involve storing user email preferences in Google Sheets.


else: # Login/Registration UI
    st.title("Login to Access")
    login_tab, register_tab = st.tabs(["Log In", "Register"])
    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Log In"):
                USERS = get_users_from_sheet() # Get users from Google Sheet
                if username in USERS and USERS[username] == password:
                    st.session_state['is_authenticated'] = True
                    st.session_state['logged_in_username'] = username
                    st.success(f"Welcome {username}!")
                    log_event("login", username)
                    st.rerun()
                else:
                    st.error("Invalid credentials.")

    with register_tab:
        with st.form("register_form"):
            new_username = st.text_input("New Username")
            new_email = st.text_input("Email")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            if st.form_submit_button("Register"):
                if new_password == confirm_password:
                    USERS_EXISTING = get_users_from_sheet()
                    if new_username in USERS_EXISTING:
                        st.error("Username already exists. Please choose a different username.")
                    else:
                        if save_new_user_to_sheet(new_username, new_password, new_email):
                            st.session_state['is_authenticated'] = True
                            st.session_state['logged_in_username'] = new_username
                            st.success("Account created!")
                            log_event("register", new_username)
                            st.rerun()
                        else:
                            st.error("Failed to register user. Please try again.")
                else:
                    st.error("Passwords do not match.")

# --- Demo Preview on Login Page ---
st.markdown("---")
st.subheader("📋 Example: This Day in History")
st.info("This is a preview of the content format. Log in or register to get today's personalized content!")

demo_user_info = {'name': 'Demo User', 'jobs': '', 'hobbies': '', 'decade': '', 'life_experiences': '', 'college_chapter': ''}
today_demo = datetime.today()
demo_data = get_this_day_in_history_facts(today_demo.day, today_demo.month, demo_user_info, client_ai)

st.markdown(f"### ✨ A Look Back at {today_demo.strftime('%B %d')}")
st.markdown("### 🗓️ Significant Event")
st.write(demo_data['event_article'])

st.markdown("### 🎂 Born on this Day")
st.write(demo_data['born_article'])

st.markdown("### 💡 Fun Fact")
st.write(demo_data['fun_fact_section'])

st.markdown("### 🧠 Test Your Knowledge!")
for q in demo_data['trivia_section']:
    st.markdown(f"- {q}")

st.markdown("### 🌟 Did You Know?")
for fact in demo_data['did_you_know_section']:
    st.markdown(f"- {fact}")

st.markdown("### 💬 Memory Lane Prompt")
st.write(demo_data['memory_prompt_section'])

if st.button("📄 Download Demo PDF"):
    demo_pdf = generate_full_history_pdf(
        demo_data, today_demo.strftime('%B %d, %Y'), demo_user_info
    )
    st.download_button(
        "Download Example PDF", 
        demo_pdf, 
        file_name=f"example_this_day_history_{today_demo.strftime('%Y%m%d')}.pdf",
        mime="application/pdf"
    )
