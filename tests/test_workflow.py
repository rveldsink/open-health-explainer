import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from ohe import workflow as w
from ohe import workflow_engine as engine
from ohe.workflow_ai import validate_advice, advise


def setup_engine(tmp_path, monkeypatch, mode="normal"):
    jar = tmp_path/"test.jar"
    jar.write_bytes(b"unit-test-double")
    manifest = engine.load_spec()
    manifest["validatorSha256"] = engine.digest(jar)
    monkeypatch.setattr(engine, "load_spec", lambda: manifest)
    def fake(command, **kwargs):
        folder = Path(command[command.index("-jar")+2])
        entries = []
        for f in reversed(sorted(folder.glob("*.json"))):
            severity = "error" if "bad" in f.name else "information"
            entries.append({"resource":{"resourceType":"OperationOutcome", "extension":[{
                "url":"http://hl7.org/fhir/StructureDefinition/operationoutcome-file", "valueString":str(f)}],
                "issue":[{"severity":severity,"code":"invalid","details":{"text":"test"}}]}})
        if mode == "duplicate":
            entries.append(entries[0])
        elif mode == "missing":
            entries = entries[:1]
        Path(command[-1]).write_text(json.dumps({"resourceType":"Bundle","entry":entries}),encoding="utf-8")
        return SimpleNamespace(returncode=int(any(e["resource"]["issue"][0]["severity"]=="error" for e in entries)))
    monkeypatch.setattr(engine.subprocess,"run",fake)
    source = tmp_path/"source.json"
    source.write_text('{"resourceType":"MedicationRequest"}')
    return jar, source


def test_batch_matches_paths_not_order(tmp_path, monkeypatch):
    jar, source = setup_engine(tmp_path,monkeypatch)
    result = engine.validate_many({"good":source,"bad":source},tmp_path/"run",jar)
    assert result["good"]["status"] == "no-errors-reported"
    assert result["bad"]["status"] == "failed"
    assert all(r["coverage"] == "incomplete" for r in result.values())


@pytest.mark.parametrize("mode",["duplicate","missing"])
def test_ambiguous_or_missing_outcome_not_pass(tmp_path,monkeypatch,mode):
    jar, source = setup_engine(tmp_path,monkeypatch,mode)
    result = engine.validate_many({"good":source,"bad":source},tmp_path/"run",jar)
    assert result["bad"]["status"] == "not-checkable"


def test_batch_survives_invalid_input_and_revalidates(tmp_path,monkeypatch):
    jar, source = setup_engine(tmp_path,monkeypatch)
    inputs=tmp_path/"inputs"; inputs.mkdir()
    corrections=tmp_path/"corrections";corrections.mkdir()
    (inputs/"valid.json").write_bytes(source.read_bytes())
    (inputs/"broken.json").write_text("not-json")
    (corrections/"valid.json").write_bytes(source.read_bytes())
    result=w.run_batch(inputs,tmp_path/"report",jar,corrections=corrections)
    assert len(result["cases"]) == 2
    assert result["cases"][0]["report"]["status"] == "not-checkable"
    assert result["cases"][1]["comparison"]["comparable"]
    assert (tmp_path/"report/index.html").exists()
    with pytest.raises(FileExistsError):
        w.run_batch(inputs,tmp_path/"report",jar)


def test_html_escapes_untrusted_resource_text(tmp_path):
    result={"cases":[{"name":"</script><script>alert(1)</script>","report":{"status":"failed"}}]}
    w.write_dashboard(result,tmp_path)
    html=(tmp_path/"index.html").read_text(encoding="utf-8")
    assert "</script><script>alert(1)" not in html
    embedded=html.split('<script id="payload" type="application/json">')[1].split('</script>')[0]
    assert json.loads(embedded)["cases"] == result["cases"]


def test_ai_cannot_invent_references():
    findings=[{"id":"F001","ruleEvidence":[{"key":"rule-1"}]}]
    good={"findingId":"F001","hypothesis":"Vermutung", "action":"Prüfen", "ruleKeys":["rule-1"]}
    assert validate_advice({"suggestions":[good]},findings)
    with pytest.raises(ValueError):
        validate_advice({"suggestions":[dict(good,ruleKeys=["invented"])]},findings)
    with pytest.raises(ValueError):
        validate_advice({"suggestions":[dict(good,findingId="F999")]},findings)
    assert advise(findings)["status"] == "disabled"


def test_comparison_not_proof_when_execution_fails():
    result=w.compare({"status":"failed","issues":[{"severity":"error"}]},
                     {"status":"not-checkable","issues":[]},{},{})
    assert not result["comparable"]


def test_rule_attribution_uses_explicit_id_not_incidental_text():
    issue={"severity":"error","code":"invariant","details":{"text":"DosageStructuredOrFreeText"}}
    report={"rawOutcome":{"resourceType":"OperationOutcome","issue":[issue]}}
    assert not w.explain_report(report)[0]["ruleEvidence"]
    issue["extension"]=[{"url":"http://hl7.org/fhir/StructureDefinition/operationoutcome-message-id",
                          "valueCode":"http://ig.fhir.de/igs/medication/StructureDefinition/DosageDgMP#DosageStructuredOrFreeText"}]
    assert w.explain_report(report)[0]["ruleEvidence"][0]["key"] == "DosageStructuredOrFreeText"


def test_engine_failure_does_not_report_pass(tmp_path,monkeypatch):
    jar,source=setup_engine(tmp_path,monkeypatch)
    original=engine.subprocess.run
    def contradiction(*args,**kwargs):
        result=original(*args,**kwargs)
        return SimpleNamespace(returncode=1)
    monkeypatch.setattr(engine.subprocess,"run",contradiction)
    result=engine.validate_many({"good":source},tmp_path/"run",jar)
    assert result["good"]["status"] == "not-checkable"


def test_engine_timeout_keeps_evidence(tmp_path,monkeypatch):
    jar,source=setup_engine(tmp_path,monkeypatch)
    def timeout(*args,**kwargs):
        raise engine.subprocess.TimeoutExpired(args[0],1)
    monkeypatch.setattr(engine.subprocess,"run",timeout)
    result=engine.validate_many({"good":source},tmp_path/"run",jar)
    assert result["good"]["status"] == "not-checkable"
    assert (tmp_path/"run/inputs/good.json").read_bytes()==source.read_bytes()


def test_local_ai_transport_is_optional_and_advisory(monkeypatch):
    import io
    import urllib.request
    findings = [{"id":"F001", "ruleEvidence":[{"key":"rule-1"}]}]
    suggestion = {"findingId":"F001", "hypothesis":"Test hypothesis",
                  "action":"Review source", "ruleKeys":["rule-1"]}
    requests = []
    class Opener:
        def open(self, request, timeout):
            requests.append(request)
            assert request.full_url == "http://127.0.0.1:11434/api/chat"
            assert timeout == 120
            payload = json.loads(request.data)
            assert payload["model"] == "installed-local-model"
            assert json.loads(payload["messages"][1]["content"]) == findings
            return io.BytesIO(json.dumps({"message":{"content":json.dumps({"suggestions":[suggestion]})}}).encode())
    def build(*handlers):
        assert any(isinstance(h, urllib.request.ProxyHandler) and h.proxies == {} for h in handlers)
        redirect = next(h for h in handlers if isinstance(h, urllib.request.HTTPRedirectHandler))
        assert redirect.redirect_request(None) is None
        return Opener()
    monkeypatch.setattr(urllib.request, "build_opener", build)
    assert advise(findings)["status"] == "disabled"
    assert requests == []
    result = advise(findings, model="installed-local-model")
    assert result["status"] == "advisory-unverified"
    assert result["suggestions"] == [suggestion]
    assert len(requests) == 1
