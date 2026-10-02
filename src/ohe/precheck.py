import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List


MOJIBAKE_PATTERNS = ("Ã¤", "Ã¶", "Ã¼", "ÃŸ", "Ã©", "Â", "â€“", "â€")
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def inspect_file(path: str) -> Dict[str, Any]:
    p = Path(path)
    raw = p.read_bytes()
    issues: List[Dict[str, Any]] = []

    encoding = "utf-8"
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        encoding = "non-utf-8"
        text = raw.decode("cp1252", errors="replace")
        issues.append({
            "errorId": "OHE-ENC-001",
            "category": "encoding",
            "severity": "error",
            "message": "Input is not valid UTF-8.",
            "detail": str(exc),
        })

    if raw.startswith(b"\xef\xbb\xbf"):
        issues.append({
            "errorId": "OHE-ENC-002",
            "category": "encoding",
            "severity": "warning",
            "message": "UTF-8 BOM detected.",
        })

    controls = CONTROL_CHAR_RE.findall(text)
    if controls:
        issues.append({
            "errorId": "OHE-CHAR-001",
            "category": "character",
            "severity": "error",
            "message": "Disallowed control characters detected.",
            "count": len(controls),
        })

    mojibake_hits = [pattern for pattern in MOJIBAKE_PATTERNS if pattern in text]
    if mojibake_hits:
        issues.append({
            "errorId": "OHE-ENC-003",
            "category": "encoding",
            "severity": "warning",
            "message": "Possible character-encoding conversion damage detected.",
            "examples": mojibake_hits[:5],
        })

    parsed = None
    if p.suffix.lower() == ".json":
        try:
            parsed = json.loads(text.lstrip("\ufeff"))
        except json.JSONDecodeError as exc:
            issues.append({
                "errorId": "OHE-JSON-001",
                "category": "syntax",
                "severity": "error",
                "message": "Invalid JSON syntax.",
                "line": exc.lineno,
                "column": exc.colno,
                "detail": exc.msg,
            })

    if isinstance(parsed, dict):
        resource_type = parsed.get("resourceType")
    else:
        resource_type = None

    return {
        "file": str(p),
        "sizeBytes": len(raw),
        "sha256": _sha256(raw),
        "encoding": encoding,
        "resourceType": resource_type,
        "issueCount": len(issues),
        "issues": issues,
    }
