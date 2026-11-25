"""The generator must be byte-for-byte reproducible and plant the three profiles it claims."""

from __future__ import annotations

from capacity_overlap.analyze import analyze
from capacity_overlap.config import AnalysisConfig
from capacity_overlap.generate import WORKSTREAMS, generate_rows, write_plan
from capacity_overlap.ingest import read_plan

SEED = 20260410


def test_the_same_seed_produces_identical_rows():
    assert generate_rows(SEED) == generate_rows(SEED)


def test_a_different_seed_produces_different_rows():
    assert generate_rows(SEED) != generate_rows(SEED + 1)


def test_the_generated_plan_uses_all_four_workstreams():
    streams = {r.workstream for r in generate_rows(SEED)}
    assert streams == set(WORKSTREAMS)


def test_the_team_size_controls_the_number_of_people():
    rows = generate_rows(SEED, team_size=12)
    assert len({r.person_id for r in rows}) == 12


def test_every_person_has_exactly_one_baseline_task():
    rows = generate_rows(SEED)
    baselines = [r for r in rows if r.task_id.startswith("base")]
    assert len(baselines) == len({r.person_id for r in rows})


def test_write_plan_roundtrips_through_the_reader(tmp_path):
    out = tmp_path / "plan.csv"
    count = write_plan(out, seed=SEED)
    plan = read_plan(out)
    assert len(plan.assignments) == count


def test_the_written_plan_reproduces_the_committed_headline(tmp_path):
    out = tmp_path / "plan.csv"
    write_plan(out, seed=SEED)
    result = analyze(read_plan(out), AnalysisConfig())
    assert result.hidden_over_person_days == 17.6


def test_the_generated_plan_contains_both_hidden_and_visible_over_allocation(tmp_path):
    out = tmp_path / "plan.csv"
    write_plan(out, seed=SEED)
    result = analyze(read_plan(out), AnalysisConfig())
    assert result.hidden_over_person_days > 0
    assert result.visible_over_person_days > 0
