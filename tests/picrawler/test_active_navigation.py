"""Sensor boundary, causal timing, scanning and resumable local navigation."""
import copy
import json
import math

import pytest

from psi_gw.body.base import Action,Observation
from psi_gw.body.picrawler.active_navigation import ActiveNavigator,NavigationConfig
from psi_gw.body.picrawler.motion_profile import MotionProfile


def profile():return MotionProfile((.9,)*6,((.8,1.),)*6,.1,.01,'a'*64)


def obs(tick,distance=1.,stamp=None,camera=None):
    sample=dict(status='ok',distance_m=distance,captured_at_s=tick*.05 if stamp is None else stamp)
    sensors=dict(ultrasonic=sample)
    if camera is not None:sensors['camera']=camera
    return Observation(tick,sensors,dict(hunger=0.,damage=0.))


def test_free_range_produces_bounded_forward_motion_without_truth():
    n=ActiveNavigator(profile());action=n.choose(obs(40))
    assert action.name=='drive' and action.params['forward_mps']>0
    assert math.hypot(action.params['forward_mps'],action.params['lateral_mps'])<=.03
    assert n.position==[0,0]
    assert n.last_decision['heading_source']=='identified_command_response_not_odometry'


@pytest.mark.parametrize('data',[{},dict(hunger=None,damage=0),dict(hunger=0,damage=2)])
def test_unknown_needs_stop(data):
    n=ActiveNavigator(profile());o=obs(0);o.internal.update(data)
    if not data:o.internal.clear()
    assert n.choose(o)==Action('stop')


def test_energy_stop_is_latched_and_cannot_be_cleared_by_later_healthy_packet():
    n=ActiveNavigator(profile());o=obs(0);o.internal['hunger']=.9
    assert n.choose(o)==Action('stop')
    assert n.choose(obs(1),Action('stop'))==Action('stop')
    assert n.mode=='energy_stop'


@pytest.mark.parametrize('status',['dropout','too_close','out_of_range'])
def test_unknown_range_does_not_assert_free_space(status):
    n=ActiveNavigator(profile());o=obs(0);o.sensors['ultrasonic'].update(status=status,distance_m=None)
    assert n.choose(o)==Action('stop')
    assert not n.points


@pytest.mark.parametrize('stamp',[-1,.1])
def test_stale_or_future_acquisition_is_rejected(stamp):
    n=ActiveNavigator(profile());assert n.choose(obs(0,stamp=stamp))==Action('stop')
    assert not n.points


def test_duplicate_decision_is_idempotent_and_conflict_is_atomic():
    n=ActiveNavigator(profile());o=obs(0);a=n.choose(o);snapshot=n.snapshot()
    assert n.choose(o)==a and n.snapshot()==snapshot
    with pytest.raises(ValueError,match='conflicting'):n.choose(obs(0,.5))
    assert n.snapshot()==snapshot


def test_truth_fields_are_discarded_before_decision_and_fingerprint():
    first=ActiveNavigator(profile());second=ActiveNavigator(profile())
    clean=obs(0);poison=copy.deepcopy(clean)
    poison.sensors.update(world={'bounds':[100,200]},pose={'x':999},collision=True,joints=[99])
    poison.internal['secret_goal']=999
    assert first.choose(clean)==second.choose(poison)
    assert first.snapshot()==second.snapshot()


def test_range_is_registered_at_acquisition_pose_not_delivery_pose():
    n=ActiveNavigator(profile());n.last_tick=0;n.last_action=Action('drive',{'yaw_rps':.3})
    n.heading=.4;n.history=[dict(t=0,x=0,y=0,heading=0)]
    n.choose(obs(1,.5,stamp=0),n.last_action)
    point=n.points[-1]
    assert point['x']==pytest.approx(.545) and point['y']==pytest.approx(0)
    before=copy.deepcopy(n.points)
    n.choose(obs(2,.5,stamp=0),n.last_action)
    assert n.points==before  # repeated capture never adds fresh evidence


def test_camera_hint_requests_scan_but_does_not_supply_fake_depth():
    n=ActiveNavigator(profile())
    camera=dict(encoding='rgb8',width=4,height=4,rgb=[[[200,200,200]]*4 for _ in range(4)],captured_at_s=0)
    camera['rgb'][3]=[[220,20,20]]*4
    action=n.choose(obs(0,1.,camera=camera))
    assert n.mode=='scan' and action.params['yaw_rps']<0
    assert all(p['distance']==1 for p in n.points)  # no pixel-derived range


def test_obstacle_hull_blocks_center_and_selects_a_clearer_side():
    n=ActiveNavigator(profile())
    n.points=[dict(x=.35,y=-.10,t=0,distance=.35,anchor_x=0,anchor_y=0)]
    assert n._clearance(0)<n._clearance(.8)
    candidate=n._select_direction()
    assert candidate is not None and candidate[1]>0


def test_old_obstacles_expire():
    n=ActiveNavigator(profile());n.points=[dict(x=.2,y=0,t=0,distance=.2,anchor_x=0,anchor_y=0)]
    n.choose(obs(1000,4))
    assert not n.points


def test_snapshot_during_scan_resumes_every_decision_exactly():
    n=ActiveNavigator(profile());a=n.choose(obs(0,.3));c=ActiveNavigator.restore(json.loads(json.dumps(n.snapshot())))
    for tick in range(1,80):
        b=n.choose(obs(tick,.3),a);d=c.choose(obs(tick,.3),a)
        assert b==d and n.snapshot()==c.snapshot();a=b


def test_previous_action_or_tick_gap_cannot_silently_move_estimate():
    n=ActiveNavigator(profile());n.choose(obs(0));before=n.snapshot()
    with pytest.raises(ValueError):n.choose(obs(2),n.last_action)
    assert n.snapshot()==before
    with pytest.raises(ValueError):n.choose(obs(1),Action('stop'))
    assert n.snapshot()==before


@pytest.mark.parametrize('version',[0,2])
def test_rejects_foreign_snapshot(version):
    p=ActiveNavigator(profile()).snapshot();p['version']=version
    with pytest.raises(ValueError):ActiveNavigator.restore(p)


def test_adjacent_free_ray_does_not_clear_obstacle_endpoint():
    n=ActiveNavigator(profile())
    point=dict(x=.4,y=.01,t=0,distance=.4,anchor_x=0,anchor_y=0)
    n.points=[copy.deepcopy(point)]
    n.choose(obs(0,1.5))
    assert n.points==[point]


def test_conflicting_or_out_of_order_capture_cannot_become_new_evidence():
    n=ActiveNavigator(profile());a=n.choose(obs(0,.3));before=copy.deepcopy(n.points)
    b=n.choose(obs(1,1.5,stamp=0),a)
    assert b==Action('stop') and n.points==before
    c=n.choose(obs(2,.3,stamp=0),b)
    assert n.points==before
    n.choose(obs(3,.4,stamp=.05),c)
    count=len(n.points);before=copy.deepcopy(n.points)
    n.choose(obs(4,.7,stamp=0),n.last_action)
    assert n.points==before and len(n.points)==count


@pytest.mark.parametrize('change',[dict(encoding='depth'),dict(width=99),dict(height=99)])
def test_malformed_camera_cannot_request_false_scan(change):
    n=ActiveNavigator(profile());camera=dict(encoding='rgb8',width=4,height=4,rgb=[[[220,20,20]]*4 for _ in range(4)],captured_at_s=0)
    camera.update(change)
    n.choose(obs(0,1.6,camera=camera))
    assert not n.camera_hint and n.mode=='travel'


def test_completed_scan_checkpoint_has_normalized_index():
    n=ActiveNavigator(profile());n._start_scan(0);action=Action('stop')
    for tick in range(400):
        action=n.choose(obs(tick,1.6),action)
        if not n.scan_targets:
            assert n.scan_index==0
            assert ActiveNavigator.restore(json.loads(json.dumps(n.snapshot()))).snapshot()==n.snapshot()
            break
    else:pytest.fail('scan did not finish in a bounded interval')


@pytest.mark.parametrize('field,value',[('position',[0]),('velocity',[0,0]),('energy_latched',1),('translation_uncertainty',-1),('last_tick',True),('scan_index',3)])
def test_malformed_checkpoint_state_is_rejected(field,value):
    p=ActiveNavigator(profile()).snapshot();p['state'][field]=value
    with pytest.raises(ValueError):ActiveNavigator.restore(p)


def test_inside_inflated_margin_can_move_away_without_erasing_obstacle():
    n=ActiveNavigator(profile());point=dict(x=.10,y=.15,t=0,distance=.2,anchor_x=0,anchor_y=0);n.points=[point]
    assert n._clearance(-1.2)>0 and n._clearance(.5)==0
    assert n._select_direction() is not None and n.points==[point]


def test_reordered_packet_reuses_only_actual_fresh_capture_without_refresh():
    n=ActiveNavigator(profile());a=n.choose(obs(0,1.6))
    a=n.choose(obs(1,1.6),a)
    n.choose(obs(2,.1,stamp=0),a)
    assert n.range_source=='retained_capture' and n.range_age_s==pytest.approx(.05)
    assert n.accepted_range['t']==.05
