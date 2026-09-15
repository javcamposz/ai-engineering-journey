"""A worked AI-driven workflow, and how far an organization can actually run it.

The operating model names five loops and says to start with a bounded workflow. It never
showed one. This is that workflow: automating UX defects, end to end, from telemetry to a
shipped fix that feeds the next eval.

Each stage declares the capability level it needs, so an assessment answers a sharper
question than "what is our stage". It answers how far down a real pipeline the
organization can run today, and what stops it.
"""

from __future__ import annotations

from dataclasses import dataclass

from .assessment import PILLARS, Assessment


@dataclass(frozen=True)
class Requirement:
    pillar: str
    minimum: int

    def met_by(self, scores: dict[str, int]) -> bool:
        return scores[self.pillar] >= self.minimum


@dataclass(frozen=True)
class Stage:
    name: str
    loop: str
    runs: str
    gate: str
    evidence: str
    requires: tuple[Requirement, ...]


# Ordered. Each stage consumes what the one before it produced, which is why a blocked
# stage makes everything after it unreachable however well resourced those are.
UX_BUG_PIPELINE: tuple[Stage, ...] = (
    Stage(
        name="Detect",
        loop="Operate",
        runs="Cluster error telemetry, session replays, and support contacts into candidate "
             "defects, each with a trace a human can open.",
        gate="A human confirms it is a defect rather than intended behaviour. Volume of "
             "candidates is not evidence of anything.",
        evidence="Share of proposed defects a human confirms, and defects users reported "
                 "that this never proposed.",
        requires=(Requirement("platform", 2), Requirement("product", 2)),
    ),
    Stage(
        name="Reproduce",
        loop="Frame",
        runs="Turn the candidate into a deterministic reproduction and a failing test that "
             "names the user-visible symptom.",
        gate="The test must fail against unmodified code for the stated reason. A test that "
             "fails for any other reason is a different defect.",
        evidence="Reproduction rate, and how often a test failed for the wrong reason.",
        requires=(Requirement("evaluation", 2), Requirement("workflow", 3)),
    ),
    Stage(
        name="Propose",
        loop="Build",
        runs="Draft the smallest change that turns the failing test green, as a pull request "
             "carrying the trace, the test, and the reasoning.",
        gate="A named human is accountable for the merge, and the diff is small enough that "
             "reviewing it is cheaper than rewriting it.",
        evidence="Accepted-change rate, review time, and reverts within a week.",
        requires=(Requirement("architecture", 3), Requirement("workflow", 3)),
    ),
    Stage(
        name="Verify",
        loop="Verify",
        runs="Run deterministic tests, visual regression over affected components, and an "
             "eval across the whole defect class rather than this one defect.",
        gate="The defect-class eval must not regress. Fixing one instance while the class "
             "gets worse is the failure this stage exists to catch.",
        evidence="Eval pass rate over time, and escaped defects in a class already fixed.",
        requires=(Requirement("evaluation", 4),),
    ),
    Stage(
        name="Ship",
        loop="Operate",
        runs="Merge and release, with autonomy graded by blast radius: cosmetic and "
             "reversible changes merge on green, anything touching a user flow, payment, "
             "authentication, or stored data waits for a person.",
        gate="The risk tier is decided before the work starts, not argued about after the "
             "change is written.",
        evidence="Incidents attributable to changes that merged without review, and time to "
                 "roll one back.",
        requires=(
            Requirement("evaluation", 4),
            Requirement("governance", 3),
            Requirement("architecture", 3),
        ),
    ),
    Stage(
        name="Learn",
        loop="Learn",
        runs="Promote every escaped defect into a permanent eval case, so the class eval "
             "that gates the next fix is built from production rather than from imagination.",
        gate="The eval set grows from what reached users, not from what was easy to write.",
        evidence="Repeat-defect rate per class, and eval coverage of classes already shipped.",
        requires=(Requirement("learning", 3), Requirement("evaluation", 4)),
    ),
)


@dataclass(frozen=True)
class StageReadiness:
    stage: Stage
    scores: dict[str, int]

    @property
    def shortfalls(self) -> tuple[tuple[Requirement, int], ...]:
        return tuple(
            (requirement, self.scores[requirement.pillar])
            for requirement in self.stage.requires
            if not requirement.met_by(self.scores)
        )

    @property
    def is_resourced(self) -> bool:
        """Whether this stage's own requirements are met, ignoring the ones before it."""
        return not self.shortfalls

    def describe_shortfalls(self) -> str:
        return "; ".join(
            f"{requirement.pillar.title()} {actual}/5, needs {requirement.minimum}/5"
            for requirement, actual in self.shortfalls
        )


@dataclass(frozen=True)
class Readiness:
    assessment: Assessment
    stages: tuple[StageReadiness, ...]

    @property
    def reach(self) -> int:
        """How many stages run before the first one that cannot.

        The pipeline is sequential, so this is the honest number. A later stage whose own
        requirements are met is still unreachable if an earlier one is blocked.
        """
        for index, stage in enumerate(self.stages):
            if not stage.is_resourced:
                return index
        return len(self.stages)

    @property
    def runs(self) -> tuple[StageReadiness, ...]:
        return self.stages[:self.reach]

    @property
    def stops_at(self) -> StageReadiness | None:
        return self.stages[self.reach] if self.reach < len(self.stages) else None

    @property
    def unreachable(self) -> tuple[StageReadiness, ...]:
        """Stages after the blockage, whatever their own requirements say."""
        return self.stages[self.reach + 1:] if self.stops_at else ()

    @property
    def resourced_but_unreachable(self) -> tuple[StageReadiness, ...]:
        return tuple(stage for stage in self.unreachable if stage.is_resourced)

    @property
    def blocking_pillars(self) -> tuple[tuple[str, int], ...]:
        """Capabilities that block stages, and how many each blocks, worst first."""
        counts: dict[str, int] = {}
        for stage in self.stages:
            for requirement, _ in stage.shortfalls:
                counts[requirement.pillar] = counts.get(requirement.pillar, 0) + 1
        return tuple(sorted(counts.items(), key=lambda item: (-item[1], PILLARS.index(item[0]))))


def assess_readiness(
    assessment: Assessment, pipeline: tuple[Stage, ...] = UX_BUG_PIPELINE
) -> Readiness:
    return Readiness(
        assessment=assessment,
        stages=tuple(StageReadiness(stage, assessment.scores) for stage in pipeline),
    )


def render_readiness(readiness: Readiness, pipeline_name: str = "UX bug automation") -> str:
    result = readiness.assessment
    total = len(readiness.stages)
    lines = [
        f"# {pipeline_name} readiness: {result.organization}",
        "",
        f"**Maturity:** {result.maturity} ({result.overall:.1f}/5.0 capability average)",
        "",
        f"**Reach:** {readiness.reach} of {total} stages"
        + (f", stopping at {readiness.stops_at.stage.name}" if readiness.stops_at else ", the whole pipeline"),
        "",
    ]
    if result.context:
        lines.extend([result.context, ""])

    lines.extend(["## What Runs Today", ""])
    if readiness.runs:
        lines.append("| Stage | Loop | What runs |")
        lines.append("|---|---|---|")
        for ready in readiness.runs:
            lines.append(f"| {ready.stage.name} | {ready.stage.loop} | {ready.stage.runs} |")
    else:
        lines.append(
            f"- Nothing. The first stage, {readiness.stages[0].stage.name}, is already blocked by "
            f"{readiness.stages[0].describe_shortfalls()}."
        )

    lines.extend(["", "## Where It Stops", ""])
    if readiness.stops_at is None:
        lines.append(
            "- Nowhere. Every stage is resourced, so the question moves from whether the "
            "pipeline can run to whether its evidence says it should."
        )
    else:
        blocked = readiness.stops_at
        lines.extend([
            f"**{blocked.stage.name}**, in the {blocked.stage.loop} loop, is blocked by "
            f"{blocked.describe_shortfalls()}.",
            "",
            f"- What it would run: {blocked.stage.runs}",
            f"- The gate it enforces: {blocked.stage.gate}",
            f"- What proves it works: {blocked.stage.evidence}",
        ])

    if readiness.unreachable:
        lines.extend(["", "## Unreachable Until Then", ""])
        for ready in readiness.unreachable:
            note = (
                "its own requirements are met, so nothing but the blockage above stops it"
                if ready.is_resourced
                else f"also short of {ready.describe_shortfalls()}"
            )
            lines.append(f"- **{ready.stage.name}**: {note}.")
        if readiness.resourced_but_unreachable:
            names = ", ".join(s.stage.name for s in readiness.resourced_but_unreachable)
            lines.extend([
                "",
                f"{names} would run today if the pipeline reached them. Raising the capability "
                "that blocks the stage above is worth more than anything spent on these.",
            ])

    lines.extend(["", "## What Blocks The Pipeline", ""])
    if readiness.blocking_pillars:
        lines.append("| Capability | Score | Stages blocked |")
        lines.append("|---|---:|---:|")
        for pillar, count in readiness.blocking_pillars:
            lines.append(f"| {pillar.title()} | {result.scores[pillar]}/5 | {count} |")
        worst, count = readiness.blocking_pillars[0]
        lines.extend([
            "",
            f"{worst.title()} at {result.scores[worst]}/5 blocks {count} of {total} stages. "
            "Run `ai-journey assess` on the same profile for the actions that raise it.",
        ])
    else:
        lines.append("- No capability blocks a stage.")

    lines.extend(["", "## The Pipeline In Full", "", "| Stage | Loop | Requires | Status |", "|---|---|---|---|"])
    for index, ready in enumerate(readiness.stages):
        requires = ", ".join(
            f"{requirement.pillar.title()} {requirement.minimum}" for requirement in ready.stage.requires
        )
        if index < readiness.reach:
            status = "Runs"
        elif readiness.stops_at is not None and index == readiness.reach:
            status = "Blocked"
        else:
            status = "Unreachable" if ready.is_resourced else "Unreachable and unresourced"
        lines.append(f"| {ready.stage.name} | {ready.stage.loop} | {requires} | {status} |")

    lines.extend([
        "",
        "Reach is what the pipeline can do, not what its best-resourced stage could do. "
        "A stage after the blockage does not run however well it is staffed.",
        "",
    ])
    return "\n".join(lines)
