# Open Health Explainer

## Current tested scope (7 October 2026)

- MedicationRequestDgMP 1.0.7: 26 synthetic cases and two revalidated corrections.
- ImmunizationRecommendation R4 4.0.1: eight synthetic cases and one revalidated correction.
- 39 automated tests pass. These are separate from the real HL7 Java Validator runs.
- Reports preserve findings and link explicit invariant IDs to official definitions.
- Offline terminology coverage is incomplete; no-errors-reported is not full conformance.
- No clinical recommendation engine, national vaccination schedule checking or proven market demand.
- Optional local AI adapter exists, but no real-model evaluation has been performed.

Published reports: [medication](https://www.veldsink.com/FHIR/prueflabor/index.html)
and [immunization](https://www.veldsink.com/FHIR/prueflabor/immunization.html).
The browser displays saved runs; new validation runs use the local CLI.

Reproduce the unit tests with `python -m pip install -e . pytest`, then `python -m pytest`.
For real validation, follow the version-pinned setup in
[medication specifications](docs/medication-specification.md),
[workflow instructions](docs/workflow.md) and [immunization](docs/immunization.md).
Java/validator binaries and the full dependency cache are not bundled.

New research mode: `ohe workflow ... --spec immunization` checks the FHIR R4
ImmunizationRecommendation base structure. See [scope and examples](docs/immunization.md).
It does not implement vaccine forecasting or national vaccination schedules.

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

## Provider-neutral connectors

The analysis engine is intentionally vendor-neutral.

Current prototype sources:
- local FHIR JSON files and Bundles
- generic read-only FHIR REST endpoint

Example:

```bash
python -m ohe.cli source examples/ --type folder
python -m ohe.cli source https://example-fhir-server/fhir --type fhir-rest --resource-type Patient --limit 1000
```

This is the foundation for future connectors to HAPI FHIR, Firely, Oracle Health, Epic and other healthcare integration platforms.

## Integration roadmap

The first prototype intentionally works with local files and folders. This keeps testing simple, reproducible and privacy-friendly.

Later versions can add connectors for systems that already manage FHIR or structured healthcare data, for example:

- HAPI FHIR JPA Server
- Firely Server
- PostgreSQL / JSONB
- FHIR REST endpoints
- local export folders and ZIP archives

The long-term flow is:

```text
Files / FHIR Server / Database Export
              |
              v
   Open Health Explainer
              |
              v
Pre-check -> FHIR validation -> error clustering -> root-cause report
```

The goal is that organizations can analyze large datasets directly from their existing infrastructure without manually inspecting thousands of individual validation errors.

## Important

This is an experimental developer tool, not a medical device and not an official HL7 product.
FHIR and HL7 are trademarks of HL7 International.

## Version-pinned German medication profile

The `validate-medication` command runs the HL7 Java Validator against official
MedicationRequestDgMP 1.0.7 definitions. See [scope, usage and limitations](docs/medication-specification.md).
This offline mode never claims complete conformance.

## Local investigation workflow

`ohe workflow` validates folders in one Java process, explains findings and compares
reviewed corrections. See [German usage guide](docs/workflow.md). Includes 26
synthetic cases and an optional local AI adapter (not enabled by default).
