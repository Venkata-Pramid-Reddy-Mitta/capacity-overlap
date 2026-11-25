"""Seeded generator for a multi-workstream resource plan with a known mix of conflicts.

The fixture is committed, so this generator runs rarely; it exists so a reviewer can see exactly
how the plan was built and regenerate it byte for byte from the seed. It plants three kinds of
person on purpose, because the whole argument needs the contrast: people who are genuinely clean,
people whose sprint utilization reads healthy while specific days are double-booked (the hidden
case), and people whose overload is already visible at the sprint level (so the hidden share is a
fraction of a real total, not the whole of a cherry-picked one).

Nothing here is random at runtime: a single random.Random(seed) drives every choice, and the rows
are sorted before writing so the CSV is identical across platforms. The names are synthetic sample
data for the tool, not real people.
"""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from .calendar import working_days

WORKSTREAMS = ("cloud-migration", "app-modernization", "data-migration", "testing-deployment")

# Synthetic team members. Initials plus surname so no row reads as a real individual.
_SURNAMES = (
    "Rivera",
    "Okafor",
    "Nguyen",
    "Haddad",
    "Larsson",
    "Mehta",
    "Delgado",
    "Osei",
    "Park",
    "Ibrahim",
    "Kovac",
    "Santos",
    "Petrov",
    "Abbasi",
    "Yamada",
    "Cohen",
    "Flores",
    "Novak",
    "Reddy",
    "Khan",
    "Moreau",
    "Silva",
    "Tran",
    "Berg",
    "Adeyemi",
    "Costa",
    "Lindqvist",
    "Varga",
)
_INITIALS = "ABCDEFGHJKLMNPRSTVW"

HORIZON_START = date(2026, 4, 13)  # a Monday
SPRINTS = 6
SPRINT_WORKING_DAYS = 10


@dataclass(frozen=True)
class _Row:
    task_id: str
    person_id: str
    person_name: str
    workstream: str
    start: date
    end: date
    allocation: float

    def as_record(self) -> dict[str, str]:
        return {
            "task_id": self.task_id,
            "person_id": self.person_id,
            "person_name": self.person_name,
            "workstream": self.workstream,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "allocation": f"{self.allocation:.2f}",
        }


def _horizon_days(team_size: int) -> list[date]:
    # Six ten-working-day sprints is sixty working days; build the day list once.
    total_working = SPRINTS * SPRINT_WORKING_DAYS
    cursor = HORIZON_START
    days: list[date] = []
    while len(days) < total_working:
        wd = working_days(cursor, cursor)
        if wd:
            days.append(wd[0])
        cursor += timedelta(days=1)
    return days


def generate_rows(seed: int, team_size: int = 26) -> list[_Row]:
    rng = random.Random(seed)
    days = _horizon_days(team_size)
    horizon_end = days[-1]
    rows: list[_Row] = []
    task_counter = 0

    def next_task(prefix: str) -> str:
        nonlocal task_counter
        task_counter += 1
        return f"{prefix}-{task_counter:03d}"

    # Fixed profile mix so the headline is stable: 8 clean, 12 hidden, 6 visible.
    profiles = ["clean"] * 8 + ["hidden"] * 12 + ["visible"] * 6
    profiles = profiles[:team_size]
    while len(profiles) < team_size:
        profiles.append("hidden")
    rng.shuffle(profiles)

    for i in range(team_size):
        pid = f"p{i + 1:02d}"
        name = f"{_INITIALS[i % len(_INITIALS)]}. {_SURNAMES[i % len(_SURNAMES)]}"
        home = WORKSTREAMS[i % len(WORKSTREAMS)]
        profile = profiles[i]

        baseline_alloc = rng.choice([0.4, 0.5, 0.6])
        rows.append(_Row(next_task("base"), pid, name, home, days[0], horizon_end, baseline_alloc))

        if profile == "clean":
            continue

        pull_streams = [w for w in WORKSTREAMS if w != home]
        if profile == "hidden":
            # Short, sharp pull-ins that push a few days over 1.0 but keep the sprint sum under
            # capacity, because the baseline is modest and the pull-in is only a few days long.
            for _ in range(rng.choice([1, 2])):
                stream = rng.choice(pull_streams)
                length = rng.choice([2, 3, 4])
                alloc = rng.choice([0.5, 0.6, 0.75])
                start = _random_working_start(rng, days, length)
                end = _working_end(days, start, length)
                rows.append(_Row(next_task("pull"), pid, name, stream, start, end, alloc))
        else:  # visible
            # A long, heavy pull-in so the sprint sum itself clears capacity.
            stream = rng.choice(pull_streams)
            length = rng.choice([6, 7, 8])
            alloc = rng.choice([0.75, 1.0])
            start = _random_working_start(rng, days, length)
            end = _working_end(days, start, length)
            rows.append(_Row(next_task("pull"), pid, name, stream, start, end, alloc))

    rows.sort(key=lambda r: (r.person_id, r.start, r.workstream, r.task_id))
    return rows


def _random_working_start(rng: random.Random, days: list[date], length: int) -> date:
    last_index = max(0, len(days) - length)
    return days[rng.randint(0, last_index)]


def _working_end(days: list[date], start: date, length: int) -> date:
    start_index = days.index(start)
    end_index = min(len(days) - 1, start_index + length - 1)
    return days[end_index]


def write_plan(path: str | Path, seed: int, team_size: int = 26) -> int:
    """Write the seeded plan to a CSV and return the number of assignment rows."""
    rows = generate_rows(seed, team_size)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "task_id",
                "person_id",
                "person_name",
                "workstream",
                "start",
                "end",
                "allocation",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row.as_record())
    return len(rows)
