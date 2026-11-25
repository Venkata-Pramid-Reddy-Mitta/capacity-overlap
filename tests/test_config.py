"""The two numbers that decide the verdict, validated at the boundary."""

from __future__ import annotations

import pytest

from capacity_overlap.config import AnalysisConfig


def test_default_capacity_is_one_full_time_equivalent():
    assert AnalysisConfig().capacity_fte == 1.0


def test_default_tolerance_is_zero_so_the_tool_reports_the_plans_own_arithmetic():
    assert AnalysisConfig().tolerance == 0.0


def test_the_threshold_is_capacity_plus_tolerance():
    assert AnalysisConfig(capacity_fte=1.0, tolerance=0.25).over_allocation_threshold == 1.25


def test_a_non_positive_capacity_is_rejected():
    with pytest.raises(ValueError, match="capacity_fte must be positive"):
        AnalysisConfig(capacity_fte=0.0)


def test_a_negative_tolerance_is_rejected():
    with pytest.raises(ValueError, match="tolerance must be non-negative"):
        AnalysisConfig(tolerance=-0.1)
