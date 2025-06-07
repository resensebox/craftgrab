import streamlit as st
from openai import OpenAI
from datetime import datetime, date, timedelta
from fpdf import FPDF
import re
import json
import base64 # Import base64 for encoding PDF content
import time # Import time for st.spinner delays
import zipfile # NEW: Import zipfile for creating zip archives
import io # NEW: Import io for in-memory file operations

st.set_option('client.showErrorDetails', True)
st.set_page_config(page_title="This Day in History", layout="centered")

# Initial dummy data structure for raw_fetched_data if no fetch has occurred or failed
_INITIAL_EMPTY_DATA = {
    'event_article': "No historical event data available. Please try again.",
    'born_article': "No birth data available. Please try again.",
    'fun_fact_section': "No fun fact available. Please try again.",
    'trivia_section': [],
    'did_you_know_section': ["No 'Did You Know?' facts available. Please try again."],
    'memory_prompt_section': ["No memory prompts available.", "Consider your favorite childhood memory.", "What's a happy moment from your past week?"],
    'local_history_section': "No local history data available. Please try again."
}

# --- Session State Initialization ---
if 'is_authenticated' not in st.session_state:
    st.session_state['is_authenticated'] = False
if 'logged_in_username' not in st.session_state:
    st.session_state['logged_in_username'] = ""
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'main_app' # Default page for authenticated users
if 'daily_data' not in st.session_state: # Store daily data to avoid re-fetching on page switch
    st.session_state['daily_data'] = None
if 'raw_fetched_data' not in st.session_state: # NEW: To store the raw, untranslated data
    st.session_state['raw_fetched_data'] = _INITIAL_EMPTY_DATA.copy() # Initialize with a default structure
if 'last_fetched_date' not in st.session_state:
    st.session_state['last_fetched_date'] = None # To track when data was last fetched
if 'trivia_question_states' not in st.session_state:
    st.session_state['trivia_question_states'] = {} # Stores per-question state: {'q_index': {'user_answer': '', 'is_correct': False, 'feedback': '', 'hint_revealed': False, 'attempts': 0, 'out_of_chances': False, 'points_earned': 0, 'related_article_content': None}}
if 'hints_remaining' not in st.session_state:
    st.session_state['hints_remaining'] = 3 # Total hints allowed per day
if 'current_trivia_score' not in st.session_state:
    st.session_state['current_trivia_score'] = 0
if 'total_possible_daily_trivia_score' not in st.session_state:
    st.session_state['total_possible_daily_trivia_score'] = 0
if 'score_logged_today' not in st.session_state:
    st.session_state['score_logged_today'] = False
if 'difficulty' not in st.session_state: # New session state for difficulty
    st.session_state['difficulty'] = 'Medium' # Default difficulty
if 'local_city' not in st.session_state:
    st.session_state['local_city'] = ""
if 'local_state_country' not in st.session_state:
    st.session_state['local_state_country'] = ""
if 'preferred_language' not in st.session_state:
    st.session_state['preferred_language'] = 'English' # Default language
if 'custom_masthead_text' not in st.session_state: # NEW: Custom masthead text for PDF
    st.session_state['custom_masthead_text'] = ""
if 'last_download_status' not in st.session_state: # NEW: To track PDF download logging status for user feedback
    st.session_state['last_download_status'] = None
if 'weekly_planner_date' not in st.session_state: # NEW: To store the selected date for weekly planner
    st.session_state['weekly_planner_date'] = date.today()


# --- Custom CSS for Sidebar Styling and Default App Theme (Black) ---
st.markdown(
    """
    <style>
    /* Overall Sidebar Styling to match logo colors */
    div[data-testid="stSidebar"] {
        background-color: #5A2D81; /* Deep purple from logo */
        color: white; /* Default text color */
    }

    /* Ensuring all text elements within sidebar are white */
    div[data-testid="stSidebar"] * {
        color: white !important;
    }

    /* Headers in sidebar */
    div[data-testid="stSidebar"] h1,
    div[data-testid="stSidebar"] h2,
    div[data-testid="stSidebar"] h3,
    div[data-testid="stSidebar"] h4,
    div[data-testid="stSidebar"] h5,
    div[data-testid="stSidebar"] h6 {
        color: white !important;
    }

    /* Info boxes in sidebar */
    div[data-testid="stSidebar"] .stAlert {
        background-color: #7B4CA0; /* Slightly lighter purple for info boxes */
        border-color: #7B4CA0;
    }

    /* Buttons in sidebar */
    div[data-testid="stSidebar"] .stButton > button {
        background-color: #8A2BE2; /* Blue Violet for buttons */
        color: white;
        border: none;
        border-radius: 0.5rem;
        padding: 0.5rem 1rem;
        transition: all 0.2s ease-in-out;
    }

    div[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #A020F0; /* Purple on hover */
        color: white;
    }

    /* Selectbox dropdown background and text */
    .st-emotion-cache-10q763j { /* This is a common class for dropdowns/popovers */
        background-color: #7B4CA0 !important; /* Lighter purple for dropdowns */
        color: white !important;
    }
    .st-emotion-cache-10q763j * { /* Ensure all text in dropdowns is white */
        color: white !important;
    }
    /* Specific styling for selectbox options on hover/selected */
    .st-emotion-cache-lck165:hover { /* Selectbox option on hover */
        background-color: #A020F0 !important;
    }
    .st-emotion-cache-1n1j053 { /* Selectbox selected option */
        background-color: #A020F0 !important;
    }

    /* Popover button (the 'ⓘ' icon) */
    div[data-testid="stSidebar"] .stPopover > button {
        color: white !important;
        background-color: transparent !important;
        border: none !important;
    }
    div[data-testid="stSidebar"] .stPopover > button:hover {
        background-color: #7B4CA0 !important; /* Lighter purple on hover for icon */
    }

    /* Input fields (e.g., text_input for selectbox search) within sidebar */
    div[data-testid="stSidebar"] input[type="text"] {
        background-color: #7B4CA0; /* Match selectbox background */
        color: white;
        border-color: #7B4CA0;
    }
    div[data-testid="stSidebar"] input[type="text"]:focus {
        border-color: #A020F0;
    }

    /* Default general app styling for main content area (black background) */
    .stApp {
        background-color: #000000; /* Black background */
        color: #E0E0E0; /* Light text for contrast */
    }
    .stMarkdown, .stText { color: #E0E0E0; }
    h1, h2, h3, h4, h5, h6 { color: #E0E0E0; }
    .stAlert {
        background-color: #333333; /* Darker background for alerts */
        color: #E0E0E0;
        border-color: #444444;
    }
    .stTextInput > div > div > input {
        background-color: #333333;
        color: #E0E0E0;
        border-color: #444444;
    }
    .stSelectbox > div > div > div { /* Target for selectbox background */
        background-color: #333333;
        color: #E0E0E0;
    }
    .stSelectbox > div > div > div > div > span { /* Target for selectbox text */
        color: #E0E0E0 !important;
    }
    /* Ensure no lingering background issues from blocks */
    div[data-testid="stVerticalBlock"] {
        background-color: transparent !important;
    }
    div[data-testid="stHorizontalBlock"] {
        background-color: transparent !important;
    }
    /* Adjust button colors for general main content buttons */
    .stButton > button {
        background-color: #555555; /* Darker button for main content */
        color: #E0E0E0;
        border: none;
        border-radius: 0.5rem;
    }
    .stButton > button:hover {
        background-color: #777777;
    }
    /* Date input styling */
    .stDateInput > div > div > input {
        background-color: #333333;
        color: #E0E0E0;
        border-color: #444444;
    }

    /* Specific styling for the "Check Answer" button */
    div[data-testid^="stButton-primary-check_btn_"] > button {
        background-color: #FFFFFF !important; /* White background */
        color: #000000 !important; /* Black text */
        border: 1px solid #000000 !important; /* Add a thin black border for contrast */
    }

    div[data-testid^="stButton-primary-check_btn_"] > button:hover {
        background-color: #F0F0F0 !important; /* Slightly off-white on hover */
        color: #000000 !important;
        border: 1px solid #000000 !important;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# --- Google Sheets API Setup ---
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Corrected scope for Google Sheets API v4
scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
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
        try:
            ws = sheet.worksheet("LoginLogs")
        except gspread.exceptions.WorksheetNotFound:
            ws = sheet.add_worksheet(title="LoginLogs", rows="100", cols="3")
            ws.append_row(["Timestamp", "EventType", "Username"])  # Add headers if new sheet
        
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
    print("Attempting to get users from sheet...") # Debugging print
    try:
        sheet = gs_client.open_by_key("15LXglm49XBJBzeavaHvhgQn3SakqLGeRV80PxPHQfZ4")
        try:
            ws = sheet.worksheet("Users")
            print("Found 'Users' worksheet.") # Debugging print
        except gspread.exceptions.WorksheetNotFound:
            print("❌ 'Users' worksheet not found. Creating it now.") # Debugging print
            st.warning("⚠️ The 'Users' database was not found. Creating it now. Please retry your registration if this is your first time.")
            ws = sheet.add_worksheet(title="Users", rows="100", cols="3")
            ws.append_row(["Username", "Password", "Email"])  # Add headers if new sheet
            return {} # Return empty dict as no users existed before this operation
        
        users_data = ws.get_all_records(head=1)
        users_dict = {row['Username']: row['Password'] for row in users_data if 'Username' in row and 'Password' in row}
        print(f"Retrieved users: {list(users_dict.keys())}") # Debugging print
        return users_dict
    except Exception as e:
        print(f"ERROR: Error retrieving users from Google Sheet: {e}") # Debugging print
        st.error(f"❌ Error retrieving users from Google Sheet: {e}")
        return {}

def log_trivia_score(username, score):
    """Logs a user's trivia score to the 'History' worksheet."""
    try:
        sheet = gs_client.open_by_key("15LXglm49XBJBzeavaHvhgQn3SakqLGeRV80PxPHQfZ4")
        try:
            ws = sheet.worksheet("History")
        except gspread.exceptions.WorksheetNotFound:
            ws = sheet.add_worksheet(title="History", rows="100", cols="3")
            ws.append_row(["Username", "Score", "Timestamp"]) # Add headers if new sheet
        
        ws.append_row([
            username,
            score,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ])
        return True
    except Exception as e:
        st.warning(f"⚠️ Could not log trivia score for '{username}': {e}")
        return False

def get_leaderboard_data():
    """Retrieves and processes scores for the leaderboard."""
    try:
        sheet = gs_client.open_by_key("15LXglm49XBJBzeavaHvhgQn3SakqLGeRV80PxPHQfZ4")
        try:
            ws = sheet.worksheet("History")
        except gspread.exceptions.WorksheetNotFound:
            return {} # No history sheet, no leaderboard
        
        scores_data = ws.get_all_records(head=1)
        
        user_highest_scores = {}
        for entry in scores_data:
            username = entry.get('Username')
            score = entry.get('Score')
            
            # Ensure score is a number and update highest score for this user
            if username and score is not None:
                try:
                    score = int(score) # Convert score to integer
                    if username not in user_highest_scores or score > user_highest_scores[username]:
                        user_highest_scores[username] = score
                except ValueError:
                    # Handle cases where score might not be a valid integer
                    continue 
        
        # Sort users by highest score in descending order
        return sorted(user_highest_scores.items(), key=lambda item: item[1], reverse=True)[:3]
    except Exception as e:
        st.error(f"❌ Error retrieving leaderboard data: {e}")
        return {}

def log_feedback(username, feedback_message):
    """Logs user feedback to the 'Feedback' worksheet."""
    try:
        sheet = gs_client.open_by_key("15LXglm49XBJBzeavaHvhgQn3SakqLGeRV80PxPHQfZ4")
        try:
            ws = sheet.worksheet("Feedback")
        except gspread.exceptions.WorksheetNotFound:
            ws = sheet.add_worksheet(title="Feedback", rows="100", cols="3")
            ws.append_row(["Timestamp", "Username/Contact", "Feedback"]) # Add headers if new sheet
        
        ws.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            username,
            feedback_message
        ])
        return True
    except Exception as e:
        st.warning(f"⚠️ Could not log feedback: {e}")
        return False

def log_pdf_download(username, filename, download_date):
    """Logs a PDF download event to the 'PDFLogs' worksheet."""
    try:
        sheet = gs_client.open_by_key("15LXglm49XBJBzeavaHvhgQn3SakqLGeRV80PxPHQfZ4")
        try:
            ws = sheet.worksheet("PDFLogs")
        except gspread.exceptions.WorksheetNotFound:
            ws = sheet.add_worksheet(title="PDFLogs", rows="100", cols="4")
            ws.append_row(["Timestamp", "Username", "Filename", "DownloadDate"]) # Add headers if new sheet
        
        ws.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            username,
            filename,
            download_date.strftime("%Y-%m-%d") if isinstance(download_date, date) else str(download_date)
        ])
        # Removed st.success here to manage feedback more centrally with session state
        return True
    except Exception as e:
        # Removed st.warning here to manage feedback more centrally with session state
        print(f"ERROR: Could not log PDF download for '{username}': {e}") # Log to console for debugging
        return False


def check_partial_correctness_with_ai(user_answer, correct_answer, _ai_client):
    """
    Uses AI to determine if a user's answer is partially correct compared to the actual answer.
    Returns "Yes" or "No".
    """
    prompt = f"""
    Compare the user's answer "{user_answer}" with the correct answer "{correct_answer}".
    Is the user's answer partially correct or substantially similar to the correct answer, even if not an exact match?
    Consider misspellings, slightly different phrasing, or capturing the main idea.
    Respond with "Yes" or "No" only.
    """
    try:
        response = _ai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=5, # Expecting a short answer
            temperature=0.0 # Make it deterministic
        )
        return response.choices[0].message.content.strip().lower() == "yes"
    except Exception as e:
        st.warning(f"⚠️ AI partial correctness check failed: {e}. Defaulting to exact match for this question.")
        return False


# --- OpenAI API Setup ---
if "OPENAI_API_KEY" not in st.secrets:
    st.error("❌ OPENAI_API_KEY is missing from Streamlit secrets.")
    st.stop()
client_ai = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


# --- Helper function to clean text for Latin-1 compatibility ---
def clean_text_for_latin1(text):
    """Replaces common problematic Unicode characters with Latin-1 safe equivalents."""
    if not isinstance(text, str):
        return text # Return as is if not a string (e.g., list or None)
    
    # Common smart quotes and other non-latin1 characters
    text = text.replace('\u2019', "'")  # Right single quotation mark
    text = text.replace('\u2018', "'")  # Left single quotation mark
    text = text.replace('\u201c', '"')  # Left double quotation mark
    text = text.replace('\u201d', '"')  # Right double quotation mark
    text = text.replace('\u2013', '-')  # En dash
    text = text.replace('\u2014', '--') # Em dash
    text = text.replace('\u2026', '...') # Ellipsis
    text = text.replace('\u00e9', 'e')  # é (e acute)
    text = text.replace('\u00e2', 'a')  # â (a circumflex)
    text = text.replace('\u00e7', 'c')  # ç (c cedilla)
    # Fallback for any remaining non-latin-1 characters (replace with '?')
    return text.encode('latin-1', errors='replace').decode('latin-1')

# --- New function to generate a specific article for a trivia question ---
def generate_related_trivia_article(question, answer, _ai_client):
    """
    Generates a short educational article explaining the answer to a trivia question.
    """
    prompt = f"""
    Write a concise, educational article (around 50-100 words) that explains the answer to the following trivia question and provides relevant context.
    
    Trivia Question: "{question}"
    Correct Answer: "{answer}"
    
    Focus on educating the reader about the topic related to the question and answer.
    """
    try:
        response = _ai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200, # Max 200 tokens for around 100 words
            temperature=0.5 # A bit more creativity
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.warning(f"⚠️ Could not generate explanation for trivia question: {e}. Please try again.")
        return "An explanation could not be generated at this time."

def translate_text_with_ai(text, target_language, _ai_client):
    """
    Translates a single string of text using the OpenAI API.
    """
    if not text or target_language == 'English':
        return text
    prompt = f"Translate the following text to {target_language} while preserving context, tone, and formatting (e.g., lists, paragraphs, specific dates/years in facts): \n\n{text}"
    try:
        response = _ai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000, # Increased max_tokens for longer articles
            temperature=0.2 # Keep it less creative for translation
        )
        translated_text = response.choices[0].message.content.strip()
        print(f"Translated '{text[:50]}...' to '{target_language}': '{translated_text[:50]}...'") # Debugging print
        return translated_text
    except Exception as e:
        st.warning(f"⚠️ Translation to {target_language} failed for some content: {e}. Displaying original English.")
        return text

def translate_content(data, target_language, _ai_client):
    """
    Translates relevant textual content within the daily_data dictionary,
    excluding trivia questions, hints, and answers.
    """
    if target_language == 'English':
        return data

    translated_data = data.copy() # Create a copy to modify

    # Translate main articles and facts
    translated_data['event_article'] = translate_text_with_ai(data['event_article'], target_language, _ai_client)
    translated_data['born_article'] = translate_text_with_ai(data['born_article'], target_language, _ai_client)
    translated_data['fun_fact_section'] = translate_text_with_ai(data['fun_fact_section'], target_language, _ai_client)
    translated_data['local_history_section'] = translate_text_with_ai(data['local_history_section'], target_language, _ai_client)

    # Translate Did You Know? section (list of strings)
    translated_data['did_you_know_section'] = [
        translate_text_with_ai(fact, target_language, _ai_client) for fact in data['did_you_know_section']
    ]

    # Translate Memory Prompts (list of strings)
    translated_data['memory_prompt_section'] = [
        translate_text_with_ai(prompt, target_language, _ai_client) for prompt in data['memory_prompt_section']
    ]

    # TRIVIA SECTION IS EXPLICITLY NOT TRANSLATED HERE.
    # It remains in its original English form as generated by get_this_day_in_history_facts.
    
    return translated_data

def parse_single_trivia_entry(entry_string):
    """
    Parses a single raw trivia entry string into its question, answer, and hint components.
    Assumes the structure: "Question (Answer) [Hint]" or variations with prefixes.
    """
    question = "No question found."
    answer = "No answer found."
    hint = "No hint found."

    temp_string = entry_string.strip()

    # Clean the string of any numbering/lettering at the very beginning (e.g., "a. - ", "1) ", "b- ")
    # Made pattern more robust to handle '.', ')', or '-' as separators for numbering
    temp_string = re.sub(r'^\s*([a-eA-E]|\d+)[.)-]?\s*', '', temp_string).strip()

    # 1. Extract Hint (looking for [Hint: ...])
    hint_match_bracket = re.search(r'\[(.*?)\]', temp_string, re.DOTALL)
    if hint_match_bracket:
        hint = hint_match_bracket.group(1).strip()
        temp_string = temp_string.replace(hint_match_bracket.group(0), '', 1).strip()
    else: # Fallback to "Hint:" or "Indice:" prefix if no brackets
        # Capture everything after "Hint:" or "Indice:" until the end of the string or a newline
        hint_match_prefix = re.search(r'(?:Hint|Indice):\s*(.*)', temp_string, re.IGNORECASE | re.DOTALL)
        if hint_match_prefix:
            hint = hint_match_prefix.group(1).strip()
            # Remove the full line that matched the hint
            temp_string = re.sub(r'(?:Hint|Indice):\s*.*', '', temp_string, flags=re.IGNORECASE | re.DOTALL).strip()

    # 2. Extract Answer (looking for (Answer))
    answer_match_paren = re.search(r'\((.*?)\)', temp_string, re.DOTALL)
    if answer_match_paren:
        answer = answer_match_paren.group(1).strip()
        temp_string = temp_string.replace(answer_match_paren.group(0), '', 1).strip()
    else: # Fallback to "Answer:" or "Reponse:" prefix
        # Capture everything after "Answer:" or "Reponse:" until the end of the string or a newline
        answer_match_prefix = re.search(r'(?:Answer|Reponse):\s*([^\n\[]*?)(?:\n|\[|\Z)', temp_string, re.IGNORECASE | re.DOTALL)
        if answer_match_prefix:
            answer = answer_match_prefix.group(1).strip()
            # Remove the matched answer prefix and its content from the string
            temp_string = re.sub(r'(?:Answer|Reponse):\s*[^\n\[]*?(?:\n|\[|\Z)', '', temp_string, flags=re.IGNORECASE | re.DOTALL).strip()

    # 3. Whatever remains is the question
    question = temp_string.strip()
    
    # Remove phrases that might indicate it's not a question (e.g., "Did you know?")
    if any(phrase.lower() in question.lower() for phrase in ["sabías que", "did you know", "disparadores de memoria", "memory prompts"]):
        question = "No question found."

    # Take only the first line of the question as the definitive question.
    question = question.split('\n')[0].strip()

    # Fallback for empty values if parsing failed for some reason
    if not question: question = "No question found."
    if not answer: answer = "No answer found."
    if not hint: hint = "No hint found."
    
    return {'question': question, 'answer': answer, 'hint': hint}


# --- This Day in History Logic ---
def get_this_day_in_history_facts(current_day, current_month, user_info, _ai_client, preferred_decade=None, topic=None, difficulty='Medium', local_city=None, local_state_country=None):
    """
    Generates 'This Day in History' facts using OpenAI API with specific content requirements.
    Incorporates customization options for decade, topic, difficulty, and local history.
    """
    current_date_str = f"{current_month:02d}-{current_day:02d}"

    event_word_count, born_word_count = 300, 150
    trivia_complexity = ""
    if difficulty == 'Easy':
        trivia_complexity = "very well-known facts, common knowledge"
    elif difficulty == 'Hard':
        trivia_complexity = "obscure facts, specific details, challenging"
    else: # Medium
        trivia_complexity = "general historical facts, moderately challenging"

    event_year_range = "between the years 1800 and 1960"
    born_year_range = "between 1800 and 1970"

    topic_clause = f" focusing on {topic}" if topic else ""
    decade_clause = f" specifically from the {preferred_decade}" if preferred_decade and preferred_decade != "None" else ""

    local_history_clause = ""
    if local_city and local_state_country:
        # Modified prompt for local history: always provide a general fact with its date/year
        local_history_clause = f"""
    7. Local History Fact: Provide one general historical fact about {local_city}, {local_state_country} (e.g., related to its founding, a major historical event, or a significant person). Always include the specific date (month, day, year) or year of the fact within the fact itself. Do NOT refer to "this day in history" or the current selected date. This fact must be a genuine historical event.
    """
    else:
        local_history_clause = """
    7. Local History Fact: Provide one general historical fact about the United States, including its specific date (month, day, year) or year. This fact must be a genuine historical event.
    """

    prompt = f"""
    You are an assistant generating 'This Day in History' facts for {current_date_str}.
    Please provide:

    1. Event Article: Write a short article (around {event_word_count} words) about a famous historical event that happened on this day {event_year_range}{topic_clause}{decade_clause}. Use clear, informative language.
    2. Born on this Day Article: Write a brief article (around {born_word_count} words) about a well-known person born on this day {born_year_range}{decade_clause}. Use clear, informative language.
    3. Fun Fact: Provide one interesting and unusual fun fact that occurred on this day in history.
    4. Trivia Questions: Provide **exactly five** concise, direct trivia questions based on today’s date. These should be actual questions that require a factual answer, and should not be "Did You Know?" statements or prompts for reflection. **Strictly avoid generating "Did You Know?" statements, "Memory Prompts", or any conversational phrases within the trivia questions themselves.** Topics can include history, famous birthdays, pop culture, or global events. The questions should be {trivia_complexity}. For each question, provide the correct answer in parentheses (like this) and a short, distinct hint in square brackets [like this]. Ensure each question is on a new line and begins with "a. ", "b. ", "c. ", "d. ", "e. " respectively.
    5. Did You Know?: Provide three "Did You Know?" facts related to nostalgic content (e.g., old prices, inventions, fashion facts) from past decades (e.g., 1930s-1970s).
    6. Memory Prompts: Provide **two to three** engaging questions to encourage reminiscing and conversation. Each prompt should be a complete sentence or question, without leading hyphens or bullet points in the raw output, ready to be formatted as paragraphs. (e.g., "Do you remember your first concert?", "What was your favorite childhood game?", "What's a memorable school event from your youth?").
    {local_history_clause}

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
        
        # Updated regex for Memory Prompt to capture multiple lines, allowing for paragraph form
        memory_prompt_match = re.search(r"6\. Memory Prompts:\s*(.*?)(?=\n7\. Local History Fact:|\Z|$)", content, re.DOTALL)

        # Special handling for Trivia Questions to extract questions, answers, and hints more robustly
        trivia_questions = []
        trivia_text_match = re.search(r"4\. Trivia Questions:\s*(.*?)(?=\n5\. Did You Know?:|\Z)", content, re.DOTALL)
        if trivia_text_match:
            raw_trivia_block = trivia_text_match.group(1).strip()
            
            # Use a more robust pattern to find individual trivia entries.
            # This pattern looks for lines starting with a letter (a-e) or digit, followed by '.' or ')' or '-',
            # and then captures everything until the next similar pattern or end of string.
            # This makes it robust to multiline questions/answers within one entry.
            trivia_entry_pattern = re.compile(r'^\s*(?:[a-eA-E]|\d+)[.)-]?\s*(.*?)(?=(?:\n\s*(?:[a-eA-E]|\d+)[.)-]?\s*|\Z))', re.MULTILINE | re.DOTALL)
            
            all_trivia_entries_raw = trivia_entry_pattern.findall(raw_trivia_block)

            for entry_text_raw in all_trivia_entries_raw:
                # The findall might return a tuple if there are capturing groups, take the first element if so
                if isinstance(entry_text_raw, tuple):
                    entry_text_raw = entry_text_raw[0]
                
                parsed_item = parse_single_trivia_entry(entry_text_raw)
                
                # Add question only if it's not the default "No question found."
                # and it actually contains some meaningful content
                if parsed_item['question'] != "No question found." and parsed_item['question'].strip() != "":
                    trivia_questions.append(parsed_item)
                
                if len(trivia_questions) >= 5: # Limit to 5 questions explicitly
                    break
        # If less than 5 questions are found, or none, ensure default behavior
        if len(trivia_questions) < 5:
            st.warning(f"⚠️ Only {len(trivia_questions)} trivia questions found. AI might not have generated enough or parsing failed for some. Filling missing questions with placeholders.")
            while len(trivia_questions) < 5:
                trivia_questions.append({
                    'question': 'No question available.',
                    'answer': 'No answer available.',
                    'hint': 'No hint available.'
                })


        # Special handling for Did You Know? to make parsing more robust
        did_you_know_lines = []
        did_you_know_match = re.search(r"5\. Did You Know\??:?\s*(?:\(Answer:\)\s*)?(.*?)(?=\n6\. Memory Prompts:|\Z)", content, re.DOTALL)
        if did_you_know_match:
            raw_facts_content = did_you_know_match.group(1).strip()
            for line in raw_facts_content.split('\n'):
                # Remove common prefixes like 'a.', 'b.', and any '(Answer:)'
                cleaned_line = re.sub(r'^[a-zA-Z]\.\s*', '', line).strip() # Remove "a. " "b. " etc.
                cleaned_line = re.sub(r'\s*\(Answer:\)\s*', '', cleaned_line).strip() # Remove (Answer:)
                if cleaned_line: # Only add if not empty after cleaning
                    did_you_know_lines.append(cleaned_line)
        
        # Ensure 'Did You Know?' always has at least one item, even if AI fails to generate
        if not did_you_know_lines:
            did_you_know_lines = ["No 'Did You Know?' facts available for today. Please try again or adjust preferences."]


        # Extract content, providing defaults if not found
        event_article = event_article_match.group(1).strip() if event_article_match else "No event article found."
        born_article = born_article_match.group(1).strip() if born_article_match else "No birth article found."
        fun_fact_section = fun_fact_match.group(1).strip() if fun_fact_match else "No fun fact found."
        
        # Parse multiple memory prompts into a list, splitting by paragraphs if possible
        memory_prompts_list = []
        if memory_prompt_match:
            raw_prompts_content = memory_prompt_match.group(1).strip()
            # Split by double newlines to get distinct paragraphs/prompts
            paragraphs = [p.strip() for p in raw_prompts_content.split('\n\n') if p.strip()]
            
            # If still only one paragraph, try splitting by single newline
            if len(paragraphs) < 2 and '\n' in raw_prompts_content:
                paragraphs = [p.strip() for p in raw_prompts_content.split('\n') if p.strip()]

            # Filter out any leading hyphens that AI might still generate despite prompt
            memory_prompts_list = [re.sub(r'^-?\s*', '', p) for p in paragraphs]

        # Ensure there are always at least a few prompts, even if AI fails
        if not memory_prompts_list:
            memory_prompts_list = [
                "No memory prompts available.",
                "Consider your favorite childhood memory.",
                "What's a happy moment from your past week?"
            ]


        # Extract Local History Fact - ensure a fact is always provided by AI.
        local_history_fact = "Could not generate local history fact." # Default if AI fails
        local_history_match = re.search(r"7\. Local History Fact:\s*(.*?)(?=\n\Z|$)", content, re.DOTALL)
        if local_history_match:
            local_history_fact = local_history_match.group(1).strip()


        return {
            'event_article': event_article,
            'born_article': born_article,
            'fun_fact_section': fun_fact_section,
            'trivia_section': trivia_questions, # Now a list of dicts {question, answer, hint}
            'did_you_know_section': did_you_know_lines,
            'memory_prompt_section': memory_prompts_list, # Now a list of prompts
            'local_history_section': local_history_fact # New local history fact
        }
    except Exception as e:
        st.error(f"Error generating history: {e}")
        return {
            'event_article': "Could not fetch event history.",
            'born_article': "Could not fetch birth history.",
            'fun_fact_section': "Could not fetch fun fact.",
            'trivia_section': [], # Empty list if error
            'did_you_know_section': ["No 'Did You Know?' facts available for today. Please try again or adjust preferences."], # Ensure default content
            'memory_prompt_section': ["No memory prompts available.", "Consider your favorite childhood memory.", "What's a happy moment from your past week?"],
            'local_history_section': "Could not fetch local history for your area. Please check your location settings or try again."
        }


def generate_full_history_pdf(data, today_date_str, user_info, current_language="English", custom_masthead_text=None): # Added custom_masthead_text parameter
    """
    Generates a PDF of 'This Day in History' facts, formatted over two pages.
    Page 1: Two-column layout with daily content.
    Page 2: About Us, Logo, and Contact Information.
    """
    pdf = FPDF(unit="mm", format="A4") # Use mm for better control
    pdf.add_page() # Start with the first page
    pdf.set_auto_page_break(True, margin=15) # Enable auto page break with a margin

    # Define dimensions for A4 and columns (in mm)
    page_width = pdf.w
    left_margin = 15
    right_margin = 15
    content_width = page_width - left_margin - right_margin
    col_width = (content_width - 10) / 2 # 10mm gutter between columns

    # Font sizes (now fixed for normal mode, as dementia mode is removed)
    title_font_size = 36
    date_font_size = 10
    section_title_font_size = 12
    article_text_font_size = 10
    line_height_normal = 5
    section_spacing_normal = 5

    # Define page 2 margins at the beginning
    left_margin_p2 = 25
    right_margin_p2 = 25
    content_width_p2 = page_width - left_margin_p2 - right_margin_p2


    # --- Masthead (Page 1) ---
    pdf.set_y(10) # Start from top
    pdf.set_x(left_margin)
    pdf.set_font("Times", "B", title_font_size) # Large, bold font for the title
    # Use custom masthead text if provided, otherwise default
    masthead_to_display = custom_masthead_text if custom_masthead_text and custom_masthead_text.strip() else "The Daily Resense Register"

    # The masthead text is specifically translated AND cleaned here.
    pdf.cell(0, 15, clean_text_for_latin1(translate_text_with_ai(masthead_to_display, current_language, client_ai)), align='C')
    pdf.ln(15)

    # Separator line
    pdf.set_line_width(0.5)
    pdf.line(left_margin, pdf.get_y(), page_width - right_margin, pdf.get_y())
    pdf.ln(8)

    pdf.set_font("Arial", "", date_font_size)
    pdf.cell(0, 5, today_date_str.upper(), align='C') # Date below the title
    pdf.ln(15)
    pdf.set_line_width(0.2) # Thinner line for content sections
    pdf.line(left_margin, pdf.get_y(), page_width - right_margin, pdf.get_y())
    pdf.ln(8)

    # --- Two-Column Layout for Page 1 ---
    # Store initial Y for content columns to ensure they start at the same height
    start_y_content = pdf.get_y()
    # Track current Y for each column
    current_y_col1 = start_y_content
    current_y_col2 = start_y_content

    # Column 1 (Left Column)
    pdf.set_left_margin(left_margin)
    pdf.set_right_margin(page_width / 2 + 5) # Right margin for left column = page_width / 2 + half_gutter
    pdf.set_x(left_margin) # Set X for the first column
    pdf.set_y(current_y_col1) # Start content at the same Y level

    # On This Day - Event Article
    pdf.set_font("Times", "B", section_title_font_size)
    pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(translate_text_with_ai("On This Day", current_language, client_ai)), 0, 'L')
    pdf.ln(2)
    pdf.set_font("Times", "", article_text_font_size)
    # Use write html to preserve line breaks within paragraphs
    pdf.write_html(line_height_normal, clean_text_for_latin1(translate_text_with_ai(data['event_article'], current_language, client_ai)))
    current_y_col1 = pdf.get_y() # Update current Y for column 1
    pdf.ln(section_spacing_normal)

    # Born on This Day - Born Article
    pdf.set_font("Times", "B", section_title_font_size)
    pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(translate_text_with_ai("Born on This Day", current_language, client_ai)), 0, 'L')
    pdf.ln(2)
    pdf.set_font("Times", "", article_text_font_size)
    pdf.write_html(line_height_normal, clean_text_for_latin1(translate_text_with_ai(data['born_article'], current_language, client_ai)))
    current_y_col1 = pdf.get_y()
    pdf.ln(section_spacing_normal)

    # Fun Fact
    pdf.set_font("Times", "B", section_title_font_size)
    pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(translate_text_with_ai("Fun Fact", current_language, client_ai)), 0, 'L')
    pdf.ln(2)
    pdf.set_font("Times", "", article_text_font_size)
    pdf.write_html(line_height_normal, clean_text_for_latin1(translate_text_with_ai(data['fun_fact_section'], current_language, client_ai)))
    current_y_col1 = pdf.get_y()
    pdf.ln(section_spacing_normal)

    # Column 2 (Right Column)
    pdf.set_left_margin(page_width / 2 + 5) # Left margin for right column = page_width / 2 + half_gutter
    pdf.set_right_margin(right_margin)
    pdf.set_x(page_width / 2 + 5) # Set X for the second column
    pdf.set_y(current_y_col2) # Start content at the same Y level

    # Did You Know?
    pdf.set_font("Times", "B", section_title_font_size)
    pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(translate_text_with_ai("Did You Know?", current_language, client_ai)), 0, 'L')
    pdf.ln(2)
    pdf.set_font("Times", "", article_text_font_size)
    # Ensure did_you_know_section is a list before iterating
    if isinstance(data['did_you_know_section'], list):
        for fact in data['did_you_know_section']:
            pdf.write_html(line_height_normal, "- " + clean_text_for_latin1(translate_text_with_ai(fact, current_language, client_ai)))
            pdf.ln(2) # Small line break between facts
    else: # Handle case where it might be a single string (fallback)
        pdf.write_html(line_height_normal, clean_text_for_latin1(translate_text_with_ai(data['did_you_know_section'], current_language, client_ai)))
    current_y_col2 = pdf.get_y()
    pdf.ln(section_spacing_normal)

    # Trivia Section
    pdf.set_font("Times", "B", section_title_font_size)
    pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(translate_text_with_ai("Trivia Time!", current_language, client_ai)), 0, 'L')
    pdf.ln(2)
    pdf.set_font("Times", "", article_text_font_size)
    # Trivia questions are NOT translated, only cleaned for Latin-1.
    if isinstance(data['trivia_section'], list):
        for i, trivia_item in enumerate(data['trivia_section']):
            question = trivia_item.get('question', 'N/A')
            answer = trivia_item.get('answer', 'N/A')
            hint = trivia_item.get('hint', 'N/A')
            pdf.write_html(line_height_normal, f"{i+1}. {clean_text_for_latin1(question)}")
            pdf.ln(line_height_normal / 2) # Smaller space after question
    else: # Fallback if trivia_section is not a list
        pdf.write_html(line_height_normal, clean_text_for_latin1(data['trivia_section']))
    current_y_col2 = pdf.get_y()
    pdf.ln(section_spacing_normal)

    # Local History Fact
    pdf.set_font("Times", "B", section_title_font_size)
    pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(translate_text_with_ai("Local History", current_language, client_ai)), 0, 'L')
    pdf.ln(2)
    pdf.set_font("Times", "", article_text_font_size)
    pdf.write_html(line_height_normal, clean_text_for_latin1(translate_text_with_ai(data['local_history_section'], current_language, client_ai)))
    current_y_col2 = pdf.get_y()
    pdf.ln(section_spacing_normal)

    # Memory Prompts
    pdf.set_font("Times", "B", section_title_font_size)
    pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(translate_text_with_ai("Memory Prompts", current_language, client_ai)), 0, 'L')
    pdf.ln(2)
    pdf.set_font("Times", "", article_text_font_size)
    # Ensure memory_prompt_section is a list before iterating
    if isinstance(data['memory_prompt_section'], list):
        for prompt_text in data['memory_prompt_section']:
            # The prompts are intended to be paragraphs, so don't add bullets.
            pdf.write_html(line_height_normal, clean_text_for_latin1(translate_text_with_ai(prompt_text, current_language, client_ai)))
            pdf.ln(line_height_normal) # New line for each prompt
    else: # Fallback if not a list
        pdf.write_html(line_height_normal, clean_text_for_latin1(translate_text_with_ai(data['memory_prompt_section'], current_language, client_ai)))
    current_y_col2 = pdf.get_y()
    pdf.ln(section_spacing_normal)


    # --- Page 2: About Us, Logo, Contact ---
    pdf.add_page()
    pdf.set_left_margin(left_margin_p2)
    pdf.set_right_margin(right_margin_p2)
    pdf.set_y(20) # Start further down on the second page

    # About Us
    pdf.set_font("Times", "B", 20)
    pdf.cell(0, 10, clean_text_for_latin1(translate_text_with_ai("About Us", current_language, client_ai)), 0, 1, 'C')
    pdf.ln(5)
    pdf.set_font("Times", "", 12)
    about_us_text = """
    Welcome to The Daily Resense Register, your personalized journey through history! Our mission is to rekindle cherished memories and spark new curiosities by connecting you with significant events and fun facts from this very day, tailored to your interests. We believe that understanding the past enriches our present and helps us build a more mindful future.
    
    Our content is carefully curated and designed to be engaging for all ages, promoting conversation and shared learning experiences within families and communities. From remarkable historical milestones to the birthdays of influential figures, and even local historical tidbits, we bring the past to life in a relevant and exciting way.
    
    Thank you for joining us on this adventure through time. We hope The Daily Resense Register becomes a cherished part of your daily routine, inspiring reflection, connection, and a deeper appreciation for the world around us.
    """
    pdf.write_html(8, clean_text_for_latin1(translate_text_with_ai(about_us_text, current_language, client_ai)))
    pdf.ln(10)

    # Logo Placeholder (if you have a logo image, you can add it here)
    # pdf.image("path/to/your/logo.png", x=pdf.w / 2 - 25, y=pdf.get_y(), w=50) # Example
    pdf.ln(10) # Space for logo if added

    # Contact Information
    pdf.set_font("Times", "B", 16)
    pdf.cell(0, 10, clean_text_for_latin1(translate_text_with_ai("Contact Us", current_language, client_ai)), 0, 1, 'C')
    pdf.ln(5)
    pdf.set_font("Times", "", 12)
    contact_info_text = f"""
    Email: info@dailyresense.com
    Website: www.dailyresense.com
    Follow us on Social Media: @DailyResense (Placeholder)

    Registered User: {user_info.get('username', 'Guest')}
    """
    pdf.write_html(8, clean_text_for_latin1(translate_text_with_ai(contact_info_text, current_language, client_ai)))
    pdf.ln(10)


    # Output the PDF as bytes
    return pdf.output(dest='S').encode('latin-1')


# --- Helper functions for page navigation (Moved here for better organization) ---
def set_page(page_name):
    st.session_state['current_page'] = page_name
    # Reset relevant session states when changing pages
    if page_name == 'main_app':
        st.session_state['last_fetched_date'] = None # Force re-fetch for main app
    st.session_state['last_download_status'] = None # Clear download status


# --- Login/Registration Page ---
def show_login_page():
    st.title("Login or Register")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Login")
        login_username = st.text_input("Username", key="login_username")
        login_password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login", key="login_button"):
            users = get_users_from_sheet()
            if login_username in users and users[login_username] == login_password:
                st.session_state['is_authenticated'] = True
                st.session_state['logged_in_username'] = login_username
                log_event("login", login_username)
                set_page('main_app') # Go to the main app after login
                st.rerun()
            else:
                st.error("Invalid username or password.")
                log_event("failed_login", login_username)

    with col2:
        st.subheader("Register")
        reg_username = st.text_input("New Username", key="reg_username")
        reg_password = st.text_input("New Password", type="password", key="reg_password")
        reg_email = st.text_input("Email (Optional)", key="reg_email")
        if st.button("Register", key="register_button"):
            users = get_users_from_sheet()
            if reg_username in users:
                st.warning("Username already exists. Please choose a different one.")
            else:
                if save_new_user_to_sheet(reg_username, reg_password, reg_email):
                    st.success("Registration successful! Please log in.")
                    log_event("registration", reg_username)
                else:
                    st.error("Failed to register. Please try again.")

# --- Main Application Page ---
def show_main_app_page():
    st.title(translate_text_with_ai("Welcome to The Daily Resense Register!", st.session_state['preferred_language'], client_ai))

    # User Info Placeholder (replace with actual user data if available)
    user_info = {
        'username': st.session_state.get('logged_in_username', 'Guest'),
        'preferred_decade': None,
        'topic': None
    }
    
    # Custom Masthead Text input
    current_masthead_text = st.session_state.get('custom_masthead_text', '')
    new_masthead_text = st.text_input(
        translate_text_with_ai("Custom PDF Masthead Text (e.g., 'Grandma's Daily Reads')", st.session_state['preferred_language'], client_ai),
        value=current_masthead_text,
        max_chars=50,
        help=translate_text_with_ai("This text will appear at the top of your generated PDF instead of the default title.", st.session_state['preferred_language'], client_ai)
    )
    if new_masthead_text != current_masthead_text:
        st.session_state['custom_masthead_text'] = new_masthead_text


    # Date Selection for Main App
    today = date.today()
    selected_date_main_app = st.date_input(
        translate_text_with_ai("Select Date for Daily Content", st.session_state['preferred_language'], client_ai),
        value=st.session_state.get('selected_date_main_app', today),
        max_value=today, # Cannot select future dates
        key='main_app_date_picker'
    )
    st.session_state['selected_date_main_app'] = selected_date_main_app

    # Conditional fetching of data to avoid re-fetching on every rerun
    if st.session_state['daily_data'] is None or st.session_state['last_fetched_date'] != selected_date_main_app:
        with st.spinner(translate_text_with_ai("Fetching today's history and facts...", st.session_state['preferred_language'], client_ai)):
            st.session_state['raw_fetched_data'] = get_this_day_in_history_facts(
                selected_date_main_app.day,
                selected_date_main_app.month,
                user_info,
                client_ai,
                difficulty=st.session_state['difficulty'],
                local_city=st.session_state['local_city'],
                local_state_country=st.session_state['local_state_country']
            )
            st.session_state['last_fetched_date'] = selected_date_main_app
            st.session_state['score_logged_today'] = False # Reset for new day
            # Re-initialize trivia question states for the new day's trivia
            st.session_state['trivia_question_states'] = {
                f'q_{i}': {
                    'user_answer': '',
                    'is_correct': False,
                    'feedback': '',
                    'hint_revealed': False,
                    'attempts': 0,
                    'out_of_chances': False,
                    'points_earned': 0,
                    'related_article_content': None
                }
                for i in range(len(st.session_state['raw_fetched_data']['trivia_section']))
            }
            st.session_state['hints_remaining'] = 3 # Reset hints for new day
            st.session_state['current_trivia_score'] = 0
            st.session_state['total_possible_daily_trivia_score'] = 0
            time.sleep(1) # Give spinner time to show


    # Translate the fetched content for display
    st.session_state['daily_data'] = translate_content(
        st.session_state['raw_fetched_data'],
        st.session_state['preferred_language'],
        client_ai
    )

    data = st.session_state['daily_data']

    st.subheader(translate_text_with_ai("On This Day", st.session_state['preferred_language'], client_ai))
    st.write(data['event_article'])

    st.subheader(translate_text_with_ai("Born on This Day", st.session_state['preferred_language'], client_ai))
    st.write(data['born_article'])

    st.subheader(translate_text_with_ai("Fun Fact", st.session_state['preferred_language'], client_ai))
    st.write(data['fun_fact_section'])

    st.subheader(translate_text_with_ai("Local History", st.session_state['preferred_language'], client_ai))
    st.write(data['local_history_section'])

    st.subheader(translate_text_with_ai("Did You Know?", st.session_state['preferred_language'], client_ai))
    for fact in data['did_you_know_section']:
        st.markdown(f"- {fact}")

    st.subheader(translate_text_with_ai("Memory Prompts", st.session_state['preferred_language'], client_ai))
    for prompt_text in data['memory_prompt_section']:
        st.write(prompt_text)
    
    st.markdown("---") # Separator

    # PDF Download Button for Main App
    if st.button(translate_text_with_ai("Download Today's PDF", st.session_state['preferred_language'], client_ai), key="download_pdf_btn"):
        with st.spinner(translate_text_with_ai("Generating PDF...", st.session_state['preferred_language'], client_ai)):
            pdf_bytes = generate_full_history_pdf(
                st.session_state['daily_data'],
                selected_date_main_app.strftime("%B %d, %Y"),
                user_info,
                st.session_state['preferred_language'],
                st.session_state['custom_masthead_text'] # Pass custom masthead text
            )
            b64_pdf = base64.b64encode(pdf_bytes).decode('latin-1')
            pdf_filename = f"Daily_Resense_Register_{selected_date_main_app.strftime('%Y%m%d')}.pdf"
            
            # Log the download event
            if log_pdf_download(st.session_state['logged_in_username'], pdf_filename, selected_date_main_app):
                st.session_state['last_download_status'] = "success"
            else:
                st.session_state['last_download_status'] = "failure"
            
            # Use markdown with a direct download link trick for better compatibility
            # This allows the download to happen without rerun issues from st.download_button's nature
            download_link = f'<a href="data:application/pdf;base64,{b64_pdf}" download="{pdf_filename}" target="_blank">{translate_text_with_ai("Click here to download your PDF!", st.session_state["preferred_language"], client_ai)}</a>'
            st.markdown(download_link, unsafe_allow_html=True)
            time.sleep(1) # Give time for the download link to appear

    # Display download status feedback
    if st.session_state['last_download_status'] == "success":
        st.success(translate_text_with_ai("PDF generated and download logged successfully!", st.session_state['preferred_language'], client_ai))
        st.session_state['last_download_status'] = None # Clear status after display
    elif st.session_state['last_download_status'] == "failure":
        st.error(translate_text_with_ai("Failed to log PDF download. PDF might still download.", st.session_state['preferred_language'], client_ai))
        st.session_state['last_download_status'] = None # Clear status


    # Button to navigate to Trivia Page
    if st.button(translate_text_with_ai("Play Trivia!", st.session_state['preferred_language'], client_ai), key="go_to_trivia_btn"):
        set_page('trivia_page')
        st.rerun()

# --- Trivia Page ---
def show_trivia_page():
    st.title(translate_text_with_ai("Daily Trivia Challenge", st.session_state['preferred_language'], client_ai))

    if not st.session_state['raw_fetched_data'] or not st.session_state['raw_fetched_data']['trivia_section']:
        st.warning(translate_text_with_ai("No trivia questions available for this date. Please go back to the main page and fetch daily content first.", st.session_state['preferred_language'], client_ai))
        if st.button(translate_text_with_ai("Back to Main App", st.session_state['preferred_language'], client_ai), key="back_to_main_from_trivia_no_content"):
            set_page('main_app')
            st.rerun()
        return

    trivia_questions = st.session_state['raw_fetched_data']['trivia_section']
    total_questions = len(trivia_questions)

    # Calculate total possible score based on initial question count
    if st.session_state['total_possible_daily_trivia_score'] == 0:
        st.session_state['total_possible_daily_trivia_score'] = total_questions * 10 # 10 points per question

    st.write(translate_text_with_ai(f"Date: {st.session_state['last_fetched_date'].strftime('%B %d, %Y')}", st.session_state['preferred_language'], client_ai))
    st.write(translate_text_with_ai(f"Hints Remaining Today: {st.session_state['hints_remaining']}", st.session_state['preferred_language'], client_ai))
    st.metric(label=translate_text_with_ai("Current Score", st.session_state['preferred_language'], client_ai), value=f"{st.session_state['current_trivia_score']} / {st.session_state['total_possible_daily_trivia_score']}")


    for i, q_data in enumerate(trivia_questions):
        q_key = f'q_{i}'
        # Initialize state for this question if not already present (should be by now)
        if q_key not in st.session_state['trivia_question_states']:
            st.session_state['trivia_question_states'][q_key] = {
                'user_answer': '', 'is_correct': False, 'feedback': '', 'hint_revealed': False,
                'attempts': 0, 'out_of_chances': False, 'points_earned': 0, 'related_article_content': None
            }
        
        q_state = st.session_state['trivia_question_states'][q_key]

        st.markdown(f"**{i+1}. {translate_text_with_ai(q_data['question'], st.session_state['preferred_language'], client_ai)}**")

        if not q_state['is_correct'] and not q_state['out_of_chances']:
            user_input = st.text_input(
                translate_text_with_ai("Your Answer:", st.session_state['preferred_language'], client_ai),
                value=q_state['user_answer'],
                key=f"user_answer_{q_key}"
            )
            
            # Update user_answer in session state immediately on input change
            if user_input != q_state['user_answer']:
                q_state['user_answer'] = user_input
                # Do not rerun here, allow the button to handle the check
                # st.experimental_rerun() # This caused issues, removed

            col_check, col_hint = st.columns([1,1])

            with col_check:
                if st.button(translate_text_with_ai("Check Answer", st.session_state['preferred_language'], client_ai), key=f"check_btn_{q_key}"):
                    q_state['attempts'] += 1
                    
                    is_correct_exact = (user_input.strip().lower() == q_data['answer'].strip().lower())
                    is_correct_ai_partial = check_partial_correctness_with_ai(user_input, q_data['answer'], client_ai)
                    
                    if is_correct_exact or is_correct_ai_partial:
                        q_state['is_correct'] = True
                        q_state['feedback'] = translate_text_with_ai("🎉 Correct!", st.session_state['preferred_language'], client_ai)
                        if q_state['attempts'] == 1:
                            q_state['points_earned'] = 10 # Full points for first try
                        else:
                            q_state['points_earned'] = 5 # Half points for subsequent correct try
                        st.session_state['current_trivia_score'] += q_state['points_earned']
                        # Generate related article only on correct answer
                        with st.spinner(translate_text_with_ai("Generating explanation...", st.session_state['preferred_language'], client_ai)):
                            q_state['related_article_content'] = generate_related_trivia_article(q_data['question'], q_data['answer'], client_ai)
                            q_state['related_article_content'] = translate_text_with_ai(q_state['related_article_content'], st.session_state['preferred_language'], client_ai)
                        st.rerun()
                    else:
                        if q_state['attempts'] >= 2: # Max 2 attempts
                            q_state['feedback'] = translate_text_with_ai(f"❌ Incorrect. The answer was: {q_data['answer']}", st.session_state['preferred_language'], client_ai)
                            q_state['out_of_chances'] = True
                            # Generate related article on exhaustion of chances
                            with st.spinner(translate_text_with_ai("Generating explanation...", st.session_state['preferred_language'], client_ai)):
                                q_state['related_article_content'] = generate_related_trivia_article(q_data['question'], q_data['answer'], client_ai)
                                q_state['related_article_content'] = translate_text_with_ai(q_state['related_article_content'], st.session_state['preferred_language'], client_ai)
                            st.rerun()
                        else:
                            q_state['feedback'] = translate_text_with_ai("Try again!", st.session_state['preferred_language'], client_ai)
                            st.warning(q_state['feedback'])
                            time.sleep(0.1) # Small delay for UI update


            with col_hint:
                if not q_state['hint_revealed'] and st.session_state['hints_remaining'] > 0:
                    if st.button(translate_text_with_ai("Get Hint", st.session_state['preferred_language'], client_ai), key=f"hint_btn_{q_key}"):
                        st.info(translate_text_with_ai(f"Hint: {q_data['hint']}", st.session_state['preferred_language'], client_ai))
                        st.session_state['hints_remaining'] -= 1
                        q_state['hint_revealed'] = True
                        time.sleep(0.1) # Small delay for UI update
                        st.rerun()
                elif q_state['hint_revealed']:
                    st.info(translate_text_with_ai(f"Hint: {q_data['hint']}", st.session_state['preferred_language'], client_ai))
                elif st.session_state['hints_remaining'] <= 0 and not q_state['hint_revealed']:
                    st.text(translate_text_with_ai("No hints left for today.", st.session_state['preferred_language'], client_ai))
        
        if q_state['is_correct'] or q_state['out_of_chances']:
            st.write(q_state['feedback'])
            if q_state['related_article_content']:
                with st.expander(translate_text_with_ai("Learn More", st.session_state['preferred_language'], client_ai)):
                    st.write(q_state['related_article_content'])
        
        st.markdown("---") # Separator between questions

    # End of Trivia
    if all(st.session_state['trivia_question_states'][f'q_{i}']['is_correct'] or st.session_state['trivia_question_states'][f'q_{i}']['out_of_chances'] for i in range(total_questions)):
        st.subheader(translate_text_with_ai("Trivia Challenge Complete!", st.session_state['preferred_language'], client_ai))
        st.metric(label=translate_text_with_ai("Final Score", st.session_state['preferred_language'], client_ai), value=f"{st.session_state['current_trivia_score']} / {st.session_state['total_possible_daily_trivia_score']}")

        if not st.session_state['score_logged_today']:
            if st.button(translate_text_with_ai("Log My Score", st.session_state['preferred_language'], client_ai), key="log_score_btn"):
                if log_trivia_score(st.session_state['logged_in_username'], st.session_state['current_trivia_score']):
                    st.success(translate_text_with_ai("Your score has been logged!", st.session_state['preferred_language'], client_ai))
                    st.session_state['score_logged_today'] = True
                else:
                    st.error(translate_text_with_ai("Failed to log your score. Please try again.", st.session_state['preferred_language'], client_ai))
        
        st.subheader(translate_text_with_ai("Leaderboard", st.session_state['preferred_language'], client_ai))
        leaderboard_data = get_leaderboard_data()
        if leaderboard_data:
            for rank, (user, score) in enumerate(leaderboard_data):
                st.write(f"{rank+1}. {user}: {score} points")
        else:
            st.info(translate_text_with_ai("No scores logged yet.", st.session_state['preferred_language'], client_ai))


    if st.button(translate_text_with_ai("Back to Main App", st.session_state['preferred_language'], client_ai), key="back_to_main_from_trivia"):
        set_page('main_app')
        st.rerun()


# --- NEW: Weekly Planner Page ---
def show_weekly_planner_page():
    st.title(translate_text_with_ai("Weekly Planner", st.session_state['preferred_language'], client_ai))
    st.write(translate_text_with_ai("Select a date to generate a week's worth of personalized historical content PDFs.", st.session_state['preferred_language'], client_ai))

    # Date selection for the week
    selected_week_start_date = st.date_input(
        translate_text_with_ai("Select a starting date for the week:", st.session_state['preferred_language'], client_ai),
        value=st.session_state['weekly_planner_date'],
        max_value=date.today(), # Cannot select future dates
        key='weekly_planner_date_picker'
    )
    st.session_state['weekly_planner_date'] = selected_week_start_date

    # Ensure the selected date is a Monday for consistency, or adjust it
    # Find the Monday of the week for the selected date
    start_of_week = selected_week_start_date - timedelta(days=selected_week_start_date.weekday())
    st.info(translate_text_with_ai(f"Generating content for the week of: **{start_of_week.strftime('%B %d, %Y')}**", st.session_state['preferred_language'], client_ai))

    # Get user info for PDF generation
    user_info = {
        'username': st.session_state.get('logged_in_username', 'Guest'),
        'preferred_decade': None, # Weekly planner doesn't currently support these custom settings per PDF
        'topic': None
    }

    if st.button(translate_text_with_ai("Generate Weekly PDFs", st.session_state['preferred_language'], client_ai), key="generate_weekly_pdfs_btn"):
        pdf_files = []
        zip_buffer = io.BytesIO()

        with st.spinner(translate_text_with_ai("Generating weekly PDFs... This may take a few minutes.", st.session_state['preferred_language'], client_ai)):
            for i in range(7):
                current_date = start_of_week + timedelta(days=i)
                day_name = current_date.strftime('%A')
                st.write(translate_text_with_ai(f"Fetching content for {day_name}, {current_date.strftime('%B %d, %Y')}...", st.session_state['preferred_language'], client_ai))

                # Fetch raw data for the specific day
                raw_data_for_day = get_this_day_in_history_facts(
                    current_date.day,
                    current_date.month,
                    user_info,
                    client_ai,
                    difficulty=st.session_state['difficulty'],
                    local_city=st.session_state['local_city'],
                    local_state_country=st.session_state['local_state_country']
                )

                # Translate the data
                translated_data_for_day = translate_content(
                    raw_data_for_day,
                    st.session_state['preferred_language'],
                    client_ai
                )

                # Generate PDF for the day
                pdf_bytes_for_day = generate_full_history_pdf(
                    translated_data_for_day,
                    current_date.strftime("%B %d, %Y"),
                    user_info,
                    st.session_state['preferred_language'],
                    st.session_state['custom_masthead_text']
                )
                pdf_files.append((f"Daily_Resense_Register_{current_date.strftime('%Y%m%d')}.pdf", pdf_bytes_for_day))
                time.sleep(0.5) # Small delay to be gentle on APIs and show progress

            # Create zip file
            with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zf:
                for filename, pdf_content in pdf_files:
                    zf.writestr(filename, pdf_content)
            
            zip_buffer.seek(0) # Rewind the buffer to the beginning

            zip_filename = f"Weekly_Resense_Register_{start_of_week.strftime('%Y%m%d')}.zip"
            st.session_state['generated_zip_file'] = zip_buffer.getvalue()
            st.session_state['generated_zip_filename'] = zip_filename

            st.success(translate_text_with_ai("Weekly PDFs generated and zipped!", st.session_state['preferred_language'], client_ai))
        
        # Display download button for the zip file
        if 'generated_zip_file' in st.session_state and st.session_state['generated_zip_file']:
            st.download_button(
                label=translate_text_with_ai("Download Weekly Planner (ZIP)", st.session_state['preferred_language'], client_ai),
                data=st.session_state['generated_zip_file'],
                file_name=st.session_state['generated_zip_filename'],
                mime="application/zip",
                key="download_weekly_zip_btn"
            )
            # Log the weekly download
            if log_pdf_download(st.session_state['logged_in_username'], st.session_state['generated_zip_filename'], start_of_week):
                st.success(translate_text_with_ai("Weekly planner download logged successfully!", st.session_state['preferred_language'], client_ai))
            else:
                st.error(translate_text_with_ai("Failed to log weekly planner download.", st.session_state['preferred_language'], client_ai))


    if st.button(translate_text_with_ai("Back to Main App", st.session_state['preferred_language'], client_ai), key="back_to_main_from_weekly"):
        set_page('main_app')
        st.rerun()


# --- Application Entry Point ---
if not st.session_state['is_authenticated']:
    show_login_page()
else:
    # --- Sidebar for Navigation and Settings ---
    with st.sidebar:
        st.image("https://i.imgur.com/Q2h9W4K.png", width=100) # Ensure this image path is correct/accessible
        st.title(translate_text_with_ai("Resense Register", st.session_state['preferred_language'], client_ai))

        st.markdown("---")
        st.subheader(translate_text_with_ai("Navigation", st.session_state['preferred_language'], client_ai))
        if st.button(translate_text_with_ai("🏠 Home", st.session_state['preferred_language'], client_ai), key="sidebar_home_btn"):
            set_page('main_app')
            st.rerun()
        if st.button(translate_text_with_ai("🧠 Daily Trivia", st.session_state['preferred_language'], client_ai), key="sidebar_trivia_btn"):
            set_page('trivia_page')
            st.rerun()
        # NEW: Weekly Planner Button
        if st.button(translate_text_with_ai("🗓️ Weekly Planner", st.session_state['preferred_language'], client_ai), key="sidebar_weekly_planner_btn"):
            set_page('weekly_planner')
            st.rerun()

        st.markdown("---")
        st.subheader(translate_text_with_ai("Settings", st.session_state['preferred_language'], client_ai))

        st.session_state['difficulty'] = st.sidebar.selectbox(
            translate_text_with_ai("Difficulty", st.session_state['preferred_language'], client_ai),
            options=['Easy', 'Medium', 'Hard'],
            index=['Easy', 'Medium', 'Hard'].index(st.session_state['difficulty']),
            key='sidebar_difficulty_select',
            help=translate_text_with_ai("Adjust the complexity of generated content and trivia.", st.session_state['preferred_language'], client_ai)
        )

        st.text_input(
            translate_text_with_ai("Local City (for history)", st.session_state['preferred_language'], client_ai),
            value=st.session_state['local_city'],
            key='sidebar_local_city',
            help=translate_text_with_ai("e.g., Pittsburgh", st.session_state['preferred_language'], client_ai)
        )
        st.text_input(
            translate_text_with_ai("Local State/Country", st.session_state['preferred_language'], client_ai),
            value=st.session_state['local_state_country'],
            key='sidebar_local_state_country',
            help=translate_text_with_ai("e.g., Pennsylvania, USA", st.session_state['preferred_language'], client_ai)
        )

        st.session_state['preferred_language'] = st.sidebar.selectbox(
            translate_text_with_ai("Display Language", st.session_state['preferred_language'], client_ai),
            options=["English", "Spanish", "French", "German", "Italian", "Portuguese"],
            index=["English", "Spanish", "French", "German", "Italian", "Portuguese"].index(st.session_state['preferred_language']),
            key='sidebar_language_select',
            help=translate_text_with_ai("Select the language for the daily content and PDF.", st.session_state['preferred_language'], client_ai)
        )

        st.sidebar.markdown("---")
        if st.sidebar.button(translate_text_with_ai("🚪 Log Out", st.session_state['preferred_language'], client_ai), key="sidebar_logout_btn"):
            log_event("logout", st.session_state['logged_in_username'])
            st.session_state['is_authenticated'] = False
            st.session_state['logged_in_username'] = ""
            set_page('login_page') # Go back to the login page (or main app if unauthenticated)
            st.rerun()

    # --- Page Rendering based on current_page ---
    if st.session_state['current_page'] == 'main_app':
        show_main_app_page()
    elif st.session_state['current_page'] == 'trivia_page':
        show_trivia_page()
    elif st.session_state['current_page'] == 'weekly_planner': # NEW: Handle Weekly Planner page
        show_weekly_planner_page()
    # Default to main_app if current_page is somehow not set to a valid page
    else:
        st.session_state['current_page'] = 'main_app'
        show_main_app_page()
