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

The command validates a 1-5 score for each capability, calculates a maturity stage, identifies the weakest constraints, and writes a phased roadmap.

```text
Organization: Example Digital Service
Maturity: Repeatable (3.0/5.0)
Priority constraints: Evaluation, Governance, Workflow
Roadmap written to roadmap.md
```

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

Scores must be integers from 1 to 5 and all seven capabilities are required. The example is fictional.

## Development

```bash
pip install -e '.[dev]'
pytest
python -m ai_engineering_journey assess examples/org-assessment.json
```

The implementation uses only the Python standard library at runtime.

## Scope

This is an operating-model diagnostic, not a maturity certificate or a substitute for system-specific assurance. Its purpose is to make assumptions explicit, prioritize constraints, and create an inspectable plan.
