"""The data model: assignments, sprints, and a plan that knows its own horizon.

These are plain frozen dataclasses with validation at construction, so an impossible assignment
(end before start, allocation above one, a blank person) is refused at the boundary rather than
producing a quietly wrong load later. The validation lives here, not in the ingest layer, so that
a plan built in a test is held to the same rules as one read from a CSV.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .calendar import BusinessCalendar, working_days


class PlanError(ValueError):
    """Raised when a plan or assignment breaks an invariant. The CLI maps this to exit code 3."""


@dataclass(frozen=True)
class Assignment:
    """One person committed to one task in one workstream for an inclusive date range.

    ``allocation`` is the fraction of a working day the plan commits this person to this task,
    in (0, 1]. It is a declared input, not observed effort: see ADR-003. Two assignments for the
    same person whose ranges share a working day are exactly the overlap this tool measures.
    """

    person_id: str
    person_name: str
    workstream: str
    start: date
    end: date
    allocation: float
    task_id: str = ""

    def __post_init__(self) -> None:
        if not self.person_id:
            raise PlanError("assignment has an empty person_id")
        if not self.workstream:
            raise PlanError(f"{self.person_id}: assignment has an empty workstream")
        if self.end < self.start:
            raise PlanError(
                f"{self.person_id}: assignment end {self.end} is before start {self.start}"
            )
        if not (0.0 < self.allocation <= 1.0):
            raise PlanError(f"{self.person_id}: allocation {self.allocation} is outside (0, 1]")

    def working_days(self) -> list[date]:
        return working_days(self.start, self.end)


@dataclass(frozen=True)
class Sprint:
    """A contiguous reporting window. The unit at which the naive utilization view aggregates."""

    index: int
    start: date
    end: date

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise PlanError(f"sprint {self.index} end {self.end} is before start {self.start}")


@dataclass(frozen=True)
class Plan:
    """A set of assignments plus the sprint calendar they are reported against.

    The horizon is derived from the assignments so that the day-level view and the sprint view
    cover exactly the same days; a mismatch there would let one view count a day the other cannot.
    """

    assignments: tuple[Assignment, ...]
    sprints: tuple[Sprint, ...]
    _calendar: BusinessCalendar | None = field(default=None, compare=False)

    def __post_init__(self) -> None:
        if not self.assignments:
            raise PlanError("a plan needs at least one assignment")
        if not self.sprints:
            raise PlanError("a plan needs at least one sprint")

    @property
    def horizon_start(self) -> date:
        return min(a.start for a in self.assignments)

    @property
    def horizon_end(self) -> date:
        return max(a.end for a in self.assignments)

    @property
    def calendar(self) -> BusinessCalendar:
        cached = self.__dict__.get("_calendar_cache")
        if cached is None:
            cached = BusinessCalendar.for_horizon(self.horizon_start, self.horizon_end)
            object.__setattr__(self, "_calendar_cache", cached)
        return cached

    def people(self) -> list[str]:
        return sorted({a.person_id for a in self.assignments})

    def workstreams(self) -> list[str]:
        return sorted({a.workstream for a in self.assignments})

    def name_of(self, person_id: str) -> str:
        for a in self.assignments:
            if a.person_id == person_id:
                return a.person_name
        return person_id

    def assignments_for(self, person_id: str) -> list[Assignment]:
        return [a for a in self.assignments if a.person_id == person_id]

    def sprint_on(self, day: date) -> Sprint | None:
        for s in self.sprints:
            if s.start <= day <= s.end:
                return s
        return None
