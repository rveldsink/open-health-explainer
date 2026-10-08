"""Explicit, checksum-pinned single-resource validation with retained evidence."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

from .explainer import explain_issue
from .validator_runner import parse_operation_outcome_json

FHIR_RELEASES = {"4.0.1": "R4", "4.3.0": "R4B", "5.0.0": "R5"}


def sha256(path):
    with Path(path).open("rb") as stream:
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_config(path):
    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict) or value.get("fhirVersion") not in FHIR_RELEASES:
        raise ValueError("Select an exact supported fhirVersion: 4.0.1, 4.3.0 or 5.0.0")
    engine = value.get("validator", {})
    if (not isinstance(engine, dict) or not isinstance(engine.get("version"), str)
            or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", engine["version"])
            or not isinstance(engine.get("sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", engine["sha256"])):
        raise ValueError("Pin validator.version and validator.sha256")
    packages = value.get("igPackages", [])
    if not isinstance(packages, list) or any(
        not isinstance(p, str) or not re.fullmatch(r"[a-zA-Z0-9_.-]+#[0-9]+\.[0-9]+\.[0-9]+", p)
        for p in packages
    ):
        raise ValueError("IG packages must use exact package#major.minor.patch versions")
    profiles = value.get("profiles", [])
    if not isinstance(profiles, list) or any(
        not isinstance(p, str) or not re.fullmatch(r"https?://[^\s|]+\|[^\s|]+", p)
        for p in profiles
    ):
        raise ValueError("Profiles must use canonical-url|version")
    return value


def validate_pinned(resource, validator, config, output, java="java", timeout=180, cache_home=None):
    """Never equate error-free output or a process exit code with full conformance."""
    settings = load_config(config)
    resource, validator, output = map(lambda p: Path(p).resolve(), (resource, validator, output))
    if sha256(validator) != settings["validator"]["sha256"]:
        raise ValueError("Validator JAR checksum differs from configuration")
    raw = resource.read_bytes()
    data = json.loads(raw)
    if not isinstance(data, dict) or not isinstance(data.get("resourceType"), str):
        raise ValueError("Expected a single FHIR JSON resource")
    if timeout <= 0:
        raise ValueError("Timeout must be positive")
    output.mkdir(parents=True, exist_ok=False)
    (output / "input.json").write_bytes(raw)
    (output / "config.json").write_text(json.dumps(settings, indent=2), encoding="utf-8")
    outcome = output / "operation-outcome.json"
    command = [str(java), "-Xmx3g"]
    if cache_home:
        command += ["-Duser.home=" + str(Path(cache_home).resolve())]
    command += ["-jar", str(validator), str(output / "input.json"),
                "-version", settings["fhirVersion"]]
    for package in settings.get("igPackages", []):
        command += ["-ig", package]
    for profile in settings.get("profiles", []):
        command += ["-profile", profile]
    command += ["-tx", "n/a", "-disable-default-resource-fetcher", "-output", str(outcome)]
    report = {"configuration": settings, "command": command,
              "inputSha256": hashlib.sha256(raw).hexdigest(),
              "status": "not-checkable", "coverage": "incomplete", "issues": [],
              "coverageNotes": ["Terminology server disabled; no full conformance claim.",
                                "Core/IG package cache and transitive dependencies are not content-locked."]}
    with (output / "validator.log").open("w", encoding="utf-8") as log:
        try:
            report["processExitCode"] = subprocess.run(
                command, stdout=log, stderr=subprocess.STDOUT, timeout=timeout
            ).returncode
        except (OSError, subprocess.TimeoutExpired) as error:
            report["executionError"] = str(error)
    try:
        parsed = parse_operation_outcome_json(outcome.read_text(encoding="utf-8-sig"))
        if not parsed["issues"]:
            raise ValueError("OperationOutcome has no issues; validation completion is unproven")
        if settings["fhirVersion"] != "5.0.0" and any(i["severity"] == "success" for i in parsed["issues"]):
            raise ValueError("Success severity is not defined for the selected pre-R5 release")
        report["rawOutcome"] = parsed["rawOutcome"]
        report["issues"] = [dict(explain_issue(i), severity=i["severity"], validatorCode=i["code"])
                            for i in parsed["issues"]]
        errors = any(i["severity"] in ("fatal", "error") for i in parsed["issues"])
        if "executionError" not in report:
            code = report.get("processExitCode")
            if code not in (0, 1) or (code == 1 and not errors):
                raise ValueError("Validator exit code does not match a completed validation")
            report["status"] = "failed" if errors else "no-errors-reported"
    except (OSError, ValueError) as error:
        report.setdefault("executionError", str(error))
    (output / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report
