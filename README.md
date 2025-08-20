# Bybit Risk Agent

Asynchronous Python 3.11+ agent that polls Bybit USDT markets and sends Telegram alerts
when risk signals are detected.

## Features

- Fetches prices and open interest for all linear USDT pairs via Bybit REST API.
- Detects pump/dump moves, open-interest spikes and price/OI divergence.
- Aggregates signals with recent volatility into a 0..1 risk score.
- Sends a Telegram message only when score exceeds `RISK_THRESHOLD`.
- Single user, no database, in-memory state.

## Configuration

Edit `config.py` or set environment variables. Example defaults:

```python
TELEGRAM_BOT_TOKEN = "8261674604:AAGnKKs0RAkzC09ZuMRLbWTt99Hy9zWL2nY"
TELEGRAM_CHAT_ID = 539549530
```

## Run

```bash
python app.py
```

## Tests

```bash
pytest
```
