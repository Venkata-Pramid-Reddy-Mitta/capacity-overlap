# ADR-005: Exit-code semantics, and an opt-in strict gate

## Status

Accepted.

## Context

`capacity-overlap analyze` is meant to run in CI as a gate. A gate needs to tell three outcomes
apart: the plan is clean, the plan hides a conflict, and the tool could not run. The common mistake
is to collapse the last two into a single non-zero code, after which a pipeline cannot distinguish a
real finding from a broken input and stops trusting the step.

A second question is whether the tool should fail the build by default when it finds hidden
over-allocation. A check that always fails on real data gets disabled within a week.

## Decision

Three exit codes:

- `0`: analyzed, no hidden over-allocation.
- `2`: analyzed, hidden over-allocation found. The gate fails here, deliberately a distinct code.
- `3`: could not analyze (bad arguments, missing or malformed plan). Every input problem maps to this
  one class via `PlanError`.

The strictness is tunable through `--tolerance`, not hard-coded. The default tolerance is zero, so the
tool reports the plan's own arithmetic, but a team that accepts light double-booking can raise the bar
rather than delete the check.

## Consequences

- A CI job can branch: treat `2` as a review-required finding and `3` as a pipeline error, and they
  will never be confused.
- The default is honest (zero tolerance reports exactly what the plan says) while the escape hatch is
  a visible flag with a number attached, not a commented-out step. This is the opt-in posture the
  rendering-and-CI lessons recommend: a check that can be tuned survives, a check that always fails
  gets removed.
- The three codes are pinned by tests, including one that asserts they are distinct, so a future
  refactor cannot quietly merge two of them.
