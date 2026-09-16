"""Grade a second assessment against what the first one asked for.

A snapshot says where an organization is. This repository is named for the journey, and
the tool does not only record state: it issues a plan. So the question a re-assessment
should answer is not only what moved, but whether the capabilities the previous roadmap
prioritised are the ones that moved, and what was given up elsewhere to move them.

Nothing is stored between runs. The earlier roadmap is fully derivable from the earlier
profile, so the comparison reconstructs exactly what was asked for.
"""

from __future__ import annotations

from dataclasses import dataclass

from .assessment import ACTIONS, PILLARS, RUNGS, Assessment, AssessmentError


@dataclass(frozen=True)
class CapabilityMovement:
    pillar: str
    before: int
    after: int
    before_rung: int
    after_rung: int
    was_prioritised: bool
    evidenced_before: bool = False
    evidenced_after: bool = False
    rests_on: str = ""

    @property
    def is_unevidenced_gain(self) -> bool:
        """Improved, with nothing recorded behind the number it improved to.

        A score that went up with nothing behind it is a different number, not a
        demonstrated improvement, and the grading above would otherwise call it delivered.
        """
        return self.delta > 0 and not self.evidenced_after

    @property
    def delta(self) -> int:
        return self.after - self.before

    @property
    def direction(self) -> str:
        if self.delta > 0:
            return "improved"
        if self.delta < 0:
            return "regressed"
        return "unchanged"

    @property
    def rung_advanced(self) -> bool:
        return self.after_rung > self.before_rung

    @property
    def practice(self) -> str:
        if self.rung_advanced:
            return f"{RUNGS[self.before_rung]} to {RUNGS[self.after_rung]}"
        if self.after_rung < self.before_rung:
            return f"{RUNGS[self.before_rung]} back to {RUNGS[self.after_rung]}"
        return RUNGS[self.after_rung]


@dataclass(frozen=True)
class Progress:
    before: Assessment
    after: Assessment
    movements: tuple[CapabilityMovement, ...]

    @property
    def days(self) -> int | None:
        if self.before.assessed_on is None or self.after.assessed_on is None:
            return None
        return (self.after.assessed_on - self.before.assessed_on).days

    def _where(self, **criteria: object) -> tuple[CapabilityMovement, ...]:
        return tuple(
            movement for movement in self.movements
            if all(getattr(movement, key) == value for key, value in criteria.items())
        )

    @property
    def delivered(self) -> tuple[CapabilityMovement, ...]:
        """Capabilities the earlier roadmap prioritised, that moved."""
        return self._where(was_prioritised=True, direction="improved")

    @property
    def demonstrated(self) -> tuple[CapabilityMovement, ...]:
        """Priorities that moved and recorded something behind the new score."""
        return tuple(move for move in self.delivered if move.evidenced_after)

    @property
    def claimed(self) -> tuple[CapabilityMovement, ...]:
        """Priorities that moved and recorded nothing behind the new score."""
        return tuple(move for move in self.delivered if not move.evidenced_after)

    @property
    def unevidenced_gains(self) -> tuple[CapabilityMovement, ...]:
        """Every capability that rose on nothing, prioritised or not."""
        return tuple(move for move in self.movements if move.is_unevidenced_gain)

    @property
    def stalled(self) -> tuple[CapabilityMovement, ...]:
        """Capabilities the earlier roadmap prioritised, that did not."""
        return tuple(
            movement for movement in self.movements
            if movement.was_prioritised and movement.direction != "improved"
        )

    @property
    def regressed(self) -> tuple[CapabilityMovement, ...]:
        return self._where(direction="regressed")

    @property
    def collateral(self) -> tuple[CapabilityMovement, ...]:
        """Capabilities that fell while attention was somewhere else."""
        return self._where(direction="regressed", was_prioritised=False)

    @property
    def stage_changed(self) -> bool:
        return self.before.maturity != self.after.maturity

    @property
    def same_bottleneck(self) -> bool:
        return set(self.before.bottleneck) == set(self.after.bottleneck)

    @property
    def renamed(self) -> bool:
        return self.before.organization != self.after.organization


def compare(before: Assessment, after: Assessment) -> Progress:
    """Compare two assessments of the same organization, earlier first."""
    if (
        before.assessed_on is not None
        and after.assessed_on is not None
        and after.assessed_on < before.assessed_on
    ):
        raise AssessmentError([
            f"the later profile is dated {after.assessed_on.isoformat()}, before the earlier one "
            f"at {before.assessed_on.isoformat()}; pass the earlier assessment first"
        ])

    movements = tuple(
        CapabilityMovement(
            pillar=pillar,
            before=before.scores[pillar],
            after=after.scores[pillar],
            before_rung=before.rung(pillar),
            after_rung=after.rung(pillar),
            was_prioritised=pillar in before.priorities,
            evidenced_before=before.is_evidenced(pillar),
            evidenced_after=after.is_evidenced(pillar),
            rests_on=after.rests_on(pillar),
        )
        for pillar in PILLARS
    )
    return Progress(before=before, after=after, movements=movements)


def render_progress(progress: Progress) -> str:
    before, after = progress.before, progress.after
    lines = [f"# AI Engineering Progress: {after.organization}", ""]

    if progress.days is None:
        lines.append(
            "**Interval:** not recorded. Add `assessed_on` to both profiles so the rate of "
            "change can be read, not just its direction."
        )
    else:
        lines.append(
            f"**Interval:** {progress.days} days, "
            f"{before.assessed_on.isoformat()} to {after.assessed_on.isoformat()}"
        )
    lines.extend([
        "",
        f"**Stage:** {before.maturity} to {after.maturity}"
        + ("" if progress.stage_changed else " (unchanged)"),
        "",
    ])
    if progress.renamed:
        lines.extend([
            f"The two profiles name different organizations, {before.organization} then "
            f"{after.organization}. Confirm this is the same organization before reading further.",
            "",
        ])

    # Every assessment names at least the capabilities at its lowest score, so there is
    # always something the earlier roadmap asked for.
    assert before.priorities, "an assessment always names at least one constraint"

    lines.extend(["## Did The Plan Land?", ""])
    for movement in progress.demonstrated:
        lines.append(
            f"- **{movement.pillar.title()}** moved {movement.before}/5 to {movement.after}/5"
            + (f", {movement.practice}" if movement.rung_advanced else ", same practice rung")
            + f", on {movement.rests_on}."
        )
    for movement in progress.claimed:
        lines.append(
            f"- **{movement.pillar.title()}** is recorded as {movement.before}/5 to "
            f"{movement.after}/5 with nothing behind the new score. That is a different "
            "number, not a demonstrated improvement, and it is the movement the plan was "
            "graded on."
        )
    for movement in progress.stalled:
        asked = ACTIONS[movement.pillar][movement.before_rung]
        if movement.direction == "regressed":
            lines.append(
                f"- **{movement.pillar.title()}** was a priority and fell "
                f"{movement.before}/5 to {movement.after}/5. The roadmap asked: {asked}"
            )
        else:
            lines.append(
                f"- **{movement.pillar.title()}** was a priority and is unchanged at "
                f"{movement.before}/5. The roadmap asked: {asked} Either the work did not "
                "happen or the action was the wrong one; both are worth knowing."
            )

    unasked = tuple(
        movement for movement in progress.unevidenced_gains if not movement.was_prioritised
    )
    for movement in unasked:
        lines.append(
            f"- **{movement.pillar.title()}** also rose {movement.before}/5 to "
            f"{movement.after}/5 on nothing recorded. Nothing was asked of it, which makes an "
            "unsupported rise harder to account for than a supported one."
        )

    lines.extend(["", "## What It Cost", ""])
    if progress.collateral:
        for movement in progress.collateral:
            lines.append(
                f"- **{movement.pillar.title()}** fell {movement.before}/5 to {movement.after}/5 "
                "while attention was elsewhere. It was not a priority, which is why this is the "
                "price of focus rather than a surprise."
            )
    elif progress.regressed:
        lines.append("- Nothing outside the priorities regressed.")
    else:
        lines.append("- No capability regressed.")

    lines.extend(["", "## Is It The Same Bottleneck?", ""])
    bottleneck = ", ".join(pillar.title() for pillar in after.bottleneck)
    lowest = after.scores[after.bottleneck[0]]
    if progress.same_bottleneck:
        lines.append(
            f"- Yes. {bottleneck} still sets the stage at {lowest}/5. A cycle that leaves the "
            "binding constraint where it was has not bought a stage, whatever else improved."
        )
    else:
        previous = ", ".join(pillar.title() for pillar in before.bottleneck)
        lines.append(
            f"- No. It was {previous}; it is now {bottleneck} at {lowest}/5."
            + ("" if progress.stage_changed else
               " The stage did not move, because one constraint replaced another.")
        )

    lines.extend([
        "",
        "## Movement",
        "",
        "| Capability | Before | After | Change | Practice | Rests on | Was a priority |",
        "|---|---:|---:|---:|---|---|---|",
    ])
    for movement in sorted(progress.movements, key=lambda item: (item.delta, PILLARS.index(item.pillar))):
        change = f"{movement.delta:+d}" if movement.delta else "0"
        lines.append(
            f"| {movement.pillar.title()} | {movement.before}/5 | {movement.after}/5 | "
            f"{change} | {movement.practice} | "
            f"{movement.rests_on or 'nothing recorded'} | "
            f"{'yes' if movement.was_prioritised else 'no'} |"
        )

    lines.extend([
        "",
        "## Next",
        "",
        "Run `ai-journey assess` on the later profile for the roadmap this position now implies. "
        "Treat an unchanged priority as evidence about the plan, not only about the organization.",
        "",
    ])
    return "\n".join(lines)
