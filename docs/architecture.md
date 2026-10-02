# Architecture v0.2

```text
StructureDefinition / known rule
            |
            v
+--------------------------+
| Negative Test Generator  |
+--------------------------+
            |
            v
 Synthetic invalid FHIR
            |
            v
 Official HL7 Validator
            |
            v
 OperationOutcome / text
            |
            v
+--------------------------+
| Normalizer + Classifier  |
+--------------------------+
            |
            v
+--------------------------+
| Explanation Catalogue    |
+--------------------------+
            |
            v
 JSON / HTML / CI
```

## Initial negative-test classes

1. Cardinality
2. Required terminology binding
3. Fixed value

Slicing and complex FHIRPath invariants are intentionally out of scope for the first prototype.

## Runtime AI policy

Core classification and explanation are deterministic.
No external AI service is required at runtime.
