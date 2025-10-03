import os
import json
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from telegram import Bot
from flask import Flask
from threading import Thread
from prettytable import PrettyTable  # for readable table in logs

# --- Configuration ---
BOT_TOKEN = os.environ['BOT_TOKEN']
GROUP_CHAT_ID = int(os.environ['GROUP_CHAT_ID'])
NOTICE_URL = "https://hub.rgukt.ac.in/hub/notice/index"
STORAGE_FILE = "sent_notices.json"

# Live mode
DEBUG_MODE = False  # False → send messages to Telegram

bot = Bot(token=BOT_TOKEN)

# --- Flask app for Render keep-alive ---
app = Flask(__name__)
@app.route("/")
def home():
    return "Exam Bot is running 🚀"

# --- Load previously sent notices safely ---
seen_notices = set()
try:
    with open(STORAGE_FILE, "r") as f:
        data = f.read().strip()
        if data:
            seen_notices = set(json.loads(data))
except (json.JSONDecodeError, FileNotFoundError, ValueError):
    seen_notices = set()

def save_seen_notices():
    with open(STORAGE_FILE, "w") as f:
        json.dump(list(seen_notices), f, indent=2)

# --- Scraper for current RGUKT notice page ---
def scrape_notices():
    try:
        resp = requests.get(NOTICE_URL)
        resp.raise_for_status()
    except Exception as e:
        print(f"[ERROR] Failed to fetch notices: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    notices_list = []

    card_headers = soup.find_all("div", class_="card-header")
    print(f"[DEBUG] Found {len(card_headers)} card headers")

    for header in card_headers:
        title_tag = header.find("a", class_="card-link")
        if not title_tag:
            continue
        title = title_tag.get_text()
        title_clean = title.strip().replace("\n", " ").replace("\r", " ")

        # Only include exam notices (case-insensitive)
        if "examination" not in title_clean.lower():
            continue

        # Get collapse body
        collapse_div = header.find_next_sibling("div", class_="collapse")
        body_text = ""
        url = NOTICE_URL  # fallback
        if collapse_div:
            body_div = collapse_div.find("div", class_="card-body")
            body_text = body_div.get_text(strip=True) if body_div else ""
            link_tag = body_div.find("a", string="Here") if body_div else None
            if link_tag:
                # Handle relative URLs
                url = urljoin(NOTICE_URL, link_tag.get("href", NOTICE_URL))

        notice_id = title_clean + "|" + url
        notices_list.append((notice_id, title_clean, url))

    print(f"[DEBUG] Scraped {len(notices_list)} notices containing 'Examination'")
    return notices_list[:10]  # latest 10

# --- Broadcast notice ---
def broadcast_notice(title, url, send=not DEBUG_MODE):
    message = f"📢 *Exam Notice:*\n\n{title}\n🔗 {url}"
    if send:
        try:
            bot.send_message(GROUP_CHAT_ID, message, parse_mode="Markdown")
        except Exception as e:
            print(f"[ERROR] Sending message failed: {e}")
    else:
        print("[DEBUG] Message ready to send:")
        print(message)
        print("-" * 50)

# --- Main bot logic ---
def run_bot():
    print("🚀 Bot is starting...")

    # --- Scrape last 10 notices ---
    last_10 = scrape_notices()

    # --- Print readable table of last 10 notices ---
    table = PrettyTable()
    table.field_names = ["Index", "Title", "URL"]
    for idx, (notice_id, title, url) in enumerate(reversed(last_10), 1):  # oldest first
        table.add_row([idx, title, url])
    print("📄 Last 10 scraped examination notices:")
    print(table)

    # --- Process notices normally ---
    for notice_id, title, url in reversed(last_10):
        if notice_id not in seen_notices:
            broadcast_notice(title, url)
            seen_notices.add(notice_id)
            time.sleep(1)
    save_seen_notices()
    print("✅ Initial 10 notices processed.")

    # Continuous monitoring
    while True:
        try:
            current_notices = scrape_notices()
            for notice_id, title, url in current_notices:
                if notice_id not in seen_notices:
                    broadcast_notice(title, url)
                    seen_notices.add(notice_id)
            save_seen_notices()
        except Exception as e:
            print(f"[ERROR] During monitoring: {e}")
        time.sleep(300)  # check every 5 minutes

# --- Run Flask and Bot ---
if __name__ == "__main__":
    bot_thread = Thread(target=run_bot)
    bot_thread.start()

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
