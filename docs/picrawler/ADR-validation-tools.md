# Lokale Entscheidung: Belastungsmatrix und Messdatenwerkzeuge

- Status: für die isolierte Vorarbeit angenommen
- Datum: 2026-11-11; Issue #35; aufbauend auf PR #31
- Keine projektweite ADR-Nummer, keine neue Abhängigkeit

Die Vorarbeit bleibt in den drei PiCrawler-Verzeichnissen. Global Workspace,
PSI-Kern, Insel, Paper, zentrale Übergabe und Claudes Versuchsreihen bleiben
unberührt. Ein eigener Draft-PR richtet sich zunächst gegen den PR-31-Branch.

## Entscheidungen

1. Die Belastungsmatrix kombiniert explizite Seeds, Energie-/Sensor-/Linkprofile.
   Sie führt den vorhandenen Body und die Mock-Bridge aus; keine zweite Physik.
   Invarianten prüfen Takt, Ladungs-/Energiebilanz, Abschaltung, Stop, Sensorcache,
   Retry-Verhalten und exakte Body-Fortsetzung nach JSON-Checkpoint.
2. Ergebnisse erhalten Konfiguration, Runtime-Versionen, Quellrevision und
   SHA-256-Fingerprints der beteiligten Python-Dateien. Wiederaufnahme überspringt
   nur passende, unbeschädigte Erfolgsberichte. Fehler erhalten Aktionsspur und
   letzten Zustand. Neue Ausgaben ersetzen keine bestehenden Dateien stillschweigend.
3. Ein separates versioniertes Messdatenformat trägt Einheit, Quelle, Methode,
   Gerät, Zeitpunkt mit Zeitzone und Herkunft `synthetic` oder `measured`.
   CSV-Import verwendet explizite Spaltennamen mit SI-Einheiten. Unbekannte Werte
   bleiben nur dort erlaubt, wo sie fachlich sinnvoll sind (fehlendes Echo).
4. Drei begrenzte Schätzungen: Akku-Innenwiderstand aus bekanntem Leerlaufwert,
   Laststrom und Klemmenspannung; thermisches R/C aus zeitlich geordneten
   Temperaturverläufen mit bekannter CPU-Verlustleistung und Umgebung;
   Entfernungs-Offset, Streuung und Ausfallquote aus bekannten Referenzabständen.
   Keine Ableitung von SOC aus Momentanspannung, keine Servo-/PWM-Kalibrierung.
5. Nur als `train` markierte Daten bestimmen Parameter. `validation` wird
   separat ausgewertet. Thermische Intervalle über eine Teilungsgrenze werden
   ausgeschlossen. Die RC-Schätzung nutzt die exakte Intervalllösung;
   unzureichend identifizierbare Versuche werden abgewiesen. Residuen sind
   deskriptiv, keine Konfidenzintervalle oder Hardware-Gütebescheinigung.
6. Der vorhandene Profilvertrag bleibt unverändert. Exportiert werden nur
   darstellbare Parameter. Synthetische Ergebnisse erhalten `assumed`, niemals
   `measured`. Entfernungsoffset und empirische Standardabweichung haben keinen
   gleichwertigen Parameter im bisherigen idealen Strahlmodell und werden
   deshalb ausschließlich im Schätzbericht abgelegt.

## Grenzen

Messqualität und Eignung des Ersatzmodells müssen am Gerät geprüft werden.
Ein belastetes CPU-/PMIC-Signal ist keine vollständige Akkustrommessung.
Kontaktkräfte, Netzwerktransport, Hardware-Watchdog und visuelle Browserabnahme
werden durch dieses Paket nicht eingeführt oder behauptet.
