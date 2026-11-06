# Type-lookup compatibility regression

Tracks official HL7 core [PR #2812](https://github.com/hapifhir/org.hl7.fhir.core/pull/2812),
merged 2026-11-03 as commit `428bcd5604c539a65bb949d783aea12c4b988ed9`.
This is development code for 7.0.5-SNAPSHOT, not a released validator.

## OHE boundary tests

Run `python -m pytest -q tests/test_type_lookup_compatibility.py`.
Synthetic OperationOutcome inputs check that error/fatal type-resolution failures
remain errors, diagnostics/details and paths survive, and no complete coverage is
claimed. These do not claim to reproduce actual HL7 messages or exercise Java.
No production rule changes are necessary for these assertions.

## Actual HL7 resolver

Requires Java and Maven as specified by the HL7 checkout, plus its build dependencies
and FHIR test packages. Clone `hapifhir/org.hl7.fhir.core`, fetch the above commit and
check it out (or use a descendant). Then:

```sh
OHE_HL7_CORE_CHECKOUT=/absolute/path/org.hl7.fhir.core \
  python -m pytest -q tests/test_type_lookup_compatibility.py
```

The opt-in test copies the supplied Java test into the standalone module and removes
it afterwards. It refuses to overwrite an existing test. Run in a dedicated checkout
without concurrent builds: its named Surefire report is removed before execution.
Maven output is kept in pytest's temporary directory. Failed builds, timeouts, missing
reports and zero/skipped Java test cases fail the opt-in test; they never count as a pass.
Without the environment variable, the Java check is explicitly skipped.

The actual StructureDefinition always has derivation=specialization, kind=resource,
type OheLookup and a minimal snapshot. A registered CanonicalResourceProxy supplies
three package-index states:

| Index derivation | Expected parser result |
| --- | --- |
| specialization | Same definition for type name, canonical URL and XML namespace/name |
| absent | Same definition; lazy proxy is loaded to inspect the real derivation |
| constraint (deliberately incorrect) | Controlled FHIRFormatError; proxy is skipped without loading |

The last case documents the changed behavior; it does not approve malformed packages.
It calls the real parser fallback directly, not full CLI validation or a hospital profile.
The Java test targets the standalone/services resolver. It does not establish R4/R4B/R5
cross-version conformance, a performance gain, or the exact OperationOutcome emitted by
the CLI. Those remain separate integration checks.
