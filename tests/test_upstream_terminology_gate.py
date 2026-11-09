"""Opt-in upstream tests for cache, language, expansion and package index fixes."""
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET
import pytest

CLASSES=['ValueSetValidatorOptionsTest','BaseWorkerContextTests',
         'TerminologyClientManagerFailureTest','ValueSetExpanderTests',
         'SQLiteINpmPackageIndexBuilderDBImplTest']

@pytest.mark.skipif(not os.environ.get('OHE_HL7_TERMINOLOGY_CHECKOUT'),
                    reason='Requires HL7 checkout and Maven; no Java results are implied')
def test_real_upstream_terminology_regressions(tmp_path):
    core=Path(os.environ['OHE_HL7_TERMINOLOGY_CHECKOUT']).resolve()
    mvn=shutil.which('mvn')
    assert mvn and (core/'pom.xml').exists()
    subprocess.run(['git','-C',str(core),'merge-base','--is-ancestor',
                    'ba7189b6aee43d4e2a1a083b6547e2d68a728ef6','HEAD'],check=True)
    # Require a disposable checkout: clean removes stale reports without touching source.
    with (tmp_path/'maven.log').open('w') as log:
        result=subprocess.run([mvn,'-B','-pl','org.hl7.fhir.r5,org.hl7.fhir.standalone,org.hl7.fhir.validation',
            '-am','clean','test','-Dtest='+','.join(CLASSES),
            '-Dsurefire.failIfNoSpecifiedTests=false','-DskipTests=false'],
            cwd=core,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
    assert result.returncode==0, f'See {tmp_path}/maven.log'
    for name in CLASSES:
        reports=list(core.glob('*/target/surefire-reports/TEST-*.'+name+'.xml'))
        assert reports, 'Missing upstream test report: '+name
        for report in reports:
            root=ET.parse(report).getroot()
            assert int(root.attrib['tests'])>0
            assert all(int(root.attrib.get(k,0))==0 for k in ('errors','failures','skipped'))
