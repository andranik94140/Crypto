"""Application configuration and environment overrides."""
from dataclasses import dataclass
import os

TELEGRAM_BOT_TOKEN = "8261674604:AAGnKKs0RAkzC09ZuMRLbWTt99Hy9zWL2nY"
TELEGRAM_CHAT_ID = 539549530
INTERVAL_MIN = 1
POLL_SECONDS = 60
HISTORY_MIN = 60
PUMP_WINDOW_MIN = 5
PUMP_PCT = 8.0
OI_DELTA_PCT = 3.0
RISK_THRESHOLD = 0.65
COOLDOWN_SECONDS = 600

@dataclass
class Config:
    """Runtime configuration values."""
    telegram_bot_token: str = TELEGRAM_BOT_TOKEN
    telegram_chat_id: int = TELEGRAM_CHAT_ID
    interval_min: int = INTERVAL_MIN
    poll_seconds: int = POLL_SECONDS
    history_min: int = HISTORY_MIN
    pump_window_min: int = PUMP_WINDOW_MIN
    pump_pct: float = PUMP_PCT
    oi_delta_pct: float = OI_DELTA_PCT
    risk_threshold: float = RISK_THRESHOLD
    cooldown_seconds: int = COOLDOWN_SECONDS


def load_config() -> Config:
    """Load configuration from environment variables."""
    return Config(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", TELEGRAM_BOT_TOKEN),
        telegram_chat_id=int(os.getenv("TELEGRAM_CHAT_ID", TELEGRAM_CHAT_ID)),
        interval_min=int(os.getenv("INTERVAL_MIN", INTERVAL_MIN)),
        poll_seconds=int(os.getenv("POLL_SECONDS", POLL_SECONDS)),
        history_min=int(os.getenv("HISTORY_MIN", HISTORY_MIN)),
        pump_window_min=int(os.getenv("PUMP_WINDOW_MIN", PUMP_WINDOW_MIN)),
        pump_pct=float(os.getenv("PUMP_PCT", PUMP_PCT)),
        oi_delta_pct=float(os.getenv("OI_DELTA_PCT", OI_DELTA_PCT)),
        risk_threshold=float(os.getenv("RISK_THRESHOLD", RISK_THRESHOLD)),
        cooldown_seconds=int(os.getenv("COOLDOWN_SECONDS", COOLDOWN_SECONDS)),
    )
