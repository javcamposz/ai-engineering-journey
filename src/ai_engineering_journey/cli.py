from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .assessment import AssessmentError, assess, render_roadmap

EXIT_OK = 0
EXIT_INPUT_ERROR = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate an AI engineering transformation roadmap")
    subparsers = parser.add_subparsers(dest="command", required=True)
    command = subparsers.add_parser("assess", help="assess a JSON capability profile")
    command.add_argument("input", type=Path)
    command.add_argument("--output", type=Path)
    return parser


def _text(value: object) -> str:
    """A JSON null is an absent name, not the word None."""
    return "" if value is None else str(value)


def _load(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AssessmentError([f"{path} is not valid JSON: {exc}"]) from exc
    if not isinstance(payload, dict):
        raise AssessmentError([f"{path} must contain a JSON object"])
    scores = payload.get("scores", {})
    if not isinstance(scores, dict):
        raise AssessmentError(["scores must be a JSON object mapping each capability to 1-5"])
    return payload


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = _load(args.input)
        result = assess(
            _text(payload.get("organization")),
            _text(payload.get("context")),
            payload.get("scores", {}),
        )
    except AssessmentError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR

    report = render_roadmap(result)
    if args.output:
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report)

    print(f"Organization: {result.organization}")
    print(f"Maturity: {result.maturity} ({result.overall:.1f}/5.0 capability average)")
    if result.is_limited:
        limiting = ", ".join(item.title() for item in result.limiting_pillars)
        print(f"Held below {result.average_stage} by: {limiting}")
    if result.is_uniform:
        print("Priority constraints: none stand out; every capability is at the same level")
    else:
        print(f"Priority constraints: {', '.join(item.title() for item in result.priorities)}")
    if args.output:
        print(f"Roadmap written to {args.output}")
    return EXIT_OK
