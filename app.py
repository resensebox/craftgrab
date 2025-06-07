import streamlit as st
from openai import OpenAI
from datetime import datetime, date, timedelta # Import timedelta for date calculations
from fpdf import FPDF
import re
import json
import base64
import time
import zipfile # Import zipfile for creating ZIP archives
import io # Import io for in-memory file operations

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
if 'user_info' not in st.session_state: # User info for API calls
    st.session_state['user_info'] = {"username": "Guest"}


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
            'trivia_section': trivia_questions,  # Now a list of dicts {question, answer, hint}
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
            'trivia_section': [],  # Empty list if error
            'did_you_know_section': ["No 'Did You Know?' facts available for today. Please try again or adjust preferences."], # Ensure default content
            'memory_prompt_section': ["No memory prompts available.", "Consider your favorite childhood memory.", "What's a happy moment from your past week?"],
            'local_history_section': "Could not fetch local history for your area. Please check your location settings or try again."
        }

# --- New function to generate companion activities ---
def generate_companion_activities(event_article, fun_fact, target_language, _ai_client):
    """
    Generates a single companion activity idea based on the main historical event and fun fact.
    The activity includes title, supplies, step-by-step instructions, and a blurb on its connection.
    """
    prompt = f"""
    For the following historical event article and fun fact, generate ONE related companion activity idea.
    The activity should be suitable for seniors or activity directors (craft, food, movement, or discussion-based).
    
    Historical Event:
    {event_article}
    
    Fun Fact:
    {fun_fact}
    
    Provide the activity details in the following structured format:
    
    Activity Title: [A concise, engaging title for the activity]
    Activity Type: [e.g., Craft, Food, Movement, Discussion]
    Required Supplies: [List of supplies, e.g., "Paper, scissors, glue"]
    Instructions:
    1. [Step 1]
    2. [Step 2]
    ...
    Connection to History: [A short paragraph explaining how this activity connects to the historical event or fun fact mentioned]
    
    Ensure the activity is practical and easy to implement.
    """
    
    if target_language != 'English':
        prompt = translate_text_with_ai(prompt, target_language, _ai_client) # Translate the prompt itself

    try:
        response = _ai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500, # Increased max tokens for detailed activity
            temperature=0.7 # Allow for more creative activity ideas
        )
        activity_content = response.choices[0].message.content.strip()

        # Parse the structured response
        activity = {
            'title': "No activity title found.",
            'type': "General",
            'supplies': "No supplies listed.",
            'instructions': [],
            'connection': "No connection explanation found."
        }
        
        title_match = re.search(r"Activity Title:\s*(.*?)(?=\n|$)", activity_content, re.DOTALL)
        type_match = re.search(r"Activity Type:\s*(.*?)(?=\n|$)", activity_content, re.DOTALL)
        supplies_match = re.search(r"Required Supplies:\s*(.*?)(?=\nInstructions:|\Z)", activity_content, re.DOTALL)
        instructions_match = re.search(r"Instructions:\s*(.*?)(?=\nConnection to History:|\Z)", activity_content, re.DOTALL)
        connection_match = re.search(r"Connection to History:\s*(.*?)(?=\n|$)", activity_content, re.DOTALL)

        if title_match: activity['title'] = title_match.group(1).strip()
        if type_match: activity['type'] = type_match.group(1).strip()
        if supplies_match: activity['supplies'] = supplies_match.group(1).strip()
        if connection_match: activity['connection'] = connection_match.group(1).strip()

        if instructions_match:
            raw_instructions = instructions_match.group(1).strip()
            # Split instructions by numbered list items
            instructions = [re.sub(r'^\d+\.\s*', '', line).strip() for line in raw_instructions.split('\n') if re.match(r'^\d+\.\s*', line)]
            activity['instructions'] = instructions if instructions else ["No instructions provided."]
        
        # Translate the generated activity if it was generated in English and target language is different
        if target_language != 'English':
            activity['title'] = translate_text_with_ai(activity['title'], target_language, _ai_client)
            activity['type'] = translate_text_with_ai(activity['type'], target_language, _ai_client)
            activity['supplies'] = translate_text_with_ai(activity['supplies'], target_language, _ai_client)
            activity['instructions'] = [translate_text_with_ai(inst, target_language, _ai_client) for inst in activity['instructions']]
            activity['connection'] = translate_text_with_ai(activity['connection'], target_language, _ai_client)

        return activity

    except Exception as e:
        st.warning(f"⚠️ Could not generate companion activity: {e}. Please try again.")
        return {
            'title': "No Activity Generated",
            'type': "N/A",
            'supplies': "N/A",
            'instructions': ["Could not generate instructions."],
            'connection': "Could not generate connection."
        }

# --- Modified PDF Generation Functions to return bytes ---
def generate_full_history_pdf(data, today_date_str, user_info, current_language="English", custom_masthead_text=None): # Added custom_masthead_text parameter
    """ 
    Generates a PDF of 'This Day in History' facts, formatted over two pages.
    Page 1: Two-column layout with daily content.
    Page 2: About Us, Logo, and Contact Information.
    Returns the PDF as bytes.
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
    masthead_to_display = clean_text_for_latin1(
        translate_text_with_ai(masthead_to_display, current_language, client_ai)
    )
    pdf.cell(content_width, 15, txt=masthead_to_display, ln=True, align='C')

    pdf.ln(2)
    pdf.set_font("Times", "", date_font_size)
    date_text = translate_text_with_ai(f"Date: {today_date_str}", current_language, client_ai)
    pdf.cell(content_width, 5, txt=clean_text_for_latin1(date_text), ln=True, align='R')
    pdf.ln(5)

    # --- Two-Column Layout (Page 1) ---
    pdf.set_y(pdf.get_y() + 5) # Move down a bit after date
    start_y = pdf.get_y() # Capture the starting Y for columns

    # Column 1 (Left)
    pdf.set_x(left_margin)
    col1_start_x = pdf.get_x()
    
    # Event Article
    pdf.set_font("Times", "B", section_title_font_size)
    event_title = translate_text_with_ai("This Day In History", current_language, client_ai)
    pdf.multi_cell(col_width, line_height_normal, txt=clean_text_for_latin1(event_title), align='L')
    pdf.ln(1)
    pdf.set_font("Times", "", article_text_font_size)
    event_article_content = clean_text_for_latin1(data['event_article'])
    pdf.multi_cell(col_width, line_height_normal, txt=event_article_content, align='J')
    pdf.ln(section_spacing_normal)

    # Born on this Day Article
    pdf.set_font("Times", "B", section_title_font_size)
    born_title = translate_text_with_ai("Born On This Day", current_language, client_ai)
    pdf.multi_cell(col_width, line_height_normal, txt=clean_text_for_latin1(born_title), align='L')
    pdf.ln(1)
    pdf.set_font("Times", "", article_text_font_size)
    born_article_content = clean_text_for_latin1(data['born_article'])
    pdf.multi_cell(col_width, line_height_normal, txt=born_article_content, align='J')
    pdf.ln(section_spacing_normal)

    # Trivia Questions (in Column 1 or dynamically flow to Column 2 if needed)
    # This might need dynamic positioning or ensuring it starts cleanly after articles
    pdf.set_font("Times", "B", section_title_font_size)
    trivia_title = translate_text_with_ai("Trivia Time!", current_language, client_ai)
    pdf.multi_cell(col_width, line_height_normal, txt=clean_text_for_latin1(trivia_title), align='L')
    pdf.ln(1)
    pdf.set_font("Times", "", article_text_font_size)
    
    # Track current Y position for trivia
    trivia_y_start = pdf.get_y()
    
    # Trivia content is NOT translated in the app, but its labels are.
    # We only clean the existing (English) question/answer/hint for Latin-1 compatibility.
    for i, q_data in enumerate(data['trivia_section']):
        question = clean_text_for_latin1(f"{i+1}. {q_data['question']}")
        answer = clean_text_for_latin1(q_data['answer'])
        hint = clean_text_for_latin1(q_data['hint'])

        pdf.multi_cell(col_width, line_height_normal, txt=f"{question}", align='L')
        pdf.multi_cell(col_width, line_height_normal, txt=f"   {translate_text_with_ai('Answer:', current_language, client_ai)} {answer}", align='L')
        pdf.multi_cell(col_width, line_height_normal, txt=f"   {translate_text_with_ai('Hint:', current_language, client_ai)} {hint}", align='L')
        pdf.ln(2) # Smaller line break for trivia

    # Column 2 (Right)
    # Set X position for column 2, aligning it with the right side of col1_start_x + col_width + gutter
    pdf.set_xy(col1_start_x + col_width + 10, start_y)

    # Fun Fact
    pdf.set_font("Times", "B", section_title_font_size)
    fun_fact_title = translate_text_with_ai("Fun Fact", current_language, client_ai)
    pdf.multi_cell(col_width, line_height_normal, txt=clean_text_for_latin1(fun_fact_title), align='L')
    pdf.ln(1)
    pdf.set_font("Times", "", article_text_font_size)
    fun_fact_content = clean_text_for_latin1(data['fun_fact_section'])
    pdf.multi_cell(col_width, line_height_normal, txt=fun_fact_content, align='J')
    pdf.ln(section_spacing_normal)

    # Did You Know?
    pdf.set_font("Times", "B", section_title_font_size)
    did_you_know_title = translate_text_with_ai("Did You Know?", current_language, client_ai)
    pdf.multi_cell(col_width, line_height_normal, txt=clean_text_for_latin1(did_you_know_title), align='L')
    pdf.ln(1)
    pdf.set_font("Times", "", article_text_font_size)
    for i, fact in enumerate(data['did_you_know_section']):
        pdf.multi_cell(col_width, line_height_normal, txt=clean_text_for_latin1(f"- {fact}"), align='L')
    pdf.ln(section_spacing_normal)

    # Memory Prompts
    pdf.set_font("Times", "B", section_title_font_size)
    memory_prompts_title = translate_text_with_ai("Memory Prompts", current_language, client_ai)
    pdf.multi_cell(col_width, line_height_normal, txt=clean_text_for_latin1(memory_prompts_title), align='L')
    pdf.ln(1)
    pdf.set_font("Times", "", article_text_font_size)
    for prompt in data['memory_prompt_section']:
        pdf.multi_cell(col_width, line_height_normal, txt=clean_text_for_latin1(prompt), align='L')
    pdf.ln(section_spacing_normal)

    # Local History Fact
    pdf.set_font("Times", "B", section_title_font_size)
    local_history_title = translate_text_with_ai("Local History", current_language, client_ai)
    pdf.multi_cell(col_width, line_height_normal, txt=clean_text_for_latin1(local_history_title), align='L')
    pdf.ln(1)
    pdf.set_font("Times", "", article_text_font_size)
    local_history_content = clean_text_for_latin1(data['local_history_section'])
    pdf.multi_cell(col_width, line_height_normal, txt=local_history_content, align='J')
    pdf.ln(section_spacing_normal)

    # --- Page 2: About Us & Contact Info ---
    pdf.add_page()
    pdf.set_y(20) # Start further down on the second page
    pdf.set_x(left_margin_p2) # Use page 2 specific margins

    # About Us Section
    pdf.set_font("Times", "B", 16)
    about_us_title = translate_text_with_ai("About Us", current_language, client_ai)
    pdf.cell(content_width_p2, 10, txt=clean_text_for_latin1(about_us_title), ln=True, align='C')
    pdf.ln(5)

    pdf.set_font("Times", "", 12)
    about_us_content = """
    The Daily Resense Register is dedicated to bringing engaging historical content to seniors and lifelong learners. Our mission is to spark memories, encourage discussion, and provide a daily dose of fascinating facts and trivia. We believe that understanding the past enriches our present and future.
    """
    about_us_content = translate_text_with_ai(about_us_content, current_language, client_ai)
    pdf.multi_cell(content_width_p2, 7, txt=clean_text_for_latin1(about_us_content), align='J')
    pdf.ln(15)

    # Contact Information
    pdf.set_font("Times", "B", 16)
    contact_title = translate_text_with_ai("Contact Information", current_language, client_ai)
    pdf.cell(content_width_p2, 10, txt=clean_text_for_latin1(contact_title), ln=True, align='C')
    pdf.ln(5)

    pdf.set_font("Times", "", 12)
    contact_email = translate_text_with_ai("Email: info@resense.com", current_language, client_ai)
    contact_website = translate_text_with_ai("Website: www.resense.com", current_language, client_ai)
    contact_phone = translate_text_with_ai("Phone: 1-800-RESENSE", current_language, client_ai)
    
    pdf.multi_cell(content_width_p2, 7, txt=clean_text_for_latin1(contact_email), align='C')
    pdf.multi_cell(content_width_p2, 7, txt=clean_text_for_latin1(contact_website), align='C')
    pdf.multi_cell(content_width_p2, 7, txt=clean_text_for_latin1(contact_phone), align='C')
    pdf.ln(15)

    # Convert PDF to bytes
    pdf_output = pdf.output(dest='S').encode('latin-1') # 'S' returns the document as a string (bytes)
    return pdf_output

def generate_activity_pdf(activity_data, today_date_str, current_language="English", custom_masthead_text=None):
    """
    Generates a PDF for a single companion activity.
    Returns the PDF as bytes.
    """
    pdf = FPDF(unit="mm", format="A4")
    pdf.add_page()
    pdf.set_auto_page_break(True, margin=15)

    page_width = pdf.w
    left_margin = 15
    right_margin = 15
    content_width = page_width - left_margin - right_margin
    
    # Masthead
    pdf.set_y(10)
    pdf.set_x(left_margin)
    pdf.set_font("Times", "B", 24)
    # Use custom masthead text if provided, otherwise default for activities
    masthead_to_display = custom_masthead_text if custom_masthead_text and custom_masthead_text.strip() else "Companion Activity"
    masthead_to_display = clean_text_for_latin1(
        translate_text_with_ai(masthead_to_display, current_language, client_ai)
    )
    pdf.cell(content_width, 10, txt=masthead_to_display, ln=True, align='C')
    pdf.ln(5)

    pdf.set_font("Times", "", 10)
    date_text = translate_text_with_ai(f"Date: {today_date_str}", current_language, client_ai)
    pdf.cell(content_width, 5, txt=clean_text_for_latin1(date_text), ln=True, align='R')
    pdf.ln(10)

    # Activity Title
    pdf.set_font("Times", "B", 18)
    activity_title_label = translate_text_with_ai("Activity:", current_language, client_ai)
    pdf.multi_cell(content_width, 10, txt=clean_text_for_latin1(f"{activity_title_label} {activity_data['title']}"), align='L')
    pdf.ln(5)

    # Activity Type
    pdf.set_font("Times", "B", 12)
    type_label = translate_text_with_ai("Type:", current_language, client_ai)
    pdf.set_font("Times", "", 12)
    pdf.multi_cell(content_width, 7, txt=clean_text_for_latin1(f"{type_label} {activity_data['type']}"), align='L')
    pdf.ln(3)

    # Required Supplies
    pdf.set_font("Times", "B", 12)
    supplies_label = translate_text_with_ai("Required Supplies:", current_language, client_ai)
    pdf.multi_cell(content_width, 7, txt=clean_text_for_latin1(supplies_label), align='L')
    pdf.set_font("Times", "", 12)
    pdf.multi_cell(content_width, 7, txt=clean_text_for_latin1(activity_data['supplies']), align='L')
    pdf.ln(5)

    # Instructions
    pdf.set_font("Times", "B", 12)
    instructions_label = translate_text_with_ai("Instructions:", current_language, client_ai)
    pdf.multi_cell(content_width, 7, txt=clean_text_for_latin1(instructions_label), align='L')
    pdf.set_font("Times", "", 12)
    for i, step in enumerate(activity_data['instructions']):
        pdf.multi_cell(content_width, 7, txt=clean_text_for_latin1(f"{i+1}. {step}"), align='L')
    pdf.ln(5)

    # Connection to History
    pdf.set_font("Times", "B", 12)
    connection_label = translate_text_with_ai("Connection to History:", current_language, client_ai)
    pdf.multi_cell(content_width, 7, txt=clean_text_for_latin1(connection_label), align='L')
    pdf.set_font("Times", "", 12)
    pdf.multi_cell(content_width, 7, txt=clean_text_for_latin1(activity_data['connection']), align='J')
    pdf.ln(10)

    pdf_output = pdf.output(dest='S').encode('latin-1')
    return pdf_output


# --- Page Navigation Functions ---
def set_page(page_name):
    st.session_state['current_page'] = page_name
    st.rerun()

# --- Login Page ---
def show_login_page():
    st.title("Welcome to The Daily Resense Register")
    st.write("Please log in or register to continue.")

    tab_login, tab_register = st.tabs(["Log In", "Register"])

    with tab_login:
        with st.form("login_form"):
            st.subheader("Log In")
            username = st.text_input("Username", key="login_username_input")
            password = st.text_input("Password", type="password", key="login_password_input")
            submitted = st.form_submit_button("Log In")

            if submitted:
                users = get_users_from_sheet()
                if username in users and users[username] == password:
                    st.session_state['is_authenticated'] = True
                    st.session_state['logged_in_username'] = username
                    st.session_state['user_info'] = {"username": username} # Set user_info here
                    log_event("login", username)
                    st.success("Logged in successfully!")
                    set_page('main_app')
                else:
                    st.error("Invalid username or password.")

    with tab_register:
        with st.form("register_form"):
            st.subheader("Register")
            new_username = st.text_input("New Username", key="register_username_input")
            new_password = st.text_input("New Password", type="password", key="register_password_input")
            confirm_password = st.text_input("Confirm Password", type="password", key="register_confirm_password_input")
            new_email = st.text_input("Email (Optional)", key="register_email_input")
            register_submitted = st.form_submit_button("Register")

            if register_submitted:
                users = get_users_from_sheet()
                if new_username in users:
                    st.error("Username already exists. Please choose a different one.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                elif not new_username or not new_password:
                    st.error("Username and password cannot be empty.")
                else:
                    if save_new_user_to_sheet(new_username, new_password, new_email):
                        log_event("register", new_username)
                        st.success("Registration successful! You can now log in.")
                        # Optionally auto-log in the user after registration
                        st.session_state['is_authenticated'] = True
                        st.session_state['logged_in_username'] = new_username
                        st.session_state['user_info'] = {"username": new_username} # Set user_info here
                        set_page('main_app')


# --- Main Application Page ---
def show_main_app_page():
    st.header(translate_text_with_ai("Today's Historical Highlights", st.session_state['preferred_language'], client_ai))
    st.markdown(
        f"*{translate_text_with_ai('Logged in as:', st.session_state['preferred_language'], client_ai)} **{st.session_state['logged_in_username']}***"
    )

    today = date.today()
    if st.session_state['last_fetched_date'] != today:
        st.session_state['raw_fetched_data'] = _INITIAL_EMPTY_DATA.copy() # Reset data
        st.session_state['daily_data'] = None # Clear translated data
        st.session_state['last_fetched_date'] = today
        st.session_state['trivia_question_states'] = {} # Reset trivia state
        st.session_state['hints_remaining'] = 3
        st.session_state['current_trivia_score'] = 0
        st.session_state['total_possible_daily_trivia_score'] = 0
        st.session_state['score_logged_today'] = False # Allow score logging for new day

    # --- Content Generation ---
    with st.spinner(translate_text_with_ai("Fetching today's history...", st.session_state['preferred_language'], client_ai)):
        if st.session_state['raw_fetched_data'] == _INITIAL_EMPTY_DATA and st.session_state['last_fetched_date'] == today:
            st.session_state['raw_fetched_data'] = get_this_day_in_history_facts(
                today.day, today.month, st.session_state['user_info'], client_ai,
                difficulty=st.session_state['difficulty'],
                local_city=st.session_state['local_city'],
                local_state_country=st.session_state['local_state_country']
            )
            # After fetching, translate the raw data once
            st.session_state['daily_data'] = translate_content(st.session_state['raw_fetched_data'], st.session_state['preferred_language'], client_ai)
        elif st.session_state['daily_data'] is None or st.session_state['daily_data']['event_article'] == _INITIAL_EMPTY_DATA['event_article'] or st.session_state['preferred_language'] != st.session_state.get('last_display_language', 'English'):
            # If language changed or data is still default, re-translate raw data
            st.session_state['daily_data'] = translate_content(st.session_state['raw_fetched_data'], st.session_state['preferred_language'], client_ai)
            st.session_state['last_display_language'] = st.session_state['preferred_language'] # Update last_display_language
    
    daily_data = st.session_state['daily_data']
    
    # --- Display Content ---
    st.subheader(translate_text_with_ai("Historical Event", st.session_state['preferred_language'], client_ai))
    st.write(daily_data['event_article'])

    st.subheader(translate_text_with_ai("Born On This Day", st.session_state['preferred_language'], client_ai))
    st.write(daily_data['born_article'])

    st.subheader(translate_text_with_ai("Fun Fact", st.session_state['preferred_language'], client_ai))
    st.write(daily_data['fun_fact_section'])

    st.subheader(translate_text_with_ai("Did You Know?", st.session_state['preferred_language'], client_ai))
    for fact in daily_data['did_you_know_section']:
        st.write(f"- {fact}")

    st.subheader(translate_text_with_ai("Memory Prompts", st.session_state['preferred_language'], client_ai))
    for prompt in daily_data['memory_prompt_section']:
        st.write(f"- {prompt}")

    st.subheader(translate_text_with_ai("Local History", st.session_state['preferred_language'], client_ai))
    st.write(daily_data['local_history_section'])

    # --- PDF Download ---
    pdf_bytes = generate_full_history_pdf(
        daily_data,
        today.strftime("%B %d, %Y"),
        st.session_state['user_info'],
        st.session_state['preferred_language'],
        st.session_state['custom_masthead_text']
    )
    pdf_filename = f"This_Day_in_History_{today.strftime('%Y-%m-%d')}.pdf"

    st.download_button(
        label=translate_text_with_ai("Download Today's PDF", st.session_state['preferred_language'], client_ai),
        data=pdf_bytes,
        file_name=pdf_filename,
        mime="application/pdf",
        on_click=lambda: log_pdf_download(st.session_state['logged_in_username'], pdf_filename, today)
    )
    if st.session_state['last_download_status'] == 'success':
        st.success(translate_text_with_ai("PDF download logged!", st.session_state['preferred_language'], client_ai))
        st.session_state['last_download_status'] = None # Clear status after display
    elif st.session_state['last_download_status'] == 'failure':
        st.error(translate_text_with_ai("Failed to log PDF download.", st.session_state['preferred_language'], client_ai))
        st.session_state['last_download_status'] = None # Clear status after display


    st.markdown("---") # Separator

    # --- Trivia Button ---
    st.button(translate_text_with_ai("🧠 Play Trivia!", st.session_state['preferred_language'], client_ai), on_click=lambda: set_page('trivia_page'))


# --- Trivia Page ---
def show_trivia_page():
    st.header(translate_text_with_ai("Daily Trivia Challenge!", st.session_state['preferred_language'], client_ai))
    st.markdown(
        f"*{translate_text_with_ai('Logged in as:', st.session_state['preferred_language'], client_ai)} **{st.session_state['logged_in_username']}***"
    )

    daily_data = st.session_state.get('daily_data', _INITIAL_EMPTY_DATA)
    trivia_questions = daily_data['trivia_section']

    if not trivia_questions:
        st.warning(translate_text_with_ai("No trivia questions available for today. Please go back to the main app and ensure content is fetched.", st.session_state['preferred_language'], client_ai))
        if st.button(translate_text_with_ai("⬅️ Back to Main App", st.session_state['preferred_language'], client_ai)):
            set_page('main_app')
        return

    st.subheader(translate_text_with_ai("Your Current Score:", st.session_state['preferred_language'], client_ai) + f" {st.session_state['current_trivia_score']}/{st.session_state['total_possible_daily_trivia_score']}")
    st.write(translate_text_with_ai(f"Hints Remaining: {st.session_state['hints_remaining']}", st.session_state['preferred_language'], client_ai))

    for i, q_data in enumerate(trivia_questions):
        q_key = f"q_{i}"
        
        # Initialize state for this question if it doesn't exist
        if q_key not in st.session_state['trivia_question_states']:
            st.session_state['trivia_question_states'][q_key] = {
                'user_answer': '',
                'is_correct': False,
                'feedback': '',
                'hint_revealed': False,
                'attempts': 0,
                'out_of_chances': False,
                'points_earned': 0,
                'related_article_content': None
            }

        question_state = st.session_state['trivia_question_states'][q_key]
        
        st.markdown(f"**{translate_text_with_ai(f'Question {i+1}:', st.session_state['preferred_language'], client_ai)}** {q_data['question']}")
        
        # Only allow input if not already correct or out of chances
        if not question_state['is_correct'] and not question_state['out_of_chances']:
            user_answer = st.text_input(translate_text_with_ai("Your Answer:", st.session_state['preferred_language'], client_ai), 
                                         value=question_state['user_answer'], 
                                         key=f"answer_input_{q_key}")
            
            col_check, col_hint = st.columns([1, 1])
            with col_check:
                if st.button(translate_text_with_ai("Check Answer", st.session_state['preferred_language'], client_ai), key=f"check_btn_{q_key}"):
                    question_state['user_answer'] = user_answer # Update session state with the latest answer
                    question_state['attempts'] += 1

                    if user_answer.strip().lower() == q_data['answer'].strip().lower():
                        question_state['is_correct'] = True
                        question_state['feedback'] = translate_text_with_ai("🎉 Correct!", st.session_state['preferred_language'], client_ai)
                        if question_state['points_earned'] == 0: # Only add points once
                            st.session_state['current_trivia_score'] += 1
                            st.session_state['total_possible_daily_trivia_score'] += 1 # Every question is potentially 1 point
                            question_state['points_earned'] = 1
                    else:
                        is_partially_correct = check_partial_correctness_with_ai(user_answer, q_data['answer'], client_ai)
                        if is_partially_correct:
                            question_state['feedback'] = translate_text_with_ai("👍 Partially correct! Consider the full answer.", st.session_state['preferred_language'], client_ai)
                        else:
                            question_state['feedback'] = translate_text_with_ai("❌ Incorrect. Try again!", st.session_state['preferred_language'], client_ai)
                            if question_state['attempts'] >= 2: # Allow 2 attempts
                                question_state['out_of_chances'] = True
                                question_state['feedback'] += " " + translate_text_with_ai(f"The correct answer was: {q_data['answer']}", st.session_state['preferred_language'], client_ai)
                                st.session_state['total_possible_daily_trivia_score'] += 1 # Mark as a question attempted, even if wrong
                    st.rerun() # Rerun to update feedback/state immediately

            with col_hint:
                if st.session_state['hints_remaining'] > 0 and not question_state['hint_revealed'] and not question_state['is_correct'] and not question_state['out_of_chances']:
                    if st.button(translate_text_with_ai("Show Hint", st.session_state['preferred_language'], client_ai), key=f"hint_btn_{q_key}"):
                        question_state['hint_revealed'] = True
                        st.session_state['hints_remaining'] -= 1
                        st.info(clean_text_for_latin1(translate_text_with_ai(f"Hint: {q_data['hint']}", st.session_state['preferred_language'], client_ai)))
                        st.rerun() # Rerun to update hint display

        # Display feedback and hint if revealed
        if question_state['feedback']:
            st.write(question_state['feedback'])
        if question_state['hint_revealed'] and not question_state['is_correct']:
            st.info(clean_text_for_latin1(translate_text_with_ai(f"Hint: {q_data['hint']}", st.session_state['preferred_language'], client_ai)))
        
        # Show related article after answer attempts are exhausted or correct
        if question_state['is_correct'] or question_state['out_of_chances']:
            if question_state['related_article_content'] is None:
                with st.spinner(translate_text_with_ai("Generating explanation...", st.session_state['preferred_language'], client_ai)):
                    question_state['related_article_content'] = generate_related_trivia_article(q_data['question'], q_data['answer'], client_ai)
            st.markdown(translate_text_with_ai("**Explanation:**", st.session_state['preferred_language'], client_ai))
            st.write(clean_text_for_latin1(question_state['related_article_content']))
        
        st.markdown("---") # Separator between questions

    # Log score once all questions are answered or user navigates away
    if all(s['is_correct'] or s['out_of_chances'] for s in st.session_state['trivia_question_states'].values()) and not st.session_state['score_logged_today']:
        log_trivia_score(st.session_state['logged_in_username'], st.session_state['current_trivia_score'])
        st.session_state['score_logged_today'] = True
        st.success(translate_text_with_ai("Your final score has been logged!", st.session_state['preferred_language'], client_ai))
        st.balloons()
    
    st.button(translate_text_with_ai("⬅️ Back to Main App", st.session_state['preferred_language'], client_ai), on_click=lambda: set_page('main_app'))
    st.button(translate_text_with_ai("🏆 View Leaderboard", st.session_state['preferred_language'], client_ai), on_click=lambda: set_page('leaderboard_page'))

# --- Leaderboard Page ---
def show_leaderboard_page():
    st.header(translate_text_with_ai("Leaderboard", st.session_state['preferred_language'], client_ai))
    st.markdown(
        f"*{translate_text_with_ai('Logged in as:', st.session_state['preferred_language'], client_ai)} **{st.session_state['logged_in_username']}***"
    )

    leaderboard_data = get_leaderboard_data()

    if leaderboard_data:
        st.subheader(translate_text_with_ai("Top Scores:", st.session_state['preferred_language'], client_ai))
        for i, (username, score) in enumerate(leaderboard_data):
            st.write(f"{i+1}. {username}: {score} {translate_text_with_ai('points', st.session_state['preferred_language'], client_ai)}")
    else:
        st.info(translate_text_with_ai("No scores logged yet. Be the first to play trivia!", st.session_state['preferred_language'], client_ai))

    if st.button(translate_text_with_ai("⬅️ Back to Trivia", st.session_state['preferred_language'], client_ai)):
        set_page('trivia_page')
    if st.button(translate_text_with_ai("🏡 Back to Main App", st.session_state['preferred_language'], client_ai)):
        set_page('main_app')

# --- Weekly Planner Page ---
def show_weekly_planner_page():
    st.header(translate_text_with_ai("Weekly Content Planner", st.session_state['preferred_language'], client_ai))
    st.markdown(
        f"*{translate_text_with_ai('Logged in as:', st.session_state['preferred_language'], client_ai)} **{st.session_state['logged_in_username']}***"
    )

    st.write(translate_text_with_ai("Select a start date to generate 'This Day in History' content and companion activities for a full week.", st.session_state['preferred_language'], client_ai))

    start_date = st.date_input(
        translate_text_with_ai("Select Start Date", st.session_state['preferred_language'], client_ai),
        value=date.today(),
        min_value=date(1900, 1, 1), # Arbitrary minimum date
        max_value=date(2099, 12, 31), # Arbitrary maximum date
        key='weekly_planner_start_date'
    )

    if st.button(translate_text_with_ai("Generate Weekly Content", st.session_state['preferred_language'], client_ai), key='generate_weekly_btn'):
        generated_pdfs = []
        zip_file_name = f"Weekly_History_and_Activities_{start_date.strftime('%Y-%m-%d')}.zip"
        
        with st.spinner(translate_text_with_ai("Generating weekly content and PDFs (this may take a few minutes)...", st.session_state['preferred_language'], client_ai)):
            current_date = start_date
            for i in range(7):
                day_data_raw = get_this_day_in_history_facts(
                    current_date.day, 
                    current_date.month, 
                    st.session_state['user_info'], 
                    client_ai,
                    difficulty=st.session_state['difficulty'],
                    local_city=st.session_state['local_city'],
                    local_state_country=st.session_state['local_state_country']
                )
                
                # Translate the raw data to the preferred language
                day_data_translated = translate_content(day_data_raw, st.session_state['preferred_language'], client_ai)

                # Generate main history PDF
                history_pdf_bytes = generate_full_history_pdf(
                    day_data_translated,
                    current_date.strftime("%B %d, %Y"),
                    st.session_state['user_info'],
                    st.session_state['preferred_language'],
                    st.session_state['custom_masthead_text']
                )
                generated_pdfs.append({
                    'name': f"History_Content_{current_date.strftime('%Y-%m-%d')}.pdf",
                    'data': history_pdf_bytes
                })

                # Generate companion activity
                activity_data = generate_companion_activities(
                    day_data_raw['event_article'], # Use raw event article for activity generation prompt
                    day_data_raw['fun_fact_section'], # Use raw fun fact for activity generation prompt
                    st.session_state['preferred_language'], # Pass preferred language for activity response translation
                    client_ai
                )

                activity_pdf_bytes = generate_activity_pdf(
                    activity_data,
                    current_date.strftime("%B %d, %Y"),
                    st.session_state['preferred_language'],
                    st.session_state['custom_masthead_text']
                )
                generated_pdfs.append({
                    'name': f"Activity_Sheet_{current_date.strftime('%Y-%m-%d')}.pdf",
                    'data': activity_pdf_bytes
                })
                
                current_date += timedelta(days=1)

        # Create ZIP file in-memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for pdf_item in generated_pdfs:
                zf.writestr(pdf_item['name'], pdf_item['data'])
        zip_buffer.seek(0) # Rewind the buffer to the beginning

        st.success(translate_text_with_ai("Weekly content generated successfully!", st.session_state['preferred_language'], client_ai))
        
        st.download_button(
            label=translate_text_with_ai("Download Weekly PDFs (ZIP)", st.session_state['preferred_language'], client_ai),
            data=zip_buffer,
            file_name=zip_file_name,
            mime="application/zip",
            on_click=lambda: log_pdf_download(st.session_state['logged_in_username'], zip_file_name, start_date) # Log the ZIP download
        )
    
    st.markdown("---")
    st.button(translate_text_with_ai("🏡 Back to Main App", st.session_state['preferred_language'], client_ai), on_click=lambda: set_page('main_app'))


# --- Sidebar Navigation ---
with st.sidebar:
    st.image("https://resense.com/wp-content/uploads/2023/12/Resense-Logo-White.png", width=200) # Assuming logo URL is static
    st.title("Navigation")
    
    if st.session_state['is_authenticated']:
        st.button(translate_text_with_ai("📰 Daily History", st.session_state['preferred_language'], client_ai), on_click=lambda: set_page('main_app'), key="sidebar_main_app_btn")
        st.button(translate_text_with_ai("🧠 Daily Trivia", st.session_state['preferred_language'], client_ai), on_click=lambda: set_page('trivia_page'), key="sidebar_trivia_btn")
        st.button(translate_text_with_ai("🏆 Leaderboard", st.session_state['preferred_language'], client_ai), on_click=lambda: set_page('leaderboard_page'), key="sidebar_leaderboard_btn")
        
        # New Weekly Planner navigation button
        st.button(translate_text_with_ai("📅 Weekly Planner", st.session_state['preferred_language'], client_ai), on_click=lambda: set_page('weekly_planner_page'), key="sidebar_weekly_planner_btn")

        st.markdown("---")
        st.subheader(translate_text_with_ai("Settings", st.session_state['preferred_language'], client_ai))
        
        # Difficulty Setting
        st.session_state['difficulty'] = st.sidebar.selectbox(
            translate_text_with_ai("Difficulty", st.session_state['preferred_language'], client_ai),
            options=['Easy', 'Medium', 'Hard'],
            index=['Easy', 'Medium', 'Hard'].index(st.session_state['difficulty']),
            key='sidebar_difficulty_select',
            help=translate_text_with_ai("Adjust the difficulty of trivia questions.", st.session_state['preferred_language'], client_ai)
        )

        # Local History Input
        with st.expander(translate_text_with_ai("Local History Settings", st.session_state['preferred_language'], client_ai)):
            st.session_state['local_city'] = st.text_input(
                translate_text_with_ai("Your City", st.session_state['preferred_language'], client_ai),
                value=st.session_state['local_city'],
                key='sidebar_local_city'
            )
            st.session_state['local_state_country'] = st.text_input(
                translate_text_with_ai("Your State/Country", st.session_state['preferred_language'], client_ai),
                value=st.session_state['local_state_country'],
                key='sidebar_local_state_country'
            )
            st.info(translate_text_with_ai("Provide city and state/country for personalized local history facts.", st.session_state['preferred_language'], client_ai))

        # Custom Masthead Text Input for PDF
        st.session_state['custom_masthead_text'] = st.text_input(
            translate_text_with_ai("Custom PDF Masthead", st.session_state['preferred_language'], client_ai),
            value=st.session_state['custom_masthead_text'],
            placeholder=translate_text_with_ai("e.g., 'Maplewood Activity Center News'", st.session_state['preferred_language'], client_ai),
            key='sidebar_masthead_text',
            help=translate_text_with_ai("Enter text to appear at the top of the generated PDFs.", st.session_state['preferred_language'], client_ai)
        )

        # Language Selection
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

# --- Page Rendering based on current_page ---
if st.session_state['current_page'] == 'main_app':
    if st.session_state['is_authenticated']:
        show_main_app_page()
    else:
        show_login_page()
elif st.session_state['current_page'] == 'trivia_page':
    if st.session_state['is_authenticated']:
        show_trivia_page()
    else:
        show_login_page()
elif st.session_state['current_page'] == 'leaderboard_page':
    if st.session_state['is_authenticated']:
        show_leaderboard_page()
    else:
        show_login_page()
elif st.session_state['current_page'] == 'weekly_planner_page': # New page
    if st.session_state['is_authenticated']:
        show_weekly_planner_page()
    else:
        show_login_page()
# Default to main_app if current_page is somehow not set to a valid page
else:
    st.session_state['current_page'] = 'main_app'
    if st.session_state['is_authenticated']:
        show_main_app_page()
    else:
        show_login_page()
