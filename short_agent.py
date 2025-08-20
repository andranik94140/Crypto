"""High level helpers to evaluate short opportunities on Bybit."""
from __future__ import annotations

import httpx

import bybit_api
from risk import calc_short_score


async def evaluate_short_symbol(client: httpx.AsyncClient, symbol: str) -> float:
    """Return a 0..1 score estimating short potential for *symbol*.

    The score combines four factors:

    - Funding rate (negative is good for shorts)
    - Position of the current price in its historical range
    - Recent open interest change (falling OI favours shorts)
    - Ratio of short liquidation volume over total liquidations
    """

    funding = await bybit_api.get_current_funding_rate(client, symbol)
    _, _, oi_delta_pct = await bybit_api.get_oi_1h_change(client, symbol)
    pmin, pmax, last_close, _, _ = await bybit_api.get_alltime_range(client, symbol)
    ratio, _ = bybit_api.historical_position_label(last_close, pmin, pmax)

    long_liq, short_liq = await bybit_api.get_liquidation_stats(client, symbol)
    total = long_liq + short_liq
    short_liq_ratio = short_liq / total if total else 0.0

    return calc_short_score(funding, ratio, oi_delta_pct, short_liq_ratio)

