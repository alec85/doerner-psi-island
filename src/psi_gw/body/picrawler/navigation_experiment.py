"""Paired navigation evaluator; truth is confined to this module.

The 900-decision endpoint remains separate from the 2400-decision diagnostic.
"""
from __future__ import annotations

import argparse
import copy
from dataclasses import asdict,dataclass
import json
import math
from pathlib import Path

from psi_gw.body.base import Action
from .active_navigation import ActiveNavigator
from .motion_profile import MotionProfile
from .mujoco_body import MujocoBody
from .mujoco_experiment import DynamicCase,DynamicEpisode,metadata
from .replay import write_replay
from .robot_benchmark import DeliveryBuffer
from .robot_controllers import ReferenceController,ControllerConfig
from .validation_io import digest,read_json,source_info,write_json


@dataclass(frozen=True)
class NavigationCase:
    seed:int
    family:str
    policy:str
    sensors:str
    max_ticks:int=2400

    def __post_init__(self):
        DynamicCase(self.seed,self.family,'memory' if self.policy in ('active','fast_memory') else self.policy,self.sensors,self.max_ticks)
        if self.policy not in ('reactive','memory','fast_memory','active'):raise ValueError('invalid navigation policy')

    @property
    def id(self):return f's{self.seed}-{self.family}-{self.policy}-{self.sensors}-t{self.max_ticks}'


class NavigationEpisode(DynamicEpisode):
    def __init__(self,case,profile):
        super().__init__(DynamicCase(case.seed,case.family,'memory' if case.policy in ('active','fast_memory') else case.policy,case.sensors,case.max_ticks))
        self.case=case
        if case.policy=='active':self.controller=ActiveNavigator(profile)
        elif case.policy=='fast_memory':self.controller=ReferenceController('memory',seed=case.seed+20000,config=ControllerConfig(speed_mps=.03))
        self.profile_sha256=profile.sha256
        self.endpoint_900=None
        self.mode_counts={};self.scan_starts=0;self.last_scan_start=-10000
        self.initial_pose=self.body.data.qpos[:3].tolist()+[self.body.frame()['pose']['yaw_rad']]
        self.trace=digest(dict(case=asdict(case),model=self.body.frame()['dynamics']['model_sha256'],profile=profile.sha256))

    def step(self):
        progressed=super().step()
        if progressed:
            mode=self.controller.last_decision['mode'];self.mode_counts[mode]=self.mode_counts.get(mode,0)+1
            if self.case.policy=='active' and self.controller.last_scan_tick!=self.last_scan_start:
                self.scan_starts+=1;self.last_scan_start=self.controller.last_scan_tick
        if progressed and (self.steps==900 or (self.outcome is not None and self.endpoint_900 is None)):
            self.endpoint_900=dict(steps=self.steps,outcome=self.outcome or 'continuing',goal=self.outcome=='goal',
                pose=copy.deepcopy(self.body.frame()['pose']),contact_ticks=self.contact_ticks,
                path_length_m=self.body.frame()['distance_travelled_m'],energy_consumed_j=self.body.frame()['telemetry']['energy_consumed_j'])
        return progressed

    def frame(self):
        frame=self.body.frame()
        frame['navigation']=copy.deepcopy(self.controller.last_decision)
        return frame

    def result(self):
        result=super().result()
        result.update(profile_sha256=self.profile_sha256,endpoint_900=self.endpoint_900,mode_counts=self.mode_counts.copy(),scan_starts=self.scan_starts,
                      path_length_m=self.body.frame()['distance_travelled_m'],
                      goal_within_900=self.outcome=='goal' and self.steps<=900,
                      goal_within_long_horizon=self.outcome=='goal')
        if self.case.policy=='active':
            x0,y0,_,yaw0=self.initial_pose
            dx,dy=self.body.data.qpos[0]-x0,self.body.data.qpos[1]-y0
            actual=(math.cos(yaw0)*dx+math.sin(yaw0)*dy,-math.sin(yaw0)*dx+math.cos(yaw0)*dy)
            # Controller has not observed the final 40 stop ticks; compare before stop via saved estimate.
            result['estimate_error_after_stop_m']=math.dist(self.controller.position,actual)
            result['heading_error_after_stop_rad']=math.remainder(result['pose']['yaw_rad']-yaw0-self.controller.heading,2*math.pi)
            result['estimated_position']=self.controller.position.copy()
        return result

    def snapshot(self):
        p=super().snapshot()
        p.update(schema='psi_gw.picrawler.navigation_episode.v1',profile_sha256=self.profile_sha256,
                 endpoint_900=copy.deepcopy(self.endpoint_900),initial_pose=self.initial_pose,mode_counts=self.mode_counts.copy(),scan_starts=self.scan_starts,last_scan_start=self.last_scan_start)
        return p

    @classmethod
    def restore(cls,p):
        if p['schema']!='psi_gw.picrawler.navigation_episode.v1':raise ValueError('unsupported navigation checkpoint')
        obj=cls.__new__(cls);obj.case=NavigationCase(**p['case']);obj.body=MujocoBody.restore(p['body'])
        obj.controller=(ActiveNavigator.restore(p['controller']) if obj.case.policy=='active' else ReferenceController.restore(p['controller']))
        obj.delivery=DeliveryBuffer.restore(p['delivery']);obj.previous=Action(**p['previous'])
        obj.steps,obj.contact_ticks,obj.outcome,obj.rest,obj.trace=(copy.deepcopy(p[k]) for k in ('steps','contact_ticks','outcome','rest','trace'))
        obj.profile_sha256=p['profile_sha256'];obj.endpoint_900=copy.deepcopy(p['endpoint_900']);obj.initial_pose=p['initial_pose']
        obj.mode_counts=copy.deepcopy(p['mode_counts']);obj.scan_starts=p['scan_starts'];obj.last_scan_start=p['last_scan_start']
        if obj.body.tick!=obj.steps+40+(40 if obj.rest is not None else 0):raise ValueError('episode clocks disagree')
        if obj.case.policy=='active' and obj.profile_sha256!=obj.controller.profile.sha256:raise ValueError('profile hash mismatch')
        return obj


def episode(case,profile,output,record=False,checkpoint=False):
    e=NavigationEpisode(case,profile);frames=[e.frame()] if record else []
    while e.step():
        if record and e.steps%20==0:frames.append(e.frame())
        if checkpoint and e.steps==250:write_json(output/(case.id+'-checkpoint.json'),e.snapshot())
    e.settle()
    if record:
        frames.append(e.frame());meta=metadata(e.body,'MuJoCo: '+case.policy+' / '+case.family+' / '+case.sensors)
        meta['profile_sha256']=profile.sha256
        write_replay(output/(case.id+'.html'),frames,meta)
    return e.result()


def run(output,profile_path,split,seeds=None,policies=None):
    output=Path(output)
    if output.exists():raise FileExistsError('use a new output directory')
    output.mkdir(parents=True)
    profile=MotionProfile.restore(read_json(profile_path))
    seeds=(10,11) if seeds is None and split=='development' else ((2000,2001) if seeds is None else seeds)
    if split=='development' and any(s not in (10,11) for s in seeds):raise ValueError('development seed not permitted')
    if split=='validation' and any(s not in (2000,2001) for s in seeds):raise ValueError('validation seed not permitted')
    provenance=dict(schema='psi_gw.picrawler.navigation.v1',source=source_info(),split=split,profile_sha256=profile.sha256,
                    endpoint_ticks=900,long_horizon_ticks=2400)
    write_json(output/'provenance.json',provenance);rows=[]
    for seed in seeds:
        for family in ('open','slalom'):
            for sensors in ('nominal','noisy','delayed'):
                for policy in (policies or ('reactive','memory','fast_memory','active')):
                    case=NavigationCase(seed,family,policy,sensors)
                    row=episode(case,profile,output,record=(policy=='active' and seed==seeds[0]),
                                checkpoint=(policy=='active' and family=='slalom' and seed==seeds[0]))
                    rows.append(row);write_json(output/'results.json',dict(**provenance,cases=rows),replace=True)
                    print(case.id,row['outcome'],row['steps'],'contacts',row['contact_ticks'],flush=True)
    summary=dict(**provenance,cases=len(rows),policies={p:dict(cases=sum(r['case']['policy']==p for r in rows),
        goals_900=sum(r['goal_within_900'] for r in rows if r['case']['policy']==p),
        goals_2400=sum(r['goal_within_long_horizon'] for r in rows if r['case']['policy']==p),
        stop_passed=sum(r['stop_pass'] for r in rows if r['case']['policy']==p),
        outcomes={k:sum(r['case']['policy']==p and r['outcome']==k for r in rows) for k in sorted({r['outcome'] for r in rows})})
        for p in sorted({r['case']['policy'] for r in rows})})
    write_json(output/'summary.json',summary)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--profile',type=Path);parser.add_argument('--split',choices=['development','validation'],default='development')
    parser.add_argument('--seeds',nargs='+',type=int);parser.add_argument('--policies',nargs='+',choices=['active','reactive','memory','fast_memory'])
    parser.add_argument('--resume',type=Path);args=parser.parse_args()
    if args.resume:
        e=NavigationEpisode.restore(read_json(args.resume))
        while e.step():pass
        e.settle();write_json(args.output,e.result())
    else:
        if args.profile is None:parser.error('--profile required')
        run(args.output,args.profile,args.split,args.seeds,args.policies)


if __name__=='__main__':main()
