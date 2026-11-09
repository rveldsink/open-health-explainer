import json
from pathlib import Path
import pytest
from ohe.cli import analyze_operation_outcome
from ohe.batch import cluster_reports

FIXTURES=Path(__file__).parent/'fixtures/snapshot-7.0.6/outcomes/java'

@pytest.mark.parametrize('path', sorted(FIXTURES.glob('*.json')), ids=lambda p:p.stem)
def test_empty_primitive_array_outcomes(path):
    report=analyze_operation_outcome(str(path))
    assert report['reportedResult']=='errors-reported'
    assert report['issueCount']==1
    issue=report['issues'][0]
    assert issue['severity']=='error'
    assert issue['validatorCode']=='invalid'
    assert issue['expression']==['Patient.name[0].given']
    assert 'Array cannot be empty' in issue['rawMessage']
    assert issue['diagnostics']

@pytest.mark.parametrize('code', ['timeout','transient'])
@pytest.mark.parametrize('severity', ['warning','error'])
def test_infrastructure_failure_is_not_a_binding_failure(tmp_path, code, severity):
    p=tmp_path/'oo.json'
    # Deliberately includes binding-like text: structured infrastructure code wins.
    p.write_text(json.dumps({'resourceType':'OperationOutcome','issue':[{
      'code':code,'severity':severity,'details':{'text':'Value not in value set; server unavailable'},
      'diagnostics':'HTTP 503','expression':['Observation.code']}]}))
    report=analyze_operation_outcome(str(p))
    assert report['validationCoverage']=='incomplete'
    assert report['issues'][0]['category']=='infrastructure'
    assert report['issues'][0]['severity']==severity
    assert report['reportedResult']==('errors-reported' if severity=='error' else 'no-errors-reported')

def test_distinct_unclassified_validator_messages_are_not_merged():
    reports=[{'source':'a.json','issues':[{'rawMessage':'Lookup A failed'}]},
             {'source':'b.json','issues':[{'rawMessage':'Lookup B failed'}]},
             {'source':'c.json','issues':[{'rawMessage':'Lookup A failed'}]}]
    clusters=cluster_reports(reports)
    assert len(clusters)==2
    assert clusters[0]['occurrences']==2
    assert clusters[0]['exampleFiles']==['a.json','c.json']
    assert clusters[0]['message']=='Lookup A failed'
