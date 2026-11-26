import asyncio
import datetime
import os
import random
import threading
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

# ================= CONFIGURATION =================
BOT_TOKEN = "9254738470:AAG85xqtnBcfFlpWX0_Eonq3p_iv8srpVlk"
CHANNEL_ID = "-1002395334740"
ADMIN_ID = 5393186266  # Sirf aapki ID par buttons kaam karenge

# Aapke Telegram Stickers ki File IDs
WIN_STICKER_ID = "CAACAgUAAxkBAAEk9DBrB-J7q40-uSyXaeY4QbFSWBMuKwACMRUAAsA16FeZI-wzeGAu_T0E"
LOSS_3X_STICKER_ID = "CAACAgUAAxkBAAEk9ChrB-IpRe3b0bdmmApGZoRKD55tRQACTwMAAk5qkVTbERf7V1MOtD0E"

TARGET_WINS = 10
REGISTER_LINK = "https://www.raxiwin.game/#/register?invitationCode=51966105844"
# =================================================

app = Flask(__name__)

@app.route('/')
def home():
    return "Raxi Win 1-Min Admin Control Bot is Running!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

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

def get_admin_keyboard():
    next_mult = 3 ** stats["current_level"]
    if stats["active"]:
        keyboard = [
            [
                InlineKeyboardButton(f"✅ WIN ({stats['wins'] + 1}/{TARGET_WINS})", callback_data="mark_win"),
                InlineKeyboardButton(f"❌ LOSS ({next_mult}X)", callback_data="mark_loss")
            ],
            [
                InlineKeyboardButton("🛑 STOP PREDICTION", callback_data="stop_session")
            ]
        ]
    else:
        keyboard = [
            [
                InlineKeyboardButton("▶️ START PREDICTION (0/10)", callback_data="start_session")
            ]
        ]
    return InlineKeyboardMarkup(keyboard)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("Sirf Admin hi button daba sakta hai!", show_alert=True)
        return

    await query.answer()
    action = query.data
    period_short = stats["current_period"][-4:] if stats["current_period"] else "----"

    if action == "start_session":
        stats["active"] = True
        stats["wins"] = 0
        stats["losses"] = 0
        stats["total_rounds"] = 0
        stats["current_level"] = 1

        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=(
                f"🔥 **RAXI WIN - WINGO 1 MIN STARTED!** 🔥\n"
                f"🎯 **Session Target:** `0/{TARGET_WINS} Wins`\n"
                f"🔗 **Register:** [Click Here to Join]({REGISTER_LINK})"
            ),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )

        await query.edit_message_text(
            text=(
                f"🟢 **PREDICTION RUNNING (0/{TARGET_WINS})**\n"
                f"Agli win par `1/{TARGET_WINS}` ho jayega:"
            ),
            reply_markup=get_admin_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

    elif action == "stop_session":
        stats["active"] = False
        ratio = calculate_ratio()

        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=(
                f"🛑 **PREDICTION SESSION STOPPED!**\n"
                f"🏆 **Total Wins:** `{stats['wins']}/{TARGET_WINS}`\n"
                f"📈 **Final Achieving Ratio:** `{ratio}%` ({stats['wins']}W / {stats['losses']}L)\n"
                f"Agle session ke liye ready rahein!"
            ),
            parse_mode=ParseMode.MARKDOWN
        )

        await query.edit_message_text(
            text=(
                f"🔴 **PREDICTION STOPPED ({stats['wins']}/{TARGET_WINS})**\n"
                f"📊 Last Session Ratio: `{ratio}%`\n"
                f"Naya session `0/10` se shuru karne ke liye **START** dabayein:"
            ),
            reply_markup=get_admin_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

    elif action == "mark_win":
        if not stats["active"]:
            await query.edit_message_text(
                "🔴 Prediction abhi band hai. Pehle START dabayein:",
                reply_markup=get_admin_keyboard()
            )
            return

        prev_wins = stats["wins"]
        stats["total_rounds"] += 1
        stats["wins"] += 1
        stats["current_level"] = 1
        stats["history"].append(stats["last_size"])
        ratio = calculate_ratio()

        # 1. Sabse pehle Win Sticker bhejein
        await context.bot.send_sticker(chat_id=CHANNEL_ID, sticker=WIN_STICKER_ID)
        
        # 2. Text mein 0/10 -> 1/10 -> 2/10... progression aur Ratio bhejein
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=(
                f"🏆 **WINNING TARGET: {prev_wins}/{TARGET_WINS} ➔ {stats['wins']}/{TARGET_WINS}** ✅\n"
                f"🆔 Period: `{period_short}` | Result: **{stats['last_size']}** PASS\n"
                f"📊 **Achieving Ratio:** `{ratio}%` ({stats['wins']}W / {stats['losses']}L)"
            ),
            parse_mode=ParseMode.MARKDOWN
        )

        # 10/10 Wins poori hote hi Auto-Stop
        if stats["wins"] >= TARGET_WINS:
            stats["active"] = False
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=(
                    f"🎉 **TARGET COMPLETE ({TARGET_WINS}/{TARGET_WINS} WINS)!** 🎉\n"
                    f"🛑 Session yahan successfully stop kiya ja raha hai.\n"
                    f"📈 **Final Achieving Ratio:** `{ratio}%` ({stats['wins']}W / {stats['losses']}L)\n"
                    f"Agle session ke liye ready rahein!"
                ),
                parse_mode=ParseMode.MARKDOWN
            )
            await query.edit_message_text(
                text=(
                    f"🏆 **10/10 WINS COMPLETE! AUTO-STOPPED**\n"
                    f"📈 Final Ratio: `{ratio}%`\n"
                    f"Naya session `0/10` se shuru karne ke liye START dabayein:"
                ),
                reply_markup=get_admin_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
            return

        await query.edit_message_text(
            text=(
                f"🟢 **PREDICTION RUNNING ({stats['wins']}/{TARGET_WINS})**\n"
                f"✅ Progress: `{prev_wins}/{TARGET_WINS} ➔ {stats['wins']}/{TARGET_WINS}`\n"
                f"🆔 Period: `{stats['current_period']}` | Ratio: `{ratio}%`"
            ),
            reply_markup=get_admin_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

    elif action == "mark_loss":
        if not stats["active"]:
            await query.edit_message_text(
                "🔴 Prediction abhi band hai. Pehle START dabayein:",
                reply_markup=get_admin_keyboard()
            )
            return

        stats["total_rounds"] += 1
        stats["losses"] += 1
        stats["current_level"] += 1
        opp_size = "SMALL" if stats["last_size"] == "BIG" else "BIG"
        stats["history"].append(opp_size)
        multiplier = 3 ** (stats["current_level"] - 1)
        ratio = calculate_ratio()

        # 3X Loss Sticker aur Alert bhejein
        await context.bot.send_sticker(chat_id=CHANNEL_ID, sticker=LOSS_3X_STICKER_ID)
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=(
                f"❌ **LOSS** | Period: `{period_short}` | Wins: `{stats['wins']}/{TARGET_WINS}`\n"
                f"⚠️ **Agle Round mein {multiplier}x Fund lagayein!**\n"
                f"📊 **Current Ratio:** `{ratio}%` ({stats['wins']}W / {stats['losses']}L)"
            ),
            parse_mode=ParseMode.MARKDOWN
        )

        await query.edit_message_text(
            text=(
                f"🟢 **PREDICTION RUNNING ({stats['wins']}/{TARGET_WINS})**\n"
                f"❌ Last: **LOSS** (Agla Round: **{multiplier}x**)\n"
                f"🆔 Period: `{stats['current_period']}` | Ratio: `{ratio}%`"
            ),
            reply_markup=get_admin_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        status_text = f"🟢 RUNNING ({stats['wins']}/{TARGET_WINS})" if stats["active"] else "🔴 STOPPED (0/10)"
        await update.message.reply_text(
            f"🎛 **RAXI WIN CONTROL PANEL ({status_text})**\nNiche buttons se Prediction Start/Stop aur Win/Loss control karein:",
            reply_markup=get_admin_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

async def prediction_worker(app_bot):
    last_predicted_period = None

    try:
        await app_bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"🎛 **RAXI WIN CONTROL PANEL READY!**\n"
                f"Session `0/{TARGET_WINS}` se shuru karne ke liye niche **START PREDICTION** dabayein:"
            ),
            reply_markup=get_admin_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        print(f"Admin message error: {e}")

    while True:
        if stats["active"]:
            now = get_ist_now()
            current_period = get_raxi_period_number(now)

            if current_period != last_predicted_period:
                last_predicted_period = current_period
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
                await app_bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=pred_msg,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )
        else:
            last_predicted_period = None

        await asyncio.sleep(2)

async def post_init(application: Application):
    asyncio.create_task(prediction_worker(application.bot))

def main():
    threading.Thread(target=run_web, daemon=True).start()
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
