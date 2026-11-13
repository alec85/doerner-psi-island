"""Motivation: Consumption, NeedAndCompetence, EpiKomp, MotiveStrength, KompBestConsumption, Motivation.

Line numbers in docstrings refer to UStrukturen.Pas unless UPSIMain.Pas is
named. The last test compares with the activity protocol of the original.
"""

import math
import re
from pathlib import Path

import pytest

from psi_gw.counters import IntProc
from psi_gw.memory import Axon, Spat
from psi_gw.motivation import NEEDS, Modulator, Motive, Tendency
from psi_gw.motivation.system import action_tendencies, select_motive
from psi_gw.random_source import RecordingSource, ReplaySource
from psi_gw.state import PsiState

ROOT = Path(__file__).resolve().parents[1]
ACTU = ROOT / "traces" / "original-runs" / "2026-11-10-zufallsmitschnitt" / "raw" / "seed16" / "actu16(1).Prt"


@pytest.fixture
def st():
    return PsiState(seed=16)


# --- Consumption (1710) ------------------------------------------------------------

def test_consumption_raises_need(st):
    m = st.motivation
    m.consumption(Motive.HUNGER, 0.5)
    store = 1 - 0.00004 * 0.5
    assert m.store[Motive.HUNGER] == store
    assert m.activity(Motive.HUNGER) == math.sqrt(1 - store)
    assert m.total_consum[Motive.HUNGER] == 0.00004 * 0.5


def test_consumption_satisfies_and_caps_store(st):
    m = st.motivation
    m.consumption(Motive.DURST, 10000)
    m.consumption(Motive.DURST, -0.3)
    assert m.store[Motive.DURST] == (1 - 0.000046 * 10000) + 0.3
    m.consumption(Motive.DURST, -1)
    assert m.store[Motive.DURST] == 1.0 and m.activity(Motive.DURST) == 0.0
    assert m.total_in[Motive.DURST] == 0.3 + 1


def test_consumption_zero_still_recomputes_activity(st):
    m = st.motivation
    m.store[Motive.AFFILI] = 0.75
    m.consumption(Motive.AFFILI, 0)
    assert m.activity(Motive.AFFILI) == 0.5


def test_consumption_nucleotides(st):
    """Nucleotides: consumption is normalised by MaxNukleo 104; activity moves towards the weight or decays."""
    m = st.motivation
    m.consumption(Motive.NUKLEO, -2)  # two nucleotides collected
    assert m.store[Motive.NUKLEO] == 1.0  # capped
    assert m.activity(Motive.NUKLEO) == 0.7 - 0.7 * 0.1
    assert m.total_in[Motive.NUKLEO] == 2
    m.consumption(Motive.NUKLEO, 52)
    assert m.store[Motive.NUKLEO] == 0.5
    a = 0.7 - 0.7 * 0.1
    assert m.activity(Motive.NUKLEO) == a + (0.7 - a) * 0.1


# --- NeedAndCompetence (UPSIMain 139) ---------------------------------------------------

def test_need_and_competence(st):
    m = st.motivation
    m.need_in[Motive.HUNGER].activity = 0.5
    m.need_in[Motive.NUKLEO].activity = 0.7  # excluded
    m.need_in[Motive.SCHADEN].activity = 0.2
    st.clock.age = 1000
    m.need_and_competence()
    r = 0.5 * 1 * 1000 + 0.2 * 0.33 * 1000
    assert m.store[Motive.KOMPETENZ] == 1 - (r / 500000) * 0.01
    assert m.activity(Motive.KOMPETENZ) == 0  # only the store changes
    assert m.age_mot_old == 1000


def test_set_modulator_clamps(st):
    m = st.motivation
    m.set_modulator(Modulator.RESOLUTION_LEVEL, 1.4)
    assert m.modulators[Modulator.RESOLUTION_LEVEL] == 1.0
    m.set_modulator(Modulator.SELECT_THRESHOLD, -0.1)
    assert m.modulators[Modulator.SELECT_THRESHOLD] == 0.0


# --- EpiKomp (2151) and MotiveStrength (2210) -------------------------------------------

def goal_structure(st):
    """Hunger knows two goals: G1 reached by action A in the protocol, G2 preceded by a sensory neuron."""
    net = st.net
    hunger = st.motivation.need_in[Motive.HUNGER]
    act, g1, g2, s = (net.new_neuron(n) for n in ("Nehmen", "Sg1", "Sg2", "Sx"))
    p = st.protocol.protocol(0, act, "P", 1000, Spat())  # protocol element recording the action
    net.connect(p, g1, Axon.POR, 0.8)  # g1 follows p: g1 ret -> p
    net.connect(s, g2, Axon.POR, 0.5)
    net.connect(hunger, g1, Axon.TO_GOAL, 1)
    net.connect(hunger, g2, Axon.TO_GOAL, 1)
    return hunger, g1, g2


def test_epistemic_competence(st):
    goal_structure(st)
    st.net.rng = RecordingSource(ReplaySource([0.0] * 6))
    age = st.clock.age
    e = st.motivation.epistemic_competence(Motive.HUNGER)
    assert e == math.log10(1 + (0.5 * 0.2 + 0.8 * 0.4))  # list order: g2 was linked last, so first
    assert st.net.rng.draws == 6  # toGoal twice, sub once, two draws each
    assert st.clock.age - age == 5  # 1 per goal, 1 per ret, 1 per action


def test_epistemic_competence_counts_an_action_once(st):
    hunger, g1, _ = goal_structure(st)
    g3 = st.net.new_neuron("Sg3")
    st.net.connect(g1.axon[Axon.RET].first.target, g3, Axon.POR, 0.9)
    st.net.connect(hunger, g3, Axon.TO_GOAL, 1)
    st.net.rng = ReplaySource([0.0] * 10)
    # order g3, g2, g1; at g1 the action is already counted and adds 0
    assert st.motivation.epistemic_competence(Motive.HUNGER) == math.log10(1 + (0.9 * 0.4 + 0.5 * 0.2 + 0.0))
    assert st.net.rng.draws == 10


def test_epistemic_competence_without_goals_draws_nothing(st):
    st.net.rng = ReplaySource([])
    assert st.motivation.epistemic_competence(Motive.DURST) == 0.0
    assert st.motivation.epistemic_competence(Motive.NIL) == 0.0


def test_motive_strength(st):
    m = st.motivation
    m.need_in[Motive.SCHADEN].activity = 0.6
    m.need_in[Motive.KOMPETENZ].activity = 0.5
    assert m.motive_strength(Motive.SCHADEN) == 0.6 * 0.33 * 0.5
    m.need_in[Motive.KOMPETENZ].activity = 0.0
    assert m.motive_strength(Motive.NUKLEO) == 0.7 * 0.7 * 1


# --- S_Beduerfnisse (2406), KompBestConsumption (2594) -----------------------------------

def test_needs_index(st):
    assert st.motivation.needs_index() == 0.5  # 0.7 / 5 < 0.5
    for m in NEEDS:
        st.motivation.need_in[m].activity = 1.0
    assert st.motivation.needs_index() == 7 / 5


def test_competence_certainty_clamps_and_weights(st):
    m = st.motivation
    m.competence_certainty(18, 0.1, 0)   # KompGewichtung[18] = 0.01, strength clamped to 0.6
    assert m.store[Motive.KOMPETENZ] == 1 - 0.01 * (0.01 * 0.6)
    assert m.store[Motive.BESTIMMTHEIT] == 1.0
    m.competence_certainty(6, 5, -5)     # 0.07 * 1.3; BestGewichtung[6] = 0.2, strength -1.3
    assert m.competence_sum[5] == 0.07 * 1.3
    assert m.certainty_sum[5] == 0.2 * -1.3
    assert m.store[Motive.BESTIMMTHEIT] == pytest.approx(1 - 0.001 * 0.26)
    assert m.station_count[17] == 1 and m.station_count[5] == 1


# --- Motivation (UPSIMain 1341) -------------------------------------------------------------

def test_action_tendencies():
    t = action_tendencies(0.5, 0.2)
    assert t[Tendency.AGGRESSION] == 0.5 * 0.8 and t[Tendency.FLIGHT] == 0.5 * 0.2
    assert t[Tendency.DIV_EXPLO] == 0.2 * 0.8 and t[Tendency.SPEC_EXPLO] == 0.5 * 0.8


@pytest.mark.parametrize("args,expected", [
    ((Motive.HUNGER, Motive.DURST, 0.9, 0.5, 0.05, 0.1), (Motive.NIL, False)),       # below threshold
    ((Motive.NIL, Motive.DURST, 0.9, 0.0, 0.5, 0.1), (Motive.DURST, False)),        # no motive before
    ((Motive.HUNGER, Motive.DURST, 0.55, 0.5, 0.5, 0.1), (Motive.HUNGER, False)),   # inhibition holds
    ((Motive.HUNGER, Motive.DURST, 0.65, 0.5, 0.5, 0.1), (Motive.DURST, True)),     # inhibition overcome
])
def test_select_motive(args, expected):
    assert select_motive(*args) == expected


def test_motivation_switch_counts_and_costs_time(st):
    m = st.motivation
    m.actual_motive = Motive.NUKLEO
    st.clock.age = 20000  # long thirst and hunger
    m.store[Motive.DURST] = 0.0
    motive = m.motivation()
    assert motive is Motive.DURST
    assert st.counters.int_proc[IntProc.MchM] == 1
    assert st.clock.age == 20003


# --- comparison with the original's activity protocol ------------------------------------------

def first_cycle_protocol():
    text = ACTU.read_text(encoding="cp1252")
    block = text[text.index("--> BedIn"):text.index("-? WAS TUN?")]
    rows = re.findall(r"^\s+(\w+)\s+(-?\d+\.\d{3})\s+(-?\d+\.\d{3})$", block, re.M)
    motive = re.search(r"AktMot: (\w+)", block).group(1)
    mods = re.search(r"AR =\s+([\d.]+) RL =\s+([\d.]+) STh =\s+([\d.]+)", block).groups()
    return rows, motive, mods


def run_first_cycle(age):
    st = PsiState(seed=16)
    st.clock.age = age
    st.motivation.need_and_competence()
    printed = []
    m = st.motivation
    original = m.motive_strength

    def strength(motive):  # record what the original prints inside the loop
        s = original(motive)
        printed.append((motive, f"{m.activity(motive):.3f}", f"{s:.3f}"))
        return s

    m.motive_strength = strength
    motive = m.motivation()
    mods = tuple(f"{m.modulators[x]:.3f}" for x in Modulator)
    return printed, motive, mods


def test_first_cycle_matches_original_protocol():
    """actu16(1).Prt, cycle 1 (seed 16): need activities, motive strengths, chosen motive and
    modulators, printed with three decimals. The age at which Motivation runs is not
    printed; the test requires that some age reproduces every printed value at once."""
    rows, motive, mods = first_cycle_protocol()
    assert len(rows) == 7 and motive == "Nukleo"
    matching = []
    for age in range(0, 5000):
        printed, chosen, our_mods = run_first_cycle(age)
        if ([(a, s) for _, a, s in printed] == [(a, s) for _, a, s in rows]
                and chosen is Motive.NUKLEO and our_mods == mods):
            matching.append(age)
    assert matching, "no age reproduces the protocol"
    assert matching == list(range(matching[0], matching[-1] + 1))  # one contiguous range
    assert 1413 <= matching[0] and matching[-1] <= 1445  # bounds implied by hunger, thirst, affiliation
