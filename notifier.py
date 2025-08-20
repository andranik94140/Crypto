"""Telegram notification helper based on Aiogram (v3)."""
import logging
from aiogram import Bot


async def send_telegram(bot: Bot, chat_id: int | str, text: str) -> None:
    """Envoie *text* à *chat_id* via le *bot* Aiogram."""
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    except Exception as exc:  # pragma: no cover - réseau / API
        logging.warning("telegram send failed: %s", exc)
