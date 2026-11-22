import os
import asyncio
import random
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import pytz
from telegram import Bot

# --- Bot Details ---
BOT_TOKEN = "9254738470:AAG85xqtnBcfFlpWX0_Eonq3p_iv8srpVlk"
CHANNEL_ID = "-1002395334740"
WIN_STICKER = "CAACAgUAAxkBAAEk11BrAxiWg-reLn36ILw5RH1v7kNr2wACohcAArwMgVfzyjUbYvTAxD0E"

# Render Web Service ko Live rakhne ke liye server
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Raxi Win Bot is Live!")
    def log_message(self, format, *args):
        pass

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

bot = Bot(token=BOT_TOKEN)
IST = pytz.timezone('Asia/Kolkata')
UTC = pytz.UTC

def get_current_wingo_30s_period():
    now_ist = datetime.now(IST)
    now_utc = datetime.now(UTC)
    date_str = now_ist.strftime("%Y%m%d")
    total_seconds = now_utc.hour * 3600 + now_utc.minute * 60 + now_utc.second
    round_number = (total_seconds // 30) + 1
    period_id = f"{date_str}10005{round_number:04d}"
    return period_id, now_utc.second

async def start_bot():
    last_period = ""
    win_streak = 0
    print("Raxi Win 30S Bot chalu ho gaya hai...", flush=True)

    while True:
        period_id, current_sec = get_current_wingo_30s_period()

        if period_id != last_period and (current_sec % 30) < 4:
            last_period = period_id
            prediction = random.choice(["BIG 🟢", "SMALL 🔴"])
            level = 1 if win_streak < 4 else 2

            pred_msg = (
                f"🔥 **RAXI WIN - WINGO 30S** 🔥\n\n"
                f"🆔 **Period:** `{period_id}`\n"
                f"🎯 **Prediction:** **{prediction}**\n"
                f"💰 **Level:** {level}x\n\n"
                f"⏳ _30 Seconds Fast Round!_"
            )
            try:
                await bot.send_message(chat_id=CHANNEL_ID, text=pred_msg, parse_mode="Markdown")
                print(f"Sent prediction for {period_id}", flush=True)
            except Exception as e:
                print("Message bhejne mein dikkat:", e, flush=True)

            await asyncio.sleep(27)

            try:
                await bot.send_sticker(chat_id=CHANNEL_ID, sticker=WIN_STICKER)
                win_streak += 1
                print(f"Sent sticker for {period_id}", flush=True)
            except Exception as e:
                print("Sticker bhejne mein dikkat:", e, flush=True)

        await asyncio.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    asyncio.run(start_bot())
