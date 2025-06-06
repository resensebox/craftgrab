import streamlit as st
import pandas as pd
import requests
import openai
from datetime import datetime

# --- Configuration ---
API_KEY = "AIzaSyBct8VijIiwffgvu8Z2qjVB8Dt4cFQN3wY"
CSE_ID = "34a2fb94f239b48ce"
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
openai.api_key = OPENAI_API_KEY

# --- Streamlit UI Config ---
st.set_page_config(page_title="CraftGrab - Yarn Deals", layout="wide")
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
    </style>
""", unsafe_allow_html=True)

# --- Header with Logo ---
st.image("https://i.postimg.cc/kXNf3Hpw/Gemini-Generated-Image-wyx05ewyx05ewyx0.png", width=200)
st.title("🧶 CraftGrab")
st.subheader("Snag crafty deals. Track your stash. Save smart.")

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
        return [item for item in items if "amazon" in item.get("link", "") or "joann" in item.get("link", "") or "michaels" in item.get("link", "") or "yarnspirations" in item.get("link", "") or "marymaxim" in item.get("link", "")]
    else:
        st.error(f"Search failed: {response.status_code} - {response.text}")
        return []

# --- Check if Item is in Stash ---
def is_in_stash(title):
    for item in st.session_state.get("stash", []):
        if item["Name"].lower() in title.lower():
            return True
    return False

# --- Display Deals in Columns ---
def display_deals_grid(results):
    cols = st.columns(3)
    for idx, result in enumerate(results):
        col = cols[idx % 3]
        with col:
            title = result.get('title', 'No Title')
            link = result.get('link', '#')
            snippet = result.get('snippet', '')
            image_url = result.get('pagemap', {}).get('cse_image', [{}])[0].get('src', '')
            col.markdown(f"#### [{title}]({link})")
            if image_url and image_url.startswith("http"):
                col.image(image_url, use_column_width=True)
            else:
                col.markdown("*(No image available)*")
            col.write(snippet)
            if is_in_stash(title):
                col.success("✅ You already have this in your stash!")
            col.markdown("---")

# --- Search UI ---
query = st.text_input("Search for a yarn deal:", "yarn sale site:joann.com")
if st.button("Search Deals"):
    with st.spinner("Searching the internet for yarn deals..."):
        results = search_yarn_deals(query)
    if results:
        st.markdown("### 🧵 Yarn Deals You Can Buy")
        display_deals_grid(results)
    else:
        st.info("No results found.")

# --- Stash Tracker ---
st.markdown("### 🧺 Your Yarn Stash")
if "stash" not in st.session_state:
    st.session_state.stash = []

with st.form("stash_form"):
    yarn_name = st.text_input("Yarn Name")
    quantity = st.number_input("Skeins", 1, 100, 1)
    fiber_type = st.text_input("Fiber Type")
    weight_type = st.selectbox("Yarn Weight", ["Lace", "Fingering", "Sport", "DK", "Worsted", "Bulky", "Super Bulky"])
    yardage = st.number_input("Total Yardage", 0, 10000, 0)
    submit = st.form_submit_button("Add to Stash")

    if submit and yarn_name:
        st.session_state.stash.append({
            "Name": yarn_name,
            "Skeins": quantity,
            "Fiber": fiber_type,
            "Weight": weight_type,
            "Yardage": yardage
        })

if st.session_state.stash:
    df_stash = pd.DataFrame(st.session_state.stash)
    st.dataframe(df_stash)
    st.markdown("#### Filter Stash")
    selected_weight = st.selectbox("Filter by Weight", ["All"] + df_stash["Weight"].unique().tolist())
    if selected_weight != "All":
        st.dataframe(df_stash[df_stash["Weight"] == selected_weight])
else:
    st.info("No yarn in stash yet. Add some above!")

# --- Wishlist ---
st.markdown("### 🧾 Wishlist")
if "wishlist" not in st.session_state:
    st.session_state.wishlist = []

with st.form("wishlist_form"):
    wish_name = st.text_input("Wishlist Item Name")
    wish_price = st.text_input("Target Price")
    wish_store = st.text_input("Preferred Store")
    wish_submit = st.form_submit_button("Add to Wishlist")
    if wish_submit and wish_name:
        st.session_state.wishlist.append({
            "Item": wish_name,
            "Target Price": wish_price,
            "Store": wish_store
        })

if st.session_state.wishlist:
    st.dataframe(pd.DataFrame(st.session_state.wishlist))
else:
    st.info("No items in wishlist yet.")

# --- Coming Soon ---
st.markdown("### 🧶 Coming Soon")
st.markdown("- Project Organizer (link stash to patterns)")
st.markdown("- Local store deals map")
st.caption("CraftGrab MVP v0.3")
