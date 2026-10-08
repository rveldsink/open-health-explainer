"""Conservative negative-test candidates from complete StructureDefinition snapshots.

Only direct, unsliced fields are supported. These are candidate mutations, not a
claim that the baseline is valid or that only a single validator error will occur.
"""
from copy import deepcopy
import re


def _finite_codes(value_set):
    """Accept only explicit finite compose lists; never guess terminology membership."""
    if not isinstance(value_set, dict) or value_set.get("resourceType") != "ValueSet":
        return None
    compose = value_set.get("compose", {})
    if not isinstance(compose, dict) or compose.get("exclude") or not compose.get("include"):
        return None
    codes = set()
    for part in compose["include"]:
        if not isinstance(part, dict) or part.get("filter") or part.get("valueSet") or not part.get("concept"):
            return None
        for concept in part["concept"]:
            if not isinstance(concept, dict) or not isinstance(concept.get("code"), str):
                return None
            codes.add(concept["code"])
    return codes or None


def generate_profile_cases(resource, profile, value_sets=None):
    if not isinstance(profile, dict) or profile.get("resourceType") != "StructureDefinition":
        raise ValueError("Expected a StructureDefinition")
    if not isinstance(resource, dict) or resource.get("resourceType") != profile.get("type"):
        raise ValueError("Resource type does not match profile.type")
    elements = profile.get("snapshot", {}).get("element")
    if not isinstance(elements, list) or not elements:
        raise ValueError("A resolved snapshot is required; differential inheritance is not inferred")
    cases, skipped = [], []
    value_sets = value_sets or {}
    root = profile["type"]

    def skip(element, rule, reason):
        skipped.append({"element": element.get("id", element.get("path")), "rule": rule, "reason": reason})

    def add(element, field, rule, value=None, remove=False):
        changed = deepcopy(resource)
        if remove:
            changed.pop(field, None)
        else:
            changed[field] = value
        # Primitive extension-only values also count; remove them with the value.
        changed.pop("_" + field, None)
        cases.append({"name": f"{len(cases)+1:03d}-{field}-{rule}", "rule": rule,
                      "element": element.get("id", element["path"]),
                      "profile": profile.get("url"), "profileVersion": profile.get("version"),
                      "resource": changed, "status": "candidate-requires-validation"})

    for element in elements:
        if not isinstance(element, dict):
            raise ValueError("Snapshot elements must be objects")
        rules = [k for k in element if k in ("min", "max", "binding", "constraint", "slicing") or k.startswith(("fixed", "pattern"))]
        path = element.get("path", "")
        parts = path.split(".")
        if path == root:
            continue
        if (len(parts) != 2 or parts[0] != root or "[" in path or ":" in element.get("id", "")
                or element.get("sliceName") or element.get("slicing")):
            for rule in rules:
                skip(element, rule, "Only direct unsliced, non-choice fields are supported")
            continue
        field = parts[1]
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", field):
            raise ValueError("Invalid FHIR element name")
        if element.get("min", 0) > 0:
            if field in resource or "_" + field in resource:
                add(element, field, "min", remove=True)
            else:
                skip(element, "min", "Baseline already omits this mandatory field")
        maximum = element.get("max", "*")
        if maximum != "*":
            if not isinstance(maximum, str) or not maximum.isdigit():
                raise ValueError("Invalid snapshot max cardinality")
            count = int(maximum)
            current = resource.get(field)
            if isinstance(current, list) and current and 1 <= count <= 100:
                add(element, field, "max", [deepcopy(current[0]) for _ in range(count + 1)])
            else:
                skip(element, "max", "Requires a nonempty repeating field and maximum between 1 and 100")
        for key in (k for k in element if k.startswith("fixed")):
            fixed = element[key]
            if field not in resource or resource[field] != fixed:
                skip(element, key, "Baseline must contain the fixed value")
            elif key == "fixedBoolean" and isinstance(fixed, bool):
                add(element, field, key, not fixed)
            elif key in ("fixedCode", "fixedString") and isinstance(fixed, str):
                add(element, field, key, fixed + "-ohe-invalid")
            else:
                skip(element, key, "Only fixedBoolean, fixedCode and fixedString are supported")
        binding = element.get("binding", {})
        if binding.get("strength") == "required":
            canonical = binding.get("valueSet")
            codes = _finite_codes(value_sets.get(canonical))
            definition = value_sets.get(canonical, {})
            resolved = definition.get("url")
            if "|" in (canonical or ""):
                resolved = str(resolved) + "|" + str(definition.get("version"))
            if (element.get("type") != [{"code": "code"}] or codes is None
                    or resolved != canonical or resource.get(field) not in codes):
                skip(element, "binding", "Requires a matching finite explicit ValueSet and a valid scalar code baseline")
            else:
                invalid = "ohe-invalid-code"
                while invalid in codes:
                    invalid += "-x"
                add(element, field, "binding", invalid)
        elif binding:
            skip(element, "binding", "Only required bindings generate invalid candidates")
        for key in (k for k in element if k == "constraint" or k.startswith("pattern")):
            skip(element, key, "Pattern and FHIRPath constraint mutation is not implemented")
    return {"profile": profile.get("url"), "fhirVersion": profile.get("fhirVersion"),
            "cases": cases, "skipped": skipped,
            "coverage": "partial", "baselineValidated": False}
