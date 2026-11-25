"""Experiment 2: over-allocation disappears as the reporting window widens.

Question answered: is the sprint window specifically what hides the clash, or would any view catch
it? Re-report the same plan under windows from one working day up to the whole horizon, measuring
the over-allocation each window can still see. The visible amount falls monotonically as the window
widens, which is the mechanism: averaging over a longer window dilutes a concentrated peak.
"""

from __future__ import annotations

from _common import load_plan, write_json

from capacity_overlap.calendar import count_working_days
from capacity_overlap.config import AnalysisConfig
from capacity_overlap.ingest import build_sprints
from capacity_overlap.model import Plan
from capacity_overlap.overlap import build_timelines
from capacity_overlap.sprintview import sprint_utilizations

WINDOWS = [1, 2, 5, 10, 20, 60]


def _aggregate_over_person_days(plan: Plan, window: int, config: AnalysisConfig) -> float:
    """Over-allocation the aggregate at this window reports: sum of (assigned - capacity)+ a block.

    At a one working-day window the aggregate equals the day-level truth; wider windows see less.
    """
    windows = build_sprints(plan.horizon_start, plan.horizon_end, window)
    windowed = Plan(assignments=plan.assignments, sprints=windows)
    timelines = build_timelines(windowed)
    total = 0.0
    for u in sprint_utilizations(windowed, timelines, config):
        capacity = u.capacity_person_days
        total += max(0.0, u.assigned_person_days - capacity)
    return round(total, 6)


def run() -> dict:
    plan = load_plan()
    config = AnalysisConfig()
    full_working_days = count_working_days(plan.horizon_start, plan.horizon_end)
    rows = []
    for window in WINDOWS:
        rows.append(
            {
                "window_working_days": window,
                "aggregate_over_person_days": _aggregate_over_person_days(plan, window, config),
            }
        )
    daily = rows[0]["aggregate_over_person_days"]
    for r in rows:
        r["hidden_vs_daily"] = round(daily - r["aggregate_over_person_days"], 6)
    payload = {
        "experiment": "aggregation_window",
        "question": "how much over-allocation each reporting window can still see",
        "horizon_working_days": full_working_days,
        "daily_over_person_days": daily,
        "sprint_over_person_days": next(
            r["aggregate_over_person_days"] for r in rows if r["window_working_days"] == 10
        ),
        "rows": rows,
    }
    write_json("aggregation_window.json", payload)
    return payload


def _print_table(payload: dict) -> None:
    print(f"\n{payload['experiment']}: {payload['question']}\n")
    print(f"{'window (wd)':>12}{'aggregate OA':>13}{'hidden vs daily':>18}")
    print("-" * 43)
    for r in payload["rows"]:
        print(
            f"{r['window_working_days']:>12}{r['aggregate_over_person_days']:>13}"
            f"{r['hidden_vs_daily']:>18}"
        )
    print(
        f"\nat 1 working day the view sees {payload['daily_over_person_days']} person-days; "
        f"at the 10-day sprint it sees {payload['sprint_over_person_days']}"
    )


if __name__ == "__main__":
    _print_table(run())
