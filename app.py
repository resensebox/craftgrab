import streamlit as st
from openai import OpenAI
from datetime import datetime, date, timedelta
from fpdf import FPDF
import re
import json
import base64 # Import base64 for encoding PDF content
import time # Import time for st.spinner delays
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gtts import gTTS
import qrcode
from io import BytesIO
from PIL import Image # Needed by qrcode[pil]
import zipfile # For creating ZIP files

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
    'local_history_section': "No local history data available. Please try again.",
    'companion_activities': "No companion activities available. Please try again." # NEW: Default for companion activities
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

# NEW: Session states for new features
if 'toggle_weekly_planner' not in st.session_state:
    st.session_state['toggle_weekly_planner'] = False
if 'toggle_group_mode' not in st.session_state:
    st.session_state['toggle_group_mode'] = False
if 'toggle_audio_qr' not in st.session_state:
    st.session_state['toggle_audio_qr'] = False
if 'toggle_companion_activities' not in st.session_state:
    st.session_state['toggle_companion_activities'] = False
if 'toggle_memory_journal' not in st.session_state:
    st.session_state['toggle_memory_journal'] = False
if 'toggle_large_print_pdf' not in st.session_state:
    st.session_state['toggle_large_print_pdf'] = False
if 'toggle_offline_pack' not in st.session_state:
    st.session_state['toggle_offline_pack'] = False
if 'toggle_autopilot_email' not in st.session_state:
    st.session_state['toggle_autopilot_email'] = False

# Group Mode Specific States
if 'group_mode_active' not in st.session_state:
    st.session_state['group_mode_active'] = False # This will be set by the toggle_group_mode checkbox
if 'current_trivia_slide' not in st.session_state:
    st.session_state['current_trivia_slide'] = 0
if 'reveal_answer' not in st.session_state:
    st.session_state['reveal_answer'] = False
if 'resident_scores' not in st.session_state:
    st.session_state['resident_scores'] = [{'name': f'Resident {i+1}', 'score': 0} for i in range(5)] # Default 5 residents

# Memory Journal Specific States
if 'current_memory_entry_text' not in st.session_state:
    st.session_state['current_memory_entry_text'] = ""
if 'current_resident_name_journal' not in st.session_state:
    st.session_state['current_resident_name_journal'] = ""

# Autopilot Email States
if 'email_recipient' not in st.session_state:
    st.session_state['email_recipient'] = ""
if 'email_frequency' not in st.session_state:
    st.session_state['email_frequency'] = "Daily"


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

# NEW: Functions for Memory Journal Logging
def log_memory_entry(username, resident_name, memory_text, entry_date):
    """Logs a memory journal entry to a 'MemoryJournal' worksheet."""
    try:
        sheet = gs_client.open_by_key("15LXglm49XBJBzeavaHvhgQn3SakqLGeRV80PxPHQfZ4")
        try:
            ws = sheet.worksheet("MemoryJournal")
        except gspread.exceptions.WorksheetNotFound:
            ws = sheet.add_worksheet(title="MemoryJournal", rows="100", cols="5") # Added 'EntryDate' column
            ws.append_row(["Timestamp", "Username", "ResidentName", "EntryDate", "MemoryText"])
        
        ws.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            username,
            resident_name,
            entry_date.strftime("%Y-%m-%d"),
            memory_text
        ])
        return True
    except Exception as e:
        st.warning(f"⚠️ Could not log memory entry: {e}")
        return False

def get_memory_entries(username):
    """Retrieves all memory journal entries for a given username."""
    try:
        sheet = gs_client.open_by_key("15LXglm49XBJBzeavaHvhgQn3SakqLGeRV80PxPHQfZ4")
        try:
            ws = sheet.worksheet("MemoryJournal")
            all_records = ws.get_all_records(head=1)
            # Filter by username to only get current user's entries
            return [rec for rec in all_records if rec.get('Username') == username]
        except gspread.exceptions.WorksheetNotFound:
            return []
    except Exception as e:
        st.error(f"❌ Error retrieving memory entries: {e}")
        return []


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

# NEW: Function to generate companion activities
def generate_companion_activities(article_content, _ai_client, current_language="English"):
    """
    Generates related craft, snack, and reminiscence activities based on an article.
    """
    prompt = f"""
    Based on the following historical article, suggest ONE related craft activity, ONE related snack idea, and ONE related reminiscence activity.
    For each, provide:
    - Activity Name
    - Materials/Ingredients (if applicable)
    - Simple Directions (3-5 steps)

    Format your response clearly with headings for each activity type (e.g., "Craft Activity:", "Snack Idea:", "Reminiscence Activity:").
    Translate the output to {current_language}.

    Historical Article:
    ---
    {article_content}
    ---
    """
    try:
        response = _ai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.7 # More creative
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error generating companion activities: {e}")
        return "Could not generate companion activities."

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
    translated_data['companion_activities'] = translate_text_with_ai(data['companion_activities'], target_language, _ai_client) # NEW: Translate companion activities

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

    # NEW: Add companion activities request to the prompt
    companion_activity_request = ""
    if st.session_state.get('toggle_companion_activities', False):
        companion_activity_request = """
    8. Companion Activities: Based on the "Event Article", suggest ONE related craft activity, ONE related snack idea, and ONE related reminiscence activity. For each, provide:
       - Activity Name
       - Materials/Ingredients (if applicable)
       - Simple Directions (3-5 steps).
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
    {companion_activity_request}

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
        
        # NEW: Regex for Companion Activities
        companion_activities_match = re.search(r"8\. Companion Activities:\s*(.*?)(?=\n\Z|$)", content, re.DOTALL)


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
            # Check if there's an 8. Companion Activities heading, if so, stop before it
            temp_local_history_content = local_history_match.group(1).strip()
            companion_activities_header_pos = temp_local_history_content.find("8. Companion Activities:")
            if companion_activities_header_pos != -1:
                local_history_fact = temp_local_history_content[:companion_activities_header_pos].strip()
            else:
                local_history_fact = temp_local_history_content
        
        # NEW: Extract Companion Activities
        companion_activities_content = "No companion activities available."
        if companion_activities_match:
            companion_activities_content = companion_activities_match.group(1).strip()


        return {
            'event_article': event_article,
            'born_article': born_article,
            'fun_fact_section': fun_fact_section,
            'trivia_section': trivia_questions, # Now a list of dicts {question, answer, hint}
            'did_you_know_section': did_you_know_lines,
            'memory_prompt_section': memory_prompts_list, # Now a list of prompts
            'local_history_section': local_history_fact, # New local history fact
            'companion_activities': companion_activities_content # NEW: Companion activities
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
            'local_history_section': "Could not fetch local history for your area. Please check your location settings or try again.",
            'companion_activities': "No companion activities available." # NEW: Default for companion activities
        }

# NEW: Function to generate audio bytes
def generate_audio_bytes(text, lang='en'):
    """Generates audio bytes for a given text using gTTS."""
    try:
        # Ensure text is a string before passing to gTTS
        text_str = str(text) if text is not None else ""
        if not text_str.strip(): # If text is empty or just whitespace
            return None # No audio to generate

        tts = gTTS(text=text_str, lang=lang, slow=False)
        audio_bytes_io = BytesIO()
        tts.write_to_fp(audio_bytes_io)
        audio_bytes_io.seek(0)
        return audio_bytes_io
    except Exception as e:
        print(f"Error generating audio: {e}") # Use print for backend errors
        return None

# NEW: Function to generate QR code image bytes
def generate_qr_code_image_bytes(data_url, box_size=3, border=2):
    """Generates QR code image bytes (PNG) from a data URL."""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=box_size,
            border=border,
        )
        qr.add_data(data_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
        
        img_bytes_io = BytesIO()
        img.save(img_bytes_io, format="PNG")
        img_bytes_io.seek(0)
        return img_bytes_io
    except Exception as e:
        print(f"Error generating QR code: {e}")
        return None


def generate_full_history_pdf(data, today_date_str, user_info, current_language="English", custom_masthead_text=None, large_print_mode=False, include_audio_qr=False): # Added new parameters
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
    if large_print_mode:
        title_font_size = 42 # Increased for large print
        date_font_size = 14 # Increased for large print
        section_title_font_size = 18 # Increased for large print
        article_text_font_size = 14 # Increased for large print
        line_height_multiplier = 1.6 # Increased line spacing
        section_spacing_multiplier = 2 # More spacing between sections
    else:
        title_font_size = 36
        date_font_size = 10
        section_title_font_size = 12
        article_text_font_size = 10
        line_height_multiplier = 1.2 # Normal line spacing
        section_spacing_multiplier = 1 # Normal spacing

    line_height = article_text_font_size * line_height_multiplier
    section_spacing = 5 * section_spacing_multiplier

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
    pdf.cell(0, 15 * line_height_multiplier, clean_text_for_latin1(translate_text_with_ai(masthead_to_display, current_language, client_ai)), align='C')
    pdf.ln(15 * line_height_multiplier)

    # Separator line
    pdf.set_line_width(0.5)
    pdf.line(left_margin, pdf.get_y(), page_width - right_margin, pdf.get_y())
    pdf.ln(8 * line_height_multiplier)

    pdf.set_font("Arial", "", date_font_size)
    pdf.cell(0, 5 * line_height_multiplier, today_date_str.upper(), align='C') # Date below the title
    pdf.ln(15 * line_height_multiplier)

    pdf.set_line_width(0.2) # Thinner line for content sections
    pdf.line(left_margin, pdf.get_y(), page_width - right_margin, pdf.get_y())
    pdf.ln(8 * line_height_multiplier)

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

    # On This Date (Event Article)
    pdf.set_font("Arial", "B", section_title_font_size)
    pdf.multi_cell(col_width, line_height, clean_text_for_latin1(translate_text_with_ai("On This Date", current_language, client_ai)))
    current_y_col1 += line_height # Update Y after title
    pdf.set_font("Arial", "", article_text_font_size) # Ensure font is not bold for article text
    # Translate content explicitly before adding to PDF
    translated_event_article = translate_text_with_ai(data.get('event_article', ''), current_language, client_ai)
    pdf.multi_cell(col_width, line_height, translated_event_article)
    current_y_col1 = pdf.get_y() + section_spacing # Update Y and add spacing
    pdf.set_y(current_y_col1) # Ensure position is updated

    # NEW: Audio QR for Event Article
    if include_audio_qr:
        event_article_audio_bytes = generate_audio_bytes(data.get('event_article', ''), lang=current_language.lower()[:2])
        if event_article_audio_bytes:
            # Embed audio bytes directly as data URI (large file warning)
            audio_base64 = base64.b64encode(event_article_audio_bytes.getvalue()).decode('latin-1')
            audio_data_url = f"data:audio/mp3;base64,{audio_base64}"
            
            event_article_qr_image_bytes = generate_qr_code_image_bytes(audio_data_url, box_size=max(1, int(3 * (article_text_font_size / 10))), border=2)
            if event_article_qr_image_bytes:
                # Add QR code to the right of the article or below it
                qr_size = 25 # mm
                pdf.image(event_article_qr_image_bytes, x=left_margin + col_width - qr_size - 5, y=current_y_col1, w=qr_size, h=qr_size, type='PNG')
                pdf.set_xy(left_margin + col_width - qr_size - 5, current_y_col1 + qr_size + 2) # Position text below QR
                pdf.set_font("Arial", "", max(8, article_text_font_size - 4))
                pdf.multi_cell(qr_size, max(4, line_height/2), clean_text_for_latin1(translate_text_with_ai("Scan to Hear Article", current_language, client_ai)), align='C')
                # Adjust current_y_col1 to account for QR code
                current_y_col1 = max(current_y_col1, pdf.get_y()) + section_spacing
                pdf.set_y(current_y_col1)


    # Fun Fact
    pdf.set_font("Arial", "B", section_title_font_size)
    pdf.multi_cell(col_width, line_height, clean_text_for_latin1(translate_text_with_ai("Fun Fact:", current_language, client_ai))) # Translated
    current_y_col1 += line_height
    pdf.set_font("Arial", "", article_text_font_size) # Ensure font is not bold for article text
    # Translate content explicitly before adding to PDF
    translated_fun_fact = translate_text_with_ai(data.get('fun_fact_section', ''), current_language, client_ai)
    pdf.multi_cell(col_width, line_height, translated_fun_fact)
    current_y_col1 = pdf.get_y() + section_spacing # Update Y and add spacing
    pdf.set_y(current_y_col1)

    current_y_col1 += section_spacing # Spacing after content section
    pdf.set_y(current_y_col1)


    # Column 2 (Right Column)
    pdf.set_xy(page_width / 2 + 5, current_y_col2) # X start for right column, Y at same level as left
    pdf.set_right_margin(right_margin)
    pdf.set_left_margin(page_width / 2 + 5) # Left margin for right column

    # Quote of the Day
    pdf.set_font("Arial", "B", section_title_font_size)
    pdf.multi_cell(col_width, line_height, clean_text_for_latin1(translate_text_with_ai("Quote of the Day", current_language, client_ai)), align='C') # Translated
    current_y_col2 += line_height
    quote_text = clean_text_for_latin1(translate_text_with_ai('"The only way to do great work is to love what you do."', current_language, client_ai)) # Placeholder quote
    quote_author = clean_text_for_latin1(translate_text_with_ai("- Unknown", current_language, client_ai)) # Placeholder author
    pdf.set_font("Times", "I", article_text_font_size) # Italic for quote
    pdf.multi_cell(col_width, line_height, quote_text, align='C')
    pdf.multi_cell(col_width, line_height, quote_author, align='C')
    current_y_col2 = pdf.get_y() + section_spacing # Update Y and add spacing
    pdf.set_y(current_y_col2)

    # Happy Birthday! (Born on this Day Article)
    pdf.set_font("Arial", "B", section_title_font_size)
    pdf.multi_cell(col_width, line_height, clean_text_for_latin1(translate_text_with_ai("Happy Birthday!", current_language, client_ai))) # Translated
    current_y_col2 += line_height
    pdf.set_font("Arial", "", article_text_font_size) # Ensure font is not bold for article text
    # Translate content explicitly before adding to PDF
    translated_born_article = translate_text_with_ai(data.get('born_article', ''), current_language, client_ai)
    pdf.multi_cell(col_width, line_height, translated_born_article)
    current_y_col2 = pdf.get_y() + section_spacing # Update Y and add spacing
    pdf.set_y(current_y_col2)

    # Did You Know?
    if data.get('did_you_know_section'): # Use .get() to check if 'did_you_know_section' key exists and is not empty/None
        pdf.set_font("Arial", "B", section_title_font_size)
        pdf.multi_cell(col_width, line_height, clean_text_for_latin1(translate_text_with_ai("Did You Know?", current_language, client_ai))) # Translated
        current_y_col2 += line_height
        pdf.set_font("Arial", "", article_text_font_size)
        for item in data['did_you_know_section']:
            # Translate each item explicitly before adding to PDF
            translated_item = translate_text_with_ai(item if item is not None else '', current_language, client_ai)
            pdf.multi_cell(col_width, line_height, f"- {translated_item}")
            current_y_col2 = pdf.get_y() # Update Y after each fact line
        current_y_col2 += section_spacing # Spacing after section
        pdf.set_y(current_y_col2)

    # Memory Prompt?
    if data.get('memory_prompt_section'): # Use .get() to check if key exists and is not empty/None
        pdf.set_font("Arial", "B", section_title_font_size)
        pdf.multi_cell(col_width, line_height, clean_text_for_latin1(translate_text_with_ai("Memory Prompt?", current_language, client_ai))) # Translated
        current_y_col2 += line_height
        pdf.set_font("Arial", "", article_text_font_size)
        # Iterate and display up to the first 3 memory prompts for PDF
        for prompt_text in data['memory_prompt_section'][:3]: # Limit to first 3 prompts
            # Translate each prompt explicitly before adding to PDF
            translated_prompt = translate_text_with_ai(prompt_text if prompt_text is not None else '', current_language, client_ai)
            pdf.multi_cell(col_width, line_height, translated_prompt)
            pdf.ln(2 * line_height_multiplier) # Small line break between prompts
            current_y_col2 = pdf.get_y() # Update Y after each prompt line
        current_y_col2 += section_spacing # Spacing after section
        pdf.set_y(current_y_col2)

    # Local History (if available) - This section will now rely on auto_page_break
    # It will only be displayed if it's not one of the "not found" messages.
    local_history_content = data.get('local_history_section', '')
    if local_history_content and \
       not local_history_content.startswith("Could not generate local history fact."): # Simplified check
        pdf.set_font("Arial", "B", section_title_font_size)
        
        # Calculate available space in each column.
        current_y_after_main_content = max(current_y_col1, current_y_col2) # Get the lowest point of content in either column
        
        # Temporarily save current margins and x to restore after local history section
        original_left_margin = pdf.l_margin
        original_right_margin = pdf.r_margin
        original_x = pdf.x

        # Reset margins for single column local history display
        pdf.set_left_margin(left_margin)
        pdf.set_right_margin(right_margin)
        pdf.set_x(left_margin) # Reset X to left margin

        # Set Y to the max of current column Ys, then add some spacing
        pdf.set_y(current_y_after_main_content + section_spacing) 

        pdf.multi_cell(content_width, line_height, clean_text_for_latin1(translate_text_with_ai("Local History:", current_language, client_ai))) # Translated
        pdf.set_font("Arial", "", article_text_font_size)
        # Translate content explicitly before adding to PDF
        translated_local_history = translate_text_with_ai(local_history_content, current_language, client_ai)
        pdf.multi_cell(content_width, line_height, translated_local_history)
        
        # Restore original margins for subsequent content (Page 2)
        pdf.set_left_margin(original_left_margin)
        pdf.set_right_margin(original_right_margin)
        pdf.set_x(original_x)

    # NEW: Companion Activities Section
    if st.session_state.get('toggle_companion_activities', False) and data.get('companion_activities'):
        companion_activities_content = data.get('companion_activities', '')
        if companion_activities_content and not companion_activities_content.startswith("No companion activities available."):
            pdf.add_page() # Start companion activities on a new page
            pdf.set_left_margin(left_margin)
            pdf.set_right_margin(right_margin)
            pdf.set_x(left_margin)
            pdf.set_y(20) # Start from top of new page

            pdf.set_font("Arial", "B", section_title_font_size * 1.2) # Larger title for this section
            pdf.multi_cell(content_width, line_height, clean_text_for_latin1(translate_text_with_ai("Companion Activities for Today's Article", current_language, client_ai)), align='C')
            pdf.ln(section_spacing)

            pdf.set_font("Arial", "", article_text_font_size)
            # Use a slightly different approach to parse and print markdown-like output
            # This is a simplified parser; a more robust one might be needed for complex markdown
            
            # Split the content by major headings
            sections = re.split(r'^(Craft Activity:|Snack Idea:|Reminiscence Activity:)\s*', companion_activities_content, flags=re.MULTILINE)
            
            # The first element before the first heading is usually empty or intro. Skip it.
            # Process sections in pairs (heading, content)
            for i in range(1, len(sections), 2):
                heading = sections[i].strip()
                body = sections[i+1].strip()

                if heading:
                    pdf.set_font("Arial", "B", section_title_font_size)
                    pdf.multi_cell(content_width, line_height, clean_text_for_latin1(heading))
                    pdf.set_font("Arial", "", article_text_font_size)
                    # Split body into lines and print, handling bullet points or new lines
                    for line in body.split('\n'):
                        pdf.multi_cell(content_width, line_height, clean_text_for_latin1(line.strip()))
                    pdf.ln(section_spacing/2) # Smaller space between activities


    # --- Page 2 Content ---
    # ALWAYS add a new page before starting the "About Us" section to ensure it's on page 2
    # and is distinctly separate from any main content that may have flowed across pages.
    pdf.add_page()

    # Set margins and starting Y for the new page (Page 2)
    pdf.set_left_margin(left_margin_p2)
    pdf.set_right_margin(right_margin_p2)
    pdf.set_x(left_margin_p2) # Start content at the new left margin
    pdf.set_y(20) # Start further down on the new page

    # About Us Title
    pdf.set_font("Arial", "B", section_title_font_size * 1.5) # Slightly smaller font for longer title
    new_about_us_title = clean_text_for_latin1(translate_text_with_ai("Learn More About US! Mindful Libraries - A Dementia-Inclusive Reading Program", current_language, client_ai))
    pdf.multi_cell(content_width_p2, 10 * line_height_multiplier, new_about_us_title, 0, 'C') # Using multi_cell for title as it's long
    pdf.ln(5 * line_height_multiplier) # Smaller line break after title

    # About Us Text
    pdf.set_font("Arial", "", article_text_font_size * 1.1) # Slightly smaller font for better fit
    new_about_us_text = clean_text_for_latin1(translate_text_with_ai("""Mindful Libraries is a collaborative initiative between Resense, Nana's Books, and Mirador
Magazine, designed to bring adaptive, nostalgic reading experiences to individuals living
with dementia. This innovative program provides:
- Curated Libraries of dementia-friendly newspapers, books, and magazines
- Staff Training accredited by NCCAP, focusing on reminiscence, person-centered care,
and meaningful engagement
- Digital Access Tools like downloadable discussion guides, activity templates, and reading
prompts
- Partnerships with Long-Term Care Communities to build inclusive, life-enriching
environments
Mindful Libraries empowers care teams to reconnect residents with their pasts, spark joyful conversation, and foster dignity through storytelling and memory-based engagement.""", current_language, client_ai))
    pdf.multi_cell(content_width_p2, 6 * line_height_multiplier, new_about_us_text, 0, 'L') # Left align for readability
    pdf.ln(5 * line_height_multiplier) # Add space after About Us text

    # New line for learning more
    pdf.set_font("Arial", "B", article_text_font_size * 1.2) # Set font to bold for this line
    pdf.multi_cell(content_width_p2, 7 * line_height_multiplier, clean_text_for_latin1(translate_text_with_ai("Learn more about our program at www.mindfullibraries.com", current_language, client_ai)), 0, 'C') # Centered and bold
    pdf.set_font("Arial", "", article_text_font_size) # Reset font to normal
    pdf.ln(10 * line_height_multiplier) # More space after this line

    # Logo - still centered horizontally on the page
    logo_width = 70
    logo_height = 70
    logo_x = (page_width - logo_width) / 2 # Still calculated based on full page width for centering
    pdf.image("https://i.postimg.cc/8CRsCGCC/Chat-GPT-Image-Jun-7-2025-12-32-18-AM.png", x=logo_x, y=pdf.get_y(), w=logo_width, h=logo_height)
    pdf.ln(logo_height + (15 * line_height_multiplier)) # Add space after logo

    # Contact Information - still centered horizontally on the page
    pdf.set_font("Arial", "B", section_title_font_size * 1.3)
    pdf.multi_cell(0, 10 * line_height_multiplier, clean_text_for_latin1(translate_text_with_ai("Contact Information", current_language, client_ai)), 0, 'C') # Translated
    pdf.ln(5 * line_height_multiplier)
    pdf.set_font("Arial", "", article_text_font_size * 1.2)
    pdf.multi_cell(0, 7 * line_height_multiplier, clean_text_for_latin1(translate_text_with_ai("Email: thisdayinhistoryapp@gmail.com", current_language, client_ai)), 0, 'C') # Translated
    pdf.multi_cell(0, 7 * line_height_multiplier, clean_text_for_latin1(translate_text_with_ai("Website: ThisDayInHistoryApp.com (Coming Soon!)", current_language, client_ai)), 0, 'C') # Translated
    
    # Original bold website URL, keep if intended to have two website mentions
    pdf.set_font("Arial", "B", article_text_font_size * 1.2) # Set font to bold
    pdf.multi_cell(0, 7 * line_height_multiplier, clean_text_for_latin1(translate_text_with_ai("www.mindfullibraries.com", current_language, client_ai)), 0, 'C') # Translated
    pdf.set_font("Arial", "", article_text_font_size) # Reset font to normal

    pdf.multi_cell(0, 7 * line_height_multiplier, clean_text_for_latin1(translate_text_with_ai("Phone: 412-212-6701 (For Support)", current_language, client_ai)), 0, 'C') # Translated
    pdf.ln(10 * line_height_multiplier)

    # User info at the very bottom of the second page, aligned right
    pdf.set_font("Arial", "I", max(8, article_text_font_size - 2))
    # Reset margins for a full width cell to align right
    pdf.set_left_margin(left_margin_p2) # Revert to page 2 margins
    pdf.set_right_margin(right_margin_p2)
    pdf.set_x(left_margin_p2)
    pdf.set_y(pdf.h - (15 * line_height_multiplier)) # Position near bottom of the page
    pdf.multi_cell(content_width_p2, 4 * line_height_multiplier, clean_text_for_latin1(translate_text_with_ai(f"Generated for {user_info['name']}", current_language, client_ai)), align='R') # Translated
        
    return pdf.output(dest='S').encode('latin-1')


# --- Page Navigation Function ---
def set_page(page_name):
    """Sets the current page in session state."""
    st.session_state['current_page'] = page_name
    # Reset trivia states if navigating away from trivia page to ensure fresh start if new day
    if page_name == 'main_app' or page_name == 'weekly_planner_page' or page_name == 'offline_pack_page': # Reset for relevant pages
        st.session_state['trivia_question_states'] = {}
        st.session_state['hints_remaining'] = 3 # Reset hints when going back to main page for a new day's content
        st.session_state['current_trivia_score'] = 0 # Reset score for a new day
        st.session_state['total_possible_daily_trivia_score'] = 0 # Reset total possible for a new day
        st.session_state['score_logged_today'] = False # Reset logging flag
        st.session_state['current_trivia_slide'] = 0 # Reset for group mode
        st.session_state['reveal_answer'] = False # Reset for group mode
        st.session_state['resident_scores'] = [{'name': f'Resident {i+1}', 'score': 0} for i in range(len(st.session_state['resident_scores']))] # Reset group scores
    # Streamlit will automatically rerun the app when session_state is modified.
    # No st.rerun() is needed here to avoid "no-op" warnings.


def show_feedback_form():
    """Displays a feedback form and logs submissions to Google Sheets."""
    st.markdown("---")
    st.subheader(translate_text_with_ai("📧 Send us feedback", st.session_state['preferred_language'], client_ai))
    st.markdown(translate_text_with_ai("We'd love to hear from you! Please share your thoughts below.", st.session_state['preferred_language'], client_ai))

    with st.form("feedback_form", clear_on_submit=True):
        feedback_text = st.text_area(translate_text_with_ai("Your Feedback", st.session_state['preferred_language'], client_ai), help=translate_text_with_ai("Tell us what you think!", st.session_state['preferred_language'], client_ai), key="feedback_text_area")
        contact_info = st.text_input(translate_text_with_ai("Your Name or Email (Optional)", st.session_state['preferred_language'], client_ai), help=translate_text_with_ai("So we can follow up, if needed.", st.session_state['preferred_language'], client_ai), key="feedback_contact_info")
        
        submitted = st.form_submit_button(translate_text_with_ai("Submit Feedback", st.session_state['preferred_language'], client_ai))
        if submitted:
            if feedback_text.strip():
                # Use logged-in username if available, otherwise use provided contact info
                username_for_feedback = st.session_state.get('logged_in_username', 'Guest')
                if contact_info.strip():
                    username_for_feedback = contact_info.strip() # Override if user provides specific contact info
                
                if log_feedback(username_for_feedback, feedback_text.strip()):
                    st.success(translate_text_with_ai("Thank you for your feedback! We appreciate it.", st.session_state['preferred_language'], client_ai))
                else:
                    st.error(translate_text_with_ai("Failed to submit feedback. Please try again later.", st.session_state['preferred_language'], client_ai))
            else:
                st.warning(translate_text_with_ai("Please enter some feedback before submitting.", st.session_state['preferred_language'], client_ai))
    st.markdown("---")

# New wrapper function for PDF download button
def handle_pdf_download_click(username, filename, selected_date):
    """
    Handles the PDF download button click event, logging the download
    and setting a session state flag for persistent feedback.
    """
    success = log_pdf_download(username, filename, selected_date)
    if success:
        st.session_state['last_download_status'] = 'success'
    else:
        st.session_state['last_download_status'] = 'failure'

# --- UI Functions for Pages ---
def show_main_app_page():
    st.title(translate_text_with_ai("📅 This Day in History", st.session_state['preferred_language'], client_ai))

    st.markdown(f"<p style='font-size:24px; font-weight:bold;'>{translate_text_with_ai('Today\'s Daily Page', st.session_state['preferred_language'], client_ai)}</p>", unsafe_allow_html=True)


    today = datetime.today()
    
    # --- Date Picker for Main Page Content ---
    selected_date = st.date_input(translate_text_with_ai("Select a date", st.session_state['preferred_language'], client_ai), value=today, key="date_picker_main_app")
    day, month, year = selected_date.day, selected_date.month, selected_date.year

    user_info = {
        'name': st.session_state['logged_in_username'],
        'jobs': '', 'hobbies': '', 'decade': '', 'life_experiences': '', 'college_chapter': ''
    }

    # Fetch daily data if not already fetched for the current day/user/preferences/language
    # Include new feature toggles in the key to ensure re-fetch if they change
    current_data_key = f"{selected_date.strftime('%Y-%m-%d')}-{st.session_state['logged_in_username']}-" \
                       f"{st.session_state.get('preferred_topic_main_app', 'None')}-" \
                       f"{st.session_state.get('preferred_decade_main_app', 'None')}-" \
                       f"trivia_difficulty_{st.session_state['difficulty']}-" \
                       f"local_city_{st.session_state['local_city']}-" \
                       f"local_state_country_{st.session_state['local_state_country']}-" \
                       f"language_{st.session_state['preferred_language']}-" \
                       f"companion_activities_enabled_{st.session_state['toggle_companion_activities']}" # ADDED COMPANION ACTIVITIES TOGGLE TO KEY

    if st.session_state['last_fetched_date'] != current_data_key or st.session_state['daily_data'] is None:
        with st.spinner(translate_text_with_ai("Fetching today's historical facts and generating content...", st.session_state['preferred_language'], client_ai)):
            # Fetch always in English first
            fetched_raw_data = get_this_day_in_history_facts( # Renamed to avoid confusion with `raw_data` later
                day, month, user_info, client_ai, 
                topic=st.session_state.get('preferred_topic_main_app') if st.session_state.get('preferred_topic_main_app') != "None" else None,
                preferred_decade=st.session_state.get('preferred_decade_main_app') if st.session_state.get('preferred_decade_main_app') != "None" else None,
                difficulty=st.session_state['difficulty'], # Pass the selected difficulty to generate trivia
                local_city=st.session_state['local_city'] if st.session_state['local_city'].strip() else None,
                local_state_country=st.session_state['local_state_country'] if st.session_state['local_state_country'].strip() else None
            )
            
            # Defensive check: Ensure fetched_raw_data is indeed a dictionary
            if not isinstance(fetched_raw_data, dict):
                st.error("Generated raw data was not a dictionary. Using default empty data.")
                fetched_raw_data = _INITIAL_EMPTY_DATA.copy()

            # Store both raw and translated data in session state
            st.session_state['raw_fetched_data'] = fetched_raw_data # Store the raw data
            st.session_state['daily_data'] = translate_content(fetched_raw_data, st.session_state['preferred_language'], client_ai)
            st.session_state['last_fetched_date'] = current_data_key
            st.session_state['trivia_question_states'] = {} # Reset trivia states for new day's data
            st.session_state['hints_remaining'] = 3 # Reset hints for a new day
            st.session_state['current_trivia_score'] = 0 # Reset score for a new day
            st.session_state['total_possible_daily_trivia_score'] = 0 # Reset total possible for a new day
            st.session_state['score_logged_today'] = False # Reset logging flag
            # Reset group mode states
            st.session_state['current_trivia_slide'] = 0
            st.session_state['reveal_answer'] = False
            st.session_state['resident_scores'] = [{'name': f'Resident {i+1}', 'score': 0} for i in range(len(st.session_state['resident_scores']))]

    data = st.session_state['daily_data'] # This 'data' is now already translated if needed
    raw_data_for_pdf = st.session_state['raw_fetched_data'] # Get the raw data for PDF generation

    # Display content - Articles are back on the main page
    st.subheader(translate_text_with_ai(f"✨ A Look Back at {selected_date.strftime('%B %d')}", st.session_state['preferred_language'], client_ai))

    # New note for scrolling down to download/print at the top of the main page
    st.info(
        translate_text_with_ai(
            """💡 Scroll down to download and print your This Day In History worksheet! 
You can download each day's content as a printable PDF—perfect for sharing with your residents or using in group activities!
Want to make it your own? You can even customize the masthead to match your community—try something fun like Arbor Courts Gazette or The Morning Maple 🍁.

🌍 Need another language? Use the left-hand menu to translate the entire page and your downloadable PDF.

This is a free platform. 
💬 We'd Love Your Support!
Word of mouth goes a long way—if you enjoy using This Day In History, please share it with your friends, coworkers, or anyone who might benefit. Your support means the world to us!

""",
            st.session_state['preferred_language'],
            client_ai
        )
    )


    st.markdown("---")
    st.subheader(translate_text_with_ai("🗓️ Significant Event", st.session_state['preferred_language'], client_ai))
    st.write(data.get('event_article', "No event article found."))

    st.markdown("---")
    st.subheader(translate_text_with_ai("🎂 Born on this Day", st.session_state['preferred_language'], client_ai))
    st.write(data.get('born_article', "No birth article found."))

    st.markdown("---")
    st.subheader(translate_text_with_ai("💡 Fun Fact", st.session_state['preferred_language'], client_ai))
    st.write(data.get('fun_fact_section', "No fun fact found."))

    # Display Local History if available and not the "not found" messages
    local_history_display_content = data.get('local_history_section', '')
    if local_history_display_content and \
       not local_history_display_content.startswith("Could not generate local history fact."): # Simplified check
        st.markdown("---")
        st.subheader(translate_text_with_ai("📍 Local History", st.session_state['preferred_language'], client_ai))
        st.write(local_history_display_content)
    else: # This covers cases where local_city/state are not set, or AI failed to generate
        st.markdown("---")
        st.subheader(translate_text_with_ai("📍 Local History", st.session_state['preferred_language'], client_ai))
        st.info(translate_text_with_ai("Could not retrieve a local history fact for your settings. Please try again with different inputs or leave blank for a general U.S. historical fact.", st.session_state['preferred_language'], client_ai))


    st.markdown("---")
    st.subheader(translate_text_with_ai("🌟 Did You Know?", st.session_state['preferred_language'], client_ai)) # Changed to '?'
    # Use .get() with an empty list as default for iteration
    for i, fact in enumerate(data.get('did_you_know_section', [])):
        st.write(f"- {fact}")

    st.markdown("---")
    st.subheader(translate_text_with_ai("💬 Memory Lane Prompt?", st.session_state['preferred_language'], client_ai)) # Changed to '?'
    # Iterate and display each memory prompt without hyphens, using .get() with an empty list as default
    memory_prompts_display_list = data.get('memory_prompt_section', [])
    if memory_prompts_display_list:
        for prompt_text in memory_prompts_display_list:
            st.write(f"{prompt_text}") # Display as paragraph, no leading hyphen
    else:
        st.write(translate_text_with_ai("No memory prompts available.", st.session_state['preferred_language'], client_ai))

    # NEW: Display Companion Activities if enabled
    if st.session_state.get('toggle_companion_activities', False):
        st.markdown("---")
        st.subheader(translate_text_with_ai("🎨 Companion Activities", st.session_state['preferred_language'], client_ai))
        if data.get('companion_activities') and not data.get('companion_activities').startswith("No companion activities available."):
            st.markdown(data.get('companion_activities'))
        else:
            st.info(translate_text_with_ai("No companion activities generated for today's article.", st.session_state['preferred_language'], client_ai))

    st.markdown("---")

    st.subheader(translate_text_with_ai("PDF Customization", st.session_state['preferred_language'], client_ai))
    st.session_state['custom_masthead_text'] = st.text_input(
        translate_text_with_ai("Optional: Custom Masthead for PDF (e.g., Your Company Name, Care Community Name)", st.session_state['preferred_language'], client_ai),
        value=st.session_state['custom_masthead_text'],
        help=translate_text_with_ai("Leave blank to use the default 'The Daily Resense Register'.", st.session_state['preferred_language'], client_ai),
        key="custom_masthead_input"
    )
    
    # Generate PDF bytes once
    # DEBUG PRINT: Confirming the masthead text used for PDF generation
    print(f"DEBUG: Generating PDF with masthead: '{st.session_state['custom_masthead_text']}' for date {selected_date.strftime('%Y-%m-%d')}")
    with st.spinner(translate_text_with_ai("Preparing your PDF worksheet...", st.session_state['preferred_language'], client_ai)):
        pdf_bytes_main = generate_full_history_pdf(
            raw_data_for_pdf, 
            selected_date.strftime('%B %d, %Y'), 
            user_info, 
            st.session_state['preferred_language'],
            st.session_state['custom_masthead_text'], # Pass the custom masthead text
            st.session_state['toggle_large_print_pdf'], # Pass large print toggle
            st.session_state['toggle_audio_qr'] # Pass audio QR toggle
        )
    
    # Create Base64 encoded link
    lang_suffix = f"_{st.session_state['preferred_language']}" if st.session_state['preferred_language'] != 'English' else ''
    pdf_file_name = f"This_Day_in_History_{selected_date.strftime('%Y%m%d')}{lang_suffix}.pdf"

    # Make download button key dynamic to ensure fresh content on re-renders
    # Using a hash of custom_masthead_text and date to ensure unique key when content changes
    download_button_key = f"download_daily_pdf_{selected_date.strftime('%Y%m%d')}_{st.session_state['preferred_language']}_masthead_{hash(st.session_state['custom_masthead_text'])}"


    b64_pdf_main = base64.b64encode(pdf_bytes_main).decode('latin-1')
    pdf_viewer_link_main = f'<a href="data:application/pdf;base64,{b64_pdf_main}" target="_blank">{translate_text_with_ai("View PDF in Browser", st.session_state["preferred_language"], client_ai)}</a>'

    # Display status message if any
    if st.session_state['last_download_status'] == 'success':
        st.success(translate_text_with_ai("PDF download successfully logged to Google Sheet!", st.session_state['preferred_language'], client_ai))
        st.session_state['last_download_status'] = None # Clear the message after display
    elif st.session_state['last_download_status'] == 'failure':
        st.error(translate_text_with_ai("Failed to log PDF download to Google Sheet. Please check permissions or try again.", st.session_state['preferred_language'], client_ai))
        st.session_state['last_download_status'] = None # Clear the message after display


    col1, col2 = st.columns([1, 1])
    with col1:
        st.download_button(
            translate_text_with_ai("Download Daily Page PDF", st.session_state['preferred_language'], client_ai),
            pdf_bytes_main, 
            file_name=pdf_file_name,
            mime="application/pdf",
            on_click=handle_pdf_download_click, # Use the new handler
            args=(st.session_state['logged_in_username'], pdf_file_name, selected_date), # Pass arguments
            key=download_button_key # Use the dynamic key
        )
    with col2:
        st.markdown(pdf_viewer_link_main, unsafe_allow_html=True)
    
    # Feedback form at the bottom
    show_feedback_form()


# NEW: show_weekly_planner_page
def show_weekly_planner_page():
    st.title(translate_text_with_ai("🗓️ Weekly Planner View", st.session_state['preferred_language'], client_ai))
    st.button(translate_text_with_ai("⬅️ Back to Main Page", st.session_state['preferred_language'], client_ai), on_click=set_page, args=('main_app',), key="back_to_main_from_weekly_top")

    st.markdown("---")
    st.markdown(translate_text_with_ai("Select a week to generate a ZIP file containing 7 daily PDFs.", st.session_state['preferred_language'], client_ai))

    selected_date = st.date_input(translate_text_with_ai("Select a date within the desired week", st.session_state['preferred_language'], client_ai), value=date.today(), key="weekly_planner_date_input")
    week_start_option = st.radio(translate_text_with_ai("Week Starts On:", st.session_state['preferred_language'], client_ai), ["Sunday", "Monday"], key='week_start_radio')

    if week_start_option == "Sunday":
        # Calculate the most recent Sunday
        start_of_week = selected_date - timedelta(days=(selected_date.weekday() + 1) % 7)
    else: # Monday
        # Calculate the most recent Monday
        start_of_week = selected_date - timedelta(days=selected_date.weekday())

    st.info(translate_text_with_ai(f"PDFs will be generated for the week of: **{start_of_week.strftime('%B %d, %Y')}** to **{(start_of_week + timedelta(days=6)).strftime('%B %d, %Y')}**", st.session_state['preferred_language'], client_ai))

    if st.button(translate_text_with_ai("Generate Weekly PDF Pack", st.session_state['preferred_language'], client_ai), key='generate_weekly_zip_btn'):
        pdf_files = {} # Dictionary to store filename and PDF bytes
        user_info = {'name': st.session_state['logged_in_username']}

        with st.spinner(translate_text_with_ai("Generating 7 daily PDFs and creating ZIP file...", st.session_state['preferred_language'], client_ai)):
            for i in range(7):
                current_day = start_of_week + timedelta(days=i)
                
                # Fetch daily data (raw, English version)
                fetched_raw_data = get_this_day_in_history_facts(
                    current_day.day, current_day.month, user_info, client_ai,
                    topic=st.session_state.get('preferred_topic_main_app') if st.session_state.get('preferred_topic_main_app') != "None" else None,
                    preferred_decade=st.session_state.get('preferred_decade_main_app') if st.session_state.get('preferred_decade_main_app') != "None' else None,
                    difficulty=st.session_state['difficulty'],
                    local_city=st.session_state['local_city'] if st.session_state['local_city'].strip() else None,
                    local_state_country=st.session_state['local_state_country'] if st.session_state['local_state_country'].strip() else None
                )

                pdf_filename = f"This_Day_in_History_{current_day.strftime('%Y%m%d')}_{st.session_state['preferred_language']}.pdf"
                
                # Generate PDF using fetched raw data (translation will occur inside generate_full_history_pdf)
                pdf_bytes_output = generate_full_history_pdf(
                    fetched_raw_data,
                    current_day.strftime('%B %d, %Y'),
                    user_info,
                    st.session_state['preferred_language'],
                    st.session_state['custom_masthead_text'],
                    st.session_state['toggle_large_print_pdf'],
                    st.session_state['toggle_audio_qr']
                )
                pdf_files[pdf_filename] = pdf_bytes_output
                log_pdf_download(st.session_state['logged_in_username'], pdf_filename, current_day)

            # Create ZIP file in memory
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zip_file:
                for filename, content in pdf_files.items():
                    zip_file.writestr(filename, content)
            zip_buffer.seek(0) # Rewind to beginning

            zip_file_name = f"This_Day_in_History_Weekly_Pack_{start_of_week.strftime('%Y%m%d')}.zip"
            st.download_button(
                label=translate_text_with_ai("Download Weekly PDF Pack (ZIP)", st.session_state['preferred_language'], client_ai),
                data=zip_buffer,
                file_name=zip_file_name,
                mime="application/zip",
                key=f"download_weekly_zip_{start_of_week.strftime('%Y%m%d')}_{st.session_state['preferred_language']}_masthead_{hash(st.session_state['custom_masthead_text'])}" # Dynamic key
            )
            st.success(translate_text_with_ai("Weekly PDF pack generated and ready for download!", st.session_state['preferred_language'], client_ai))
    
    st.button(translate_text_with_ai("⬅️ Back to Main Page", st.session_state['preferred_language'], client_ai), on_click=set_page, args=('main_app',), key="back_to_main_from_weekly_bottom")
    show_feedback_form()


# NEW: show_group_mode_trivia_page
def show_group_mode_trivia_page(daily_data, client_ai):
    st.title(translate_text_with_ai("👥 Group Trivia Challenge!", st.session_state['preferred_language'], client_ai))
    st.button(translate_text_with_ai("⬅️ Back to Main Page", st.session_state['preferred_language'], client_ai), on_click=set_page, args=('main_app',), key="back_to_main_from_group_top")

    if not daily_data or not daily_data['trivia_section']:
        st.warning(translate_text_with_ai("No trivia questions available for today. Please fetch daily data from the main page.", st.session_state['preferred_language'], client_ai))
        return

    trivia_questions = daily_data['trivia_section']
    num_questions = len(trivia_questions)

    st.subheader(translate_text_with_ai("Group Settings", st.session_state['preferred_language'], client_ai))
    # Allow setting number of residents
    num_residents = st.number_input(translate_text_with_ai("Number of Participants (max 10)", st.session_state['preferred_language'], client_ai), min_value=1, max_value=10, value=len(st.session_state['resident_scores']), key='num_residents_group_mode')
    if len(st.session_state['resident_scores']) != num_residents:
        st.session_state['resident_scores'] = [{'name': f'Resident {i+1}', 'score': 0} for i in range(num_residents)]
        # Reinitialize states for existing questions based on new number of residents.
        # This part might need more sophisticated handling if existing scores need to be preserved.
        # For simplicity, resetting scores if number of residents changes.
        st.session_state['current_trivia_slide'] = 0
        st.session_state['reveal_answer'] = False
        st.experimental_rerun() # Rerun to apply participant count change

    st.markdown("---")

    current_q_index = st.session_state['current_trivia_slide']

    if current_q_index < num_questions:
        current_question = trivia_questions[current_q_index]

        st.markdown(f"### {translate_text_with_ai('Question', st.session_state['preferred_language'], client_ai)} {current_q_index + 1} / {num_questions}")
        st.markdown(f"<h1 style='text-align: center; font-size: 3em;'>{clean_text_for_latin1(current_question['question'])}</h1>", unsafe_allow_html=True)
        st.write("") # Add some space

        col1, col2 = st.columns(2)
        with col1:
            if st.button(translate_text_with_ai("💡 Hint", st.session_state['preferred_language'], client_ai), key=f'hint_btn_group_{current_q_index}'):
                st.info(translate_text_with_ai(f"Hint: {clean_text_for_latin1(current_question['hint'])}", st.session_state['preferred_language'], client_ai))
        with col2:
            if st.button(translate_text_with_ai("👁️ Reveal Answer", st.session_state['preferred_language'], client_ai), key=f'reveal_btn_group_{current_q_index}'):
                st.session_state['reveal_answer'] = True

        if st.session_state['reveal_answer']:
            st.markdown(f"### {translate_text_with_ai('Answer', st.session_state['preferred_language'], client_ai)}:")
            st.markdown(f"<h2 style='text-align: center; color: #28a745;'>{clean_text_for_latin1(current_question['answer'])}</h2>", unsafe_allow_html=True)
            
            # Generate explanation for the answer (if not already generated and stored in a temporary state)
            explanation_key = f'explanation_group_{current_q_index}'
            if explanation_key not in st.session_state:
                 with st.spinner(translate_text_with_ai("Generating explanation...", st.session_state['preferred_language'], client_ai)):
                    generated_explanation_en = generate_related_trivia_article(current_question['question'], current_question['answer'], client_ai)
                    st.session_state[explanation_key] = translate_text_with_ai(generated_explanation_en, st.session_state['preferred_language'], client_ai)
            st.info(translate_text_with_ai(f"Explanation: {clean_text_for_latin1(st.session_state[explanation_key])}", st.session_state['preferred_language'], client_ai))
            
            st.markdown("---")
            st.markdown(translate_text_with_ai("### Score Participants", st.session_state['preferred_language'], client_ai))
            
            # Use columns for score input
            score_cols = st.columns(num_residents)
            for i, resident in enumerate(st.session_state['resident_scores']):
                with score_cols[i]:
                    if st.button(translate_text_with_ai(f"➕ {resident['name']}", st.session_state['preferred_language'], client_ai), key=f'score_btn_group_{current_q_index}_{i}'):
                        st.session_state['resident_scores'][i]['score'] += 1
                        st.success(translate_text_with_ai(f"{resident['name']} scored!", st.session_state['preferred_language'], client_ai))
                    st.markdown(f"**{resident['name']}: {resident['score']}**")

            st.markdown("---")
            if st.button(translate_text_with_ai("➡️ Next Question", st.session_state['preferred_language'], client_ai), key=f'next_q_btn_group_{current_q_index}'):
                st.session_state['current_trivia_slide'] += 1
                st.session_state['reveal_answer'] = False # Reset for next question
                st.experimental_rerun() # Rerun to show next question
    else:
        st.success(translate_text_with_ai("All trivia questions completed!", st.session_state['preferred_language'], client_ai))
        st.markdown(translate_text_with_ai("### Final Scores:", st.session_state['preferred_language'], client_ai))
        
        # Sort residents by score for final display
        sorted_scores = sorted(st.session_state['resident_scores'], key=lambda x: x['score'], reverse=True)
        for i, resident in enumerate(sorted_scores):
            st.write(f"{i+1}. {resident['name']}: {resident['score']} {translate_text_with_ai('points', st.session_state['preferred_language'], client_ai)}")
        
        if st.button(translate_text_with_ai("Restart Trivia", st.session_state['preferred_language'], client_ai), key='restart_trivia_btn_group'):
            st.session_state['current_trivia_slide'] = 0
            st.session_state['reveal_answer'] = False
            for resident in st.session_state['resident_scores']: # Reset scores
                resident['score'] = 0
            st.experimental_rerun()
    
    st.button(translate_text_with_ai("⬅️ Back to Main Page", st.session_state['preferred_language'], client_ai), on_click=set_page, args=('main_app',), key="back_to_main_from_group_bottom")
    show_feedback_form()


# NEW: show_memory_journal_page
def show_memory_journal_page():
    st.title(translate_text_with_ai("✍️ Memory Journal", st.session_state['preferred_language'], client_ai))
    st.button(translate_text_with_ai("⬅️ Back to Main Page", st.session_state['preferred_language'], client_ai), on_click=set_page, args=('main_app',), key="back_to_main_from_journal_top")

    st.markdown("---")
    st.markdown(translate_text_with_ai("Use this tool to record resident memories or reactions to daily prompts.", st.session_state['preferred_language'], client_ai))

    st.session_state['current_resident_name_journal'] = st.text_input(
        translate_text_with_ai("Resident Name:", st.session_state['preferred_language'], client_ai),
        value=st.session_state['current_resident_name_journal'],
        key='memory_resident_name_input'
    )
    st.session_state['current_memory_entry_text'] = st.text_area(
        translate_text_with_ai("Memory/Reaction Entry:", st.session_state['preferred_language'], client_ai),
        value=st.session_state['current_memory_entry_text'],
        height=200,
        key='memory_text_area_input'
    )

    if st.button(translate_text_with_ai("Save Memory Entry", st.session_state['preferred_language'], client_ai), key='save_memory_btn'):
        if st.session_state['current_resident_name_journal'].strip() and st.session_state['current_memory_entry_text'].strip():
            if log_memory_entry(st.session_state['logged_in_username'], st.session_state['current_resident_name_journal'].strip(), st.session_state['current_memory_entry_text'].strip(), date.today()):
                st.success(translate_text_with_ai("Memory saved successfully!", st.session_state['preferred_language'], client_ai))
                st.session_state['current_memory_entry_text'] = "" # Clear text area
                # st.session_state['current_resident_name_journal'] = "" # Keep name for consecutive entries
            else:
                st.error(translate_text_with_ai("Failed to save memory. Please try again.", st.session_state['preferred_language'], client_ai))
        else:
            st.warning(translate_text_with_ai("Please provide both resident name and the memory entry.", st.session_state['preferred_language'], client_ai))

    st.markdown("---")
    st.subheader(translate_text_with_ai("Download Journal", st.session_state['preferred_language'], client_ai))

    if st.button(translate_text_with_ai("Download Full Memory Journal (PDF)", st.session_state['preferred_language'], client_ai), key='download_journal_pdf_btn'):
        entries = get_memory_entries(st.session_state['logged_in_username'])
        if entries:
            # Generate PDF for journal
            pdf = FPDF(unit="mm", format="A4")
            pdf.add_page()
            pdf.set_auto_page_break(True, margin=15)
            
            pdf.set_font("Arial", "B", 18)
            pdf.cell(0, 10, clean_text_for_latin1(translate_text_with_ai(f"{st.session_state['logged_in_username']}'s Memory Journal", st.session_state['preferred_language'], client_ai)), 0, 1, 'C')
            pdf.ln(10)

            for entry in entries:
                pdf.set_font("Arial", "B", 14)
                pdf.multi_cell(0, 8, clean_text_for_latin1(translate_text_with_ai(f"Resident: {entry.get('ResidentName', 'N/A')}", st.session_state['preferred_language'], client_ai)))
                pdf.set_font("Arial", "", 10)
                pdf.multi_cell(0, 6, clean_text_for_latin1(translate_text_with_ai(f"Date: {entry.get('EntryDate', 'N/A')}", st.session_state['preferred_language'], client_ai)))
                pdf.ln(2)
                pdf.set_font("Arial", "", 12)
                pdf.multi_cell(0, 7, clean_text_for_latin1(entry.get('MemoryText', '')))
                pdf.ln(10) # Space between entries
            
            pdf_bytes = BytesIO()
            pdf.output(pdf_bytes)
            pdf_bytes.seek(0)

            journal_filename = f"Memory_Journal_{st.session_state['logged_in_username']}_{date.today().strftime('%Y%m%d')}.pdf"
            st.download_button(
                label=translate_text_with_ai("Click to Download Journal", st.session_state['preferred_language'], client_ai),
                data=pdf_bytes,
                file_name=journal_filename,
                mime="application/pdf",
                key=f'final_journal_download_btn_{date.today().strftime("%Y%m%d")}' # Dynamic key
            )
        else:
            st.info(translate_text_with_ai("No memory entries to download yet.", st.session_state['preferred_language'], client_ai))
    
    st.button(translate_text_with_ai("⬅️ Back to Main Page", st.session_state['preferred_language'], client_ai), on_click=set_page, args=('main_app',), key="back_to_main_from_journal_bottom")
    show_feedback_form()

# NEW: show_offline_pack_page
def show_offline_pack_page():
    st.title(translate_text_with_ai("📦 Offline Content Pack", st.session_state['preferred_language'], client_ai))
    st.button(translate_text_with_ai("⬅️ Back to Main Page", st.session_state['preferred_language'], client_ai), on_click=set_page, args=('main_app',), key="back_to_main_from_offline_top")

    st.markdown("---")
    st.markdown(translate_text_with_ai("Download the next 7 days of 'This Day in History' PDFs in a single ZIP file for offline access.", st.session_state['preferred_language'], client_ai))

    current_date = date.today()
    st.info(translate_text_with_ai(f"This will download content for the next 7 days, starting from **{current_date.strftime('%B %d, %Y')}**.", st.session_state['preferred_language'], client_ai))

    if st.button(translate_text_with_ai("Pre-download Next 7 Days (ZIP)", st.session_state['preferred_language'], client_ai), key='download_offline_pack_btn'):
        pdf_files = {}
        user_info = {'name': st.session_state['logged_in_username']}

        with st.spinner(translate_text_with_ai("Generating next 7 days of PDFs and creating ZIP file...", st.session_state['preferred_language'], client_ai)):
            for i in range(7):
                day_to_fetch = current_date + timedelta(days=i)
                
                fetched_raw_data = get_this_day_in_history_facts(
                    day_to_fetch.day, day_to_fetch.month, user_info, client_ai,
                    topic=st.session_state.get('preferred_topic_main_app') if st.session_state.get('preferred_topic_main_app') != "None" else None,
                    preferred_decade=st.session_state.get('preferred_decade_main_app') if st.session_state.get('preferred_decade_main_app') != "None" else None,
                    difficulty=st.session_state['difficulty'],
                    local_city=st.session_state['local_city'] if st.session_state['local_city'].strip() else None,
                    local_state_country=st.session_state['local_state_country'] if st.session_state['local_state_country'].strip() else None
                )

                pdf_filename = f"This_Day_in_History_{day_to_fetch.strftime('%Y%m%d')}_{st.session_state['preferred_language']}.pdf"
                
                pdf_bytes_output = generate_full_history_pdf(
                    fetched_raw_data,
                    day_to_fetch.strftime('%B %d, %Y'),
                    user_info,
                    st.session_state['preferred_language'],
                    st.session_state['custom_masthead_text'],
                    st.session_state['toggle_large_print_pdf'],
                    st.session_state['toggle_audio_qr']
                )
                pdf_files[pdf_filename] = pdf_bytes_output
                log_pdf_download(st.session_state['logged_in_username'], pdf_filename, day_to_fetch)

            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zip_file:
                for filename, content in pdf_files.items():
                    zip_file.writestr(filename, content)
            zip_buffer.seek(0)

            zip_file_name = f"This_Day_in_History_Offline_Pack_{current_date.strftime('%Y%m%d')}.zip"
            st.download_button(
                label=translate_text_with_ai("Download Offline Pack (ZIP)", st.session_state['preferred_language'], client_ai),
                data=zip_buffer,
                file_name=zip_file_name,
                mime="application/zip",
                key=f"download_offline_zip_{current_date.strftime('%Y%m%d')}_{st.session_state['preferred_language']}_masthead_{hash(st.session_state['custom_masthead_text'])}" # Dynamic key
            )
            st.success(translate_text_with_ai("Offline PDF pack generated and ready for download!", st.session_state['preferred_language'], client_ai))
    
    st.button(translate_text_with_ai("⬅️ Back to Main Page", st.session_state['preferred_language'], client_ai), on_click=set_page, args=('main_app',), key="back_to_main_from_offline_bottom")
    show_feedback_form()

# NEW: show_autopilot_email_page
def show_autopilot_email_page():
    st.title(translate_text_with_ai("📧 Autopilot Email Feature", st.session_state['preferred_language'], client_ai))
    st.button(translate_text_with_ai("⬅️ Back to Main Page", st.session_state['preferred_language'], client_ai), on_click=set_page, args=('main_app',), key="back_to_main_from_email_top")

    st.markdown("---")
    st.warning(
        translate_text_with_ai(
            """**Important Note on Autopilot Email:**
            This feature requires an external email service and a separate backend process to function automatically (e.g., a scheduled cloud function, or integration with a service like Zapier/Make.com).
            Direct automated email sending is not possible from within this Streamlit application environment for security and technical reasons.
            
            Below, you can configure your preferences for how you'd *like* this feature to work,
            and we will explore ways to integrate with external solutions in the future.
            """,
            st.session_state['preferred_language'],
            client_ai
        )
    )

    st.markdown("---")
    st.subheader(translate_text_with_ai("Email Preferences (Conceptual)", st.session_state['preferred_language'], client_ai))
    
    st.session_state['email_recipient'] = st.text_input(
        translate_text_with_ai("Recipient Email Address:", st.session_state['preferred_language'], client_ai),
        value=st.session_state['email_recipient'],
        key='email_recipient_input',
        help=translate_text_with_ai("Enter the email address where you'd like to receive PDFs.", st.session_state['preferred_language'], client_ai)
    )

    st.session_state['email_frequency'] = st.selectbox(
        translate_text_with_ai("Email Frequency:", st.session_state['preferred_language'], client_ai),
        options=["Daily", "Weekly (Sunday)", "Weekly (Monday)"],
        index=["Daily", "Weekly (Sunday)", "Weekly (Monday)"].index(st.session_state['email_frequency']),
        key='email_frequency_select',
        help=translate_text_with_ai("Choose how often you want to receive the PDF bundles.", st.session_state['preferred_language'], client_ai)
    )

    st.info(
        translate_text_with_ai(
            f"If enabled externally, daily/weekly PDFs would be sent to: **{st.session_state['email_recipient'] if st.session_state['email_recipient'] else 'Not set'}** with a **{st.session_state['email_frequency']}** frequency.",
            st.session_state['preferred_language'],
            client_ai
        )
    )
    
    st.button(translate_text_with_ai("⬅️ Back to Main Page", st.session_state['preferred_language'], client_ai), on_click=set_page, args=('main_app',), key="back_to_main_from_email_bottom")
    show_feedback_form()


def show_trivia_page():
    # Conditional rendering for Group Mode
    if st.session_state.get('toggle_group_mode', False):
        show_group_mode_trivia_page(st.session_state['daily_data'], client_ai)
        return # Exit to avoid showing the regular trivia below

    st.title(translate_text_with_ai("🧠 Daily Trivia Challenge!", st.session_state['preferred_language'], client_ai))
    st.button(translate_text_with_ai("⬅️ Back to Main Page", st.session_state['preferred_language'], client_ai), on_click=set_page, args=('main_app',), key="back_to_main_from_trivia_top")

    # Feedback email note at the top
    st.markdown("---")
    st.markdown(translate_text_with_ai("📧 You can send us feedback at: `thisdayinhistoryapp@gmail.com`", st.session_state['preferred_language'], client_ai))
    st.markdown("---")

    st.subheader(translate_text_with_ai("Trivia Settings", st.session_state['preferred_language'], client_ai))
    # Add the note about inputting a response
    st.info(translate_text_with_ai("💡 To check your answer, please input your response into the text box and then click the 'Check Answer' button.", st.session_state['preferred_language'], client_ai))
    
    # Moved: Difficulty selection is now on the trivia page
    st.session_state['difficulty'] = st.selectbox(
        translate_text_with_ai("Trivia Difficulty", st.session_state['preferred_language'], client_ai),
        options=["Easy", "Medium", "Hard"],
        index=["Easy", "Medium", "Hard"].index(st.session_state['difficulty']), # Set initial value from session state
        key='trivia_difficulty_select',
        help=translate_text_with_ai("Adjusts the complexity of the trivia questions: Easy (well-known), Medium (general facts), Hard (obscure facts).", st.session_state['preferred_language'], client_ai)
    )
    st.markdown("---")

    # If difficulty changes, we need to re-fetch the main content (which includes trivia)
    # This simulates re-generating the daily content with the new trivia difficulty
    current_selected_date = datetime.today().date() # Assume trivia is for today's date
    data_key_for_trivia_regen = f"{current_selected_date.strftime('%Y-%m-%d')}-{st.session_state['logged_in_username']}-" \
                               f"{st.session_state.get('preferred_topic_main_app', 'None')}-" \
                               f"{st.session_state.get('preferred_decade_main_app', 'None')}-" \
                               f"trivia_difficulty_{st.session_state['difficulty']}-" \
                               f"local_city_{st.session_state['local_city']}-" \
                               f"local_state_country_{st.session_state['local_state_country']}-" \
                               f"language_{st.session_state['preferred_language']}"


    # Only re-fetch if the selected difficulty or date or language has changed
    if st.session_state['last_fetched_date'] != data_key_for_trivia_regen:
        with st.spinner(translate_text_with_ai(f"Generating new trivia questions for {st.session_state['difficulty']} difficulty...", st.session_state['preferred_language'], client_ai)):
            # Fetch always in English first, translation happens in translate_content for other sections
            fetched_raw_data = get_this_day_in_history_facts(
                current_selected_date.day, current_selected_date.month, 
                {'name': st.session_state['logged_in_username']}, client_ai, 
                topic=st.session_state.get('preferred_topic_main_app') if st.session_state.get('preferred_topic_main_app') != "None" else None,
                preferred_decade=st.session_state.get('preferred_decade_main_app') if st.session_state.get('preferred_decade_main_app') != "None" else None,
                difficulty=st.session_state['difficulty'],
                local_city=st.session_state['local_city'] if st.session_state['local_city'].strip() else None,
                local_state_country=st.session_state['local_state_country'] if st.session_state['local_state_country'].strip() else None
            )
            # Defensive check: Ensure fetched_raw_data is indeed a dictionary
            if not isinstance(fetched_raw_data, dict):
                st.error("Generated raw data for trivia was not a dictionary. Using default empty data.")
                fetched_raw_data = _INITIAL_EMPTY_DATA.copy()
            
            # Store translated content for non-trivia sections, but trivia in raw_data will remain English
            st.session_state['daily_data'] = translate_content(fetched_raw_data, st.session_state['preferred_language'], client_ai) 
            # Store the raw, untranslated trivia questions separately for direct use on trivia page
            st.session_state['raw_trivia_data'] = fetched_raw_data['trivia_section']
            st.session_state['raw_fetched_data'] = fetched_raw_data # Store the raw data for PDF generation on main page
            st.session_state['last_fetched_date'] = data_key_for_trivia_regen # Update fetched key
            st.session_state['trivia_question_states'] = {} # Reset trivia states for new difficulty's data
            st.session_state['hints_remaining'] = 3
            st.session_state['current_trivia_score'] = 0
            st.session_state['total_possible_daily_trivia_score'] = 0
            st.session_state['score_logged_today'] = False
            st.rerun() # Rerun to apply new content

    # Use the raw, untranslated trivia questions for display on the trivia page
    trivia_questions = st.session_state.get('raw_trivia_data', [])

    if trivia_questions: # Only proceed to display trivia questions if they exist
        # Calculate total possible points
        st.session_state['total_possible_daily_trivia_score'] = len(trivia_questions) * 3
        st.info(f"**{translate_text_with_ai('Total Possible Points', st.session_state['preferred_language'], client_ai)}:** {st.session_state['total_possible_daily_trivia_score']} | **{translate_text_with_ai('Your Current Score', st.session_state['preferred_language'], client_ai)}:** {st.session_state['current_trivia_score']}")
        st.markdown(translate_text_with_ai("**Scoring:** You earn 3 points for a correct answer on the first attempt, 2 points on the second, and 1 point on the third. No points are awarded after three incorrect attempts.", st.session_state['preferred_language'], client_ai))


        for i, trivia_item in enumerate(trivia_questions):
            question_key_base = f"trivia_q_{i}" # Base key for state
            
            # Initialize state for this question if not already present
            if question_key_base not in st.session_state['trivia_question_states']:
                st.session_state['trivia_question_states'][question_key_base] = {
                    'user_answer': '',
                    'is_correct': False,
                    'feedback': '',
                    'hint_revealed': False,
                    'attempts': 0, # NEW: Track attempts for this question
                    'out_of_chances': False, # NEW: Track if user is out of chances for this question
                    'points_earned': 0, # NEW: Points earned for this specific question
                    'related_article_content': None # NEW: Store generated article for this question
                }

            q_state = st.session_state['trivia_question_states'][question_key_base]

            st.markdown(f"---")
            # Question X of Y indicator
            st.markdown(f"**{translate_text_with_ai('Question', st.session_state['preferred_language'], client_ai)} {i+1} {translate_text_with_ai('of', st.session_state['preferred_language'], client_ai)} {len(trivia_questions)}:**")
            
            # Display question
            st.markdown(f"{clean_text_for_latin1(trivia_item.get('question', 'No question available.'))}") # Display question
            
            # Display hint ONLY if revealed or out of chances
            if q_state['hint_revealed'] or q_state.get('out_of_chances', False):
                 if trivia_item.get('hint'):
                    st.info(f"Hint: {clean_text_for_latin1(trivia_item.get('hint', 'No hint available.'))}") # Display hint

            col_input, col_check, col_hint = st.columns([0.6, 0.2, 0.2])

            with col_input:
                user_input = st.text_input(
                    translate_text_with_ai(f"Your Answer for Q{i+1}:", st.session_state['preferred_language'], client_ai), 
                    value=q_state['user_answer'], 
                    key=f"input_{question_key_base}", 
                    disabled=q_state['is_correct'] or q_state.get('out_of_chances', False) # Disable if correct or out of chances
                )
                q_state['user_answer'] = user_input # Update state on input change for persistence

            with col_check:
                # Disable check button if correct, no input, or out of chances
                if not q_state['is_correct'] and not q_state.get('out_of_chances', False):
                    if st.button(translate_text_with_ai("Check Answer", st.session_state['preferred_language'], client_ai), key=f"check_btn_{question_key_base}", disabled=not user_input.strip()):
                        user_answer_cleaned = user_input.strip().lower()
                        correct_answer_original = trivia_item.get('answer', '').strip() # Use .get() here too
                        correct_answer_cleaned = correct_answer_original.lower()

                        is_exact_match = (user_answer_cleaned == correct_answer_cleaned)
                        is_partial_match = False
                        if not is_exact_match:
                            is_partial_match = check_partial_correctness_with_ai(user_input, correct_answer_original, client_ai)

                        if is_exact_match or is_partial_match:
                            if not q_state['is_correct']: # Only award points if not already correct
                                q_state['is_correct'] = True
                                points = 0
                                if q_state['attempts'] == 0: # First try (0 attempts before this correct one)
                                    points = 3
                                elif q_state['attempts'] == 1: # Second try
                                    points = 2
                                elif q_state['attempts'] == 2: # Third try
                                    points = 1
                                # If points have already been awarded, don't add them again
                                if q_state['points_earned'] == 0:
                                    q_state['points_earned'] = points
                                    st.session_state['current_trivia_score'] += points
                                
                                if is_exact_match:
                                    q_state['feedback'] = translate_text_with_ai(f"✅ Correct! You earned {points} points for this question.", st.session_state['preferred_language'], client_ai)
                                else: # It's a partial match
                                    q_state['feedback'] = translate_text_with_ai(f"✅ Partially correct! You earned {points} points for this question.", st.session_state['preferred_language'], client_ai)
                            else:
                                q_state['feedback'] = translate_text_with_ai("✅ Already correct!", st.session_state['preferred_language'], client_ai) # Should not happen with disabled button, but as a safeguard
                        else: # Neither exact nor partial match
                            q_state['attempts'] += 1 # Increment attempts on incorrect answer
                            if q_state['attempts'] >= 3:
                                q_state['out_of_chances'] = True
                                # Display correct answer here if user is out of chances
                                translated_correct_answer = translate_text_with_ai(trivia_item.get('answer', ''), st.session_state['preferred_language'], client_ai) # Use .get() here too
                                q_state['feedback'] = translate_text_with_ai(f"❌ You've used all {q_state['attempts']} attempts. The correct answer was: **{translated_correct_answer}**. You earned 0 points for this question.", st.session_state['preferred_language'], client_ai)
                                st.info(f"Answer: {clean_text_for_latin1(trivia_item.get('answer', 'No answer available.'))}") # Display answer immediately if out of chances
                                # Ensure points_earned is 0 if out of chances and not previously correct
                                if q_state['points_earned'] == 0:
                                    q_state['points_earned'] = 0 # Explicitly set to 0
                            else:
                                q_state['feedback'] = translate_text_with_ai(f"❌ Incorrect. Try again! (Attempts: {q_state['attempts']}/3)", st.session_state['preferred_language'], client_ai)
                        # No st.rerun() needed here; button click triggers rerun automatically

            with col_hint:
                # Show hint button only if not correct, not out of chances, hints remaining, not already revealed, and hint content exists
                if not q_state['is_correct'] and not q_state.get('out_of_chances', False) and st.session_state['hints_remaining'] > 0 and not q_state['hint_revealed'] and trivia_item.get('hint'):
                    if st.button(translate_text_with_ai(f"Hint ({st.session_state['hints_remaining']})", st.session_state['preferred_language'], client_ai), key=f"hint_btn_{question_key_base}"):
                        st.session_state['hints_remaining'] -= 1
                        q_state['hint_revealed'] = True
                        # No st.rerun() needed here; button click triggers rerun automatically
                # Always display hint if it was revealed for this question OR out of chances (for learning) AND hint content exists
                elif (q_state['hint_revealed'] or q_state.get('out_of_chances', False)) and trivia_item.get('hint'):
                    st.info(f"{translate_text_with_ai('Hint', st.session_state['preferred_language'], client_ai)}: {clean_text_for_latin1(trivia_item.get('hint', ''))}")

            # Display feedback based on the state
            if q_state['feedback']:
                if q_state['is_correct']:
                    st.success(q_state['feedback'])
                elif q_state.get('out_of_chances', False):
                    st.error(q_state['feedback'])
                else: # Incorrect but still has chances
                    st.error(q_state['feedback'])

            # Add expander for related article - ONLY show if out of chances or correct
            if q_state.get('out_of_chances', False) or q_state['is_correct']: # Show explanation if correct OR out of chances
                with st.expander(translate_text_with_ai(f"Show Explanation for Q{i+1}", st.session_state['preferred_language'], client_ai)):
                    if q_state['related_article_content'] is None:
                        # Generate article in English first
                        generated_article_en = generate_related_trivia_article(
                            trivia_item.get('question', ''), trivia_item.get('answer', ''), client_ai # Use .get() here too
                        )
                        # Translate to preferred language for display
                        translated_article = translate_text_with_ai(generated_article_en, st.session_state['preferred_language'], client_ai)
                        q_state['related_article_content'] = clean_text_for_latin1(translated_article)
                    st.write(q_state['related_article_content'])
            
        st.markdown("---")
        # Check if all questions are answered correctly or out of chances
        all_completed = all(st.session_state['trivia_question_states'][f"trivia_q_{i}"]['is_correct'] or \
                            st.session_state['trivia_question_states'][f"trivia_q_{i}"].get('out_of_chances', False) \
                            for i in range(len(trivia_questions)))
        
        if all_completed:
            st.success(translate_text_with_ai("You've completed the trivia challenge for today!", st.session_state['preferred_language'], client_ai))
            if not st.session_state['score_logged_today']:
                if log_trivia_score(st.session_state['logged_in_username'], st.session_state['current_trivia_score']):
                    st.session_state['score_logged_today'] = True
                    st.success(translate_text_with_ai("Your score has been logged!", st.session_state['preferred_language'], client_ai))
                else:
                    st.error(translate_text_with_ai("Failed to log your score.", st.session_state['preferred_language'], client_ai))
        else:
            st.info(translate_text_with_ai(f"You have {st.session_state['hints_remaining']} hints remaining.", st.session_state['preferred_language'], client_ai))
        
        st.markdown("---")
        st.subheader(translate_text_with_ai("🏆 Leaderboard", st.session_state['preferred_language'], client_ai))
        leaderboard = get_leaderboard_data()
        if leaderboard:
            for rank, (username, score) in enumerate(leaderboard):
                st.write(f"{rank+1}. {username}: {score} {translate_text_with_ai('points', st.session_state['preferred_language'], client_ai)}")
        else:
            st.info(translate_text_with_ai("No scores logged yet for the leaderboard. Be the first!", st.session_state['preferred_language'], client_ai))

        st.button(translate_text_with_ai("⬅️ Back to Main Page", st.session_state['preferred_language'], client_ai), on_click=set_page, args=('main_app',), key="back_to_main_from_trivia_bottom")
    else: # Added an else block here to explicitly state if no trivia is loaded
        st.info(translate_text_with_ai("No trivia questions are available for today. Please check your content preferences or try again later.", st.session_state['preferred_language'], client_ai))


def show_login_register_page():
    # Centering the logo using columns
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("https://i.postimg.cc/8CRsCGCC/Chat-GPT-Image-Jun-7-2025-12-32-18-AM.png", use_container_width=False, width=200)

    st.markdown(
        translate_text_with_ai(
        """
        Welcome to **This Day in History**!
        Discover fascinating historical events, learn about notable birthdays, and test your knowledge with daily trivia.
        Sign in or register to personalize your daily historical journey and track your trivia scores!
        """, st.session_state['preferred_language'], client_ai)
    )
    st.title(translate_text_with_ai("Login to Access", st.session_state['preferred_language'], client_ai))

    st.markdown("---")

    # Feedback email note at the top
    st.markdown(translate_text_with_ai("📧 You can send us feedback at: `thisdayinhistoryapp@gmail.com`", st.session_state['preferred_language'], client_ai))
    st.markdown("---")

    login_tab, register_tab = st.tabs([translate_text_with_ai("Log In", st.session_state['preferred_language'], client_ai), translate_text_with_ai("Register", st.session_state['preferred_language'], client_ai)])
    with login_tab:
        with st.form("login_form"):
            username = st.text_input(translate_text_with_ai("Username", st.session_state['preferred_language'], client_ai), key="login_username_input")
            password = st.text_input(translate_text_with_ai("Password", st.session_state['preferred_language'], client_ai), type="password", key="login_password_input")
            if st.form_submit_button(translate_text_with_ai("Log In", st.session_state['preferred_language'], client_ai)):
                print(f"Login attempt for username: '{username}'") # Debugging print
                USERS = get_users_from_sheet() # Get users from Google Sheet
                print(f"Users retrieved for login: {USERS}") # Debugging print
                if username in USERS and USERS[username] == password:
                    st.session_state['is_authenticated'] = True
                    st.session_state['logged_in_username'] = username
                    st.success(translate_text_with_ai(f"Welcome {username}!", st.session_state['preferred_language'], client_ai))
                    log_event("login", username)
                    set_page('main_app') # Go to main app page (this handles the rerun)
                else:
                    st.error(translate_text_with_ai("Invalid credentials.", st.session_state['preferred_language'], client_ai))

    with register_tab:
        with st.form("register_form"):
            new_username = st.text_input(translate_text_with_ai("New Username", st.session_state['preferred_language'], client_ai), key="register_username_input")
            new_email = st.text_input(translate_text_with_ai("Email", st.session_state['preferred_language'], client_ai), key="register_email_input")
            st.markdown(
                f"""
                <p style='font-size:0.8em; color:#AAAAAA; margin-top:-1em;'>
                {translate_text_with_ai("*No spam or marketing emails. Used only for account support like lost passwords.*", st.session_state['preferred_language'], client_ai)}
                </p>
                """,
                unsafe_allow_html=True
            )
            new_password = st.text_input(translate_text_with_ai("New Password", st.session_state['preferred_language'], client_ai), type="password", key="register_password_input")
            confirm_password = st.text_input(translate_text_with_ai("Confirm Password", st.session_state['preferred_language'], client_ai), type="password", key="register_confirm_password_input")
            if st.form_submit_button(translate_text_with_ai("Register", st.session_state['preferred_language'], client_ai)):
                if new_password == confirm_password:
                    USERS_EXISTING = get_users_from_sheet() # Get users from Google Sheet right before check
                    print(f"Register attempt for username: '{new_username}'") # Debugging print
                    print(f"Existing users during registration: {USERS_EXISTING}") # Debugging print
                    
                    if new_username in USERS_EXISTING:
                        st.error(translate_text_with_ai("Username already exists. Please choose a different username.", st.session_state['preferred_language'], client_ai))
                    else:
                        if save_new_user_to_sheet(new_username, new_password, new_email):
                            st.session_state['is_authenticated'] = True
                            st.session_state['logged_in_username'] = new_username
                            st.success(translate_text_with_ai(f"Account created successfully! You are now logged in as {new_username}.", st.session_state['preferred_language'], client_ai)) # Updated success message
                            log_event("register", new_username)
                            set_page('main_app') # Go to main app page (this handles the rerun)
                        else:
                            st.error(translate_text_with_ai("Failed to register user. Please try again.", st.session_state['preferred_language'], client_ai))
                else:
                    st.error(translate_text_with_ai("Passwords do not match.", st.session_state['preferred_language'], client_ai))

    # --- Example: This Day in History (on login page) ---
    st.markdown("---")
    st.subheader(translate_text_with_ai("📋 Example: This Day in History", st.session_state['preferred_language'], client_ai))
    st.info(translate_text_with_ai("This is a preview of the content format. Log in or register to get today's personalized content!", st.session_state['preferred_language'], client_ai))

    # Display content based off of January 1st for the example content on the login page
    january_1st_example_date = date(datetime.today().year, 1, 1) # Use current year's Jan 1st for the example
    example_user_info = {'name': 'Example User', 'jobs': '', 'hobbies': '', 'decade': '', 'life_experiences': '', 'college_chapter': ''}
    
    with st.spinner(translate_text_with_ai("Loading example content...", st.session_state['preferred_language'], client_ai)):
        # Always fetch example content in English first
        fetched_raw_example_data = get_this_day_in_history_facts(
            january_1st_example_date.day, 
            january_1st_example_date.month, 
            example_user_info, 
            client_ai, 
            difficulty='Medium',
            local_city=st.session_state['local_city'] if st.session_state['local_city'].strip() else None,
            local_state_country=st.session_state['local_state_country'] if st.session_state['local_state_country'].strip() else None
        )
        
        # Defensive check for example data as well
        if not isinstance(fetched_raw_example_data, dict):
            st.error("Generated raw example data was not a dictionary. Using default empty data for example.")
            fetched_raw_example_data = _INITIAL_EMPTY_DATA.copy()
            
        example_data = translate_content(fetched_raw_example_data, st.session_state['preferred_language'], client_ai)


    st.markdown(translate_text_with_ai(f"### ✨ A Look Back at {january_1st_example_date.strftime('%B %d')}", st.session_state['preferred_language'], client_ai))
    st.markdown(translate_text_with_ai("### 🗓️ Significant Event", st.session_state['preferred_language'], client_ai))
    st.write(example_data.get('event_article', "No event article found."))

    st.markdown(translate_text_with_ai("### 🎂 Born on this Day", st.session_state['preferred_language'], client_ai))
    st.write(example_data.get('born_article', "No birth article found."))

    st.markdown(translate_text_with_ai("### 💡 Fun Fact", st.session_state['preferred_language'], client_ai))
    st.write(example_data.get('fun_fact_section', "No fun fact found."))

    # Display Local History if available and not the "not found" messages
    local_history_example_content = example_data.get('local_history_section', '')
    if local_history_example_content and \
       not local_history_example_content.startswith("Could not generate local history fact."):
        st.markdown("---")
        st.subheader(translate_text_with_ai("📍 Local History", st.session_state['preferred_language'], client_ai))
        st.write(local_history_example_content)
    else:
        st.markdown("---")
        st.subheader(translate_text_with_ai("📍 Local History", st.session_state['preferred_language'], client_ai))
        st.info(translate_text_with_ai("Could not retrieve a local history fact for your settings. Please try again with different inputs or leave blank for a general U.S. historical fact.", st.session_state['preferred_language'], client_ai))


    st.markdown(translate_text_with_ai("### 🧠 Test Your Knowledge!", st.session_state['preferred_language'], client_ai))
    # Loop through the first 4 trivia questions for the example PDF
    trivia_example_questions = fetched_raw_example_data.get('trivia_section', [])
    if trivia_example_questions: # Use fetched_raw_example_data for trivia section
        for i, trivia_item in enumerate(trivia_example_questions[:4]): # Limit to 4 for example PDF
            st.markdown(f"**Question {i+1}:** {clean_text_for_latin1(trivia_item.get('question', 'No question available.'))}")
            st.info(f"Answer: {clean_text_for_latin1(trivia_item.get('answer', 'No answer available.'))}") # Display answer for example content
            # Safely display hint for example content
            if trivia_item.get('hint'): # Use .get() here too
                st.info(f"Hint: {clean_text_for_latin1(trivia_item.get('hint', 'No hint available.'))}")
    else: # Added an else block here to explicitly state if no trivia is loaded
        st.info(translate_text_with_ai("No example trivia questions are available. Please try again later.", st.session_state['preferred_language'], client_ai))


    st.markdown(translate_text_with_ai("### 🌟 Did You Know?", st.session_state['preferred_language'], client_ai))
    # Use .get() with an empty list as default for iteration
    for fact in example_data.get('did_you_know_section', []):
        st.markdown(f"- {fact}")

    st.markdown(translate_text_with_ai("### 💬 Memory Lane Prompt?", st.session_state['preferred_language'], client_ai))
    # Iterate and display each memory prompt for example data without hyphens, using .get() with an empty list as default
    memory_prompts_example_list = example_data.get('memory_prompt_section', [])
    if memory_prompts_example_list:
        for prompt_text in memory_prompts_example_list:
            st.write(f"{prompt_text}") # Display as paragraph, no leading hyphen
    else:
        st.write(translate_text_with_ai("No memory prompts available.", st.session_state['preferred_language'], client_ai))

    # Display Companion Activities if enabled (for example content, if the toggle is on)
    if st.session_state.get('toggle_companion_activities', False):
        st.markdown("---")
        st.subheader(translate_text_with_ai("🎨 Example Companion Activities", st.session_state['preferred_language'], client_ai))
        if example_data.get('companion_activities') and not example_data.get('companion_activities').startswith("No companion activities available."):
            st.markdown(example_data.get('companion_activities'))
        else:
            st.info(translate_text_with_ai("No example companion activities generated.", st.session_state['preferred_language'], client_ai))


    # Generate PDF bytes once for example content
    with st.spinner(translate_text_with_ai("Preparing example PDF...", st.session_state['preferred_language'], client_ai)):
        pdf_bytes_example = generate_full_history_pdf(
            fetched_raw_example_data, 
            january_1st_example_date.strftime('%B %d, %Y'), 
            example_user_info, 
            st.session_state['preferred_language'],
            # No custom masthead for the example PDF, so pass None or empty string
            "",
            st.session_state['toggle_large_print_pdf'], # Pass large print toggle
            st.session_state['toggle_audio_qr'] # Pass audio QR toggle
        )

    # Create Base64 encoded link for example content
    lang_suffix = f"_{st.session_state['preferred_language']}" if st.session_state['preferred_language'] != 'English' else ''
    pdf_file_name_example = f"example_this_day_history_{january_1st_example_date.strftime('%Y%m%d')}{lang_suffix}.pdf"

    b64_pdf_example = base64.b64encode(pdf_bytes_example).decode('latin-1')
    pdf_viewer_link_example = f'<a href="data:application/pdf;base64,{b64_pdf_example}" target="_blank">{translate_text_with_ai("View Example PDF in Browser", st.session_state["preferred_language"], client_ai)}</a>'

    col1_example, col2_example = st.columns([1, 1])
    with col1_example:
        st.download_button(
            translate_text_with_ai("Download Example PDF", st.session_state['preferred_language'], client_ai),
            pdf_bytes_example,
            file_name=pdf_file_name_example,
            mime="application/pdf",
            key=f"download_example_pdf_{january_1st_example_date.strftime('%Y%m%d')}_{st.session_state['preferred_language']}_masthead_example" # Dynamic key for example
        )
    with col2_example:
        st.markdown(pdf_viewer_link_example, unsafe_allow_html=True)


# --- Main App Logic (Router) ---
if st.session_state['is_authenticated']:
    # --- Sidebar content (always visible when authenticated) ---
    st.sidebar.image("https://i.postimg.cc/8CRsCGCC/Chat-GPT-Image-Jun-7-2025-12-32-18-AM.png", use_container_width=True)
    st.sidebar.markdown("---")
    st.sidebar.header(translate_text_with_ai("Navigation", st.session_state['preferred_language'], client_ai))
    if st.sidebar.button(translate_text_with_ai("🏠 Home", st.session_state['preferred_language'], client_ai), key="sidebar_home_btn"):
        set_page('main_app')
    if st.sidebar.button(translate_text_with_ai("🎮 Play Trivia!", st.session_state['preferred_language'], client_ai), key="sidebar_trivia_btn"):
        set_page('trivia_page')
    
    st.sidebar.markdown("---") # Separator before feature toggles explanation
    st.sidebar.info(translate_text_with_ai("💡 Check the boxes below to enable new features, then use the navigation buttons above!", st.session_state['preferred_language'], client_ai))
    
    st.sidebar.subheader(translate_text_with_ai("✨ New Feature Toggles", st.session_state['preferred_language'], client_ai))
    st.session_state['toggle_weekly_planner'] = st.sidebar.checkbox(translate_text_with_ai("📊 Enable Weekly Planner", st.session_state['preferred_language'], client_ai), value=st.session_state['toggle_weekly_planner'], key='toggle_weekly_planner')
    st.session_state['toggle_group_mode'] = st.sidebar.checkbox(translate_text_with_ai("👥 Enable Group Mode (Trivia)", st.session_state['preferred_language'], client_ai), value=st.session_state['toggle_group_mode'], key='toggle_group_mode')
    st.session_state['toggle_audio_qr'] = st.sidebar.checkbox(translate_text_with_ai("🎧 Enable Audio QR Codes (PDF)", st.session_state['preferred_language'], client_ai), value=st.session_state['toggle_audio_qr'], key='toggle_audio_qr')
    st.session_state['toggle_companion_activities'] = st.sidebar.checkbox(translate_text_with_ai("🎨 Enable Companion Activities", st.session_state['preferred_language'], client_ai), value=st.session_state['toggle_companion_activities'], key='toggle_companion_activities')
    st.session_state['toggle_memory_journal'] = st.sidebar.checkbox(translate_text_with_ai("✍️ Enable Memory Journal Tool", st.session_state['preferred_language'], client_ai), value=st.session_state['toggle_memory_journal'], key='toggle_memory_journal')
    st.session_state['toggle_large_print_pdf'] = st.sidebar.checkbox(translate_text_with_ai("🖨️ Enable Large Print PDF", st.session_state['preferred_language'], client_ai), value=st.session_state['toggle_large_print_pdf'], key='toggle_large_print_pdf')
    st.session_state['toggle_offline_pack'] = st.sidebar.checkbox(translate_text_with_ai("📦 Enable Offline Pack", st.session_state['preferred_language'], client_ai), value=st.session_state['toggle_offline_pack'], key='toggle_offline_pack')
    st.session_state['toggle_autopilot_email'] = st.sidebar.checkbox(translate_text_with_ai("📧 Enable Autopilot Email", st.session_state['preferred_language'], client_ai), value=st.session_state['toggle_autopilot_email'], key='toggle_autopilot_email')

    # NEW: Navigation for new features (moved below toggles but still in general navigation section)
    # These buttons will now appear only if the corresponding toggle is checked.
    if st.session_state['toggle_weekly_planner']:
        if st.sidebar.button(translate_text_with_ai("📊 Weekly Planner", st.session_state['preferred_language'], client_ai), key="sidebar_weekly_planner_btn_nav"): # Changed key to avoid conflict if any
            set_page('weekly_planner_page')
    if st.session_state['toggle_memory_journal']:
        if st.sidebar.button(translate_text_with_ai("✍️ Memory Journal", st.session_state['preferred_language'], client_ai), key="sidebar_memory_journal_btn_nav"): # Changed key
            set_page('memory_journal_page')
    if st.session_state['toggle_offline_pack']:
        if st.sidebar.button(translate_text_with_ai("📦 Offline Pack", st.session_state['preferred_language'], client_ai), key="sidebar_offline_pack_btn_nav"): # Changed key
            set_page('offline_pack_page')
    if st.session_state['toggle_autopilot_email']:
        if st.sidebar.button(translate_text_with_ai("📧 Autopilot Email", st.session_state['preferred_language'], client_ai), key="sidebar_autopilot_email_btn_nav"): # Changed key
            set_page('autopilot_email_page')

    st.sidebar.markdown("---")
    st.sidebar.header(translate_text_with_ai("Content Settings", st.session_state['preferred_language'], client_ai))
    
    st.sidebar.subheader(translate_text_with_ai("Content Customization", st.session_state['preferred_language'], client_ai))
    st.session_state['preferred_topic_main_app'] = st.sidebar.selectbox(
        translate_text_with_ai("Preferred Topic for Events (Optional)", st.session_state['preferred_language'], client_ai),
        options=["None", "Sports", "Music", "Inventions", "Politics", "Science", "Arts"],
        index=0,
        key='sidebar_topic_select'
    )
    st.session_state['preferred_decade_main_app'] = st.sidebar.selectbox(
        translate_text_with_ai("Preferred Decade for Articles (Optional)", st.session_state['preferred_language'], client_ai),
        options=["None", "1800s", "1900s", "1910s", "1920s", "1930s", "1940s", "1950s", "1960s", "1970s", "1980s"],
        index=0,
        key='sidebar_decade_select'
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader(translate_text_with_ai("📍 Local History Settings", st.session_state['preferred_language'], client_ai))
    st.session_state['local_city'] = st.sidebar.text_input(
        translate_text_with_ai("Your City (Optional)", st.session_state['preferred_language'], client_ai),
        value=st.session_state['local_city'],
        key='sidebar_local_city'
    )
    st.session_state['local_state_country'] = st.sidebar.text_input(
        translate_text_with_ai("Your State/Country (Optional)", st.session_state['preferred_language'], client_ai),
        value=st.session_state['local_state_country'],
        key='sidebar_local_state_country'
    )
    st.sidebar.info(translate_text_with_ai("Integrating local historical facts specific to your area. Please fill in both fields for best results. If left blank, a general U.S. historical fact will be provided.", st.session_state['preferred_language'], client_ai))
    
    st.sidebar.markdown("---")
    st.sidebar.subheader(translate_text_with_ai("🌐 Language Settings", st.session_state['preferred_language'], client_ai))
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
        show_main_app_page()
    elif st.session_state['current_page'] == 'trivia_page':
        show_trivia_page()
    # NEW: Route to new feature pages
    elif st.session_state['current_page'] == 'weekly_planner_page' and st.session_state['toggle_weekly_planner']:
        show_weekly_planner_page()
    elif st.session_state['current_page'] == 'memory_journal_page' and st.session_state['toggle_memory_journal']:
        show_memory_journal_page()
    elif st.session_state['current_page'] == 'offline_pack_page' and st.session_state['toggle_offline_pack']:
        show_offline_pack_page()
    elif st.session_state['current_page'] == 'autopilot_email_page' and st.session_state['toggle_autopilot_email']:
        show_autopilot_email_page()
    # Default to main_app if current_page is somehow not set to a valid page or feature is toggled off
    else:
        st.session_state['current_page'] = 'main_app'
        show_main_app_page()
else: # Not authenticated, show login/register and January 1st example
    show_login_register_page()
