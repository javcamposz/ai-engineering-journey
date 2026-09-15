"""How far down a real workflow an organization can run.

The operating model named five loops and never showed one worked through. docs/ux-bug-
automation.md is that workflow; this is the part that reads an assessment against it.
"""

from pathlib import Path

import pytest

from ai_engineering_journey import (
    UX_BUG_PIPELINE,
    Requirement,
    Stage,
    assess,
    assess_readiness,
    render_readiness,
)
from ai_engineering_journey.assessment import PILLARS
from ai_engineering_journey.cli import main

ROOT = Path(__file__).parents[1]
EXAMPLE = ROOT / "examples/org-assessment.json"
Q2 = ROOT / "examples/org-assessment-q2.json"
SCORES = dict(zip(PILLARS, (4, 3, 2, 3, 4, 2, 3)))


def readiness(scores=None):
    return assess_readiness(assess("Example", "", scores or SCORES))


def stage_named(readiness_result, name):
    return next(item for item in readiness_result.stages if item.stage.name == name)


# --- the pipeline itself ---

def test_every_stage_requires_capabilities_the_assessment_scores():
    for stage in UX_BUG_PIPELINE:
        assert stage.requires, stage.name
        for requirement in stage.requires:
            assert requirement.pillar in PILLARS, (stage.name, requirement.pillar)
            assert 1 <= requirement.minimum <= 5, (stage.name, requirement.minimum)


def test_every_stage_names_a_loop_from_the_operating_model():
    loops = {"Frame", "Build", "Verify", "Operate", "Learn"}

    assert {stage.loop for stage in UX_BUG_PIPELINE} <= loops
    assert loops <= {stage.loop for stage in UX_BUG_PIPELINE}


def test_every_stage_states_a_gate_and_the_evidence_for_it():
    for stage in UX_BUG_PIPELINE:
        assert stage.gate.strip() and stage.runs.strip() and stage.evidence.strip(), stage.name


def test_the_documented_pipeline_matches_the_one_the_tool_reads():
    doc = (ROOT / "docs/ux-bug-automation.md").read_text()

    for index, stage in enumerate(UX_BUG_PIPELINE, start=1):
        assert f"### {index}. {stage.name} — the {stage.loop} loop" in doc, stage.name


# --- reach ---

def test_reach_stops_at_the_first_stage_that_cannot_run():
    result = readiness()

    assert result.reach == 3
    assert [item.stage.name for item in result.runs] == ["Detect", "Reproduce", "Propose"]
    assert result.stops_at.stage.name == "Verify"


def test_a_stage_after_the_blockage_is_unreachable_however_resourced():
    """Reach is what the pipeline can do, not what its best-resourced stage could do."""
    scores = dict(SCORES, governance=5, learning=5)
    result = readiness(scores)

    learn = stage_named(result, "Learn")
    assert learn.scores["learning"] == 5
    assert not learn.is_resourced  # still short on evaluation
    assert learn in result.unreachable
    assert result.reach == 3


def test_a_resourced_stage_behind_a_blockage_is_named_as_such():
    scores = dict(SCORES, architecture=5, governance=5)
    result = readiness(scores)

    ship = stage_named(result, "Ship")
    assert ship.is_resourced is False  # evaluation still short
    scores = dict(scores, evaluation=4, workflow=1)
    result = readiness(scores)

    assert result.stops_at.stage.name == "Reproduce"
    assert [item.stage.name for item in result.resourced_but_unreachable] == ["Verify", "Ship", "Learn"]


def test_a_fully_resourced_organization_reaches_every_stage():
    result = readiness(dict.fromkeys(PILLARS, 5))

    assert result.reach == len(UX_BUG_PIPELINE)
    assert result.stops_at is None
    assert result.unreachable == ()


def test_an_organization_blocked_at_the_first_stage_reaches_nothing():
    result = readiness(dict.fromkeys(PILLARS, 1))

    assert result.reach == 0
    assert result.runs == ()
    assert result.stops_at.stage.name == "Detect"


def test_blocking_capabilities_are_counted_worst_first():
    result = readiness()

    assert result.blocking_pillars == (("evaluation", 3), ("governance", 1))


# --- the report ---

def test_the_report_leads_with_reach_and_what_stops_it():
    report = render_readiness(readiness())

    assert "**Reach:** 3 of 6 stages, stopping at Verify" in report
    assert "**Verify**, in the Verify loop, is blocked by Evaluation 2/5, needs 4/5." in report
    assert "Evaluation at 2/5 blocks 3 of 6 stages." in report


def test_the_report_names_stages_that_would_run_if_reached():
    report = render_readiness(readiness(dict(SCORES, evaluation=4, workflow=1)))

    assert "would run today if the pipeline reached them" in report
    assert "Raising the capability that blocks the stage above is worth more" in report


def test_a_complete_pipeline_says_the_question_has_changed():
    report = render_readiness(readiness(dict.fromkeys(PILLARS, 5)))

    assert "Nowhere. Every stage is resourced" in report
    assert "whether its evidence says it should" in report


def test_the_full_table_marks_every_stage():
    report = render_readiness(readiness())
    table = report.split("## The Pipeline In Full", 1)[1]

    assert "| Detect | Operate | Platform 2, Product 2 | Runs |" in table
    assert "| Verify | Verify | Evaluation 4 | Blocked |" in table
    assert "Unreachable" in table


def test_the_heading_does_not_mangle_the_pipeline_name():
    assert "# UX bug automation readiness:" in render_readiness(readiness())


# --- the CLI ---

def test_readiness_reports_reach_and_the_blocker(tmp_path, capsys):
    output = tmp_path / "readiness.md"

    assert main(["readiness", str(EXAMPLE), "--output", str(output)]) == 0

    out = capsys.readouterr().out
    assert "Pipeline: UX bug automation (6 stages)" in out
    assert "Reach: 3 of 6, stopping at Verify" in out
    assert "Blocked by: Evaluation 2/5, needs 4/5" in out
    assert output.read_text().startswith("# UX bug automation readiness:")


def test_a_regression_elsewhere_shortens_the_reach(capsys):
    """Q2 improved evaluation and lost workflow; the pipeline stops three stages earlier."""
    assert main(["readiness", str(EXAMPLE)]) == 0
    first = capsys.readouterr().out
    assert main(["readiness", str(Q2)]) == 0
    second = capsys.readouterr().out

    assert "Reach: 3 of 6, stopping at Verify" in first
    assert "Reach: 1 of 6, stopping at Reproduce" in second
    assert "Blocked by: Workflow 2/5, needs 3/5" in second


def test_an_invalid_profile_is_reported_cleanly(tmp_path, capsys):
    path = tmp_path / "profile.json"
    path.write_text('{"organization": "X", "scores": {"product": 9}}')

    assert main(["readiness", str(path)]) == 2
    assert "error: " in capsys.readouterr().err


def test_a_custom_pipeline_can_be_assessed():
    tiny = (
        Stage("Only", "Build", "runs", "gate", "evidence", (Requirement("workflow", 5),)),
    )
    result = assess_readiness(assess("X", "", SCORES), tiny)

    assert result.reach == 0
    assert result.stops_at.describe_shortfalls() == "Workflow 3/5, needs 5/5"


def test_requirements_compare_against_the_assessed_scores():
    assert Requirement("workflow", 3).met_by(SCORES)
    assert not Requirement("evaluation", 3).met_by(SCORES)
