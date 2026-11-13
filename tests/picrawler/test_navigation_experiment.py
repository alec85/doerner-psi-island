"""Real physical episode continuation includes navigator, buffers and profile."""
import json
import subprocess
import sys

import pytest

pytest.importorskip('mujoco')
from psi_gw.body.picrawler.motion_profile import MotionProfile
from psi_gw.body.picrawler.navigation_experiment import NavigationCase,NavigationEpisode


def profile():return MotionProfile((.9,)*6,((.8,1.),)*6,.1,.01,'a'*64)


@pytest.mark.parametrize('sensors',['nominal','noisy','delayed'])
def test_episode_resume_matches_every_following_tick(sensors):
    e=NavigationEpisode(NavigationCase(10,'slalom','active',sensors,max_ticks=35),profile())
    for _ in range(12):assert e.step()
    c=NavigationEpisode.restore(json.loads(json.dumps(e.snapshot())))
    while e.step():
        assert c.step()
        assert e.snapshot()==c.snapshot()
    assert not c.step()
    e.settle();c.settle()
    assert e.result()==c.result() and not e.result()['goal_within_900']


def test_fresh_process_resume_is_exact(tmp_path):
    e=NavigationEpisode(NavigationCase(10,'slalom','active','delayed',max_ticks=45),profile())
    for _ in range(20):e.step()
    start=tmp_path/'checkpoint.json';end=tmp_path/'result.json'
    start.write_text(json.dumps(e.snapshot()))
    subprocess.run([sys.executable,'-m','psi_gw.body.picrawler.navigation_experiment','--resume',str(start),'--output',str(end)],check=True)
    while e.step():pass
    e.settle()
    assert json.load(open(end))==json.loads(json.dumps(e.result()))


def test_profile_hash_mismatch_is_rejected():
    e=NavigationEpisode(NavigationCase(10,'open','active','nominal',max_ticks=5),profile())
    p=e.snapshot();p['profile_sha256']='0'*64
    with pytest.raises(ValueError,match='profile hash'):NavigationEpisode.restore(p)


@pytest.mark.parametrize('policy',['reactive','memory'])
def test_legacy_baseline_physics_and_controller_are_unchanged(policy):
    from psi_gw.body.picrawler.mujoco_experiment import DynamicCase,DynamicEpisode
    old=DynamicEpisode(DynamicCase(10,'slalom',policy,'delayed',max_ticks=25))
    new=NavigationEpisode(NavigationCase(10,'slalom',policy,'delayed',max_ticks=25),profile())
    for _ in range(25):
        assert old.step() and new.step()
        assert old.body.snapshot()==new.body.snapshot()
        assert old.controller.snapshot()==new.controller.snapshot()
        assert old.delivery.snapshot()==new.delivery.snapshot()
