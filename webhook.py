# webhook.py
# ─── webhook.py ────────────────────────────────────────────────────────────────
# This is a simple Telegram bot that uses OpenAI's Chat API to respond to messages.
# It sets up a webhook to receive messages and sends replies using the OpenAI API.
# The bot is designed to be deployed on Render.com, but can be adapted for other platforms.
# ─── Requirements ──────────────────────────────────────────────────────────────
import os
import logging
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext
import openai
from openai import OpenAI

# ─── Configuration ─────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL    = os.getenv("WEBHOOK_URL")    # e.g. "https://<your-app>.onrender.com/webhook"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o")

client = OpenAI(api_key=OPENAI_API_KEY)

if not TELEGRAM_TOKEN or not WEBHOOK_URL or not OPENAI_API_KEY:
    raise RuntimeError("Missing one of TELEGRAM_TOKEN, WEBHOOK_URL, or OPENAI_API_KEY")

# set up bots & clients
bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot, None, use_context=True, workers=0)
openai.api_key = OPENAI_API_KEY

# ─── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ─── Handlers ─────────────────────────────────────────────────────────────────
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "👋 Hi! Send me text and I’ll reply via ChatGPT, or send a photo and I’ll save it."
    )

def handle_text(update: Update, context: CallbackContext):
    user_text = update.message.text
    logger.info(f"Received text from {update.effective_user.id}: {user_text!r}")

    # Call OpenAI ChatCompletion
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": user_text}]
        )
        reply = resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error("OpenAI API error", exc_info=e)
        reply = "⚠️ Sorry, I couldn’t process that. Please try again later."

    update.message.reply_text(reply)

def handle_photo(update: Update, context: CallbackContext):
    logger.info(f"Received photo from {update.effective_user.id}")
    # pick highest resolution
    photo = update.message.photo[-1]
    file = photo.get_file()
    os.makedirs("downloads", exist_ok=True)
    local_path = os.path.join("downloads", f"{file.file_id}.jpg")
    file.download(custom_path=local_path)
    update.message.reply_text(f"✅ Image saved to `{local_path}`", quote=False)


# register handlers
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
dispatcher.add_handler(MessageHandler(Filters.photo, handle_photo))


# ─── Flask App ────────────────────────────────────────────────────────────────
app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK", 200


# ─── Startup ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Register webhook with Telegram
    success = bot.set_webhook(WEBHOOK_URL)
    if not success:
        logger.error("Failed to set webhook")
        raise RuntimeError("Webhook setup failed")

    # Start Flask (Render.com will bind to $PORT)
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
