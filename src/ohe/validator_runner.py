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
        issues.append({
            "severity": issue.get("severity"),
            "code": issue.get("code"),
            "details": (issue.get("details") or {}).get("text"),
            "diagnostics": issue.get("diagnostics"),
            "expression": issue.get("expression", []),
        })
    return {"resourceType": "OperationOutcome", "issues": issues}
