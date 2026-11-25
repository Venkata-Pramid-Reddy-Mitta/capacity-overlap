"""Invariants of the data model. Validation lives in the model, so these guard every entry point."""

from __future__ import annotations

from datetime import date

import pytest

from capacity_overlap.model import Assignment, Plan, PlanError, Sprint

MON = date(2026, 4, 13)
FRI = date(2026, 4, 17)


def make_assignment(**kw) -> Assignment:
    base = {
        "person_id": "p01",
        "person_name": "A. Rivera",
        "workstream": "cloud-migration",
        "start": MON,
        "end": FRI,
        "allocation": 0.5,
        "task_id": "t1",
    }
    base.update(kw)
    return Assignment(**base)


def make_plan(assignments=None, sprints=None) -> Plan:
    assignments = assignments or (make_assignment(),)
    sprints = sprints or (Sprint(index=1, start=MON, end=FRI),)
    return Plan(assignments=tuple(assignments), sprints=tuple(sprints))


def test_a_valid_assignment_is_accepted():
    a = make_assignment()
    assert a.allocation == 0.5


def test_an_empty_person_id_is_rejected():
    with pytest.raises(PlanError, match="empty person_id"):
        make_assignment(person_id="")


def test_an_empty_workstream_is_rejected():
    with pytest.raises(PlanError, match="empty workstream"):
        make_assignment(workstream="")


def test_an_end_before_start_is_rejected():
    with pytest.raises(PlanError, match="before start"):
        make_assignment(start=FRI, end=MON)


def test_an_allocation_of_zero_is_rejected():
    with pytest.raises(PlanError, match="outside"):
        make_assignment(allocation=0.0)


def test_an_allocation_above_one_is_rejected():
    with pytest.raises(PlanError, match="outside"):
        make_assignment(allocation=1.5)


def test_an_allocation_of_exactly_one_is_accepted():
    assert make_assignment(allocation=1.0).allocation == 1.0


def test_assignment_working_days_excludes_weekends():
    a = make_assignment(start=MON, end=date(2026, 4, 20))
    assert date(2026, 4, 18) not in a.working_days()
    assert len(a.working_days()) == 6


def test_a_sprint_with_end_before_start_is_rejected():
    with pytest.raises(PlanError, match="before start"):
        Sprint(index=1, start=FRI, end=MON)


def test_a_plan_needs_at_least_one_assignment():
    with pytest.raises(PlanError, match="at least one assignment"):
        Plan(assignments=(), sprints=(Sprint(index=1, start=MON, end=FRI),))


def test_a_plan_needs_at_least_one_sprint():
    with pytest.raises(PlanError, match="at least one sprint"):
        Plan(assignments=(make_assignment(),), sprints=())


def test_plan_horizon_spans_the_earliest_start_to_the_latest_end():
    plan = make_plan(
        assignments=(
            make_assignment(start=MON, end=FRI),
            make_assignment(task_id="t2", start=date(2026, 4, 20), end=date(2026, 4, 24)),
        )
    )
    assert plan.horizon_start == MON
    assert plan.horizon_end == date(2026, 4, 24)


def test_plan_people_are_sorted_and_unique():
    plan = make_plan(
        assignments=(
            make_assignment(person_id="p02"),
            make_assignment(person_id="p01", task_id="t2"),
            make_assignment(person_id="p02", task_id="t3"),
        )
    )
    assert plan.people() == ["p01", "p02"]


def test_plan_workstreams_are_sorted_and_unique():
    plan = make_plan(
        assignments=(
            make_assignment(workstream="testing-deployment"),
            make_assignment(workstream="cloud-migration", task_id="t2"),
        )
    )
    assert plan.workstreams() == ["cloud-migration", "testing-deployment"]


def test_plan_name_of_returns_the_persons_name():
    assert make_plan().name_of("p01") == "A. Rivera"


def test_plan_name_of_falls_back_to_the_id_for_an_unknown_person():
    assert make_plan().name_of("p99") == "p99"


def test_plan_assignments_for_filters_by_person():
    plan = make_plan(
        assignments=(
            make_assignment(person_id="p01"),
            make_assignment(person_id="p02", task_id="t2"),
        )
    )
    assert len(plan.assignments_for("p01")) == 1


def test_plan_sprint_on_finds_the_containing_sprint():
    plan = make_plan(sprints=(Sprint(1, MON, FRI), Sprint(2, date(2026, 4, 20), date(2026, 4, 24))))
    assert plan.sprint_on(date(2026, 4, 21)).index == 2


def test_plan_sprint_on_returns_none_outside_every_sprint():
    assert make_plan().sprint_on(date(2026, 9, 1)) is None


def test_plan_calendar_covers_the_whole_horizon():
    plan = make_plan(assignments=(make_assignment(start=MON, end=date(2026, 4, 24)),))
    assert plan.calendar.start == MON
    assert plan.calendar.end == date(2026, 4, 24)
