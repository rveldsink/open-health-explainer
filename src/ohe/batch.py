from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .precheck import inspect_file


def _fingerprint(issue: Dict[str, Any]) -> str:
    return "|".join([
        str(issue.get("errorId", "OHE-UNKNOWN")),
        str(issue.get("category", "unknown")),
        str(issue.get("message", "")),
    ])


def cluster_reports(reports: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    counts = Counter()
    examples = defaultdict(list)

    for report in reports:
        for issue in report.get("issues", []):
            key = _fingerprint(issue)
            counts[key] += 1
            if len(examples[key]) < 3:
                examples[key].append(report.get("file"))

    clusters = []
    for key, count in counts.most_common():
        error_id, category, message = key.split("|", 2)
        clusters.append({
            "errorId": error_id,
            "category": category,
            "message": message,
            "occurrences": count,
            "exampleFiles": examples[key],
        })
    return clusters


def analyze_directory(path: str) -> Dict[str, Any]:
    root = Path(path)
    files = sorted(p for p in root.rglob("*.json") if p.is_file())
    reports = [inspect_file(str(p)) for p in files]
    clusters = cluster_reports(reports)

    files_with_issues = sum(1 for r in reports if r["issueCount"] > 0)
    return {
        "directory": str(root),
        "fileCount": len(reports),
        "filesWithIssues": files_with_issues,
        "totalIssues": sum(r["issueCount"] for r in reports),
        "clusters": clusters,
        "files": reports,
    }
