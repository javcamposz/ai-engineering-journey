# Worked Example: Automating UX Defects End To End

[The operating model](operating-model.md) names five delivery loops and says to start with a bounded
workflow. This is one, worked through: taking a UX defect from telemetry to a shipped fix that makes
the next fix safer.

UX defects are a good first workflow for the reasons the model already argues. They arrive in volume,
so a baseline is cheap to establish. They are bounded, so the unit of work is small enough to review.
And their blast radius varies enormously between a mis-aligned label and a broken checkout step,
which forces the autonomy question to be answered explicitly rather than by default.

This is a reference for the shape of the work. `ai-journey readiness` reports how far down it a given
organization can actually run.

## The Pipeline

### 1. Detect — the Operate loop

Cluster error telemetry, session replays, and support contacts into candidate defects, each carrying a
trace a human can open.

**The gate:** a human confirms it is a defect rather than intended behaviour. A model proposing a
hundred candidates has not found a hundred defects, and counting candidates is the first way this
workflow starts measuring generated volume instead of outcomes.

**What proves it works:** the share of proposed defects a human confirms, and — the number that
matters more — defects users reported that this never proposed.

**Needs:** Platform 2 (telemetry exists and is reachable), Product 2 (a baseline outcome to compare
against).

### 2. Reproduce — the Frame loop

Turn the candidate into a deterministic reproduction and a failing test that names the user-visible
symptom rather than the suspected cause.

**The gate:** the test must fail against unmodified code for the stated reason. A test that fails for
a different reason is describing a different defect, and a fix that turns it green has fixed nothing
anyone reported.

**What proves it works:** reproduction rate, and how often a test failed for the wrong reason. The
second is the one that degrades quietly.

**Needs:** Evaluation 2 (somewhere for the test to live), Workflow 3 (small reviewable changes are
already routine).

### 3. Propose — the Build loop

Draft the smallest change that turns the failing test green, as a pull request carrying the trace, the
test, and the reasoning.

**The gate:** a named human is accountable for the merge, and the diff is small enough that reviewing
it is cheaper than rewriting it. A change nobody can review in less time than it would take to write
is not a saving, whatever the generation time was.

**What proves it works:** accepted-change rate, review time, and reverts within a week. Acceptance
without the revert rate beside it flatters the pipeline.

**Needs:** Architecture 3 (model calls sit behind interfaces that constrain the change), Workflow 3.

### 4. Verify — the Verify loop

Run deterministic tests, visual regression over the affected components, and an eval across the whole
defect class rather than this one defect.

**The gate:** the defect-class eval must not regress. Fixing one instance while the class gets worse
is the specific failure this stage exists to catch, and it is invisible to a test suite that only
knows about the defect in front of it.

**What proves it works:** eval pass rate over time, and escaped defects in a class already fixed.

**Needs:** Evaluation 4. This is the expensive requirement, and it is where most organizations stop.

### 5. Ship — the Operate loop

Merge and release, with autonomy graded by blast radius:

| Blast radius | Example | Autonomy |
|---|---|---|
| Cosmetic and reversible | Spacing, truncation, a mis-aligned label | Merge on green |
| Behavioural, contained | A validation message, a sort order | Merge on green, sampled review |
| User flow, payment, authentication, stored data | Checkout step, login redirect, a migration | A person approves, always |

**The gate:** the risk tier is decided before the work starts. A tier argued about after the change is
written is a tier chosen to justify the change.

**What proves it works:** incidents attributable to changes that merged without review, and time to
roll one back. If rollback is slow, the top row of that table is not actually reversible and the
autonomy it grants is borrowed.

**Needs:** Evaluation 4, Governance 3 (risk tiering and decision owners exist), Architecture 3.

### 6. Learn — the Learn loop

Promote every escaped defect into a permanent eval case, so the class eval that gates the next fix is
built from what reached users rather than from what was easy to write.

**The gate:** the eval set grows from production. An eval suite that only contains defects someone
imagined will keep passing while the same class keeps escaping.

**What proves it works:** repeat-defect rate per class, and eval coverage of classes already shipped.

**Needs:** Learning 3, Evaluation 4.

## Reach, Not Readiness Per Stage

The stages consume each other's output, so a blocked stage makes everything after it unreachable
however well resourced those stages are. An organization with strong governance and weak evaluation
does not get to ship autonomously and skip verification; it gets to stop at verification.

```bash
ai-journey readiness examples/org-assessment.json
```

```text
Reach: 3 of 6, stopping at Verify
Blocked by: Evaluation 2/5, needs 4/5
```

That organization can detect, reproduce and propose. It cannot verify, so nothing ships without a
person reading every change, and the Learn loop never closes. Its roadmap already named Evaluation a
priority constraint; this says what the constraint costs.

## What This Does Not Claim

Nothing here says the pipeline should be run. Reach is a statement about capability, not about
whether automating this workflow is worth it for a given product, and a pipeline that runs end to end
can still be producing changes nobody needed. The evidence columns above are the ones that answer
that, and they are deliberately about accepted work and user outcomes rather than about how much was
generated.
