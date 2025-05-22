# telegram_webhook_app.py
# A simple Flask application to receive Telegram updates via webhook
# Uses only Flask and requests. Deploy with Gunicorn.

import os
from flask import Flask, request
import requests

# Configuration via environment variables
TOKEN = os.getenv("TELEGRAM_TOKEN")  # Telegram bot token
APP_URL = os.getenv("APP_URL")        # Public URL where this app is hosted (e.g., https://your-domain.com)
PORT = int(os.environ.get("PORT", 5000))

if not TOKEN or not APP_URL:
    raise RuntimeError("Environment variables TELEGRAM_TOKEN and APP_URL must be set.")

# Construct webhook path and full URL\ nWEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"{APP_URL}{WEBHOOK_PATH}"

app = Flask(__name__)


def set_webhook():
    """
    Sets the Telegram webhook with drop_pending_updates=True to clear any backlog.
    """
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    params = {
        "url": WEBHOOK_URL,
        "drop_pending_updates": True
    }
    resp = requests.get(url, params=params)
    result = resp.json()
    if resp.status_code == 200 and result.get("ok"):
        print(f"[INFO] Webhook set to {WEBHOOK_URL}")
    else:
        print(f"[ERROR] Failed to set webhook: {result}")


@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    """
    Handler for incoming Telegram updates.
    Echoes back received text messages.
    """
    update = request.get_json(force=True)
    # Basic validation
    message = update.get("message")
    if not message:
        return {"ok": True}

    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    # Echo the message back\ n    send_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": f"You said: {text}"  # Simple echo
    }
    requests.post(send_url, json=payload)
    return {"ok": True}


if __name__ == "__main__":
    # Set webhook on startup
    set_webhook()
    # Start Flask development server (not for production)
    app.run(host="0.0.0.0", port=PORT)
