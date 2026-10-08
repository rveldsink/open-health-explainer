"""Isolated, read-only synthetic R4 data. No patient file loading or persistence."""
from copy import deepcopy


class DemoStore:
    resource_type = "Patient"

    def __init__(self):
        self._resources = {
            "ohe-demo-1": {"resourceType": "Patient", "id": "ohe-demo-1", "active": True,
                           "name": [{"family": "SyntheticOne"}]},
            "ohe-demo-2": {"resourceType": "Patient", "id": "ohe-demo-2", "active": False,
                           "name": [{"family": "SyntheticTwo"}]},
        }

    def read(self, resource_id):
        return deepcopy(self._resources.get(resource_id))

    def search(self, ids=None):
        return [deepcopy(value) for key, value in sorted(self._resources.items())
                if ids is None or key in ids]
