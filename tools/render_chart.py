"""Plot the aggregation-window sensitivity curve from the experiment JSON.

The one figure where a plot beats a table: over-allocation the aggregate can see, against the width
of the reporting window. Reading the committed experiment JSON (rather than recomputing) keeps the
chart and the number in the README from the same source, so they cannot disagree.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "experiments" / "aggregation_window.json"
OUT = ROOT / "docs" / "img" / "aggregation_window.png"


def main() -> int:
    payload = json.loads(DATA.read_text())
    windows = [r["window_working_days"] for r in payload["rows"]]
    seen = [r["aggregate_over_person_days"] for r in payload["rows"]]

    fig, ax = plt.subplots(figsize=(7.2, 3.8), dpi=150)
    ax.plot(windows, seen, marker="o", color="#2f6feb", linewidth=2)
    ax.fill_between(windows, seen, color="#2f6feb", alpha=0.08)
    ax.set_xscale("log")
    ax.set_xticks(windows)
    ax.set_xticklabels([str(w) for w in windows])
    ax.set_xlabel("reporting window (working days, log scale)")
    ax.set_ylabel("over-allocation the aggregate sees\n(person-days)")
    ax.set_title("A wider window hides more: aggregate over-allocation vs reporting window")
    ax.grid(True, which="both", linewidth=0.4, alpha=0.5)
    ax.annotate(
        f"daily view: {payload['daily_over_person_days']} person-days (the truth)",
        xy=(windows[0], seen[0]), xytext=(1.4, seen[0] - 2.5),
        fontsize=9, color="#333",
    )
    ax.annotate(
        f"10-day sprint: {payload['sprint_over_person_days']}",
        xy=(10, payload["sprint_over_person_days"]), xytext=(11, 6),
        fontsize=9, color="#b42318",
        arrowprops={"arrowstyle": "->", "color": "#b42318"},
    )
    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT)
    plt.close(fig)
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
