"""Own optional MJCF model; inertial, contact and actuator values are assumptions.

See docs/picrawler/ADR-mujoco.md. No MuJoCo import is needed to build the XML.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import math
import xml.etree.ElementTree as ET

from .kinematics import Geometry, LEG_ORDER, ATTACHMENT_YAWS, hip_position, inverse_leg
from .world import World, finite

ENGINE_VERSION = "3.3.7"
JOINT_LIMITS = ((-1.2, 1.2), (-1.6, 1.6), (-2.8, -0.15))


@dataclass(frozen=True, slots=True)
class DynamicsConfig:
    dt_s: float = 0.05
    physics_dt_s: float = 0.002
    torque_limit_nm: float = 0.35
    kp: float = 6.0
    kd: float = 0.02
    target_speed_rad_s: float = 4.0
    friction: float = 0.8
    foot_radius_m: float = 0.008
    chassis_mass_kg: float = 0.35
    cycle_s: float = 1.2
    stance_fraction: float = 0.85
    lift_m: float = 0.012
    max_speed_m_s: float = 0.03
    max_yaw_rad_s: float = 0.30

    def __post_init__(self):
        for name, value in asdict(self).items():
            if finite(value, name) <= 0:
                raise ValueError(f"{name} must be positive")
        if not 0.5 < self.stance_fraction < 1:
            raise ValueError("stance_fraction must be between 0.5 and 1")
        ratio = self.dt_s / self.physics_dt_s
        if ratio < 1 or not math.isclose(ratio, round(ratio), abs_tol=1e-10):
            raise ValueError("dt_s must be an integer multiple of physics_dt_s")

    @property
    def substeps(self):
        return round(self.dt_s / self.physics_dt_s)


def nominal_angles(geometry: Geometry = Geometry()) -> list[float]:
    j = inverse_leg((geometry.nominal_reach_m, 0, -geometry.nominal_height_m), geometry)
    return [j.yaw_rad, j.hip_rad, j.knee_rad] * 4


def _element(parent, tag, **attrs):
    def format_value(value):
        if isinstance(value, (tuple, list)):
            return " ".join(str(v) for v in value)
        return str(value)
    return ET.SubElement(parent, tag, {k: format_value(v) for k, v in attrs.items()})


def model_xml(world: World = World(), geometry: Geometry = Geometry(),
              config: DynamicsConfig = DynamicsConfig()) -> str:
    root = ET.Element("mujoco", model="picrawler_assumed_dynamics_v1")
    _element(root, "compiler", angle="radian", autolimits="true")
    option = _element(root, "option", timestep=config.physics_dt_s, gravity=(0, 0, -9.81),
                      integrator="implicitfast", solver="Newton", iterations=50, tolerance=1e-10)
    _element(option, "flag", autoreset="disable")
    default = _element(root, "default")
    _element(default, "joint", damping=0.01, frictionloss=0.005, armature=0.00002)
    _element(default, "geom", friction=(config.friction, 0.005, 0.0001),
             solref=(0.01, 1), solimp=(0.9, 0.95, 0.001))
    wb = _element(root, "worldbody")
    _element(wb, "geom", name="floor", type="plane", size=(0, 0, 0.05),
             contype=2, conaffinity=1, group=0, rgba=(0.65, 0.65, 0.65, 1))
    xmin, ymin, xmax, ymax = world.bounds
    walls = [("west", xmin-0.025, (ymin+ymax)/2, 0.025, (ymax-ymin)/2),
             ("east", xmax+0.025, (ymin+ymax)/2, 0.025, (ymax-ymin)/2),
             ("south", (xmin+xmax)/2, ymin-0.025, (xmax-xmin)/2+0.05, 0.025),
             ("north", (xmin+xmax)/2, ymax+0.025, (xmax-xmin)/2+0.05, 0.025)]
    for name, x, y, sx, sy in walls:
        _element(wb, "geom", name="wall_"+name, type="box", pos=(x, y, 0.15),
                 size=(sx, sy, 0.15), contype=2, conaffinity=1, group=0,
                 rgba=(0.3, 0.35, 0.4, 1))
    for i, o in enumerate(world.obstacles):
        _element(wb, "geom", name=f"obstacle_{i}", type="box",
                 pos=((o.x_min+o.x_max)/2, (o.y_min+o.y_max)/2, o.height_m/2),
                 size=((o.x_max-o.x_min)/2, (o.y_max-o.y_min)/2, o.height_m/2),
                 contype=2, conaffinity=1, group=0, rgba=tuple(c/255 for c in o.color)+(1,))
    body = _element(wb, "body", name="chassis", pos=(0, 0, geometry.nominal_height_m+config.foot_radius_m))
    _element(body, "freejoint", name="root")
    robot = dict(contype=1, conaffinity=2, group=1, rgba=(0.25, 0.5, 0.8, 1))
    _element(body, "geom", name="chassis_geom", type="box", size=(0.045, 0.04, 0.015),
             mass=config.chassis_mass_kg, **robot)
    for leg, yaw in zip(LEG_ORDER, ATTACHMENT_YAWS):
        origin = _element(body, "body", name=leg+"_yaw_body", pos=hip_position(leg, geometry), euler=(0, 0, yaw))
        _element(origin, "site", name=leg+"_origin", pos=(0, 0, 0))
        _element(origin, "joint", name=leg+"_yaw", axis=(0, 0, 1), range=JOINT_LIMITS[0])
        _element(origin, "geom", name=leg+"_coxa_geom", type="capsule", fromto=(0, 0, 0, geometry.coxa_m, 0, 0), size=0.006, mass=0.015, **robot)
        hip = _element(origin, "body", name=leg+"_hip_body", pos=(geometry.coxa_m, 0, 0))
        _element(hip, "site", name=leg+"_coxa", pos=(0, 0, 0))
        _element(hip, "joint", name=leg+"_hip", axis=(0, -1, 0), range=JOINT_LIMITS[1])
        _element(hip, "geom", name=leg+"_upper_geom", type="capsule", fromto=(0, 0, 0, geometry.upper_m, 0, 0), size=0.006, mass=0.020, **robot)
        knee = _element(hip, "body", name=leg+"_knee_body", pos=(geometry.upper_m, 0, 0))
        _element(knee, "site", name=leg+"_knee", pos=(0, 0, 0))
        _element(knee, "joint", name=leg+"_knee", axis=(0, -1, 0), range=JOINT_LIMITS[2])
        _element(knee, "geom", name=leg+"_lower_geom", type="capsule", fromto=(0, 0, 0, geometry.lower_m, 0, 0), size=0.005, mass=0.025, **robot)
        _element(knee, "site", name=leg+"_toe", pos=(geometry.lower_m, 0, 0))
        _element(knee, "geom", name=leg+"_foot", type="sphere", pos=(geometry.lower_m, 0, 0), size=config.foot_radius_m, mass=0.003, **robot)
    actuators = _element(root, "actuator")
    for leg in LEG_ORDER:
        for joint in ("yaw", "hip", "knee"):
            _element(actuators, "motor", name=leg+"_"+joint+"_motor", joint=leg+"_"+joint,
                     gear=1, ctrlrange=(-config.torque_limit_nm, config.torque_limit_nm),
                     forcerange=(-config.torque_limit_nm, config.torque_limit_nm))
    keys = _element(root, "keyframe")
    _element(keys, "key", name="nominal", qpos=[0, 0, geometry.nominal_height_m+config.foot_radius_m, 1, 0, 0, 0]+nominal_angles(geometry))
    return ET.tostring(root, encoding="unicode")


def model_digest(xml: str) -> str:
    return hashlib.sha256(xml.encode()).hexdigest()
