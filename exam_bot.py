from flask import Flask
import threading
import time
import requests
from bs4 import BeautifulSoup
from telegram import Bot
import os

app = Flask(__name__)

# Telegram Bot setup
BOT_TOKEN = os.environ['BOT_TOKEN']
GROUP_CHAT_ID = int(os.environ['GROUP_CHAT_ID'])
NOTICE_URL = "https://hub.rgukt.ac.in/hub/notice/index"
STORAGE_FILE = "sent_notices.json"

bot = Bot(token=BOT_TOKEN)

# Load seen notices
try:
    import json
    with open(STORAGE_FILE, "r") as f:
        seen_notices = set(json.load(f))
except:
    seen_notices = set()

def save_seen_notices():
    with open(STORAGE_FILE, "w") as f:
        json.dump(list(seen_notices), f, indent=2)

def scrape_notices():
    resp = requests.get(NOTICE_URL)
    resp.raise_for_status()
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
    return notices_list

def broadcast_notice(title, url):
    message = f"📢 *Exam Notice:*\n\n{title}\n🔗 {url}"
    bot.send_message(GROUP_CHAT_ID, message, parse_mode="Markdown")

# Bot loop in a thread
def bot_loop():
    # Post last 10 notices on startup
    all_notices = scrape_notices()
    last_10 = all_notices[:10]
    for notice_id, title, url in reversed(last_10):
        if notice_id not in seen_notices:
            seen_notices.add(notice_id)
            broadcast_notice(title, url)
            time.sleep(1)
    save_seen_notices()

    # Continuous monitoring
    while True:
        current_notices = scrape_notices()
        for notice_id, title, url in current_notices:
            if notice_id not in seen_notices:
                seen_notices.add(notice_id)
                broadcast_notice(title, url)
        save_seen_notices()
        time.sleep(300)

# Start bot in a background thread
threading.Thread(target=bot_loop).start()

# Flask route just to bind a port
@app.route("/")
def home():
    return "Bot is running!"

if __name__ == "__main__":
    # Run Flask on port 10000 (Render requires a PORT environment variable)
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
