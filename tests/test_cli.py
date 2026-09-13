import json
from pathlib import Path

from ai_engineering_journey.cli import main

ROOT = Path(__file__).parents[1]
EXAMPLE = ROOT / "examples/org-assessment.json"


def test_assess_writes_a_roadmap(tmp_path, capsys):
    output = tmp_path / "roadmap.md"

    assert main(["assess", str(EXAMPLE), "--output", str(output)]) == 0

    out = capsys.readouterr().out
    assert "Maturity: Assisted" in out
    assert "Held below Repeatable by: Evaluation, Governance" in out
    assert output.read_text().startswith("# AI Engineering Roadmap:")


def test_an_invalid_profile_reports_every_problem_without_a_traceback(tmp_path, capsys):
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({
        "organization": "X",
        "scores": {"product": 9, "workflow": 0, "evaluation": 2, "architecture": 3,
                   "platform": 4, "governance": 2, "learning": 3},
    }))

    assert main(["assess", str(path)]) == 2

    err = capsys.readouterr().err
    assert err.startswith("error: ")
    assert "product is 9" in err
    assert "workflow is 0" in err
    assert "Traceback" not in err


def test_a_missing_file_is_reported_cleanly(tmp_path, capsys):
    assert main(["assess", str(tmp_path / "absent.json")]) == 2
    assert "error: " in capsys.readouterr().err


def test_malformed_json_is_reported_cleanly(tmp_path, capsys):
    path = tmp_path / "profile.json"
    path.write_text("{not json")

    assert main(["assess", str(path)]) == 2
    assert "is not valid JSON" in capsys.readouterr().err


def test_a_non_object_payload_is_reported_cleanly(tmp_path, capsys):
    path = tmp_path / "profile.json"
    path.write_text("[1, 2, 3]")

    assert main(["assess", str(path)]) == 2
    assert "must contain a JSON object" in capsys.readouterr().err


def test_non_object_scores_are_reported_cleanly(tmp_path, capsys):
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({"organization": "X", "scores": [1, 2, 3]}))

    assert main(["assess", str(path)]) == 2
    assert "scores must be a JSON object" in capsys.readouterr().err


def test_a_uniform_profile_is_described_rather_than_ranked(tmp_path, capsys):
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({
        "organization": "Floor",
        "scores": {key: 1 for key in
                   ("product", "workflow", "evaluation", "architecture",
                    "platform", "governance", "learning")},
    }))

    assert main(["assess", str(path), "--output", str(tmp_path / "r.md")]) == 0
    assert "none stand out" in capsys.readouterr().out


def test_a_null_organization_is_absent_rather_than_the_word_none(tmp_path, capsys):
    path = tmp_path / "profile.json"
    output = tmp_path / "roadmap.md"
    path.write_text(json.dumps({
        "organization": None,
        "context": None,
        "scores": {key: 3 for key in
                   ("product", "workflow", "evaluation", "architecture",
                    "platform", "governance", "learning")},
    }))

    assert main(["assess", str(path), "--output", str(output)]) == 0

    assert "Organization: Unnamed organization" in capsys.readouterr().out
    roadmap = output.read_text()
    assert roadmap.startswith("# AI Engineering Roadmap: Unnamed organization")
    assert "\nNone\n" not in roadmap
