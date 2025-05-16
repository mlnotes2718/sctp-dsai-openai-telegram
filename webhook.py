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
from asgiref.wsgi import WsgiToAsgi

# ─── Configuration ─────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL    = os.getenv("WEBHOOK_URL")    # e.g. "https://your-app.onrender.com/webhook"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

# sanity check
if not (TELEGRAM_TOKEN and WEBHOOK_URL and OPENAI_API_KEY):
    raise RuntimeError("Please set TELEGRAM_TOKEN, WEBHOOK_URL, and OPENAI_API_KEY")

# ─── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── Build your Flask app and PTB Application ─────────────────────────────────
sync_app = Flask(__name__)

application = (
    ApplicationBuilder()
    .token(TELEGRAM_TOKEN)
    .build()
)
openai.api_key = OPENAI_API_KEY
client = OpenAI(api_key=OPENAI_API_KEY)


# ─── Bot Handlers ──────────────────────────────────────────────────────────────
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
            messages=[{"role": "user", "content": user_text}],
        )
        reply = resp.choices[0].message.content.strip()
    except Exception:
        logger.exception("OpenAI error")
        reply = "⚠️ Sorry, I couldn't process that right now."
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
application.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
)
application.add_handler(MessageHandler(filters.PHOTO, handle_photo))


# ─── One‐time startup: initialize, start, and set webhook ─────────────────────
@sync_app.before_first_request
def _setup_bot():
    loop = asyncio.get_event_loop()
    # these three must be awaited once at startup
    loop.create_task(application.initialize())
    loop.create_task(application.start())
    loop.create_task(application.bot.set_webhook(WEBHOOK_URL))
    logger.info("🐳 Bot initialized and webhook set")


# ─── Webhook route (sync) ─────────────────────────────────────────────────────
@sync_app.route("/webhook", methods=["POST"])
def telegram_webhook():
    """Receive updates from Telegram, dispatch into PTB's queue."""
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    # schedule PTB to handle it asynchronously
    asyncio.get_event_loop().create_task(application.process_update(update))
    return "OK", 200


# ─── Wrap Flask as ASGI ────────────────────────────────────────────────────────
# Hypercorn (or Uvicorn) can now serve this ASGI app:
app = WsgiToAsgi(flask_app)
