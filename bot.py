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

# Raxi Win API URL (WinGo 1 Min ke liye typeId: 1)
API_URL = "https://raxi4.com/api/webapi/GetNoaverageEmerdList"

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Raxi Win 1Min Bot is Live!")
    def log_message(self, format, *args):
        pass

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

bot = Bot(token=BOT_TOKEN)
IST = pytz.timezone('Asia/Kolkata')
UTC = pytz.UTC

# Loss hone par 1x -> 2x -> 4x -> 8x -> 16x -> 32x progression
LEVELS = [1, 2, 4, 8, 16, 32]
level_index = 0

def get_current_wingo_1min_period():
    now_ist = datetime.now(IST)
    now_utc = datetime.now(UTC)
    date_str = now_ist.strftime("%Y%m%d")
    total_minutes = now_utc.hour * 60 + now_utc.minute
    round_number = total_minutes + 1
    period_id = f"{date_str}10001{round_number:04d}"
    return period_id, now_utc.second

def fetch_actual_result(target_period):
    """Raxi Win server se 1Min ka asli result (BIG ya SMALL) check karta hai"""
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": "https://raxi4.com",
        "Referer": "https://raxi4.com/"
    }
    payload = {
        "pageSize": 5,
        "pageNo": 1,
        "typeId": 1,
        "language": 0
    }
    try:
        res = requests.post(API_URL, json=payload, headers=headers, timeout=8)
        data = res.json()
        records = data.get("data", {}).get("list", [])
        for item in records:
            if str(item.get("issueNumber")) == str(target_period):
                num = int(item.get("number"))
                return "BIG" if num >= 5 else "SMALL"
    except Exception as e:
        print("API error:", e, flush=True)
    return None

async def check_result_and_send_sticker(period_id, pred_choice):
    """1 minute baad result check karega: sirf WIN par sticker, LOSS par 2x/4x/8x"""
    global level_index
    await asyncio.sleep(61)

    actual_result = None
    for _ in range(3):
        actual_result = fetch_actual_result(period_id)
        if actual_result:
            break
        await asyncio.sleep(2)

    if actual_result == pred_choice:
        # Sirf WIN hone par sticker dalega aur level wapas 1x (index 0) karega
        try:
            await bot.send_sticker(chat_id=CHANNEL_ID, sticker=WIN_STICKER)
            print(f"WIN! Sticker sent for {period_id}", flush=True)
        except Exception as e:
            print("Sticker error:", e, flush=True)
        level_index = 0
    elif actual_result is not None:
        # LOSS hone par sticker nahi dalega aur level 2x, 4x, 8x badhayega
        level_index = (level_index + 1) % len(LEVELS)
        print(f"LOSS for {period_id} (Actual: {actual_result}). Next level: {LEVELS[level_index]}x", flush=True)
    else:
        print(f"Result fetch nahi hua for {period_id}", flush=True)

async def start_bot():
    last_period = ""
    print("Raxi Win 1-Min Smart Bot chalu ho gaya hai...", flush=True)

    while True:
        period_id, current_sec = get_current_wingo_1min_period()

        if period_id != last_period and current_sec < 4:
            last_period = period_id
            current_mult = LEVELS[level_index]
            pred_choice = random.choice(["BIG", "SMALL"])
            pred_display = "BIG 🟢" if pred_choice == "BIG" else "SMALL 🔴"

            pred_msg = (
                f"🔥 **RAXI WIN - WINGO 1 MIN** 🔥\n\n"
                f"🆔 **Period:** `{period_id}`\n"
                f"🎯 **Prediction:** **{pred_display}**\n"
                f"💰 **Level:** {current_mult}x\n\n"
                f"⏳ _1 Minute Round!_"
            )
            try:
                await bot.send_message(chat_id=CHANNEL_ID, text=pred_msg, parse_mode="Markdown")
                print(f"Sent 1Min prediction for {period_id}: {pred_choice} ({current_mult}x)", flush=True)
                asyncio.create_task(check_result_and_send_sticker(period_id, pred_choice))
            except Exception as e:
                print("Message error:", e, flush=True)

        await asyncio.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    asyncio.run(start_bot())
