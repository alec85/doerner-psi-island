"""Seeded benchmark worlds and evaluator-only reachability; no policy inputs."""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
import math
from typing import Any

from psi_gw.random_source import NumpySource

from .world import Obstacle, World

FAMILIES = ("open", "slalom", "dead_end", "gate")
SENSOR_PROFILES = ("nominal", "noisy", "delayed")
TASKS = ("progress", "explore", "energy_stop")


@dataclass(frozen=True)
class Course:
    seed: int
    family: str
    world: World
    initial_x_m: float
    initial_y_m: float
    initial_yaw_rad: float
    shutter_tick: int | None = None

    def snapshot(self) -> dict[str, Any]:
        return {**{k: v for k, v in asdict(self).items() if k != "world"}, "world": self.world.snapshot()}

    @classmethod
    def restore(cls, payload: dict[str, Any]) -> Course:
        return cls(**{**payload, "world": World.restore(payload["world"])})


def generate_course(seed: int, family: str) -> Course:
    if type(seed) is not int or seed < 0 or family not in FAMILIES:
        raise ValueError("invalid course seed/family")
    rng = NumpySource(seed)
    jitter = (rng.random(site="picrawler.course.layout") - .5) * .04
    colored = (220, 45, 45)
    boxes = []
    if family == "slalom":
        boxes = [Obstacle("lower", -.18 + jitter, -.62, -.05 + jitter, -.12, .24, colored),
                 Obstacle("upper", .38 + jitter, .12, .50 + jitter, .55, .24, (40, 90, 230))]
    elif family == "dead_end":
        boxes = [Obstacle("back", .10 + jitter, -.35, .20 + jitter, .35, .24, colored),
                 Obstacle("left", -.45, .35, .20 + jitter, .45, .24, (40, 90, 230)),
                 Obstacle("right", -.45, -.45, .20 + jitter, -.35, .24, (40, 90, 230))]
    elif family == "gate":
        boxes = [Obstacle("lower", -.02 + jitter, -.38, .06 + jitter, -.30, .24, colored),
                 Obstacle("upper", -.02 + jitter, .30, .06 + jitter, .38, .24, (40, 90, 230))]
    course = Course(seed, family, World((-1.0, -.9, 1.0, .9), tuple(boxes)),
        -.65 + (rng.random(site="picrawler.course.start") - .5) * .02,
        (rng.random(site="picrawler.course.start") - .5) * .02,
        (rng.random(site="picrawler.course.heading") - .5) * .08,
        300 if family == "gate" else None)
    cells = reachable_cells(course.world, (course.initial_x_m, course.initial_y_m))
    if not cells or not any(cell_center(cell)[0] >= .35 for cell in cells):
        raise ValueError("generated course has no conservative raster path to the goal")
    return course


def cell_for(x: float, y: float, step: float = .15) -> tuple[int, int]:
    return math.floor(x / step), math.floor(y / step)


def cell_center(cell: tuple[int, int], step: float = .15) -> tuple[float, float]:
    return (cell[0] + .5) * step, (cell[1] + .5) * step


def reachable_cells(world: World, start: tuple[float, float], radius: float = .18) -> set[tuple[int, int]]:
    if not world.is_free(*start, radius):
        raise ValueError("start is not free")
    xmin, ymin, xmax, ymax = world.bounds
    free = set()
    for ix in range(math.floor(xmin / .15), math.ceil(xmax / .15)):
        for iy in range(math.floor(ymin / .15), math.ceil(ymax / .15)):
            if world.is_free(*cell_center((ix, iy)), radius):
                free.add((ix, iy))
    nearest = min(free, key=lambda c: math.dist(cell_center(c), start)) if free else None
    if nearest is None:
        return set()
    nx, ny = cell_center(nearest)
    if world.sweep(*start, nx - start[0], ny - start[1], radius) < 1:
        return set()
    seen, queue = {nearest}, deque([nearest])
    while queue:
        cell = queue.popleft()
        x, y = cell_center(cell)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            other = cell[0] + dx, cell[1] + dy
            if other in free and other not in seen:
                ox, oy = cell_center(other)
                if world.sweep(x, y, ox - x, oy - y, radius) == 1:
                    seen.add(other)
                    queue.append(other)
    return seen


def shutter_world(course: Course) -> World:
    return World(course.world.bounds, course.world.obstacles +
        (Obstacle("shutter", -.02, -.12, .06, .12, .24, (230, 200, 35)),))
