# Bridge mit simuliertem Gegenüber

`psi_gw.body.picrawler.bridge` stellt einen ausführbaren Protokoll- und
Verbindungstest bereit. Der vorhandene `PiCrawlerSimBody` ist das Gegenüber.
Die Nachrichten bestehen aus versioniertem JSON; die Übertragung in diesem
Modul läuft ausschließlich im Speicher. Es gibt keine Sockets, keinen
Netzwerkserver, keine Threads und keine Wanduhr. ROS, MQTT und Hardware-SDKs
werden nicht benötigt.

Die spätere Bridge-Technik bleibt offen. Ein anderer Transport kann dieselben
Nachrichten an `BridgeEndpoint.receive()` übergeben und die Antworten
zurückliefern. Ein Hardwareadapter muss darüber hinaus die tatsächliche
Ausführung, den unabhängigen Motor-Watchdog und die Anmeldung umsetzen.

## Kleines vollständiges Beispiel

Aus dem Repository mit installiertem Paket beziehungsweise `PYTHONPATH=src`:

```python
from psi_gw.body import Action
from psi_gw.body.picrawler.body import PiCrawlerSimBody, SimConfig
from psi_gw.body.picrawler.bridge import (
    BridgeEndpoint, InMemoryTransport, Reply, Request,
)

body = PiCrawlerSimBody(config=SimConfig(camera_enabled=False))
endpoint = BridgeEndpoint(body, watchdog_ticks=5)
link = InMemoryTransport(endpoint)
session = link.connect("controller")

request = Request(
    session=session,
    request_id="drive-1",
    sequence=1,
    issued_tick=link.tick,
    deadline_tick=link.tick + 4,
    action=Action("drive", {"forward_mps": 0.02}),
)
wire = request.to_json()
link.send(wire)
link.step()

ack = Reply.from_json(link.receive()[0])
assert ack.status == "completed"
assert ack.execution_tick == body.tick
observation = ack.fresh_observation(
    now_tick=link.tick, max_age_ticks=0, session=session,
)
print(ack.execution_tick, observation.sensors["ultrasonic"])
```

`action=None` stellt eine reine Beobachtungsanfrage. Auch dabei läuft ein
Simulatortick mit `stop`; der Sensorcache wird frisch aufgenommen. Die Anfrage
verlängert nicht den Motor-Watchdog. `observe()` am Körper selbst bleibt ein
lesender Zugriff ohne Tick und ohne neue Zufallszüge.

## Schnittstellen

| API | Verhalten |
|---|---|
| `Request(...).to_json()` / `Request.from_json(text)` | Anfrage serialisieren beziehungsweise strikt prüfen |
| `Reply.from_json(text)` / `reply.to_json()` | ACK prüfen beziehungsweise serialisieren |
| `reply.fresh_observation(now_tick=..., max_age_ticks=..., session=...)` | Alter und optional Verbindung prüfen; unabhängige Kopie der Beobachtung liefern |
| `BridgeEndpoint(body, watchdog_ticks=5, max_command_age_ticks=20, max_pending=8, reply_cache_size=32)` | Körper mit begrenzter Warteschlange und Antwortcache verbinden |
| `endpoint.connect(client_id)` | Alte Verbindung sperren, einen Stop-Tick ausführen, neue Session liefern |
| `endpoint.receive(text)` | Anfrage prüfen und vormerken; direkte ACK-Zeichenkette oder `None` zurückgeben |
| `endpoint.step()` | Genau einen regulären Körpertick ausführen; Liste fertiger ACKs liefern |
| `endpoint.disconnect()` | Warteschlange und Cache leeren, alte Session sperren, einen Stop-Tick ausführen |
| `InMemoryTransport(endpoint, capacity=16)` | Zwei begrenzte Übertragungswarteschlangen anlegen |
| `link.send(text, request_delay_ticks=0, reply_delay_ticks=0, drop_request=False, drop_reply=False)` | Eine Übertragung mit expliziter Fehlerkonfiguration anstoßen |
| `link.step(ticks=1)` | Fällige Anfragen zustellen, Endpunkt weiterschalten, Antworten terminieren |
| `link.receive()` | Alle inzwischen zugestellten ACK-Zeichenketten abholen |
| `link.connect(client_id)` / `link.disconnect()` | Zusätzlich alle alten Transportpuffer verwerfen |

`endpoint.tick` und `link.tick` sind der aktuelle `body.tick`. Der Transport
besitzt keine zweite Uhr. Ein exklusiver Endpunkt steuert den Körper; der
Aufrufer führt währenddessen keine eigenen `body.act()`- oder `reset()`-Aufrufe
aus. `connect` und `disconnect` bewegen den Körper nicht weiter, führen aber
jeweils einen regulären Stop-Tick einschließlich neuer Messwerte aus.

## Nachrichtenformat Version 1

Eine Fahranfrage:

```json
{
  "version": 1,
  "kind": "request",
  "operation": "command",
  "session": "controller:1",
  "request_id": "drive-1",
  "sequence": 1,
  "issued_tick": 1,
  "deadline_tick": 5,
  "action": {
    "name": "drive",
    "params": {"forward_mps": 0.02}
  }
}
```

Eine Beobachtungsanfrage verwendet `operation: "observe"` und `action: null`.
Die übrigen Felder bleiben gleich. Die Sequenz gilt für **alle** Anfragen einer
Session; sie beginnt bei 1. `request_id` ist eine Korrelation für den Aufrufer,
die Identität für die Ausführung bilden Session und Sequenz gemeinsam.

Eine Antwort enthält:

| Feld | Bedeutung |
|---|---|
| `version`, `kind` | `1`, `"ack"` |
| `session`, `request_id`, `sequence`, `operation` | Eindeutige Zuordnung zur Anfrage |
| `status` | `completed`, `expired` oder `rejected` |
| `reason` | Bei Erfolg `null`, sonst der dokumentierte Ablehnungsgrund |
| `server_tick` | Endpunkttick, zu dem diese Antwort erzeugt wurde |
| `execution_tick` | Tick der abgeschlossenen Körperaktion; sonst `null` |
| `observation` | `tick`, `sensors`, `internal` des Körper-Sensorcaches |

Bei einer erfolgreich erledigten Beobachtungsanfrage bleibt `execution_tick`
ebenfalls `null`: Es wurde keine angeforderte Körperaktion ausgeführt.

IDs haben 1–64 ASCII-Zeichen und beginnen alphanumerisch; danach sind zusätzlich
`_`, `.`, `:`, `-` zulässig. Die Clientkennung für `connect` ist höchstens 32
Zeichen lang. Ticks und Sequenzen sind echte ganze Zahlen bis `2**53 - 1`;
Boolesche Werte zählen nicht als Zahlen. Doppelte JSON-Schlüssel, unbekannte
Felder, unbekannte Versionen, NaN und Unendlich werden zurückgewiesen.
Anfragen sind auf 16 KiB, Antworten auf 2 MB begrenzt.

Erlaubte Aktionen sind `drive`, `stop` und `stand`. `drive` nimmt ausschließlich
endliche `forward_mps`, `lateral_mps` und `yaw_rps` entgegen; ausgelassene Werte
sind null. Die konkreten Geschwindigkeitsgrenzen prüft der Körper. `stop` und
`stand` haben keine Parameter.

Die Beobachtung ist ebenfalls geprüft: Ultraschallstatus und Distanz müssen
zueinander passen, Kameradaten müssen exakt die angegebenen RGB8-Abmessungen
haben. Die optionale Energietelemetrie behält `source: "simulated"`; ihr Schema
umfasst die Größen aus `energy.py` einschließlich typisierter aktueller und
historischer Flags. Eine reale Telemetriequelle wird nicht durch Umbenennen
dieser Simulationswerte vorgetäuscht. Unbekannte interne Eingänge bleiben
`null`; Debugpose, Objektidentitäten und zusätzliche nicht deklarierte
Sensorfelder gelangen nicht in das Protokoll.

## Zeit, Ablauf und Verbindungsfehler

### Deadline und Alter

`issued_tick` und `deadline_tick` beziehen sich auf die bekannte Endpunktuhr.
Die Deadline ist einschließlich: Die Aktion muss bis zu diesem Tick fertig
sein. Eine Anfrage bei Tick 10 mit Deadline 11 kann im nächsten Schritt
abgeschlossen werden; eine Deadline 10 ist bereits zu spät. Die Deadline
wird beim Empfang **und erneut vor der Ausführung** geprüft. Auch eine weit
entfernte Deadline hebt `max_command_age_ticks` nicht auf.

Der Simulationsaufrufer kennt die Uhr direkt. Die Synchronisierung eines
räumlich getrennten Controllers ist eine spätere Transportaufgabe; es werden
keine unsynchronisierten PC- und Pi-Wanduhren miteinander verglichen.

### Wiederholungen und begrenzter Cache

Bei ausbleibender Antwort sendet der Aufrufer **dieselbe Anfrage mit derselben
Sequenz, ID und denselben Zeitangaben** erneut. Eine noch wartende identische
Anfrage erzeugt keine zweite Aktion. Eine erledigte Anfrage liefert die
gespeicherte Antwort bytegleich zurück. Geänderte Daten unter derselben
Sequenz werden als `sequence_conflict` abgelehnt.

Der Antwortcache ist begrenzt. Ist eine alte Antwort verdrängt, liefert der
Endpunkt `replay_too_old`; die monotone Sequenzgrenze verhindert trotzdem eine
zweite Ausführung. Die ursprüngliche Ausführung kann dann aus dieser
Verbindung nicht mehr rekonstruiert werden. Das Protokoll verspricht deshalb
höchstens eine Ausführung je Sequenz, keine verlustfreie Zustellung.

Wichtige Ablehnungsgründe:

| Grund | Verhalten |
|---|---|
| `deadline`, `stale` | `expired`; die Aktion wird nicht ausgeführt |
| `wrong_session` | Nachricht gehört nicht zur aktiven Verbindung |
| `sequence_conflict` | Gleiche Sequenz, andere Anfragedaten |
| `sequence_gap` | Frühere Sequenz fehlt; die Anfrage wurde noch nicht aufgenommen |
| `replay_too_old` | Sequenz bereits verbraucht, Antwort nicht mehr im Cache |
| `future_tick` | Angeblicher Erzeugungszeitpunkt liegt aus Sicht der Endpunktuhr in der Zukunft |
| `queue_full` | Endpunkt kann keine weitere Aktion vormerken |
| `invalid_action` | Körper lehnt die Aktionsparameter vor der Zustandsänderung ab |

Nur neue Anfragen mit der genau nächsten Sequenz werden aufgenommen.
`sequence_gap` belegt noch keinen Sequenzplatz; nach Zustellung der fehlenden
Anfrage darf dieselbe spätere Anfrage erneut versucht werden. Sobald eine
Anfrage mit der nächsten Sequenz aufgenommen oder wegen `queue_full`,
`future_tick` oder Ablaufs abgelehnt wurde, ist ihre Sequenz verbraucht und
ihr Ausgang wird gespeichert. Für einen neuen Versuch mit anderen Parametern
ist eine neue Sequenz nötig.

### Beobachtungsalter

Eine Wiederholung verändert weder `server_tick` noch `observation.tick` der
gespeicherten Antwort. Eine verspätete ACK bleibt daher erkennbar alt.
`fresh_observation()` lehnt zu alte Werte mit `StaleObservation` ab; mit dem
optionalen `session`-Argument auch Werte einer fremden Verbindung. Der
Aufrufer entscheidet die zulässige Altersgrenze und fordert nötigenfalls
eine neue Beobachtung mit neuer Sequenz an.

### Stop und Watchdog

Ein `drive` gilt für genau einen Tick. Ohne neue ausführbare Aktion wird immer
`stop` ausgeführt; die letzte Geschwindigkeit wird nie stillschweigend
weiterverwendet. Nach `watchdog_ticks` ohne erfolgreich abgeschlossenen neuen
Aktionsauftrag wird `endpoint.watchdog_tripped` wahr. Beobachtungsanfragen,
abgelaufene Nachrichten und Wiederholungen alter ACKs verlängern diese Frist
nicht. Ein frischer erfolgreicher Aktionsauftrag hebt den Timeout wieder auf.

`stop` bedeutet im aktuellen Körpermodell Nullgeschwindigkeit bei gehaltener
Haltung. Es bedeutet weder stromlose Servos noch einen physikalisch geprüften
Not-Halt. Der deterministische Watchdog schreitet nur mit `step()` voran; ein
stehengebliebener Python-Prozess kann damit keine echte Hardware absichern.
Ein realer Controller braucht einen unabhängigen, zeitgesteuerten Watchdog.

### Disconnect und Reconnect

Ein Disconnect verwirft vorgemerkte Aktionen und sperrt die Session. Reconnect
vergibt eine neue monoton nummerierte Session, setzt die Anfrage-Sequenz auf 1
und verwirft beide Transportpuffer. Eine nachträglich eingespeiste alte
Anfrage wird auch dann abgelehnt, wenn sie wieder Sequenz 1 trägt.

Diese Zusicherung gilt über die Lebensdauer des `BridgeEndpoint`. Sein
Sessionzähler und Antwortcache sind hier nicht persistent. Nach einem echten
Serverneustart braucht eine Hardwareintegration eine neue, nicht wiederholte
Bootkennung beziehungsweise persistentes Fencing. Anmeldung, Authentifizierung,
Verschlüsselung und das physische Motorprotokoll sind nicht simuliert.

Ein unerwarteter Fehler während `act()` sperrt die Session und verwirft
weitere Arbeit; die betroffene Sequenz wird nicht erneut aufgerufen. Der
Adaptervertrag verlangt eine atomare Körperaktion: vollständig abgeschlossen
oder Fehler vor der Zustandsübernahme. Ein Hardwareadapter muss unklaren
Ausführungszustand und unabhängigen Stop ausdrücklich behandeln.

## Deterministische Fehlerszenarien

```python
# Anfrage kommt erst nach drei idle ticks am Endpunkt an.
link.send(wire, request_delay_ticks=3)

# Aktion läuft, aber die ACK wird vier Ticks zurückgehalten.
link.send(wire, reply_delay_ticks=4)

# Expliziter Verlust einer Anfrage oder einer ACK.
link.send(wire, drop_request=True)
link.send(wire, drop_reply=True)
```

Ein Request-Delay `N` erzeugt `N` Idle-Ticks vor dem Empfang; danach braucht
die Ausführung ihren einen Körpertick. Das Reply-Delay beginnt bei der
Erzeugung der ACK. Fehler werden nicht zufällig ausgewählt: dieselbe Folge
von Sendungen, Parametern und `step()`-Aufrufen führt zum selben Ergebnis.

Die Request-Queue wirft bei Überfüllung `QueueFull`, bevor die Nachricht
angenommen wird. Eine volle Reply-Queue verwirft die betreffende ACK; der
Endpunktcache erlaubt einen späteren identischen Retry. `request_drops`,
`reply_drops` und `queued_counts` machen diese Fälle sichtbar. Warteschlangen,
vorgemerkte Aktionen, Antwortcache und Nachrichtengröße haben feste Grenzen.

## Prüfungen

```bash
PYTHONPATH=src python -m pytest tests/picrawler/test_bridge.py
```

Die Tests verwenden den tatsächlichen kinematischen Körper und prüfen unter
anderem normalen Fahrbefehl, verzögerte ACK und Retry ohne doppelte Bewegung,
Verlust in beiden Richtungen, Deadline während des Wartens, Sequenzkonflikte,
Antwortcache-Verdrängung, begrenzte Queues, alte Nachrichten nach Reconnect,
Watchdog trotz Telemetrieverkehr, frische Beobachtungen und strikte JSON-,
Bild- und Energietelemetrieprüfung. Sie öffnen keine Netzwerkverbindung und
steuern keine Hardware an.
