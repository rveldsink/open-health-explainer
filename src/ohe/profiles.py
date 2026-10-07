"""Explicit, version-pinned workflow modes; no clinical forecasting."""
import json
from pathlib import Path
from .specification import digest, requirements

IMMUNIZATION = Path(__file__).parent/'specs'/'immunization-r4'


def catalogue(mode='medication'):
    if mode == 'medication':
        result = requirements()
        result['specification'].update(resourceType='MedicationRequest', label='Medication IG DE 1.0.7')
        return result
    if mode != 'immunization':
        raise ValueError('Unsupported workflow specification')
    manifest = json.loads((IMMUNIZATION/'manifest.json').read_text(encoding='utf-8'))
    item = manifest['files'][0]
    path = IMMUNIZATION/'definitions'/item['file']
    if digest(path) != item['sha256']:
        raise ValueError('Immunization definition checksum mismatch')
    definition = json.loads(path.read_bytes())
    rows = []
    for i, element in enumerate(definition['snapshot']['element']):
        for kind in ('min','max','type','binding','constraint'):
            if kind in element:
                rows.append({'profile':definition['url'], 'version':definition['version'],
                    'element':element['id'], 'pointer':f'/snapshot/element/{i}/{kind}',
                    'kind':kind, 'value':element[kind], 'file':item['file'],
                    'sha256':item['sha256'], 'method':'delegated-to-hl7-validator'})
    return {'specification':manifest, 'requirements':rows,
        'scope':'FHIR R4 base structure only. No national vaccination schedules or clinical recommendation logic; terminology coverage incomplete.'}
