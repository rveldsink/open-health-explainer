"""Version-pinned MedicationRequest profile validation, not full IG conformance."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

SPEC = Path(__file__).parent / 'specs' / 'medication-1.0.7'

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load_spec():
    manifest = json.loads((SPEC / 'manifest.json').read_text(encoding='utf-8'))
    expected = {item['file'] for item in manifest['files']}
    if {p.name for p in (SPEC/'definitions').iterdir()} != expected:
        raise ValueError('Unexpected or missing official definition files')
    for item in manifest['files']:
        if digest(SPEC / 'definitions' / item['file']) != item['sha256']:
            raise ValueError('Official definition checksum mismatch: ' + item['file'])
    return manifest

def requirements():
    """Machine-readable profile statements, with exact provenance, not a prose inventory."""
    spec = load_spec()
    rows = []
    for item in spec['files']:
        definition = json.loads((SPEC/'definitions'/item['file']).read_text(encoding='utf-8'))
        for i, element in enumerate(definition.get('differential', {}).get('element', [])):
            for field in ('min', 'max', 'type', 'binding', 'constraint', 'mustSupport', 'fixedCode', 'patternCodeableConcept'):
                if field in element:
                    rows.append({'profile':item['url'], 'version':item['version'], 'element':element['id'],
                                 'pointer':f'/differential/element/{i}/{field}', 'kind':field,
                                 'value':element[field], 'file':item['file'], 'sha256':item['sha256'],
                                 'method':'manual-capability-review' if field=='mustSupport' else 'delegated-to-hl7-validator'})
    return {'specification':spec, 'scope':'Selected differential statements; inherited rules remain in official definitions. Not an exhaustive inventory of narrative requirements.', 'requirements':rows}

def validate(resource, validator, output, java='java', cache_home=None, timeout=180):
    spec = load_spec()
    resource, validator, output = Path(resource).resolve(), Path(validator).resolve(), Path(output).resolve()
    if digest(validator) != spec['validatorSha256']:
        raise ValueError('Expected the pinned HL7 Java Validator 6.10.4 JAR; checksum differs')
    raw = resource.read_bytes()
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get('resourceType') != 'MedicationRequest':
        raise ValueError('This specification command accepts one MedicationRequest JSON resource')
    output.mkdir(parents=True, exist_ok=False)  # Never replace evidence from a previous run.
    (output/'input.json').write_bytes(raw)
    outcome = output/'operation-outcome.json'
    command = [java, '-Xmx3g']
    if cache_home:
        command += ['-Duser.home='+str(Path(cache_home).resolve())]
    command += ['-jar',str(validator),str(output/'input.json'),'-version',spec['fhir'],
                '-ig',str(SPEC.resolve()/'definitions'),'-profile',spec['profile'],
                '-tx','n/a','-allow-example-urls','true','-disable-default-resource-fetcher',
                '-output',str(outcome)]
    report = {'startedAt':datetime.now(timezone.utc).isoformat(), 'specification':spec,
              'inputSha256':hashlib.sha256(raw).hexdigest(), 'command':command,
              'coverage':'incomplete', 'status':'not-checkable', 'issues':[]}
    with (output/'validator.log').open('w',encoding='utf-8') as log:
        try:
            report['processExitCode'] = subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=timeout).returncode
        except (OSError, subprocess.TimeoutExpired) as error:
            report['executionError'] = str(error)
    if outcome.exists():
        try:
            oo = json.loads(outcome.read_text(encoding='utf-8-sig'))
            if not isinstance(oo, dict) or oo.get('resourceType') != 'OperationOutcome' or not isinstance(oo.get('issue'),list) or not oo['issue']:
                raise ValueError('Missing or invalid OperationOutcome issues')
            if any(not isinstance(i, dict) or i.get('severity') not in ('fatal','error','warning','information') for i in oo['issue']):
                raise ValueError('Malformed OperationOutcome issue')
            report['issues'] = oo['issue']
            report['rawOutcome'] = oo
            if 'executionError' not in report:
                if any(i.get('severity') in ('error','fatal') for i in oo['issue']):
                    report['status'] = 'failed'
                elif report.get('processExitCode') == 0:
                    report['status'] = 'no-errors-reported'
        except (ValueError,TypeError) as error:
            report['executionError'] = str(error)
    else:
        report.setdefault('executionError','Validator did not produce an OperationOutcome')
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'requirements.json').write_text(json.dumps(requirements(),ensure_ascii=False,indent=2),encoding='utf-8')
    return report
