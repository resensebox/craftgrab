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
        
        # Parse multiple memory prompts into a list, splitting by newline and filtering empty strings
        memory_prompt_section = []
        if memory_prompt_match:
            raw_prompts = memory_prompt_match.group(1).strip()
            # Split by newline and clean each line
            for prompt_line in raw_prompts.split('\n'):
                cleaned_prompt = prompt_line.strip()
                # Remove any bullet points or hyphens that the AI might incorrectly add
                cleaned_prompt = re.sub(r'^\s*[\-\*•]\s*', '', cleaned_prompt)
                if cleaned_prompt: # Only add if not empty after cleaning
                    memory_prompt_section.append(cleaned_prompt)

        # Fallback if no prompts are found
        if not memory_prompt_section:
            memory_prompt_section = ["No memory prompts available.", "Consider your favorite childhood memory.", "What's a happy moment from your past week?"]

        # Local History Fact
        local_history_section_match = re.search(r"7\. Local History Fact:\s*(.*?)(?=\Z)", content, re.DOTALL)
        local_history_section = local_history_section_match.group(1).strip() if local_history_section_match else "No local history data available. Please try again."

        # Return structured data
        return {
            'event_article': event_article,
            'born_article': born_article,
            'fun_fact_section': fun_fact_section,
            'trivia_section': trivia_questions,
            'did_you_know_section': did_you_know_lines,
            'memory_prompt_section': memory_prompt_section,
            'local_history_section': local_history_section
        }

    except Exception as e:
        st.error(f"❌ Error fetching 'This Day in History' facts: {e}")
        return _INITIAL_EMPTY_DATA.copy() # Return initial dummy data on failure


# --- PDF Generation Functions ---

# Custom header for the PDF
def header(pdf, client_ai, current_language):
    pdf.set_font('Arial', 'B', 15)
    pdf.set_text_color(0, 0, 0) # Black text
    pdf.cell(0, 10, clean_text_for_latin1(translate_text_with_ai("The Daily Resense Register", current_language, client_ai)), 0, 1, 'C') # Main title

    if st.session_state.get('custom_masthead_text'):
        pdf.set_font('Arial', 'I', 10)
        pdf.multi_cell(0, 5, clean_text_for_latin1(translate_text_with_ai(st.session_state['custom_masthead_text'], current_language, client_ai)), align='C')
    
    pdf.ln(5)

# Page 1 content
def add_page_1_content(pdf, data, current_date, client_ai, current_language):
    # Title
    pdf.set_font('Arial', 'B', 18)
    pdf.set_text_color(0, 0, 0) # Black text
    pdf.cell(0, 10, clean_text_for_latin1(translate_text_with_ai(f"This Day in History: {current_date.strftime('%B %d, %Y')}", current_language, client_ai)), 0, 1, 'C')
    pdf.ln(10)

    # Event Article
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, clean_text_for_latin1(translate_text_with_ai("📜 Historical Event", current_language, client_ai)), 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 5, clean_text_for_latin1(translate_text_with_ai(data['event_article'], current_language, client_ai)))
    pdf.ln(5)

    # Born on this Day Article
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, clean_text_for_latin1(translate_text_with_ai("🎂 Born on This Day", current_language, client_ai)), 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 5, clean_text_for_latin1(translate_text_with_ai(data['born_article'], current_language, client_ai)))
    pdf.ln(5)

    # Fun Fact
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, clean_text_for_latin1(translate_text_with_ai("💡 Fun Fact", current_language, client_ai)), 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 5, clean_text_for_latin1(translate_text_with_ai(data['fun_fact_section'], current_language, client_ai)))
    pdf.ln(5)

    # Local History Fact
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, clean_text_for_latin1(translate_text_with_ai("🗺️ Local History Fact", current_language, client_ai)), 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 5, clean_text_for_latin1(translate_text_with_ai(data['local_history_section'], current_language, client_ai)))
    pdf.ln(5)

    # "Did You Know?"
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, clean_text_for_latin1(translate_text_with_ai("🤔 Did You Know?", current_language, client_ai)), 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    for i, fact in enumerate(data['did_you_know_section']):
        pdf.multi_cell(0, 5, clean_text_for_latin1(translate_text_with_ai(f"- {fact}", current_language, client_ai)))
    pdf.ln(5)

# Page 2 content
def add_page_2_content(pdf, data, trivia_question_states, client_ai, current_language):
    # Trivia Questions
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, clean_text_for_latin1(translate_text_with_ai("🧠 Daily Trivia Challenge", current_language, client_ai)), 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    for i, trivia_item in enumerate(data['trivia_section']):
        q_state = trivia_question_states.get(str(i), {})
        question = trivia_item['question']
        correct_answer = trivia_item['answer']
        user_answer = q_state.get('user_answer', 'Not answered')
        is_correct = q_state.get('is_correct')
        
        pdf.multi_cell(0, 5, clean_text_for_latin1(translate_text_with_ai(f"Q{i+1}: {question}", current_language, client_ai)))
        
        # Display user's answer and correctness (translated)
        if user_answer != 'Not answered':
            pdf.set_font('Arial', 'I', 9)
            pdf.multi_cell(0, 5, clean_text_for_latin1(translate_text_with_ai(f"Your Answer: {user_answer}", current_language, client_ai)))
            if is_correct is not None:
                correct_status = clean_text_for_latin1(translate_text_with_ai("Correct!", current_language, client_ai)) if is_correct else clean_text_for_latin1(translate_text_with_ai("Incorrect.", current_language, client_ai))
                pdf.multi_cell(0, 5, correct_status)
            pdf.set_font('Arial', '', 10) # Reset font

        # Always display the correct answer below the user's answer
        pdf.set_font('Arial', 'B', 9)
        pdf.multi_cell(0, 5, clean_text_for_latin1(translate_text_with_ai(f"Answer: {correct_answer}", current_language, client_ai)))
        pdf.set_font('Arial', '', 10) # Reset font

        # Display related article if available (translated)
        if q_state.get('related_article_content'):
            pdf.set_font('Arial', 'I', 9)
            pdf.multi_cell(0, 5, clean_text_for_latin1(translate_text_with_ai("Explanation:", current_language, client_ai)))
            pdf.multi_cell(0, 5, clean_text_for_latin1(translate_text_with_ai(q_state['related_article_content'], current_language, client_ai)))
            pdf.set_font('Arial', '', 10) # Reset font

        pdf.ln(2)

    pdf.ln(5)

    # Memory Prompts
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, clean_text_for_latin1(translate_text_with_ai("💭 Memory Prompts", current_language, client_ai)), 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    for i, prompt in enumerate(data['memory_prompt_section']):
        pdf.multi_cell(0, 5, clean_text_for_latin1(translate_text_with_ai(f"- {prompt}", current_language, client_ai)))
    pdf.ln(5)
    
    # Contact Info (adjust as needed)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 10, clean_text_for_latin1(translate_text_with_ai("Contact Us", current_language, client_ai)), 0, 1, 'C')
    pdf.set_font('Arial', '', 9)
    contact_info = "Email: info@resenseregister.com | Website: www.resenseregister.com"
    content_width_p2 = pdf.w - 2 * pdf.l_margin
    # Add more contact info as needed
    pdf.multi_cell(content_width_p2, 5, clean_text_for_latin1(translate_text_with_ai(contact_info, current_language, client_ai)), align='C') # Translated
    # Footer for Page 2
    pdf.set_y(-20) # Position at 20mm from bottom
    pdf.set_font("Arial", "I", 8)
    pdf.multi_cell(0, 5, clean_text_for_latin1(translate_text_with_ai(f"© {datetime.now().year} The Daily Resense Register. All rights reserved.", current_language, client_ai)), align='C') # Translated
    return base64.b64encode(pdf.output(dest='S').encode('latin-1')).decode('latin-1') # Return as base64 encoded string


def generate_pdf(current_date, daily_data, trivia_question_states, client_ai, current_language):
    pdf = FPDF('P', 'mm', 'A4')
    pdf.add_page()
    
    # Set up alias for num_pages for footer
    pdf.alias_nb_pages()

    # Page 1
    header(pdf, client_ai, current_language)
    add_page_1_content(pdf, daily_data, current_date, client_ai, current_language)

    # Page 2
    pdf.add_page()
    header(pdf, client_ai, current_language) # Add header to second page too
    return add_page_2_content(pdf, daily_data, trivia_question_states, client_ai, current_language)


# --- Helper Functions for UI Logic ---
def set_page(page_name):
    st.session_state['current_page'] = page_name
    st.rerun()

def reset_trivia_state():
    st.session_state['trivia_question_states'] = {}
    st.session_state['hints_remaining'] = 3
    st.session_state['current_trivia_score'] = 0
    st.session_state['total_possible_daily_trivia_score'] = 0
    st.session_state['score_logged_today'] = False

# --- User Authentication and Registration ---
def show_login_page():
    st.title("Login to Daily Resense Register")
    st.write("Please enter your credentials to access the app.")

    users = get_users_from_sheet() # Fetch users from Google Sheet

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_button = st.form_submit_button("Login")

        if login_button:
            if username in users and users[username] == password:
                st.session_state['is_authenticated'] = True
                st.session_state['logged_in_username'] = username
                log_event("login", username)
                st.success("Logged in successfully!")
                time.sleep(1) # Give time for success message to be seen
                set_page('main_app') # Redirect to main app
                st.rerun() # Ensure immediate page update
            else:
                st.error("Invalid username or password.")
    
    st.markdown("---")
    st.subheader("New User? Register Here!")
    with st.form("register_form"):
        new_username = st.text_input("New Username")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        new_email = st.text_input("Email (Optional)")
        register_button = st.form_submit_button("Register")

        if register_button:
            if new_username in users:
                st.error("Username already exists. Please choose a different one.")
            elif new_password != confirm_password:
                st.error("Passwords do not match.")
            elif len(new_username) < 3 or len(new_password) < 6:
                st.error("Username must be at least 3 characters and password at least 6 characters.")
            else:
                if save_new_user_to_sheet(new_username, new_password, new_email):
                    st.success("Registration successful! You can now log in.")
                    log_event("register", new_username)
                    time.sleep(1) # Give time for success message to be seen
                    # No explicit rerun needed here, as the form submission will trigger a rerun
                else:
                    st.error("Failed to register user. Please try again.")

def show_main_app_page():
    st.sidebar.title("App Settings")

    # Display logged-in username if authenticated
    if st.session_state['is_authenticated']:
        st.sidebar.success(f"Welcome, {st.session_state['logged_in_username']}!")

    # Date Selection
    today = date.today()
    # Default to a fixed date for consistent demo experience
    fixed_demo_date = date(today.year, 1, 1) # Jan 1st of current year
    
    selected_date = st.sidebar.date_input(
        "Select Date",
        value=fixed_demo_date, # Set default to Jan 1st
        min_value=date(1800, 1, 1),
        max_value=today
    )

    # Decade Selection
    current_year = datetime.now().year
    decade_options = ["None"] + [f"{y - (y % 10)}s" for y in range(current_year, 1899, -10)]
    preferred_decade = st.sidebar.selectbox(
        "Preferred Decade",
        options=decade_options,
        index=0
    )

    # Topic Selection
    topic_options = ["None", "Science", "Technology", "Arts", "Politics", "Sports", "War", "Culture", "Business"]
    topic = st.sidebar.selectbox(
        "Topic (Optional)",
        options=topic_options,
        index=0
    )

    # Difficulty Selection
    difficulty_options = ["Easy", "Medium", "Hard"]
    st.session_state['difficulty'] = st.sidebar.selectbox(
        "Trivia Difficulty",
        options=difficulty_options,
        index=1 # Default to Medium
    )

    # Local History Location Input
    st.sidebar.markdown("---")
    st.sidebar.subheader("Local History Preferences")
    st.session_state['local_city'] = st.sidebar.text_input("Your City (Optional)", value=st.session_state['local_city'], help="Enter your city for local historical facts.")
    st.session_state['local_state_country'] = st.sidebar.text_input("Your State/Country (Optional)", value=st.session_state['local_state_country'], help="e.g., California, USA or Ontario, Canada")

    # Masthead text for PDF
    st.sidebar.markdown("---")
    st.sidebar.subheader("PDF Customization")
    st.session_state['custom_masthead_text'] = st.sidebar.text_area(
        "Custom Masthead Text for PDF (Optional)",
        value=st.session_state['custom_masthead_text'],
        help="This text will appear below 'The Daily Resense Register' on the PDF."
    )

    # Language Selection (using preferred_language from session_state)
    st.session_state['preferred_language'] = st.sidebar.selectbox(
        "Display Language",
        options=["English", "Spanish", "French", "German", "Italian", "Portuguese"],
        index=["English", "Spanish", "French", "German", "Italian", "Portuguese"].index(st.session_state['preferred_language']),
        key='sidebar_language_select',
        help="Select the language for the daily content and PDF."
    )

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Log Out", key="sidebar_logout_btn"):
        log_event("logout", st.session_state['logged_in_username'])
        st.session_state['is_authenticated'] = False
        st.session_state['logged_in_username'] = ""
        set_page('login_page') # Go back to the login page (or main app if unauthenticated)
        st.rerun()

    st.title("The Daily Resense Register")
    st.header(f"Today's Edition: {selected_date.strftime('%B %d, %Y')}")

    # --- Fetch and Display Daily Data ---
    # Only fetch if data for the selected date is not already in session state
    # or if the selected language has changed from the one the data was last translated to
    if (st.session_state['daily_data'] is None or 
        st.session_state['last_fetched_date'] != selected_date or 
        st.session_state['daily_data'].get('language') != st.session_state['preferred_language']):

        with st.spinner(translate_text_with_ai("Fetching and translating today's historical data...", st.session_state['preferred_language'], client_ai)):
            # Always fetch raw data, then translate it
            raw_data_fetched = get_this_day_in_history_facts(
                selected_date.day,
                selected_date.month,
                st.session_state['logged_in_username'],
                client_ai,
                preferred_decade,
                topic,
                st.session_state['difficulty'],
                st.session_state['local_city'],
                st.session_state['local_state_country']
            )
            st.session_state['raw_fetched_data'] = raw_data_fetched # Store raw data

            # Translate the raw data to the preferred language for display
            translated_data = translate_content(raw_data_fetched.copy(), st.session_state['preferred_language'], client_ai)
            translated_data['language'] = st.session_state['preferred_language'] # Store the language this data was translated to
            
            st.session_state['daily_data'] = translated_data
            st.session_state['last_fetched_date'] = selected_date
            reset_trivia_state() # Reset trivia state for new data

    # Display Content
    data = st.session_state['daily_data']

    st.subheader(translate_text_with_ai("📜 Historical Event", st.session_state['preferred_language'], client_ai))
    st.write(data['event_article'])

    st.subheader(translate_text_with_ai("🎂 Born on This Day", st.session_state['preferred_language'], client_ai))
    st.write(data['born_article'])

    st.subheader(translate_text_with_ai("💡 Fun Fact", st.session_state['preferred_language'], client_ai))
    st.write(data['fun_fact_section'])

    st.subheader(translate_text_with_ai("🗺️ Local History Fact", st.session_state['preferred_language'], client_ai))
    st.write(data['local_history_section'])

    st.subheader(translate_text_with_ai("🤔 Did You Know?", st.session_state['preferred_language'], client_ai))
    for fact in data['did_you_know_section']:
        st.write(f"- {fact}")

    st.subheader(translate_text_with_ai("💭 Memory Prompts", st.session_state['preferred_language'], client_ai))
    for prompt in data['memory_prompt_section']:
        st.write(f"- {prompt}")

    st.markdown("---")
    st.subheader(translate_text_with_ai("🧠 Daily Trivia Challenge", st.session_state['preferred_language'], client_ai))
    if st.button(translate_text_with_ai("Start Trivia Challenge", st.session_state['preferred_language'], client_ai), key="start_trivia_btn"):
        set_page('trivia_page')
        st.rerun()

    st.markdown("---")
    st.subheader(translate_text_with_ai("Download Today's Register", st.session_state['preferred_language'], client_ai))
    if st.button(translate_text_with_ai("Generate and Download PDF", st.session_state['preferred_language'], client_ai), key="download_pdf_btn"):
        with st.spinner(translate_text_with_ai("Generating PDF...", st.session_state['preferred_language'], client_ai)):
            # Pass raw_fetched_data for trivia section as it's not translated for PDF display.
            # Only the main content is translated for PDF.
            pdf_data = generate_pdf(selected_date, st.session_state['raw_fetched_data'], st.session_state['trivia_question_states'], client_ai, st.session_state['preferred_language'])
            st.download_button(
                label=translate_text_with_ai("Click to Download", st.session_state['preferred_language'], client_ai),
                data=pdf_data,
                file_name=f"Daily_Resense_Register_{selected_date.strftime('%Y-%m-%d')}.pdf",
                mime="application/pdf"
            )
        st.success(translate_text_with_ai("PDF generated successfully!", st.session_state['preferred_language'], client_ai))


def show_trivia_page():
    st.title(translate_text_with_ai("🧠 Daily Trivia Challenge", st.session_state['preferred_language'], client_ai))
    
    # Back button to main app
    if st.button(translate_text_with_ai("⬅️ Back to Main App", st.session_state['preferred_language'], client_ai), key="back_to_main_btn"):
        set_page('main_app')
        st.rerun()

    st.markdown("---")
    
    trivia_questions = st.session_state['raw_fetched_data']['trivia_section'] # Use raw data for questions/answers
    if not trivia_questions:
        st.warning(translate_text_with_ai("No trivia questions available for today. Please go back to the main app and try fetching data again.", st.session_state['preferred_language'], client_ai))
        return

    # Initialize or reset total possible score if needed
    if st.session_state['total_possible_daily_trivia_score'] == 0:
        st.session_state['total_possible_daily_trivia_score'] = len(trivia_questions) * 10 # Assuming 10 points per question

    st.info(translate_text_with_ai(f"Hints remaining: {st.session_state['hints_remaining']}", st.session_state['preferred_language'], client_ai))
    st.success(translate_text_with_ai(f"Current Score: {st.session_state['current_trivia_score']} / {st.session_state['total_possible_daily_trivia_score']}", st.session_state['preferred_language'], client_ai))

    for i, trivia_item in enumerate(trivia_questions):
        q_index = str(i)
        
        # Initialize state for this question if it doesn't exist
        if q_index not in st.session_state['trivia_question_states']:
            st.session_state['trivia_question_states'][q_index] = {
                'user_answer': '',
                'is_correct': None,
                'feedback': '',
                'hint_revealed': False,
                'attempts': 0,
                'out_of_chances': False,
                'points_earned': 0,
                'related_article_content': None
            }

        q_state = st.session_state['trivia_question_states'][q_index]
        question = trivia_item['question']
        correct_answer = trivia_item['answer']
        hint = trivia_item['hint']

        st.markdown(f"**{translate_text_with_ai('Question', st.session_state['preferred_language'], client_ai)} {i+1}:** {question}")
        
        # Only allow input if not out of chances for this question
        if not q_state['out_of_chances']:
            user_answer = st.text_input(translate_text_with_ai("Your Answer", st.session_state['preferred_language'], client_ai), value=q_state['user_answer'], key=f"q{i}_answer_input")
            col1, col2 = st.columns([1, 1])

            with col1:
                check_btn_label = translate_text_with_ai("Check Answer", st.session_state['preferred_language'], client_ai)
                if st.button(check_btn_label, key=f"check_btn_{i}", type="primary"):
                    q_state['user_answer'] = user_answer # Update user's answer in state
                    q_state['attempts'] += 1

                    # Check for correctness: exact match or AI-assisted partial correctness
                    is_correct_exact = (user_answer.strip().lower() == correct_answer.strip().lower())
                    is_correct_partial = False
                    if not is_correct_exact:
                        is_correct_partial = check_partial_correctness_with_ai(user_answer, correct_answer, client_ai)

                    if is_correct_exact or is_correct_partial:
                        q_state['is_correct'] = True
                        q_state['feedback'] = translate_text_with_ai("🥳 Correct! Well done!", st.session_state['preferred_language'], client_ai)
                        if q_state['points_earned'] == 0: # Award points only once
                            q_state['points_earned'] = 10
                            st.session_state['current_trivia_score'] += 10
                        st.success(q_state['feedback'])
                    else:
                        q_state['is_correct'] = False
                        q_state['feedback'] = translate_text_for_latin1(translate_text_with_ai("🤔 Incorrect. Try again!", st.session_state['preferred_language'], client_ai))
                        st.error(q_state['feedback'])
                        if q_state['attempts'] >= 2: # Max 2 attempts
                            q_state['out_of_chances'] = True
                            st.warning(translate_text_for_latin1(translate_text_with_ai(f"You're out of chances for this question. The correct answer was: **{correct_answer}**", st.session_state['preferred_language'], client_ai)))
                    
                    # Generate related article if answer is correct or out of chances
                    if q_state['is_correct'] or q_state['out_of_chances']:
                        with st.spinner(translate_text_with_ai("Generating explanation...", st.session_state['preferred_language'], client_ai)):
                            q_state['related_article_content'] = generate_related_trivia_article(question, correct_answer, client_ai)
                            st.markdown(f"**{translate_text_with_ai('Explanation', st.session_state['preferred_language'], client_ai)}:**")
                            st.write(q_state['related_article_content'])
                    
                    st.session_state['trivia_question_states'][q_index] = q_state # Update session state explicitly
                    st.rerun() # Rerun to update feedback/score
            with col2:
                hint_btn_label = translate_text_with_ai("Get Hint (1 remaining)", st.session_state['preferred_language'], client_ai) if st.session_state['hints_remaining'] == 1 else translate_text_with_ai(f"Get Hint ({st.session_state['hints_remaining']} remaining)", st.session_state['preferred_language'], client_ai)
                if st.session_state['hints_remaining'] > 0 and not q_state['hint_revealed'] and st.button(hint_btn_label, key=f"hint_btn_{i}"):
                    q_state['hint_revealed'] = True
                    st.session_state['hints_remaining'] -= 1
                    st.info(translate_text_for_latin1(translate_text_with_ai(f"Hint: {hint}", st.session_state['preferred_language'], client_ai)))
                    st.session_state['trivia_question_states'][q_index] = q_state # Update session state explicitly
                    st.rerun() # Rerun to update hint count
                elif q_state['hint_revealed']:
                    st.info(translate_text_for_latin1(translate_text_with_ai(f"Hint: {hint}", st.session_state['preferred_language'], client_ai)))
                elif st.session_state['hints_remaining'] == 0 and not q_state['hint_revealed']:
                    st.button(translate_text_with_ai("No Hints Left", st.session_state['preferred_language'], client_ai), key=f"hint_btn_{i}_disabled", disabled=True)
        else: # Out of chances for this question
            st.write(translate_text_for_latin1(translate_text_with_ai("You're out of chances for this question.", st.session_state['preferred_language'], client_ai)))
            st.markdown(f"**{translate_text_for_latin1(translate_text_with_ai('Correct Answer', st.session_state['preferred_language'], client_ai))}:** {correct_answer}")
            if q_state.get('related_article_content'):
                st.markdown(f"**{translate_text_for_latin1(translate_text_with_ai('Explanation', st.session_state['preferred_language'], client_ai))}:**")
                st.write(q_state['related_article_content'])

        st.markdown("---") # Separator for questions

    # End of Trivia Section - Score Logging
    all_questions_attempted = all(s['out_of_chances'] or s['is_correct'] for s in st.session_state['trivia_question_states'].values())

    if all_questions_attempted and not st.session_state['score_logged_today']:
        st.subheader(translate_text_with_ai("Trivia Complete!", st.session_state['preferred_language'], client_ai))
        final_score = st.session_state['current_trivia_score']
        st.write(translate_text_with_ai(f"Your final score is: {final_score} / {st.session_state['total_possible_daily_trivia_score']}", st.session_state['preferred_language'], client_ai))

        if st.session_state['is_authenticated'] and st.button(translate_text_with_ai("Log My Score to Leaderboard", st.session_state['preferred_language'], client_ai), key="log_score_btn"):
            if log_trivia_score(st.session_state['logged_in_username'], final_score):
                st.success(translate_text_with_ai("Score logged successfully!", st.session_state['preferred_language'], client_ai))
                st.session_state['score_logged_today'] = True # Prevent logging multiple times
                st.rerun() # Rerun to update button state
            else:
                st.error(translate_text_with_ai("Failed to log score. Please try again.", st.session_state['preferred_language'], client_ai))
    elif st.session_state['score_logged_today']:
        st.info(translate_text_with_ai("Your score has already been logged for today.", st.session_state['preferred_language'], client_ai))

    st.markdown("---")
    st.subheader(translate_text_with_ai("Leaderboard", st.session_state['preferred_language'], client_ai))
    leaderboard = get_leaderboard_data()
    if leaderboard:
        leaderboard_df = [{"Rank": i+1, "Username": user, "Highest Score": score} for i, (user, score) in enumerate(leaderboard)]
        st.table(leaderboard_df)
    else:
        st.info(translate_text_with_ai("No leaderboard data yet. Play trivia to get on the board!", st.session_state['preferred_language'], client_ai))

    st.markdown("---")
    st.subheader(translate_text_with_ai("Share Your Feedback", st.session_state['preferred_language'], client_ai))
    feedback_message = st.text_area(translate_text_with_ai("We'd love to hear your thoughts!", st.session_state['preferred_language'], client_ai), key="feedback_input")
    if st.button(translate_text_with_ai("Submit Feedback", st.session_state['preferred_language'], client_ai), key="submit_feedback_btn"):
        if feedback_message:
            username_for_feedback = st.session_state['logged_in_username'] if st.session_state['is_authenticated'] else "Guest"
            if log_feedback(username_for_feedback, feedback_message):
                st.success(translate_text_with_ai("Thank you for your feedback!", st.session_state['preferred_language'], client_ai))
                st.session_state['feedback_input'] = "" # Clear the text area
            else:
                st.error(translate_text_with_ai("Failed to submit feedback. Please try again.", st.session_state['preferred_language'], client_ai))
        else:
            st.warning(translate_text_with_ai("Please enter some feedback before submitting.", st.session_state['preferred_language'], client_ai))


# --- Main App Flow ---
if not st.session_state['is_authenticated']:
    show_login_page()
else:
    # --- Page Rendering based on current_page ---
    if st.session_state['current_page'] == 'main_app':
        show_main_app_page()
    elif st.session_state['current_page'] == 'trivia_page':
        show_trivia_page()
    # Default to main_app if current_page is somehow not set to a valid page
    else:
        st.session_state['current_page'] = 'main_app'
        show_main_app_page()
