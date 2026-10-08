from copy import deepcopy
import json
from pathlib import Path

import pytest

from ohe.profile_tests import generate_profile_cases


def fixtures():
    resource = {"resourceType":"Patient", "active":True, "gender":"female", "name":[{"family":"Synthetic"}]}
    profile = {"resourceType":"StructureDefinition", "type":"Patient", "url":"https://example.org/profile",
               "version":"1.0.0", "fhirVersion":"4.0.1", "snapshot":{"element":[
        {"id":"Patient.active", "path":"Patient.active", "min":1, "fixedBoolean":True},
        {"id":"Patient.name", "path":"Patient.name", "max":"1"},
        {"id":"Patient.gender", "path":"Patient.gender", "type":[{"code":"code"}],
         "binding":{"strength":"required", "valueSet":"https://example.org/gender|1.0.0"}},
    ]}}
    vs = {"resourceType":"ValueSet", "url":"https://example.org/gender", "version":"1.0.0",
          "compose":{"include":[{"system":"https://example.org/codes", "concept":[{"code":"female"}, {"code":"male"}]}]}}
    return resource, profile, {"https://example.org/gender|1.0.0":vs}


def test_profile_rules_generate_deterministic_candidates():
    args = fixtures()
    before = deepcopy(args)
    result = generate_profile_cases(*args)
    assert args == before
    assert result == generate_profile_cases(*args)
    cases = {case["rule"]:case for case in result["cases"]}
    assert set(cases) == {"min", "max", "fixedBoolean", "binding"}
    assert "active" not in cases["min"]["resource"]
    assert cases["fixedBoolean"]["resource"]["active"] is False
    assert len(cases["max"]["resource"]["name"]) == 2
    assert cases["binding"]["resource"]["gender"] not in ("female", "male")
    assert all(c["profileVersion"] == "1.0.0" for c in cases.values())
    assert result["baselineValidated"] is False


@pytest.mark.parametrize("change", ["nested", "slice", "choice", "filter", "exclude", "missing-vs", "wrong-version", "bad-baseline"])
def test_unsupported_rules_are_explicit(change):
    resource, profile, values = fixtures()
    element = profile["snapshot"]["element"][-1]
    if change in ("nested", "slice", "choice"):
        element["path"] = {"nested":"Patient.contact.gender", "slice":"Patient.gender", "choice":"Patient.deceased[x]"}[change]
        element["id"] = "Patient.gender:a" if change == "slice" else element["path"]
    elif change == "filter":
        next(iter(values.values()))["compose"]["include"][0]["filter"] = [{"property":"x"}]
    elif change == "exclude":
        next(iter(values.values()))["compose"]["exclude"] = [{"system":"x"}]
    elif change == "missing-vs":
        values = {}
    elif change == "wrong-version":
        next(iter(values.values()))["version"] = "2.0.0"
    else:
        resource["gender"] = "already-invalid"
    result = generate_profile_cases(resource, profile, values)
    assert not any(c["rule"] == "binding" for c in result["cases"])
    assert any(s["rule"] == "binding" for s in result["skipped"])


def test_primitive_extensions_removed_and_differential_rejected():
    resource, profile, values = fixtures()
    resource["_active"] = {"extension":[{"url":"https://example.org/reason","valueString":"demo"}]}
    minimum = next(c for c in generate_profile_cases(resource, profile, values)["cases"] if c["rule"] == "min")
    assert "_active" not in minimum["resource"]
    profile["differential"] = profile.pop("snapshot")
    with pytest.raises(ValueError, match="snapshot"):
        generate_profile_cases(resource, profile)


def test_official_immunization_snapshot():
    root = Path(__file__).resolve().parents[1]
    profile = json.loads((root / "src/ohe/specs/immunization-r4/definitions/StructureDefinition-ImmunizationRecommendation.json").read_text())
    resource = json.loads((root / "examples/immunization-r4/00-reference.json").read_text())
    result = generate_profile_cases(resource, profile)
    removed = {c["element"] for c in result["cases"] if c["rule"] == "min"}
    assert {"ImmunizationRecommendation.patient", "ImmunizationRecommendation.date", "ImmunizationRecommendation.recommendation"} <= removed
    assert result["skipped"]  # Nested rules are not silently claimed as implemented.
