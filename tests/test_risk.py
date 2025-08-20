import pytest

from risk import calc_risk_score, compute_volatility


def test_compute_volatility() -> None:
    vol = compute_volatility([100, 110, 105])
    assert vol == pytest.approx(10.2851895, rel=1e-3)


def test_calc_risk_score() -> None:
    vol = 10.0
    score = calc_risk_score(True, False, False, vol)
    assert score == pytest.approx(0.7 * (1 / 3) + 0.3 * 1)
