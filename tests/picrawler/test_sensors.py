"""Range randomness and synthetic camera geometry, without a cognitive adapter."""

import math
import random

import numpy as np
import pytest

from psi_gw.body.picrawler.sensors import CameraConfig, RangeConfig, render_camera, sample_range
from psi_gw.body.picrawler.world import Obstacle, World
from psi_gw.random_source import RecordingSource, ReplaySource


def range_world():
    return World((-2, -2, 2, 2), (Obstacle("target", 0.8, -0.3, 1, 0.3, 0.3),))


def test_ideal_range_uses_mount_offset_and_separates_truth_from_observation():
    rng = ReplaySource([])
    observation, debug = sample_range(range_world(), (0, 0, 0, 0.06), rng,
                                      RangeConfig(offset_forward_m=0.05, mount_height_m=0.03))
    assert observation == {"distance_m": 0.75, "status": "ok"}
    assert set(observation) == {"distance_m", "status"}
    assert debug["truth_distance_m"] == 0.75
    assert debug["origin"] == pytest.approx([0.05, 0, 0.09])
    assert debug["direction"] == [1, 0, 0]
    assert rng.draws == 0


def test_range_mount_rotates_with_body_and_height_can_clear_a_low_object():
    world = World((-2, -2, 2, 2), (Obstacle("low", -0.3, 0.8, 0.3, 1, 0.1),))
    config = RangeConfig(offset_forward_m=0.05, mount_height_m=0.03)
    below, debug = sample_range(world, (0, 0, math.pi / 2, 0.06), ReplaySource([]), config)
    assert below["distance_m"] == pytest.approx(0.75)
    assert debug["origin"] == pytest.approx([0, 0.05, 0.09], abs=1e-15)
    above, _ = sample_range(world, (0, 0, math.pi / 2, 0.08), ReplaySource([]), config)
    assert above["distance_m"] == pytest.approx(1.95)


@pytest.mark.parametrize("draw,expected", [(0, 0.65), (0.5, 0.75), (0.75, 0.8)])
def test_range_uniform_noise_uses_one_controlled_draw(draw, expected):
    rng = RecordingSource(ReplaySource([draw]))
    reading, debug = sample_range(range_world(), (0, 0, 0, 0.06), rng,
                                 RangeConfig(offset_forward_m=0.05, noise_half_width_m=0.1))
    assert reading["status"] == "ok"
    assert reading["distance_m"] == pytest.approx(expected)
    assert debug["truth_distance_m"] == 0.75
    assert [entry.site for entry in rng.log] == ["picrawler.range.noise"]


def test_dropout_precedes_noise_and_does_not_spend_a_noise_draw():
    rng = RecordingSource(ReplaySource([0.1]))
    reading, debug = sample_range(range_world(), (0, 0, 0, 0.06), rng,
                                 RangeConfig(dropout_probability=0.2, noise_half_width_m=0.1))
    assert reading == {"distance_m": None, "status": "dropout"}
    assert debug["truth_distance_m"] == pytest.approx(0.755)
    assert [entry.site for entry in rng.log] == ["picrawler.range.dropout"]


def test_successful_dropout_check_is_followed_by_noise_in_declared_order():
    rng = RecordingSource(ReplaySource([0.8, 0.75]))
    reading, _ = sample_range(range_world(), (0, 0, 0, 0.06), rng,
                             RangeConfig(offset_forward_m=0.05, dropout_probability=0.2,
                                         noise_half_width_m=0.1))
    assert reading["distance_m"] == pytest.approx(0.8)
    assert [entry.site for entry in rng.log] == ["picrawler.range.dropout", "picrawler.range.noise"]


def test_dropout_threshold_is_strict():
    rng = ReplaySource([0.25])
    reading, _ = sample_range(range_world(), (0, 0, 0, 0.06), rng,
                             RangeConfig(dropout_probability=0.25))
    assert reading["status"] == "ok"
    assert rng.draws == 1


@pytest.mark.parametrize("config,status", [
    (RangeConfig(minimum_m=1.1, maximum_m=2, offset_forward_m=0,
                 dropout_probability=0.5, noise_half_width_m=0.1), "too_close"),
    (RangeConfig(maximum_m=0.9, offset_forward_m=0,
                 dropout_probability=0.5, noise_half_width_m=0.1), "out_of_range"),
])
def test_invalid_geometric_ranges_do_not_draw_or_return_a_fabricated_distance(config, status):
    rng = ReplaySource([])
    reading, _ = sample_range(World((-1, -1, 1, 1)), (0, 0, 0, 0.06), rng, config)
    assert reading == {"distance_m": None, "status": status}
    assert rng.draws == 0


@pytest.mark.parametrize("draw,status", [(0, "too_close"), (0.999, "out_of_range")])
def test_noise_outside_sensor_interval_is_invalid_instead_of_clipped(draw, status):
    rng = ReplaySource([draw])
    config = RangeConfig(minimum_m=0.9, maximum_m=1.1, offset_forward_m=0, noise_half_width_m=0.2)
    reading, debug = sample_range(World((-1, -1, 1, 1)), (0, 0, 0, 0.06), rng, config)
    assert reading == {"distance_m": None, "status": status}
    assert debug["truth_distance_m"] == 1
    assert rng.draws == 1


@pytest.mark.parametrize("minimum,maximum", [(1, 2), (0, 1)])
def test_sensor_range_endpoints_are_inclusive(minimum, maximum):
    reading, _ = sample_range(World((-1, -1, 1, 1)), (0, 0, 0, 0.06), ReplaySource([]),
                             RangeConfig(minimum_m=minimum, maximum_m=maximum, offset_forward_m=0))
    assert reading == {"distance_m": 1, "status": "ok"}


@pytest.mark.parametrize("values", [
    {"minimum_m": -1}, {"minimum_m": 4}, {"maximum_m": 0},
    {"maximum_m": float("inf")}, {"noise_half_width_m": -0.1},
    {"dropout_probability": -0.01}, {"dropout_probability": 1.01},
    {"offset_forward_m": -0.01}, {"mount_height_m": -0.01},
    {"minimum_m": float("nan")}, {"maximum_m": True},
])
def test_range_configuration_rejects_invalid_numbers(values):
    with pytest.raises(ValueError):
        RangeConfig(**values)


@pytest.mark.parametrize("values", [
    {"width": 0}, {"width": 321}, {"height": 0}, {"height": 241},
    {"width": 48.0}, {"height": True}, {"horizontal_fov_rad": 0},
    {"horizontal_fov_rad": math.pi}, {"horizontal_fov_rad": float("nan")},
    {"offset_forward_m": -0.01}, {"mount_height_m": -0.01},
    {"mount_height_m": float("inf")},
])
def test_camera_configuration_rejects_invalid_numbers(values):
    with pytest.raises(ValueError):
        CameraConfig(**values)


def test_central_near_box_occludes_far_box_independent_of_insertion_order():
    near = Obstacle("near", 1, -0.3, 1.2, 0.3, 0.8, (200, 0, 0))
    far = Obstacle("far", 2, -0.2, 2.2, 0.2, 0.8, (0, 0, 200))
    config = CameraConfig(width=33, height=25, horizontal_fov_rad=math.pi / 2,
                          offset_forward_m=0, mount_height_m=0)
    pose = (0, 0, 0, 0.4)
    near_image = render_camera(World((-3, -3, 3, 3), (near,)), pose, config)
    far_image = render_camera(World((-3, -3, 3, 3), (far,)), pose, config)
    assert tuple(near_image[12, 16]) == (186, 0, 0)
    assert tuple(far_image[12, 16]) == (0, 0, 172)
    for obstacles in ((near, far), (far, near)):
        image = render_camera(World((-3, -3, 3, 3), obstacles), pose, config)
        np.testing.assert_array_equal(image, near_image)


@pytest.mark.parametrize("yaw,obstacles", [
    (0, (Obstacle("left", 1, 0.25, 1.2, 0.45, 0.7, (220, 0, 0)),
         Obstacle("right", 1, -0.45, 1.2, -0.25, 0.7, (0, 220, 0)))),
    (math.pi / 2, (Obstacle("left", -0.45, 1, -0.25, 1.2, 0.7, (220, 0, 0)),
                  Obstacle("right", 0.25, 1, 0.45, 1.2, 0.7, (0, 220, 0)))),
])
def test_camera_image_right_is_body_negative_y_even_after_yaw_rotation(yaw, obstacles):
    config = CameraConfig(width=65, height=33, horizontal_fov_rad=math.pi / 2,
                          offset_forward_m=0, mount_height_m=0)
    image = render_camera(World((-3, -3, 3, 3), obstacles), (0, 0, yaw, 0.35), config)
    red = (image[..., 0] > 100) & (image[..., 1] == 0) & (image[..., 2] == 0)
    green = (image[..., 0] == 0) & (image[..., 1] > 100) & (image[..., 2] == 0)
    assert red.any() and green.any()
    assert np.where(red)[1].max() < config.width // 2
    assert np.where(green)[1].min() > config.width // 2


def test_renderer_is_repeatable_owns_its_image_and_never_uses_global_randomness(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("rendering must not draw from a random source")

    for name in ("random", "rand", "uniform", "default_rng"):
        monkeypatch.setattr(np.random, name, forbidden)
    monkeypatch.setattr(random, "random", forbidden)
    world = range_world()
    before = world.snapshot()
    config = CameraConfig(width=33, height=25)
    with np.errstate(all="raise"):
        image = render_camera(world, (0, 0, 0, 0.06), config)
        expected = render_camera(world, (0, 0, 0, 0.06), config)
    assert image.shape == (25, 33, 3)
    assert image.dtype == np.uint8
    np.testing.assert_array_equal(image, expected)
    image[:] = 0
    np.testing.assert_array_equal(render_camera(world, (0, 0, 0, 0.06), config), expected)
    assert world.snapshot() == before


@pytest.mark.parametrize("index", range(4))
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_sensor_entry_points_reject_nonfinite_pose(index, value):
    pose = [0.0, 0.0, 0.0, 0.06]
    pose[index] = value
    with pytest.raises(ValueError):
        sample_range(World(), tuple(pose), ReplaySource([]), RangeConfig())
    with pytest.raises(ValueError):
        render_camera(World(), tuple(pose), CameraConfig())
