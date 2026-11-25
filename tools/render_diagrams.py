"""Render the architecture diagram to a committed SVG with intrinsic dimensions and a light ground.

The SVG is authored here from a small node and edge description rather than rendered from a Mermaid
fence, for two reasons learned from the rendering traps: GitHub refuses to render some Mermaid
fences from inside its own lazily loaded renderer, and a committed Mermaid SVG embedded with
<img src> breaks unless HTML labels are off and the root carries explicit width and height.
Authoring the SVG gives text labels, a fixed viewBox, and a light ground, nothing to vendor.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "architecture.svg"

# (id, label, column, row). Columns left to right, rows top to bottom.
NODES = [
    ("csv", "plan.csv\n(assignments)", 0, 1),
    ("ingest", "ingest\npandas to model", 1, 1),
    ("cal", "calendar\nworking days", 1, 3),
    ("overlap", "overlap\nday-level load", 2, 0),
    ("sprint", "sprintview\nsprint aggregate", 2, 2),
    ("analyze", "analyze\nreconcile", 3, 1),
    ("report", "report + cli\ntext / json / html / exit code", 4, 1),
]
EDGES = [
    ("csv", "ingest"),
    ("ingest", "overlap"),
    ("ingest", "sprint"),
    ("cal", "overlap"),
    ("cal", "sprint"),
    ("overlap", "analyze"),
    ("sprint", "analyze"),
    ("analyze", "report"),
]

COL_W, ROW_H = 190, 86
BOX_W, BOX_H = 150, 56
PAD = 30


def _xy(col: int, row: int) -> tuple[int, int]:
    return PAD + col * COL_W, PAD + row * ROW_H


def render() -> str:
    positions = {nid: _xy(c, r) for nid, _, c, r in NODES}
    width = PAD * 2 + (max(c for _, _, c, _ in NODES)) * COL_W + BOX_W
    height = PAD * 2 + (max(r for _, _, _, r in NODES)) * ROW_H + BOX_H

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Segoe UI, Helvetica, Arial, sans-serif">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#fbfbfd"/>',
        '<defs><marker id="arrow" markerWidth="9" markerHeight="9" refX="7" refY="3" '
        'orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="#5b6472"/></marker></defs>',
    ]

    for src, dst in EDGES:
        x1, y1 = positions[src]
        x2, y2 = positions[dst]
        sx, sy = x1 + BOX_W, y1 + BOX_H // 2
        tx, ty = x2, y2 + BOX_H // 2
        midx = (sx + tx) / 2
        parts.append(
            f'<path d="M{sx},{sy} C{midx},{sy} {midx},{ty} {tx - 2},{ty}" '
            f'fill="none" stroke="#5b6472" stroke-width="1.6" marker-end="url(#arrow)"/>'
        )

    for nid, label, col, row in NODES:
        x, y = _xy(col, row)
        fill = "#eef4ff" if nid in {"overlap", "analyze"} else "#f3f4f6"
        stroke = "#2f6feb" if nid in {"overlap", "analyze"} else "#c7cbd3"
        parts.append(
            f'<rect x="{x}" y="{y}" width="{BOX_W}" height="{BOX_H}" rx="7" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>'
        )
        lines = label.split("\n")
        start_y = y + BOX_H // 2 - (len(lines) - 1) * 8 + 4
        for i, line in enumerate(lines):
            weight = "600" if i == 0 else "400"
            colour = "#1a1a1a" if i == 0 else "#55606e"
            size = 13 if i == 0 else 11
            parts.append(
                f'<text x="{x + BOX_W // 2}" y="{start_y + i * 16}" text-anchor="middle" '
                f'font-size="{size}" font-weight="{weight}" fill="{colour}">{line}</text>'
            )

    parts.append("</svg>")
    return "\n".join(parts)


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render() + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
