"""Fixture-only checks for read-only Raspberry Pi telemetry collectors."""

import json
import subprocess

import pytest

from psi_gw.body.picrawler.telemetry import (
    battery_voltage_from_adc,
    collect_telemetry,
    parse_pmic_adc,
    parse_throttled,
)


MODEL = "/proc/device-tree/model"
THERMAL = "/sys/class/thermal/thermal_zone0/temp"
NOW = "2026-11-10T12:00:00+00:00"


class FixtureHost:
    def __init__(self, model="Raspberry Pi 4 Model B Rev 1.5", temperature="42500\n"):
        self.files = {MODEL: model + "\x00", THERMAL: temperature}
        self.commands = {
            ("vcgencmd", "measure_temp"): "temp=43.5'C\n",
            ("vcgencmd", "measure_temp", "pmic"): "temp=39.2'C\n",
            ("vcgencmd", "measure_volts", "core"): "volt=0.8500V\n",
            ("vcgencmd", "measure_clock", "arm"): "frequency(48)=1500000000\n",
            ("vcgencmd", "get_throttled"): "throttled=0x50000\n",
            ("vcgencmd", "pmic_read_adc"): (
                " VDD_CORE_A current(7)=0.51794000A\n"
                " VDD_CORE_V volt(15)=0.75186740V\n"
                " EXT5V_V volt(24)=5.06788000V\n"
                " BATT_V volt(25)=3.10000000V\n"
            ),
        }
        self.reads = []
        self.calls = []

    def read(self, path):
        self.reads.append(path)
        value = self.files.get(path, FileNotFoundError(path))
        if isinstance(value, Exception):
            raise value
        return value

    def run(self, command):
        command = tuple(command)
        self.calls.append(command)
        value = self.commands.get(command, FileNotFoundError("vcgencmd"))
        if isinstance(value, Exception):
            raise value
        return value

    def collect(self, **kwargs):
        return collect_telemetry(read_text=self.read, run_command=self.run, observed_at=NOW, **kwargs)


def test_current_and_historical_throttling_are_separate():
    flags = parse_throttled("throttled=0x50000\n")
    assert flags["raw"] == 0x50000
    assert not any(flags["current"].values())
    assert flags["history"] == {
        "undervoltage": True, "frequency_capped": False,
        "throttled": True, "soft_temperature_limit": False,
    }
    assert flags["unknown_bits"] == 0
    current = parse_throttled("throttled=0x8000a")
    assert current["current"] == {
        "undervoltage": False, "frequency_capped": True,
        "throttled": False, "soft_temperature_limit": True,
    }
    assert current["history"]["soft_temperature_limit"]


def test_unknown_throttle_bits_are_not_reinterpreted():
    result = parse_throttled("throttled=0x20")
    assert result["unknown_bits"] == 0x20
    assert not any(result["current"].values())


@pytest.mark.parametrize("value", ["0x50000", "throttled=none", "throttled=0x100000000", "throttled=-1"])
def test_malformed_throttle_masks_rejected(value):
    with pytest.raises(ValueError):
        parse_throttled(value)


def test_pi4_reads_temperature_and_core_voltage_but_never_invents_battery():
    host = FixtureHost()
    data = host.collect()
    assert data["type"] == "psi_gw.picrawler.telemetry"
    assert data["version"] == 1
    assert data["observed_at"] == NOW
    assert data["device"]["raspberry_pi"]
    measurements = data["measurements"]
    assert measurements["cpu_temperature_c"]["value"] == 42.5
    assert measurements["cpu_temperature_c"]["source"] == THERMAL
    assert measurements["pmic_temperature_c"]["value"] == 39.2
    assert measurements["core_voltage_v"]["value"] == 0.85
    assert measurements["arm_frequency_hz"]["value"] == 1_500_000_000
    assert measurements["supply_voltage_v"]["status"] == "unsupported"
    assert measurements["battery_voltage_v"]["value"] is None
    assert measurements["battery_voltage_v"]["status"] == "unavailable"
    assert ("vcgencmd", "pmic_read_adc") not in host.calls
    assert ("vcgencmd", "measure_temp") not in host.calls
    assert data["throttle"]["history"]["undervoltage"]
    assert not data["throttle"]["current"]["undervoltage"]
    json.dumps(data, allow_nan=False)


@pytest.mark.parametrize("temperature", [FileNotFoundError("thermal"), PermissionError("thermal"), "NaN", "bad data"])
def test_cpu_temperature_uses_firmware_fallback_when_sysfs_fails(temperature):
    host = FixtureHost(temperature=temperature)
    result = host.collect()["measurements"]["cpu_temperature_c"]
    assert result["status"] == "measured"
    assert result["value"] == 43.5
    assert result["source"] == "vcgencmd measure_temp"


def test_pi5_supply_and_rails_remain_distinct_from_battery_and_servo_current():
    host = FixtureHost("Raspberry Pi 5 Model B Rev 1.0")
    data = host.collect(battery_reader=lambda: 7.81)
    measurements = data["measurements"]
    assert data["device"]["pi5_family"]
    assert measurements["supply_voltage_v"]["value"] == 5.06788
    assert measurements["core_voltage_v"]["value"] == 0.85
    assert measurements["battery_voltage_v"]["value"] == 7.81
    assert data["pmic_rails"]["BATT_V"]["value"] == 3.1
    assert data["pmic_rails"]["VDD_CORE_A"]["value"] == 0.51794
    assert measurements["battery_current_a"]["value"] is None
    assert measurements["servo_current_a"]["value"] is None
    assert measurements["servo_position_feedback_rad"]["value"] is None
    assert measurements["imu_acceleration_mps2"]["status"] == "unsupported"
    assert measurements["imu_angular_velocity_rps"]["status"] == "unsupported"


def test_pi5_adc_missing_named_5v_channel_does_not_return_a_different_voltage():
    host = FixtureHost("Raspberry Pi 5 Model B Rev 1.0")
    host.commands[("vcgencmd", "pmic_read_adc")] = "BATT_V volt(25)=3.1V\n"
    data = host.collect()
    assert data["measurements"]["supply_voltage_v"]["value"] is None
    assert data["measurements"]["supply_voltage_v"]["status"] == "unavailable"
    assert data["measurements"]["battery_voltage_v"]["value"] is None


def test_pi3_does_not_probe_pmic_temperature_or_adc():
    host = FixtureHost("Raspberry Pi 3 Model B Plus Rev 1.3")
    data = host.collect()
    assert data["measurements"]["pmic_temperature_c"]["status"] == "unsupported"
    assert ("vcgencmd", "measure_temp", "pmic") not in host.calls
    assert ("vcgencmd", "pmic_read_adc") not in host.calls


@pytest.mark.parametrize("model", ["Generic Virtual Machine", None])
def test_non_pi_hosts_never_use_the_host_cpu_temperature_or_execute_commands(model):
    host = FixtureHost()
    if model is None:
        host.files.pop(MODEL)
    else:
        host.files[MODEL] = model
    data = host.collect()
    assert not data["device"]["raspberry_pi"]
    assert not host.calls
    assert THERMAL not in host.reads
    assert all(record["value"] is None for record in data["measurements"].values())
    assert all(value is None for value in data["throttle"]["current"].values())


@pytest.mark.parametrize("failure,expected", [
    (FileNotFoundError("vcgencmd"), "unavailable"),
    (PermissionError("vcio"), "unavailable"),
    (subprocess.TimeoutExpired("vcgencmd", 2), "unavailable"),
    ("error=1 error_msg=\"Command not registered\"", "unsupported"),
    ("volt=NaNV", "error"),
])
def test_missing_or_bad_commands_produce_explicit_absent_readings(failure, expected):
    host = FixtureHost()
    host.commands[("vcgencmd", "measure_volts", "core")] = failure
    result = host.collect()["measurements"]["core_voltage_v"]
    assert result["value"] is None
    assert result["status"] == expected
    assert result["source"] == "vcgencmd measure_volts core"
    assert result["detail"]


def test_failed_throttle_read_has_unknown_flags_not_false_healthy_flags():
    host = FixtureHost()
    host.commands[("vcgencmd", "get_throttled")] = FileNotFoundError("vcgencmd")
    throttle = host.collect()["throttle"]
    assert throttle["raw"]["value"] is None
    assert all(value is None for value in throttle["current"].values())
    assert all(value is None for value in throttle["history"].values())


@pytest.mark.parametrize("value", [True, -1, float("nan"), "7.4"])
def test_invalid_battery_values_are_not_relabelled_as_valid_measurements(value):
    host = FixtureHost()
    reading = host.collect(battery_reader=lambda: value)["measurements"]["battery_voltage_v"]
    assert reading["value"] is None
    assert reading["status"] == "error"


def test_optional_battery_reader_failure_is_explicit():
    def missing_reader():
        raise NotImplementedError("No A4 channel on this board")

    reading = FixtureHost().collect(battery_reader=missing_reader)["measurements"]["battery_voltage_v"]
    assert reading["value"] is None
    assert reading["status"] == "unsupported"


def test_adc_conversion_endpoints_and_custom_calibration():
    assert battery_voltage_from_adc(0) == 0
    assert battery_voltage_from_adc(4095) == pytest.approx(9.9)
    assert battery_voltage_from_adc(3100) == pytest.approx(3100 / 4095 * 9.9)
    assert battery_voltage_from_adc(4095, reference_v=3.28, divider_ratio=2.98) == pytest.approx(3.28 * 2.98)


@pytest.mark.parametrize("value", [-1, 4096, 1.5, True])
def test_adc_conversion_rejects_invalid_samples(value):
    with pytest.raises(ValueError):
        battery_voltage_from_adc(value)


@pytest.mark.parametrize("text", ["", "EXT5V_V volt(24)=5A", "VDD_CORE_A current(7)=-1A", "noise", "EXT5V_V volt(24)=5V\nEXT5V_V volt(24)=5V"])
def test_malformed_pmic_results_are_rejected(text):
    with pytest.raises(ValueError):
        parse_pmic_adc(text)


def test_default_command_runner_has_fixed_commands_timeout_and_no_shell(monkeypatch):
    from psi_gw.body.picrawler import telemetry

    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0, "volt=0.85V", "")

    monkeypatch.setattr(telemetry.subprocess, "run", fake_run)
    assert telemetry._run_command(("vcgencmd", "measure_volts", "core")) == "volt=0.85V"
    assert calls[0][1]["shell"] is False
    assert calls[0][1]["timeout"] == 2.0
    with pytest.raises(ValueError):
        telemetry._run_command(("vcgencmd", "set_logging", "1"))
    assert len(calls) == 1
