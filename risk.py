"""Risk and short-scoring utilities."""
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
    vol_score = min(volatility / 5, 1.0)  # 5% return std dev == max
    return 0.7 * signal_score + 0.3 * vol_score


def calc_short_score(funding_rate: float, price_position: float, oi_delta_pct: float) -> float:
    """Return 0..1 score indicating short opportunity strength.

    Parameters
    ----------
    funding_rate: float
        Current funding rate as a decimal (e.g. ``-0.0005`` for ``-0.05%``).
        Negative funding implies traders are short biased and is favourable for
        initiating new short positions. A rate ``<= -1%`` yields the maximum
        contribution while positive rates give 0.

    price_position: float
        Ratio of the current price within its historical range where ``0``
        represents the all-time low and ``1`` the all-time high. Shorting is
        preferred when this ratio is high (price near its highs).

    oi_delta_pct: float
        Percentage change in open interest over the last hour. A negative change
        indicates positions are closing which can strengthen the short bias.

    Returns
    -------
    float
        Combined score in ``[0, 1]``. Higher values suggest better conditions to
        open a short.
    """

    # Funding score: negative funding up to -1% scales 0..1
    funding_score = min(max(-funding_rate * 100, 0.0), 1.0)

    # Price score: directly use the ratio (high price => high score)
    price_score = min(max(price_position, 0.0), 1.0)

    # Open interest score: falling OI up to -5% over 1h scales 0..1
    oi_score = min(max(-oi_delta_pct / 5.0, 0.0), 1.0)

    return 0.5 * funding_score + 0.3 * price_score + 0.2 * oi_score

