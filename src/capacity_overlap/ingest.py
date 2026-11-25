"""Read a plan CSV into the model, and derive the sprint calendar it is reported against.

pandas does the parsing because a resource plan is a spreadsheet in every shop this is aimed at,
and meeting it as a table is the honest interface. The algorithm core does not touch pandas: it
works on the frozen dataclasses this module produces, so the hot path stays plain Python and the
dependency sits only at the edge. Validation is delegated to the model so a hand-built plan in a
test and a parsed plan obey the same rules.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from .calendar import is_working_day
from .model import Assignment, Plan, PlanError, Sprint

REQUIRED_COLUMNS = (
    "task_id",
    "person_id",
    "person_name",
    "workstream",
    "start",
    "end",
    "allocation",
)


def read_plan(path: str | Path, sprint_working_days: int = 10) -> Plan:
    """Parse a plan CSV and attach a derived sprint calendar.

    Raises PlanError (which the CLI maps to exit code 3) for a missing column, an unparseable date,
    or any assignment that fails the model's invariants. A missing file is also a PlanError rather
    than a bare OSError so the CLI reports one input-error class.
    """
    p = Path(path)
    if not p.exists():
        raise PlanError(f"plan file not found: {p}")
    try:
        frame = pd.read_csv(
            p, dtype={"task_id": str, "person_id": str, "person_name": str, "workstream": str}
        )
    except pd.errors.EmptyDataError as exc:
        raise PlanError(f"plan file is empty: {p}") from exc

    missing = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
    if missing:
        raise PlanError(f"plan is missing columns: {', '.join(missing)}")

    assignments = tuple(_row_to_assignment(i, row) for i, row in frame.iterrows())
    sprints = build_sprints(
        min(a.start for a in assignments),
        max(a.end for a in assignments),
        sprint_working_days,
    )
    return Plan(assignments=assignments, sprints=sprints)


def _row_to_assignment(index: int, row: pd.Series) -> Assignment:
    try:
        start = _parse_date(row["start"])
        end = _parse_date(row["end"])
        allocation = float(row["allocation"])
    except (ValueError, TypeError) as exc:
        raise PlanError(f"row {index}: {exc}") from exc
    return Assignment(
        person_id=str(row["person_id"]).strip(),
        person_name=str(row["person_name"]).strip(),
        workstream=str(row["workstream"]).strip(),
        start=start,
        end=end,
        allocation=allocation,
        task_id=str(row["task_id"]).strip(),
    )


def _parse_date(value: object) -> date:
    if isinstance(value, date):
        return value
    text = str(value).strip()
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"'{text}' is not an ISO date (YYYY-MM-DD)") from exc


def build_sprints(start: date, end: date, sprint_working_days: int) -> tuple[Sprint, ...]:
    """Partition the horizon into consecutive blocks of N working days, anchored to the first one.

    Sprints are a calendar imposed on the plan, not a column in it, so the same assignments can be
    re-reported under a different cadence (the aggregation-window experiment does exactly that).
    Each sprint spans from its first working day to the calendar day before the next sprint starts,
    so weekends belong to the sprint that precedes them and no day falls between two sprints.
    """
    if sprint_working_days < 1:
        raise PlanError(f"sprint_working_days must be at least 1, got {sprint_working_days}")
    # Anchor on the first working day at or after the horizon start.
    anchor = start
    while not is_working_day(anchor):
        anchor += timedelta(days=1)

    sprints: list[Sprint] = []
    index = 1
    sprint_start = anchor
    while sprint_start <= end:
        sprint_end = _nth_working_day_end(sprint_start, sprint_working_days)
        sprints.append(Sprint(index=index, start=sprint_start, end=sprint_end))
        sprint_start = sprint_end + timedelta(days=1)
        index += 1
    return tuple(sprints)


def _nth_working_day_end(sprint_start: date, sprint_working_days: int) -> date:
    """The calendar day that closes a sprint of N working days beginning on sprint_start.

    Returns the day before the following working day after the Nth, so trailing weekend days are
    kept inside the sprint rather than orphaned.
    """
    seen = 0
    cursor = sprint_start
    last_working = sprint_start
    while True:
        if is_working_day(cursor):
            seen += 1
            last_working = cursor
            if seen == sprint_working_days:
                break
        cursor += timedelta(days=1)
    # Extend through any weekend that follows the last working day.
    tail = last_working + timedelta(days=1)
    while not is_working_day(tail):
        last_working = tail
        tail += timedelta(days=1)
    return last_working
