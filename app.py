import os
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from openai import OpenAI

# Load configuration from environment
TOKEN = os.environ["TELEGRAM_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]  # e.g. "https://your.domain/webhook"
PORT = int(os.environ.get("PORT", "8443"))
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the OpenAI Responses API client
openai_client = OpenAI(api_key=OPENAI_API_KEY)  # :contentReference[oaicite:0]{index=0}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("👋 Hello! I'm your AI assistant.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.text:
        user_text = update.message.text

        # Call the Responses API with a simple instruction
        response = openai_client.responses.create(
            model="gpt-4o",
            instructions="You are a helpful assistant.",
            input=user_text,
        )
        await update.message.reply_text(response.output_text)

def main():
    # Build the bot application
    app = ApplicationBuilder().token(TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the webhook listener, dropping any pending updates on startup
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}",
        drop_pending_updates=True,  # :contentReference[oaicite:1]{index=1}
    )

if __name__ == "__main__":
    main()
