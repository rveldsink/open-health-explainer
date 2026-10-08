import argparse
import json
from pathlib import Path

from .batch import analyze_directory
from .explainer import explain, explain_issue
from .precheck import inspect_file
from .validator_runner import run_validator, parse_operation_outcome_json
from .sources import LocalFolderSource, FhirRestSource, summarize_source


def analyze_operation_outcome(path: str):
    raw = Path(path).read_text(encoding="utf-8")
    outcome = parse_operation_outcome_json(raw)

    report = []
    for issue in outcome["issues"]:
        explained = explain_issue(issue)
        explained["severity"] = issue.get("severity")
        explained["validatorCode"] = issue.get("code")
        explained["expression"] = issue.get("expression", [])
        report.append(explained)

    return {
        "source": path,
        "issueCount": len(report),
        "issues": report,
        "reportedResult": "errors-reported" if any(i["severity"] in ("error", "fatal") for i in report) else "no-errors-reported",
        "validationCoverage": "incomplete" if any(i["coverageGap"] for i in report) else "unknown",
        "coverageNote": "OperationOutcome allein belegt keinen vollständigen Prüfumfang. Laufkonfiguration, Profile und Terminologieunterstützung separat nachweisen.",
        "rawOutcome": outcome["rawOutcome"],
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

    source_p = subs.add_parser("source")
    source_p.add_argument("location")
    source_p.add_argument("--type", choices=["folder", "fhir-rest"], default="folder")
    source_p.add_argument("--resource-type", default="Patient")
    source_p.add_argument("--limit", type=int)

    subs.add_parser("specification", help="Export pinned official profile statements")
    medication_p = subs.add_parser("validate-medication", help="Validate MedicationRequest against German medication 1.0.7")
    medication_p.add_argument("resource")
    medication_p.add_argument("--validator", required=True)
    medication_p.add_argument("--output", required=True)
    medication_p.add_argument("--java", default="java")
    medication_p.add_argument("--cache-home")
    medication_p.add_argument("--timeout", type=int, default=180)
    workflow_p = subs.add_parser("workflow", help="Local batch validation, explanations and correction comparison")
    workflow_p.add_argument("inputs", help="JSON file or directory")
    workflow_p.add_argument("--output", required=True)
    workflow_p.add_argument("--validator", required=True)
    workflow_p.add_argument("--java", default="java")
    workflow_p.add_argument("--cache-home")
    workflow_p.add_argument("--corrections", help="Reviewed corrected files with matching names")
    workflow_p.add_argument("--ai-model", help="Optional installed local Ollama model; no downloads")
    workflow_p.add_argument("--timeout", type=int, default=180)
    workflow_p.add_argument("--spec", choices=("medication", "immunization"), default="medication",
                            help="Explicit profile mode; immunization checks R4 structure, not vaccine schedules")
    pinned_p = subs.add_parser("validate-pinned", help="General version-pinned validation with evidence")
    pinned_p.add_argument("resource")
    pinned_p.add_argument("--validator", required=True)
    pinned_p.add_argument("--config", required=True)
    pinned_p.add_argument("--output", required=True)
    pinned_p.add_argument("--java", default="java")
    pinned_p.add_argument("--cache-home")
    pinned_p.add_argument("--timeout", type=int, default=180)
    demo_p = subs.add_parser("serve-demo", help="Loopback-only synthetic FHIR R4 fixture")
    demo_p.add_argument("--port", type=int, default=8765)
    negative_p = subs.add_parser("profile-cases", help="Negative candidates from a resolved snapshot")
    negative_p.add_argument("resource")
    negative_p.add_argument("profile")
    negative_p.add_argument("--value-set", action="append", default=[])
    negative_p.add_argument("--output", required=True)
    args = parser.parse_args()

    if args.cmd == "serve-demo":
        from .demo_server import serve_demo
        try:
            serve_demo(args.port)
        except (OSError, ValueError) as error:
            parser.error(str(error))
        return
    if args.cmd == "validate-pinned":
        from .validation import validate_pinned
        try:
            report = validate_pinned(args.resource, args.validator, args.config, args.output,
                                     args.java, args.timeout, args.cache_home)
        except (OSError, ValueError) as error:
            parser.error(str(error))
        print(json.dumps({k: report[k] for k in ("status", "coverage", "inputSha256")}, indent=2))
        raise SystemExit({"failed": 1, "not-checkable": 2, "no-errors-reported": 3}[report["status"]])
    if args.cmd == "profile-cases":
        from .profile_tests import generate_profile_cases
        try:
            read = lambda path: json.loads(Path(path).read_text(encoding="utf-8-sig"))
            value_sets = {}
            for path in args.value_set:
                value = read(path)
                value_sets[value["url"]] = value
                if value.get("version"):
                    value_sets[value["url"] + "|" + value["version"]] = value
            result = generate_profile_cases(read(args.resource), read(args.profile), value_sets)
            output = Path(args.output)
            output.mkdir(parents=True, exist_ok=False)
            for case in result["cases"]:
                (output / (case["name"] + ".json")).write_text(json.dumps(case["resource"], indent=2), encoding="utf-8")
            (output / "manifest.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        except (OSError, ValueError, KeyError, TypeError) as error:
            parser.error(str(error))
        print(json.dumps({"candidates": len(result["cases"]), "skipped": len(result["skipped"])}))
        return

    if args.cmd == "workflow":
        from .workflow import run_batch
        try:
            result = run_batch(args.inputs, args.output, args.validator, args.java, args.cache_home,
                               args.corrections, args.ai_model, args.timeout, mode=args.spec)
        except (OSError, ValueError) as error:
            parser.error(str(error))
        print(json.dumps(result["summary"], indent=2))
        print(str(Path(args.output).resolve()/"index.html"))
        raise SystemExit(2 if any(c.get("workflowError") or c["report"]["status"] == "not-checkable" or c.get("after", {}).get("status") == "not-checkable" for c in result["cases"]) else
                         1 if any(c.get("after", c["report"])["status"] == "failed" for c in result["cases"]) else 3)


    if args.cmd == "specification":
        from .specification import requirements
        print(json.dumps(requirements(), indent=2, ensure_ascii=True))
        return
    if args.cmd == "validate-medication":
        from .specification import validate
        try:
            report = validate(args.resource, args.validator, args.output, args.java, args.cache_home, args.timeout)
        except (OSError, ValueError) as error:
            parser.error(str(error))
        print(json.dumps({k: report[k] for k in ("status", "coverage", "inputSha256")}, indent=2))
        # Offline coverage is incomplete even when the validator reports no errors.
        raise SystemExit({"failed": 1, "not-checkable": 2, "no-errors-reported": 3}[report["status"]])

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

    if args.cmd == "source":
        if args.type == "folder":
            source = LocalFolderSource(args.location)
        else:
            source = FhirRestSource(args.location, resource_type=args.resource_type)

        print(json.dumps(
            summarize_source(source, limit=args.limit),
            indent=2,
            ensure_ascii=False
        ))
        return


if __name__ == "__main__":
    main()
