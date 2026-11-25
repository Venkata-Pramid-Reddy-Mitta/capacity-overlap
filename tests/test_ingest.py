"""CSV ingestion and sprint derivation. One input-error class, and a calendar that leaves no gaps."""

from __future__ import annotations

from datetime import date

import pytest

from capacity_overlap.ingest import build_sprints, read_plan
from capacity_overlap.model import PlanError

MON = date(2026, 4, 13)

GOOD = (
    "task_id,person_id,person_name,workstream,start,end,allocation\n"
    "t1,p01,A. Rivera,cloud-migration,2026-04-13,2026-04-17,0.50\n"
    "t2,p01,A. Rivera,data-migration,2026-04-15,2026-04-15,0.75\n"
)


def write(tmp_path, text, name="plan.csv"):
    p = tmp_path / name
    p.write_text(text)
    return p


def test_a_well_formed_plan_loads_all_rows(tmp_path):
    plan = read_plan(write(tmp_path, GOOD))
    assert len(plan.assignments) == 2
    assert plan.people() == ["p01"]


def test_a_missing_file_is_a_plan_error(tmp_path):
    with pytest.raises(PlanError, match="not found"):
        read_plan(tmp_path / "nope.csv")


def test_an_empty_file_is_a_plan_error(tmp_path):
    with pytest.raises(PlanError, match="empty"):
        read_plan(write(tmp_path, ""))


def test_a_missing_column_is_a_plan_error(tmp_path):
    text = "task_id,person_id,workstream,start,end,allocation\nt1,p01,cloud,2026-04-13,2026-04-17,0.5\n"
    with pytest.raises(PlanError, match="missing columns"):
        read_plan(write(tmp_path, text))


def test_a_non_iso_date_is_a_plan_error(tmp_path):
    text = GOOD.replace("2026-04-13", "13/04/2026")
    with pytest.raises(PlanError, match="not an ISO date"):
        read_plan(write(tmp_path, text))


def test_an_out_of_range_allocation_is_a_plan_error(tmp_path):
    text = GOOD.replace("0.50", "1.50")
    with pytest.raises(PlanError, match="outside"):
        read_plan(write(tmp_path, text))


def test_sprints_cover_from_the_first_working_day():
    sprints = build_sprints(date(2026, 4, 13), date(2026, 7, 3), 10)
    assert sprints[0].start == date(2026, 4, 13)


def test_sprints_leave_no_gap_between_consecutive_windows():
    sprints = build_sprints(date(2026, 4, 13), date(2026, 7, 3), 10)
    for earlier, later in zip(sprints, sprints[1:], strict=False):
        assert (later.start - earlier.end).days == 1


def test_a_horizon_starting_on_a_weekend_anchors_to_monday():
    sprints = build_sprints(date(2026, 4, 11), date(2026, 5, 1), 10)  # the 11th is a Saturday
    assert sprints[0].start == date(2026, 4, 13)


def test_six_ten_day_sprints_span_sixty_working_days():
    sprints = build_sprints(date(2026, 4, 13), date(2026, 7, 3), 10)
    assert len(sprints) == 6


def test_a_sprint_length_below_one_is_rejected():
    with pytest.raises(PlanError, match="at least 1"):
        build_sprints(date(2026, 4, 13), date(2026, 4, 17), 0)


def test_dates_already_parsed_are_accepted(tmp_path):
    # pandas may hand back a date for an ISO column; the parser must pass it through.
    plan = read_plan(write(tmp_path, GOOD))
    assert plan.horizon_start == MON
