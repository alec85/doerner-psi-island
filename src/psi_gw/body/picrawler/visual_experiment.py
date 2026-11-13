"""Separate preregistered camera-heading trial against frozen active v1."""
from __future__ import annotations

import argparse
import copy
from dataclasses import asdict
from pathlib import Path

from .motion_profile import MotionProfile
from .navigation_experiment import NavigationCase,NavigationEpisode
from .visual_heading import VisualNavigator
from .mujoco_experiment import metadata
from .replay import write_replay
from .validation_io import read_json,write_json,source_info


class VisualEpisode(NavigationEpisode):
    def __init__(self,case,profile):
        super().__init__(case,profile);self.controller=VisualNavigator(profile)

    @classmethod
    def restore(cls,p):
        copy_payload=copy.deepcopy(p);visual=VisualNavigator.restore(copy_payload['controller'])
        copy_payload['controller']=visual.snapshot()['base']
        base=NavigationEpisode.restore(copy_payload);obj=cls.__new__(cls);obj.__dict__.update(base.__dict__);obj.controller=visual
        return obj


def run(output,profile_path,split,seeds=None):
    output=Path(output)
    if output.exists():raise FileExistsError('use a new output directory')
    output.mkdir(parents=True)
    profile=MotionProfile.restore(read_json(profile_path))
    allowed=(10,11) if split=='development' else (3000,3001)
    seeds=allowed if seeds is None else seeds
    if any(s not in allowed for s in seeds):raise ValueError('seed does not belong to this split')
    provenance=dict(schema='psi_gw.picrawler.visual_navigation.v1',split=split,source=source_info(),profile_sha256=profile.sha256)
    write_json(output/'provenance.json',provenance);rows=[]
    variants=('visual',) if split=='development' else ('active_v1','visual')
    for seed in seeds:
        for family in ('open','slalom'):
            for sensors in ('nominal','noisy','delayed'):
                for variant in variants:
                    case=NavigationCase(seed,family,'active',sensors)
                    e=(VisualEpisode if variant=='visual' else NavigationEpisode)(case,profile)
                    record=seed==seeds[0] and variant=='visual';frames=[e.frame()] if record else []
                    name=variant+'-'+case.id
                    while e.step():
                        if record and e.steps%20==0:frames.append(e.frame())
                        if variant=='visual' and family=='slalom' and seed==seeds[0] and e.steps==250:
                            write_json(output/(name+'-checkpoint.json'),dict(variant=variant,episode=e.snapshot()))
                    e.settle();row=e.result();row.update(id=name,variant=variant)
                    if variant=='visual':row.update(visual_updates=e.controller.visual_updates,visual_attempts=e.controller.visual_attempts)
                    rows.append(row);write_json(output/'results.json',dict(**provenance,cases=rows),replace=True)
                    if record:frames.append(e.frame());write_replay(output/(name+'.html'),frames,metadata(e.body,'MuJoCo: '+variant+' / '+family+' / '+sensors))
                    print(name,row['outcome'],row['steps'],row['contact_ticks'],row.get('visual_updates'),flush=True)
    summary=dict(**provenance,cases=len(rows),variants={v:dict(cases=sum(r['variant']==v for r in rows),
        goals_900=sum(r['goal_within_900'] for r in rows if r['variant']==v),goals_2400=sum(r['goal_within_long_horizon'] for r in rows if r['variant']==v),
        stop_passed=sum(r['stop_pass'] for r in rows if r['variant']==v),outcomes={k:sum(r['variant']==v and r['outcome']==k for r in rows) for k in sorted({r['outcome'] for r in rows})}) for v in variants})
    write_json(output/'summary.json',summary)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);p.add_argument('--profile',type=Path)
    p.add_argument('--split',choices=['development','validation'],default='development');p.add_argument('--seeds',nargs='+',type=int);p.add_argument('--resume',type=Path);a=p.parse_args()
    if a.resume:
        payload=read_json(a.resume);e=VisualEpisode.restore(payload['episode'])
        while e.step():pass
        e.settle();r=e.result();r.update(id=payload['variant']+'-'+e.case.id,variant=payload['variant'],visual_updates=e.controller.visual_updates,visual_attempts=e.controller.visual_attempts)
        write_json(a.output,r)
    else:
        if a.profile is None:p.error('--profile required')
        run(a.output,a.profile,a.split,a.seeds)


if __name__=='__main__':main()
