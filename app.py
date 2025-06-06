import streamlit as st
import pandas as pd
import requests
import openai
from datetime import datetime
import re # For regular expressions
import gspread # For Google Sheets integration
from oauth2client.service_account import ServiceAccountCredentials # For Google Sheets authentication

# --- Configuration ---
API_KEY = st.secrets["google_cse_api_key"]  # Custom Search API Key
CSE_ID = st.secrets["google_cse_api_key"]        # Custom Search Engine ID
OPENAI_API_KEY = st.secrets["openai_api_key"]
openai.api_key = OPENAI_API_KEY

# --- Google Sheets Configuration ---
GOOGLE_SHEETS_CREDENTIALS = {
    "type": st.secrets["google_service_account"]["type"],
    "project_id": st.secrets["google_service_account"]["project_id"],
    "private_key_id": st.secrets["google_service_account"]["private_key_id"],
    "private_key": st.secrets["google_service_account"]["private_key"],
    "client_email": st.secrets["google_service_account"]["client_email"],
    "client_id": st.secrets["google_service_account"]["client_id"],
    "auth_uri": st.secrets["google_service_account"]["auth_uri"],
    "token_uri": st.secrets["google_service_account"]["token_uri"],
    "auth_provider_x509_cert_url": st.secrets["google_service_account"]["auth_provider_x509_cert_url"],
    "client_x509_cert_url": st.secrets["google_service_account"]["client_x509_cert_url"],
    "universe_domain": st.secrets["google_service_account"].get("universe_domain", "")
}

# Your actual Google Sheet ID
GOOGLE_SHEET_ID = "1L1fFRV8nlq4gwUk20CDYSizgO0ycY5EvGNQPyJKHreo"

# --- Streamlit UI Config ---
st.set_page_config(page_title="CraftGrab - Yarn Deals", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
    <style>
        body {
            background-color: white;
            font-family: 'Helvetica Neue', sans-serif;
        }
        .main h1, .main h2, .main h3, .main h4 {
            color: #8F5FE8;
        }
        .block-container {
            padding-top: 1rem;
        }
        .stButton>button {
            background-color: #8F5FE8;
            color: white;
            border-radius: 5px;
            border: none;
            padding: 10px 20px;
            cursor: pointer;
        }
        .stButton>button:hover {
            background-color: #7A4CD1;
        }
        .stTextInput>div>div>input {
            border-radius: 5px;
            border: 1px solid #ccc;
            padding: 10px;
        }
        .deal-card {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 2px 2px 8px rgba(0,0,0,0.1);
        }
    </style>
""", unsafe_allow_html=True)


# --- Header with Logo ---
col1, col2 = st.columns([1, 4])
with col1:
    st.image("https://i.postimg.cc/kXNf3Hpw/Gemini-Generated-Image-wyx05ewyx05ewyx0.png", width=150)
with col2:
    st.title("🧶 CraftGrab")
    st.subheader("Snag crafty deals. Track your stash. Save smart.")

# --- Google Sheets Functions ---
@st.cache_resource
def get_google_sheet_client():
    """Authenticates and returns a gspread client."""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_SHEETS_CREDENTIALS, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Error authenticating with Google Sheets: {e}")
        return None

def log_search_to_sheets(query, results_count):
    """Logs search queries and results to Google Sheets."""
    client = get_google_sheet_client()
    if client:
        try:
            sheet = client.open_by_id(GOOGLE_SHEET_ID).worksheet("SearchLogs") # Assuming a worksheet named "SearchLogs"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([timestamp, query, results_count])
        except gspread.exceptions.WorksheetNotFound:
            st.warning("Worksheet 'SearchLogs' not found. Please create it in your Google Sheet with the specified ID.")
        except Exception as e:
            st.error(f"Error logging to Google Sheets: {e}")

# --- Search Deals Function ---
def search_yarn_deals(query):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": API_KEY,
        "cx": CSE_ID,
        "q": query,
        "num": 10
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        items = response.json().get("items", [])
        return items
    else:
        st.error(f"Search failed: {response.status_code} - {response.text}")
        return []

# --- AI Summary for Each Result (Enhanced) ---
def summarize_item(item):
    title = item.get('title', 'No Title')
    snippet = item.get('snippet', '')
    html_snippet = item.get('htmlSnippet', '')
    link = item.get('link', '#')

    prompt = f"""
    You are a helpful assistant specialized in e-commerce product summarization.
    Summarize this product listing with key sale information.
    Extract the following details as accurately as possible:
    1. **Product Name:** (e.g., "Lion Brand Wool-Ease Thick & Quick")
    2. **Store:** (e.g., "Joann Fabrics", "LoveCrafts")
    3. **Price:** (e.g., "$5.99", "Reg. $10, Now $7.50") - Prioritize sale price.
    4. **Sale Details:** (e.g., "50% off", "Buy One Get One Free", "Clearance")
    5. **Yarn Type/Material:** (e.g., "Acrylic worsted yarn", "Merino wool blend")
    6. **Key Features/Notes:** (Any other important details like weight, brand, color availability).

    If a piece of information is not present, state "N/A".
    Be concise but ensure all requested information is extracted if available.

    Title: {title}
    Snippet: {snippet}
    HTML Body (if available): {html_snippet}
    Link: {link}
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3, # Slightly lower temperature for more factual extraction
            max_tokens=200 # Increased max_tokens for more detailed summary
        )
        summary_text = response.choices[0].message.content.strip()

        # Attempt to parse structured info from the summary for better filtering
        parsed_info = {
            "Product Name": "N/A", "Store": "N/A", "Price": "N/A",
            "Sale Details": "N/A", "Yarn Type/Material": "N/A", "Key Features/Notes": "N/A"
        }
        for line in summary_text.split('\n'):
            if ":" in line:
                key, value = line.split(':', 1)
                key = key.strip().replace('**', '') # Clean up markdown
                value = value.strip()
                if key in parsed_info:
                    parsed_info[key] = value
        return parsed_info, summary_text # Return both structured and raw summary
    except Exception as e:
        st.warning(f"AI summary failed for item '{title}': {e}")
        return {k: "Summary unavailable." for k in ["Product Name", "Store", "Price", "Sale Details", "Yarn Type/Material", "Key Features/Notes"]}, "Summary unavailable."

def extract_price_value(price_string):
    """Extracts a numerical price from a price string."""
    if isinstance(price_string, str):
        # Regex to find common price formats, e.g., $X.XX, X.XX, $X
        match = re.search(r'\$?(\d+\.?\d*)', price_string)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
    return None

# --- Check if Item is in Stash ---
def is_in_stash(title):
    for item in st.session_state.get("stash", []):
        if item["Name"].lower() in title.lower():
            return True
    return False

# --- Deal Ranking Logic ---
def rank_deals(summarized_deals, search_query):
    ranked_deals = []
    for summary_info, raw_summary, item in summarized_deals:
        rank_score = 0
        title = item.get('title', '').lower()
        snippet = item.get('snippet', '').lower()

        # Keyword matching (simple)
        for keyword in search_query.lower().split():
            if keyword in title or keyword in snippet:
                rank_score += 2

        # Price availability
        if summary_info.get("Price") != "N/A":
            rank_score += 3
            # Further boost for specific sale details (e.g., "off", "clearance")
            if "off" in summary_info.get("Sale Details", "").lower() or \
               "clearance" in summary_info.get("Sale Details", "").lower():
                rank_score += 2

        # Store preference (can be added as user input)
        # if "joann" in summary_info.get("Store", "").lower():
        #     rank_score += 1

        # Check if already in stash (lower rank for items already owned)
        if is_in_stash(title):
            rank_score -= 5 # Penalize if already in stash

        # Add original item and its score
        ranked_deals.append((rank_score, summary_info, raw_summary, item))

    # Sort in descending order of rank_score
    ranked_deals.sort(key=lambda x: x[0], reverse=True)
    return ranked_deals

# --- Display Deals in Columns with Ranking ---
def display_deals_grid(results, filters):
    st.markdown("### ✨ Top Ranked Deals")
    if not results:
        st.info("No deals found for your search query.")
        return

    summarized_items = []
    for item in results:
        summary_info, raw_summary = summarize_item(item)
        if raw_summary != "Summary unavailable.":
            summarized_items.append((summary_info, raw_summary, item))

    ranked_items = rank_deals(summarized_items, st.session_state.current_search_query)

    filtered_items = []
    for rank_score, summary_info, raw_summary, item in ranked_items:
        # Apply price filter
        if filters["min_price"] is not None or filters["max_price"] is not None:
            price_value = extract_price_value(summary_info.get("Price"))
            if price_value is not None:
                if filters["min_price"] is not None and price_value < filters["min_price"]:
                    continue
                if filters["max_price"] is not None and price_value > filters["max_price"]:
                    continue
            elif filters["min_price"] is not None or filters["max_price"] is not None:
                # If price is N/A and filter is active, skip
                continue

        # Apply keyword filter to summary
        if filters["keyword"]:
            if filters["keyword"].lower() not in raw_summary.lower() and \
               filters["keyword"].lower() not in item.get('title', '').lower():
                continue

        filtered_items.append((rank_score, summary_info, raw_summary, item))

    if not filtered_items:
        st.info("No deals match your current filters.")
        return

    cols = st.columns(3)
    for idx, (rank_score, summary_info, raw_summary, item) in enumerate(filtered_items):
        col = cols[idx % 3]
        with col:
            st.markdown(f'<div class="deal-card">', unsafe_allow_html=True)
            title = item.get('title', 'No Title')
            link = item.get('link', '#')
            image_url = item.get('pagemap', {}).get('cse_image', [{}])[0].get('src', '')

            st.markdown(f"**Rank: {rank_score}**")
            st.markdown(f"#### [{title}]({link})")
            if image_url and image_url.startswith("http"):
                st.image(image_url, use_container_width=True)
            else:
                st.markdown("*(No image available)*")

            st.write(f"**Store:** {summary_info.get('Store')}")
            st.write(f"**Price:** {summary_info.get('Price')}")
            st.write(f"**Sale Details:** {summary_info.get('Sale Details')}")
            st.write(f"**Yarn Type:** {summary_info.get('Yarn Type/Material')}")
            st.caption(f"_{raw_summary}_") # Original AI summary for context

            if is_in_stash(title):
                st.success("✅ You already have this in your stash!")

            st.markdown("</div>", unsafe_allow_html=True)

# --- Initialize Session State for Stash and Wishlist ---
if "stash" not in st.session_state:
    st.session_state.stash = []
if "wishlist" not in st.session_state:
    st.session_state.wishlist = []
if "search_history" not in st.session_state:
    st.session_state.search_history = []
if "current_search_query" not in st.session_state:
    st.session_state.current_search_query = ""
if "last_search_results" not in st.session_state:
    st.session_state.last_search_results = [] # Initialize to an empty list

# --- Search UI ---
st.sidebar.header("🔍 Find Deals")
query = st.sidebar.text_input("Search for a yarn deal:", value=st.session_state.current_search_query or "yarn sale site:joann.com")

# Price Filter
min_price = st.sidebar.number_input("Minimum Price", min_value=0.0, format="%.2f", value=None)
max_price = st.sidebar.number_input("Maximum Price", min_value=0.0, format="%.2f", value=None)
filter_keyword = st.sidebar.text_input("Filter by Keyword in Summary (e.g., 'merino', 'clearance')")

search_button = st.sidebar.button("Search Deals")

if search_button:
    if query:
        st.session_state.current_search_query = query
        st.session_state.search_history.append({"query": query, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        with st.spinner(f"Searching the internet for '{query}' deals..."):
            results = search_yarn_deals(query)
            log_search_to_sheets(query, len(results)) # Log the search
            st.session_state.last_search_results = results # Store results to re-filter
        if not results:
            st.info("No results found for your search.")
    else:
        st.warning("Please enter a search query.")

# Display results if a search has been performed or if filters are changed
if st.session_state.last_search_results:
    filters = {
        "min_price": min_price,
        "max_price": max_price,
        "keyword": filter_keyword
    }
    display_deals_grid(st.session_state.last_search_results, filters)


# --- Sidebar Navigation ---
st.sidebar.markdown("---")
st.sidebar.header("Your Crafting Hub")
page = st.sidebar.radio("Go to", ["Find Deals", "Your Yarn Stash", "Your Wishlist", "Search History"])

if page == "Your Yarn Stash":
    st.markdown("### 🧺 Your Yarn Stash")
    with st.form("stash_form"):
        yarn_name = st.text_input("Yarn Name", key="stash_yarn_name")
        quantity = st.number_input("Skeins", 1, 100, 1, key="stash_quantity")
        fiber_type = st.text_input("Fiber Type", key="stash_fiber_type")
        weight_type = st.selectbox("Yarn Weight", ["Lace", "Fingering", "Sport", "DK", "Worsted", "Bulky", "Super Bulky"], key="stash_weight_type")
        yardage = st.number_input("Total Yardage", 0, 10000, 0, key="stash_yardage")
        submit = st.form_submit_button("Add to Stash")

        if submit and yarn_name:
            st.session_state.stash.append({
                "Name": yarn_name,
                "Skeins": quantity,
                "Fiber": fiber_type,
                "Weight": weight_type,
                "Yardage": yardage
            })
            st.success(f"'{yarn_name}' added to your stash!")

    if st.session_state.stash:
        df_stash = pd.DataFrame(st.session_state.stash)
        st.dataframe(df_stash)
        st.markdown("#### Filter Stash")
        selected_weight = st.selectbox("Filter by Weight", ["All"] + df_stash["Weight"].unique().tolist(), key="filter_stash_weight")
        if selected_weight != "All":
            st.dataframe(df_stash[df_stash["Weight"] == selected_weight])
        if st.button("Clear Stash"):
            st.session_state.stash = []
            st.rerun()
    else:
        st.info("No yarn in stash yet. Add some above!")

elif page == "Your Wishlist":
    st.markdown("### 🧾 Wishlist")
    with st.form("wishlist_form"):
        wish_name = st.text_input("Wishlist Item Name", key="wish_name")
        wish_price = st.text_input("Target Price (e.g., $10, $5.99)", key="wish_price")
        wish_store = st.text_input("Preferred Store", key="wish_store")
        wish_submit = st.form_submit_button("Add to Wishlist")
        if wish_submit and wish_name:
            st.session_state.wishlist.append({
                "Item": wish_name,
                "Target Price": wish_price,
                "Store": wish_store
            })
            st.success(f"'{wish_name}' added to your wishlist!")

    if st.session_state.wishlist:
        st.dataframe(pd.DataFrame(st.session_state.wishlist))
        if st.button("Clear Wishlist"):
            st.session_state.wishlist = []
            st.rerun()
    else:
        st.info("No items in wishlist yet.")

elif page == "Search History":
    st.markdown("### 🕰️ Search History")
    if st.session_state.search_history:
        df_history = pd.DataFrame(st.session_state.search_history)
        st.dataframe(df_history)
        if st.button("Clear Search History"):
            st.session_state.search_history = []
            st.rerun()
    else:
        st.info("No search history yet.")

# --- Coming Soon ---
st.markdown("---")
st.markdown("### 🧶 Coming Soon")
st.markdown("- Project Organizer (link stash to patterns)")
st.markdown("- Local store deals map")
st.caption("CraftGrab MVP v1.0")
