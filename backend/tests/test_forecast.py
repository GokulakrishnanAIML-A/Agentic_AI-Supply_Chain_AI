from __future__ import annotations

import pytest
from app.agents.demand import _seasonal_forecast


def test_seasonal_forecast_with_full_history():
    # 24 months of synthetic seasonal order data
    base_year = [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1500, 1400, 1300, 1200, 1100]
    history = [{"month": f"2023-{i+1:02d}", "quantity": q} for i, q in enumerate(base_year)]
    history += [{"month": f"2024-{i+1:02d}", "quantity": int(q * 1.1)} for i, q in enumerate(base_year)]

    fc, method = _seasonal_forecast(history)
    assert method == "seasonal_naive_blend_3ma"
    assert fc > 0
    # Expected: 0.55 * prev[-1] (1100 from year 1) + 0.45 * recent (mean(1430, 1320, 1210) = 1320 from year 2)
    expected = int(round(0.55 * 1100 + 0.45 * 1320))  # 605 + 594 = 1199
    assert fc == expected



def test_forecast_short_history():
    short_history = [
        {"month": "2024-06", "quantity": 500},
        {"month": "2024-07", "quantity": 600},
        {"month": "2024-08", "quantity": 700},
    ]
    fc, method = _seasonal_forecast(short_history)
    assert method == "trailing_mean"
    assert fc == 600


def test_forecast_empty_history():
    fc, method = _seasonal_forecast([])
    assert method == "no_history"
    assert fc == 0
