from __future__ import annotations
import os
from dataclasses import dataclass

@dataclass
class Config:
    # Telegram / accès
    telegram_bot_token: str
    authorized_users: set[int]  # mono-utilisateur possible : {123456789}
    # Pump/Dump
    threshold_percent: float     # ex. 6.0  (pour valider en conditions calmes)
    time_window_sec: int         # ex. 1200 (20 min)
    cooldown_sec: int            # ex. 600  (anti-spam par symbole)
    # OI confirmation
    require_oi_confirm: bool     # True = on filtre les alertes selon OI
    confirm_oi_pct: float        # ex. 1.0 (%)
    # Sources
    use_binance_ws: bool         # True pour activer Binance WS
    use_bybit_ws: bool           # True pour activer Bybit WS
    # Capture (optionnelle)
    enable_coinglass_capture: bool
    chromedriver_path: str | None
    chrome_user_data: str | None

def load_config() -> Config:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "8261674604:AAGnKKs0RAkzC09ZuMRLbWTt99Hy9zWL2nY")
    # Mets ici *ton* ID (ou plusieurs)
    users_env = os.getenv("AUTHORIZED_USERS", "539549530")
    if users_env.strip():
        authorized = {int(x) for x in users_env.replace(",", " ").split()}
    else:
        # fallback pour tests rapides
        authorized = {539549530}

    return Config(
        telegram_bot_token=token,
        authorized_users=authorized,
        threshold_percent=float(os.getenv("THRESHOLD_PERCENT", "8.0")),
        time_window_sec=int(os.getenv("TIME_WINDOW_SEC", "1200")),
        cooldown_sec=int(os.getenv("COOLDOWN_SEC", "600")),
        require_oi_confirm=os.getenv("REQUIRE_OI_CONFIRM", "true").lower() == "false",
        confirm_oi_pct=float(os.getenv("CONFIRM_OI_PCT", "1.0")),
        use_binance_ws=os.getenv("USE_BINANCE_WS", "true").lower() == "true",
        use_bybit_ws=os.getenv("USE_BYBIT_WS", "true").lower() == "true",
        enable_coinglass_capture=os.getenv("ENABLE_COINGLASS_CAPTURE", "false").lower() == "true",
        chromedriver_path=os.getenv("CHROMEDRIVER_PATH"),
        chrome_user_data=os.getenv("CHROME_USER_DATA"),
    )
