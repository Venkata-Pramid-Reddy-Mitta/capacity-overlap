"""Experiment 1: how far a sprint utilization bar sits from the worst day underneath it.

Question answered: for the people the sprint view calls healthy, how large is the gap between
what the bar shows and what their worst day actually carries? The table is the headline evidence,
and the JSON feeds the receipts.
"""

from __future__ import annotations

from _common import load_plan, write_json

from capacity_overlap.analyze import analyze
from capacity_overlap.config import AnalysisConfig


def run() -> dict:
    result = analyze(load_plan(), AnalysisConfig())
    hidden = sorted(
        result.hidden_findings, key=lambda f: (-f.peak_load, -f.over_person_days, f.person_id)
    )
    rows = [
        {
            "person_id": f.person_id,
            "person_name": f.person_name,
            "sprint": f.sprint_index,
            "sprint_util_pct": f.utilization_pct,
            "peak_day_pct": f.peak_pct,
            "gap_pct": round(f.peak_pct - f.utilization_pct, 1),
            "over_person_days": f.over_person_days,
            "clash_days": len(f.over_days),
        }
        for f in hidden
    ]
    payload = {
        "experiment": "hidden_vs_sprint",
        "question": "how far does a healthy sprint bar sit from the worst day underneath it",
        "hidden_over_person_days": result.hidden_over_person_days,
        "total_over_person_days": result.total_over_person_days,
        "hidden_share_pct": result.hidden_share_pct,
        "green_conflicted_pairs": result.green_conflicted_pairs,
        "people_conflicted_while_green": result.people_conflicted_while_green,
        "max_gap_pct": max((r["gap_pct"] for r in rows), default=0.0),
        "findings": rows,
    }
    write_json("hidden_vs_sprint.json", payload)
    return payload


def _print_table(payload: dict) -> None:
    print(f"\n{payload['experiment']}: {payload['question']}\n")
    print(f"{'person':<16}{'sprint':>7}{'sprint%':>9}{'peak%':>8}{'gap%':>7}{'clash d':>9}")
    print("-" * 56)
    for r in payload["findings"][:12]:
        print(
            f"{r['person_name']:<16}{r['sprint']:>7}{r['sprint_util_pct']:>9}"
            f"{r['peak_day_pct']:>8}{r['gap_pct']:>7}{r['clash_days']:>9}"
        )
    print(
        f"\nhidden over-allocation: {payload['hidden_over_person_days']} person-days "
        f"({payload['hidden_share_pct']}% of the plan's total), "
        f"{payload['people_conflicted_while_green']} people called healthy"
    )


if __name__ == "__main__":
    _print_table(run())
