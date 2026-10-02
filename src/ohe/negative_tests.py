from copy import deepcopy
from typing import Dict, Any, List, Tuple

def generate_negative_cases(resource: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    """
    v0.2 proof of concept.
    Later versions will derive mutations directly from StructureDefinition snapshots.
    """
    cases = []

    if "identifier" in resource:
        mutated = deepcopy(resource)
        mutated.pop("identifier", None)
        cases.append(("missing_identifier", mutated))

    if "active" in resource:
        mutated = deepcopy(resource)
        mutated["active"] = "definitely-not-a-boolean"
        cases.append(("wrong_active_type", mutated))

    if "birthDate" in resource:
        mutated = deepcopy(resource)
        mutated["birthDate"] = "23-11-1965"
        cases.append(("invalid_birthdate_format", mutated))

    return cases
