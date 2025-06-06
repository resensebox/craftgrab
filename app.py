import streamlit as st
import pandas as pd


st.set_page_config(page_title="CraftGrab Yarn Deals", layout="wide")

st.sidebar.title("CraftGrab Navigation")
page = st.sidebar.radio("Go to", ["Home", "Browse All Yarn Deals"])



# =====================
# Yarn Scrapers (US Stores)
# =====================

import requests
from bs4 import BeautifulSoup

def scrape_yarn_com(search_term=None):
    url = "https://www.yarn.com/categories/sirdar-yarn"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    products = []
    for item in soup.select(".productgrid--item"):
        name_tag = item.select_one(".productitem--title")
        price_tag = item.select_one(".price--compare")
        sale_tag = item.select_one(".price--highlight")
        link_tag = item.find("a", href=True)

        if name_tag and sale_tag and price_tag:
            name = name_tag.text.strip()
            if search_term and search_term.lower() not in name.lower():
                continue

            original_price = price_tag.text.strip()
            sale_price = sale_tag.text.strip()
            product_url = "https://www.yarn.com" + link_tag['href'] if link_tag else "N/A"

            products.append({
                "Product Name": name,
                "Original Price": original_price,
                "Sale Price": sale_price,
                "Product URL": product_url
            })

    return products


def scrape_joann(search_term=None):
    url = "https://www.joann.com/yarn/sale/"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    products = []
    for item in soup.select(".product-tile"):
        name_tag = item.select_one(".product-name")
        price_tag = item.select_one(".sr-only.regular-price")
        sale_tag = item.select_one(".sr-only.sales-price")
        link_tag = item.find("a", href=True)

        if name_tag and sale_tag and price_tag:
            name = name_tag.text.strip()
            if search_term and search_term.lower() not in name.lower():
                continue

            original_price = price_tag.text.strip()
            sale_price = sale_tag.text.strip()
            product_url = "https://www.joann.com" + link_tag['href'] if link_tag else "N/A"

            products.append({
                "Product Name": name,
                "Original Price": original_price,
                "Sale Price": sale_price,
                "Product URL": product_url
            })

    return products


def scrape_michaels(search_term=None):
    url = "https://www.michaels.com/yarn-clearance"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    products = []
    for item in soup.select(".product"):
        name_tag = item.select_one(".product-name")
        price_tag = item.select_one(".regular-price")
        sale_tag = item.select_one(".sale-price")
        link_tag = item.find("a", href=True)

        if name_tag and sale_tag and price_tag:
            name = name_tag.text.strip()
            if search_term and search_term.lower() not in name.lower():
                continue

            original_price = price_tag.text.strip()
            sale_price = sale_tag.text.strip()
            product_url = "https://www.michaels.com" + link_tag['href'] if link_tag else "N/A"

            products.append({
                "Product Name": name,
                "Original Price": original_price,
                "Sale Price": sale_price,
                "Product URL": product_url
            })

    return products


def scrape_knitpicks(search_term=None):
    url = "https://www.knitpicks.com/sale/yarn/c/301027"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    products = []
    for item in soup.select(".product-tile"):
        name_tag = item.select_one(".product-tile__title")
        price_tag = item.select_one(".price--compare")
        sale_tag = item.select_one(".price--highlight")
        link_tag = item.find("a", href=True)

        if name_tag and sale_tag and price_tag:
            name = name_tag.text.strip()
            if search_term and search_term.lower() not in name.lower():
                continue

            original_price = price_tag.text.strip()
            sale_price = sale_tag.text.strip()
            product_url = "https://www.knitpicks.com" + link_tag['href'] if link_tag else "N/A"

            products.append({
                "Product Name": name,
                "Original Price": original_price,
                "Sale Price": sale_price,
                "Product URL": product_url
            })

    return products


def scrape_wecrochet(search_term=None):
    url = "https://www.wecrochet.com/sale/yarn/c/301027"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    products = []
    for item in soup.select(".product-tile"):
        name_tag = item.select_one(".product-tile__title")
        price_tag = item.select_one(".price--compare")
        sale_tag = item.select_one(".price--highlight")
        link_tag = item.find("a", href=True)

        if name_tag and sale_tag and price_tag:
            name = name_tag.text.strip()
            if search_term and search_term.lower() not in name.lower():
                continue

            original_price = price_tag.text.strip()
            sale_price = sale_tag.text.strip()
            product_url = "https://www.wecrochet.com" + link_tag['href'] if link_tag else "N/A"

            products.append({
                "Product Name": name,
                "Original Price": original_price,
                "Sale Price": sale_price,
                "Product URL": product_url
            })

    return products


def scrape_all_us_stores(search_term=None):
    all_results = []
    all_results.extend(scrape_yarn_com(search_term))
    all_results.extend(scrape_joann(search_term))
    all_results.extend(scrape_michaels(search_term))
    all_results.extend(scrape_knitpicks(search_term))
    all_results.extend(scrape_wecrochet(search_term))
    return all_results


import requests
import openai
from datetime import datetime
import re
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- Configuration ---
API_KEY = st.secrets["google_cse_api_key"]
CSE_ID = st.secrets["google_cse_cx"]
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
        /* The .deal-card styling has been removed here to take out the visual boxes */
        .deal-card h4 {
            margin-top: 0.5rem;
            margin-bottom: 0.5rem;
        }
        .deal-card img {
            max-height: 200px; /* Limit image height */
            object-fit: contain; /* Ensure image fits without cropping */
            width: 100%;
            margin-bottom: 10px;
        }
        .stMultiSelect, .stSelectbox {
            margin-bottom: 10px;
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
            sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet("SearchLogs")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_row([timestamp, query, results_count])
        except gspread.exceptions.WorksheetNotFound:
            st.error("❌ Worksheet 'SearchLogs' not found. Please create it in your Google Sheet with the specified ID and name 'SearchLogs'.")
        except gspread.exceptions.APIError as api_error:
            st.error(f"❌ API Error when accessing the sheet. Please check permissions and sheet ID: {api_error}")
        except Exception as e:
            st.error(f"❌ Unexpected error logging to Google Sheets: {repr(e)}. Ensure your service account has edit access to the Google Sheet.")


# --- Search Deals Function ---
def search_yarn_deals(query):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": API_KEY,
        "cx": CSE_ID,
        "q": query,
        "num": 10
    }
    try:
        response = requests.get(url, params=params, timeout=5) # Added timeout
        response.raise_for_status() # Raise an exception for HTTP errors
        items = response.json().get("items", [])
        return items
    except requests.exceptions.Timeout:
        st.error("Search request timed out. Please try again.")
        return []
    except requests.exceptions.RequestException as e:
        st.error(f"Search failed due to a network error: {e}")
        return []
    except Exception as e:
        st.error(f"An unexpected error occurred during search: {e}")
        return []


# --- AI Summary for Each Result (Enhanced with Caching) ---
@st.cache_data(show_spinner=False) # Cache the output of this function
def summarize_item(item):
    title = item.get('title', 'No Title')
    snippet = item.get('snippet', '')
    html_snippet = item.get('htmlSnippet', '')
    link = item.get('link', '#')

    prompt = f"""
    You are a helpful assistant specialized in e-commerce product summarization for crafting supplies, specifically yarn.
    Analyze the provided listing (title and snippet ONLY) and extract the following details as accurately as possible.
    If the information is not explicitly stated but can be clearly inferred, please provide it.
    Categorize the "Listing Type" and identify any "Coupon Code".

    Extract the following details:
    1. **Product Name:** (e.g., "Lion Brand Wool-Ease Thick & Quick")
    2. **Store:** (e.g., "Joann Fabrics", "LoveCrafts")
    3. **Price:** (e.g., "$5.99", "Reg. $10, Now $7.50") - Prioritize sale price. If original and sale price are both mentioned, extract both. **Crucial: Extract any numerical price found.**
    4. **Sale Details:** (e.g., "50% off", "Buy One Get One Free", "Clearance")
    5. **Yarn Type/Material:** (e.g., "Acrylic worsted yarn", "Merino wool blend")
    6. **Key Features/Notes:** (Any other important details like weight, brand, color availability, specific deal terms).
    7. **Listing Type:** (Identify as "Product Page", "Category Page", "Blog Post", or "General Website").
    8. **Coupon Code:** (If a specific code is mentioned, e.g., "SAVE20", otherwise "N/A" or "See site for details").

    If a piece of information is genuinely not present or cannot be inferred from the provided text, state "N/A".
    Be concise but ensure all requested information is extracted if available.

    Title: {title}
    Snippet: {snippet}
    Link: {link}
    """
    try:
        response = openai.chat.completions.create(
            # Using gpt-3.5-turbo for faster summarization. Change to "gpt-4" for potentially higher quality but slower results.
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300 # Increased max tokens to accommodate more detailed summary
        )
        summary_text = response.choices[0].message.content.strip()

        parsed_info = {
            "Product Name": "N/A", "Store": "N/A", "Price": "N/A",
            "Sale Details": "N/A", "Yarn Type/Material": "N/A", "Key Features/Notes": "N/A",
            "Listing Type": "N/A", "Coupon Code": "N/A" # Added new fields
        }
        for line in summary_text.split('\n'):
            if ":" in line:
                key, value = line.split(':', 1)
                key = key.strip().replace('**', '')
                value = value.strip()
                if key in parsed_info:
                    parsed_info[key] = value
        return parsed_info, summary_text
    except openai.APIError as e:
        st.warning(f"OpenAI API error for item '{title}': {e}. This might be due to rate limits or invalid requests.")
        return {k: "Summary unavailable." for k in parsed_info.keys()}, "Summary unavailable due to API error."
    except Exception as e:
        st.warning(f"AI summary failed for item '{title}': {e}")
        return {k: "Summary unavailable." for k in parsed_info.keys()}, "Summary unavailable."

def extract_price_value(price_string):
    """Extracts a numerical price from a price string."""
    if isinstance(price_string, str):
        # Improved regex to handle various price formats including ranges and "Reg. $X"
        # It tries to find the first numerical price that looks like a direct price.
        match = re.search(r'(?:\$?(\d[\d,]*\.?\d{0,2})(?:\s*-\s*\$?\d[\d,]*\.?\d{0,2})?|\bReg\.\s*\$?(\d[\d,]*\.?\d{0,2}))', price_string, re.IGNORECASE)
        if match:
            # Prioritize the direct price capture group, then the "Reg." price capture group
            if match.group(1):
                try:
                    return float(match.group(1).replace(',', ''))
                except ValueError:
                    pass
            elif match.group(2):
                try:
                    return float(match.group(2).replace(',', ''))
                except ValueError:
                    pass
    return None

# --- Check if Item is in Stash ---

def is_in_stash(title):
    title = title.lower()
    for item in st.session_state.get("stash", []):
        stash_name = item["Name"].lower()
        if fuzzy_match(stash_name, title):
            return True
    return False

    for item in st.session_state.get("stash", []):
        if item["Name"].lower() in title.lower():
            return True
    return False

# --- Deal Ranking Logic ---

from difflib import SequenceMatcher
def fuzzy_match(a, b):
    return SequenceMatcher(None, a, b).ratio() > 0.75

def rank_deals(summarized_deals, search_query):
    ranked_deals = []
    for summary_info, raw_summary, item in summarized_deals:
        rank_score = 0
        title = item.get('title', '').lower()
        snippet = item.get('snippet', '').lower()

        # Keyword matching
        query_keywords = set(search_query.lower().split())
        for keyword in query_keywords:
            if keyword in title or keyword in snippet:
                rank_score += 2
            if keyword in raw_summary.lower():
                rank_score += 1 # Boost for keywords in AI summary

        # Price availability and deal significance
        price = summary_info.get("Price", "N/A")
        sale_details = summary_info.get("Sale Details", "").lower()

        if price != "N/A":
            rank_score += 3
            if "off" in sale_details or "discount" in sale_details or "clearance" in sale_details:
                rank_score += 4 # Higher boost for clear sale indicators
            elif "buy one get one" in sale_details or "bogo" in sale_details:
                rank_score += 3
            elif "sale" in sale_details:
                rank_score += 2

        # Store preference (could be user-configurable)
        # Example: prioritize specific stores
        # if "joann" in summary_info.get("Store", "").lower() or "hobby lobby" in summary_info.get("Store", "").lower():
        #     rank_score += 1

        # Check if already in stash (lower rank for items already owned)
        if is_in_stash(title):
            rank_score -= 10 # Stronger penalty

        # --- Yarn Relevance Check (New) ---
        yarn_type = summary_info.get("Yarn Type/Material", "").lower()
        product_name_summary = summary_info.get("Product Name", "").lower() # Product name from AI summary

        is_definitely_yarn = False
        yarn_keywords = ["yarn", "wool", "acrylic", "cotton", "merino", "alpaca", "silk", "blend", "fiber", "skein", "hank", "ball", "crochet", "knit"]

        # Check in AI-summarized yarn type/material, product name, and original title/snippet
        if any(keyword in yarn_type for keyword in yarn_keywords):
            is_definitely_yarn = True
        elif any(keyword in product_name_summary for keyword in yarn_keywords):
            is_definitely_yarn = True
        elif any(keyword in title for keyword in yarn_keywords):
            is_definitely_yarn = True
        elif any(keyword in snippet for keyword in yarn_keywords):
            is_definitely_yarn = True
        
        # Add a significant penalty if the item does not appear to be yarn
        # This will push non-yarn items to the very bottom of the results.
        if not is_definitely_yarn:
            rank_score -= 100 # A large penalty to effectively filter out non-yarn items

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
    with st.spinner("Analyzing deals with AI (first-time summaries will take longer)..."):
        for item in results:
            title_snippet_combined = (item.get('title', '') + item.get('snippet', '')).lower()
            yarn_terms = ["yarn", "wool", "acrylic", "cotton", "fiber", "skein", "hank", "ball", "knit", "crochet"]
            if not any(term in title_snippet_combined for term in yarn_terms):
                continue  # Skip summarizing if clearly not yarn-related
            
            summary_info, raw_summary = summarize_item(item)
            if raw_summary != "Summary unavailable.":
                summarized_items.append((summary_info, raw_summary, item))

    if not summarized_items:
        st.info("No deals could be summarized. This might be due to AI API issues or content not being relevant.")
        return

    ranked_items = rank_deals(summarized_items, st.session_state.current_search_query)

    filtered_items = []
    for rank_score, summary_info, raw_summary, item in ranked_items:
        # Apply price filter
        price_value = extract_price_value(summary_info.get("Price"))
        if (filters["min_price"] is not None and (price_value is None or price_value < filters["min_price"])):
            continue
        if (filters["max_price"] is not None and (price_value is None or price_value > filters["max_price"])):
            continue

        # Apply keyword filter to summary and title
        if filters["keyword"]:
            filter_lower = filters["keyword"].lower()
            if not (filter_lower in raw_summary.lower() or filter_lower in item.get('title', '').lower()):
                continue

        filtered_items.append((rank_score, summary_info, raw_summary, item))


    if sort_option == "Lowest Price":
        filtered_items.sort(key=lambda x: extract_price_value(x[1].get("Price", "")) or float('inf'))
    elif sort_option == "Highest Discount":
        import re
        filtered_items.sort(key=lambda x: -1 if "%" not in x[1].get("Sale Details", "") else -int(re.findall(r'\\d+', x[1]["Sale Details"])[0]))


    if not filtered_items:
        st.info("No deals match your current filters.")
        return

    # Use columns to display cards
    num_cols = 3
    cols = st.columns(num_cols)

    for idx, (rank_score, summary_info, raw_summary, item) in enumerate(filtered_items):
        with cols[idx % num_cols]:
            st.markdown(f'<div class="deal-card">', unsafe_allow_html=True)
            title = item.get('title', 'No Title')
            link = item.get('link', '#')
            image_url = item.get('pagemap', {}).get('cse_image', [{}])[0].get('src', '')

            st.markdown(f"#### [{title}]({link})")
            if image_url and image_url.startswith("http"):
                st.image(image_url, use_container_width=True)
            else:
                st.markdown("*(No image available)*")

            st.write(f"**Store:** {summary_info.get('Store', 'N/A')}")
            st.write(f"**Price:** {summary_info.get('Price', 'N/A')}")
            st.write(f"**Sale Details:** {summary_info.get('Sale Details', 'N/A')}")
            st.write(f"**Yarn Type:** {summary_info.get('Yarn Type/Material', 'N/A')}")
            # Display new fields
            st.write(f"**Listing Type:** {summary_info.get('Listing Type', 'N/A')}")
            st.write(f"**Coupon Code:** {summary_info.get('Coupon Code', 'N/A')}")
            st.write(f"**Notes:** {summary_info.get('Key Features/Notes', 'N/A')}")


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
    st.session_state.last_search_results = []

# --- Search UI ---
st.sidebar.header("🔍 Find Deals")
query = st.sidebar.text_input("Search for a yarn deal:", value=st.session_state.current_search_query or "yarn sale site:joann.com OR site:lovecrafts.com OR site:knitpicks.com OR site:wecrochet.com")

# Price Filter
min_price = st.sidebar.number_input("Minimum Price", min_value=0.0, format="%.2f", value=None, key="min_price_filter")
max_price = st.sidebar.number_input("Maximum Price", min_value=0.0, format="%.2f", value=None, key="max_price_filter")
filter_keyword = st.sidebar.text_input("Filter by Keyword in Summary (e.g., 'merino', 'clearance')", key="keyword_filter")

sort_option = st.sidebar.selectbox("Sort results by", ["Best Match", "Lowest Price", "Highest Discount"])


search_button = st.sidebar.button("Search Deals")

if search_button:
    if query:
        st.session_state.current_search_query = query
        st.session_state.search_history.append({"query": query, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        with st.spinner(f"Searching the internet for '{query}' deals..."):
            results = search_yarn_deals(query)
            log_search_to_sheets(query, len(results))
            st.session_state.last_search_results = results
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
        fiber_type = st.text_input("Fiber Type (e.g., Wool, Acrylic, Cotton)", key="stash_fiber_type")
        weight_type = st.selectbox("Yarn Weight", ["Lace", "Fingering", "Sport", "DK", "Worsted", "Aran", "Bulky", "Super Bulky", "Jumbo"], key="stash_weight_type")
        color = st.text_input("Color", key="stash_color")
        dye_lot = st.text_input("Dye Lot (optional)", key="stash_dye_lot")
        purchase_date = st.date_input("Purchase Date (optional)", value=None, key="stash_purchase_date")
        notes = st.text_area("Notes (e.g., project ideas, special features)", key="stash_notes")
        submit = st.form_submit_button("Add to Stash")

        if submit and yarn_name:
            st.session_state.stash.append({
                "Name": yarn_name,
                "Skeins": quantity,
                "Fiber": fiber_type,
                "Weight": weight_type,
                "Color": color,
                "Dye Lot": dye_lot if dye_lot else "N/A",
                "Purchase Date": purchase_date.strftime("%Y-%m-%d") if purchase_date else "N/A",
                "Notes": notes if notes else "N/A"
            })
            st.success(f"'{yarn_name}' added to your stash!")
            st.rerun() # Rerun to clear the form fields

    if st.session_state.stash:
        df_stash = pd.DataFrame(st.session_state.stash)

        st.markdown("#### Filter Your Stash")
        col_filter1, col_filter2 = st.columns(2)
        with col_filter1:
            selected_weight = st.selectbox("Filter by Weight", ["All"] + df_stash["Weight"].unique().tolist(), key="filter_stash_weight")
        with col_filter2:
            selected_fiber = st.selectbox("Filter by Fiber Type", ["All"] + df_stash["Fiber"].unique().tolist(), key="filter_stash_fiber")

        filtered_df_stash = df_stash.copy()
        if selected_weight != "All":
            filtered_df_stash = filtered_df_stash[filtered_df_stash["Weight"] == selected_weight]
        if selected_fiber != "All":
            filtered_df_stash = filtered_df_stash[filtered_df_stash["Fiber"] == selected_fiber]

        st.dataframe(filtered_df_stash, use_container_width=True)

        if st.button("Clear Stash", key="clear_stash_button"):
            st.session_state.stash = []
            st.success("Your stash has been cleared!")
            st.rerun()
    else:
        st.info("No yarn in stash yet. Add some above!")

elif page == "Your Wishlist":
    st.markdown("### 🧾 Wishlist")
    with st.form("wishlist_form"):
        wish_name = st.text_input("Wishlist Item Name", key="wish_name")
        wish_price = st.text_input("Target Price (e.g., $10, $5.99)", key="wish_price_input")
        wish_store = st.text_input("Preferred Store", key="wish_store_input")
        wish_notes = st.text_area("Notes (e.g., specific color, reason)", key="wish_notes")
        wish_submit = st.form_submit_button("Add to Wishlist")
        if wish_submit and wish_name:
            st.session_state.wishlist.append({
                "Item": wish_name,
                "Target Price": wish_price if wish_price else "N/A",
                "Store": wish_store if wish_store else "N/A",
                "Notes": wish_notes if wish_notes else "N/A"
            })
            st.success(f"'{wish_name}' added to your wishlist!")
            st.rerun() # Rerun to clear form

    if st.session_state.wishlist:
        st.dataframe(pd.DataFrame(st.session_state.wishlist), use_container_width=True)
        if st.button("Clear Wishlist", key="clear_wishlist_button"):
            st.session_state.wishlist = []
            st.success("Your wishlist has been cleared!")
            st.rerun()
    else:
        st.info("No items in wishlist yet.")

elif page == "Search History":
    st.markdown("### 🕰️ Search History")
    if st.session_state.search_history:
        df_history = pd.DataFrame(st.session_state.search_history)
        st.dataframe(df_history, use_container_width=True)
        if st.button("Clear Search History", key="clear_history_button"):
            st.session_state.search_history = []
            st.success("Your search history has been cleared!")
            st.rerun()
    else:
        st.info("No search history yet.")

# --- Coming Soon ---
st.markdown("---")
st.markdown("### 🧶 Coming Soon")
st.markdown("- Project Organizer (link stash to patterns)")
st.markdown("- Local store deals map")
st.caption("CraftGrab MVP v1.1 - Enhanced Deal Finding and Stash Management")



# =====================
# 🧾 Website-Specific Yarn Sales
# =====================
st.header("🧾 Website-Specific Yarn Sales")

try:
    search_term_input = st.text_input("Search for a specific yarn or term (optional):", value="")
    if st.button("Search Sales Across Stores"):
        sales_data = scrape_all_us_stores(search_term_input if search_term_input else None)
        if sales_data:
            # Add website/source column
            for row in sales_data:
                if "yarn.com" in row["Product URL"]:
                    row["Website"] = "Yarn.com"
                elif "joann.com" in row["Product URL"]:
                    row["Website"] = "Joann"
                elif "michaels.com" in row["Product URL"]:
                    row["Website"] = "Michaels"
                elif "knitpicks.com" in row["Product URL"]:
                    row["Website"] = "KnitPicks"
                elif "wecrochet.com" in row["Product URL"]:
                    row["Website"] = "WeCrochet"
                else:
                    row["Website"] = "Unknown"

            df = pd.DataFrame(sales_data)
            df = df[["Product Name", "Original Price", "Sale Price", "Website", "Product URL"]]
            st.dataframe(df)
        else:
            st.write("No sale products found matching that term.")
except Exception as e:
    st.error(f"Error fetching sale data: {e}")



if page == "Browse All Yarn Deals":
    st.title("🧵 All Yarn Deals by Website")

    all_sales = scrape_all_us_stores()

    if all_sales:
        site_groups = {
            "Yarn.com": [],
            "Joann": [],
            "Michaels": [],
            "KnitPicks": [],
            "WeCrochet": []
        }

        for row in all_sales:
            if "yarn.com" in row["Product URL"]:
                site_groups["Yarn.com"].append(row)
            elif "joann.com" in row["Product URL"]:
                site_groups["Joann"].append(row)
            elif "michaels.com" in row["Product URL"]:
                site_groups["Michaels"].append(row)
            elif "knitpicks.com" in row["Product URL"]:
                site_groups["KnitPicks"].append(row)
            elif "wecrochet.com" in row["Product URL"]:
                site_groups["WeCrochet"].append(row)

        for site, products in site_groups.items():
            if products:
                st.subheader(f"{site} - {len(products)} Deals Found")
                df_site = pd.DataFrame(products)[["Product Name", "Original Price", "Sale Price", "Product URL"]]
                st.dataframe(df_site)
            else:
                st.subheader(f"{site} - No deals found.")
    else:
        st.write("No sales found right now.")
