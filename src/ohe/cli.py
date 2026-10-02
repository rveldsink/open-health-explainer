import argparse
import json
from pathlib import Path

from .batch import analyze_directory
from .explainer import explain
from .precheck import inspect_file
from .validator_runner import run_validator, parse_operation_outcome_json


def analyze_operation_outcome(path: str):
    raw = Path(path).read_text(encoding="utf-8")
    outcome = parse_operation_outcome_json(raw)

    report = []
    for issue in outcome["issues"]:
        message = issue.get("diagnostics") or issue.get("details") or ""
        explained = explain(message)
        explained["severity"] = issue.get("severity")
        explained["validatorCode"] = issue.get("code")
        explained["expression"] = issue.get("expression", [])
        report.append(explained)

    return {
        "source": path,
        "issueCount": len(report),
        "issues": report,
    }


def main():
    parser = argparse.ArgumentParser(prog="ohe")
    subs = parser.add_subparsers(dest="cmd", required=True)

    explain_p = subs.add_parser("explain")
    explain_p.add_argument("message")

    validate_p = subs.add_parser("validate")
    validate_p.add_argument("resource")
    validate_p.add_argument("--validator", required=True)

    analyze_p = subs.add_parser("analyze")
    analyze_p.add_argument("operation_outcome")

    precheck_p = subs.add_parser("precheck")
    precheck_p.add_argument("file")

    batch_p = subs.add_parser("batch")
    batch_p.add_argument("directory")

    args = parser.parse_args()

    if args.cmd == "explain":
        print(json.dumps(explain(args.message), indent=2, ensure_ascii=False))
        return

    if args.cmd == "validate":
        result = run_validator(args.resource, args.validator)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        raise SystemExit(result.returncode)

    if args.cmd == "analyze":
        print(json.dumps(analyze_operation_outcome(args.operation_outcome), indent=2, ensure_ascii=False))
        return

    if args.cmd == "precheck":
        print(json.dumps(inspect_file(args.file), indent=2, ensure_ascii=False))
        return

    if args.cmd == "batch":
        print(json.dumps(analyze_directory(args.directory), indent=2, ensure_ascii=False))
        return


if __name__ == "__main__":
    main()
