"""Flat test arenas, continuous swept-disk collision and ideal ray intersections.

Distances are metres. The disk is an intentionally conservative locomotion
envelope, not a measured PiCrawler collision mesh. Obstacles cannot be climbed.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any


def finite(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


@dataclass(frozen=True, slots=True)
class Obstacle:
    name: str
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    height_m: float = 0.20
    color: tuple[int, int, int] = (211, 145, 72)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("obstacle name must be a nonempty string")
        for key in ("x_min", "y_min", "x_max", "y_max", "height_m"):
            finite(getattr(self, key), key)
        if self.x_min >= self.x_max or self.y_min >= self.y_max or self.height_m <= 0:
            raise ValueError("obstacle dimensions must be positive")
        if len(self.color) != 3 or any(type(v) is not int or not 0 <= v <= 255 for v in self.color):
            raise ValueError("color must contain three RGB8 integers")
        object.__setattr__(self, "color", tuple(self.color))


@dataclass(frozen=True, slots=True)
class RayHit:
    distance_m: float
    name: str


@dataclass(frozen=True, slots=True)
class World:
    bounds: tuple[float, float, float, float] = (-1.0, -0.8, 1.0, 0.8)
    obstacles: tuple[Obstacle, ...] = ()

    def __post_init__(self) -> None:
        if len(self.bounds) != 4:
            raise ValueError("bounds must be (xmin, ymin, xmax, ymax)")
        for v in self.bounds:
            finite(v, "world bound")
        xmin, ymin, xmax, ymax = self.bounds
        if xmin >= xmax or ymin >= ymax:
            raise ValueError("world dimensions must be positive")
        if any(not isinstance(o, Obstacle) for o in self.obstacles):
            raise ValueError("obstacles must be Obstacle instances")
        if len({o.name for o in self.obstacles}) != len(self.obstacles):
            raise ValueError("obstacle names must be unique")
        for o in self.obstacles:
            if not (xmin <= o.x_min < o.x_max <= xmax and ymin <= o.y_min < o.y_max <= ymax):
                raise ValueError(f"obstacle {o.name!r} is outside the arena")
        object.__setattr__(self, "bounds", tuple(float(v) for v in self.bounds))
        object.__setattr__(self, "obstacles", tuple(self.obstacles))

    def snapshot(self) -> dict[str, Any]:
        return {"bounds": list(self.bounds), "obstacles": [asdict(o) for o in self.obstacles]}

    @classmethod
    def restore(cls, data: dict[str, Any]) -> World:
        return cls(tuple(data["bounds"]), tuple(Obstacle(**o) for o in data["obstacles"]))

    def is_free(self, x: float, y: float, radius: float) -> bool:
        for v in (x, y, radius):
            finite(v, "position/radius")
        if radius <= 0:
            raise ValueError("radius must be positive")
        xmin, ymin, xmax, ymax = self.bounds
        if not (xmin + radius <= x <= xmax - radius and ymin + radius <= y <= ymax - radius):
            return False
        for o in self.obstacles:
            dx = max(o.x_min - x, 0.0, x - o.x_max)
            dy = max(o.y_min - y, 0.0, y - o.y_max)
            if dx * dx + dy * dy < radius * radius:
                return False
        return True

    def sweep(self, x: float, y: float, dx: float, dy: float, radius: float) -> float:
        """Return the safe fraction of a segment; a thin wall cannot be skipped.

        Rectangle offsets consist of four straight edges and four circular
        corners, so diagonals retain the disk's actual rounded envelope.
        """
        for v in (x, y, dx, dy, radius):
            finite(v, "sweep parameter")
        if not self.is_free(x, y, radius):
            raise ValueError("sweep starts in collision")
        length = math.hypot(dx, dy)
        if length == 0:
            return 1.0
        candidates = [1.0]
        xmin, ymin, xmax, ymax = self.bounds
        if dx > 0:
            candidates.append((xmax - radius - x) / dx)
        elif dx < 0:
            candidates.append((xmin + radius - x) / dx)
        if dy > 0:
            candidates.append((ymax - radius - y) / dy)
        elif dy < 0:
            candidates.append((ymin + radius - y) / dy)
        for o in self.obstacles:
            if dx:
                surface = o.x_min - radius if dx > 0 else o.x_max + radius
                t = (surface - x) / dx
                if 0 <= t <= 1 and o.y_min <= y + t * dy <= o.y_max:
                    candidates.append(t)
            if dy:
                surface = o.y_min - radius if dy > 0 else o.y_max + radius
                t = (surface - y) / dy
                if 0 <= t <= 1 and o.x_min <= x + t * dx <= o.x_max:
                    candidates.append(t)
            for cx in (o.x_min, o.x_max):
                for cy in (o.y_min, o.y_max):
                    px, py = x - cx, y - cy
                    a = dx * dx + dy * dy
                    b = px * dx + py * dy
                    c = px * px + py * py - radius * radius
                    discriminant = b * b - a * c
                    # A double root is a tangent, not entry into the disk.
                    if b < 0 and discriminant > 1e-14 * a * radius * radius:
                        t = (-b - math.sqrt(discriminant)) / a
                        if 0 <= t <= 1:
                            candidates.append(t)
        fraction = min(t for t in candidates if t >= 0)
        # Keep subsequent steps out of a floating-point overlap at contact.
        return max(0.0, fraction - 1e-9 / length) if fraction < 1.0 else 1.0

    def raycast(self, x: float, y: float, dx: float, dy: float,
                max_distance_m: float, height_m: float = 0.09) -> RayHit | None:
        """First intersection of an ideal, horizontal, infinitesimal beam."""
        for v in (x, y, dx, dy, max_distance_m, height_m):
            finite(v, "ray parameter")
        norm = math.hypot(dx, dy)
        if norm == 0 or max_distance_m <= 0 or height_m < 0:
            raise ValueError("invalid ray direction, range or height")
        dx, dy = dx / norm, dy / norm
        xmin, ymin, xmax, ymax = self.bounds
        if not (xmin <= x <= xmax and ymin <= y <= ymax):
            raise ValueError("ray origin is outside the arena")
        hits: list[RayHit] = []
        if dx > 0:
            hits.append(RayHit((xmax - x) / dx, "wall"))
        elif dx < 0:
            hits.append(RayHit((xmin - x) / dx, "wall"))
        if dy > 0:
            hits.append(RayHit((ymax - y) / dy, "wall"))
        elif dy < 0:
            hits.append(RayHit((ymin - y) / dy, "wall"))
        for o in self.obstacles:
            if o.height_m < height_m:
                continue
            near, far = 0.0, max_distance_m
            for p, d, lo, hi in ((x, dx, o.x_min, o.x_max), (y, dy, o.y_min, o.y_max)):
                if abs(d) < 1e-15:
                    if p < lo or p > hi:
                        far = -1.0
                        break
                else:
                    a, b = (lo - p) / d, (hi - p) / d
                    near, far = max(near, min(a, b)), min(far, max(a, b))
            if 0 <= near <= far:
                hits.append(RayHit(near, o.name))
        result = min(hits, key=lambda hit: hit.distance_m) if hits else None
        return result if result is not None and result.distance_m <= max_distance_m else None


def demo_world() -> World:
    """Small arena with obstacles suitable for deterministic scripted demos."""
    return World((-1.0, -0.8, 1.0, 0.8), (
        Obstacle("block", 0.28, -0.18, 0.43, 0.18, 0.22, (217, 147, 65)),
        Obstacle("pillar", -0.45, 0.36, -0.23, 0.53, 0.28, (93, 163, 183)),
    ))
