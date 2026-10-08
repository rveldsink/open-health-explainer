"""Loopback-only FHIR R4 read/search fixture, not a production FHIR server."""
import json
from http import HTTPStatus
from urllib.parse import parse_qs, urlencode
from wsgiref.simple_server import make_server

from .demo_store import DemoStore


def outcome(code, message):
    return {"resourceType": "OperationOutcome", "issue": [
        {"severity": "error", "code": code, "diagnostics": message}]}


def accepts_json(header):
    # Most-specific media ranges override wildcards (including explicit q=0).
    matches = []
    for item in (header or "*/*").split(","):
        pieces = [p.strip() for p in item.split(";")]
        media = pieces[0].lower()
        params = dict(p.split("=", 1) for p in pieces[1:] if "=" in p)
        try:
            quality = float(params.get("q", "1"))
        except ValueError:
            continue
        if params.get("fhirVersion", "4.0").strip('"') not in ("4.0", "4.0.1"):
            continue
        if media in ("application/fhir+json", "application/json", "application/*", "*/*"):
            matches.append((2 if media in ("application/fhir+json", "application/json") else 1 if media == "application/*" else 0, quality))
    if not matches:
        return False
    specificity = max(m[0] for m in matches)
    return any(0 < quality <= 1 for rank, quality in matches if rank == specificity)


class DemoApplication:
    def __init__(self, port=8765):
        if not isinstance(port, int) or not 1 <= port <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        self.base = f"http://127.0.0.1:{port}/fhir"
        self.store = DemoStore()

    def capability_statement(self):
        return {
            "resourceType": "CapabilityStatement", "status": "draft",
            "date": "2026-10-08", "kind": "instance", "fhirVersion": "4.0.1",
            "format": ["json"], "software": {"name": "Open Health Explainer synthetic demo"},
            "implementation": {"description": "Local synthetic fixture; read-only, no clinical data",
                               "url": self.base},
            "rest": [{"mode": "server", "resource": [{
                "type": "Patient", "versioning": "no-version",
                "interaction": [{"code": "read"}, {"code": "search-type"}],
                "searchParam": [{"name": "_id", "type": "token",
                                 "definition": "http://hl7.org/fhir/SearchParameter/Resource-id"}],
                "documentation": "Synthetic fixtures only. Supports _id, _count, JSON _format and opaque next links. No writes or history."
            }]}],
        }

    def dispatch(self, method, path, query, accept):
        if method not in ("GET", "HEAD"):
            return 405, outcome("not-supported", "Read-only demo: use GET or HEAD")
        params = parse_qs(query, keep_blank_values=True)
        if any(len(values) != 1 for values in params.values()):
            return 400, outcome("invalid", "Repeated query parameters are unsupported")
        params = {key: values[0] for key, values in params.items()}
        if params.get("_format", "json") not in ("json", "application/json", "application/fhir+json"):
            return 406, outcome("not-supported", "Only JSON format is available")
        if "_format" not in params and not accepts_json(accept):
            return 406, outcome("not-supported", "Only FHIR R4 JSON is available")
        params.pop("_format", None)
        if path == "/fhir/metadata" and not params:
            return 200, self.capability_statement()
        if path.startswith("/fhir/Patient/") and not params:
            value = self.store.read(path[len("/fhir/Patient/"):])
            return (200, value) if value is not None else (404, outcome("not-found", "Patient not found"))
        if path != "/fhir/Patient":
            return 404, outcome("not-found", "Unsupported route or parameters")
        if set(params) - {"_id", "_count", "_offset"}:
            return 400, outcome("not-supported", "Unsupported search parameter")
        try:
            count, offset = int(params.get("_count", "100")), int(params.get("_offset", "0"))
            if not 0 <= count <= 1000 or offset < 0:
                raise ValueError()
        except ValueError:
            return 400, outcome("invalid", "Invalid _count (0..1000) or _offset (>=0)")
        resources = self.store.search(params["_id"].split(",") if "_id" in params else None)
        def link(relation, values):
            return {"relation": relation, "url": self.base + "/Patient" + ("?" + urlencode(values) if values else "")}
        result = {"resourceType": "Bundle", "type": "searchset", "total": len(resources),
                  "link": [link("self", params)]}
        page = resources[offset:offset + count]
        if page:
            result["entry"] = [{"fullUrl": self.base + "/Patient/" + r["id"],
                                "resource": r, "search": {"mode": "match"}} for r in page]
        if count and offset + count < len(resources):
            result["link"].append(link("next", dict(params, _count=count, _offset=offset + count)))
        return 200, result

    def __call__(self, environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET")
        status, resource = self.dispatch(method, environ.get("PATH_INFO", ""),
                                         environ.get("QUERY_STRING", ""), environ.get("HTTP_ACCEPT", ""))
        payload = json.dumps(resource, ensure_ascii=False).encode("utf-8")
        headers = [("Content-Type", "application/fhir+json; charset=utf-8; fhirVersion=4.0"),
                   ("Content-Length", str(len(payload))), ("Cache-Control", "no-store")]
        if status == 405:
            headers.append(("Allow", "GET, HEAD"))
        start_response(f"{status} {HTTPStatus(status).phrase}", headers)
        return [b"" if method == "HEAD" else payload]


def serve_demo(port=8765):
    app = DemoApplication(port)
    with make_server("127.0.0.1", port, app) as server:
        print(f"Synthetic FHIR R4 demo: {app.base}/metadata", flush=True)
        server.serve_forever()
