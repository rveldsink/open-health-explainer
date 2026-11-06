"""Pinned upstream golden outcomes; opt-in real Java validation is separate."""
import json
import os
from pathlib import Path
import subprocess

import pytest
from ohe.cli import analyze_operation_outcome
from ohe.explainer import explain_issue
from ohe.validator_runner import parse_operation_outcome_json

FIXTURES = Path(__file__).parent/'fixtures/snapshot-7.0.5'
OUTCOMES = sorted((FIXTURES/'outcomes/java').glob('*.json'))


@pytest.mark.parametrize('path', OUTCOMES, ids=lambda p: p.stem)
def test_upstream_outcome_preserved_and_explained(path):
    raw = json.loads(path.read_text())
    parsed = parse_operation_outcome_json(path.read_text())
    report = analyze_operation_outcome(str(path))
    assert parsed['rawOutcome'] == raw
    assert report['rawOutcome'] == raw
    assert report['issueCount'] == len(raw.get('issue', []))
    has_errors = any(i['severity'] in ('error', 'fatal') for i in raw.get('issue', []))
    assert report['reportedResult'] == ('errors-reported' if has_errors else 'no-errors-reported')
    assert report['validationCoverage'] != 'complete'
    for normalized, explained, original in zip(parsed['issues'], report['issues'], raw.get('issue', [])):
        assert normalized['diagnostics'] == original.get('diagnostics')
        assert explained['rawMessage'] == original['details']['text']
        assert explained['rawIssue'] == original
        assert explained['severity'] == original['severity']
        assert explained['validatorCode'] == original['code']
        assert explained['expression'] == original.get('expression', [])
        if 'minimum required' in original['details']['text']:
            assert explained['errorId'] == 'OHE-CARD-001'


@pytest.mark.parametrize('details', [None, '', '   '])
def test_diagnostics_fallback(details):
    result = explain_issue({'details': details, 'diagnostics': 'Patient.active: minimum required = 1'})
    assert result['errorId'] == 'OHE-CARD-001'
    assert result['diagnostics'] == 'Patient.active: minimum required = 1'


def test_readable_details_win_and_diagnostics_survive():
    issue = {'details': 'Patient.active: minimum required = 1', 'diagnostics': '[8,6]'}
    result = explain_issue(issue)
    assert result['errorId'] == 'OHE-CARD-001'
    assert result['rawMessage'] == issue['details']
    assert result['diagnostics'] == '[8,6]'


@pytest.mark.skipif(not os.environ.get('OHE_SNAPSHOT_VALIDATOR_JAR'),
                    reason='Set OHE_SNAPSHOT_VALIDATOR_JAR for actual Java snapshot validation')
@pytest.mark.parametrize('expected_path', OUTCOMES, ids=lambda p: p.stem)
def test_real_snapshot_validation(tmp_path, expected_path):
    case = expected_path.name.removeprefix('R4.').removesuffix('-base.json')
    output = tmp_path/'outcome.json'
    jar = Path(os.environ['OHE_SNAPSHOT_VALIDATOR_JAR']).resolve()
    assert jar.is_file()
    command = ['java', '-jar', str(jar), str(FIXTURES/(case+'.json')),
               '-version', '4.0.1', '-tx', 'n/a', '-allow-example-urls', 'true',
               '-output', str(output)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=240)
    (tmp_path/'validator.log').write_text(result.stdout+'\n'+result.stderr)
    assert '7.0.5' in result.stdout, 'Expected 7.0.5 snapshot; inspect validator.log'
    assert result.returncode in (0, 1), 'Unexpected process failure; inspect validator.log'
    assert output.is_file(), 'Validator produced no OperationOutcome'
    actual = parse_operation_outcome_json(output.read_text())['rawOutcome']
    expected = json.loads(expected_path.read_text())
    def fingerprint(i):
        return (i['severity'], i['code'], (i.get('details') or {}).get('text'), tuple(i.get('expression', [])))
    actual_issues = actual.get('issue', [])
    # Ignore extra informational/best-practice warnings, but never unexpected errors.
    for issue in expected.get('issue', []):
        assert fingerprint(issue) in [fingerprint(i) for i in actual_issues]
    expected_errors = [fingerprint(i) for i in expected.get('issue', []) if i['severity'] in ('error', 'fatal')]
    assert [fingerprint(i) for i in actual_issues if i['severity'] in ('error', 'fatal')] == expected_errors
