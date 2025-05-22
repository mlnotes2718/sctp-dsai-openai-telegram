# app.py

import os
import requests
from flask import Flask, request
import openai
from openai import OpenAI

# ─────── Configuration ───────
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
WEBHOOK_URL     = os.environ["WEBHOOK_URL"]  

# Set the base URL for the webhook
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# OpenAI API key
# Setup the OpenAI client
openai.api_key = OPENAI_API_KEY
client = OpenAI(api_key=openai.api_key)

# ─────── Flask App ───────
app = Flask(__name__)

@app.route("/", methods=["GET"])
def set_telegram_webhook():
    """Register or re-register your webhook on Telegram with no pending updates."""
    url = f"{TELEGRAM_API_URL}/setWebhook"
    payload = {
        "url": WEBHOOK_URL,
        "drop_pending_updates": True
    }
    response = requests.post(url, json=payload)
    print("Webhook set:", response.status_code, response.text)
    # Check if the webhook was set successfully
    if response.status_code == 200:
        return "Webhook set successfully.", response.status_code
    else:
        return f"Failed to set webhook: {response.text}", response.status_code




@app.route("/webhook", methods=["POST"])
def telegram_webhook():

    # Handle incoming updates from Telegram
    data = request.get_json(force=True)

    # Basic validation
    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"]["text"]

        # Call OpenAI ChatCompletion
        response = client.responses.create(
            model="gpt-4.1",
             input=[{"role": "user", "content": user_text}],
        )

        reply = response.output_text

        # Send reply via Telegram
        send_url = f"{TELEGRAM_API_URL}/sendMessage"
        payload = {"chat_id": chat_id, "text": reply}
        requests.post(send_url, json=payload)

    return "OK", 200


if __name__ == "__main__":
    # For local testing only; in production use Gunicorn
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
