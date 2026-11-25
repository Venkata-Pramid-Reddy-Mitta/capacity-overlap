# Defense guide: capacity-overlap

Read this before the interview. Every number here is machine-checked against the code by
`tools/check_numbers.py`, so it will not drift from what the tool prints.

## The 30 second version

"A resource plan is read one number per person per sprint: effort over capacity. That number
averages across the sprint, so it cannot see two tasks from different workstreams landing on the same
days. I rebuild each person's load one working day at a time and compare. On a seeded plan of 26
people, there are 17.6 hidden person-days of over-allocation that every sprint bar shows as at or
below 100%, which is 85.4% of all the over-allocation in the plan." Then stop.

The question that usually comes next: "isn't that just summing hours differently?" Answer: no, it is
the opposite of summing. The aggregate already sums; the bug is that summing then dividing by the
window hides concentration. The fix is to not aggregate until after you have found the peak.

## The claims, each with how it is proved

**Claim 1: the sprint view hides 17.6 person-days of over-allocation.**
Command: `capacity-overlap analyze data/plan.csv`.
It reports 17.6 hidden person-days across 25 person-sprint pairs that read at or below 100%, affecting
16 people the sprint view calls healthy.
If pushed ("maybe the plan is just bad"): that is the point, but the plan reads *fine* at the sprint
level, which is the only level most status reports show. The tool finds the plans that look fine and
are not.

**Claim 2: 85.4% of the over-allocation is invisible at the sprint level.**
Command: `python experiments/exp_aggregation_window.py`.
A daily view sees 20.6 person-days of over-allocation; the sprint reports 1.0. The gap is what the
window hides, and it grows monotonically as the window widens.
If pushed ("is that an artefact of your window choice?"): the experiment sweeps windows from one
working day to the whole horizon; the effect is monotone, so there is nothing special about ten days
except that it is the common sprint length.

**Claim 3: it is concurrency, not rounding.**
Command: `python experiments/exp_threshold_sensitivity.py`.
Even allowing 125% days, 1.85 hidden person-days remain across three people. The finding does not
evaporate under a generous tolerance.

**Claim 4: every number here is re-measured.**
Command: `make verify`.
124 tests at 100% line coverage, the experiments re-run, and `check_numbers.py` fails the build if any
figure in the README or this guide drifts from the code.

## Questions that are meant to be hard

**"Isn't this just a pandas groupby with extra steps?"**
pandas reads the CSV and nothing else. The core (`overlap`, `analyze`) is plain Python and never
imports pandas. The work is the day-level materialisation and the reconciliation against the
aggregate, which is not a groupby; a groupby over the sprint is exactly the flawed view I am arguing
with.

**"The data is synthetic. Does any of this transfer?"**
The algorithm is independent of the data: it is interval overlap plus an average-versus-peak
comparison. The fixture exists to make the numbers reproducible, not to prove the effect is large in
any particular org. The claim that transfers is structural: an average at or below capacity can sit
over a peak, so a sprint utilization number cannot certify a plan. That is true of any plan, synthetic
or not. ADR-004 explains why the fixture is committed.

**"What is the weakest part?"**
The uniform-within-a-task assumption (ADR-003). Allocations are spread evenly across a task's working
days, so if two tasks' real effort happened to back-load into non-overlapping weeks, the tool would
report a clash that effort did not. I kept it because the alternative needs per-day effort data the
tool deliberately does not depend on, and because the headline is a comparison of two readings of the
*same* declared plan, so the assumption is shared by both sides and cannot invent a hidden clash. But
if I had one more week, this is where it would go.

**"What would you do differently with more time?"**
Build the rescheduler (the Pivot). The tool already reports the slack days a clash could move into
(174 on this plan); turning that into a suggested move needs per-task constraints (earliest start,
latest finish, who can do the work). Without those a suggestion is a guess, so I stopped at naming the
clash and the slack.

**"Why not just fail CI on any over-allocation?"**
ADR-005. A check that always fails on real data gets deleted. The gate fails on hidden over-allocation
by default (exit code 2, distinct from the input-error code 3) but the strictness is a visible
`--tolerance` flag, so a team tunes it rather than disabling it.

**"How do I know the numbers are real?"**
Break one. Change the headline 17.6 to any other number in the README and run `make verify`; the
build fails with a stale-figure error naming the file. The checker matches anchor phrases, not bare
digits, so it only accepts that value where the surrounding words say "hidden person-days of".

## Things to say

- "The aggregate is not wrong, it is lossy: averaging over the window is the flaw."
- "The tool is conservative: a missing holiday or uniform-effort assumption cancels on both sides of
  the comparison, so it understates rather than inflates."
- "Every figure is reproduced by one offline command."

## Things not to say

- Do not say "it finds over-worked people". It finds plans that cannot be true as written; observed
  effort is out of scope.
- Do not present the 174 slack days as a fix. It is the room a fix would use, not the fix.
- Do not claim the effect size is representative of real orgs. The size is a property of the seeded
  fixture; the mechanism is what generalises.

## The live demo script

```bash
capacity-overlap analyze data/plan.csv                 # 17.6 hidden person-days, worst case 140% peak
python experiments/exp_aggregation_window.py           # daily sees 20.6, the sprint reports 1.0
python experiments/exp_threshold_sensitivity.py        # 1.85 survive a 125%-day tolerance
capacity-overlap analyze data/plan.csv --tolerance 0.5 --quiet; echo "exit $?"  # gate tuned off: exit 0
python tools/check_numbers.py                          # every figure matches the code
```
