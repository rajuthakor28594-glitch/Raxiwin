import asyncio
import datetime
import os
import random
import threading
import requests
from flask import Flask
from telegram import Bot
from telegram.constants import ParseMode

# ================= CONFIGURATION =================
BOT_TOKEN = "9254738470:AAG85xqtnBcfFlpWX0_Eonq3p_iv8srpVlk"
CHANNEL_ID = "-1002395334740"

# Aapke Telegram Stickers ki File IDs
WIN_STICKER_ID = "CAACAgUAAxkBAAEk9DBrB-J7q40-uSyXaeY4QbFSWBMuKwACMRUAAsA16FeZI-wzeGAu_T0E"
LOSS_3X_STICKER_ID = "CAACAgUAAxkBAAEk9ChrB-IpRe3b0bdmmApGZoRKD55tRQACTwMAAk5qkVTbERf7V1MOtD0E"

# Target Setting: 10 wins complete hote hi bot band ho jayega
TARGET_WINS = 10

# Platform API URL
API_URL = "https://api.bdg88zf.com/api/webapi/GetNoaverageEmerdList"
# =================================================

# Render par bot ko active rakhne ke liye web server
app = Flask(__name__)

@app.route('/')
def home():
    return "Raxi Win 1-Min Auto Prediction Bot is Running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

bot = Bot(token=BOT_TOKEN)

stats = {
    "total_rounds": 0,
    "wins": 0,
    "losses": 0,
    "current_level": 1,
    "history": []
}

def get_latest_result():
    try:
        payload = {"pageSize": 5, "pageNo": 1, "typeId": 1, "language": 0}
        response = requests.post(API_URL, json=payload, timeout=10).json()
        latest = response["data"]["list"][0]
        period = str(latest["issueNumber"])
        number = int(latest["number"])
        result_type = "BIG" if number >= 5 else "SMALL"
        return period, number, result_type
    except Exception as e:
        print(f"API Error: {e}")
        return None, None, None

def smart_prediction(history):
    if len(history) < 3:
        return random.choice(["BIG", "SMALL"])
    
    last_three = history[-3:]
    # Dragon trend follow karein (3 same results)
    if last_three[0] == last_three[1] == last_three[2]:
        return last_three[-1]
    # Alternate pattern (BIG-SMALL-BIG) par reversal
    elif last_three[0] == last_three[2] and last_three[0] != last_three[1]:
        return last_three[1]
    else:
        return "SMALL" if last_three[-1] == "BIG" else "BIG"

def calculate_ratio():
    if stats["total_rounds"] == 0:
        return 0.0
    return round((stats["wins"] / stats["total_rounds"]) * 100, 2)

async def send_prediction_loop():
    last_processed_period = None
    active_prediction = None
    target_period = None

    await bot.send_message(
        chat_id=CHANNEL_ID,
        text=(
            f"🚀 **RAXI WIN 1-MIN AUTO PREDICTION STARTED!**\n"
            f"🎯 **Session Target:** `{TARGET_WINS} Wins`\n"
            f"Smart logic active hai. Fund manage karke khelein!"
        ),
        parse_mode=ParseMode.MARKDOWN
    )

    while True:
        period, number, actual_result = get_latest_result()

        if period and period != last_processed_period:
            last_processed_period = period
            stats["history"].append(actual_result)

            # 1. Pichhli prediction ka result check karein
            if target_period == period and active_prediction:
                stats["total_rounds"] += 1
                
                if active_prediction == actual_result:
                    # WIN CASE
                    stats["wins"] += 1
                    stats["current_level"] = 1
                    ratio = calculate_ratio()
                    
                    await bot.send_sticker(chat_id=CHANNEL_ID, sticker=WIN_STICKER_ID)
                    await bot.send_message(
                        chat_id=CHANNEL_ID,
                        text=(
                            f"✅ **WIN ({stats['wins']}/{TARGET_WINS})!** | Period: `{period[-4:]}`\n"
                            f"🎲 Result: **{actual_result} ({number})**\n"
                            f"📊 **Achieving Ratio:** `{ratio}%` ({stats['wins']}W / {stats['losses']}L)"
                        ),
                        parse_mode=ParseMode.MARKDOWN
                    )

                    # 10 Wins poori hote hi Auto-Stop
                    if stats["wins"] >= TARGET_WINS:
                        await bot.send_message(
                            chat_id=CHANNEL_ID,
                            text=(
                                f"🛑 **TARGET ACHIEVED ({TARGET_WINS}/{TARGET_WINS} WINS)!**\n"
                                f"🏆 Session yahan successfully stop kiya ja raha hai.\n"
                                f"📈 **Final Achieving Ratio:** `{ratio}%` ({stats['wins']}W / {stats['losses']}L)\n"
                                f"Agle session ke liye ready rahein!"
                            ),
                            parse_mode=ParseMode.MARKDOWN
                        )
                        break

                else:
                    # LOSS CASE (3X Multiplier)
                    stats["losses"] += 1
                    stats["current_level"] += 1
                    multiplier = 3 ** (stats["current_level"] - 1)
                    ratio = calculate_ratio()

                    await bot.send_sticker(chat_id=CHANNEL_ID, sticker=LOSS_3X_STICKER_ID)
                    await bot.send_message(
                        chat_id=CHANNEL_ID,
                        text=(
                            f"❌ **LOSS** | Period: `{period[-4:]}`\n"
                            f"🎲 Result: **{actual_result} ({number})**\n"
                            f"⚠️ **Agle Round mein {multiplier}X Fund lagayein!**\n"
                            f"📊 **Current Ratio:** `{ratio}%` ({stats['wins']}W / {stats['losses']}L)"
                        ),
                        parse_mode=ParseMode.MARKDOWN
                    )

            # 2. Agle Period ki Prediction bhejein
            next_period = str(int(period) + 1)
            target_period = next_period
            active_prediction = smart_prediction(stats["history"])
            multiplier = 3 ** (stats["current_level"] - 1)

            pred_msg = (
                f"🔮 **WINGO 1-MIN PREDICTION**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🆔 **Period:** `{next_period[-4:]}`\n"
                f"🎯 **Prediction:** **{active_prediction}**\n"
                f"💰 **Level:** `{multiplier}X`\n"
                f"🏆 **Progress:** `{stats['wins']}/{TARGET_WINS} Wins`\n"
                f"━━━━━━━━━━━━━━━━━━"
            )
            await bot.send_message(chat_id=CHANNEL_ID, text=pred_msg, parse_mode=ParseMode.MARKDOWN)

        await asyncio.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    asyncio.run(send_prediction_loop())
