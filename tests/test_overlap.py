"""The day-level load core: accumulation is overlap detection, and over-days are its output."""

from __future__ import annotations

from datetime import date

from capacity_overlap.config import AnalysisConfig
from capacity_overlap.model import Assignment, Plan, Sprint
from capacity_overlap.overlap import build_timelines, total_over_person_days

MON = date(2026, 4, 13)
TUE = date(2026, 4, 14)
WED = date(2026, 4, 15)
FRI = date(2026, 4, 17)


def assignment(person="p01", ws="cloud-migration", start=MON, end=FRI, alloc=0.5, task="t"):
    return Assignment(person, "N. Name", ws, start, end, alloc, task)


def plan_of(*assignments):
    return Plan(assignments=tuple(assignments), sprints=(Sprint(1, MON, date(2026, 4, 24)),))


def test_a_single_assignment_puts_its_allocation_on_each_working_day():
    tl = build_timelines(plan_of(assignment(alloc=0.4)))["p01"]
    assert tl.load_on(MON) == 0.4
    assert tl.load_on(FRI) == 0.4


def test_two_assignments_on_the_same_day_sum_their_allocations():
    tl = build_timelines(
        plan_of(
            assignment(task="a", ws="cloud-migration", alloc=0.5),
            assignment(task="b", ws="data-migration", alloc=0.6),
        )
    )["p01"]
    assert tl.load_on(WED) == 1.1


def test_non_overlapping_assignments_do_not_stack():
    tl = build_timelines(
        plan_of(
            assignment(task="a", start=MON, end=TUE, alloc=0.8),
            assignment(task="b", start=date(2026, 4, 20), end=date(2026, 4, 21), alloc=0.8),
        )
    )["p01"]
    assert tl.load_on(MON) == 0.8
    assert tl.load_on(date(2026, 4, 20)) == 0.8


def test_weekend_days_never_receive_load():
    tl = build_timelines(plan_of(assignment(start=MON, end=date(2026, 4, 20))))["p01"]
    assert tl.load_on(date(2026, 4, 18)) == 0.0


def test_peak_is_the_highest_daily_load():
    tl = build_timelines(
        plan_of(
            assignment(task="a", alloc=0.5),
            assignment(task="b", start=WED, end=WED, ws="data-migration", alloc=0.75),
        )
    )["p01"]
    assert tl.peak() == 1.25


def test_a_person_with_only_weekend_dates_has_an_empty_timeline():
    # An assignment that spans only a weekend carries no working days, so the person's load is empty.
    tl = build_timelines(plan_of(assignment(start=date(2026, 4, 18), end=date(2026, 4, 19))))["p01"]
    assert tl.loads == {}
    assert tl.peak() == 0.0


def test_over_days_lists_only_days_above_the_threshold():
    tl = build_timelines(
        plan_of(
            assignment(task="a", alloc=0.6),
            assignment(task="b", start=WED, end=WED, ws="data-migration", alloc=0.6),
        )
    )["p01"]
    over = tl.over_days(AnalysisConfig())
    assert [od.day for od in over] == [WED]
    assert over[0].load == 1.2
    assert abs(over[0].excess - 0.2) < 1e-9


def test_a_day_exactly_at_capacity_is_not_over_allocated():
    tl = build_timelines(
        plan_of(
            assignment(task="a", alloc=0.5),
            assignment(task="b", ws="data-migration", alloc=0.5),
        )
    )["p01"]
    assert tl.over_days(AnalysisConfig()) == []


def test_tolerance_raises_the_bar_before_a_day_counts():
    tl = build_timelines(
        plan_of(
            assignment(task="a", alloc=0.6),
            assignment(task="b", ws="data-migration", alloc=0.6),
        )
    )["p01"]
    # Load is 1.2; a tolerance of 0.25 means 1.25 is the bar, so 1.2 no longer counts.
    assert tl.over_days(AnalysisConfig(tolerance=0.25)) == []


def test_total_over_person_days_sums_excess_across_people():
    plan = Plan(
        assignments=(
            assignment(person="p01", task="a", alloc=0.6),
            assignment(person="p01", task="b", ws="data-migration", alloc=0.6),
            assignment(person="p02", task="c", alloc=0.7),
            assignment(person="p02", task="d", ws="data-migration", alloc=0.7),
        ),
        sprints=(Sprint(1, MON, FRI),),
    )
    tls = build_timelines(plan)
    # p01: 0.2 excess on 5 days = 1.0; p02: 0.4 excess on 5 days = 2.0; total 3.0.
    assert total_over_person_days(tls, AnalysisConfig()) == 3.0
