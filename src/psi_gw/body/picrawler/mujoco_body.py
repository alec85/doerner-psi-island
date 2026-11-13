"""Optional physical Body adapter, with observer-only joint/contact diagnostics.

No body translation/orientation is prescribed after reset. All numerical values
are experiment assumptions (ADR-mujoco), not hardware calibration.
"""
from __future__ import annotations

import copy
from dataclasses import asdict
import json
import math

import numpy as np

from psi_gw.body.base import Action, Observation
from psi_gw.random_source import NumpySource, restore_source
from .energy import (EnergyConfig, EnergyEnvironment, EnergyState, initial_energy,
                     energy_readings, advance_energy, need_signals)
from .kinematics import (Geometry, LEG_ORDER, leg_to_body, body_to_leg, inverse_leg)
from .mujoco_model import DynamicsConfig, ENGINE_VERSION, JOINT_LIMITS, model_xml, model_digest, nominal_angles
from .peripherals import PeripheralConfig, PeripheralSim
from .sensors import RangeConfig, CameraConfig
from .world import World, finite


def _engine():
    try:
        import mujoco
    except ImportError as error:
        raise ImportError('Install the optional backend with pip install -e ".[mujoco]"') from error
    if mujoco.__version__ != ENGINE_VERSION:
        raise RuntimeError(f"MuJoCo {ENGINE_VERSION} required, found {mujoco.__version__}")
    return mujoco


class MujocoBody:
    """Free floating quadruped; local servos only use their own joint feedback.

    ``relax`` is an explicit local experiment action, absent from the bridge.
    CPU ray sensors include full physical orientation but exclude robot geoms.
    """
    def __init__(self, *, world: World = World(), geometry: Geometry = Geometry(),
                 config: DynamicsConfig = DynamicsConfig(), range_config: RangeConfig = RangeConfig(),
                 camera_config: CameraConfig | None = CameraConfig(width=24, height=16),
                 energy_config: EnergyConfig = EnergyConfig(), seed: int = 0,
                 initial_pose: tuple[float, float, float] = (0, 0, 0)):
        self.mj = _engine()
        self.world, self.geometry, self.config = world, geometry, config
        self.range_config, self.camera_config, self.energy_config = range_config, camera_config, energy_config
        if len(initial_pose) != 3:
            raise ValueError("initial_pose must contain x, y, yaw")
        self.initial_pose = tuple(finite(v, "initial pose") for v in initial_pose)
        # Conservative initial placement, not a constraint on future dynamics.
        if not world.is_free(*self.initial_pose[:2], 0.16):
            raise ValueError("initial pose overlaps the arena boundary or obstacle")
        self.xml = model_xml(world, geometry, config)
        self.model = self.mj.MjModel.from_xml_string(self.xml)
        self.data = self.mj.MjData(self.model)
        self._body_id = self.model.body("chassis").id
        self._state_spec = self.mj.mjtState.mjSTATE_INTEGRATION
        self.reset(seed)

    @property
    def tick(self):
        return self._tick

    @property
    def time_s(self):
        return self._tick * self.config.dt_s

    def reset(self, seed: int):
        if type(seed) is not int or seed < 0:
            raise ValueError("seed must be a nonnegative integer")
        self.mj.mj_resetDataKeyframe(self.model, self.data, 0)
        x, y, yaw = self.initial_pose
        self.data.qpos[:2] = x, y
        self.data.qpos[3:7] = math.cos(yaw/2), 0, 0, math.sin(yaw/2)
        self.mj.mj_forward(self.model, self.data)
        self._seed, self._rng = seed, NumpySource(seed)
        self._tick, self._phase, self._distance = 0, 0.0, 0.0
        self._targets = np.array(nominal_angles(self.geometry))
        self._command = dict(forward_mps=0.0, lateral_mps=0.0, yaw_rps=0.0)
        self._relaxed = False
        self._faulted = False
        self._positive_work_j = self._negative_work_j = 0.0
        self._energy = initial_energy(self.energy_config)
        self._environment = EnergyEnvironment(self.energy_config.cpu_load, self.energy_config.ambient_temperature_c)
        self.peripherals = PeripheralSim(PeripheralConfig(dt_s=self.config.dt_s))
        self._pending_buttons = []
        self._telemetry = energy_readings(self._energy, self.energy_config, self._environment,
                                          camera_enabled=self.camera_config is not None)
        self._cache()
        return self.observe()

    def available_actions(self):
        return ["drive", "stop", "stand", "relax", "tone", "sound", "speak", "stop_audio", "led"]

    def observe(self):
        return Observation(self._tick, copy.deepcopy(self._readings),
                           need_signals(self._telemetry, self.energy_config) if self.energy_config.enabled else {})

    def set_environment(self, *, cpu_load=None, ambient_temperature_c=None):
        self._environment = EnergyEnvironment(
            self._environment.cpu_load if cpu_load is None else cpu_load,
            self._environment.ambient_temperature_c if ambient_temperature_c is None else ambient_temperature_c)

    def inject_button(self, button: str, down: bool):
        if button not in ("user", "reset") or type(down) is not bool:
            raise ValueError("invalid button")
        self._pending_buttons.append((button, down))

    def _parse_action(self, action):
        if not isinstance(action, Action) or action.name not in self.available_actions() or not isinstance(action.params, dict):
            raise ValueError("invalid action")
        command = dict(forward_mps=0.0, lateral_mps=0.0, yaw_rps=0.0)
        peripheral = PeripheralSim.restore(self.peripherals.snapshot())
        if action.name == "drive":
            if action.params.keys() - command.keys():
                raise ValueError("unknown drive parameter")
            for key, value in action.params.items():
                command[key] = finite(value, key)
            speed = math.hypot(command["forward_mps"], command["lateral_mps"])
            if speed > self.config.max_speed_m_s:
                for key in ("forward_mps", "lateral_mps"):
                    command[key] *= self.config.max_speed_m_s / speed
            command["yaw_rps"] = float(np.clip(command["yaw_rps"], -self.config.max_yaw_rad_s, self.config.max_yaw_rad_s))
        elif action.name in ("stop", "stand", "relax"):
            if action.params:
                raise ValueError("action takes no parameters")
        else:
            peripheral.command(action.name, **action.params)
        return command, peripheral

    def _gait_targets(self):
        if not any(self._command.values()):
            return np.array(nominal_angles(self.geometry))
        result = []
        c, g = self.config, self.geometry
        # A slow crawl: stance feet move backwards in the body frame.
        for leg, offset in zip(LEG_ORDER, (0.0, 0.5, 0.25, 0.75)):
            phase = (self._phase + offset) % 1
            nominal = np.array(leg_to_body(leg, (g.nominal_reach_m, 0, -g.nominal_height_m), g))
            velocity = np.array((self._command["forward_mps"]-self._command["yaw_rps"]*nominal[1],
                                 self._command["lateral_mps"]+self._command["yaw_rps"]*nominal[0], 0.0))
            if phase < c.stance_fraction:
                progress, lift = phase/c.stance_fraction, 0.0
                delta = (0.5-progress)*c.cycle_s*c.stance_fraction
            else:
                u = (phase-c.stance_fraction)/(1-c.stance_fraction)
                progress = u*u*(3-2*u)
                delta = (progress-0.5)*c.cycle_s*c.stance_fraction
                lift = c.lift_m*math.sin(math.pi*u)**2
            target = nominal + velocity*delta + np.array((0, 0, lift))
            j = inverse_leg(body_to_leg(leg, target, g), g)
            result.extend((j.yaw_rad, j.hip_rad, j.knee_rad))
        return np.clip(result, np.tile(np.array(JOINT_LIMITS)[:, 0], 4), np.tile(np.array(JOINT_LIMITS)[:, 1], 4))

    def act(self, action):
        if self._faulted:
            raise RuntimeError("MuJoCo numerical fault; reset required")
        command, peripheral = self._parse_action(action)
        if not np.isfinite(self.data.qpos).all() or not np.isfinite(self.data.qvel).all():
            self._faulted = True
            self.data.ctrl[:] = 0
            raise RuntimeError("MuJoCo numerical fault; reset required")
        # Preflight all target computations before mutating state.
        previous = self._command
        self._command = command
        try:
            self._gait_targets()
        except Exception:
            self._command = previous
            raise
        self.peripherals = peripheral
        for event in self._pending_buttons:
            self.peripherals.inject_button(*event)
        self._pending_buttons = []
        self._relaxed = action.name == "relax"
        c, d = self.config, self.data
        old_xy = d.qpos[:2].copy()
        averages = dict(current_a=0.0, power_w=0.0, cpu_power_w=0.0, servo_power_w=0.0)
        for _ in range(c.substeps):
            desired = self._gait_targets()
            self._targets += np.clip(desired-self._targets, -c.target_speed_rad_s*c.physics_dt_s, c.target_speed_rad_s*c.physics_dt_s)
            torque = np.clip(c.kp*(self._targets-d.qpos[7:])-c.kd*d.qvel[6:], -c.torque_limit_nm, c.torque_limit_nm)
            if self._relaxed or (self.energy_config.enabled and not self._telemetry["powered"]):
                torque[:] = 0
            mechanical = torque*d.qvel[6:]
            motor_power = float(np.maximum(mechanical, 0).sum()/0.65 + 8*np.square(torque).sum())
            accessory = motor_power + self.peripherals.additional_power_w()
            if self.energy_config.enabled:
                self._energy, self._telemetry = advance_energy(self._energy, self.energy_config, self._environment,
                    dt_s=c.physics_dt_s, motion_fraction=0, camera_enabled=self.camera_config is not None,
                    accessory_power_w=accessory)
                active_fraction = (self._telemetry["power_w"]/self._telemetry["requested_power_w"]
                                   if self._telemetry["requested_power_w"] > 0 else 0.0)
                self._telemetry["servo_power_w"] += motor_power * active_fraction
                # A cutoff disables the next whole 2 ms step, including partial depletion.
                if not self._telemetry["powered"]:
                    torque[:] = 0
                for key in averages:
                    averages[key] += self._telemetry[key]/c.substeps
            d.ctrl[:] = torque
            self._positive_work_j += float(np.maximum(torque*d.qvel[6:], 0).sum()*c.physics_dt_s)
            self._negative_work_j += float(np.maximum(-torque*d.qvel[6:], 0).sum()*c.physics_dt_s)
            self.mj.mj_step(self.model, d)
            if not np.isfinite(d.qpos).all() or not np.isfinite(d.qvel).all() or any(w.number for w in d.warning):
                d.ctrl[:] = 0
                self._faulted = True
                raise RuntimeError("MuJoCo numerical fault; reset required")
            if any(command.values()):
                self._phase = (self._phase+c.physics_dt_s/c.cycle_s) % 1
        if self.energy_config.enabled:
            self._telemetry.update(averages)
        self._tick += 1
        self._distance += float(np.linalg.norm(d.qpos[:2]-old_xy))
        self.peripherals.advance(powered=not self.energy_config.enabled or self._telemetry["powered"])
        self.mj.mj_forward(self.model, d)
        self._cache()

    def _rays(self, origin, directions):
        directions = np.ascontiguousarray(directions, dtype=np.float64).reshape(-1, 3)
        ids = np.full(len(directions), -1, dtype=np.int32)
        distances = np.full(len(directions), -1.0)
        self.mj.mj_multiRay(self.model, self.data, np.asarray(origin, dtype=np.float64), directions.ravel(),
            np.array([1, 0, 0, 0, 0, 0], dtype=np.uint8), 1, -1, ids, distances, len(ids), 100.0)
        return ids, distances

    def _cache(self):
        d, r = self.data, self.range_config
        rotation = d.xmat[self._body_id].reshape(3, 3)
        position = d.xpos[self._body_id]
        origin = position + rotation @ np.array((r.offset_forward_m, 0, r.mount_height_m))
        direction = rotation[:, 0]
        _, distances = self._rays(origin, [direction])
        truth = float(distances[0])
        value, status = None, "out_of_range"
        if 0 <= truth < r.minimum_m:
            status = "too_close"
        elif r.minimum_m <= truth <= r.maximum_m:
            if r.dropout_probability and self._rng.random(site="picrawler.range.dropout") < r.dropout_probability:
                status = "dropout"
            else:
                noise = (2*self._rng.random(site="picrawler.range.noise")-1)*r.noise_half_width_m if r.noise_half_width_m else 0
                candidate = truth+noise
                if candidate < r.minimum_m:
                    status = "too_close"
                elif candidate <= r.maximum_m:
                    value, status = candidate, "ok"
        self._sensor_debug = dict(origin=origin.tolist(), direction=direction.tolist(), distance_m=value,
            truth_distance_m=truth if truth >= 0 else None, max_range_m=r.maximum_m, status=status)
        readings = dict(ultrasonic=dict(distance_m=value, status=status))
        if self.camera_config is not None:
            c = self.camera_config
            focal = c.width/(2*math.tan(c.horizontal_fov_rad/2))
            u, v = np.meshgrid(np.arange(c.width)+0.5, np.arange(c.height)+0.5)
            vectors = np.stack((np.ones_like(u), -(u-c.width/2)/focal, -(v-c.height/2)/focal), axis=-1).reshape(-1, 3)
            vectors /= np.linalg.norm(vectors, axis=1)[:, None]
            vectors = vectors @ rotation.T
            camera_origin = position + rotation @ np.array((c.offset_forward_m, 0, c.mount_height_m))
            ids, depths = self._rays(camera_origin, vectors)
            rgb = np.tile(np.array([189, 210, 222], dtype=np.uint8), (len(ids), 1))
            valid = ids >= 0
            rgb[valid] = np.clip(self.model.geom_rgba[ids[valid], :3]*255, 0, 255).astype(np.uint8)
            floor = ids == self.model.geom("floor").id
            floor_points = camera_origin+vectors[floor]*depths[floor, None]
            checker = (np.floor(floor_points[:, 0]/0.1)+np.floor(floor_points[:, 1]/0.1)) % 2
            rgb[floor] = np.where(checker[:, None] == 0, (214, 216, 211), (194, 200, 193))
            readings["camera"] = dict(encoding="rgb8", width=c.width, height=c.height, rgb=rgb.reshape(c.height, c.width, 3).tolist())
        if self.energy_config.enabled:
            readings["telemetry"] = copy.deepcopy(self._telemetry)
        readings["peripherals"] = self.peripherals.observe(self._telemetry["battery_voltage_v"] if self.energy_config.enabled else None,
            powered=not self.energy_config.enabled or self._telemetry["powered"])
        self._readings = readings
        self._frame_cache = self._make_frame(rotation)

    def _make_frame(self, rotation):
        d = self.data
        contacts, supported, collision = [], set(), False
        for i in range(d.ncon):
            contact = d.contact[i]
            names = [self.mj.mj_id2name(self.model, self.mj.mjtObj.mjOBJ_GEOM, int(g)) for g in (contact.geom1, contact.geom2)]
            force = np.zeros(6)
            self.mj.mj_contactForce(self.model, d, i, force)
            contacts.append(dict(geoms=names, position=contact.pos.tolist(), normal_force_n=float(force[0])))
            feet = [name[:-5] for name in names if name.endswith("_foot")]
            if "floor" in names and feet and force[0] > 0:
                supported.update(feet)
            elif force[0] > 0:
                collision = True
        legs = []
        for i, leg in enumerate(LEG_ORDER):
            legs.append(dict(name=leg, points=[d.site_xpos[self.model.site(leg+"_"+s).id].tolist() for s in ("origin", "coxa", "knee", "toe")],
                joints_rad=dict(zip(("yaw_rad", "hip_rad", "knee_rad"), d.qpos[7+3*i:10+3*i].tolist())), stance=leg in supported))
        return dict(tick=self._tick, time_s=self.time_s,
            pose=dict(x_m=float(d.qpos[0]), y_m=float(d.qpos[1]), yaw_rad=math.atan2(rotation[1, 0], rotation[0, 0]), height_m=float(d.qpos[2])),
            legs=legs, sensor=copy.deepcopy(self._sensor_debug), collision=collision, workspace_limited=False,
            distance_travelled_m=self._distance, command=self._command.copy(),
            dynamics=dict(engine=ENGINE_VERSION, model_sha256=model_digest(self.xml), quaternion_wxyz=d.qpos[3:7].tolist(),
                root_velocity=d.qvel[:6].tolist(), upright_cosine=float(rotation[2, 2]), contacts=contacts,
                torque_nm=d.actuator_force.tolist(), targets_rad=self._targets.tolist(),
                positive_work_j=self._positive_work_j, negative_work_j=self._negative_work_j,
                fallen=bool(rotation[2, 2] < math.cos(math.pi/4) or d.qpos[2] < 0.035)),
            telemetry=copy.deepcopy(self._telemetry) if self.energy_config.enabled else None,
            needs=need_signals(self._telemetry, self.energy_config) if self.energy_config.enabled else {},
            peripherals=copy.deepcopy(self._readings["peripherals"]), peripheral_events=copy.deepcopy(self.peripherals.events),
            **(dict(camera_rgb=copy.deepcopy(self._readings["camera"]["rgb"])) if self.camera_config is not None else {}))

    def frame(self, *, include_camera=True):
        result = copy.deepcopy(self._frame_cache)
        if not include_camera:
            result.pop("camera_rgb", None)
        return result

    def snapshot(self):
        if self._faulted:
            raise RuntimeError("Cannot resume a faulted integration; reset required")
        state = np.empty(self.mj.mj_stateSize(self.model, self._state_spec))
        self.mj.mj_getState(self.model, self.data, state, self._state_spec)
        return copy.deepcopy(dict(type="psi_gw.picrawler.mujoco", version=1, engine=ENGINE_VERSION,
            model_sha256=model_digest(self.xml), world=self.world.snapshot(), geometry=asdict(self.geometry), config=asdict(self.config),
            range_config=asdict(self.range_config), camera_config=asdict(self.camera_config) if self.camera_config else None,
            energy_config=asdict(self.energy_config), initial_pose=list(self.initial_pose), seed=self._seed,
            tick=self._tick, phase=self._phase, targets=self._targets.tolist(), command=self._command, relaxed=self._relaxed,
            state=state.tolist(), rng=self._rng.snapshot(), energy=asdict(self._energy), environment=asdict(self._environment),
            telemetry=self._telemetry, peripherals=self.peripherals.snapshot(), pending_buttons=[list(e) for e in self._pending_buttons],
            distance=self._distance, positive_work_j=self._positive_work_j, negative_work_j=self._negative_work_j,
            readings=self._readings, sensor_debug=self._sensor_debug, frame_cache=self._frame_cache))

    @classmethod
    def restore(cls, payload):
        # JSON roundtrip rejects non-JSON values and all nonfinite numbers.
        p = json.loads(json.dumps(payload, allow_nan=False))
        if p.get("type") != "psi_gw.picrawler.mujoco" or p.get("version") != 1 or p.get("engine") != ENGINE_VERSION:
            raise ValueError("unsupported MuJoCo snapshot or engine version")
        obj = cls(world=World.restore(p["world"]), geometry=Geometry(**p["geometry"]), config=DynamicsConfig(**p["config"]),
                  range_config=RangeConfig(**p["range_config"]), camera_config=CameraConfig(**p["camera_config"]) if p["camera_config"] else None,
                  energy_config=EnergyConfig(**p["energy_config"]), seed=p["seed"], initial_pose=p["initial_pose"])
        if p.keys() != obj.snapshot().keys():
            raise ValueError("invalid snapshot fields")
        if p["model_sha256"] != model_digest(obj.xml):
            raise ValueError("snapshot model hash mismatch")
        state = np.asarray(p["state"], dtype=np.float64)
        if state.shape != (obj.mj.mj_stateSize(obj.model, obj._state_spec),):
            raise ValueError("invalid integration state size")
        if type(p["tick"]) is not int or p["tick"] < 0 or type(p["relaxed"]) is not bool:
            raise ValueError("invalid logical state")
        if type(p["phase"]) not in (int, float) or not 0 <= p["phase"] < 1 or len(p["targets"]) != 12:
            raise ValueError("invalid servo state")
        obj.mj.mj_setState(obj.model, obj.data, state, obj._state_spec)
        if not math.isclose(obj.data.time, p["tick"]*obj.config.dt_s, abs_tol=1e-8):
            raise ValueError("physics and logical clocks disagree")
        if not math.isclose(float(np.linalg.norm(obj.data.qpos[3:7])), 1.0, abs_tol=1e-10):
            raise ValueError("invalid root quaternion")
        if np.any(np.abs(obj.data.ctrl) > obj.config.torque_limit_nm):
            raise ValueError("invalid stored actuator control")
        obj.mj.mj_forward(obj.model, obj.data)
        # Forward regenerates derived values, then restore the saved warmstart too.
        obj.mj.mj_setState(obj.model, obj.data, state, obj._state_spec)
        obj._tick, obj._phase, obj._targets = p["tick"], p["phase"], np.array(p["targets"])
        obj._command = obj._parse_action(Action("drive", p["command"]))[0]
        if obj._command != p["command"]:
            raise ValueError("invalid stored command")
        obj._relaxed, obj._rng = p["relaxed"], restore_source(p["rng"])
        obj._energy, obj._environment = EnergyState(**p["energy"]), EnergyEnvironment(**p["environment"])
        obj._telemetry = p["telemetry"]
        obj.peripherals = PeripheralSim.restore(p["peripherals"])
        if obj.peripherals.tick != obj.tick:
            raise ValueError("peripheral and body clocks disagree")
        obj._pending_buttons = []
        for event in p["pending_buttons"]:
            obj.inject_button(*event)
        obj._distance, obj._positive_work_j, obj._negative_work_j = p["distance"], p["positive_work_j"], p["negative_work_j"]
        obj._readings, obj._sensor_debug, obj._frame_cache = p["readings"], p["sensor_debug"], p["frame_cache"]
        from .bridge import _observation
        _observation(asdict(obj.observe()))
        expected_peripherals = obj.peripherals.observe(
            obj._telemetry["battery_voltage_v"] if obj.energy_config.enabled else None,
            powered=not obj.energy_config.enabled or obj._telemetry["powered"])
        if obj._readings["peripherals"] != expected_peripherals:
            raise ValueError("inconsistent peripheral cache")
        if obj._frame_cache["tick"] != obj.tick or obj._frame_cache["time_s"] != obj.time_s:
            raise ValueError("inconsistent frame clock")
        if obj._frame_cache["sensor"] != obj._sensor_debug:
            raise ValueError("inconsistent sensor debug cache")
        for key in ("distance", "positive_work_j", "negative_work_j"):
            if finite(p[key], key) < 0:
                raise ValueError("negative cumulative state")
        limits = np.tile(np.array(JOINT_LIMITS), (4, 1))
        if obj._targets.shape != (12,) or np.any(obj._targets < limits[:, 0]) or np.any(obj._targets > limits[:, 1]):
            raise ValueError("invalid stored servo targets")
        return obj
