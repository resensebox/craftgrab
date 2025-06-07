import streamlit as st
import json
from fpdf import FPDF
from datetime import datetime, date
from openai import OpenAI
import os
import logging # Import the logging module

# --- Logging Setup ---
# Configure logging to write to a file. In a production environment,
# you might want to use a more robust logging solution (e.g., Loguru, or cloud-based logging).
logging.basicConfig(filename='app_activity.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

st.set_option('client.showErrorDetails', True)
st.set_page_config(page_title="This Day in History", layout="centered")

# --- Custom CSS ---
st.markdown("""
<style>
body { background-color: #e8f0fe; font-family: 'Inter', sans-serif; }
h1 { text-align: center; color: #333333; margin: 2rem auto 1.5rem; font-size: 2.5em; font-weight: 700; }
.stButton>button { background-color: #4CAF50; color: white; padding: 0.8em 2em; border: none; border-radius: 8px; font-weight: bold; box-shadow: 2px 2px 4px rgba(0,0,0,0.2); }
.stButton>button:hover { background-color: #45a049; transform: translateY(-2px); }
.stTextInput>div>div>input { border-radius: 8px; padding: 10px; border: 1px solid #ccc; box-shadow: inset 0 1px 2px rgba(0,0,0,0.05); }
.stTextInput>div>div>input:focus { border-color: #4CAF50; }
.stAlert { border-radius: 8px; background-color: #e6f7ff; border-color: #91d5ff; color: #004085; }
</style>
""", unsafe_allow_html=True)

# --- OpenAI Init ---
# Removed debug st.write statements for a cleaner UI
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
    # Ensure content is encoded/decoded properly for PDF to avoid errors with special characters
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
    # Added simple markdown parsing for bolding in PDF
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

# --- Login System Placeholder ---
def login_form():
    st.sidebar.header("Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Log In"):
        # In a real app, you would verify these credentials against a database
        if username == "user" and password == "password": # Example credentials
            st.session_state['logged_in'] = True
            st.session_state['username'] = username
            logging.info(f"User '{username}' logged in successfully.")
            st.rerun() # Rerun to hide login form and show app
        else:
            st.sidebar.error("Incorrect username or password.")
            logging.warning(f"Failed login attempt for username: {username}")
    st.sidebar.markdown("---")

# --- Main App ---
st.header("🗓️ This Day in History!")

# Implement the login check
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    login_form()
    st.info("Please log in to use the This Day in History app.")
else:
    st.sidebar.success(f"Logged in as {st.session_state['username']}")
    if st.sidebar.button("Log Out"):
        logging.info(f"User '{st.session_state['username']}' logged out.")
        st.session_state['logged_in'] = False
        st.session_state.pop('username', None)
        st.session_state.pop('parsed', None)
        st.session_state.pop('last_date', None)
        st.rerun()

    name = st.text_input("Enter Pair's Name:", "")
    today = st.date_input("Select a date", value=date.today(), max_value=date.today())

    day, month = today.day, today.month
    today_str = today.strftime('%B %d, %Y')
    profile = {"name": name, "jobs": "", "hobbies": "", "decade": "", "life_experiences": ""} # Consider adding more profile inputs in the UI

    if name:
        # Only fetch data if the date has changed or if it's the first time for this session
        if 'last_date' not in st.session_state or st.session_state['last_date'] != today or 'parsed' not in st.session_state:
            with st.spinner("Getting today's facts..."):
                raw = get_this_day_in_history(day, month, profile, client_ai)
                if raw.startswith("ERROR"):
                    st.error(raw)
                    logging.error(f"Failed to retrieve history for {today_str} due to an AI error.")
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

        st.markdown(f"### Today is: **{today_str}**") # Bold the date
        st.subheader("Significant Event:")
        st.markdown(f"**{parsed['event_title']}**")
        st.info(parsed['event_article'])
        if st.download_button("Download Article PDF", generate_article_pdf(parsed['event_title'], parsed['event_article']), file_name=f"{parsed['event_title'].replace(' ', '_')}_article.pdf"):
            logging.info(f"User '{st.session_state['username']}' downloaded article PDF: {parsed['event_title']}.")

        st.markdown("---")
        st.subheader("Famous Person Born Today:")
        name_guess = parsed['born_section'].split('\n')[0] if '\n' in parsed['born_section'] else parsed['born_section']
        st.image(f"https://placehold.co/150x150?text={name_guess}", width=150, caption=name_guess) # Added caption
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
