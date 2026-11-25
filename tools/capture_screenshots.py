"""Screenshot the real HTML report, and fail if the verdict badge renders illegibly.

The report is generated here from the committed fixture, never photographed off disk, so a stale
report cannot be captured. After the shot the tool reads back the computed style of the verdict
badge and fails when its text and background are the same colour or it has zero size, because a
headline that renders invisible is exactly the failure a screenshot step exists to catch. A manifest
records the badge reading and the framing so the evidence is reproducible.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from capacity_overlap.analyze import analyze  # noqa: E402
from capacity_overlap.config import AnalysisConfig  # noqa: E402
from capacity_overlap.ingest import read_plan  # noqa: E402
from capacity_overlap.report import render_html  # noqa: E402

OUT_PNG = ROOT / "docs" / "img" / "report.png"
OUT_HTML = ROOT / "docs" / "img" / "report.html"
MANIFEST = ROOT / "docs" / "img" / "manifest.json"
CHROME = "/usr/bin/google-chrome"


def build_report() -> str:
    result = analyze(read_plan(ROOT / "data" / "plan.csv"), AnalysisConfig())
    return render_html(result)


def main() -> int:
    from playwright.sync_api import sync_playwright

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    html = build_report()
    OUT_HTML.write_text(html)

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1000, "height": 760}, device_scale_factor=2)
        page.goto(OUT_HTML.as_uri())
        badge = page.evaluate(
            """() => {
                const b = document.querySelector('.badge');
                if (!b) return null;
                const s = getComputedStyle(b);
                return {color: s.color, background: s.backgroundColor,
                        w: b.offsetWidth, h: b.offsetHeight};
            }"""
        )
        if badge is None or badge["w"] == 0 or badge["h"] == 0:
            print("FAIL: verdict badge is missing or zero-sized", file=sys.stderr)
            return 1
        if badge["color"] == badge["background"]:
            print("FAIL: verdict badge text and background are the same colour", file=sys.stderr)
            return 1
        page.screenshot(path=str(OUT_PNG), full_page=True)
        browser.close()

    MANIFEST.write_text(
        json.dumps(
            {
                "image": "report.png",
                "source": "render_html on data/plan.csv (capacity 1.0, tolerance 0.0)",
                "badge": badge,
                "note": "regenerate with: python tools/capture_screenshots.py",
            },
            indent=2,
        )
        + "\n"
    )
    print(f"wrote {OUT_PNG.relative_to(ROOT)} (badge {badge['color']} on {badge['background']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
