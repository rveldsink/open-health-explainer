import json
from pathlib import Path

from ohe.batch import analyze_directory
from ohe.generate_mass_test import generate


def test_mass_test_generation_and_batch(tmp_path: Path):
    out = tmp_path / "mass"
    generate(str(out), count=100, seed=42)

    expected = json.loads((out / "_expected_distribution.json").read_text())
    generated = sum(value for key, value in expected.items() if key != "count")
    assert generated == expected["count"]

    result = analyze_directory(str(out))

    ids = {cluster["errorId"] for cluster in result["clusters"]}
    assert "OHE-JSON-001" in ids
    assert "OHE-ENC-003" in ids
