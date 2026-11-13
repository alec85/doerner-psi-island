"""Isolated tests for the deterministic V4 board accessories."""
import json
import pytest
from psi_gw.body.picrawler.peripherals import PeripheralSim, PeripheralConfig

def test_audio_speech_and_tone_finish_on_logical_ticks():
    p = PeripheralSim(PeripheralConfig(dt_s=.05))
    p.command("tone", hz=440, duration_s=.11)
    assert p.observe()["speaker"]["playing"]
    assert p.additional_power_w() == .4
    p.advance(); p.advance()
    assert p.observe()["speaker"]["playing"]
    p.advance()
    assert not p.observe()["speaker"]["playing"]
    p.command("speak", text="Ich brauche Energie", duration_s=.05)
    assert p.observe()["speaker"]["event"]["mode"] == "speak"
    assert p.events[-1]["kind"] == "audio_start"

def test_led_buttons_battery_indicators_and_unknowns():
    p=PeripheralSim()
    p.command("led", on=True)
    p.inject_button("user", True)
    assert p.observe()["battery_indicator_leds"] is None
    assert p.observe(7.61)["battery_indicator_leds"] == 2
    assert p.observe(7.6)["battery_indicator_leds"] == 1
    assert p.observe(7.14)["battery_indicator_leds"] == 0
    assert p.observe(7.61)["microphone"] is None
    assert p.observe(7.61)["extra_connected_sensors"] is None
    assert p.observe(7.61)["user_button_down"] is True
    assert p.additional_power_w() == .04
    assert not p.observe(8.2,powered=False)["user_led"]

def test_snapshot_continues_active_audio_exactly():
    a=PeripheralSim()
    a.command("sound",id="alert_low_battery",duration_s=.25)
    a.advance()
    b=PeripheralSim.restore(json.loads(json.dumps(a.snapshot())))
    for _ in range(9):
        a.advance(); b.advance()
        assert a.snapshot()==b.snapshot()

@pytest.mark.parametrize("name,params",[
    ("tone",{"hz":0,"duration_s":1}),("tone",{"hz":440,"duration_s":float("nan")}),
    ("speak",{"text":"","duration_s":1}),("sound",{"id":"../a","duration_s":1}),
    ("led",{"on":1}),("stop_audio",{"unused":1}),("motor",{})])
def test_invalid_commands_are_atomic(name,params):
    p=PeripheralSim()
    original=p.snapshot()
    with pytest.raises(ValueError): p.command(name,**params)
    assert p.snapshot()==original

def test_power_loss_stops_sound_without_resetting_buttons():
    p=PeripheralSim()
    p.inject_button("reset",True)
    p.command("tone",hz=400,duration_s=1)
    p.advance(powered=False)
    assert not p.observe(powered=False)["speaker"]["playing"]
