# app.py
# This is a simple Telegram bot that uses the OpenAI Responses API to respond to user messages.
# It uses the python-telegram-bot library for Telegram bot functionality and the OpenAI Python client for API calls.
# Make sure to install the required libraries:
# pip install python-telegram-bot openai python-dotenv
# This program is develop for local testing with polling.

# Import necessary libraries
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

# Load environment variables from .env file
import dotenv
dotenv.load_dotenv()

# Load configuration from environment
TOKEN = os.environ["TELEGRAM_TOKEN"]
PORT = int(os.environ.get("PORT", "8443"))
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the OpenAI Responses API client
openai_client = OpenAI(api_key=OPENAI_API_KEY)  # :contentReference[oaicite:0]{index=0}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Hello! I'm your AI assistant. (polling)")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.text:
        user_text = update.message.text

        # Call the Responses API with a simple instruction
        response = openai_client.responses.create(
            model="gpt-4o",
            instructions="You are a helpful assistant. But you only answer anything related to Information Technology and AI",
            input=user_text,
        )
        await update.message.reply_text(response.output_text)

def main():
    # Build the bot application
    app = ApplicationBuilder().token(TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    
    logger.info("Bot is running with polling...")

    # Local testing with polling
    app.run_polling()

if __name__ == "__main__":
    main()

# this is a simple Telegram bot that uses the OpenAI Responses API to respond to user messages.
# It uses the python-telegram-bot library for Telegram bot functionality and the OpenAI Python client for API calls.
# We only use polling for local testing.
# To test webhook, you can use ngrok to expose your local server to the internet.
# Make sure to set the TELEGRAM_TOKEN and OPENAI_API_KEY environment variables before running the bot.