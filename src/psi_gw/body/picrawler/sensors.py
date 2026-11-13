"""Idealised range sensing and a small pinhole RGB renderer.

The camera is synthetic geometric imagery, not a calibrated OV5647 model.
The range beam has no material response or echo cone. Noise/dropout are local
experiment settings, not measured HC-SR04 characteristics. Rendering is pure.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from psi_gw.random_source import RandomSource

from .world import World, finite


def _validate_pose(pose: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    if len(pose) != 4:
        raise ValueError("pose must contain x, y, yaw, height")
    result = tuple(finite(v, "sensor pose") for v in pose)
    if result[3] <= 0:
        raise ValueError("body height must be positive")
    return result


@dataclass(frozen=True, slots=True)
class RangeConfig:
    minimum_m: float = 0.02
    maximum_m: float = 4.0
    noise_half_width_m: float = 0.0
    dropout_probability: float = 0.0
    offset_forward_m: float = 0.045
    mount_height_m: float = 0.03

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            finite(getattr(self, name), name)
        if not (0 <= self.minimum_m < self.maximum_m):
            raise ValueError("invalid range interval")
        if self.noise_half_width_m < 0 or not 0 <= self.dropout_probability <= 1:
            raise ValueError("invalid range noise/dropout")
        if self.offset_forward_m < 0 or self.mount_height_m < 0:
            raise ValueError("sensor offsets must be nonnegative")


@dataclass(frozen=True, slots=True)
class CameraConfig:
    width: int = 48
    height: int = 32
    horizontal_fov_rad: float = math.pi / 3
    offset_forward_m: float = 0.035
    mount_height_m: float = 0.04

    def __post_init__(self) -> None:
        if type(self.width) is not int or type(self.height) is not int:
            raise ValueError("camera dimensions must be integers")
        if not (1 <= self.width <= 320 and 1 <= self.height <= 240):
            raise ValueError("camera dimensions exceed the small renderer's bounds")
        for name in ("horizontal_fov_rad", "offset_forward_m", "mount_height_m"):
            finite(getattr(self, name), name)
        if not 0 < self.horizontal_fov_rad < math.pi:
            raise ValueError("field of view must be between 0 and pi")
        if self.offset_forward_m < 0 or self.mount_height_m < 0:
            raise ValueError("camera offsets must be nonnegative")


def sample_range(world: World, pose: tuple[float, float, float, float],
                 rng: RandomSource, config: RangeConfig) -> tuple[dict[str, Any], dict[str, Any]]:
    """Take one measurement. The caller caches it for all reads of this tick."""
    x, y, yaw, height = _validate_pose(pose)
    direction = (math.cos(yaw), math.sin(yaw), 0.0)
    origin = (x + config.offset_forward_m * direction[0],
              y + config.offset_forward_m * direction[1], height + config.mount_height_m)
    hit = world.raycast(origin[0], origin[1], direction[0], direction[1],
                        config.maximum_m, origin[2])
    value: float | None = None
    status = "out_of_range"
    if hit is not None:
        if hit.distance_m < config.minimum_m:
            status = "too_close"
        elif config.dropout_probability and rng.random(site="picrawler.range.dropout") < config.dropout_probability:
            status = "dropout"
        else:
            noise = (2 * rng.random(site="picrawler.range.noise") - 1) * config.noise_half_width_m if config.noise_half_width_m else 0.0
            candidate = hit.distance_m + noise
            if candidate < config.minimum_m:
                status = "too_close"
            elif candidate > config.maximum_m:
                status = "out_of_range"
            else:
                value, status = candidate, "ok"
    reading = {"distance_m": value, "status": status}
    # Ground truth belongs to the debugger, never to the agent's observation.
    debug = {"origin": list(origin), "direction": list(direction),
             "distance_m": value, "truth_distance_m": hit.distance_m if hit else None,
             "max_range_m": config.maximum_m, "status": status}
    return reading, debug


def render_camera(world: World, pose: tuple[float, float, float, float],
                  config: CameraConfig) -> np.ndarray:
    """Ray/AABB RGB image with a ground checkerboard and opaque obstacles.

    Camera forward is body +x; image right is body -y; world up is +z.
    The image contains no semantic labels, pose or object identities.
    """
    x, y, yaw, height = _validate_pose(pose)
    co, si = math.cos(yaw), math.sin(yaw)
    origin = np.array((x + co * config.offset_forward_m,
                       y + si * config.offset_forward_m, height + config.mount_height_m))
    xmin, ymin, xmax, ymax = world.bounds
    if not (xmin <= origin[0] <= xmax and ymin <= origin[1] <= ymax):
        raise ValueError("camera origin is outside the arena")
    focal = config.width / (2 * math.tan(config.horizontal_fov_rad / 2))
    u, v = np.meshgrid(np.arange(config.width) + 0.5, np.arange(config.height) + 0.5)
    right = (u - config.width / 2) / focal
    up = -(v - config.height / 2) / focal
    directions = np.stack((co + si * right, si - co * right, up), axis=-1)
    directions /= np.linalg.norm(directions, axis=-1, keepdims=True)
    shape = (config.height, config.width)
    distances = np.full(shape, np.inf)
    rgb = np.empty((*shape, 3), dtype=np.uint8)
    rgb[:] = (189, 210, 222)

    down = directions[..., 2] < -1e-14
    floor_t = np.full(shape, np.inf)
    np.divide(-origin[2], directions[..., 2], out=floor_t, where=down)
    floor = down & (floor_t >= 0)
    safe_t = np.where(floor, floor_t, 0.0)
    fx = origin[0] + directions[..., 0] * safe_t
    fy = origin[1] + directions[..., 1] * safe_t
    check = (np.floor(fx / 0.10).astype(np.int64) + np.floor(fy / 0.10).astype(np.int64)) % 2
    rgb[floor] = np.where(check[floor, None] == 0, np.array((214, 216, 211)), np.array((194, 200, 193)))
    distances[floor] = floor_t[floor]

    xmin, ymin, xmax, ymax = world.bounds
    boxes = [(o.x_min, o.y_min, 0.0, o.x_max, o.y_max, o.height_m, o.color) for o in world.obstacles]
    wall_color = (117, 137, 151)
    boxes += [
        (xmin - 0.02, ymin - 0.02, 0, xmin, ymax + 0.02, 0.40, wall_color),
        (xmax, ymin - 0.02, 0, xmax + 0.02, ymax + 0.02, 0.40, wall_color),
        (xmin, ymin - 0.02, 0, xmax, ymin, 0.40, wall_color),
        (xmin, ymax, 0, xmax, ymax + 0.02, 0.40, wall_color),
    ]
    for bx0, by0, bz0, bx1, by1, bz1, color in boxes:
        near = np.full(shape, -np.inf)
        far = np.full(shape, np.inf)
        valid = np.ones(shape, dtype=bool)
        for axis, (lo, hi) in enumerate(((bx0, bx1), (by0, by1), (bz0, bz1))):
            d = directions[..., axis]
            parallel = np.abs(d) < 1e-14
            valid &= ~(parallel & ((origin[axis] < lo) | (origin[axis] > hi)))
            safe_d = np.where(parallel, 1.0, d)
            a, b = (lo - origin[axis]) / safe_d, (hi - origin[axis]) / safe_d
            near = np.maximum(near, np.where(parallel, -np.inf, np.minimum(a, b)))
            far = np.minimum(far, np.where(parallel, np.inf, np.maximum(a, b)))
        hit_t = np.maximum(near, 0.0)
        hit = valid & (far >= hit_t) & (hit_t < distances)
        distances[hit] = hit_t[hit]
        shade = np.clip(1 - hit_t[hit, None] * 0.07, 0.4, 1.0)
        rgb[hit] = (np.array(color) * shade).astype(np.uint8)
    return rgb
