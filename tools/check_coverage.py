"""Fail the build when line coverage falls below a floor, reading coverage.xml.

A floor in CI rather than a target in a README: a number nobody enforces drifts down. The script
reads the Cobertura XML that pytest-cov writes, computes the line rate, and exits non-zero below the
floor so the Actions job turns red rather than merely printing a lower number.
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def line_rate(coverage_xml: Path) -> float:
    root = ET.parse(coverage_xml).getroot()
    return float(root.attrib["line-rate"]) * 100


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Enforce a coverage floor from coverage.xml.")
    parser.add_argument("--floor", type=float, default=95.0)
    parser.add_argument("--xml", type=Path, default=Path("coverage.xml"))
    args = parser.parse_args(argv)

    if not args.xml.exists():
        print(f"coverage file not found: {args.xml}", file=sys.stderr)
        return 2

    rate = line_rate(args.xml)
    if rate + 1e-9 < args.floor:
        print(f"coverage {rate:.2f}% is below the floor of {args.floor:.2f}%", file=sys.stderr)
        return 1
    print(f"coverage {rate:.2f}% meets the floor of {args.floor:.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
