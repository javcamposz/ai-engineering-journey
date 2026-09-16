"""What the scores rest on.

The README says the tool exists to make assumptions explicit, and an assessment was seven
self-reported integers with nothing behind them. The sharpest case is `progress`: a
capability recorded as 2/5 then 4/5, with nothing behind either number, was graded as a
delivered priority. That is a different number, not a demonstrated improvement.
"""

import json
from pathlib import Path

import pytest

from ai_engineering_journey import (
    AssessmentError,
    assess,
    assess_readiness,
    compare,
    render_progress,
    render_readiness,
    render_roadmap,
)
from ai_engineering_journey.assessment import PILLARS
from ai_engineering_journey.cli import main

ROOT = Path(__file__).parents[1]
EXAMPLE = ROOT / "examples/org-assessment.json"
Q2 = ROOT / "examples/org-assessment-q2.json"
SCORES = dict(zip(PILLARS, (4, 3, 2, 3, 4, 2, 3)))


def built(scores=None, evidence=None, on=None):
    return assess("Example", "", scores or SCORES, on, evidence)


# --- the record ---

def test_a_capability_knows_whether_anything_is_behind_its_score():
    result = built(evidence={"evaluation": "evals/task-set-v1.md"})

    assert result.is_evidenced("evaluation")
    assert result.rests_on("evaluation") == "evals/task-set-v1.md"
    assert not result.is_evidenced("workflow")
    assert result.rests_on("workflow") == ""


def test_evidenced_and_unevidenced_partition_the_capabilities():
    result = built(evidence={"evaluation": "a.md", "product": "b.md"})

    assert set(result.evidenced) == {"product", "evaluation"}
    assert set(result.evidenced) | set(result.unevidenced) == set(PILLARS)
    assert not set(result.evidenced) & set(result.unevidenced)


def test_a_profile_without_evidence_still_assesses():
    result = built()

    assert result.evidenced == ()
    assert len(result.unevidenced) == len(PILLARS)
    assert result.maturity == "Assisted"


def test_evidence_for_something_that_is_not_a_capability_is_refused():
    with pytest.raises(AssessmentError, match="evidence names velocity, which is not a capability"):
        built(evidence={"velocity": "a.md"})


def test_a_placeholder_is_not_evidence():
    for placeholder in ("N/A", "TBD", "see above", "  none  "):
        with pytest.raises(AssessmentError, match="name what the score rests on"):
            built(evidence={"evaluation": placeholder})


def test_blank_evidence_is_refused_rather_than_read_as_absent():
    with pytest.raises(AssessmentError, match="omit it rather than leaving it blank"):
        built(evidence={"evaluation": "   "})


# --- the roadmap ---

def test_the_baseline_says_what_each_score_rests_on():
    report = render_roadmap(built(evidence={"evaluation": "evals/task-set-v1.md"}))

    assert "| Evaluation | 2/5 | Establish | evals/task-set-v1.md |" in report
    assert "| Workflow | 3/5 | Standardise | nothing recorded |" in report


def test_the_roadmap_does_not_re_rate_an_unevidenced_score():
    """Re-rating for a reason the reader cannot see would be the wrong correction."""
    bare = built()
    supported = built(evidence={pillar: f"{pillar}.md" for pillar in PILLARS})

    assert bare.scores == supported.scores
    assert bare.maturity == supported.maturity
    assert bare.priorities == supported.priorities
    assert "re-rating a capability for a reason the reader cannot see" in render_roadmap(bare)


def test_the_roadmap_says_when_the_stage_rests_on_nothing():
    report = render_roadmap(built())

    assert "The stage rests on Evaluation, Governance, which records nothing" in report
    assert "follows from a number nobody has had to justify" in report


def test_a_fully_evidenced_profile_makes_no_such_complaint():
    report = render_roadmap(built(evidence={pillar: f"{pillar}.md" for pillar in PILLARS}))

    assert "nothing recorded" not in report
    assert "scores record nothing behind them" not in report


def test_the_bottleneck_being_evidenced_is_asked_separately():
    assert not built(evidence={"product": "a.md"}).bottleneck_is_evidenced
    assert built(evidence={"evaluation": "a.md", "governance": "b.md"}).bottleneck_is_evidenced


# --- the grading ---

def test_a_priority_that_rose_on_evidence_is_demonstrated():
    before = built(on="2026-01-15")
    after = built(dict(SCORES, evaluation=3), {"evaluation": "evals/v1.md"}, "2026-04-20")
    progress = compare(before, after)

    assert [move.pillar for move in progress.demonstrated] == ["evaluation"]
    assert progress.claimed == ()
    assert "on evals/v1.md." in render_progress(progress)


def test_a_priority_that_rose_on_nothing_is_a_claim_not_a_delivery():
    before = built(on="2026-01-15")
    after = built(dict(SCORES, evaluation=3), on="2026-04-20")
    progress = compare(before, after)

    assert [move.pillar for move in progress.claimed] == ["evaluation"]
    assert progress.demonstrated == ()
    report = render_progress(progress)
    assert "with nothing behind the new score" in report
    assert "a different number, not a demonstrated improvement" in report
    assert "it is the movement the plan was graded on" in report


def test_delivered_still_counts_both_so_the_headline_is_unchanged():
    """The count the terminal reports is about the plan, not about the evidence."""
    before = built(on="2026-01-15")
    after = built(dict(SCORES, evaluation=3), on="2026-04-20")
    progress = compare(before, after)

    assert len(progress.delivered) == 1
    assert len(progress.demonstrated) + len(progress.claimed) == len(progress.delivered)


def test_a_rise_nobody_asked_for_and_nobody_supported_is_named():
    before = built(on="2026-01-15")
    after = built(dict(SCORES, learning=4), on="2026-04-20")
    progress = compare(before, after)

    assert [move.pillar for move in progress.unevidenced_gains] == ["learning"]
    report = render_progress(progress)
    assert "**Learning** also rose 3/5 to 4/5 on nothing recorded" in report
    assert "harder to account for than a supported one" in report


def test_a_fall_is_never_an_unevidenced_gain():
    before = built(on="2026-01-15")
    after = built(dict(SCORES, workflow=1), on="2026-04-20")

    assert compare(before, after).unevidenced_gains == ()


def test_the_movement_table_carries_what_each_score_rests_on():
    report = render_progress(compare(
        built(on="2026-01-15"),
        built(dict(SCORES, evaluation=3), {"evaluation": "evals/v1.md"}, "2026-04-20"),
    ))

    assert "| Rests on |" in report or "Rests on" in report
    assert "| evals/v1.md |" in report
    assert "| nothing recorded |" in report


# --- readiness ---

def test_readiness_says_when_a_blocker_rests_on_nothing():
    report = render_readiness(assess_readiness(built()))

    assert "Evaluation, Governance record nothing behind their scores" in report
    assert "Ask for the evidence before spending against them" in report


def test_readiness_makes_no_such_note_when_the_blockers_are_evidenced():
    result = built(evidence={"evaluation": "a.md", "governance": "b.md"})
    report = render_readiness(assess_readiness(result))

    assert "record nothing behind" not in report
    assert "records nothing behind" not in report


# --- the files ---

def test_the_shipped_profiles_carry_evidence():
    payload = json.loads(Q2.read_text())

    assert set(payload["evidence"]) == {"product", "platform", "evaluation"}
    assert "learning" not in payload["evidence"]


def test_the_cli_reports_the_shipped_claim(capsys):
    assert main(["progress", str(EXAMPLE), str(Q2)]) == 0
    capsys.readouterr()
    assert main(["progress", str(EXAMPLE), str(Q2), "--output", "/dev/null"]) == 0


def test_a_non_object_evidence_block_is_refused(tmp_path, capsys):
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({
        "organization": "X", "evidence": ["a.md"],
        "scores": {pillar: 3 for pillar in PILLARS},
    }))

    assert main(["assess", str(path)]) == 2
    assert "evidence must be a JSON object" in capsys.readouterr().err


def test_evidence_problems_are_reported_with_the_others(tmp_path, capsys):
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({
        "organization": "X", "evidence": {"evaluation": "TBD", "velocity": "a.md"},
        "scores": dict({pillar: 3 for pillar in PILLARS}, product=9),
    }))

    assert main(["assess", str(path)]) == 2
    err = capsys.readouterr().err
    assert "product is 9" in err
    assert "evidence for evaluation is 'TBD'" in err
    assert "evidence names velocity" in err
