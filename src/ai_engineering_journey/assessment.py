from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Mapping

PILLARS = (
    "product",
    "workflow",
    "evaluation",
    "architecture",
    "platform",
    "governance",
    "learning",
)

ACTIONS = {
    "product": (
        "Define one bounded workflow and its baseline user outcome.",
        "Instrument acceptance, rework, and service-quality measures.",
        "Use outcome evidence to stop, reshape, or scale AI use cases.",
    ),
    "workflow": (
        "Adopt small, reviewable changes with named human accountability.",
        "Standardize context, review, and rollback patterns across teams.",
        "Continuously optimize flow using delivery and defect evidence.",
    ),
    "evaluation": (
        "Create a representative task set and record the non-AI baseline.",
        "Gate releases with deterministic tests and task-specific evals.",
        "Monitor drift and refresh evals from production failures.",
    ),
    "architecture": (
        "Put model calls behind typed interfaces and explicit permissions.",
        "Separate planning, execution, and verification boundaries.",
        "Design for model substitution, trace replay, and graceful failure.",
    ),
    "platform": (
        "Publish approved tools, models, and data-handling constraints.",
        "Provide reusable telemetry, evaluation, and deployment paths.",
        "Manage cost, latency, and quality as an integrated portfolio.",
    ),
    "governance": (
        "Tier use cases by impact and assign accountable decision owners.",
        "Attach evidence and approval gates to higher-impact releases.",
        "Review incidents and leading indicators at portfolio level.",
    ),
    "learning": (
        "Run weekly demonstrations and capture reusable delivery patterns.",
        "Build role-based practice around real engineering tasks.",
        "Update standards and training from measured delivery evidence.",
    ),
}


@dataclass(frozen=True)
class Assessment:
    organization: str
    context: str
    scores: dict[str, int]
    overall: float
    maturity: str
    priorities: tuple[str, ...]


def _maturity(score: float) -> str:
    if score < 1.8:
        return "Exploratory"
    if score < 2.6:
        return "Assisted"
    if score < 3.4:
        return "Repeatable"
    if score < 4.2:
        return "Measured"
    return "Adaptive"


def assess(organization: str, context: str, scores: Mapping[str, object]) -> Assessment:
    missing = sorted(set(PILLARS) - set(scores))
    extra = sorted(set(scores) - set(PILLARS))
    if missing or extra:
        raise ValueError(f"scores must contain exactly {', '.join(PILLARS)}; missing={missing}, extra={extra}")

    validated: dict[str, int] = {}
    for pillar in PILLARS:
        value = scores[pillar]
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
            raise ValueError(f"{pillar} must be an integer from 1 to 5")
        validated[pillar] = value

    overall = round(mean(validated.values()), 1)
    priorities = tuple(sorted(PILLARS, key=lambda item: (validated[item], PILLARS.index(item)))[:3])
    return Assessment(
        organization=organization.strip() or "Unnamed organization",
        context=context.strip(),
        scores=validated,
        overall=overall,
        maturity=_maturity(overall),
        priorities=priorities,
    )


def render_roadmap(result: Assessment) -> str:
    phase_labels = ("Days 0-30: establish evidence", "Days 31-90: make it repeatable", "Months 4-6: scale with control")
    lines = [
        f"# AI Engineering Roadmap: {result.organization}",
        "",
        f"**Maturity:** {result.maturity} ({result.overall:.1f}/5.0)",
        "",
    ]
    if result.context:
        lines.extend([result.context, ""])

    lines.extend(["## Capability Baseline", "", "| Capability | Score |", "|---|---:|"])
    lines.extend(f"| {pillar.title()} | {result.scores[pillar]}/5 |" for pillar in PILLARS)
    lines.extend(["", "## Priority Constraints", ""])
    lines.extend(f"- **{pillar.title()}**: {ACTIONS[pillar][0]}" for pillar in result.priorities)

    for phase_index, label in enumerate(phase_labels):
        lines.extend(["", f"## {label}", ""])
        for pillar in result.priorities:
            lines.append(f"- **{pillar.title()}:** {ACTIONS[pillar][phase_index]}")

    lines.extend([
        "",
        "## Evidence Review",
        "",
        "At the end of each phase, review cycle time, accepted-change rate, escaped defects, evaluation pass rate, incidents, cost, and user outcome movement. Do not scale a practice whose benefit or control evidence remains unclear.",
        "",
    ])
    return "\n".join(lines)
