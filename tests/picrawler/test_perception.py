"""Sensor-only scenarios: absent echoes, noise, occlusion, colours and delay."""

import copy
import json
import math

import pytest

from psi_gw.body.picrawler.perception import (
    ColorBand,
    PerceptionConfig,
    camera_features,
    median_range_window,
    perceive,
    range_features,
)


def rgb_image(width=8, height=6, color=(90, 90, 90)):
    """Reusable synthetic camera fixture; every pixel has independent storage."""
    return [[list(color) for _ in range(width)] for _ in range(height)]


def sensor_scenarios():
    """Return fresh, reusable raw-input cases without simulator world metadata."""
    colors = rgb_image()
    for y in range(2, 4):
        for x in range(1, 3):
            colors[y][x] = [240, 20, 20]
    for y in range(1, 5):
        for x in range(5, 7):
            colors[y][x] = [20, 30, 240]
    occluded = rgb_image(6, 4, (235, 20, 20))
    for row in occluded:
        row[2] = row[3] = [90, 90, 90]
    return {
        "missing_echo": {"ultrasonic": {"distance_m": None, "status": "dropout", "captured_at_s": 1.0}},
        "colors": {"camera": {"encoding": "rgb8", "rgb": colors, "captured_at_s": 1.0}},
        "occlusion": {"camera": {"encoding": "rgb8", "rgb": occluded, "captured_at_s": 1.0}},
        "delayed": {
            "ultrasonic": {"distance_m": 0.08, "status": "ok", "captured_at_s": 0.2},
            "camera": {"encoding": "rgb8", "rgb": colors, "captured_at_s": 0.2},
        },
        "noisy_window": [
            {"distance_m": distance, "status": "ok", "captured_at_s": 0.8 + i * 0.025}
            for i, distance in enumerate((0.20, 0.21, 0.19, 0.20, 3.0))
        ] + [
            {"distance_m": None, "status": "dropout", "captured_at_s": 0.99},
            {"distance_m": 0.02, "status": "ok", "captured_at_s": 0.1},
        ],
    }


@pytest.mark.parametrize("distance,expected", [(0.02, 1), (0.1, 1), (0.3, 0.5), (0.5, 0), (4.0, 0)])
def test_range_has_an_explicit_bounded_proximity(distance, expected):
    feature = range_features({"distance_m": distance, "captured_at_s": 1.0}, now_s=1.1)
    assert feature.valid and feature.usable
    assert feature.age_s == pytest.approx(0.1)
    assert feature.proximity == pytest.approx(expected)


@pytest.mark.parametrize("distance", [None, -0.1, 0.01, 4.01, float("nan"), float("inf"), True, "0.3"])
def test_invalid_echo_is_never_interpreted_as_free_space(distance):
    feature = range_features({"distance_m": distance, "captured_at_s": 1.0}, now_s=1.0)
    assert not feature.valid and not feature.usable
    assert feature.proximity is None


def test_dropouts_and_missing_sensor_are_explicit():
    result = perceive(sensor_scenarios()["missing_echo"], now_s=1.0)
    assert result.range.status == "dropout"
    assert result.range.proximity is None
    assert result.camera.status == "missing"
    empty = perceive({}, now_s=1.0)
    assert empty.range.status == "missing"
    assert not empty.range.usable


def test_sensor_status_overrides_a_plausible_numeric_echo():
    feature = range_features({"distance_m": 0.2, "status": "dropout", "captured_at_s": 1}, now_s=1)
    assert not feature.valid
    assert feature.distance_m == 0.2
    assert feature.proximity is None


def test_missing_timestamp_is_not_invented():
    sensors = {"ultrasonic": {"distance_m": 0.2}, "camera": {"rgb": rgb_image()}}
    unknown = perceive(sensors, now_s=4)
    assert unknown.range.valid and not unknown.range.usable
    assert unknown.range.freshness == "unknown"
    assert unknown.to_dict()["range"]["stale"] is None
    explicit = perceive(sensors, now_s=4, sample_time_s=4)
    assert explicit.range.usable and explicit.camera.usable


@pytest.mark.parametrize("stamp,freshness", [(0.2, "stale"), (1.1, "future"), (float("nan"), "invalid"), (-1, "invalid")])
def test_bad_capture_times_are_not_overridden_by_fallback(stamp, freshness):
    sensor = {"distance_m": 0.2, "captured_at_s": stamp}
    feature = range_features(sensor, now_s=1.0, sample_time_s=1.0)
    assert feature.freshness == freshness
    assert not feature.usable and feature.proximity is None


def test_delayed_camera_and_echo_do_not_yield_actionable_features():
    result = perceive(sensor_scenarios()["delayed"], now_s=1.0)
    assert result.range.valid and result.camera.valid
    assert not result.range.usable and not result.camera.usable
    assert result.range.age_s == pytest.approx(0.8)
    assert result.range.proximity is None
    assert result.camera.blobs == ()
    assert result.to_dict()["camera"]["stale"] is True


def test_noise_window_uses_only_fresh_valid_samples():
    samples = sensor_scenarios()["noisy_window"]
    original = copy.deepcopy(samples)
    feature = median_range_window(samples, now_s=1.0)
    assert feature.usable
    assert feature.samples_used == 5
    assert feature.distance_m == 0.20
    assert feature.age_s == pytest.approx(0.2)
    assert feature.proximity == pytest.approx(0.75)
    assert samples == original
    insufficient = median_range_window(samples, now_s=2.0)
    assert not insufficient.usable
    assert insufficient.status == "insufficient_fresh_samples"
    assert insufficient.proximity is None


def test_color_components_have_normalized_area_centroid_and_bounds():
    result = perceive(sensor_scenarios()["colors"], now_s=1.0)
    blue, red = result.camera.blobs
    assert blue.color == "blue" and red.color == "red"
    assert blue.pixel_count == 8 and red.pixel_count == 4
    assert blue.area_fraction == pytest.approx(8 / 48)
    assert blue.centroid_x == pytest.approx(6 / 8)
    assert blue.centroid_y == pytest.approx(3 / 6)
    assert blue.bounds == pytest.approx((5 / 8, 1 / 6, 7 / 8, 5 / 6))
    assert red.centroid_x == pytest.approx(2 / 8)
    assert red.centroid_y == pytest.approx(3 / 6)


def test_occlusion_splits_visible_regions_without_claiming_hidden_identity():
    result = perceive(sensor_scenarios()["occlusion"], now_s=1.0)
    left, right = result.camera.blobs
    assert left.color == right.color == "red"
    assert left.pixel_count == right.pixel_count == 8
    assert left.centroid_x == pytest.approx(1 / 6)
    assert right.centroid_x == pytest.approx(5 / 6)
    assert not hasattr(left, "object_id")


def test_diagonal_pixels_are_separate_under_four_connectivity():
    image = rgb_image(2, 2)
    image[0][0] = image[1][1] = [255, 0, 0]
    result = camera_features({"rgb": image}, now_s=0, sample_time_s=0,
                             config=PerceptionConfig(minimum_blob_pixels=1))
    assert [b.pixel_count for b in result.blobs] == [1, 1]


def test_red_hue_wraps_at_zero_and_dark_gray_pixels_are_ignored():
    image = [[[255, 0, 12], [255, 12, 0], [20, 0, 0], [100, 100, 100]]]
    result = camera_features({"rgb": image}, now_s=0, sample_time_s=0,
                             config=PerceptionConfig(minimum_blob_pixels=1))
    assert len(result.blobs) == 1
    assert result.blobs[0].color == "red" and result.blobs[0].pixel_count == 2


def test_world_metadata_cannot_change_the_baseline():
    inputs = sensor_scenarios()["colors"]
    before = copy.deepcopy(inputs)
    result = perceive(inputs, now_s=1)
    changed = copy.deepcopy(inputs)
    changed.update(world={"objects": ["food", "predator"]}, pose=[999, 999], collision=True)
    assert perceive(changed, now_s=1) == result
    assert inputs == before
    assert json.loads(json.dumps(result.to_dict(), allow_nan=False))["source"] == "sensor_baseline"


@pytest.mark.parametrize("rgb", [[], [[[]]], [[[0, 0, 256]]], [[[True, 0, 0]]], [[[0.5, 0, 0]]], [[[0, 0, 0]], []]])
def test_malformed_camera_data_fails_closed(rgb):
    result = camera_features({"rgb": rgb}, now_s=1, sample_time_s=1)
    assert not result.valid and not result.usable
    assert result.blobs == ()
    assert result.status == "invalid_image"


def test_camera_dimensions_and_encoding_are_checked():
    assert camera_features({"rgb": rgb_image(), "width": 7}, now_s=0).status == "dimension_mismatch"
    assert camera_features({"rgb": rgb_image(), "encoding": "bgr8"}, now_s=0).status == "unsupported_encoding"
    large = camera_features({"rgb": rgb_image()}, now_s=0,
                            config=PerceptionConfig(maximum_image_pixels=10))
    assert large.status == "invalid_image"


@pytest.mark.parametrize("kwargs", [{"near_m": 1, "far_m": 0.5}, {"maximum_age_s": -1}, {"minimum_blob_pixels": True}, {"minimum_saturation": math.nan}, {"maximum_blobs": 0}])
def test_invalid_configuration_is_rejected(kwargs):
    with pytest.raises(ValueError):
        PerceptionConfig(**kwargs)


def test_duplicate_color_names_and_invalid_time_are_rejected():
    with pytest.raises(ValueError):
        PerceptionConfig(colors=(ColorBand("red", 0, 0.1), ColorBand("red", 0.1, 0.1)))
    with pytest.raises(ValueError):
        perceive({}, now_s=-1)
    with pytest.raises(ValueError):
        perceive({}, now_s=0, sample_time_s=math.inf)
    with pytest.raises(ValueError):
        median_range_window([], now_s=0, minimum_samples=0)
