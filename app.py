# app.py

import os
import yaml
from dotenv import load_dotenv
import logging

from flask import Flask, request, jsonify
import requests
from openai import OpenAI

# ------------------------------------------------------------------------------
# Environment & Configuration
# ------------------------------------------------------------------------------

# Load environment variables from a .env file into os.environ
load_dotenv()

# Configure global logging settings
logging.basicConfig(
    level=logging.INFO,  # Capture INFO-level and above
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)  # Logger for this module

# Load YAML configuration (e.g. webhook URL, model name, system prompt)
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# ------------------------------------------------------------------------------
# Telegram & OpenAI Settings
# ------------------------------------------------------------------------------

# Telegram Bot API token from environment
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
# Webhook URL to which Telegram will send updates
WEBHOOK_URL = config['telegram']['webhook_url']

# OpenAI API key from environment
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
# Model name to use (e.g., "gpt-4o-mini") from config
MODEL = config['openai']['model']

# System prompt that frames all user interactions, loaded from config
SYSTEM_PROMPT = config['system_prompt']

# Initialize OpenAI client instance
client = OpenAI(api_key=OPENAI_API_KEY)

# ------------------------------------------------------------------------------
# Flask App & Telegram Webhook Handler
# ------------------------------------------------------------------------------

app = Flask(__name__)

@app.route('/webhook_telegram', methods=['POST'])
def webhook_telegram():
    """
    Endpoint that Telegram calls whenever the bot receives a new message.
    """
    data = request.get_json()
    logger.info('Received update: %s', data)

    # Only process if it's a message (ignore e.g., edits, callbacks)
    if 'message' in data:
        chat_id   = data['message']['chat']['id']   # Unique ID for this chat
        user_text = data['message']['text']         # Text that the user sent
        logger.info('Chat %s says: %s', chat_id, user_text)

        # Call OpenAI's Chat Completions API with system + user messages
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_text}
            ]
        )
        # Extract the assistant’s reply text
        reply = response.choices[0].message.content
        logger.info('OpenAI reply: %s', reply)

        # Send that reply back to the user via Telegram
        send_url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
        payload = {
            'chat_id': chat_id,
            'text': reply
        }
        resp = requests.post(send_url, json=payload)
        if resp.status_code != 200:
            # Log errors if Telegram API call fails
            logger.error('Failed to send message: %s - %s', resp.status_code, resp.text)
        else:
            logger.info('Message sent successfully to chat %s', chat_id)

        # Acknowledge receipt of the webhook to Telegram
        return jsonify({'status': 'ok'})

    # If it's not a message update, simply return the Flask app (no action)
    return '', 200

# ------------------------------------------------------------------------------
# App Startup: Webhook Management & Server Launch
# ------------------------------------------------------------------------------

if __name__ == '__main__':
    
    logger.info('Starting Telegram Bot with OpenAI integration...')

    # Ensure TELEGRAM_TOKEN and WEBHOOK_URL are set
    if not TELEGRAM_TOKEN or not WEBHOOK_URL:
        logger.error('TELEGRAM_TOKEN and WEBHOOK_URL must be set in the environment or config.yaml')
        exit(1)
    
    # Ensure OPENAI_API_KEY is set
    if not OPENAI_API_KEY:
        logger.error('OPENAI_API_KEY must be set in the environment')
        exit(1)
    logger.info('Using OpenAI model: %s', MODEL)
    logger.info('Using Telegram webhook URL: %s', WEBHOOK_URL)
    logger.info('Using system prompt: %s', SYSTEM_PROMPT)
    
    # On startup, remove any existing webhook to clear pending updates
    delete_webhook_url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteWebhook'
    response = requests.post(
        delete_webhook_url,
        json={'url': WEBHOOK_URL, 'drop_pending_updates': True}
    )
    if response.status_code == 200:
        logger.info('Previous Webhook %s removed', WEBHOOK_URL)
    else:
        logger.error('Failed to remove webhook: %s - %s', response.status_code, response.text)

    # Then set the new webhook so Telegram knows where to send updates
    set_webhook_url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook'
    response = requests.post(set_webhook_url, json={'url': WEBHOOK_URL})
    if response.status_code == 200:
        logger.info('Webhook set successfully to %s', WEBHOOK_URL)
    else:
        logger.error('Failed to set webhook: %s - %s', response.status_code, response.text)

    # Finally, start the Flask development server (or use Gunicorn in production)
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

# Note: In production, consider using Gunicorn or another WSGI server instead of Flask's built-in server.
# This is a simple Flask app that handles Telegram messages and responds using OpenAI's API.
