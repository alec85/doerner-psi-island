"""Read-only Raspberry Pi telemetry, with explicit missing-value provenance.

No Robot HAT, GPIO, I2C, servo or camera library is imported. Optional battery
access is a caller-supplied reader; merely importing Robot HAT can initialise
hardware on some library versions. The default collector reads device-tree and
thermal files and executes a small fixed list of read-only ``vcgencmd`` commands.

Sources:
https://www.raspberrypi.com/documentation/computers/os.html#get_throttled
https://www.raspberrypi.com/documentation/computers/os.html#measure_volts-block
https://www.raspberrypi.com/documentation/computers/os.html#pmic_read_adc-channel
https://www.raspberrypi.com/documentation/computers/config_txt.html
https://docs.sunfounder.com/projects/robot-hat-v4/en/stable/hardware_introduction.html#adc
https://github.com/sunfounder/robot-hat/blob/2.5.x/robot_hat/device.py

Core voltage, the Pi's 5 V supply, PMIC rails and the Robot HAT battery are
distinct quantities. PMIC rail currents exclude consumers powered directly
from 5 V and are never presented as total battery or servo current.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime, timezone
import math
from pathlib import Path
import re
import subprocess
from typing import Any


ReadText = Callable[[str], str]
RunCommand = Callable[[Sequence[str]], str]
BatteryReader = Callable[[], float]
_MODEL_PATHS = ("/proc/device-tree/model", "/sys/firmware/devicetree/base/model")
_THERMAL_PATH = "/sys/class/thermal/thermal_zone0/temp"
_FLAG_NAMES = ("undervoltage", "frequency_capped", "throttled", "soft_temperature_limit")
_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
_COMMANDS = {
    ("vcgencmd", "measure_temp"), ("vcgencmd", "measure_temp", "pmic"),
    ("vcgencmd", "get_throttled"), ("vcgencmd", "measure_volts", "core"),
    ("vcgencmd", "measure_clock", "arm"), ("vcgencmd", "pmic_read_adc"),
}


def _read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _run_command(command: Sequence[str]) -> str:
    args = tuple(command)
    if args not in _COMMANDS:
        raise ValueError("command is not a supported read-only telemetry query")
    result = subprocess.run(args, capture_output=True, text=True, check=True,
                            timeout=2.0, shell=False)
    return result.stdout


def _metric(value: Any, unit: str, status: str, source: str, detail: str = "") -> dict[str, Any]:
    return {"value": value, "unit": unit, "status": status, "source": source, "detail": detail}


def _numeric(value: Any, *, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("measurement must be a finite number")
    if nonnegative and value < 0:
        raise ValueError("measurement must be nonnegative")
    return float(value)


def _scalar(text: str, pattern: str, *, nonnegative: bool = False) -> float:
    match = re.fullmatch(pattern, text.strip())
    if match is None:
        raise ValueError("unrecognised telemetry response")
    return _numeric(float(match.group(1)), nonnegative=nonnegative)


def _attempt(reader: Callable[[], Any], parser: Callable[[Any], Any], unit: str,
             source: str, detail: str = "") -> dict[str, Any]:
    try:
        raw = reader()
        if isinstance(raw, str) and re.search(
            r"not registered|unknown command|not supported|unsupported|unrecognized command|unrecognised command",
            raw, re.IGNORECASE,
        ):
            raise NotImplementedError(raw.strip())
        value = parser(raw)
    except NotImplementedError as error:
        return _metric(None, unit, "unsupported", source, str(error)[:240])
    except (OSError, subprocess.SubprocessError) as error:
        return _metric(None, unit, "unavailable", source, str(error)[:240])
    except Exception as error:
        return _metric(None, unit, "error", source, f"{type(error).__name__}: {error}"[:240])
    return _metric(value, unit, "measured", source, detail)


def parse_throttled(text: str) -> dict[str, Any]:
    """Keep current flags separate from sticky historical flags.

    Historical flags report that a condition occurred; they are not a current
    undervoltage/temperature alarm. Unknown bits remain visible in the raw mask.
    """
    match = re.fullmatch(r"throttled=(0x[0-9a-fA-F]+)", text.strip())
    if match is None:
        raise ValueError("invalid get_throttled response")
    raw = int(match.group(1), 16)
    if raw > 0xFFFFFFFF:
        raise ValueError("throttled mask exceeds 32 bits")
    return {
        "raw": raw,
        "current": {name: bool(raw & (1 << i)) for i, name in enumerate(_FLAG_NAMES)},
        "history": {name: bool(raw & (1 << (i + 16))) for i, name in enumerate(_FLAG_NAMES)},
        "unknown_bits": raw & ~0xF000F,
    }


def parse_pmic_adc(text: str) -> dict[str, dict[str, Any]]:
    """Parse named PMIC rails without treating their sum as total power."""
    result: dict[str, dict[str, Any]] = {}
    pattern = rf"\s*([A-Za-z0-9_]+)\s+(volt|current)\((\d+)\)=({_NUMBER})([VA])\s*"
    for line in text.splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(pattern, line)
        if match is None:
            raise ValueError("invalid pmic_read_adc response")
        name, kind, channel, raw_value, unit = match.groups()
        if name in result or unit != {"volt": "V", "current": "A"}[kind]:
            raise ValueError("duplicate PMIC channel or inconsistent unit")
        value = _numeric(float(raw_value), nonnegative=True)
        result[name] = {"value": value, "unit": unit, "channel": int(channel), "kind": kind}
    if not result:
        raise ValueError("empty pmic_read_adc response")
    return result


def battery_voltage_from_adc(raw: int, *, reference_v: float = 3.3,
                             divider_ratio: float = 3.0) -> float:
    """Convert a Robot HAT A4 12-bit ADC sample; performs no hardware access.

    The documented V4 divider is 20 kOhm / 10 kOhm. The reference and divider
    should be replaced by measured calibration values when available.
    """
    if type(raw) is not int or not 0 <= raw <= 4095:
        raise ValueError("A4 ADC sample must be an integer in [0, 4095]")
    reference_v = _numeric(reference_v, nonnegative=True)
    divider_ratio = _numeric(divider_ratio, nonnegative=True)
    if reference_v == 0 or divider_ratio == 0:
        raise ValueError("ADC reference and divider must be positive")
    return raw / 4095.0 * reference_v * divider_ratio


def collect_telemetry(*, read_text: ReadText | None = None,
                      run_command: RunCommand | None = None,
                      battery_reader: BatteryReader | None = None,
                      observed_at: str | None = None) -> dict[str, Any]:
    """Collect one explicitly sourced snapshot without actuator outputs.

    ``read_text(path)`` and ``run_command(argv)`` are injectable fixtures. The
    optional battery reader returns volts from an already configured read-only
    source; the collector never imports or initialises Robot HAT itself. On a
    host not identified as Raspberry Pi no firmware commands are attempted.
    Missing values remain ``None``, never nominal or simulated replacements.
    """
    read_text = read_text or _read_text
    run_command = run_command or _run_command
    timestamp = observed_at if observed_at is not None else datetime.now(timezone.utc).isoformat()
    try:
        parsed_timestamp = datetime.fromisoformat(timestamp)
    except (TypeError, ValueError) as error:
        raise ValueError("observed_at must be an ISO timestamp with timezone") from error
    if parsed_timestamp.utcoffset() is None:
        raise ValueError("observed_at must include timezone")
    model: str | None = None
    model_source = "device-tree model"
    model_detail = "Raspberry Pi device-tree model is unavailable"
    for path in _MODEL_PATHS:
        try:
            value = read_text(path).replace("\x00", "").strip()
            if value:
                model, model_source, model_detail = value, path, ""
                break
        except (OSError, ValueError, TypeError, AttributeError) as error:
            model_detail = f"{type(error).__name__}: {error}"[:240]
    is_pi = bool(model and model.startswith("Raspberry Pi"))
    pi5 = bool(model and re.search(r"Raspberry Pi (?:5\b|500\b|Compute Module 5\b)", model))
    pi4 = bool(model and re.search(r"Raspberry Pi (?:4\b|400\b|Compute Module 4\b)", model))
    device = {"model": model, "raspberry_pi": is_pi, "pi5_family": pi5,
              "status": "identified" if model else "unavailable", "source": model_source,
              "detail": model_detail}
    missing_detail = "Raspberry Pi host not identified; firmware queries were not executed"
    measurements = {
        name: _metric(None, unit, "unsupported", source, missing_detail)
        for name, unit, source in (
            ("cpu_temperature_c", "degC", _THERMAL_PATH),
            ("pmic_temperature_c", "degC", "vcgencmd measure_temp pmic"),
            ("core_voltage_v", "V", "vcgencmd measure_volts core"),
            ("supply_voltage_v", "V", "vcgencmd pmic_read_adc EXT5V_V"),
            ("arm_frequency_hz", "Hz", "vcgencmd measure_clock arm"),
        )
    }
    throttle = {"raw": _metric(None, "bitmask", "unsupported", "vcgencmd get_throttled", missing_detail),
                "current": {name: None for name in _FLAG_NAMES},
                "history": {name: None for name in _FLAG_NAMES}, "unknown_bits": None}
    pmic_rails: dict[str, Any] = {}
    pmic_status = _metric(None, "rails", "unsupported", "vcgencmd pmic_read_adc", "PMIC ADC collection requires Raspberry Pi 5")

    def query(args: tuple[str, ...], parser: Callable[[str], Any], unit: str,
              detail: str = "") -> dict[str, Any]:
        return _attempt(lambda: run_command(args), parser, unit, " ".join(args), detail)

    if is_pi:
        cpu = _attempt(lambda: read_text(_THERMAL_PATH),
                       lambda text: _numeric(float(text.strip())) / 1000.0,
                       "degC", _THERMAL_PATH, "kernel thermal value converted from millidegrees Celsius")
        if cpu["status"] != "measured":
            cpu = query(("vcgencmd", "measure_temp"),
                        lambda text: _scalar(text, rf"temp=({_NUMBER})'C"), "degC")
        measurements["cpu_temperature_c"] = cpu
        measurements["core_voltage_v"] = query(
            ("vcgencmd", "measure_volts", "core"),
            lambda text: _scalar(text, rf"volt=({_NUMBER})V", nonnegative=True), "V",
            "Core/VC4 rail voltage; this is neither the 5 V input nor battery voltage",
        )
        measurements["arm_frequency_hz"] = query(
            ("vcgencmd", "measure_clock", "arm"),
            lambda text: _scalar(text, rf"frequency\(\d+\)=({_NUMBER})", nonnegative=True), "Hz",
        )
        flag_result = query(("vcgencmd", "get_throttled"), parse_throttled, "bitmask")
        if flag_result["status"] == "measured":
            parsed = flag_result["value"]
            throttle = {"raw": {**flag_result, "value": parsed["raw"]},
                        "current": parsed["current"], "history": parsed["history"],
                        "unknown_bits": parsed["unknown_bits"]}
        else:
            throttle["raw"] = flag_result
        if pi4 or pi5:
            measurements["pmic_temperature_c"] = query(
                ("vcgencmd", "measure_temp", "pmic"),
                lambda text: _scalar(text, rf"temp=({_NUMBER})'C"), "degC",
            )
        else:
            measurements["pmic_temperature_c"]["detail"] = "PMIC temperature is documented for Raspberry Pi 4 and 5 families"
        if pi5:
            pmic_status = query(("vcgencmd", "pmic_read_adc"), parse_pmic_adc, "rails")
            if pmic_status["status"] == "measured":
                for name, rail in pmic_status["value"].items():
                    pmic_rails[name] = _metric(
                        rail["value"], rail["unit"], "measured", f"vcgencmd pmic_read_adc: {name}",
                        "PMIC rail only; excludes loads connected directly to 5 V and is not the Robot HAT battery",
                    )
                if "EXT5V_V" in pmic_rails:
                    measurements["supply_voltage_v"] = dict(pmic_rails["EXT5V_V"])
                else:
                    measurements["supply_voltage_v"] = _metric(None, "V", "unavailable", "vcgencmd pmic_read_adc: EXT5V_V", "EXT5V_V channel was absent")
                pmic_status = {**pmic_status, "value": sorted(pmic_rails)}
            else:
                measurements["supply_voltage_v"] = {**pmic_status, "value": None, "unit": "V"}
        else:
            measurements["supply_voltage_v"]["detail"] = "EXT5V_V ADC reading is documented for Raspberry Pi 5; no battery substitution"

    if battery_reader is None:
        measurements["battery_voltage_v"] = _metric(
            None, "V", "unavailable", "Robot HAT A4 / injected battery_reader",
            "No battery reader configured; no Robot HAT import or ADC initialisation was attempted",
        )
    else:
        measurements["battery_voltage_v"] = _attempt(
            battery_reader, lambda value: _numeric(value, nonnegative=True), "V",
            "injected battery_reader (Robot HAT A4 or separately calibrated source)",
        )
    for name, unit, detail in (
        ("battery_state_of_charge", "1", "No calibrated fuel gauge; voltage alone does not determine state of charge precisely"),
        ("battery_current_a", "A", "No calibrated battery-current sensor configured"),
        ("servo_current_a", "A", "Stock PWM control does not measure servo current"),
        ("servo_position_feedback_rad", "rad", "Commanded servo angles are not measured joint feedback"),
        ("imu_acceleration_mps2", "m/s^2", "No IMU reader configured; stock PiCrawler hardware documentation does not list an IMU"),
        ("imu_angular_velocity_rps", "rad/s", "No IMU reader configured"),
    ):
        measurements[name] = _metric(None, unit, "unsupported", "not configured", detail)
    return {"type": "psi_gw.picrawler.telemetry", "version": 1, "observed_at": timestamp,
            "device": device, "measurements": measurements, "throttle": throttle,
            "pmic_rails": pmic_rails, "pmic_status": pmic_status}
