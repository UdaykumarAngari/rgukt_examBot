import os
import json
import time
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from flask import Flask
from threading import Thread

# --- Configuration ---
BOT_TOKEN = os.environ['BOT_TOKEN']
GROUP_CHAT_ID = int(os.environ['GROUP_CHAT_ID'])
NOTICE_URL = "https://hub.rgukt.ac.in/hub/notice/index"
STORAGE_FILE = "sent_notices.json"

# --- Set DEBUG_MODE to True for safe testing (prints messages instead of sending) ---
DEBUG_MODE = True

bot = Bot(token=BOT_TOKEN)

# --- Flask app to keep Render service alive ---
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

# --- Scrape notices ---
def scrape_notices():
    try:
        resp = requests.get(NOTICE_URL)
        resp.raise_for_status()
    except Exception as e:
        print(f"[ERROR] Failed to fetch notices: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    notices_list = []

    for div in soup.find_all("div", class_="panel panel-default"):
        title_tag = div.find("h4")
        if not title_tag:
            continue
        title = title_tag.text.strip()
        if "Examination" not in title:
            continue
        link_tag = div.find("a", string="Download: Notice Attachment")
        if not link_tag:
            link_tag = div.find("a", string="Click Here")
        url = link_tag["href"] if link_tag else NOTICE_URL
        notice_id = title + "|" + url
        notices_list.append((notice_id, title, url))

    return notices_list[:10]  # newest 10 for first run

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

    # Post last 10 notices on first run
    last_10 = scrape_notices()
    for notice_id, title, url in reversed(last_10):  # oldest first
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
    # Run bot in background thread
    bot_thread = Thread(target=run_bot)
    bot_thread.start()

    # Run Flask app for Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
