import json
from ohe.validator_runner import parse_operation_outcome_json

def test_operation_outcome_parser():
    raw = json.dumps({
        "resourceType": "OperationOutcome",
        "issue": [{
            "severity": "error",
            "code": "structure",
            "diagnostics": "Example error",
            "expression": ["Patient.identifier"]
        }]
    })
    parsed = parse_operation_outcome_json(raw)
    assert parsed["issues"][0]["code"] == "structure"
    assert parsed["issues"][0]["expression"] == ["Patient.identifier"]
