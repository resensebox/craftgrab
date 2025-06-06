import streamlit as st
import pandas as pd
import requests
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

# Pages
if page == "Home":
    st.title("Welcome to CraftGrab!")
    st.write("Search for yarn sales across major U.S. retailers.")

    search_term_input = st.text_input("Search for a specific yarn or brand (optional):", "")
    
    # Add a loading spinner while scraping
    if st.button("Search"):
        with st.spinner("Searching for deals... This might take a moment."):
            results = scrape_all_us_stores(search_term_input if search_term_input else None)
        
        if results:
            df = pd.DataFrame(results)
            # Assign 'Website' based on URL, ensuring consistency and handling unknown cases
            # Michaels removed from this list
            df["Website"] = df["Product URL"].apply(lambda url: next((site for site in ["Yarn.com", "Joann", "KnitPicks", "WeCrochet"] if site.lower() in url.lower() or (site.lower() == "wecrochet" and "crochet.com" in url.lower())), "Unknown"))
            st.dataframe(df, use_container_width=True) # Use full container width for better display
        else:
            st.write("No matching deals found. Try a different search term or browse all deals.")

elif page == "Browse All Yarn Deals":
    st.title("🧵 All Yarn Deals by Website")
    
    # Add a loading spinner while scraping
    with st.spinner("Loading all yarn deals... This might take a moment."):
        results = scrape_all_us_stores()
    
    if results:
        df = pd.DataFrame(results)
        # Assign 'Website' based on URL, ensuring consistency and handling unknown cases
        # Michaels removed from this list
        df["Website"] = df["Product URL"].apply(lambda url: next((site for site in ["Yarn.com", "Joann", "KnitPicks", "WeCrochet"] if site.lower() in url.lower() or (site.lower() == "wecrochet" and "crochet.com" in url.lower())), "Unknown"))
        
        # Define a consistent order for displaying websites
        # Michaels removed from this list
        ordered_sites = ["Yarn.com", "Joann", "KnitPicks", "WeCrochet"]
        
        for site in ordered_sites:
            site_df = df[df["Website"] == site]
            if not site_df.empty:
                st.subheader(f"{site} - {len(site_df)} Products")
                st.dataframe(site_df, use_container_width=True) # Use full container width
    else:
        st.write("No deals found. Please check your internet connection or try again later.")
