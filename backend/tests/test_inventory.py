from __future__ import annotations

import pytest
from app.agents.inventory import net_requirement


def test_no_double_count():
    # Demand=10,000, Available=1,140, SafetyStock=1,750
    # Correct replenishment: 10,000 + 1,750 - 1,140 = 10,610
    # Old buggy formula returned 9,470 (under-procuring by 1,140)
    assert net_requirement(10000, 1140, 1750) == 10610


def test_surplus_is_zero():
    # High available stock (5,000) easily covers demand (1,000) + SS (500)
    assert net_requirement(1000, 5000, 500) == 0


def test_ss_topup():
    # Demand=1,000, Available=1,200, SS=500 -> Net requirement = 1000 + 500 - 1200 = 300
    assert net_requirement(1000, 1200, 500) == 300


def test_zero_everything():
    assert net_requirement(0, 0, 0) == 0
