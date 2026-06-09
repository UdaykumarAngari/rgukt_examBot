from flask import Flask
import asyncio
from exam_bot import main

app = Flask(__name__)

@app.route("/")
def run_bot():
    asyncio.run(main())
    return "RGUKT Exam Bot Executed"