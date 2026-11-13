"""The identified runtime profile must be bounded and split-safe."""
from dataclasses import replace
import pytest
from psi_gw.body.picrawler.motion_profile import MotionProfile,fit_profile


def profile():
    return MotionProfile((.9,)*6,((.8,1.0),)*6,.1,.01,'a'*64)


def test_response_is_signed_bounded_and_causal():
    p=profile()
    v=p.response([0,0,0],dict(forward_mps=.03,lateral_mps=.03,yaw_rps=-5),.05)
    assert 0<v[0]<.03*.9 and v[0]==v[1]
    assert -.27<v[2]<0
    stopped=p.response(v,{},.05)
    assert 0<stopped[0]<v[0] and v[2]<stopped[2]<0


def test_json_roundtrip_and_fingerprint():
    import json
    p=profile();assert MotionProfile.restore(json.loads(json.dumps(p.snapshot())))==p
    assert replace(p,response_time_s=.2).sha256!=p.sha256


@pytest.mark.parametrize('changes',[dict(gains=(1,)),dict(response_time_s=0),dict(stop_distance_m=float('nan')),dict(source_sha256='x'),dict(engine='4.0')])
def test_rejects_invalid_profiles(changes):
    with pytest.raises(ValueError):replace(profile(),**changes)


def test_fit_cannot_use_validation_data():
    with pytest.raises(ValueError,match='development'):fit_profile([dict(split='validation')],'a'*64)
    with pytest.raises(ValueError,match='insufficient'):fit_profile([dict(split='development',axis=0,sign=1)],'a'*64)
