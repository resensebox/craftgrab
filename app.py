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
    section_spacing_normal = 5 # Define page 2 margins at the beginning left_margin_p2 = 25 right_margin_p2 = 25 content_width_p2 = page_width - left_margin_p2 - right_margin_p2 # --- Masthead (Page 1) --- pdf.set_y(10) # Start from top pdf.set_x(left_margin) pdf.set_font("Times", "B", title_font_size) # Large, bold font for the title # Use custom masthead text if provided, otherwise default masthead_to_display = custom_masthead_text if custom_masthead_text and custom_masthead_text.strip() else "The Daily Resense Register" pdf.cell(0, 15, clean_text_for_latin1(translate_text_with_ai(masthead_to_display, current_language, client_ai)), align='C') # Translated pdf.ln(15) # Separator line pdf.set_line_width(0.5) pdf.line(left_margin, pdf.get_y(), page_width - right_margin, pdf.get_y()) pdf.ln(8) pdf.set_font("Arial", "", date_font_size) pdf.cell(0, 5, today_date_str.upper(), align='C') # Date below the title pdf.ln(15) pdf.set_line_width(0.2) # Thinner line for content sections pdf.line(left_margin, pdf.get_y(), page_width - right_margin, pdf.get_y()) pdf.ln(8) # --- Two-Column Layout for Page 1 --- # Store initial Y for content columns to ensure they start at the same height start_y_content = pdf.get_y() # Track current Y for each column current_y_col1 = start_y_content current_y_col2 = start_y_content # Column 1 (Left Column) pdf.set_left_margin(left_margin) pdf.set_right_margin(page_width / 2 + 5) # Right margin for left column = page_width / 2 + half_gutter pdf.set_x(left_margin) # Set X for the first column pdf.set_y(current_y_col1) # Start content at the same Y level # On This Date pdf.set_font("Arial", "B", section_title_font_size) pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(translate_text_with_ai("On This Date", current_language, client_ai))) current_y_col1 += line_height_normal # Update Y after title # Use .get() with a default empty string to prevent TypeError if AI returns None for this field pdf.set_font("Arial", "", article_text_font_size) # Ensure font is not bold for article text pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(data.get('event_article', ''))) current_y_col1 = pdf.get_y() + section_spacing_normal # Update Y and add spacing pdf.set_y(current_y_col1) # Ensure position is updated # Fun Fact pdf.set_font("Arial", "B", section_title_font_size) pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(translate_text_with_ai("Fun Fact:", current_language, client_ai))) # Translated current_y_col1 += line_height_normal # Use .get() with a default empty string pdf.set_font("Arial", "", article_text_font_size) # Ensure font is not bold for article text pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(data.get('fun_fact_section', ''))) current_y_col1 = pdf.get_y() + section_spacing_normal # Update Y and add spacing pdf.set_y(current_y_col1) # Daily Trivia if data.get('trivia_section'): # Use .get() to check if 'trivia_section' key exists and is not empty/None pdf.set_font("Arial", "B", section_title_font_size) pdf.multi_cell(col_width, line_height_normal, "Daily Trivia") # NOT translated current_y_col1 += line_height_normal # Font for trivia questions is intentionally bolded, and answers/hints are not. # Loop through the first 4 trivia questions for the PDF for i, item in enumerate(data['trivia_section'][:4]): # Limit to 4 questions for PDF # Use .get() with default empty string for question, answer, hint question_text_clean = clean_text_for_latin1(f"{chr(97+i)}. - {item.get('question', '')}") # Added hyphen answer_text_clean = clean_text_for_latin1(f"Answer: {item.get('answer', '')}") # NOT translated hint_text_clean = clean_text_for_latin1(f"Hint: {item.get('hint', '')}") # NOT translated pdf.set_font("Arial", "B", trivia_q_font_size) # Bold for question pdf.multi_cell(col_width, line_height_trivia_ans_hint, question_text_clean) pdf.set_font("Arial", "", trivia_ans_hint_font_size) # Normal for answer pdf.multi_cell(col_width, line_height_trivia_ans_hint, answer_text_clean) pdf.multi_cell(col_width, line_height_trivia_ans_hint, hint_text_clean) current_y_col1 = pdf.get_y() + section_spacing_normal # Update Y and add spacing pdf.set_y(current_y_col1) # Ensure position is updated # Column 2 (Right Column) pdf.set_left_margin(page_width / 2 + 5) # Left margin for right column pdf.set_right_margin(right_margin) pdf.set_x(page_width / 2 + 5) # Set X for the second column pdf.set_y(current_y_col2) # Start content at the same Y level # Born on This Day pdf.set_font("Arial", "B", section_title_font_size) pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(translate_text_with_ai("Born on This Day", current_language, client_ai))) current_y_col2 += line_height_normal pdf.set_font("Arial", "", article_text_font_size) pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(data.get('born_article', ''))) current_y_col2 = pdf.get_y() + section_spacing_normal # Did You Know? pdf.set_y(current_y_col2) # Ensure position is updated pdf.set_font("Arial", "B", section_title_font_size) pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(translate_text_with_ai("Did You Know?", current_language, client_ai))) current_y_col2 += line_height_normal pdf.set_font("Arial", "", article_text_font_size) if data.get('did_you_know_section'): # Check if list is not empty for fact in data['did_you_know_section']: pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(fact)) current_y_col2 = pdf.get_y() # Adjust Y after each fact pdf.ln(1) # Small spacing between facts current_y_col2 += 1 pdf.ln(section_spacing_normal - 1) # Add remaining spacing after all facts # Memory Prompts pdf.set_y(current_y_col2) # Ensure position is updated pdf.set_font("Arial", "B", section_title_font_size) pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(translate_text_with_ai("Memory Prompts", current_language, client_ai))) current_y_col2 += line_height_normal pdf.set_font("Arial", "", article_text_font_size) if data.get('memory_prompt_section'): # Check if list is not empty for prompt_text in data['memory_prompt_section']: pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(prompt_text)) current_y_col2 = pdf.get_y() # Adjust Y after each prompt pdf.ln(1) # Small spacing between prompts current_y_col2 += 1 pdf.ln(section_spacing_normal - 1) # Local History Fact pdf.set_y(current_y_col2) # Ensure position is updated pdf.set_font("Arial", "B", section_title_font_size) pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(translate_text_with_ai("Local History Fact", current_language, client_ai))) current_y_col2 += line_height_normal pdf.set_font("Arial", "", article_text_font_size) pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(data.get('local_history_section', ''))) # --- Remaining Trivia Question on Page 2 (if it existed) --- if len(data.get('trivia_section', [])) > 4: # Check if there's a 5th question for page 2 pdf.add_page() # New page for the 5th trivia question pdf.set_left_margin(left_margin) pdf.set_right_margin(right_margin) pdf.set_x(left_margin) pdf.set_y(20) # Start a bit lower on the new page pdf.set_font("Arial", "B", section_title_font_size) pdf.multi_cell(0, line_height_normal, "Daily Trivia (Continued)") # NOT translated pdf.ln(section_spacing_normal) item = data['trivia_section'][4] # The 5th question question_text_clean = clean_text_for_latin1(f"e. - {item.get('question', '')}") # Ensure it's labeled 'e.' answer_text_clean = clean_text_for_latin1(f"Answer: {item.get('answer', '')}") hint_text_clean = clean_text_for_latin1(f"Hint: {item.get('hint', '')}") pdf.set_font("Arial", "B", trivia_q_font_size) # Bold for question pdf.multi_cell(0, line_height_trivia_ans_hint, question_text_clean) pdf.set_font("Arial", "", trivia_ans_hint_font_size) # Normal for answer pdf.multi_cell(0, line_height_trivia_ans_hint, answer_text_clean) pdf.multi_cell(0, line_height_trivia_ans_hint, hint_text_clean) pdf.ln(section_spacing_normal * 2) # Extra space before About Us # --- Page 2: About Us, Logo, Contact (always on a new page) --- else: # If no 5th trivia question, add page 2 directly pdf.add_page() pdf.set_auto_page_break(True, margin=15) # Ensure auto page break is on for this page as well pdf.set_left_margin(left_margin_p2) # Use specific margins for page 2 pdf.set_right_margin(right_margin_p2) # About Us Section pdf.set_y(20) pdf.set_font("Arial", "B", 16) pdf.multi_cell(content_width_p2, 10, clean_text_for_latin1(translate_text_with_ai("About Us", current_language, client_ai)), align='C') # Translated pdf.ln(5) pdf.set_font("Arial", "", 10) about_us_text = """
The Daily Resense Register is dedicated to bringing you a personalized journey through history, combining factual events with engaging content designed to spark memory and curiosity. Our mission is to make learning about the past an interactive and enriching experience every day. We believe that understanding our history helps us appreciate the present and look forward to the future.
""" # Add more text for the About Us section as needed pdf.multi_cell(content_width_p2, 6, clean_text_for_latin1(translate_text_with_ai(about_us_text, current_language, client_ai))) # Translated pdf.ln(10) # Placeholder for Logo (replace with actual image embedding if available) logo_placeholder_text = clean_text_for_latin1(translate_text_with_ai("~ Your Logo Here ~", current_language, client_ai)) # Translated pdf.set_font("Arial", "I", 12) # Italic font for placeholder pdf.multi_cell(content_width_p2, 7, logo_placeholder_text, align='C') pdf.ln(10) # Contact Information pdf.set_font("Arial", "B", 14) pdf.multi_cell(content_width_p2, 8, clean_text_for_latin1(translate_text_with_ai("Contact Us", current_language, client_ai)), align='C') # Translated pdf.ln(3) pdf.set_font("Arial", "", 10) contact_info = """
Email: support@dailyresenseregister.com
Website: www.dailyresenseregister.com
Follow us on social media for more historical insights and updates!
""" # Add more contact info as needed pdf.multi_cell(content_width_p2, 5, clean_text_for_latin1(translate_text_with_ai(contact_info, current_language, client_ai)), align='C') # Translated # Footer for Page 2 pdf.set_y(-20) # Position at 20mm from bottom pdf.set_font("Arial", "I", 8) pdf.multi_cell(0, 5, clean_text_for_latin1(translate_text_with_ai(f"© {datetime.now().year} The Daily Resense Register. All rights reserved.", current_language, client_ai)), align='C') # Translated return base64.b64encode(pdf.output(dest='S').encode('latin-1')).decode('latin-1') # Return as base64 encoded string

# Dummy function for page navigation (if not already defined)
def set_page(page_name):
    st.session_state['current_page'] = page_name

# Dummy functions for showing pages (if not already defined)
def show_main_app_page():
    st.title(translate_text_with_ai("Main Application", st.session_state['preferred_language'], client_ai))
    st.write(translate_text_with_ai("Content for the main application goes here.", st.session_state['preferred_language'], client_ai))

def show_trivia_page():
    st.title(translate_text_with_ai("Trivia Game", st.session_state['preferred_language'], client_ai))
    st.write(translate_text_with_ai("Content for the trivia game goes here.", st.session_state['preferred_language'], client_ai))

def show_leaderboard_page():
    st.title(translate_text_with_ai("Leaderboard", st.session_state['preferred_language'], client_ai))
    st.write(translate_text_with_ai("Content for the leaderboard goes here.", st.session_state['preferred_language'], client_ai))

def show_feedback_page():
    st.title(translate_text_with_ai("Feedback", st.session_state['preferred_language'], client_ai))
    st.write(translate_text_with_ai("Content for the feedback page goes here.", st.session_state['preferred_language'], client_ai))


# --- Page Functions ---
def show_login_page():
    st.title("Login / Register")
    login_tab, register_tab = st.tabs(["Login", "Register"])

    users = get_users_from_sheet() # Fetch users at the start of the login page function

    with login_tab:
        st.subheader("Login")
        login_username = st.text_input("Username", key="login_username_input")
        login_password = st.text_input("Password", type="password", key="login_password_input")
        if st.button("Login", key="login_btn"):
            if login_username in users and users[login_username] == login_password:
                st.session_state['is_authenticated'] = True
                st.session_state['logged_in_username'] = login_username
                log_event("login", login_username)
                st.success("Logged in successfully!")
                st.rerun() # Rerun to switch to main app page
            else:
                st.error("Invalid username or password.")
                log_event("failed_login", login_username)

    with register_tab:
        st.subheader("Register New Account")
        new_username = st.text_input("New Username", key="register_username_input")
        new_password = st.text_input("New Password", type="password", key="register_password_input")
        confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password_input")
        new_email = st.text_input("Email (Optional)", key="register_email_input")

        if st.button("Register", key="register_btn"):
            if not new_username or not new_password:
                st.warning("Username and Password cannot be empty.")
            elif new_username in users:
                st.warning("Username already exists. Please choose a different one.")
            elif new_password != confirm_password:
                st.warning("Passwords do not match.")
            else:
                if save_new_user_to_sheet(new_username, new_password, new_email):
                    st.success("Account created successfully! You can now log in.")
                    log_event("registration", new_username)
                    # Clear registration fields
                    st.session_state['register_username_input'] = ""
                    st.session_state['register_password_input'] = ""
                    st.session_state['confirm_password_input'] = ""
                    st.session_state['register_email_input'] = ""
                    # Automatically switch to login tab or prompt user to log in
                    st.info("Please proceed to the Login tab.")
                else:
                    st.error("Failed to register account. Please try again.")

# --- Main App & Navigation Logic ---
if st.session_state['is_authenticated']:
    st.sidebar.title(translate_text_with_ai("Navigation", st.session_state['preferred_language'], client_ai))
    
    # Navigation buttons
    if st.sidebar.button(translate_text_with_ai("🏠 Main App", st.session_state['preferred_language'], client_ai), key="sidebar_main_app"):
        set_page('main_app')
    if st.sidebar.button(translate_text_with_ai("🧠 Trivia Game", st.session_state['preferred_language'], client_ai), key="sidebar_trivia_page"):
        set_page('trivia_page')
    if st.sidebar.button(translate_text_with_ai("🏆 Leaderboard", st.session_state['preferred_language'], client_ai), key="sidebar_leaderboard_page"):
        set_page('leaderboard_page')
    if st.sidebar.button(translate_text_with_ai("✉️ Feedback", st.session_state['preferred_language'], client_ai), key="sidebar_feedback_page"):
        set_page('feedback_page')

    st.sidebar.markdown("---") # Separator

    # Language Translation Option (moved here)
    st.sidebar.subheader(translate_text_with_ai("Language Settings", st.session_state['preferred_language'], client_ai))
    st.session_state['preferred_language'] = st.sidebar.selectbox(
        translate_text_with_ai("Display Language", st.session_state['preferred_language'], client_ai),
        options=["English", "Spanish", "French", "German", "Italian", "Portuguese"],
        index=["English", "Spanish", "French", "German", "Italian", "Portuguese"].index(st.session_state['preferred_language']),
        key='sidebar_language_select',
        help=translate_text_with_ai("Select the language for the daily content and PDF.", st.session_state['preferred_language'], client_ai)
    )

    st.sidebar.markdown("---") # Separator

    # Custom Content Option (moved below language)
    st.sidebar.subheader(translate_text_with_ai("Custom Content", st.session_state['preferred_language'], client_ai))
    st.session_state['custom_masthead_text'] = st.sidebar.text_input(
        translate_text_with_ai("PDF Masthead Text", st.session_state['preferred_language'], client_ai),
        value=st.session_state['custom_masthead_text'],
        help=translate_text_with_ai("Enter custom text to appear at the top of the generated PDF. (e.g., 'Grandma's Daily News')", st.session_state['preferred_language'], client_ai)
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
    elif st.session_state['current_page'] == 'leaderboard_page':
        show_leaderboard_page()
    elif st.session_state['current_page'] == 'feedback_page':
        show_feedback_page()
    # Default to main_app if current_page is somehow not set to a valid page
    else:
        st.session_state['current_page'] = 'main_app'
        show_main_app_page()

else:
    show_login_page()
