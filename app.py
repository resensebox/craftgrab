import streamlit as st
from openai import OpenAI
from datetime import datetime, date
from fpdf import FPDF
import re
import json
import base64 # Import base64 for encoding PDF content

st.set_option('client.showErrorDetails', True)
st.set_page_config(page_title="This Day in History", layout="centered")

# --- Session State Initialization ---
if 'is_authenticated' not in st.session_state:
    st.session_state['is_authenticated'] = False
if 'logged_in_username' not in st.session_state:
    st.session_state['logged_in_username'] = ""
# Removed 'dementia_mode' from session state
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'main_app' # Default page for authenticated users
if 'daily_data' not in st.session_state: # Store daily data to avoid re-fetching on page switch
    st.session_state['daily_data'] = None
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
        
        ws.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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
    text = text.replace('?', '-') # Replace question marks with dashes
    # Add more replacements as needed for other common problematic characters
    
    # Fallback for any remaining non-latin-1 characters (replace with '?')
    # This aggressive replacement should be a last resort but ensures no encoding errors
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


# --- This Day in History Logic ---
def get_this_day_in_history_facts(current_day, current_month, user_info, _ai_client, preferred_decade=None, topic=None, difficulty='Medium'):
    """
    Generates 'This Day in History' facts using OpenAI API with specific content requirements.
    Incorporates customization options for decade, topic, and difficulty.
    """
    current_date_str = f"{current_month:02d}-{current_day:02d}"

    # Adjust parameters based on difficulty for Trivia Questions ONLY
    # Main articles word count and language tone do not change with difficulty
    event_word_count, born_word_count = 300, 150 # Increased event_word_count by 100 words
    trivia_complexity = ""
    if difficulty == 'Easy':
        trivia_complexity = "very well-known facts, common knowledge"
    elif difficulty == 'Hard':
        trivia_complexity = "obscure facts, specific details, challenging"
    else: # Medium
        trivia_complexity = "general historical facts, moderately challenging"

    # Build prompt for event and born date ranges
    event_year_range = "between the years 1800 and 1960"
    born_year_range = "between 1800 and 1970"

    # Add topic customization to prompt if selected
    topic_clause = f" focusing on {topic}" if topic else ""
    
    # Add decade customization to prompt if selected (AI may need more fine-tuning to adhere perfectly)
    decade_clause = f" specifically from the {preferred_decade}" if preferred_decade and preferred_decade != "None" else ""


    prompt = f"""
    You are an assistant generating 'This Day in History' facts for {current_date_str}.
    Please provide:

    1. Event Article: Write a short article (around {event_word_count} words) about a famous historical event that happened on this day {event_year_range}{topic_clause}{decade_clause}. Use clear, informative language.
    2. Born on this Day Article: Write a brief article (around {born_word_count} words) about a well-known person born on this day {born_year_range}{decade_clause}. Use clear, informative language.
    3. Fun Fact: Provide one interesting and unusual fun fact that occurred on this day in history.
    4. Trivia Questions: Provide five concise, direct trivia questions based on today’s date. These should be actual questions that require a factual answer, and should not be "Did You Know?" statements or prompts for reflection. Topics can include history, famous birthdays, pop culture, or global events. The questions should be {trivia_complexity}. For each question, provide the correct answer in parentheses and a short, distinct hint in square brackets (e.g., "What year did the Berlin Wall fall? (1989) [Hint: Cold War era]").
    5. Did You Know?: Provide three "Did You Know?" facts related to nostalgic content (e.g., old prices, inventions, fashion facts) from past decades (e.g., 1930s-1970s).
    6. Memory Prompts: Provide **two to three** engaging questions to encourage reminiscing and conversation. Each prompt should be a complete sentence or question, without leading hyphens or bullet points in the raw output, ready to be formatted as paragraphs. (e.g., "Do you remember your first concert?", "What was your favorite childhood game?", "What's a memorable school event from your youth?").

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
        memory_prompt_match = re.search(r"6\. Memory Prompts:\s*(.*?)(?=\n\Z|$)", content, re.DOTALL)

        # Special handling for Trivia Questions to extract questions, answers, and hints
        trivia_questions = []
        trivia_text_match = re.search(r"4\. Trivia Questions:\s*(.*?)(?=\n5\. Did You Know?:|\Z)", content, re.DOTALL)
        if trivia_text_match:
            raw_trivia = trivia_text_match.group(1).strip()
            
            # Use a more specific regex to find lines that look like trivia questions
            # This regex looks for:
            # - Starts with optional number (e.g., "1.", "a.")
            # - Captures the question text
            # - Captures the answer in parentheses
            # - Captures the hint in square brackets
            # It also handles variations where there might be extra spaces.
            trivia_line_pattern = re.compile(r'^\s*\d*\.?\s*(.*?)\s*\((.*?)\)\s*\[(.*?)\]\s*$')

            for line in raw_trivia.split('\n'):
                line = line.strip()
                if not line:
                    continue # Skip empty lines

                match = trivia_line_pattern.match(line)
                if match:
                    question_text = match.group(1).strip()
                    answer = match.group(2).strip()
                    hint = match.group(3).strip()
                    
                    trivia_questions.append({'question': question_text, 'answer': answer, 'hint': hint})
                
                # IMPORTANT: Limit to 5 questions explicitly after successful parsing
                if len(trivia_questions) >= 5:
                    break

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


        return {
            'event_article': event_article,
            'born_article': born_article,
            'fun_fact_section': fun_fact_section,
            'trivia_section': trivia_questions, # Now a list of dicts {question, answer, hint}
            'did_you_know_section': did_you_know_lines,
            'memory_prompt_section': memory_prompts_list # Now a list of prompts
        }
    except Exception as e:
        st.error(f"Error generating history: {e}")
        return {
            'event_article': "Could not fetch event history.",
            'born_article': "Could not fetch birth history.",
            'fun_fact_section': "Could not fetch fun fact.",
            'trivia_section': [], # Empty list if error
            'did_you_know_section': ["No 'Did You Know?' facts available for today. Please try again or adjust preferences."], # Ensure default content
            'memory_prompt_section': ["No memory prompts available.", "Consider your favorite childhood memory.", "What's a happy moment from your past week?"]
        }

def generate_full_history_pdf(data, today_date_str, user_info): # Removed dementia_mode parameter
    """
    Generates a PDF of 'This Day in History' facts, formatted over two pages.
    Page 1: Two-column layout with daily content.
    Page 2: About Us, Logo, and Contact Information.
    """
    pdf = FPDF(unit="mm", format="A4") # Use mm for better control
    pdf.add_page()
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

    # --- Masthead ---
    pdf.set_y(10) # Start from top
    pdf.set_x(left_margin)
    pdf.set_font("Times", "B", title_font_size) # Large, bold font for the title
    pdf.cell(0, 15, "The Daily Resense Register", align='C')
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
    pdf.multi_cell(col_width, line_height_normal, "On This Date")
    current_y_col1 += line_height_normal # Update Y after title
    pdf.set_font("Arial", "", article_text_font_size)
    pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(data['event_article']))
    current_y_col1 = pdf.get_y() + section_spacing_normal # Update Y and add spacing

    pdf.set_y(current_y_col1) # Ensure position is updated

    # Fun Fact
    pdf.set_font("Arial", "B", section_title_font_size)
    pdf.multi_cell(col_width, line_height_normal, "Fun Fact:")
    current_y_col1 += line_height_normal
    pdf.set_font("Arial", "", article_text_font_size)
    pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(data['fun_fact_section']))
    current_y_col1 = pdf.get_y() + section_spacing_normal # Update Y and add spacing
    pdf.set_y(current_y_col1)

    # Daily Trivia
    pdf.set_font("Arial", "B", section_title_font_size)
    pdf.multi_cell(col_width, line_height_normal, "Daily Trivia")
    current_y_col1 += line_height_normal
    pdf.set_font("Arial", "", trivia_q_font_size) # Reset font to regular for trivia text if needed

    # Loop through the first 4 trivia questions for the PDF
    for i, item in enumerate(data['trivia_section'][:4]): # Limit to 4 questions for PDF
        question_text_clean = clean_text_for_latin1(f"{chr(97+i)}. {item['question']}")
        answer_text_clean = clean_text_for_latin1(f"Answer: {item['answer']}")
        hint_text_clean = clean_text_for_latin1(f"Hint: {item['hint']}")

        pdf.set_font("Arial", "B", trivia_q_font_size) # Bold for question
        pdf.multi_cell(col_width, line_height_trivia_ans_hint, question_text_clean)
        
        pdf.set_font("Arial", "", trivia_ans_hint_font_size) # Smaller, regular for answer
        pdf.multi_cell(col_width, line_height_trivia_ans_hint, answer_text_clean)
        pdf.multi_cell(col_width, line_height_trivia_ans_hint, hint_text_clean) # Display hint
        pdf.ln(3) # Small spacing after each trivia question

        current_y_col1 = pdf.get_y() # Get current Y to accurately track position

    current_y_col1 += section_spacing_normal # Spacing after trivia section
    pdf.set_y(current_y_col1)


    # Column 2 (Right Column)
    pdf.set_xy(page_width / 2 + 5, current_y_col2) # X start for right column, Y at same level as left
    pdf.set_right_margin(right_margin)
    pdf.set_left_margin(page_width / 2 + 5) # Left margin for right column

    # Quote of the Day
    pdf.set_font("Arial", "B", section_title_font_size)
    pdf.multi_cell(col_width, line_height_normal, "Quote of the Day", align='C')
    current_y_col2 += line_height_normal
    quote_text = clean_text_for_latin1(f'"The only way to do great work is to love what you do."') # Placeholder quote
    quote_author = clean_text_for_latin1("- Unknown") # Placeholder author
    pdf.set_font("Times", "I", article_text_font_size) # Italic for quote
    pdf.multi_cell(col_width, line_height_normal, quote_text, align='C')
    pdf.multi_cell(col_width, line_height_normal, quote_author, align='C')
    current_y_col2 = pdf.get_y() + section_spacing_normal # Update Y and add spacing
    pdf.set_y(current_y_col2)

    # Happy Birthday!
    pdf.set_font("Arial", "B", section_title_font_size)
    pdf.multi_cell(col_width, line_height_normal, "Happy Birthday!")
    current_y_col2 += line_height_normal
    pdf.set_font("Arial", "", article_text_font_size)
    pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(data['born_article']))
    current_y_col2 = pdf.get_y() + section_spacing_normal # Update Y and add spacing
    pdf.set_y(current_y_col2)

    # Did You Know-
    if data['did_you_know_section']:
        pdf.set_font("Arial", "B", section_title_font_size)
        pdf.multi_cell(col_width, line_height_normal, "Did You Know-") # Replaced ? with -
        current_y_col2 += line_height_normal
        pdf.set_font("Arial", "", article_text_font_size)
        for item in data['did_you_know_section']:
            did_you_know_line = clean_text_for_latin1(f"- {item}")
            pdf.multi_cell(col_width, line_height_normal, did_you_know_line)
            current_y_col2 = pdf.get_y() # Update Y after each fact line
        current_y_col2 += section_spacing_normal # Spacing after section
        pdf.set_y(current_y_col2)

    # Memory Prompt-
    if data['memory_prompt_section']:
        pdf.set_font("Arial", "B", section_title_font_size)
        pdf.multi_cell(col_width, line_height_normal, "Memory Prompt-") # Replaced ? with -
        current_y_col2 += line_height_normal
        pdf.set_font("Arial", "", article_text_font_size)
        # Iterate and display up to the first 3 memory prompts for PDF
        for prompt_text in data['memory_prompt_section'][:3]: # Limit to first 3 prompts
            # Display without a leading hyphen to appear more like a paragraph
            pdf.multi_cell(col_width, line_height_normal, clean_text_for_latin1(prompt_text))
            pdf.ln(2) # Small line break between prompts
            current_y_col2 = pdf.get_y() # Update Y after each prompt line
        current_y_col2 += section_spacing_normal # Spacing after section
        pdf.set_y(current_y_col2)


    # --- Page 2 Content ---
    pdf.add_page()
    # Set new, better margins for page 2 content
    left_margin_p2 = 25
    right_margin_p2 = 25
    content_width_p2 = page_width - left_margin_p2 - right_margin_p2

    pdf.set_left_margin(left_margin_p2)
    pdf.set_right_margin(right_margin_p2)
    pdf.set_x(left_margin_p2) # Start content at the new left margin
    pdf.set_y(20) # Start further down on the new page

    # About Us Title
    pdf.set_font("Arial", "B", 18) # Slightly smaller font for longer title
    new_about_us_title = clean_text_for_latin1("Learn More About US! Mindful Libraries - A Dementia-Inclusive Reading Program")
    pdf.multi_cell(content_width_p2, 10, new_about_us_title, 0, 'C') # Using multi_cell for title as it's long
    pdf.ln(5) # Smaller line break after title

    # About Us Text
    pdf.set_font("Arial", "", 11) # Slightly smaller font for better fit
    new_about_us_text = clean_text_for_latin1("""Mindful Libraries is a collaborative initiative between Resense, Nana's Books, and Mirador
Magazine, designed to bring adaptive, nostalgic reading experiences to individuals living
with dementia. This innovative program provides:
- Curated Libraries of dementia-friendly newspapers, books, and magazines
- Staff Training accredited by NCCAP, focusing on reminiscence, person-centered care,
and meaningful engagement
- Digital Access Tools like downloadable discussion guides, activity templates, and reading
prompts
- Partnerships with Long-Term Care Communities to build inclusive, life-enriching
environments
Mindful Libraries empowers care teams to reconnect residents with their pasts, spark joyful conversation, and foster dignity through storytelling and memory-based engagement.""")
    pdf.multi_cell(content_width_p2, 6, new_about_us_text, 0, 'L') # Left align for readability
    pdf.ln(5) # Add space after About Us text

    # New line for learning more
    pdf.set_font("Arial", "B", 12) # Set font to bold for this line
    pdf.multi_cell(content_width_p2, 7, clean_text_for_latin1("Learn more about our program at www.mindfullibraries.com"), 0, 'C') # Centered and bold
    pdf.set_font("Arial", "", 12) # Reset font to normal
    pdf.ln(10) # More space after this line

    # Logo - still centered horizontally on the page
    logo_width = 70
    logo_height = 70
    logo_x = (page_width - logo_width) / 2 # Still calculated based on full page width for centering
    pdf.image("https://i.postimg.cc/8CRsCGCC/Chat-GPT-Image-Jun-7-2025-12-32-18-AM.png", x=logo_x, y=pdf.get_y(), w=logo_width, h=logo_height)
    pdf.ln(logo_height + 15) # Add space after logo

    # Contact Information - still centered horizontally on the page
    pdf.set_font("Arial", "B", 16)
    pdf.multi_cell(0, 10, clean_text_for_latin1("Contact Information"), 0, 'C') # Use multi_cell for consistency and cleaning
    pdf.ln(5)
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 7, clean_text_for_latin1("Email: thisdayinhistoryapp@gmail.com"), 0, 'C')
    pdf.multi_cell(0, 7, clean_text_for_latin1("Website: ThisDayInHistoryApp.com (Coming Soon!)"), 0, 'C')
    
    # Original bold website URL, keep if intended to have two website mentions
    pdf.set_font("Arial", "B", 12) # Set font to bold
    pdf.multi_cell(0, 7, clean_text_for_latin1("www.mindfullibraries.com"), 0, 'C')
    pdf.set_font("Arial", "", 12) # Reset font to normal

    pdf.multi_cell(0, 7, clean_text_for_latin1("Phone: 412-212-6701 (For Support)"), 0, 'C')
    pdf.ln(10)

    # User info at the very bottom of the second page, aligned right
    pdf.set_font("Arial", "I", 8)
    # Reset margins for a full width cell to align right
    pdf.set_left_margin(left_margin_p2) # Revert to page 2 margins
    pdf.set_right_margin(right_margin_p2)
    pdf.set_x(left_margin_p2)
    pdf.set_y(pdf.h - 15) # Position near bottom of the page
    pdf.multi_cell(content_width_p2, 4, clean_text_for_latin1(f"Generated for {user_info['name']}"), align='R')
        
    return pdf.output(dest='S').encode('latin-1')


# --- Page Navigation Function ---
def set_page(page_name):
    """Sets the current page in session state."""
    st.session_state['current_page'] = page_name
    # Reset trivia states if navigating away from trivia page to ensure fresh start if new day
    if page_name == 'main_app':
        st.session_state['trivia_question_states'] = {}
        st.session_state['hints_remaining'] = 3 # Reset hints when going back to main page for a new day's content
        st.session_state['current_trivia_score'] = 0 # Reset score for a new day
        st.session_state['total_possible_daily_trivia_score'] = 0 # Reset total possible for a new day
        st.session_state['score_logged_today'] = False # Reset logging flag
    # Streamlit will automatically rerun the app when session_state is modified.
    # No st.rerun() is needed here to avoid "no-op" warnings.


def show_feedback_form():
    """Displays a feedback form and logs submissions to Google Sheets."""
    st.markdown("---")
    st.subheader("📧 Send us feedback")
    st.markdown("We'd love to hear from you! Please share your thoughts below.")

    with st.form("feedback_form", clear_on_submit=True):
        feedback_text = st.text_area("Your Feedback", help="Tell us what you think!", key="feedback_text_area")
        contact_info = st.text_input("Your Name or Email (Optional)", help="So we can follow up, if needed.", key="feedback_contact_info")
        
        submitted = st.form_submit_button("Submit Feedback")
        if submitted:
            if feedback_text.strip():
                # Use logged-in username if available, otherwise use provided contact info
                username_for_feedback = st.session_state.get('logged_in_username', 'Guest')
                if contact_info.strip():
                    username_for_feedback = contact_info.strip() # Override if user provides specific contact info
                
                if log_feedback(username_for_feedback, feedback_text.strip()):
                    st.success("Thank you for your feedback! We appreciate it.")
                else:
                    st.error("Failed to submit feedback. Please try again later.")
            else:
                st.warning("Please enter some feedback before submitting.")
    st.markdown("---")


# --- UI Functions for Pages ---
def show_main_app_page():
    st.title("📅 This Day in History")

    st.markdown("<p style='font-size:24px; font-weight:bold;'>Today's Daily Page</p>", unsafe_allow_html=True)


    today = datetime.today()
    
    # --- Date Picker for Main Page Content ---
    selected_date = st.date_input("Select a date", value=today, key="date_picker_main_app")
    day, month, year = selected_date.day, selected_date.month, selected_date.year

    user_info = {
        'name': st.session_state['logged_in_username'],
        'jobs': '', 'hobbies': '', 'decade': '', 'life_experiences': '', 'college_chapter': ''
    }

    # Fetch daily data if not already fetched for the current day/user/preferences
    # This key ensures data is re-fetched if date or preferences change
    # IMPORTANT: 'difficulty' is no longer part of the key for main page content, as it's now controlled on trivia page
    current_data_key = f"{selected_date.strftime('%Y-%m-%d')}-{st.session_state['logged_in_username']}-" \
                       f"{st.session_state.get('preferred_topic_main_app', 'None')}-" \
                       f"{st.session_state.get('preferred_decade_main_app', 'None')}-" \
                       f"trivia_difficulty_{st.session_state['difficulty']}" # Still include trivia difficulty so data regenerates if it changes

    if st.session_state['last_fetched_date'] != current_data_key or st.session_state['daily_data'] is None:
        st.session_state['daily_data'] = get_this_day_in_history_facts(
            day, month, user_info, client_ai, 
            topic=st.session_state.get('preferred_topic_main_app') if st.session_state.get('preferred_topic_main_app') != "None" else None,
            preferred_decade=st.session_state.get('preferred_decade_main_app') if st.session_state.get('preferred_decade_main_app') != "None" else None,
            difficulty=st.session_state['difficulty'] # Pass the selected difficulty to generate trivia
        )
        st.session_state['last_fetched_date'] = current_data_key
        st.session_state['trivia_question_states'] = {} # Reset trivia states for new day's data
        st.session_state['hints_remaining'] = 3 # Reset hints for a new day
        st.session_state['current_trivia_score'] = 0 # Reset score for a new day
        st.session_state['total_possible_daily_trivia_score'] = 0 # Reset total possible for a new day
        st.session_state['score_logged_today'] = False # Reset logging flag

    data = st.session_state['daily_data']

    # Display content - Articles are back on the main page
    st.subheader(f"✨ A Look Back at {selected_date.strftime('%B %d')}")

    # New note for scrolling down to download/print at the top of the main page
    st.info("Make sure to scroll down to download and print your 'This Day In History' worksheet!")

    st.markdown("---")
    st.subheader("🗓️ Significant Event")
    st.write(data['event_article'])

    st.markdown("---")
    st.subheader("🎂 Born on this Day")
    st.write(data['born_article'])

    st.markdown("---")
    st.subheader("💡 Fun Fact")
    st.write(data['fun_fact_section'])

    st.markdown("---")
    st.subheader("🌟 Did You Know-") # Replaced ? with -
    for i, fact in enumerate(data['did_you_know_section']):
        st.write(f"- {fact}")

    st.markdown("---")
    st.subheader("💬 Memory Lane Prompt-") # Replaced ? with -
    # Iterate and display each memory prompt without hyphens
    if data['memory_prompt_section']:
        for prompt_text in data['memory_prompt_section']:
            st.write(f"{prompt_text}") # Display as paragraph, no leading hyphen
    else:
        st.write("No memory prompts available.")

    st.markdown("---")
    
    # Generate PDF bytes once
    pdf_bytes_main = generate_full_history_pdf(
        data, selected_date.strftime('%B %d, %Y'), user_info
    )
    
    # Create Base64 encoded link
    b64_pdf_main = base64.b64encode(pdf_bytes_main).decode('latin-1')
    pdf_viewer_link_main = f'<a href="data:application/pdf;base64,{b64_pdf_main}" target="_blank">View PDF in Browser</a>'

    col1, col2 = st.columns([1, 1])
    with col1:
        st.download_button(
            "Download Daily Page PDF", 
            pdf_bytes_main, 
            file_name=f"This_Day_in_History_{selected_date.strftime('%Y%m%d')}.pdf",
            mime="application/pdf"
        )
    with col2:
        st.markdown(pdf_viewer_link_main, unsafe_allow_html=True)
    
    # --- Offline Access (Conceptual - requires local storage solution) ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("Offline Access")
    st.sidebar.info("Offline access for the past 7 days is a planned feature. For now, you can download PDFs to save content.")
    
    # --- Sharing/Email Option (Conceptual - requires external email service) ---
    st.sidebar.subheader("Share Daily Page")
    st.sidebar.info("Daily/weekly sharing via email is a planned feature. This would integrate with an email service.")

    # Feedback form at the bottom
    show_feedback_form()


def show_trivia_page():
    st.title("🧠 Daily Trivia Challenge!")
    st.button("⬅️ Back to Main Page", on_click=set_page, args=('main_app',), key="back_to_main_from_trivia_top")

    # Feedback email note at the top
    st.markdown("---")
    st.markdown("📧 You can send us feedback at: `thisdayinhistoryapp@gmail.com`")
    st.markdown("---")

    st.subheader("Trivia Settings")
    # Add the note about inputting a response
    st.info("💡 To check your answer, please input your response into the text box and then click the 'Check Answer' button.")
    
    # Moved: Difficulty selection is now on the trivia page
    st.session_state['difficulty'] = st.selectbox(
        "Trivia Difficulty",
        options=["Easy", "Medium", "Hard"],
        index=["Easy", "Medium", "Hard"].index(st.session_state['difficulty']), # Set initial value from session state
        key='trivia_difficulty_select',
        help="Adjusts the complexity of the trivia questions."
    )
    st.markdown("---")

    # If difficulty changes, we need to re-fetch the main content (which includes trivia)
    # This simulates re-generating the daily content with the new trivia difficulty
    current_selected_date = datetime.today().date() # Assume trivia is for today's date
    data_key_for_trivia_regen = f"{current_selected_date.strftime('%Y-%m-%d')}-{st.session_state['logged_in_username']}-" \
                               f"{st.session_state.get('preferred_topic_main_app', 'None')}-" \
                               f"{st.session_state.get('preferred_decade_main_app', 'None')}-" \
                               f"trivia_difficulty_{st.session_state['difficulty']}"

    # Only re-fetch if the selected difficulty or date has changed
    if st.session_state['last_fetched_date'] != data_key_for_trivia_regen:
        st.session_state['daily_data'] = get_this_day_in_history_facts(
            current_selected_date.day, current_selected_date.month, 
            {'name': st.session_state['logged_in_username']}, client_ai, 
            topic=st.session_state.get('preferred_topic_main_app') if st.session_state.get('preferred_topic_main_app') != "None" else None,
            preferred_decade=st.session_state.get('preferred_decade_main_app') if st.session_state.get('preferred_decade_main_app') != "None" else None,
            difficulty=st.session_state['difficulty']
        )
        st.session_state['last_fetched_date'] = data_key_for_trivia_regen # Update fetched key
        st.session_state['trivia_question_states'] = {} # Reset trivia states for new difficulty's data
        st.session_state['hints_remaining'] = 3
        st.session_state['current_trivia_score'] = 0
        st.session_state['total_possible_daily_trivia_score'] = 0
        st.session_state['score_logged_today'] = False
        st.rerun() # Rerun to apply new content

    if st.session_state['daily_data'] and st.session_state['daily_data']['trivia_section']:
        trivia_questions = st.session_state['daily_data']['trivia_section']

        # Calculate total possible points
        st.session_state['total_possible_daily_trivia_score'] = len(trivia_questions) * 3
        st.info(f"**Total Possible Points:** {st.session_state['total_possible_daily_trivia_score']} | **Your Current Score:** {st.session_state['current_trivia_score']}")

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
            st.markdown(f"**Question {i+1}:** {trivia_item['question']}")

            col_input, col_check, col_hint = st.columns([0.6, 0.2, 0.2])

            with col_input:
                user_input = st.text_input(
                    f"Your Answer for Q{i+1}:", 
                    value=q_state['user_answer'], 
                    key=f"input_{question_key_base}", 
                    disabled=q_state['is_correct'] or q_state.get('out_of_chances', False) # Disable if correct or out of chances
                )
                q_state['user_answer'] = user_input # Update state on input change for persistence

            with col_check:
                # Disable check button if correct, no input, or out of chances
                if not q_state['is_correct'] and not q_state.get('out_of_chances', False):
                    if st.button("Check Answer", key=f"check_btn_{question_key_base}", disabled=not user_input.strip()): # Changed button text to "Check Answer"
                        user_answer_cleaned = user_input.strip().lower()
                        correct_answer_cleaned = trivia_item['answer'].strip().lower()

                        is_exact_match = (user_answer_cleaned == correct_answer_cleaned)
                        is_partial_match = False
                        if not is_exact_match:
                            is_partial_match = check_partial_correctness_with_ai(user_input, trivia_item['answer'], client_ai)

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
                                    q_state['feedback'] = f"✅ Correct! You earned {points} points for this question."
                                else: # It's a partial match
                                    q_state['feedback'] = f"✅ Partially correct! You earned {points} points for this question."
                            else:
                                q_state['feedback'] = "✅ Already correct!" # Should not happen with disabled button, but as a safeguard
                        else: # Neither exact nor partial match
                            q_state['attempts'] += 1 # Increment attempts on incorrect answer
                            if q_state['attempts'] >= 3:
                                q_state['out_of_chances'] = True
                                q_state['feedback'] = f"❌ You've used all {q_state['attempts']} attempts. The correct answer was: **{trivia_item['answer']}**. You earned 0 points for this question."
                                # Ensure points_earned is 0 if out of chances and not previously correct
                                if q_state['points_earned'] == 0:
                                    q_state['points_earned'] = 0 # Explicitly set to 0
                            else:
                                q_state['feedback'] = f"❌ Incorrect. Try again! (Attempts: {q_state['attempts']}/3)"
                        # No st.rerun() needed here; button click triggers rerun automatically

            with col_hint:
                # Show hint button only if not correct, not out of chances, hints remaining, not already revealed, and hint content exists
                if not q_state['is_correct'] and not q_state.get('out_of_chances', False) and st.session_state['hints_remaining'] > 0 and not q_state['hint_revealed'] and trivia_item.get('hint'):
                    if st.button(f"Hint ({st.session_state['hints_remaining']})", key=f"hint_btn_{question_key_base}"):
                        st.session_state['hints_remaining'] -= 1
                        q_state['hint_revealed'] = True
                        # No st.rerun() needed here; button click triggers rerun automatically
                # Always display hint if it was revealed for this question AND hint content exists
                elif q_state['hint_revealed'] and trivia_item.get('hint'):
                    st.info(f"Hint: {trivia_item['hint']}")
                # If question is correct or out of chances, display the hint if it exists (for learning)
                elif (q_state['is_correct'] or q_state.get('out_of_chances', False)) and trivia_item.get('hint'):
                    st.info(f"Hint: {trivia_item['hint']}")

            # Display feedback based on the state
            if q_state['feedback']:
                if q_state['is_correct']:
                    st.success(q_state['feedback'])
                elif q_state.get('out_of_chances', False):
                    st.error(q_state['feedback'])
                else: # Incorrect but still has chances
                    st.error(q_state['feedback'])

            # Add expander for related article - ONLY show if out of chances
            if q_state.get('out_of_chances', False):
                with st.expander(f"Show Explanation for Q{i+1}"):
                    if q_state['related_article_content'] is None:
                        # Generate article if it hasn't been generated yet
                        with st.spinner("Generating explanation..."):
                            generated_article = generate_related_trivia_article(
                                trivia_item['question'], trivia_item['answer'], client_ai
                            )
                            q_state['related_article_content'] = clean_text_for_latin1(generated_article)
                        st.write(q_state['related_article_content'])
                    else:
                        st.write(q_state['related_article_content'])
            
        st.markdown("---")
        # Check if all questions are answered correctly or out of chances
        all_completed = all(st.session_state['trivia_question_states'][f"trivia_q_{i}"]['is_correct'] or \
                            st.session_state['trivia_question_states'][f"trivia_q_{i}"].get('out_of_chances', False) \
                            for i in range(len(trivia_questions)))
        
        if all_completed:
            st.success("You've completed the trivia challenge for today!")
            if not st.session_state['score_logged_today']:
                if log_trivia_score(st.session_state['logged_in_username'], st.session_state['current_trivia_score']):
                    st.session_state['score_logged_today'] = True
                    st.success("Your score has been logged!")
                else:
                    st.error("Failed to log your score.")
        else:
            st.info(f"You have {st.session_state['hints_remaining']} hints remaining.")
        
        st.markdown("---")
        st.subheader("🏆 Leaderboard")
        leaderboard = get_leaderboard_data()
        if leaderboard:
            for rank, (username, score) in enumerate(leaderboard):
                st.write(f"{rank+1}. {username}: {score} points")
        else:
            st.info("No scores logged yet for the leaderboard. Be the first!")

        st.button("⬅️ Back to Main Page", on_click=set_page, args=('main_app',), key="back_to_main_from_trivia_bottom")
    else: # This else now correctly corresponds to the 'if' above it for trivia questions
        st.write("No trivia questions available for today. Please go back to the main page.")
        st.button("⬅️ Back to Main Page", on_click=set_page, args=('main_app',), key="back_to_main_from_trivia_no_questions")


def show_login_register_page():
    # Centering the logo using columns
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("https://i.postimg.cc/8CRsCGCC/Chat-GPT-Image-Jun-7-2025-12-32-18-AM.png", use_container_width=False, width=200)

    st.markdown(
        """
        Welcome to **This Day in History**!
        Discover fascinating historical events, learn about notable birthdays, and test your knowledge with daily trivia.
        Sign in or register to personalize your daily historical journey and track your trivia scores!
        """
    )
    st.title("Login to Access") # Moved this line

    st.markdown("---")

    # Feedback email note at the top
    st.markdown("📧 You can send us feedback at: `thisdayinhistoryapp@gmail.com`")
    st.markdown("---")

    login_tab, register_tab = st.tabs(["Log In", "Register"])
    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username_input")
            password = st.text_input("Password", type="password", key="login_password_input")
            # Removed the 'key' argument from st.form_submit_button
            if st.form_submit_button("Log In"):
                USERS = get_users_from_sheet() # Get users from Google Sheet
                if username in USERS and USERS[username] == password:
                    st.session_state['is_authenticated'] = True
                    st.session_state['logged_in_username'] = username
                    st.success(f"Welcome {username}!")
                    log_event("login", username)
                    set_page('main_app') # Go to main app page
                else:
                    st.error("Invalid credentials.")

    with register_tab:
        with st.form("register_form"):
            new_username = st.text_input("New Username", key="register_username_input")
            new_email = st.text_input("Email", key="register_email_input")
            # Added email usage note
            st.markdown(
                """
                <p style='font-size:0.8em; color:#AAAAAA; margin-top:-1em;'>
                *No spam or marketing emails. Used only for account support like lost passwords.*
                </p>
                """,
                unsafe_allow_html=True
            )
            new_password = st.text_input("New Password", type="password", key="register_password_input")
            confirm_password = st.text_input("Confirm Password", type="password", key="register_confirm_password_input")
            # Removed the 'key' argument from st.form_submit_button
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
                            set_page('main_app') # Go to main app page
                        else:
                            st.error("Failed to register user. Please try again.")
                else:
                    st.error("Passwords do not match.")

    # --- Example: This Day in History (on login page) ---
    st.markdown("---")
    st.subheader("📋 Example: This Day in History")
    st.info("This is a preview of the content format. Log in or register to get today's personalized content!")

    # Display content based off of January 1st for the example content on the login page
    january_1st_example_date = date(datetime.today().year, 1, 1) # Use current year's Jan 1st for the example
    example_user_info = {'name': 'Example User', 'jobs': '', 'hobbies': '', 'decade': '', 'life_experiences': '', 'college_chapter': ''}
    # For the example, use a default difficulty (e.g., 'Medium') as it's not user-selectable here
    example_data = get_this_day_in_history_facts(january_1st_example_date.day, january_1st_example_date.month, example_user_info, client_ai, difficulty='Medium')

    st.markdown(f"### ✨ A Look Back at {january_1st_example_date.strftime('%B %d')}")
    st.markdown("### 🗓️ Significant Event")
    st.write(example_data['event_article'])

    st.markdown("### 🎂 Born on this Day")
    st.write(example_data['born_article'])

    st.markdown("### 💡 Fun Fact")
    st.write(example_data['fun_fact_section'])

    st.markdown("### 🧠 Test Your Knowledge!")
    # Loop through the first 4 trivia questions for the example PDF
    if example_data['trivia_section']:
        for i, trivia_item in enumerate(example_data['trivia_section'][:4]): # Limit to 4 for example PDF
            st.markdown(f"**Question {i+1}:** {trivia_item['question']}")
            st.info(f"Answer: {trivia_item['answer']}") # Display answer for example content
            # Safely display hint for example content
            if trivia_item.get('hint'): # Use .get() here too
                st.info(f"Hint: {trivia_item['hint']}")
    else:
        st.write("No trivia questions available.")


    st.markdown("### 🌟 Did You Know-") # Replaced ? with -
    for fact in example_data['did_you_know_section']:
        st.markdown(f"- {fact}")

    st.markdown("### 💬 Memory Lane Prompt-") # Replaced ? with -
    # Iterate and display each memory prompt for example data without hyphens
    if example_data['memory_prompt_section']:
        for prompt_text in example_data['memory_prompt_section']:
            st.write(f"{prompt_text}") # Display as paragraph, no leading hyphen
    else:
        st.write("No memory prompts available.")


    # Generate PDF bytes once for example content
    pdf_bytes_example = generate_full_history_pdf(
        example_data, january_1st_example_date.strftime('%B %d, %Y'), example_user_info
    )

    # Create Base64 encoded link for example content
    b64_pdf_example = base64.b64encode(pdf_bytes_example).decode('latin-1')
    pdf_viewer_link_example = f'<a href="data:application/pdf;base64,{b64_pdf_example}" target="_blank">View Example PDF in Browser</a>'

    col1_example, col2_example = st.columns([1, 1])
    with col1_example:
        st.download_button(
            "Download Example PDF",
            pdf_bytes_example,
            file_name=f"example_this_day_history_{january_1st_example_date.strftime('%Y%m%d')}.pdf",
            mime="application/pdf"
        )
    with col2_example:
        st.markdown(pdf_viewer_link_example, unsafe_allow_html=True)


# --- Main App Logic (Router) ---
if st.session_state['is_authenticated']:
    # --- Sidebar content (always visible when authenticated) ---
    st.sidebar.image("https://i.postimg.cc/8CRsCGCC/Chat-GPT-Image-Jun-7-2025-12-32-18-AM.png", use_container_width=True)
    st.sidebar.markdown("---")
    st.sidebar.header("Navigation")
    if st.sidebar.button("🏠 Home", key="sidebar_home_btn"):
        set_page('main_app')
    if st.sidebar.button("🎮 Play Trivia!", key="sidebar_trivia_btn"):
        set_page('trivia_page')

    st.sidebar.markdown("---")
    st.sidebar.header("Settings")
    
    st.sidebar.subheader("Content Customization")
    st.session_state['preferred_topic_main_app'] = st.sidebar.selectbox(
        "Preferred Topic for Events (Optional)",
        options=["None", "Sports", "Music", "Inventions", "Politics", "Science", "Arts"],
        index=0,
        key='sidebar_topic_select'
    )
    st.session_state['preferred_decade_main_app'] = st.sidebar.selectbox(
        "Preferred Decade for Articles (Optional)",
        options=["None", "1800s", "1900s", "1910s", "1920s", "1930s", "1940s", "1950s", "1960s", "1970s", "1980s"],
        index=0,
        key='sidebar_decade_select'
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Local History (Planned)")
    st.sidebar.info("Integrating local historical facts specific to your area is a planned feature. This would require a separate local history database.")
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Log Out", key="sidebar_logout_btn"):
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
        st.session_state['current_page'] = 'main_app'
        show_main_app_page()
else: # Not authenticated, show login/register and January 1st example
    show_login_register_page()
