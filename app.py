# Updated translationandcustomheader.py with the new note
import streamlit as st
from openai import OpenAI
from datetime import datetime, date
from fpdf import FPDF
import re
import json
import base64 # Import base64 for encoding PDF content
import time # Import time for st.spinner delays

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

def log_trivia_score(username, score):
    """Logs a user's trivia score to the 'History' worksheet."""
    try:
        sheet = gs_client.open_by_key("15LXglm49XBJBzeavaHvhgQn3SakqLGeRV80PxPHQfZ4")
        try:
            ws = sheet.worksheet("History")
        except gspread.exceptions.WorksheetNotFound:
            ws = sheet.add_worksheet(title="History", rows="100", cols="3")
            ws.append_row(["Username", "Score", "Timestamp"]) # Add headers if new sheet
        
        # Corrected order: [Username, Score, Timestamp]
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
        return response.choices[0].message.content.strip()
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
    trivia_q_font_size = 10
    trivia_ans_hint_font_size = 9
    line_height_normal = 5
    line_height_trivia_ans_hint = 4
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
    pdf.cell(0, 15, clean_text_for_latin1(translate_text_with_ai(masthead_to_display, current_language, client_ai)), align='C') # Translated
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

    # On This Date
    pdf.set_font("Arial", "B", section_title_font_size)
    pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(translate_text_with_ai("On This Date", current_language, client_ai)))
    current_y_col1 += line_height_normal # Update Y after title
    # Use .get() with a default empty string to prevent TypeError if AI returns None for this field
    pdf.set_font("Arial", "", article_text_font_size) # Ensure font is not bold for article text
    pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(data.get('event_article', '')))
    current_y_col1 = pdf.get_y() + section_spacing_normal # Update Y and add spacing
    pdf.set_y(current_y_col1) # Ensure position is updated

    # Fun Fact
    pdf.set_font("Arial", "B", section_title_font_size)
    pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(translate_text_with_ai("Fun Fact:", current_language, client_ai))) # Translated
    current_y_col1 += line_height_normal
    # Use .get() with a default empty string
    pdf.set_font("Arial", "", article_text_font_size) # Ensure font is not bold for article text
    pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(data.get('fun_fact_section', '')))
    current_y_col1 = pdf.get_y() + section_spacing_normal # Update Y and add spacing
    pdf.set_y(current_y_col1)

    # Daily Trivia
    if data.get('trivia_section'): # Use .get() to check if 'trivia_section' key exists and is not empty/None
        pdf.set_font("Arial", "B", section_title_font_size)
        pdf.multi_cell(col_width, line_height_normal, "Daily Trivia") # NOT translated
        current_y_col1 += line_height_normal

        # Font for trivia questions is intentionally bolded, and answers/hints are not.
        # Loop through the first 4 trivia questions for the PDF
        for i, item in enumerate(data['trivia_section'][:4]): # Limit to 4 questions for PDF
            # Use .get() with default empty string for question, answer, hint
            question_text_clean = clean_text_for_latin1(f"{chr(97+i)}. - {item.get('question', '')}") # Added hyphen
            
            pdf.set_font("Arial", "B", trivia_q_font_size) # Question in bold
            pdf.multi_cell(col_width, line_height_normal, question_text_clean)
            
            pdf.set_font("Arial", "", trivia_ans_hint_font_size) # Answer/Hint in normal font
            answer_text_clean = clean_text_for_latin1(translate_text_with_ai(f"Answer: {item.get('answer', '')}", current_language, client_ai))
            pdf.multi_cell(col_width, line_height_trivia_ans_hint, answer_text_clean)
            
            hint_text_clean = clean_text_for_latin1(translate_text_with_ai(f"Hint: {item.get('hint', '')}", current_language, client_ai))
            pdf.multi_cell(col_width, line_height_trivia_ans_hint, hint_text_clean)
            
            current_y_col1 = pdf.get_y() + section_spacing_normal # Update Y and add spacing
            pdf.set_y(current_y_col1) # Ensure position is updated

    # Column 2 (Right Column)
    pdf.set_left_margin(page_width / 2 + 5) # Left margin for right column = page_width / 2 + half_gutter
    pdf.set_right_margin(right_margin)
    pdf.set_x(page_width / 2 + 5) # Set X for the second column
    pdf.set_y(current_y_col2) # Start content at the same Y level

    # Born on this Day
    pdf.set_font("Arial", "B", section_title_font_size)
    pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(translate_text_with_ai("Born on this Day", current_language, client_ai)))
    current_y_col2 += line_height_normal
    pdf.set_font("Arial", "", article_text_font_size) # Ensure font is not bold for article text
    pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(data.get('born_article', '')))
    current_y_col2 = pdf.get_y() + section_spacing_normal
    pdf.set_y(current_y_col2)

    # Did You Know?
    if data.get('did_you_know_section'): # Use .get() to check if key exists
        pdf.set_font("Arial", "B", section_title_font_size)
        pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(translate_text_with_ai("Did You Know?", current_language, client_ai))) # Translated
        current_y_col2 += line_height_normal
        pdf.set_font("Arial", "", article_text_font_size)
        for i, fact in enumerate(data['did_you_know_section']):
            pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(f"- {fact}")) # Add bullet point back
            current_y_col2 = pdf.get_y() # Update Y for each fact
        current_y_col2 += section_spacing_normal # Add spacing after all facts
        pdf.set_y(current_y_col2)

    # Memory Prompts
    if data.get('memory_prompt_section'):
        pdf.set_font("Arial", "B", section_title_font_size)
        pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(translate_text_with_ai("Memory Prompts:", current_language, client_ai))) # Translated
        current_y_col2 += line_height_normal
        pdf.set_font("Arial", "", article_text_font_size)
        for prompt in data['memory_prompt_section']:
            pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(f"• {prompt}")) # Add bullet point
            current_y_col2 = pdf.get_y()
        current_y_col2 += section_spacing_normal
        pdf.set_y(current_y_col2)

    # Local History Fact
    pdf.set_font("Arial", "B", section_title_font_size)
    pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(translate_text_with_ai("Local History Fact:", current_language, client_ai))) # Translated
    current_y_col2 += line_height_normal
    pdf.set_font("Arial", "", article_text_font_size)
    pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(data.get('local_history_section', '')))
    current_y_col2 = pdf.get_y() + section_spacing_normal
    pdf.set_y(current_y_col2)

    # Add Page 2
    pdf.add_page()
    pdf.set_left_margin(left_margin_p2)
    pdf.set_right_margin(right_margin_p2)

    # About Us Title
    pdf.set_y(20)
    pdf.set_font("Arial", "B", 24)
    pdf.cell(0, 10, clean_text_for_latin1(translate_text_with_ai("About Us", current_language, client_ai)), align='C')
    pdf.ln(15)

    pdf.set_font("Arial", "", 12)
    about_us_text = translate_text_with_ai(
        "Welcome to 'This Day in History', your daily dose of fascinating facts and memories! Our mission is to bring you engaging historical content, fun trivia, and thought-provoking prompts to enrich your day. We believe in making history accessible and enjoyable for everyone, fostering curiosity and connection through shared moments of the past. Thank you for being a part of our journey!",
        current_language, client_ai
    )
    pdf.multi_cell(content_width_p2, 7, clean_text_for_latin1(about_us_text))
    pdf.ln(15)

    # Contact Info
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, clean_text_for_latin1(translate_text_with_ai("Contact Us", current_language, client_ai)), align='C')
    pdf.ln(10)

    pdf.set_font("Arial", "", 12)
    contact_email = translate_text_with_ai("Email:", current_language, client_ai)
    pdf.cell(0, 7, clean_text_for_latin1(f"{contact_email} support@thisdayinhistoryapp.com"), 0, 1, 'C')
    contact_website = translate_text_with_ai("Website:", current_language, client_ai)
    pdf.cell(0, 7, clean_text_for_latin1(f"{contact_website} www.thisdayinhistoryapp.com"), 0, 1, 'C')
    pdf.ln(15)

    # Placeholder for a Logo (Example - you can replace with actual image logic)
    # For a real app, you'd embed an image here.
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 5, clean_text_for_latin1(translate_text_with_ai("[ Placeholder for App Logo ]", current_language, client_ai)), align='C')
    pdf.ln(10)


    # Base64 encode the PDF for download
    pdf_output = pdf.output(dest='S').encode('latin-1')
    return base64.b64encode(pdf_output).decode('latin-1')


# --- Page Navigation ---
def set_page(page_name):
    st.session_state['current_page'] = page_name

# --- User Authentication Functions ---
def authenticate_user(username, password):
    users = get_users_from_sheet()
    if username in users and users[username] == password:
        st.session_state['is_authenticated'] = True
        st.session_state['logged_in_username'] = username
        log_event("login", username)
        return True
    return False

def register_user(username, password, email):
    users = get_users_from_sheet()
    if username in users:
        st.error("Username already exists. Please choose a different username.")
        return False
    if save_new_user_to_sheet(username, password, email):
        st.success("Registration successful! You can now log in.")
        log_event("registration", username)
        return True
    return False

# --- Helper to reset trivia state for a new day/fetch ---
def reset_trivia_state():
    st.session_state['trivia_question_states'] = {}
    st.session_state['hints_remaining'] = 3
    st.session_state['current_trivia_score'] = 0
    st.session_state['total_possible_daily_trivia_score'] = 0
    st.session_state['score_logged_today'] = False

# --- Main Application Page ---
def show_main_app_page():
    st.title(translate_text_with_ai("This Day in History", st.session_state['preferred_language'], client_ai))
    
    st.info(
        translate_text_with_ai(
            "Welcome! You can download the daily content as a printable PDF. "
            "Customize the masthead for your company (e.g., 'Arbor Courts Gazette') by entering text in the 'PDF Customization' section below. "
            "On the left-hand navigation menu, you can customize your language and translate the entire page and PDF using the 'Display Language' dropdown.",
            st.session_state['preferred_language'],
            client_ai
        )
    )

    today = date.today()
    
    # Date Input
    selected_date = st.date_input(
        translate_text_with_ai("Select a Date", st.session_state['preferred_language'], client_ai),
        value=today,
        max_value=today,
        key='date_selector'
    )

    # Only fetch new data if the date has changed or it's a new day and no data is present
    # or if raw_fetched_data is empty (e.g., initial load or failed fetch)
    if st.session_state['last_fetched_date'] != selected_date or st.session_state['raw_fetched_data'] == _INITIAL_EMPTY_DATA:
        with st.spinner(translate_text_with_ai("Fetching today's history...", st.session_state['preferred_language'], client_ai)):
            # Clear previous trivia states and scores if date changes
            reset_trivia_state() 
            st.session_state['raw_fetched_data'] = get_this_day_in_history_facts(
                selected_date.day, selected_date.month, st.session_state['logged_in_username'], client_ai,
                difficulty=st.session_state['difficulty'], # Pass difficulty
                local_city=st.session_state['local_city'], # Pass local city
                local_state_country=st.session_state['local_state_country'] # Pass local state/country
            )
            st.session_state['last_fetched_date'] = selected_date
            # Translate raw data to preferred language
            st.session_state['daily_data'] = translate_content(
                st.session_state['raw_fetched_data'],
                st.session_state['preferred_language'],
                client_ai
            )
        st.experimental_rerun() # Rerun to display translated content immediately

    # If data is present (either freshly fetched or from session state)
    if st.session_state['daily_data']:
        st.subheader(translate_text_with_ai("On This Date", st.session_state['preferred_language'], client_ai))
        st.markdown(st.session_state['daily_data']['event_article'])

        st.subheader(translate_text_with_ai("Born on This Day", st.session_state['preferred_language'], client_ai))
        st.markdown(st.session_state['daily_data']['born_article'])

        st.subheader(translate_text_with_ai("Fun Fact", st.session_state['preferred_language'], client_ai))
        st.markdown(st.session_state['daily_data']['fun_fact_section'])
        
        st.subheader(translate_text_with_ai("Local History Fact", st.session_state['preferred_language'], client_ai))
        st.markdown(st.session_state['daily_data']['local_history_section'])

        st.subheader(translate_text_with_ai("Did You Know?", st.session_state['preferred_language'], client_ai))
        for fact in st.session_state['daily_data']['did_you_know_section']:
            st.markdown(f"- {fact}")

        st.subheader(translate_text_with_ai("Memory Prompts", st.session_state['preferred_language'], client_ai))
        for prompt in st.session_state['daily_data']['memory_prompt_section']:
            st.markdown(f"• {prompt}")
        
        st.subheader(translate_text_with_ai("PDF Customization", st.session_state['preferred_language'], client_ai))
        st.session_state['custom_masthead_text'] = st.text_input(
            translate_text_with_ai("Enter custom text for PDF masthead (e.g., 'The Arbor Courts Gazette'):", st.session_state['preferred_language'], client_ai),
            value=st.session_state['custom_masthead_text'],
            placeholder=translate_text_with_ai("Leave empty for default masthead", st.session_state['preferred_language'], client_ai),
            key="custom_masthead_input"
        )


        if st.button(translate_text_with_ai("Generate Printable PDF", st.session_state['preferred_language'], client_ai)):
            with st.spinner(translate_text_with_ai("Generating PDF...", st.session_state['preferred_language'], client_ai)):
                today_date_formatted = selected_date.strftime("%B %d, %Y")
                
                # Pass the raw data for PDF generation to ensure original English is used for untranslated parts in PDF.
                # The generate_full_history_pdf function will handle translation for other parts.
                pdf_output_b64 = generate_full_history_pdf(
                    st.session_state['raw_fetched_data'],
                    today_date_formatted,
                    st.session_state['logged_in_username'],
                    st.session_state['preferred_language'], # Pass preferred language to PDF generator
                    st.session_state['custom_masthead_text'] # Pass custom masthead text
                )
                
                # Use markdown with HTML to create a download link for the PDF
                st.markdown(
                    f'<a href="data:application/pdf;base64,{pdf_output_b64}" download="This_Day_in_History_{selected_date}.pdf">'
                    f'<button style="background-color:#4CAF50;color:white;border:none;padding:10px 20px;text-align:center;text-decoration:none;display:inline-block;font-size:16px;margin:4px 2px;cursor:pointer;border-radius:8px;">'
                    f'{translate_text_with_ai("Download PDF", st.session_state["preferred_language"], client_ai)}'
                    f'</button></a>',
                    unsafe_allow_html=True
                )
        
        st.markdown("---") # Separator

        if st.session_state['raw_fetched_data'] and st.session_state['raw_fetched_data']['trivia_section']:
            # The trivia section remains in raw_fetched_data (English) and is displayed in show_trivia_page
            # The actual questions and answers for trivia are NOT translated because check_partial_correctness_with_ai relies on original English.
            st.button(translate_text_with_ai("🌟 Play Today's Trivia!", st.session_state['preferred_language'], client_ai), on_click=lambda: set_page('trivia_page'))
        else:
            st.info(translate_text_with_ai("No trivia available for this date. Please try another date or check back later.", st.session_state['preferred_language'], client_ai))

        st.markdown("---") # Separator


# --- Trivia Page ---
def show_trivia_page():
    st.title(translate_text_with_ai("Daily Trivia Challenge!", st.session_state['preferred_language'], client_ai))
    
    st.write(translate_text_with_ai(f"Welcome, {st.session_state['logged_in_username']}! Test your knowledge.", st.session_state['preferred_language'], client_ai))
    
    st.button(translate_text_with_ai("⬅ Back to Main Page", st.session_state['preferred_language'], client_ai), on_click=lambda: set_page('main_app'))
    st.markdown("---")

    if not st.session_state['raw_fetched_data'] or not st.session_state['raw_fetched_data']['trivia_section']:
        st.warning(translate_text_with_ai("No trivia questions available for this date. Please go back to the main page and select a date with content.", st.session_state['preferred_language'], client_ai))
        return

    trivia_questions = st.session_state['raw_fetched_data']['trivia_section'] # Use raw data for trivia

    st.subheader(translate_text_with_ai(f"Your Current Score: {st.session_state['current_trivia_score']} / {st.session_state['total_possible_daily_trivia_score']}", st.session_state['preferred_language'], client_ai))
    st.info(translate_text_with_ai(f"Hints Remaining: {st.session_state['hints_remaining']}", st.session_state['preferred_language'], client_ai))
    
    # Initialize total possible score
    if st.session_state['total_possible_daily_trivia_score'] == 0:
        st.session_state['total_possible_daily_trivia_score'] = len(trivia_questions) * 10 # 10 points per question initially

    for i, item in enumerate(trivia_questions):
        question_key = f"q_{i}"
        
        # Initialize state for this question if not already present
        if question_key not in st.session_state['trivia_question_states']:
            st.session_state['trivia_question_states'][question_key] = {
                'user_answer': '',
                'is_correct': False,
                'feedback': '',
                'hint_revealed': False,
                'attempts': 0,
                'out_of_chances': False,
                'points_earned': 0, # Points for this specific question
                'related_article_content': None # Stores generated article for this question
            }
        
        q_state = st.session_state['trivia_question_states'][question_key]

        st.markdown(f"### {translate_text_with_ai('Question', st.session_state['preferred_language'], client_ai)} {i+1}:")
        st.write(translate_text_with_ai(item['question'], st.session_state['preferred_language'], client_ai)) # Translate question for display

        # User input for answer
        user_input = st.text_input(
            translate_text_with_ai("Your Answer:", st.session_state['preferred_language'], client_ai),
            value=q_state['user_answer'],
            key=f"user_answer_{i}",
            disabled=q_state['is_correct'] or q_state['out_of_chances'] # Disable if correct or out of chances
        )

        # Update user_answer in state immediately when input changes
        if user_input != q_state['user_answer']:
            st.session_state['trivia_question_states'][question_key]['user_answer'] = user_input
            # Reset feedback if user changes answer
            st.session_state['trivia_question_states'][question_key]['feedback'] = ''
            # If they change the answer after being out of chances, give them another chance
            if q_state['out_of_chances'] and not q_state['is_correct']:
                st.session_state['trivia_question_states'][question_key]['out_of_chances'] = False
                st.session_state['trivia_question_states'][question_key]['attempts'] = 0


        col1, col2 = st.columns([1, 1])

        # Check Answer Button
        with col1:
            if st.button(translate_text_with_ai("Check Answer", st.session_state['preferred_language'], client_ai), key=f"check_btn_{i}", disabled=q_state['is_correct'] or q_state['out_of_chances']):
                q_state['attempts'] += 1
                processed_user_answer = user_input.strip().lower()
                processed_correct_answer = item['answer'].strip().lower()

                is_correct = False
                feedback_message = ""

                if processed_user_answer == processed_correct_answer:
                    is_correct = True
                    feedback_message = translate_text_with_ai("🎉 Correct! Well done!", st.session_state['preferred_language'], client_ai)
                    if not q_state['is_correct']: # Only award points if not already correct
                        st.session_state['current_trivia_score'] += 10 # Award points
                        q_state['points_earned'] = 10
                elif check_partial_correctness_with_ai(processed_user_answer, processed_correct_answer, client_ai):
                    is_correct = True
                    feedback_message = translate_text_with_ai("✅ Close enough! That's correct!", st.session_state['preferred_language'], client_ai)
                    if not q_state['is_correct']:
                        st.session_state['current_trivia_score'] += 10 # Award points
                        q_state['points_earned'] = 10
                else:
                    if q_state['attempts'] < 3: # Allow up to 3 attempts
                        feedback_message = translate_text_with_ai(f"❌ Incorrect. You have {3 - q_state['attempts']} attempts left.", st.session_state['preferred_language'], client_ai)
                    else:
                        feedback_message = translate_text_with_ai(f"❌ Incorrect. The correct answer was: **{item['answer']}**", st.session_state['preferred_language'], client_ai)
                        q_state['out_of_chances'] = True # Mark as out of chances

                q_state['is_correct'] = is_correct
                q_state['feedback'] = feedback_message
                st.session_state['trivia_question_states'][question_key] = q_state # Update state
                st.experimental_rerun() # Rerun to show feedback

        # Hint Button
        with col2:
            if st.button(translate_text_with_ai("Get Hint", st.session_state['preferred_language'], client_ai), key=f"hint_btn_{i}", disabled=q_state['hint_revealed'] or st.session_state['hints_remaining'] <= 0 or q_state['is_correct']):
                if st.session_state['hints_remaining'] > 0:
                    st.session_state['hints_remaining'] -= 1
                    q_state['hint_revealed'] = True
                    q_state['feedback'] = translate_text_with_ai(f"💡 Hint: {item['hint']}", st.session_state['preferred_language'], client_ai)
                    st.session_state['trivia_question_states'][question_key] = q_state
                    st.experimental_rerun()
                else:
                    st.warning(translate_text_with_ai("You have no hints left for today!", st.session_state['preferred_language'], client_ai))
        
        # Display feedback if any
        if q_state['feedback']:
            if q_state['is_correct']:
                st.success(q_state['feedback'])
            elif q_state['hint_revealed'] and "Hint:" in q_state['feedback']:
                st.info(q_state['feedback'])
            else:
                st.error(q_state['feedback'])

        # Show Explanation Button (only if correct or out of chances)
        if (q_state['is_correct'] or q_state['out_of_chances']) and not q_state['related_article_content']:
            if st.button(translate_text_with_ai("Show Explanation", st.session_state['preferred_language'], client_ai), key=f"show_explanation_btn_{i}"):
                with st.spinner(translate_text_with_ai("Generating explanation...", st.session_state['preferred_language'], client_ai)):
                    # Generate and store the article content
                    q_state['related_article_content'] = generate_related_trivia_article(
                        item['question'], item['answer'], client_ai
                    )
                    st.session_state['trivia_question_states'][question_key] = q_state
                    st.experimental_rerun() # Rerun to display the generated article

        if q_state['related_article_content']:
            st.markdown(translate_text_with_ai("**Explanation:**", st.session_state['preferred_language'], client_ai))
            st.info(translate_text_with_ai(q_state['related_article_content'], st.session_state['preferred_language'], client_ai))
        
        st.markdown("---") # Separator between questions

    # Log score once all questions are answered or user decides to log
    all_answered = all(s['is_correct'] or s['out_of_chances'] for s in st.session_state['trivia_question_states'].values())
    if all_answered and not st.session_state['score_logged_today']:
        if st.button(translate_text_with_ai("Log My Score!", st.session_state['preferred_language'], client_ai)):
            if log_trivia_score(st.session_state['logged_in_username'], st.session_state['current_trivia_score']):
                st.success(translate_text_with_ai("Your score has been logged!", st.session_state['preferred_language'], client_ai))
                st.session_state['score_logged_today'] = True # Prevent multiple logs for the same day/score
            else:
                st.error(translate_text_with_ai("Failed to log score. Please try again.", st.session_state['preferred_language'], client_ai))

    st.subheader(translate_text_with_ai("Leaderboard", st.session_state['preferred_language'], client_ai))
    leaderboard_data = get_leaderboard_data()
    if leaderboard_data:
        for username, score in leaderboard_data:
            st.write(f"• {username}: {score} {translate_text_with_ai('points', st.session_state['preferred_language'], client_ai)}")
    else:
        st.info(translate_text_with_ai("No scores logged yet. Be the first!", st.session_state['preferred_language'], client_ai))

    st.markdown("---")
    st.button(translate_text_with_ai("⬅ Back to Main Page", st.session_state['preferred_language'], client_ai), on_click=lambda: set_page('main_app'), key="back_from_trivia_bottom")


# --- Login/Registration Page ---
def show_login_page():
    st.title("Welcome to This Day in History")

    st.subheader("Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_button = st.form_submit_button("Login")

        if login_button:
            if authenticate_user(username, password):
                st.success(f"Welcome, {username}!")
                set_page('main_app')
                st.experimental_rerun()
            else:
                st.error("Invalid username or password.")

    st.subheader("Register New User")
    with st.form("register_form"):
        new_username = st.text_input("New Username")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        email = st.text_input("Email (Optional)")
        register_button = st.form_submit_button("Register")

        if register_button:
            if new_password == confirm_password:
                if register_user(new_username, new_password, email):
                    # No rerun here, success message is shown, user can then log in
                    pass 
                else:
                    st.error("Registration failed. Username might already exist or an error occurred.")
            else:
                st.error("Passwords do not match.")
    
    st.markdown("---")
    st.subheader("Send Us Your Feedback!")
    with st.form("feedback_form"):
        feedback_username = st.text_input("Your Name/Contact (Optional)", value=st.session_state['logged_in_username'] if st.session_state['is_authenticated'] else "")
        feedback_message = st.text_area("Your Feedback")
        submit_feedback_button = st.form_submit_button("Submit Feedback")

        if submit_feedback_button:
            if feedback_message:
                if log_feedback(feedback_username, feedback_message):
                    st.success("Thank you for your feedback!")
                else:
                    st.error("Failed to submit feedback. Please try again.")
            else:
                st.warning("Please enter some feedback before submitting.")


# --- Sidebar ---
with st.sidebar:
    st.image("https://github.com/resense-apps/this-day-in-history/blob/main/assets/Resense_This_Day_in_History_Logo.png?raw=true", width=250)
    st.markdown("---")

    if st.session_state['is_authenticated']:
        st.write(translate_text_with_ai(f"Logged in as: {st.session_state['logged_in_username']}", st.session_state['preferred_language'], client_ai))
        st.markdown("---")

        st.subheader(translate_text_with_ai("Daily Content Preferences", st.session_state['preferred_language'], client_ai))
        
        # Difficulty selection
        st.session_state['difficulty'] = st.selectbox(
            translate_text_with_ai("Select Difficulty", st.session_state['preferred_language'], client_ai),
            options=['Easy', 'Medium', 'Hard'],
            index=['Easy', 'Medium', 'Hard'].index(st.session_state['difficulty']),
            key='difficulty_select',
            help=translate_text_with_ai("Adjust the complexity of generated content and trivia.", st.session_state['preferred_language'], client_ai)
        )

        # Local History Input
        st.markdown(translate_text_with_ai("### Local History Focus (Optional)", st.session_state['preferred_language'], client_ai))
        st.session_state['local_city'] = st.text_input(
            translate_text_with_ai("Your City:", st.session_state['preferred_language'], client_ai),
            value=st.session_state['local_city'],
            key="local_city_input",
            help=translate_text_with_ai("Enter a city for local history facts (e.g., 'Philadelphia').", st.session_state['preferred_language'], client_ai)
        )
        st.session_state['local_state_country'] = st.text_input(
            translate_text_with_ai("State/Country:", st.session_state['preferred_language'], client_ai),
            value=st.session_state['local_state_country'],
            key="local_state_country_input",
            help=translate_text_with_ai("Enter the corresponding state or country (e.g., 'Pennsylvania, USA').", st.session_state['preferred_language'], client_ai)
        )
        # Clear local history input button
        if st.button(translate_text_with_ai("Clear Local History Settings", st.session_state['preferred_language'], client_ai), key="clear_local_history_btn"):
            st.session_state['local_city'] = ""
            st.session_state['local_state_country'] = ""
            st.experimental_rerun() # Rerun to clear the input fields


        st.markdown("---")
        st.subheader(translate_text_with_ai("Language Settings", st.session_state['preferred_language'], client_ai))
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
    # Default to main_app if current_page is somehow not set to a valid page
    else:
        st.session_state['current_page'] = 'login_page' # Fallback to login if state is bad
        show_login_page() # Ensure login page is shown if not authenticated or page not set
