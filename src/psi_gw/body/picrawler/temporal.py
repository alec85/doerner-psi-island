"""Bounded sensor history; no body, pose, world or object identity is available."""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass
import math
from statistics import median
from typing import Any

from .perception import PerceptionConfig, camera_features, range_features


@dataclass(frozen=True)
class TemporalConfig:
    maximum_age_s: float = .30
    hold_s: float = .15
    maximum_speed_mps: float = .03
    uncertainty_m: float = .005
    track_lifetime_s: float = .30
    association_gate: float = .20
    maximum_tracks: int = 32

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if type(value) not in (float, int) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"invalid temporal parameter {name}")
        if self.hold_s > self.maximum_age_s or type(self.maximum_tracks) is not int:
            raise ValueError("invalid history bounds")


class SensorMemory:
    """Freshness-aware distance estimate and deterministic colour-region tracks."""

    def __init__(self, config: TemporalConfig = TemporalConfig()) -> None:
        self.config = config
        self.range_history: list[dict[str, float]] = []
        self.range_capture = -1.0
        self.camera_capture = -1.0
        self.tracks: list[dict[str, Any]] = []
        self.next_track = 1
        self.last_now = -1.0
        self.last_rotation_s = -1.0

    def update(self, sensors: dict[str, Any], *, now_s: float,
               rotated: bool = False) -> dict[str, Any]:
        if type(now_s) not in (int, float) or not math.isfinite(now_s) or now_s < self.last_now:
            raise ValueError("sensor history requires nondecreasing finite time")
        if type(rotated) is not bool:
            raise ValueError("rotated must be boolean")
        self.last_now = now_s
        config = PerceptionConfig(maximum_age_s=self.config.maximum_age_s)
        raw = sensors.get("ultrasonic")
        feature = range_features(raw, now_s=now_s, config=config)
        if rotated:
            self.range_history = []
            self.last_rotation_s = now_s
        self.range_history = [r for r in self.range_history if now_s - r["captured_at_s"] <= self.config.maximum_age_s]
        captured = raw.get("captured_at_s") if isinstance(raw, dict) else None
        aligned = feature.usable and captured >= self.last_rotation_s
        fresh_sample = aligned and captured > self.range_capture
        if fresh_sample:
            self.range_capture = captured
            self.range_history.append({"distance_m": feature.distance_m, "captured_at_s": captured})
            self.range_history = self.range_history[-3:]
        usable_current = aligned and captured == self.range_capture
        distance, source, age = None, "unknown", feature.age_s
        if usable_current:
            # A sudden near measurement always wins over the smoother history.
            middle = median(r["distance_m"] for r in self.range_history) if self.range_history else feature.distance_m
            distance = max(0.0, min(feature.distance_m, middle) - self.config.maximum_speed_mps * feature.age_s - self.config.uncertainty_m)
            source = "measured"
        elif self.range_history and not rotated:
            last = self.range_history[-1]
            age = now_s - last["captured_at_s"]
            if age <= self.config.hold_s + 1e-9:
                distance = max(0.0, last["distance_m"] - self.config.maximum_speed_mps * age - self.config.uncertainty_m)
                source = "held_estimate"

        image = sensors.get("camera")
        timestamp = image.get("captured_at_s") if isinstance(image, dict) else None
        valid_time = type(timestamp) in (int, float) and math.isfinite(timestamp) and 0 <= timestamp <= now_s
        new_image = valid_time and timestamp > self.camera_capture and now_s - timestamp <= self.config.maximum_age_s
        camera = camera_features(image, now_s=now_s, config=config) if new_image else None
        camera_status = camera.status if camera is not None else (
            "missing" if timestamp is None else "future_or_invalid" if not valid_time else
            "stale" if now_s - timestamp > self.config.maximum_age_s else "repeated_or_old")
        self.tracks = [t for t in self.tracks if now_s - t["last_seen_s"] <= self.config.track_lifetime_s + 1e-9]
        if camera is not None and camera.usable:
            self.camera_capture = timestamp
            blobs = [asdict(b) for b in camera.blobs]
            candidates = []
            for ti, track in enumerate(self.tracks):
                for bi, blob in enumerate(blobs):
                    separation = math.hypot(track["centroid_x"] - blob["centroid_x"], track["centroid_y"] - blob["centroid_y"])
                    if track["color"] == blob["color"] and separation <= self.config.association_gate:
                        candidates.append((separation, track["id"], ti, bi))
            assigned_tracks, assigned_blobs = set(), set()
            for _, _, ti, bi in sorted(candidates):
                if ti in assigned_tracks or bi in assigned_blobs:
                    continue
                self.tracks[ti].update(blobs[bi], last_seen_s=timestamp)
                self.tracks[ti]["hits"] += 1
                assigned_tracks.add(ti)
                assigned_blobs.add(bi)
            for bi, blob in enumerate(blobs):
                if bi not in assigned_blobs and len(self.tracks) < self.config.maximum_tracks:
                    self.tracks.append({**blob, "id": self.next_track, "hits": 1, "last_seen_s": timestamp})
                    self.next_track += 1
        output_tracks = []
        for track in self.tracks:
            age_s = max(0.0, now_s - track["last_seen_s"])
            output_tracks.append({**copy.deepcopy(track), "age_s": age_s,
                "confidence": max(0.0, 1 - age_s / self.config.track_lifetime_s),
                "observed_now": camera is not None and camera.usable and track["last_seen_s"] == timestamp})
        return {"distance_m": distance, "range_source": source, "range_age_s": age,
                "raw_range_status": feature.status, "tracks": output_tracks,
                "camera_status": camera_status}

    def snapshot(self) -> dict[str, Any]:
        return {"type": "psi_gw.picrawler.sensor_memory", "version": 1, "config": asdict(self.config),
            "range_history": copy.deepcopy(self.range_history), "range_capture": self.range_capture,
            "camera_capture": self.camera_capture, "tracks": copy.deepcopy(self.tracks),
            "next_track": self.next_track, "last_now": self.last_now, "last_rotation_s": self.last_rotation_s}

    @classmethod
    def restore(cls, payload: dict[str, Any]) -> SensorMemory:
        if payload.get("type") != "psi_gw.picrawler.sensor_memory" or payload.get("version") != 1:
            raise ValueError("unsupported sensor memory")
        obj = cls(TemporalConfig(**payload["config"]))
        for field in ("range_history", "range_capture", "camera_capture", "tracks", "next_track", "last_now", "last_rotation_s"):
            setattr(obj, field, copy.deepcopy(payload[field]))
        if len(obj.range_history) > 3 or len(obj.tracks) > obj.config.maximum_tracks:
            raise ValueError("history exceeds its bounds")
        return obj
