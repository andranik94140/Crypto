"""Telegram notification helper based on aiogram."""
import logging

from aiogram import Bot


async def send_telegram(bot: Bot, chat_id: int, text: str) -> None:
    """Send *text* to *chat_id* using *bot*."""
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    except Exception as exc:  # pragma: no cover - network issues
        logging.warning("telegram send failed: %s", exc)
