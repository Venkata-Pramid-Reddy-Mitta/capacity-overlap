"""Rendering: one source of numbers, three surfaces, and a badge that must not render invisible."""

from __future__ import annotations

from datetime import date

from capacity_overlap.analyze import analyze
from capacity_overlap.config import AnalysisConfig
from capacity_overlap.model import Assignment, Plan, Sprint
from capacity_overlap.report import render_html, render_json, render_text, result_dict

MON = date(2026, 4, 13)
WED = date(2026, 4, 15)
FRI = date(2026, 4, 17)


def hidden_result():
    plan = Plan(
        assignments=(
            Assignment("p01", "A. Rivera", "cloud-migration", MON, FRI, 0.5, "base"),
            Assignment("p01", "A. Rivera", "data-migration", WED, WED, 0.75, "pull"),
        ),
        sprints=(Sprint(1, MON, FRI),),
    )
    return analyze(plan, AnalysisConfig())


def clean_result():
    plan = Plan(
        assignments=(Assignment("p01", "A. Rivera", "cloud-migration", MON, FRI, 0.5, "base"),),
        sprints=(Sprint(1, MON, FRI),),
    )
    return analyze(plan, AnalysisConfig())


def test_result_dict_headline_matches_the_analysis():
    d = result_dict(hidden_result())
    assert d["headline"]["hidden_over_person_days"] == 0.25
    assert d["headline"]["people_conflicted_while_green"] == 1


def test_result_dict_worst_hidden_is_null_when_clean():
    assert result_dict(clean_result())["worst_hidden"] is None


def test_text_report_leads_with_the_hidden_number():
    text = render_text(hidden_result())
    assert "HIDDEN over-allocation: 0.25 person-days" in text


def test_text_report_states_a_fail_verdict_when_hidden_exists():
    assert "FAIL: hidden over-allocation present" in render_text(hidden_result())


def test_text_report_states_a_pass_verdict_when_clean():
    assert "PASS: clean" in render_text(clean_result())


def test_json_report_is_valid_and_round_trips():
    import json

    d = json.loads(render_json(hidden_result()))
    assert d["headline"]["green_conflicted_pairs"] == 1


def test_html_report_carries_the_fail_badge_when_hidden():
    html = render_html(hidden_result())
    assert "badge-fail" in html
    assert "HIDDEN OVER-ALLOCATION" in html


def test_html_report_carries_the_pass_badge_when_clean():
    html = render_html(clean_result())
    assert "badge-pass" in html
    assert ">CLEAN<" in html


def test_html_report_lists_the_conflicted_person():
    html = render_html(hidden_result())
    assert "A. Rivera" in html


def test_every_css_class_used_in_the_html_has_a_rule():
    # Guards the badge-invisible failure at the source: a class in the markup with no stylesheet rule.
    import re

    html = render_html(hidden_result())
    used = set(re.findall(r'class="([^"]+)"', html))
    classes = {c for group in used for c in group.split()}
    style_block = html.split("<style>")[1].split("</style>")[0]
    for cls in classes:
        assert f".{cls}" in style_block, f"class {cls} used in markup but absent from stylesheet"
