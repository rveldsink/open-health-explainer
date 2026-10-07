# Lokaler Prüfablauf für kleine Softwareteams

Stand: 5. Oktober 2026. Entwicklungswerkzeug mit synthetischen Beispielen,
kein zertifiziertes Medizinprodukt und kein vollständiger Konformitätsnachweis.

## Direkt ausprobieren

Der vorbereitete Bericht liegt unter `output/fhir-lab/workflow-corpus/index.html`.
Er öffnet sich auch ohne Webserver direkt im Browser. Dort sind 26 echte
Prüfergebnisse und zwei erneut validierte Korrekturen enthalten. Ein neuer
Validatorlauf startet über die Kommandozeile, nicht durch die HTML-Ansicht.

Installation im Repository: `python -m pip install .` (Python >=3.10).
Java 21 und die festgelegte Validator-JAR werden zusätzlich benötigt, siehe
[Versionen und Bezugsquellen](medication-specification.md).

```sh
ohe workflow examples/medication-corpus --corrections examples/workflow/corrections --validator validator_cli.jar --output lauf-001 --cache-home runtime-home --timeout 480
```

`--java` erlaubt den vollständigen Pfad zur Java-Datei. Alle JSON-Dateien direkt
im Eingabeordner werden verarbeitet, keine Unterordner. Je Datei wird genau eine
MedicationRequest erwartet; Bundles/andere Ressourcentypen sind nicht unterstützt.
Korrekturen liegen separat und haben denselben Dateinamen wie das Original.
Der Ausgabeordner muss neu sein. Eingabedaten werden nicht überschrieben.

Der Validator lädt die Profile nur einmal für alle Ausgangs- und Korrekturdateien.
Die Zuordnung erfolgt über die explizite operationoutcome-file-Extension, nie über
die Reihenfolge. Unbekannte/mehrdeutige Zuordnungen führen zu nicht prüfbar.
Fehlerhafte Eingaben werden dokumentiert; andere Dateien werden weiter bearbeitet.

## Was das Team erhält

- Interaktiven HTML-Bericht mit Suche, Ergebnisfilter und vier Detailansichten.
- Meldungen nach Schweregrad, deutsche Erklärungen und technische nächste Schritte.
- Direkte Regelbelege über offizielle Invarianten-IDs, Version, JSON-Pointer und Quelldatei.
- Unveränderte OperationOutcome und Logdatei; keine erfundenen Prüfergebnisse.
- Bearbeitbaren JSON-Entwurf zum Download sowie Vergleich nach erneuter Prüfung.
- Zusammenfassung wiederkehrender Fehlerfamilien und maschinenlesbaren Gesamtbericht.

Die Angabe „keine Fehler gemeldet“ bedeutet ausdrücklich nicht „vollständig gültig“.
coverage bleibt incomplete. Fehlende Terminologie und nicht durch Profile geprüfte
Dosierungstextkonsistenz sind offene Punkte. Änderungen an Meldungstexten können
als neue/verschwundene Befunde erscheinen; der Vergleich beweist keine Ursache.

## Optionale lokale KI

`--ai-model MODELLNAME` ruft ein bereits installiertes lokales Ollama-Modell über
http://127.0.0.1:11434/api/chat auf. Grundlage:
https://docs.ollama.com/api/chat . Es werden keine Modelle heruntergeladen und
keine kostenpflichtigen Dienste konfiguriert. Verwende ausschließlich ein lokal
rechnendes Modell; die Konfiguration des Ollama-Dienstes liegt beim Betreiber.

Die KI erhält Validatorbefunde und zugeordnete Regeln, keine zusätzlichen
Konten oder Werkzeuge. Befunde können trotzdem Angaben aus Eingabedaten enthalten.
Anfrage und Antwort werden für Nachvollziehbarkeit im Laufordner gespeichert.
Verweise auf unbekannte Befunde/Regeln werden verworfen. Das prüft die Verweise,
**nicht die fachliche Wahrheit** einer KI-Aussage. Alle Vorschläge bleiben
ungeprüfte Ursachenvermutungen. Keine automatische Änderung oder Übertragung in
Produktionssysteme. Ohne Modell: regelbasierte Erklärung, KI-Status disabled.
Bei Verbindungs-/Formatfehlern: unavailable, Validatorergebnis bleibt erhalten.
In dieser Umgebung war kein lokales Modell eingerichtet; ein echter KI-Lauf
ist daher noch nicht nachgewiesen. Adaptertests ersetzen keine Modell-Evaluation.

## Beispiele und Korrekturen

`examples/medication-corpus` enthält 26 synthetische Varianten: Referenz,
Reihenfolgeänderung, veralteter Text, geänderte Dosis, Frequenz, widersprüchliche
Zeitangaben, doppelte Zeitfenster, fehlende Dosis/Timing/Metadaten/Version,
Freitext-Mischung, unzulässige Felder, fehlende/falsche Einheit, Status, unbekanntes
Profil und Korrekturkontrolle. Herkunft/Prüfhypothesen stehen im separaten Manifest;
sie sind keine automatisch bewiesenen Erwartungen.

Die zwei Dateien unter `examples/workflow/corrections` stammen vom bekannten
synthetischen Referenzfall. Sie dienen als Testkorrekturen, nicht als allgemeine
Reparaturregel: im Kundenfall darf man weder einen Code raten noch Freitext
ungeprüft entfernen. Fehlende fachliche Informationen müssen vom Anbieter kommen.
Es wurden keine echten Firmenbeispiele beschafft oder Kontaktaufnahmen versendet.

## Aufnahme eines späteren Firmenbeispiels

Vorlage `examples/partner-case-template.json` liegt außerhalb der Eingabeordner.
Anbieter dokumentieren verwendete Profil-/Paketversion, erwartetes Verhalten,
minimale synthetische Reproduktion, Fehlerbild und Datenfreigabe. Zuerst mit
synthetischen Reproduktionen arbeiten. Personenbezug wird nicht automatisch
anonymisiert; Berichte und Downloads enthalten die vollständigen Testdaten.

## Ablage und Exitcodes

- engine/inputs: tatsächlich geprüfte unveränderte Kopien.
- engine/operation-outcomes.json, validator.log, reports.json: gemeinsame Ausführung.
- case-NNN/before/report.json und after/report.json: Einzelberichte.
- case-NNN/ai-advice.json: optionaler KI-Schritt, einschließlich Fehlerstatus.
- workflow.json, requirements.json, index.html: Gesamtergebnis, Regelkatalog, Ansicht.

Exitcode 1: mindestens ein letztes Prüfergebnis meldet Fehler; 2: mindestens ein
Lauf/Workflow-Schritt nicht prüfbar; 3: keine letzten Fehler, aber Abdeckung
unvollständig. Nachprüfung ersetzt nicht den Originalnachweis.

## Verifikation dieses Ausbaus

37 automatisierte Tests plus echte Integrationsläufe. Im gemeinsamen Lauf wurden
26 Ausgangsfälle und zwei Korrekturdateien geprüft: 19 Ausgangsfälle mit Fehlern,
7 ohne gemeldete Fehler; beide Korrekturen ohne gemeldete Fehler. Es gibt weiterhin
Warnungen/Informationen. Keine vollständige Sensitivitäts-/Spezifitätsaussage.
Browserprüfung: Fallauswahl, Regelzuordnung und Vorher-nachher-Ansicht.
Nicht veröffentlicht; kein GitHub-Push oder Website-Deployment in diesem Schritt.
