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

WIN_STICKER_ID = "CAACAgUAAxkBAAEk9DBrB-J7q40-uSyXaeY4QbFSWBMuKwACMRUAAsA16FeZI-wzeGAu_T0E"
LOSS_3X_STICKER_ID = "CAACAgUAAxkBAAEk9ChrB-IpRe3b0bdmmApGZoRKD55tRQACTwMAAk5qkVTbERf7V1MOtD0E"

TARGET_WINS = 10

RAXI_API_URLS = [
    "https://api.raxiwin.game/api/webapi/GetNoaverageEmerdList",
    "https://www.raxiwin.game/api/webapi/GetNoaverageEmerdList",
    "https://raxiwin.game/api/webapi/GetNoaverageEmerdList",
    "https://api.bdg88zf.com/api/webapi/GetNoaverageEmerdList"
]

REGISTER_LINK = "https://www.raxiwin.game/#/register?invitationCode=51966105844"
# =================================================

app = Flask(__name__)

@app.route('/')
def home():
    return "Raxi Win 1-Min Auto Prediction Bot is Running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

bot = Bot(token=BOT_TOKEN)

# Screenshot ke last 5 results (7, 1, 4, 0, 7 -> BIG, SMALL, SMALL, SMALL, BIG) se start
stats = {
    "total_rounds": 0,
    "wins": 0,
    "losses": 0,
    "current_level": 1,
    "history": ["BIG", "SMALL", "SMALL", "SMALL", "BIG"]
}

def get_ist_now():
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)

def get_raxi_period_number(dt):
    """1:22 PM (802 mins) = 20261126100010473 ke hisaab se exact Period Number"""
    date_prefix = dt.strftime("%Y%m%d")
    minutes_passed = dt.hour * 60 + dt.minute
    round_seq = 9671 + minutes_passed
    return f"{date_prefix}1000{round_seq}"

def fetch_raxi_result():
    payload = {
        "pageSize": 5,
        "pageNo": 1,
        "typeId": 1,
        "language": 0,
        "random": "4a0522c6ecd8410496260e686be2a572",
        "signature": "334B5E70A0C9B8918B0B15E517E2069C",
        "timestamp": int(datetime.datetime.now().timestamp())
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36",
        "Origin": "https://www.raxiwin.game",
        "Referer": "https://www.raxiwin.game/",
        "Content-Type": "application/json;charset=UTF-8"
    }

    for url in RAXI_API_URLS:
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if data and "data" in data and data["data"] and "list" in data["data"]:
                    latest = data["data"]["list"][0]
                    period = str(latest["issueNumber"])
                    number = int(latest["number"])
                    result_type = "BIG" if number >= 5 else "SMALL"
                    return period, number, result_type
        except Exception:
            continue
    return None, None, None

def smart_prediction(history):
    last_three = history[-3:]
    if last_three[0] == last_three[1] == last_three[2]:
        pred_size = last_three[-1]
    elif last_three[0] == last_three[2] and last_three[0] != last_three[1]:
        pred_size = last_three[1]
    else:
        pred_size = "SMALL" if last_three[-1] == "BIG" else "BIG"

    if pred_size == "BIG":
        pred_nums = sorted(random.sample([5, 6, 7, 8, 9], 2))
    else:
        pred_nums = sorted(random.sample([0, 1, 2, 3, 4], 2))

    return pred_size, pred_nums

def calculate_ratio():
    if stats["total_rounds"] == 0:
        return 0.0
    return round((stats["wins"] / stats["total_rounds"]) * 100, 2)

async def send_prediction_loop():
    last_predicted_period = None
    active_size = None
    active_nums = []
    target_period = None

    await bot.send_message(
        chat_id=CHANNEL_ID,
        text=(
            f"🔥 **RAXI WIN - WINGO 1 MIN STARTED!** 🔥\n"
            f"🎯 **Session Target:** `{TARGET_WINS} Wins`\n"
            f"🔗 **Register:** [Click Here to Join]({REGISTER_LINK})"
        ),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )

    while True:
        now = get_ist_now()
        current_period = get_raxi_period_number(now)

        if current_period != last_predicted_period:
            last_predicted_period = current_period

            # 1. Pichhle period ka real number check karein
            if target_period and active_size:
                await asyncio.sleep(4)
                res_period, number, actual_result = fetch_raxi_result()

                if res_period == target_period and actual_result:
                    stats["total_rounds"] += 1
                    stats["history"].append(actual_result)
                    is_size_win = (active_size == actual_result)
                    is_num_win = (number in active_nums)

                    if is_size_win or is_num_win:
                        stats["wins"] += 1
                        stats["current_level"] = 1
                        ratio = calculate_ratio()
                        win_label = "NUMBER + BIG/SMALL!" if (is_size_win and is_num_win) else ("NUMBER WIN!" if is_num_win else "BIG/SMALL WIN!")

                        await bot.send_sticker(chat_id=CHANNEL_ID, sticker=WIN_STICKER_ID)
                        await bot.send_message(
                            chat_id=CHANNEL_ID,
                            text=(
                                f"✅ **WIN ({stats['wins']}/{TARGET_WINS}) - {win_label}**\n"
                                f"🆔 Period: `{target_period[-4:]}` | Real Number: **{number} ({actual_result})**\n"
                                f"📊 **Achieving Ratio:** `{ratio}%` ({stats['wins']}W / {stats['losses']}L)"
                            ),
                            parse_mode=ParseMode.MARKDOWN
                        )

                        if stats["wins"] >= TARGET_WINS:
                            await bot.send_message(
                                chat_id=CHANNEL_ID,
                                text=(
                                    f"🛑 **TARGET ACHIEVED ({TARGET_WINS}/{TARGET_WINS} WINS)!**\n"
                                    f"🏆 Session complete! Final Ratio: `{ratio}%` ({stats['wins']}W / {stats['losses']}L)"
                                ),
                                parse_mode=ParseMode.MARKDOWN
                            )
                            break
                    else:
                        stats["losses"] += 1
                        stats["current_level"] += 1
                        multiplier = 3 ** (stats["current_level"] - 1)
                        ratio = calculate_ratio()

                        await bot.send_sticker(chat_id=CHANNEL_ID, sticker=LOSS_3X_STICKER_ID)
                        await bot.send_message(
                            chat_id=CHANNEL_ID,
                            text=(
                                f"❌ **LOSS** | Period: `{target_period[-4:]}`\n"
                                f"🎲 Real Number: **{number} ({actual_result})**\n"
                                f"⚠️ **Agle Round mein {multiplier}x Fund lagayein!**\n"
                                f"📊 **Current Ratio:** `{ratio}%` ({stats['wins']}W / {stats['losses']}L)"
                            ),
                            parse_mode=ParseMode.MARKDOWN
                        )

            # 2. Naya Prediction bhejein (Exact Period + BIG/SMALL + Numbers)
            target_period = current_period
            active_size, active_nums = smart_prediction(stats["history"])
            multiplier = 3 ** (stats["current_level"] - 1)
            size_emoji = "🟢" if active_size == "BIG" else "🔴"
            nums_str = f"{active_nums[0]}, {active_nums[1]}"

            pred_msg = (
                f"🔥 **RAXI WIN - WINGO 1 MIN** 🔥\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🆔 **Period:** `{current_period}`\n"
                f"🎯 **Prediction:** **{active_size}** {size_emoji}\n"
                f"🔢 **Numbers:** **{nums_str}**\n"
                f"💰 **Level:** `{multiplier}x`\n"
                f"🏆 **Wins:** `{stats['wins']}/{TARGET_WINS}`\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🔗 [Play on Raxi Win]({REGISTER_LINK})"
            )
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text=pred_msg,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )

        await asyncio.sleep(2)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    asyncio.run(send_prediction_loop())
