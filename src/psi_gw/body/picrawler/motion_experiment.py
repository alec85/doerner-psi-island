"""Measure the unchanged model offline; ground truth never enters a controller."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import math
from pathlib import Path

import numpy as np

from psi_gw.body.base import Action
from .mujoco_body import MujocoBody
from .mujoco_model import DynamicsConfig,model_digest
from .motion_profile import AXES,fit_profile
from .validation_io import source_info,write_json


def measure(axis,sign,friction,phase,yaw,split):
    magnitude=((.03,.02,.3) if split=='development' else (.02,.015,.2))[axis]
    b=MujocoBody(config=DynamicsConfig(friction=friction),initial_pose=(0,0,yaw),camera_config=None)
    for _ in range(40):b.act(Action('stand'))
    b._phase=phase  # Experiment-controlled initial gait phase, no pose feedback.
    samples=[];positions=[];last_yaw=yaw;angle=yaw
    for i in range(120):
        b.act(Action('drive',{AXES[axis]:sign*magnitude}))
        f=b.frame(include_camera=False)
        current=f['pose']['yaw_rad'];angle+=math.remainder(current-last_yaw,2*math.pi);last_yaw=current
        co,si=math.cos(yaw),math.sin(yaw)
        x,y=b.data.qpos[:2]
        value=(co*x+si*y,-si*x+co*y,angle-yaw)[axis]
        positions.append(value)
        samples.append(dict(t_s=(i+1)*.05,axis_position=value,root_velocity=b.data.qvel[:6].tolist(),
                            fallen=f['dynamics']['fallen']))
    steady=float((positions[-1]-positions[39])/4/(sign*magnitude))
    lag=6-positions[-1]/(steady*sign*magnitude)
    start=b.data.qpos[:2].copy();start_angle=angle
    for _ in range(40):
        b.act(Action('stop'));current=b.frame()['pose']['yaw_rad'];angle+=math.remainder(current-last_yaw,2*math.pi);last_yaw=current
    return dict(split=split,axis=axis,sign=sign,command=sign*magnitude,friction=friction,phase=phase,initial_yaw=yaw,
        model_sha256=model_digest(b.xml),config=asdict(b.config),steady_gain=steady,effective_lag_s=lag,
        stop_distance_m=float(np.linalg.norm(b.data.qpos[:2]-start)),stop_angle_rad=angle-start_angle,
        stop_linear_speed=float(np.linalg.norm(b.data.qvel[:3])),stop_angular_speed=float(np.linalg.norm(b.data.qvel[3:6])),
        samples=samples)


def run(output):
    output=Path(output)
    if output.exists():raise FileExistsError('use a new output directory')
    output.mkdir(parents=True)
    provenance=source_info();rows=[]
    for split,frictions,phases in [('development',(.4,.8,1.2),(0,.5)),('validation',(.6,1.0),(.13,.63))]:
        for friction in frictions:
            for phase in phases:
                for axis in range(3):
                    for sign in (1,-1):
                        row=measure(axis,sign,friction,phase,.2 if phase<.5 else -.3,split);rows.append(row)
                        write_json(output/'measurements.json',dict(source=provenance,cases=rows),replace=True)
                        print(split,friction,phase,axis,sign,round(row['steady_gain'],4),flush=True)
        if split=='development':
            profile=fit_profile(rows,provenance['code_sha256'])
            write_json(output/'profile.json',profile.snapshot())
    validation=[r for r in rows if r['split']=='validation']
    errors=[]
    for r in validation:
        pred=profile.gain(r['axis'],r['sign'])
        lo,hi=profile.gain_bounds[2*r['axis']+(r['sign']<0)]
        errors.append(dict(axis=r['axis'],sign=r['sign'],gain=r['steady_gain'],predicted_gain=pred,
                           relative_error=abs(r['steady_gain']/pred-1),inside_empirical_bounds=bool(lo<=r['steady_gain']<=hi)))
    summary=dict(source=provenance,development_cases=36,validation_cases=24,profile_sha256=profile.sha256,
        validation=errors,validation_inside=sum(r['inside_empirical_bounds'] for r in errors),
        maximum_relative_error=max(r['relative_error'] for r in errors),
        falls=sum(any(s['fallen'] for s in r['samples']) for r in rows))
    write_json(output/'summary.json',summary)
    print('completed',summary['validation_inside'],'/24 inside empirical bounds',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    run(parser.parse_args().output)
