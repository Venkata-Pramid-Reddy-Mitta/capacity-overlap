"""Rendering: the same Analysis as a terminal summary, a JSON payload, and an HTML report.

Three renderers, one source of numbers. The JSON is what the experiments and the receipts tooling
read, so no figure is ever typed twice. The HTML exists for the committed screenshot and carries a
verdict badge whose colour the screenshot tool reads back, because a headline that renders invisible
is the failure mode the evidence step is there to catch.
"""

from __future__ import annotations

import html
import json

from .analyze import Analysis


def result_dict(analysis: Analysis) -> dict:
    """A JSON-serialisable summary. The single structure every downstream consumer reads."""
    worst = analysis.worst_hidden()
    return {
        "inputs": {
            "people_total": analysis.people_total,
            "workstreams_total": analysis.workstreams_total,
            "sprints_total": analysis.sprints_total,
            "horizon_working_days": analysis.horizon_working_days,
            "capacity_fte": analysis.config.capacity_fte,
            "tolerance": analysis.config.tolerance,
        },
        "headline": {
            "hidden_over_person_days": analysis.hidden_over_person_days,
            "total_over_person_days": analysis.total_over_person_days,
            "visible_over_person_days": analysis.visible_over_person_days,
            "hidden_share_pct": analysis.hidden_share_pct,
            "green_conflicted_pairs": analysis.green_conflicted_pairs,
            "people_conflicted_while_green": analysis.people_conflicted_while_green,
            "reschedulable_slack_days": analysis.reschedulable_slack_days,
        },
        "worst_hidden": None
        if worst is None
        else {
            "person_id": worst.person_id,
            "person_name": worst.person_name,
            "sprint_index": worst.sprint_index,
            "utilization_pct": worst.utilization_pct,
            "peak_pct": worst.peak_pct,
            "over_person_days": worst.over_person_days,
            "over_days": [od.day.isoformat() for od in worst.over_days],
        },
        "hidden_findings": [
            {
                "person_id": f.person_id,
                "person_name": f.person_name,
                "sprint_index": f.sprint_index,
                "utilization_pct": f.utilization_pct,
                "peak_pct": f.peak_pct,
                "over_person_days": f.over_person_days,
                "over_days": [od.day.isoformat() for od in f.over_days],
                "slack_days": f.slack_days,
            }
            for f in sorted(
                analysis.hidden_findings,
                key=lambda f: (-f.peak_load, -f.over_person_days, f.person_id),
            )
        ],
    }


def render_text(analysis: Analysis) -> str:
    h = analysis.hidden_over_person_days
    lines = [
        "capacity-overlap report",
        "=" * 48,
        f"people: {analysis.people_total}   workstreams: {analysis.workstreams_total}   "
        f"sprints: {analysis.sprints_total}   working days: {analysis.horizon_working_days}",
        f"capacity: {analysis.config.capacity_fte} FTE   tolerance: {analysis.config.tolerance}",
        "",
        f"HIDDEN over-allocation: {h} person-days",
        f"  across {analysis.green_conflicted_pairs} person-sprint pairs that read at or below "
        f"100%,",
        f"  affecting {analysis.people_conflicted_while_green} people the sprint view "
        f"calls healthy.",
        f"total over-allocation: {analysis.total_over_person_days} person-days "
        f"({analysis.hidden_share_pct}% of it invisible at sprint level)",
        f"reschedulable slack in those same sprints: {analysis.reschedulable_slack_days} days",
    ]
    worst = analysis.worst_hidden()
    if worst is not None:
        lines += [
            "",
            "worst hidden case:",
            f"  {worst.person_name} ({worst.person_id}), sprint {worst.sprint_index}: "
            f"sprint reads {worst.utilization_pct}%, peaks at {worst.peak_pct}% on a single day",
            f"  clash days: {', '.join(od.day.isoformat() for od in worst.over_days)}",
        ]
    verdict = "FAIL: hidden over-allocation present" if analysis.gate_failed() else "PASS: clean"
    lines += ["", verdict]
    return "\n".join(lines)


def render_json(analysis: Analysis) -> str:
    return json.dumps(result_dict(analysis), indent=2)


def render_html(analysis: Analysis) -> str:
    d = result_dict(analysis)
    hd = d["headline"]
    failed = analysis.gate_failed()
    badge_class = "badge-fail" if failed else "badge-pass"
    badge_text = "HIDDEN OVER-ALLOCATION" if failed else "CLEAN"
    rows = "".join(
        f"<tr><td>{html.escape(f['person_name'])} ({html.escape(f['person_id'])})</td>"
        f"<td class='num'>{f['sprint_index']}</td>"
        f"<td class='num'>{f['utilization_pct']}%</td>"
        f"<td class='num peak'>{f['peak_pct']}%</td>"
        f"<td class='num'>{f['over_person_days']}</td>"
        f"<td>{html.escape(', '.join(f['over_days']))}</td></tr>"
        for f in d["hidden_findings"][:12]
    )
    return _HTML_TEMPLATE.format(
        badge_class=badge_class,
        badge_text=badge_text,
        hidden=hd["hidden_over_person_days"],
        pairs=hd["green_conflicted_pairs"],
        people=hd["people_conflicted_while_green"],
        total=hd["total_over_person_days"],
        share=hd["hidden_share_pct"],
        slack=hd["reschedulable_slack_days"],
        people_total=d["inputs"]["people_total"],
        rows=rows,
    )


_HTML_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>capacity-overlap report</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; color: #1a1a1a;
         background: #ffffff; margin: 0; padding: 32px; }}
  h1 {{ font-size: 22px; margin: 0 0 4px; }}
  .sub {{ color: #555; margin: 0 0 20px; font-size: 13px; }}
  .badge {{ display: inline-block; padding: 6px 14px; border-radius: 4px; font-weight: 700;
            font-size: 13px; letter-spacing: .4px; color: #ffffff; }}
  .badge-fail {{ background: #b42318; }}
  .badge-pass {{ background: #067647; }}
  .cards {{ display: flex; gap: 16px; margin: 20px 0 8px; flex-wrap: wrap; }}
  .card {{ border: 1px solid #e3e3e3; border-radius: 8px; padding: 14px 18px; min-width: 150px; }}
  .card .n {{ font-size: 26px; font-weight: 700; }}
  .card .l {{ font-size: 12px; color: #555; margin-top: 2px; }}
  .card.head .n {{ color: #b42318; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 18px; font-size: 13px; }}
  th, td {{ border-bottom: 1px solid #ececec; padding: 7px 10px; text-align: left; }}
  th {{ background: #f6f6f6; font-size: 12px; }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  td.peak {{ font-weight: 700; color: #b42318; }}
  h2 {{ font-size: 15px; margin: 24px 0 2px; }}
</style></head>
<body>
  <h1>capacity-overlap</h1>
  <p class="sub">day-level over-allocation hidden under a sprint utilization view
    of {people_total} people</p>
  <span class="badge {badge_class}">{badge_text}</span>
  <div class="cards">
    <div class="card head"><div class="n">{hidden}</div>
      <div class="l">hidden person-days</div></div>
    <div class="card"><div class="n">{pairs}</div>
      <div class="l">green person-sprint pairs with a clash</div></div>
    <div class="card"><div class="n">{people}</div>
      <div class="l">people called healthy</div></div>
    <div class="card"><div class="n">{share}%</div>
      <div class="l">of all over-allocation invisible</div></div>
    <div class="card"><div class="n">{slack}</div>
      <div class="l">reschedulable slack days</div></div>
  </div>
  <p class="sub">total over-allocation across the plan: {total} person-days</p>
  <h2>The people a sprint bar shows as at or below 100%</h2>
  <table>
    <thead><tr><th>person</th><th>sprint</th><th>sprint util</th><th>peak day</th>
      <th>over person-days</th><th>clash days</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</body></html>
"""
