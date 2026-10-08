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
    if not isinstance(data, dict) or data.get("resourceType") != "OperationOutcome":
        raise ValueError("Expected FHIR OperationOutcome JSON")

    raw_issues = data.get("issue", [])
    if not isinstance(raw_issues, list):
        raise ValueError("OperationOutcome.issue must be an array")
    issues = []
    for issue in raw_issues:
        if not isinstance(issue, dict):
            raise ValueError("OperationOutcome issue must be an object")
        if issue.get("severity") not in ("fatal", "error", "warning", "information", "success"):
            raise ValueError("Missing or unsupported OperationOutcome severity")
        if not isinstance(issue.get("code"), str) or not issue["code"]:
            raise ValueError("Missing OperationOutcome issue code")
        for name in ("expression", "location"):
            items = issue.get(name, [])
            if not isinstance(items, list) or any(not isinstance(i, str) for i in items):
                raise ValueError("OperationOutcome." + name + " must be an array of strings")
        details = issue.get("details", {})
        if not isinstance(details, dict):
            raise ValueError("OperationOutcome.details must be an object")
        for text in (issue.get("diagnostics"), details.get("text")):
            if text is not None and not isinstance(text, str):
                raise ValueError("OperationOutcome diagnostic text must be a string")
        extensions = issue.get("extension", [])
        if not isinstance(extensions, list) or any(not isinstance(e, dict) for e in extensions):
            raise ValueError("OperationOutcome.extension must be an array of objects")
        def values(suffix, field):
            url = "http://hl7.org/fhir/StructureDefinition/operationoutcome-" + suffix
            return [item[field] for item in extensions if item.get("url") == url and isinstance(item.get(field), str)]
        issues.append({
            "severity": issue.get("severity"),
            "code": issue.get("code"),
            "details": (issue.get("details") or {}).get("text"),
            "diagnostics": issue.get("diagnostics"),
            "expression": issue.get("expression", []),
            "location": issue.get("location", []),
            "detailsCoding": details.get("coding", []),
            "messageIds": values("message-id", "valueCode"),
            "profileContexts": values("issue-context", "valueString"),
            "validatorSources": values("issue-source", "valueString"),
            "rawIssue": issue,
        })
    return {"resourceType": "OperationOutcome", "issues": issues, "rawOutcome": data}
