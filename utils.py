"""Utility helpers for calculations and time handling."""
from __future__ import annotations

import statistics
import time
from typing import Iterable, Iterator, Sequence


def pct_change(old: float, new: float) -> float:
    """Return percentage change between two values."""
    if old == 0:
        return 0.0
    return (new - old) / old * 100.0


def ema(values: Sequence[float], period: int) -> float:
    """Return the exponential moving average of *values*."""
    if not values:
        raise ValueError("values is empty")
    k = 2 / (period + 1)
    ema_val = values[0]
    for v in values[1:]:
        ema_val = v * k + ema_val * (1 - k)
    return ema_val


def window(seq: Sequence[float], size: int) -> Iterator[Sequence[float]]:
    """Yield sliding windows from *seq* of length *size*."""
    for i in range(size, len(seq) + 1):
        yield seq[i - size : i]


def utc_now() -> float:
    """Return current UTC timestamp in seconds."""
    return time.time()


def stddev(values: Iterable[float]) -> float:
    """Return standard deviation of *values* or 0 for <2 items."""
    vals = list(values)
    if len(vals) < 2:
        return 0.0
    return statistics.stdev(vals)
