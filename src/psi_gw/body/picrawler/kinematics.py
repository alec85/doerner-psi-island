"""Independent, idealised PiCrawler leg kinematics in metres and radians.

Only geometric dimensions are taken from the manufacturer: the three link
lengths are 33, 48 and 78 mm and the square hip spacing is 77 mm. Sources:

https://github.com/sunfounder/picrawler/blob/14a54bc1909d4ce8f73e95d0fc09514c974910ce/picrawler/picrawler.py
https://github.com/sunfounder/picrawler/blob/14a54bc1909d4ce8f73e95d0fc09514c974910ce/picrawler-control/references/api.md
https://docs.sunfounder.com/projects/pi-crawler/en/latest/python/python_action_gallery.html

The equations, frames and angle conventions below are our own model, not the
SunFounder SDK/PWM conventions. In the body frame x points forward, y left and z
up. Each hip's local x axis points radially outward at its attachment yaw, local
y is counterclockwise from x when viewed from above, and local z points up.

Leg yaw rotates about local +z. Hip pitch is measured up from the horizontal;
knee pitch is relative to the upper leg. Zero pitch makes both links horizontal
and outward. Inverse kinematics selects the negative-knee branch. Nominal stance
dimensions are configurable simulation choices, not manufacturer measurements.

This model does not specify servo limits, PWM mapping, masses, contact forces or
stability. In particular it must not be used as an uncalibrated hardware driver.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, fields
from math import acos, atan2, cos, hypot, isfinite, pi, sin
from numbers import Real


Point3 = tuple[float, float, float]
LEG_ORDER = ("front_right", "front_left", "rear_left", "rear_right")
ATTACHMENT_YAWS = (-pi / 4, pi / 4, 3 * pi / 4, -3 * pi / 4)
_HIP_SIGNS = ((1, -1), (1, 1), (-1, 1), (-1, -1))
_REL_TOL = 1e-12


def _finite(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real number")
    result = float(value)
    if not isfinite(result):
        raise ValueError(f"{name} must be a finite real number")
    return result


def _point(values: Sequence[float]) -> Point3:
    try:
        x, y, z = values
    except (TypeError, ValueError) as error:
        raise ValueError("a point must contain exactly three finite coordinates") from error
    return (_finite(x, "x"), _finite(y, "y"), _finite(z, "z"))


def _leg_index(leg: str) -> int:
    try:
        return LEG_ORDER.index(leg)
    except ValueError as error:
        raise ValueError(f"unknown leg {leg!r}; expected one of {LEG_ORDER}") from error


@dataclass(frozen=True, slots=True)
class Geometry:
    """Positive geometric dimensions; ``hip_spacing_m`` describes a square.

    The two nominal dimensions describe a configurable idealised standing pose.
    They do not change link geometry or impose joint limits.
    """

    coxa_m: float = 0.033
    upper_m: float = 0.048
    lower_m: float = 0.078
    hip_spacing_m: float = 0.077
    nominal_height_m: float = 0.060
    nominal_reach_m: float = 0.085

    def __post_init__(self) -> None:
        for field in fields(self):
            value = _finite(getattr(self, field.name), field.name)
            if value <= 0:
                raise ValueError(f"{field.name} must be strictly positive")
            object.__setattr__(self, field.name, value)


@dataclass(frozen=True, slots=True)
class JointAngles:
    """Local yaw, absolute hip pitch and relative knee pitch, all in radians."""

    yaw_rad: float
    hip_rad: float
    knee_rad: float

    def __post_init__(self) -> None:
        for field in fields(self):
            object.__setattr__(
                self, field.name, _finite(getattr(self, field.name), field.name)
            )


def leg_points(
    joints: JointAngles, geometry: Geometry = Geometry()
) -> tuple[Point3, Point3, Point3, Point3]:
    """Return local hip origin, coxa end, knee and toe positions.

    Forward kinematics can represent singular postures. It does not claim that
    any chosen angle is mechanically attainable on the physical robot.
    """
    direction_x, direction_y = cos(joints.yaw_rad), sin(joints.yaw_rad)
    knee_radius = geometry.coxa_m + geometry.upper_m * cos(joints.hip_rad)
    knee_z = geometry.upper_m * sin(joints.hip_rad)
    toe_radius = knee_radius + geometry.lower_m * cos(
        joints.hip_rad + joints.knee_rad
    )
    toe_z = knee_z + geometry.lower_m * sin(joints.hip_rad + joints.knee_rad)
    return (
        (0.0, 0.0, 0.0),
        (geometry.coxa_m * direction_x, geometry.coxa_m * direction_y, 0.0),
        (knee_radius * direction_x, knee_radius * direction_y, knee_z),
        (toe_radius * direction_x, toe_radius * direction_y, toe_z),
    )


def forward_leg(joints: JointAngles, geometry: Geometry = Geometry()) -> Point3:
    """Return a toe position in its own hip's local frame."""
    return leg_points(joints, geometry)[-1]


def inverse_leg(foot: Sequence[float], geometry: Geometry = Geometry()) -> JointAngles:
    """Solve the negative-knee branch for a local toe target.

    Raise ``ValueError`` for invalid, unreachable or singular targets; targets
    are never projected onto the workspace. Radius zero leaves yaw undefined.
    A fully straight or folded two-link chain is also singular and rejected.
    A relative tolerance of 1e-12 classifies roundoff at workspace boundaries as
    singular rather than unreachable. This is numerical tolerance, not slack in
    the physical link lengths.
    """
    x, y, z = _point(foot)
    radius = hypot(x, y)
    scale = geometry.coxa_m + geometry.upper_m + geometry.lower_m
    tolerance = scale * _REL_TOL
    if radius <= tolerance:
        raise ValueError("singular target: leg yaw is undefined on its vertical axis")

    horizontal = radius - geometry.coxa_m
    distance = hypot(horizontal, z)
    minimum = abs(geometry.upper_m - geometry.lower_m)
    maximum = geometry.upper_m + geometry.lower_m
    if not isfinite(distance) or distance < minimum - tolerance or distance > maximum + tolerance:
        raise ValueError("unreachable target: outside the two-link workspace")
    if distance <= minimum + tolerance or distance >= maximum - tolerance:
        raise ValueError("singular target: the two-link chain is fully folded or straight")

    # Work with dimensionless ratios to avoid squaring metre values directly.
    ratio = distance / maximum
    upper = geometry.upper_m / maximum
    lower = geometry.lower_m / maximum
    knee_cosine = (ratio * ratio - upper * upper - lower * lower) / (2 * upper * lower)
    if not -1.0 < knee_cosine < 1.0:
        raise ValueError("singular target: insufficient numerical separation from a boundary")
    knee = -acos(knee_cosine)
    hip = atan2(z, horizontal) - atan2(
        geometry.lower_m * sin(knee),
        geometry.upper_m + geometry.lower_m * cos(knee),
    )
    return JointAngles(atan2(y, x), hip, knee)


def hip_position(leg: str, geometry: Geometry = Geometry()) -> Point3:
    """Return the named hip's body-frame position at zero height."""
    sign_x, sign_y = _HIP_SIGNS[_leg_index(leg)]
    half = geometry.hip_spacing_m / 2
    return (sign_x * half, sign_y * half, 0.0)


def leg_to_body(
    leg: str, point: Sequence[float], geometry: Geometry = Geometry()
) -> Point3:
    """Transform a local point into the body frame for a name in ``LEG_ORDER``."""
    x, y, z = _point(point)
    yaw = ATTACHMENT_YAWS[_leg_index(leg)]
    hx, hy, _ = hip_position(leg, geometry)
    return (hx + cos(yaw) * x - sin(yaw) * y, hy + sin(yaw) * x + cos(yaw) * y, z)


def body_to_leg(
    leg: str, point: Sequence[float], geometry: Geometry = Geometry()
) -> Point3:
    """Invert ``leg_to_body`` without changing the point's height."""
    x, y, z = _point(point)
    yaw = ATTACHMENT_YAWS[_leg_index(leg)]
    hx, hy, _ = hip_position(leg, geometry)
    dx, dy = x - hx, y - hy
    return (cos(yaw) * dx + sin(yaw) * dy, -sin(yaw) * dx + cos(yaw) * dy, z)
