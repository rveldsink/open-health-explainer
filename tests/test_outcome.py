import json
from ohe.cli import analyze_operation_outcome
from ohe.explainer import explain_issue
from ohe.validator_runner import parse_operation_outcome_json


def issue(message_id, text="Beliebige Übersetzung", severity="warning"):
    return {"severity": severity, "code": "structure", "details": {"text": text},
            "expression": ["Patient.meta.profile[0]"], "extension": [
                {"url": "http://hl7.org/fhir/StructureDefinition/operationoutcome-message-id", "valueCode": message_id},
                {"url": "http://hl7.org/fhir/StructureDefinition/operationoutcome-issue-context", "valueString": "https://example.org/profile|0.1.0"},
                {"url": "https://example.org/unknown-extension", "valueString": "preserve"}]}


def test_translated_minimum_uses_id_and_preserves_evidence():
    raw = {"resourceType": "OperationOutcome", "issue": [issue("Validation_VAL_Profile_Minimum", severity="error")]}
    parsed = parse_operation_outcome_json(json.dumps(raw))
    result = explain_issue(parsed["issues"][0])
    assert result["errorId"] == "OHE-CARD-001"
    assert result["classificationBasis"] == "validator-message-id"
    assert result["fixPolicy"] == "manual-review"
    assert result["profileContexts"] == ["https://example.org/profile|0.1.0"]
    assert result["rawIssue"] == raw["issue"][0]
    assert parsed["rawOutcome"] == raw


def test_unavailable_profile_overrides_misleading_text(tmp_path):
    raw = {"resourceType": "OperationOutcome", "issue": [issue("VALIDATION_VAL_PROFILE_UNKNOWN_NOT_POLICY", "unknown code")]}
    path = tmp_path / "outcome.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    result = analyze_operation_outcome(str(path))
    assert result["validationCoverage"] == "incomplete"
    assert result["reportedResult"] == "no-errors-reported"
    assert result["issues"][0]["category"] == "profile-unavailable"
    assert result["issues"][0]["pathSource"] == "expression"


def test_empty_outcome_does_not_prove_complete_validation(tmp_path):
    path = tmp_path / "outcome.json"
    path.write_text('{"resourceType":"OperationOutcome","issue":[]}', encoding="utf-8")
    result = analyze_operation_outcome(str(path))
    assert result["validationCoverage"] == "unknown"
    assert result["reportedResult"] == "no-errors-reported"


def test_unknown_id_is_not_claimed_as_supported():
    parsed = parse_operation_outcome_json(json.dumps({"resourceType": "OperationOutcome", "issue": [issue("FUTURE_ID")]}))
    result = explain_issue(parsed["issues"][0])
    assert result["matched"] is False
    assert result["classificationBasis"] == "unclassified"
