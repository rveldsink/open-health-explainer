import json
from pathlib import Path

import pytest

from ohe.cli import main


def test_profile_cli_outputs_candidates(tmp_path, monkeypatch, capsys):
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / "cases"
    monkeypatch.setattr("sys.argv", ["ohe", "profile-cases",
        str(root / "examples/immunization-r4/00-reference.json"),
        str(root / "src/ohe/specs/immunization-r4/definitions/StructureDefinition-ImmunizationRecommendation.json"),
        "--output", str(output)])
    main()
    summary = json.loads(capsys.readouterr().out)
    assert summary["candidates"] == 3
    manifest = json.loads((output / "manifest.json").read_text())
    for case in manifest["cases"]:
        assert json.loads((output / (case["name"] + ".json")).read_text()) == case["resource"]
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2


@pytest.mark.parametrize("status,code", [("failed", 1), ("not-checkable", 2), ("no-errors-reported", 3)])
def test_pinned_cli_status_and_arguments(monkeypatch, capsys, status, code):
    def validate(*args):
        assert args == ("patient.json", "validator.jar", "r4.json", "run", "java", 180, None)
        return {"status":status, "coverage":"incomplete", "inputSha256":"mock"}
    monkeypatch.setattr("ohe.validation.validate_pinned", validate)
    monkeypatch.setattr("sys.argv", ["ohe", "validate-pinned", "patient.json", "--validator", "validator.jar",
                                    "--config", "r4.json", "--output", "run"])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == code
    assert json.loads(capsys.readouterr().out)["coverage"] == "incomplete"
