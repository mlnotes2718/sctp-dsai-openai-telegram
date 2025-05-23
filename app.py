import os
import logging

from fastapi import FastAPI, Request, HTTPException
from httpx import AsyncClient, HTTPError
from openai import AsyncOpenAI

# ——— Logging setup —————————————————————————————————————
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ——— Load & validate env vars ——————————————————————————
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("Missing TELEGRAM_TOKEN")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY")

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
if not WEBHOOK_URL:
    raise RuntimeError("Missing WEBHOOK_URL (e.g. https://your-domain)")

# ——— FastAPI app ——————————————————————————————————————
app = FastAPI()

@app.on_event("startup")
async def startup_event():
    # create and store shared HTTPX client with a 10s timeout
    app.state.http = AsyncClient(timeout=10.0)

    # AsyncOpenAI client
    app.state.openai = AsyncOpenAI(api_key=OPENAI_API_KEY)

    # 1. Delete existing webhook & drop pending updates
    try:
        resp = await app.state.http.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteWebhook",
            json={"drop_pending_updates": True}
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            logger.error("deleteWebhook failed: %s", data)
    except HTTPError as e:
        logger.error("Error deleting Telegram webhook", exc_info=True)

    # 2. Register new webhook
    hook_endpoint = f"{WEBHOOK_URL}/webhook/{TELEGRAM_TOKEN}"
    try:
        resp = await app.state.http.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook",
            json={"url": hook_endpoint}
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("ok"):
            logger.info("Registered webhook at %s", hook_endpoint)
        else:
            logger.error("setWebhook failed: %s", data)
    except HTTPError:
        logger.error("Error setting Telegram webhook", exc_info=True)


@app.post("/webhook/{token}")
async def telegram_webhook(token: str, request: Request):
    # validate token
    if token != TELEGRAM_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")

    body = await request.json()

    # support both new and edited messages
    msg = body.get("message") or body.get("edited_message")
    if not msg:
        return {"ok": True}

    text = msg.get("text")
    if not text:
        # ignore stickers, photos, etc.
        return {"ok": True}

    chat_id = msg["chat"]["id"]

    # — Query OpenAI —
    try:
        completion = await app.state.openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": text}],
            timeout=10.0  # override if needed
        )
        reply = completion.choices[0].message.content
    except Exception:
        logger.exception("OpenAI API error")
        reply = "❗️ Sorry, something went wrong on the AI side. Please try again."

    # — Send reply back to Telegram —
    try:
        resp = await app.state.http.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": reply}
        )
        resp.raise_for_status()
    except HTTPError:
        logger.error("Failed to send Telegram message", exc_info=True)

    return {"ok": True}


@app.on_event("shutdown")
async def shutdown_event():
    # close HTTPX client
    await app.state.http.aclose()
    # close OpenAI client (if it supports aclose)
    try:
        await app.state.openai.aclose()
    except AttributeError:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))

## gunicorn app:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT

