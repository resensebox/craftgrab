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
# These are placeholders and would typically be loaded from Streamlit secrets in a deployed app
GOOGLE_CSE_API_KEY = "YOUR_GOOGLE_CSE_API_KEY" # Placeholder
GOOGLE_CSE_ID = "YOUR_GOOGLE_CSE_ID"         # Placeholder
OPENAI_API_KEY = "YOUR_OPENAI_API_KEY"       # Placeholder

# Set OpenAI API key (ensure it's securely managed in a real deployment)
openai.api_key = OPENAI_API_KEY

def search_yarn_deals(query="yarn sale"):
    """
    Searches Google Custom Search for yarn deals.
    Note: Requires GOOGLE_CSE_API_KEY and GOOGLE_CSE_ID to be valid.
    """
    params = {
        "key": GOOGLE_CSE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": query
    }
    url = "https://www.googleapis.com/customsearch/v1"
    try:
        res = requests.get(url, params=params)
        res.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        return res.json().get("items", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Error searching for deals: {e}")
        return []

def summarize_deals(results):
    """
    Summarizes search results into key yarn deals using OpenAI GPT-4.
    """
    if not results:
        return "No deals found to summarize."

    snippets = "\n".join([f"- {r.get('title', 'N/A')}: {r.get('snippet', '')}" for r in results if r.get('snippet')])
    if not snippets.strip():
        return "No relevant snippets to summarize."

    prompt = f"""Summarize these search snippets into top 3 yarn deals with store, price, and short description.
    Focus on clear, concise deal information. If no specific price is mentioned, state 'Price varies' or similar.
    If less than 3 distinct deals are present, list all found deals.

    Search Snippets:
    {snippets}

    Formatted Summary:
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-4", # Or "gpt-3.5-turbo" for faster/cheaper responses
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes craft deals."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except openai.APIError as e:
        st.error(f"OpenAI API error: {e}")
        return "Could not summarize deals due to an API error."
    except Exception as e:
        st.error(f"An unexpected error occurred during summarization: {e}")
        return "Could not summarize deals."

# --- AI-Powered Yarn Deals Section ---
st.markdown("### 🔥 AI-Powered Yarn Deals")
deal_query = st.text_input("Enter a specific craft item to search for deals (e.g., 'wool roving sale', 'embroidery floss clearance')", "yarn sale")
if st.button("🔍 Search Latest Deals"):
    with st.spinner("Searching for deals..."):
        search_results = search_yarn_deals(deal_query)
        if search_results:
            st.markdown("#### Top Deals Summary:")
            summary = summarize_deals(search_results)
            st.markdown(summary)
            st.markdown("---")
            st.markdown("#### Raw Search Results (for debugging/more detail):")
            for i, result in enumerate(search_results[:5]): # Show top 5 raw results
                st.markdown(f"**{i+1}. {result.get('title', 'No Title')}**")
                st.markdown(f"*{result.get('link', 'No Link')}*")
                st.markdown(f"{result.get('snippet', 'No Snippet')}")
                st.markdown("---")
        else:
            st.info("No deals found for your query. Try a different search term or check API keys.")


# --- Stash Tracker System ---
st.markdown("### 🧺 Your Yarn Stash")
if "stash" not in st.session_state:
    st.session_state.stash = []

with st.form("stash_form"):
    yarn_name = st.text_input("Yarn Name", key="yarn_name_input")
    quantity = st.number_input("Skeins", min_value=0, value=1, key="skeins_input")
    fiber_type = st.text_input("Fiber Type (e.g., 'Merino Wool', 'Cotton Blend')", key="fiber_type_input")
    weight_type = st.selectbox("Yarn Weight", ["Lace", "Fingering", "Sport", "DK", "Worsted", "Aran", "Bulky", "Super Bulky", "Other"], key="weight_type_select")
    yardage = st.text_input("Total Yardage (per skein or total)", key="yardage_input")
    add_to_stash = st.form_submit_button("Add to Stash")

    if add_to_stash and yarn_name:
        st.session_state.stash.append({
            "Name": yarn_name,
            "Skeins": quantity,
            "Fiber": fiber_type,
            "Weight": weight_type,
            "Yardage": yardage
        })
        st.success(f"Added {yarn_name} to your stash!") # User feedback

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
        st.success(f"Added {wish_name} to your wishlist!") # User feedback

if st.session_state.wishlist:
    st.dataframe(pd.DataFrame(st.session_state.wishlist))
else:
    st.info("No items in wishlist yet.")

# --- Coming Soon Section ---
st.markdown("### 🧶 Coming Soon")
st.markdown("- Project Organizer (link stash to patterns)")
st.markdown("- Local store deals map")

st.markdown("---")
st.markdown("CraftGrab MVP v0.3")
