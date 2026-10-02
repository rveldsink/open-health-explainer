from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, Optional, Any


@dataclass
class ResourceEnvelope:
    source: str
    resource: Dict[str, Any]
    reference: Optional[str] = None


class ResourceSource:
    """Provider-neutral source abstraction."""

    name = "source"

    def iter_resources(self) -> Iterator[ResourceEnvelope]:
        raise NotImplementedError


class LocalFolderSource(ResourceSource):
    name = "local-folder"

    def __init__(self, path: str):
        self.path = Path(path)

    def iter_resources(self) -> Iterator[ResourceEnvelope]:
        for file in sorted(self.path.rglob("*.json")):
            if not file.is_file() or file.name.startswith("_"):
                continue
            try:
                data = json.loads(file.read_text(encoding="utf-8-sig"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue

            if isinstance(data, dict) and data.get("resourceType") == "Bundle":
                for entry in data.get("entry", []):
                    resource = entry.get("resource")
                    if isinstance(resource, dict):
                        yield ResourceEnvelope(
                            source=self.name,
                            resource=resource,
                            reference=str(file),
                        )
            elif isinstance(data, dict) and data.get("resourceType"):
                yield ResourceEnvelope(
                    source=self.name,
                    resource=data,
                    reference=str(file),
                )


class FhirRestSource(ResourceSource):
    """
    Minimal read-only FHIR REST connector.

    v0.4 intentionally supports unauthenticated endpoints only.
    Authentication/TLS/client-certificate handling belongs in a later secure adapter layer.
    """

    name = "fhir-rest"

    def __init__(self, base_url: str, resource_type: str = "Patient", page_size: int = 100):
        self.base_url = base_url.rstrip("/")
        self.resource_type = resource_type
        self.page_size = page_size

    def _first_url(self) -> str:
        query = urllib.parse.urlencode({"_count": self.page_size})
        return f"{self.base_url}/{self.resource_type}?{query}"

    @staticmethod
    def _next_link(bundle: Dict[str, Any]) -> Optional[str]:
        for link in bundle.get("link", []):
            if link.get("relation") == "next":
                return link.get("url")
        return None

    @staticmethod
    def _fetch_json(url: str) -> Dict[str, Any]:
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/fhir+json, application/json",
                "User-Agent": "OpenHealthExplainer/0.4",
            },
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)

    def iter_resources(self) -> Iterator[ResourceEnvelope]:
        url: Optional[str] = self._first_url()
        while url:
            bundle = self._fetch_json(url)
            if bundle.get("resourceType") != "Bundle":
                raise ValueError("FHIR endpoint did not return a Bundle")

            for entry in bundle.get("entry", []):
                resource = entry.get("resource")
                if isinstance(resource, dict):
                    yield ResourceEnvelope(
                        source=self.name,
                        resource=resource,
                        reference=entry.get("fullUrl"),
                    )

            url = self._next_link(bundle)


def summarize_source(source: ResourceSource, limit: Optional[int] = None) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    total = 0
    examples = []

    for envelope in source.iter_resources():
        resource_type = envelope.resource.get("resourceType", "Unknown")
        counts[resource_type] = counts.get(resource_type, 0) + 1
        total += 1

        if len(examples) < 5:
            examples.append({
                "resourceType": resource_type,
                "id": envelope.resource.get("id"),
                "reference": envelope.reference,
            })

        if limit is not None and total >= limit:
            break

    return {
        "source": source.name,
        "resourceCount": total,
        "resourceTypes": counts,
        "examples": examples,
    }
