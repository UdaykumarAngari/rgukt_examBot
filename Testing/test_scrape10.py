import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
from prettytable import PrettyTable

NOTICE_URL = "https://hub.rgukt.ac.in/hub/notice/index"

def extract_notice_links(body_div):
    """
    Returns a tuple: (attachment_url, external_url)
    attachment_url → first file link (pdf/doc/docx)
    external_url → Click Here link or URL in text
    """
    attachment_url = None
    external_url = None

    if not body_div:
        return attachment_url, external_url

    # 1️⃣ Find first file link (pdf/doc/docx)
    for a_tag in body_div.find_all("a", href=True):
        href = a_tag["href"]
        if any(href.lower().endswith(ext) for ext in [".pdf", ".doc", ".docx"]):
            attachment_url = urljoin(NOTICE_URL, href)
            break

    # 2️⃣ External link: "Click Here" or first URL in body text
    click_tag = body_div.find("a", string=lambda x: x and "here" in x.lower())
    if click_tag and click_tag.get("href"):
        external_url = urljoin(NOTICE_URL, click_tag.get("href"))
    else:
        # fallback: first URL in text that is not the attachment
        text_urls = re.findall(r'https?://\S+', body_div.get_text())
        for u in text_urls:
            if u != attachment_url:
                external_url = u
                break

    return attachment_url, external_url

def scrape_last_10_exam_notices():
    try:
        resp = requests.get(NOTICE_URL)
        resp.raise_for_status()
    except Exception as e:
        print(f"[ERROR] Failed to fetch notices: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    notices_list = []

    for header in soup.find_all("div", class_="card-header"):
        title_tag = header.find("a", class_="card-link")
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        if "examination" not in title.lower():
            continue

        collapse_div = header.find_next_sibling("div", class_="collapse")
        body_div = collapse_div.find("div", class_="card-body") if collapse_div else None
        attachment_url, external_url = extract_notice_links(body_div)

        notices_list.append((title, attachment_url, external_url))
        if len(notices_list) >= 10:
            break  # only last 10

    return notices_list

if __name__ == "__main__":
    last_10 = scrape_last_10_exam_notices()

    # Pretty print
    table = PrettyTable()
    table.field_names = ["Index", "Title", "Attachment URL", "External URL"]

    for idx, (title, attachment, external) in enumerate(last_10, 1):
        table.add_row([idx, title, attachment or "-", external or "-"])

    print("📄 Last 10 Examination Notices with both links:")
    print(table)
