"""In-memory application state."""
from collections import deque
from typing import Deque, Dict, Iterable, Tuple

PRICE_HISTORY: Dict[str, Deque[Tuple[float, float]]] = {}
OI_HISTORY: Dict[str, Deque[Tuple[float, float]]] = {}
LAST_ALERT: Dict[str, float] = {}


def _update(history: Dict[str, Deque[Tuple[float, float]]], symbol: str, value: float, ts: float, max_age: float) -> None:
    dq = history.setdefault(symbol, deque())
    dq.append((ts, value))
    while dq and ts - dq[0][0] > max_age:
        dq.popleft()


def update_price(symbol: str, price: float, ts: float, max_age: float) -> None:
    _update(PRICE_HISTORY, symbol, price, ts, max_age)


def update_oi(symbol: str, oi: float, ts: float, max_age: float) -> None:
    _update(OI_HISTORY, symbol, oi, ts, max_age)


def get_prices(symbol: str) -> Iterable[float]:
    return [p for _, p in PRICE_HISTORY.get(symbol, [])]


def get_ois(symbol: str) -> Iterable[float]:
    return [v for _, v in OI_HISTORY.get(symbol, [])]


def can_notify(symbol: str, now: float, cooldown: float) -> bool:
    last = LAST_ALERT.get(symbol)
    return last is None or now - last >= cooldown


def mark_notified(symbol: str, now: float) -> None:
    LAST_ALERT[symbol] = now
