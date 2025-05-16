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
from asgiref.wsgi import WsgiToAsgi

# ─── Configuration ─────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL    = os.getenv("WEBHOOK_URL")    # e.g. "https://<your-service>.onrender.com/webhook"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

if not (TELEGRAM_TOKEN and WEBHOOK_URL and OPENAI_API_KEY):
    raise RuntimeError("Please set TELEGRAM_TOKEN, WEBHOOK_URL & OPENAI_API_KEY")

# ─── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── 1) Build the *synchronous* Flask app ──────────────────────────────────────
sync_app = Flask(__name__)

# ─── 2) Build your PTB Application (v20, async) ────────────────────────────────
application = (
    ApplicationBuilder()
    .token(TELEGRAM_TOKEN)
    .build()
)
openai.api_key = OPENAI_API_KEY

# ─── 3) Register your async handlers ───────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! Send me text or a photo.")

async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    logger.info(f"Text from {update.effective_user.id}: {user_text!r}")
    try:
        resp = await openai.ChatCompletion.acreate(
            model=OPENAI_MODEL,
            messages=[{"role":"user","content":user_text}]
        )
        reply = resp.choices[0].message.content.strip()
    except Exception:
        logger.exception("OpenAI error")
        reply = "⚠️ Sorry, something went wrong."
    await update.message.reply_text(reply)

async def handle_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Photo from {update.effective_user.id}")
    photo = update.message.photo[-1]
    file = await photo.get_file()
    os.makedirs("downloads", exist_ok=True)
    path = os.path.join("downloads", f"{file.file_id}.jpg")
    await file.download_to_drive(path)
    await update.message.reply_text(f"✅ Saved image to `{path}`")

application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
application.add_handler(MessageHandler(filters.PHOTO, handle_photo))


# ─── 4) Flask hooks on *sync_app* ───────────────────────────────────────────────

@sync_app.before_first_request
def _startup():
    """
    This runs once, before Flask handles the very first request.
    We use it to spin up the PTB Application and register the webhook.
    """
    loop = asyncio.get_event_loop()
    # schedule the coroutines on Flask’s event loop (which Hypercorn/Uvicorn will drive)
    loop.create_task(application.initialize())
    loop.create_task(application.start())
    loop.create_task(application.bot.set_webhook(WEBHOOK_URL))
    logger.info("🤖 Bot started and webhook registered")

@sync_app.route("/webhook", methods=["POST"])
def telegram_webhook():
    """
    Synchronous Flask view that simply enqueues the update to PTB.
    """
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    # schedule the async handler
    asyncio.get_event_loop().create_task(application.process_update(update))
    return "", 200


# ─── 5) Wrap Flask as ASGI for Hypercorn/Uvicorn ──────────────────────────────
app = WsgiToAsgi(sync_app)
