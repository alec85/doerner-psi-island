"""Clock: age part of LiftInc (UStrukturen.Pas, line 695)."""

from psi_gw.clock import Clock


def test_fractions_accumulate_into_age():
    c = Clock()
    for _ in range(3):
        c.advance(0.5)
    assert c.age == 1 and c.realtime == 0.5
    c.advance(2.75)
    assert c.age == 4 and c.realtime == 0.25


def test_snapshot_round_trip():
    c = Clock(age=7, realtime=0.125)
    assert Clock.restore(c.snapshot()) == c
