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

# --- Search Deals Function ---
def search_yarn_deals(query):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": API_KEY,
        "cx": CSE_ID,
        "q": query,
        "num": 5
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get("items", [])
    else:
        st.error(f"Search failed: {response.status_code} - {response.text}")
        return []

# --- Summarize Deals with OpenAI ---
def summarize_deals(results):
    snippets = "\n".join([f"- {r['title']}: {r.get('snippet', '')}" for r in results])
    prompt = f"Summarize these search snippets into top 3 yarn deals with store, price, and short description:\n{snippets}"
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# --- Streamlit UI ---
st.set_page_config(page_title="CraftGrab - Yarn Deals", layout="wide")
st.title("🧶 CraftGrab")
st.subheader("Snag crafty deals. Track your stash. Save smart.")

query = st.text_input("Search for a yarn deal:", "yarn sale site:joann.com")
if st.button("Search Deals"):
    with st.spinner("Searching the internet for yarn deals..."):
        results = search_yarn_deals(query)
    if results:
        st.markdown("### 🧵 Top Deals Summary")
        st.markdown(summarize_deals(results))
        st.markdown("---")
        for result in results:
            st.markdown(f"### [{result['title']}]({result['link']})")
            st.write(result.get("snippet", ""))
            st.write("---")
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
