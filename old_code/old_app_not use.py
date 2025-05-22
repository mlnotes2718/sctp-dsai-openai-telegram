# app.py

# This is a simple Flask application that serves as a Telegram bot
# and integrates with OpenAI's ChatGPT API.
# It listens for incoming messages from Telegram, processes them using
# the OpenAI API, and sends the responses back to the Telegram chat.
# Requirements:
# - Flask
# - requests
# - python-dotenv (for loading environment variables)
# Install the required packages:
# pip install Flask requests python-dotenv
# Make sure to set the following environment variables:
# - TELEGRAM_TOKEN: Your Telegram bot token
# - OPENAI_API_KEY: Your OpenAI API key
# - WEBHOOK_URL: The URL where your app is hosted (e.g., https://<your-app>.onrender.com)
# - PORT: The port on which your app will run (default is 5000)
# Example usage:
# 1. Set the environment variables in a .env file or your environment.
# 2. Run the app: python app.py

# import necessary libraries
import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # e.g., https://<your-app>.onrender.com
PORT = int(os.getenv("PORT", 5000))

# API endpoints
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

# Send a message back to Telegram

def send_telegram_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    resp = requests.post(url, json=payload)
    resp.raise_for_status()

# Query ChatGPT via OpenAI API

def generate_chatgpt_response(user_message):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": user_message}
        ]
    }
    response = requests.post(OPENAI_API_URL, headers=headers, json=data)
    response.raise_for_status()
    result = response.json()
    return result["choices"][0]["message"]["content"]

# Endpoint to receive updates from Telegram

@app.route(f"/webhook/{TELEGRAM_TOKEN}", methods=["POST"])
def telegram_webhook():
    update = request.get_json()
    if "message" in update:
        chat = update["message"]["chat"]
        chat_id = chat["id"]
        text = update["message"].get("text")
        if text:
            reply = generate_chatgpt_response(text)
            send_telegram_message(chat_id, reply)
    return jsonify({"ok": True})

# Optional route to set Telegram webhook and drop pending updates

@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    url = f"{TELEGRAM_API_URL}/setWebhook"
    webhook_endpoint = f"{WEBHOOK_URL}/webhook/{TELEGRAM_TOKEN}"
    resp = requests.post(url, json={
        "url": webhook_endpoint,
        "drop_pending_updates": True
    })
    return jsonify(resp.json())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
