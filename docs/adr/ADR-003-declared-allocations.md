# ADR-003: Declared allocations are the input; observed effort is out of scope

## Status

Accepted.

## Context

An allocation in the plan (person X is on task Y at 50%) is a commitment, not a measurement. A tool
could try to reconcile it against observed effort from timesheets or issue-tracker activity, which
would make the output "what actually happened" rather than "what the plan says".

## Decision

Treat declared allocations as the single source of truth and keep observed effort out of scope. The
tool measures the plan's internal contradiction: a plan that commits a person over capacity on a day
is self-inconsistent regardless of what was later worked.

Also treat each task's allocation as uniform across its working days. A ramp-up or a crunch at the
end of a task is not modeled.

## Consequences

- The result is fully offline and reproducible from one committed artifact, with no feed to trust or
  mock and no credentials. This is worth more for a portfolio reviewer than realism would be: every
  number is reproducible with one command.
- A 50% allocation that was really worked at 90% is invisible. The tool does not claim to find real
  over-work; it finds plans that cannot be true as written, which is a different and cleaner claim.
- The uniform-within-a-task assumption can overstate a clash if two tasks' real effort was
  back-loaded into non-overlapping weeks. The honest framing in the README and defense guide is that
  the tool audits the plan, not the people.

## Why this is the right boundary for the claim

The headline is a comparison between two readings of the same declared plan, so any imprecision in
the allocations is shared by both readings and cannot manufacture a hidden clash. The one input a
reviewer must trust is the plan, and it is committed.
