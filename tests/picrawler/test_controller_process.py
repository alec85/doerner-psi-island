"""Actual subprocesses, partial pipes, fencing, replay and bounded write failure."""

from dataclasses import asdict
import json
import subprocess
import sys
import time

import pytest

from psi_gw.body import Action, Observation
from psi_gw.body.picrawler.controller_process import ProcessController, parse_line, validated_action
from psi_gw.body.picrawler.robot_benchmark import BenchmarkCase, Episode, run_episode, run_process_episode
from psi_gw.body.picrawler.robot_controllers import ReferenceController
from psi_gw.body.picrawler.validation_io import canonical, digest


def obs(tick, distance=.8):
    return Observation(tick, {"ultrasonic": {"status": "ok", "distance_m": distance, "captured_at_s": tick * .05}},
                       {"hunger": 0.0, "damage": 0.0})


@pytest.mark.parametrize("policy", ["reactive", "memory"])
def test_real_child_decisions_states_and_checkpoint_restart_equal_direct_policy(policy):
    direct, previous = ReferenceController(policy, 17), Action("stop")
    with ProcessController(policy, 17) as remote:
        assert remote.process.pid != __import__("os").getpid()
        assert not remote.failed, remote.failure_reason
        for tick in range(24):
            value = obs(tick, .2 if 6 <= tick < 12 else .8)
            actual = remote.choose(value, previous)
            expected = direct.choose(value, previous)
            assert actual == expected, remote.failure_reason
            assert digest(remote.snapshot()) == digest(direct.snapshot())
            previous = expected
            if tick == 12:
                saved = remote.snapshot()
                assert remote.restart(state=saved)
    assert remote.process.poll() is not None


@pytest.mark.parametrize("policy", ["reactive", "memory"])
def test_real_process_episode_and_direct_episode_have_identical_results(policy):
    case = BenchmarkCase(0, "slalom", policy, "delayed", "progress", max_ticks=45)
    direct, remote = run_episode(case), run_process_episode(case)
    assert remote == direct


def test_killed_child_causes_body_stop_and_stays_fenced_until_explicit_new_session():
    with ProcessController("memory", 20_000) as remote:
        episode = Episode(BenchmarkCase(0, "open", "memory", "nominal", "progress", max_ticks=50), controller=remote)
        for _ in range(5):
            episode.step()
        before = episode.body.frame()["pose"]
        old_session = remote.session
        remote.process.kill(); remote.process.wait(timeout=2)
        episode.step()
        assert remote.failed and episode.done
        assert episode.previous_action == Action("stop")
        assert episode.body.frame()["pose"] == before
        restored = Episode.restore(json.loads(canonical(episode.snapshot())))
        assert restored.result() == episode.result()
        assert remote.choose(obs(7)) == Action("stop")
        assert remote.restart() and remote.session != old_session
        assert remote.choose(obs(8)).name == "drive"


_READY = '''
import sys,json,time
from psi_gw.body.picrawler.robot_controllers import ReferenceController,ControllerConfig
r=json.loads(sys.stdin.readline())
c=ReferenceController(r['payload']['policy'],r['payload']['seed'],ControllerConfig(**r['payload']['config']))
response={'version':1,'session':r['session'],'sequence':0,'ok':True,'payload':{'state':c.snapshot()}}
sys.stdout.write(json.dumps(response)+'\\n');sys.stdout.flush()
'''


def test_nonreading_worker_cannot_block_a_large_request_write():
    command = [sys.executable, "-c", _READY + "time.sleep(10)\n"]
    with ProcessController("reactive", timeout_s=.05, worker_command=command) as remote:
        assert not remote.failed, remote.failure_reason
        large = obs(0)
        large.sensors["camera"] = {"rgb": [[[20, 20, 20]] * 320 for _ in range(240)],
            "width": 320, "height": 240, "encoding": "rgb8", "captured_at_s": 0.0}
        start = time.monotonic()
        assert remote.choose(large) == Action("stop")
        assert remote.failed and "deadline" in remote.failure_reason
        assert time.monotonic() - start < 5
        assert remote.process.poll() is not None


def test_partial_response_without_newline_times_out_and_does_not_become_an_action():
    script = _READY + "sys.stdin.readline();sys.stdout.write('{');sys.stdout.flush();time.sleep(10)\n"
    with ProcessController("reactive", timeout_s=.05, worker_command=[sys.executable, "-c", script]) as remote:
        assert remote.choose(obs(0)) == Action("stop")
        assert remote.failed and "deadline" in remote.failure_reason


@pytest.mark.parametrize("mutation", ["wrong_session", "wrong_sequence", "overspeed", "nonfinite"])
def test_invalid_worker_response_is_rejected_before_body_execution(mutation):
    script = _READY + '''
r=json.loads(sys.stdin.readline());a=c.choose(__import__('psi_gw.body',fromlist=['Observation']).Observation(**r['payload']['observation']))
response={'version':1,'session':r['session'],'sequence':r['sequence'],'ok':True,'payload':{'action':{'name':a.name,'params':a.params},'state':c.snapshot(),'decision':c.last_decision}}
'''
    script += {
        "wrong_session": "response['session']='other'\n",
        "wrong_sequence": "response['sequence']+=1\n",
        "overspeed": "response['payload']['action']['params']={'forward_mps':99}\n",
        "nonfinite": "response['payload']['action']['params']={'forward_mps':float('nan')}\n",
    }[mutation]
    script += "sys.stdout.write(json.dumps(response)+'\\n');sys.stdout.flush()\n"
    with ProcessController("reactive", worker_command=[sys.executable, "-c", script]) as remote:
        assert remote.choose(obs(0)) == Action("stop")
        assert remote.failed


def test_worker_caches_identical_request_and_rejects_a_conflicting_sequence():
    config = asdict(ReferenceController("reactive").config)
    init = {"version": 1, "session": "test", "sequence": 0, "operation": "init",
            "payload": {"policy": "reactive", "seed": 0, "config": config, "state": None}}
    choose = {"version": 1, "session": "test", "sequence": 1, "operation": "choose",
              "payload": {"observation": asdict(obs(0)), "previous_action": asdict(Action("stop"))}}
    conflict = json.loads(canonical(choose)); conflict["payload"]["observation"]["tick"] = 1
    run = subprocess.run([sys.executable, "-m", "psi_gw.body.picrawler.controller_process", "--worker"],
        input="\n".join(canonical(x) for x in (init, choose, choose, conflict)) + "\n",
        capture_output=True, text=True, timeout=10)
    lines = run.stdout.splitlines()
    assert lines[1] == lines[2]
    assert json.loads(lines[3])["ok"] is False and run.returncode == 2


@pytest.mark.parametrize("line", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}', b'[]'])
def test_protocol_rejects_duplicate_nonfinite_and_nonobject_json(line):
    with pytest.raises(ValueError):
        parse_line(line)


@pytest.mark.parametrize("action", [
    {"name": "drive", "params": {"yaw_rps": True}},
    {"name": "stop", "params": {"forward_mps": 0}},
    {"name": "drive", "params": {"forward_mps": .03, "lateral_mps": .03}},
    {"name": "speak", "params": {}},
    {"name": "drive", "params": {"forward_mps": 10**1000}},
])
def test_reference_process_action_envelope_is_strict(action):
    with pytest.raises(ValueError):
        validated_action(action)


def test_worker_command_rejects_shell_text():
    with pytest.raises(ValueError, match="argument list"):
        ProcessController("reactive", worker_command="python --worker")
