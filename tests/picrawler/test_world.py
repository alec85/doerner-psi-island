"""Independent contact and ray geometry checks for the flat arena."""

import json
import math

import pytest

from psi_gw.body.picrawler.world import Obstacle, World


def test_disk_uses_rounded_corners_instead_of_an_expanded_box():
    world = World((-2, -2, 2, 2), (Obstacle("box", 0, 0, 1, 1),))
    assert world.is_free(-0.20, -0.20, 0.25)
    assert not world.is_free(-0.125, -0.125, 0.25)
    # This enters the square bounding the rounded corner but not the disk offset.
    assert world.sweep(-0.60, -0.20, 0.40, 0, 0.25) == 1.0


@pytest.mark.parametrize("dx,dy", [(4, 0), (-4, 0), (0, 4), (0, -4)])
def test_sweep_stops_at_each_arena_wall_and_leaves_a_free_endpoint(dx, dy):
    world = World((-2, -2, 2, 2))
    fraction = world.sweep(0, 0, dx, dy, 0.125)
    assert fraction == pytest.approx(1.875 / 4, abs=1e-9)
    assert world.is_free(fraction * dx, fraction * dy, 0.125)
    assert not world.is_free((fraction + 1e-6) * dx, (fraction + 1e-6) * dy, 0.125)


def test_fast_motion_cannot_tunnel_through_a_thin_obstacle():
    world = World((-2, -2, 2, 2), (Obstacle("thin", 0.20, -0.5, 0.200001, 0.5),))
    assert world.is_free(-0.60, 0, 0.10)
    assert world.is_free(0.60, 0, 0.10)
    fraction = world.sweep(-0.60, 0, 1.20, 0, 0.10)
    assert fraction == pytest.approx(0.70 / 1.20, abs=1e-9)
    assert world.is_free(-0.60 + fraction * 1.20, 0, 0.10)
    assert not world.is_free(-0.60 + (fraction + 1e-6) * 1.20, 0, 0.10)


@pytest.mark.parametrize("sx,sy", [(-1, -1), (-1, 1), (1, -1), (1, 1)])
def test_diagonal_approach_hits_each_circular_corner_at_analytic_distance(sx, sy):
    world = World((-2, -2, 2, 2), (Obstacle("box", -0.25, -0.25, 0.25, 0.25),))
    dx, dy = -2 * sx, -2 * sy
    fraction = world.sweep(sx, sy, dx, dy, 0.25)
    # Along a 45 degree diagonal, disk contact is r/sqrt(2) from each corner axis.
    expected = (1 - 0.25 - 0.25 / math.sqrt(2)) / 2
    assert fraction == pytest.approx(expected, abs=1e-9)
    assert world.is_free(sx + fraction * dx, sy + fraction * dy, 0.25)
    assert not world.is_free(sx + (fraction + 1e-6) * dx, sy + (fraction + 1e-6) * dy, 0.25)


@pytest.mark.parametrize("x,y,dx,dy", [
    (-0.25, 0.5, -0.5, 0),  # move away from an obstacle face
    (-0.25, 0.5, 0, 0.25),  # slide along a face
    (-0.25, 0.5, 0, 1.0),   # slide beyond a rounded corner
    (-0.5, -0.25, 1.0, 0),  # graze the bottom circular corners
])
def test_touching_obstacle_does_not_block_nonpenetrating_motion(x, y, dx, dy):
    world = World((-2, -2, 2, 2), (Obstacle("box", 0, 0, 1, 1),))
    assert world.is_free(x, y, 0.25)
    assert world.sweep(x, y, dx, dy, 0.25) == 1.0


def test_arena_contact_allows_tangent_and_away_motion_but_blocks_inward_motion():
    world = World((-2, -2, 2, 2))
    assert world.sweep(1.75, 0, 0, 1, 0.25) == 1.0
    assert world.sweep(1.75, 0, -1, 0, 0.25) == 1.0
    assert world.sweep(1.75, 0, 1, 0, 0.25) == 0.0


def test_zero_motion_and_obstacle_contact_have_explicit_results():
    world = World((-2, -2, 2, 2), (Obstacle("box", 0, 0, 1, 1),))
    assert world.sweep(-0.5, 0, 0, 0, 0.25) == 1.0
    assert world.sweep(-0.25, 0.5, 1, 0, 0.25) == 0.0
    with pytest.raises(ValueError, match="starts in collision"):
        world.sweep(0.5, 0.5, 0, 0, 0.25)


@pytest.mark.parametrize("dx,dy,distance", [(2, 0, 4), (-5, 0, 2), (0, 10, 5), (0, -3, 3)])
def test_raycast_normalizes_direction_and_handles_parallel_axes(dx, dy, distance):
    world = World((-2, -3, 4, 5))
    hit = world.raycast(0, 0, dx, dy, 10)
    assert hit.name == "wall"
    assert hit.distance_m == pytest.approx(distance)
    assert world.raycast(0, 0, dx, dy, distance).distance_m == pytest.approx(distance)
    assert world.raycast(0, 0, dx, dy, distance - 0.01) is None


def test_raycast_hits_nearest_box_independent_of_obstacle_order():
    near = Obstacle("near", 0.5, -0.2, 0.6, 0.2)
    far = Obstacle("far", 1.0, -0.3, 1.3, 0.3)
    behind = Obstacle("behind", -1.0, -0.3, -0.5, 0.3)
    off_axis = Obstacle("off-axis", 0.1, 0.2, 0.2, 0.4)
    for obstacles in ((far, off_axis, behind, near), (near, behind, off_axis, far)):
        hit = World((-2, -2, 2, 2), obstacles).raycast(0, 0, 1, 0, 2)
        assert hit.name == "near"
        assert hit.distance_m == 0.5


def test_raycast_respects_obstacle_height_and_diagonal_metric_distance():
    world = World((-3, -3, 3, 3), (
        Obstacle("low", 0.5, 0.5, 0.75, 0.75, 0.1),
        Obstacle("high", 1, 1, 1.5, 1.5, 0.5),
    ))
    at_top = world.raycast(0, 0, 1, 1, 5, height_m=0.1)
    assert at_top.name == "low"
    assert at_top.distance_m == pytest.approx(math.sqrt(0.5))
    over_low = world.raycast(0, 0, 1, 1, 5, height_m=0.1001)
    assert over_low.name == "high"
    assert over_low.distance_m == pytest.approx(math.sqrt(2))


def test_ray_origin_inside_an_obstacle_reports_zero_distance():
    world = World((-2, -2, 2, 2), (Obstacle("box", -0.25, -0.25, 0.25, 0.25),))
    hit = world.raycast(0, 0, 1, 0, 1)
    assert (hit.name, hit.distance_m) == ("box", 0.0)


@pytest.mark.parametrize("overrides", [
    {"x_min": float("nan")}, {"height_m": float("inf")}, {"x_max": True},
    {"x_min": 1}, {"y_min": 1}, {"height_m": 0}, {"name": ""},
    {"color": (0, 256, 0)}, {"color": (0, -1, 0)}, {"color": (0, 0)},
    {"color": (0, 0.5, 0)}, {"color": (0, False, 0)},
])
def test_invalid_obstacles_are_rejected(overrides):
    values = dict(name="box", x_min=0, y_min=0, x_max=1, y_max=1)
    values.update(overrides)
    with pytest.raises(ValueError):
        Obstacle(**values)


@pytest.mark.parametrize("bounds,obstacles", [
    ((0, 0, 0, 1), ()), ((0, 0, 1, -1), ()), ((0, 0, 1), ()),
    ((0, 0, float("inf"), 1), ()), ((False, 0, 1, 1), ()),
    ((0, 0, 1, 1), ("box",)),
    ((0, 0, 1, 1), (Obstacle("outside", -0.01, 0, 0.5, 0.5),)),
    ((0, 0, 1, 1), (Obstacle("same", 0, 0, 0.2, 0.2), Obstacle("same", 0.5, 0.5, 0.7, 0.7))),
])
def test_invalid_world_definitions_are_rejected(bounds, obstacles):
    with pytest.raises(ValueError):
        World(bounds, obstacles)


@pytest.mark.parametrize("arguments", [
    (0, 0, 0, 1, 0), (0, 0, 0, 1, -0.1), (0, 0, float("nan"), 1, 0.1),
    (0, 0, 0, float("inf"), 0.1), (True, 0, 0, 1, 0.1),
])
def test_invalid_sweep_parameters_are_rejected(arguments):
    with pytest.raises(ValueError):
        World().sweep(*arguments)


@pytest.mark.parametrize("arguments", [
    (0, 0, 0, 0, 1, 0.1), (0, 0, 1, 0, 0, 0.1),
    (0, 0, 1, 0, 1, -0.1), (0, 0, float("nan"), 0, 1, 0.1),
    (0, 0, 1, 0, float("inf"), 0.1), (2, 0, 1, 0, 1, 0.1),
    (0, 0, True, 0, 1, 0.1),
])
def test_invalid_rays_are_rejected(arguments):
    with pytest.raises(ValueError):
        World().raycast(*arguments)


def test_world_snapshot_round_trip_preserves_geometry_without_aliasing():
    world = World((-2, -2, 2, 2), (Obstacle("box", 0.5, -0.25, 0.75, 0.25),))
    state = world.snapshot()
    restored = World.restore(json.loads(json.dumps(state)))
    assert restored == world
    state["bounds"][0] = -100
    state["obstacles"][0]["x_min"] = -100
    assert world.bounds == (-2, -2, 2, 2)
    assert restored.raycast(0, 0, 1, 0, 2).distance_m == 0.5
