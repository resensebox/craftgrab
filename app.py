# CraftGrab Streamlit App (Phase 1 MVP with AI-powered deal scanner)

import streamlit as st
import pandas as pd
import requests
import openai
from datetime import datetime

st.set_page_config(page_title="CraftGrab", layout="wide")
st.title("🧶 CraftGrab")
st.subheader("Snag crafty deals. Track your stash. Save smart.")

# --- API Keys from Streamlit Secrets ---
GOOGLE_CSE_API_KEY = st.secrets["GOOGLE_CSE_API_KEY"]
GOOGLE_CSE_ID = st.secrets["GOOGLE_CSE_ID"]
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

openai.api_key = OPENAI_API_KEY

def search_yarn_deals(query="yarn sale"):
    params = {
        "key": GOOGLE_CSE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": query
    }
    url = "https://www.googleapis.com/customsearch/v1"
    res = requests.get(url, params=params)
    st.markdown("#### 🔍 Raw Google API Response")
    st.code(res.text, language="json")
    if res.status_code == 200:
        return res.json().get("items", [])
    else:
        return []

def summarize_deals(results):
    snippets = "\n".join([f"- {r['title']}: {r.get('snippet', '')}" for r in results])
    prompt = f"Summarize these search snippets into top 3 yarn deals with store, price, and short description:\n{snippets}"
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content

# --- AI-Powered Deal Feed ---
st.markdown("### 🔥 AI-Powered Yarn Deals")

if st.button("🔍 Search Latest Deals"):
    with st.spinner("Searching the internet for yarn deals..."):
        search_results = search_yarn_deals()
        if search_results:
            summary = summarize_deals(search_results)
            st.markdown(summary)
        else:
            st.error("No results found or API error.")

# --- Yarn Stash Tracker ---
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

# --- Wishlist System ---
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

# --- Coming Soon Sections ---
st.markdown("### 🧶 Coming Soon")
st.markdown("- Project Organizer (link stash to patterns)")
st.markdown("- Local store deals map")

st.caption("CraftGrab MVP v0.3")
