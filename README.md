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
