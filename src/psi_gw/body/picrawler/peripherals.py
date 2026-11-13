"""Hardware-aware, deterministic PiCrawler V4 peripheral model.

This is separate from the kinematic Body so existing snapshots, command
protocol and Claude's work remain untouched. Call advance() once for each
kinematic tick; snapshot() preserves the active audio timeline. Sound output
is an event description, NOT PCM synthesis or evidence of physical hearing.
"""
from __future__ import annotations
import copy
import math
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class PeripheralConfig:
    dt_s: float = 0.05
    sound_power_w: float = 0.4       # assumed additional load when audible
    led_power_w: float = 0.04        # assumed, not a calibrated measurement
    maximum_audio_s: float = 30.0
    def __post_init__(self):
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in
               (self.dt_s, self.sound_power_w, self.led_power_w, self.maximum_audio_s)):
            raise ValueError("parameters must be finite numbers")
        if self.dt_s <= 0 or self.maximum_audio_s <= 0 or min(self.sound_power_w, self.led_power_w) < 0:
            raise ValueError("invalid peripheral limits")

class PeripheralSim:
    """Model confirmed V4 speaker, user LED/button and power indicators.

    A controller may request tone, named sound or speech. Audio never becomes
    a microphone reading. Button presses are experiment injections only.
    Unknown plug-in sensors are NEVER fabricated. No GPIO, audio device,
    network connection or system clock is accessed.
    """
    def __init__(self, config: PeripheralConfig | None = None):
        self.config = config or PeripheralConfig()
        self.tick = 0
        self.led_on = False
        self.user_button_down = False
        self.reset_button_down = False
        self.audio = None
        self.events: list[dict[str, Any]] = []

    def _record(self, kind: str, **data: Any) -> None:
        self.events.append({"tick": self.tick, "time_s": self.tick*self.config.dt_s,
                            "kind": kind, **data})

    def command(self, name: str, **params: Any) -> None:
        """A new audio command replaces the current sound; stop_audio silences."""
        if name == "led":
            if set(params) != {"on"} or type(params["on"]) is not bool:
                raise ValueError("led requires boolean on")
            self.led_on = params["on"]
            self._record("led", on=self.led_on)
            return
        if name == "stop_audio":
            if params: raise ValueError("stop_audio takes no parameters")
            self.audio = None
            self._record("audio_stop")
            return
        if name not in {"tone", "sound", "speak"}:
            raise ValueError("unknown peripheral command")
        keys = {"tone": {"hz", "duration_s"}, "sound": {"id", "duration_s"},
                "speak": {"text", "duration_s"}}[name]
        if set(params) != keys:
            raise ValueError("invalid audio parameter names")
        duration = params["duration_s"]
        if type(duration) not in (int, float) or not math.isfinite(duration) or not 0 < duration <= self.config.maximum_audio_s:
            raise ValueError("invalid audio duration")
        if name == "tone":
            hz = params["hz"]
            if type(hz) not in (int, float) or not math.isfinite(hz) or not 40 <= hz <= 12000:
                raise ValueError("tone frequency outside model limits")
        else:
            value = params["id"] if name == "sound" else params["text"]
            if not isinstance(value, str) or not value.strip() or len(value) > (64 if name == "sound" else 500):
                raise ValueError("invalid audio identifier or text")
            if name == "sound" and not all(c.isalnum() or c in "_-." for c in value):
                raise ValueError("sound id is not a safe symbolic identifier")
        # The scheduled end is represented by a logical tick; never rely on
        # elapsed wall time. Old events remain in history for replay.
        total = max(1, math.ceil(duration / self.config.dt_s))
        self.audio = {"mode": name, "payload": {k: params[k] for k in keys},
                      "start_tick": self.tick, "end_tick": self.tick + total}
        self._record("audio_start", audio=copy.deepcopy(self.audio))

    def inject_button(self, button: str, down: bool) -> None:
        if button not in {"user", "reset"} or type(down) is not bool:
            raise ValueError("invalid button")
        field = "user_button_down" if button == "user" else "reset_button_down"
        setattr(self, field, down)
        self._record("button", button=button, down=down)
        # Reset is an input EVENT, not an automatic reboot of PSI.

    def advance(self, *, powered: bool = True) -> None:
        if type(powered) is not bool: raise ValueError("powered must be boolean")
        self.tick += 1
        if not powered and self.audio is not None:
            self.audio = None
            self._record("audio_stop", reason="power_loss")
        elif self.audio is not None and self.tick >= self.audio["end_tick"]:
            self.audio = None
            self._record("audio_stop", reason="completed")

    def observe(self, battery_voltage_v: float | None = None, *, powered: bool = True) -> dict[str, Any]:
        if type(powered) is not bool: raise ValueError("powered must be boolean")
        if battery_voltage_v is not None and (
            type(battery_voltage_v) not in (int, float) or not math.isfinite(battery_voltage_v)
            or battery_voltage_v < 0):
            raise ValueError("invalid battery voltage")
        # The manufacturer describes >7.6 V = two LEDs, 7.15..7.6 = one.
        # Unknown voltage stays unknown; LEDs are indicators, NOT SOC sensors.
        indicators = None if battery_voltage_v is None else (
            2 if battery_voltage_v > 7.6 else 1 if battery_voltage_v >= 7.15 else 0)
        return {"tick": self.tick, "source": "simulated",
                "speaker": {"playing": powered and self.audio is not None,
                            "event": copy.deepcopy(self.audio) if powered else None},
                "user_led": powered and self.led_on,
                "user_button_down": self.user_button_down,
                "reset_button_down": self.reset_button_down,
                "battery_indicator_leds": indicators if powered else 0,
                "microphone": None,
                "extra_connected_sensors": None}

    def additional_power_w(self, *, powered: bool = True) -> float:
        """Optional load for a later joint energy integrator; not added twice."""
        if type(powered) is not bool: raise ValueError("powered must be boolean")
        return 0.0 if not powered else (
            (self.config.sound_power_w if self.audio else 0) +
            (self.config.led_power_w if self.led_on else 0))

    def snapshot(self) -> dict[str, Any]:
        return {"type": "psi_gw.picrawler.peripherals", "version": 1,
                "config": {"dt_s": self.config.dt_s, "sound_power_w": self.config.sound_power_w,
                           "led_power_w": self.config.led_power_w,
                           "maximum_audio_s": self.config.maximum_audio_s},
                "tick": self.tick, "led_on": self.led_on,
                "user_button_down": self.user_button_down,
                "reset_button_down": self.reset_button_down,
                "audio": copy.deepcopy(self.audio), "events": copy.deepcopy(self.events)}

    @classmethod
    def restore(cls, payload: dict[str, Any]) -> "PeripheralSim":
        if not isinstance(payload, dict) or payload.get("type") != "psi_gw.picrawler.peripherals" or payload.get("version") != 1:
            raise ValueError("unsupported peripheral snapshot")
        item = cls(PeripheralConfig(**payload["config"]))
        if type(payload["tick"]) is not int or payload["tick"] < 0:
            raise ValueError("invalid tick")
        for key in ("led_on", "user_button_down", "reset_button_down"):
            if type(payload[key]) is not bool: raise ValueError("invalid boolean state")
            setattr(item, key, payload[key])
        item.tick = payload["tick"]
        item.audio = copy.deepcopy(payload["audio"])
        if item.audio is not None:
            if not isinstance(item.audio, dict) or item.audio.get("mode") not in {"tone", "sound", "speak"}:
                raise ValueError("invalid active sound")
            if type(item.audio.get("start_tick")) is not int or type(item.audio.get("end_tick")) is not int:
                raise ValueError("invalid audio ticks")
            if not 0 <= item.audio["start_tick"] <= item.tick < item.audio["end_tick"]:
                raise ValueError("invalid audio timing")
            probe = cls(item.config)
            probe.command(item.audio["mode"], **item.audio["payload"])
        if not isinstance(payload["events"], list):
            raise ValueError("invalid events")
        item.events = copy.deepcopy(payload["events"])
        return item
