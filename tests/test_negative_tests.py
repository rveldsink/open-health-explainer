import json
from pathlib import Path
from ohe.negative_tests import generate_negative_cases

def test_negative_cases_are_generated():
    root = Path(__file__).resolve().parents[1]
    resource = json.loads((root / "examples" / "patient_valid_synthetic.json").read_text(encoding="utf-8"))
    cases = dict(generate_negative_cases(resource))
    assert "missing_identifier" in cases
    assert "identifier" not in cases["missing_identifier"]
    assert "invalid_birthdate_format" in cases
