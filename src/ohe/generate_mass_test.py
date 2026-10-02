import argparse
import json
import random
from pathlib import Path


def make_patient(index: int):
    return {
        "resourceType": "Patient",
        "id": f"synthetic-{index:05d}",
        "identifier": [{
            "system": "https://example.org/patient-id",
            "value": f"TEST-{index:05d}"
        }],
        "active": True,
        "name": [{
            "use": "official",
            "family": f"Muster{index}",
            "given": ["Anna"]
        }],
        "gender": "female" if index % 2 == 0 else "male",
        "birthDate": f"{1960 + (index % 50):04d}-11-23"
    }


def generate(output_dir: str, count: int = 1000, seed: int = 42):
    random.seed(seed)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    stats = {
        "count": count,
        "clean": 0,
        "wrong_date_format": 0,
        "missing_identifier": 0,
        "mojibake_name": 0,
        "broken_json": 0,
    }

    for i in range(count):
        patient = make_patient(i)
        roll = random.random()

        if roll < 0.50:
            stats["clean"] += 1
            kind = "clean"
        elif roll < 0.72:
            patient["birthDate"] = "23.11.1965"
            stats["wrong_date_format"] += 1
            kind = "wrong-date"
        elif roll < 0.87:
            patient.pop("identifier", None)
            stats["missing_identifier"] += 1
            kind = "missing-identifier"
        elif roll < 0.97:
            patient["name"][0]["family"] = "MÃ¼ller"
            stats["mojibake_name"] += 1
            kind = "mojibake"
        else:
            stats["broken_json"] += 1
            kind = "broken-json"

        path = out / f"{i:05d}-{kind}.json"

        if kind == "broken-json":
            path.write_text('{"resourceType":"Patient",}', encoding="utf-8")
        else:
            path.write_text(
                json.dumps(patient, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )

    (out / "_expected_distribution.json").write_text(
        json.dumps(stats, indent=2),
        encoding="utf-8"
    )

    print(json.dumps(stats, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", nargs="?", default="examples/mass_test")
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    generate(args.output_dir, args.count, args.seed)


if __name__ == "__main__":
    main()
