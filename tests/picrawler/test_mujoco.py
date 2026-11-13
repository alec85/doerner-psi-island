"""Executed physical invariants, state continuation and unchanged sensor boundary."""
import copy
from dataclasses import asdict
import json
import math
import os
import subprocess
import sys

import numpy as np
import pytest

from psi_gw.body.base import Action
from psi_gw.body.picrawler.kinematics import (Geometry, JointAngles, LEG_ORDER, leg_points, leg_to_body)
from psi_gw.body.picrawler.mujoco_model import DynamicsConfig, model_xml

mujoco = pytest.importorskip("mujoco")
from psi_gw.body.picrawler.mujoco_body import MujocoBody
from psi_gw.body.picrawler.sensors import RangeConfig, CameraConfig
from psi_gw.body.picrawler.energy import EnergyConfig


def body(**kwargs):
    return MujocoBody(camera_config=None, **kwargs)


@pytest.mark.parametrize('angles', [(0, .3, -1.5), (.6, -.5, -2.2), (-.8, 1.2, -.3)])
def test_mjcf_sites_match_independent_forward_kinematics(angles):
    b = body()
    b.data.qpos[7:] = list(angles)*4
    mujoco.mj_forward(b.model, b.data)
    for leg in LEG_ORDER:
        for suffix, point in zip(('origin', 'coxa', 'knee', 'toe'), leg_points(JointAngles(*angles))):
            expected = np.array(leg_to_body(leg, point)) + b.data.qpos[:3]
            np.testing.assert_allclose(b.data.site_xpos[b.model.site(leg+'_'+suffix).id], expected, atol=1e-14)
    assert (b.model.nq, b.model.nv, b.model.nu) == (19, 18, 12)
    assert b.model.body_mass.sum() == pytest.approx(.602)


def test_gravity_and_contact_are_physical_not_frozen_pose():
    b = body()
    initial = b.data.qpos[2]
    for _ in range(40):
        b.act(Action('relax'))
    assert b.data.qpos[2] < initial-.015
    assert b.data.ncon > 0
    assert np.all(b.data.ctrl == 0)
    assert b.frame()['dynamics']['fallen']


def test_stand_supports_weight_and_reacts_to_external_force():
    b = body()
    for _ in range(60): b.act(Action('stand'))
    f = b.frame()
    assert .06 < f['pose']['height_m'] < .075
    assert not f['dynamics']['fallen']
    assert len([leg for leg in f['legs'] if leg['stance']]) == 4
    assert sum(c['normal_force_n'] for c in f['dynamics']['contacts']) == pytest.approx(.602*9.81, rel=.01)
    assert np.linalg.norm(b.data.qvel[:6]) < 1e-5
    before = b.data.qpos[:3].copy()
    b.data.xfrc_applied[b.model.body('chassis').id, 0] = 4
    b.act(Action('stand'))
    assert b.data.qpos[0] > before[0]+.001
    assert np.max(np.abs(b.data.ctrl)) <= b.config.torque_limit_nm


def test_stop_does_not_teleport_or_freeze_free_joint():
    b = body()
    b.data.qvel[0] = .2
    b.act(Action('stop'))
    assert b.data.qpos[0] > .002
    assert np.linalg.norm(b.data.qvel[:6]) > 0


def test_servo_targets_slew_and_torques_saturate():
    b = body()
    b.data.qpos[7] = .9
    initial = b._targets.copy()
    b.act(Action('drive', {'forward_mps': .03, 'yaw_rps': .3}))
    assert np.max(np.abs(b._targets-initial)) <= b.config.target_speed_rad_s*b.config.dt_s+1e-12
    assert np.max(np.abs(b.data.ctrl)) <= .35
    assert np.max(np.abs(b.data.actuator_force)) <= .35


@pytest.mark.parametrize('action', [Action('bad'), Action('drive', {'forward_mps':float('nan')}), Action('stop', {'x':1}), Action('led', {'on':1})])
def test_invalid_action_is_atomic(action):
    b = body()
    before = b.snapshot()
    with pytest.raises((ValueError, TypeError)): b.act(action)
    assert b.snapshot() == before


def test_snapshot_during_contact_noise_and_pending_button_is_exact():
    b = body(range_config=RangeConfig(noise_half_width_m=.01, dropout_probability=.2))
    for _ in range(37): b.act(Action('drive', {'forward_mps':.015}))
    b.inject_button('user', True)
    b.act(Action('tone', {'hz':440, 'duration_s':1}))
    b.inject_button('reset', True)
    snapshot = json.loads(json.dumps(b.snapshot()))
    c = MujocoBody.restore(snapshot)
    assert c.snapshot() == snapshot
    for _ in range(50):
        b.observe(); b.frame()
        for robot in (b, c): robot.act(Action('drive', {'forward_mps':.015, 'yaw_rps':.1}))
        assert b.snapshot() == c.snapshot()
    assert c.observe().sensors['peripherals']['reset_button_down']


def test_snapshot_fresh_process_continuation(tmp_path):
    b = body(range_config=RangeConfig(noise_half_width_m=.005))
    for _ in range(31): b.act(Action('drive', {'lateral_mps':.01}))
    b.data.xfrc_applied[b.model.body('chassis').id, 1] = .1
    start = tmp_path/'start.json'; end = tmp_path/'end.json'
    start.write_text(json.dumps(b.snapshot()))
    code = '''import json,sys
from psi_gw.body.picrawler.mujoco_body import MujocoBody
from psi_gw.body.base import Action
b=MujocoBody.restore(json.load(open(sys.argv[1])))
for i in range(40): b.act(Action('drive', {'lateral_mps':.01}))
open(sys.argv[2],'w').write(json.dumps(b.snapshot(),sort_keys=True))
'''
    subprocess.run([sys.executable, '-c', code, str(start), str(end)], check=True)
    for _ in range(40): b.act(Action('drive', {'lateral_mps':.01}))
    assert json.loads(end.read_text()) == json.loads(json.dumps(b.snapshot()))


@pytest.mark.parametrize('field,value', [('engine','0'), ('model_sha256','bad'), ('state',[1]), ('tick',-1)])
def test_reject_incompatible_snapshot(field, value):
    snapshot = body().snapshot(); snapshot[field] = value
    with pytest.raises(ValueError): MujocoBody.restore(snapshot)


def test_bridge_compatible_observation_does_not_expose_truth():
    from psi_gw.body.picrawler.bridge import _observation
    b = MujocoBody(camera_config=CameraConfig(width=8,height=6))
    for _ in range(3): b.act(Action('stand'))
    observation = asdict(b.observe())
    assert _observation(observation) == b.observe()
    assert set(observation['sensors']) == {'ultrasonic','camera','telemetry','peripherals'}
    assert 'dynamics' not in observation['sensors']
    assert 'dynamics' in b.frame()
    cached = b.snapshot()
    b.observe().sensors['camera']['rgb'][0][0][0] = 0
    b.frame()['dynamics']['contacts'].clear()
    assert b.snapshot() == cached


def test_camera_and_range_follow_tilted_chassis():
    b = MujocoBody(camera_config=CameraConfig(width=8,height=6))
    b.data.qpos[3:7] = math.cos(math.pi/4), 0, math.sin(math.pi/4), 0
    mujoco.mj_forward(b.model,b.data); b._cache()
    assert b.frame()['sensor']['direction'][2] == pytest.approx(-1)
    assert b.observe().sensors['ultrasonic']['distance_m'] == pytest.approx(.068-.045, abs=1e-12)
    colors = np.array(b.observe().sensors['camera']['rgb'])
    assert colors.shape == (6,8,3)
    assert colors.min() >= 0 and colors.max() <= 255


def test_energy_cutoff_disables_actuation_but_gravity_continues():
    b = body(energy_config=EnergyConfig(battery_initial_soc=0))
    for _ in range(30): b.act(Action('stand'))
    assert not b.observe().sensors['telemetry']['powered']
    assert b.frame()['dynamics']['fallen']
    assert np.all(b.data.ctrl == 0)
    assert b.observe().sensors['telemetry']['energy_consumed_j'] == 0


@pytest.mark.parametrize('kwargs', [dict(dt_s=.051),dict(kp=0),dict(physics_dt_s=float('inf')),dict(stance_fraction=1)])
def test_invalid_physics_config(kwargs):
    with pytest.raises(ValueError): DynamicsConfig(**kwargs)


def test_optional_backend_is_lazy_and_has_actionable_import_error():
    script = '''import sys,importlib.abc
class Deny(importlib.abc.MetaPathFinder):
 def find_spec(self, fullname, path=None, target=None):
  if fullname == 'mujoco' or fullname.startswith('mujoco.'):
   raise ModuleNotFoundError('blocked optional dependency')
sys.meta_path.insert(0,Deny())
from psi_gw.body.picrawler import PiCrawlerSimBody
from psi_gw.body.picrawler.mujoco_body import MujocoBody
assert 'mujoco' not in sys.modules
try: MujocoBody()
except ImportError as error: assert '[mujoco]' in str(error)
else: raise AssertionError('optional import unexpectedly succeeded')
'''
    subprocess.run([sys.executable, '-c', script], check=True)


def test_fault_latches_until_reset():
    b = body()
    b.data.qvel[0] = float('nan')
    with pytest.raises(RuntimeError, match='reset required'): b.act(Action('stand'))
    with pytest.raises(RuntimeError, match='reset required'): b.act(Action('stand'))
    with pytest.raises(RuntimeError, match='reset required'): b.snapshot()
    b.reset(0)
    b.act(Action('stand'))
    assert np.isfinite(b.data.qpos).all()


def test_complete_dynamic_episode_resume_keeps_policy_delivery_and_physics():
    from psi_gw.body.picrawler.mujoco_experiment import DynamicCase, DynamicEpisode
    b = DynamicEpisode(DynamicCase(1000,'slalom','memory','delayed',max_ticks=25))
    for _ in range(12): assert b.step()
    c = DynamicEpisode.restore(json.loads(json.dumps(b.snapshot())))
    assert c.snapshot() == b.snapshot()
    while b.step(): pass
    while c.step(): pass
    b.settle(); c.settle()
    assert b.result() == c.result()
    assert b.result()['outcome'] == 'timeout'
    assert b.result()['stop_pass']
    before=b.snapshot(); b.settle(); assert b.snapshot() == before


def test_mujoco_replay_uses_explicit_backend_labels(tmp_path):
    from psi_gw.body.picrawler.mujoco_experiment import metadata
    from psi_gw.body.picrawler.replay import write_replay
    b=body()
    path=tmp_path/'replay.html'
    write_replay(path,[b.frame()],metadata(b,'Physical replay'))
    html=path.read_text()
    assert 'MuJoCo · angenommene Dynamik' in html
    assert 'Kinematik-Testbett' not in html
    assert 'Kein Nachweis realer Standsicherheit' in html


def test_snapshot_rejects_inconsistent_peripheral_cache():
    p=body().snapshot()
    p['readings']['peripherals']['user_led']=True
    with pytest.raises(ValueError,match='peripheral cache'): MujocoBody.restore(p)


@pytest.mark.parametrize('joint',range(12))
@pytest.mark.parametrize('side',[-1,1])
def test_soft_joint_limit_generates_opposing_constraint_force(joint,side):
    b=body()
    b.data.qpos[2]=1.0  # Isolate joint stops from ground contacts.
    limits=b.model.jnt_range[joint+1]
    b.data.qpos[7+joint]=(limits[0] if side<0 else limits[1])+side*.01
    mujoco.mj_forward(b.model,b.data)
    assert b.model.jnt_limited[joint+1]
    assert any(t==mujoco.mjtConstraint.mjCNSTR_LIMIT_JOINT for t in b.data.efc_type)
    assert b.data.qfrc_constraint[6+joint]*side < 0
