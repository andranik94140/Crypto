"""Bybit REST API helpers."""
import httpx

BASE_URL = "https://api.bybit.com"


async def fetch_tickers(client: httpx.AsyncClient) -> list[dict]:
    """Return list of tickers with price and open interest."""
    resp = await client.get(f"{BASE_URL}/v5/market/tickers", params={"category": "linear"})
    resp.raise_for_status()
    data = resp.json()
    return data.get("result", {}).get("list", [])
