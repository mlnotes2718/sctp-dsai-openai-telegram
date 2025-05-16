# webhook.py
# ─── webhook.py ────────────────────────────────────────────────────────────────
# This is a simple Telegram bot that uses OpenAI's Chat API to respond to messages.
# It sets up a webhook to receive messages and sends replies using the OpenAI API.
# The bot is designed to be deployed on Render.com, but can be adapted for other platforms.
# ─── Requirements ──────────────────────────────────────────────────────────────

import os
import logging
import asyncio

from flask import Flask, request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import openai
from openai import OpenAI 

# ─── Configuration ─────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL    = os.getenv("WEBHOOK_URL")    # e.g. "https://<your-app>.onrender.com/webhook"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o")

if not (TELEGRAM_TOKEN and WEBHOOK_URL and OPENAI_API_KEY):
    raise RuntimeError("Please set TELEGRAM_TOKEN, WEBHOOK_URL, and OPENAI_API_KEY")

# ─── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── Build the PTB Application ─────────────────────────────────────────────────
app = Flask(__name__)
application = (
    ApplicationBuilder()
    .token(TELEGRAM_TOKEN)
    .build()
)
openai.api_key = OPENAI_API_KEY
client = OpenAI(api_key=OPENAI_API_KEY)

# ─── Handlers ─────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi! Send me text and I'll reply via ChatGPT, or send a photo and I'll save it."
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logger.info(f"Text from {update.effective_user.id}: {user_text!r}")
    try:
        resp = await client.chat.completions.acreate(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": user_text}]
        )
        reply = resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error("OpenAI API error", exc_info=e)
        reply = "⚠️ Sorry, I couldn't process that. Please try again later."
    await update.message.reply_text(reply)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Photo from {update.effective_user.id}")
    photo = update.message.photo[-1]
    file = await photo.get_file()
    os.makedirs("downloads", exist_ok=True)
    path = os.path.join("downloads", f"{file.file_id}.jpg")
    await file.download_to_drive(path)
    await update.message.reply_text(f"✅ Saved image to `{path}`")

# register handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

# ─── Flask endpoint to receive Telegram updates ────────────────────────────────
@app.route("/webhook", methods=["POST"])
async def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.update_queue.put(update)
    return "OK", 200

# ─── Startup: register webhook and run ──────────────────────────────────────────
if __name__ == "__main__":
    # register webhook with Telegram
    asyncio.run(application.bot.set_webhook(WEBHOOK_URL))

    # for local testing; in production use an ASGI server (see below)
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
