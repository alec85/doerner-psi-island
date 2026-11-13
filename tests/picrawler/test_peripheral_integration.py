"""End-to-end peripheral integration with kinematic Body and transport."""
import json
import pytest

from psi_gw.body import Action, Body
from psi_gw.body.picrawler import PiCrawlerSimBody, SimConfig, EnergyConfig
from psi_gw.body.picrawler.bridge import BridgeEndpoint, Request, Reply
from psi_gw.body.picrawler.replay import write_replay

def factory(**kwargs):
    return PiCrawlerSimBody(config=SimConfig(peripherals_enabled=True, camera_enabled=False, **kwargs), seed=13)

def test_peripherals_are_exposed_as_real_body_actions_and_observations():
    body=factory()
    assert isinstance(body, Body)
    assert {"speak","tone","sound","stop_audio","led"}.issubset(set(body.available_actions()))
    assert body.observe().sensors["peripherals"]["battery_indicator_leds"] is not None
    body.act(Action("led",{"on":True}))
    body.act(Action("speak",{"text":"Akku knapp","duration_s":.15}))
    obs=body.observe()
    assert obs.tick==2
    assert obs.sensors["peripherals"]["speaker"]["playing"]
    assert obs.sensors["peripherals"]["user_led"]
    assert body.frame()["peripheral_events"][-1]["kind"]=="audio_start"
    for _ in range(3): body.act(Action("stop"))
    assert not body.observe().sensors["peripherals"]["speaker"]["playing"]
    assert body.tick==body.peripherals.tick

def test_audio_consumes_battery_in_same_tick_and_legacy_behavior_is_opt_in():
    baseline=factory()
    sounding=factory()
    baseline.act(Action("stop"))
    sounding.act(Action("tone",{"hz":440,"duration_s":.5}))
    assert sounding.observe().sensors["telemetry"]["energy_consumed_j"] > baseline.observe().sensors["telemetry"]["energy_consumed_j"]
    assert sounding.observe().sensors["telemetry"]["state_of_charge"] < baseline.observe().sensors["telemetry"]["state_of_charge"]
    assert "peripherals" not in PiCrawlerSimBody(config=SimConfig(camera_enabled=False)).observe().sensors

def test_checkpoint_during_speech_restores_all_following_ticks():
    original=factory()
    original.act(Action("speak",{"text":"Warnung!","duration_s":.5}))
    for _ in range(3): original.act(Action("drive",{"forward_mps":.01}))
    serialized=json.loads(json.dumps(original.snapshot(),allow_nan=False))
    assert serialized["version"]==3
    restored=PiCrawlerSimBody.restore(serialized)
    assert restored.snapshot()==original.snapshot()
    for _ in range(16):
        original.act(Action("stop")); restored.act(Action("stop"))
        assert restored.snapshot()==original.snapshot()
        assert restored.frame()==original.frame()

def test_invalid_audio_does_not_mutate_body_energy_or_rng():
    body=factory()
    before=body.snapshot()
    with pytest.raises(ValueError):
        body.act(Action("tone",{"hz":999999,"duration_s":.5}))
    assert body.snapshot()==before

def test_buttons_are_queued_as_external_inputs_and_preserved_in_snapshot():
    body=factory()
    body.inject_button("user",True)
    assert not body.observe().sensors["peripherals"]["user_button_down"]
    body.act(Action("stop"))
    assert body.observe().sensors["peripherals"]["user_button_down"]
    assert PiCrawlerSimBody.restore(json.loads(json.dumps(body.snapshot()))).snapshot()==body.snapshot()

def test_unpowered_audio_is_stopped_and_led_goes_dark():
    body=factory(energy=EnergyConfig(battery_initial_soc=0))
    body.act(Action("speak",{"text":"cannot speak","duration_s":2}))
    per=body.observe().sensors["peripherals"]
    assert not per["speaker"]["playing"]
    assert not per["user_led"]
    assert per["battery_indicator_leds"]==0

def test_checkpoint_before_button_tick_preserves_queued_inputs_and_sensor_cache():
    body = factory()
    body.inject_button("user", True)
    body.inject_button("reset", True)
    body.inject_button("user", False)
    before = body.observe()
    assert not before.sensors["peripherals"]["reset_button_down"]
    assert body.frame()["peripheral_events"] == []
    restored = PiCrawlerSimBody.restore(json.loads(json.dumps(body.snapshot())))
    assert restored.snapshot() == body.snapshot()
    for item in (body, restored):
        item.act(Action("stop"))
        assert item.observe().sensors["peripherals"]["reset_button_down"]
        assert not item.observe().sensors["peripherals"]["user_button_down"]
        assert len(item.frame()["peripheral_events"]) == 3
        item.act(Action("stop"))
        assert len(item.frame()["peripheral_events"]) == 3
    assert restored.snapshot() == body.snapshot()

def test_failed_action_preserves_pending_buttons_for_the_next_valid_tick():
    body = factory()
    body.inject_button("user", True)
    before = body.snapshot()
    with pytest.raises(ValueError):
        body.act(Action("tone", {"hz": -1, "duration_s": 1}))
    assert body.snapshot() == before
    body.act(Action("stop"))
    assert body.observe().sensors["peripherals"]["user_button_down"]

def test_original_v3_checkpoint_without_pending_button_field_still_restores():
    body = factory()
    state = body.snapshot()
    state.pop("pending_buttons")
    assert PiCrawlerSimBody.restore(state).snapshot() == body.snapshot()

@pytest.mark.parametrize("action", [
    Action("tone", {"hz": 440, "duration_s": .1}),
    Action("sound", {"id": "alert", "duration_s": .1}),
    Action("speak", {"text": "Warnung", "duration_s": .1}),
])
def test_audio_and_led_power_are_counted_once_for_exactly_the_active_ticks(action):
    baseline, active = factory(), factory()
    baseline.act(Action("stop"))
    active.act(Action("led", {"on": True}))
    for command, expected_accessory in ((action, .44), (Action("stop"), .44),
                                         (Action("stop"), .04)):
        old_base = baseline.observe().sensors["telemetry"]["energy_consumed_j"]
        old_active = active.observe().sensors["telemetry"]["energy_consumed_j"]
        baseline.act(Action("stop"))
        active.act(command)
        used_base = baseline.observe().sensors["telemetry"]["energy_consumed_j"] - old_base
        used_active = active.observe().sensors["telemetry"]["energy_consumed_j"] - old_active
        expected = expected_accessory / active.config.energy.regulator_efficiency * active.config.dt_s
        assert used_active - used_base == pytest.approx(expected, abs=1e-12)

def test_speech_and_pending_button_checkpoint_continue_in_a_fresh_python_process(tmp_path):
    import subprocess
    import sys
    from psi_gw.body.picrawler.sensors import RangeConfig

    body = PiCrawlerSimBody(config=SimConfig(peripherals_enabled=True,
        range_sensor=RangeConfig(noise_half_width_m=.002, dropout_probability=.02)), seed=42)
    body.act(Action("speak", {"text": "Checkpoint", "duration_s": .4}))
    body.inject_button("reset", True)
    checkpoint = tmp_path / "checkpoint.json"
    checkpoint.write_text(json.dumps(body.snapshot()))
    expected = []
    for _ in range(12):
        body.act(Action("drive", {"forward_mps": .01}))
        expected.append({"snapshot": body.snapshot(), "frame": body.frame()})
    script = '''
import json, sys
from psi_gw.body import Action
from psi_gw.body.picrawler import PiCrawlerSimBody
body = PiCrawlerSimBody.restore(json.load(open(sys.argv[1])))
states = []
for _ in range(12):
    body.act(Action("drive", {"forward_mps": .01}))
    states.append({"snapshot": body.snapshot(), "frame": body.frame()})
print(json.dumps(states))
'''
    result = subprocess.run([sys.executable, "-c", script, str(checkpoint)],
                            cwd=tmp_path, capture_output=True, text=True, check=True, timeout=20)
    assert json.loads(result.stdout) == json.loads(json.dumps(expected))

def test_bridge_can_send_speech_and_observe_peripherals():
    body=factory()
    endpoint=BridgeEndpoint(body)
    session=endpoint.connect("controller")
    request=Request(session,"say-hi",1,endpoint.tick,endpoint.tick+3,
                    Action("speak",{"text":"Hallo","duration_s":.4}))
    assert endpoint.receive(request.to_json()) is None
    response=Reply.from_json(endpoint.step()[0])
    assert response.status=="completed"
    assert response.observation.sensors["peripherals"]["speaker"]["playing"]
    assert endpoint.receive(request.to_json())==response.to_json()

def test_replay_embeds_peripheral_timeline_without_external_resources(tmp_path):
    body=factory()
    frames=[body.frame()]
    body.act(Action("speak",{"text":"Ich brauche Energie","duration_s":1}))
    frames.append(body.frame())
    target=tmp_path/"replay.html"
    write_replay(target,frames,{"world":body.world.snapshot(),"dt_s":body.config.dt_s})
    text=target.read_text()
    assert "peripheral-panel" in text
    assert "renderPeripherals(f)" in text
    assert "Ich brauche Energie" in text
    assert "fetch(" not in text
