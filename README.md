# RGUKT Exam Notice Bot

A Telegram-based automation bot that monitors **official RGUKT exam and academic notifications** and delivers real-time updates to students through a dedicated Telegram channel.  
The project aims to ensure that no student misses critical academic announcements due to unreliable or informal communication channels.

---

## Official Telegram Channel

All verified exam and academic updates are posted here:

Link : https://t.me/examsrguktb

Students are encouraged to **join the channel** to receive instant notifications.

---

## Why This Project?

### Problem

At RGUKT, important academic notifications—such as **remedial exam registration announcements**—are often circulated through informal channels like WhatsApp groups or forwarded messages. Due to message overload, delayed forwarding, or limited reach of these groups, several students missed critical notifications from the RGUKT Hub, resulting in missed deadlines and academic inconvenience.

---

### Solution

To address this issue, a **dedicated Telegram notification bot** was developed. The bot independently tracks official RGUKT exam and academic notice sources and publishes verified updates directly to a centralized Telegram channel. This removes dependency on informal forwarding mechanisms and ensures timely, consistent, and reliable delivery of important announcements.

---

### Impact

The application provides a **centralized and reliable notification system** for RGUKT students. By delivering real-time updates via Telegram, it significantly reduces the risk of missing time-sensitive academic information, improves communication efficiency, and enhances students’ ability to stay informed without repeatedly checking multiple platforms.

---

## Features

- Automatically monitors official RGUKT exam and academic notices  
- Detects newly published or updated notifications  
- Sends real-time alerts to a Telegram channel  
- Prevents duplicate notifications  
- Simple, lightweight, and efficient  

---

## Tech Stack

- **Language:** Python  
- **Web Scraping / Automation:** Requests, BeautifulSoup  
- **Notifications:** Telegram Bot API  
- **Scheduling:** Cron / Time-based execution  

---

## 📂 Project Structure

```text
rgukt_examBot/
│
├── main.py / bot.py       # Core bot logic
├── requirements.txt       # Project dependencies
├── sent_notices.json      # Stores already sent notices
└── README.md              # Documentation
