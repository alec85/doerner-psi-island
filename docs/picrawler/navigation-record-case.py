"""Re-record one frozen report case and require exact result reproduction."""
import argparse
import copy

from psi_gw.body.picrawler.motion_profile import MotionProfile
from psi_gw.body.picrawler.navigation_experiment import NavigationCase,NavigationEpisode
from psi_gw.body.picrawler.visual_experiment import VisualEpisode
from psi_gw.body.picrawler.mujoco_experiment import metadata
from psi_gw.body.picrawler.replay import write_replay
from psi_gw.body.picrawler.validation_io import read_json,write_json

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',required=True);p.add_argument('--id',required=True);p.add_argument('--profile',required=True);p.add_argument('--output',required=True);p.add_argument('--check',required=True);a=p.parse_args()
original=next(r for r in read_json(a.report)['cases'] if r['id']==a.id)
profile=MotionProfile.restore(read_json(a.profile));variant=original.get('variant')
e=(VisualEpisode if variant=='visual' else NavigationEpisode)(NavigationCase(**original['case']),profile)
frames=[e.frame()]
while e.step():
    if e.steps%20==0:frames.append(e.frame())
e.settle();frames.append(e.frame());result=e.result()
if variant is not None:result.update(id=variant+'-'+e.case.id,variant=variant)
if variant=='visual':result.update(visual_updates=e.controller.visual_updates,visual_attempts=e.controller.visual_attempts)
assert result==original,'frozen case did not reproduce exactly'
write_replay(a.output,frames,metadata(e.body,'MuJoCo: reproduzierter Prüffehlschlag'))
write_json(a.check,dict(id=a.id,exact_result=True,body_sha256=result['body_sha256'],trace_sha256=result['trace_sha256'],frames=len(frames)))
print('Exact failure case reproduced',a.id,len(frames),flush=True)
