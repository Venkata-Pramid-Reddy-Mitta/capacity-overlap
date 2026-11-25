"""Experiment 3: the finding survives a generous tolerance, so it is not rounding noise.

Question answered: if a team shrugs off light double-booking, does the hidden over-allocation go
away? Raise the tolerance from zero (strict) through half an FTE and watch how much hidden
over-allocation, and how many people, remain. A finding that vanishes at a tolerance of 0.05 would
be noise; one that persists at 0.25 is real concurrency.
"""

from __future__ import annotations

from _common import load_plan, write_json

from capacity_overlap.analyze import analyze
from capacity_overlap.config import AnalysisConfig

TOLERANCES = [0.0, 0.05, 0.1, 0.25, 0.5]


def run() -> dict:
    plan = load_plan()
    rows = []
    for tol in TOLERANCES:
        result = analyze(plan, AnalysisConfig(tolerance=tol))
        rows.append(
            {
                "tolerance": tol,
                "hidden_over_person_days": result.hidden_over_person_days,
                "people_conflicted_while_green": result.people_conflicted_while_green,
                "green_conflicted_pairs": result.green_conflicted_pairs,
            }
        )
    payload = {
        "experiment": "threshold_sensitivity",
        "question": "how much hidden over-allocation survives a growing tolerance",
        "strict_hidden_over_person_days": rows[0]["hidden_over_person_days"],
        "hidden_at_quarter_fte_tolerance": next(
            r["hidden_over_person_days"] for r in rows if r["tolerance"] == 0.25
        ),
        "people_at_quarter_fte_tolerance": next(
            r["people_conflicted_while_green"] for r in rows if r["tolerance"] == 0.25
        ),
        "rows": rows,
    }
    write_json("threshold_sensitivity.json", payload)
    return payload


def _print_table(payload: dict) -> None:
    print(f"\n{payload['experiment']}: {payload['question']}\n")
    print(f"{'tolerance':>10}{'hidden OA':>12}{'people':>9}{'pairs':>8}")
    print("-" * 39)
    for r in payload["rows"]:
        print(
            f"{r['tolerance']:>10}{r['hidden_over_person_days']:>12}"
            f"{r['people_conflicted_while_green']:>9}{r['green_conflicted_pairs']:>8}"
        )
    print(
        f"\neven allowing 125% days (tolerance 0.25), "
        f"{payload['hidden_at_quarter_fte_tolerance']} hidden person-days remain across "
        f"{payload['people_at_quarter_fte_tolerance']} people"
    )


if __name__ == "__main__":
    _print_table(run())
