"""Analysis configuration: the thresholds a reviewer will want to move, in one place.

Capacity and tolerance are the two numbers that decide what counts as over-allocation, so they
are configuration rather than constants buried in the overlap code. The defaults are stated here
with their reasons, and the CLI exposes both, because an auditor's first question is 'what did you
call full, and how much slack did you allow before you called it a conflict?'.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AnalysisConfig:
    """Everything that changes the verdict, with a reason for each default.

    capacity_fte: a person's daily capacity in FTE. Default 1.0 means one person is one full day.
        A part-time person is modelled by supplying their fraction, not by scaling allocations.
    tolerance: slack added to capacity before a day is called over-allocated. Default 0.0 so the
        tool reports the plan's own arithmetic; a team that tolerates light double-booking can
        raise it. ADR-005 explains why the strict gate stays opt-in.
    """

    capacity_fte: float = 1.0
    tolerance: float = 0.0

    def __post_init__(self) -> None:
        if self.capacity_fte <= 0:
            raise ValueError(f"capacity_fte must be positive, got {self.capacity_fte}")
        if self.tolerance < 0:
            raise ValueError(f"tolerance must be non-negative, got {self.tolerance}")

    @property
    def over_allocation_threshold(self) -> float:
        """The daily load above which a day is a conflict."""
        return self.capacity_fte + self.tolerance
