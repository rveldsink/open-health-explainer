import json
import subprocess
from typing import Dict, Any, List

def run_validator(resource_path: str, validator_jar: str, ig_packages: List[str] | None = None) -> subprocess.CompletedProcess:
    command = ["java", "-jar", validator_jar, resource_path, "-output-style", "json"]
    for package in ig_packages or []:
        command.extend(["-ig", package])
    return subprocess.run(command, text=True, capture_output=True)

def parse_operation_outcome_json(raw: str) -> Dict[str, Any]:
    data = json.loads(raw)
    if data.get("resourceType") != "OperationOutcome":
        raise ValueError("Expected FHIR OperationOutcome JSON")

    issues = []
    for issue in data.get("issue", []):
        extensions = issue.get("extension", [])
        def values(suffix, field):
            url = "http://hl7.org/fhir/StructureDefinition/operationoutcome-" + suffix
            return [item[field] for item in extensions if item.get("url") == url and field in item]
        issues.append({
            "severity": issue.get("severity"),
            "code": issue.get("code"),
            "details": (issue.get("details") or {}).get("text"),
            "diagnostics": issue.get("diagnostics"),
            "expression": issue.get("expression", []),
            "messageIds": values("message-id", "valueCode"),
            "profileContexts": values("issue-context", "valueString"),
            "validatorSources": values("issue-source", "valueString"),
            "rawIssue": issue,
        })
    return {"resourceType": "OperationOutcome", "issues": issues, "rawOutcome": data}
