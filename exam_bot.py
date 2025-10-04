import asyncio
import os
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
from threading import Thread
from telegram.ext import Application
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown
from flask import Flask
from prettytable import PrettyTable

# --- Configuration ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # set in Render secrets
GROUP_CHAT_ID = int(os.environ.get("GROUP_CHAT_ID"))  # your Telegram group/channel
NOTICE_URL = "https://hub.rgukt.ac.in/hub/notice/index"
STORAGE_FILE = "sent_notices.json"

# --- Flask app for Render keep-alive ---
app = Flask(__name__)
@app.route("/")
def home():
    return "RGUKT Exam Bot is running 🚀"

# --- Load/Save sent notices ---
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

# --- Scraping functions ---
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

# --- Build Telegram message ---
def build_message(title, external_url, attachment_url):
    title = escape_markdown(title, version=2)
    attachment_url = escape_markdown(attachment_url, version=2) if attachment_url else None
    external_url = escape_markdown(external_url, version=2) if external_url else None

    if attachment_url and external_url:
        return f"{title}\nURL: {external_url}\nNotice Attachment: {attachment_url}"
    else:
        return f"{title}\nURL: {external_url or attachment_url}"

# --- Async bot runner ---
async def run_bot():
    print("🚀 Exam Bot starting...")
    app_instance = Application.builder().token(BOT_TOKEN).build()
    seen_notices = load_seen_notices()

    # --- First run: scrape last 10 notices ---
    last_10 = scrape_last_10_notices()

    # --- PrettyTable for logs ---
    table = PrettyTable()
    table.field_names = ["Index", "Title", "URL", "Attachment"]
    for idx, (notice_id, title, external, attachment) in enumerate(reversed(last_10), 1):
        table.add_row([idx, title, external or "-", attachment or "-"])
    print("📄 Last 10 scraped examination notices:")
    print(table)

    # --- Send last 10 notices ---
    for notice_id, title, external, attachment in reversed(last_10):
        if notice_id not in seen_notices:
            msg = build_message(title, external, attachment)
            print("[DEBUG] Message ready to send:\n", msg)
            try:
                await app_instance.bot.send_message(
                    chat_id=GROUP_CHAT_ID,
                    text=msg,
                    parse_mode=ParseMode.MARKDOWN_V2
                )
                print(f"[SUCCESS] Sent: {title}")
            except Exception as e:
                print(f"[ERROR] Failed to send message: {e}")
            seen_notices.add(notice_id)
    save_seen_notices(seen_notices)
    print("✅ Initial 10 notices processed.")

    # --- Continuous monitoring ---
    while True:
        try:
            current_notices = scrape_last_10_notices()
            for notice_id, title, external, attachment in current_notices:
                if notice_id not in seen_notices:
                    msg = build_message(title, external, attachment)
                    print("[DEBUG] New notice ready:\n", msg)
                    try:
                        await app_instance.bot.send_message(
                            chat_id=GROUP_CHAT_ID,
                            text=msg,
                            parse_mode=ParseMode.MARKDOWN_V2
                        )
                        print(f"[SUCCESS] Sent: {title}")
                    except Exception as e:
                        print(f"[ERROR] Failed to send message: {e}")
                    seen_notices.add(notice_id)
            save_seen_notices(seen_notices)
        except Exception as e:
            print(f"[ERROR] During monitoring: {e}")
        await asyncio.sleep(300)  # check every 5 minutes

# --- Run Flask + Bot concurrently ---
if __name__ == "__main__":
    bot_thread = Thread(target=lambda: asyncio.run(run_bot()), daemon=True)
    bot_thread.start()

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
