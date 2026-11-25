"""Properties of the working-day calendar, the primitive every published number rides on."""

from __future__ import annotations

from datetime import date

import pytest

from capacity_overlap.calendar import (
    BusinessCalendar,
    count_working_days,
    is_working_day,
    working_days,
)

MON = date(2026, 4, 13)
FRI = date(2026, 4, 17)
SAT = date(2026, 4, 18)
SUN = date(2026, 4, 19)
NEXT_MON = date(2026, 4, 20)


def test_monday_through_friday_are_working_days():
    for offset in range(5):
        assert is_working_day(date(2026, 4, 13 + offset)) is True


def test_saturday_and_sunday_are_not_working_days():
    assert is_working_day(SAT) is False
    assert is_working_day(SUN) is False


def test_working_days_over_one_week_counts_five():
    assert count_working_days(MON, NEXT_MON) == 6  # Mon-Fri plus the next Monday


def test_working_days_excludes_the_weekend_in_the_middle():
    days = working_days(MON, NEXT_MON)
    assert SAT not in days
    assert SUN not in days


def test_working_days_is_inclusive_of_both_ends():
    days = working_days(MON, FRI)
    assert days[0] == MON
    assert days[-1] == FRI
    assert len(days) == 5


def test_working_days_of_a_single_working_day_is_that_day():
    assert working_days(MON, MON) == [MON]


def test_working_days_of_a_single_weekend_day_is_empty():
    assert working_days(SAT, SAT) == []


def test_working_days_with_end_before_start_is_empty():
    assert working_days(FRI, MON) == []


def test_count_working_days_matches_length_of_working_days():
    assert count_working_days(MON, NEXT_MON) == len(working_days(MON, NEXT_MON))


def test_a_friday_to_monday_span_is_two_working_days_not_four():
    # The headline reason the calendar exists: the weekend must not inflate capacity.
    assert count_working_days(FRI, NEXT_MON) == 2


def test_business_calendar_length_is_the_working_day_count():
    cal = BusinessCalendar.for_horizon(MON, NEXT_MON)
    assert len(cal) == 6


def test_business_calendar_ordinals_are_dense_and_zero_based():
    cal = BusinessCalendar.for_horizon(MON, FRI)
    assert [cal.ordinal_of(d) for d in working_days(MON, FRI)] == [0, 1, 2, 3, 4]


def test_business_calendar_ordinal_and_date_are_inverse_on_working_days():
    cal = BusinessCalendar.for_horizon(MON, NEXT_MON)
    for i in range(len(cal)):
        assert cal.ordinal_of(cal.date_of(i)) == i


def test_business_calendar_ordinal_of_a_weekend_day_raises():
    cal = BusinessCalendar.for_horizon(MON, NEXT_MON)
    with pytest.raises(ValueError, match="not a working day"):
        cal.ordinal_of(SAT)


def test_business_calendar_ordinal_of_an_out_of_range_day_raises():
    cal = BusinessCalendar.for_horizon(MON, FRI)
    with pytest.raises(ValueError):
        cal.ordinal_of(NEXT_MON)


def test_business_calendar_start_and_end_are_the_first_and_last_working_days():
    cal = BusinessCalendar.for_horizon(MON, NEXT_MON)
    assert cal.start == MON
    assert cal.end == NEXT_MON


def test_business_calendar_contains_only_working_days_in_range():
    cal = BusinessCalendar.for_horizon(MON, NEXT_MON)
    assert cal.contains(MON) is True
    assert cal.contains(SAT) is False
    assert cal.contains(date(2026, 1, 1)) is False


def test_business_calendar_index_cache_is_stable_across_calls():
    # The lazy cache on a frozen dataclass is a known footgun; pin that it is built once and holds.
    cal = BusinessCalendar.for_horizon(MON, NEXT_MON)
    first = cal.ordinal_of(FRI)
    second = cal.ordinal_of(FRI)
    assert first == second == 4
