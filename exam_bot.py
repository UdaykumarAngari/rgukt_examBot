import requests
from bs4 import BeautifulSoup
import time
from telegram import Bot

# 🔑 Your bot details
BOT_TOKEN = "1079829863:AAHEEEocjDQev462BAtflyY782cPLtHNca8"
GROUP_CHAT_ID = -1003133538365  # 👉 replace with your real chat_id
NOTICE_URL = "https://hub.rgukt.ac.in/hub/notice/index"

bot = Bot(token=BOT_TOKEN)
seen_notices = set()

def scrape_notices():
    resp = requests.get(NOTICE_URL)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    new_notices = []
    for div in soup.find_all("div", class_="panel panel-default"):
        title_tag = div.find("h4")
        if not title_tag:
            continue
        title = title_tag.text.strip()

        # filter only Examination notices
        if "Examination" not in title:
            continue

        link_tag = div.find("a", string="Download: Notice Attachment")
        if not link_tag:
            link_tag = div.find("a", string="Click Here")
        url = link_tag["href"] if link_tag else NOTICE_URL

        notice_id = title + "|" + url
        if notice_id not in seen_notices:
            seen_notices.add(notice_id)
            new_notices.append((title, url))
    return new_notices

def broadcast_notices():
    notices = scrape_notices()
    for title, url in notices:
        message = f"📢 *New Exam Notice:*\n\n{title}\n🔗 {url}"
        bot.send_message(GROUP_CHAT_ID, message, parse_mode="Markdown")

if __name__ == "__main__":
    print("🚀 Bot is running... (Press Ctrl+C to stop)")
    while True:
        broadcast_notices()
        time.sleep(300)  # check every 5 min
