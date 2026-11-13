"""The exported replay is offline, preserves samples and treats text as data."""

import copy
from html.parser import HTMLParser
import json
import shutil
import subprocess

import pytest

from psi_gw.body.picrawler.replay import write_replay


class _Document(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self.external_resources = []
        self.handlers = []
        self._script = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script":
            self._script = {"attributes": attrs, "text": ""}
            self.scripts.append(self._script)
        if tag in ("script", "img", "iframe", "link"):
            self.external_resources.extend(
                attrs[key] for key in ("src", "href") if key in attrs
            )
        self.handlers.extend(key for key in attrs if key.lower().startswith("on"))

    def handle_data(self, data):
        if self._script is not None:
            self._script["text"] += data

    def handle_endtag(self, tag):
        if tag == "script":
            self._script = None


def _frame(time_s=0.0):
    return {
        "tick": round(time_s * 20),
        "time_s": time_s,
        "pose": {"x_m": 0.0, "y_m": 0.0, "yaw_rad": 0.0, "height_m": 0.06},
        "legs": [],
        "sensor": {
            "origin": [0.05, 0, 0.06],
            "direction": [1, 0, 0],
            "distance_m": None,
            "max_range_m": 4.0,
        },
        "command": {"forward_mps": 0.0, "lateral_mps": 0.0, "yaw_rps": 0.0},
        "collision": False,
    }


def test_html_round_trip_is_safe_offline_and_does_not_mutate_input(tmp_path):
    frames = [_frame(), _frame(0.05)]
    metadata = {
        "title": '</script><script src="https://example.test/inject.js">&\u2028PiCrawler',
        "seed": 42,
        "dt_s": 0.05,
        "world": {"bounds": [-1, -1, 1, 1], "obstacles": []},
    }
    original = copy.deepcopy((frames, metadata))
    target = tmp_path / "nested" / "replay.html"
    write_replay(target, frames, metadata)
    document = _Document()
    document.feed(target.read_text(encoding="utf-8"))
    assert len(document.scripts) == 2
    assert document.external_resources == []
    assert document.handlers == []
    data_script = document.scripts[0]
    assert data_script["attributes"] == {
        "id": "replay-data",
        "type": "application/json",
    }
    assert json.loads(data_script["text"]) == {"frames": frames, "metadata": metadata}
    assert (frames, metadata) == original


@pytest.mark.parametrize("times", [[], [-0.01], [float("nan")], [float("inf")], [0.1, 0.0]])
def test_invalid_frame_times_are_rejected_without_writing(tmp_path, times):
    target = tmp_path / "replay.html"
    with pytest.raises(ValueError):
        write_replay(target, [dict(_frame(), time_s=t) for t in times], {})
    assert not target.exists()


def test_nonfinite_nested_values_are_rejected(tmp_path):
    frame = _frame()
    frame["sensor"]["distance_m"] = float("nan")
    with pytest.raises(ValueError):
        write_replay(tmp_path / "replay.html", [frame], {})


def test_recorded_camera_data_is_preserved(tmp_path):
    frame = _frame()
    frame["camera_rgb"] = [[[1, 2, 3], [253, 254, 255]]]
    target = tmp_path / "replay.html"
    write_replay(target, [frame], {})
    document = _Document()
    document.feed(target.read_text())
    assert json.loads(document.scripts[0]["text"])["frames"][0]["camera_rgb"] == frame["camera_rgb"]


_NODE_DOM_TEST = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const input=JSON.parse(fs.readFileSync(0,'utf8')),payload=JSON.parse(input.data);
let scheduled,canvasCalls=0,cameraWrites=0,lastImage;
function contextFor(id){return new Proxy({}, {get(_,key){
  if(key==='createImageData')return(w,h)=>({data:new Uint8ClampedArray(w*h*4),width:w,height:h});
  if(key==='putImageData')return image=>{lastImage=image;cameraWrites++;};
  return(...args)=>{if(['arc','moveTo','lineTo','clearRect','setTransform','rect','strokeRect'].includes(key))args.forEach(n=>assert(Number.isFinite(n),id+': '+key));canvasCalls++;};
},set(){return true;}});}
class Element{
 constructor(id){this.id=id;this.listeners={};this.style={};this.value='1';this.checked=true;this._text='';this.tagName='DIV';this.children=[];this.child={};this.classes=new Set();this.classList={toggle:(n,on)=>on?this.classes.add(n):this.classes.delete(n),add:n=>this.classes.add(n),remove:n=>this.classes.delete(n)};this.context=contextFor(id);}
 set textContent(value){this._text=value;this.children=[];}
 get textContent(){return this._text;}
 addEventListener(n,fn){this.listeners[n]=fn;}
 getContext(){return this.context;}
 getBoundingClientRect(){return this.id==='scene'?{width:900,height:530}:{width:230,height:104};}
 appendChild(child){this.children.push(child);this.child=child;}
 querySelector(){return this.child;}
 setAttribute(){}
 setPointerCapture(){}
 click(){this.listeners.click({});}
}
const elements=new Map(),get=id=>{if(!elements.has(id))elements.set(id,new Element(id));return elements.get(id);};
get('replay-data').textContent=input.data;
const document={getElementById:get,createElement:()=>new Element('generated'),addEventListener(){},activeElement:{tagName:'BODY'},hidden:false};
const runtime={document,window:{devicePixelRatio:2,addEventListener(){}},console,ResizeObserver:class{constructor(fn){this.fn=fn;}observe(){this.fn();}},requestAnimationFrame:fn=>{scheduled=fn;},Uint8ClampedArray};
vm.runInNewContext(input.code,runtime,{timeout:5000});
assert.strictEqual(get('tick').textContent,String(payload.frames[0].tick));
assert(canvasCalls>0);
if(input.mode==='peripherals'){
 for(let index=0;index<payload.frames.length;index++){
  get('scrub').listeners.input({target:{value:String(index)}});
  const f=payload.frames[index],p=f.peripherals;
  assert.strictEqual(get('tick').textContent,String(f.tick));
  assert.strictEqual(get('peripheral-panel').hidden,!p);
  if(!p)continue;
  const status=get('peripheral-status').children.map(e=>e.textContent).join(' · ');
  assert(status.includes('Benutzer-LED: '+(p.user_led?'an':'aus')));
  assert(status.includes('USR: '+(p.user_button_down?'gedrückt':'frei')));
  assert(status.includes('RST: '+(p.reset_button_down?'gedrückt':'frei')));
  assert(status.includes('Lautsprecher: '+(p.speaker.playing?'aktiv ('+p.speaker.event.mode+')':'still')));
  const events=(f.peripheral_events||[]).filter(e=>e.tick<=f.tick).slice(-8);
  assert.strictEqual(get('peripheral-log').children.length,events.length);
  events.forEach((e,i)=>{
   if(e.kind==='audio_start'&&e.audio.mode==='speak')assert(get('peripheral-log').children[i].textContent.includes(e.audio.payload.text));
  });
 }
 get('play').click();scheduled(0);scheduled(100);get('play').click();
 get('blob-overlay').listeners.change();
 get('scene').listeners.pointerdown({clientX:20,clientY:20,pointerId:1});
 get('scene').listeners.pointermove({clientX:60,clientY:40});
 get('scene').listeners.pointerup();
}else if(input.mode==='legacy'){
 assert.strictEqual(get('telemetry-dock').hidden,true);
 assert.strictEqual(get('perception-card').hidden,true);
}else{
 assert.strictEqual(get('telemetry-dock').hidden,false);
 assert.strictEqual(get('battery-voltage').textContent,'7,80 V');
 assert.strictEqual(get('hunger-value').textContent,'0,20');
 assert(get('core-voltage').textContent.includes('nicht modelliert/erfasst'));
 assert(get('telemetry-source').textContent.includes('Simulation'));
 assert.strictEqual(get('perception-card').hidden,false);
 assert.strictEqual(get('overlay-control').hidden,false);
 assert(get('color-blobs').textContent.includes('Rot'));
 assert.strictEqual(lastImage.data[0],240);
 get('scrub').listeners.input({target:{value:'1'}});
 assert.strictEqual(get('hunger-value').textContent,'0,90');
 assert.strictEqual(get('damage-value').textContent,'0,80');
 assert(get('alarms').children.some(e=>e.textContent.includes('Unterspannung')));
 assert(get('alarms').children.some(e=>e.textContent.includes('Temperaturdrosselung')));
 assert.strictEqual(get('historical-flags').hidden,false);
 get('scrub').listeners.input({target:{value:'2'}});
 assert.strictEqual(get('battery-voltage').textContent,'—');
 assert.strictEqual(get('hunger-value').textContent,'—');
 assert.strictEqual(get('needs-panel').hidden,true);
 assert.strictEqual(get('perception-card').hidden,true);
 assert.strictEqual(get('overlay-control').hidden,true);
 assert(get('alarms').children.some(e=>e.textContent==='Keine Statusflags aufgezeichnet'));
}
get('top').click();get('zoom-in').click();get('zoom-out').click();get('restart').click();
assert.strictEqual(get('tick').textContent,String(payload.frames[0].tick));
console.log(JSON.stringify({passed:true,canvasCalls,cameraWrites}));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="optional JavaScript runtime for offline DOM/Canvas execution")
@pytest.mark.parametrize("mode", ["legacy", "telemetry", "telemetry_history"])
def test_replay_executes_with_legacy_and_extended_frames_without_a_browser(tmp_path, mode):
    """Run the actual embedded script, not a reimplementation of its logic.

    This checks state changes and numerical Canvas calls. It is deliberately
    not presented as browser layout or screenshot verification.
    """
    frames = [_frame(0), _frame(0.05), _frame(0.10)]
    if mode != "legacy":
        from psi_gw.body.picrawler.perception import perceive

        pixels = [[[240, 20, 20]] * 2 for _ in range(2)]
        features = perceive({"camera": {"rgb": pixels}, "ultrasonic": {"distance_m": 0.3}},
                            now_s=0, sample_time_s=0).to_dict()
        frames[0].update(
            camera_rgb=pixels, perception=features,
            telemetry={"battery_voltage_v": 7.8, "state_of_charge": 0.8,
                       "cpu_temperature_c": 50, "core_voltage_v": None,
                       "supply_voltage_v": 5.0, "current_a": 0.7, "power_w": 3.5,
                       "undervoltage": False, "thermal_throttled": False,
                       "power_limited": False, "battery_depleted": False,
                       "source": "simulated"},
            needs={"hunger": 0.2, "damage": 0.0},
        )
        frames[1].update(
            telemetry={"battery_voltage_v": 6.3, "state_of_charge": 0.1,
                       "cpu_temperature_c": 85, "current_a": 1.4, "power_w": 7.0,
                       "undervoltage": True, "thermal_throttled": True,
                       "power_limited": True, "battery_depleted": False,
                       "historical_flags": {"undervoltage": True}, "source": "simulated"},
            needs={"hunger": 0.9, "damage": 0.8},
        )
        if mode == "telemetry_history":
            frames[1]["telemetry"]["history"] = frames[1]["telemetry"].pop("historical_flags")
    target = tmp_path / "replay.html"
    write_replay(target, frames, {"seed": 7, "dt_s": 0.05})
    document = _Document()
    document.feed(target.read_text())
    run = subprocess.run(
        [shutil.which("node"), "-e", _NODE_DOM_TEST],
        input=json.dumps({"code": document.scripts[1]["text"],
                          "data": document.scripts[0]["text"], "mode": mode}),
        capture_output=True, text=True, timeout=15, check=False,
    )
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout)["passed"]


@pytest.mark.skipif(shutil.which("node") is None, reason="optional JavaScript runtime")
def test_peripheral_replay_script_scrubs_audio_led_buttons_and_literal_speech(tmp_path):
    from psi_gw.body import Action
    from psi_gw.body.picrawler import PiCrawlerSimBody, SimConfig

    body = PiCrawlerSimBody(config=SimConfig(peripherals_enabled=True))
    frames = [body.frame()]
    body.act(Action("led", {"on": True}))
    frames.append(body.frame())
    body.inject_button("user", True)
    body.act(Action("speak", {"text": "</script><b>Warnung</b>", "duration_s": .1}))
    frames.append(body.frame())
    body.act(Action("stop"))
    frames.append(body.frame())
    target = tmp_path / "peripherals.html"
    write_replay(target, frames, {"dt_s": body.config.dt_s})
    document = _Document()
    document.feed(target.read_text())
    assert len(document.scripts) == 2
    result = subprocess.run([shutil.which("node"), "-e", _NODE_DOM_TEST],
        input=json.dumps({"code": document.scripts[1]["text"],
                          "data": document.scripts[0]["text"], "mode": "peripherals"}),
        capture_output=True, text=True, timeout=15, check=True)
    assert json.loads(result.stdout)["passed"]
