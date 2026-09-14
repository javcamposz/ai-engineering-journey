"""A second assessment is graded against what the first one asked for.

The tool does not only record state, it issues a plan. So the question is not only what
moved, but whether the capabilities the previous roadmap prioritised are the ones that
moved, and what was given up elsewhere to move them.
"""

import pytest

from ai_engineering_journey import AssessmentError, assess, compare, render_progress
from ai_engineering_journey.assessment import PILLARS

BEFORE = dict(zip(PILLARS, (4, 3, 2, 3, 4, 2, 3)))
AFTER = dict(BEFORE, evaluation=3, workflow=2)


def built(scores, on=None, name="Example"):
    return assess(name, "", scores, on)


def progress(before=None, after=None, before_on="2026-01-15", after_on="2026-04-20"):
    return compare(
        built(before or BEFORE, before_on),
        built(after or AFTER, after_on),
    )


def test_the_interval_is_measured_when_both_profiles_are_dated():
    assert progress().days == 95


def test_an_undated_profile_leaves_the_interval_unknown_rather_than_guessed():
    result = progress(before_on=None, after_on=None)

    assert result.days is None
    assert "Interval:** not recorded" in render_progress(result)


def test_profiles_passed_in_the_wrong_order_are_refused():
    with pytest.raises(AssessmentError, match="pass the earlier assessment first"):
        compare(built(BEFORE, "2026-04-20"), built(AFTER, "2026-01-15"))


def test_two_profiles_on_the_same_day_are_allowed():
    assert compare(built(BEFORE, "2026-01-15"), built(AFTER, "2026-01-15")).days == 0


# --- did the plan land? ---

def test_a_priority_that_moved_is_reported_as_delivered():
    result = progress()

    assert [m.pillar for m in result.delivered] == ["evaluation"]
    assert result.delivered[0].rung_advanced
    assert result.delivered[0].practice == "establish to standardise"


def test_a_priority_that_did_not_move_is_named_with_what_was_asked():
    result = progress()
    report = render_progress(result)

    assert [m.pillar for m in result.stalled] == ["governance"]
    assert "**Governance** was a priority and is unchanged at 2/5" in report
    assert "Tier use cases by impact and assign accountable decision owners." in report
    assert "Either the work did not happen or the action was the wrong one" in report


def test_a_priority_that_went_backwards_counts_as_stalled_not_delivered():
    result = progress(after=dict(BEFORE, evaluation=1))

    assert [m.pillar for m in result.delivered] == []
    assert {m.pillar for m in result.stalled} == {"evaluation", "governance"}
    assert "was a priority and fell 2/5 to 1/5" in render_progress(result)


def test_only_capabilities_the_earlier_roadmap_prioritised_are_graded():
    result = progress()
    graded = {m.pillar for m in result.delivered} | {m.pillar for m in result.stalled}

    assert graded == set(result.before.priorities) == {"evaluation", "governance"}


# --- what it cost ---

def test_a_capability_that_fell_while_unattended_is_named_as_the_price_of_focus():
    result = progress()

    assert [m.pillar for m in result.collateral] == ["workflow"]
    assert "**Workflow** fell 3/5 to 2/5 while attention was elsewhere" in render_progress(result)


def test_no_regression_is_stated_rather_than_left_blank():
    result = progress(after=dict(BEFORE, evaluation=3))

    assert result.regressed == ()
    assert "- No capability regressed." in render_progress(result)


def test_a_regression_inside_the_priorities_is_not_called_collateral():
    result = progress(after=dict(BEFORE, evaluation=1))

    assert result.regressed and result.collateral == ()
    assert "Nothing outside the priorities regressed." in render_progress(result)


# --- the bottleneck ---

def test_a_replaced_bottleneck_explains_why_the_stage_did_not_move():
    result = progress()
    report = render_progress(result)

    assert not result.stage_changed
    assert not result.same_bottleneck
    assert "It was Evaluation, Governance; it is now Workflow, Governance at 2/5" in report
    assert "one constraint replaced another" in report


def test_an_unchanged_bottleneck_is_stated_plainly():
    result = progress(after=dict(BEFORE, product=5, platform=5))
    report = render_progress(result)

    assert result.same_bottleneck
    assert "still sets the stage at 2/5" in report
    assert "has not bought a stage, whatever else improved" in report


def test_lifting_every_capability_moves_the_stage():
    result = progress(after={pillar: 4 for pillar in PILLARS})

    assert result.stage_changed
    assert result.before.maturity == "Assisted"
    assert result.after.maturity == "Measured"


def test_a_renamed_organization_is_queried_rather_than_assumed():
    result = compare(built(BEFORE, "2026-01-15", "Old Name"), built(AFTER, "2026-04-20", "New Name"))

    assert result.renamed
    assert "name different organizations, Old Name then New Name" in render_progress(result)


def test_every_capability_appears_in_the_movement_table():
    report = render_progress(progress())
    rows = [line for line in report.splitlines() if line.startswith("| ") and "/5 |" in line]

    assert len(rows) == len(PILLARS)
    assert "| 0 |" in report and "| +1 |" in report and "| -1 |" in report


def test_the_date_shape_is_enforced_before_parsing():
    """date.fromisoformat takes the whole ISO 8601 set from 3.11, so 3.10 and 3.12 would disagree."""
    for value in ("20260115", "2026-W03-4", "15/01/2026", "2026-1-5"):
        with pytest.raises(AssessmentError, match="it must be a date as YYYY-MM-DD"):
            assess("X", "", BEFORE, value)


def test_a_well_shaped_but_impossible_date_is_rejected_as_such():
    with pytest.raises(AssessmentError, match="that is not a real date"):
        assess("X", "", BEFORE, "2026-02-30")


def test_the_documented_shape_is_accepted():
    assert assess("X", "", BEFORE, "2026-01-15").assessed_on.isoformat() == "2026-01-15"


def test_an_assessment_always_names_at_least_one_constraint():
    """The renderer relies on this; a profile with no constraints cannot be produced."""
    from itertools import product

    for combo in product((1, 3, 5), repeat=len(PILLARS)):
        assert assess("X", "", dict(zip(PILLARS, combo))).priorities


def test_the_change_column_is_formatted_from_the_delta_alone():
    report = render_progress(progress())
    rows = [line for line in report.splitlines() if line.startswith("| ") and "/5 |" in line]
    changes = [row.split("|")[4].strip() for row in rows]

    assert set(changes) == {"0", "+1", "-1"}
    assert all(not change.startswith("+0") for change in changes)
