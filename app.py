"""Main entry point for the Bybit trading agent (Aiogram)."""
import asyncio
import logging
from typing import Any

import httpx
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

import bybit_api
import detectors
import notifier
import risk
import state
from config import Config, load_config
from utils import utc_now

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")


async def process_symbol(
    cfg: Config, bot: Bot, symbol: str, price: float, oi: float, now: float
) -> None:
    """Met à jour l'état, calcule le risque et envoie une alerte si nécessaire."""
    history_seconds = cfg.history_min * 60

    state.update_price(symbol, price, now, history_seconds)
    state.update_oi(symbol, oi, now, history_seconds)

    prices = list(state.get_prices(symbol))
    ois = list(state.get_ois(symbol))
    if len(prices) < cfg.pump_window_min + 1 or len(ois) < cfg.pump_window_min + 1:
        return  # pas assez d'historique

    pump = detectors.detect_pump_dump(prices[-cfg.pump_window_min :], cfg.pump_pct)
    oi_delta = detectors.detect_oi_delta(ois[-cfg.pump_window_min :], cfg.oi_delta_pct)
    divergence = detectors.detect_divergence(
        prices[-cfg.pump_window_min :], ois[-cfg.pump_window_min :]
    )
    vol = risk.compute_volatility(prices)
    score = risk.calc_risk_score(pump, oi_delta, divergence, vol)

    if score >= cfg.risk_threshold and state.can_notify(symbol, now, cfg.cooldown_seconds):
        text = (
            f"{symbol}: risk {score:.2f} "
            f"(pump={pump} oi={oi_delta} div={divergence} vol={vol:.2f})"
        )
        await notifier.send_telegram(bot, cfg.telegram_chat_id, text)
        state.mark_notified(symbol, now)


async def poll(cfg: Config, bot: Bot) -> None:
    """Boucle principale: récupère les tickers et traite chaque symbole."""
    timeout = httpx.Timeout(10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        while True:
            try:
                tickers: list[dict[str, Any]] = await bybit_api.fetch_tickers(client)
                now = utc_now()
                for item in tickers:
                    symbol = item.get("symbol")
                    if not symbol or not symbol.endswith("USDT"):
                        continue
                    price = float(item.get("lastPrice", 0.0))
                    oi = float(item.get("openInterest", 0.0))
                    await process_symbol(cfg, bot, symbol, price, oi, now)
            except Exception as exc:  # pragma: no cover - réseau / API
                logging.warning("poll failed: %s", exc)
            await asyncio.sleep(cfg.poll_seconds)


async def main() -> None:
    cfg = load_config()

    bot = Bot(cfg.telegram_bot_token)
    dp = Dispatcher()

    async def cmd_start(message: Message) -> None:
        """Retourne les valeurs de configuration courantes."""
        text = (
            "Agent running\n"
            f"Poll: {cfg.poll_seconds}s\n"
            f"Pump window: {cfg.pump_window_min}m\n"
            f"Pump pct: {cfg.pump_pct}%\n"
            f"OI delta pct: {cfg.oi_delta_pct}%\n"
            f"Risk threshold: {cfg.risk_threshold}"
        )
        await message.answer(text)

    dp.message.register(cmd_start, Command("start"))

    await asyncio.gather(poll(cfg, bot), dp.start_polling(bot))


if __name__ == "__main__":
    asyncio.run(main())
