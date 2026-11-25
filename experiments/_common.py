"""Shared helpers for the experiments: find the repo, load the fixture, write JSON under docs."""

from __future__ import annotations

import json
from pathlib import Path

from capacity_overlap.ingest import read_plan
from capacity_overlap.model import Plan

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data" / "plan.csv"
OUT_DIR = ROOT / "docs" / "experiments"


def load_plan(sprint_working_days: int = 10) -> Plan:
    return read_plan(FIXTURE, sprint_working_days=sprint_working_days)


def write_json(name: str, payload: dict) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    path.write_text(json.dumps(payload, indent=2) + "\n")
    return path
