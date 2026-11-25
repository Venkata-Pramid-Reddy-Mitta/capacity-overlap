"""Experiment 4: which workstream combinations the hidden over-allocation comes from.

Question answered: the sprint view cannot say where a clash originates; the day-level view can.
For every over-allocated day inside a hidden finding, the distinct workstreams a person is active in
that day are the colliding parties, so the day's excess is attributed to that combination. Ranking
the combinations names the cross-workstream pulls that produce the invisible over-allocation.
"""

from __future__ import annotations

from collections import defaultdict

from _common import load_plan, write_json

from capacity_overlap.analyze import analyze
from capacity_overlap.config import AnalysisConfig
from capacity_overlap.model import Plan


def _streams_active_on(plan: Plan, person_id: str, day) -> tuple[str, ...]:
    streams = {a.workstream for a in plan.assignments_for(person_id) if a.start <= day <= a.end}
    return tuple(sorted(streams))


def run() -> dict:
    plan = load_plan()
    result = analyze(plan, AnalysisConfig())
    by_combo: dict[tuple[str, ...], dict] = defaultdict(
        lambda: {"over_person_days": 0.0, "clash_days": 0}
    )
    for f in result.hidden_findings:
        for od in f.over_days:
            combo = _streams_active_on(plan, f.person_id, od.day)
            by_combo[combo]["over_person_days"] += od.excess
            by_combo[combo]["clash_days"] += 1

    rows = [
        {
            "workstreams": list(combo),
            "pair_size": len(combo),
            "over_person_days": round(stats["over_person_days"], 6),
            "clash_days": stats["clash_days"],
        }
        for combo, stats in by_combo.items()
    ]
    rows.sort(key=lambda r: (-r["over_person_days"], r["workstreams"]))
    cross = sum(r["over_person_days"] for r in rows if r["pair_size"] >= 2)
    payload = {
        "experiment": "workstream_attribution",
        "question": "which workstream combinations the hidden over-allocation comes from",
        "combinations": len(rows),
        "cross_workstream_over_person_days": round(cross, 6),
        "hidden_over_person_days": result.hidden_over_person_days,
        "top_combination": rows[0] if rows else None,
        "rows": rows,
    }
    write_json("workstream_attribution.json", payload)
    return payload


def _print_table(payload: dict) -> None:
    print(f"\n{payload['experiment']}: {payload['question']}\n")
    print(f"{'workstreams':<44}{'over p-days':>12}{'clash d':>9}")
    print("-" * 65)
    for r in payload["rows"][:8]:
        label = " + ".join(r["workstreams"])
        print(f"{label:<44}{r['over_person_days']:>12}{r['clash_days']:>9}")
    print(
        f"\n{payload['cross_workstream_over_person_days']} of "
        f"{payload['hidden_over_person_days']} hidden person-days come from days spanning "
        f"two or more workstreams"
    )


if __name__ == "__main__":
    _print_table(run())
