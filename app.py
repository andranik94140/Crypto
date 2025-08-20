"""Main entry point for the Bybit trading agent."""
import asyncio
import logging

import httpx

import bybit_api
import detectors
import notifier
import risk
import state
from config import Config, load_config
from utils import utc_now

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")


async def process_symbol(cfg: Config, symbol: str, price: float, oi: float, now: float) -> None:
    state.update_price(symbol, price, now, cfg.history_min * 60)
    state.update_oi(symbol, oi, now, cfg.history_min * 60)

    prices = list(state.get_prices(symbol))
    ois = list(state.get_ois(symbol))
    pump = detectors.detect_pump_dump(prices[-cfg.pump_window_min :], cfg.pump_pct)
    oi_delta = detectors.detect_oi_delta(ois[-cfg.pump_window_min :], cfg.oi_delta_pct)
    divergence = detectors.detect_divergence(prices[-cfg.pump_window_min :], ois[-cfg.pump_window_min :])
    vol = risk.compute_volatility(prices)
    score = risk.calc_risk_score(pump, oi_delta, divergence, vol)

    if score >= cfg.risk_threshold and state.can_notify(symbol, now, cfg.cooldown_seconds):
        text = f"{symbol}: risk {score:.2f} (pump={pump} oi={oi_delta} div={divergence} vol={vol:.2f})"
        async with httpx.AsyncClient() as client:
            await notifier.send_telegram(client, cfg.telegram_bot_token, cfg.telegram_chat_id, text)
        state.mark_notified(symbol, now)


async def poll(cfg: Config) -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        while True:
            try:
                tickers = await bybit_api.fetch_tickers(client)
                now = utc_now()
                for item in tickers:
                    symbol = item.get("symbol")
                    if not symbol or not symbol.endswith("USDT"):
                        continue
                    price = float(item.get("lastPrice", 0))
                    oi = float(item.get("openInterest", 0))
                    await process_symbol(cfg, symbol, price, oi, now)
            except Exception as exc:  # pragma: no cover - network issues
                logging.warning("poll failed: %s", exc)
            await asyncio.sleep(cfg.poll_seconds)


async def main() -> None:
    cfg = load_config()
    await poll(cfg)


if __name__ == "__main__":
    asyncio.run(main())
