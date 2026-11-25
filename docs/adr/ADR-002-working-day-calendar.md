# ADR-002: Count working days, and ship without a holiday calendar

## Status

Accepted. This is the boundary ADR: it states what the repository deliberately does not model.

## Context

Every number in the tool divides work by capacity, and capacity is measured in days. Two choices
present themselves: what counts as a day of capacity, and how precise that calendar needs to be.

If capacity counted calendar days, a weekend would be counted as available time. A task running
Friday to Monday would span four days of capacity when only two are real, which lowers utilization
and makes the aggregate even more forgiving than the flaw this tool exists to expose. So capacity
must be working days.

The harder question is holidays. A correct per-region holiday calendar is a real, maintained dataset
with edge cases (observed-on dates, half days, regional variation) that would become the largest and
least interesting part of this codebase.

## Decision

Count Monday to Friday as working days, computed in exactly one module (`calendar`). Do not model
public holidays. State this as a boundary in the README and here, rather than approximating holidays
and getting them subtly wrong.

## Consequences

- A public holiday is counted as capacity, so utilization is marginally overstated and a real clash
  on the day before a holiday could read slightly lower than reality. This makes the tool's estimate
  of hidden over-allocation conservative, not inflated, which is the safe direction for a number
  whose job is to say "worse than it looks".
- Because the headline compares two readings of the same calendar, a missing holiday cancels on both
  sides: it cannot create a hidden clash that is not there. This is why the boundary is safe.
- Adding holidays later is a localised change behind the same `is_working_day` seam, with a stated
  first metric to watch (the change in horizon working days once they are removed).
