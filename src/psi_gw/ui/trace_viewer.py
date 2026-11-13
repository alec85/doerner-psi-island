"""Export one or two ADR-0006 traces as a self-contained, offline HTML viewer.

Usage: python -m psi_gw.ui.trace_viewer RUN.jsonl.gz [OTHER.jsonl.gz] --output viewer.html
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile

from psi_gw.tracing.runfile import read_run


def _finite(value):
    """Make a separate JSON-safe copy; leave absent values absent, never zero-fill."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: _finite(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_finite(v) for v in value]
    return value


def load_trace(path: Path):
    """Read through the established trace reader and retain source provenance."""
    path = Path(path)
    before = path.read_bytes()
    try:
        run = read_run(path)
    except (TypeError, KeyError, AttributeError, IndexError) as exc:
        raise ValueError(f"{path}: invalid trace structure: {exc}") from exc
    if path.read_bytes() != before:
        raise ValueError(f"{path}: input changed while being read")
    raw = {"name": path.name, "sha256": hashlib.sha256(before).hexdigest(),
           "header": run.header.to_dict(),
           "cycles": [r.to_dict() for r in run.cycles],
           "events": [r.to_dict() for r in run.events],
           "summary": run.summary.to_dict() if run.summary is not None else None}
    # json.dumps allows NaN/Infinity; the browser must receive strict JSON.
    raw["nonfinite_values"] = sum(1 for token in _walk(raw)
                                  if isinstance(token, float) and not math.isfinite(token))
    return _finite(raw)


def _walk(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk(item)
    else:
        yield value


def render_html(traces):
    """Embed data without allowing input strings to terminate the JSON script."""
    if not 1 <= len(traces) <= 2:
        raise ValueError("select one or two traces")
    payload = json.dumps(traces, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    payload = (payload.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
               .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))
    return _HTML.replace("__TRACE_DATA__", payload)


def export_viewer(paths, output, *, force=False):
    """Write atomically; never overwrite source traces, including symlink aliases."""
    paths = [Path(p) for p in paths]
    output = Path(output)
    if not 1 <= len(paths) <= 2:
        raise ValueError("select one or two traces")
    if output.resolve() in {p.resolve() for p in paths}:
        raise ValueError("output must not overwrite an input trace")
    if output.exists() and not force:
        raise FileExistsError(f"{output}: already exists; choose another output or use --force")
    document = render_html([load_trace(p) for p in paths])
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent,
                                         prefix=".trace-viewer-", suffix=".tmp", delete=False) as fh:
            temporary = Path(fh.name)
            fh.write(document)
        if force:
            os.replace(temporary, output)
        else:
            # Linking fails atomically if another writer created the destination.
            os.link(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("traces", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--force", action="store_true", help="replace an existing report, never an input")
    args = parser.parse_args(argv)
    try:
        output = export_viewer(args.traces, args.output, force=args.force)
    except (OSError, ValueError, UnicodeError, EOFError) as exc:
        parser.exit(2, f"trace viewer: {exc}\n")
    print(f"Trace viewer: {output}")
    return 0


_HTML = r'''<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; connect-src 'none'; base-uri 'none'; form-action 'none'">
<title>PSI · Trace-Viewer</title>
<style>
:root{color-scheme:light;--ink:#142c35;--muted:#526971;--line:#dce5e4;--paper:#f4f7f5;--a:#086e73;--b:#a84b29;--wash:#e9f3f0}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.5 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}button,input,select{font:inherit;color:inherit}button,select,input:not([type=range]){background:white;border:1px solid #b8cacb;border-radius:7px;padding:8px 10px;max-width:100%}button{cursor:pointer}button:hover{background:var(--wash)}button:disabled{opacity:.45;cursor:default}button:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible{outline:3px solid #298b9d;outline-offset:3px}main{max-width:1320px;margin:auto;padding:32px}header{display:flex;justify-content:space-between;align-items:start;gap:20px;margin-bottom:26px}.eyebrow{text-transform:uppercase;letter-spacing:.16em;font-weight:700;font-size:12px;color:var(--a)}h1{font-size:clamp(30px,4vw,44px);line-height:1.15;letter-spacing:-.04em;margin:10px 0}h2{font-size:20px;letter-spacing:-.02em;margin:0 0 6px}p{margin:6px 0}.muted,.hint{color:var(--muted)}.tag{background:var(--wash);border:1px solid #d1e3dd;border-radius:20px;padding:6px 12px;white-space:nowrap;font-size:12px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:16px;margin-bottom:18px}.card,.panel{background:#fff;border:1px solid var(--line);border-radius:13px;padding:22px}.card{border-top:3px solid var(--a)}.card.b{border-top-color:var(--b)}.card h2{font-size:16px;overflow-wrap:anywhere}.stats{display:flex;gap:28px;margin:14px 0}.stat strong{display:block;font-size:27px;font-weight:600;letter-spacing:-.04em}.stat span{font-size:12px;color:var(--muted)}.badge{font-size:12px;font-weight:700;letter-spacing:.06em;color:var(--a)}.b .badge{color:var(--b)}.notice{border-left:3px solid #c69442;background:#fff6e8;padding:12px 16px;margin:18px 0;border-radius:3px;font-size:13px}.panel{margin-bottom:18px}.row{display:flex;gap:14px;align-items:end;flex-wrap:wrap}.spread{justify-content:space-between}.controls{margin:20px 0 12px}.field{display:flex;flex-direction:column;gap:5px;font-size:12px;font-weight:600}.field select{font-size:14px;min-width:140px}.metric{flex:1;min-width:250px}.bound{width:135px}.small{font-size:12px}#chart{display:block;width:100%;height:auto;min-height:160px;margin-top:12px}.chart-wrap{position:relative}.legend{display:flex;gap:20px;flex-wrap:wrap;font-size:13px}.swatch{display:inline-block;width:22px;border-top:3px solid var(--a);margin:0 8px 3px 0}.swatch.b{border-color:var(--b);border-top-style:dashed}.chart-empty{padding:40px 15px;color:var(--muted);text-align:center}#chart-status{min-height:20px;margin-top:4px}table{width:100%;border-collapse:collapse;font-size:13px}th{text-align:left;color:var(--muted);font-weight:500;padding:10px 12px;border-bottom:1px solid var(--line);white-space:nowrap}td{padding:10px 12px;border-bottom:1px solid #edf0f0;vertical-align:top;overflow-wrap:anywhere}tbody tr:hover{background:#f5f9f7}.table-wrap{overflow:auto;margin-top:16px}td button{border:0;padding:0;background:none;color:var(--a);font-weight:650;text-align:left}td.run-a{color:var(--a);font-weight:700}td.run-b{color:var(--b);font-weight:700}#event-search{min-width:220px}.pager{margin-top:14px;font-size:13px}.details-grid{display:grid;grid-template-columns:1fr 1fr;gap:22px}.details-grid>div{min-width:0}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f8f6;border-radius:7px;padding:14px;font:12px/1.55 ui-monospace,SFMono-Regular,Consolas,monospace;max-height:380px;overflow:auto}summary{cursor:pointer;color:var(--a);font-size:13px}details{margin-top:12px}input[type=range]{width:100%;accent-color:var(--a)}.navigator{display:grid;grid-template-columns:auto 1fr auto;gap:12px;align-items:center;margin-top:14px}footer{font-size:12px;color:var(--muted);padding:0 2px 18px}.sr-only{position:absolute;width:1px;height:1px;padding:0;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}@media(max-width:650px){main{padding:18px 12px}header{display:block}header .tag{display:inline-block;margin-top:10px}.panel,.card{padding:16px}.details-grid{grid-template-columns:1fr}.bound{width:calc(50% - 8px)}.row{gap:10px}.metric{min-width:100%;width:100%}.field select,#event-search{min-width:0;width:100%}.controls>.field{flex:1}h1{font-size:33px}th,td{padding:9px 8px}.stats{gap:22px}}
</style>
</head>
<body><main>
<header><div><div class="eyebrow">PSI / Beobachtung &amp; Diagnose</div><h1>Läufe nachvollziehen.</h1><p class="muted">Aufgezeichnete Zustände, Messwerte und Ereignisse auf einer gemeinsamen Zeitachse.</p></div><span class="tag">Lokal · nur lesend · ohne Server</span></header>
<div id="runs" class="cards"></div><div id="warnings" aria-live="polite"></div>
<section class="panel" aria-labelledby="signals-heading">
<div class="row spread"><div><h2 id="signals-heading">Messwerte im Verlauf</h2><p class="hint small">Lauf A durchgezogen, Lauf B gestrichelt. Datenlücken werden nicht mit Null aufgefüllt.</p></div><div id="legend" class="legend"></div></div>
<div class="row controls">
<label class="field metric">Messwert<select id="metric"></select></label>
<label class="field">Zeitachse<select id="axis"><option value="age">Alter (Simulationseinheiten)</option><option value="cycle">Zyklus</option></select></label>
<label class="field bound">Von<input id="from" type="number" step="any" placeholder="Anfang"></label>
<label class="field bound">Bis<input id="to" type="number" step="any" placeholder="Ende"></label>
<button id="reset">Zurücksetzen</button></div>
<div class="chart-wrap"><svg id="chart" viewBox="0 0 1100 300" role="img" aria-label="Messwertverlauf"></svg><p id="empty-chart" class="chart-empty" hidden>Für diesen Messwert und Ausschnitt sind keine Werte mit Zeitkoordinate erfasst.</p></div>
<p id="chart-status" class="small muted" aria-live="polite"></p>
</section>
<section class="panel" aria-labelledby="events-heading">
<div class="row spread"><div><h2 id="events-heading">Ereignisse erkunden</h2><p class="small muted">Beginn und Ende einer Aktion sind getrennte Datensätze; Ereigniszahlen sind keine Handlungszahlen.</p></div><span id="event-count" class="tag"></span></div>
<div class="row controls">
<label class="field">Lauf<select id="run-filter"><option value="all">Alle Läufe</option></select></label>
<label class="field">Aktion<select id="action-filter"><option value="all">Alle Aktionen</option></select></label>
<label class="field">Suche<input id="event-search" type="search" placeholder="Situation, Objekt, Parameter …"></label>
</div>
<div class="table-wrap"><table><caption class="sr-only">Gefilterte Ereignisdatensätze</caption><thead><tr><th>Lauf</th><th>Zyklus</th><th>Alter</th><th>Aktion / Phase</th><th>Situation / Objekt</th></tr></thead><tbody id="events"></tbody></table></div>
<div class="row spread pager"><span id="page-label" aria-live="polite"></span><div class="row"><button id="previous-page">← Vorige Seite</button><button id="next-page">Nächste Seite →</button></div></div>
</section>
<section class="panel" aria-labelledby="detail-heading"><div class="details-grid"><div><h2 id="detail-heading">Ein Ereignis im Detail</h2><p id="selected-label" class="small muted"></p><div class="navigator"><button id="previous-event" aria-label="Vorheriges Ereignis">←</button><label><span class="sr-only">Ereignis auswählen</span><input id="cursor" type="range" min="0" max="0" value="0"></label><button id="next-event" aria-label="Nächstes Ereignis">→</button></div><pre id="event-detail" aria-live="polite">Noch kein Ereignis ausgewählt.</pre></div><div><h2>Leseregeln</h2><p class="small muted">Die Achse verwendet ausschließlich das gespeicherte Alter oder die gespeicherte Zyklusnummer. Läufe werden nicht zeitlich verformt oder nach Zeilenposition ausgerichtet.</p><p class="small muted">Nicht erfasste Felder erscheinen als „nicht erfasst“ oder <code>null</code>. Kurven verbinden nur aufeinanderfolgende gültige Datensätze; gleiche Zeitkoordinaten bleiben erhalten. Linien sind eine Darstellungshilfe, keine rekonstruierten Zwischenwerte.</p><p class="small muted">Ein Abschlussdatensatz ist eine archivierte Zusammenfassung, kein Beweis für einen vollständig protokollierten Lebenslauf. Der Viewer prüft keine Äquivalenz und führt keine Simulation aus.</p></div></div></section>
<footer>PSI Trace-Viewer · ADR 0006 · Eingaben bleiben unverändert. Der Bericht enthält die eingebetteten Laufdaten.</footer>
</main>
<script id="trace-data" type="application/json">__TRACE_DATA__</script>
<script>
'use strict';
const traces=JSON.parse(document.getElementById('trace-data').textContent);
const $=id=>document.getElementById(id), colors=['#086e73','#a84b29'];
const numeric=v=>typeof v==='number'&&Number.isFinite(v);
const fmt=v=>v===null||v===undefined?'nicht erfasst':(numeric(v)?new Intl.NumberFormat('de-DE',{maximumFractionDigits:5}).format(v):String(v));
const labelMap={hunger:'Hunger',thirst:'Durst',nucleotides:'Nukleotide',damage:'Schaden',certainty:'Bestimmtheit',competence:'Kompetenz',affiliation:'Affiliation',arousal:'Aktiviertheit',resolution_level:'Auflösungsgrad',selection_threshold:'Selektionsschwelle',successful_locomotions:'Erfolgreiche Ortswechsel',unsuccessful_locomotions:'Fehlgeschlagene Ortswechsel',locations_discovered:'Entdeckte Orte',exitus:'Exitus',aggressions:'Aggressionen',successful_manipulations:'Erfolgreiche Manipulationen',unsuccessful_manipulations:'Fehlgeschlagene Manipulationen',nucleotides_collected:'Gesammelte Nukleotide',look_around:'Umschauen',automatism:'Automatismus',plan:'Planen',what_could_be_done:'Versuch und Irrtum'};
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
function svg(tag,attributes,text){const n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v] of Object.entries(attributes))n.setAttribute(k,v);if(text!==undefined)n.textContent=text;return n;}
const metrics=[];
const groups=[['events','needs','Bedürfnis · Ereigniswert'],['events','modulators','Modulator · Ereigniswert'],['cycles','need_pct','Bedürfnis · Prozent'],['cycles','counters','Leistungszähler · kumulativ'],['cycles','stage_times','Regulationszeit · Alterseinheiten']];
for(const [kind,group,title] of groups){const keys=new Set();for(const run of traces)for(const row of run[kind])for(const key of Object.keys(row[group]||{}))keys.add(key);if(!keys.size)continue;const optgroup=el('optgroup');optgroup.label=title;for(const key of keys){const id=metrics.length;metrics.push({kind,group,key,title});const option=el('option',labelMap[key]||key);option.value=id;optgroup.append(option);}$('metric').append(optgroup);}
if(!metrics.length){const option=el('option','Keine Messwerte erfasst');option.value='';$('metric').append(option);$('metric').disabled=true;}
for(let i=0;i<traces.length;i++){
 const run=traces[i],name=String.fromCharCode(65+i),card=el('article',undefined,'card '+(i?'b':''));
 card.append(el('span','LAUF '+name+' / '+fmt(run.header.source),'badge'),el('h2',run.name),el('p','Seed '+fmt(run.header.seed)+' · '+fmt(run.header.world),'small muted'));
 const stats=el('div',undefined,'stats');for(const [value,label] of [[run.cycles.length,'Zyklusdatensätze'],[run.events.length,'Ereignisdatensätze']]){const stat=el('div',undefined,'stat');stat.append(el('strong',fmt(value)),el('span',label));stats.append(stat);}card.append(stats);
 card.append(el('p',run.summary?'Abschlussdatensatz vorhanden':'Kein Abschlussdatensatz · Vollständigkeit unbekannt','small muted'));
 const details=el('details'),summary=el('summary','Herkunft, Parameter & Zusammenfassung');const metadata={datei:run.name,sha256:run.sha256,header:run.header,summary:run.summary};details.append(summary,el('pre',JSON.stringify(metadata,null,2)));card.append(details);$('runs').append(card);
 const legend=el('span');const swatch=el('i',undefined,'swatch '+(i?'b':''));legend.append(swatch,document.createTextNode('Lauf '+name));$('legend').append(legend);
 const option=el('option','Lauf '+name);option.value=String(i);$('run-filter').append(option);
 if(run.nonfinite_values)$('warnings').append(el('p',fmt(run.nonfinite_values)+' nichtendliche Werte in Lauf '+name+' werden als fehlend angezeigt.','notice'));
}
if(traces.length===2){const keys=['seed','world','psi_data','params'];const different=keys.filter(k=>JSON.stringify(traces[0].header[k])!==JSON.stringify(traces[1].header[k]));if(different.length)$('warnings').append(el('p','Abweichende Laufmetadaten: '+different.join(', ')+'. Die Überlagerung ist ein visueller Vergleich, kein Gleichheitsnachweis.','notice'));}
const allEvents=traces.flatMap((r,run)=>r.events.map((event,index)=>({run,index,event})));
const actions=[...new Set(allEvents.map(x=>x.event.action))].sort();for(const a of actions){const option=el('option',a);option.value=a;$('action-filter').append(option);}
let filtered=[],page=0,cursor=0;
function range(){const a=$('from').value.trim(),b=$('to').value.trim();return [a===''?-Infinity:Number(a),b===''?Infinity:Number(b)];}
function validRange(){const [lo,hi]=range();return !Number.isNaN(lo)&&!Number.isNaN(hi)&&lo<=hi;}
function inRange(row){const [lo,hi]=range(),x=row[$('axis').value];if(lo===-Infinity&&hi===Infinity)return true;return numeric(x)&&x>=lo&&x<=hi;}
function pointsFor(run,metric){return run[metric.kind].map(row=>({x:row[$('axis').value],y:row[metric.group]?.[metric.key]}));}
function draw(){const root=$('chart');root.replaceChildren();const metric=metrics[Number($('metric').value)];
 if(!validRange()){$('empty-chart').hidden=false;$('empty-chart').textContent='Der Bereich „Von“ muss kleiner oder gleich „Bis“ sein.';$('chart-status').textContent='Ungültiger Zeitbereich.';root.hidden=true;return;}
 const series=metric?traces.map(r=>pointsFor(r,metric)):[],[lo,hi]=range();
 const visible=series.map(points=>points.filter(p=>numeric(p.x)&&numeric(p.y)&&p.x>=lo&&p.x<=hi));
 const flat=visible.flat();root.hidden=!flat.length;$('empty-chart').hidden=!!flat.length;$('empty-chart').textContent='Für diesen Messwert und Ausschnitt sind keine Werte mit Zeitkoordinate erfasst.';
 if(!flat.length){$('chart-status').textContent='Keine darstellbaren Messwerte. Fehlende Werte werden nicht ergänzt.';return;}
 let xmin=Infinity,xmax=-Infinity,ymin=Infinity,ymax=-Infinity;for(const p of flat){xmin=Math.min(xmin,p.x);xmax=Math.max(xmax,p.x);ymin=Math.min(ymin,p.y);ymax=Math.max(ymax,p.y);}if(xmin===xmax){xmin-=.5;xmax+=.5;}if(ymin===ymax){ymin-=.05;ymax+=.05;}else{const pad=(ymax-ymin)*.08;ymin-=pad;ymax+=pad;}
 const X=x=>80+(x-xmin)/(xmax-xmin)*990,Y=y=>250-(y-ymin)/(ymax-ymin)*220;
 root.append(svg('title',{},(labelMap[metric.key]||metric.key)+' über '+($('axis').value==='age'?'Alter':'Zyklus')));
 for(let i=0;i<5;i++){const y=ymin+(ymax-ymin)*i/4,x=xmin+(xmax-xmin)*i/4;root.append(svg('line',{x1:80,x2:1070,y1:Y(y),y2:Y(y),stroke:'#e2e9e7'}),svg('text',{x:67,y:Y(y)+4,'text-anchor':'end',fill:'#526971','font-size':12},fmt(y)),svg('text',{x:X(x),y:277,'text-anchor':'middle',fill:'#526971','font-size':12},fmt(x)));}
 const descriptions=[];
 for(let i=0;i<series.length;i++){let path='',connected=false,missing=0;const points=series[i];for(const p of points){if(!numeric(p.x)||!numeric(p.y)){connected=false;missing++;continue;}if(p.x<lo||p.x>hi){connected=false;continue;}path+=(connected?'L':'M')+X(p.x).toFixed(2)+','+Y(p.y).toFixed(2)+' ';connected=true;}
  root.append(svg('path',{d:path,fill:'none',stroke:colors[i],'stroke-width':2.4,'stroke-dasharray':i?'7 4':'','data-run':i}));
  // Dots keep isolated values and equal-time observations visible.
  for(const p of visible[i])root.append(svg('circle',{cx:X(p.x),cy:Y(p.y),r:2,fill:colors[i]}));
  descriptions.push('Lauf '+String.fromCharCode(65+i)+': '+fmt(visible[i].length)+' sichtbare Werte; '+fmt(missing)+' Datensätze ohne gültigen Messwert oder Zeitkoordinate insgesamt.');
 }
 const selected=filtered[cursor];if(selected){const x=selected.event[$('axis').value];if(numeric(x)&&x>=xmin&&x<=xmax)root.append(svg('line',{x1:X(x),x2:X(x),y1:22,y2:250,stroke:'#6c7880','stroke-dasharray':'3 4','data-cursor':'true'}));}
 $('chart-status').textContent=descriptions.join(' ');
}
function phase(v){return ({0:'Beginn',1:'Ende','-1':'Mitteilung'})[v]||'Phase nicht erfasst';}
function selectEvent(index){cursor=Math.min(Math.max(index,0),Math.max(filtered.length-1,0));const selected=filtered[cursor];$('cursor').max=String(Math.max(0,filtered.length-1));$('cursor').value=String(cursor);$('cursor').disabled=!filtered.length;$('previous-event').disabled=!filtered.length||cursor===0;$('next-event').disabled=!filtered.length||cursor===filtered.length-1;
 if(!selected){$('selected-label').textContent='Keine Ereignisse für diese Filter.';$('event-detail').textContent='Kein Ereignis ausgewählt.';}else{$('selected-label').textContent='Lauf '+String.fromCharCode(65+selected.run)+' · Ereignis '+(cursor+1)+' von '+filtered.length+' · Zyklus '+fmt(selected.event.cycle)+' · Alter '+fmt(selected.event.age);$('event-detail').textContent=JSON.stringify(selected.event,null,2);}draw();}
function renderTable(){const body=$('events');body.replaceChildren();const start=page*50,rows=filtered.slice(start,start+50);if(!rows.length){const tr=el('tr'),td=el('td','Keine Ereignisse für diese Filter.');td.colSpan=5;tr.append(td);body.append(tr);}for(let j=0;j<rows.length;j++){const item=rows[j],e=item.event,tr=el('tr'),action=el('button',fmt(e.action));action.addEventListener('click',()=>selectEvent(start+j));const actionCell=el('td');actionCell.append(action,el('div',phase(e.status),'small muted'));tr.append(el('td',String.fromCharCode(65+item.run),item.run?'run-b':'run-a'),el('td',fmt(e.cycle)),el('td',fmt(e.age)),actionCell,el('td',fmt(e.situation)+' / '+fmt(e.object)));body.append(tr);}
 $('event-count').textContent=fmt(filtered.length)+' von '+fmt(allEvents.length);$('page-label').textContent=filtered.length?`${start+1}–${Math.min(start+50,filtered.length)} von ${filtered.length}`:'0 Ereignisse';$('previous-page').disabled=page===0;$('next-page').disabled=(page+1)*50>=filtered.length;}
function filter(){const run=$('run-filter').value,action=$('action-filter').value,query=$('event-search').value.toLocaleLowerCase('de');filtered=validRange()?allEvents.filter(item=>(run==='all'||String(item.run)===run)&&(action==='all'||item.event.action===action)&&inRange(item.event)&&JSON.stringify(item.event).toLocaleLowerCase('de').includes(query)):[];
 filtered.sort((a,b)=>{const x=a.event[$('axis').value],y=b.event[$('axis').value];if(!numeric(x))return numeric(y)?1:a.run-b.run||a.index-b.index;if(!numeric(y))return -1;return x-y||a.run-b.run||a.index-b.index;});page=0;renderTable();selectEvent(0);}
$('metric').addEventListener('change',draw);for(const id of ['axis','run-filter','action-filter'])$(id).addEventListener('change',filter);for(const id of ['from','to','event-search'])$(id).addEventListener('input',filter);
$('reset').addEventListener('click',()=>{$('from').value='';$('to').value='';$('event-search').value='';$('run-filter').value='all';$('action-filter').value='all';filter();});
$('previous-page').addEventListener('click',()=>{page--;renderTable();});$('next-page').addEventListener('click',()=>{page++;renderTable();});$('cursor').addEventListener('input',()=>selectEvent(Number($('cursor').value)));$('previous-event').addEventListener('click',()=>selectEvent(cursor-1));$('next-event').addEventListener('click',()=>selectEvent(cursor+1));
filter();
</script></body></html>'''


if __name__ == "__main__":
    raise SystemExit(main())
