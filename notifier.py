"""Telegram notification helper."""
import logging

import httpx


async def send_telegram(client: httpx.AsyncClient, token: str, chat_id: int, text: str) -> None:
    """Send *text* to *chat_id* using Bot *token*."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = await client.post(url, json={"chat_id": chat_id, "text": text})
        resp.raise_for_status()
    except Exception as exc:  # pragma: no cover - network issues
        logging.warning("telegram send failed: %s", exc)
