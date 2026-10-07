import io
import json
import socket
import urllib.error
import urllib.request
from email.message import Message
from pathlib import Path

import pytest

from ohe.sources import FhirRestSource, LocalFolderSource, summarize_source


def test_local_folder_source_reads_resource_and_bundle(tmp_path: Path):
    (tmp_path / "patient.json").write_text(
        json.dumps({"resourceType": "Patient", "id": "p1"}),
        encoding="utf-8",
    )
    (tmp_path / "bundle.json").write_text(
        json.dumps({
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [
                {"resource": {"resourceType": "Observation", "id": "o1"}},
                {"resource": {"resourceType": "Patient", "id": "p2"}},
            ],
        }),
        encoding="utf-8",
    )

    summary = summarize_source(LocalFolderSource(str(tmp_path)))

    assert summary["resourceCount"] == 3
    assert summary["resourceTypes"]["Patient"] == 2
    assert summary["resourceTypes"]["Observation"] == 1


BASE = "https://fhir.example/fhir"
FIRST = BASE + "/Patient?_count=25"


def bundle(resource_id="p1", next_link=None):
    result = {
        "resourceType": "Bundle",
        "entry": [
            {"fullUrl": BASE + "/Patient/" + resource_id,
             "resource": {"resourceType": "Patient", "id": resource_id}},
            {"search": {"mode": "outcome"}},
        ],
    }
    if next_link is not None:
        result["link"] = [{"relation": "next", "url": next_link}]
    return result


@pytest.fixture
def http(monkeypatch):
    """Mock the transport, retaining urllib's real redirect processing."""
    routes, calls = {}, []

    def no_network(*args, **kwargs):
        pytest.fail("Unexpected real network access")

    def open_request(handler, req):
        calls.append(req)
        status, payload, location = routes[req.full_url]
        headers = Message()
        if location is not None:
            headers["Location"] = location
        response = urllib.response.addinfourl(
            io.BytesIO(json.dumps(payload).encode()), headers, req.full_url, status
        )
        response.msg = "mock response"
        return response

    monkeypatch.setattr(socket, "create_connection", no_network)
    monkeypatch.setattr(socket, "getaddrinfo", no_network)
    monkeypatch.setattr(urllib.request.HTTPHandler, "http_open", open_request)
    monkeypatch.setattr(urllib.request.HTTPSHandler, "https_open", open_request)
    return routes, calls


@pytest.mark.parametrize("next_link, expected", [
    (BASE + "/Patient?page=2", BASE + "/Patient?page=2"),
    ("?page=2", BASE + "/Patient?page=2"),
    ("Patient?page=2", BASE + "/Patient?page=2"),
    ("/fhir/Patient?page=2", BASE + "/Patient?page=2"),
    ("//fhir.example/fhir/Patient?page=2", BASE + "/Patient?page=2"),
    ("https://FHIR.example:443/fhir/Patient?page=2",
     "https://FHIR.example:443/fhir/Patient?page=2"),
])
def test_rest_pagination(http, next_link, expected):
    routes, calls = http
    routes[FIRST] = 200, bundle(next_link=next_link), None
    routes[expected] = 200, bundle("p2"), None

    resources = list(FhirRestSource(BASE, page_size=25).iter_resources())

    assert [req.full_url for req in calls] == [FIRST, expected]
    assert [r.resource["id"] for r in resources] == ["p1", "p2"]
    assert [r.reference for r in resources] == [BASE + "/Patient/p1", BASE + "/Patient/p2"]
    assert all(r.source == "fhir-rest" for r in resources)
    assert all(req.get_method() == "GET" and req.timeout == 30 for req in calls)
    assert calls[0].get_header("Accept") == "application/fhir+json, application/json"


UNSAFE_LINKS = [
    "https://other.example/fhir/Patient", "//other.example/fhir/Patient",
    "http://fhir.example/fhir/Patient", "https://fhir.example:444/fhir/Patient",
    "https://fhir.example.evil.test/Patient", "https://fhir.example@other.example/",
    "https://user:secret@fhir.example/", "file:///etc/passwd",
    "ftp://fhir.example/file", "data:application/json,{}", "javascript:alert(1)",
    "https://fhir.example:invalid/", "https://fhir.example\\@other.example/",
    "https://fhir.example/\nPatient",
]


@pytest.mark.parametrize("next_link", UNSAFE_LINKS)
def test_rest_rejects_unsafe_next_before_fetch(http, next_link):
    routes, calls = http
    routes[FIRST] = 200, bundle(next_link=next_link), None
    with pytest.raises(ValueError):
        list(FhirRestSource(BASE, page_size=25).iter_resources())
    assert [req.full_url for req in calls] == [FIRST]


@pytest.mark.parametrize("base", [
    "file:///tmp/fhir", "ftp://fhir.example", "/fhir", "https:///fhir",
    "https://user@fhir.example", "https://fhir.example:invalid", "\nhttps://fhir.example",
])
def test_rest_rejects_invalid_initial_endpoint(http, base):
    with pytest.raises(ValueError):
        list(FhirRestSource(base).iter_resources())
    assert http[1] == []


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
@pytest.mark.parametrize("target", [
    "https://other.example/", "//other.example/", "http://fhir.example/",
    "https://fhir.example:444/", "https://user@fhir.example/", "file:///etc/passwd",
    "ftp://fhir.example/file",
])
def test_rest_rejects_unsafe_redirect_before_fetch(http, status, target):
    routes, calls = http
    routes[FIRST] = status, {}, target
    with pytest.raises((ValueError, urllib.error.HTTPError)):
        list(FhirRestSource(BASE, page_size=25).iter_resources())
    assert [req.full_url for req in calls] == [FIRST]


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_rest_safe_redirect_and_relative_next(http, status):
    routes, calls = http
    redirected = BASE + "/search/pages/1"
    second = BASE + "/search/pages/2"
    routes[FIRST] = status, {}, "/fhir/search/pages/1"
    routes[redirected] = 200, bundle(next_link="2"), None
    routes[second] = 200, bundle("p2"), None
    resources = list(FhirRestSource(BASE, page_size=25).iter_resources())
    assert [r.resource["id"] for r in resources] == ["p1", "p2"]
    assert [req.full_url for req in calls] == [FIRST, redirected, second]


def test_rest_checks_every_redirect_hop(http):
    routes, calls = http
    safe = BASE + "/search"
    routes[FIRST] = 302, {}, safe
    routes[safe] = 302, {}, "https://other.example/"
    with pytest.raises(ValueError):
        list(FhirRestSource(BASE, page_size=25).iter_resources())
    assert [req.full_url for req in calls] == [FIRST, safe]


def test_rest_redirect_loop_is_bounded(http):
    routes, calls = http
    routes[FIRST] = 302, {}, FIRST
    with pytest.raises(urllib.error.HTTPError):
        list(FhirRestSource(BASE, page_size=25).iter_resources())
    assert 1 < len(calls) <= 5


def test_rest_non_bundle_still_raises(http):
    routes, calls = http
    routes[FIRST] = 200, {"resourceType": "Patient"}, None
    with pytest.raises(ValueError, match="did not return a Bundle"):
        list(FhirRestSource(BASE, page_size=25).iter_resources())
    assert len(calls) == 1
