from __future__ import annotations
import httpx

BASE = "https://api.bybit.com"

async def fetch_usdt_perp_symbols(client: httpx.AsyncClient) -> list[str]:
    """Retourne la liste des symboles USDT perp (Bybit v5)."""
    symbols: list[str] = []
    cursor = None
    while True:
        params = {"category": "linear"}
        if cursor:
            params["cursor"] = cursor
        r = await client.get(f"{BASE}/v5/market/instruments-info", params=params)
        r.raise_for_status()
        data = r.json()
        items = (data.get("result") or {}).get("list") or []
        symbols += [it["symbol"] for it in items if str(it.get("symbol","")).endswith("USDT")]
        cursor = (data.get("result") or {}).get("nextPageCursor")
        if not cursor:
            break
    return symbols

async def get_oi_1h_change(client: httpx.AsyncClient, symbol: str) -> tuple[float,float,float]:
    """
    Retourne (oi_1h_ago, oi_last, delta_pct) à partir de /v5/market/open-interest
    periodisé 5min, limit=13 (~65min) pour couvrir '≈1h'.
    """
    params = {
        "category": "linear",
        "symbol": symbol,
        "intervalTime": "5min",
        "limit": 13,
    }
    r = await client.get(f"{BASE}/v5/market/open-interest", params=params)
    r.raise_for_status()
    data = r.json()
    rows = (data.get("result") or {}).get("list") or []
    if not rows:
        return 0.0, 0.0, 0.0

    def _ts(row):
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

async def get_volume_1h_change(client: httpx.AsyncClient, symbol: str) -> tuple[float, float, float, float, float, float]:
    """
    Retourne (vol_1h_ago, vol_last, vol_delta_pct, notional_1h_ago, notional_last, notional_delta_pct)
    à partir de /v5/market/kline en 5min, limit=13 (~65min).

    - volume  : quantité (base) du contrat échangée sur l'intervalle
    - turnover: notionnel (quote, USDT) échangé sur l'intervalle
    """
    params = {
        "category": "linear",
        "symbol": symbol,
        "interval": "5",  # 5 minutes
        "limit": 13,      # ~1h
    }
    r = await client.get(f"{BASE}/v5/market/kline", params=params)
    r.raise_for_status()
    data = r.json()
    rows = (data.get("result") or {}).get("list") or []
    if not rows:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

    # Bybit renvoie souvent les klines du plus récent au plus ancien -> on trie par timestamp croissant
    def _ts(row):
        # format attendu: [start, open, high, low, close, volume, turnover]
        try:
            return int(row[0])
        except Exception:
            return 0
    try:
        rows = sorted(rows, key=_ts)
    except Exception:
        pass

    def _to_float(x):
        try:
            return float(x)
        except Exception:
            return 0.0

    # Dernier intervalle
    last = rows[-1]
    vol_last = _to_float(last[5])
    notional_last = _to_float(last[6])

    # Intervalle ~1h avant (le premier de la fenêtre)
    first = rows[0]
    vol_1h_ago = _to_float(first[5])
    notional_1h_ago = _to_float(first[6])

    vol_delta_pct = ((vol_last - vol_1h_ago) / vol_1h_ago * 100.0) if vol_1h_ago else 0.0
    notional_delta_pct = ((notional_last - notional_1h_ago) / notional_1h_ago * 100.0) if notional_1h_ago else 0.0

    return vol_1h_ago, vol_last, vol_delta_pct, notional_1h_ago, notional_last, notional_delta_pct
