import re
from typing import Optional, Dict, Any
from .catalog import ERROR_CATALOG

def extract_path(message: str) -> Optional[str]:
    match = re.match(r"([A-Za-z][A-Za-z0-9_.\\[\\]-]*):", message.strip())
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
