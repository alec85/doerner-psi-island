"""Param.Dat (ReadParameter in InitPsi, UStrukturen.Pas line 2645)."""

import json

from psi_gw.motivation import Modulator, Motive
from psi_gw.params import PsiParams, read_param_dat


def test_island_parameters():
    p = read_param_dat()
    assert (p.memory.forgetting_rate, p.memory.protocol_factor, p.memory.base_reinforcement) == (0.0, 1000.0, 0.001)
    assert [tuple(p.needs[m].__getattribute__(f) for f in ("weight", "increment", "decrement")) for m in Motive
            if m is not Motive.NIL] == [
        (1, 0.00004, 1), (1, 0.000046, 1), (0.7, 0.1, 0.1), (0.33, 1, 1),
        (1, 0.001, 0.01), (1, 0.01, 0.03), (1, 0.000005, 1)]
    assert [(m.gain, m.minimum, m.maximum) for m in p.modulators.values()] == [(0.75, 0, 1), (0.7, 0, 1), (0.1, 0, 1)]
    assert list(p.modulators) == list(Modulator)


def test_snapshot_round_trip():
    p = read_param_dat()
    assert PsiParams.restore(json.loads(json.dumps(p.snapshot()))) == p
