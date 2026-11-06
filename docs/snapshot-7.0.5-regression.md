# Validator 7.0.5 snapshot regressions

The upstream fixes are merged development code, not an approved production validator:
- https://github.com/hapifhir/org.hl7.fhir.core/pull/2819 (ValueSet parameter without name)
- https://github.com/hapifhir/org.hl7.fhir.core/pull/2815 (StructureMap import without value)
- https://github.com/hapifhir/org.hl7.fhir.core/pull/2816 (dependent input without mode)

Pinned upstream inputs and golden OperationOutcomes are in
`tests/fixtures/snapshot-7.0.5`; `provenance.json` records exact source commit URLs.
These are upstream expectations, not outputs of a Java run performed in this project.

`python -m pytest -q` exercises the real OHE parser, analyzer and explainer against
these outcomes. It checks error/warning distinctions, cardinality classification,
raw issues, diagnostics and expressions, including outcomes with no issue array.
The explainer now prefers readable details over diagnostics and retains diagnostics
separately. It falls back to diagnostics when details is absent, empty or whitespace.
No new message-specific rule is invented for SM_IMPORT_NO_VALUE.

For actual Java execution, build a 7.0.5-SNAPSHOT containing the three fixes and run:

```sh
OHE_SNAPSHOT_VALIDATOR_JAR=/absolute/path/validator_cli.jar \
  python -m pytest -q tests/test_snapshot_outcomes.py
```

Requires Java and cached official R4/terminology/extension packages. Tests disable the
online terminology server and allow the official fixtures' example URLs. Full engine
logs remain in pytest temporary directories. Each run writes a new OperationOutcome.
Without the variable these six Java cases are explicitly skipped. Exact issue text,
codes, expressions and error ordering are intentional compatibility assertions;
source-coordinate diagnostics are not compared because formatting can move them.
Additional warning/information issues are permitted, unexpected errors are not.

This does not change the checksum-pinned production engines in specification modes,
merge the draft PR, or assert that a snapshot is production-ready. Real Java validation
and the optional type-lookup Maven suite remain separate integration gates.
