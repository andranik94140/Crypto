"""Risk and short-scoring utilities."""
from typing import Sequence

from utils import pct_change, stddev


def _to_percentage_points(x: float) -> float:
    """
    Normalise en points de pourcentage.
    Si |x| <= 1, on considère que x est en décimal (ex: 0.02 -> 2.0).
    Sinon on suppose déjà en points de % (ex: 2.0 -> 2.0).
    """
    return x * 100.0 if -1.0 <= x <= 1.0 else x


def compute_volatility(prices: Sequence[float]) -> float:
    """Return standard deviation of price returns (en points de %)."""
    if len(prices) < 2:
        return 0.0
    returns_raw = [pct_change(prices[i - 1], prices[i]) for i in range(1, len(prices))]
    returns_pp = [_to_percentage_points(r) for r in returns_raw]
    return stddev(returns_pp)


def calc_risk_score(pump: bool, oi_delta: bool, divergence: bool, volatility: float) -> float:
    """
    Combine signals et volatilité en un score 0..1.
    'volatility' attendu en points de %, cf. compute_volatility.
    """
    signals = [pump, oi_delta, divergence]
    signal_score = sum(1.0 for s in signals if s) / len(signals)
    # 5 points de % d'écart-type des retours ~= score max sur la composante vol
    vol_score = min(max(volatility / 5.0, 0.0), 1.0)
    return 0.7 * signal_score + 0.3 * vol_score


def calc_short_score(
    funding_rate: float,
    price_position: float,
    oi_delta_pct: float,
    short_liq_ratio: float = 0.0,
) -> float:
    """Return 0..1 score indicating short opportunity strength.

    funding_rate: décimal (ex: -0.0005 pour -0.05%)
    price_position: ratio [0..1] (0=plus bas historique, 1=plus haut)
    oi_delta_pct: variation d'OI sur ~1h en points de % (ex: -3.2)
    short_liq_ratio: ratio [0..1] des liq shorts / (longs+shorts)
    """
    # Funding score: négatif → mieux pour short ; -1% -> 1.0
    funding_score = min(max(-funding_rate * 100.0, 0.0), 1.0)

    # Price score: plus proche du haut historique → mieux pour short
    price_score = min(max(price_position, 0.0), 1.0)

    # OI score: baisse de l'OI (jusqu'à -5%) → 1.0
    oi_score = min(max(-oi_delta_pct / 5.0, 0.0), 1.0)

    # Liquidations: ratio [0..1]
    liq_score = min(max(short_liq_ratio, 0.0), 1.0)

    # Poids normalisés qui somment à 1.0
    w_funding, w_price, w_oi, w_liq = 0.4, 0.3, 0.2, 0.1
    score = (w_funding * funding_score
             + w_price * price_score
             + w_oi * oi_score
             + w_liq * liq_score)
    return min(max(score, 0.0), 1.0)
