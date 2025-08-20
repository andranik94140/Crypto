"""Signal detectors for price and open interest."""
from typing import Sequence

from utils import pct_change


def detect_pump_dump(prices: Sequence[float], threshold_pct: float) -> bool:
    """Return True if price changes by *threshold_pct* percent."""
    if len(prices) < 2:
        return False
    change = pct_change(prices[0], prices[-1])
    return abs(change) >= threshold_pct


def detect_oi_delta(oi_values: Sequence[float], threshold_pct: float) -> bool:
    """Return True if open interest changes by *threshold_pct* percent."""
    if len(oi_values) < 2:
        return False
    change = pct_change(oi_values[0], oi_values[-1])
    return abs(change) >= threshold_pct


def detect_divergence(prices: Sequence[float], oi_values: Sequence[float]) -> bool:
    """Return True if price and OI move in opposite directions."""
    if len(prices) < 2 or len(oi_values) < 2:
        return False
    price_change = pct_change(prices[0], prices[-1])
    oi_change = pct_change(oi_values[0], oi_values[-1])
    return price_change * oi_change < 0
