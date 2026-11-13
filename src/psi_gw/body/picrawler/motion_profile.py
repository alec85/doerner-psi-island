"""Offline-identified command response; deliberately not measured odometry.

Only the separate identification experiment may use model pose. This runtime
profile contains aggregate response coefficients and explicit empirical ranges.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any

from .validation_io import digest
from .world import finite

AXES = ('forward_mps','lateral_mps','yaw_rps')


@dataclass(frozen=True)
class MotionProfile:
    gains: tuple[float, ...]
    gain_bounds: tuple[tuple[float,float], ...]
    response_time_s: float
    stop_distance_m: float
    source_sha256: str
    engine: str = '3.3.7'
    version: int = 1

    def __post_init__(self):
        if len(self.gains)!=6 or len(self.gain_bounds)!=6 or type(self.version) is not int or self.version!=1 or self.engine!='3.3.7':
            raise ValueError('unsupported motion profile')
        for gain,bounds in zip(self.gains,self.gain_bounds):
            if len(bounds)!=2 or not 0 < finite(bounds[0],'gain lower') <= finite(gain,'gain') <= finite(bounds[1],'gain upper') < 3:
                raise ValueError('invalid empirical gain range')
        if not .01 <= finite(self.response_time_s,'response time') <= 2:
            raise ValueError('invalid response time')
        if not 0 <= finite(self.stop_distance_m,'stop distance') <= .2:
            raise ValueError('invalid stop distance')
        if not isinstance(self.source_sha256,str) or len(self.source_sha256)!=64:
            raise ValueError('profile requires source hash')
        object.__setattr__(self,'gains',tuple(float(v) for v in self.gains))
        object.__setattr__(self,'gain_bounds',tuple(tuple(float(v) for v in pair) for pair in self.gain_bounds))

    def gain(self,axis,value):
        return self.gains[2*axis+(1 if value<0 else 0)]

    @property
    def relative_uncertainty(self):
        return max((hi-lo)/gain for gain,(lo,hi) in zip(self.gains,self.gain_bounds))

    def response(self,velocity,command,dt_s):
        """First order mean response; no guarantee of real stopping distance."""
        dt=finite(dt_s,'dt_s')
        if dt<=0 or dt>.5: raise ValueError('invalid integration interval')
        if len(velocity)!=3 or not isinstance(command,dict) or command.keys()-set(AXES):
            raise ValueError('invalid response state or command')
        velocity=[finite(v,'velocity') for v in velocity]
        target=[finite(command.get(axis,0),axis) for axis in AXES]
        speed=math.hypot(*target[:2])
        if speed>.03: target[:2]=[v*.03/speed for v in target[:2]]
        target[2]=max(-.3,min(.3,target[2]))
        return [v+(self.gain(i,u)*u-v)*(-math.expm1(-dt/self.response_time_s)) for i,(v,u) in enumerate(zip(velocity,target))]

    def snapshot(self):
        return dict(type='psi_gw.picrawler.motion_profile',**asdict(self))

    @classmethod
    def restore(cls,p):
        p=dict(p)
        if p.pop('type',None)!='psi_gw.picrawler.motion_profile':raise ValueError('invalid profile type')
        return cls(**p)

    @property
    def sha256(self): return digest(self.snapshot())


def fit_profile(rows: list[dict[str,Any]],source_sha256: str) -> MotionProfile:
    if not rows or any(r.get('split')!='development' for r in rows):
        raise ValueError('fit requires development data only')
    gains=[];bounds=[]
    for axis in range(3):
        for sign in (1,-1):
            selected=[r for r in rows if r['axis']==axis and r['sign']==sign]
            if len(selected)<3:raise ValueError('insufficient repeated response measurements')
            values=sorted(r['steady_gain'] for r in selected)
            gains.append(sum(values)/len(values));bounds.append((min(values)*.95,max(values)*1.05))
    # Effective start lag is phase dependent; retain a bounded first-order mean.
    tau=max(.05,min(.5,sum(max(0,r['effective_lag_s']) for r in rows)/len(rows)))
    stop=max(r['stop_distance_m'] for r in rows)*1.25+.002
    return MotionProfile(tuple(gains),tuple(bounds),tau,stop,source_sha256)
