"""Versioned physical acceptance and sensor-only closed-loop experiments.

Criteria are fixed in docs/picrawler/MUJOCO-VALIDATION.md before validation.
This evaluator alone sees pose/contact truth. Neither reference policy does.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import math
import json
from pathlib import Path

import numpy as np

from psi_gw.body.base import Action
from .energy import EnergyConfig
from .mujoco_body import MujocoBody
from .mujoco_model import DynamicsConfig, ENGINE_VERSION, model_digest
from .replay import write_replay
from .robot_benchmark import DeliveryBuffer
from .robot_controllers import ReferenceController
from .robot_courses import generate_course
from .sensors import RangeConfig, CameraConfig
from .validation_io import digest, read_json, source_info, write_json


SCHEMA = "psi_gw.picrawler.mujoco.acceptance.v1"


def stopped(body, start):
    d = body.data
    return dict(linear_speed_m_s=float(np.linalg.norm(d.qvel[:3])),
                angular_speed_rad_s=float(np.linalg.norm(d.qvel[3:6])),
                drift_m=float(np.linalg.norm(d.qpos[:2]-start)))


def stop_pass(metrics):
    return (metrics['linear_speed_m_s'] <= .005 and metrics['angular_speed_rad_s'] <= .05
            and metrics['drift_m'] <= .03)


def metadata(body, title):
    return dict(title=title, backend="mujoco", engine=ENGINE_VERSION,
                model_sha256=model_digest(body.xml), seed=body._seed, dt_s=body.config.dt_s,
                world=body.world.snapshot(), source_commit=source_info()['revision'],
                assumptions="Angenommene Massen, Reibung, Servomomente und elektrische Verluste; keine Hardwarekalibrierung.")


def gait_case(yaw, friction, name, *, replay=None):
    commands = {'forward': {'forward_mps':.02}, 'backward': {'forward_mps':-.02},
                'left': {'lateral_mps':.015}, 'right': {'lateral_mps':-.015}, 'turn': {'yaw_rps':.15}}
    b = MujocoBody(config=DynamicsConfig(friction=friction), initial_pose=(0,0,yaw),
                   camera_config=CameraConfig(width=16,height=12))
    frames = [b.frame()]
    for i in range(40):
        b.act(Action('stand'))
        if i%10 == 9: frames.append(b.frame())
    stand = b.frame()
    stand_ok = (.06 <= b.data.qpos[2] <= .075 and not stand['dynamics']['fallen'] and
                np.linalg.norm(b.data.qvel[:3]) <= .001 and np.linalg.norm(b.data.qvel[3:6]) <= .01 and
                sum(leg['stance'] for leg in stand['legs']) == 4)
    start = b.data.qpos[:2].copy()
    fallen, peak_torque, peak_joint_speed = False, 0.0, 0.0
    for i in range(160):
        b.act(Action('drive',commands[name]))
        f = b.frame(include_camera=False)
        fallen |= f['dynamics']['fallen']
        peak_torque = max(peak_torque,float(np.max(np.abs(b.data.actuator_force))))
        peak_joint_speed = max(peak_joint_speed,float(np.max(np.abs(b.data.qvel[6:]))))
        if i%5 == 4: frames.append(b.frame())
    co, si = math.cos(yaw), math.sin(yaw)
    displacement = b.data.qpos[:2]-start
    body_delta = np.array([[co,si],[-si,co]]) @ displacement
    yaw_delta = math.remainder(b.frame()['pose']['yaw_rad']-yaw,2*math.pi)
    if name == 'turn':
        motion_ok = .5 <= yaw_delta <= 1.8 and np.linalg.norm(displacement) <= .05
        progress, cross = yaw_delta, float(np.linalg.norm(displacement))
    else:
        axis = 0 if name in ('forward','backward') else 1
        sign = -1 if name in ('backward','right') else 1
        progress, cross = float(sign*body_delta[axis]), float(abs(body_delta[1-axis]))
        lo, hi, cross_limit, yaw_limit = (.10,.22,.025,.12) if axis == 0 else (.07,.16,.04,.15)
        motion_ok = lo <= progress <= hi and cross <= cross_limit and abs(yaw_delta) <= yaw_limit
    stop_start = b.data.qpos[:2].copy()
    for i in range(40):
        b.act(Action('stop'))
        fallen |= b.frame(include_camera=False)['dynamics']['fallen']
        if i%5 == 4: frames.append(b.frame())
    rest = stopped(b, stop_start)
    result = dict(id=f'{name}-yaw{yaw}-friction{friction}', command=commands[name], yaw=yaw,
        friction=friction, model_sha256=model_digest(b.xml), config=asdict(b.config),
        stand_pass=bool(stand_ok), motion_pass=bool(motion_ok), stop_pass=bool(stop_pass(rest)),
        fallen=fallen, peak_torque_nm=peak_torque, sampled_peak_joint_speed_rad_s=peak_joint_speed,
        signed_progress=progress, cross_error_m=cross, yaw_delta_rad=yaw_delta, stop=rest,
        energy_consumed_j=b.observe().sensors['telemetry']['energy_consumed_j'])
    result['passed'] = bool(stand_ok and motion_ok and stop_pass(rest) and not fallen and peak_torque <= .35+1e-12)
    if replay:
        write_replay(replay,frames,metadata(b,"MuJoCo: "+name))
    return result


@dataclass(frozen=True)
class DynamicCase:
    seed: int
    family: str
    policy: str
    sensors: str
    max_ticks: int = 900

    def __post_init__(self):
        if (type(self.seed) is not int or self.seed < 0 or self.family not in ('open','slalom') or
            self.policy not in ('reactive','memory') or self.sensors not in ('nominal','noisy','delayed') or
            type(self.max_ticks) is not int or self.max_ticks < 1):
            raise ValueError('invalid dynamic benchmark case')

    @property
    def id(self):
        return f's{self.seed}-{self.family}-{self.policy}-{self.sensors}-t{self.max_ticks}'


class DynamicEpisode:
    def __init__(self, case: DynamicCase):
        self.case = case
        course = generate_course(case.seed,case.family)
        self.body = MujocoBody(world=course.world, seed=case.seed+10000,
            initial_pose=(course.initial_x_m,course.initial_y_m,course.initial_yaw_rad),
            camera_config=CameraConfig(width=16,height=12),
            range_config=RangeConfig(noise_half_width_m=.02 if case.sensors == 'noisy' else 0,
                                     dropout_probability=.08 if case.sensors == 'noisy' else 0))
        for _ in range(40): self.body.act(Action('stand'))
        self.controller = ReferenceController(case.policy,seed=case.seed+20000)
        self.delivery = DeliveryBuffer(case.sensors)
        self.previous = Action('stop')
        self.steps, self.contact_ticks = 0, 0
        self.outcome, self.rest = None, None
        self.trace = digest({'case':asdict(case),'model':model_digest(self.body.xml)})

    def step(self):
        if self.outcome is not None:
            return False
        observation = self.delivery.deliver(self.body.observe())
        action = self.controller.choose(observation,self.previous)
        self.body.act(action)
        self.previous = action
        self.steps += 1
        frame = self.body.frame(include_camera=False)
        self.contact_ticks += int(frame['collision'])
        self.trace = digest(dict(previous=self.trace,action=asdict(action),pose=frame['pose'],
                                 range=frame['sensor'],needs=frame['needs']))
        if frame['dynamics']['fallen']:
            self.outcome = 'fall'
        elif self.contact_ticks >= 25:
            self.outcome = 'contact_budget'
        elif not self.body.observe().sensors['telemetry']['powered']:
            self.outcome = 'power_off'
        elif frame['pose']['x_m'] >= .35:
            self.outcome = 'goal'
        elif self.steps >= self.case.max_ticks:
            self.outcome = 'timeout'
        return True

    def settle(self):
        if self.outcome is None:
            raise ValueError('episode is still running')
        if self.rest is None:
            start = self.body.data.qpos[:2].copy()
            for _ in range(40): self.body.act(Action('stop'))
            self.rest = stopped(self.body,start)
        return self.rest

    def result(self):
        if self.outcome is None or self.rest is None:
            raise ValueError('episode has not finished')
        frame = self.body.frame(include_camera=False)
        return dict(id=self.case.id,case=asdict(self.case),outcome=self.outcome,steps=self.steps,
                    contact_ticks=self.contact_ticks,pose=frame['pose'],stop=self.rest,
                    stop_pass=bool(stop_pass(self.rest) and not frame['dynamics']['fallen']),
                    energy_consumed_j=frame['telemetry']['energy_consumed_j'],trace_sha256=self.trace,
                    body_sha256=digest(self.body.snapshot()),model_sha256=model_digest(self.body.xml))

    def snapshot(self):
        return json.loads(json.dumps(dict(schema=SCHEMA,case=asdict(self.case),body=self.body.snapshot(),controller=self.controller.snapshot(),
                    delivery=self.delivery.snapshot(),previous=asdict(self.previous),steps=self.steps,
                    contact_ticks=self.contact_ticks,outcome=self.outcome,rest=self.rest,trace=self.trace), allow_nan=False))

    @classmethod
    def restore(cls,p):
        if p['schema'] != SCHEMA:
            raise ValueError('unsupported dynamic experiment snapshot')
        obj = cls.__new__(cls)
        obj.case = DynamicCase(**p['case'])
        obj.body = MujocoBody.restore(p['body'])
        obj.controller = ReferenceController.restore(p['controller'])
        obj.delivery = DeliveryBuffer.restore(p['delivery'])
        obj.previous = Action(**p['previous'])
        obj.steps,obj.contact_ticks,obj.outcome,obj.rest,obj.trace = (p[k] for k in ('steps','contact_ticks','outcome','rest','trace'))
        if obj.body.tick != obj.steps+40+(40 if obj.rest is not None else 0):
            raise ValueError('episode clocks disagree')
        return obj


def run(output):
    output = Path(output)
    if output.exists():
        raise FileExistsError('use a new output directory to preserve existing results')
    output.mkdir(parents=True)
    provenance = dict(schema=SCHEMA,source=source_info(),engine=ENGINE_VERSION,criteria='MUJOCO-VALIDATION.md v1')
    write_json(output/'provenance.json',provenance)
    gaits = []
    for yaw in (.3,-.4):
        for friction in (.4,.8,1.2):
            for name in ('forward','backward','left','right','turn'):
                replay = output/f'gait-{name}.html' if yaw == .3 and friction == .8 and name in ('forward','turn') else None
                row = gait_case(yaw,friction,name,replay=replay)
                gaits.append(row)
                write_json(output/'gaits.json',dict(**provenance,cases=gaits),replace=True)
                print(row['id'], 'pass' if row['passed'] else 'FAIL',flush=True)
    results = []
    for seed in (1000,1001):
        for family in ('open','slalom'):
            for policy in ('reactive','memory'):
                for sensors in ('nominal','noisy','delayed'):
                    case = DynamicCase(seed,family,policy,sensors)
                    episode = DynamicEpisode(case)
                    frames = [episode.body.frame()]
                    save_checkpoint = seed == 1000 and family == 'slalom' and policy == 'memory'
                    record = save_checkpoint and sensors == 'delayed'
                    while episode.step():
                        if record and episode.steps%10 == 0:
                            frames.append(episode.body.frame())
                        if save_checkpoint and episode.steps == 150:
                            write_json(output/f'checkpoint-{sensors}.json',episode.snapshot())
                    episode.settle()
                    if record:
                        frames.append(episode.body.frame())
                        write_replay(output/'closed-loop.html',frames,metadata(episode.body,'MuJoCo: sensorbeschränkter Slalom'))
                    row = episode.result(); results.append(row)
                    write_json(output/'closed-loop.json',dict(**provenance,cases=results),replace=True)
                    print(row['id'],row['outcome'],row['steps'],flush=True)
    summary = dict(**provenance,gait_cases=len(gaits),gait_passed=sum(r['passed'] for r in gaits),
                   benchmark_cases=len(results),outcomes={k:sum(r['outcome']==k for r in results) for k in sorted({r['outcome'] for r in results})},
                   stop_passed=sum(r['stop_pass'] for r in results))
    write_json(output/'summary.json',summary)
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--resume',type=Path)
    args=parser.parse_args()
    if args.resume:
        if args.output is None: parser.error('--resume requires --output')
        episode=DynamicEpisode.restore(read_json(args.resume))
        while episode.step(): pass
        episode.settle()
        write_json(args.output,episode.result())
    elif args.output:
        run(args.output)
    else:
        parser.error('--output is required')


if __name__ == '__main__':
    main()
