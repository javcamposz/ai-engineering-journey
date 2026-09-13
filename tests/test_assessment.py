import pytest

from ai_engineering_journey import AssessmentError, assess, render_roadmap
from ai_engineering_journey.assessment import PILLARS

SCORES = {
    "product": 4,
    "workflow": 3,
    "evaluation": 2,
    "architecture": 3,
    "platform": 4,
    "governance": 2,
    "learning": 3,
}


def advice(report: str) -> list[str]:
    return [line for line in report.splitlines() if line.startswith("- **")]


def test_assessment_identifies_constraints_deterministically():
    result = assess("Example", "Context", SCORES)

    assert result.overall == 3.0
    assert result.average_stage == "Repeatable"
    assert result.maturity == "Assisted"
    assert result.priorities == ("evaluation", "governance")


def test_roadmap_contains_each_phase_and_priority():
    report = render_roadmap(assess("Example", "Context", SCORES))

    assert "Days 0-30" in report
    assert "Days 31-90" in report
    assert "Months 4-6" in report
    assert "**Evaluation:**" in report


def test_every_problem_in_a_profile_is_reported_at_once():
    with pytest.raises(AssessmentError) as caught:
        assess("Example", "", dict(SCORES, product=9, workflow=0, extra=1))

    assert [problem.split(";")[0] for problem in caught.value.problems] == [
        "extra is not a capability",
        "product is 9",
        "workflow is 0",
    ]


def test_a_non_integer_score_is_rejected():
    with pytest.raises(AssessmentError, match="must be an integer"):
        assess("Example", "", dict(SCORES, evaluation=5.5))

    with pytest.raises(AssessmentError, match="must be an integer"):
        assess("Example", "", dict(SCORES, evaluation=True))


def test_a_missing_capability_is_named():
    incomplete = {key: value for key, value in SCORES.items() if key != "learning"}

    with pytest.raises(AssessmentError, match="1 capability is missing: learning"):
        assess("Example", "", incomplete)


# --- the stage must not flatter the organization ---

def test_the_stage_is_read_from_the_unrounded_average():
    """Seven scores summing to 18 average 2.571, which is Assisted, not Repeatable."""
    scores = dict.fromkeys(("product", "workflow", "evaluation", "architecture"), 3)
    scores.update(dict.fromkeys(("platform", "governance", "learning"), 2))

    result = assess("Example", "", scores)

    assert result.overall == 2.6
    assert result.average_stage == "Assisted"


def test_a_capability_in_crisis_is_not_averaged_away():
    """Four strong pillars must not buy a stage the weakest three contradict."""
    scores = {"product": 5, "workflow": 1, "evaluation": 1,
              "architecture": 5, "platform": 5, "governance": 1, "learning": 5}

    result = assess("Crisis", "", scores)

    assert result.average_stage == "Repeatable"
    assert result.maturity == "Exploratory"
    assert result.is_limited
    assert result.limiting_pillars == ("workflow", "evaluation", "governance")


def test_a_balanced_organization_is_not_held_back():
    result = assess("Balanced", "", dict.fromkeys(PILLARS, 4))

    assert result.maturity == result.average_stage == "Measured"
    assert not result.is_limited
    assert result.limiting_pillars == ()


def test_the_roadmap_explains_why_the_stage_was_held():
    scores = dict(SCORES)
    report = render_roadmap(assess("Example", "", scores))

    assert "held at Assisted by Evaluation, Governance at 2/5" in report
    assert "Challenge that score before accepting the stage" in report


# --- constraints must be constraints ---

def test_a_strong_capability_is_never_called_a_constraint():
    scores = dict.fromkeys(PILLARS, 5)
    scores["platform"] = 4

    result = assess("Strong", "", scores)

    assert result.priorities == ("platform",)


def test_a_tie_at_the_cutoff_is_not_truncated():
    scores = {"product": 1, "workflow": 1, "evaluation": 1, "architecture": 1,
              "platform": 5, "governance": 5, "learning": 5}

    result = assess("Tied", "", scores)

    assert result.priorities == ("product", "workflow", "evaluation", "architecture")


def test_a_uniform_profile_reports_no_single_bottleneck():
    result = assess("Floor", "", dict.fromkeys(PILLARS, 1))
    report = render_roadmap(result)

    assert result.is_uniform
    assert "no single bottleneck" in report
    assert "The system as a whole is the constraint" in report


# --- advice must depend on where the capability is ---

def test_two_organizations_with_the_same_weak_pillars_get_different_advice():
    """The same three weakest pillars at 1/5 and at 4/5 used to produce identical roadmaps."""
    crisis = {"product": 5, "workflow": 1, "evaluation": 1,
              "architecture": 5, "platform": 5, "governance": 1, "learning": 5}
    nearly = dict(crisis, workflow=4, evaluation=4, governance=4)

    crisis_advice = advice(render_roadmap(assess("Crisis", "", crisis)))
    nearly_advice = advice(render_roadmap(assess("Nearly", "", nearly)))

    assert crisis_advice != nearly_advice
    assert len(crisis_advice) > len(nearly_advice)


def test_a_capability_at_the_floor_climbs_every_rung():
    scores = dict.fromkeys(PILLARS, 5)
    scores["evaluation"] = 1
    result = assess("One Gap", "", scores)

    assert [action for _, action in result.ladder("evaluation")] == [
        "Create a representative task set and record the non-AI baseline.",
        "Gate releases with deterministic tests and task-specific evals.",
        "Monitor drift and refresh evals from production failures.",
    ]


def test_a_capability_near_the_top_is_not_told_to_start_over():
    scores = dict.fromkeys(PILLARS, 5)
    scores["evaluation"] = 4
    result = assess("Nearly", "", scores)

    assert [action for _, action in result.ladder("evaluation")] == [
        "Monitor drift and refresh evals from production failures.",
    ]


def test_a_phase_with_nothing_scheduled_says_so_rather_than_repeating():
    scores = dict.fromkeys(PILLARS, 5)
    scores["evaluation"] = 4
    report = render_roadmap(assess("Nearly", "", scores))

    assert "No further practice change is scheduled" in report
    assert report.count("Monitor drift") == 2  # the constraint line and one phase


def test_the_baseline_table_names_the_practice_each_score_has_reached():
    report = render_roadmap(assess("Example", "", SCORES))

    assert "| Evaluation | 2/5 | Establish |" in report
    assert "| Product | 4/5 | Optimise |" in report
    assert "| Workflow | 3/5 | Standardise |" in report


def test_the_stage_is_what_the_weakest_capability_demonstrates():
    """Not a blend: a weakest score of w forces the mean above w, so the average never wins."""
    from itertools import product

    from ai_engineering_journey.assessment import PILLAR_STAGE

    for combo in product((1, 3, 5), repeat=len(PILLARS)):
        result = assess("X", "", dict(zip(PILLARS, combo)))
        assert result.maturity == PILLAR_STAGE[min(combo)], combo


def test_a_strong_average_does_not_buy_a_stage_the_weakest_capability_has_not_reached():
    lopsided = assess("Lopsided", "", dict(zip(PILLARS, (2, 5, 5, 5, 5, 5, 5))))
    flat = assess("Flat", "", dict.fromkeys(PILLARS, 2))

    assert lopsided.overall == 4.6
    assert flat.overall == 2.0
    assert lopsided.maturity == flat.maturity == "Assisted"

    # The stage is deliberately blunt; the roadmaps are where the two differ.
    assert lopsided.priorities != flat.priorities
    assert advice(render_roadmap(lopsided)) != advice(render_roadmap(flat))
