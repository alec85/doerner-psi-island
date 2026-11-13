"""Write a self-contained, read-only HTML replay of recorded simulator frames.

The browser only selects and projects saved samples. It neither imports the
simulator nor advances its clock or random source. All distances are metres;
angles are radians. No network connection or third-party JavaScript is needed.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


def write_replay(
    path: str | Path, frames: list[dict[str, Any]], metadata: dict[str, Any]
) -> None:
    """Save an offline 3-D replay using the public recorded-frame dictionary.

    ``frames`` must contain at least one sample with finite, monotonically
    increasing ``time_s`` values. ``metadata`` contains the world bounds and
    obstacle boxes. Optional RGB, telemetry, need and perception samples are
    displayed when present; older recordings remain readable without them.
    Inputs must be JSON serializable with finite numbers and are never mutated.
    Default labels describe the kinematic backend. Explicit ``backend=mujoco``
    metadata selects dynamics labels; neither implies hardware calibration.
    """
    if not frames:
        raise ValueError("at least one frame is required")
    previous_time = -math.inf
    for frame in frames:
        time_s = frame.get("time_s")
        if (
            isinstance(time_s, bool)
            or not isinstance(time_s, (int, float))
            or not math.isfinite(time_s)
            or time_s < 0
            or time_s < previous_time
        ):
            raise ValueError("frame time_s must be finite, nonnegative and ordered")
        previous_time = time_s
    # HTML parsers recognize </script> even inside a JSON string. Escaping all
    # '<' characters protects the script-data element without altering the data.
    payload = json.dumps(
        {"metadata": metadata, "frames": frames},
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    html = _HTML
    if metadata.get("backend") == "mujoco":
        html = html.replace("Kinematik-Testbett", "MuJoCo · angenommene Dynamik")
        html = html.replace("Zeitdiskrete Körperbewegung, Gelenkgeometrie und einfache Sensorik auf ebener Fläche.",
                            "Aufgezeichnete MuJoCo-Kontakte, Gelenke und freie Körperbewegung mit angenommenen Modellparametern.")
        html = html.replace("Kein Nachweis für Standsicherheit, Reibung, Motorleistung oder reale Schrittweite.",
                            "Kein Nachweis realer Standsicherheit oder kalibrierter Reibung, Motorleistung und Schrittweite.")
    destination.write_text(html.replace("__REPLAY_DATA__", payload), encoding="utf-8")


_HTML = r"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark">
<title>PiCrawler · Simulations-Replay</title>
<style>
:root{--bg:#0b111b;--panel:#111c2c;--line:#253448;--muted:#9aabc0;--text:#eaf1fa;--cyan:#54ddd4;--gold:#ffcb77;--red:#ff7e8d;--blue:#7097ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}button,select,input{font:inherit}button,select{color:var(--text);background:#1a2b3f;border:1px solid #344b65;border-radius:8px;padding:9px 14px;cursor:pointer}button:hover,select:hover{background:#253e56}button:focus-visible,select:focus-visible,input:focus-visible{outline:2px solid var(--cyan);outline-offset:3px}button.active{color:#0a2027;background:var(--cyan);border-color:var(--cyan)}header{max-width:1500px;margin:auto;padding:28px 32px 20px;display:flex;align-items:center;justify-content:space-between;gap:20px}.eyebrow{color:var(--cyan);font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.18em}h1{font-size:29px;line-height:1.2;font-weight:650;letter-spacing:-.04em;margin:7px 0}header p{margin:4px 0;color:var(--muted);font-size:13px}.badge{border:1px solid #38616a;background:#142b33;color:#b6f6ed;padding:7px 11px;border-radius:20px;white-space:nowrap;font-size:12px}.layout{max-width:1500px;margin:auto;padding:0 32px 28px;display:grid;grid-template-columns:minmax(0,1fr) 280px;gap:18px}.stage{background:linear-gradient(155deg,#152338,#0f1a2a 60%);border:1px solid var(--line);border-radius:15px;overflow:hidden;position:relative}.scene-wrap{position:relative;height:clamp(350px,57vh,680px);min-height:350px}#scene{display:block;width:100%;height:100%;touch-action:none}.stage-top{position:absolute;z-index:2;left:19px;right:19px;top:17px;display:flex;align-items:center;justify-content:space-between;gap:8px;pointer-events:none}.stage-label{color:var(--muted);font-size:11px;letter-spacing:.1em;text-transform:uppercase}.views{display:flex;gap:6px;pointer-events:auto}.views button{font-size:12px;padding:6px 9px}.hint{position:absolute;bottom:13px;left:19px;color:#8296b1;font-size:11px;pointer-events:none}.legend{position:absolute;bottom:13px;right:19px;display:flex;gap:12px;flex-wrap:wrap;color:#b7c5d7;font-size:11px}.dot{width:7px;height:7px;display:inline-block;border-radius:50%;margin-right:5px}.controls{background:#0f1b2b;border-top:1px solid var(--line);padding:17px 19px}.timeline-head{display:flex;justify-content:space-between;align-items:center;font-size:12px;color:var(--muted);margin-bottom:5px}.timeline-head strong{font-variant-numeric:tabular-nums;font-weight:500;color:var(--text)}input[type=range]{accent-color:var(--cyan);width:100%;margin:8px 0;cursor:pointer}.playbar{display:flex;gap:9px;align-items:center;flex-wrap:wrap;margin-top:8px}.playbar #play{min-width:125px;background:var(--cyan);border-color:var(--cyan);color:#0a2027;font-weight:650}.playbar button{font-size:13px}.playbar label{font-size:12px;color:var(--muted)}.playbar select{font-size:12px;padding:8px}.frame-counter{margin-left:auto;font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums}.sidebar{display:flex;flex-direction:column;gap:14px}.card{background:var(--panel);border:1px solid var(--line);border-radius:13px;padding:18px}.card h2{font-size:11px;font-weight:650;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);margin:0 0 15px}.range-value{font-size:36px;letter-spacing:-.04em;font-weight:650;line-height:1.1;font-variant-numeric:tabular-nums}.range-value span{font-size:15px;color:var(--muted);font-weight:400;letter-spacing:0}.meter{height:5px;background:#24364b;border-radius:3px;overflow:hidden;margin:16px 0 10px}.meter div{height:100%;width:0;background:var(--gold);transition:width .06s linear}.small{font-size:11px;color:var(--muted);margin:6px 0}.telemetry{display:grid;grid-template-columns:1fr auto;gap:9px;font-size:12px;margin:0}.telemetry dt{color:var(--muted)}.telemetry dd{margin:0;font-variant-numeric:tabular-nums;text-align:right}.status{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--cyan)}.status i{width:6px;height:6px;background:currentColor;border-radius:50%}.status.blocked{color:var(--red)}.notes{font-size:12px;color:var(--muted);margin:0;line-height:1.6}.notes strong{color:#c5d7ea;font-weight:550}.meta{border-top:1px solid var(--line);margin-top:14px;padding-top:12px;font-size:11px;color:#7e91ab;overflow-wrap:anywhere}.camera{width:100%;aspect-ratio:4/3;display:block;background:#08101c;border:1px solid #31435a;border-radius:7px;image-rendering:pixelated}.camera-card[hidden]{display:none}footer{max-width:1500px;margin:auto;padding:0 32px 24px;color:#7489a4;font-size:11px}kbd{font:10px system-ui;color:#afc0d5;border:1px solid #35475e;border-radius:3px;padding:1px 4px}#error{display:none;background:#541f2a;color:#ffe3e8;padding:12px;margin:15px;border-radius:6px}
@media(max-width:900px){.layout{grid-template-columns:minmax(0,1fr);padding:0 18px 20px}header{padding:22px 18px 17px}.sidebar{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.sidebar .notes-card{grid-column:1/-1}.scene-wrap{height:470px}.card{padding:15px}footer{padding:0 18px 20px}}
@media(max-width:520px){header{align-items:flex-start}h1{font-size:25px}header p{font-size:12px}.badge{font-size:10px;padding:6px 8px}.scene-wrap{height:370px}.stage-top{left:12px;right:12px}.stage-label{font-size:9px}.hint{display:none}.legend{left:12px;right:12px;justify-content:center;font-size:10px}.controls{padding:14px 12px}.playbar{gap:7px}.playbar #play{min-width:113px}.frame-counter{width:100%;margin:0}.sidebar{grid-template-columns:1fr 1fr}.range-value{font-size:29px}.card h2{font-size:10px}.telemetry{font-size:11px}.camera-card{grid-column:1/-1}}
.layout{align-items:start}.telemetry-dock{padding:18px 19px 20px;background:#0d1827;border-top:1px solid var(--line)}[hidden]{display:none!important}.dock-heading{display:flex;justify-content:space-between;gap:10px;align-items:baseline;margin:0 0 14px}.dock-heading h2{margin:0;font-size:14px;font-weight:600}.source-tag{font-size:10px;color:#98d9d2;border:1px solid #315454;padding:3px 7px;border-radius:5px}.metrics-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.metric{padding:12px;background:#152439;border:1px solid #2a3c52;border-radius:9px;min-width:0}.metric-name{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em}.metric-value{font-size:24px;line-height:1.3;letter-spacing:-.025em;font-weight:600;font-variant-numeric:tabular-nums;margin:5px 0}.metric-sub{font-size:11px;color:#a6b8cb;min-height:17px}.metric .meter{margin:9px 0 3px}.metric .meter div{background:var(--cyan)}.alarms{display:flex;gap:7px;flex-wrap:wrap;margin:12px 0;min-height:20px}.alarm{font-size:11px;padding:3px 7px;border-radius:5px;border:1px solid #3b4c63;color:#b4c8df}.alarm.critical{color:#ffd0d7;background:#472431;border-color:#854251}.alarm.ok{color:#a5d7c7;border-color:#315650}.needs-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:14px}.need{padding:11px 12px;border:1px solid #35475b;border-radius:8px}.need-head{display:flex;justify-content:space-between;align-items:baseline;gap:8px;font-size:12px}.need-head strong{font-variant-numeric:tabular-nums;color:#ffd28d;font-size:16px}.need .meter{margin:9px 0 0}.need.damage .meter div{background:#f6899b}.history-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:17px}.history-card{border:1px solid #293b52;border-radius:8px;padding:10px 9px;background:#101d2e;min-width:0}.history-title{font-size:10px;color:#b1c2d4;margin-bottom:7px}.history-canvas{width:100%;height:104px;display:block}.history-key{font-size:9px;color:#8fa4bd;margin-top:5px}.history-key span{margin-right:7px}.history-key i{display:inline-block;width:10px;height:2px;vertical-align:middle;margin-right:3px}.need-note{font-size:10px;color:#8fa4bd;margin:8px 0 0}.perception-readout{font-size:12px;color:#c3d5e7;line-height:1.55;margin:0 0 10px}.overlay-label{font-size:11px;display:flex;gap:7px;align-items:center;color:#aec3d8;margin:9px 0 0}.overlay-label input{accent-color:var(--cyan)}.camera-note{font-size:10px;line-height:1.5;color:#8fa4bd;margin:7px 0 0}.history-time{color:#7890aa;font-size:9px;margin-top:8px}.hint{color:#9db4cf}.source-note{font-size:10px;color:#93a8c1;margin:10px 0 0}
@media(max-width:1100px){.layout{grid-template-columns:minmax(0,1fr) 260px}.metrics-grid{gap:7px}.metric{padding:10px}.metric-value{font-size:21px}.history-grid{gap:7px}.history-card{padding:9px 6px}.history-title{font-size:9px}}
@media(max-width:900px){.layout{grid-template-columns:minmax(0,1fr)}.history-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.metric-value{font-size:24px}.history-title{font-size:10px}}
@media(max-width:580px){.telemetry-dock{padding:16px 12px}.metrics-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.metric:last-child{grid-column:1/-1}.history-grid{grid-template-columns:1fr}.history-canvas{height:110px}.needs-grid{grid-template-columns:1fr}.dock-heading{align-items:flex-start}.source-tag{font-size:9px}.source-note{font-size:10px}.stage-top{flex-wrap:wrap;row-gap:6px}.hint{display:block;bottom:32px;font-size:9px}.views{flex-wrap:wrap}.perception-card{grid-column:1/-1}}
.peripheral-panel{border-top:1px solid var(--line);padding:16px 19px;background:#112036}.peripheral-panel h2{font-size:13px;margin:0 0 8px}.peripheral-status{display:flex;flex-wrap:wrap;gap:8px;font-size:12px;color:var(--muted)}.peripheral-status span{padding:4px 7px;border:1px solid #385064;border-radius:6px}.peripheral-log{max-height:160px;overflow:auto;margin:10px 0 0;padding-left:20px;font-size:12px;color:#b2cce0}.peripheral-log li{margin:4px 0}.peripheral-log strong{color:#f6cf94}
</style>
</head>
<body>
<header><div><div class="eyebrow">PSI-GW · PiCrawler Lab</div><h1 id="title">PiCrawler-Simulation</h1><p>Gespeicherte Bewegung · frei drehbare Ansicht · vollständig offline</p></div><div class="badge">Kinematik-Testbett</div></header>
<main class="layout">
<section class="stage" aria-label="Dreidimensionale Wiedergabe">
  <div class="scene-wrap"><canvas id="scene" aria-label="Roboter, Hindernisse und Distanzmessung"></canvas><div class="stage-top"><span class="stage-label">4 Beine / 12 Gelenke</span><div class="views"><button id="perspective" class="active" type="button">Raum</button><button id="top" type="button">Draufsicht</button><button id="zoom-in" type="button" aria-label="Vergrößern">+</button><button id="zoom-out" type="button" aria-label="Verkleinern">−</button><button id="reset-view" type="button" title="Ansicht zurücksetzen">↺</button></div></div><div class="hint">Ziehen: drehen · Mausrad: zoomen</div><div class="legend"><span><i class="dot" style="background:var(--cyan)"></i>Roboter</span><span><i class="dot" style="background:var(--gold)"></i>Distanzstrahl</span><span><i class="dot" style="background:var(--blue)"></i>Weg</span></div></div>
  <div id="error" role="alert"></div>
  <div class="controls"><div class="timeline-head"><span>Simulationszeit</span><strong id="time-label">0,00 / 0,00 s</strong></div><label for="scrub" class="small">Aufgezeichneten Zeitpunkt auswählen</label><input id="scrub" type="range" min="0" max="0" step="1" value="0" aria-label="Aufgezeichneten Frame auswählen"><div class="playbar"><button id="play" type="button">▶ Abspielen</button><button id="restart" type="button" aria-label="Zum Anfang">⏮ Anfang</button><label for="speed">Tempo</label><select id="speed" aria-label="Wiedergabetempo"><option value="0.25">¼×</option><option value="0.5">½×</option><option value="1" selected>1×</option><option value="2">2×</option><option value="4">4×</option></select><span id="frame-label" class="frame-counter"></span></div></div>
  <section id="peripheral-panel" class="peripheral-panel" hidden><h2>Audio, LED und Taster · simulierte Ereignisse</h2><div id="peripheral-status" class="peripheral-status"></div><ol id="peripheral-log" class="peripheral-log"></ol><p class="source-note">Symbolische Audioereignisse: noch keine abspielbare Sprach-/Tondatei. Alle Werte gehören zum gewählten Simulationstick.</p></section>
  <section id="telemetry-dock" class="telemetry-dock" hidden aria-label="Betriebswerte und vorgeschlagene Bedürfnisabbildung">
    <div class="dock-heading"><h2>Betriebszustand</h2><span id="telemetry-source" class="source-tag">Quelle unbekannt</span></div><p id="initial-conditions" class="small" hidden></p>
    <div class="metrics-grid">
      <div class="metric"><div class="metric-name">Akku</div><div id="battery-voltage" class="metric-value">—</div><div id="battery-charge" class="metric-sub">Ladestand unbekannt</div><div class="meter"><div id="charge-bar"></div></div></div>
      <div class="metric"><div class="metric-name">CPU-Temperatur</div><div id="cpu-temperature" class="metric-value">—</div><div id="core-voltage" class="metric-sub">Kernspannung nicht erfasst</div></div>
      <div class="metric"><div class="metric-name">Strom &amp; Leistung</div><div id="power-current" class="metric-value">—</div><div id="supply-voltage" class="metric-sub">Versorgung unbekannt</div></div>
    </div>
    <div id="alarms" class="alarms" aria-live="polite"></div><p id="historical-flags" class="small" hidden></p>
    <div id="needs-panel" hidden><div class="dock-heading"><h2>Bedürfnis-Abbildung</h2><span class="small">0 = kein Bedarf · 1 = maximal</span></div><div class="needs-grid"><div class="need"><div class="need-head"><span>Hunger <span class="small">(Energie)</span></span><strong id="hunger-value">—</strong></div><div class="meter"><div id="hunger-bar"></div></div></div><div class="need damage"><div class="need-head"><span>Schaden <span class="small">(therm./elektr.)</span></span><strong id="damage-value">—</strong></div><div class="meter"><div id="damage-bar"></div></div></div></div><p class="need-note">Lokale, vorgeschlagene Abbildung der Betriebswerte; noch keine Rückwirkung auf den PSI-Kern.</p></div>
    <div class="history-grid"><div class="history-card"><div class="history-title">Akku-Ladestand [%]</div><canvas id="charge-history" class="history-canvas" aria-label="Verlauf des Akku-Ladestands"></canvas><div class="history-key"><span><i style="background:var(--cyan)"></i>Ladestand</span></div></div><div class="history-card"><div class="history-title">CPU-Temperatur [°C]</div><canvas id="temperature-history" class="history-canvas" aria-label="Verlauf der CPU-Temperatur"></canvas><div class="history-key"><span><i style="background:var(--gold)"></i>Temperatur</span></div></div><div class="history-card"><div class="history-title">Bedürfnispegel [0–1]</div><canvas id="needs-history" class="history-canvas" aria-label="Verlauf von Hunger und Schaden"></canvas><div class="history-key"><span><i style="background:var(--gold)"></i>Hunger</span><span><i style="background:var(--red)"></i>Schaden</span></div></div></div>
    <div id="history-time" class="history-time"></div><p id="telemetry-note" class="source-note">Alle Werte stammen aus der Aufzeichnung.</p><p id="run-assumptions" class="source-note" hidden></p>
  </section>
</section>
<aside class="sidebar" aria-label="Messwerte des gespeicherten Frames">
  <section class="card"><h2>Distanz nach vorn</h2><div class="range-value" id="distance">—</div><div class="meter"><div id="distance-bar"></div></div><p class="small" id="distance-detail">Idealisierte Distanzmessung</p><div id="collision" class="status"><i></i><span>Freie Bewegung</span></div></section>
  <section class="card"><h2>Zustand &amp; Befehl</h2><dl class="telemetry"><dt>Tick</dt><dd id="tick">0</dd><dt>Position x / y</dt><dd id="position">—</dd><dt>Ausrichtung</dt><dd id="yaw">—</dd><dt>Vorwärts</dt><dd id="forward">—</dd><dt>Seitwärts</dt><dd id="lateral">—</dd><dt>Drehung</dt><dd id="turn">—</dd></dl></section>
  <section id="camera-card" class="card camera-card" hidden><h2>Gespeichertes Kamerabild</h2><canvas id="camera" class="camera" aria-label="Idealisierte Kameraaufnahme"></canvas><label id="overlay-control" class="overlay-label" hidden><input id="blob-overlay" type="checkbox" checked>Farbflächen markieren</label><p class="camera-note">Synthetisches RGB-Bild. Markierungen zeigen zusammenhängende Farbflächen, keine identifizierten Objekte.</p></section>
  <section id="perception-card" class="card perception-card" hidden><h2>Was die Sensoren hergeben</h2><div id="range-perception" class="perception-readout"></div><div id="camera-perception" class="perception-readout"></div><p id="color-blobs" class="small"></p><p class="camera-note">Nur Pixel, Echo und Zeitstempel. Ein fehlendes oder veraltetes Echo bedeutet nicht „freier Weg“.</p></section>
  <section class="card notes-card"><h2>Was diese Ansicht zeigt</h2><p class="notes">Zeitdiskrete Körperbewegung, Gelenkgeometrie und einfache Sensorik auf ebener Fläche. <strong>Kein Nachweis für Standsicherheit, Reibung, Motorleistung oder reale Schrittweite.</strong> Die Ansicht liest nur aufgezeichnete Zustände.</p><div class="meta" id="metadata"></div></section>
</aside>
</main>
<footer><kbd>Leertaste</kbd> Abspielen/Pause &nbsp; <kbd>←</kbd> <kbd>→</kbd> Einzelbild &nbsp; · &nbsp; Alle Längen in Metern. Wiedergabetempo verändert nur die Ansicht.</footer>
<script id="replay-data" type="application/json">__REPLAY_DATA__</script>
<script>
"use strict";
(() => {
  const {metadata: meta, frames} = JSON.parse(document.getElementById("replay-data").textContent);
  const $ = id => document.getElementById(id);
  const canvas = $("scene"), ctx = canvas.getContext("2d"), camera = $("camera"), cameraCtx = camera.getContext("2d");
  const world = meta.world || {}, bounds = world.bounds || [-1,-1,1,1], obstacles = world.obstacles || [];
  const center = [(bounds[0]+bounds[2])/2, (bounds[1]+bounds[3])/2, 0];
  const extent = Math.max(bounds[2]-bounds[0], bounds[3]-bounds[1], .2);
  let index = 0, playing = false, playTime = frames[0].time_s, lastWall = null;
  let view = "space", azimuth = -.72, elevation = .78, zoom = 1;
  let width = 0, height = 0, scale = 1, drag = null;
  const fmt = (n, digits=2) => Number(n).toLocaleString("de-DE",{minimumFractionDigits:digits, maximumFractionDigits:digits});
  const finite = (n, fallback=0) => Number.isFinite(n) ? n : fallback;
  const unitValue = n => Number.isFinite(n)&&n>=0&&n<=1?n:null;
  const numberText = (n,unit,digits=2,missing="—") => Number.isFinite(n)?fmt(n,digits)+" "+unit:missing;
  const last = frames.length-1, firstTime = frames[0].time_s, lastTime = frames[last].time_s;
  const hasHealth = frames.some(f=>f.telemetry||f.needs);
  const flags = [["undervoltage","⚡ Unterspannung"],["thermal_throttled","♨ Temperaturdrosselung"],["power_limited","! Leistung begrenzt"],["battery_depleted","▱ Akku leer"]];
  const colorNames={red:"Rot",yellow:"Gelb",green:"Grün",blue:"Blau"};
  const colors={red:"#ff8494",yellow:"#ffd475",green:"#77e2ad",blue:"#8cb5ff"};
  $("title").textContent = String(meta.title || "PiCrawler-Simulation");
  $("metadata").textContent = "Seed " + String(meta.seed ?? "—") + " · " + frames.length + " Frames · Δt " + fmt(meta.dt_s ?? 0,3) + " s" + (meta.source_commit ? " · Basis " + String(meta.source_commit).slice(0,12) : "");
  $("scrub").max = String(last);
  $("initial-conditions").hidden=!meta.initial_conditions;$("initial-conditions").textContent=String(meta.initial_conditions||"");
  $("run-assumptions").hidden=!meta.assumptions;$("run-assumptions").textContent=String(meta.assumptions||"");

  function project(point) {
    const x = point[0]-center[0], y = point[1]-center[1], z = point[2] || 0;
    const ca = Math.cos(azimuth), sa = Math.sin(azimuth), ce = Math.cos(elevation), se = Math.sin(elevation);
    const right = ca*x + sa*y, away = -sa*x + ca*y;
    return [width*.5 + right*scale, height*.53 + (away*se-z*ce)*scale, away*ce+z*se];
  }
  function stroke(points, color, lineWidth=1, dash=[]) {
    if (!points.length) return;
    ctx.beginPath(); points.forEach((p,n)=>{const q=project(p);n?ctx.lineTo(q[0],q[1]):ctx.moveTo(q[0],q[1]);});
    ctx.strokeStyle=color;ctx.lineWidth=lineWidth;ctx.lineCap="round";ctx.lineJoin="round";ctx.setLineDash(dash);ctx.stroke();ctx.setLineDash([]);
  }
  function polygon(points, fill, border) {
    ctx.beginPath();points.forEach((p,n)=>{const q=project(p);n?ctx.lineTo(q[0],q[1]):ctx.moveTo(q[0],q[1]);});ctx.closePath();ctx.fillStyle=fill;ctx.fill();
    if(border){ctx.strokeStyle=border;ctx.lineWidth=1;ctx.stroke();}
  }
  function dot(point,radius,color,outline) {
    const p=project(point);ctx.beginPath();ctx.arc(p[0],p[1],radius,0,2*Math.PI);ctx.fillStyle=color;ctx.fill();if(outline){ctx.strokeStyle=outline;ctx.lineWidth=1.3;ctx.stroke();}
  }
  function textAt(point,text,color="#91a6bf") {
    const p=project(point);ctx.font="10px system-ui";ctx.fillStyle=color;ctx.fillText(text,p[0]+5,p[1]-5);
  }
  function robotPoint(pose,x,y,z) {
    const c=Math.cos(pose.yaw_rad),s=Math.sin(pose.yaw_rad);
    return [pose.x_m+c*x-s*y,pose.y_m+s*x+c*y,z];
  }
  function grid() {
    polygon([[bounds[0],bounds[1],0],[bounds[2],bounds[1],0],[bounds[2],bounds[3],0],[bounds[0],bounds[3],0]],"#152539","#32475e");
    const target=extent/12,power=10**Math.floor(Math.log10(target)),step=Math.ceil(target/power)*power;
    for(let x=Math.ceil(bounds[0]/step)*step;x<=bounds[2]+step/100;x+=step) stroke([[x,bounds[1],.0001],[x,bounds[3],.0001]],"#23374b");
    for(let y=Math.ceil(bounds[1]/step)*step;y<=bounds[3]+step/100;y+=step) stroke([[bounds[0],y,.0001],[bounds[2],y,.0001]],"#23374b");
    const base=[bounds[0]+extent*.08,bounds[1]+extent*.08,.002],l=extent*.1;
    stroke([base,[base[0]+l,base[1],base[2]]],"#d28a95",1.8);textAt([base[0]+l,base[1],base[2]],"x","#dba2ac");
    stroke([base,[base[0],base[1]+l,base[2]]],"#7fb9a8",1.8);textAt([base[0],base[1]+l,base[2]],"y","#8bc7b8");
  }
  function boxFaces() {
    const faces=[];
    const visibleObstacles=frames[index].world?.obstacles||obstacles;
    visibleObstacles.forEach((b,n)=>{
      const x0=b.x_min,x1=b.x_max,y0=b.y_min,y1=b.y_max,z=b.height_m ?? .18;
      const a=[x0,y0,0],c=[x1,y0,0],d=[x1,y1,0],e=[x0,y1,0],A=[x0,y0,z],C=[x1,y0,z],D=[x1,y1,z],E=[x0,y1,z];
      const colors=["#304157","#3b516a","#293b50","#3c4e62","#4a6078"];
      [[a,c,C,A],[c,d,D,C],[d,e,E,D],[e,a,A,E],[A,C,D,E]].forEach((points,k)=>faces.push({points,color:colors[k],depth:points.reduce((v,p)=>v+project(p)[2],0)/4}));
    });
    return faces;
  }
  function render() {
    if(!width||!height)return;
    const f=frames[index],p=f.pose;
    ctx.clearRect(0,0,width,height);grid();
    // The path contains recorded positions only, with no inferred motion.
    const path=frames.slice(0,index+1).map(q=>[q.pose.x_m,q.pose.y_m,.002]);stroke(path,"#6e98ff",Math.max(1.5,1.7*zoom));
    const r=.075;
    const shadow=[];for(let i=0;i<24;i++){const a=2*Math.PI*i/24;shadow.push(robotPoint(p,r*Math.cos(a),r*Math.sin(a),.001));}
    polygon(shadow,"rgba(0,0,0,.25)");
    const draws=boxFaces().map(face=>({depth:face.depth,draw:()=>polygon(face.points,face.color,"#567086")}));
    (f.legs||[]).forEach(leg=>{leg.points.forEach((q,i)=>{
      draws.push({depth:project(q)[2],draw:()=>dot(q,Math.max(i===3?2:2.8,scale*(i===3?.003:.004)),i===3?"#0c1c2b":"#d9f8f0","#3b7f86")});
      if(i){const segment=[leg.points[i-1],q];draws.push({depth:(project(segment[0])[2]+project(q)[2])/2,draw:()=>{stroke(segment,"#182a35",Math.max(4,scale*.011));stroke(segment,"#83c9c6",Math.max(2.4,scale*.007));}});}
    });});
    const half=.0385,h=p.height_m ?? .06;
    const chassis=(f.legs||[]).length===4?f.legs.map(leg=>leg.points[0]):[[-half,-half],[half,-half],[half,half],[-half,half]].map(q=>robotPoint(p,q[0],q[1],h));
    draws.push({depth:project([p.x_m,p.y_m,h])[2],draw:()=>{
      polygon(chassis,"#37a9a5","#a6f1dc");
      polygon([robotPoint(p,.031,0,h+.001),robotPoint(p,-.009,-.015,h+.001),robotPoint(p,-.009,.015,h+.001)],"#c4fff0");
      dot(robotPoint(p,0,0,h+.003),Math.max(1.5,scale*.0025),"#0b3547");
    }});
    draws.sort((a,b)=>a.depth-b.depth).forEach(item=>item.draw());
    const sensor=f.sensor||{}, origin=sensor.origin||robotPoint(p,.045,0,h),direction=sensor.direction||[Math.cos(p.yaw_rad),Math.sin(p.yaw_rad),0];
    const measured=Number.isFinite(sensor.distance_m),distance=measured?sensor.distance_m:finite(sensor.max_range_m,1);
    const end=origin.map((v,k)=>v+direction[k]*distance);
    stroke([origin,end],measured?"rgba(255,203,119,.9)":"rgba(255,203,119,.3)",1.7,measured?[]:[5,5]);dot(origin,2.8,"#ffd58c");if(measured)dot(end,3.2,"#ffd58c","#6d5634");
    if(f.collision||f.workspace_limited){const radius=finite(meta.collision_radius_m,.13),ring=[];for(let i=0;i<=40;i++){const a=2*Math.PI*i/40;ring.push([p.x_m+radius*Math.cos(a),p.y_m+radius*Math.sin(a),.003]);}stroke(ring,"#ff8091",2,[4,4]);}
  }
  function renderCamera(rgb,perception) {
    const available=Array.isArray(rgb)&&rgb.length&&Array.isArray(rgb[0])&&rgb[0].length;
    $("camera-card").hidden=!available;if(!available)return;
    const h=rgb.length,w=rgb[0].length;camera.width=w;camera.height=h;camera.style.aspectRatio=String(w)+"/"+String(h);
    const im=cameraCtx.createImageData(w,h);
    for(let y=0;y<h;y++)for(let x=0;x<w;x++){const px=rgb[y][x],offset=4*(y*w+x);im.data[offset]=px[0];im.data[offset+1]=px[1];im.data[offset+2]=px[2];im.data[offset+3]=255;}
    cameraCtx.putImageData(im,0,0);
    if($("blob-overlay").checked&&perception?.camera?.usable){
      (perception.camera.blobs||[]).forEach(blob=>{
        const b=blob.bounds;if(!Array.isArray(b)||b.length!==4||!b.every(n=>unitValue(n)!==null))return;
        cameraCtx.strokeStyle=colors[blob.color]||"#fff";cameraCtx.lineWidth=Math.max(.65,w/150);
        cameraCtx.strokeRect(b[0]*w,b[1]*h,(b[2]-b[0])*w,(b[3]-b[1])*h);
        if(unitValue(blob.centroid_x)!==null&&unitValue(blob.centroid_y)!==null){const x=blob.centroid_x*w,y=blob.centroid_y*h;cameraCtx.beginPath();cameraCtx.moveTo(x-1.3,y);cameraCtx.lineTo(x+1.3,y);cameraCtx.moveTo(x,y-1.3);cameraCtx.lineTo(x,y+1.3);cameraCtx.stroke();}
      });
    }
  }
  function freshnessText(feature){
    const labels={fresh:"frisch",stale:"veraltet",unknown:"Zeitstempel fehlt",future:"Zeitstempel liegt in der Zukunft",invalid:"ungültiger Zeitstempel"};
    return(labels[feature?.freshness]||"nicht erfasst")+(Number.isFinite(feature?.age_s)?" · "+fmt(feature.age_s*1000,0)+" ms alt":"");
  }
  function renderPerception(p){
    $("perception-card").hidden=!p;$("overlay-control").hidden=!(p?.camera?.usable&&(p.camera.blobs||[]).length);if(!p)return;
    const r=p.range||{},c=p.camera||{};
    $("range-perception").textContent=r.usable&&unitValue(r.proximity)!==null?"Hindernisnähe "+fmt(r.proximity*100,0)+" % · "+freshnessText(r):"Kein nutzbares Echo · "+freshnessText(r);
    $("camera-perception").textContent=(c.usable?"Bild nutzbar":c.valid?"Bild aktuell nicht nutzbar":"Kein gültiges Bild")+" · "+freshnessText(c);
    const blobs=c.usable?(c.blobs||[]):[];
    $("color-blobs").textContent=blobs.length?blobs.slice(0,6).map(b=>(colorNames[b.color]||String(b.color))+": "+numberText(b.area_fraction*100,"%",1)+" bei x="+fmt(b.centroid_x)+", y="+fmt(b.centroid_y)).join(" · "):"Keine verwendbaren Farbflächen.";
  }
  function drawHistory(id,series,yMin,yMax,digits=0){
    const el=$(id),r=el.getBoundingClientRect();if(!r.width||!r.height)return;
    const context=el.getContext("2d"),dpr=Math.min(window.devicePixelRatio||1,3);el.width=Math.round(r.width*dpr);el.height=Math.round(r.height*dpr);context.setTransform(dpr,0,0,dpr,0,0);
    const left=27,right=r.width-7,top=8,bottom=r.height-14,span=Math.max(lastTime-firstTime,.001),x=t=>left+(t-firstTime)/span*(right-left),y=v=>bottom-(v-yMin)/(yMax-yMin)*(bottom-top);
    context.clearRect(0,0,r.width,r.height);context.font="9px system-ui";context.lineWidth=1;context.fillStyle="#7991ac";context.strokeStyle="#273c53";context.textAlign="right";
    [yMin,(yMin+yMax)/2,yMax].forEach(value=>{const py=y(value);context.beginPath();context.moveTo(left,py);context.lineTo(right,py);context.stroke();context.fillText(fmt(value,digits),left-4,py+3);});
    context.save();context.beginPath();context.rect(left,top,right-left,bottom-top);context.clip();
    series.forEach(line=>{context.beginPath();let pen=false;for(let i=0;i<=index;i++){const value=line.value(frames[i]);if(!Number.isFinite(value)){pen=false;continue;}const px=x(frames[i].time_s),py=y(value);pen?context.lineTo(px,py):context.moveTo(px,py);pen=true;}context.strokeStyle=line.color;context.lineWidth=1.8;context.stroke();const current=line.value(frames[index]);if(Number.isFinite(current)){context.beginPath();context.arc(x(frames[index].time_s),y(current),2.3,0,2*Math.PI);context.fillStyle=line.color;context.fill();}});
    context.restore();context.beginPath();context.setLineDash([2,3]);context.moveTo(x(frames[index].time_s),top);context.lineTo(x(frames[index].time_s),bottom);context.strokeStyle="#91a6bc";context.lineWidth=1;context.stroke();context.setLineDash([]);context.textAlign="left";
  }
  function renderHistories(){
    if(!hasHealth)return;
    const temperatures=frames.map(f=>f.telemetry?.cpu_temperature_c).filter(Number.isFinite);
    const low=Math.min(0,...temperatures.map(n=>Math.floor(n/10)*10)),high=Math.max(100,...temperatures.map(n=>Math.ceil(n/10)*10));
    drawHistory("charge-history",[{color:"#54ddd4",value:f=>unitValue(f.telemetry?.state_of_charge)===null?null:f.telemetry.state_of_charge*100}],0,100);
    drawHistory("temperature-history",[{color:"#ffcb77",value:f=>f.telemetry?.cpu_temperature_c}],low,high);
    drawHistory("needs-history",[{color:"#ffcb77",value:f=>unitValue(f.needs?.hunger)},{color:"#ff7e8d",value:f=>unitValue(f.needs?.damage)}],0,1,1);
    $("history-time").textContent="Gespeicherte Simulationszeit "+fmt(firstTime,1)+"–"+fmt(lastTime,1)+" s · angezeigt bis "+fmt(frames[index].time_s,1)+" s. Fehlende Werte bleiben Lücken.";
  }
  function renderHealth(f){
    $("telemetry-dock").hidden=!hasHealth;if(!hasHealth)return;
    const t=f.telemetry||{},n=f.needs||{},soc=unitValue(t.state_of_charge),hunger=unitValue(n.hunger),damage=unitValue(n.damage);
    $("telemetry-source").textContent=t.source==="simulated"?"Modellwerte · Simulation":t.source==="hardware"?"Aufgezeichnete Hardwarewerte":"Quelle nicht angegeben";
    $("battery-voltage").textContent=numberText(t.battery_voltage_v,"V");$("battery-charge").textContent=soc===null?"Ladestand nicht erfasst":fmt(soc*100,1)+" % Ladung";$("charge-bar").style.width=(soc===null?0:soc*100)+"%";
    $("cpu-temperature").textContent=numberText(t.cpu_temperature_c,"°C",1);$("core-voltage").textContent=Number.isFinite(t.core_voltage_v)?"CPU-Kernspannung "+numberText(t.core_voltage_v,"V",3):"CPU-Kernspannung nicht modelliert/erfasst";
    $("power-current").textContent=numberText(t.current_a,"A")+" · "+numberText(t.power_w,"W",1);$("supply-voltage").textContent=Number.isFinite(t.supply_voltage_v)?"Versorgung "+numberText(t.supply_voltage_v,"V"):"Versorgung nicht erfasst";
    $("alarms").textContent="";let count=0;flags.forEach(([key,label])=>{if(t[key]!==true)return;const e=document.createElement("span");e.className="alarm critical";e.textContent=label;$("alarms").appendChild(e);count++;});
    if(!count){const e=document.createElement("span");e.className="alarm ok";e.textContent=flags.some(([key])=>typeof t[key]==="boolean")?"✓ Keine aktiven Statusmeldungen":"Keine Statusflags aufgezeichnet";$("alarms").appendChild(e);}
    const savedHistory=t.historical_flags||t.history||{},history=flags.filter(([key])=>savedHistory[key]===true).map(([,label])=>label);$("historical-flags").hidden=!history.length;$("historical-flags").textContent=history.length?"Früher im Lauf: "+history.join(" · "):"";
    $("needs-panel").hidden=!(f.needs);$("hunger-value").textContent=hunger===null?"—":fmt(hunger,2);$("damage-value").textContent=damage===null?"—":fmt(damage,2);$("hunger-bar").style.width=(hunger===null?0:100*hunger)+"%";$("damage-bar").style.width=(damage===null?0:100*damage)+"%";
    $("telemetry-note").textContent=t.source==="simulated"?"Elektrische und thermische Werte stammen aus einem parametrierten Modell. Startzustand und Grenzen sind keine Hardwarekalibrierung.":"Betriebswerte und Statusflags werden unverändert aus dem gespeicherten Frame gelesen.";
    renderHistories();
  }
  function renderPeripherals(frame) {
    const panel=$("peripheral-panel"), p=frame.peripherals;
    panel.hidden=!p;
    if(!p)return;
    const current=p.speaker?.event;
    const status=$("peripheral-status"); status.textContent="";
    const parts=[
      "Lautsprecher: "+(p.speaker?.playing?"aktiv ("+String(current?.mode||"Ton")+")":"still"),
      "Benutzer-LED: "+(p.user_led?"an":"aus"),
      "Akku-LEDs: "+(p.battery_indicator_leds===null?"unbekannt":String(p.battery_indicator_leds)),
      "USR: "+(p.user_button_down?"gedrückt":"frei"),
      "RST: "+(p.reset_button_down?"gedrückt":"frei")
    ];
    parts.forEach(label=>{const item=document.createElement("span");item.textContent=label;status.appendChild(item);});
    const log=$("peripheral-log");log.textContent="";
    // The full event history comes from the same saved tick as the image.
    const events=(frame.peripheral_events||[]).filter(event=>event.tick<=frame.tick).slice(-8);
    for(const event of events){
      const item=document.createElement("li");
      const kind=String(event.kind||"Ereignis");
      let message=kind;
      if(kind==="audio_start"){
        const a=event.audio||{};
        const descriptor=a.mode==="speak"?a.payload?.text:a.mode==="tone"?String(a.payload?.hz)+" Hz":a.payload?.id;
        message="▶ "+String(a.mode||"Audio")+" · "+String(descriptor||"");
      } else if(kind==="audio_stop"){message="■ Audio beendet"+(event.reason?" ("+String(event.reason)+")":"");}
      else if(kind==="led"){message="LED "+(event.on?"an":"aus");}
      else if(kind==="button"){message=String(event.button)+"-Taster "+(event.down?"gedrückt":"losgelassen");}
      item.textContent=fmt(event.time_s,2)+" s · "+message;
      log.appendChild(item);
    }
  }
  function setFrame(next) {
    index=Math.max(0,Math.min(last,next));const f=frames[index],p=f.pose,s=f.sensor||{},command=f.command||{};
    $("scrub").value=String(index);$("time-label").textContent=fmt(f.time_s)+" / "+fmt(lastTime)+" s";
    $("frame-label").textContent="Frame "+(index+1)+" / "+frames.length;$("tick").textContent=String(f.tick);
    $("position").textContent=fmt(p.x_m)+" / "+fmt(p.y_m)+" m";$("yaw").textContent=fmt(p.yaw_rad*180/Math.PI,1)+"°";
    $("forward").textContent=fmt(command.forward_mps||0,3)+" m/s";$("lateral").textContent=fmt(command.lateral_mps||0,3)+" m/s";$("turn").textContent=fmt(command.yaw_rps||0,3)+" rad/s";
    const valid=Number.isFinite(s.distance_m),distanceEl=$("distance");distanceEl.textContent=valid?fmt(s.distance_m):"—";
    const unit=document.createElement("span");unit.textContent=valid?" m":" kein Echo";distanceEl.appendChild(unit);
    $("distance-bar").style.width=(valid?100*Math.min(1,Math.max(0,s.distance_m/Math.max(.001,finite(s.max_range_m,1)))):0)+"%";
    $("distance-detail").textContent="Modellbereich bis "+fmt(finite(s.max_range_m,0),1)+" m · idealisierte Sensorik";
    $("collision").classList.toggle("blocked",Boolean(f.collision||f.workspace_limited));$("collision").querySelector("span").textContent=f.workspace_limited?"Kinematische Grenze":f.collision?"Hindernisgrenze erreicht":"Freie Bewegung";
    renderPerception(f.perception);renderCamera(f.camera_rgb,f.perception);renderHealth(f);renderPeripherals(f);render();
  }
  function setPlaying(value){playing=value;lastWall=null;$("play").textContent=playing?"Ⅱ Pause":"▶ Abspielen";$("play").setAttribute("aria-pressed",String(playing));}
  $("play").addEventListener("click",()=>{if(!playing&&index===last){playTime=firstTime;setFrame(0);}setPlaying(!playing);});
  $("restart").addEventListener("click",()=>{setPlaying(false);playTime=firstTime;setFrame(0);});
  $("scrub").addEventListener("input",event=>{setPlaying(false);setFrame(Number(event.target.value));playTime=frames[index].time_s;});
  $("blob-overlay").addEventListener("change",()=>renderCamera(frames[index].camera_rgb,frames[index].perception));
  function chooseView(name){view=name;azimuth=name==="top"?0:-.72;elevation=name==="top"?Math.PI/2:.78;$("perspective").classList.toggle("active",name==="space");$("top").classList.toggle("active",name==="top");render();}
  $("perspective").addEventListener("click",()=>chooseView("space"));$("top").addEventListener("click",()=>chooseView("top"));
  $("zoom-in").addEventListener("click",()=>{zoom=Math.min(4,zoom*1.3);resize();});$("zoom-out").addEventListener("click",()=>{zoom=Math.max(.5,zoom/1.3);resize();});
  $("reset-view").addEventListener("click",()=>{zoom=1;chooseView("space");resize();});
  canvas.addEventListener("pointerdown",event=>{drag=[event.clientX,event.clientY,azimuth,elevation];canvas.setPointerCapture(event.pointerId);});
  canvas.addEventListener("pointermove",event=>{if(!drag)return;azimuth=drag[2]-(event.clientX-drag[0])*.008;elevation=Math.min(Math.PI/2,Math.max(.2,drag[3]+(event.clientY-drag[1])*.008));view="space";$("perspective").classList.add("active");$("top").classList.remove("active");render();});
  canvas.addEventListener("pointerup",()=>{drag=null;});canvas.addEventListener("pointercancel",()=>{drag=null;});
  canvas.addEventListener("wheel",event=>{event.preventDefault();zoom=Math.max(.5,Math.min(4,zoom*Math.exp(-event.deltaY*.001)));resize();},{passive:false});
  document.addEventListener("keydown",event=>{if(["INPUT","SELECT","BUTTON","TEXTAREA"].includes(document.activeElement.tagName))return;if(event.code==="Space"){event.preventDefault();$("play").click();}else if(event.code==="ArrowRight"||event.code==="ArrowLeft"){event.preventDefault();setPlaying(false);setFrame(index+(event.code==="ArrowRight"?1:-1));playTime=frames[index].time_s;}});
  document.addEventListener("visibilitychange",()=>{lastWall=null;});
  function resize(){const r=canvas.getBoundingClientRect(),dpr=Math.min(window.devicePixelRatio||1,3);width=r.width;height=r.height;canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);scale=Math.min(width*.63,height*.72)/extent*zoom;render();renderHistories();}
  new ResizeObserver(resize).observe(canvas);window.addEventListener("resize",resize);
  function animate(now){if(playing&&!document.hidden){if(lastWall!==null){playTime+=(now-lastWall)/1000*Number($("speed").value);let lo=0,hi=last;while(lo<hi){const mid=Math.ceil((lo+hi)/2);if(frames[mid].time_s<=playTime)lo=mid;else hi=mid-1;}if(lo!==index)setFrame(lo);if(playTime>=lastTime){setFrame(last);setPlaying(false);}}lastWall=now;}else{lastWall=null;}requestAnimationFrame(animate);}
  resize();setFrame(0);requestAnimationFrame(animate);
})();
</script>
</body>
</html>
"""
