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

# Aapka Raxi Win Authorization Token
AUTH_TOKEN = "EyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOiIxNzk1Mzc0MjY4IiwibmJmIjoiMTc5NTM3NDI2OCIsImV4cCI6IjE3OTUzNzYwNjgiLCJodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL3dzLzIwMDgvMDYvaWRlbnRpdHkvY2xhaW1zL2V4cGlyYXRpb24iOiIxMS8yMy8yMDI2IDE6MDQ6MjggQU0iLCJodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL3dzLzIwMDgvMDYvaWRlbnRpdHkvY2xhaW1zL3JvbGUiOiJBY2Nlc3NfVG9rZW4iLCJVc2VySWQiOiIxMDU4NDQiLCJVc2VyTmFtZSI6IjkxNzM1OTg3MjM3NCIsIlVzZXJQaG90byI6IjEiLCJOaWNrTmFtZSI6Ik1lbWJlck5OR1ZDOU1GIiwiQW1vdW50IjoiMC4wMCIsIkludGVncmFsIjoiMCIsIkxvZ2luTWFyayI6Ikg1IiwiTG9naW5UaW1lIjoiMTEvMjMvMjAyNiAxMjozNDoyOCBBTSIsIkxvZ2luSVBBZGRyZXNzIjoiMjQwOTo0MGMxOjg6N2NiMDo4MDAwOjoiLCJEYk51bWJlciI6IjAiLCJJc3ZhbGlkYXRvciI6IjAiLCJLZXlDb2RlIjoiMTE4IiwiVG9rZW5UeXBlIjoiQWNjZXNzX1Rva2VuIiwiUGhvbmVUeXBlIjoiMSIsIlVzZXJUeXBlIjoiMCIsIlVzZXJOYW1lMiI6IiIsImlzcyI6Imp3dElzc3VlciIsImF1ZCI6ImxvdHRlcnlUaWNrZXQifQ.ve8GqpfR0d5RNLYCJh1UE41KaUDP0VPFMO4dCdXj11I"
API_URL = "https://www.raxi4.com/api/webapi/GetNoaverageEmerdList"

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
        "language": 0
    }
    try:
        res = requests.post(API_URL, json=payload, headers=headers, timeout=8)
        if not res.text.strip():
            return []
        data = res.json()
        return data.get("data", {}).get("list", [])
    except Exception as e:
        print("API error:", e, flush=True)
        return []

def get_smart_prediction():
    global level_index, last_pred
    records = fetch_recent_records(10)
    if not records:
        return random.choice(["BIG", "SMALL"])

    outcomes = ["BIG" if int(item.get("number")) >= 5 else "SMALL" for item in records]
    latest = outcomes[0]

    # 1. Agar lagatar 3 ya zyada ek hi result aa raha hai (Dragon Trend), to trend follow karein
    if len(outcomes) >= 3 and outcomes[0] == outcomes[1] == outcomes[2]:
        choice = latest
    # 2. Agar pichhle 2 level (1x, 2x) loss hue hain, to strategy palat kar opposite chunein
    elif level_index >= 2 and last_pred:
        choice = "SMALL" if last_pred == "BIG" else "BIG"
    # 3. Zig-Zag pattern (ABAB) check karein
    elif len(outcomes) >= 4 and outcomes[0] != outcomes[1] and outcomes[1] != outcomes[2] and outcomes[2] != outcomes[3]:
        choice = "SMALL" if latest == "BIG" else "BIG"
    # 4. Pichhle 10 rounds mein jo kam aaya hai uska balance karein
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
    for _ in range(4):
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
        print(f"Result fetch nahi ho paya for {period_id} (Check Token)", flush=True)

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
