
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
            products.append({"Product Name": name, "Original Price": original_price, "Sale Price": sale_price, "Product URL": product_url})
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
            products.append({"Product Name": name, "Original Price": original_price, "Sale Price": sale_price, "Product URL": product_url})
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
            products.append({"Product Name": name, "Original Price": original_price, "Sale Price": sale_price, "Product URL": product_url})
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
            products.append({"Product Name": name, "Original Price": original_price, "Sale Price": sale_price, "Product URL": product_url})
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
            products.append({"Product Name": name, "Original Price": original_price, "Sale Price": sale_price, "Product URL": product_url})
    return products

def scrape_all_us_stores(search_term=None):
    all_results = []
    all_results.extend(scrape_yarn_com(search_term))
    all_results.extend(scrape_joann(search_term))
    all_results.extend(scrape_michaels(search_term))
    all_results.extend(scrape_knitpicks(search_term))
    all_results.extend(scrape_wecrochet(search_term))
    return all_results

# Pages
if page == "Home":
    st.title("Welcome to CraftGrab!")
    st.write("Search for yarn sales across major U.S. retailers.")

    search_term_input = st.text_input("Search for a specific yarn or brand (optional):", "")
    if st.button("Search"):
        results = scrape_all_us_stores(search_term_input if search_term_input else None)
        if results:
            df = pd.DataFrame(results)
            df["Website"] = df["Product URL"].apply(lambda url: next((site for site in ["Yarn.com", "Joann", "Michaels", "KnitPicks", "WeCrochet"] if site.lower() in url.lower()), "Unknown"))
            st.dataframe(df)
        else:
            st.write("No matching deals found.")

elif page == "Browse All Yarn Deals":
    st.title("🧵 All Yarn Deals by Website")
    results = scrape_all_us_stores()
    if results:
        df = pd.DataFrame(results)
        df["Website"] = df["Product URL"].apply(lambda url: next((site for site in ["Yarn.com", "Joann", "Michaels", "KnitPicks", "WeCrochet"] if site.lower() in url.lower()), "Unknown"))
        for site in ["Yarn.com", "Joann", "Michaels", "KnitPicks", "WeCrochet"]:
            site_df = df[df["Website"] == site]
            if not site_df.empty:
                st.subheader(f"{site} - {len(site_df)} Products")
                st.dataframe(site_df)
    else:
        st.write("No deals found.")
