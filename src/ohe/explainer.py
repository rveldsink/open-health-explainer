import re
from typing import Optional, Dict, Any
from .catalog import ERROR_CATALOG

# Observed with HL7 Java 6.10.4. This is an adapter, not a normative rule catalogue.
PROFILE_UNAVAILABLE = {
    "VALIDATION_VAL_PROFILE_UNKNOWN_NOT_POLICY",
    "VALIDATION_VAL_PROFILE_UNKNOWN_ERROR",
}


def explain_issue(issue: Dict[str, Any]) -> Dict[str, Any]:
    message = issue.get("diagnostics") or issue.get("details") or ""
    result = explain(message)
    ids = set(issue.get("messageIds", []))
    result["classificationBasis"] = "text-heuristic" if result["matched"] else "unclassified"
    result["coverageGap"] = False
    if ids & PROFILE_UNAVAILABLE:
        result.update(matched=True, errorId="OHE-COVERAGE-001", category="profile-unavailable",
                      fixPolicy="manual-review", coverageGap=True,
                      explanation_de="Ein angegebenes Profil konnte nicht geprüft werden. Die Prüfung ist unvollständig.",
                      explanation_en="A declared profile could not be checked. Validation is incomplete.",
                      suggestedAction_de="Profilpaket, Version und Resolver prüfen; Zielprofil explizit vorgeben und erneut validieren.",
                      suggestedAction_en="Check profile package, version and resolver; explicitly require the target profile and validate again.")
        result["classificationBasis"] = "validator-message-id"
    elif "Validation_VAL_Profile_Minimum" in ids:
        rule = next(r for r in ERROR_CATALOG if r["errorId"] == "OHE-CARD-001")
        result.update({k: v for k, v in rule.items() if k != "patterns"})
        result.update(matched=True, classificationBasis="validator-message-id", fixPolicy="manual-review")
        result["suggestedAction_de"] = "Pflichtfeld anhand verlässlicher Quelldaten ergänzen. Keinen Wert erfinden; anschließend erneut validieren."
        result["suggestedAction_en"] = "Supply the required field from reliable source data. Do not invent a value; validate again."
    expressions = issue.get("expression", [])
    result["pathSource"] = "message-text" if result.get("path") else None
    if not result.get("path") and len(expressions) == 1:
        result["path"] = expressions[0]
        result["pathSource"] = "expression"
    for key in ("messageIds", "profileContexts", "validatorSources", "rawIssue"):
        result[key] = issue.get(key)
    return result

def extract_path(message: str) -> Optional[str]:
    match = re.match(r"([A-Za-z][A-Za-z0-9_.\[\]-]*):", message.strip())
    return match.group(1) if match else None

def explain(message: str) -> Dict[str, Any]:
    lowered = message.lower()
    for rule in ERROR_CATALOG:
        for pattern in rule["patterns"]:
            if pattern.lower() in lowered:
                return {
                    "matched": True,
                    "errorId": rule["errorId"],
                    "category": rule["category"],
                    "path": extract_path(message),
                    "fixPolicy": rule["fixPolicy"],
                    "explanation_de": rule["explanation_de"],
                    "explanation_en": rule["explanation_en"],
                    "suggestedAction_de": rule["suggestedAction_de"],
                    "suggestedAction_en": rule["suggestedAction_en"],
                    "rawMessage": message,
                }

    return {
        "matched": False,
        "errorId": "OHE-UNKNOWN-001",
        "category": "unknown",
        "path": extract_path(message),
        "fixPolicy": "manual-review",
        "explanation_de": "Dieser Validator-Fehler ist noch nicht klassifiziert.",
        "explanation_en": "This validator error is not yet classified.",
        "rawMessage": message,
    }
