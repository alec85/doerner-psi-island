"""Psi's memory network: neurons, axons and synaptic transmission (ADR 0010, Issue #18).

Port of the network operations of ``UStrukturen.Pas`` (line numbers refer to
``reference/delphi-original/PsiCode/UStrukturen.Pas``). In Dörner's theory the
memory consists of quads: neurons linked by four kinds of relation, „por“
(successor), „ret“ (predecessor), „sub“ (part) and „sur“ (whole), plus
connections to needs and goals. Every neuron has one ordered synapse list per
relation („Axon“).

Reading is writing. Whenever Psi follows a synapse (``transmit``, originally
``Junction``), the synapse first forgets according to the time since its last
use (``decay``) and then conducts with a probability equal to its weight; a
conducting synapse is strengthened. Both steps draw random numbers. This is
the one place where reading changes weights; all searches and associations
of later modules go through it.

Reference mode: with a shared ``DelphiRandom`` source this module draws the
same random numbers in the same order as the original, labelled with the call
sites of ``psi_gw.tracing.delphi_random_sites``.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from enum import IntEnum
from typing import Any, Iterable

from psi_gw.clock import Clock
from psi_gw.memory.lists import ZERO_SPAT, NilDereference, Spat, Synapse, SynapseList
from psi_gw.random_source import RandomSource

__all__ = [
    "Axon", "MemoryNetwork", "MemoryParams", "Neuron", "Spat", "Synapse", "SynapseList", "conter",
]

SITE_DECAY = "UStrukturen.Decay#1"
SITE_JUNCTION = "UStrukturen.Junction#1"


class Axon(IntEnum):
    """Kinds of relation of a neuron (``TAxon``).

    Members in the order of the original, so ``int(axon)`` is the Pascal
    ordinal.
    """

    POR = 0
    """„por“: successor in a sequence (Nachfolger)."""
    RET = 1
    """„ret“: predecessor in a sequence (Vorgänger)."""
    SUB = 2
    """„sub“: part of (Teil)."""
    SUR = 3
    """„sur“: whole of (Ganzes)."""
    TO_SATIS = 4
    """„toSatis“: link to the satisfaction of a need."""
    TO_GOAL = 5
    """„toGoal“: link to a goal."""
    TO_NEED = 6
    """„toNeed“: link to a need."""
    TO_AVERS = 7
    """„ToAvers“: link to an aversive event."""
    LAN = 8
    """„Lan“: language."""
    PIC = 9
    """„Pic“: picture."""


_CONTER = {
    Axon.POR: Axon.RET, Axon.RET: Axon.POR,
    Axon.SUB: Axon.SUR, Axon.SUR: Axon.SUB,
    Axon.TO_SATIS: Axon.TO_GOAL, Axon.TO_GOAL: Axon.TO_SATIS,
    Axon.TO_NEED: Axon.TO_AVERS, Axon.TO_AVERS: Axon.TO_NEED,
}


def conter(axon: Axon) -> Axon:
    """Counter relation („Konterrelation“, ``Conter``, line 993).

    ``Lan`` and ``Pic`` have no counter relation; the original returns
    ``ret`` for them.
    """
    return _CONTER.get(axon, Axon.RET)


class Neuron:
    """A node of the memory network (record ``Neuron``).

    Attributes:
        name: name of the neuron („namneuron“); the first letter gives its
            kind, e.g. ``P`` protocol, ``S`` sensory.
        activity: own activity („activity“). Unused by most of Psi, which
            spreads activation by building lists; ``-1`` marks „not used“
            (``InitNeuron``, line 1437).
        axon: one ordered ``SynapseList`` per relation, indexed by ``Axon``.
    """

    __slots__ = ("name", "activity", "axon")

    def __init__(self, name: str = "") -> None:
        self.name = name
        self.activity = -1.0
        self.axon = [SynapseList() for _ in Axon]

    def __repr__(self) -> str:
        return f"Neuron({self.name!r})"


@dataclass(frozen=True, slots=True)
class MemoryParams:
    """Memory parameters („Gedächtnisparameter“, first block of ``Param.Dat``).

    Defaults are the values of ``PsiDaten/InselIII/Param.Dat``, which the
    reference runs use. Note that forgetting is switched off there.

    Attributes:
        forgetting_rate: „Vergessensrate“ (``param[VergessensRate]``).
        protocol_factor: „Protokollfaktor“ (``param[ProtokollFaktor]``).
        base_reinforcement: „Grundverstärkung“ (``param[GVerstaerkung]``).
        max_weight: maximal synaptic weight („maximales neuronales
            Übergangsgewicht“, ``maxweight``, set in ``InitPsi``).
    """

    forgetting_rate: float = 0.0
    protocol_factor: float = 1000.0
    base_reinforcement: float = 0.001
    max_weight: float = 1.0


class MemoryNetwork:
    """All neurons of one Psi and the operations on their synapses.

    The network owns its neurons (in creation order, which defines their
    index in snapshots), reads age from a shared ``Clock`` and draws from a
    shared ``RandomSource``.
    """

    def __init__(self, params: MemoryParams, rng: RandomSource, clock: Clock) -> None:
        self.params = params
        self.rng = rng
        self.clock = clock
        self.neurons: list[Neuron] = []

    # --- neurons -----------------------------------------------------------------

    def new_neuron(self, name: str = "") -> Neuron:
        """Create and register a neuron (``InitNeuron``, line 1437)."""
        neuron = Neuron(name)
        self.neurons.append(neuron)
        return neuron

    def dispose_neuron(self, neuron: Neuron) -> None:
        """``DisposeNeuron`` (UStrukturen 538): delete a neuron and the links pointing back to it.

        For every link of the neuron, the first back link of the target (on the
        counter relation) is removed. Then the neuron leaves the network.
        """
        for axon in Axon:
            for syn in list(neuron.axon[axon]):
                if syn.target is not None:
                    syn.target.axon[conter(axon)].remove(neuron)
            neuron.axon[axon] = SynapseList()
        self.neurons.remove(neuron)

    # --- structure -----------------------------------------------------------------

    @staticmethod
    def connected(a: Neuron, b: Neuron, axon: Axon) -> Synapse | None:
        """Synapse from ``a`` to ``b`` on ``axon``, if any (``Connected``, line 1008)."""
        return a.axon[axon].find(b)

    def connect_one_way(self, a: Neuron, b: Neuron, axon: Axon, strength: float, spat: Spat) -> None:
        """Link ``a`` to ``b`` on ``axon`` unless already linked (``ConnectVonNach``, line 1101).

        The new synapse goes to the front of the list, with weight
        ``min(strength, max_weight)`` and ``timup`` set to the current age.
        """
        if a.axon[axon].find(b) is not None:
            return
        syn = a.axon[axon].add_front(Synapse(b, 0.0, 0, ZERO_SPAT))
        assert syn is not None
        syn.weight = strength if strength <= self.params.max_weight else self.params.max_weight
        syn.timup = self.clock.age
        syn.spat = spat

    def connect(self, a: Neuron, b: Neuron, axon: Axon, strength: float, spat: Spat = ZERO_SPAT) -> None:
        """Link ``a`` to ``b`` on ``axon`` and ``b`` to ``a`` on the counter relation (``Connect``, line 1124).

        ``spat.z`` is set to 0 and ``spat.t`` to the current age; the back link
        carries the negated relation.
        """
        forward = Spat(spat.x, spat.y, 0, self.clock.age)
        self.connect_one_way(a, b, axon, strength, forward)
        self.connect_one_way(b, a, conter(axon), strength, -forward)

    @staticmethod
    def disconnect(a: Neuron, b: Neuron, axon: Axon) -> None:
        """Remove the link from ``a`` to ``b`` on ``axon`` (``Disconnect``, line 1209)."""
        a.axon[axon].remove(b)

    # --- weights -----------------------------------------------------------------

    def decay(self, syn: Synapse) -> None:
        """Forget according to the time since the last refresh (``Decay``, line 1030).

        Always one random draw. With ``r = min(weight², 1)``::

            r := r - random * (age - timup) * Vergessensrate;  r := max(r, 0)
            weight := sqrt(r);  timup := age
        """
        age = self.clock.age
        elapsed = age - syn.timup
        r = syn.weight * syn.weight
        if r > 1:
            r = 1.0
        r = r - self.rng.random(site=SITE_DECAY) * elapsed * self.params.forgetting_rate
        if r < 0:
            r = 0.0
        syn.weight = math.sqrt(r)
        syn.timup = age

    def _strengthen(self, syn: Synapse, amount: float, cap: float) -> None:
        weight = math.sqrt(syn.weight) + amount
        weight = weight * weight
        syn.weight = cap if weight > cap else weight

    def reinforce(self, a: Neuron, b: Neuron, axon: Axon, amount: float) -> None:
        """Strengthen the link between ``a`` and ``b`` in both directions (``ReInforce``, line 1137).

        Each existing direction first decays (one draw), then
        ``weight := min((sqrt(weight) + amount)², max_weight)``.
        """
        syn = a.axon[axon].find(b)
        if syn is not None:
            self.decay(syn)
            self._strengthen(syn, amount, self.params.max_weight)
        syn = b.axon[conter(axon)].find(a)
        if syn is not None:
            self.decay(syn)
            self._strengthen(syn, amount, self.params.max_weight)

    def transmit(self, source: Neuron, target: Neuron, axon: Axon) -> Synapse | None:
        """Try to pass activation from ``source`` to ``target`` along ``axon`` (``Junction``, line 1049).

        Finds the first synapse to ``target``; if there is none, nothing
        happens and nothing is drawn. Otherwise the synapse decays (one
        draw) and conducts if ``random < weight`` (second draw). A conducting
        synapse is strengthened by the base reinforcement, capped at 1.

        Returns the synapse if it conducted, else ``None``. (The original
        returns a boolean and sets a ``var`` pointer only on success.)
        """
        syn = source.axon[axon].find(target)
        if syn is None:
            return None
        self.decay(syn)
        # Junction weights by r = 1; using the neuron's activity is commented
        # out in the original.
        if self.rng.random(site=SITE_JUNCTION) < syn.weight:
            self._strengthen(syn, self.params.base_reinforcement, 1.0)
            return syn
        return None

    # --- traversal -----------------------------------------------------------------

    @staticmethod
    def trace(current: Neuron, por_or_ret: Axon, pending: SynapseList,
              direction: Axon | None) -> tuple[Neuron | None, Axon | None]:
        """One step of a depth-first walk through a tree of quads (``Trace``, line 1505).

        Goes down along ``sub`` if possible, remembering the first sideways
        synapse (``por_or_ret`` for protocol neurons, ``por`` otherwise) at the
        front of ``pending``. Without ``sub`` it continues with the first
        pending neuron. Only neurons with a ``sub`` link record their
        sideways link, so successors of leaves are not visited. Returns the next neuron (``None`` when the tree is
        exhausted) and the direction taken; ``direction`` is returned unchanged
        if no step was possible, as the ``var`` parameter in the original.
        """
        sub = current.axon[Axon.SUB].first
        if sub is not None:
            nxt = sub.target
            side = por_or_ret if current.name[:1] == "P" else Axon.POR
            if current.axon[side]:
                pending.add_front(current.axon[side].first)
            return nxt, Axon.SUB
        if pending:
            nxt = pending.first.target  # type: ignore[union-attr]
            direction = Axon.RET if nxt.name[:1] == "P" else Axon.POR
            pending.remove(nxt)
            return nxt, direction
        return None, direction

    @staticmethod
    def boss(neuron: Neuron) -> Neuron:
        """Top of a schema: follow the first ``ret`` link to the end (``Boss``, line 1459)."""
        while neuron.axon[Axon.RET]:
            neuron = neuron.axon[Axon.RET].first.target  # type: ignore[union-attr]
        return neuron

    @staticmethod
    def head(neuron: Neuron) -> tuple[Neuron, Spat]:
        """Head of a schema and its position relative to ``neuron`` (``Kopf``, line 1476).

        Sums the ``x`` and ``y`` offsets of the ``ret`` links followed.
        """
        x = y = 0
        ret = Axon.RET
        items = neuron.axon[ret]._items  # hot path: list access without the property
        while items:
            syn = items[0]
            x += syn.spat.x
            y += syn.spat.y
            neuron = syn.target  # type: ignore[assignment]
            items = neuron.axon[ret]._items
        # DEVIATION(ADR-0010): SpaTAdd leaves z and t of its result unset;
        # they are 0 here (the value Locus starts with).
        return neuron, Spat(x, y, 0, 0)

    @staticmethod
    def situation_list(start: Neuron | None, origin: tuple[int, int]) -> SynapseList:
        """Objects of a situation with their positions (``GenSitList``, line 1401).

        Walks the ``por`` chain from ``start``. For each element the first
        ``sub`` synapse (target and weight) is added at the front of the
        result, with ``x``/``y`` set to the accumulated position starting at
        ``origin`` (``LocSit`` in the original). The result is in reverse
        order of the chain.
        """
        result = SynapseList()
        x, y = origin
        neuron = start
        while neuron is not None:
            sub = neuron.axon[Axon.SUB].first
            if sub is None:
                raise NilDereference(f"GenSitList: {neuron!r} has no sub link")
            result.add_front(Synapse(sub.target, sub.weight, 0, Spat(x, y, 0, 0)))
            por = neuron.axon[Axon.POR].first
            if por is None:
                break
            x += por.spat.x
            y += por.spat.y
            neuron = por.target
        return result

    # --- persistence -----------------------------------------------------------------

    def snapshot(self, extra: Iterable[Neuron | None] = ()) -> dict[str, Any]:
        """Complete state of the network as a JSON compatible dict.

        Clock and random source are shared with other components and are
        saved by their owner (``PsiState``).

        Disposed neurons can still be referenced, as dangling pointers are in
        the original (e.g. ``kzg[2]`` after perception disposed a protocol
        element; ``NewProt`` clears it before the next use). They are stored as
        ``detached``: restored as neurons outside the network, so references
        stay the same objects. ``extra`` lists further references (from the
        state) to check. ``snapshot_ids`` afterwards maps ``id(neuron)`` to
        the index used in the snapshot.
        """
        ids = {id(n): i for i, n in enumerate(self.neurons)}
        detached: list[Neuron] = []

        def visit(n: Neuron | None) -> None:
            if n is not None and id(n) not in ids:
                ids[id(n)] = len(self.neurons) + len(detached)
                detached.append(n)

        for n in self.neurons:
            for a in Axon:
                for s in n.axon[a]:
                    visit(s.target)
        for n in extra:
            visit(n)
        k = 0
        while k < len(detached):
            for a in Axon:
                for s in detached[k].axon[a]:
                    visit(s.target)
            k += 1
        self.snapshot_ids = ids

        def item(n: Neuron) -> dict[str, Any]:
            return {"name": n.name, "activity": n.activity,
                    "axon": {a.name: n.axon[a].snapshot(ids) for a in Axon if n.axon[a]}}

        return {
            "params": asdict(self.params),
            "neurons": [item(n) for n in self.neurons],
            "detached": [item(n) for n in detached],
        }

    @classmethod
    def restore(cls, data: dict[str, Any], rng: RandomSource, clock: Clock) -> "MemoryNetwork":
        net = cls(MemoryParams(**data["params"]), rng, clock)
        for item in data["neurons"]:
            neuron = net.new_neuron(item["name"])
            neuron.activity = item["activity"]
        detached = []
        for item in data.get("detached", []):
            neuron = Neuron(item["name"])
            neuron.activity = item["activity"]
            detached.append(neuron)
        everything = net.neurons + detached
        for neuron, item in zip(everything, data["neurons"] + data.get("detached", [])):
            for name, syns in item["axon"].items():
                neuron.axon[Axon[name]] = SynapseList.restore(syns, everything)
        net.restored_neurons = everything
        """Live and detached neurons in snapshot order, for resolving references after ``restore``."""
        return net
