from pathlib import Path

from ohe.precheck import inspect_file


def test_valid_utf8_json(tmp_path: Path):
    p = tmp_path / "patient.json"
    p.write_text('{"resourceType":"Patient","name":"Müller"}', encoding="utf-8")
    result = inspect_file(str(p))
    assert result["encoding"] == "utf-8"
    assert result["resourceType"] == "Patient"
    assert result["issueCount"] == 0
    assert len(result["sha256"]) == 64


def test_invalid_json_is_reported(tmp_path: Path):
    p = tmp_path / "broken.json"
    p.write_text('{"resourceType":"Patient",}', encoding="utf-8")
    result = inspect_file(str(p))
    assert any(x["errorId"] == "OHE-JSON-001" for x in result["issues"])


def test_non_utf8_is_reported(tmp_path: Path):
    p = tmp_path / "ansi.json"
    p.write_bytes('{"name":"Müller"}'.encode("cp1252"))
    result = inspect_file(str(p))
    assert any(x["errorId"] == "OHE-ENC-001" for x in result["issues"])
