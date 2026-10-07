# Impfempfehlungs-Daten strukturell prüfen

Stand: 7. Oktober 2026. Dieser Modus prüft die FHIR-R4-Basisressource
ImmunizationRecommendation 4.0.1. Er berechnet keine Impfempfehlung, prüft keine
nationalen Impfpläne und bewertet keine medizinische Eignung.

```sh
ohe workflow examples/immunization-r4 --spec immunization --corrections examples/immunization-corrections --validator validator_cli.jar --output neuer-impfdatenlauf --cache-home runtime-home --timeout 240
```

Python >=3.10, Java 21 und HL7 Java Validator 6.10.4 sind erforderlich.
Die Validator-Prüfsumme und die unveränderte offizielle StructureDefinition
stehen unter `src/ohe/specs/immunization-r4`. Basis-/Supportpakete werden aus
dem FHIR-Paketcache verwendet; dieser ist noch nicht vollständig eingefroren.
Terminologie ist offline unvollständig. `coverage` bleibt deshalb `incomplete`.

Quelle: https://hl7.org/fhir/R4/immunizationrecommendation.html
Definition aus `hl7.fhir.r4.core#4.0.1`; originale Herkunfts- und Lizenzfelder
bleiben in der JSON-Datei erhalten. Paketlizenz: CC0-1.0.

Der Katalog enthält Snapshot-Regeln mit JSON-Pointer, Version und Prüfsumme.
Direkte Zuordnung einer Meldung erfolgt nur bei expliziter Invarianten-ID,
beispielsweise `imr-1`. Pflichtfeldmeldungen werden nicht als exakt zugeordnete
Invarianten ausgegeben. Nationale Profile und narrative Anforderungen sind
damit nicht vollständig umgesetzt.

Die acht synthetischen Beispiele umfassen einen strukturellen Referenzfall
sowie fehlende Pflichtfelder, fehlende Krankheit/Impfstoffangabe, eine
unzulässige positiveInt-Zahl und zwei gleichzeitig gesetzte Choice-Typen.
Die Korrektur stellt den künstlichen Referenzzustand wieder her; sie ist keine
allgemeine Reparaturregel und darf nicht auf echte medizinische Daten übertragen
werden. Freitext-Testwerte stellen keine nutzbare Impfempfehlung dar.

Der Bericht zeigt Ressourcen, Befunde, Regelbelege und erneute Prüfung.
Die HTML-Ansicht startet selbst keinen Validator; neue Läufe starten über den
obigen Befehl. `--spec medication` bleibt der Standard für den bisherigen
Medikationsmodus. Falsche Ressourcentypen werden als nicht prüfbar dokumentiert.
Ein Prozess-Exitcode 0 ersetzt keine Auswertung der OperationOutcome-Befunde.
