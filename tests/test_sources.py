import json
from pathlib import Path

from ohe.sources import LocalFolderSource, summarize_source


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
