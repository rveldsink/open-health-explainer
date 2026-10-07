"""One pinned Java process for a batch; outcomes are mapped by explicit file extension."""
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from .specification import SPEC, digest, load_spec


def validate_many(resources, output, validator, java="java", cache_home=None, timeout=480, mode="medication"):
    output = Path(output).resolve()
    validator = Path(validator).resolve()
    spec = load_spec()
    definitions = SPEC.resolve()/"definitions"
    if mode != "medication":
        from .profiles import catalogue, IMMUNIZATION
        spec = catalogue(mode)["specification"]
        definitions = IMMUNIZATION.resolve()/"definitions"
    resource_type = spec.get("resourceType", "MedicationRequest")
    if digest(validator) != spec["validatorSha256"]:
        raise ValueError("Pinned validator checksum mismatch")
    output.mkdir(parents=True, exist_ok=False)
    inputs = output/"inputs"
    inputs.mkdir()
    reports, expected = {}, {}
    for key, source in resources.items():
        if not key.replace("-", "").isalnum():
            raise ValueError("Invalid internal case key")
        r = {"status":"not-checkable", "coverage":"incomplete", "issues":[], "specification":spec,
             "startedAt":datetime.now(timezone.utc).isoformat()}
        reports[key] = r
        try:
            raw = Path(source).read_bytes()
            data = json.loads(raw)
            if not isinstance(data, dict) or data.get("resourceType") != resource_type:
                raise ValueError(f"One {resource_type} JSON resource expected for {mode} mode")
            target = inputs/(key+".json")
            target.write_bytes(raw)
            r["inputSha256"] = digest(target)
            expected[str(target.resolve()).casefold()] = key
        except (OSError, ValueError) as error:
            r["executionError"] = str(error)
    outcome = output/"operation-outcomes.json"
    command = [str(java), "-Xmx3g"]
    if cache_home:
        command += ["-Duser.home="+str(Path(cache_home).resolve())]
    command += ["-jar",str(validator),str(inputs),"-version",spec["fhir"],"-ig",str(definitions),
                "-profile",spec["profile"],"-tx","n/a","-allow-example-urls","true",
                "-disable-default-resource-fetcher","-output",str(outcome)]
    error, code = None, None
    if expected:
        with (output/"validator.log").open("w",encoding="utf-8") as log:
            try:
                code = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=timeout).returncode
            except (OSError, subprocess.TimeoutExpired) as exc:
                error = str(exc)
    try:
        if expected:
            data = json.loads(outcome.read_text(encoding="utf-8-sig"))
            entries = [data] if data.get("resourceType") == "OperationOutcome" else [e.get("resource", {}) for e in data.get("entry", [])] if data.get("resourceType") == "Bundle" else []
            mapped = {}
            for oo in entries:
                filenames = [e.get("valueString") for e in oo.get("extension", []) if e.get("url") == "http://hl7.org/fhir/StructureDefinition/operationoutcome-file"]
                if len(filenames) != 1 or not isinstance(filenames[0], str):
                    raise ValueError("Outcome has no unambiguous file attribution")
                key = expected.get(str(Path(filenames[0]).resolve()).casefold())
                if key is None or key in mapped:
                    raise ValueError("Unknown or duplicate outcome attribution")
                issues = oo.get("issue")
                if oo.get("resourceType") != "OperationOutcome" or not isinstance(issues,list) or not issues or any(not isinstance(i,dict) or i.get("severity") not in ("error","fatal","warning","information") for i in issues):
                    raise ValueError("Malformed OperationOutcome")
                mapped[key] = oo
            if code == 1 and mapped and not any(i["severity"] in ("error", "fatal") for oo in mapped.values() for i in oo["issue"]):
                raise ValueError("Validator exit code contradicts error-free outcomes")
            for key, oo in mapped.items():
                reports[key].update(rawOutcome=oo, issues=oo["issue"])
                if error is None and code in (0,1):
                    reports[key]["status"] = "failed" if any(i["severity"] in ("error","fatal") for i in oo["issue"]) else "no-errors-reported"
            for key in expected.values():
                if key not in mapped:
                    reports[key]["executionError"] = "Missing outcome for this file"
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        error = str(exc)
    for key, r in reports.items():
        r.update(command=command, processExitCode=code, executionMode="shared-java-process")
        if error:
            r.update(status="not-checkable", executionError=error)
        elif code not in (0,1) and key in expected.values():
            r["executionError"] = "Validator process did not complete normally"
    (output/"reports.json").write_text(json.dumps(reports, ensure_ascii=False, indent=2),encoding="utf-8")
    return reports
