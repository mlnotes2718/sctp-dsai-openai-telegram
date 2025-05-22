import os
import requests
from flask import Flask, request, jsonify
from openai import OpenAI
import logging

# ─────── Configuration ───────
TELEGRAM_TOKEN  = os.getenv("TELEGRAM_TOKEN", "")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
WEBHOOK_URL     = os.getenv("WEBHOOK_URL", "")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup the OpenAI client for the Responses API
client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)

# In-memory store for previous_response_id per chat (for multi-turn)
conversation_history = {}


def send_telegram_message(chat_id: int, text: str):
    """Helper to send a message back to Telegram."""
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    resp = requests.post(url, json=payload, timeout=5)
    resp.raise_for_status()
    logger.info("Sent message to %s", chat_id)


@app.route("/", methods=["GET"])
def home_status():
    """Show current webhook URL & status."""
    info = requests.get(f"{TELEGRAM_API_URL}/getWebhookInfo", timeout=5).json()
    if not info.get("ok"):
        return "Failed to fetch webhook info", 500
    r = info["result"]
    return jsonify(
        url=r.get("url"),
        pending_updates=r.get("pending_update_count"),
        last_error=r.get("last_error_message")
    ), 200


@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    """Register the Telegram webhook (drop any pending updates)."""
    resp = requests.post(
        f"{TELEGRAM_API_URL}/setWebhook",
        json={
            "url": WEBHOOK_URL,
            "drop_pending_updates": True
        },
        timeout=5
    )
    if resp.ok:
        logger.info("Webhook set successfully")
        return "Webhook set successfully.", 200
    logger.error("Error setting webhook: %s", resp.text)
    return f"Error setting webhook: {resp.text}", resp.status_code


@app.route("/webhook_status", methods=["GET"])
def webhook_status():
    """Check current webhook info."""
    info = requests.get(f"{TELEGRAM_API_URL}/getWebhookInfo", timeout=5).json()
    if info.get("ok"):
        url = info["result"].get("url", "<none>")
        last_error = info["result"].get("last_error_message")
        return jsonify(url=url, last_error=last_error), 200
    return "Unable to fetch webhook info", 500


@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    data = request.get_json(force=True)
    text    = data.get("message", {}).get("text")
    chat_id = data.get("message", {}).get("chat", {}).get("id")
    if not text or not chat_id:
        return "OK", 200

    api_kwargs = {"model": "gpt-4o-mini", "input": text}
    prev_id = conversation_history.get(chat_id)
    if prev_id:
        api_kwargs["previous_response_id"] = prev_id

    try:
        response = client.responses.create(**api_kwargs)
        reply = response.output_text
        conversation_history[chat_id] = response.id
    except Exception as e:
        logger.error("OpenAI Responses API error: %s", e)
        reply = "Sorry, something went wrong."

    try:
        send_telegram_message(chat_id, reply)
    except Exception as e:
        logger.error("Telegram send error: %s", e)

    return "OK", 200


if __name__ == "__main__":
    # Automatically register webhook on startup
    try:
        set_webhook()
    except Exception as e:
        logger.error("Failed to set webhook on startup: %s", e)

    # Local testing only; in production use Gunicorn
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))

