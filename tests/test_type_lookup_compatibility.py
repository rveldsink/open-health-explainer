"""OHE boundary checks; the OperationOutcomes below are synthetic test inputs."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

import pytest
from ohe.cli import analyze_operation_outcome
from ohe.validator_runner import parse_operation_outcome_json


@pytest.mark.parametrize('severity', ['error', 'fatal'])
@pytest.mark.parametrize('message_field', ['details', 'diagnostics'])
def test_unresolved_type_never_reported_as_success(tmp_path, severity, message_field):
    message = 'Unable to resolve resource type OheLookup'
    issue = {'severity': severity, 'code': 'structure',
             'expression': ['OheLookup'], 'location': ['line 1, column 1']}
    issue[message_field] = {'text': message} if message_field == 'details' else message
    outcome = {'resourceType': 'OperationOutcome', 'issue': [issue]}
    path = tmp_path/'outcome.json'
    path.write_text(json.dumps(outcome), encoding='utf-8')
    parsed = parse_operation_outcome_json(path.read_text())
    assert parsed['issues'][0]['rawIssue'] == issue
    report = analyze_operation_outcome(str(path))
    assert report['reportedResult'] == 'errors-reported'
    assert report['validationCoverage'] != 'complete'
    assert report['issues'][0]['severity'] == severity
    assert report['issues'][0]['expression'] == ['OheLookup']
    assert report['rawOutcome'] == outcome


def test_resolved_type_does_not_claim_complete_coverage(tmp_path):
    path = tmp_path/'outcome.json'
    path.write_text(json.dumps({'resourceType': 'OperationOutcome', 'issue': [
        {'severity': 'information', 'code': 'informational', 'details': {'text': 'All OK'}}
    ]}), encoding='utf-8')
    report = analyze_operation_outcome(str(path))
    assert report['reportedResult'] == 'no-errors-reported'
    assert report['validationCoverage'] != 'complete'


@pytest.mark.skipif(not os.environ.get('OHE_HL7_CORE_CHECKOUT'),
                    reason='Set OHE_HL7_CORE_CHECKOUT for real HL7 Java resolver tests')
def test_real_hl7_specialization_lookup(tmp_path):
    core = Path(os.environ['OHE_HL7_CORE_CHECKOUT']).resolve()
    assert (core/'pom.xml').is_file(), 'Expected org.hl7.fhir.core source checkout'
    mvn = shutil.which('mvn')
    assert mvn, 'Maven required when integration test explicitly enabled'
    # Verify ancestry, so a released 7.0.4 checkout cannot accidentally pass this gate.
    subprocess.run(['git', '-C', str(core), 'merge-base', '--is-ancestor',
                    '428bcd5604c539a65bb949d783aea12c4b988ed9', 'HEAD'], check=True)
    source = Path(__file__).parent/'compatibility/TypeLookupRegressionTest.java'
    module = core/'org.hl7.fhir.standalone'
    target = module/'src/test/java/org/hl7/fhir/services/elementmodel/TypeLookupRegressionTest.java'
    report = module/'target/surefire-reports/TEST-org.hl7.fhir.services.elementmodel.TypeLookupRegressionTest.xml'
    # Never consume an earlier successful run's report.
    report.unlink(missing_ok=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x', encoding='utf-8') as stream:
        stream.write(source.read_text(encoding='utf-8'))
    try:
        with (tmp_path/'maven.log').open('w') as log:
            result = subprocess.run([mvn, '-B', '-pl', 'org.hl7.fhir.standalone', '-am',
                'test', '-Dtest=TypeLookupRegressionTest',
                '-Dsurefire.failIfNoSpecifiedTests=false', '-DskipTests=false'],
                cwd=core, stdout=log, stderr=subprocess.STDOUT, timeout=1800)
        assert result.returncode == 0, f'Maven failed; see {tmp_path}/maven.log'
        root = ET.parse(report).getroot()
        assert int(root.attrib['tests']) == 3
        assert all(int(root.attrib.get(k, 0)) == 0 for k in ('failures', 'errors', 'skipped'))
    finally:
        target.unlink()
