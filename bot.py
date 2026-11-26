import datetime
import json
import os
import random
import threading
import time
import requests
from flask import Flask, request

# ================= CONFIGURATION =================
BOT_TOKEN = "9254738470:AAG85xqtnBcfFlpWX0_Eonq3p_iv8srpVlk"
CHANNEL_ID = "-1002395334740"
ADMIN_ID = 5393186266

TARGET_WINS = 10
REGISTER_LINK = "https://www.raxiwin.game/#/register?invitationCode=51966105844"
RENDER_URL = "https://raxiwin.onrender.com"
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
# =================================================

app = Flask(__name__)

# Yahan aapke khud ke bot se bheje gaye stickers save honge
stickers = {
    "win": "",
    "jackpot": "",
    "loss": "",
    "waiting_for": None  # 'win', 'jackpot', ya 'loss'
}

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
    w_ok = "✅" if stickers["win"] else "⚠️"
    j_ok = "✅" if stickers["jackpot"] else "⚠️"
    l_ok = "✅" if stickers["loss"] else "⚠️"

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
            ],
            [
                {"text": f"{w_ok} Set Win", "callback_data": "set_win"},
                {"text": f"{j_ok} Set Jackpot", "callback_data": "set_jackpot"},
                {"text": f"{l_ok} Set Loss", "callback_data": "set_loss"}
            ]
        ]
    else:
        keyboard = [
            [
                {"text": "▶️ START PREDICTION", "callback_data": "start_session"}
            ],
            [
                {"text": f"{w_ok} Set Win Sticker", "callback_data": "set_win"},
                {"text": f"{j_ok} Set Jackpot Sticker", "callback_data": "set_jackpot"}
            ],
            [
                {"text": f"{l_ok} Set Loss Sticker", "callback_data": "set_loss"}
            ]
        ]
    return json.dumps({"inline_keyboard": keyboard})

def tg_send_msg(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(f"{TG_API}/sendMessage", json=payload, timeout=10)
    except Exception as e:
        print(f"Send Msg Error: {e}")

def tg_send_sticker(chat_id, sticker_id):
    if not sticker_id:
        return
    try:
        res = requests.post(
            f"{TG_API}/sendSticker",
            json={"chat_id": chat_id, "sticker": sticker_id},
            timeout=10
        ).json()
        if not res.get("ok"):
            tg_send_msg(ADMIN_ID, f"⚠️ Sticker Error: `{res.get('description')}`")
    except Exception as e:
        print(f"Send Sticker Error: {e}")

def edit_admin_panel(chat_id, message_id, text):
    try:
        requests.post(
            f"{TG_API}/editMessageText",
            json={
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "parse_mode": "Markdown",
                "reply_markup": json.loads(get_keyboard_json())
            },
            timeout=10
        )
    except Exception as e:
        print(f"Edit Panel Error: {e}")

def post_next_prediction():
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
    tg_send_msg(CHANNEL_ID, pred_msg)

def handle_action(action, chat_id, message_id):
    period_short = stats["current_period"][-4:] if stats["current_period"] else "----"

    if action in ["set_win", "set_jackpot", "set_loss"]:
        key = action.replace("set_", "")
        stickers["waiting_for"] = key
        tg_send_msg(ADMIN_ID, f"👇 Ab apna **{key.upper()} STICKER** is chat mein bhejein (send karein):")
        return

    if action == "start_session":
        stats["active"] = True
        stats["wins"] = 0
        stats["losses"] = 0
        stats["total_rounds"] = 0
        stats["current_level"] = 1

        tg_send_msg(
            CHANNEL_ID,
            f"🔥 **RAXI WIN - WINGO 1 MIN STARTED!** 🔥\n"
            f"🎯 **Session Target:** `0/{TARGET_WINS} Wins`\n"
            f"🔗 **Register:** [Click Here to Join]({REGISTER_LINK})"
        )

        post_next_prediction()

        edit_admin_panel(
            chat_id, message_id,
            f"🟢 **PREDICTION RUNNING (0/{TARGET_WINS})**\n"
            f"🆔 Active Period: `{stats['current_period']}` (`{stats['last_size']}` | `{stats['last_nums'][0]}, {stats['last_nums'][1]}`)\n"
            f"⏳ Result aane ke baad niche button dabayein:"
        )

    elif action == "stop_session":
        stats["active"] = False
        ratio = calculate_ratio()

        tg_send_msg(
            CHANNEL_ID,
            f"🛑 **PREDICTION SESSION STOPPED!**\n"
            f"🏆 **Total Wins:** `{stats['wins']}/{TARGET_WINS}`\n"
            f"📈 **Final Achieving Ratio:** `{ratio}%` ({stats['wins']}W / {stats['losses']}L)\n"
            f"Agle session ke liye ready rahein!"
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

        tg_send_sticker(CHANNEL_ID, stickers["win"])
        tg_send_msg(
            CHANNEL_ID,
            f"🏆 **WINNING TARGET: {prev_wins}/{TARGET_WINS} ➔ {stats['wins']}/{TARGET_WINS}** ✅\n"
            f"🆔 Period: `{period_short}` | Result: **{stats['last_size']}** PASS\n"
            f"📊 **Achieving Ratio:** `{ratio}%` ({stats['wins']}W / {stats['losses']}L)"
        )

        time.sleep(1.5)
        post_next_prediction()

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

        tg_send_sticker(CHANNEL_ID, stickers["win"])
        tg_send_sticker(CHANNEL_ID, stickers["jackpot"])
        tg_send_msg(
            CHANNEL_ID,
            f"🎰 **JACKPOT NUMBER WIN!** 🎰\n"
            f"🏆 **WINNING TARGET: {prev_wins}/{TARGET_WINS} ➔ {stats['wins']}/{TARGET_WINS}** ✅\n"
            f"🆔 Period: `{period_short}` | Result: **{stats['last_size']}** & Number (**{nums_str}**) PASS!\n"
            f"📊 **Achieving Ratio:** `{ratio}%` ({stats['wins']}W / {stats['losses']}L)"
        )

        time.sleep(1.5)
        post_next_prediction()

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

        tg_send_sticker(CHANNEL_ID, stickers["loss"])
        tg_send_msg(
            CHANNEL_ID,
            f"❌ **LOSS** | Period: `{period_short}` | Wins: `{stats['wins']}/{TARGET_WINS}`\n"
            f"⚠️ **Agle Round mein {multiplier}x Fund lagayein!**\n"
            f"📊 **Current Ratio:** `{ratio}%` ({stats['wins']}W / {stats['losses']}L)"
        )

        time.sleep(1.5)
        post_next_prediction()

        edit_admin_panel(
            chat_id, message_id,
            f"🟢 **PREDICTION RUNNING ({stats['wins']}/{TARGET_WINS})**\n"
            f"❌ Last: **LOSS** ➔ Next Level: **{multiplier}x**\n"
            f"🆔 Next Period: `{stats['current_period']}` (`{stats['last_size']}` | `{stats['last_nums'][0]}, {stats['last_nums'][1]}`)\n"
            f"📊 Ratio: `{ratio}%`"
        )

@app.route('/')
def home():
    return "Raxi Win Webhook Bot is Active!"

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    upd = request.get_json(silent=True) or {}

    if "message" in upd and upd["message"].get("from", {}).get("id") == ADMIN_ID:
        msg = upd["message"]
        txt = msg.get("text", "")

        # Agar Admin ne sticker bheja hai toh uski exact file_id save karein
        if "sticker" in msg:
            file_id = msg["sticker"]["file_id"]
            target = stickers["waiting_for"] or "win"
            stickers[target] = file_id
            stickers["waiting_for"] = None
            tg_send_msg(
                ADMIN_ID,
                f"✅ **{target.upper()} STICKER SAVED!**\nAb channel mein 100% sticker jayega:",
                reply_markup=get_keyboard_json()
            )
            return "OK", 200

        if txt.startswith("/start"):
            status_txt = f"🟢 RUNNING ({stats['wins']}/{TARGET_WINS})" if stats["active"] else "🔴 STOPPED"
            tg_send_msg(
                ADMIN_ID,
                f"🎛 **RAXI WIN CONTROL PANEL ({status_txt})**\n"
                f"Pehle niche buttons se apne 3 stickers set kar lein (⚠️ ➔ ✅), phir **START PREDICTION** dabayein:",
                reply_markup=get_keyboard_json()
            )

    elif "callback_query" in upd:
        cb = upd["callback_query"]
        if cb.get("from", {}).get("id") == ADMIN_ID:
            try:
                requests.post(f"{TG_API}/answerCallbackQuery", json={"callback_query_id": cb["id"]}, timeout=5)
            except Exception:
                pass
            action = cb.get("data")
            chat_id = cb["message"]["chat"]["id"]
            msg_id = cb["message"]["message_id"]
            threading.Thread(target=handle_action, args=(action, chat_id, msg_id), daemon=True).start()

    return "OK", 200

def setup_webhook_and_ping():
    time.sleep(3)
    try:
        requests.post(
            f"{TG_API}/setWebhook",
            json={"url": f"{RENDER_URL}/webhook", "drop_pending_updates": True},
            timeout=10
        )
        tg_send_msg(
            ADMIN_ID,
            f"🎛 **RAXI WIN STICKER-SETUP PANEL READY!**\n"
            f"Niche **`⚠️ Set Win Sticker`**, **`⚠️ Set Jackpot Sticker`**, aur **`⚠️ Set Loss Sticker`** daba kar apne teeno stickers bhejein, phir **START PREDICTION** dabayein:",
            reply_markup=get_keyboard_json()
        )
    except Exception as e:
        print(f"Webhook Setup Error: {e}")

    while True:
        time.sleep(600)
        try:
            requests.get(RENDER_URL, timeout=10)
        except Exception:
            pass

if __name__ == "__main__":
    threading.Thread(target=setup_webhook_and_ping, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
