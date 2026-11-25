"""The reconciliation: where the day-level view and the sprint view are set against each other.

A (person, sprint) pair is 'hidden over-allocation' when the sprint utilization reads at or below
100% and yet at least one day inside that sprint is over the threshold. That intersection is the
whole product: the aggregate says healthy, the days say otherwise. Everything the report and the
CLI exit code are built on is computed once here, so there is a single definition of the headline
number rather than one per consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .calendar import count_working_days
from .config import AnalysisConfig
from .model import Plan
from .overlap import OverDay, PersonTimeline, build_timelines
from .sprintview import SprintUtilization, sprint_utilizations


@dataclass(frozen=True)
class PersonSprintFinding:
    """The two views reconciled for one person in one sprint."""

    person_id: str
    person_name: str
    sprint_index: int
    utilization_pct: float
    peak_load: float
    over_days: tuple[OverDay, ...]
    slack_days: int  # working days in the sprint below capacity: room the clash could move into

    @property
    def over_person_days(self) -> float:
        return round(sum(od.excess for od in self.over_days), 10)

    @property
    def reads_healthy(self) -> bool:
        return self.utilization_pct <= 100.0 + 1e-9

    @property
    def is_conflicted(self) -> bool:
        return len(self.over_days) > 0

    @property
    def is_hidden(self) -> bool:
        """Healthy on the aggregate, conflicted on the days. The case the tool is built to find."""
        return self.reads_healthy and self.is_conflicted

    @property
    def peak_pct(self) -> float:
        return round(self.peak_load * 100, 1)


@dataclass(frozen=True)
class Analysis:
    """The full result: per person-sprint findings plus the aggregates the README leads with."""

    findings: tuple[PersonSprintFinding, ...]
    config: AnalysisConfig
    people_total: int
    workstreams_total: int
    sprints_total: int
    horizon_working_days: int
    _timelines: dict[str, PersonTimeline] = field(default=None, compare=False, repr=False)

    # --- aggregates, each the sum of a clearly named subset of findings ---

    @property
    def total_over_person_days(self) -> float:
        return round(sum(f.over_person_days for f in self.findings), 10)

    @property
    def hidden_over_person_days(self) -> float:
        return round(sum(f.over_person_days for f in self.findings if f.is_hidden), 10)

    @property
    def visible_over_person_days(self) -> float:
        return round(self.total_over_person_days - self.hidden_over_person_days, 10)

    @property
    def hidden_findings(self) -> list[PersonSprintFinding]:
        return [f for f in self.findings if f.is_hidden]

    @property
    def green_conflicted_pairs(self) -> int:
        return len(self.hidden_findings)

    @property
    def people_conflicted_while_green(self) -> int:
        return len({f.person_id for f in self.hidden_findings})

    @property
    def reschedulable_slack_days(self) -> int:
        """Below-capacity working days inside the same sprints that hide a conflict.

        The number that turns the finding into an action: the clash is concentration, not a
        shortfall, so this is how many days of room exist in the same sprint to move it into.
        """
        return sum(f.slack_days for f in self.hidden_findings)

    @property
    def hidden_share_pct(self) -> float:
        """Share of all over-allocation the sprint view cannot see. The uncomfortable fraction."""
        total = self.total_over_person_days
        if total == 0:
            return 0.0
        return round(self.hidden_over_person_days / total * 100, 1)

    def worst_hidden(self) -> PersonSprintFinding | None:
        """The green-but-conflicted person-sprint with the highest peak day. The poster child."""
        hidden = self.hidden_findings
        if not hidden:
            return None
        return max(hidden, key=lambda f: (f.peak_load, f.over_person_days))

    def gate_failed(self) -> bool:
        """True when any hidden over-allocation exists. Drives the CLI exit code."""
        return self.hidden_over_person_days > 1e-9


def analyze(plan: Plan, config: AnalysisConfig | None = None) -> Analysis:
    config = config or AnalysisConfig()
    timelines = build_timelines(plan)
    utils = {(u.person_id, u.sprint_index): u for u in sprint_utilizations(plan, timelines, config)}
    findings: list[PersonSprintFinding] = []
    for person_id in plan.people():
        tl = timelines.get(person_id)
        for sprint in plan.sprints:
            u: SprintUtilization = utils[(person_id, sprint.index)]
            over = _over_days_in_sprint(tl, sprint, config)
            peak = _peak_in_sprint(tl, sprint)
            slack = _slack_days_in_sprint(tl, sprint, config)
            findings.append(
                PersonSprintFinding(
                    person_id=person_id,
                    person_name=plan.name_of(person_id),
                    sprint_index=sprint.index,
                    utilization_pct=u.utilization_pct,
                    peak_load=peak,
                    over_days=tuple(over),
                    slack_days=slack,
                )
            )
    return Analysis(
        findings=tuple(findings),
        config=config,
        people_total=len(plan.people()),
        workstreams_total=len(plan.workstreams()),
        sprints_total=len(plan.sprints),
        horizon_working_days=len(plan.calendar),
        _timelines=timelines,
    )


def _over_days_in_sprint(tl, sprint, config) -> list[OverDay]:
    if tl is None:
        return []
    return [od for od in tl.over_days(config) if sprint.start <= od.day <= sprint.end]


def _peak_in_sprint(tl, sprint) -> float:
    if tl is None:
        return 0.0
    loads = [load for day, load in tl.loads.items() if sprint.start <= day <= sprint.end]
    return max(loads, default=0.0)


def _slack_days_in_sprint(tl, sprint, config) -> int:
    """Working days in the sprint whose load is strictly below capacity (room to move work into)."""
    working = count_working_days(sprint.start, sprint.end)
    if tl is None:
        return working
    threshold = config.capacity_fte
    at_or_over = sum(
        1
        for day, load in tl.loads.items()
        if sprint.start <= day <= sprint.end and load >= threshold - 1e-9
    )
    return working - at_or_over
