"""Local batch validation. Suggestions never modify source data."""
import difflib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from .specification import validate, requirements
from .validator_runner import parse_operation_outcome_json
from .explainer import explain_issue


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def explain_report(report, rule_catalogue=None):
    outcome = report.get("rawOutcome", {"resourceType": "OperationOutcome", "issue": []})
    issues = parse_operation_outcome_json(json.dumps(outcome))["issues"]
    rules = (rule_catalogue if rule_catalogue is not None else requirements())["requirements"]
    findings = []
    for number, issue in enumerate(issues, 1):
        explanation = explain_issue(issue)
        message = issue.get("diagnostics") or issue.get("details") or ""
        evidence = []
        # Only explicit invariant keys count as direct rule matches.
        for rule in rules:
            if rule["kind"] == "constraint":
                for invariant in rule["value"]:
                    key = invariant.get("key")
                    if key and rule["profile"] + "#" + key in issue.get("messageIds", []):
                        evidence.append({"key": key, "profile": rule["profile"], "version": rule["version"],
                                         "file": rule["file"], "pointer": rule["pointer"], "sha256": rule["sha256"], "rule": invariant})
        ids = set(issue.get("messageIds", []))
        if ids & {"Terminology_TX_NoValid_15", "TERMINOLOGY_TX_WARNING"}:
            explanation.update(explanation_de="Terminologie konnte nicht vollständig geprüft werden.",
                               suggestedAction_de="Die genannte Terminologie in passender Version bereitstellen und erneut prüfen. Keinen Code allein wegen dieses Hinweises ändern.",
                               coverageGap=True, classificationBasis="validator-message-id", category="terminology-unavailable")
        elif ids & {"Unknown_Code_in_Version", "Terminology_TX_NoValid_12", "Terminology_TX_NoValid_16"}:
            explanation.update(explanation_de="Der angegebene Code ist unbekannt oder gehört nicht zur geforderten Wertemenge.",
                               suggestedAction_de="Code, System-URI und Version mit den Quelldaten und der offiziellen Wertemenge abgleichen. Kein Ersatzwert ohne fachliche Grundlage.",
                               classificationBasis="validator-message-id", category="code-membership")
        elif "Validation_VAL_Profile_Maximum" in ids:
            explanation.update(explanation_de="Ein Feld ist häufiger vorhanden als im Profil erlaubt oder dort ausgeschlossen.",
                               suggestedAction_de="Profil und Datenstelle abgleichen. Vor Entfernen prüfen, ob die Information an anderer Stelle übertragen werden muss.",
                               classificationBasis="validator-message-id", category="maximum-cardinality")
        elif evidence:
            explanation.update(explanation_de=evidence[0]["rule"].get("human", "Eine offizielle Profilregel ist verletzt."),
                               suggestedAction_de="Die betroffene Datenstelle mit dieser Regel und den freigegebenen Quelldaten vergleichen. Eine Korrektur separat speichern und erneut prüfen.",
                               classificationBasis="official-invariant-id", category=evidence[0]["key"])
        findings.append({"id": f"F{number:03}", "severity": issue.get("severity"),
                         "message": message, "locations": issue.get("expression", []),
                         "explanation": explanation, "ruleEvidence": evidence,
                         "ruleLinkStatus": "explicit-invariant-match" if evidence else "not-resolved"})
    return findings


def compare(before, after, old_data, new_data):
    def signature(issue):
        return json.dumps([issue.get("severity"), issue.get("code"), issue.get("expression"),
                           issue.get("diagnostics"), issue.get("details")], sort_keys=True)
    a, b = Counter(map(signature, before.get("issues", []))), Counter(map(signature, after.get("issues", [])))
    return {"beforeStatus": before["status"], "afterStatus": after["status"],
            "comparisonMethod": "Exact issue signature; changed wording is not proof of a repaired cause.",
            "comparable": before["status"] != "not-checkable" and after["status"] != "not-checkable",
            "disappeared": sum((a-b).values()), "new": sum((b-a).values()),
            "remaining": sum((a & b).values()),
            "diff": "".join(difflib.unified_diff(
                json.dumps(old_data, ensure_ascii=False, indent=2).splitlines(True),
                json.dumps(new_data, ensure_ascii=False, indent=2).splitlines(True),
                fromfile="before.json", tofile="after.json"))}


def run_batch(inputs, output, validator, java="java", cache_home=None, corrections=None, ai_model=None, timeout=180, mode="medication"):
    from .profiles import catalogue
    selected_catalogue = catalogue(mode)
    inputs, output = Path(inputs).resolve(), Path(output).resolve()
    files = sorted(inputs.glob("*.json")) if inputs.is_dir() else [inputs]
    if not files or any(not f.is_file() for f in files):
        raise ValueError("No input JSON files found")
    output.mkdir(parents=True, exist_ok=False)
    result = {"schemaVersion": 1, "createdAt": datetime.now(timezone.utc).isoformat(),
              "specification": selected_catalogue["specification"], "cases": [], "mode": mode,
              "scope": selected_catalogue["scope"],
              "ai": "optional-local-advisory; never alters validator results"}
    from .workflow_engine import validate_many
    resources = {f"case-{i:03}-before": f for i, f in enumerate(files)}
    if corrections:
        resources.update({f"case-{i:03}-after": Path(corrections)/f.name for i, f in enumerate(files)
                          if (Path(corrections)/f.name).is_file()})
    reports = validate_many(resources, output/"engine", validator, java, cache_home, timeout, mode=mode)
    for index, source in enumerate(files):
        case = {"id": f"case-{index:03}", "name": source.name, "origin": "Eingabedatei; Freigabe oder synthetische Herkunft nicht automatisch festgestellt"}
        directory = output/case["id"]
        directory.mkdir()
        try:
            before = reports[case["id"]+"-before"]
            (directory/"before").mkdir()
            save(directory/"before"/"report.json", before)
            case.update(report=before, findings=explain_report(before, selected_catalogue))
            captured = output/"engine"/"inputs"/(case["id"]+"-before.json")
            if captured.exists():
                case["input"] = json.loads(captured.read_bytes())
            else:
                case["workflowError"] = before.get("executionError", "Input not available for this mode")
            case["evidence"] = f"{case['id']}/before/report.json"
            from .workflow_ai import advise
            case["aiAdvice"] = advise(case["findings"], ai_model)
            save(directory/"ai-advice.json", case["aiAdvice"])
            if corrections and (Path(corrections)/source.name).is_file():
                corrected = Path(corrections)/source.name
                after = reports[case["id"]+"-after"]
                (directory/"after").mkdir()
                save(directory/"after"/"report.json", after)
                new_data = json.loads((output/"engine"/"inputs"/(case["id"]+"-after.json")).read_bytes())
                case.update(after=after, afterFindings=explain_report(after, selected_catalogue), correctedInput=new_data,
                            comparison=compare(before, after, case["input"], new_data))
        except (OSError, ValueError) as error:
            case["workflowError"] = str(error)
            case.setdefault("report", {"status": "not-checkable", "coverage": "incomplete", "issues": []})
            case.setdefault("findings", [])
        result["cases"].append(case)
        write_dashboard(result, output)  # Preserve progress if a later file fails.
    return result


def write_dashboard(result, output):
    output = Path(output)
    result["summary"] = dict(Counter(c["report"]["status"] for c in result["cases"]))
    result["findingGroups"] = dict(Counter(f["explanation"]["category"] for c in result["cases"] for f in c.get("findings", []) if f["severity"] in ("error", "fatal")))
    save(output/"workflow.json", result)
    from .profiles import catalogue
    save(output/"requirements.json", catalogue(result.get("mode", "medication")))
    template = (Path(__file__).parent/"workflow.html").read_text(encoding="utf-8")
    # Escaping '<' prevents resource text from terminating the JSON script element.
    payload = json.dumps(result, ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    (output/"index.html").write_text(template.replace("__WORKFLOW_DATA__", payload), encoding="utf-8")
