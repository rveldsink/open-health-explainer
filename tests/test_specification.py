from pathlib import Path
import json
import shutil
import subprocess
from types import SimpleNamespace
import pytest
from ohe import specification as spec


def test_official_definitions_and_rule_provenance():
    catalog = spec.requirements()
    assert catalog['specification']['package'] == 'de.fhir.medication#1.0.7'
    assert catalog['requirements']
    for row in catalog['requirements']:
        definition = json.loads((spec.SPEC/'definitions'/row['file']).read_text(encoding='utf-8'))
        _, _, _, index, field = row['pointer'].split('/')
        assert definition['differential']['element'][int(index)][field] == row['value']


@pytest.mark.parametrize('mutation', ['modify', 'extra', 'missing'])
def test_definition_integrity(tmp_path, monkeypatch, mutation):
    shutil.copytree(spec.SPEC, tmp_path/'spec')
    monkeypatch.setattr(spec, 'SPEC', tmp_path/'spec')
    target = next((spec.SPEC/'definitions').iterdir())
    if mutation == 'modify':
        target.write_text('{}')
    elif mutation == 'missing':
        target.unlink()
    else:
        (spec.SPEC/'definitions'/'extra.json').write_text('{}')
    with pytest.raises(ValueError):
        spec.load_spec()


@pytest.mark.parametrize('issues,exit_code,expected', [
    ([{'severity':'information'}], 0, 'no-errors-reported'),
    ([{'severity':'error'}], 1, 'failed'),
    ([{'severity':'information'}], 1, 'not-checkable'),
    ([], 0, 'not-checkable'),
    (['bad'], 0, 'not-checkable'),
])
def test_outcome_never_implies_complete_coverage(tmp_path, monkeypatch, issues, exit_code, expected):
    jar = tmp_path/'validator.jar'
    jar.write_bytes(b'test double, not real validator')
    manifest = spec.load_spec()
    manifest['validatorSha256'] = spec.digest(jar)
    monkeypatch.setattr(spec, 'load_spec', lambda: manifest)
    resource = tmp_path/'input.json'
    resource.write_text('{"resourceType":"MedicationRequest"}')
    def fake_run(command, **kwargs):
        Path(command[-1]).write_text(json.dumps({'resourceType':'OperationOutcome','issue':issues}))
        return SimpleNamespace(returncode=exit_code)
    monkeypatch.setattr(spec.subprocess, 'run', fake_run)
    report = spec.validate(resource, jar, tmp_path/'evidence')
    assert report['status'] == expected
    assert report['coverage'] == 'incomplete'
    assert (tmp_path/'evidence'/'input.json').read_bytes() == resource.read_bytes()
    with pytest.raises(FileExistsError):
        spec.validate(resource, jar, tmp_path/'evidence')


def test_unpinned_engine_rejected(tmp_path):
    jar = tmp_path/'wrong.jar'
    jar.write_bytes(b'wrong version')
    with pytest.raises(ValueError, match='checksum'):
        spec.validate(tmp_path/'absent.json', jar, tmp_path/'output')
    assert not (tmp_path/'output').exists()


def test_catalog_cli_portable_json():
    import os
    import sys
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]/'src'))
    result = subprocess.run([sys.executable, '-m', 'ohe.cli', 'specification'], env=env, capture_output=True)
    assert result.returncode == 0
    assert json.loads(result.stdout)['requirements']
