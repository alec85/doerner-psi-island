"""GoalGen and InterMedGoals (UPSIMain.Pas, lines 1500 and 1453)."""

import pytest

from psi_gw.counters import IntProc
from psi_gw.memory import Axon, Spat, Synapse
from psi_gw.motivation import Modulator, Motive
from psi_gw.motivation.goals import goal_gen
from psi_gw.random_source import RecordingSource, ReplaySource
from psi_gw.state import PsiState


def setup(stream, actual=Motive.HUNGER):
    st = PsiState(seed=16)
    st.net.rng = RecordingSource(ReplaySource(list(stream)))
    st.motivation.actual_motive = actual
    return st


def names(lst):
    return [s.target.name for s in lst]


def test_nil_motive_is_a_range_error():
    st = setup([], Motive.NIL)
    with pytest.raises(IndexError):
        goal_gen(st.motivation, st.goal_list, st.mani_actors)


def test_main_goal_always_passes_but_draws():
    st = setup([0.0, 0.0, 0.999])  # Decay, Junction, GoalGen
    mot = st.motivation
    goal = st.net.new_neuron("Sg")
    st.net.connect(mot.need_in[Motive.HUNGER], goal, Axon.TO_GOAL, 0.5)
    mot.need_in[Motive.HUNGER].activity = 0.3
    st.goal_list.append_copy(Synapse(st.net.new_neuron("old")))
    age = st.clock.age
    assert goal_gen(mot, st.goal_list, st.mani_actors) is True
    assert names(st.goal_list) == ["Sg"]  # cleared, then filled
    assert [d.site for d in st.net.rng.log] == ["UStrukturen.Decay#1", "UStrukturen.Junction#1", "UPSIMain.GoalGen#1"]
    assert st.counters.int_proc[IntProc.MmGo] == 1 and st.counters.int_proc[IntProc.SGoa] == 1
    assert mot.station_count[1] == 1  # KompBestConsumption(2, ...): goals found
    assert st.clock.age - age == 7 + 1 + 1  # one per need, one per goal link, one per conducting goal
    assert st.goal_list[0].weight == (0.5 ** 0.5 + 0.001) ** 2  # copied after strengthening


@pytest.mark.parametrize("u,passes", [(0.0299, True), (0.0301, False)])
def test_background_goal_chance(u, passes):
    """Background goal: random < r - (r - strength(actual) * threshold)."""
    st = setup([0.0, 0.0, u])
    mot = st.motivation
    mot.need_in[Motive.HUNGER].activity = 0.6       # current motive, strength 0.6
    mot.modulators[Modulator.SELECT_THRESHOLD] = 0.05  # 0.6 * 0.05 = 0.03
    goal = st.net.new_neuron("Sw")
    st.net.connect(mot.need_in[Motive.DURST], goal, Axon.TO_GOAL, 0.8)
    mot.need_in[Motive.DURST].activity = 0.5
    assert goal_gen(mot, st.goal_list, st.mani_actors) is False
    assert (names(st.goal_list) == ["Sw"]) is passes
    assert st.counters.int_proc[IntProc.MbGo] == int(passes)
    assert mot.station_count[0 if not passes else 1] == 1


def test_inactive_need_and_known_goal_draw_nothing():
    st = setup([0.0, 0.0, 0.0])
    mot = st.motivation
    goal = st.net.new_neuron("Sg")
    st.net.connect(mot.need_in[Motive.HUNGER], goal, Axon.TO_GOAL, 1)
    st.net.connect(mot.need_in[Motive.DURST], goal, Axon.TO_GOAL, 1)  # same goal for thirst
    st.net.connect(mot.need_in[Motive.AFFILI], st.net.new_neuron("Sa"), Axon.TO_GOAL, 1)
    mot.need_in[Motive.HUNGER].activity = 0.3
    mot.need_in[Motive.DURST].activity = 0.3   # but goal already in the list
    mot.need_in[Motive.AFFILI].activity = 0.0  # inactive
    goal_gen(mot, st.goal_list, st.mani_actors)
    assert names(st.goal_list) == ["Sg"] and st.net.rng.draws == 3


def test_intermediate_goal_from_manipulation():
    """InterMedGoals: situation S0 --(manipulation A)--> goal G makes S0 an intermediate goal."""
    st = setup([0.0] * 7)  # main goal 3 draws, two transmissions in InterMedGoals 4 draws
    mot = st.motivation
    s0, act, goal = (st.net.new_neuron(n) for n in ("Ss0", "Nehmen", "Sg"))
    st.mani_actors.add_front(Synapse(act))
    for x in (s0, act, goal):
        st.protocol.protocol(0, x, "P", 1000, Spat())
    st.net.connect(mot.need_in[Motive.HUNGER], goal, Axon.TO_GOAL, 1)
    mot.need_in[Motive.HUNGER].activity = 0.3
    goal_gen(mot, st.goal_list, st.mani_actors)
    assert names(st.goal_list) == ["Sg", "Ss0"]
    assert st.counters.int_proc[IntProc.MiGo] == 1 and st.net.rng.draws == 7


def test_no_intermediate_goal_without_manipulation():
    st = setup([0.0] * 5)
    mot = st.motivation
    s0, loco, goal = (st.net.new_neuron(n) for n in ("Ss0", "lN", "Sg"))
    for x in (s0, loco, goal):
        st.protocol.protocol(0, x, "P", 1000, Spat())
    st.net.connect(mot.need_in[Motive.HUNGER], goal, Axon.TO_GOAL, 1)
    mot.need_in[Motive.HUNGER].activity = 0.3
    goal_gen(mot, st.goal_list, st.mani_actors)
    assert names(st.goal_list) == ["Sg"] and st.net.rng.draws == 5
