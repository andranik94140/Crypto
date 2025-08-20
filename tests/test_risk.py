import pytest

from risk import calc_risk_score, compute_volatility, calc_short_score


def test_compute_volatility() -> None:
    vol = compute_volatility([100, 110, 105])
    assert vol == pytest.approx(10.2851895, rel=1e-3)


def test_calc_risk_score() -> None:
    vol = 10.0
    score = calc_risk_score(True, False, False, vol)
    assert score == pytest.approx(0.7 * (1 / 3) + 0.3 * 1)


def test_calc_short_score() -> None:
    base = calc_short_score(-0.01, 0.8, -10)
    high_liq = calc_short_score(-0.01, 0.8, -10, 0.8)
    low = calc_short_score(0.01, 0.2, 5, 0.1)
    assert base == pytest.approx(0.94, rel=1e-3)
    assert high_liq == pytest.approx(1.0, rel=1e-3)
    assert low == pytest.approx(0.08, rel=1e-3)
