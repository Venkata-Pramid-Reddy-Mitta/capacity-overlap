"""CLI contract: the three exit codes a gate branches on, plus generate and JSON output."""

from __future__ import annotations

import json

import pytest

from capacity_overlap.cli import EXIT_HIDDEN, EXIT_INPUT, EXIT_OK, main

CLEAN = (
    "task_id,person_id,person_name,workstream,start,end,allocation\n"
    "t1,p01,A. Rivera,cloud-migration,2026-04-13,2026-04-17,0.50\n"
)
HIDDEN = CLEAN + "t2,p01,A. Rivera,data-migration,2026-04-15,2026-04-15,0.75\n"


def write(tmp_path, text):
    p = tmp_path / "plan.csv"
    p.write_text(text)
    return p


def test_analyze_returns_zero_on_a_clean_plan(tmp_path, capsys):
    code = main(["analyze", str(write(tmp_path, CLEAN))])
    assert code == EXIT_OK
    assert "PASS: clean" in capsys.readouterr().out


def test_analyze_returns_two_when_hidden_over_allocation_is_found(tmp_path):
    assert main(["analyze", str(write(tmp_path, HIDDEN))]) == EXIT_HIDDEN


def test_analyze_returns_three_on_a_missing_file(tmp_path, capsys):
    code = main(["analyze", str(tmp_path / "missing.csv")])
    assert code == EXIT_INPUT
    assert "error:" in capsys.readouterr().err


def test_analyze_returns_three_on_a_malformed_plan(tmp_path, capsys):
    bad = write(tmp_path, CLEAN.replace("0.50", "9.0"))
    assert main(["analyze", str(bad)]) == EXIT_INPUT


def test_the_distinct_codes_separate_a_finding_from_a_failure():
    # The reason exit codes matter: 'conflict found' and 'could not run' must not collide.
    assert EXIT_HIDDEN != EXIT_INPUT != EXIT_OK


def test_quiet_suppresses_the_text_report(tmp_path, capsys):
    main(["analyze", str(write(tmp_path, HIDDEN)), "--quiet"])
    assert capsys.readouterr().out == ""


def test_json_output_is_written_and_valid(tmp_path):
    out = tmp_path / "out" / "report.json"
    main(["analyze", str(write(tmp_path, HIDDEN)), "--json", str(out), "--quiet"])
    data = json.loads(out.read_text())
    assert data["headline"]["hidden_over_person_days"] == 0.25


def test_tolerance_flag_can_turn_a_fail_into_a_pass(tmp_path):
    marginal = CLEAN + "t2,p01,A. Rivera,data-migration,2026-04-15,2026-04-15,0.60\n"
    path = str(write(tmp_path, marginal))
    assert main(["analyze", path, "--quiet"]) == EXIT_HIDDEN
    assert main(["analyze", path, "--quiet", "--tolerance", "0.2"]) == EXIT_OK


def test_generate_writes_a_plan_and_returns_zero(tmp_path, capsys):
    out = tmp_path / "plan.csv"
    code = main(["generate", "--seed", "20260410", "--out", str(out), "--team-size", "10"])
    assert code == EXIT_OK
    assert out.exists()
    assert "wrote" in capsys.readouterr().out


def test_version_flag_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0


def test_no_command_is_an_error(capsys):
    with pytest.raises(SystemExit):
        main([])
