"""Read-only exports, strict JSON embedding, incomplete data and CLI failures."""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from psi_gw.tracing import Run, RunHeader, CycleRecord, EventRecord, write_run, compute_summary
from psi_gw.tracing.vocabulary import COUNTER_NAMES
from psi_gw.ui.trace_viewer import export_viewer, load_trace, render_html


def sample_run():
    run = Run(RunHeader(source="python", seed=0, world="InselIII", params={"variant": "reference"}),
        cycles=[CycleRecord(cycle=0, age=0, counters={k: 0 for k in COUNTER_NAMES},
                            need_pct={"hunger": 0}, stage_times=None)],
        events=[EventRecord(action="Start", cycle=1, age=0, needs={"hunger": 0.0},
                            modulators={"arousal": .2}, object=None),
                EventRecord(action="Motivation", cycle=1, age=2, params=["Hunger", "0.1"],
                            needs={"hunger": None}, modulators={})])
    return run


def embedded(document):
    raw = document.split('<script id="trace-data" type="application/json">',1)[1].split('</script>',1)[0]
    return json.loads(raw, parse_constant=lambda x: pytest.fail(f"non-JSON token {x}"))


@pytest.mark.parametrize("suffix", [".jsonl", ".jsonl.gz"])
def test_source_unchanged_and_exact_records_embedded(tmp_path, suffix):
    path = tmp_path / ("run"+suffix)
    run = sample_run()
    run.summary = compute_summary(run)
    write_run(path, run)
    before = path.read_bytes()
    output = tmp_path / "viewer.html"
    export_viewer([path], output)
    assert path.read_bytes() == before
    data = embedded(output.read_text())[0]
    assert data["header"] == run.header.to_dict()
    assert data["events"] == [e.to_dict() for e in run.events]
    assert data["cycles"] == [c.to_dict() for c in run.cycles]
    assert data["summary"] == run.summary.to_dict()
    assert data["sha256"] == hashlib.sha256(before).hexdigest()
    assert data["header"]["seed"] == 0


def test_missing_data_never_becomes_zero(tmp_path):
    path=tmp_path / "partial.jsonl"
    write_run(path,sample_run())
    data=load_trace(path)
    assert data["summary"] is None
    assert data["events"][1]["needs"]["hunger"] is None
    assert "thirst" not in data["events"][1]["needs"]
    assert data["cycles"][0]["stage_times"] is None


def test_header_only_run_and_two_run_export(tmp_path):
    a,b=tmp_path / 'a.jsonl',tmp_path / 'b.jsonl'
    write_run(a,Run(RunHeader(source="delphi")))
    write_run(b,sample_run())
    output=tmp_path / 'compare.html'
    export_viewer([a,b],output)
    data=embedded(output.read_text())
    assert len(data)==2
    assert data[0]["events"]==[]
    assert data[0]["summary"] is None


def test_script_injection_is_inert_and_round_trips(tmp_path):
    text='</script><script>globalThis.injected=1</script>&<img src=x onerror=alert(1)>\u2028\u2029'
    run=sample_run();run.header.params["text"]=text;run.events[0].action=text
    path=tmp_path / 'attack.jsonl';write_run(path,run)
    document=render_html([load_trace(path)])
    assert '</script><script>globalThis.injected' not in document
    assert '<img src=x' not in document
    assert embedded(document)[0]["events"][0]["action"]==text


@pytest.mark.parametrize('value',[float('nan'),float('inf'),-float('inf')])
def test_nonfinite_values_become_explicit_missing(tmp_path,value):
    run=sample_run();run.events[0].needs['hunger']=value
    path=tmp_path / 'nonfinite.jsonl';write_run(path,run)
    data=embedded(render_html([load_trace(path)]))[0]
    assert data['events'][0]['needs']['hunger'] is None
    assert data['nonfinite_values']==1


@pytest.mark.parametrize('force',[False,True])
def test_output_never_overwrites_input_or_alias(tmp_path,force):
    path=tmp_path / 'run.jsonl';write_run(path,sample_run());before=path.read_bytes()
    with pytest.raises(ValueError,match='input trace'):
        export_viewer([path],path,force=force)
    alias=tmp_path / 'alias.html';alias.symlink_to(path)
    with pytest.raises(ValueError,match='input trace'):
        export_viewer([path],alias,force=force)
    assert path.read_bytes()==before


def test_existing_output_requires_force(tmp_path):
    path=tmp_path / 'run.jsonl';write_run(path,sample_run())
    output=tmp_path / 'report.html';output.write_text('existing')
    with pytest.raises(FileExistsError):export_viewer([path],output)
    assert output.read_text()=='existing'
    export_viewer([path],output,force=True)
    assert len(embedded(output.read_text()))==1
    assert not list(tmp_path.glob('.trace-viewer-*'))


@pytest.mark.parametrize('contents',['', '{}\n', '[]\n', '{invalid',
    '{"type":"run","source":"python","format_version":999}\n',
    '{"type":"run","source":"python","format_version":1}\n{"type":"event","action":"A","position":[]}\n'])
def test_invalid_input_does_not_create_or_replace_report(tmp_path,contents):
    path=tmp_path / 'bad.jsonl';path.write_text(contents)
    output=tmp_path / 'report.html';output.write_text('existing')
    with pytest.raises((ValueError,KeyError,TypeError)):
        export_viewer([path],output,force=True)
    assert output.read_text()=='existing'


def test_cli_export_and_missing_input(tmp_path):
    path=tmp_path / 'run.jsonl.gz';write_run(path,sample_run())
    output=tmp_path / 'new-dir' / 'viewer.html'
    cmd=[sys.executable,'-m','psi_gw.ui.trace_viewer',str(path),'--output',str(output)]
    result=subprocess.run(cmd,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert output.exists()
    before=output.read_bytes()
    result=subprocess.run([sys.executable,'-m','psi_gw.ui.trace_viewer',str(tmp_path/'missing'),
                           '--output',str(output),'--force'],capture_output=True,text=True)
    assert result.returncode==2
    assert 'trace viewer:' in result.stderr
    assert output.read_bytes()==before


@pytest.mark.parametrize('count',[0,3])
def test_input_count_is_bounded(tmp_path,count):
    with pytest.raises(ValueError,match='one or two'):
        export_viewer([tmp_path/'x']*count,tmp_path/'out.html')


def test_invalid_gzip_does_not_create_report(tmp_path):
    path=tmp_path/'broken.jsonl.gz';path.write_bytes(b'not gzip')
    with pytest.raises(OSError):export_viewer([path],tmp_path/'out.html')
    assert not (tmp_path/'out.html').exists()
