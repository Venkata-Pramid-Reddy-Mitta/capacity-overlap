"""Day-level load: the view the sprint aggregate structurally cannot produce.

This is the core of the repository. For each person it materialises every assignment onto its
working days and sums the concurrent allocations, so a day carrying two half-time tasks from two
workstreams reads 1.0 and a day carrying two full tasks reads 2.0. Over-allocation is then just
the load above the configured threshold, per day, which is a quantity the sprint view erases when
it divides a sum by a window length.

Materialising onto days (rather than returning intervals) is a deliberate choice: the report has
to show a reviewer the specific calendar days that clash, and a day-indexed load is directly
inspectable. The cost is memory proportional to people times horizon days, which ADR-001 prices.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from .config import AnalysisConfig
from .model import Plan


@dataclass(frozen=True)
class OverDay:
    """A single working day on which a person's summed allocation exceeds the threshold."""

    day: date
    load: float
    excess: float  # load minus the threshold; the person-day cost of this one day's clash


@dataclass(frozen=True)
class PersonTimeline:
    """One person's daily load across the whole horizon, plus the derived over-allocated days."""

    person_id: str
    loads: dict[date, float]  # only days with any load are present

    def load_on(self, day: date) -> float:
        return self.loads.get(day, 0.0)

    def peak(self) -> float:
        return max(self.loads.values(), default=0.0)

    def over_days(self, config: AnalysisConfig) -> list[OverDay]:
        threshold = config.over_allocation_threshold
        out: list[OverDay] = []
        for day in sorted(self.loads):
            load = self.loads[day]
            if load > threshold + _EPSILON:
                out.append(OverDay(day=day, load=load, excess=round(load - threshold, 10)))
        return out


# Floating allocations (0.5, 0.25) sum exactly in binary often enough, but 0.1-style inputs do
# not, so comparisons use a tolerance. 1e-9 is far below any allocation granularity a plan uses.
_EPSILON = 1e-9


def build_timelines(plan: Plan) -> dict[str, PersonTimeline]:
    """Sum each person's assignments onto their working days.

    The accumulation is the overlap detection: two assignments contribute to the same day key
    exactly when their inclusive date ranges share a working day. Weekends never receive load
    because ``Assignment.working_days`` already excludes them.
    """
    stacks: dict[str, dict[date, float]] = defaultdict(lambda: defaultdict(float))
    for a in plan.assignments:
        person = stacks[a.person_id]
        for day in a.working_days():
            person[day] += a.allocation
    return {pid: PersonTimeline(person_id=pid, loads=dict(days)) for pid, days in stacks.items()}


def total_over_person_days(timelines: dict[str, PersonTimeline], config: AnalysisConfig) -> float:
    """Sum of every day's excess over threshold, across all people. The full over-allocation."""
    total = 0.0
    for tl in timelines.values():
        total += sum(od.excess for od in tl.over_days(config))
    return round(total, 10)
