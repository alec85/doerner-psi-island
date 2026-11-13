"""Protocol memory: NextName, NewProt, GenProtEl, Protocoll, ReInforceRetro (Issue #18).

Line numbers refer to reference/delphi-original/PsiCode/UStrukturen.Pas.
"""

import csv
import gzip
from pathlib import Path

import pytest

from psi_gw.clock import Clock
from psi_gw.memory import (Axon, MemoryNetwork, MemoryParams, NameGenerator, NilDereference,
                           ProtocolMemory, Spat)
from psi_gw.random_source import DelphiRandom, RecordingSource

ROOT = Path(__file__).resolve().parents[1]
TRACE = ROOT / "traces" / "original-runs" / "2026-11-10-zufallsmitschnitt" / "random_draws.tsv.gz"
REINFORCE_RETRO_RET = "00479C70"  # return address of the ReInforce call inside ReInforceRetro


def make():
    net = MemoryNetwork(MemoryParams(), RecordingSource(DelphiRandom(16)), Clock())
    return net, ProtocolMemory(net)


# --- NextName ----------------------------------------------------------------------

def test_next_name_counts_per_letter():
    """NextName (857): 'aaa' first, then increment the last letter, carry over 'z'."""
    g = NameGenerator()
    assert [g.next_name("P", 0) for _ in range(3)] == ["aaa", "aab", "aac"]
    g.last["P"] = "azz"
    assert g.next_name("P", 0) == "baa"
    g.last["P"] = "zzz"
    assert g.next_name("P", 0) == "zzz"  # exhausted: unchanged, as in the original


def test_next_name_sensory_layers_use_offset_counters():
    """'S' counts under S, T, U for layers 1, 2, 3; T and U start at 'daa' and 'gaa' (InitPsi, 2826)."""
    g = NameGenerator()
    assert g.next_name("S", 1) == "aaa"
    assert g.next_name("S", 2) == "dab"
    assert g.next_name("S", 3) == "gab"
    assert g.next_name("S", 4) == "mab"


def test_next_name_out_of_range():
    with pytest.raises(IndexError):
        NameGenerator().next_name("A", 0)


# --- KZG and protocol chains -----------------------------------------------------------

def test_kzg_neurons():
    net, pm = make()
    assert [n.name for n in pm.kzg] == [f"ShortTerm{i}" for i in range(8)]
    assert pm.head(0) is None


def test_protocol_builds_chain():
    """Protocoll (1750) and GenProtEl (1609): por/ret chain, sub to the protocollandum, weight 1."""
    net, pm = make()
    s1, s2, s3 = (net.new_neuron(n) for n in ("Sx", "Sy", "Sz"))
    p1 = pm.protocol(0, s1, "P", 1000, Spat(1, 2))
    assert net.clock.age == 1  # GenProtEl costs 1
    p2 = pm.protocol(0, s2, "P", 1000, Spat(3, 4))
    assert net.clock.age == 3  # moving the head costs 1 more
    p3 = pm.protocol(0, s3, "P", 1000, Spat())
    assert [p.name for p in (p1, p2, p3)] == ["Paaa", "Paab", "Paac"]
    assert pm.head(0) is p3 and pm.kzg[0].axon[Axon.RET].first.target is p2
    assert p1.axon[Axon.POR].targets() == [p2] and p2.axon[Axon.RET].targets() == [p1]
    assert p2.axon[Axon.POR].targets() == [p3] and p3.axon[Axon.RET].targets() == [p2]
    sub = p2.axon[Axon.SUB][0]
    assert sub.target is s2 and sub.weight == 1.0
    assert s2.axon[Axon.SUR].targets() == [p2]
    # Connect stamps the current age into spat.t: p2 was created at age 2
    assert (sub.spat, p1.axon[Axon.POR][0].spat) == (Spat(3, 4, 0, 2), Spat(3, 4, 0, 2))
    assert pm.last_protocol_time == 4
    assert net.rng.draws == 0


def test_protocol_strength_is_base_reinforcement_times_factor():
    net, pm = make()
    s = net.new_neuron("Sx")
    p = pm.protocol(0, s, "P", 200, Spat())
    assert p.axon[Axon.SUB][0].weight == 0.001 * 200


def test_new_protocol_starts_a_new_chain():
    """NewProt (1559) forgets the head; the old chain stays."""
    net, pm = make()
    a, b = net.new_neuron("Sa"), net.new_neuron("Sb")
    p1 = pm.protocol(1, a, "S", 1000, Spat())
    pm.new_protocol(1)
    p2 = pm.protocol(1, b, "S", 1000, Spat())
    assert (p1.name, p2.name) == ("Saaa", "Saab")
    assert not p2.axon[Axon.RET] and not p1.axon[Axon.POR]
    assert a.axon[Axon.SUR].targets() == [p1]


def test_layers_are_independent():
    net, pm = make()
    s = net.new_neuron("Sa")
    pm.protocol(0, s, "P", 1000, Spat())
    q = pm.protocol(2, s, "S", 1000, Spat())
    assert q.name == "Sdab" and not q.axon[Axon.RET]
    assert s.axon[Axon.SUR].targets() == [q, pm.head(0)]


# --- ReInforceRetro --------------------------------------------------------------------

def situation(net, n, last_has_sub=True):
    """Situation 'Ssit' with sub to a por chain of n elements, each with sub to an object."""
    sit = net.new_neuron("Ssit")
    elements = [net.new_neuron(f"Se{i}") for i in range(n)]
    net.connect(sit, elements[0], Axon.SUB, 0.0)
    for i, e in enumerate(elements):
        if i + 1 < n:
            net.connect(e, elements[i + 1], Axon.POR, 0.0)
        if last_has_sub or i + 1 < n:
            net.connect(e, net.new_neuron(f"So{i}"), Axon.SUB, 0.0)
    return sit, elements


@pytest.mark.parametrize("impulse,steps", [(1.0, 34), (0.5, 17)])
def test_reinforce_retro_step_count(impulse, steps):
    """34 steps for impulse 1, 17 for 0.5; each ReInforce decays both directions (two draws)."""
    net, pm = make()
    sit, _ = situation(net, 30)
    pm.reinforce_retro(sit, impulse)
    assert net.rng.draws == 2 * steps
    assert {d.site for d in net.rng.log} == {"UStrukturen.Decay#1"}


def test_reinforce_retro_order_and_amounts():
    """Down along sub, then sideways along por; r drops by 0.03 per step.

    With weight 0 and no forgetting a reinforced weight becomes r².
    """
    net, pm = make()
    sit, el = situation(net, 3)
    pm.reinforce_retro(sit, 1.0)
    links = [(sit, el[0], Axon.SUB), (el[0], el[0].axon[Axon.SUB][0].target, Axon.SUB),
             (el[0], el[1], Axon.POR), (el[1], el[1].axon[Axon.SUB][0].target, Axon.SUB),
             (el[1], el[2], Axon.POR), (el[2], el[2].axon[Axon.SUB][0].target, Axon.SUB)]
    r = 1.0
    for a, b, axon in links:
        assert net.connected(a, b, axon).weight == r * r
        assert net.connected(b, a, {Axon.SUB: Axon.SUR, Axon.POR: Axon.RET}[axon]).weight == r * r
        r -= 0.03
    assert net.rng.draws == 12  # walk ended after a downward step: clean end


def test_reinforce_retro_dereferences_nil_like_the_original():
    """If the walk ends right after a sideways step, the original follows a nil pointer."""
    net, pm = make()
    sit, _ = situation(net, 3, last_has_sub=False)
    with pytest.raises(NilDereference):
        pm.reinforce_retro(sit, 1.0)


def test_original_reinforce_retro_runs_until_used_up():
    """In the trace every ReInforceRetro call makes 68 or 34 draws (34 or 17 steps, two each);
    runs of 102 are two calls in a row, and the last run is cut off by the end of the trace.
    So the original never ran out of tree, and the nil case was not reached."""
    with gzip.open(TRACE, "rt", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    runs, length = [], 0
    for row in rows:
        if row["ret2"] == REINFORCE_RETRO_RET:
            length += 1
        elif length:
            runs.append(length)
            length = 0
    assert length == 41  # cut off at draw 20000
    assert set(runs) <= {68, 34, 102} and len(runs) == 21


# --- persistence -------------------------------------------------------------------------

def test_snapshot_round_trip():
    net, pm = make()
    s = net.new_neuron("Sa")
    for _ in range(3):
        pm.protocol(0, s, "P", 1000, Spat())
    pm.protocol(2, s, "S", 1000, Spat())
    net2 = MemoryNetwork.restore(net.snapshot(), net.rng, Clock.restore(net.clock.snapshot()))
    pm2 = ProtocolMemory.restore(pm.snapshot(), net2)
    assert pm2.snapshot() == pm.snapshot()
    assert pm2.head(0).name == pm.head(0).name
    assert pm2.protocol(0, net2.neurons[net.neurons.index(s)], "P", 1000, Spat()).name == \
        pm.protocol(0, s, "P", 1000, Spat()).name


# --- LookFor -----------------------------------------------------------------------------

def chain(names):
    """Protocol chain recording neurons with the given names; returns net, pm, elements, recorded."""
    net, pm = make()
    recorded = [net.new_neuron(n) for n in names]
    elements = [pm.protocol(0, r, "P", 1000, Spat()) for r in recorded]
    return net, pm, elements, recorded


def parts(mapping):
    return lambda name: mapping.get(name, f"~~~ [{name}]")


def test_look_for_finds_goal_forward():
    """LookFor (1784): follow por through transmit until an element records the goal."""
    from psi_gw.memory import SynapseList
    net, pm, el, rec = chain(["Sa", "Sb", "Sc"])
    age, draws = net.clock.age, net.rng.draws
    found = pm.look_for(el[0], Axon.POR, rec[2], SynapseList(), parts({}))
    assert found is el[2]
    assert net.rng.draws - draws == 4  # two transmissions, weight 1 always conducts
    assert net.clock.age - age == 2  # 0.5 at the start, 0.5 per step, 0.5 at the goal


def test_look_for_matches_part_name_and_goes_backward():
    from psi_gw.memory import SynapseList
    net, pm, el, rec = chain(["Sa", "Sb", "Sc"])
    other = net.new_neuron("Sx")
    found = pm.look_for(el[2], Axon.RET, other, SynapseList(), parts({"Sa": "Fels3", "Sx": "Fels3"}))
    assert found is el[0]


def test_look_for_stops_at_breakpoint_and_at_end():
    from psi_gw.memory import Synapse, SynapseList
    net, pm, el, rec = chain(["Sa", "Sb", "Sc"])
    assert pm.look_for(el[0], Axon.POR, rec[2], SynapseList([Synapse(rec[1])]), parts({})) is None
    stranger = net.new_neuron("Sz")
    assert pm.look_for(el[0], Axon.POR, stranger, SynapseList(), parts({})) is None


def test_look_for_stops_when_link_does_not_conduct():
    from psi_gw.memory import SynapseList
    net, pm, el, rec = chain(["Sa", "Sb", "Sc"])
    net.connected(el[0], el[1], Axon.POR).weight = 0.0
    draws = net.rng.draws
    assert pm.look_for(el[0], Axon.POR, rec[2], SynapseList(), parts({})) is None
    assert net.rng.draws - draws == 2
