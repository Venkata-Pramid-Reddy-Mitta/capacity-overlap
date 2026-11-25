# ADR-001: Reconstruct load at the day level, not from the sprint aggregate

## Status

Accepted.

## Context

The product has to report over-allocation the sprint utilization view cannot. There were two ways to
compute it. The cheap one stays at the sprint level: for each person-sprint, if planned effort
exceeds capacity, report the excess. The expensive one rebuilds each person's load one working day at
a time and sums concurrent allocations, then looks for days over capacity.

The cheap path is structurally unable to do the job. A sprint aggregate is an average over the
window, and an average at or below capacity can still sit over a peak: a person planned at 50% for
the sprint can be at 140% on one day. Over-allocation above 100% is the only kind the aggregate can
see, and that kind is already visible without this tool. The entire value is in the days the average
smooths away.

## Decision

Materialise a per-person, per-working-day load by summing every assignment active on each day, and
derive over-allocation from that. The accumulation is the overlap detection: two assignments
contribute to the same day exactly when their inclusive date ranges share a working day.

## Consequences

- Memory and time are proportional to people times horizon working days. For a plan of dozens of
  people over a few months this is trivial; for ten thousand people over five years it would need a
  sweep over interval endpoints rather than a per-day materialisation. The Pivot notes the trigger.
- The day-indexed load is directly inspectable, so the report can show the exact clash days, which is
  what makes the finding actionable rather than a flag.
- The aggregate is still computed, in `sprintview`, precisely so the two can be set against each
  other in `analyze` and in the tests. Keeping the flawed view in the codebase is deliberate: it is
  the baseline the product argues with.

## The invariant this rests on

Any person-sprint whose aggregate reads above 100% must contain a day over capacity (an average above
a bound forces a value above it). So "hidden" over-allocation is exactly the healthy-reading case,
and the test suite asserts the invariant across the fixture and three thousand random plans.
