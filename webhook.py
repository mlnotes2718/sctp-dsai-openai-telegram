# webhook.py
# ─── webhook.py ────────────────────────────────────────────────────────────────
# This is a simple Telegram bot that uses OpenAI's Chat API to respond to messages.
# It sets up a webhook to receive messages and sends replies using the OpenAI API.
# The bot is designed to be deployed on Render.com, but can be adapted for other platforms.
# ─── Requirements ──────────────────────────────────────────────────────────────

import os
import logging
from openai import OpenAI
from fastapi import FastAPI, Request
from telegram import Bot, Update
from telegram.ext import ContextTypes

# --- Configuration ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # e.g. https://<your-render-app>.onrender.com/webhook

# --- Clients ---
bot = Bot(token=TELEGRAM_TOKEN)
app = FastAPI()

openai.api_key = OPENAI_API_KEY
client = OpenAI(api_key=OPENAI_API_KEY)
# --- Logging ---
logging.basicConfig(level=logging.INFO)


async def query_chatgpt(prompt: str) -> str:
    resp = await client.chat.completions.acreate(
        model="gpt-3.5-turbo",
        messages=[{"role":"user", "content": prompt}]
    )
    return resp.choices[0].message.content.strip()


@app.on_event("startup")
async def on_startup():
    # register webhook with Telegram
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)


@app.post("/webhook")
async def receive_update(req: Request):
    data = await req.json()
    update = Update.de_json(data, bot)

    if update.message and update.message.text:
        user_text = update.message.text
        logging.info(f"Received message: {user_text!r}")
        reply = await query_chatgpt(user_text)
        await bot.send_message(chat_id=update.effective_chat.id, text=reply)

    return {"ok": True}


@app.get("/")  # health check
async def health():
    return {"status": "ok"}
