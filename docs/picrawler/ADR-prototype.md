# ADR-Entwurf: isoliertes PiCrawler-Testbett

- Status: implementierter Prototyp auf eigenem Branch; keine projektweite Simulatorentscheidung
- Datum: 2026-11-10
- Auftrag: Issue #30, vorgezogene Vorarbeit ohne Eingriff in Claudes laufende Arbeit
- Bezug: ADR 0010, ADR 0012, Roadmap Phase 4/5

## Kontext

Der Nutzer möchte die PiCrawler-Simulation parallel vorbereiten. Auf `main`
(`ed62d4a4c158219084e202248df1de5bceea0358`) existiert ein `Body`-Entwurf mit
`reset`, `observe`, `act`, `available_actions`. Auch der geprüfte aktive Branch
`claude/28-vergleichsbasis` (`1217647107cbe3b27ca77b59e329db2ecea3276a`)
ändert diesen Vertrag nicht. Der produktive `IslandBody` verwendet jedoch
inselspezifische Methoden und Client-Zustand; `IslandLife` lässt sich heute
nicht einfach durch Übergabe eines anderen `Body` auf einen Roboter umstellen.

SunFounder veröffentlicht Kinematikmaße, zwölf Servos, Kamera und Ultraschall.
Ein vollständiges, verwendbar lizenziertes Herstellermodell samt Massen,
Trägheiten, Kontakt- und Lastparametern wurde nicht gefunden. Die endgültige
Wahl MuJoCo/Webots ist laut Roadmap noch offen. Das Hersteller-SDK ist GPLv3;
Quelltext und Gangtabellen werden hier nicht übernommen.

## Lokale Entscheidungen für den Prototyp

1. **Nur neue Dateien.** Code in `body/picrawler/`, Tests in `tests/picrawler/`,
   Dokumentation hier. Kern, Insel, `Body`-Vertrag, Zufallsmodul, Abhängigkeiten,
   CI und zentrale Übergabe bleiben unberührt. Der Branch bleibt ein Draft-PR.
2. **Kinematik auf ebener Fläche.** Der Körper folgt einem vorgegebenen Twist
   in festen Zeitschritten. Vier dreigelenkige Beine werden per IK dargestellt.
   Standfüße sind weltfest; Schwungfüße folgen einer vorgegebenen Bahn. Bewegung
   wird nicht aus Kräften berechnet. Tragfähigkeit und dynamische Stabilität
   sind damit ausdrücklich nicht nachgewiesen.
3. **Eigene, eindeutige Koordinaten.** SI-Einheiten (m, rad, s); Körper +x
   vorwärts, +y links, +z oben. Beinlokal +x radial nach außen, +y tangential.
   Gelenkwinkel sind mathematische Winkel dieses Modells, keine PWM-Winkel
   und keine Zusicherung von SDK-Kompatibilität. Hardware-Offsets und die
   Montageorientierung müssen am konkreten Roboter bestimmt werden.
4. **Konservative Hindernisgrenze.** Ein konfigurierbarer Kreis um den Körper
   wird kontinuierlich gegen Hindernisse und Arenagrenzen geprüft. Innerhalb
   eines Ticks gibt es feste Unterschritte. Kein Überspringen dünner Wände,
   kein Treppensteigen, keine Fuß-/Selbstkollision und kein Schlupfmodell.
5. **Sensoren getrennt von Wahrheit.** Die Beobachtung enthält modellierten
   Ultraschall und optional rohe RGB-Bilder. Weltkoordinaten, Hindernisnamen,
   Kollision und Gelenkgeometrie sind nur in Debug-/Replay-Daten verfügbar.
   Modellierte Betriebswerte sind ausdrücklich als simuliert markiert. Die
   unten beschriebene lokale Bedürfnisabbildung ist ein experimenteller Adapter,
   keine Änderung an Dörners Motivationskern.
6. **Zeit und Zufall.** Ein `act` bedeutet genau einen Tick; ungültige Aktionen
   ändern nichts. `observe` und Rendering sind lesend. Rauschen und Ausfälle
   werden einmal pro Tick über eine explizite `RandomSource` gezogen und
   zwischengespeichert. Kein globaler Zufall und keine Wanduhr im Modell.
7. **Persistenz.** Versionierter JSON-Schnappschuss mit Welt, Konfiguration,
   Körper, allen Fußbahnen, Phase, Sensorcache und Zufallszustand. Eine
   Fortsetzung im frischen Prozess muss dieselben Folgezustände erzeugen.
8. **Keine neue Laufzeitabhängigkeit.** Standardbibliothek und bereits im
   Projekt vorhandenes NumPy. Die HTML-Ansicht spielt ausschließlich gemessene
   Simulatordaten ab und hat keine Netzwerkabhängigkeit.

## Herkunft der Parameter

| Parameter | Wert | Herkunft / Status |
|---|---:|---|
| radialer Offset | 0,033 m | Herstellerkinematik, `C = 33 mm` |
| oberer Schenkel | 0,048 m | Herstellerkinematik, `A = 48 mm` |
| unterer Schenkel | 0,078 m | Herstellerkinematik, `B = 78 mm` |
| quadratischer Hüftabstand | 0,077 m | Körpermaß des Hersteller-Gangmodells; kein vollständiges Chassis-Außenmaß |
| nominelle Körperhöhe / lokale Fußreichweite | 0,060 / 0,085 m | austauschbare Modellwahl |
| Kollisionsradius | 0,180 m | konservative Modellwahl, nicht vermessen |
| Kameraauflösung / horizontaler Blickwinkel | 48 × 32 / 60° | Modellwahl, keine kalibrierte Hardwareintrinsik |
| Ultraschallbereich | 0,02–4,0 m | konservative Modellwahl anhand widersprüchlicher Herstellerangaben 4/5 m |
| Rauschen / Ausfallrate | standardmäßig 0 / 0 | idealer Sensor; optionale experimentelle Parameter |

## Späterer Integrationsschritt

Die wiederverwendbaren Bestandteile sind Kinematik, Einheiten, Testarenen,
Sensorvertrag, reproduzierbare Szenarien, Replay und Körperadapter. Vor der
Anbindung müssen eine Perzeptionsschicht die Sensordaten auf PSI-Schemata
abbilden und ein Aktionsadapter PSI-Absichten in Körperbefehle übersetzen.
Erst dann lässt sich dieselbe Kognition mit einem anderen Körper prüfen.

MuJoCo/Webots, vermessene Kamera-/Motor-/Kontaktparameter und der reale
Hardwaretransport bleiben eigene Entscheidungen. Dieses
Dokument nimmt weder eine globale ADR-Nummer noch die Simulatorwahl vorweg.

## Ergänzung: Betriebsphysik und vorbereitete Adapter (2026-11-10)

Der Nutzer hat physikalische Annahmen und die Vorarbeiten Kalibrierung,
Wahrnehmungstests und Mock-Bridge ausdrücklich beauftragt. Sie bleiben innerhalb
der drei isolierten PiCrawler-Verzeichnisse.

1. Ein austauschbares, deterministisches elektrisches und thermisches Modell
   ergänzt die Kinematik: 2S-Akku mit Ladungsbilanz und Innenwiderstand,
   lastabhängiger Verbrauch sowie ein thermisches CPU-RC-Modell. Zahlen für
   Kapazität, Lasten und Kühlung sind gekennzeichnete Annahmen, keine Messungen
   des konkreten Geräts. Das Modell löst weiterhin keine Kontaktkräfte.
2. Akkuspannung, geregelte Versorgung und CPU-Kernspannung bleiben verschiedene
   Größen. Nicht modellierte bzw. auf Hardware nicht verfügbare Messungen sind
   `None`, nicht erfundene Sensorwerte. Ladezustand ist ein Modellzustand und
   wird nicht als direkt aus Spannung gemessener Prozentsatz ausgegeben.
3. Das lokale Profil bildet Energiemangel auf `hunger` (Hunger) und thermische/
   elektrische Gefährdung auf `damage` (Schaden / Integritätsbedarf) in [0, 1]
   ab. Es behauptet keine bereits eingetretene Beschädigung. Durst, Nukleo und
   kognitive Bedürfnisse erhalten keine willkürlichen elektrischen Surrogate.
   Der Motivationskern und seine Skalierung bleiben unberührt.
4. CPU-Last und Umgebungstemperatur sind explizite Experimentbedingungen.
   Laden wird nicht als überall verfügbare Roboteraktion erfunden. Bei leerem
   Akku bzw. Modellabschaltung sind keine Motorbewegungen mehr möglich; die
   Simulation kann zum Beobachten und Abkühlen weiter ticken. Thermische
   CPU-Drosselung wird als Signal und CPU-Leistungsreduktion modelliert, nicht
   mit einem unkalibrierten mechanischen Geschwindigkeitsfaktor gleichgesetzt.
5. Schnappschüsse erhalten Version 2 einschließlich Energiemodell, Umgebung,
   Bedarfskonfiguration und historischen Warnflags. Version-1-Schnappschüsse
   bleiben mit deaktiviertem Energiemodell lesbar. JSON-Fortsetzung muss wieder
   identisch sein; Beobachten verbraucht weder Zeit noch Energie.
6. Der Kalibriercollector liest nur verfügbare Werte; Servo-/GPIO-Ausgaben
   fehlen. Die Bridge nutzt explizite Simulationsticks, Sitzungen und
   Sequenzen. Transport, Wiederholung, Ablauf und Beobachtungsfrische sind
   ohne Hardware testbar. Wahrnehmung verarbeitet nur Sensorbeobachtungen,
   keine Namen oder Positionen aus der Weltwahrheit.
7. Die interaktive Ansicht zeigt Welt, Crawler, Kamerabild, Messwertverläufe
   und abgeleitete Bedarfe desselben aufgezeichneten Laufs. Das Ressourcenszenario
   startet ausdrücklich mit warmem Prozessor und niedrigem Akkustand; die
   Zeit wird nicht heimlich beschleunigt und es agiert kein angebundenes PSI.
8. Ein optionaler Medienexport darf dieselben Aufzeichnungen mit extern
   bereitgestelltem Matplotlib und FFmpeg als PNG/MP4 darstellen. Seine Imports
   sind lokal und verzögert; Simulator und HTML-Replay behalten NumPy als
   einzige Projektabhängigkeit. Der Export benötigt keinen Browser und ist
   kein Ersatz für die noch ausstehende visuelle Browserprüfung der HTML-Datei.

## Quellen

- [Hersteller-API, festgehaltener Stand](https://github.com/sunfounder/picrawler/blob/14a54bc1909d4ce8f73e95d0fc09514c974910ce/picrawler-control/references/api.md)
- [Hersteller-Kinematik und SDK](https://github.com/sunfounder/picrawler/blob/14a54bc1909d4ce8f73e95d0fc09514c974910ce/picrawler/picrawler.py)
- [Action Gallery, Körpermaße](https://docs.sunfounder.com/projects/pi-crawler/en/latest/python/python_action_gallery.html)
- [Hardwareübersicht](https://docs.sunfounder.com/projects/pi-crawler/en/latest/)
- [Herstellerlizenz](https://github.com/sunfounder/picrawler/blob/14a54bc1909d4ce8f73e95d0fc09514c974910ce/LICENSE)
