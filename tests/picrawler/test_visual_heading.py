"""Pinhole fixture registration and complete visual-state continuation."""
import copy
import json
import math
import subprocess
import sys

import numpy as np
import pytest

from psi_gw.body.base import Action,Observation
from psi_gw.body.picrawler.motion_profile import MotionProfile
from psi_gw.body.picrawler.visual_heading import VisualNavigator,match_yaw


def profile():return MotionProfile((.9,)*6,((.8,1.),)*6,.1,.01,'a'*64)


def scene(delta=0):
    w,h=16,12;row=np.empty((w,3));row[:]=[190,200,210];row[:5]=[220,30,20];row[10:]=[25,70,230]
    focal=w/(2*math.tan(math.pi/6));x=np.arange(w);angles=np.arctan((w/2-(x+.5))/focal)
    source=w/2-focal*np.tan(angles+delta)-.5
    warped=np.stack([np.interp(source,x,row[:,i]) for i in range(3)],axis=1)
    return dict(encoding='rgb8',width=w,height=h,rgb=np.tile(warped,(h,1,1)).tolist())


@pytest.mark.parametrize('delta',[-.15,-.08,0,.08,.15])
def test_known_pinhole_rotations_are_recovered(delta):
    result=match_yaw(scene(),scene(delta))
    assert result is not None
    assert result['delta_yaw_rad']==pytest.approx(delta,abs=.0051)


def test_uniform_or_invalid_images_do_not_invent_orientation():
    uniform=dict(rgb=[[[200,200,200]]*16 for _ in range(12)])
    assert match_yaw(uniform,uniform) is None
    bad=scene();bad['width']=99
    assert match_yaw(scene(),bad) is None


def test_visual_update_uses_capture_time_and_normalizes_saved_state():
    n=VisualNavigator(profile());n.last_tick=10;n.heading=.2
    n.history=[dict(t=.4,x=0,y=0,heading=.05),dict(t=.5,x=0,y=0,heading=.2)]
    n.visual_reference=dict(sample=scene(),position=[0,0],heading=0,t=0)
    n.visual_camera=dict(sample=scene(.08),t=.4)
    correction=n._align()
    assert correction==pytest.approx(.03,abs=.0051)
    assert n.heading==pytest.approx(.23,abs=.0051)  # not simply the old capture heading
    assert n.visual_updates==1
    saved=n.snapshot();assert VisualNavigator.restore(json.loads(json.dumps(saved))).snapshot()==saved


def test_bad_predecessor_does_not_mutate_visual_cache():
    n=VisualNavigator(profile());o=Observation(0,dict(ultrasonic=dict(status='ok',distance_m=1.6)),dict(hunger=0,damage=0));n.choose(o)
    before=n.snapshot()
    with pytest.raises(ValueError):n.choose(Observation(2,o.sensors,o.internal),n.last_action)
    assert n.snapshot()==before


def test_visual_episode_fresh_process_resume(tmp_path):
    pytest.importorskip('mujoco')
    from psi_gw.body.picrawler.visual_experiment import VisualEpisode
    from psi_gw.body.picrawler.navigation_experiment import NavigationCase
    e=VisualEpisode(NavigationCase(10,'slalom','active','delayed',max_ticks=300),profile())
    for _ in range(260):e.step()
    start=tmp_path/'checkpoint.json';end=tmp_path/'result.json'
    start.write_text(json.dumps(dict(variant='visual',episode=e.snapshot())))
    subprocess.run([sys.executable,'-m','psi_gw.body.picrawler.visual_experiment','--resume',str(start),'--output',str(end)],check=True)
    while e.step():pass
    e.settle();row=e.result();row.update(id='visual-'+e.case.id,variant='visual',visual_updates=e.controller.visual_updates,visual_attempts=e.controller.visual_attempts)
    assert json.loads(json.dumps(row))==json.load(open(end))


def test_translation_gate_does_not_interpret_motion_as_yaw():
    n=VisualNavigator(profile());n.position=[.06,0]
    n.visual_reference=dict(sample=scene(),position=[0,0],heading=0,t=0)
    n.visual_camera=dict(sample=scene(.1),t=0)
    assert n._align() is None and n.visual_updates==0


def test_truth_fields_cannot_affect_visual_controller():
    a,b=VisualNavigator(profile()),VisualNavigator(profile())
    camera=scene();camera['captured_at_s']=0
    clean=Observation(0,dict(ultrasonic=dict(status='ok',distance_m=1.6),camera=camera),dict(hunger=0,damage=0))
    dirty=copy.deepcopy(clean);dirty.sensors.update(world={'pose':999},collision=True,goal=.35)
    assert a.choose(clean)==b.choose(dirty) and a.snapshot()==b.snapshot()
