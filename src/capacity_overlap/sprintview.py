"""The naive sprint-level utilization view: the artefact this tool exists to contradict.

A resource plan is normally read one number per person per sprint: planned effort divided by
capacity for the window. That number is faithfully reproduced here, including the thing that makes
it misleading. It sums each day's load over the sprint and divides by capacity times the number of
working days, so a person whose work is concentrated into a few double-booked days reads the same
as one whose identical total is spread evenly. The averaging is the flaw, and reproducing it
exactly is what lets a test put the two views side by side.
"""

from __future__ import annotations

from dataclasses import dataclass

from .calendar import count_working_days
from .config import AnalysisConfig
from .model import Plan, Sprint
from .overlap import PersonTimeline


@dataclass(frozen=True)
class SprintUtilization:
    """One person's aggregate utilization for one sprint: what the status report shows."""

    person_id: str
    sprint_index: int
    assigned_person_days: float
    capacity_person_days: float

    @property
    def utilization(self) -> float:
        if self.capacity_person_days == 0:
            return 0.0
        return self.assigned_person_days / self.capacity_person_days

    @property
    def utilization_pct(self) -> float:
        return round(self.utilization * 100, 1)

    def reads_healthy(self) -> bool:
        """The plan looks fine for this person-sprint: utilization at or below full capacity."""
        return self.utilization <= 1.0 + 1e-9


def sprint_utilizations(
    plan: Plan, timelines: dict[str, PersonTimeline], config: AnalysisConfig
) -> list[SprintUtilization]:
    """Aggregate each person's daily load to one utilization per sprint.

    The numerator sums the raw daily load, not the load clipped at capacity, which is what a
    timesheet rollup does: a day planned at 2.0 FTE contributes 2.0 planned person-days. That is
    why a person can still read above 100% here; when they do, the over-allocation is visible and
    this tool is not needed. The hidden case is the one that reads at or below 100%.
    """
    out: list[SprintUtilization] = []
    for person_id in plan.people():
        tl = timelines.get(person_id)
        for sprint in plan.sprints:
            assigned = _assigned_in_sprint(tl, sprint)
            capacity = config.capacity_fte * count_working_days(sprint.start, sprint.end)
            out.append(
                SprintUtilization(
                    person_id=person_id,
                    sprint_index=sprint.index,
                    assigned_person_days=round(assigned, 10),
                    capacity_person_days=round(capacity, 10),
                )
            )
    return out


def _assigned_in_sprint(tl: PersonTimeline | None, sprint: Sprint) -> float:
    if tl is None:
        return 0.0
    return sum(load for day, load in tl.loads.items() if sprint.start <= day <= sprint.end)
