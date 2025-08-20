"""Telegram notification helper (Aiogram)."""
from __future__ import annotations
import logging
from aiogram import Bot
from aiogram.types import FSInputFile

async def send_text(bot: Bot, chat_id: int | str, text: str, parse_mode: str = "HTML"):
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
    except Exception as exc:  # pragma: no cover
        logging.warning("telegram send failed: %s", exc)

async def send_photo_with_caption(
    bot: Bot,
    chat_id: int | str,
    photo_path: str,
    caption: str,
    parse_mode: str = "HTML",
):
    try:
        photo = FSInputFile(photo_path)
        await bot.send_photo(chat_id=chat_id, photo=photo, caption=caption, parse_mode=parse_mode)
    except Exception as exc:  # pragma: no cover
        logging.warning("telegram send photo failed: %s", exc)
        # fallback texte
        await send_text(bot, chat_id, caption, parse_mode)
