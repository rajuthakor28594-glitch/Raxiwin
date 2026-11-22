import asyncio
import random
from datetime import datetime
import pytz
from telegram import Bot

# --- यहाँ सिर्फ अपना Bot Token डालें ---
BOT_TOKEN = "9254738470:AAG85xqtnBcfFlpWXO_Eonq3 p_iv8srpVlk"

CHANNEL_ID = "-1002395334740"
WIN_STICKER = "CAACAgUAAxkBAAEk11BrAxiWg-reLn36ILw5RH1v7kNr2wACohcAArwMgVfzyjUbYvTAxD0E"

bot = Bot(token=BOT_TOKEN)
IST = pytz.timezone('Asia/Kolkata')

def get_current_wingo_30s_period():
    now = datetime.now(IST)
    date_str = now.strftime("%Y%m%d")
    total_seconds = now.hour * 3600 + now.minute * 60 + now.second
    round_number = (total_seconds // 30) + 1
    period_id = f"{date_str}10005{round_number:04d}"
    return period_id, now.second

async def start_bot():
    last_period = ""
    win_streak = 0
    print("Raxi Win 30S Bot चालू हो गया है...")

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
            except Exception as e:
                print("मैसेज भेजने में दिक्कत:", e)

            await asyncio.sleep(27)

            try:
                await bot.send_sticker(chat_id=CHANNEL_ID, sticker=WIN_STICKER)
                win_streak += 1
            except Exception as e:
                print("स्टिकर भेजने में दिक्कत:", e)

        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(start_bot())
