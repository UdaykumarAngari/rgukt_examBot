import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

NOTICE_URL = "https://hub.rgukt.ac.in/hub/notice/index"

def extract_notice_url(body_div):
    default_url = NOTICE_URL

    if not body_div:
        return default_url

    # 1️⃣ Download link
    download_tag = body_div.find("a", string=lambda x: x and "download" in x.lower())
    if download_tag and download_tag.get("href"):
        return urljoin(NOTICE_URL, download_tag.get("href"))

    # 2️⃣ Click Here link
    click_tag = body_div.find("a", string=lambda x: x and "here" in x.lower())
    if click_tag and click_tag.get("href"):
        return urljoin(NOTICE_URL, click_tag.get("href"))

    # 3️⃣ Extract URL from body text
    text = body_div.get_text()
    urls = re.findall(r'https?://\S+', text)
    if urls:
        return urls[0]  # first URL found

    # fallback
    return default_url

def scrape_latest_exam_notice():
    try:
        resp = requests.get(NOTICE_URL)
        resp.raise_for_status()
    except Exception as e:
        print(f"[ERROR] Failed to fetch notices: {e}")
        return

    soup = BeautifulSoup(resp.text, "html.parser")

    for header in soup.find_all("div", class_="card-header"):
        title_tag = header.find("a", class_="card-link")
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        if "examination" not in title.lower():
            continue

        collapse_div = header.find_next_sibling("div", class_="collapse")
        body_div = collapse_div.find("div", class_="card-body") if collapse_div else None
        url = extract_notice_url(body_div)

        print("Title       :", title)
        print("Resolved URL:", url)
        print("-" * 50)
        break  # only latest notice

if __name__ == "__main__":
    scrape_latest_exam_notice()
