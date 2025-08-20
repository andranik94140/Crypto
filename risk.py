"""Risk score calculation."""
from typing import Sequence

from utils import pct_change, stddev


def compute_volatility(prices: Sequence[float]) -> float:
    """Return standard deviation of price returns."""
    if len(prices) < 2:
        return 0.0
    returns = [pct_change(prices[i - 1], prices[i]) for i in range(1, len(prices))]
    return stddev(returns)


def calc_risk_score(pump: bool, oi_delta: bool, divergence: bool, volatility: float) -> float:
    """Combine signals and volatility into a 0..1 risk score."""
    signals = [pump, oi_delta, divergence]
    signal_score = sum(1.0 for s in signals if s) / len(signals)
    vol_score = min(volatility / 5, 1.0)  # 5%% return std dev == max
    return 0.7 * signal_score + 0.3 * vol_score
