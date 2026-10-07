import json
from pathlib import Path
from types import SimpleNamespace
from ohe.profiles import catalogue
from ohe import workflow_engine as engine
from ohe.workflow import explain_report, run_batch


def test_official_imr_rule_has_exact_provenance():
    c=catalogue('immunization')
    assert c['specification']['resourceType']=='ImmunizationRecommendation'
    rows=[r for r in c['requirements'] if r['kind']=='constraint' and any(i['key']=='imr-1' for i in r['value'])]
    assert rows and rows[0]['pointer'].startswith('/snapshot/element/')
    issue={'severity':'error','code':'invariant','details':{'text':'rule'},'extension':[{
        'url':'http://hl7.org/fhir/StructureDefinition/operationoutcome-message-id',
        'valueCode':'http://hl7.org/fhir/StructureDefinition/ImmunizationRecommendation#imr-1'}]}
    f=explain_report({'rawOutcome':{'resourceType':'OperationOutcome','issue':[issue]}},c)
    assert f[0]['ruleEvidence'][0]['key']=='imr-1'


def test_mode_rejects_wrong_resource_and_exit_zero_does_not_hide_errors(tmp_path,monkeypatch):
    jar=tmp_path/'fake.jar';jar.write_bytes(b'test-only')
    from ohe import profiles
    real=profiles.catalogue
    def patched(mode):
        c=real(mode);c['specification']['validatorSha256']=engine.digest(jar);return c
    monkeypatch.setattr(profiles,'catalogue',patched)
    def fake(cmd,**kwargs):
        assert 'ImmunizationRecommendation|4.0.1' in cmd[cmd.index('-profile')+1]
        folder=Path(cmd[cmd.index('-jar')+2]);entries=[]
        for p in folder.glob('*.json'):
            entries.append({'resource':{'resourceType':'OperationOutcome','extension':[{
                'url':'http://hl7.org/fhir/StructureDefinition/operationoutcome-file','valueString':str(p)}],
                'issue':[{'severity':'error','code':'required','details':{'text':'test-double'}}]}})
        Path(cmd[-1]).write_text(json.dumps({'resourceType':'Bundle','entry':entries}))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(engine.subprocess,'run',fake)
    inputs=tmp_path/'inputs';inputs.mkdir()
    (inputs/'a.json').write_text('{"resourceType":"ImmunizationRecommendation"}')
    (inputs/'b.json').write_text('{"resourceType":"MedicationRequest"}')
    result=run_batch(inputs,tmp_path/'out',jar,mode='immunization')
    assert result['cases'][0]['report']['status']=='failed'
    assert result['cases'][1]['report']['status']=='not-checkable'
    assert 'ImmunizationRecommendation' in result['cases'][1]['report']['executionError']
    saved=json.loads((tmp_path/'out/requirements.json').read_text())
    assert saved['specification']['resourceType']=='ImmunizationRecommendation'
