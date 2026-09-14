from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from statistics import mean
from typing import Mapping

MINIMUM_SCORE = 1
MAXIMUM_SCORE = 5

# date.fromisoformat accepts the whole ISO 8601 set from Python 3.11, so "20260115" and
# "2026-W03-4" parse there and are rejected on 3.10. Both are supported, so the shape is
# checked first and only the documented one reaches the parser.
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

PILLARS = (
    "product",
    "workflow",
    "evaluation",
    "architecture",
    "platform",
    "governance",
    "learning",
)

# Each pillar's actions are rungs on a ladder, not a three-month schedule. A capability
# joins the ladder at the rung its current score has reached and climbs one rung per phase,
# so a pillar at 1/5 and a pillar at 4/5 are given different work.
RUNGS = ("establish", "standardise", "optimise")
SCORE_RUNG = {1: 0, 2: 0, 3: 1, 4: 2, 5: 2}

# Stage names in ascending order, and the stage a single pillar's score demonstrates.
STAGES = ("Exploratory", "Assisted", "Repeatable", "Measured", "Adaptive")
PILLAR_STAGE = {1: "Exploratory", 2: "Assisted", 3: "Repeatable", 4: "Measured", 5: "Adaptive"}

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


class AssessmentError(ValueError):
    """Every problem found in a capability profile, reported together."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = list(problems)
        detail = "\n".join(f"  - {problem}" for problem in self.problems)
        noun = "problem" if len(self.problems) == 1 else "problems"
        super().__init__(f"{len(self.problems)} {noun} in the capability profile\n{detail}")


@dataclass(frozen=True)
class Assessment:
    organization: str
    context: str
    scores: dict[str, int]
    overall: float
    maturity: str
    priorities: tuple[str, ...]
    average_stage: str
    limiting_pillars: tuple[str, ...]
    assessed_on: date | None = None

    @property
    def bottleneck(self) -> tuple[str, ...]:
        """The capabilities at the lowest score, which is what sets the stage.

        Distinct from limiting_pillars, which is empty when the average agrees with the
        weakest capability. Something is always the bottleneck; it is not always a gap.
        """
        lowest = min(self.scores.values())
        return tuple(pillar for pillar in PILLARS if self.scores[pillar] == lowest)

    @property
    def is_limited(self) -> bool:
        """True when the weakest capability holds the organization below its average."""
        return self.maturity != self.average_stage

    @property
    def is_uniform(self) -> bool:
        return len(set(self.scores.values())) == 1

    def rung(self, pillar: str) -> int:
        return SCORE_RUNG[self.scores[pillar]]

    def ladder(self, pillar: str) -> tuple[tuple[int, str], ...]:
        """The (phase, action) pairs for one pillar, climbing one rung per phase."""
        return tuple(
            (phase, ACTIONS[pillar][rung])
            for phase, rung in enumerate(range(self.rung(pillar), len(RUNGS)))
        )


def _maturity(score: float) -> str:
    """Stage implied by the capability average, read from the unrounded mean.

    Bucketing a rounded mean moved organizations up a stage: seven scores summing to 18
    average 2.571, which is Assisted, but round to 2.6 and were reported as Repeatable.
    """
    if score < 1.8:
        return "Exploratory"
    if score < 2.6:
        return "Assisted"
    if score < 3.4:
        return "Repeatable"
    if score < 4.2:
        return "Measured"
    return "Adaptive"


def _constraints(scores: dict[str, int]) -> tuple[str, ...]:
    """Capabilities that actually hold the organization back.

    A capability is a constraint when it sits below the organization's own average or at
    the lowest score in the profile. Taking the bottom three regardless of value named
    capabilities scoring 5/5 as constraints and silently dropped the fourth pillar of a
    four-way tie.
    """
    average = mean(scores.values())
    lowest = min(scores.values())
    return tuple(
        pillar for pillar in PILLARS
        if scores[pillar] < average or scores[pillar] == lowest
    )


def assess(
    organization: str,
    context: str,
    scores: Mapping[str, object],
    assessed_on: str | None = None,
) -> Assessment:
    problems: list[str] = []
    taken_on: date | None = None
    if assessed_on:
        if not ISO_DATE.match(assessed_on):
            problems.append(f"assessed_on is {assessed_on!r}; it must be a date as YYYY-MM-DD")
        else:
            try:
                taken_on = date.fromisoformat(assessed_on)
            except ValueError:
                problems.append(
                    f"assessed_on is {assessed_on!r}; that is not a real date"
                )
    missing = [pillar for pillar in PILLARS if pillar not in scores]
    if missing:
        noun = "capability is" if len(missing) == 1 else "capabilities are"
        problems.append(f"{len(missing)} {noun} missing: {', '.join(missing)}")
    extra = sorted(key for key in scores if key not in set(PILLARS))
    if extra:
        noun = "is not a capability" if len(extra) == 1 else "are not capabilities"
        problems.append(f"{', '.join(extra)} {noun}; the seven are {', '.join(PILLARS)}")

    validated: dict[str, int] = {}
    for pillar in PILLARS:
        if pillar not in scores:
            continue
        value = scores[pillar]
        if isinstance(value, bool) or not isinstance(value, int):
            problems.append(f"{pillar} must be an integer from {MINIMUM_SCORE} to {MAXIMUM_SCORE}")
        elif not MINIMUM_SCORE <= value <= MAXIMUM_SCORE:
            problems.append(
                f"{pillar} is {value}; scores run from {MINIMUM_SCORE} to {MAXIMUM_SCORE}"
            )
        else:
            validated[pillar] = value

    if problems:
        raise AssessmentError(problems)

    average = mean(validated.values())
    average_stage = _maturity(average)
    weakest = min(validated.values())

    # The stage is the one the weakest capability demonstrates, not a blend. Each stage in
    # the operating model has exit evidence, and that evidence is per capability: an
    # organization cannot claim Repeatable, whose exit evidence is stable evals, while
    # evaluation sits at 2/5. A strong platform does not buy a stage evaluation has not
    # reached. Taking min() with the average stage would be dead code: a weakest score of w
    # forces the mean to at least w, so the average stage is never the lower of the two.
    maturity = PILLAR_STAGE[weakest]
    limiting = tuple(pillar for pillar in PILLARS if validated[pillar] == weakest)

    priorities = tuple(
        sorted(_constraints(validated), key=lambda item: (validated[item], PILLARS.index(item)))
    )
    return Assessment(
        organization=organization.strip() or "Unnamed organization",
        context=context.strip(),
        scores=validated,
        overall=round(average, 1),
        maturity=maturity,
        priorities=priorities,
        average_stage=average_stage,
        limiting_pillars=limiting if maturity != average_stage else (),
        assessed_on=taken_on,
    )


PHASE_LABELS = (
    "Days 0-30: establish evidence",
    "Days 31-90: make it repeatable",
    "Months 4-6: scale with control",
)


def render_roadmap(result: Assessment) -> str:
    lines = [
        f"# AI Engineering Roadmap: {result.organization}",
        "",
        f"**Maturity:** {result.maturity} ({result.overall:.1f}/5.0 capability average)",
        "",
    ]
    if result.is_limited:
        limiting = ", ".join(pillar.title() for pillar in result.limiting_pillars)
        weakest = result.scores[result.limiting_pillars[0]]
        lines.extend([
            f"The capability average alone reads as {result.average_stage}. The stage is held at "
            f"{result.maturity} by {limiting} at {weakest}/5, because the organization is not at a "
            "stage its weakest capability contradicts. Challenge that score before accepting the stage.",
            "",
        ])
    if result.context:
        lines.extend([result.context, ""])

    lines.extend(["## Capability Baseline", "", "| Capability | Score | Practice reached |", "|---|---:|---|"])
    lines.extend(
        f"| {pillar.title()} | {result.scores[pillar]}/5 | {RUNGS[result.rung(pillar)].title()} |"
        for pillar in PILLARS
    )

    lines.extend(["", "## Priority Constraints", ""])
    if result.is_uniform:
        lines.append(
            f"- Every capability scores {result.scores[PILLARS[0]]}/5, so no single bottleneck "
            "stands out. The system as a whole is the constraint; sequence the work by "
            "consequence rather than by score."
        )
    else:
        for pillar in result.priorities:
            lines.append(
                f"- **{pillar.title()}** ({result.scores[pillar]}/5): "
                f"{ACTIONS[pillar][result.rung(pillar)]}"
            )

    scheduled: dict[int, list[str]] = {phase: [] for phase in range(len(PHASE_LABELS))}
    for pillar in result.priorities:
        for phase, action in result.ladder(pillar):
            scheduled[phase].append(f"- **{pillar.title()}:** {action}")

    for phase, label in enumerate(PHASE_LABELS):
        lines.extend(["", f"## {label}", ""])
        if scheduled[phase]:
            lines.extend(scheduled[phase])
        else:
            lines.append(
                "- No further practice change is scheduled. Every priority capability has "
                "reached the top rung this model describes; the next gain is evidence that "
                "the practice works, not another practice."
            )

    lines.extend([
        "",
        "## Evidence Review",
        "",
        "At the end of each phase, review cycle time, accepted-change rate, escaped defects, "
        "evaluation pass rate, incidents, cost, and user outcome movement. Do not scale a practice "
        "whose benefit or control evidence remains unclear.",
        "",
    ])
    return "\n".join(lines)
