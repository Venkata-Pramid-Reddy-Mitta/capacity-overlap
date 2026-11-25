"""Working-day calendar: the primitive that both the aggregate and the day-level view ride on.

Why this file exists at all: every number in this repository changes depending on whether a
weekend counts as capacity. A plan that runs Friday to Monday spans four calendar days but
two working days. If the sprint denominator counts calendar days it reads a lower utilization
than reality, which makes the aggregate even more forgiving than the flaw this tool is about.
So working days are computed in exactly one place, here, and everything else asks this module.

The second job of this module is to map a date to a dense business-day ordinal. Overlap
detection is cleanest when concurrent intervals share an index; with weekends removed from the
number line, two tasks that run across the same working days share the same ordinals and their
allocations add. ``ordinal_of`` and ``date_of`` are inverses on working days only, by design:
a weekend date has no ordinal because it carries no capacity.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

# Monday is 0 and Sunday is 6 in date.weekday(); Saturday and Sunday are non-working.
_WEEKEND = {5, 6}


def is_working_day(day: date) -> bool:
    """True for Monday to Friday. No holiday calendar: ADR-002 explains why that is a boundary."""
    return day.weekday() not in _WEEKEND


def working_days(start: date, end: date) -> list[date]:
    """Inclusive list of working days from start to end.

    Inclusive of both ends on purpose: a task assigned 'start to end' is worked on its end day.
    An exclusive end was the first real bug in this build (see docs/war-story.md); it dropped the
    final working day of every task and quietly lowered the over-allocation count.
    """
    if end < start:
        return []
    out: list[date] = []
    cursor = start
    while cursor <= end:
        if is_working_day(cursor):
            out.append(cursor)
        cursor += timedelta(days=1)
    return out


def count_working_days(start: date, end: date) -> int:
    """Number of working days in the inclusive range. The capacity denominator for a sprint."""
    return len(working_days(start, end))


@dataclass(frozen=True)
class BusinessCalendar:
    """A dense, ordered mapping between working days in a horizon and integer ordinals.

    Built once for a plan's horizon so that overlap accumulation indexes into a list rather than
    a dict keyed by date. Frozen so it cannot drift after a plan is loaded.
    """

    days: tuple[date, ...]

    @classmethod
    def for_horizon(cls, start: date, end: date) -> BusinessCalendar:
        return cls(tuple(working_days(start, end)))

    def __len__(self) -> int:
        return len(self.days)

    @property
    def start(self) -> date:
        return self.days[0]

    @property
    def end(self) -> date:
        return self.days[-1]

    def ordinal_of(self, day: date) -> int:
        """Index of a working day within the horizon. Raises for a weekend or an out-of-range date.

        Raising rather than clamping is deliberate: a silent clamp would fold a task that starts
        before the horizon onto day zero and invent overlap that does not exist.
        """
        try:
            return self._index[day]
        except KeyError as exc:
            raise ValueError(f"{day.isoformat()} is not a working day inside the horizon") from exc

    def date_of(self, ordinal: int) -> date:
        return self.days[ordinal]

    def contains(self, day: date) -> bool:
        return day in self._index

    @property
    def _index(self) -> dict[date, int]:
        # Cached lazily; the dataclass is frozen so this is memoised through object.__setattr__.
        cached = self.__dict__.get("_index_cache")
        if cached is None:
            cached = {d: i for i, d in enumerate(self.days)}
            object.__setattr__(self, "_index_cache", cached)
        return cached
