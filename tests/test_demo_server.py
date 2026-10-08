import io
import json
import urllib.request
from email.message import Message
from urllib.parse import urlsplit

import pytest

from ohe.demo_server import DemoApplication, serve_demo
from ohe.sources import FhirRestSource
from ohe.validator_runner import parse_operation_outcome_json


def call(app, path, method="GET", accept="application/fhir+json", query=""):
    response = {}
    def start(status, headers):
        response.update(status=int(status.split()[0]), headers=dict(headers))
    raw = b"".join(app({"REQUEST_METHOD":method, "PATH_INFO":path,
                         "QUERY_STRING":query, "HTTP_ACCEPT":accept}, start))
    response["body"] = json.loads(raw) if raw else None
    return response


def test_capabilities_match_implemented_interactions():
    app = DemoApplication()
    result = call(app, "/fhir/metadata")
    cs = result["body"]
    assert result["status"] == 200
    assert cs["fhirVersion"] == "4.0.1"
    resource = cs["rest"][0]["resource"][0]
    assert resource["type"] == "Patient"
    assert {i["code"] for i in resource["interaction"]} == {"read", "search-type"}
    assert resource["versioning"] == "no-version"
    assert not cs["rest"][0].get("operation")
    assert call(app, "/fhir/Patient")["status"] == 200
    assert call(app, "/fhir/Patient/ohe-demo-1")["status"] == 200
    assert call(app, "/fhir/Patient/ohe-demo-1")["body"]["id"] == "ohe-demo-1"


def test_paging_and_count_zero():
    app = DemoApplication()
    first = call(app, "/fhir/Patient", query="_count=1")["body"]
    assert first["type"] == "searchset" and first["total"] == 2
    second_url = next(l["url"] for l in first["link"] if l["relation"] == "next")
    parts = urlsplit(second_url)
    second = call(app, parts.path, query=parts.query)["body"]
    assert second["entry"][0]["resource"]["id"] != first["entry"][0]["resource"]["id"]
    assert not any(l["relation"] == "next" for l in second["link"])
    count = call(app, "/fhir/Patient", query="_count=0")["body"]
    assert count["total"] == 2 and "entry" not in count
    assert len(count["link"]) == 1
    assert call(app, "/fhir/Patient", query="_id=ohe-demo-2")["body"]["total"] == 1
    assert call(app, "/fhir/Patient", query="_id=missing")["body"]["total"] == 0


@pytest.mark.parametrize("path,query,method,accept,status", [
    ("/fhir/Patient", "_count=-1", "GET", "*/*", 400),
    ("/fhir/Patient", "_count=bad", "GET", "*/*", 400),
    ("/fhir/Patient", "_count=1&_count=2", "GET", "*/*", 400),
    ("/fhir/Patient", "name=ignored", "GET", "*/*", 400),
    ("/fhir/Patient", "_format=xml", "GET", "*/*", 406),
    ("/fhir/Patient", "", "GET", "application/xml", 406),
    ("/fhir/Patient", "", "GET", "application/fhir+json;fhirVersion=5.0", 406),
    ("/fhir/Patient", "", "GET", "application/fhir+json;q=0", 406),
    ("/fhir/Patient/missing", "", "GET", "*/*", 404),
    ("/fhir/Patient/ohe-demo-1/_history/1", "", "GET", "*/*", 404),
    ("/fhir/Observation", "", "GET", "*/*", 404),
    ("/fhir/Patient", "", "POST", "*/*", 405),
    ("/fhir/Patient/ohe-demo-1", "", "DELETE", "*/*", 405),
])
def test_errors_are_fhir_outcomes(path, query, method, accept, status):
    result = call(DemoApplication(), path, method, accept, query)
    assert result["status"] == status
    parsed = parse_operation_outcome_json(json.dumps(result["body"]))
    assert parsed["issues"][0]["severity"] == "error"
    if status == 405:
        assert result["headers"]["Allow"] == "GET, HEAD"


def test_head_and_store_isolation():
    app = DemoApplication()
    get = call(app, "/fhir/Patient/ohe-demo-1")
    head = call(app, "/fhir/Patient/ohe-demo-1", method="HEAD")
    assert head["status"] == get["status"] == 200
    assert head["body"] is None
    assert head["headers"]["Content-Length"] == get["headers"]["Content-Length"]
    patient = app.store.read("ohe-demo-1")
    patient["active"] = False
    assert app.store.read("ohe-demo-1")["active"] is True


def test_existing_connector_against_demo_without_network(monkeypatch):
    app, calls = DemoApplication(), []
    def transport(handler, request):
        calls.append(request.full_url)
        parts = urlsplit(request.full_url)
        value = call(app, parts.path, query=parts.query)
        headers = Message()
        headers["Content-Type"] = value["headers"]["Content-Type"]
        response = urllib.response.addinfourl(io.BytesIO(json.dumps(value["body"]).encode()),
                                             headers, request.full_url, value["status"])
        response.msg = "mock"
        return response
    monkeypatch.setattr(urllib.request.HTTPHandler, "http_open", transport)
    resources = list(FhirRestSource(app.base, page_size=1).iter_resources())
    assert len(calls) == 2
    assert [r.resource["id"] for r in resources] == ["ohe-demo-1", "ohe-demo-2"]
    assert all(r.reference.startswith(app.base) for r in resources)


def test_runner_binds_only_loopback(monkeypatch):
    events = []
    class Server:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def serve_forever(self):
            events.append("serve")
    def factory(host, port, app):
        assert host == "127.0.0.1" and port == 8123
        assert app.base == "http://127.0.0.1:8123/fhir"
        return Server()
    monkeypatch.setattr("ohe.demo_server.make_server", factory)
    serve_demo(8123)
    assert events == ["serve"]


def test_format_overrides_accept():
    result = call(DemoApplication(), "/fhir/Patient", query="_format=json", accept="application/xml")
    assert result["status"] == 200
    assert result["body"]["resourceType"] == "Bundle"
