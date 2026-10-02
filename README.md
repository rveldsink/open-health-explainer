# Open Health Explainer

Open-source prototype for reproducible analysis of HL7 FHIR validation failures.

**Initial concept and implementation:** Albert Gert Jan Veldsink  
**Known as:** René Veldsink  
**Project start:** October 2026  
**Development:** AI-assisted, with human review and responsibility.

## Why this project exists

The official HL7 FHIR Validator is authoritative and technically powerful.
Open Health Explainer does not replace it.

This project experiments with two complementary ideas:

1. Normalize validator output into stable error classes with human-readable explanations.
2. Generate deliberate negative test cases from profile rules, starting with simple, deterministic rule classes such as cardinality, required bindings and fixed values.

## v0.2 scope

- deterministic error catalogue
- stable OHE error IDs
- DE/EN explanations
- synthetic FHIR Patient example
- negative-test generator
- command wrapper for the official validator_cli.jar
- OperationOutcome parser
- JSON report format
- pytest tests
- no patient data
- no runtime AI dependency

## Quick demo

Generate synthetic invalid resources:

```bash
python -m ohe.generate_negative_tests
```

Explain a raw validator message:

```bash
python -m ohe.cli explain "Patient.identifier: minimum required = 1, but only found 0"
```

Run the official validator when validator_cli.jar is available:

```bash
python -m ohe.cli validate examples/generated/missing_identifier.json --validator ./validator_cli.jar
```

## Important

This is an experimental developer tool, not a medical device and not an official HL7 product.
FHIR and HL7 are trademarks of HL7 International.
