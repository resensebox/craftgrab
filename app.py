import streamlit as st
from openai import OpenAI
from datetime import datetime, date
from fpdf import FPDF
import re
import json
import base64 # Import base64 for encoding PDF content

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
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = 'main_app' # Default page for authenticated users
if 'daily_data' not in st.session_state: # Store daily data to avoid re-fetching on page switch
    st.session_state['daily_data'] = None
if 'last_fetched_date' not in st.session_state:
    st.session_state['last_fetched_date'] = None # To track when data was last fetched
if 'trivia_question_states' not in st.session_state:
    st.session_state['trivia_question_states'] = {} # Stores per-question state: {'q_index': {'user_answer': '', 'is_correct': False, 'feedback': '', 'hint_revealed': False}}
if 'hints_remaining' not in st.session_state:
    st.session_state['hints_remaining'] = 3 # Total hints allowed per day

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
    
    # Add decade customization to prompt if selected (AI may need more fine-tuning to adhere perfectly)
    decade_clause = f" specifically from the {preferred_decade}" if preferred_decade and preferred_decade != "None" else ""


    prompt = f"""
    You are an assistant generating 'This Day in History' facts for {current_date_str}.
    Please provide:

    1. Event Article: Write a short article (around 200 words) about a famous historical event that happened on this day {event_year_range}{topic_clause}{decade_clause}.
    2. Born on this Day Article: Write a brief article (around 150-200 words) about a well-known person born on this day {born_year_range}{decade_clause}.
    3. Fun Fact: Provide one interesting and unusual fun fact that occurred on this day in history.
    4. Trivia Questions: Provide five trivia questions based on today’s date, spanning topics like history, famous birthdays, pop culture, or global events. For each question, provide the answer in parentheses and a short, distinct hint in square brackets (e.g., "[Hint: ...]").
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
        did_you_know_match = re.search(r"5\. Did You Know:\?\s*(.*?)(?=\n6\. Memory Prompt:|\Z)", content, re.DOTALL)
        memory_prompt_match = re.search(r"6\. Memory Prompt:\s*(.*)", content, re.DOTALL)
        
        # Special handling for Trivia Questions to extract questions, answers, and hints
        trivia_questions = []
        trivia_text_match = re.search(r"4\. Trivia Questions:\s*(.*?)(?=\n5\. Did You Know?:|\Z)", content, re.DOTALL)
        if trivia_text_match:
            raw_trivia = trivia_text_match.group(1).strip()
            for line in raw_trivia.split('\n'):
                line = line.strip()
                if line:
                    answer_match = re.search(r'\((.*?)\)', line)
                    hint_match = re.search(r'\[(.*?)\]', line)
                    
                    question_text = line
                    answer = ''
                    hint = ''

                    if answer_match:
                        answer = answer_match.group(1).strip()
                        question_text = question_text.replace(answer_match.group(0), '').strip()
                    if hint_match:
                        hint = hint_match.group(1).strip()
                        question_text = question_text.replace(hint_match.group(0), '').strip()
                    
                    # Clean up question_text by removing any numbering like "1."
                    question_text = re.sub(r'^\d+\.\s*', '', question_text).strip()

                    trivia_questions.append({'question': question_text, 'answer': answer, 'hint': hint})

        # Extract content, providing defaults if not found
        event_article = event_article_match.group(1).strip() if event_article_match else "No event article found."
        born_article = born_article_match.group(1).strip() if born_article_match else "No birth article found."
        fun_fact_section = fun_fact_match.group(1).strip() if fun_fact_match else "No fun fact found."
        did_you_know_lines = [f.strip() for f in did_you_know_match.group(1).strip().split('\n') if f.strip()] if did_you_know_match else []
        memory_prompt_section = memory_prompt_match.group(1).strip() if memory_prompt_match else "No memory prompt available."

        return {
            'event_article': event_article,
            'born_article': born_article,
            'fun_fact_section': fun_fact_section,
            'trivia_section': trivia_questions, # Now a list of dicts {question, answer, hint}
            'did_you_know_section': did_you_know_lines,
            'memory_prompt_section': memory_prompt_section
        }
    except Exception as e:
        st.error(f"Error generating history: {e}")
        return {
            'event_article': "Could not fetch event history.",
            'born_article': "Could not fetch birth history.",
            'fun_fact_section': "Could not fetch fun fact.",
            'trivia_section': [], # Empty list if error
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

    # Trivia - Now includes answers in PDF (for reference)
    if not dementia_mode: pdf.set_font("Arial", "B", 14)
    pdf.multi_cell(0, line_height, "Trivia:")
    if not dementia_mode: pdf.set_font("Arial", "", 12)
    for item in data['trivia_section']:
        pdf.multi_cell(0, line_height, f"{item['question']} (Answer: {item['answer']})") # Include answer in PDF
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

# --- Page Navigation Function ---
def set_page(page_name):
    st.session_state['current_page'] = page_name
    # Reset trivia states if navigating away from trivia page to ensure fresh start if new day
    if page_name == 'main_app':
        st.session_state['trivia_question_states'] = {}
        st.session_state['hints_remaining'] = 3 # Reset hints when going back to main page for a new day's content
    st.rerun() # Rerun to switch page immediately


# --- UI Functions for Pages ---
def show_main_app_page():
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
    day, month, year = today.day, today.month, today.year
    user_info = {
        'name': st.session_state['logged_in_username'],
        'jobs': '', 'hobbies': '', 'decade': '', 'life_experiences': '', 'college_chapter': ''
    }

    # Fetch daily data if not already fetched for the current day/user/preferences
    # This key ensures data is re-fetched if date or preferences change
    current_data_key = f"{day}-{month}-{year}-{st.session_state['logged_in_username']}-" \
                       f"{st.session_state.get('preferred_topic_main_app', 'None')}-" \
                       f"{st.session_state.get('preferred_decade_main_app', 'None')}"

    if st.session_state['last_fetched_date'] != current_data_key or st.session_state['daily_data'] is None:
        st.session_state['daily_data'] = get_this_day_in_history_facts(
            day, month, user_info, client_ai, 
            topic=st.session_state.get('preferred_topic_main_app') if st.session_state.get('preferred_topic_main_app') != "None" else None,
            preferred_decade=st.session_state.get('preferred_decade_main_app') if st.session_state.get('preferred_decade_main_app') != "None" else None
        )
        st.session_state['last_fetched_date'] = current_data_key
        st.session_state['trivia_question_states'] = {} # Reset trivia states for new day's data
        st.session_state['hints_remaining'] = 3 # Reset hints for a new day

    data = st.session_state['daily_data']

    # Display content
    st.subheader(f"✨ A Look Back at {today.strftime('%B %d')}")

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
    st.subheader("🌟 Did You Know?")
    for i, fact in enumerate(data['did_you_know_section']):
        st.write(f"- {fact}")

    st.markdown("---")
    st.subheader("💬 Memory Lane Prompt")
    st.write(data['memory_prompt_section'])

    st.markdown("---")
    
    # Generate PDF bytes once
    pdf_bytes_main = generate_full_history_pdf(
        data, today.strftime('%B %d, %Y'), user_info, st.session_state['dementia_mode']
    )
    
    # Create Base64 encoded link
    b64_pdf_main = base64.b64encode(pdf_bytes_main).decode('latin-1')
    pdf_viewer_link_main = f'<a href="data:application/pdf;base64,{b64_pdf_main}" target="_blank">View PDF in Browser</a>'

    col1, col2 = st.columns([1, 1])
    with col1:
        st.download_button(
            "Download Daily Page PDF", 
            pdf_bytes_main, 
            file_name=f"This_Day_in_History_{today.strftime('%Y%m%d')}.pdf",
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


def show_trivia_page():
    st.title("🧠 Daily Trivia Challenge!")
    st.button("⬅️ Back to Main Page", on_click=set_page, args=('main_app',), key="back_to_main_from_trivia_top")

    if st.session_state['daily_data'] and st.session_state['daily_data']['trivia_section']:
        trivia_questions = st.session_state['daily_data']['trivia_section']

        for i, trivia_item in enumerate(trivia_questions):
            question_key_base = f"trivia_q_{i}" # Base key for state
            
            # Initialize state for this question if not already present
            if question_key_base not in st.session_state['trivia_question_states']:
                st.session_state['trivia_question_states'][question_key_base] = {
                    'user_answer': '',
                    'is_correct': False,
                    'feedback': '',
                    'hint_revealed': False, # New: track if hint has been revealed for this question
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
                    disabled=q_state['is_correct']
                )
                q_state['user_answer'] = user_input # Update state on input change for persistence

            with col_check:
                if not q_state['is_correct']: # Only show check button if not yet correct
                    if st.button("Check", key=f"check_btn_{question_key_base}", disabled=not user_input.strip()):
                        if user_input.strip().lower() == trivia_item['answer'].strip().lower():
                            q_state['is_correct'] = True
                            q_state['feedback'] = "✅ Correct!"
                            st.success(q_state['feedback'])
                        else:
                            q_state['is_correct'] = False # Ensure it's false
                            q_state['feedback'] = "❌ Incorrect. Try again!"
                            st.error(q_state['feedback'])
                        st.rerun() # Rerun to update feedback/disable input immediately

            with col_hint:
                # Show hint button only if not correct and hints are remaining and hint not already revealed for this question
                if not q_state['is_correct'] and st.session_state['hints_remaining'] > 0 and not q_state['hint_revealed']:
                    if st.button(f"Hint ({st.session_state['hints_remaining']})", key=f"hint_btn_{question_key_base}"):
                        st.session_state['hints_remaining'] -= 1
                        q_state['hint_revealed'] = True
                        st.info(f"Hint: {trivia_item['hint']}")
                        st.rerun() # Rerun to update hint count and hide button
                elif q_state['hint_revealed']:
                    st.info(f"Hint: {trivia_item['hint']}") # Always display hint if it was revealed

            # Display general feedback if not correct
            if q_state['feedback'] and not q_state['is_correct']:
                st.error(q_state['feedback'])
            
            # Display final correct message
            elif q_state['is_correct']:
                st.success(f"✅ Correct! The answer was: **{trivia_item['answer']}**")
            
        st.markdown("---")
        # Check if all questions are answered correctly
        all_correct = all(st.session_state['trivia_question_states'][f"trivia_q_{i}"]['is_correct'] for i in range(len(trivia_questions)))
        if all_correct:
            st.success("You've completed the trivia challenge for today!")
        else:
            st.info(f"You have {st.session_state['hints_remaining']} hints remaining.")

        st.button("⬅️ Back to Main Page", on_click=set_page, args=('main_app',), key="back_to_main_from_trivia_bottom")
    else:
        st.write("No trivia questions available for today. Please go back to the main page.")
        st.button("⬅️ Back to Main Page", on_click=set_page, args=('main_app',), key="back_to_main_from_trivia_no_questions")


def show_login_register_page():
    st.title("Login to Access")
    login_tab, register_tab = st.tabs(["Log In", "Register"])
    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username_input")
            password = st.text_input("Password", type="password", key="login_password_input")
            if st.form_submit_button("Log In", key="login_submit_button"):
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
            new_password = st.text_input("New Password", type="password", key="register_password_input")
            confirm_password = st.text_input("Confirm Password", type="password", key="register_confirm_password_input")
            if st.form_submit_button("Register", key="register_submit_button"):
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
    example_data = get_this_day_in_history_facts(january_1st_example_date.day, january_1st_example_date.month, example_user_info, client_ai)

    st.markdown(f"### ✨ A Look Back at {january_1st_example_date.strftime('%B %d')}")
    st.markdown("### 🗓️ Significant Event")
    st.write(example_data['event_article'])

    st.markdown("### 🎂 Born on this Day")
    st.write(example_data['born_article'])

    st.markdown("### 💡 Fun Fact")
    st.write(example_data['fun_fact_section'])

    st.markdown("### 🧠 Test Your Knowledge!")
    if example_data['trivia_section']:
        for i, trivia_item in enumerate(example_data['trivia_section']):
            st.markdown(f"**Question {i+1}:** {trivia_item['question']}")
            st.info(f"Answer: {trivia_item['answer']}") # Display answer for example content
            if trivia_item['hint']:
                st.info(f"Hint: {trivia_item['hint']}")
    else:
        st.write("No trivia questions available.")


    st.markdown("### 🌟 Did You Know?")
    for fact in example_data['did_you_know_section']:
        st.markdown(f"- {fact}")

    st.markdown("### 💬 Memory Lane Prompt")
    st.write(example_data['memory_prompt_section'])

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
    st.sidebar.title("This Day in History")
    st.sidebar.markdown("---")
    st.sidebar.header("Navigation")
    if st.sidebar.button("🏠 Home", key="sidebar_home_btn"):
        set_page('main_app')
    if st.sidebar.button("🎮 Play Trivia!", key="sidebar_trivia_btn"):
        set_page('trivia_page')

    st.sidebar.markdown("---")
    st.sidebar.header("Settings")
    st.session_state['dementia_mode'] = st.sidebar.checkbox("Dementia-Friendly Mode", value=st.session_state['dementia_mode'], key="sidebar_dementia_mode")

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
