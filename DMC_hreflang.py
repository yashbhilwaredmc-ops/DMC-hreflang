import streamlit as st
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import pandas as pd
import time
from fake_useragent import UserAgent
import pycountry

# ---- Helper Functions ----
def fetch_http(url):
    try:
        ua = UserAgent()
        user_agent = ua.chrome
        headers = {"User-Agent": user_agent}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return {
            "status": response.status_code,
            "html": response.text,
            "user_agent": user_agent
        }
    except Exception as e:
        return {"status": "Failed", "html": "", "user_agent": "N/A", "error": str(e)}

def validate_hreflang(hreflang):
    if hreflang == 'x-default':
        return True
    parts = hreflang.split('-')
    if len(parts) > 2:
        return False        
    try:
        if parts[0]:
            pycountry.languages.get(alpha_2=parts[0])
        if len(parts) > 1 and parts[1]:
            pycountry.countries.get(alpha_2=parts[1].upper())
        return True
    except:
        return False

def check_indexable(soup):
    robots = soup.find('meta', attrs={'name': 'robots'})
    return not (robots and 'noindex' in robots.get('content', '').lower())

# ---- Streamlit UI ----
st.title("🌍 Advanced Hreflang Analyzer (Web Version)")

url_input = st.text_area("Enter URLs (one per line):")
run_button = st.button("Analyze URLs")

if run_button:
    urls = [u.strip() for u in url_input.split("\n") if u.strip()]
    results = []
    progress_bar = st.progress(0)

    for i, url in enumerate(urls, start=1):
        response = fetch_http(url)
        if response["status"] == "Failed":
            results.append({"URL": url, "Status": "Failed", "Issues": response.get("error", "Error")})
            continue
        
        soup = BeautifulSoup(response["html"], 'lxml')
        hreflang_tags = [(link.get('hreflang', ''), urljoin(url, link.get('href', ''))) 
                         for link in soup.find_all('link', rel='alternate')]
        
        issues = []
        for hreflang, href in hreflang_tags:
            if hreflang and not validate_hreflang(hreflang):
                issues.append(f"Invalid hreflang: {hreflang}")

        results.append({
            "URL": url,
            "Status": f"{response['status']} OK",
            "Title": soup.title.string if soup.title else "No Title",
            "Language": soup.html.get('lang', '-') if soup.html else '-',
            "Indexable": "✔️" if check_indexable(soup) else "❌",
            "User-Agent": response["user_agent"],
            "hreflangs": ", ".join([h for h, _ in hreflang_tags]),
            "Issues": ", ".join(issues) if issues else "Valid"
        })

        progress_bar.progress(i / len(urls))

    df = pd.DataFrame(results)
    st.subheader("Results")
    st.dataframe(df)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download CSV", csv, "hreflang_results.csv", "text/csv")
