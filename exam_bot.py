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
# Configuration

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID"))

SPREADSHEET_ID =  os.getenv("SPREADSHEET_ID")

NOTICE_URL = "https://hub.rgukt.ac.in/hub/notice/index"

MAX_STORE = 20
COMPARE_COUNT = 10
FETCH_COUNT = 10

KEYWORDS = [
    "exam",
    "examination",
    "external",
    "externals",
    "internal",
    "internals",
    "mt",
    "annual",
    "annual_exam",
    "rem",
    "remedial",
    "lab",
    "practical",
    'exams'
]

# Fetching GOOGLE SHEETS credentials from environment variable and authorizing gspread
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

# TELEGRAM 


async def send_notice(bot, notice):

    title, external, attachment = notice.split("|")

    msg = f"{title}\n"

    if external and external != "None":
        msg += f"\nURL: {external}"

    if attachment and attachment != "None":
        msg += f"\nAttachment: {attachment}"

    await bot.send_message(
        chat_id=GROUP_CHAT_ID,
        text=msg
    )


# SCRAPER 


def is_exam_notice(title):

    title = title.lower()

    for keyword in KEYWORDS:
        if keyword in title:
            return True

    return False


def extract_links(body_div):

    attachment = None
    external = None

    if not body_div:
        return None, None

    for tag in body_div.find_all("a", href=True):

        href = tag["href"]

        if href.lower().endswith(
            (".pdf", ".doc", ".docx")
        ):
            attachment = urljoin(
                NOTICE_URL,
                href
            )
            break

    click_here = body_div.find(
        "a",
        string=lambda x: x and "here" in x.lower()
    )

    if click_here:
        external = urljoin(
            NOTICE_URL,
            click_here.get("href")
        )

    return attachment, external


def scrape_latest_notices():

    response = requests.get(
        NOTICE_URL,
        timeout=20
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    notices = []

    headers = soup.find_all(
        "div",
        class_="card-header"
    )

    for header in headers:

        title_tag = header.find(
            "a",
            class_="card-link"
        )

        if not title_tag:
            continue

        title = title_tag.get_text(
            strip=True
        )

        if not is_exam_notice(title):
            continue

        collapse_div = header.find_next_sibling(
            "div",
            class_="collapse"
        )

        body_div = None

        if collapse_div:
            body_div = collapse_div.find(
                "div",
                class_="card-body"
            )

        attachment, external = extract_links(
            body_div
        )

        notice = (
            f"{title}|"
            f"{external}|"
            f"{attachment}"
        )

        notices.append(notice)

    return notices[:FETCH_COUNT]


# Google Sheets Storage 


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

    sheet.clear()

    sheet.update(
        "A1",
        data
    )

    print(
        f"Saved {len(merged)} notices"
    )


# MAIN 


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


if __name__ == "__main__":
    asyncio.run(main())