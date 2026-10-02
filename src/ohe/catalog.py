ERROR_CATALOG = [
    {
        "errorId": "OHE-CARD-001",
        "category": "cardinality",
        "patterns": ["minimum required", "minimum required = 1, but only found 0", "minimum cardinality"],
        "fixPolicy": "deterministic",
        "explanation_de": "Ein vom aktiven Profil vorgeschriebenes Pflichtfeld fehlt.",
        "explanation_en": "A mandatory element required by the active profile is missing.",
        "suggestedAction_de": "Prüfe die Kardinalität des betroffenen Elements und ergänze das erforderliche Feld.",
        "suggestedAction_en": "Check the element cardinality and add the required field."
    },
    {
        "errorId": "OHE-BIND-001",
        "category": "required-binding",
        "patterns": ["not in the value set", "not in value set", "code is not in the value set", "unknown code"],
        "fixPolicy": "manual-review",
        "explanation_de": "Der verwendete Code erfüllt die Terminologie-Bindung des Profils nicht.",
        "explanation_en": "The supplied code does not satisfy the terminology binding of the profile.",
        "suggestedAction_de": "Prüfe CodeSystem, ValueSet und Binding-Stärke des Elements.",
        "suggestedAction_en": "Check the CodeSystem, ValueSet and binding strength of the element."
    },
    {
        "errorId": "OHE-FIXED-001",
        "category": "fixed-value",
        "patterns": ["fixed value", "does not match the fixed value", "must have the value"],
        "fixPolicy": "deterministic",
        "explanation_de": "Der Wert weicht von einem im Profil fest vorgegebenen Wert ab.",
        "explanation_en": "The value differs from a value fixed by the profile.",
        "suggestedAction_de": "Setze das Element auf den vom Profil vorgeschriebenen festen Wert.",
        "suggestedAction_en": "Set the element to the fixed value required by the profile."
    },
    {
        "errorId": "OHE-CONSTRAINT-001",
        "category": "constraint",
        "patterns": ["failed invariant", "constraint failed", "fhirpath"],
        "fixPolicy": "explain-only",
        "explanation_de": "Eine Profilregel oder FHIRPath-Constraint wurde verletzt.",
        "explanation_en": "A profile rule or FHIRPath constraint was violated.",
        "suggestedAction_de": "Prüfe die referenzierte Constraint-Regel im aktiven Profil.",
        "suggestedAction_en": "Review the referenced constraint in the active profile."
    }
]
