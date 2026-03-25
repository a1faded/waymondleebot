import os
import logging
import aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ---- Configuration from environment variables ----
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_KEY = os.environ.get("API_KEY")
API_BASE_URL = os.environ.get("API_BASE_URL", "https://ucheck.pro/api_v1/")

if not BOT_TOKEN or not API_KEY:
    raise Exception("Missing environment variables: BOT_TOKEN, API_KEY")

# ---- Logging ----
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# ---- API Client ----
async def api_request(params: dict) -> dict:
    params["key"] = API_KEY
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(API_BASE_URL, params=params, timeout=10) as resp:
                return await resp.json()
        except Exception as e:
            logger.error(f"API request failed: {e}")
            return {"type": "error", "data": {"message": "Network error or API unavailable"}}

# ---- Handlers ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to the Card Checker Bot!\n\n"
        "Commands:\n"
        "/balance - Check your account balance\n"
        "/check <cc> <expm> <expy> <cvc> [address] [zip] - Check a card\n"
        "  Example: /check 4111111111111111 05 2029 456\n"
        "  With AVS: /check 4111111111111111 05 2029 456 \"7 Colonial Drive\" 12345\n"
        "  Note: Use quotes if address contains spaces.\n"
        "/help - Show this message"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    params = {"task": "balance"}
    result = await api_request(params)
    if result.get("type") == "success":
        balance = result["data"]["balance"]
        await update.message.reply_text(f"💰 Balance: {balance}")
    else:
        error = result.get("data", {}).get("message", "Unknown error")
        await update.message.reply_text(f"❌ Error: {error}")

async def check_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 4:
        await update.message.reply_text(
            "Usage: /check <cc> <expm> <expy> <cvc> [address] [zip]\n"
            "Example: /check 4111111111111111 05 2029 456"
        )
        return

    cc, expm, expy, cvc = args[0], args[1], args[2], args[3]
    address, zipcode = None, None
    if len(args) >= 6:
        address = args[4]
        zipcode = args[5]
    elif len(args) == 5:
        address = args[4]

    params = {
        "task": "check",
        "num": cc,
        "expm": expm,
        "expy": expy,
        "cvc": cvc,
    }
    if address:
        params["address"] = address
    if zipcode:
        params["zip"] = zipcode

    result = await api_request(params)

    if result.get("type") == "success":
        data = result["data"]
        check = data["check"]
        valid = check["valid"]
        result_text = check["result"]
        new_balance = data.get("new_balance", "N/A")
        status = "✅ Valid" if valid == 1 else "❌ Invalid"
        msg = (f"Card: {cc[:4]}...{cc[-4:]}\n"
               f"Status: {status}\n"
               f"Result: {result_text}\n"
               f"New balance: {new_balance}")
        await update.message.reply_text(msg)
    else:
        error = result.get("data", {}).get("message", "Unknown error")
        await update.message.reply_text(f"❌ Error: {error}")

# ---- Main ----
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("check", check_card))
    app.run_polling()

if __name__ == "__main__":
    main()
