"""Command line entry point with exit codes that a CI gate can branch on.

The exit codes separate the two things a pipeline must tell apart: a clean answer, a clean 'no
this plan hides a conflict', and a failure to answer at all. Collapsing the middle two into one
non-zero code is the common mistake; a gate then cannot distinguish a real finding from a broken
input, and stops trusting the step.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .analyze import analyze
from .config import AnalysisConfig
from .generate import SPRINT_WORKING_DAYS, write_plan
from .ingest import read_plan
from .model import PlanError
from .report import render_json, render_text

EXIT_OK = 0  # analysed, and no hidden over-allocation
EXIT_HIDDEN = 2  # analysed, and hidden over-allocation was found (the gate fails)
EXIT_INPUT = 3  # could not analyse: bad arguments or an unreadable plan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="capacity-overlap",
        description="Find the person-days of over-allocation a sprint utilization view hides.",
    )
    parser.add_argument("--version", action="version", version=f"capacity-overlap {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    analyze_cmd = sub.add_parser("analyze", help="analyse a plan CSV")
    analyze_cmd.add_argument("plan", type=Path, help="path to the plan CSV")
    analyze_cmd.add_argument("--capacity", type=float, default=1.0, help="daily capacity in FTE")
    analyze_cmd.add_argument(
        "--tolerance", type=float, default=0.0, help="slack above capacity before a day counts"
    )
    analyze_cmd.add_argument(
        "--sprint-days", type=int, default=SPRINT_WORKING_DAYS, help="working days per sprint"
    )
    analyze_cmd.add_argument("--json", type=Path, default=None, help="write the JSON report here")
    analyze_cmd.add_argument(
        "--quiet", action="store_true", help="suppress the text report on stdout"
    )

    gen_cmd = sub.add_parser("generate", help="regenerate the seeded plan fixture")
    gen_cmd.add_argument("--seed", type=int, required=True, help="generator seed")
    gen_cmd.add_argument("--out", type=Path, required=True, help="CSV destination")
    gen_cmd.add_argument("--team-size", type=int, default=26, help="number of people")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "generate":
        return _run_generate(args)
    return _run_analyze(args)


def _run_generate(args: argparse.Namespace) -> int:
    try:
        count = write_plan(args.out, seed=args.seed, team_size=args.team_size)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_INPUT
    print(f"wrote {count} rows to {args.out}")
    return EXIT_OK


def _run_analyze(args: argparse.Namespace) -> int:
    try:
        config = AnalysisConfig(capacity_fte=args.capacity, tolerance=args.tolerance)
        plan = read_plan(args.plan, sprint_working_days=args.sprint_days)
    except (PlanError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_INPUT

    analysis = analyze(plan, config)

    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(render_json(analysis))
    if not args.quiet:
        print(render_text(analysis))

    return EXIT_HIDDEN if analysis.gate_failed() else EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
