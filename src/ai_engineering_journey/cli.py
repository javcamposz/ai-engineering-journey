from __future__ import annotations

import argparse
import json
from pathlib import Path

from .assessment import assess, render_roadmap


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate an AI engineering transformation roadmap")
    subparsers = parser.add_subparsers(dest="command", required=True)
    command = subparsers.add_parser("assess", help="assess a JSON capability profile")
    command.add_argument("input", type=Path)
    command.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = assess(payload.get("organization", ""), payload.get("context", ""), payload.get("scores", {}))
    report = render_roadmap(result)

    if args.output:
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report)

    priorities = ", ".join(item.title() for item in result.priorities)
    print(f"Organization: {result.organization}")
    print(f"Maturity: {result.maturity} ({result.overall:.1f}/5.0)")
    print(f"Priority constraints: {priorities}")
    if args.output:
        print(f"Roadmap written to {args.output}")
    return 0
