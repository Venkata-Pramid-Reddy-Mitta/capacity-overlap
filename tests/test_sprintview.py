"""The naive aggregate: it must reproduce the averaging that hides concentration, exactly."""

from __future__ import annotations

from datetime import date

from capacity_overlap.config import AnalysisConfig
from capacity_overlap.model import Assignment, Plan, Sprint
from capacity_overlap.overlap import build_timelines
from capacity_overlap.sprintview import sprint_utilizations

MON = date(2026, 4, 13)
TUE = date(2026, 4, 14)
WED = date(2026, 4, 15)
FRI = date(2026, 4, 17)
SPRINT = Sprint(1, MON, FRI)  # one five working-day sprint


def util_for(*assignments, config=None):
    plan = Plan(assignments=tuple(assignments), sprints=(SPRINT,))
    tls = build_timelines(plan)
    utils = sprint_utilizations(plan, tls, config or AnalysisConfig())
    return {u.person_id: u for u in utils}


def a(person="p01", start=MON, end=FRI, alloc=0.5, ws="cloud-migration", task="t"):
    return Assignment(person, "N. Name", ws, start, end, alloc, task)


def test_a_half_time_full_sprint_assignment_reads_fifty_percent():
    u = util_for(a(alloc=0.5))["p01"]
    assert u.utilization_pct == 50.0


def test_capacity_person_days_is_capacity_times_working_days():
    u = util_for(a())["p01"]
    assert u.capacity_person_days == 5.0


def test_two_concurrent_half_time_tasks_read_one_hundred_percent_for_the_sprint():
    # Full overlap every day: load is 1.0 all five days, the aggregate is exactly 100%.
    u = util_for(a(task="x", alloc=0.5), a(task="y", ws="data-migration", alloc=0.5))["p01"]
    assert u.utilization_pct == 100.0
    assert u.reads_healthy() is True


def test_concentration_and_spread_read_the_same_aggregate():
    # The whole point: 2.0 FTE on one day equals 0.4 FTE on five days in the sprint sum.
    concentrated = util_for(
        a(task="base", alloc=0.5),
        a(task="spike", start=WED, end=WED, ws="data-migration", alloc=1.0),
    )["p01"]
    # base 0.5 x 5 = 2.5, spike 1.0 x 1 = 1.0, total 3.5 over 5 = 70%
    assert concentrated.utilization_pct == 70.0


def test_a_person_sum_above_capacity_reads_above_one_hundred_percent():
    u = util_for(
        a(task="base", alloc=0.7),
        a(task="pull", start=MON, end=FRI, ws="data-migration", alloc=0.6),
    )["p01"]
    assert u.utilization_pct > 100.0
    assert u.reads_healthy() is False


def test_a_person_with_no_assignments_reads_zero():
    plan = Plan(
        assignments=(a(person="p01"), a(person="p02", task="t2")),
        sprints=(SPRINT,),
    )
    tls = build_timelines(plan)
    # Drop p02 from the timelines to model a person with no load in this sprint.
    tls.pop("p02", None)
    utils = {u.person_id: u for u in sprint_utilizations(plan, tls, AnalysisConfig())}
    assert utils["p02"].utilization_pct == 0.0


def test_utilization_is_zero_when_capacity_is_zero_days():
    # A degenerate sprint with no working days must not divide by zero.
    plan = Plan(assignments=(a(),), sprints=(Sprint(1, date(2026, 4, 18), date(2026, 4, 19)),))
    tls = build_timelines(plan)
    utils = sprint_utilizations(plan, tls, AnalysisConfig())
    assert utils[0].utilization == 0.0
