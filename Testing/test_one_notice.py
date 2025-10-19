import asyncio
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
from telegram.ext import Application
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown

# --- Configuration ---
BOT_TOKEN = "8079829863:AAHEEEocjDQev462BAtflyY782cPLtHNca8"
GROUP_CHAT_ID = -1003133538365  # replace with your group/channel ID
NOTICE_URL = "https://hub.rgukt.ac.in/hub/notice/index"

# --- Functions to scrape notices ---
def extract_notice_links(body_div):
    attachment_url = None
    external_url = None

    if not body_div:
        return attachment_url, external_url

    # 1️⃣ Attachment: first file with .pdf/.doc/.docx
    for a_tag in body_div.find_all("a", href=True):
        href = a_tag["href"]
        if any(href.lower().endswith(ext) for ext in [".pdf", ".doc", ".docx"]):
            attachment_url = urljoin(NOTICE_URL, href)
            break

    # 2️⃣ External URL: "Click Here" or first URL in text
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

def scrape_latest_notice():
    try:
        resp = requests.get(NOTICE_URL)
        resp.raise_for_status()
    except Exception as e:
        print(f"[ERROR] Failed to fetch notices: {e}")
        return None

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
        attachment_url, external_url = extract_notice_links(body_div)

        return title, attachment_url, external_url

# --- Build Telegram message safely ---
def build_message(title, attachment_url, external_url):
    title = escape_markdown(title, version=2)
    attachment_url = escape_markdown(attachment_url, version=2) if attachment_url else None
    external_url = escape_markdown(external_url, version=2) if external_url else None

    if attachment_url and external_url:
        return f"{title}\nURL: {external_url}\nNotice Attachment: {attachment_url}"
    else:
        return f"{title}\nURL: {external_url or attachment_url}"

# --- Async function to send notice ---
async def send_latest_notice(application: Application):
    notice = scrape_latest_notice()
    if notice:
        title, attachment, external = notice
        msg = build_message(title, attachment, external)
        print("Message to send:\n", msg)

        try:
            await application.bot.send_message(
                chat_id=GROUP_CHAT_ID,
                text=msg,
                parse_mode=ParseMode.MARKDOWN_V2
            )
            print("[SUCCESS] Message sent to Telegram!")
        except Exception as e:
            print(f"[ERROR] Failed to send message: {e}")
    else:
        print("No examination notice found.")

# --- Main execution ---
if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    asyncio.run(send_latest_notice(app))
