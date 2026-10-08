# Plattform-Grundlage und Standardabdeckung

Stand: 8. Oktober 2026. Dies ist ein erster Ausbau, keine vollständige FHIR-Plattform
und kein Konformitätsnachweis. Die Matrix ordnet die Bereiche des offiziellen
[Dokumentationsindex R4](https://hl7.org/fhir/R4/documentation.html) und
[R5](https://hl7.org/fhir/R5/documentation.html) dem tatsächlichen Programm zu.
Sie behauptet weder die Prüfung aller verlinkten Seiten noch aller Beispiele.

## Vorhandene Arbeit weiterverwenden

Basis ist `522f2ee`: Medikamenten-IG 1.0.7, ImmunizationRecommendation R4,
prüfsummengesicherte offizielle Definitionen, lokale KI-Vorschläge und
Workflow-Nachweise waren bereits vorhanden. Der frühere Pfadextraktionsfehler ist
auf dieser Basis behoben. Dieser Ausbau dupliziert diese Workflows nicht.
[PR #1](https://github.com/rveldsink/open-health-explainer/pull/1) bleibt separat;
seine Absicherung für Pagination/Redirects muss zusätzlich übernommen werden,
bevor fremde REST-Endpunkte angeschlossen werden.

## 1. Allgemeine versionierte Validierung

```bash
PYTHONPATH=src python -m ohe.cli validate-pinned examples/patient_valid_synthetic.json \
  --validator /path/to/validator_cli.jar \
  --config examples/validation/r4.json --output runs/patient-r4
```

Die Konfiguration verlangt die exakte FHIR-Version, Validator-Version und
SHA-256-Prüfsumme. Der Beispiel-Lock verwendet denselben HL7 Java Validator
6.10.4 wie die vorhandenen Workflows. IGs müssen `package#major.minor.patch`
verwenden, explizite Profile `canonical-url|version`. Kein `latest` und keine
stille Auswahl des neuesten Releases. `4.0.1`, `4.3.0` und `5.0.0` sind im
Adapter zugelassen; das ist keine pauschale Kompatibilitätszusage für alle IGs.

Jeder Lauf speichert Eingabe, Konfiguration, Aufruf, Log, OperationOutcome und
Bericht in einem neuen Verzeichnis. Ein vorhandenes Verzeichnis wird nicht
überschrieben. Exitcodes: 1 = Fehler gemeldet, 2 = nicht prüfbar, 3 = keine Fehler
gemeldet bei unvollständiger Abdeckung. Leere/fehlerhafte Outcomes, widersprüchliche
Exitcodes, Prozessfehler und Zeitüberschreitungen gelten nicht als Erfolg.
Der bestehende einfache `validate`-Aufruf bleibt unverändert; für nachvollziehbare
Läufe ist `validate-pinned` vorgesehen.

Die Argumente `-version`, `-ig`, `-profile`, `-tx n/a`,
`-disable-default-resource-fetcher` und `-output` wurden gegen den offiziellen
[Quellstand 6.10.4](https://github.com/hapifhir/org.hl7.fhir.core/tree/6.10.4/org.hl7.fhir.validation.cli/src/main/java/org/hl7/fhir/validation/cli/picocli)
geprüft, insbesondere `commands/ValidateCommand.java`,
`options/ValidationEngineOptions.java` und `options/InstanceValidatorOptions.java`.

**Grenzen:** Der Terminologieserver ist deaktiviert. Java kann fehlende
FHIR-/IG-Pakete laden. Der Paketcache und transitive Abhängigkeiten sind noch
nicht vollständig über Inhaltsprüfsummen gesichert. Ein JAR-Hash und feste
Versionsnamen sind deshalb noch keine vollständig reproduzierbare Offlineumgebung.
FHIR-Release und explizite IG-Versionen werden nicht automatisch aktualisiert.
Der Validator 6.10.4 lädt intern zusätzlich die unversionierten Kompatibilitätspakete
`hl7.terminology` und (vor R5) `hl7.fhir.uv.extensions`; auch deren Auflösung hängt
vom Cache ab. Das wurde in `ValidationService.loadIgsAndExtensions` im offiziellen
6.10.4-Quellstand und beim Integrationslauf beobachtet. Keine automatische
Ressourcenkonvertierung.

## 2. Aus Profilen abgeleitete Negativtest-Kandidaten

```bash
PYTHONPATH=src python -m ohe.cli profile-cases \
  examples/immunization-r4/00-reference.json \
  src/ohe/specs/immunization-r4/definitions/StructureDefinition-ImmunizationRecommendation.json \
  --output runs/immunization-candidates
```

Unterstützt werden direkte, ungeslicte Felder eines aufgelösten Snapshots:
Pflichtfeld entfernen, begrenzte Wiederholung überschreiten, `fixedBoolean`,
`fixedCode`, `fixedString` verletzen sowie einen skalaren `code` außerhalb eines
explizit und endlich definierten Required-ValueSets einsetzen. ValueSets können
mit wiederholtem `--value-set path.json` übergeben werden. Canonical und Version
müssen zur Bindung passen. Differential-Vererbung wird nicht geraten.

Das Manifest enthält die Profilreferenz, Mutationsregel, Kandidaten und
übersprungene Regeln mit Begründung. Die Ausgangsressource bleibt unverändert.
Die Kandidaten müssen anschließend gegen das Profil validiert werden; weder
Baseline-Gültigkeit noch exakt ein resultierender Fehler werden behauptet.
Slicing, verschachtelte Felder, Choice-Typen, FHIRPath, komplexe Fixed/Pattern-Werte,
Terminologiefilter und importierte ValueSets bleiben offen.

## 3. Lokaler FHIR-Demoserver

```bash
PYTHONPATH=src python -m ohe.cli serve-demo --port 8765
# In einem zweiten Terminal:
PYTHONPATH=src python -m ohe.cli source http://127.0.0.1:8765/fhir --type fhir-rest
```

| Route | Tatsächliche Funktion |
| --- | --- |
| `GET /fhir/metadata` | R4 CapabilityStatement der implementierten Funktionen |
| `GET /fhir/Patient/{id}` | Einen der zwei synthetischen Patienten lesen |
| `GET /fhir/Patient` | Searchset; `_id`, `_count`, servereigene Next-Links |
| `HEAD` auf diesen Routen | Gleiche Metadaten, kein Antwortkörper |

JSON ist das einzige Format. Unbekannte Suchparameter werden abgelehnt, nicht
unbemerkt ignoriert. `_count=0` liefert nur Gesamtzahl und Links. Fehler sind
OperationOutcomes. Schreiboperationen werden mit 405 zurückgewiesen. Es gibt
keine Authentifizierung, Datenbank, importierten Patientendaten oder Historie.
Der Startbefehl bindet ausschließlich an `127.0.0.1`; er ist eine Entwicklungs-
und Testumgebung. Nicht mit einem öffentlichen WSGI-Server veröffentlichen.

`demo_store.py` hält synthetische Daten, `demo_server.py` HTTP/WSGI und
`validation.py` Validatoraufrufe getrennt. Der Server behauptet weder `$validate`
noch R4B/R5-Unterstützung. Der Erklärer arbeitet separat auf den Ergebnissen.

Für eine persistente Plattform wurde der offizielle
[HAPI FHIR JPA Starter](https://hapifhir.github.io/hapi-fhir-jpaserver-starter/)
als wiederverwendbare Basis geprüft. Die Demo vermeidet eine parallele eigene
Implementierung vollständiger FHIR-Suche, Transaktionen und Persistenz.
Eine versionierte HAPI-Anbindung mit Datenbank und Betriebsprüfungen ist der
nächste Plattformschritt; HAPI wurde hier nicht installiert oder gestartet.

## Abdeckungsmatrix

„Delegiert“ heißt: an den offiziellen Validator übergeben, keine eigenständige
Implementierung und kein Nachweis aller Standardregeln.

| Standardbereich / Quelle | Release | Code und Beispiele | Nachweis / offene Anforderungen |
| --- | --- | --- | --- |
| [Validierung](https://hl7.org/fhir/R4/validation.html), Profile | R4; Adapter auch R4B/R5 | `validation.py`, bestehende `specification.py`/`profiles.py` | `test_validation.py`; vollständige Terminologie und Paket-Lock offen |
| [OperationOutcome](https://hl7.org/fhir/R5/operationoutcome.html) | R4/R5 | Originalbeispiele in `tests/fixtures/hl7`; Rohdaten, Coding, Location, Expression bleiben erhalten | Parsertests, SHA-256; unbekannte Regeln bleiben unklassifiziert |
| [ElementDefinition](https://hl7.org/fhir/R4/elementdefinition.html) | R4-Testprofil | `profile_tests.py`, offizieller ImmunizationRecommendation-Snapshot | `test_profile_cases.py`; komplexe Regeln explizit übersprungen |
| [REST](https://hl7.org/fhir/R4/http.html) | R4 | `demo_server.py`, zwei synthetische Patienten | `test_demo_server.py`; nur Lesen/Suchteilmenge |
| [CapabilityStatement](https://hl7.org/fhir/R4/capabilitystatement.html) | R4 | `/metadata` | Deklarationen gegen Routen getestet; kein Zertifikat |
| [Suche](https://hl7.org/fhir/R4/search.html) | R4-Teilmenge | `_id`, `_count`, Pagination | Connector/Server-Test ohne Netzwerk; Chaining, Includes, Sortierung offen |
| JSON, XML, RDF, NDJSON | R4/R5 | JSON-Vorprüfung vorhanden; JSON-Server | XML/RDF/NDJSON-Ingestion nicht implementiert |
| Datentypen, References, Narrative, Extensions | profilabhängig | Strukturelle Prüfung delegiert | Keine vollständige semantische oder klinische Prüfung |
| Terminologien, ValueSets, CodeSystems | profilabhängig | Lokale Definitionen, endliche Test-ValueSets | Kein eigener Terminologiedienst; externe Terminologie deaktiviert |
| FHIRPath, Invarianten, Slicing | profilabhängig | Validierung delegiert, bekannte Meldungen erklärt | Kein eigener Interpreter; Mutationsgenerator deckt sie nicht ab |
| Versionsverwaltung und Transformation | R4/R4B/R5 | explizite Release-Auswahl | Adaptertests; keine automatische Migration zwischen Releases |
| Schreiben, Patch, Transaktionen, History | offen | keine Implementierung in der Demo | Persistenter HAPI-Backend-Ausbau erforderlich |
| Operations, GraphQL, Asynchronität, Subscriptions | offen | keine entsprechenden Serverfähigkeiten deklariert | eigener Meilenstein nach Persistenz/Auth |
| Dokumente, Messaging, Workflow, Compartments | offen/teilweise | Bundles lokal lesbar; vorhandener Analyse-Workflow | Kein FHIR-Messaging- oder Dokumentenserver |
| Security, Signaturen, Consent, Audit | offen | Loopback-Demo; PR #1 separat | OAuth/SMART, Rechte, AuditEvent, Signaturen und Betriebskonzept fehlen |
| Mappings, v2, v3, CDA, klinische Regeln | offen | keine Umsetzung behauptet | Eigene fachliche Spezifikation und Tests nötig |
| KI-Vorschläge | lokale Zusatzfunktion | vorhandenes `workflow_ai.py` weiterverwendet | bestehende Mocktests; deaktiviert ohne Modell, keine automatische Datenkorrektur |

## Tests und nächste Schritte

```bash
python -m pytest -q                  # Unit-Tests, echte Netzwerkaufrufe blockiert
OHE_VALIDATOR_JAR=/path/to/validator_cli.jar \
OHE_VALIDATOR_CACHE=/path/to/cache-home \
python -m pytest -m integration -q   # separat, echter Java-Validator
```

Die Integrationstests prüfen einen synthetischen Patienten und das tatsächliche
CapabilityStatement gegen FHIR R4. Ohne expliziten JAR-Pfad werden sie übersprungen.
Ein leerer Paketcache kann Downloads auslösen. Die offiziellen OperationOutcome-
Beispiele liegen lokal mit Herkunft und Hash; Unit-Tests laden sie nicht nach.

Priorisierte Fortsetzung:

1. Paket-/Dependency-Lock, R4B/R5-Integration und mehr offizielle Beispielkorpora.
2. Profilgenerator um verschachtelte Regeln erweitern und jede Mutation am echten
   Validator bestätigen; anschließend Slicing/Bindings/Constraints systematisch erweitern.
3. Persistenten HAPI-Server versioniert anbinden; definierte Schreibinteraktionen,
   Zugriffskontrolle und Audit mit unabhängigen Conformance-Tests absichern.
4. Terminologie, erweiterte Suche und Subscriptions je als getesteten Meilenstein.
   KI bleibt eine gekennzeichnete Empfehlungsschicht, keine Konformitätsinstanz.
