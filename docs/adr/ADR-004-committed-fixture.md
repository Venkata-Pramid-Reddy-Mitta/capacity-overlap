# ADR-004: A committed fixture plus a seeded generator

## Status

Accepted. This is the boring-choice ADR.

## Context

The repository needs data to measure against. The options were a generator run at verify time, a
committed fixture, or both. A generated-at-verify-time plan is tempting because it looks dynamic, but
it makes every published number depend on the generator producing the same output on the reviewer's
machine, across Python versions and platforms.

## Decision

Commit the generated plan as `data/plan.csv`, and keep the seeded generator (`make generate`) for
regenerating it. `make verify` reads the committed fixture; it does not regenerate it. The generator
is driven entirely by one `random.Random(seed)` and sorts its rows before writing, so regeneration is
byte-for-byte stable, but the committed file is the artefact of record.

## Consequences

- Every number in the repository is reproducible from a fixed file plus one command, with no
  dependence on the generator running identically elsewhere. A reviewer can read the plan.
- The generator stays in the repository and is tested, so a reviewer can see exactly how the data was
  built and that it was not hand-tuned to flatter the result: it plants a fixed profile mix (clean,
  hidden, visible) and the headline falls out of that.
- If the generator and the committed fixture ever disagree, a test catches it
  (`test_the_written_plan_reproduces_the_committed_headline`), so the two cannot drift silently.

## Why boring is right

The exciting version (generate on every run) trades reproducibility for the appearance of freshness.
For a tool whose entire credibility is "every number is real and checkable", reproducibility wins.
