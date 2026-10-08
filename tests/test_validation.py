import hashlib
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from ohe.validation import load_config, validate_pinned
from ohe.validator_runner import parse_operation_outcome_json
from ohe.explainer import explain_issue


@pytest.fixture
def setup(tmp_path):
    jar = tmp_path / "validator.jar"
    jar.write_bytes(b"mock-engine")
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"fhirVersion": "4.0.1", "validator": {
        "version": "6.10.4", "sha256": hashlib.sha256(jar.read_bytes()).hexdigest()},
        "igPackages": ["example.fhir#1.2.3"], "profiles": ["https://example.org/profile|1.0.0"]}))
    resource = tmp_path / "patient.json"
    resource.write_text('{"resourceType":"Patient","id":"synthetic"}')
    return resource, jar, config, tmp_path / "evidence"


@pytest.mark.parametrize("release", ["4.0.1", "4.3.0", "5.0.0"])
def test_version_and_evidence(setup, monkeypatch, release):
    resource, jar, config, output = setup
    settings = json.loads(config.read_text())
    settings["fhirVersion"] = release
    config.write_text(json.dumps(settings))
    def run(command, **kwargs):
        assert command[command.index("-version") + 1] == release
        assert command[command.index("-ig") + 1] == "example.fhir#1.2.3"
        assert command[command.index("-profile") + 1] == "https://example.org/profile|1.0.0"
        assert "-output-style" not in command
        assert command[command.index("-tx") + 1] == "n/a"
        assert "-disable-default-resource-fetcher" in command
        assert kwargs["timeout"] == 180
        Path(command[-1]).write_text(json.dumps({"resourceType": "OperationOutcome", "issue": [
            {"severity": "information", "code": "informational", "diagnostics": "Done"}]}))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(subprocess, "run", run)
    result = validate_pinned(*setup)
    assert result["status"] == "no-errors-reported"
    assert result["coverage"] == "incomplete"
    assert (output / "input.json").read_bytes() == resource.read_bytes()
    assert json.loads((output / "config.json").read_text()) == settings
    assert json.loads((output / "report.json").read_text()) == result
    with pytest.raises(FileExistsError):
        validate_pinned(*setup)


@pytest.mark.parametrize("result,code,expected", [
    ({"resourceType":"OperationOutcome","issue":[{"severity":"error","code":"invalid"}]}, 1, "failed"),
    ({"resourceType":"OperationOutcome","issue":[{"severity":"information","code":"informational"}]}, 1, "not-checkable"),
    ({"resourceType":"OperationOutcome","issue":[{"severity":"error","code":"invalid"}]}, 2, "not-checkable"),
    ({"resourceType":"OperationOutcome","issue":[]}, 0, "not-checkable"),
    ({"resourceType":"OperationOutcome","issue":[{"severity":"success","code":"informational"}]}, 0, "not-checkable"),
    ({"resourceType":"Bundle"}, 0, "not-checkable"),
    (None, 0, "not-checkable"),
])
def test_no_false_success(setup, monkeypatch, result, code, expected):
    def run(command, **kwargs):
        if result is not None:
            Path(command[-1]).write_text(json.dumps(result))
        return SimpleNamespace(returncode=code)
    monkeypatch.setattr(subprocess, "run", run)
    report = validate_pinned(*setup)
    assert report["status"] == expected
    if expected == "not-checkable":
        assert report["executionError"]


@pytest.mark.parametrize("error", [OSError("no java"), subprocess.TimeoutExpired("java", 1)])
def test_engine_failure_retains_evidence(setup, monkeypatch, error):
    def run(*args, **kwargs):
        raise error
    monkeypatch.setattr(subprocess, "run", run)
    report = validate_pinned(*setup)
    assert report["status"] == "not-checkable"
    assert report["executionError"]
    assert (setup[-1] / "report.json").exists()


def test_checksum_blocks_execution(setup, monkeypatch):
    setup[1].write_bytes(b"tampered")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("Must not run"))
    with pytest.raises(ValueError, match="checksum"):
        validate_pinned(*setup)
    assert not setup[-1].exists()


@pytest.mark.parametrize("key,value", [("fhirVersion", "R4"), ("fhirVersion", "latest"),
    ("igPackages", ["example#latest"]), ("igPackages", ["https://example.org/ig"]),
    ("profiles", ["https://example.org/unversioned"]), ("validator", {})])
def test_rejects_unpinned_configuration(setup, key, value):
    config = setup[2]
    data = json.loads(config.read_text())
    data[key] = value
    config.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_config(config)


@pytest.mark.parametrize("data", [[], None, {"resourceType":"Patient"},
    {"resourceType":"OperationOutcome","issue":{}},
    {"resourceType":"OperationOutcome","issue":[None]},
    {"resourceType":"OperationOutcome","issue":[{"severity":"unknown","code":"invalid"}]},
    {"resourceType":"OperationOutcome","issue":[{"severity":"error"}]},
    {"resourceType":"OperationOutcome","issue":[{"severity":"error","code":"invalid","expression":"Patient"}]},
    {"resourceType":"OperationOutcome","issue":[{"severity":"error","code":"invalid","details":[]}]},
    {"resourceType":"OperationOutcome","issue":[{"severity":"error","code":"invalid","diagnostics":{}}]},
])
def test_malformed_outcome_is_rejected(data):
    with pytest.raises(ValueError):
        parse_operation_outcome_json(json.dumps(data))


def test_official_examples_and_location_fallback():
    fixtures = Path(__file__).parent / "fixtures" / "hl7"
    for source in json.loads((fixtures / "manifest.json").read_text()):
        raw = (fixtures / source["file"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == source["sha256"]
        parsed = parse_operation_outcome_json(raw)
        assert parsed["rawOutcome"] == json.loads(raw)
        assert len(parsed["issues"]) == 1
        assert parsed["issues"][0]["code"] == "code-invalid"
    issue = {"severity":"error", "code":"invalid", "location":["Patient.name"],
             "details":{"coding":[{"system":"https://example.org/codes", "code":"test"}]}}
    parsed = parse_operation_outcome_json(json.dumps({"resourceType":"OperationOutcome","issue":[issue]}))
    explained = explain_issue(parsed["issues"][0])
    assert explained["path"] == "Patient.name"
    assert explained["pathSource"] == "location"
    assert parsed["issues"][0]["detailsCoding"] == issue["details"]["coding"]
