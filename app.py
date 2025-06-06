import streamlit as st
import json
from fpdf import FPDF
from datetime import datetime, date
import base64 # Import base64 for PDF download
from openai import OpenAI
from collections import Counter # Needed for Counter in load_pairs in original, but not strictly here. Kept for minimal dependencies.

st.set_option('client.showErrorDetails', True)

st.set_page_config(page_title="This Day in History", layout="centered")

# --- Custom CSS for enhanced UI (simplified for standalone app) ---
st.markdown("""
    <style>
    body {
        background-color: #e8f0fe; /* Light blue background */
        font-family: 'Inter', sans-serif;
    }
    h1 {
        text-align: center;
        color: #333333;
        margin-top: 2rem;
        margin-bottom: 1.5rem;
        font-size: 2.5em;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    .stButton>button {
        background-color: #4CAF50; /* Green button */
        color: white;
        padding: 0.8em 2em;
        border: none;
        border-radius: 8px;
        font-weight: bold;
        transition: background-color 0.3s ease, transform 0.2s ease;
        box-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    .stButton>button:hover {
        background-color: #45a049;
        transform: translateY(-2px);
    }
    .stTextInput>div>div>input {
        border-radius: 8px;
        padding: 10px;
        border: 1px solid #ccc;
        box-shadow: inset 0 1px 2px rgba(0,0,0,0.05);
        transition: border-color 0.2s ease;
    }
    .stTextInput>div>div>input:focus {
        border-color: #4CAF50;
        outline: none;
    }
    .stSpinner>div>div>span {
        color: #4CAF50 !important;
    }
    .stAlert {
        border-radius: 8px;
        background-color: #e6f7ff;
        border-color: #91d5ff;
        color: #004085;
    }
    </style>
""", unsafe_allow_html=True)


# --- OpenAI Initialization ---
try:
    if "OPENAI_API_KEY" not in st.secrets:
        st.error("❌ OPENAI_API_KEY is missing from secrets. Please add it to your Streamlit secrets.")
        st.stop()
    client_ai = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception as e:
    st.error(f"Failed to initialize OpenAI client. Please check your `st.secrets` configuration. Error: {e}")
    st.stop()

# --- Session State Variables (minimal for this app) ---
if 'this_day_history_data' not in st.session_state:
    st.session_state['this_day_history_data'] = {
        'event_title': "",
        'event_article': "",
        'born_section': "",
        'fun_fact_section': "",
        'trivia_section': []
    }
if 'last_history_date' not in st.session_state:
    st.session_state['last_history_date'] = None
if 'current_user_name' not in st.session_state: # To personalize PDF output
    st.session_state['current_user_name'] = ""

# --- Helper Functions ---

@st.cache_data(ttl=86400) # Cache for 24 hours (entire day)
def get_this_day_in_history_facts(current_day, current_month, user_info_for_ai, _ai_client):
    """Generates famous event, person born, fun fact, and trivia for the current day."""
    current_date_str = f"{current_month:02d}-{current_day:02d}"

    # Prepare user info for personalization
    user_profile_summary = ""
    if user_info_for_ai.get('name'): user_profile_summary += f"Pair's Name: {user_info_for_ai['name']}. "
    if user_info_for_ai.get('jobs'): user_profile_summary += f"Past Jobs: {user_info_for_ai['jobs']}. "
    if user_info_for_ai.get('hobbies'): user_profile_summary += f"Hobbies: {user_info_for_ai['hobbies']}. "
    if user_info_for_ai.get('decade'): user_profile_summary += f"Favorite Decade: {user_info_for_ai['decade']}. "
    if user_info_for_ai.get('life_experiences'): user_profile_summary += f"Life Experiences: {user_info_for_ai['life_experiences']}. "
    if user_info_for_ai.get('college_chapter'): user_profile_summary += f"College Chapter: {user_info_for_ai['college_chapter']}. "

    prompt = f"""
    You are an expert historical archivist and a compassionate assistant for student volunteers working with individuals living with dementia.
    For today's date, {current_date_str}, provide the following information:

    1.  **A famous event** that happened on this day in the past (between 1900 and 1965). Write a 200-word article about it. Ensure the event is broadly positive or culturally significant, suitable for sparking pleasant memories.
    2.  **A famous person born on this day** (between 1850 and 1960). Try to pick someone that the user's pair (a person living with dementia) might be interested in, based on their profile. Include a brief description of who they are/what they are famous for.
        User's Pair Profile: {user_profile_summary if user_profile_summary else 'No specific profile details provided. Try to pick a broadly recognizable figure.'}
    3.  **A fun fact** related to this day in history.
    4.  **Three easy trivia questions** about general knowledge or common historical facts that would be simple for individuals with dementia. For each question, provide a clear, simple answer. These questions should not require direct memory recall of specific dates or complex details, but rather general recognition or common sense.

    Format your response strictly as follows:
    Event: [Event Title] - [Year]
    [200-word article content]

    Born on this Day: [Person's Name]
    [Person's Description]

    Fun Fact: [Your fun fact]

    Trivia Questions:
    1. [Question 1]? (Answer: [Answer 1])
    2. [Question 2]? (Answer: [Answer 2])
    3. [Question 3]? (Answer: [Answer 3])
    """
    try:
        response = _ai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Could not retrieve 'This Day in History' facts. Error: {e}"

def generate_article_pdf(title, content):
    """Generates a PDF of a single article title and content."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.multi_cell(0, 10, title, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", "", 12)
    # Ensure content is encoded properly for FPDF
    pdf.multi_cell(0, 8, content.encode('latin-1', 'replace').decode('latin-1'))
    
    return pdf.output(dest='S').encode('latin-1')

def generate_full_history_pdf(event_title, event_article, born_section, fun_fact_section, trivia_section, today_date_str, user_name_for_pdf):
    """Generates a PDF of the entire 'This Day in History' page content."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 20)
    pdf.multi_cell(0, 10, f"This Day in History: {today_date_str}", align='C')
    pdf.ln(10)

    pdf.set_font("Arial", "B", 14)
    pdf.multi_cell(0, 10, "Significant Event:")
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 8, f"**{event_title}**\n{event_article}".encode('latin-1', 'replace').decode('latin-1'))
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
    for trivia_item in trivia_section:
        pdf.multi_cell(0, 8, trivia_item.encode('latin-1', 'replace').decode('latin-1'))
    pdf.ln(5)

    pdf.set_font("Arial", "I", 10)
    # Use user_name_for_pdf here
    pdf.multi_cell(0, 5, f"Generated for {user_name_for_pdf} by Mindful Libraries on {today_date_str}".encode('latin-1', 'replace').decode('latin-1'), align='C')

    return pdf.output(dest='S').encode('latin-1')


# --- Main App Logic ---
st.header("🗓️ This Day in History!")

# Simplified Pair Name input for this standalone app
st.session_state['current_user_name'] = st.text_input(
    "Enter the Pair's Name (for PDF personalization):",
    value=st.session_state['current_user_name'],
    key="standalone_pair_name_input"
)

# Dummy user_info for AI personalization, as full profile is not present here
user_info_for_ai = {
    'name': st.session_state['current_user_name'],
    'jobs': '', # Not available in standalone
    'life_experiences': '', # Not available in standalone
    'hobbies': '', # Not available in standalone
    'decade': '', # Not available in standalone
    'college_chapter': '' # Not available in standalone
}


today = date.today()
current_day = today.day
current_month = today.month
today_date_str = today.strftime('%B %d, %Y')

st.markdown(f"### Today is: {today_date_str}")

if st.session_state['current_user_name']:
    # Check if history data is already loaded and from today
    if st.session_state['last_history_date'] != today:
        with st.spinner("Fetching historical insights for today..."):
            history_facts_raw = get_this_day_in_history_facts(current_day, current_month, user_info_for_ai, client_ai)

            # Parse the raw text response from the AI
            event_title = ""
            event_article = ""
            born_section = ""
            fun_fact_section = ""
            trivia_section = []

            sections = history_facts_raw.split('\n\n') # Split by double newline for sections

            for i, section in enumerate(sections):
                if section.startswith("Event:"):
                    first_line = section.split('\n')[0].replace("Event:", "").strip()
                    if ' - ' in first_line:
                        event_title = first_line.split(' - ', 1)[0].strip()
                    else:
                        event_title = first_line.strip()
                    event_article = '\n'.join(section.split('\n')[1:]).strip()
                elif section.startswith("Born on this Day:"):
                    born_section = section.replace("Born on this Day:", "").strip()
                elif section.startswith("Fun Fact:"):
                    fun_fact_section = section.replace("Fun Fact:", "").strip()
                elif section.startswith("Trivia Questions:"):
                    trivia_lines = section.replace("Trivia Questions:", "").strip().split('\n')
                    trivia_section = [line.strip() for line in trivia_lines if line.strip()]
            
            # Store parsed data in session state
            st.session_state['this_day_history_data'] = {
                'event_title': event_title,
                'event_article': event_article,
                'born_section': born_section,
                'fun_fact_section': fun_fact_section,
                'trivia_section': trivia_section
            }
            st.session_state['last_history_date'] = today # Mark when this data was fetched/stored
    else:
        st.info("Showing cached insights for today.")
            
    # Retrieve from session state for display and PDF generation
    event_title = st.session_state['this_day_history_data']['event_title']
    event_article = st.session_state['this_day_history_data']['event_article']
    born_section = st.session_state['this_day_history_data']['born_section']
    fun_fact_section = st.session_state['this_day_history_data']['fun_fact_section']
    trivia_section = st.session_state['this_day_history_data']['trivia_section']

    st.markdown("---")
    st.subheader("Significant Event:")
    if event_title and event_article:
        st.markdown(f"**{event_title}**")
        st.info(event_article)
        
        pdf_bytes_article = generate_article_pdf(event_title, event_article)
        st.download_button(
            label="Download Article as PDF",
            data=pdf_bytes_article,
            file_name=f"{event_title.replace(' ', '_')}_Article.pdf",
            mime="application/pdf",
            key="download_event_article_pdf"
        )

    else:
        st.info("No famous event found for this day in the specified era.")

    st.markdown("---")
    st.subheader("Famous Person Born Today:")
    if born_section:
        person_name_match = born_section.split('\n')[0] if '\n' in born_section else born_section
        st.markdown(f"**{person_name_match}**")
        person_name_for_url = person_name_match.split('-')[0].strip().replace(' ', '+')
        img_url_placeholder = f"https://placehold.co/150x150/8d8d8d/ffffff?text={person_name_for_url}"
        st.image(img_url_placeholder, width=150, caption=person_name_match)
        st.markdown(born_section)
    else:
        st.info("No famous person found for this day in the specified era.")

    st.markdown("---")
    st.subheader("Fun Fact:")
    if fun_fact_section:
        st.info(fun_fact_section)
    else:
        st.info("No fun fact available for this day.")

    st.markdown("---")
    st.subheader("Trivia Time! (with answers for the volunteer):")
    if trivia_section:
        for i, trivia_item in enumerate(trivia_section):
            st.markdown(f"{trivia_item}")
    else:
        st.info("No trivia questions generated for this day.")

    st.markdown("---")
    st.subheader("Full Page Summary:")
    if st.session_state['this_day_history_data']['event_title']: # Only show if content has been generated
        full_page_pdf_bytes = generate_full_history_pdf(
            st.session_state['this_day_history_data']['event_title'],
            st.session_state['this_day_history_data']['event_article'],
            st.session_state['this_day_history_data']['born_section'],
            st.session_state['this_day_history_data']['fun_fact_section'],
            st.session_state['this_day_history_data']['trivia_section'],
            today_date_str,
            st.session_state['current_user_name'] # Pass the current user name for PDF
        )
        st.download_button(
            label="Download This Day in History Page as PDF",
            data=full_page_pdf_bytes,
            file_name=f"This_Day_in_History_{today.strftime('%Y_%m_%d')}.pdf",
            mime="application/pdf",
            key="download_full_history_page_pdf"
        )
    else:
        st.info("Generate the daily history content first to download the full page PDF.")
else:
    st.info("Please enter a Pair's Name to get today's historical insights.")

