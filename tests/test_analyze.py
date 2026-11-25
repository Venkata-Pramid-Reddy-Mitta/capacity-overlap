"""The reconciliation: hidden detection, the aggregates, and the asymmetry the whole thing rests on."""

from __future__ import annotations

from datetime import date

from capacity_overlap.analyze import analyze
from capacity_overlap.config import AnalysisConfig
from capacity_overlap.ingest import read_plan
from capacity_overlap.model import Assignment, Plan, Sprint

MON = date(2026, 4, 13)
WED = date(2026, 4, 15)
FRI = date(2026, 4, 17)
SPRINT = Sprint(1, MON, FRI)
FIXTURE = "data/plan.csv"


def a(person="p01", start=MON, end=FRI, alloc=0.5, ws="cloud-migration", task="t"):
    return Assignment(person, "N. Name", ws, start, end, alloc, task)


def analyze_assignments(*assignments, config=None, sprints=(SPRINT,)):
    plan = Plan(assignments=tuple(assignments), sprints=tuple(sprints))
    return analyze(plan, config or AnalysisConfig())


def test_a_concentrated_clash_under_full_capacity_is_hidden():
    # base 0.5 all week, plus a 0.75 pull on one day: that day is 1.25 (over), sprint is 65%.
    result = analyze_assignments(
        a(task="base", alloc=0.5),
        a(task="pull", start=WED, end=WED, ws="data-migration", alloc=0.75),
    )
    assert result.hidden_over_person_days == 0.25
    assert result.green_conflicted_pairs == 1
    assert result.people_conflicted_while_green == 1


def test_an_evenly_spread_plan_hides_nothing():
    result = analyze_assignments(a(task="base", alloc=0.5))
    assert result.hidden_over_person_days == 0.0
    assert result.gate_failed() is False


def test_a_visibly_overloaded_person_is_not_counted_as_hidden():
    # Sum above capacity reads above 100%, so its over-allocation is visible, not hidden.
    result = analyze_assignments(
        a(task="base", alloc=0.7),
        a(task="pull", start=MON, end=FRI, ws="data-migration", alloc=0.6),
    )
    assert result.hidden_over_person_days == 0.0
    assert result.visible_over_person_days > 0.0


def test_hidden_plus_visible_equals_total_over_person_days():
    result = analyze(read_plan(FIXTURE), AnalysisConfig())
    assert round(result.hidden_over_person_days + result.visible_over_person_days, 6) == round(
        result.total_over_person_days, 6
    )


def test_any_person_sprint_above_one_hundred_percent_has_a_day_over_capacity():
    # The asymmetry the product depends on: an average above capacity forces a peak above it,
    # so over-allocation above 100% is always visible and only the healthy case can hide one.
    result = analyze(read_plan(FIXTURE), AnalysisConfig())
    for f in result.findings:
        if f.utilization_pct > 100.0 + 1e-9:
            assert f.is_conflicted, (
                f"{f.person_id} s{f.sprint_index} reads >100% but shows no clash"
            )


def test_a_hidden_finding_reads_healthy_and_is_conflicted():
    result = analyze_assignments(
        a(task="base", alloc=0.5),
        a(task="pull", start=WED, end=WED, ws="data-migration", alloc=0.75),
    )
    f = result.hidden_findings[0]
    assert f.reads_healthy is True
    assert f.is_conflicted is True
    assert f.is_hidden is True


def test_worst_hidden_is_the_highest_peak_among_healthy_conflicts():
    result = analyze(read_plan(FIXTURE), AnalysisConfig())
    worst = result.worst_hidden()
    assert worst is not None
    assert worst.peak_pct == max(f.peak_pct for f in result.hidden_findings)


def test_worst_hidden_is_none_when_nothing_is_hidden():
    result = analyze_assignments(a(task="base", alloc=0.5))
    assert result.worst_hidden() is None


def test_hidden_share_is_zero_when_there_is_no_over_allocation():
    result = analyze_assignments(a(task="base", alloc=0.5))
    assert result.hidden_share_pct == 0.0


def test_hidden_share_is_the_hidden_fraction_of_total():
    result = analyze(read_plan(FIXTURE), AnalysisConfig())
    expected = round(result.hidden_over_person_days / result.total_over_person_days * 100, 1)
    assert result.hidden_share_pct == expected


def test_reschedulable_slack_counts_below_capacity_days_in_hidden_sprints():
    """Pins the fix for the war-story bug (docs/war-story.md).

    The first version of this metric counted fully idle days (zero load) and read a structural
    zero on every plan, because the generator gives everyone a horizon-long baseline so no day is
    ever fully idle. The metric now counts days strictly below capacity, the room a clash could
    move into. Here the baseline is 0.5 on five days and one day is pushed to 1.25 by a pull: the
    clash day is at or over capacity, the other four are slack, so the answer is four, not zero.
    """
    result = analyze_assignments(
        a(task="base", alloc=0.5),
        a(task="pull", start=WED, end=WED, ws="data-migration", alloc=0.75),
    )
    assert result.reschedulable_slack_days == 4


def test_raising_tolerance_can_clear_a_marginal_conflict():
    strict = analyze_assignments(
        a(task="base", alloc=0.5),
        a(task="pull", start=WED, end=WED, ws="data-migration", alloc=0.6),
    )
    lax = analyze_assignments(
        a(task="base", alloc=0.5),
        a(task="pull", start=WED, end=WED, ws="data-migration", alloc=0.6),
        config=AnalysisConfig(tolerance=0.2),
    )
    assert strict.gate_failed() is True
    assert lax.gate_failed() is False


def test_aggregate_inputs_describe_the_plan():
    result = analyze(read_plan(FIXTURE), AnalysisConfig())
    assert result.people_total == 26
    assert result.workstreams_total == 4
    assert result.sprints_total == 6


def test_the_committed_fixture_has_the_published_headline():
    # Pins the exact numbers the README and defense guide quote, straight from the fixture.
    result = analyze(read_plan(FIXTURE), AnalysisConfig())
    assert result.hidden_over_person_days == 17.6
    assert result.green_conflicted_pairs == 25
    assert result.people_conflicted_while_green == 16
    assert result.hidden_share_pct == 85.4
