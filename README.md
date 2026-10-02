# Open Health Explainer

Open-source prototype for reproducible analysis of HL7 FHIR validation failures.

**Initial concept and implementation:** Albert Gert Jan Veldsink  
**Known as:** René Veldsink  
**Project start:** October 2026  
**Development:** AI-assisted, with human review and responsibility.

## In one sentence

> Everyone builds their own FHIR interface. We help make sure the right ingredients are used, so the final result is consistent and interoperable across Europe.

Or, less technically:

> Everyone cooks their own soup — we help make sure the right ingredients go in, so in the end the soup tastes the same everywhere, just as European interoperability intends.

## Why this project exists

The official HL7 FHIR Validator is authoritative and technically powerful.
Open Health Explainer does not replace it.

This project experiments with two complementary ideas:

1. Normalize validator output into stable error classes with human-readable explanations.
2. Generate deliberate negative test cases from profile rules, starting with simple, deterministic rule classes such as cardinality, required bindings and fixed values.

## Current scope

Open Health Explainer now has three layers:

1. **Pre-validation** — encoding, BOM, control characters, malformed JSON, SHA-256 fingerprinting.
2. **FHIR validation explanation** — normalize and explain official validator output.
3. **Batch/error clustering** — scan many JSON resources and collapse repeated technical failures into error families.

The goal is not to show developers 50,000 almost identical errors. The goal is to help them see that those 50,000 symptoms may come from only a few systematic root causes.

## v0.3 prototype scope

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

Pre-check one file:

```bash
python -m ohe.cli precheck examples/patient_valid_synthetic.json
```

Scan a directory and cluster repeated technical errors:

```bash
python -m ohe.cli batch examples/
```

Example idea for a large import:

```text
48,312 validation issues
4 recurring error families

31,442  date conversion / Patient.birthDate
 9,814  character encoding damage
 6,921  missing mandatory identifier
   135  invalid terminology code
```

This makes the project useful not only as a validator frontend, but as an error-intelligence layer for interface and migration testing.

## Important

This is an experimental developer tool, not a medical device and not an official HL7 product.
FHIR and HL7 are trademarks of HL7 International.
