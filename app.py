import streamlit as st
import pandas as pd
import requests
import json # Import json for json.dumps
from bs4 import BeautifulSoup

# Set Streamlit page config FIRST
st.set_page_config(page_title="CraftGrab Yarn Deals", layout="wide", initial_sidebar_state="expanded")

# Navigation
st.sidebar.title("CraftGrab Navigation")
page = st.sidebar.radio("Go to", ["Home", "Browse All Yarn Deals"])

# Define scraper functions
def scrape_yarn_com(search_term=None):
    """
    Scrapes yarn deals from yarn.com for Sirdar yarn category.
    Filters results by search_term if provided.
    """
    url = "https://www.yarn.com/categories/sirdar-yarn"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10) # Added timeout for robustness
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
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
                products.append({"Product Name": name, "Original Price": original_price, "Sale Price": sale_price, "Product URL": product_url})
        return products
    except requests.exceptions.RequestException as e:
        st.error(f"Error scraping Yarn.com: {e}")
        return []

def scrape_joann(search_term=None):
    """
    Scrapes yarn deals from joann.com's yarn sale section.
    Filters results by search_term if provided.
    """
    url = "https://www.joann.com/yarn/sale/"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
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
                products.append({"Product Name": name, "Original Price": original_price, "Sale Price": sale_price, "Product URL": product_url})
        return products
    except requests.exceptions.RequestException as e:
        st.error(f"Error scraping Joann: {e}")
        return []

# Removed scrape_michaels function due to persistent 404 errors and difficulty in finding a consistent sale/clearance page for automated scraping.
# def scrape_michaels(search_term=None):
#     """
#     Scrapes yarn deals from michaels.com's yarn clearance section.
#     Filters results by search_term if provided.
#     """
#     url = "https://www.michaels.com/yarn-clearance" # This URL consistently returns 404
#     headers = {"User-Agent": "Mozilla/5.0"}
    
#     try:
#         response = requests.get(url, headers=headers, timeout=10)
#         response.raise_for_status()
#         soup = BeautifulSoup(response.text, 'html.parser')

#         products = []
#         for item in soup.select(".product"):
#             name_tag = item.select_one(".product-name")
#             price_tag = item.select_one(".regular-price")
#             sale_tag = item.select_one(".sale-price")
#             link_tag = item.find("a", href=True)

#             if name_tag and sale_tag and price_tag:
#                 name = name_tag.text.strip()
#                 if search_term and search_term.lower() not in name.lower():
#                     continue
#                 original_price = price_tag.text.strip()
#                 sale_price = sale_tag.text.strip()
#                 product_url = "https://www.michaels.com" + link_tag['href'] if link_tag else "N/A"
#                 products.append({"Product Name": name, "Original Price": original_price, "Sale Price": sale_price, "Product URL": product_url})
#         return products
#     except requests.exceptions.RequestException as e:
#         st.error(f"Error scraping Michaels: {e}")
#         return []

def scrape_knitpicks(search_term=None):
    """
    Scrapes yarn deals from knitpicks.com's yarn sale section.
    Filters results by search_term if provided.
    """
    # Updated URL to a more reliable clearance page
    url = "https://www.knitpicks.com/clearance/clearance-yarn/c/301002"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
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
                products.append({"Product Name": name, "Original Price": original_price, "Sale Price": sale_price, "Product URL": product_url})
        return products
    except requests.exceptions.RequestException as e:
        st.error(f"Error scraping KnitPicks: {e}")
        return []

def scrape_wecrochet(search_term=None):
    """
    Scrapes yarn deals from wecrochet.com's yarn sale section.
    Filters results by search_term if provided.
    """
    # Updated URL to a more reliable sale page on crochet.com (associated with WeCrochet)
    url = "https://www.crochet.com/sale/yarn/c/50110701"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
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
                product_url = "https://www.wecrochet.com" + link_tag['href'] if link_tag else "N/A" # Still use wecrochet.com as base for URL
                products.append({"Product Name": name, "Original Price": original_price, "Sale Price": sale_price, "Product URL": product_url})
        return products
    except requests.exceptions.RequestException as e:
        st.error(f"Error scraping WeCrochet: {e}")
        return []

@st.cache_data(ttl=3600) # Cache data for 1 hour to prevent excessive scraping
def scrape_all_us_stores(search_term=None):
    """
    Aggregates yarn deal results from all supported U.S. retailers.
    """
    all_results = []
    # Using a list of functions and iterating to make it more scalable and readable
    # Michaels scraper removed due to persistent 404/difficulty in finding a reliable sale page.
    scrapers = [scrape_yarn_com, scrape_joann, scrape_knitpicks, scrape_wecrochet]
    
    for scraper_func in scrapers:
        all_results.extend(scraper_func(search_term))
    return all_results

# Define the LLM API call function for Python environment
def generate_ai_summary(product_data):
    """
    Generates an AI-powered summary for a given product using the Gemini API.
    This function simulates the API call from a Python backend.
    """
    product_name = product_data.get("Product Name", "N/A")
    original_price = product_data.get("Original Price", "N/A")
    sale_price = product_data.get("Sale Price", "N/A")
    product_url = product_data.get("Product URL", "N/A")
    website = product_data.get("Website", "Unknown")

    prompt = f"""
    Generate a brief, engaging product description (around 2-3 sentences) for a yarn deal.
    Highlight the sale aspect and potential uses.
    Product Details:
    - Name: {product_name}
    - Original Price: {original_price}
    - Sale Price: {sale_price}
    - Website: {website}
    - URL: {product_url}
    """

    # Mimicking the structure for a Python requests call to a Gemini API endpoint
    # In a real deployed scenario, `__gemini_api_key__` would be provided by the environment
    # For local testing, you might need to replace `""` with your actual API key
    # or handle it via environment variables.
    apiKey = "" 
    apiUrl = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

    headers = {
        'Content-Type': 'application/json'
    }
    # Payload structured as per Gemini API requirements
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    try:
        # Append API key to URL if available
        if apiKey:
            request_url = f"{apiUrl}?key={apiKey}"
        else: # For environments where API key is automatically handled, e.g., Canvas runtime
            request_url = apiUrl # The Canvas runtime will inject the key

        response = requests.post(request_url, headers=headers, data=json.dumps(payload), timeout=20)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        result = response.json()
        
        if result.get("candidates") and len(result["candidates"]) > 0 and \
           result["candidates"][0].get("content") and result["candidates"][0]["content"].get("parts") and \
           len(result["candidates"][0]["content"]["parts"]) > 0:
            return result["candidates"][0]["content"]["parts"][0]["text"]
        else:
            return "AI summary not available."
    except requests.exceptions.RequestException as e:
        st.error(f"Error generating AI summary: {e}. Please check your network or API key configuration.")
        return "AI summary generation failed."
    except json.JSONDecodeError:
        st.error("Error decoding AI response from LLM.")
        return "AI summary generation failed."

def display_product_with_ai(product_data):
    """
    Displays a single product's details along with its AI-generated summary.
    """
    st.markdown(f"**Product Name:** {product_data.get('Product Name', 'N/A')}")
    st.markdown(f"**Website:** {product_data.get('Website', 'Unknown')}")
    st.markdown(f"**Original Price:** {product_data.get('Original Price', 'N/A')}")
    st.markdown(f"**Sale Price:** {product_data.get('Sale Price', 'N/A')}")
    st.markdown(f"**Product URL:** [Link]({product_data.get('Product URL', '#')})")

    # Add a loading spinner specifically for AI summary generation
    with st.spinner("Generating AI summary..."):
        ai_summary = generate_ai_summary(product_data)
    st.write(ai_summary)
    st.markdown("---") # Separator for products


# Pages
if page == "Home":
    st.title("Welcome to CraftGrab!")
    st.write("Search for yarn sales across major U.S. retailers.")

    search_term_input = st.text_input("Search for a specific yarn or brand (optional):", "")
    
    if st.button("Search"):
        with st.spinner("Searching for deals... This might take a moment."):
            results = scrape_all_us_stores(search_term_input if search_term_input else None)
        
        if results:
            df = pd.DataFrame(results)
            df["Website"] = df["Product URL"].apply(lambda url: next((site for site in ["Yarn.com", "Joann", "KnitPicks", "WeCrochet"] if site.lower() in url.lower() or (site.lower() == "wecrochet" and "crochet.com" in url.lower())), "Unknown"))
            
            st.subheader("Found Deals with AI Summaries:")
            if len(df) > 10: # Warn if too many AI calls might be made
                st.warning(f"Found {len(df)} deals. Generating AI summaries for all might take some time.")
            
            # Display products with AI summaries
            for index, row in df.iterrows():
                display_product_with_ai(row.to_dict())
        else:
            st.write("No matching deals found. Try a different search term or browse all deals.")

elif page == "Browse All Yarn Deals":
    st.title("🧵 All Yarn Deals by Website")
    
    with st.spinner("Loading all yarn deals... This might take a moment, especially for many results."):
        results = scrape_all_us_stores()
    
    if results:
        df = pd.DataFrame(results)
        df["Website"] = df["Product URL"].apply(lambda url: next((site for site in ["Yarn.com", "Joann", "KnitPicks", "WeCrochet"] if site.lower() in url.lower() or (site.lower() == "wecrochet" and "crochet.com" in url.lower())), "Unknown"))
        
        ordered_sites = ["Yarn.com", "Joann", "KnitPicks", "WeCrochet"]
        
        st.subheader("All Deals with AI Summaries:")
        if len(df) > 20: # Warn if too many AI calls might be made for browse all
            st.warning(f"Found {len(df)} deals across all sites. Generating AI summaries for all might take significant time.")

        for site in ordered_sites:
            site_df = df[df["Website"] == site]
            if not site_df.empty:
                st.subheader(f"{site} - {len(site_df)} Products")
                for index, row in site_df.iterrows():
                    display_product_with_ai(row.to_dict())
            else:
                st.info(f"No deals found for {site}.") # Inform user if a site has no deals
    else:
        st.write("No deals found. Please check your internet connection or try again later.")
