# AI Engineering Journey

[![CI](https://github.com/javcamposz/ai-engineering-journey/actions/workflows/ci.yml/badge.svg)](https://github.com/javcamposz/ai-engineering-journey/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A practical, evidence-led way to assess how ready a software organization is for AI-assisted engineering and turn the result into a focused 90-day roadmap.

The central idea is simple: tool access is not transformation. Sustainable gains require changes across product discovery, development workflow, evaluation, architecture, platform, governance, and learning.

## Run The Assessment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
ai-journey assess examples/org-assessment.json --output roadmap.md
```

The command validates a 1-5 score for each capability, calculates a maturity stage, identifies which
capabilities are actually constraining the organization, and writes a phased roadmap.

```text
Organization: Example Digital Service
Maturity: Assisted (3.0/5.0 capability average)
Held below Repeatable by: Evaluation, Governance
Priority constraints: Evaluation, Governance
Roadmap written to roadmap.md
```

## Grade The Journey, Not Just The Snapshot

The tool does not only record where an organization is; it issues a plan. A quarter later the
question is not only what moved, but whether the capabilities the roadmap prioritised are the ones
that moved, and what was given up elsewhere to move them.

```bash
ai-journey progress examples/org-assessment.json examples/org-assessment-q2.json
```

```text
Organization: Example Digital Service (95 days)
Stage: Assisted to Assisted (unchanged)
Priorities delivered: 1 of 2
Stalled: Governance
Regressed while unattended: Workflow
Same bottleneck: no
```

The report leads with **Did The Plan Land?**, and a priority that did not move is quoted back the
action it was given:

> **Governance** was a priority and is unchanged at 2/5. The roadmap asked: Tier use cases by impact
> and assign accountable decision owners. Either the work did not happen or the action was the wrong
> one; both are worth knowing.

It then names what focus cost — a capability that fell while attention was elsewhere — and answers
whether the binding constraint is still the binding constraint. In the example the stage did not move
even though evaluation improved, because workflow slipped into the gap evaluation left:

> No. It was Evaluation, Governance; it is now Workflow, Governance at 2/5. The stage did not move,
> because one constraint replaced another.

Nothing is stored between runs. The earlier roadmap is fully derivable from the earlier profile, so
the comparison reconstructs exactly what was asked for. Add `assessed_on` to a profile and the
interval is measured rather than guessed; profiles passed in the wrong order are refused rather than
silently inverted.

## How Far Can You Actually Run A Real Workflow?

A stage and a roadmap describe capability in the abstract. [The UX bug automation worked
example](docs/ux-bug-automation.md) takes one bounded workflow end to end — telemetry to a shipped
fix that feeds the next eval — and each of its six stages declares the capability level it needs.

```bash
ai-journey readiness examples/org-assessment.json
```

```text
Organization: Example Digital Service
Pipeline: UX bug automation (6 stages)
Reach: 3 of 6, stopping at Verify
Blocked by: Evaluation 2/5, needs 4/5
```

**Reach is what the pipeline can do, not what its best-resourced stage could do.** The stages consume
each other's output, so a blocked stage makes everything after it unreachable however well resourced
those stages are. An organization with strong governance and weak evaluation does not get to ship
autonomously and skip verification; it gets to stop at verification. The report names stages that
would run today if the pipeline reached them, because effort spent on those buys nothing.

This turns "Evaluation is your constraint" into what the constraint costs: that organization can
detect, reproduce and propose fixes, nothing ships without a person reading every change, and the
Learn loop never closes.

It also says what fixing it buys, which is not the same as the stage count it blocks:

> Evaluation at 2/5 blocks 3 of 6 stages, but blocking a stage and opening one are different things.
> Raising it to 4/5 would move reach from 3 to 4 of 6, where Governance 2/5, needs 3/5 stops it.

The two example profiles show the same thing from the other direction. Between them evaluation
improved and workflow regressed, and reach fell from three stages to one:

```text
Reach: 1 of 6, stopping at Reproduce
Blocked by: Workflow 2/5, needs 3/5
```

## How The Stage Is Decided

**The stage is the one the weakest capability demonstrates.** It is not a blend of the average and the
weakest score: each stage in the operating model has exit evidence, and that evidence is per capability.
An organization cannot claim Repeatable, whose exit evidence is stable evals, while evaluation sits at
2/5. The capability average alone would read this example as Repeatable; it is reported as Assisted
because two capabilities sit at 2/5.

This is deliberately blunt. An organization scoring 2 on one capability and 5 on the other six reports the
same stage as one scoring 2 everywhere, because both are blocked in the same place. The two are told very
different things by the roadmap, which is where the difference belongs.

Both numbers are printed, and the roadmap names the capability holding the stage down, so the judgement
is inspectable and can be challenged rather than taken on trust.

A capability is a **constraint** when it scores below the organization's own average or sits at the lowest
score in the profile. Every capability that ties at the cutoff is listed. When all seven scores are equal
there is no bottleneck to rank, and the roadmap says so instead of inventing one.

## Advice Depends On Where A Capability Is

Each capability has three actions, and they are rungs on a ladder rather than a three-month schedule:
establish, standardise, optimise. A capability joins the ladder at the rung its score has reached and
climbs one rung per phase.

| Score | Practice reached | First action |
|---:|---|---|
| 1-2 | Establish | Put the basic practice in place |
| 3 | Standardise | Make it consistent across teams |
| 4-5 | Optimise | Improve it from operational evidence |

A capability at 4/5 is therefore not told to start from the beginning, and a phase with nothing left to
schedule says so rather than repeating advice the organization has already outgrown.

## The Seven Capabilities

| Capability | What good looks like |
|---|---|
| Product | AI work starts from measurable user and service outcomes. |
| Workflow | Small changes, reviewable context, and human accountability are routine. |
| Evaluation | Tests and task-specific evals gate releases. |
| Architecture | Interfaces constrain model behavior and isolate failure. |
| Platform | Approved models, observability, and reusable paved roads reduce friction. |
| Governance | Risk tiering and decision rights match the impact of each use case. |
| Learning | Delivery evidence continuously changes standards and training. |

See [the operating model](docs/operating-model.md) for maturity stages, delivery loops, and adoption principles.

## Input Format

```json
{
  "organization": "Example Digital Service",
  "context": "A product group moving from individual copilots to governed team delivery.",
  "scores": {
    "product": 4,
    "workflow": 3,
    "evaluation": 2,
    "architecture": 3,
    "platform": 4,
    "governance": 2,
    "learning": 3
  }
}
```

An optional `assessed_on` records when the profile was taken, as `YYYY-MM-DD` and only that
shape. Python's own ISO parser widened in 3.11, so `20260115` would be read on 3.12 and
rejected on 3.10; the shape is checked before parsing so both supported versions agree.

Scores must be integers from 1 to 5 and all seven capabilities are required. Every problem in a profile
is reported in one pass with the capability named, so a profile is corrected in a single edit. An invalid
profile exits `2`; a valid one exits `0`. The example is fictional.

## Development

```bash
pip install -e '.[dev]'
pytest
python -m ai_engineering_journey assess examples/org-assessment.json
```

The implementation uses only the Python standard library at runtime.

## Scope

This is an operating-model diagnostic, not a maturity certificate or a substitute for system-specific assurance. Its purpose is to make assumptions explicit, prioritize constraints, and create an inspectable plan.
