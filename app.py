import streamlit as st
import requests

# --- Google Custom Search Configuration ---
API_KEY = "AIzaSyBct8VijIiwffgvu8Z2qjVB8Dt4cFQN3wY" # Replace with your real API key
CSE_ID = "34a2fb94f239b48ce"  # Replace with your custom search engine ID

# --- Yarn Deal Search Function ---
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
        data = response.json()
        return data.get("items", [])
    else:
        st.error(f"Search failed: {response.status_code} - {response.text}")
        return []

# --- Streamlit UI ---
st.set_page_config(page_title="CraftGrab - Yarn Deals")
st.title("CraftGrab")
st.subheader("Find the best yarn and crafting deals online!")

query = st.text_input("Search for a yarn deal:", "yarn sale site:etsy.com")

if st.button("Search Deals"):
    results = search_yarn_deals(query)
    if results:
        for result in results:
            st.write(f"### [{result['title']}]({result['link']})")
            st.write(result.get("snippet", ""))
    else:
        st.info("No results found.")

