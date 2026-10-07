# Offizielle Medikationsprofile in Open Health Explainer

Implementierter Ausschnitt: eine einzelne MedicationRequest-Ressource gegen
**MedicationRequestDgMP 1.0.7**, aus **de.fhir.medication 1.0.7**, FHIR **4.0.1**.
Offizielle Quelle: https://ig.fhir.de/igs/medication/1.0.7/
Dies ist eine konkrete Profilprüfung, keine vollständige Umsetzung sämtlicher
Anforderungen des Implementation Guides und keine Zertifizierung.

## Benutzung

Python >=3.10, Java 21 und der HL7 Java Validator 6.10.4 werden benötigt.
Installation: `python -m pip install .`
Die JAR wird nicht mitgeliefert. Bezug:
https://github.com/hapifhir/org.hl7.fhir.core/releases/tag/6.10.4
Die erwartete SHA-256 steht in `src/ohe/specs/medication-1.0.7/manifest.json`.

```sh
ohe specification > requirements.json
ohe validate-medication examples/medication-1.0.7/00-reference.json --validator validator_cli.jar --output evidence/run-001 --java java --cache-home runtime-home
```

Ein neuer Ausgabeordner ist Pflicht; vorhandene Prüfnachweise werden nicht
überschrieben. Gespeichert werden Eingabe, SHA-256, vollständiger Aufruf,
Validatorlog, originale OperationOutcome, Bericht und Anforderungskatalog.
Optional erklärt `ohe analyze evidence/run-001/operation-outcome.json` die Befunde.
Die originalen Regeln werden dem etablierten Validator übergeben, nicht als
eigene vereinfachte Prüfregeln nachgebaut.

## Was enthalten ist

17 unveränderte JSON-Artefakte: offizielle Medikationsprofile einschließlich
Dosage und Timing, zugehörige ValueSets, die benötigte Cross-Version-Extension
und KBV-Dosiereinheiten CodeSystem/ValueSet 1.01. SHA-256-Prüfungen erkennen
fehlende, zusätzliche und veränderte Definitionen. Der Katalog verweist auf
exakte JSON-Pointer, URL, Version und Quelldatei. Er listet ausgewählte
Differential-Aussagen auch für die mitgelieferten Geschwisterprofile; er ist
kein Nachweis, dass jede Aussage bei jedem MedicationRequest-Lauf geprüft wurde.
Geerbte Regeln bleiben Bestandteil der offiziellen Definitionen.

## Ergebnisse und Grenzen

- `failed`, Exitcode 1: Validator meldet Fehler.
- `not-checkable`, Exitcode 2: Ausführung oder Ergebnis nicht verwertbar.
- `no-errors-reported`, Exitcode 3: keine Fehler gemeldet, Prüfabdeckung trotzdem unvollständig.

`coverage` bleibt in diesem Offline-Modus immer `incomplete`. Ein fehlerfreier
Lauf ist kein medizinischer Richtigkeitsnachweis. Nicht alle Terminologien sind
lokal vorhanden; beispielsweise können Sprachcodes und periodUnit ungeprüft
bleiben. MustSupport-Fähigkeiten eines sendenden/empfangenden Systems lassen
sich nicht durch ein einzelnes JSON-Dokument nachweisen. Die Generierung und
der Vergleich des Dosierungstextes sind hier nicht implementiert. Vollständige
KBV-Verordnungen, gematik-Dienste und klinische Plausibilität sind nicht umfasst.

Die JAR und die mitgelieferten Definitionen sind festgelegt. Der externe FHIR-
Paketcache ist noch nicht vollständig hermetisch: benötigte Basis-/Supportpakete
müssen vorhanden sein oder vom Validator geladen werden. Das ist keine Garantie
für vollständig netzwerkfreien Betrieb. Die Studie verwendet einen vorbereiteten
Cache. Abhängigkeiten des Originalpakets: hl7.fhir.r4.core 4.0.1,
hl7.terminology.r4 7.2.0, hl7.fhir.uv.extensions.r4 5.2.0.

## Herkunft

Medication IG DE: HL7 Deutschland e.V.; Paketlizenz CC0-1.0.
KBV-Terminologie aus kbv.all.st-combined 1.12.0:
https://packages.simplifier.net/kbv.all.st-combined/1.12.0
Cross-Version-Extension aus hl7.fhir.uv.xver-r5.r4 0.0.1-snapshot-2:
https://hl7.org/fhir/uv/xver-r5.r4/0.0.1-snapshot-2/
Originale Copyright-/Lizenzfelder der Ressourcen bleiben unverändert erhalten.
Keine Zugehörigkeit zu oder Freigabe durch diese Organisationen wird behauptet.

## Prüfung

Unit-Tests decken Definitionsintegrität, Quellenverweise, unveränderte
Eingabesicherung, Überschreibschutz und vorsichtige Ergebnisinterpretation ab.
Testdoubles in Unit-Tests sind ausdrücklich keine echten Validatorläufe.
Die getrennten lokalen Integrationsnachweise liegen unter
`output/fhir-lab/software-spec-integration`: Referenz, gemischte Dosierungsangabe,
unbekannte Dosiereinheit und korrigierter Fall, jeweils mit echten Rohdaten.
