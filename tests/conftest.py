"""Default tests must not reach real HTTP/FHIR/AI services."""
import socket
import pytest


@pytest.fixture(autouse=True)
def block_network(monkeypatch, request):
    if request.node.get_closest_marker("integration"):
        return
    def blocked(*args, **kwargs):
        pytest.fail("Real network access in a unit test; mock the transport")
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)
