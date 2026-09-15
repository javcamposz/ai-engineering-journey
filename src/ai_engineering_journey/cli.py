from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .assessment import AssessmentError, assess, render_roadmap
from .pipeline import assess_readiness, render_readiness
from .progress import compare, render_progress

EXIT_OK = 0
EXIT_INPUT_ERROR = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate an AI engineering transformation roadmap")
    subparsers = parser.add_subparsers(dest="command", required=True)
    command = subparsers.add_parser("assess", help="assess a JSON capability profile")
    command.add_argument("input", type=Path)
    command.add_argument("--output", type=Path)
    command.set_defaults(handler=_assess)

    journey = subparsers.add_parser(
        "progress", help="grade a later assessment against what the earlier roadmap asked for"
    )
    journey.add_argument("before", type=Path, help="the earlier capability profile")
    journey.add_argument("after", type=Path, help="the later capability profile")
    journey.add_argument("--output", type=Path)
    journey.set_defaults(handler=_progress)

    readiness = subparsers.add_parser(
        "readiness",
        help="report how far down the UX bug automation pipeline a profile can run",
    )
    readiness.add_argument("input", type=Path)
    readiness.add_argument("--output", type=Path)
    readiness.set_defaults(handler=_readiness)
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


def _assessment(path: Path):
    payload = _load(path)
    return assess(
        _text(payload.get("organization")),
        _text(payload.get("context")),
        payload.get("scores", {}),
        _text(payload.get("assessed_on")) or None,
    )


def _emit(report: str, output: Path | None) -> None:
    if output:
        output.write_text(report, encoding="utf-8")
    else:
        print(report)


def _assess(args: argparse.Namespace) -> int:
    result = _assessment(args.input)
    _emit(render_roadmap(result), args.output)

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


def _progress(args: argparse.Namespace) -> int:
    progress = compare(_assessment(args.before), _assessment(args.after))
    _emit(render_progress(progress), args.output)

    interval = "interval not recorded" if progress.days is None else f"{progress.days} days"
    print(f"Organization: {progress.after.organization} ({interval})")
    print(f"Stage: {progress.before.maturity} to {progress.after.maturity}"
          + ("" if progress.stage_changed else " (unchanged)"))
    print(f"Priorities delivered: {len(progress.delivered)} of "
          f"{len(progress.delivered) + len(progress.stalled)}")
    if progress.stalled:
        print(f"Stalled: {', '.join(item.pillar.title() for item in progress.stalled)}")
    if progress.collateral:
        print(f"Regressed while unattended: "
              f"{', '.join(item.pillar.title() for item in progress.collateral)}")
    print("Same bottleneck: " + ("yes" if progress.same_bottleneck else "no"))
    if args.output:
        print(f"Progress report written to {args.output}")
    return EXIT_OK


def _readiness(args: argparse.Namespace) -> int:
    readiness = assess_readiness(_assessment(args.input))
    _emit(render_readiness(readiness), args.output)

    total = len(readiness.stages)
    print(f"Organization: {readiness.assessment.organization}")
    print(f"Pipeline: UX bug automation ({total} stages)")
    if readiness.stops_at is None:
        print(f"Reach: all {total} stages")
    else:
        print(f"Reach: {readiness.reach} of {total}, stopping at {readiness.stops_at.stage.name}")
        print(f"Blocked by: {readiness.stops_at.describe_shortfalls()}")
    if readiness.resourced_but_unreachable:
        names = ", ".join(s.stage.name for s in readiness.resourced_but_unreachable)
        print(f"Resourced but unreachable: {names}")
    if args.output:
        print(f"Readiness report written to {args.output}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except AssessmentError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR
