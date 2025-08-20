import pytest

import sys
import types


# Stub external dependencies to import app without installing packages
httpx_stub = types.ModuleType("httpx")
httpx_stub.AsyncClient = object
httpx_stub.Timeout = object
sys.modules.setdefault("httpx", httpx_stub)

websockets_stub = types.ModuleType("websockets")
sys.modules.setdefault("websockets", websockets_stub)

aiogram_stub = types.ModuleType("aiogram")
aiogram_stub.Bot = object
aiogram_stub.Dispatcher = object
sys.modules.setdefault("aiogram", aiogram_stub)

enums_stub = types.ModuleType("aiogram.enums")
class ParseMode:
    HTML = "HTML"
enums_stub.ParseMode = ParseMode
sys.modules.setdefault("aiogram.enums", enums_stub)

default_stub = types.ModuleType("aiogram.client.default")
class DefaultBotProperties:
    def __init__(self, *args, **kwargs):
        pass
default_stub.DefaultBotProperties = DefaultBotProperties
client_pkg = types.ModuleType("aiogram.client")
client_pkg.default = default_stub
sys.modules.setdefault("aiogram.client.default", default_stub)
sys.modules.setdefault("aiogram.client", client_pkg)

filters_stub = types.ModuleType("aiogram.filters")
def Command(*args, **kwargs):
    pass
filters_stub.Command = Command
sys.modules.setdefault("aiogram.filters", filters_stub)

types_stub = types.ModuleType("aiogram.types")
class Message:
    from_user = types.SimpleNamespace(id=0)
    text = ""
    async def answer(self, *args, **kwargs):
        pass
types_stub.Message = Message
class FSInputFile:
    def __init__(self, *args, **kwargs):
        pass
types_stub.FSInputFile = FSInputFile
sys.modules.setdefault("aiogram.types", types_stub)

import app
from config import Config


def make_config() -> Config:
    return Config(
        telegram_bot_token="",
        authorized_users={1},
        threshold_percent=5.0,
        time_window_sec=60,
        cooldown_sec=0,
        require_oi_confirm=False,
        confirm_oi_pct=1.0,
        use_binance_ws=False,
        use_bybit_ws=False,
        enable_coinglass_capture=False,
        chromedriver_path=None,
        chrome_user_data=None,
    )


def test_handle_alert_filters_by_short_score(monkeypatch):
    cfg = make_config()

    async def fake_get_oi_1h_change(http, symbol):
        return 100.0, 90.0, -10.0

    async def fake_get_volume_1h_change(http, symbol):
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

    async def fake_get_current_funding_rate(http, symbol):
        return -0.01

    async def fake_get_liquidation_stats(http, symbol):
        return 10.0, 90.0  # mostly short liquidations

    async def fake_get_alltime_range(http, symbol):
        return 1.0, 3.0, 2.8, 0, 0  # price near highs -> high ratio

    messages = []

    async def fake_send_text(bot, uid, caption, parse_mode=None):
        messages.append(caption)

    async def run_high():
        monkeypatch.setattr(app.bybit_api, "get_oi_1h_change", fake_get_oi_1h_change)
        monkeypatch.setattr(app.bybit_api, "get_volume_1h_change", fake_get_volume_1h_change)
        monkeypatch.setattr(app.bybit_api, "get_current_funding_rate", fake_get_current_funding_rate)
        monkeypatch.setattr(app.bybit_api, "get_liquidation_stats", fake_get_liquidation_stats)
        monkeypatch.setattr(app.bybit_api, "get_alltime_range", fake_get_alltime_range)

        monkeypatch.setattr(app.notifier, "send_text", fake_send_text)
        monkeypatch.setattr(app.notifier, "send_photo_with_caption", fake_send_text)

        app.last_alert_time = {}
        await app.handle_alert(cfg, bot=None, http=None, symbol="TESTUSDT", variation=10.0, direction="up", exchange="Bybit")

    import asyncio
    asyncio.run(run_high())
    assert messages, "Alert should be sent when score > 0.50"

    async def low_funding(http, symbol):
        return 0.01

    async def low_alltime(http, symbol):
        return 1.0, 3.0, 1.2, 0, 0  # price near lows -> low ratio

    async def low_liq(http, symbol):
        return 90.0, 10.0  # mostly long liquidations

    async def run_low():
        monkeypatch.setattr(app.bybit_api, "get_current_funding_rate", low_funding)
        monkeypatch.setattr(app.bybit_api, "get_alltime_range", low_alltime)
        monkeypatch.setattr(app.bybit_api, "get_liquidation_stats", low_liq)
        messages.clear()
        app.last_alert_time = {}
        await app.handle_alert(cfg, bot=None, http=None, symbol="TESTUSDT", variation=10.0, direction="up", exchange="Bybit")

    asyncio.run(run_low())
    assert not messages, "Alert should be suppressed when score <= 0.50"

