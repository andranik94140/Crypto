# Bybit Risk Agent


## Features

- Fetches prices and open interest for all linear USDT pairs via Bybit REST API.
- Detects pump/dump moves, open-interest spikes and price/OI divergence.
- Aggregates signals with recent volatility into a 0..1 risk score.
- Sends a Telegram message only when score exceeds `RISK_THRESHOLD`.
- Single user, no database, in-memory state.
- Provides a `/short SYMBOL` command that returns a 0..1 score for shorting
  based on funding rate, price position, open-interest trend and recent
  liquidation imbalance.

- Alerts are sent only when the short score exceeds `0.50` for clearer signals.
- Alerts include this short score for quick assessment.

### Liquidation data

The short-scoring logic subscribes to Bybit's public `all_liquidation_stream`
WebSocket channel to approximate the volume of liquidations on each side over
the last hour. Bybit pushes a batch of recent liquidation events when the stream
is opened; we aggregate those within the past hour and compute the ratio of
short liquidations over the total. This stream may occasionally lag or miss
events, so treat the ratio as an indicative signal rather than a precise
measure.



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
