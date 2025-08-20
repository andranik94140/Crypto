import pytest

from utils import ema, pct_change, stddev, window


def test_pct_change() -> None:
    assert pct_change(100, 110) == pytest.approx(10)
    assert pct_change(0, 50) == 0


def test_ema() -> None:
    assert ema([1, 1, 1, 1], 3) == 1
    assert ema([1, 2, 3], 3) == pytest.approx(2.25)


def test_window() -> None:
    assert list(window([1, 2, 3, 4], 2)) == [[1, 2], [2, 3], [3, 4]]


def test_stddev() -> None:
    assert stddev([1, 2, 3]) == pytest.approx(1.0)
