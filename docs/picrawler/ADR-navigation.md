# Bewegungsprofil und sensorbeschränkte Navigation

- Status: angenommen für unabhängige technische Vorarbeit; Alec beauftragt am 2026-11-13.
- Issue #49; eigener Branch auf Draft-PR #43. Keine neue Abhängigkeit.

## Entscheidung vor Implementierung

Das MuJoCo-Modell und die beiden bisherigen Referenzcontroller bleiben unverändert.
Ein Offline-Versuch darf Modellpose zur Identifikation von Befehlswirkung, Verzögerung,
Stopweg und Streuung verwenden. Das daraus abgeleitete versionierte Bewegungsprofil
enthält explizite Herkunft, Gültigkeitsbereich und empirische Unsicherheit. Das sind
Simulationsmessungen, keine Hardwarekalibrierung oder garantierten Fehlergrenzen.

Der neue Controller verwendet ausschließlich freigegebene RGB-/Echomessungen samt
Erwerbszeit, Bedürfniswerte und eigene ausgegebene Befehle. Eine Bewegungs-/Richtungs-
schätzung aus dem Profil ist weiterhin **keine gemessene Odometrie**. Sie trägt eine
wachsende Unsicherheit. Vergangene Messungen werden dem geschätzten Zustand zu ihrer
Erwerbszeit zugeordnet; Duplikate tragen keine neue Evidenz bei. Fehlende/veraltete
Echos sind keine freie Fahrt. Unbekannte Bedürfnisse führen zum Halt, Energiesignale
zum eingerasteten Halt.

Aktive Abtastung dreht den Körper, um mehrere Echos aus verschiedenen Richtungen
zu erhalten. Farbige Bildregionen dienen als Hinweis auf seitliche Hindernisse und
auf zusätzliche Abtastrichtungen; Farben sind keine bekannten Objektidentitäten.
Ein lokaler, befristeter Hindernisspeicher und konservative Hüllen dienen der
Wegauswahl. Kein Zugriff auf World, MuJoCo-Daten, Kontakte, Erfolg oder echte Pose.
Holonome kleine Seitwärtsschritte sind erlaubt, da das vorhandene Modell diese
Aktion bereits unterstützt. Eine gewünschte ursprüngliche Fortschrittsrichtung
ersetzt keine dem Controller mitgeteilte globale Zielkoordinate.

Ein Kameraprojektionshinweis darf bekannte synthetische Intrinsik/Montage und die
Annahme annähernd ebener Haltung verwenden; fehlende gemessene Lage und verdeckte
Fußpunkte bleiben Unsicherheiten. Er wird nicht als gemessene Tiefe bezeichnet.

Die neue Evaluation speichert mindestens den unveränderten Endpunkt bei 900
Entscheidungen. Zusätzliche Fahrzeit bis 2400 Entscheidungen ist eine getrennte
Langhorizont-Diagnose und kein nachträglicher Erfolg im früheren Zeitbudget.
Kontaktbudget 25 Ticks, Sturz- und Stopkriterien aus #43 bleiben erhalten. Keine
Abschwächung von PSI-Golden-Master- oder alten Robotertests.

## Daten und Persistenz

Entwicklung: Bewegungsprofile auf Phasen/Startwinkeln und Reibung 0,4/0,8/1,2;
Navigation nur Seeds 10/11, zusätzlich kleine explizite Sensorfixtures. Die bisherigen
Prüfseeds 1000/1001 werden nicht zur Controllerabstimmung verwendet. Neue zurückgehaltene
Seeds 2000/2001 bleiben bis zum gesicherten Code-/Parameterstand unberührt.
Verglichen werden unveränderte reaktive/Gedächtnis-Baselines und der neue Controller,
bei gleicher Physik, Sensorzustellung und Budget. Modelltruth bleibt im Evaluator.

Alle zustandswirksamen Variablen (Profil, Bewegungs-/Karten-/Abtastzustand, zeitliche
Zuordnung, Aktionscache, Controller, Body, Zustellung und Messgrößen) gehören in
versionierte JSON-Checkpoints. Frische Prozesse müssen exakt fortsetzen. Quell- und
Profilhash werden festgehalten. Nach Beginn der unabhängigen Prüfung keine
Parameteroptimierung auf deren Ergebnissen; Fehlerkorrekturen explizit dokumentieren.

## Grenzen

Keine PSI-Integration, kein SLAM mit gemessener Lage, keine neuen Sensoren, kein
Hardwaretransport. Eigenkollision/Selbstverdeckung und Modellannahmen aus #43 bleiben.
Papier-/Workspace-Arbeit und zentraler HANDOFF werden nicht verändert. Nur Alec mergt.
