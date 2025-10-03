import requests
from bs4 import BeautifulSoup
import time
from telegram import Bot
import os
import json

BOT_TOKEN = os.environ['BOT_TOKEN']
GROUP_CHAT_ID = int(os.environ['GROUP_CHAT_ID'])
NOTICE_URL = "https://hub.rgukt.ac.in/hub/notice/index"
STORAGE_FILE = "sent_notices.json"

bot = Bot(token=BOT_TOKEN)

# Load previously sent notices
try:
    with open(STORAGE_FILE, "r") as f:
        seen_notices = set(json.load(f))
except FileNotFoundError:
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

    # assume newest first
    return notices_list

def broadcast_notice(title, url):
    message = f"📢 *Exam Notice:*\n\n{title}\n🔗 {url}"
    bot.send_message(GROUP_CHAT_ID, message, parse_mode="Markdown")

if __name__ == "__main__":
    print("🚀 Bot is starting...")

    # --- FIRST RUN: force post last 10 notices ---
    all_notices = scrape_notices()
    last_10 = all_notices[:10]  # newest 10
    for notice_id, title, url in reversed(last_10):  # oldest first
        if notice_id not in seen_notices:
            broadcast_notice(title, url)
            seen_notices.add(notice_id)
            time.sleep(1)
    save_seen_notices()
    print("✅ Initial 10 notices posted.")

    # --- CONTINUOUS MONITORING ---
    while True:
        current_notices = scrape_notices()
        for notice_id, title, url in current_notices:
            if notice_id not in seen_notices:
                broadcast_notice(title, url)
                seen_notices.add(notice_id)
        save_seen_notices()
        time.sleep(300)
