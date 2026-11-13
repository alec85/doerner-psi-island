"""Small, deterministic perceptual baselines using only recorded sensor inputs.

These functions receive RGB pixels, range samples and timestamps. They cannot
inspect the simulator's world, object names, poses, collision state or ray-hit
identity. A colour blob is a connected image region, not an identified object.
The module changes neither a body nor PSI's cognitive state and draws no random
numbers. Thresholds are explicit modelling choices, not calibrated hardware
properties. See ``docs/picrawler/PERCEPTION.md``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from colorsys import rgb_to_hsv
from dataclasses import asdict, dataclass
import math
from numbers import Integral, Real
from statistics import median
from typing import Any


def _real(value: Any) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value)


@dataclass(frozen=True)
class ColorBand:
    """A circular HSV hue interval; hue is in turns, not degrees."""

    name: str
    hue: float
    half_width: float

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("colour bands require a nonempty name")
        if not _real(self.hue) or not 0 <= self.hue < 1:
            raise ValueError("colour hue must lie in [0, 1)")
        if not _real(self.half_width) or not 0 < self.half_width < 0.5:
            raise ValueError("colour half-width must lie in (0, 0.5)")


@dataclass(frozen=True)
class PerceptionConfig:
    """Explicit baseline thresholds; all times are seconds and lengths metres."""

    minimum_range_m: float = 0.02
    maximum_range_m: float = 4.0
    near_m: float = 0.10
    far_m: float = 0.50
    maximum_age_s: float = 0.30
    minimum_blob_pixels: int = 4
    minimum_saturation: float = 0.35
    minimum_value: float = 0.25
    maximum_image_pixels: int = 262_144
    maximum_blobs: int = 64
    colors: tuple[ColorBand, ...] = (
        ColorBand("red", 0.0, 0.06),
        ColorBand("yellow", 1 / 6, 0.06),
        ColorBand("green", 1 / 3, 0.08),
        ColorBand("blue", 2 / 3, 0.09),
    )

    def __post_init__(self) -> None:
        limits = (self.minimum_range_m, self.maximum_range_m, self.near_m,
                  self.far_m, self.maximum_age_s, self.minimum_saturation,
                  self.minimum_value)
        if not all(_real(v) for v in limits):
            raise ValueError("perception thresholds must be finite numbers")
        if not 0 <= self.minimum_range_m <= self.near_m < self.far_m <= self.maximum_range_m:
            raise ValueError("expected minimum_range <= near < far <= maximum_range")
        if self.maximum_age_s < 0:
            raise ValueError("maximum_age_s must be nonnegative")
        if not 0 <= self.minimum_saturation <= 1 or not 0 <= self.minimum_value <= 1:
            raise ValueError("HSV thresholds must lie in [0, 1]")
        for name in ("minimum_blob_pixels", "maximum_image_pixels", "maximum_blobs"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if not isinstance(self.colors, tuple) or not all(isinstance(c, ColorBand) for c in self.colors):
            raise ValueError("colors must be a tuple of ColorBand values")
        if len({c.name for c in self.colors}) != len(self.colors):
            raise ValueError("colour names must be unique")


@dataclass(frozen=True)
class RangeFeatures:
    """``proximity`` is available only for a usable, fresh range measurement."""

    valid: bool
    usable: bool
    freshness: str
    age_s: float | None
    distance_m: float | None
    proximity: float | None
    status: str
    samples_used: int = 0


@dataclass(frozen=True)
class ColorBlob:
    """A four-connected region; positions use image-relative pixel centres.

    x increases to the right and y downwards. Bounding-box maxima are exclusive
    image edges, so a full-frame box is ``(0, 0, 1, 1)``.
    """

    color: str
    pixel_count: int
    area_fraction: float
    centroid_x: float
    centroid_y: float
    bounds: tuple[float, float, float, float]


@dataclass(frozen=True)
class CameraFeatures:
    valid: bool
    usable: bool
    freshness: str
    age_s: float | None
    width: int
    height: int
    blobs: tuple[ColorBlob, ...]
    status: str


@dataclass(frozen=True)
class PerceptionResult:
    range: RangeFeatures
    camera: CameraFeatures

    def to_dict(self) -> dict[str, Any]:
        """Return new JSON-compatible data, with explicit stale indicators."""
        result = asdict(self)
        for feature in result.values():
            feature["stale"] = (
                feature["freshness"] == "stale"
                if feature["freshness"] in ("fresh", "stale") else None
            )
        result["source"] = "sensor_baseline"
        return result


def _time_context(now_s: float, sample_time_s: float | None) -> None:
    if not _real(now_s) or now_s < 0:
        raise ValueError("now_s must be a finite nonnegative time")
    if sample_time_s is not None and (not _real(sample_time_s) or sample_time_s < 0):
        raise ValueError("sample_time_s must be a finite nonnegative time or None")


def _freshness(sample: Mapping[str, Any], now_s: float,
               fallback: float | None, config: PerceptionConfig) -> tuple[str, float | None]:
    captured = sample.get("captured_at_s", fallback)
    if captured is None:
        return "unknown", None
    if not _real(captured) or captured < 0:
        return "invalid", None
    if captured > now_s + 1e-9:
        return "future", None
    age = max(0.0, float(now_s - captured))
    return ("stale" if age > config.maximum_age_s + 1e-9 else "fresh"), age


def _proximity(distance: float, config: PerceptionConfig) -> float:
    return min(1.0, max(0.0, (config.far_m - distance) / (config.far_m - config.near_m)))


def range_features(sample: Mapping[str, Any] | None, *, now_s: float,
                   sample_time_s: float | None = None,
                   config: PerceptionConfig = PerceptionConfig()) -> RangeFeatures:
    """Interpret one range sample without treating a missing echo as free space.

    ``valid`` describes the measured value and sensor status. ``usable`` also
    requires a known, recent timestamp. Delayed values remain visible for
    diagnostics, but their proximity is ``None``.
    """
    _time_context(now_s, sample_time_s)
    if not isinstance(sample, Mapping):
        return RangeFeatures(False, False, "unknown", None, None, None, "missing")
    freshness, age = _freshness(sample, now_s, sample_time_s, config)
    raw = sample.get("distance_m")
    status = sample.get("status", "ok")
    distance = float(raw) if _real(raw) else None
    valid = (
        status == "ok" and distance is not None
        and config.minimum_range_m <= distance <= config.maximum_range_m
    )
    usable = valid and freshness == "fresh"
    if status != "ok":
        reason = str(status) if isinstance(status, str) else "invalid_status"
    elif not valid:
        reason = "missing_echo" if raw is None else "invalid_distance"
    else:
        reason = "ok" if usable else f"timestamp_{freshness}"
    return RangeFeatures(
        bool(valid), bool(usable), freshness, age, distance,
        _proximity(distance, config) if usable else None, reason, int(usable),
    )


def median_range_window(samples: Sequence[Mapping[str, Any]], *, now_s: float,
                        minimum_samples: int = 3,
                        config: PerceptionConfig = PerceptionConfig()) -> RangeFeatures:
    """Median of explicitly supplied fresh samples, with no hidden history.

    Each sample needs ``captured_at_s``. Invalid, stale and future samples are
    excluded. The returned age is the oldest contributing sample's age. This
    is a small noise/outlier baseline, not evidence that the nearest obstacle
    is static or that a missing echo is safe.
    """
    _time_context(now_s, None)
    if type(minimum_samples) is not int or minimum_samples < 1:
        raise ValueError("minimum_samples must be a positive integer")
    candidates = [range_features(s, now_s=now_s, config=config) for s in samples]
    accepted = [s for s in candidates if s.usable]
    if len(accepted) < minimum_samples:
        return RangeFeatures(False, False, "unknown", None, None, None,
                             "insufficient_fresh_samples", len(accepted))
    distance = float(median(s.distance_m for s in accepted))
    return RangeFeatures(True, True, "fresh", max(s.age_s for s in accepted),
                         distance, _proximity(distance, config), "ok", len(accepted))


def _pixels(value: Any, config: PerceptionConfig) -> tuple[list[list[tuple[int, int, int]]], int, int]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise ValueError("RGB image must contain rows")
    height = len(value)
    if not isinstance(value[0], Sequence) or isinstance(value[0], (str, bytes)) or not value[0]:
        raise ValueError("RGB rows must contain pixels")
    width = len(value[0])
    if width * height > config.maximum_image_pixels:
        raise ValueError("RGB image exceeds configured size")
    image = []
    for row in value:
        if not isinstance(row, Sequence) or isinstance(row, (str, bytes)) or len(row) != width:
            raise ValueError("RGB image must be rectangular")
        parsed = []
        for pixel in row:
            if not isinstance(pixel, Sequence) or isinstance(pixel, (str, bytes)) or len(pixel) != 3:
                raise ValueError("RGB pixels must have three channels")
            if any(not isinstance(v, Integral) or isinstance(v, bool) or not 0 <= v <= 255 for v in pixel):
                raise ValueError("RGB channels must be uint8 integers")
            parsed.append(tuple(int(v) for v in pixel))
        image.append(parsed)
    return image, width, height


def _blobs(image: list[list[tuple[int, int, int]]], width: int, height: int,
           config: PerceptionConfig) -> tuple[ColorBlob, ...]:
    labels = [[-1] * width for _ in range(height)]
    for y, row in enumerate(image):
        for x, pixel in enumerate(row):
            hue, saturation, value = rgb_to_hsv(*(v / 255.0 for v in pixel))
            if saturation < config.minimum_saturation or value < config.minimum_value:
                continue
            for index, color in enumerate(config.colors):
                delta = abs(hue - color.hue)
                if min(delta, 1.0 - delta) <= color.half_width:
                    labels[y][x] = index
                    break  # Ordered bands resolve overlaps deterministically.
    regions = []
    for y in range(height):
        for x in range(width):
            color = labels[y][x]
            if color < 0:
                continue
            labels[y][x] = -1
            pending = [(x, y)]
            count, sx, sy = 0, 0.0, 0.0
            xmin = xmax = x
            ymin = ymax = y
            while pending:
                px, py = pending.pop()
                count += 1
                sx += px + 0.5
                sy += py + 0.5
                xmin, xmax, ymin, ymax = min(xmin, px), max(xmax, px), min(ymin, py), max(ymax, py)
                for nx, ny in ((px - 1, py), (px + 1, py), (px, py - 1), (px, py + 1)):
                    if 0 <= nx < width and 0 <= ny < height and labels[ny][nx] == color:
                        labels[ny][nx] = -1
                        pending.append((nx, ny))
            if count >= config.minimum_blob_pixels:
                regions.append(ColorBlob(
                    config.colors[color].name, count, count / (width * height),
                    sx / (count * width), sy / (count * height),
                    (xmin / width, ymin / height, (xmax + 1) / width, (ymax + 1) / height),
                ))
    regions.sort(key=lambda b: (-b.pixel_count, b.color, b.centroid_y, b.centroid_x))
    return tuple(regions[:config.maximum_blobs])


def camera_features(sample: Mapping[str, Any] | None, *, now_s: float,
                    sample_time_s: float | None = None,
                    config: PerceptionConfig = PerceptionConfig()) -> CameraFeatures:
    """Extract colour components from fresh RGB8 pixels, without object labels."""
    _time_context(now_s, sample_time_s)
    if not isinstance(sample, Mapping):
        return CameraFeatures(False, False, "unknown", None, 0, 0, (), "missing")
    freshness, age = _freshness(sample, now_s, sample_time_s, config)
    if sample.get("encoding", "rgb8") != "rgb8":
        return CameraFeatures(False, False, freshness, age, 0, 0, (), "unsupported_encoding")
    try:
        image, width, height = _pixels(sample.get("rgb"), config)
    except (TypeError, ValueError):
        return CameraFeatures(False, False, freshness, age, 0, 0, (), "invalid_image")
    if sample.get("width", width) != width or sample.get("height", height) != height:
        return CameraFeatures(False, False, freshness, age, width, height, (), "dimension_mismatch")
    usable = freshness == "fresh"
    return CameraFeatures(True, usable, freshness, age, width, height,
                          _blobs(image, width, height, config) if usable else (),
                          "ok" if usable else f"timestamp_{freshness}")


def perceive(sensors: Mapping[str, Any], *, now_s: float,
             sample_time_s: float | None = None,
             config: PerceptionConfig = PerceptionConfig()) -> PerceptionResult:
    """Interpret one sensor bundle using explicit capture and observation times.

    ``sample_time_s`` is an optional, explicit fallback for legacy synchronous
    observations without per-sensor ``captured_at_s``. It never overrides a
    supplied sensor timestamp. The caller owns sample history and the clock.
    """
    if not isinstance(sensors, Mapping):
        raise ValueError("sensors must be a mapping")
    return PerceptionResult(
        range_features(sensors.get("ultrasonic"), now_s=now_s,
                       sample_time_s=sample_time_s, config=config),
        camera_features(sensors.get("camera"), now_s=now_s,
                        sample_time_s=sample_time_s, config=config),
    )
