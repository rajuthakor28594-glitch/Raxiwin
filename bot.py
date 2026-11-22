import os
import re
import asyncio
import random
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import pytz
from telegram import Bot
from playwright.async_api import async_playwright

# --- Bot & Login Details ---
BOT_TOKEN = "9254738470:AAG85xqtnBcfFlpWX0_Eonq3p_iv8srpVlk"
CHANNEL_ID = "-1002395334740"
WIN_STICKER = "CAACAgUAAxkBAAEk11BrAxiWg-reLn36ILw5RH1v7kNr2wACohcAArwMgVfzyjUbYvTAxD0E"

RAXI_PHONE = "8320617764"
RAXI_PASSWORD = "8320617764"  # Suraksha ke liye apna naya password yahan dalein

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Raxi Win 1Min Playwright Bot is Live!")
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
browser_page = None

def get_current_wingo_1min_period():
    now_ist = datetime.now(IST)
    now_utc = datetime.now(UTC)
    date_str = now_ist.strftime("%Y%m%d")
    total_minutes = now_utc.hour * 60 + now_utc.minute
    round_number = total_minutes + 1
    period_id = f"{date_str}10001{round_number:04d}"
    return period_id, now_utc.second

async def init_browser():
    """Raxi Win mein auto-login karke WinGo 1Min page kholta hai"""
    global browser_page
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage"]
    )
    context = await browser.new_context(
        viewport={"width": 390, "height": 844},
        user_agent="Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
    )
    page = await context.new_page()
    try:
        print("Raxi Win login page khol raha hai...", flush=True)
        await page.goto("https://www.raxi4.com/#/login", timeout=60000)
        await page.wait_for_timeout(4000)

        # Phone aur Password inputs bharna
        inputs = page.locator("input")
        count = await inputs.count()
        for i in range(count):
            inp = inputs.nth(i)
            inp_type = await inp.get_attribute("type") or ""
            placeholder = (await inp.get_attribute("placeholder") or "").lower()
            if inp_type == "password" or "password" in placeholder:
                await inp.fill(RAXI_PASSWORD)
            elif inp_type in ["text", "tel", "number"] or "phone" in placeholder or "number" in placeholder:
                await inp.fill(RAXI_PHONE)

        await page.wait_for_timeout(1000)
        # Login button dabana
        login_btn = page.locator("button:has-text('Log in'), button:has-text('Login'), .login-btn").first
        if await login_btn.count() > 0:
            await login_btn.click()
        else:
            await page.keyboard.press("Enter")

        await page.wait_for_timeout(5000)
        # Seedhe WinGo 1Min game page par jana
        await page.goto("https://www.raxi4.com/#/saasLottery/WinGo?gameCode=WinGo_1M&lottery=WinGo", timeout=60000)
        await page.wait_for_timeout(4000)
        browser_page = page
        print("Browser login aur WinGo 1Min page ready hai!", flush=True)
    except Exception as e:
        print("Browser setup error:", e, flush=True)

async def fetch_result_from_page(target_period):
    """Khule hue webpage ke Game History text se period ka result nikalta hai"""
    global browser_page
    if not browser_page:
        return None
    try:
        body_text = await browser_page.inner_text("body")
        # Period number ke aas-paas Big ya Small dhundhna
        pattern = rf"{target_period}[\s\S]{{0,60}}?(Big|Small)"
        match = re.search(pattern, body_text, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    except Exception as e:
        print("Page read error:", e, flush=True)
    return None

async def check_result_and_send_sticker(period_id, pred_choice):
    global level_index
    await asyncio.sleep(62)

    actual_result = None
    for _ in range(4):
        actual_result = await fetch_result_from_page(period_id)
        if actual_result:
            break
        await asyncio.sleep(2)

    if actual_result == pred_choice:
        try:
            await bot.send_sticker(chat_id=CHANNEL_ID, sticker=WIN_STICKER)
            print(f"WIN! Sticker sent for {period_id}", flush=True)
        except Exception as e:
            print("Sticker error:", e, flush=True)
        level_index = 0
    elif actual_result is not None:
        level_index = (level_index + 1) % len(LEVELS)
        print(f"LOSS for {period_id} (Actual: {actual_result}). Next level: {LEVELS[level_index]}x", flush=True)
    else:
        print(f"Page se result nahi mila for {period_id}", flush=True)

async def start_bot():
    await init_browser()
    last_period = ""
    print("Raxi Win 1-Min 24x7 Smart Bot chalu ho gaya hai...", flush=True)

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
