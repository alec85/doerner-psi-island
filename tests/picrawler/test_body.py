"""Behaviour, isolation and process-resume checks for the PiCrawler body."""

from __future__ import annotations

import copy
import json
import math
import os
from pathlib import Path
import subprocess
import sys

import pytest

from psi_gw.body import Action, Body, Observation
from psi_gw.body.picrawler import (
    CameraConfig,
    Obstacle,
    PiCrawlerSimBody,
    RangeConfig,
    SimConfig,
    World,
)
from psi_gw.body.picrawler.kinematics import LEG_ORDER
from psi_gw.random_source import DelphiRandom, NumpySource, ReplaySource


def json_state(body):
    """Compare the real on-disk representation, including tuples converted to lists."""
    return json.loads(json.dumps(body.snapshot(), allow_nan=False))


def body_in_open_arena(**config):
    values = {"initial_x_m": 0.0, "camera_enabled": False}
    values.update(config)
    return PiCrawlerSimBody(World((-5, -5, 5, 5)), SimConfig(**values), seed=37)


def assert_leg_geometry(body, frame):
    geometry = body.config.geometry
    assert tuple(leg["name"] for leg in frame["legs"]) == LEG_ORDER
    for leg in frame["legs"]:
        points = leg["points"]
        assert len(points) == 4
        assert [math.dist(a, b) for a, b in zip(points, points[1:])] == pytest.approx(
            [geometry.coxa_m, geometry.upper_m, geometry.lower_m], abs=2e-12
        )
        assert all(math.isfinite(value) for point in points for value in point)
        assert -1e-12 <= points[-1][2] <= body.config.foot_lift_m + 1e-12
        if leg["stance"]:
            assert points[-1][2] == pytest.approx(0.0, abs=1e-12)


def test_body_protocol_reset_and_exactly_one_tick_per_accepted_action():
    body = body_in_open_arena()
    assert isinstance(body, Body)
    first = body.reset(19)
    assert isinstance(first, Observation)
    assert first.tick == 0
    assert body.tick == 0
    assert body.time_s == 0
    assert body.available_actions() == ["drive", "stop", "stand"]
    actions = [Action("drive", {"forward_mps": 0.02}), Action("stop"), Action("stand"), Action("drive")]
    for tick, action in enumerate(actions, 1):
        assert body.act(action) is None
        assert body.tick == tick
        assert body.time_s == tick * body.config.dt_s
        assert body.observe().tick == tick
        assert body.frame()["tick"] == tick


@pytest.mark.parametrize(
    ("command", "expected_pose"),
    [
        ({"forward_mps": 0.03}, (0.03, 0, 0)),
        ({"forward_mps": -0.03}, (-0.03, 0, 0)),
        ({"lateral_mps": 0.03}, (0, 0.03, 0)),
        ({"lateral_mps": -0.03}, (0, -0.03, 0)),
        ({"yaw_rps": 0.3}, (0, 0, 0.3)),
        ({"yaw_rps": -0.3}, (0, 0, -0.3)),
    ],
)
def test_drive_directions_and_rates_over_one_second(command, expected_pose):
    body = body_in_open_arena()
    for _ in range(20):
        body.act(Action("drive", command))
        frame = body.frame()
        assert not frame["collision"]
        assert not frame["workspace_limited"]
        assert_leg_geometry(body, frame)
    pose = frame["pose"]
    assert (pose["x_m"], pose["y_m"], pose["yaw_rad"]) == pytest.approx(expected_pose, abs=1e-12)


def test_forward_command_is_in_body_frame_after_initial_rotation():
    body = body_in_open_arena(initial_yaw_rad=math.pi / 2)
    for _ in range(20):
        body.act(Action("drive", {"forward_mps": 0.02}))
    pose = body.frame()["pose"]
    assert (pose["x_m"], pose["y_m"], pose["yaw_rad"]) == pytest.approx(
        (0, 0.02, math.pi / 2), abs=1e-12
    )


def test_simultaneous_translation_and_rotation_follow_a_circular_arc():
    body = body_in_open_arena()
    speed, omega = 0.02, 0.2
    for _ in range(20):
        body.act(Action("drive", {"forward_mps": speed, "yaw_rps": omega}))
    pose = body.frame()["pose"]
    # A unit-second constant-twist trajectory has radius speed / omega.
    radius = speed / omega
    assert (pose["x_m"], pose["y_m"], pose["yaw_rad"]) == pytest.approx(
        (radius * math.sin(omega), radius * (1 - math.cos(omega)), omega), abs=1e-12
    )


def test_stop_and_empty_drive_do_not_reuse_a_previous_velocity():
    body = body_in_open_arena()
    body.act(Action("drive", {"forward_mps": 0.025, "yaw_rps": 0.2}))
    before = body.snapshot()
    assert any(foot["swing_start"] is not None for foot in before["feet"])
    for action in [Action("stop")] * 5 + [Action("drive")] * 5:
        body.act(action)
        after = body.snapshot()
        for key in ("pose", "feet", "phase", "distance_m"):
            assert after[key] == before[key]
        assert after["command"] == {"forward_mps": 0, "lateral_mps": 0, "yaw_rps": 0}


def test_stand_replants_all_feet_and_reset_reproduces_the_initial_state():
    body = body_in_open_arena()
    initial = json_state(body)
    for _ in range(9):
        body.act(Action("drive", {"forward_mps": 0.02}))
    pose = body.frame()["pose"]
    body.act(Action("stand"))
    assert body.frame()["pose"] == pose
    assert all(leg["stance"] for leg in body.frame()["legs"])
    assert all(foot["swing_start"] is None for foot in body.snapshot()["feet"])
    assert body.snapshot()["phase"] == 0
    assert_leg_geometry(body, body.frame())
    body.reset(37)
    assert json_state(body) == initial


def test_stance_feet_remain_fixed_in_world_during_translation_and_turns():
    body = body_in_open_arena()
    previous = body.frame()
    stance_checks = 0
    saw_swing = set()
    for _ in range(96):
        body.act(Action("drive", {"forward_mps": 0.018, "lateral_mps": 0.008, "yaw_rps": 0.2}))
        frame = body.frame()
        assert not frame["workspace_limited"]
        assert sum(not leg["stance"] for leg in frame["legs"]) <= 1
        assert_leg_geometry(body, frame)
        for old, new in zip(previous["legs"], frame["legs"]):
            if not new["stance"]:
                saw_swing.add(new["name"])
            if old["stance"] and new["stance"]:
                assert new["points"][-1] == pytest.approx(old["points"][-1], abs=1e-12)
                stance_checks += 1
        previous = frame
    assert saw_swing == set(LEG_ORDER)
    assert stance_checks > 200


@pytest.mark.parametrize("omega", [-0.3, 0.3])
def test_multiple_full_turns_keep_geometry_reachable_and_yaw_wrapped(omega):
    body = body_in_open_arena()
    count = 720
    for _ in range(count):
        body.act(Action("drive", {"yaw_rps": omega}))
        frame = body.frame()
        assert not frame["workspace_limited"]
        assert not frame["collision"]
        assert -math.pi <= frame["pose"]["yaw_rad"] <= math.pi
        assert_leg_geometry(body, frame)
    pose = frame["pose"]
    assert (pose["x_m"], pose["y_m"]) == (0, 0)
    assert pose["yaw_rad"] == pytest.approx(math.remainder(count * body.config.dt_s * omega, 2 * math.pi), abs=1e-11)
    assert frame["distance_travelled_m"] == 0


def test_mid_swing_command_reversals_do_not_invalidate_the_body():
    body = body_in_open_arena()
    commands = [
        {"forward_mps": 0.025}, {"lateral_mps": 0.025}, {"yaw_rps": -0.25},
        {"forward_mps": -0.025}, {"lateral_mps": -0.025}, {"yaw_rps": 0.25},
    ]
    for tick in range(240):
        body.act(Action("drive", commands[(tick // 7) % len(commands)]))
        frame = body.frame()
        assert not frame["workspace_limited"]
        assert not frame["collision"]
        assert_leg_geometry(body, frame)


def test_thin_wall_blocks_the_swept_envelope_and_retreat_is_possible():
    world = World((-1, -1, 1, 1), (Obstacle("thin_wall", 0, -1, 0.00001, 1),))
    body = PiCrawlerSimBody(world, SimConfig(initial_x_m=-0.18005, camera_enabled=False))
    body.act(Action("drive", {"forward_mps": 0.03}))
    hit_x = body.frame()["pose"]["x_m"]
    assert body.frame()["collision"]
    assert -0.18005 < hit_x <= -0.18
    for _ in range(8):
        body.act(Action("drive", {"forward_mps": 0.03}))
        frame = body.frame()
        assert frame["collision"]
        assert frame["pose"]["x_m"] <= -0.18
        assert world.is_free(frame["pose"]["x_m"], frame["pose"]["y_m"], body.config.collision_radius_m)
        assert_leg_geometry(body, frame)
    body.act(Action("drive", {"forward_mps": -0.02}))
    assert not body.frame()["collision"]
    assert body.frame()["pose"]["x_m"] < hit_x


def test_arena_boundary_cannot_be_crossed():
    world = World((-0.3, -0.3, 0.3, 0.3))
    body = PiCrawlerSimBody(world, SimConfig(initial_x_m=0.11995, camera_enabled=False))
    for _ in range(5):
        body.act(Action("drive", {"forward_mps": 0.03}))
        pose = body.frame()["pose"]
        assert body.frame()["collision"]
        assert pose["x_m"] <= 0.12
        assert world.is_free(pose["x_m"], pose["y_m"], body.config.collision_radius_m)


def test_observation_has_only_sensor_data_and_all_reads_are_alias_safe():
    body = PiCrawlerSimBody(config=SimConfig(camera=CameraConfig(width=8, height=6)))
    before = json_state(body)
    observation = body.observe()
    assert set(observation.sensors) == {"ultrasonic", "camera", "telemetry"}
    assert set(observation.sensors["ultrasonic"]) == {"distance_m", "status"}
    assert set(observation.sensors["camera"]) == {"encoding", "width", "height", "rgb"}
    assert observation.internal == {"hunger": 0.0, "damage": 0.0}
    assert observation.sensors["telemetry"]["source"] == "simulated"
    assert "truth_distance_m" in body.frame()["sensor"]
    observation.sensors["ultrasonic"]["distance_m"] = -999
    observation.sensors["camera"]["rgb"][0][0][0] = 999
    observation.internal["energy"] = 1
    observation.sensors["telemetry"]["state_of_charge"] = 99
    frame = body.frame()
    frame["pose"]["x_m"] = 99
    frame["legs"][0]["points"][0][0] = 99
    frame["sensor"]["origin"][0] = 99
    frame["command"]["forward_mps"] = 99
    frame["camera_rgb"][0][0][0] = 999
    frame["telemetry"]["history"]["undervoltage"] = True
    frame["needs"]["hunger"] = 99
    snapshot = body.snapshot()
    snapshot["config"]["geometry"]["coxa_m"] = 99
    snapshot["readings"]["camera"]["rgb"][0][0][0] = 999
    snapshot["command"]["yaw_rps"] = 99
    actions = body.available_actions()
    actions.clear()
    assert json_state(body) == before
    assert body.available_actions() == ["drive", "stop", "stand"]


def test_observe_frame_snapshot_do_not_advance_rng_or_state():
    config = SimConfig(camera=CameraConfig(width=8, height=6), range_sensor=RangeConfig(noise_half_width_m=0.005, dropout_probability=0.3))
    body = PiCrawlerSimBody(config=config, seed=51)
    body.act(Action("drive", {"forward_mps": 0.02}))
    before = json_state(body)
    assert before["rng"]["draws"] > 0
    for _ in range(12):
        body.observe()
        body.frame()
        body.frame(include_camera=False)
        body.snapshot()
    assert json_state(body) == before


def test_seeded_noise_and_dropout_are_reproducible_and_seed_sensitive():
    config = SimConfig(camera_enabled=False, range_sensor=RangeConfig(noise_half_width_m=0.005, dropout_probability=0.3))

    def sequence(seed):
        body = PiCrawlerSimBody(config=config, seed=seed)
        readings = [body.observe().sensors["ultrasonic"]]
        for _ in range(70):
            body.act(Action("stop"))
            readings.append(body.observe().sensors["ultrasonic"])
        return readings, json_state(body)

    first, state = sequence(51)
    duplicate, duplicate_state = sequence(51)
    other, _ = sequence(52)
    assert first == duplicate
    assert state == duplicate_state
    assert first != other
    assert {reading["status"] for reading in first} == {"ok", "dropout"}
    valid = [reading["distance_m"] for reading in first if reading["status"] == "ok"]
    assert len(set(valid)) > 10
    assert all(abs(value - 1.555) <= 0.005 for value in valid)


@pytest.mark.parametrize(
    "action",
    [
        None, "drive", Action("fly"), Action("stop", {"forward_mps": 0.01}),
        Action("stand", {"height": 0.1}), Action("drive", []),
        Action("drive", {"speed": 0.01}), Action("drive", {"forward_mps": float("nan")}),
        Action("drive", {"lateral_mps": float("inf")}), Action("drive", {"yaw_rps": True}),
        Action("drive", {"forward_mps": 0.031}), Action("drive", {"forward_mps": 0.03, "lateral_mps": 0.03}),
        Action("drive", {"yaw_rps": -0.31}),
    ],
)
def test_invalid_actions_leave_all_state_and_rng_unchanged(action):
    body = PiCrawlerSimBody(config=SimConfig(camera_enabled=False, range_sensor=RangeConfig(noise_half_width_m=0.01, dropout_probability=0.3)), seed=4)
    body.act(Action("drive", {"forward_mps": 0.02}))
    before = json_state(body)
    with pytest.raises(ValueError):
        body.act(action)
    assert json_state(body) == before


def test_failed_sensor_draw_rolls_back_motion_and_partially_consumed_rng():
    body = PiCrawlerSimBody(config=SimConfig(camera_enabled=False, range_sensor=RangeConfig(noise_half_width_m=0.01, dropout_probability=0.3)))
    # Reset consumes two draws. The next action consumes dropout, then exhausts
    # the noise stream; both the draw offset and the provisional motion roll back.
    body.reset(0, random_source=ReplaySource([0.9, 0.5, 0.9]))
    before = json_state(body)
    assert before["rng"]["draws"] == 2
    with pytest.raises(IndexError, match="exhausted"):
        body.act(Action("drive", {"forward_mps": 0.02}))
    assert json_state(body) == before


def test_failed_reset_preserves_previous_state_rng_and_ability_to_continue():
    body = PiCrawlerSimBody(config=SimConfig(camera_enabled=False, range_sensor=RangeConfig(noise_half_width_m=0.01)), seed=4)
    for _ in range(5):
        body.act(Action("drive", {"forward_mps": 0.02}))
    before = json_state(body)
    expected = PiCrawlerSimBody.restore(before)
    with pytest.raises(IndexError, match="exhausted"):
        body.reset(7, random_source=ReplaySource([]))
    assert json_state(body) == before
    next_action = Action("drive", {"lateral_mps": 0.01})
    body.act(next_action)
    expected.act(next_action)
    assert json_state(body) == json_state(expected)


def continuation_actions():
    return (
        [Action("drive", {"forward_mps": 0.02, "yaw_rps": 0.12})] * 7
        + [Action("stop")] * 2
        + [Action("drive", {"lateral_mps": -0.02})] * 9
        + [Action("drive", {"yaw_rps": -0.2})] * 11
        + [Action("stand")]
        + [Action("drive", {"forward_mps": -0.02})] * 12
    )


def advanced_source_body(source):
    for _ in range(23):
        source.random()
    config = SimConfig(initial_x_m=-0.3, camera=CameraConfig(width=8, height=6), range_sensor=RangeConfig(noise_half_width_m=0.005, dropout_probability=0.3))
    body = PiCrawlerSimBody(config=config, seed=11)
    # The source seed/state deliberately differs from the body's metadata seed.
    body.reset(11, random_source=source)
    for _ in range(5):
        body.act(Action("drive", {"forward_mps": 0.02, "yaw_rps": 0.12}))
    state = json_state(body)
    assert state["rng"]["draws"] > 23
    assert any(foot["swing_start"] is not None for foot in state["feet"])
    assert any(foot["position"][2] > 0 for foot in state["feet"])
    return body


@pytest.mark.parametrize("source_type", [NumpySource, DelphiRandom])
def test_json_restore_preserves_mid_swing_and_advanced_rng_each_tick(source_type):
    original = advanced_source_body(source_type(938))
    saved = json_state(original)
    restored = PiCrawlerSimBody.restore(saved)
    assert json_state(restored) == saved
    saved["readings"]["ultrasonic"]["status"] = "caller mutation"
    for action in continuation_actions():
        original.act(action)
        restored.act(action)
        assert json_state(restored) == json_state(original)
        assert restored.observe() == original.observe()
        assert restored.frame() == original.frame()


def test_fresh_process_resume_matches_full_state_after_every_tick(tmp_path):
    original = advanced_source_body(NumpySource(938))
    saved = json_state(original)
    actions = continuation_actions()
    expected = [saved]
    for action in actions:
        original.act(action)
        expected.append(json_state(original))

    script = """
import json
import sys
from psi_gw.body import Action
from psi_gw.body.picrawler import PiCrawlerSimBody
payload = json.load(sys.stdin)
body = PiCrawlerSimBody.restore(payload['snapshot'])
states = [body.snapshot()]
for item in payload['actions']:
    body.act(Action(item['name'], item['params']))
    states.append(body.snapshot())
json.dump(states, sys.stdout, allow_nan=False)
"""
    payload = {"snapshot": saved, "actions": [{"name": action.name, "params": action.params} for action in actions]}
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(str(Path(path).resolve()) for path in sys.path if path)
    process = subprocess.run(
        [sys.executable, "-c", script], input=json.dumps(payload, allow_nan=False),
        text=True, capture_output=True, check=True, env=env, cwd=tmp_path, timeout=30,
    )
    assert json.loads(process.stdout) == expected


@pytest.mark.parametrize("change", ["version", "geometry", "pose_shape", "pose_nonfinite", "pose_collision", "negative_tick", "invalid_phase", "missing_foot"])
def test_restore_rejects_invalid_version_geometry_pose_and_progress(change):
    body = body_in_open_arena()
    saved = json_state(body)
    invalid = copy.deepcopy(saved)
    if change == "version":
        invalid["version"] = 999
    elif change == "geometry":
        invalid["config"]["geometry"]["upper_m"] = -0.048
    elif change == "pose_shape":
        invalid["pose"] = [0, 0]
    elif change == "pose_nonfinite":
        invalid["pose"][0] = float("nan")
    elif change == "pose_collision":
        invalid["pose"][0] = 100
    elif change == "negative_tick":
        invalid["tick"] = -1
    elif change == "invalid_phase":
        invalid["phase"] = 1
    elif change == "missing_foot":
        invalid["feet"].pop()
    with pytest.raises(ValueError):
        PiCrawlerSimBody.restore(invalid)
    assert json_state(body) == saved
