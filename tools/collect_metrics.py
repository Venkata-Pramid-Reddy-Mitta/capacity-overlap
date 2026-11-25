"""Re-measure every published figure and write docs/metrics.json. Nothing is typed by hand.

The test count and coverage come from the machine-readable reports pytest writes (junit.xml and
coverage.json), not from a parsed progress line, because a progress line becomes whatever the last
run happened to print. The analysis figures come from running the analysis on the committed fixture,
and the experiment figures from re-running the experiments. Every value here is therefore produced
by code in this build, which is the condition that makes check_numbers.py meaningful.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))
sys.path.insert(0, str(ROOT / "src"))

from capacity_overlap.analyze import analyze  # noqa: E402
from capacity_overlap.config import AnalysisConfig  # noqa: E402
from capacity_overlap.ingest import read_plan  # noqa: E402

# Anchor phrases: the number plus two or three words a document must use, never a whole clause,
# so a match survives markdown wrapping the sentence across a line.
ANCHORS = {
    "tests_total": ["{} tests"],
    "coverage_line_pct": ["{}% line coverage"],
    "people_total": ["{} people across"],
    "workstreams_total": ["{} workstreams"],
    "sprints_total": ["{} sprints"],
    "horizon_working_days": ["{} working days"],
    "hidden_over_person_days": ["{} hidden person-days of"],
    "total_over_person_days": ["{} person-days in total"],
    "hidden_share_pct": ["{}% of it invisible"],
    "green_conflicted_pairs": ["{} person-sprint pairs"],
    "people_conflicted_while_green": ["{} people the sprint view"],
    "worst_peak_pct": ["peaks at {}%"],
    "worst_sprint_util_pct": ["reads {}% for the sprint"],
    "max_gap_pct": ["a {}-point gap"],
    "daily_over_person_days": ["a daily view sees {}"],
    "sprint_aggregate_over_person_days": ["the sprint reports {}"],
    "hidden_at_quarter_fte_tolerance": ["{} hidden person-days remain"],
    "top_combination_over_person_days": ["{} person-days, the largest"],
}

CHECKED_DOCUMENTS = [
    "README.md",
    "docs/defense-guide.md",
    "docs/adr/ADR-001-day-level-sweep-over-sprint-aggregate.md",
]


def _run_experiment(module_name: str) -> dict:
    module = __import__(module_name)
    return module.run()


def _test_metrics(skip_tests: bool) -> dict:
    junit = ROOT / "junit.xml"
    cov = ROOT / "coverage.json"
    if not skip_tests:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "--junitxml=junit.xml",
                "--cov=capacity_overlap",
                "--cov-report=json",
                "--cov-report=xml",
            ],
            cwd=ROOT,
            check=True,
        )
    if not junit.exists() or not cov.exists():
        raise SystemExit("junit.xml or coverage.json missing; run the test step first")
    tree = ET.parse(junit).getroot()
    suite = tree if tree.tag == "testsuite" else tree.find("testsuite")
    tests = int(suite.attrib["tests"]) - int(suite.attrib.get("skipped", 0))
    coverage_pct = round(json.loads(cov.read_text())["totals"]["percent_covered"], 1)
    return {"tests_total": tests, "coverage_line_pct": coverage_pct}


def collect(skip_tests: bool) -> dict:
    result = analyze(read_plan(ROOT / "data" / "plan.csv"), AnalysisConfig())
    worst = result.worst_hidden()

    exp1 = _run_experiment("exp_hidden_vs_sprint")
    exp2 = _run_experiment("exp_aggregation_window")
    exp3 = _run_experiment("exp_threshold_sensitivity")
    exp4 = _run_experiment("exp_workstream_attribution")

    metrics = {
        **_test_metrics(skip_tests),
        "people_total": result.people_total,
        "workstreams_total": result.workstreams_total,
        "sprints_total": result.sprints_total,
        "horizon_working_days": result.horizon_working_days,
        "hidden_over_person_days": result.hidden_over_person_days,
        "total_over_person_days": result.total_over_person_days,
        "hidden_share_pct": result.hidden_share_pct,
        "green_conflicted_pairs": result.green_conflicted_pairs,
        "people_conflicted_while_green": result.people_conflicted_while_green,
        "reschedulable_slack_days": result.reschedulable_slack_days,
        "worst_peak_pct": worst.peak_pct,
        "worst_sprint_util_pct": worst.utilization_pct,
        "max_gap_pct": exp1["max_gap_pct"],
        "daily_over_person_days": exp2["daily_over_person_days"],
        "sprint_aggregate_over_person_days": exp2["sprint_over_person_days"],
        "hidden_at_quarter_fte_tolerance": exp3["hidden_at_quarter_fte_tolerance"],
        "top_combination_over_person_days": exp4["top_combination"]["over_person_days"],
    }
    payload = {
        "metrics": metrics,
        "anchors": ANCHORS,
        "checked_documents": CHECKED_DOCUMENTS,
        "note": "every value is produced by the test suite, the analysis, and the experiments",
    }
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Re-measure every published figure.")
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="read junit.xml and coverage.json instead of running pytest",
    )
    args = parser.parse_args(argv)
    payload = collect(args.skip_tests)
    out = ROOT / "docs" / "metrics.json"
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {out.relative_to(ROOT)} with {len(payload['metrics'])} metrics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
