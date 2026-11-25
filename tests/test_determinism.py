"""Determinism: the same plan yields the same numbers, independent of row and dict ordering."""

from __future__ import annotations

from capacity_overlap.analyze import analyze
from capacity_overlap.config import AnalysisConfig
from capacity_overlap.ingest import read_plan
from capacity_overlap.model import Plan

FIXTURE = "data/plan.csv"


def test_analysis_is_identical_across_two_runs():
    first = analyze(read_plan(FIXTURE), AnalysisConfig())
    second = analyze(read_plan(FIXTURE), AnalysisConfig())
    assert first.hidden_over_person_days == second.hidden_over_person_days
    assert first.total_over_person_days == second.total_over_person_days
    assert first.green_conflicted_pairs == second.green_conflicted_pairs


def test_shuffling_the_assignment_order_does_not_change_the_headline():
    plan = read_plan(FIXTURE)
    reversed_plan = Plan(assignments=tuple(reversed(plan.assignments)), sprints=plan.sprints)
    base = analyze(plan, AnalysisConfig())
    shuffled = analyze(reversed_plan, AnalysisConfig())
    assert base.hidden_over_person_days == shuffled.hidden_over_person_days
    assert base.worst_hidden().person_id == shuffled.worst_hidden().person_id


def test_the_worst_hidden_tiebreak_is_stable():
    # Two runs must pick the same worst person even when several share the top peak.
    a = analyze(read_plan(FIXTURE), AnalysisConfig()).worst_hidden()
    b = analyze(read_plan(FIXTURE), AnalysisConfig()).worst_hidden()
    assert (a.person_id, a.sprint_index) == (b.person_id, b.sprint_index)
