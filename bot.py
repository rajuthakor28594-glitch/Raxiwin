import datetime
import io
import json
import os
import random
import threading
import time
import requests
from flask import Flask, request
from PIL import Image, ImageDraw, ImageFont

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

stats = {
    "total_rounds": 0,
    "wins": 0,
    "losses": 0,
    "current_level": 1,
    "consecutive_losses": 0,
    "active": False,
    "current_period": "",
    "last_size": "BIG",
    "last_nums": [5, 7],
    "history": ["BIG", "SMALL", "BIG", "BIG", "SMALL", "SMALL", "BIG", "SMALL"],
    "num_history": [7, 2, 6, 8, 1, 4, 9, 3],
    "strategy_used": "TREND SCAN"
}

def get_ist_now():
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)

def get_raxi_period_number(dt):
    date_prefix = dt.strftime("%Y%m%d")
    minutes_passed = dt.hour * 60 + dt.minute
    round_seq = 9671 + minutes_passed
    return f"{date_prefix}1000{round_seq}"

def opposite(side):
    return "SMALL" if side == "BIG" else "BIG"

def smart_prediction(history, num_history, consec_losses):
    h = history[-8:]
    last1 = h[-1]
    last2 = h[-2:]
    last3 = h[-3:]
    last4 = h[-4:]

    if consec_losses >= 2:
        if last2[0] == last2[1]:
            pred_size = opposite(last1)
            strategy = "ANTI-TRAP BREAK"
        else:
            pred_size = last1
            strategy = "ANTI-TRAP LOCK"
    elif len(set(last4)) == 1:
        if len(h) >= 6 and len(set(h[-6:])) == 1:
            pred_size = opposite(last1)
            strategy = "DRAGON REVERSAL"
        else:
            pred_size = last1
            strategy = "DRAGON FOLLOW"
    elif last4[0] == last4[1] and last4[2] == last4[3] and last4[0] != last4[2]:
        pred_size = opposite(last1)
        strategy = "2-2 PAIR SHIFT"
    elif last4[0] != last4[1] and last4[1] != last4[2] and last4[2] != last4[3]:
        pred_size = opposite(last1)
        strategy = "ZIG-ZAG FLOW"
    elif last3[0] == last3[2] and last3[0] != last3[1]:
        pred_size = last3[1]
        strategy = "MIRROR PATTERN"
    elif last3[0] == last3[1] == last3[2]:
        pred_size = last1
        strategy = "STREAK RIDE"
    else:
        big_count = h.count("BIG")
        small_count = h.count("SMALL")
        if big_count >= 5:
            pred_size = "SMALL"
            strategy = "BALANCE SHIFT"
        elif small_count >= 5:
            pred_size = "BIG"
            strategy = "BALANCE SHIFT"
        else:
            pred_size = opposite(last1)
            strategy = "SMART ALTERNATE"

    recent_nums = set(num_history[-4:])
    pool = [5, 6, 7, 8, 9] if pred_size == "BIG" else [0, 1, 2, 3, 4]
    fresh_nums = [n for n in pool if n not in recent_nums]
    if len(fresh_nums) >= 2:
        pred_nums = sorted(random.sample(fresh_nums, 2))
    else:
        pred_nums = sorted(random.sample(pool, 2))

    return pred_size, pred_nums, strategy

def calculate_ratio():
    if stats["total_rounds"] == 0:
        return 0.0
    return round((stats["wins"] / stats["total_rounds"]) * 100, 2)

# ================= DYNAMIC WEBP STICKER GENERATOR =================
def get_font(size):
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    ]
    for path in font_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def draw_centered_text(draw, text, y, font, fill, stroke_fill=None, stroke_width=0):
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    x = (512 - w) // 2
    draw.text((x, y), text, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)

def image_to_webp_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=95)
    buf.seek(0)
    return buf

def make_prediction_sticker(period_short, level, pred_size):
    img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    border_col = (255, 195, 0, 255) if pred_size == "BIG" else (0, 225, 255, 255)
    text_col = (255, 220, 60, 255) if pred_size == "BIG" else (80, 240, 255, 255)

    # Outer glow card
    draw.rounded_rectangle([24, 24, 488, 488], radius=75, fill=(18, 20, 32, 248), outline=border_col, width=14)
    draw.rounded_rectangle([42, 42, 470, 470], radius=62, outline=(255, 60, 120, 180), width=4)

    # Top pill: #Period • LVL
    draw.rounded_rectangle([110, 82, 402, 134], radius=26, fill=(38, 42, 66, 255), outline=border_col, width=3)
    draw_centered_text(draw, f"#{period_short}  •  LVL {level}", 93, get_font(26), (255, 255, 255, 255))

    # Main BIG / SMALL text
    main_font = get_font(112 if pred_size == "BIG" else 88)
    y_pos = 185 if pred_size == "BIG" else 200
    draw_centered_text(draw, pred_size, y_pos, main_font, text_col, stroke_fill=(255, 90, 0, 255), stroke_width=4)

    # Bottom brand pill
    draw.rounded_rectangle([96, 365, 416, 418], radius=26, fill=(28, 32, 52, 255), outline=(0, 225, 255, 255), width=3)
    draw_centered_text(draw, "GOLDEN GROUP™ AI", 377, get_font(24), (255, 255, 255, 255))

    return image_to_webp_bytes(img)

def make_numbers_sticker(period_short, level, nums, pred_size):
    img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([24, 24, 488, 488], radius=75, fill=(14, 18, 30, 248), outline=(0, 230, 255, 255), width=14)

    # Top pill
    draw.rounded_rectangle([92, 68, 420, 118], radius=25, fill=(45, 25, 70, 255), outline=(220, 80, 255, 255), width=3)
    draw_centered_text(draw, f"{nums[0]} • {nums[1]}  |  #{period_short} LVL {level}", 80, get_font(22), (255, 255, 255, 255))

    # Left Gold Ball
    draw.ellipse([52, 155, 246, 349], fill=(245, 165, 0, 255), outline=(255, 245, 180, 255), width=10)
    draw.ellipse([68, 171, 230, 333], outline=(255, 255, 255, 200), width=4)
    draw.text((116, 192), str(nums[0]), font=get_font(105), fill=(255, 255, 255, 255), stroke_width=4, stroke_fill=(120, 60, 0, 255))

    # Right Emerald Green Ball
    draw.ellipse([266, 155, 460, 349], fill=(0, 195, 95, 255), outline=(180, 255, 210, 255), width=10)
    draw.ellipse([282, 171, 444, 333], outline=(255, 255, 255, 200), width=4)
    draw.text((330, 192), str(nums[1]), font=get_font(105), fill=(255, 255, 255, 255), stroke_width=4, stroke_fill=(0, 80, 35, 255))

    draw_centered_text(draw, f"GOLDEN JACKPOT NUMBERS ({pred_size})", 392, get_font(20), (190, 245, 255, 255))
    return image_to_webp_bytes(img)

def make_win_count_sticker(win_num, target_wins, period_short):
    img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([24, 24, 488, 488], radius=75, fill=(14, 32, 22, 250), outline=(0, 255, 130, 255), width=14)
    draw.rounded_rectangle([44, 44, 468, 468], radius=60, outline=(255, 215, 0, 200), width=4)

    draw_centered_text(draw, f"PERIOD #{period_short}", 80, get_font(26), (180, 255, 210, 255))
    draw_centered_text(draw, f"WIN {win_num}", 155, get_font(112), (0, 255, 135, 255), stroke_fill=(255, 215, 0, 255), stroke_width=4)

    draw.rounded_rectangle([120, 310, 392, 368], radius=28, fill=(255, 200, 0, 255))
    draw_centered_text(draw, f"TARGET {win_num}/{target_wins} PASS", 324, get_font(26), (20, 25, 15, 255))
    draw_centered_text(draw, "GOLDEN GROUP™ VIP", 405, get_font(23), (255, 255, 255, 255))

    return image_to_webp_bytes(img)

def make_number_jackpot_sticker(hit_num, period_short):
    img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([24, 24, 488, 488], radius=75, fill=(32, 16, 42, 250), outline=(255, 200, 0, 255), width=14)
    draw_centered_text(draw, "JACKPOT NUMBER HIT!", 68, get_font(28), (255, 225, 70, 255))

    # Big Golden Center Ball (0 to 9)
    draw.ellipse([141, 130, 371, 360], fill=(255, 175, 0, 255), outline=(255, 250, 200, 255), width=12)
    draw.ellipse([159, 148, 353, 342], outline=(255, 255, 255, 220), width=4)
    draw_centered_text(draw, str(hit_num), 172, get_font(135), (255, 255, 255, 255), stroke_fill=(130, 50, 0, 255), stroke_width=5)

    draw_centered_text(draw, f"NUMBER {hit_num} WIN  •  #{period_short}", 398, get_font(25), (255, 255, 255, 255))
    return image_to_webp_bytes(img)

def make_loss_sticker(next_mult, period_short):
    img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([24, 24, 488, 488], radius=75, fill=(38, 14, 20, 250), outline=(255, 55, 75, 255), width=14)
    draw_centered_text(draw, f"PERIOD #{period_short} LOSS", 85, get_font(28), (255, 180, 185, 255))
    draw_centered_text(draw, f"NEXT {next_mult}X", 175, get_font(102), (255, 65, 80, 255), stroke_fill=(255, 220, 0, 255), stroke_width=3)
    draw_centered_text(draw, "FOLLOW FUND MANAGEMENT", 335, get_font(23), (255, 230, 120, 255))
    draw_centered_text(draw, "GOLDEN GROUP™ AI", 405, get_font(22), (255, 255, 255, 255))

    return image_to_webp_bytes(img)

# ================= TELEGRAM SEND HELPERS =================
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

def tg_send_webp_sticker(chat_id, webp_buf):
    try:
        requests.post(
            f"{TG_API}/sendSticker",
            data={"chat_id": chat_id},
            files={"sticker": ("sticker.webp", webp_buf, "image/webp")},
            timeout=15
        )
    except Exception as e:
        print(f"Send WebP Sticker Error: {e}")

def get_keyboard_json():
    next_mult = 3 ** stats["current_level"]
    n1, n2 = stats["last_nums"][0], stats["last_nums"][1]

    if stats["active"]:
        keyboard = [
            [
                {"text": f"✅ WIN ({stats['wins'] + 1}/{TARGET_WINS})", "callback_data": "mark_win"},
                {"text": f"❌ LOSS ({next_mult}X)", "callback_data": "mark_loss"}
            ],
            [
                {"text": f"🎰 NUM {n1} WIN", "callback_data": f"num_win_{n1}"},
                {"text": f"🎰 NUM {n2} WIN", "callback_data": f"num_win_{n2}"}
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
    return {"inline_keyboard": keyboard}

def edit_admin_panel(chat_id, message_id, text):
    try:
        requests.post(
            f"{TG_API}/editMessageText",
            json={
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

def post_next_prediction():
    now = get_ist_now()
    current_period = get_raxi_period_number(now)
    stats["current_period"] = current_period
    period_short = current_period[-4:]

    active_size, active_nums, strategy = smart_prediction(
        stats["history"],
        stats["num_history"],
        stats["consecutive_losses"]
    )
    stats["last_size"] = active_size
    stats["last_nums"] = active_nums
    stats["strategy_used"] = strategy

    level_num = stats["current_level"]
    multiplier = 3 ** (level_num - 1)
    nums_str = f"[ {active_nums[0]} , {active_nums[1]} ]"

    # 1. Text Prediction Message
    pred_msg = (
        f"⚡ **GOLDEN GROUP™ AI QUANTUM PRO • WINGO 1 MINUTE**\n\n"
        f"🆔 **Period:** `{current_period}` (`#{period_short}`)\n"
        f"⏱ **Prediction:** **{active_size}**\n"
        f"🎯 **Jackpot Numbers:** **{nums_str}**\n"
        f"📊 **Active Level:** `LEVEL {level_num}` (`{multiplier}x`)\n"
        f"🏆 **Session Wins:** `{stats['wins']}/{TARGET_WINS}`\n"
        f"🛡 **Always maintain 7 level fund**\n"
        f"🔗 [Register on Raxi Win]({REGISTER_LINK})"
    )
    tg_send_msg(CHANNEL_ID, pred_msg)

    # 2. Custom BIG/SMALL Badge Sticker
    st1 = make_prediction_sticker(period_short, level_num, active_size)
    tg_send_webp_sticker(CHANNEL_ID, st1)

    # 3. Custom Dual Numbers Sticker
    st2 = make_numbers_sticker(period_short, level_num, active_nums, active_size)
    tg_send_webp_sticker(CHANNEL_ID, st2)

def handle_action(action, chat_id, message_id):
    period_short = stats["current_period"][-4:] if stats["current_period"] else "0000"

    if action == "start_session":
        stats["active"] = True
        stats["wins"] = 0
        stats["losses"] = 0
        stats["total_rounds"] = 0
        stats["current_level"] = 1
        stats["consecutive_losses"] = 0

        tg_send_msg(
            CHANNEL_ID,
            f"🔥 **GOLDEN GROUP™ — WINGO 1 MIN STARTED!** 🔥\n"
            f"🎯 **Session Target:** `0/{TARGET_WINS} Wins`\n"
            f"🔗 **Register:** [Click Here to Join]({REGISTER_LINK})"
        )

        post_next_prediction()

        edit_admin_panel(
            chat_id, message_id,
            f"🟢 **PREDICTION RUNNING (0/{TARGET_WINS})**\n"
            f"🆔 Active: `#{period_short}` (`{stats['last_size']}` | `{stats['last_nums'][0]}, {stats['last_nums'][1]}`)\n"
            f"🧠 AI Logic: `{stats['strategy_used']}`"
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
        stats["consecutive_losses"] = 0
        stats["history"].append(stats["last_size"])
        stats["num_history"].append(random.choice(stats["last_nums"]))
        ratio = calculate_ratio()

        # WIN 1, WIN 2 ... WIN 10 Custom Sticker
        win_st = make_win_count_sticker(stats["wins"], TARGET_WINS, period_short)
        tg_send_webp_sticker(CHANNEL_ID, win_st)

        tg_send_msg(
            CHANNEL_ID,
            f"🏆 **WINNING TARGET: {prev_wins}/{TARGET_WINS} ➔ {stats['wins']}/{TARGET_WINS}** ✅\n"
            f"🆔 Period: `#{period_short}` | Result: **{stats['last_size']}** PASS\n"
            f"📊 **Achieving Ratio:** `{ratio}%` ({stats['wins']}W / {stats['losses']}L)"
        )

        time.sleep(1.5)
        post_next_prediction()

        edit_admin_panel(
            chat_id, message_id,
            f"🟢 **PREDICTION RUNNING ({stats['wins']}/{TARGET_WINS})**\n"
            f"✅ Last: **WIN {stats['wins']}** (`#{period_short}`)\n"
            f"🆔 Next: `#{stats['current_period'][-4:]}` (`{stats['last_size']}` | `{stats['last_nums'][0]}, {stats['last_nums'][1]}`)\n"
            f"🧠 Logic: `{stats['strategy_used']}` | Ratio: `{ratio}%`"
        )

    elif action.startswith("num_win_"):
        if not stats["active"]:
            edit_admin_panel(chat_id, message_id, "🔴 Prediction band hai. Pehle START dabayein:")
            return

        hit_num = int(action.split("_")[-1])
        prev_wins = stats["wins"]
        stats["total_rounds"] += 1
        stats["wins"] += 1
        stats["current_level"] = 1
        stats["consecutive_losses"] = 0
        stats["history"].append(stats["last_size"])
        stats["num_history"].append(hit_num)
        ratio = calculate_ratio()

        # 1. WIN 1..10 Sticker
        win_st = make_win_count_sticker(stats["wins"], TARGET_WINS, period_short)
        tg_send_webp_sticker(CHANNEL_ID, win_st)

        # 2. Exact Winning Number (0 to 9) Jackpot Sticker
        num_st = make_number_jackpot_sticker(hit_num, period_short)
        tg_send_webp_sticker(CHANNEL_ID, num_st)

        tg_send_msg(
            CHANNEL_ID,
            f"🎰 **JACKPOT NUMBER {hit_num} WIN!** 🎰\n"
            f"🏆 **WINNING TARGET: {prev_wins}/{TARGET_WINS} ➔ {stats['wins']}/{TARGET_WINS}** ✅\n"
            f"🆔 Period: `#{period_short}` | **{stats['last_size']}** & Number **{hit_num}** PASS!\n"
            f"📊 **Achieving Ratio:** `{ratio}%` ({stats['wins']}W / {stats['losses']}L)"
        )

        time.sleep(1.5)
        post_next_prediction()

        edit_admin_panel(
            chat_id, message_id,
            f"🟢 **PREDICTION RUNNING ({stats['wins']}/{TARGET_WINS})**\n"
            f"🎰 Last: **NUM {hit_num} JACKPOT** (`WIN {stats['wins']}`)\n"
            f"🆔 Next: `#{stats['current_period'][-4:]}` (`{stats['last_size']}` | `{stats['last_nums'][0]}, {stats['last_nums'][1]}`)\n"
            f"🧠 Logic: `{stats['strategy_used']}` | Ratio: `{ratio}%`"
        )

    elif action == "mark_loss":
        if not stats["active"]:
            edit_admin_panel(chat_id, message_id, "🔴 Prediction band hai. Pehle START dabayein:")
            return

        stats["total_rounds"] += 1
        stats["losses"] += 1
        stats["current_level"] += 1
        stats["consecutive_losses"] += 1
        opp_size = opposite(stats["last_size"])
        stats["history"].append(opp_size)
        opp_pool = [5, 6, 7, 8, 9] if opp_size == "BIG" else [0, 1, 2, 3, 4]
        stats["num_history"].append(random.choice(opp_pool))
        multiplier = 3 ** (stats["current_level"] - 1)
        ratio = calculate_ratio()

        # Dynamic NEXT 3X / 9X Loss Sticker
        loss_st = make_loss_sticker(multiplier, period_short)
        tg_send_webp_sticker(CHANNEL_ID, loss_st)

        tg_send_msg(
            CHANNEL_ID,
            f"❌ **LOSS** | Period: `#{period_short}` | Wins: `{stats['wins']}/{TARGET_WINS}`\n"
            f"⚠️ **Agle Round mein {multiplier}x Fund lagayein!**\n"
            f"📊 **Current Ratio:** `{ratio}%` ({stats['wins']}W / {stats['losses']}L)"
        )

        time.sleep(1.5)
        post_next_prediction()

        edit_admin_panel(
            chat_id, message_id,
            f"🟢 **PREDICTION RUNNING ({stats['wins']}/{TARGET_WINS})**\n"
            f"❌ Last: **LOSS** ➔ Next Level: **{multiplier}x**\n"
            f"🆔 Next: `#{stats['current_period'][-4:]}` (`{stats['last_size']}` | `{stats['last_nums'][0]}, {stats['last_nums'][1]}`)\n"
            f"🧠 Logic: `{stats['strategy_used']}` | Ratio: `{ratio}%`"
        )

@app.route('/')
def home():
    return "Golden Group Dynamic Sticker Bot is Active!"

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    upd = request.get_json(silent=True) or {}

    if "message" in upd and upd["message"].get("from", {}).get("id") == ADMIN_ID:
        txt = upd["message"].get("text", "")
        if txt.startswith("/start"):
            status_txt = f"🟢 RUNNING ({stats['wins']}/{TARGET_WINS})" if stats["active"] else "🔴 STOPPED"
            tg_send_msg(
                ADMIN_ID,
                f"🎛 **GOLDEN GROUP™ DYNAMIC STICKER PANEL ({status_txt})**\n"
                f"Har trade ke saath live #Period + BIG/SMALL + Numbers stickers banenge:",
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
            f"🎛 **GOLDEN GROUP™ DYNAMIC STICKER BOT READY!**\n"
            f"Har prediction ke saath live **#Period + BIG/SMALL + Dual Numbers**, **WIN 1–10**, aur **0–9 Number Win** stickers automatic banenge!\n"
            f"Shuru karne ke liye **START PREDICTION** dabayein:",
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
