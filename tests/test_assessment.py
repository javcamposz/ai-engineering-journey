import pytest

from ai_engineering_journey import assess, render_roadmap


SCORES = {
    "product": 4,
    "workflow": 3,
    "evaluation": 2,
    "architecture": 3,
    "platform": 4,
    "governance": 2,
    "learning": 3,
}


def test_assessment_identifies_constraints_deterministically():
    result = assess("Example", "Context", SCORES)

    assert result.overall == 3.0
    assert result.maturity == "Repeatable"
    assert result.priorities == ("evaluation", "governance", "workflow")


def test_roadmap_contains_each_phase_and_priority():
    report = render_roadmap(assess("Example", "Context", SCORES))

    assert "Days 0-30" in report
    assert "Days 31-90" in report
    assert "Months 4-6" in report
    assert "**Evaluation:**" in report


def test_scores_require_complete_integer_range():
    with pytest.raises(ValueError, match="exactly"):
        assess("Example", "", {"product": 3})

    invalid = dict(SCORES, evaluation=5.5)
    with pytest.raises(ValueError, match="integer"):
        assess("Example", "", invalid)
