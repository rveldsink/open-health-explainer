import json
from pathlib import Path
from .negative_tests import generate_negative_cases

def main():
    project_root = Path(__file__).resolve().parents[3]
    source = project_root / "examples" / "patient_valid_synthetic.json"
    outdir = project_root / "examples" / "generated"
    outdir.mkdir(parents=True, exist_ok=True)

    resource = json.loads(source.read_text(encoding="utf-8"))
    cases = generate_negative_cases(resource)

    manifest = []
    for case_id, mutated in cases:
        path = outdir / f"{case_id}.json"
        path.write_text(json.dumps(mutated, indent=2, ensure_ascii=False), encoding="utf-8")
        manifest.append({"caseId": case_id, "file": str(path.relative_to(project_root))})

    (outdir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"Generated {len(cases)} negative test cases in {outdir}")

if __name__ == "__main__":
    main()
