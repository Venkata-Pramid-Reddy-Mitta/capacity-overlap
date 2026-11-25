"""Fail the build when a document quotes a figure the code no longer produces.

Two checks. The forward check turns each anchor into a regex with the number replaced by a capture
group, scans every checked document with whitespace normalised so a wrapped line still matches, and
fails if an anchor phrase carries a number other than the current metric. That is what catches a
stale figure, and it is demonstrable: change one README number and the build goes red. The reverse
check reports any number in the README that matches no metric, excluding code spans and fenced
blocks where an example invocation may legitimately contain a made-up count.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METRICS = ROOT / "docs" / "metrics.json"

_NUMBER = r"(\d[\d,]*(?:\.\d+)?)"


def _value_candidates(value: object) -> set[str]:
    """Every string form the document may legitimately use for this value."""
    out = {str(value)}
    if isinstance(value, float) and value.is_integer():
        out.add(str(int(value)))
    if isinstance(value, int):
        out.add(f"{value}.0")
    return out


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _strip_code(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)  # html tags and their attributes
    return text


def forward_check(metrics: dict, anchors: dict, docs: dict[str, str]) -> list[str]:
    failures: list[str] = []
    joined = {name: _normalise(text) for name, text in docs.items()}
    for metric, templates in anchors.items():
        if metric not in metrics:
            failures.append(f"anchor for unknown metric '{metric}'")
            continue
        value = metrics[metric]
        candidates = _value_candidates(value)
        seen_anywhere = False
        for template in templates:
            pattern = re.escape(template).replace(r"\{\}", _NUMBER)
            regex = re.compile(pattern)
            for doc_name, text in joined.items():
                for match in regex.finditer(text):
                    seen_anywhere = True
                    quoted = match.group(1).replace(",", "")
                    if quoted not in {c.replace(",", "") for c in candidates}:
                        failures.append(
                            f"{doc_name}: '{template.format(quoted)}' is stale; "
                            f"code produces {value}"
                        )
        if not seen_anywhere:
            failures.append(
                f"metric '{metric}' ({value}) has an anchor but appears in no checked document"
            )
    return failures


def reverse_check(metrics: dict, readme: str) -> list[str]:
    known = set()
    for value in metrics.values():
        known |= {c.replace(",", "") for c in _value_candidates(value)}
    warnings: list[str] = []
    prose = _strip_code(readme)
    for match in re.finditer(r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)(?![\w])", prose):
        raw = match.group(1).replace(",", "")
        if raw in known:
            continue
        if _is_ignorable(raw, match, prose):
            continue
        warnings.append(f"README number {match.group(1)} matches no metric")
    return warnings


def _is_ignorable(raw: str, match: re.Match, prose: str) -> bool:
    # Years, version-like small integers, and single digits used in prose are not metrics.
    if raw in {"0", "1", "2", "3", "4", "5", "100"}:
        return True
    if re.fullmatch(r"20\d\d", raw):  # a year
        return True
    context = prose[max(0, match.start() - 12) : match.start()]
    return bool(re.search(r"(Python|ADR|exit code|-)\s*$", context))


def main() -> int:
    payload = json.loads(METRICS.read_text())
    metrics, anchors = payload["metrics"], payload["anchors"]
    docs: dict[str, str] = {}
    for rel in payload["checked_documents"]:
        path = ROOT / rel
        if not path.exists():
            print(f"checked document missing: {rel}", file=sys.stderr)
            return 2
        docs[rel] = path.read_text()

    failures = forward_check(metrics, anchors, docs)
    warnings = reverse_check(metrics, docs.get("README.md", ""))

    for w in warnings:
        print(f"warning: {w}")
    if failures:
        for f in failures:
            print(f"FAIL: {f}", file=sys.stderr)
        print(f"\n{len(failures)} stale or missing figure(s)", file=sys.stderr)
        return 1
    print(f"check_numbers: {len(anchors)} anchored figures match the code")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
