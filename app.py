# app.py

import os
import yaml
from dotenv import load_dotenv
import logging

from flask import Flask, request, jsonify
import requests
from openai import OpenAI

# Load environment variables from .env
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Load configuration from YAML
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Telegram settings
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN') 
WEBHOOK_URL = config['telegram']['webhook_url']

# OpenAI settings
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY') 
MODEL = config['openai']['model']

# System prompt loaded from config
SYSTEM_PROMPT = config['system_prompt']

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Initialize Flask app
app = Flask(__name__)

# Telegram webhook endpoint
@app.route('/webhook_telegram', methods=['POST'])
def webhook_telegram():
    data = request.get_json()
    logger.info('Received update: %s', data)

    if 'message' in data:
        chat_id = data['message']['chat']['id']
        user_text = data['message']['text']
        logger.info('Chat %s says: %s', chat_id, user_text)

        # Call OpenAI Chat Completions API
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_text}
            ]
        )
        reply = response.choices[0].message.content
        logger.info('OpenAI reply: %s', reply)

        # Send reply back to Telegram
        send_url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
        payload = {
            'chat_id': chat_id,
            'text': reply
        }
        response = requests.post(send_url, json=payload)
        if response.status_code != 200:
            logger.error('Failed to send message: %s - %s', response.status_code, response.text)
        else:
            logger.info('Message sent successfully to chat %s', chat_id)

        return jsonify({'status': 'ok'})

    return app


if __name__ == '__main__':

    # Delete any previous Telegram webhook on startup
    delete_webhook_url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteWebhook'
    response = requests.post(delete_webhook_url, json={'url': WEBHOOK_URL, 'drop_pending_updates': True})
    if response.status_code == 200:
        logger.info('Previous Webhook %s removed', WEBHOOK_URL)
    else:
        logger.error('Failed to remove webhook: %s - %s', response.status_code, response.text)

    # Set Telegram webhook on startup
    set_webhook_url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook'
    response = requests.post(set_webhook_url, json={'url': WEBHOOK_URL})
    if response.status_code == 200:
        logger.info('Webhook set successfully to %s', WEBHOOK_URL)
    else:
        logger.error('Failed to set webhook: %s - %s', response.status_code, response.text)

    # Run app
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

