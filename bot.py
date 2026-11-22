import os
import asyncio
import random
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import pytz
from telegram import Bot

# --- Bot Details ---
BOT_TOKEN = "9254738470:AAG85xqtnBcfFlpWX0_Eonq3p_iv8srpVlk"
CHANNEL_ID = "-1002395334740"
WIN_STICKER = "CAACAgUAAxkBAAEk11BrAxiWg-reLn36ILw5RH1v7kNr2wACohcAArwMgVfzyjUbYvTAxD0E"

AUTH_TOKEN = "EyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOiIxNzk1Mzc2MDA0IiwibmJmIjoiMTc5NTM3NjAwNCIsImV4cCI6IjE3OTUzNzc4MDQiLCJodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL3dzLzIwMDgvMDYvaWRlbnRpdHkvY2xhaW1zL2V4cGlyYXRpb24iOiIxMS8yMy8yMDI2IDE6MzM6MjQgQU0iLCJodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL3dzLzIwMDgvMDYvaWRlbnRpdHkvY2xhaW1zL3JvbGUiOiJBY2Nlc3NfVG9rZW4iLCJVc2VySWQiOiI0Nzg1OTM0IiwiVXNlck5hbWUiOiI5MTg2MTk5NDQzMzUiLCJVc2VyUGhvdG8iOiIxIiwiTmlja05hbWUiOiJNZW1iZXJOTkdERFY1SiIsIkFtb3VudCI6IjQuNDkiLCJJbnRlZ3JhbCI6IjAiLCJMb2dpbk1hcmsiOiJINSIsIkxvZ2luVGltZSI6IjExLzIzLzIwMjYgMTowMzoyNCBBTSIsIkxvZ2luSVBBZGRyZXNzIjoiMjQwOTo0MGMxOjg6N2NiMDo4MDAwOjoiLCJEYk51bWJlciI6IjAiLCJJc3ZhbGlkYXRvciI6IjAiLCJLZXlDb2RlIjoiNDU2IiwiVG9rZW5UeXBlIjoiQWNjZXNzX1Rva2VuIiwiUGhvbmVUeXBlIjoiMSIsIlVzZXJUeXBlIjoiMCIsIlVzZXJOYW1lMiI6IiIsImlzcyI6Imp3dElzc3VlciIsImF1ZCI6ImxvdHRlcnlUaWNrZXQifQ.OZ3Cty04ADJy0YWmMJKihHk5hZhmTyT6s6u3awVRBdY"

API_URLS = [
    "https://www.raxi4.com/api/webapi/GetNoaverageEmerdList",
    "https://api.raxi4.com/api/webapi/GetNoaverageEmerdList"
]

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Raxi Win Smart 1Min Bot is Live!")
    def log_message(self, format, *args):
        pass

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

bot = Bot(token=BOT_TOKEN)
UTC = pytz.UTC

LEVELS = [1, 2, 4, 8, 16, 32]
level_index = 0
last_pred = None
win_streak = 0

def get_current_wingo_1min_period():
    now_utc = datetime.now(UTC)
    date_str = now_utc.strftime("%Y%m%d")
    total_minutes = now_utc.hour * 60 + now_utc.minute
    round_number = total_minutes + 1
    period_id = f"{date_str}10001{round_number:04d}"
    return period_id, now_utc.second

def fetch_recent_records(count=10):
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Origin": "https://www.raxi4.com",
        "Referer": "https://www.raxi4.com/"
    }
    payload = {
        "pageSize": count,
        "pageNo": 1,
        "typeId": 1,
        "language": 0,
        "random": "4a0522c6ecd8410496260e686be2a57c",
        "signature": "334B5E70A0C9B8918B0B15E517E2069C",
        "timestamp": int(datetime.now(UTC).timestamp())
    }
    for url in API_URLS:
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=8)
            print(f"API [{url}] Status: {res.status_code} | Resp: {res.text[:150]}", flush=True)
            if res.text.strip():
                data = res.json()
                records = data.get("data", {}).get("list", [])
                if records:
                    return records
        except Exception as e:
            print(f"API error [{url}]: {e}", flush=True)
    return []

def get_smart_prediction():
    global level_index, last_pred
    records = fetch_recent_records(10)
    if not records:
        return random.choice(["BIG", "SMALL"])

    outcomes = ["BIG" if int(item.get("number")) >= 5 else "SMALL" for item in records]
    latest = outcomes[0]

    if len(outcomes) >= 3 and outcomes[0] == outcomes[1] == outcomes[2]:
        choice = latest
    elif level_index >= 2 and last_pred:
        choice = "SMALL" if last_pred == "BIG" else "BIG"
    elif len(outcomes) >= 4 and outcomes[0] != outcomes[1] and outcomes[1] != outcomes[2] and outcomes[2] != outcomes[3]:
        choice = "SMALL" if latest == "BIG" else "BIG"
    else:
        big_count = outcomes.count("BIG")
        small_count = outcomes.count("SMALL")
        choice = "SMALL" if big_count > small_count else ("BIG" if small_count > big_count else latest)

    last_pred = choice
    return choice

def fetch_actual_result(target_period):
    records = fetch_recent_records(10)
    for item in records:
        if str(item.get("issueNumber")) == str(target_period):
            num = int(item.get("number"))
            return "BIG" if num >= 5 else "SMALL"
    return None

async def check_result_and_send_sticker(period_id, pred_choice):
    global level_index, win_streak
    await asyncio.sleep(62)

    actual_result = None
    for _ in range(3):
        actual_result = fetch_actual_result(period_id)
        if actual_result:
            break
        await asyncio.sleep(2)

    if actual_result == pred_choice:
        win_streak += 1
        try:
            await bot.send_sticker(chat_id=CHANNEL_ID, sticker=WIN_STICKER)
            print(f"WIN! (Streak: {win_streak}) Sticker sent for {period_id}", flush=True)
        except Exception as e:
            print("Sticker error:", e, flush=True)
        level_index = 0
    elif actual_result is not None:
        win_streak = 0
        level_index = (level_index + 1) % len(LEVELS)
        print(f"LOSS for {period_id} (Actual: {actual_result}). Next level: {LEVELS[level_index]}x", flush=True)
    else:
        print(f"Result fetch nahi ho paya for {period_id}", flush=True)

async def start_bot():
    last_period = ""
    print("Raxi Win Smart 1-Min Bot chalu ho gaya hai!", flush=True)

    while True:
        period_id, current_sec = get_current_wingo_1min_period()

        if period_id != last_period and current_sec < 4:
            last_period = period_id
            current_mult = LEVELS[level_index]
            pred_choice = get_smart_prediction()
            pred_display = "BIG 🟢" if pred_choice == "BIG" else "SMALL 🔴"
            streak_line = f"🔥 **Win Streak:** {win_streak}\n" if win_streak >= 2 else ""

            pred_msg = (
                f"🔥 **RAXI WIN - WINGO 1 MIN** 🔥\n\n"
                f"🆔 **Period:** `{period_id}`\n"
                f"🎯 **Prediction:** **{pred_display}**\n"
                f"💰 **Level:** {current_mult}x\n"
                f"{streak_line}\n"
                f"⏳ _1 Minute Round!_"
            )
            try:
                await bot.send_message(chat_id=CHANNEL_ID, text=pred_msg, parse_mode="Markdown")
                print(f"Sent Smart prediction for {period_id}: {pred_choice} ({current_mult}x)", flush=True)
                asyncio.create_task(check_result_and_send_sticker(period_id, pred_choice))
            except Exception as e:
                print("Message error:", e, flush=True)

        await asyncio.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    asyncio.run(start_bot())
