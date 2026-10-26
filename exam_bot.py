import os
import asyncio
import requests
import gspread
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from telegram.ext import Application
import json
from google.oauth2.service_account import Credentials

from flask import Flask
from threading import Thread
import time

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID"))

SPREADSHEET_ID =  os.getenv("SPREADSHEET_ID")

NOTICE_URL = os.getenv("HUB_NOTICE_URL", "https://hub.rgukt.ac.in/hub/notice/index")

MAX_STORE = 10
COMPARE_COUNT = 5
FETCH_COUNT = 5

KEYWORDS = [
    "exam",
    "exams",
    "examination",
    "examinations",
    "external",
    "externals",
    "internal",
    "internals",
    "mt",
    "annual_exam",
    "rem",
    "remedial",
    "lab",
    "practical"  
]

def get_sheet():

    creds_info = json.loads(
        os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    )

    creds = Credentials.from_service_account_info(
        creds_info,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets"
        ]
    )

    gc = gspread.authorize(creds)

    spreadsheet = gc.open_by_key(
        SPREADSHEET_ID
    )

    return spreadsheet.worksheet(
        "Notices"
    )


async def send_notice(bot, notice):
    parts = notice.split("|", 2)

    title = parts[0]
    external = parts[1] if len(parts) > 1 else None
    attachment = parts[2] if len(parts) > 2 else None

    msg = f"\n{title}"

    if external and external != "None":
        msg += f"\nURL: {external}"
    else:
        msg += f"\nURL: {NOTICE_URL}"

    if attachment and attachment != "None":
        msg += f"\nAttachment: {attachment}"

    await bot.send_message(
        chat_id=GROUP_CHAT_ID,
        text=msg
    )

def is_exam_notice(title):

    title = title.lower()

    for keyword in KEYWORDS:
        if keyword in title:
            return True

    return False


def extract_links(body_div, base_url=NOTICE_URL):
    attachment = None
    external = None

    if body_div is None:
        return attachment, external

    for tag in body_div.find_all("a", href=True):
        href = tag["href"].strip()
        text = tag.get_text(" ", strip=True).lower()

        if not href:
            continue

        full_url = urljoin(base_url, href)

        if (
            text in {"download attachment", "download"}
            or href.lower().split("?")[0].endswith(
                (".pdf", ".doc", ".docx")
            )
        ):
            attachment = full_url

        elif "here" in text or "view link" in text:
            external = full_url

    return attachment, external



def scrape_latest_notices():
    response = requests.get(
        NOTICE_URL,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    items = soup.select(".notice-item")

    if not items:
        raise RuntimeError(
            "No notice items found. Check portal HTML."
        )

    notices = []

    for item in items:
        header = item.select_one(".accordion-header")

        if header is None:
            continue
 
        title_tag = header.select_one(".notice-subject")

        if title_tag:
            title = title_tag.get_text(" ", strip=True)
        else:
             
            header_copy = BeautifulSoup(
                str(header), "html.parser"
            )

            for element in header_copy.select(
                ".notice-new, .notice-date, .notice-ico, i"
            ):
                element.decompose()

            title = header_copy.get_text(" ", strip=True)

        if not title or not is_exam_notice(title):
            continue

        body = item.select_one(
            ".accordion-collapse .accordion-body"
        )

        if body is None:
            body = item.select_one(".notice-body")

        attachment, external = extract_links(
            body, response.url
        )

        notices.append(
            f"{title}|{external}|{attachment}"
        )

    print(f"Portal items found: {len(items)}")
    print(f"Matching exam notices: {len(notices)}")

    return notices[:FETCH_COUNT]



def get_last_five_from_sheet():

    sheet = get_sheet()

    values = sheet.col_values(1)

    if not values:
        return []

    if values[0].lower() == "notice":
        values = values[1:]

    return values[:COMPARE_COUNT]


def save_notices(new_notices):

    sheet = get_sheet()

    try:
        existing = sheet.col_values(1)

        if existing and existing[0].lower() == "notice":
            existing = existing[1:]

    except Exception:
        existing = []

    merged = []
    seen = set()

    for notice in new_notices + existing:

        if notice not in seen:

            merged.append(notice)

            seen.add(notice)

    merged = merged[:MAX_STORE]

    data = [["notice"]]

    for notice in merged:
        data.append([notice])

    sheet.update(
        range_name=f"A1:A{len(data)}",
        values=data
    )

    print(
        f"Saved {len(merged)} notices"
    )

async def main():

    print("\nFetching RGUKT notices...")

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    latest_notices = scrape_latest_notices()

    sheet_notices = get_last_five_from_sheet()

    new_notices = []

    for notice in latest_notices:

        if notice not in sheet_notices:
            new_notices.append(notice)

    print(
        f"Latest fetched : {len(latest_notices)}"
    )

    print(
        f"Compared against : {len(sheet_notices)}"
    )

    print(
        f"New notices : {len(new_notices)}"
    )

    for notice in reversed(new_notices):

        print(
            "Sending:",
            notice.split("|")[0]
        )

        await send_notice(
            app.bot,
            notice
        )

    save_notices(
        latest_notices
    )

    print("Done")


app = Flask(__name__)

@app.route("/")
def home():
    return "RGUKT Exam Bot Running"

def start_bot():

    while True:

        try:

            print("\nChecking notices...")

            asyncio.run(main())

        except Exception as e:

            print(
                f"Bot Error: {e}"
            )

        time.sleep(300)  


if __name__ == "__main__":

    bot_thread = Thread(
        target=start_bot,
        daemon=True
    )

    bot_thread.start()

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
