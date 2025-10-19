import asyncio
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import os
import json
from telegram.ext import Application
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown

# --- Configuration ---
BOT_TOKEN = "8079829863:AAHEEEocjDQev462BAtflyY782cPLtHNca8"
GROUP_CHAT_ID = -1003133538365  # replace with your Telegram group/channel ID
NOTICE_URL = "https://hub.rgukt.ac.in/hub/notice/index"
STORAGE_FILE = "sent_notices.json"  # persist sent notices

# --- Functions to scrape notices ---
def extract_notice_links(body_div):
    attachment_url = None
    external_url = None

    if not body_div:
        return attachment_url, external_url

    # Attachment: first file with .pdf/.doc/.docx
    for a_tag in body_div.find_all("a", href=True):
        href = a_tag["href"]
        if any(href.lower().endswith(ext) for ext in [".pdf", ".doc", ".docx"]):
            attachment_url = urljoin(NOTICE_URL, href)
            break

    # External URL: "Click Here" or first URL in text
    click_tag = body_div.find("a", string=lambda x: x and "here" in x.lower())
    if click_tag and click_tag.get("href"):
        external_url = urljoin(NOTICE_URL, click_tag.get("href"))
    else:
        text_urls = re.findall(r'https?://\S+', body_div.get_text())
        for u in text_urls:
            if u != attachment_url:
                external_url = u
                break

    return attachment_url, external_url

def scrape_last_10_notices():
    try:
        resp = requests.get(NOTICE_URL)
        resp.raise_for_status()
    except Exception as e:
        print(f"[ERROR] Failed to fetch notices: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    notices = []

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
        notice_id = f"{title}|{external_url}|{attachment_url}"

        notices.append((notice_id, title, external_url, attachment_url))

    return notices[:10]  # latest 10

# --- Build Telegram message safely ---
def build_message(title, external_url, attachment_url):
    title = escape_markdown(title, version=2)
    attachment_url = escape_markdown(attachment_url, version=2) if attachment_url else None
    external_url = escape_markdown(external_url, version=2) if external_url else None

    if attachment_url and external_url:
        return f"{title}\nURL: {external_url}\nNotice Attachment: {attachment_url}"
    else:
        return f"{title}\nURL: {external_url or attachment_url}"

# --- Load previously sent notices ---
def load_seen_notices():
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r") as f:
                data = f.read().strip()
                if data:
                    return set(json.loads(data))
        except (json.JSONDecodeError, FileNotFoundError, ValueError):
            return set()
    return set()

def save_seen_notices(seen_notices):
    with open(STORAGE_FILE, "w") as f:
        json.dump(list(seen_notices), f, indent=2)

# --- Async function to send last 10 notices ---
async def send_last_10_notices(application: Application):
    seen_notices = load_seen_notices()
    notices = scrape_last_10_notices()
    if not notices:
        print("No examination notices found.")
        return

    for notice_id, title, external, attachment in reversed(notices):  # oldest first
        if notice_id not in seen_notices:
            msg = build_message(title, external, attachment)
            print("[DEBUG] Message ready to send:\n", msg)
            try:
                await application.bot.send_message(
                    chat_id=GROUP_CHAT_ID,
                    text=msg,
                    parse_mode=ParseMode.MARKDOWN_V2
                )
                print(f"[SUCCESS] Sent: {title}")
            except Exception as e:
                print(f"[ERROR] Failed to send message: {e}")
            seen_notices.add(notice_id)

    save_seen_notices(seen_notices)

# --- Main execution ---
if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    asyncio.run(send_last_10_notices(app))
