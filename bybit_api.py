from __future__ import annotations
import time
from typing import List, Tuple

import httpx

BASE = "https://api.bybit.com"


# ===== Liste des symboles USDT perp =====
async def fetch_usdt_perp_symbols(client: httpx.AsyncClient) -> List[str]:
    """Retourne la liste des symboles USDT perp (Bybit v5)."""
    symbols: List[str] = []
    cursor: str | None = None
    while True:
        params = {"category": "linear"}
        if cursor:
            params["cursor"] = cursor
        r = await client.get(f"{BASE}/v5/market/instruments-info", params=params)
        r.raise_for_status()
        data = r.json() or {}
        result = data.get("result") or {}
        items = result.get("list") or []
        # garde uniquement les perp en USDT (ex: BTCUSDT, ETHUSDT…)
        symbols += [str(it.get("symbol", "")) for it in items if str(it.get("symbol", "")).endswith("USDT")]
        cursor = result.get("nextPageCursor")
        if not cursor:
            break
    # unique + ordre stable
    seen = set()
    uniq = []
    for s in symbols:
        if s and s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq


# ===== Open Interest: variation ≈1h =====
async def get_oi_1h_change(client: httpx.AsyncClient, symbol: str) -> Tuple[float, float, float]:
    """
    Retourne (oi_1h_ago, oi_last, delta_pct) à partir de /v5/market/open-interest
    période 5min, limit=13 (~65min) pour couvrir ≈1h.
    """
    params = {
        "category": "linear",
        "symbol": symbol,
        "intervalTime": "5min",
        "limit": 13,
    }
    r = await client.get(f"{BASE}/v5/market/open-interest", params=params)
    r.raise_for_status()
    data = r.json() or {}
    rows = (data.get("result") or {}).get("list") or []
    if not rows:
        return 0.0, 0.0, 0.0

    def _ts(row: dict) -> int:
        return int(row.get("timestamp") or row.get("ts") or row.get("startTime") or 0)

    try:
        rows = sorted(rows, key=_ts)
    except Exception:
        pass

    try:
        oi_last = float(rows[-1]["openInterest"])
    except Exception:
        oi_last = 0.0
    try:
        oi_1h = float(rows[0]["openInterest"])
    except Exception:
        oi_1h = 0.0

    delta_pct = ((oi_last - oi_1h) / oi_1h * 100.0) if oi_1h else 0.0
    return oi_1h, oi_last, delta_pct


# ===== Volume / Notionnel: variation ≈1h =====
async def get_volume_1h_change(
    client: httpx.AsyncClient,
    symbol: str
) -> Tuple[float, float, float, float, float, float]:
    """
    Retourne (vol_1h_ago, vol_last, vol_delta_pct, notional_1h_ago, notional_last, notional_delta_pct)
    à partir de /v5/market/kline en 5min, limit=13 (~65min).

    - volume   : quantité (base) échangée sur l'intervalle
    - turnover : notionnel (quote, USDT) échangé sur l'intervalle
    """
    params = {
        "category": "linear",
        "symbol": symbol,
        "interval": "5",  # 5 minutes
        "limit": 13,      # ~1h
    }
    r = await client.get(f"{BASE}/v5/market/kline", params=params)
    r.raise_for_status()
    data = r.json() or {}
    rows = (data.get("result") or {}).get("list") or []
    if not rows:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

    # Bybit renvoie souvent les klines du plus récent au plus ancien -> trie croissant
    def _ts(row: list) -> int:
        try:
            return int(row[0])
        except Exception:
            return 0

    try:
        rows = sorted(rows, key=_ts)
    except Exception:
        pass

    def _f(x) -> float:
        try:
            return float(x)
        except Exception:
            return 0.0

    # Dernier intervalle
    last = rows[-1]
    vol_last = _f(last[5])
    notional_last = _f(last[6])

    # Intervalle ~1h avant (le premier de la fenêtre)
    first = rows[0]
    vol_1h_ago = _f(first[5])
    notional_1h_ago = _f(first[6])

    vol_delta_pct = ((vol_last - vol_1h_ago) / vol_1h_ago * 100.0) if vol_1h_ago else 0.0
    notional_delta_pct = ((notional_last - notional_1h_ago) / notional_1h_ago * 100.0) if notional_1h_ago else 0.0

    return vol_1h_ago, vol_last, vol_delta_pct, notional_1h_ago, notional_last, notional_delta_pct


# ===== Liquidations ≈1h (HTTP) =====
async def get_liquidation_stats(client: httpx.AsyncClient, symbol: str) -> Tuple[float, float]:
    """Retourne les volumes de liquidations long et short sur ~1h (somme des qty)."""
    params = {
        "category": "linear",
        "symbol": symbol,
        "limit": 200,
    }
    r = await client.get(f"{BASE}/v5/market/liquidation", params=params)
    r.raise_for_status()
    data = r.json() or {}
    rows = (data.get("result") or {}).get("list") or []

    cutoff = int(time.time() * 1000) - 60 * 60 * 1000
    long_vol = 0.0
    short_vol = 0.0
    for row in rows:
        try:
            ts = int(row.get("time") or row.get("updatedTime") or row.get("ts") or 0)
            if ts < cutoff:
                continue
            qty = float(row.get("qty") or row.get("size") or 0.0)
            side = str(row.get("side") or "").lower()
            # convention: si side == "sell", ce sont des longs liquidés
            if side == "sell":
                long_vol += qty
            elif side == "buy":
                short_vol += qty
        except Exception:
            continue
    return long_vol, short_vol


# ===== Funding rate (actuel) =====
async def get_current_funding_rate(client: httpx.AsyncClient, symbol: str) -> float:
    """
    Lit le funding rate actuel pour un perpetual 'symbol' (Bybit v5).
    Source: /v5/market/tickers (category=linear, symbol=...)
    """
    params = {"category": "linear", "symbol": symbol}
    r = await client.get(f"{BASE}/v5/market/tickers", params=params)
    r.raise_for_status()
    data = r.json() or {}
    rows = (data.get("result") or {}).get("list") or []
    if not rows:
        return 0.0
    try:
        return float(rows[0].get("fundingRate", 0.0))
    except Exception:
        return 0.0


# ===== Position dans l'historique (all-time) =====
async def get_alltime_range(
    client: httpx.AsyncClient,
    symbol: str,
    max_days: int = 4000,
) -> Tuple[float, float, float, int, int]:
    """
    Retourne (min_price, max_price, last_close, ts_min, ts_max)
    en scannant des klines 1D aussi loin que possible (pagination par fenêtres).
    """
    now_ms = int(time.time() * 1000)
    window_days = 900  # ~2.5 ans par bloc
    day_ms = 24 * 60 * 60 * 1000

    all_min = float("inf")
    all_max = 0.0
    last_close = 0.0
    ts_min = 0
    ts_max = 0

    scanned_days = 0
    end = now_ms

    while scanned_days < max_days:
        start = max(0, end - window_days * day_ms)
        params = {
            "category": "linear",
            "symbol": symbol,
            "interval": "D",
            "start": start,
            "end": end,
            "limit": 1000,
        }
        r = await client.get(f"{BASE}/v5/market/kline", params=params)
        r.raise_for_status()
        data = r.json() or {}
        rows = (data.get("result") or {}).get("list") or []
        if not rows:
            break

        # Format: [start, open, high, low, close, volume, turnover]
        try:
            rows.sort(key=lambda x: int(x[0]))
        except Exception:
            pass

        for row in rows:
            try:
                ts = int(row[0])
                h = float(row[2]); l = float(row[3]); c = float(row[4])
            except Exception:
                continue
            if l < all_min:
                all_min = l
                ts_min = ts
            if h > all_max:
                all_max = h
                ts_max = ts
            last_close = c  # progresse vers le plus récent du bloc

        oldest_ts = int(rows[0][0])
        if oldest_ts <= 0 or oldest_ts == start:
            break
        end = oldest_ts - 1
        scanned_days += window_days

    if all_min == float("inf"):
        all_min = 0.0
    return all_min, all_max, last_close, ts_min, ts_max


def historical_position_label(last_price: float, pmin: float, pmax: float) -> Tuple[float, str]:
    """
    Retourne (ratio, label) où ratio = (last - min) / (max - min) ∈ [0,1],
    label ∈ {"bas de l'historique","milieu de l'historique","haut de l'historique"}.
    """
    if pmax <= pmin:
        return 0.0, "inconnu"
    ratio = (last_price - pmin) / (pmax - pmin)
    if ratio < 0.33:
        return ratio, "bas de l'historique"
    if ratio < 0.66:
        return ratio, "milieu de l'historique"
    return ratio, "haut de l'historique"
