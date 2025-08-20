from detectors import detect_divergence, detect_oi_delta, detect_pump_dump


def test_detect_pump_dump() -> None:
    assert detect_pump_dump([100, 108], 8)
    assert not detect_pump_dump([100, 105], 8)


def test_detect_oi_delta() -> None:
    assert detect_oi_delta([100, 104], 3)
    assert not detect_oi_delta([100, 101], 3)


def test_detect_divergence() -> None:
    assert detect_divergence([100, 110], [100, 90])
    assert not detect_divergence([100, 110], [100, 115])
