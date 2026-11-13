# Entscheidungsvorlage: nächste Simulationsbasis

- Status: angenommen am 2026-11-12: MuJoCo als optionales zweites Backend;
  Umsetzung in Issue #42, siehe [ADR-mujoco.md](ADR-mujoco.md)
- Datum: 2026-11-11; Anschluss an Issue #37 / Draft-PR #38
- Diese Vorlage ist keine angenommene globale Architektur-ADR.

## Was die abgeschlossene Vorarbeit bereits trennt

Der geschlossene Benchmark, zeitliche Sensorverarbeitung und Controller-
Prozessgrenze sind unabhängig vom PSI-Kern verfügbar. Das bisherige Modell
bewegt einen kinematischen Körper innerhalb einer konservativen Hülle.
Es berechnet weder Tragkräfte noch Gleichgewicht, Schlupf oder Servo-Dynamik.

Die Entwicklungsfahrten zeigen daneben eine eigene Wahrnehmungsgrenze:
Seitliche Körperkontakte können auftreten, obwohl der schmale vordere
Entfernungsstrahl ausreichend Raum meldet. Mehr Kontaktphysik allein würde
diese fehlende Beobachtung nicht beseitigen. Aktive Abtastung und visuelle
Geometrie bleiben ein separates zukünftiges Arbeitsfeld.

## Konkrete Architekturwahl

Soll der nächste größere Robotikschritt ein optionales **MuJoCo-Dynamikbackend**
erhalten, oder soll **Webots** die externe Simulationsumgebung bilden?
Das wäre eine grundlegende neue Modell-/Abhängigkeitsentscheidung und wird
deshalb nicht stillschweigend innerhalb der Referenzcontroller-Vorarbeit getroffen.

| Aspekt | MuJoCo | Webots |
|---|---|---|
| Bestätigte offizielle Schnittstelle | Bibliothek mit C-API und Python-Bindings; MJCF-Modelle, auch URDF-Import | Robotik-Anwendung mit Python-Controller-API und Weltdateien |
| Einbindung in das bisherige Projekt | Als zusätzliches Python-Body-Backend vorgeschlagen | Als getrennte Simulatoranwendung mit Adapter vorgeschlagen |
| Automatisierung laut Dokumentation | Explizites schrittweises Simulieren über die API | CLI mit Simulationsmodus, `--batch` und `--no-rendering` für die Hauptansicht |
| In dieser Session tatsächlich getestet | Keine Installation oder Engine-Ausführung | Keine Installation oder Engine-Ausführung |

Die Zeilen zur gewünschten Einbindung sind Projektvorschläge, keine bereits
implementierten Fähigkeiten. `--no-rendering` wird nicht als Nachweis einer
ohne weitere Einrichtung nutzbaren Kamera-/Headless-Konfiguration ausgegeben.

## Empfehlung und reviewbarer Folgeschritt

Für die bestehende Python-Struktur empfehle ich **MuJoCo als optionales zweites
Backend**, bei unveränderter kinematischer Referenz. Das ist eine Einschätzung
zum Integrationsaufwand, kein ausgeführter Leistungsvergleich gegen Webots.

Bei Zustimmung würde das nächste Arbeitspaket in dieser Reihenfolge arbeiten:

1. Eigene Modellbeschreibung mit vier Beinen und zwölf Gelenken; Segmentlängen
   aus dem vorhandenen Profil, Massen/Trägheiten/Reibung/Antriebswerte ausdrücklich
   als noch zu messende Annahmen. Kein fremder SDK-/Gangtabellencode.
2. Zuerst passiven Stand, Gravitation, Gelenkgrenzen und Kontaktbeobachtung
   prüfen. Keine Behauptung bereits kalibrierter Gänge oder realer Stabilität.
3. Explizite Antriebsgrenzen und lokale Gelenkregelung, danach eigene Gangtests.
4. Gleichen sensorbeschränkten Controllervertrag und die vorhandenen
   Benchmark-Aufgaben wiederverwenden. Welt-/Kontaktwahrheit bleibt Debugging.
5. Eigene versionierte Snapshots und festgelegte Reproduzierbarkeitsprüfungen
   für die gewählte Engine-Version. Die bestehenden PSI-/Insel-Golden-Master-
   Toleranzen und die kinematischen Regressionen werden nicht abgeschwächt.

Eine Engine ersetzt weder die Geräteidentifikation noch Messungen von Masse,
Montage, Servo-Offsets und Leistungs-/Kühlparametern. Sie kann aber das bisher
bewusst ausgelassene dynamische Verhalten als untersuchbares Modell ergänzen.
PSI-/Workspace-Integration und Hardwaretransport bleiben auch dann getrennt.

## Geprüfte Primärquellen

- [MuJoCo: offizielle Übersicht](https://mujoco.readthedocs.io/en/stable/overview.html)
  – Modellbeschreibung, Bibliothek, Kontakt-/Gelenkdynamik und API-Schritte.
- [MuJoCo: offizielle Python-Bindings](https://github.com/google-deepmind/mujoco/blob/main/python/README.md)
  – Python-Anbindung und Bereitstellung der Bibliothek.
- [Webots: offizieller Python-Leitfaden](https://github.com/cyberbotics/webots/blob/master/docs/guide/using-python.md)
  – Controller-API und Python-Start.
- [Webots: offizielle Startoptionen](https://github.com/cyberbotics/webots/blob/master/docs/guide/starting-webots.md)
  – Modi, Batch und Hauptansicht-Rendering.

Quellenstand geprüft am 2026-11-11. Kein Kosten-, Installations-, Lizenz- oder
Performanceergebnis einer tatsächlichen lokalen Engine-Erprobung behauptet.
