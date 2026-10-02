# Synthetic mass test

The mass-test generator creates a reproducible dataset with deliberately injected error families.

Default population: 1,000 synthetic Patient resources.

The default seeded distribution contains five buckets:

- clean resources
- wrong date format (DD.MM.YYYY)
- missing identifier
- mojibake / encoding damage (MÃ¼ller)
- malformed JSON

Generate the dataset:

~~~bash
python -m ohe.generate_mass_test examples/mass_test --count 1000 --seed 42
~~~

Run the technical batch pre-check:

~~~bash
python -m ohe.cli batch examples/mass_test
~~~

## Important current limitation

The current pre-check layer can identify malformed JSON and likely encoding damage.

A wrong FHIR date format and a missing profile-required identifier require the FHIR/profile validation layer. They are deliberately present in the dataset so the same corpus can later be passed through the official HL7 FHIR Validator and compared with the pre-check results.

This separation is intentional:

1. transport / encoding / syntax errors
2. base FHIR errors
3. profile-specific conformance errors
4. grouped root-cause analysis
