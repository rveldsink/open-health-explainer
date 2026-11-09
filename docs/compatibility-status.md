# Compatibility implementation status (2026-11-09)

## Implemented in OHE

- Prefer readable details.text; preserve diagnostics separately.
- Mark OperationOutcome timeout/transient codes as infrastructure coverage gaps,
  retaining the original severity and raw outcome. Do not reinterpret arbitrary
  exceptions, HTTP text or not-found codes as infrastructure errors.
- Keep distinct unclassified validator messages in separate clusters, and preserve
  source filenames from analyzer reports.
- Pin the official 7.0.5-era StructureMap/ValueSet outcomes and the eight STU3/R4/R4B/R5
  primitive-array expected outcomes from FHIR/fhir-test-cases PR #337. The latter are
  development expectations for 7.0.6-SNAPSHOT, not captured local Java results.
- Add an opt-in upstream terminology regression gate for language isolation,
  transient cache handling, unknown-code-system handling, expansion failures and
  package-index construction. It requires ancestry containing HL7 PR #2827 and runs
  the upstream test classes, rejecting missing, empty or skipped reports.

## Run

`python -m pytest -q`: 67 passed, 8 skipped in the implementation environment.
Skipped: six Java fixture validations, one injected Java type-resolution test, and
one upstream terminology Maven suite. These skips are not proof of compatibility.

The Maven gate requires a dedicated disposable checkout and runs Maven clean:

```sh
OHE_HL7_TERMINOLOGY_CHECKOUT=/absolute/path/org.hl7.fhir.core \
  python -m pytest -q tests/test_upstream_terminology_gate.py
```

See snapshot-7.0.5-regression.md and type-lookup-regression.md for other gates.

## Release versus integration

HL7 7.0.5 is the latest published version verified for this change. Newer cache,
language and primitive-array changes remain 7.0.6-SNAPSHOT development code.
The production medication/immunization workflows still require their checksum-pinned
6.10.4 validator. Changing that pin without rerunning the full profile suite would
invalidate their reproducibility claims; this update does not do so.

Remaining acceptance work: run the Java gates, test inherited contentReference
invariants (Composition cmp-1/2, Parameters inv-1, Extension ext-1) and terminology
supplement/reserved-code/filter cases against the selected release. Only then select
and checksum-pin a new workflow engine. No upstream Java cache or snapshot-generator
code has been reimplemented in Python.

This repository provides a local workflow and generated HTML reports. No production
web hosting target is configured in the reviewed project. Publishing repository code
is separate from deploying an application.

## Official sources

- https://github.com/hapifhir/org.hl7.fhir.core/releases/tag/7.0.5
- https://github.com/hapifhir/org.hl7.fhir.core/pull/2822
- https://github.com/hapifhir/org.hl7.fhir.core/pull/2825
- https://github.com/hapifhir/org.hl7.fhir.core/pull/2827
- https://github.com/hapifhir/org.hl7.fhir.core/pull/2847
- https://github.com/hapifhir/org.hl7.fhir.core/pull/2848
- https://github.com/hapifhir/org.hl7.fhir.core/pull/2846
- https://github.com/FHIR/fhir-test-cases/pull/337
