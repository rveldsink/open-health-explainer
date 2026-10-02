from pathlib import Path

from ohe.batch import analyze_directory


def test_batch_clusters_repeated_errors(tmp_path: Path):
    for index in range(3):
        p = tmp_path / f"broken-{index}.json"
        p.write_text('{"resourceType":"Patient",}', encoding="utf-8")

    result = analyze_directory(str(tmp_path))
    assert result["fileCount"] == 3
    assert result["filesWithIssues"] == 3
    assert result["clusters"][0]["errorId"] == "OHE-JSON-001"
    assert result["clusters"][0]["occurrences"] == 3
