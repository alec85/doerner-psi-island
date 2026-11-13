"""Memory network: Connect, ReInforce, Decay, Junction, Trace (Issue #18).

Expected values follow UStrukturen.Pas (line numbers in docstrings). The last
tests check the port's draw structure against the random trace of the
original (traces/original-runs/2026-11-10-zufallsmitschnitt).
"""

import csv
import gzip
import math
from pathlib import Path

import pytest

from psi_gw.clock import Clock
from psi_gw.memory import Axon, MemoryNetwork, MemoryParams, Neuron, Spat, conter
from psi_gw.random_source import DelphiRandom, RecordingSource, ReplaySource

ROOT = Path(__file__).resolve().parents[1]
TRACE = ROOT / "traces" / "original-runs" / "2026-11-10-zufallsmitschnitt" / "random_draws.tsv.gz"


def make_net(stream=(), forgetting_rate=0.001, age=0):
    rng = RecordingSource(ReplaySource(list(stream)))
    return MemoryNetwork(MemoryParams(forgetting_rate=forgetting_rate), rng, Clock(age=age))


def test_conter_pairs():
    """Conter (993): por/ret, sub/sur, toSatis/toGoal, toNeed/toAvers; Lan and Pic give ret."""
    for a, b in [(Axon.POR, Axon.RET), (Axon.SUB, Axon.SUR),
                 (Axon.TO_SATIS, Axon.TO_GOAL), (Axon.TO_NEED, Axon.TO_AVERS)]:
        assert conter(a) is b and conter(b) is a
    assert conter(Axon.LAN) is Axon.RET and conter(Axon.PIC) is Axon.RET


def test_defaults_are_island_parameters():
    """PsiDaten/InselIII/Param.Dat: Vergessensrate 0, Protokollfaktor 1000, Grundverstärkung 0.001."""
    p = MemoryParams()
    assert (p.forgetting_rate, p.protocol_factor, p.base_reinforcement, p.max_weight) == (0.0, 1000.0, 0.001, 1.0)


def test_new_neuron_activity_is_minus_one():
    """InitNeuron (1437): activity -1 marks 'not used'."""
    net = make_net()
    n = net.new_neuron("Sx")
    assert n.activity == -1 and all(not lst for lst in n.axon) and net.neurons == [n]


def test_connect_both_directions_front_insert():
    """Connect (1124) / ConnectVonNach (1101)."""
    net = make_net(age=42)
    a, b, c = (net.new_neuron(x) for x in "ABC")
    net.connect(a, b, Axon.POR, 0.4, Spat(3, -2, 9, 9))
    net.connect(a, c, Axon.POR, 1.7, Spat(1, 1, 0, 0))
    assert [s.target for s in a.axon[Axon.POR]] == [c, b]  # new links in front
    ab = net.connected(a, b, Axon.POR)
    assert (ab.weight, ab.timup, ab.spat) == (0.4, 42, Spat(3, -2, 0, 42))
    ba = net.connected(b, a, Axon.RET)
    assert (ba.weight, ba.timup, ba.spat) == (0.4, 42, Spat(-3, 2, 0, -42))
    assert net.connected(a, c, Axon.POR).weight == 1.0  # capped at maxweight
    assert net.rng.draws == 0


def test_connect_existing_link_is_unchanged():
    net = make_net(age=1)
    a, b = net.new_neuron("A"), net.new_neuron("B")
    net.connect(a, b, Axon.SUB, 0.3)
    net.clock.age = 5
    net.connect(a, b, Axon.SUB, 0.9)
    assert len(a.axon[Axon.SUB]) == 1 and a.axon[Axon.SUB][0].weight == 0.3
    assert b.axon[Axon.SUR][0].timup == 1


def test_disconnect_one_direction():
    """Disconnect (1209) removes only the given direction."""
    net = make_net()
    a, b = net.new_neuron("A"), net.new_neuron("B")
    net.connect(a, b, Axon.POR, 0.5)
    net.disconnect(a, b, Axon.POR)
    assert not a.axon[Axon.POR] and b.axon[Axon.RET]


def test_decay_formula():
    """Decay (1030): weight := sqrt(max(min(w², 1) - random*(age-timup)*rate, 0)); timup := age."""
    net = make_net([0.5], forgetting_rate=0.001, age=10)
    a, b = net.new_neuron("A"), net.new_neuron("B")
    net.clock.age = 0
    net.connect_one_way(a, b, Axon.POR, 0.5, Spat())
    net.clock.age = 10
    syn = a.axon[Axon.POR][0]
    net.decay(syn)
    assert syn.weight == math.sqrt(0.25 - 0.5 * 10 * 0.001)
    assert syn.timup == 10


def test_decay_clamps_at_zero_and_one():
    net = make_net([0.99, 0.0], forgetting_rate=1.0, age=100)
    a, b, c = (net.new_neuron(x) for x in "ABC")
    net.connect_one_way(a, b, Axon.POR, 0.5, Spat())
    syn = a.axon[Axon.POR][0]
    syn.timup = 0
    net.decay(syn)
    assert syn.weight == 0.0
    syn.weight = 1.2  # weights above 1 are squared and clamped to 1 first
    net.decay(syn)
    assert syn.weight == 1.0


@pytest.mark.parametrize("w", [0.001, 0.1, 0.3333333333333333, 0.5, 0.7071067811865476, 0.999999])
def test_decay_without_forgetting_keeps_weight_but_draws(w):
    """Island parameters have Vergessensrate 0: Decay still draws, the weight stays exact."""
    net = make_net([0.7], forgetting_rate=0.0, age=5)
    a, b = net.new_neuron("A"), net.new_neuron("B")
    net.connect_one_way(a, b, Axon.POR, w, Spat())
    syn = a.axon[Axon.POR][0]
    net.decay(syn)
    assert syn.weight == w and net.rng.draws == 1


def test_transmit_conducting():
    """Junction (1049): Decay draw, then random < weight; on success (sqrt(w)+GVerstaerkung)²."""
    net = make_net([0.5, 0.3], forgetting_rate=0.001)
    a, b = net.new_neuron("A"), net.new_neuron("B")
    net.connect_one_way(a, b, Axon.POR, 0.5, Spat())
    net.clock.age = 10
    syn = net.transmit(a, b, Axon.POR)
    decayed = math.sqrt(0.25 - 0.5 * 10 * 0.001)
    assert syn is a.axon[Axon.POR][0]
    assert syn.weight == (math.sqrt(decayed) + 0.001) ** 2
    assert [d.site for d in net.rng.log] == ["UStrukturen.Decay#1", "UStrukturen.Junction#1"]


def test_transmit_not_conducting_only_decays():
    net = make_net([0.0, 0.9], forgetting_rate=0.0)
    a, b = net.new_neuron("A"), net.new_neuron("B")
    net.connect_one_way(a, b, Axon.POR, 0.5, Spat())
    assert net.transmit(a, b, Axon.POR) is None
    assert a.axon[Axon.POR][0].weight == 0.5 and net.rng.draws == 2


def test_transmit_strengthening_capped_at_one():
    net = make_net([0.0, 0.0], forgetting_rate=0.0)
    a, b = net.new_neuron("A"), net.new_neuron("B")
    net.connect_one_way(a, b, Axon.POR, 0.9999999, Spat())
    assert net.transmit(a, b, Axon.POR).weight == 1.0


def test_transmit_without_link_draws_nothing():
    net = make_net([])
    a, b = net.new_neuron("A"), net.new_neuron("B")
    net.connect_one_way(b, a, Axon.POR, 0.5, Spat())
    assert net.transmit(a, b, Axon.POR) is None and net.rng.draws == 0


def test_transmit_uses_first_matching_synapse():
    net = make_net([0.0, 0.0], forgetting_rate=0.0)
    a, b = net.new_neuron("A"), net.new_neuron("B")
    net.connect_one_way(a, b, Axon.POR, 0.5, Spat())
    a.axon[Axon.POR].append_copy(a.axon[Axon.POR][0])  # duplicate further back
    syn = net.transmit(a, b, Axon.POR)
    assert syn is a.axon[Axon.POR][0] and a.axon[Axon.POR][1].weight == 0.5


def test_reinforce_both_directions():
    """ReInforce (1137): per existing direction one Decay draw, then (sqrt(w)+r)² capped at maxweight."""
    net = make_net([0.1, 0.2], forgetting_rate=0.0)
    a, b = net.new_neuron("A"), net.new_neuron("B")
    net.connect(a, b, Axon.SUB, 0.25)
    net.reinforce(a, b, Axon.SUB, 0.5)
    assert a.axon[Axon.SUB][0].weight == 1.0  # (0.5 + 0.5)² = 1
    assert b.axon[Axon.SUR][0].weight == 1.0
    assert net.rng.draws == 2


def test_reinforce_one_direction_draws_once():
    net = make_net([0.1], forgetting_rate=0.0)
    a, b = net.new_neuron("A"), net.new_neuron("B")
    net.connect_one_way(b, a, Axon.SUR, 0.04, Spat())
    net.reinforce(a, b, Axon.SUB, 0.1)
    assert b.axon[Axon.SUR][0].weight == pytest.approx(0.09, rel=1e-15)
    assert net.rng.draws == 1


def _tree():
    """Root R with parts X (parts X1, X2 in por sequence) and Y; X por Y."""
    net = make_net()
    r, x, y, x1, x2 = (net.new_neuron(n) for n in ("R", "X", "Y", "X1", "X2"))
    net.connect(r, x, Axon.SUB, 1)
    net.connect(x, y, Axon.POR, 1)
    net.connect(x, x1, Axon.SUB, 1)
    net.connect(x1, x2, Axon.POR, 1)
    return net, r


def test_trace_depth_first_walk():
    """Trace (1505): down along sub, remember por at the front, then continue with pending.

    Only neurons that go down record their sideways link, so the successor of
    a leaf (X1 -> X2) is not visited. That is the original's behaviour.
    """
    net, root = _tree()
    from psi_gw.memory import SynapseList
    pending = SynapseList()
    seq, cur, direction = [], root, None
    while cur is not None:
        cur, direction = net.trace(cur, Axon.POR, pending, direction)
        if cur is not None:
            seq.append((cur.name, direction.name))
    assert seq == [("X", "SUB"), ("X1", "SUB"), ("Y", "POR")]
    assert direction is Axon.POR  # unchanged by the final, empty step


def test_boss_and_head():
    """Boss (1459) and Kopf (1476) follow the first ret link to the top."""
    net = make_net()
    h, m, t = (net.new_neuron(n) for n in ("H", "M", "T"))
    net.connect(h, m, Axon.POR, 1, Spat(2, 3))
    net.connect(m, t, Axon.POR, 1, Spat(1, -1))
    assert net.boss(t) is h
    top, pos = net.head(t)
    assert top is h and pos == Spat(-3, -2, 0, 0)


def test_situation_list():
    """GenSitList (1401): sub targets of a por chain with accumulated positions, reversed."""
    net = make_net()
    s1, s2, o1, o2 = (net.new_neuron(n) for n in ("s1", "s2", "o1", "o2"))
    net.connect(s1, o1, Axon.SUB, 0.6)
    net.connect(s2, o2, Axon.SUB, 0.7)
    net.connect(s1, s2, Axon.POR, 1, Spat(5, -1))
    lst = net.situation_list(s1, (10, 20))
    assert [(s.target.name, s.weight, s.spat) for s in lst] == [
        ("o2", 0.7, Spat(15, 19, 0, 0)), ("o1", 0.6, Spat(10, 20, 0, 0))]


def test_draw_labels_with_delphi_source():
    net = MemoryNetwork(MemoryParams(), RecordingSource(DelphiRandom(16)), Clock())
    a, b = net.new_neuron("A"), net.new_neuron("B")
    net.connect(a, b, Axon.POR, 0.5)
    net.transmit(a, b, Axon.POR)
    net.reinforce(a, b, Axon.POR, 0.001)
    sites = [d.site for d in net.rng.log]
    assert sites == ["UStrukturen.Decay#1", "UStrukturen.Junction#1", "UStrukturen.Decay#1", "UStrukturen.Decay#1"]
    assert net.rng.log[0].state_before == 16


# --- structure of the original's draws ---------------------------------------------

JUNCTION_DECAY_RET = "0047916A"   # return address of the Decay call inside Junction
REINFORCE_DECAY_RET = ("004793AA", "0047941B")  # the two Decay calls inside ReInforce


@pytest.fixture(scope="module")
def trace_rows():
    with gzip.open(TRACE, "rt", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def test_original_junction_always_preceded_by_its_decay(trace_rows):
    """Every Junction draw directly follows the Decay draw made inside the same Junction call,
    the draw pair that MemoryNetwork.transmit reproduces."""
    pairs = 0
    for prev, row in zip(trace_rows, trace_rows[1:]):
        if row["site"] == "UStrukturen.Junction#1":
            assert prev["site"] == "UStrukturen.Decay#1"
            assert prev["ret1"] == JUNCTION_DECAY_RET
            assert prev["ret2"] == row["ret1"]  # same caller of Junction
            pairs += 1
    assert pairs == 8500


def test_original_decay_callers_are_junction_and_reinforce(trace_rows):
    callers = {r["ret1"] for r in trace_rows if r["site"] == "UStrukturen.Decay#1"}
    assert callers == {JUNCTION_DECAY_RET, *REINFORCE_DECAY_RET}


def test_original_reinforce_decays_come_in_direction_pairs(trace_rows):
    """In ReInforce the forward Decay is followed by the backward Decay (both links exist)."""
    rows = trace_rows[:-1]  # the trace stops after its last draw
    for i, row in enumerate(rows):
        if row["ret1"] == REINFORCE_DECAY_RET[0]:
            assert trace_rows[i + 1]["ret1"] == REINFORCE_DECAY_RET[1]
