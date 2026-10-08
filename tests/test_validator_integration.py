"""Opt-in real Java tests; package downloads may occur if the cache is empty.

OHE_VALIDATOR_JAR=/path/validator_cli.jar OHE_VALIDATOR_CACHE=/path/cache-home \
    python -m pytest -m integration -q
"""
import json
import os
from pathlib import Path

import pytest

from ohe.demo_server import DemoApplication
from ohe.validation import validate_pinned


@pytest.mark.integration
@pytest.mark.parametrize("resource_type", ["Patient", "CapabilityStatement"])
def test_demo_resources_with_official_validator(tmp_path, resource_type):
    jar = os.environ.get("OHE_VALIDATOR_JAR")
    if not jar:
        pytest.skip("Set OHE_VALIDATOR_JAR to the pinned 6.10.4 JAR for real integration")
    app = DemoApplication()
    resource = app.store.read("ohe-demo-1") if resource_type == "Patient" else app.capability_statement()
    source = tmp_path / "resource.json"
    source.write_text(json.dumps(resource), encoding="utf-8")
    settings = json.loads((Path(__file__).parents[1] / "examples/validation/r4.json").read_text())
    settings["profiles"] = ["http://hl7.org/fhir/StructureDefinition/" + resource_type + "|4.0.1"]
    config = tmp_path / "config.json"
    config.write_text(json.dumps(settings))
    output = tmp_path / "evidence"
    report = validate_pinned(source, jar, config, output, timeout=240,
                             cache_home=os.environ.get("OHE_VALIDATOR_CACHE"))
    assert report["status"] == "no-errors-reported", (report, (output / "validator.log").read_text()[-4000:])
    assert report["coverage"] == "incomplete"
