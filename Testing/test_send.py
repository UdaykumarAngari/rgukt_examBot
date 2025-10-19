import asyncio
from telegram.ext import Application
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN") or "8079829863:AAHEEEocjDQev462BAtflyY782cPLtHNca8"
GROUP_CHAT_ID = int(os.environ.get("GROUP_CHAT_ID") or -1003133538365)  # your channel/group ID

async def main():
    application = Application.builder().token(BOT_TOKEN).build()
    try:
        await application.bot.send_message(GROUP_CHAT_ID, "✅ Test message from RGUKT Exam Bot")
        print("[SUCCESS] Test message sent!")
    except Exception as e:
        print(f"[ERROR] Test message failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
