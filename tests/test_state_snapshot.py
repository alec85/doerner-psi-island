"""Acceptance test for persistence (ADR 0010): resuming equals not stopping.

A run is stopped after k steps, written to JSON, restored in a fresh Python
process and continued. Draws and final state must match an uninterrupted run
exactly, and so must the complete state after every single step (a
difference can vanish again later, e.g. when a need store is capped at 1).
Hidden state anywhere in PsiState makes this fail.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import state_workload as wl  # noqa: E402

RESUME = """
import json, sys
sys.path.insert(0, {tests!r})
import state_workload as wl
st = wl.restore(json.load(open({path!r})))
prints = wl.run(st, {steps})
print(json.dumps({{"draws": wl.draw_log(st), "state": wl.snapshot(st), "prints": prints}}))
"""


@pytest.mark.parametrize("seed,k,m", [(16, 150, 350), (901, 1, 500)])
def test_resume_in_fresh_process_equals_uninterrupted_run(tmp_path, seed, k, m):
    full = wl.new_state(seed)
    full_prints = wl.run(full, k + m)

    part = wl.new_state(seed)
    for _ in range(k):
        wl.step(part)
    cut = len(part.rng.log)
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(wl.snapshot(part)))

    script = RESUME.format(tests=str(Path(__file__).parent), path=str(path), steps=m)
    out = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=True)
    resumed = json.loads(out.stdout)

    assert resumed["draws"] == json.loads(json.dumps(wl.draw_log(full)[cut:]))
    assert resumed["prints"] == full_prints[k:]  # identical state after every step
    assert resumed["state"] == json.loads(json.dumps(wl.snapshot(full)))
    # the workload must actually exercise memory, protocol and motivation
    sites = {d.site for d in full.rng.log}
    assert {"UStrukturen.Decay#1", "UStrukturen.Junction#1", "UStrukturen.LSection#1"} <= sites
    assert any(n.name.startswith("P") for n in full.net.neurons)
    assert full.cycle > 10 and sum(full.motivation.station_count) > 10
    assert "UPSIMain.GoalGen#1" in sites


def test_snapshot_round_trip_keeps_identities():
    st = wl.new_state(5)
    for _ in range(300):
        wl.step(st)
    copy = wl.restore(json.loads(json.dumps(wl.snapshot(st))))
    old, new = st.net.neurons, copy.net.neurons
    for n_old, n_new in zip(old, new):
        for a_old, a_new in zip(n_old.axon, n_new.axon):
            assert [new.index(s.target) for s in a_new] == [old.index(s.target) for s in a_old]
    assert [new.index(n) for n in copy.protocol.kzg] == [old.index(n) for n in st.protocol.kzg]
    assert copy.motivation.aras is new[4] and copy.aggressio is new[13]
