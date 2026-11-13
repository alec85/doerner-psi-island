"""Evaluator isolation, generated-world feasibility and complete continuation."""

from dataclasses import asdict
import copy
import json
import subprocess
import sys

import pytest

from psi_gw.body import Action, Observation
from psi_gw.body.picrawler.robot_benchmark import BenchmarkCase, DeliveryBuffer, Episode, run_episode, run_suite
from psi_gw.body.picrawler.robot_controllers import ReferenceController, sensor_view
from psi_gw.body.picrawler.robot_courses import FAMILIES, generate_course, reachable_cells, cell_center
from psi_gw.body.picrawler.temporal import SensorMemory
from psi_gw.body.picrawler.validation_io import canonical, digest, read_json


def observation(tick, distance=.8, *, hunger=0.0, captured=None):
    return Observation(tick, {"ultrasonic": {"status": "ok" if distance is not None else "dropout",
        "distance_m": distance, "captured_at_s": tick * .05 if captured is None else captured}},
        {"hunger": hunger, "damage": 0.0})


def camera(x=4, *, captured=0.0, present=True):
    pixels = [[[20, 20, 20] for _ in range(24)] for _ in range(16)]
    if present:
        for yy in range(5, 9):
            for xx in range(x, x + 4):
                pixels[yy][xx] = [230, 20, 20]
    return {"rgb": pixels, "width": 24, "height": 16, "encoding": "rgb8", "captured_at_s": captured}


@pytest.mark.parametrize("family", FAMILIES)
@pytest.mark.parametrize("seed", [0, 1, 2, 3, 1000, 1001, 1002, 1003])
def test_seeded_courses_have_a_conservative_path_and_are_reproducible(seed, family):
    a, b = generate_course(seed, family), generate_course(seed, family)
    assert a.snapshot() == b.snapshot()
    cells = reachable_cells(a.world, (a.initial_x_m, a.initial_y_m))
    assert any(cell_center(c)[0] >= .35 for c in cells)
    assert all(a.world.is_free(*cell_center(c), .18) for c in cells)


def test_sensor_view_discards_world_pose_truth_and_unrecognized_fields():
    raw = observation(0)
    raw.sensors.update(world={"name": "secret"}, pose={"x": 100})
    raw.sensors["ultrasonic"]["truth_distance_m"] = .01
    raw.internal["debug_goal"] = 1
    view = sensor_view(raw)
    assert set(view.sensors) == {"ultrasonic"}
    assert set(view.sensors["ultrasonic"]) == {"distance_m", "status", "captured_at_s"}
    assert set(view.internal) == {"hunger", "damage"}
    a, b = ReferenceController("memory", 7), ReferenceController("memory", 7)
    assert a.choose(raw) == b.choose(observation(0))
    assert digest(a.snapshot()) == digest(b.snapshot())
    view.sensors["ultrasonic"]["distance_m"] = 2
    assert raw.sensors["ultrasonic"]["distance_m"] == .8


@pytest.mark.parametrize("policy", ["reactive", "memory"])
def test_unknown_echo_stops_and_energy_stop_latches(policy):
    c = ReferenceController(policy)
    assert c.choose(observation(0, None)).name == "stop"
    assert c.choose(observation(1, hunger=.9)).name == "stop"
    assert c.last_decision["mode"] == "energy_stop"
    assert c.choose(observation(2, hunger=0)).name == "stop"


def test_duplicate_decision_does_not_advance_state_and_conflicting_replay_is_rejected():
    c = ReferenceController("memory")
    obs = observation(0)
    action = c.choose(obs)
    state = copy.deepcopy(c.snapshot())
    assert c.choose(obs) == action
    assert c.snapshot() == state
    with pytest.raises(ValueError, match="conflicting"):
        c.choose(observation(0, .1))
    with pytest.raises(ValueError, match="backwards"):
        c.choose(observation(2)); c.choose(observation(1))


def test_temporal_range_is_bounded_does_not_refresh_duplicates_and_handles_sudden_near_echo():
    m = SensorMemory()
    assert m.update(observation(0).sensors, now_s=0)["range_source"] == "measured"
    # A dropout may briefly retain a conservative estimate at the original timestamp.
    sample = m.update(observation(1, None).sensors, now_s=.05)
    assert sample["range_source"] == "held_estimate" and sample["distance_m"] < .8
    m.update(observation(0).sensors, now_s=.10)
    assert m.range_capture == 0
    assert m.update(observation(4, None).sensors, now_s=.20)["distance_m"] is None
    m.update(observation(5).sensors, now_s=.25)
    near = m.update(observation(6, .1).sensors, now_s=.30)
    assert near["distance_m"] <= .1


def test_old_beam_is_not_reused_after_rotation_even_when_delivery_timestamp_is_recent():
    m = SensorMemory()
    m.update(observation(0).sensors, now_s=0)
    assert m.update(observation(0).sensors, now_s=.05, rotated=True)["distance_m"] is None
    assert m.update(observation(0).sensors, now_s=.10)["distance_m"] is None
    assert m.update(observation(3).sensors, now_s=.15)["range_source"] == "measured"


def test_temporal_colour_tracks_survive_brief_occlusion_but_expire_and_ignore_duplicates():
    m = SensorMemory()
    a = m.update({"camera": camera()}, now_s=0)["tracks"][0]
    repeated = m.update({"camera": camera()}, now_s=.05)["tracks"][0]
    assert repeated["id"] == a["id"] and repeated["hits"] == 1
    moved = m.update({"camera": camera(5, captured=.1)}, now_s=.1)["tracks"][0]
    assert moved["id"] == a["id"] and moved["hits"] == 2
    hidden = m.update({"camera": camera(captured=.15, present=False)}, now_s=.15)["tracks"][0]
    assert hidden["id"] == a["id"] and not hidden["observed_now"]
    assert m.update({"camera": camera(captured=.5, present=False)}, now_s=.5)["tracks"] == []


def test_future_images_cannot_create_tracks_and_region_assignment_is_one_to_one():
    m = SensorMemory()
    assert m.update({"camera": camera(captured=1)}, now_s=0)["tracks"] == []
    image = camera()
    for y in range(5, 9):
        for x in range(14, 18):
            image["rgb"][y][x] = [230, 20, 20]
    tracks = m.update({"camera": image}, now_s=0)["tracks"]
    assert len(tracks) == 2 and len({t["id"] for t in tracks}) == 2


@pytest.mark.parametrize("policy", ["reactive", "memory"])
@pytest.mark.parametrize("profile", ["nominal", "noisy", "delayed"])
def test_complete_episode_checkpoint_preserves_every_following_tick(policy, profile):
    episode = Episode(BenchmarkCase(0, "slalom", policy, profile, "progress", max_ticks=50))
    for _ in range(13):
        episode.step()
    restored = Episode.restore(json.loads(canonical(episode.snapshot())))
    assert digest(episode.snapshot()) == digest(restored.snapshot())
    while not episode.done:
        episode.step(); restored.step()
        assert digest(episode.snapshot()) == digest(restored.snapshot())
    assert episode.result() == restored.result()


def test_dynamic_obstacle_is_inserted_without_teleporting_body_and_survives_checkpoint():
    episode = Episode(BenchmarkCase(0, "gate", "memory", "nominal", "progress", max_ticks=315))
    for _ in range(300):
        episode.step()
    before = episode.snapshot()
    resumed = Episode.restore(json.loads(canonical(before)))
    episode.step(); resumed.step()
    assert episode.world_event in ("inserted", "skipped_occupied")
    assert digest(episode.snapshot()) == digest(resumed.snapshot())
    assert episode.body.world.is_free(episode.body.frame()["pose"]["x_m"], episode.body.frame()["pose"]["y_m"], .18)


def test_delivery_preserves_acquisition_time_and_fresh_internal_signals():
    buffer = DeliveryBuffer("delayed")
    for tick in range(8):
        received = buffer.deliver(observation(tick, distance=.8 - tick * .01, hunger=tick / 10))
    assert received.tick == 7
    assert received.internal["hunger"] == .7
    assert received.sensors["ultrasonic"]["captured_at_s"] == pytest.approx(.15)
    restored = DeliveryBuffer.restore(json.loads(canonical(buffer.snapshot())))
    assert restored.deliver(observation(8)) == buffer.deliver(observation(8))


@pytest.mark.parametrize("policy", ["reactive", "memory"])
def test_energy_task_stops_within_declared_deadline_and_is_checkpoint_verified(policy):
    report = run_episode(BenchmarkCase(0, "open", policy, "nominal", "energy_stop"))
    assert report["success"] and report["energy_reaction_ticks"] <= 2
    assert report["metrics"]["late_stop_ticks"] == 0
    assert report["verified_continuation_ticks"] == 5


def test_open_course_progress_is_reached_from_sensor_control_without_world_inputs():
    report = run_episode(BenchmarkCase(0, "open", "memory", "nominal", "progress"))
    assert report["success"], report
    assert report["ticks"] <= 900 and report["distance_m"] >= .99


def test_suite_resume_checks_integrity_and_regenerated_runs_are_identical(tmp_path):
    cases = [BenchmarkCase(0, "open", p, "nominal", "energy_stop") for p in ("reactive", "memory")]
    a = run_suite(tmp_path / "a", cases)
    b = run_suite(tmp_path / "b", cases)
    assert a == b
    assert run_suite(tmp_path / "a", cases, resume=True) == a
    path = tmp_path / "a/cases" / (cases[0].id + ".json")
    value = read_json(path); value["success"] = False; path.write_text(canonical(value))
    with pytest.raises(ValueError, match="corrupt"):
        run_suite(tmp_path / "a", cases, resume=True)


@pytest.mark.parametrize("split,seed", [("validation", 0), ("development", 1000), ("development", True)])
def test_development_and_validation_seeds_cannot_be_mixed(split, seed):
    with pytest.raises(ValueError):
        BenchmarkCase(seed, "open", "memory", "nominal", "progress", split)


def test_cli_can_run_in_a_separate_working_directory(tmp_path):
    run = subprocess.run([sys.executable, "-m", "psi_gw.body.picrawler.robot_benchmark",
        "--output", str(tmp_path / "suite"), "--seeds", "0", "--families", "open",
        "--tasks", "energy_stop", "--sensors", "nominal"], cwd=tmp_path,
        capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout)["successful"] == 2


def test_embedded_replay_script_renders_the_recorded_world_for_each_frame(tmp_path):
    import importlib.util
    import shutil
    from pathlib import Path
    from psi_gw.body.picrawler.replay import write_replay

    if shutil.which("node") is None:
        pytest.skip("optional JavaScript runtime")
    spec = importlib.util.spec_from_file_location("replay_helpers", Path(__file__).with_name("test_replay.py"))
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    frames = [helper._frame(i * .05) for i in range(3)]
    frames[0]["world"] = {"obstacles": []}
    frames[1]["world"] = {"obstacles": [{"x_min": 0, "x_max": .2, "y_min": 0, "y_max": .2, "height_m": .2}]}
    frames[2]["world"] = {"obstacles": []}
    path = tmp_path / "world.html"
    write_replay(path, frames, {})
    document = helper._Document(); document.feed(path.read_text())
    probe = '''
if(input.mode==='dynamic'){
 get('scrub').listeners.input({target:{value:'0'}});const before=canvasCalls;
 get('scrub').listeners.input({target:{value:'0'}});const empty=canvasCalls-before;
 const start=canvasCalls;get('scrub').listeners.input({target:{value:'1'}});
 assert(canvasCalls-start>empty+20,'recorded obstacle was not rendered');
 const last=canvasCalls;get('scrub').listeners.input({target:{value:'2'}});
 assert(canvasCalls-last<empty+20,'obstacle persisted after the frame removed it');
}else if(input.mode==='peripherals'){
'''
    code = helper._NODE_DOM_TEST.replace("if(input.mode==='peripherals'){", probe)
    run = subprocess.run([shutil.which("node"), "-e", code],
        input=json.dumps({"code": document.scripts[1]["text"], "data": document.scripts[0]["text"], "mode": "dynamic"}),
        capture_output=True, text=True, timeout=20)
    assert run.returncode == 0, run.stderr


def test_example_export_failure_leaves_no_partial_directory_and_can_be_retried(tmp_path, monkeypatch):
    from psi_gw.body.picrawler import robot_benchmark

    case = BenchmarkCase(0, "open", "memory", "nominal", "energy_stop")
    original = robot_benchmark.write_replay
    def fail(*args, **kwargs):
        raise OSError("injected interrupted export")
    monkeypatch.setattr(robot_benchmark, "write_replay", fail)
    target = tmp_path / "episode"
    with pytest.raises(OSError, match="interrupted"):
        run_episode(case, target)
    assert not target.exists() and list(tmp_path.iterdir()) == []
    monkeypatch.setattr(robot_benchmark, "write_replay", original)
    assert run_episode(case, target)["success"]
    assert (target / "replay.html").exists()


@pytest.mark.parametrize("policy", ["reactive", "memory"])
@pytest.mark.parametrize("profile", ["nominal", "noisy", "delayed"])
def test_full_episode_continuation_matches_in_a_fresh_process(tmp_path, policy, profile):
    episode = Episode(BenchmarkCase(0, "gate", policy, profile, "progress", max_ticks=60))
    for _ in range(13):
        episode.step()
    path = tmp_path / "checkpoint.json"
    path.write_text(canonical(episode.snapshot()))
    expected = []
    for _ in range(12):
        episode.step(); expected.append(digest(episode.snapshot()))
    script = '''
import json,sys
from psi_gw.body.picrawler.robot_benchmark import Episode
from psi_gw.body.picrawler.validation_io import digest
episode=Episode.restore(json.load(open(sys.argv[1])))
states=[]
for _ in range(12):
    episode.step();states.append(digest(episode.snapshot()))
print(json.dumps(states))
'''
    run = subprocess.run([sys.executable, "-c", script, str(path)], cwd=tmp_path,
                         capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout) == expected
