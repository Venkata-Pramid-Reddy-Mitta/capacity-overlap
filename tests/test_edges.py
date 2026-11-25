"""Defensive and edge paths: the branches that exist so a wrong input fails loudly, not quietly."""

from __future__ import annotations

from datetime import date

from capacity_overlap.analyze import _over_days_in_sprint, _peak_in_sprint, _slack_days_in_sprint
from capacity_overlap.cli import EXIT_INPUT, main
from capacity_overlap.generate import generate_rows
from capacity_overlap.ingest import _parse_date
from capacity_overlap.model import Sprint

MON = date(2026, 4, 13)
FRI = date(2026, 4, 17)
SPRINT = Sprint(1, MON, FRI)


def test_parse_date_passes_through_an_existing_date():
    # pandas can hand back a date object for a parsed column; it must survive untouched.
    assert _parse_date(MON) == MON


def test_peak_in_sprint_of_a_missing_person_is_zero():
    assert _peak_in_sprint(None, SPRINT) == 0.0


def test_over_days_in_sprint_of_a_missing_person_is_empty():
    assert _over_days_in_sprint(None, SPRINT, None) == []


def test_slack_in_sprint_of_a_missing_person_is_the_whole_sprint():
    from capacity_overlap.config import AnalysisConfig

    assert _slack_days_in_sprint(None, SPRINT, AnalysisConfig()) == 5


def test_generate_fills_extra_people_beyond_the_default_profile_mix():
    # The profile list is 26 long; a larger team must still assign everyone a profile.
    rows = generate_rows(20260410, team_size=30)
    assert len({r.person_id for r in rows}) == 30


def test_generate_to_an_unwritable_path_returns_input_error(tmp_path, capsys):
    # Parent is a file, so creating the output directory fails: a generate-side input error.
    blocker = tmp_path / "blocker"
    blocker.write_text("x")
    code = main(["generate", "--seed", "1", "--out", str(blocker / "plan.csv")])
    assert code == EXIT_INPUT
    assert "error:" in capsys.readouterr().err
