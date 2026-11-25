# War story: the metric that read exactly zero

## Symptom

The first version of the report carried a metric called `masked_idle_days`: fully idle working days
sitting inside a sprint that also hid a conflict. The intended story was sharp, a sprint that holds
both a fire and a gap. On the seeded plan it read zero. Not small, zero, on every run and every seed
I tried.

## Diagnosis

A metric that is always zero is either a true fact about the data or a structural impossibility, and
the two are told apart by asking whether the input could ever move it. The generator gives every
person a baseline task that spans the whole horizon. A baseline allocation is strictly above zero on
every working day, so no working day is ever *fully* idle. "Masked idle days" was therefore
unreachable by construction, not a measured zero. It would have published a confident 0 that meant
nothing, which is worse than publishing nothing.

## Root cause

The metric measured the wrong quantity. The intuition was right (a conflicted sprint usually hides
slack somewhere), but "idle" was the wrong threshold. The useful quantity is not days at zero load,
it is days *below capacity*, because those are the days the clashing work could move into.

## Fix

`slack_days` now counts working days whose load is strictly below capacity, and the aggregate is
`reschedulable_slack_days`. On the same plan it is 174, and it changes the posture of the whole
report: the clashes are concentration, not a staffing shortfall, and there is room in the same
sprints to resolve them. The definition lives in `analyze._slack_days_in_sprint`, pinned by
`test_reschedulable_slack_counts_below_capacity_days_in_hidden_sprints`.

## What the measurement taught

The receipts discipline is what surfaced this. A metric wired into the report and printed on every
run made its constant zero obvious immediately; a number computed once in a notebook and pasted into
a document would have shipped. The lesson generalised into a habit for the rest of the build: a
metric that cannot move is a bug in the metric, so every published figure has at least one test that
makes it move.
