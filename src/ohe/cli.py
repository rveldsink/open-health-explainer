import argparse
import json
from .explainer import explain
from .validator_runner import run_validator

def main():
    parser = argparse.ArgumentParser(prog="ohe")
    subs = parser.add_subparsers(dest="cmd", required=True)

    explain_p = subs.add_parser("explain")
    explain_p.add_argument("message")

    validate_p = subs.add_parser("validate")
    validate_p.add_argument("resource")
    validate_p.add_argument("--validator", required=True)

    args = parser.parse_args()

    if args.cmd == "explain":
        print(json.dumps(explain(args.message), indent=2, ensure_ascii=False))
        return

    if args.cmd == "validate":
        result = run_validator(args.resource, args.validator)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        raise SystemExit(result.returncode)

if __name__ == "__main__":
    main()
