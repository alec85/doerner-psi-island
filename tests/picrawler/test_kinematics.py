"""Independent geometric checks for the idealised PiCrawler test bed."""

from dataclasses import FrozenInstanceError, fields
from math import dist, pi, sqrt

import pytest

from psi_gw.body.picrawler.kinematics import (
    LEG_ORDER,
    Geometry,
    JointAngles,
    body_to_leg,
    forward_leg,
    hip_position,
    inverse_leg,
    leg_points,
    leg_to_body,
)


def test_manufacturer_link_dimensions_and_explicit_nominal_stance():
    geometry = Geometry()
    assert (geometry.coxa_m, geometry.upper_m, geometry.lower_m) == (0.033, 0.048, 0.078)
    assert geometry.hip_spacing_m == 0.077
    target = (geometry.nominal_reach_m, 0.0, -geometry.nominal_height_m)
    angles = inverse_leg(target, geometry)
    assert angles.knee_rad < 0
    assert forward_leg(angles, geometry) == pytest.approx(target, abs=1e-14)


def test_forward_known_right_angle_configurations():
    geometry = Geometry()
    assert forward_leg(JointAngles(0, 0, 0)) == pytest.approx((0.159, 0, 0), abs=1e-14)
    assert forward_leg(JointAngles(pi / 2, 0, 0)) == pytest.approx((0, 0.159, 0), abs=1e-14)
    # Upper link outward, lower link straight down.
    assert forward_leg(JointAngles(0, 0, -pi / 2)) == pytest.approx(
        (geometry.coxa_m + geometry.upper_m, 0, -geometry.lower_m), abs=1e-14
    )
    # Upper link up, lower link outward; no trig expressions used in the oracle.
    assert forward_leg(JointAngles(0, pi / 2, -pi / 2)) == pytest.approx(
        (geometry.coxa_m + geometry.lower_m, 0, geometry.upper_m), abs=1e-14
    )


def test_inverse_known_right_angle_configuration():
    angles = inverse_leg((0.081, 0.0, -0.078))
    assert (angles.yaw_rad, angles.hip_rad, angles.knee_rad) == pytest.approx(
        (0, 0, -pi / 2), abs=1e-13
    )


@pytest.mark.parametrize("yaw", [-2.6, -0.8, 0.0, 0.7, 2.4])
@pytest.mark.parametrize("hip", [-0.25, 0.0, 0.5, 1.1])
@pytest.mark.parametrize("knee", [-0.35, -0.9, -1.4])
def test_inverse_forward_round_trip_on_reachable_negative_knee_branch(yaw, hip, knee):
    angles = JointAngles(yaw, hip, knee)
    toe = forward_leg(angles)
    restored = inverse_leg(toe)
    assert (restored.yaw_rad, restored.hip_rad, restored.knee_rad) == pytest.approx(
        (yaw, hip, knee), abs=1e-12
    )
    assert forward_leg(restored) == pytest.approx(toe, abs=1e-14)


@pytest.mark.parametrize("target", [(0.085, 0, -0.060), (0.060, 0.045, -0.050), (0.070, -0.020, -0.040)])
def test_inverse_forward_targets_without_forward_generated_oracle(target):
    joints = inverse_leg(target)
    assert joints.knee_rad < 0
    assert forward_leg(joints) == pytest.approx(target, abs=1e-14)


def test_points_preserve_each_link_length_for_custom_geometry():
    geometry = Geometry(coxa_m=0.025, upper_m=0.061, lower_m=0.089)
    points = leg_points(JointAngles(-0.7, 0.25, -1.2), geometry)
    assert points[0] == (0, 0, 0)
    assert [dist(a, b) for a, b in zip(points, points[1:])] == pytest.approx(
        [0.025, 0.061, 0.089], abs=1e-14
    )
    assert points[-1] == forward_leg(JointAngles(-0.7, 0.25, -1.2), geometry)


def test_named_hips_and_radial_axes_have_declared_orientation():
    expected_hips = ((0.0385, -0.0385, 0), (0.0385, 0.0385, 0), (-0.0385, 0.0385, 0), (-0.0385, -0.0385, 0))
    expected_directions = ((1, -1), (1, 1), (-1, 1), (-1, -1))
    for leg, hip, (sx, sy) in zip(LEG_ORDER, expected_hips, expected_directions):
        assert hip_position(leg) == hip
        assert leg_to_body(leg, (0, 0, 0)) == hip
        assert leg_to_body(leg, (sqrt(2), 0, -0.06)) == pytest.approx(
            (hip[0] + sx, hip[1] + sy, -0.06), abs=1e-14
        )
        # Positive tangent is +90 degrees from positive radial in every frame.
        assert leg_to_body(leg, (0, sqrt(2), 0)) == pytest.approx(
            (hip[0] - sy, hip[1] + sx, 0), abs=1e-14
        )


@pytest.mark.parametrize("leg", LEG_ORDER)
def test_frame_transforms_are_inverse_and_preserve_distances(leg):
    geometry = Geometry(hip_spacing_m=0.12)
    a, b = (0.071, -0.012, -0.061), (0.025, 0.016, 0.040)
    body_a, body_b = leg_to_body(leg, a, geometry), leg_to_body(leg, b, geometry)
    assert body_to_leg(leg, body_a, geometry) == pytest.approx(a, abs=1e-14)
    assert leg_to_body(leg, body_to_leg(leg, b, geometry), geometry) == pytest.approx(b, abs=1e-14)
    assert dist(body_a, body_b) == pytest.approx(dist(a, b), abs=1e-14)


@pytest.mark.parametrize("name", [field.name for field in fields(Geometry)])
@pytest.mark.parametrize("value", [0, -0.001, float("nan"), float("inf"), float("-inf"), True, "0.1"])
def test_geometry_rejects_nonpositive_or_nonfinite_dimensions(name, value):
    with pytest.raises(ValueError):
        Geometry(**{name: value})


@pytest.mark.parametrize("name", [field.name for field in fields(JointAngles)])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), False, "0"])
def test_angles_reject_nonfinite_or_nonnumeric_values(name, value):
    angles = {"yaw_rad": 0.0, "hip_rad": 0.0, "knee_rad": -1.0}
    angles[name] = value
    with pytest.raises(ValueError):
        JointAngles(**angles)


def test_geometry_and_joint_values_are_immutable():
    with pytest.raises(FrozenInstanceError):
        Geometry().coxa_m = 1.0
    with pytest.raises(FrozenInstanceError):
        JointAngles(0, 0, -1).yaw_rad = 1.0


@pytest.mark.parametrize("target", [(0.3, 0, 0), (0.033, 0, 0), (0.04, 0, 0), (1e308, 1e308, 1e308)])
def test_inverse_rejects_unreachable_points(target):
    with pytest.raises(ValueError, match="unreachable"):
        inverse_leg(target)


@pytest.mark.parametrize("target", [(0, 0, -0.06), (0.159, 0, 0), (0.063, 0, 0), (0.159 + 1e-14, 0, 0)])
def test_inverse_rejects_undefined_yaw_and_workspace_singularities(target):
    with pytest.raises(ValueError, match="singular"):
        inverse_leg(target)


def test_small_reachable_margin_is_not_silently_clipped_to_boundary():
    target = (0.159 - 1e-8, 0.0, 0.0)
    joints = inverse_leg(target)
    assert joints.knee_rad < 0
    assert forward_leg(joints) == pytest.approx(target, abs=1e-14)
    with pytest.raises(ValueError, match="unreachable"):
        inverse_leg((0.159 + 1e-8, 0, 0))


@pytest.mark.parametrize("point", [(float("nan"), 0, 0), (0, float("inf"), 0), (1, 2), (1, 2, 3, 4), None, (True, 0, 0)])
def test_all_point_apis_reject_invalid_points(point):
    for operation in (inverse_leg, lambda p: leg_to_body("front_right", p), lambda p: body_to_leg("front_right", p)):
        with pytest.raises(ValueError):
            operation(point)


def test_unknown_leg_names_are_not_treated_as_indices():
    for leg in ("back_left", "RF", 0, None):
        with pytest.raises(ValueError):
            hip_position(leg)
        with pytest.raises(ValueError):
            leg_to_body(leg, (0, 0, 0))
        with pytest.raises(ValueError):
            body_to_leg(leg, (0, 0, 0))
