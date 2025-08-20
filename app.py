"""Main entry point: Pump/Dump first; OI fetched only when alert triggers."""
from __future__ import annotations
import asyncio
import json
import time
import logging
import os

import httpx
import websockets
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import Message

from config import load_config, Config
import notifier
import bybit_api
import short_agent
from risk import calc_short_score

# ---- Logging ----
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

# ---- Price buffers & cooldown ----
price_data: dict[str, list[tuple[float, float]]] = {}
last_alert_time: dict[str, float] = {}

# ---- Optional Coinglass capture ----
def capture_page_if_enabled(url: str, symbol: str, cfg: Config) -> str | None:
    if not cfg.enable_coinglass_capture:
        return None
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from PIL import Image

        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--window-size=1920x1080")
        if cfg.chrome_user_data:
            chrome_options.add_argument(f"user-data-dir={cfg.chrome_user_data}")
        if os.name == "nt":
            chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

        service = Service(executable_path=cfg.chromedriver_path) if cfg.chromedriver_path else Service()
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(url)
        time.sleep(5)
        os.makedirs("capture", exist_ok=True)
        screenshot_path = f"capture/PumpDump_{symbol}.png"
        driver.save_screenshot(screenshot_path)
        driver.quit()
        # normalisation PNG
        try:
            img = Image.open(screenshot_path)
            img.save(screenshot_path)
        except Exception:
            pass
        return screenshot_path
    except Exception as e:
        logging.warning("capture failed: %s", e)
        return None

# ---- Alert pipeline ----
async def handle_alert(
    cfg: Config,
    bot: Bot,
    http: httpx.AsyncClient,
    symbol: str,
    variation: float,
    direction: str,  # "up" | "down"
    exchange: str,   # "Binance" | "Bybit"
):
    now = time.time()
    # cooldown par symbole
    if symbol in last_alert_time and now - last_alert_time[symbol] < cfg.cooldown_sec:
        return
    last_alert_time[symbol] = now

    # URLs utilitaires
    if exchange.lower() == "binance":
        coinglass_url = f"https://www.coinglass.com/tv/Binance_{symbol}"
    elif exchange.lower() == "bybit":
        coinglass_url = f"https://www.coinglass.com/tv/Bybit_{symbol}"
    else:
        coinglass_url = "https://www.coinglass.com"
    exchange_url = f"https://www.bybit.com/trade/usdt/{symbol}"

    # ---- Récupère OI ~1h vs dernier
    try:
        oi_1h, oi_last, oi_delta_pct = await bybit_api.get_oi_1h_change(http, symbol)
        if oi_delta_pct > 0:
            oi_trend = f"OI ↑ (+{oi_delta_pct:.2f}%)"
        elif oi_delta_pct < 0:
            oi_trend = f"OI ↓ ({oi_delta_pct:.2f}%)"
        else:
            oi_trend = "OI ≈ (0.00%)"
    except Exception as e:
        oi_1h = oi_last = oi_delta_pct = 0.0
        oi_trend = f"OI: erreur ({e})"

    try:
        (vol_1h, vol_last, vol_dpct,
         not_1h, not_last, not_dpct) = await bybit_api.get_volume_1h_change(http, symbol)

        if vol_dpct > 0:
            vol_trend = f"Vol ↑ (+{vol_dpct:.2f}%)"
        elif vol_dpct < 0:
            vol_trend = f"Vol ↓ ({vol_dpct:.2f}%)"
        else:
            vol_trend = "Vol ≈ (0.00%)"

        # Notionnel en USDT (turnover)
        if not_dpct > 0:
            not_trend = f"Notionnel ↑ (+{not_dpct:.2f}%)"
        elif not_dpct < 0:
            not_trend = f"Notionnel ↓ ({not_dpct:.2f}%)"
        else:
            not_trend = "Notionnel ≈ (0.00%)"
    except Exception as e:
        vol_1h = vol_last = vol_dpct = 0.0
        not_1h = not_last = not_dpct = 0.0
        vol_trend = f"Vol: erreur ({e})"
        not_trend = ""
    
    # ---- Funding rate (actuel)
    raw_funding = 0.0
    try:
        raw_funding = await bybit_api.get_current_funding_rate(http, symbol)
        # Bybit renvoie une fraction (ex: 0.0034 => 0.34%)
        funding_pct = raw_funding * 100.0
        funding_bp = funding_pct * 100.0              # basis points (optionnel)
        funding_str = f"{funding_pct:+.2f}% ({funding_bp:+.0f} bp)"
    except Exception as e:
        funding_str = "n/a"
        logging.warning("funding fetch failed for %s: %s", symbol, e)


    # ---- Position dans l'historique (1D all-time scan)
    ratio = 0.0
    try:
        pmin, pmax, plast, ts_min, ts_max = await bybit_api.get_alltime_range(http, symbol)
        ratio, label = bybit_api.historical_position_label(plast, pmin, pmax)
        # ratio en %
        pos_pct = ratio * 100.0
    except Exception as e:
        pmin = pmax = plast = 0.0
        pos_pct = 0.0
        label = "inconnu"
        logging.warning("all-time range failed for %s: %s", symbol, e)
    
    

    # ---- (Optionnel) Filtrer selon OI
    if cfg.require_oi_confirm:
        if (direction == "up" and oi_delta_pct <= +cfg.confirm_oi_pct) or \
           (direction == "down" and oi_delta_pct >= -cfg.confirm_oi_pct):
            logging.info("%s alert ignored: OI not confirming (%+.2f%%)", symbol, oi_delta_pct)
            return

    short_score = calc_short_score(raw_funding, ratio, oi_delta_pct)

    if short_score <= 0.50:
        logging.info(
            "%s alert ignored: short score %.2f <= 0.50", symbol, short_score
        )
        return

    emoji = "📈" if direction == "up" else "📉"
    message_type = "PUMP" if direction == "up" else "DUMP"

    caption = (
        f"{emoji} <b>{message_type}</b> détecté sur <b>{symbol}</b> ({exchange})\n"
        f"Variation sur {cfg.time_window_sec // 60} min : <b>{variation:.2f}%</b>\n"
        f"{oi_trend} — 1h: <code>{oi_1h:.0f}</code> → now: <code>{oi_last:.0f}</code>\n"
        f"{vol_trend} — 5m: <code>{vol_1h:.0f}</code> → now: <code>{vol_last:.0f}</code>\n"
        f"{not_trend}\n"
        f"Funding: <b>{funding_str}</b>  |  Position historique: <b>{pos_pct:.1f}%</b> ({label})\n"
        f"Score short: <b>{short_score:.2f}</b>\n"
        f"<a href=\"{coinglass_url}\">🔗 Coinglass</a> | "
        f"<a href=\"{exchange_url}\">🔗 Bybit</a>"
    )

    # envoi à tous les users autorisés
    screenshot = capture_page_if_enabled(coinglass_url, symbol, cfg)
    for uid in cfg.authorized_users:
        if screenshot:
            await notifier.send_photo_with_caption(bot, uid, screenshot, caption, parse_mode="HTML")
        else:
            await notifier.send_text(bot, uid, caption, parse_mode="HTML")

    logging.info("%s alert sent | Δ=%.2f%% | %s", symbol, variation, oi_trend)

# ---- Binance WS (!ticker@arr) ----
async def price_monitor_binance(cfg: Config, bot: Bot, http: httpx.AsyncClient):
    uri = "wss://stream.binance.com:9443/ws/!ticker@arr"
    while True:
        try:
            async with websockets.connect(uri, ping_interval=20, ping_timeout=10) as websocket:
                logging.info("✅ Connected to Binance WebSocket")
                while True:
                    msg = await websocket.recv()
                    data = json.loads(msg)
                    current_time = time.time()
                    for ticker in data:
                        symbol = ticker.get("s")
                        if not symbol or not symbol.endswith("USDT"):
                            continue
                        try:
                            price = float(ticker["c"])
                        except Exception:
                            continue

                        buf = price_data.setdefault(symbol, [])
                        buf.append((current_time, price))
                        # prune by window
                        cutoff = current_time - cfg.time_window_sec
                        price_data[symbol] = [(t, p) for (t, p) in buf if t >= cutoff]

                        prices = [p for (_, p) in price_data[symbol]]
                        if len(prices) < 2:
                            continue
                        mn, mx = min(prices), max(prices)
                        if mn <= 0:
                            continue
                        variation = (mx - mn) / mn * 100.0
                        if variation >= cfg.threshold_percent:
                            direction = "up" if prices[-1] > prices[0] else "down"
                            await handle_alert(cfg, bot, http, symbol, variation, direction, "Binance")
                            price_data[symbol] = []
        except Exception as e:
            logging.warning("[Binance WS error] %s", e)
        logging.info("🔄 Reconnecting Binance WS in 5s…")
        await asyncio.sleep(5)

# ---- Bybit WS (v5/public/linear tickers.SYMBOL) ----
async def price_monitor_bybit(cfg: Config, bot: Bot, http: httpx.AsyncClient):
    uri = "wss://stream.bybit.com/v5/public/linear"
    # récupère liste des symboles USDT perp
    symbols = await bybit_api.fetch_usdt_perp_symbols(http)
    args = [f"tickers.{s}" for s in symbols]
    chunk_size = 100

    while True:
        try:
            async with websockets.connect(uri) as websocket:
                logging.info("✅ Connected to Bybit WebSocket (%d symbols)", len(symbols))
                # subscribe par chunks
                for i in range(0, len(args), chunk_size):
                    chunk = args[i:i+chunk_size]
                    await websocket.send(json.dumps({"op": "subscribe", "args": chunk}))
                    await asyncio.sleep(0.1)

                while True:
                    msg = await websocket.recv()
                    data = json.loads(msg)
                    topic = data.get("topic", "")
                    if not topic.startswith("tickers."):
                        continue
                    symbol = topic.split(".", 1)[1]
                    ticker_data = data.get("data", {})
                    last_price = ticker_data.get("lastPrice")
                    if last_price is None:
                        continue
                    try:
                        price = float(last_price)
                    except Exception:
                        continue

                    current_time = time.time()
                    buf = price_data.setdefault(symbol, [])
                    buf.append((current_time, price))
                    cutoff = current_time - cfg.time_window_sec
                    price_data[symbol] = [(t, p) for (t, p) in buf if t >= cutoff]

                    prices = [p for (_, p) in price_data[symbol]]
                    if len(prices) < 2:
                        continue
                    mn, mx = min(prices), max(prices)
                    if mn <= 0:
                        continue
                    variation = (mx - mn) / mn * 100.0
                    if variation >= cfg.threshold_percent:
                        direction = "up" if prices[-1] > prices[0] else "down"
                        await handle_alert(cfg, bot, http, symbol, variation, direction, "Bybit")
                        price_data[symbol] = []
        except Exception as e:
            logging.warning("[Bybit WS error] %s", e)
        logging.info("🔄 Reconnecting Bybit WS in 5s…")
        await asyncio.sleep(5)

# ---- Telegram commands ----
def is_authorized(uid: int, cfg: Config) -> bool:
    return uid in cfg.authorized_users

def register_commands(dp: Dispatcher, cfg: Config):
    @dp.message(Command("start"))
    async def cmd_start(message: Message):
        if not is_authorized(message.from_user.id, cfg):
            await message.answer("🚫 Accès refusé.")
            return
        await message.answer(
            "🤖 Pump/Dump monitor prêt.\n"
            f"Seuil: {cfg.threshold_percent:.2f}%\n"
            f"Fenêtre: {cfg.time_window_sec // 60} min\n"
            f"OI confirm: {cfg.require_oi_confirm} (±{cfg.confirm_oi_pct:.2f}%)"
        )

    @dp.message(Command("status"))
    async def cmd_status(message: Message):
        if not is_authorized(message.from_user.id, cfg):
            await message.answer("🚫 Accès refusé.")
            return
        await message.answer(
            "📊 Statut:\n"
            f"• tracked symbols: {len({k for k in price_data.keys() if price_data[k]})}\n"
            f"• cooldown: {cfg.cooldown_sec}s\n"
        )

    @dp.message(Command("short"))
    async def cmd_short(message: Message):
        if not is_authorized(message.from_user.id, cfg):
            await message.answer("🚫 Accès refusé.")
            return
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("Usage: /short SYMBOL")
            return
        symbol = parts[1].upper()
        timeout = httpx.Timeout(10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            score = await short_agent.evaluate_short_symbol(client, symbol)
        await message.answer(f"Score short {symbol}: {score:.2f}")

# ---- main ----
async def main():
    cfg = load_config()
    bot = Bot(
        cfg.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    register_commands(dp, cfg)

    timeout = httpx.Timeout(10.0)
    async with httpx.AsyncClient(timeout=timeout) as http:
        tasks = [dp.start_polling(bot)]
        if cfg.use_binance_ws:
            tasks.append(price_monitor_binance(cfg, bot, http))
        if cfg.use_bybit_ws:
            tasks.append(price_monitor_bybit(cfg, bot, http))
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
