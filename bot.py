import asyncio
import datetime
import json
import os
import random
import threading
import time
import requests
from flask import Flask
from telegram import Bot
from telegram.constants import ParseMode

# ================= CONFIGURATION =================
BOT_TOKEN = "9254738470:AAG85xqtnBcfFlpWX0_Eonq3p_iv8srpVlk"
CHANNEL_ID = "-1002395334740"
ADMIN_ID = 5393186266  # Sirf aapki ID par buttons kaam karenge

# Aapke Teeno Naye Telegram Stickers ki File IDs
WIN_STICKER_ID = "CAACAgUAAxkBAAEk9IRrB_GSO5UIfZQftzfQFE8svAbQaQAC_x8AAggtMFbkJANnlpbxHz0E"
JACKPOT_STICKER_ID = "CAACAgUAAxkBAAEk9IZrB_HKtsW4aNvLbiremRn0j9Db8AACuBcAAjH9wFY9iSPUQkDLej0E"
LOSS_3X_STICKER_ID = "CAACAgUAAxkBAAEk9H5rB_EPVt_xMlrn1vf_yYsOUwh0CQAckBEAAi4AATBXrdSO4Z9ezAM9BA"

TARGET_WINS = 10
REGISTER_LINK = "https://www.raxiwin.game/#/register?invitationCode=51966105844"
RENDER_URL = "https://raxiwin.onrender.com"
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
# =================================================

app = Flask(__name__)

@app.route('/')
def home():
    return "Raxi Win 1-Min Admin Control Bot is Running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def keep_alive_pinger():
    """Har 10 minute mein Render server ko ping karta hai taaki bot sleep na ho"""
    while True:
        time.sleep(600)
        try:
            requests.get(RENDER_URL, timeout=10)
        except Exception:
            pass

bot = Bot(token=BOT_TOKEN)

stats = {
    "total_rounds": 0,
    "wins": 0,
    "losses": 0,
    "current_level": 1,
    "active": False,
    "current_period": "",
    "last_size": "BIG",
    "last_nums": [6, 8],
    "history": ["BIG", "SMALL", "SMALL", "SMALL", "BIG"]
}

def get_ist_now():
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)

def get_raxi_period_number(dt):
    date_prefix = dt.strftime("%Y%m%d")
    minutes_passed = dt.hour * 60 + dt.minute
    round_seq = 9671 + minutes_passed
    return f"{date_prefix}1000{round_seq}"

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

def get_keyboard_json():
    next_mult = 3 ** stats["current_level"]
    if stats["active"]:
        keyboard = [
            [
                {"text": f"✅ WIN ({stats['wins'] + 1}/{TARGET_WINS})", "callback_data": "mark_win"},
                {"text": f"❌ LOSS ({next_mult}X)", "callback_data": "mark_loss"}
            ],
            [
                {"text": f"🎰 JACKPOT WIN ({stats['wins'] + 1}/{TARGET_WINS})", "callback_data": "mark_jackpot"}
            ],
            [
                {"text": "🛑 STOP PREDICTION", "callback_data": "stop_session"}
            ]
        ]
    else:
        keyboard = [
            [
                {"text": "▶️ START PREDICTION", "callback_data": "start_session"}
            ]
        ]
    return json.dumps({"inline_keyboard": keyboard})

def send_admin_panel(text):
    try:
        requests.post(
            f"{TG_API}/sendMessage",
            data={
                "chat_id": ADMIN_ID,
                "text": text,
                "parse_mode": "Markdown",
                "reply_markup": get_keyboard_json()
            },
            timeout=10
        )
    except Exception as e:
        print(f"Admin Panel Error: {e}")

def edit_admin_panel(chat_id, message_id, text):
    try:
        requests.post(
            f"{TG_API}/editMessageText",
            data={
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "parse_mode": "Markdown",
                "reply_markup": get_keyboard_json()
            },
            timeout=10
        )
    except Exception as e:
        print(f"Edit Panel Error: {e}")

async def post_next_prediction():
    """Naya current period nikal kar channel mein next trade post karta hai"""
    now = get_ist_now()
    current_period = get_raxi_period_number(now)
    stats["current_period"] = current_period

    active_size, active_nums = smart_prediction(stats["history"])
    stats["last_size"] = active_size
    stats["last_nums"] = active_nums

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

async def process_admin_action(action, chat_id, message_id):
    period_short = stats["current_period"][-4:] if stats["current_period"] else "----"

    if action == "start_session":
        stats["active"] = True
        stats["wins"] = 0
        stats["losses"] = 0
        stats["total_rounds"] = 0
        stats["current_level"] = 1

        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=(
                f"🔥 **RAXI WIN - WINGO 1 MIN STARTED!** 🔥\n"
                f"🎯 **Session Target:** `0/{TARGET_WINS} Wins`\n"
                f"🔗 **Register:** [Click Here to Join]({REGISTER_LINK})"
            ),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )

        await post_next_prediction()

        edit_admin_panel(
            chat_id, message_id,
            f"🟢 **PREDICTION RUNNING (0/{TARGET_WINS})**\n"
            f"🆔 Active Period: `{stats['current_period']}` (`{stats['last_size']}` | `{stats['last_nums'][0]}, {stats['last_nums'][1]}`)\n"
            f"⏳ Result aane ke baad niche button dabayein:"
        )

    elif action == "stop_session":
        stats["active"] = False
        ratio = calculate_ratio()

        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=(
                f"🛑 **PREDICTION SESSION STOPPED!**\n"
                f"🏆 **Total Wins:** `{stats['wins']}/{TARGET_WINS}`\n"
                f"📈 **Final Achieving Ratio:** `{ratio}%` ({stats['wins']}W / {stats['losses']}L)\n"
                f"Agle session ke liye ready rahein!"
            ),
            parse_mode=ParseMode.MARKDOWN
        )

        edit_admin_panel(
            chat_id, message_id,
            f"🔴 **PREDICTION STOPPED**\n"
            f"📊 Final Ratio: `{ratio}%` ({stats['wins']}W / {stats['losses']}L)\n"
            f"Dobara shuru karne ke liye **START PREDICTION** dabayein:"
        )

    elif action == "mark_win":
        if not stats["active"]:
            edit_admin_panel(chat_id, message_id, "🔴 Prediction band hai. Pehle START dabayein:")
            return

        prev_wins = stats["wins"]
        stats["total_rounds"] += 1
        stats["wins"] += 1
        stats["current_level"] = 1
        stats["history"].append(stats["last_size"])
        ratio = calculate_ratio()

        # 1. Normal Win Sticker bhejein
        await bot.send_sticker(chat_id=CHANNEL_ID, sticker=WIN_STICKER_ID)

        # 2. Winning Target progression aur Ratio bhejein
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=(
                f"🏆 **WINNING TARGET: {prev_wins}/{TARGET_WINS} ➔ {stats['wins']}/{TARGET_WINS}** ✅\n"
                f"🆔 Period: `{period_short}` | Result: **{stats['last_size']}** PASS\n"
                f"📊 **Achieving Ratio:** `{ratio}%` ({stats['wins']}W / {stats['losses']}L)"
            ),
            parse_mode=ParseMode.MARKDOWN
        )

        await asyncio.sleep(2)
        await post_next_prediction()

        edit_admin_panel(
            chat_id, message_id,
            f"🟢 **PREDICTION RUNNING ({stats['wins']}/{TARGET_WINS})**\n"
            f"✅ Last: **WIN** (`{prev_wins}/{TARGET_WINS} ➔ {stats['wins']}/{TARGET_WINS}`)\n"
            f"🆔 Next Period: `{stats['current_period']}` (`{stats['last_size']}` | `{stats['last_nums'][0]}, {stats['last_nums'][1]}`)\n"
            f"📊 Ratio: `{ratio}%`"
        )

    elif action == "mark_jackpot":
        if not stats["active"]:
            edit_admin_panel(chat_id, message_id, "🔴 Prediction band hai. Pehle START dabayein:")
            return

        prev_wins = stats["wins"]
        stats["total_rounds"] += 1
        stats["wins"] += 1
        stats["current_level"] = 1
        stats["history"].append(stats["last_size"])
        ratio = calculate_ratio()
        nums_str = f"{stats['last_nums'][0]}, {stats['last_nums'][1]}"

        # 1. Dono Stickers bhejein (Pehle Win Sticker, phir Jackpot Number Sticker)
        await bot.send_sticker(chat_id=CHANNEL_ID, sticker=WIN_STICKER_ID)
        await bot.send_sticker(chat_id=CHANNEL_ID, sticker=JACKPOT_STICKER_ID)

        # 2. Jackpot Number Win message + Win Count update bhejein
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=(
                f"🎰 **JACKPOT NUMBER WIN!** 🎰\n"
                f"🏆 **WINNING TARGET: {prev_wins}/{TARGET_WINS} ➔ {stats['wins']}/{TARGET_WINS}** ✅\n"
                f"🆔 Period: `{period_short}` | Result: **{stats['last_size']}** & Number (**{nums_str}**) PASS!\n"
                f"📊 **Achieving Ratio:** `{ratio}%` ({stats['wins']}W / {stats['losses']}L)"
            ),
            parse_mode=ParseMode.MARKDOWN
        )

        await asyncio.sleep(2)
        await post_next_prediction()

        edit_admin_panel(
            chat_id, message_id,
            f"🟢 **PREDICTION RUNNING ({stats['wins']}/{TARGET_WINS})**\n"
            f"🎰 Last: **JACKPOT WIN** (`{prev_wins}/{TARGET_WINS} ➔ {stats['wins']}/{TARGET_WINS}`)\n"
            f"🆔 Next Period: `{stats['current_period']}` (`{stats['last_size']}` | `{stats['last_nums'][0]}, {stats['last_nums'][1]}`)\n"
            f"📊 Ratio: `{ratio}%`"
        )

    elif action == "mark_loss":
        if not stats["active"]:
            edit_admin_panel(chat_id, message_id, "🔴 Prediction band hai. Pehle START dabayein:")
            return

        stats["total_rounds"] += 1
        stats["losses"] += 1
        stats["current_level"] += 1
        opp_size = "SMALL" if stats["last_size"] == "BIG" else "BIG"
        stats["history"].append(opp_size)
        multiplier = 3 ** (stats["current_level"] - 1)
        ratio = calculate_ratio()

        # 1. Naya Loss Sticker aur Alert bhejein
        await bot.send_sticker(chat_id=CHANNEL_ID, sticker=LOSS_3X_STICKER_ID)
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=(
                f"❌ **LOSS** | Period: `{period_short}` | Wins: `{stats['wins']}/{TARGET_WINS}`\n"
                f"⚠️ **Agle Round mein {multiplier}x Fund lagayein!**\n"
                f"📊 **Current Ratio:** `{ratio}%` ({stats['wins']}W / {stats['losses']}L)"
            ),
            parse_mode=ParseMode.MARKDOWN
        )

        await asyncio.sleep(2)
        await post_next_prediction()

        edit_admin_panel(
            chat_id, message_id,
            f"🟢 **PREDICTION RUNNING ({stats['wins']}/{TARGET_WINS})**\n"
            f"❌ Last: **LOSS** ➔ Next Level: **{multiplier}x**\n"
            f"🆔 Next Period: `{stats['current_period']}` (`{stats['last_size']}` | `{stats['last_nums'][0]}, {stats['last_nums'][1]}`)\n"
            f"📊 Ratio: `{ratio}%`"
        )

async def main_loop():
    offset = 0

    try:
        r = requests.get(f"{TG_API}/getUpdates", params={"offset": -1}, timeout=5).json()
        if r.get("result"):
            offset = r["result"][-1]["update_id"] + 1
    except Exception:
        pass

    send_admin_panel(
        f"🎛 **RAXI WIN CONTROL PANEL READY!**\n"
        f"Teeno naye stickers aur **🎰 JACKPOT WIN** button update ho gaye hain.\n"
        f"Shuru karne ke liye **START PREDICTION** dabayein:"
    )

    while True:
        try:
            res = requests.get(f"{TG_API}/getUpdates", params={"offset": offset, "timeout": 1}, timeout=5).json()
            for upd in res.get("result", []):
                offset = upd["update_id"] + 1

                if "message" in upd and upd["message"].get("from", {}).get("id") == ADMIN_ID:
                    txt = upd["message"].get("text", "")
                    if txt.startswith("/start"):
                        status_txt = f"🟢 RUNNING ({stats['wins']}/{TARGET_WINS})" if stats["active"] else "🔴 STOPPED"
                        send_admin_panel(
                            f"🎛 **RAXI WIN CONTROL PANEL ({status_txt})**\n"
                            f"Niche buttons se control karein:"
                        )

                elif "callback_query" in upd:
                    cb = upd["callback_query"]
                    if cb.get("from", {}).get("id") == ADMIN_ID:
                        requests.post(f"{TG_API}/answerCallbackQuery", data={"callback_query_id": cb["id"]}, timeout=5)
                        action = cb.get("data")
                        chat_id = cb["message"]["chat"]["id"]
                        msg_id = cb["message"]["message_id"]
                        await process_admin_action(action, chat_id, msg_id)
        except Exception as e:
            print(f"Update check error: {e}")

        await asyncio.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=keep_alive_pinger, daemon=True).start()
    asyncio.run(main_loop())
