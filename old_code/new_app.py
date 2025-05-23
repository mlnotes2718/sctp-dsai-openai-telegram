import os
import logging
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# ─────── Configuration ───────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
WEBHOOK_URL    = os.getenv("WEBHOOK_URL", "")  # e.g. https://your-domain.com/<token>

# ───── Logging ─────
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ───── OpenAI Client ─────
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ───── Handlers ─────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.effective_chat.id

    # Call OpenAI Responses API
    try:
        response = openai_client.responses.create(
            model="gpt-4o-mini",
            input=text,
            # Optionally pass previous_response_id from context.bot_data
            previous_response_id=context.bot_data.get(str(chat_id))
        )
        reply = response.output_text
        # store for multi-turn
        context.bot_data[str(chat_id)] = response.id
    except Exception as e:
        logger.error("OpenAI API error: %s", e)
        reply = "Sorry, something went wrong."

    await update.message.reply_text(reply)

# ───── Main ─────
def main():
    if not TELEGRAM_TOKEN or not OPENAI_API_KEY or not WEBHOOK_URL:
        logger.error(
            "Missing environment variables: TELEGRAM_TOKEN, OPENAI_API_KEY, or WEBHOOK_URL"
        )
        return

    # Build the Telegram bot application
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    # In-memory store for response IDs per chat for context
    app.bot_data = {}

    # Register handler for plain-text messages (ignoring commands)
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Determine webhook path
    webhook_path = f"/{TELEGRAM_TOKEN}"

    # Start webhook with dropping any pending updates
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        url_path=TELEGRAM_TOKEN,
        webhook_url=f"{WEBHOOK_URL}{webhook_path}",
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()
