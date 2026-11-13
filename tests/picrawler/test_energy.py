"""Physical balances, protective signals and deterministic body integration."""

from __future__ import annotations

import copy
import json
from dataclasses import replace

import pytest

from psi_gw.body import Action
from psi_gw.body.picrawler import EnergyConfig, PiCrawlerSimBody, SimConfig, World
from psi_gw.body.picrawler.energy import (
    EnergyEnvironment, EnergyState, advance_energy, energy_readings, initial_energy,
    need_signals, open_circuit_voltage,
)


def step(state, config=None, environment=None, **kwargs):
    config = config or EnergyConfig()
    environment = environment or EnergyEnvironment(config.cpu_load, config.ambient_temperature_c)
    return advance_energy(state, config, environment, dt_s=kwargs.pop("dt_s", 0.05),
                          motion_fraction=kwargs.pop("motion_fraction", 0.0), **kwargs)


@pytest.mark.parametrize("values", [
    {"enabled": 1}, {"battery_capacity_ah": 0}, {"battery_initial_soc": -0.01},
    {"battery_initial_soc": 1.01}, {"battery_internal_resistance_ohm": -0.1},
    {"battery_voltage_full_v": 6.0}, {"battery_cutoff_voltage_v": 9},
    {"regulator_efficiency": 0}, {"regulator_efficiency": 1.1},
    {"cpu_load": 1.1}, {"servo_motion_power_w": -1}, {"idle_cpu_power_w": float("nan")},
    {"thermal_resistance_c_per_w": 0}, {"thermal_capacity_j_per_c": -1},
    {"initial_cpu_temperature_c": -300}, {"ambient_temperature_c": float("inf")},
    {"temperature_warning_c": 90}, {"temperature_throttle_c": 90},
    {"hunger_soc_critical": 0.4}, {"hunger_soc_warning": 2},
])
def test_invalid_configs_are_rejected(values):
    with pytest.raises(ValueError):
        EnergyConfig(**values)


def test_open_circuit_voltage_is_bounded_monotonic_and_has_configured_endpoints():
    config = EnergyConfig()
    values = [open_circuit_voltage(i / 100, config) for i in range(101)]
    assert values == sorted(values)
    assert values[0] == config.battery_voltage_empty_v
    assert values[-1] == config.battery_voltage_full_v


@pytest.mark.parametrize("resistance", [0.0, 0.15, 0.4])
def test_current_voltage_and_power_obey_circuit_and_charge_balances(resistance):
    config = EnergyConfig(battery_internal_resistance_ohm=resistance)
    before = initial_energy(config)
    after, values = step(before, config, motion_fraction=0.6, dt_s=0.05)
    assert values["powered"]
    current = values["current_a"]
    assert values["battery_voltage_v"] * current == pytest.approx(values["power_w"], abs=1e-12)
    assert values["open_circuit_voltage_v"] - values["battery_voltage_v"] == pytest.approx(current * resistance)
    assert after.charge_used_ah == pytest.approx(current * 0.05 / 3600)
    assert before.state_of_charge - after.state_of_charge == pytest.approx(after.charge_used_ah / config.battery_capacity_ah)
    assert after.energy_consumed_j == pytest.approx(values["power_w"] * 0.05)
    assert after.battery_loss_j == pytest.approx(current * current * resistance * 0.05)
    assert after.energy_consumed_j + after.battery_loss_j == pytest.approx(values["open_circuit_voltage_v"] * current * 0.05)


def test_motion_stall_camera_and_cpu_load_increase_consumption_without_free_energy():
    config, state, environment = EnergyConfig(), initial_energy(EnergyConfig()), EnergyEnvironment()
    idle = energy_readings(state, config, environment, camera_enabled=False)
    camera = energy_readings(state, config, environment, camera_enabled=True)
    moving = energy_readings(state, config, environment, motion_fraction=1)
    stalled = energy_readings(state, config, environment, motion_fraction=1, stalled=True)
    busy = energy_readings(state, config, EnergyEnvironment(cpu_load=1), motion_fraction=1, stalled=True)
    assert 0 < idle["power_w"] < camera["power_w"] < moving["power_w"] < stalled["power_w"] < busy["power_w"]
    assert moving["battery_voltage_v"] < idle["battery_voltage_v"]
    assert camera["power_w"] - idle["power_w"] == pytest.approx(config.camera_power_w / config.regulator_efficiency)
    assert moving["core_voltage_v"] is None
    assert moving["source"] == "simulated"


def test_empty_battery_bounds_consumption_and_cools_without_motor_power():
    config = EnergyConfig(battery_capacity_ah=0.01, battery_initial_soc=0.0001,
                          battery_internal_resistance_ohm=0)
    initial = initial_energy(config)
    empty, values = step(initial, config, dt_s=10)
    assert empty.state_of_charge == 0
    assert empty.charge_used_ah == pytest.approx(config.battery_capacity_ah * config.battery_initial_soc)
    assert empty.shutdown_reason == "battery_empty"
    assert not values["powered"] and values["battery_depleted"]
    assert values["current_a"] * 10 / 3600 == pytest.approx(empty.charge_used_ah)
    later, quiet = step(empty, config, dt_s=50, motion_fraction=1)
    assert later.energy_consumed_j == empty.energy_consumed_j
    assert later.charge_used_ah == empty.charge_used_ah
    assert quiet["current_a"] == quiet["power_w"] == quiet["supply_voltage_v"] == 0
    assert config.ambient_temperature_c < later.cpu_temperature_c < empty.cpu_temperature_c


def test_passive_cooling_is_stable_and_independent_of_time_partition():
    config = EnergyConfig()
    initial = EnergyState(0, 100, shutdown_reason="battery_empty")
    whole, _ = step(initial, config, dt_s=60)
    split = initial
    for _ in range(600):
        split, _ = step(split, config, dt_s=0.1)
    assert split.cpu_temperature_c == pytest.approx(whole.cpu_temperature_c, abs=1e-10)
    assert config.ambient_temperature_c < whole.cpu_temperature_c < initial.cpu_temperature_c
    cold = EnergyState(0, 0, shutdown_reason="battery_empty")
    warmed, _ = step(cold, config, dt_s=60)
    assert 0 < warmed.cpu_temperature_c < config.ambient_temperature_c


def test_thermal_equilibrium_and_more_cpu_work_produce_expected_heat():
    config = EnergyConfig(idle_cpu_power_w=1, active_cpu_power_w=1)
    equilibrium = config.ambient_temperature_c + config.thermal_resistance_c_per_w
    initial = EnergyState(0.8, equilibrium)
    same, _ = step(initial, config, EnergyEnvironment(cpu_load=0), dt_s=20)
    hot, _ = step(initial, config, EnergyEnvironment(cpu_load=1), dt_s=20)
    assert same.cpu_temperature_c == pytest.approx(equilibrium)
    assert hot.cpu_temperature_c > same.cpu_temperature_c


def test_throttle_reduces_dynamic_cpu_power_and_history_is_not_current_status():
    config = EnergyConfig(idle_cpu_power_w=0, active_cpu_power_w=3)
    environment = EnergyEnvironment(cpu_load=1, ambient_temperature_c=0)
    cool_values = energy_readings(EnergyState(0.8, 79), config, environment)
    hot = EnergyState(0.8, 81)
    hot_values = energy_readings(hot, config, environment)
    assert hot_values["thermal_throttled"] and not cool_values["thermal_throttled"]
    assert hot_values["cpu_power_w"] < cool_values["cpu_power_w"]
    after, values = step(hot, config, EnergyEnvironment(cpu_load=0, ambient_temperature_c=0), dt_s=30)
    assert after.cpu_temperature_c < config.temperature_throttle_c
    assert not values["thermal_throttled"]
    assert values["history"]["thermal_throttled"]


def test_voltage_sag_can_recover_while_historical_flag_remains_set():
    config = EnergyConfig(battery_initial_soc=0.5, battery_internal_resistance_ohm=0.5, regulator_min_input_v=7.5)
    moved, loaded = step(initial_energy(config), config, motion_fraction=1)
    assert loaded["powered"] and loaded["undervoltage"]
    rested, resting = step(moved, config, motion_fraction=0)
    assert resting["battery_voltage_v"] > loaded["battery_voltage_v"]
    assert not resting["undervoltage"]
    assert rested.undervoltage_occurred and resting["history"]["undervoltage"]
    assert need_signals(resting, config)["damage"] == 0


@pytest.mark.parametrize("resistance,reason", [(0.8, "battery_cutoff"), (10, "power_limit")])
def test_unachievable_loads_latch_power_off_and_never_emit_nonfinite_values(resistance, reason):
    config = EnergyConfig(battery_internal_resistance_ohm=resistance)
    shutdown, values = step(initial_energy(config), config, motion_fraction=1)
    assert shutdown.shutdown_reason == reason
    assert not values["powered"] and values["undervoltage"]
    assert values["current_a"] == values["power_w"] == 0
    assert shutdown.charge_used_ah == 0
    _, later = step(shutdown, config, motion_fraction=0)
    assert not later["powered"]
    json.dumps(later, allow_nan=False)


@pytest.mark.parametrize("soc,expected", [(1, 0), (0.3, 0), (0.175, 0.5), (0.05, 1), (0, 1)])
def test_hunger_is_a_configurable_bounded_charge_deficit(soc, expected):
    assert need_signals({"state_of_charge": soc}, EnergyConfig())["hunger"] == pytest.approx(expected)


@pytest.mark.parametrize("temperature,expected", [(20, 0), (65, 0), (75, 0.5), (85, 1), (100, 1)])
def test_damage_is_protective_risk_not_a_claim_of_irreversible_injury(temperature, expected):
    assert need_signals({"cpu_temperature_c": temperature}, EnergyConfig())["damage"] == expected


def test_missing_measurements_stay_unknown_and_history_alone_does_not_raise_need():
    config = EnergyConfig()
    assert need_signals({"battery_voltage_v": 7.4}, config) == {"hunger": None, "damage": None}
    assert need_signals({"undervoltage": False, "history": {"undervoltage": True}}, config)["damage"] == 0
    assert need_signals({"cpu_temperature_c": 40, "undervoltage": True}, config)["damage"] == 1


def test_body_stops_motors_when_empty_and_observation_is_an_external_model_readout():
    body = PiCrawlerSimBody(config=SimConfig(camera_enabled=False, energy=EnergyConfig(battery_initial_soc=0)))
    initial = body.frame()
    for _ in range(5):
        body.act(Action("drive", {"forward_mps": 0.03}))
    assert body.frame()["pose"] == initial["pose"]
    assert body.frame()["legs"] == initial["legs"]
    assert body.frame()["telemetry"]["powered"] is False
    assert body.observe().internal == {"hunger": 1, "damage": 1}
    assert body.tick == 5


def test_experiment_inputs_take_effect_on_next_tick_without_mutating_cached_observation():
    body = PiCrawlerSimBody(config=SimConfig(camera_enabled=False))
    previous = body.observe()
    body.set_environment(cpu_load=1, ambient_temperature_c=35)
    assert body.tick == 0 and body.observe() == previous
    saved = body.snapshot()
    with pytest.raises(ValueError):
        body.set_environment(cpu_load=2)
    assert body.snapshot() == saved
    body.act(Action("stop"))
    telemetry = body.observe().sensors["telemetry"]
    assert telemetry["cpu_load"] == 1 and telemetry["ambient_temperature_c"] == 35
    assert telemetry["state_of_charge"] < previous.sensors["telemetry"]["state_of_charge"]


def test_energy_environment_flags_and_need_outputs_resume_exactly_after_json_roundtrip():
    config = SimConfig(camera_enabled=False, energy=EnergyConfig(battery_initial_soc=0.15, initial_cpu_temperature_c=81))
    body = PiCrawlerSimBody(config=config, seed=43)
    body.set_environment(cpu_load=1, ambient_temperature_c=30)
    for _ in range(20):
        body.act(Action("drive", {"forward_mps": 0.02}))
    resumed = PiCrawlerSimBody.restore(json.loads(json.dumps(body.snapshot())))
    for action in [Action("stop"), Action("stand"), Action("drive", {"yaw_rps": 0.3})] * 20:
        body.act(action)
        resumed.act(action)
        assert body.snapshot() == resumed.snapshot()
        assert body.observe().internal == resumed.observe().internal


def test_version_one_migration_disables_energy_and_preserves_kinematic_continuation():
    config = SimConfig(camera_enabled=False, energy=EnergyConfig(enabled=False))
    original = PiCrawlerSimBody(config=config, seed=11)
    original.act(Action("drive", {"forward_mps": 0.02}))
    legacy = copy.deepcopy(original.snapshot())
    legacy["version"] = 1
    del legacy["config"]["energy"], legacy["energy"], legacy["environment"]
    restored = PiCrawlerSimBody.restore(json.loads(json.dumps(legacy)))
    assert not restored.config.energy.enabled
    for _ in range(20):
        original.act(Action("drive", {"forward_mps": 0.02}))
        restored.act(Action("drive", {"forward_mps": 0.02}))
        assert original.snapshot() == restored.snapshot()
        assert restored.observe().internal == {}
        assert "telemetry" not in restored.observe().sensors


def test_thermal_throttling_does_not_invent_mechanical_slowdown():
    base = SimConfig(initial_x_m=0, camera_enabled=False, energy=EnergyConfig(initial_cpu_temperature_c=82))
    hot = PiCrawlerSimBody(World((-2, -2, 2, 2)), base)
    cool = PiCrawlerSimBody(World((-2, -2, 2, 2)), replace(base, energy=EnergyConfig()))
    for _ in range(20):
        hot.act(Action("drive", {"forward_mps": 0.03}))
        cool.act(Action("drive", {"forward_mps": 0.03}))
    assert hot.frame()["telemetry"]["thermal_throttled"]
    assert hot.frame()["pose"] == cool.frame()["pose"]
