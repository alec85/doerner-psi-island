"""PsiState: initial structures as built by InitPsi (UStrukturen.Pas line 2643)."""

import json

from psi_gw.motivation import NEEDS, Motive
from psi_gw.state import PsiState


def names(lst):
    return [s.target.name for s in lst]


def test_neurons_in_initpsi_order():
    st = PsiState()
    expected = (["Ver2", "Hor2", "Dia2", "Adi2", "", "lO", "lNO", "lN", "lNW", "lW", "lSW", "lS", "lSO", "AAgg", "AReg",
                 "Hunger1", "Durst2", "Nukleo3", "Schaden4", "Bestimmtheit5", "Kompetenz6", "Affiliation7"]
                + [f"ShortTerm{i}" for i in range(8)] + [f"Control{i}" for i in range(10)])
    assert [n.name for n in st.net.neurons] == expected


def test_lists_built_front_first():
    st = PsiState()
    assert names(st.loco_actors) == ["lSO", "lS", "lSW", "lW", "lNW", "lN", "lNO", "lO"]
    assert names(st.approach_actors) == ["AReg", "AAgg"]
    assert names(st.all_actors) == names(st.loco_actors) + ["AReg", "AAgg"]
    assert names(st.motive_list)[0] == "Affiliation7"
    assert names(st.short_term_list)[0] == "ShortTerm7" and names(st.control_list)[0] == "Control9"


def test_initial_needs():
    st = PsiState()
    mot = st.motivation
    assert all(mot.store[m] == 1.0 for m in NEEDS)  # all weights > 0 on the island
    assert [mot.activity(m) for m in NEEDS] == [0, 0, 0.7, 0, 0, 0, 0]
    assert st.aras.activity == 0 and mot.actual_motive is Motive.NIL
    assert st.counters.performance[7] == 5  # Leistung[NNukleotide]
    assert st.rng.rand_seed == 2  # Psi.Ini default


def test_snapshot_round_trip():
    st = PsiState(seed=16)
    st.motivation.consumption(Motive.HUNGER, 0.3)
    data = json.loads(json.dumps(st.snapshot()))
    copy = PsiState.restore(data)
    assert copy.snapshot() == data
    assert copy.motivation.need_in[Motive.HUNGER] is copy.net.neurons[15]
