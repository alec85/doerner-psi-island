"""Protocol memory: Psi's autobiographical record (ADR 0010, Issue #18).

Port of ``NewProt``, ``GenProtEl``, ``Protocoll``, ``ReInforceRetro`` and ``LookFor`` from
``UStrukturen.Pas`` (line numbers refer to
``reference/delphi-original/PsiCode/UStrukturen.Pas``).

Psi records what it perceives and does as chains of protocol neurons
(„Protokollelemente“). Each element points ``sub`` to what it records (a
situation, an object, an action) and is linked ``por``/``ret`` to its
predecessor. Several chains run in parallel, one per layer: layer 0 is the
main protocol of situations and actions (kind ``P``), layers 1 to 3 record
perception in finer grain (kind ``S``).

The head of each chain is held by a short-term memory neuron
(„Kurzzeitgedächtnis“, ``kzg[i]``, named ``ShortTerm<i>``). Its ``sub`` list
holds a single element pointing to the current protocol element and its
``ret`` list a single element pointing to the previous one. These two lists
are registers, not synapses: only their target is used.

The original writes each new ``P`` element to the activity protocol
(``actu<seed>.Prt``). The port does not write files; structured events for
that output follow with ``psi_gw.tracing`` (ADR 0010).
"""

from __future__ import annotations

from typing import Any, Callable

from psi_gw.memory.lists import NilDereference, Spat, Synapse, SynapseList
from psi_gw.memory.names import NameGenerator
from psi_gw.memory.network import Axon, MemoryNetwork, Neuron, conter

MAX_KZG = 7
"""Highest index of the short-term memory neurons („maxkzg“)."""

RETRO_DECREMENT = 0.03
"""Decrease of the reinforcement per step in ``ReInforceRetro``."""


class ProtocolMemory:
    """Short-term memory heads and the protocol chains they grow.

    Attributes:
        net: the memory network the protocol neurons live in.
        names: name counters for new neurons (``NextName``).
        kzg: short-term memory neurons ``kzg[0..MAX_KZG]`` („KZG“).
        last_protocol_time: age at the last linked protocol element
            (``lastprotime``). Written, but read nowhere in the original.
    """

    def __init__(self, net: MemoryNetwork, names: NameGenerator | None = None,
                 kzg: list[Neuron] | None = None) -> None:
        self.net = net
        self.names = names if names is not None else NameGenerator()
        # InitPsi, line 2803: kzg[i] := InitNeuron, named 'ShortTerm<i>'.
        self.kzg = kzg if kzg is not None else [net.new_neuron(f"ShortTerm{i}") for i in range(MAX_KZG + 1)]
        self.last_protocol_time = 0
        self.prn = None
        """Optional text sink for the original's protocol lines (``psi_gw.prn.Prn``)."""
        self.part_name: Callable[[str], str] | None = None
        """``GetPartName`` for those lines."""

    def head(self, layer: int) -> Neuron | None:
        """Current protocol element of a layer (``kzg[layer]^.axon[sub]^.thisneuron``)."""
        first = self.kzg[layer].axon[Axon.SUB].first
        return None if first is None else first.target

    def new_protocol(self, layer: int) -> None:
        """Free a short-term memory neuron for a new chain (``NewProt``, line 1559).

        Clears its ``por``, ``ret`` and ``sub`` lists. The old chain stays in
        memory; only the head is forgotten.
        """
        for axon in (Axon.POR, Axon.RET, Axon.SUB):
            self.kzg[layer].axon[axon] = SynapseList()

    def generate_element(self, protocollandum: Neuron, antecedent: Neuron | None, kind: str,
                         layer: int, strength: float, spat: Spat) -> Neuron:
        """Create a protocol element (``GenProtEl``, line 1609).

        The new neuron is named ``kind`` plus the next name of its layer. It is
        linked ``por`` from ``antecedent`` (if any) and ``sub`` to
        ``protocollandum``, both with ``strength`` and in both directions.
        Costs one unit of time.
        """
        net = self.net
        neuron = net.new_neuron(kind + self.names.next_name(kind, layer))
        if antecedent is not None:
            # The original sets spat.t to the time since the last element;
            # Connect overwrites it with the current age, so only
            # lastprotime is affected.
            spat = Spat(spat.x, spat.y, spat.z, net.clock.age - self.last_protocol_time)
            self.last_protocol_time = net.clock.age
            net.connect(antecedent, neuron, Axon.POR, strength, spat)
        net.connect(neuron, protocollandum, Axon.SUB, strength, spat)
        if kind == "P" and self.prn is not None:
            part = self.part_name(protocollandum.name) if self.part_name else ""
            self.prn.writeln(f"{neuron.name}->{protocollandum.name} {part} "
                             f"{neuron.axon[Axon.SUB].first.weight:7.5f}")
        net.clock.advance(1)
        return neuron

    def protocol(self, layer: int, protocollandum: Neuron, kind: str, strength: float, spat: Spat) -> Neuron:
        """Append ``protocollandum`` to the chain of a layer (``Protocoll``, line 1750).

        The current element becomes the previous one (costs one unit of
        time if there was one), and a new element linked to it with weight
        ``Grundverstärkung * strength`` becomes the current one. Callers pass
        the protocol factor as ``strength``, so with the island parameters
        new links get weight 0.001 * 1000 = 1. Returns the new element.
        """
        reinforcement = self.net.params.base_reinforcement * strength
        head = self.kzg[layer]
        sub, ret = head.axon[Axon.SUB], head.axon[Axon.RET]
        if sub:
            if not ret:
                # DEVIATION(ADR-0010): register element from InitSyn; its
                # weight is uninitialised in the original and never read.
                ret.append_copy(Synapse())
            ret.first.target = sub.first.target  # type: ignore[union-attr]
            self.net.clock.advance(1)
        else:
            sub.append_copy(Synapse())  # DEVIATION(ADR-0010): as above
        antecedent = ret.first.target if ret else None  # type: ignore[union-attr]
        element = self.generate_element(protocollandum, antecedent, kind, layer, reinforcement, spat)
        sub.first.target = element  # type: ignore[union-attr]
        return element

    def reinforce_retro(self, start: Neuron, impulse: float) -> None:
        """Reinforce the structure below ``start`` after a need was met or hurt (``ReInforceRetro``, line 1536).

        Walks the tree below ``start`` with ``MemoryNetwork.trace`` (sideways
        along ``ret`` for protocol neurons, ``por`` otherwise) and reinforces
        every link it follows, starting with ``impulse`` and decreasing by
        0.03 per step until the reinforcement is used up or the walk ends.
        In the original both callers (UAction.pas, lines 91 and 144) pass the
        current situation, with impulse 1 after satisfaction and 0.5 after
        pain, i.e. 34 or 17 steps.

        Raises:
            NilDereference: where the original would follow a nil pointer:
                the walk ends right after a sideways step, or the reached
                neuron has no link back.
        """
        net = self.net
        pending = SynapseList()
        current: Neuron | None = start
        direction: Axon | None = None  # uninitialised in the original
        r = impulse
        if self.prn is not None:
            self.prn.writeln(f"  -* Consum-Verstärkung ab {start.name}")
        while True:
            nxt, direction = net.trace(current, Axon.RET, pending, direction)  # type: ignore[arg-type]
            if direction is not Axon.SUB:
                if nxt is None:
                    raise NilDereference(f"ReInforceRetro: walk from {start!r} ended after a sideways step")
                back = nxt.axon[conter(direction)].first  # type: ignore[arg-type]
                if back is None:
                    raise NilDereference(f"ReInforceRetro: {nxt!r} has no {conter(direction).name} link")  # type: ignore[arg-type]
                current = back.target
            if nxt is not None:
                net.reinforce(current, nxt, direction, r)  # type: ignore[arg-type]
                # DEVIATION(ADR-0005): r is a 64-bit real, but the original
                # subtracts in 80-bit precision before rounding.
                r = r - RETRO_DECREMENT
            current = nxt
            if current is None or r <= 0:
                break

    def look_for(self, start: Neuron, direction: Axon, goal: Neuron, breakpoints: SynapseList,
                 part_name: Callable[[str], str]) -> Neuron | None:
        """Search a protocol chain for an element recording ``goal`` (``LookFor``, line 1784).

        Starting at the protocol element ``start``, follows ``direction``
        (``por`` or ``ret``) through ``transmit`` until an element records
        ``goal`` or a neuron with the same part name. The search stops without
        result when a link does not conduct, the chain ends, or an element
        records a neuron listed in ``breakpoints``.

        Args:
            part_name: maps a neuron name to the name of the world object part
                it stands for (``GetPartName``, i.e. ``PsiClient.PartList.GetName``).
                For unknown names the original returns ``'~~~ [' + name + ']'``;
                the function passed here must do the same.

        Returns:
            The element found, or ``None``.

        Raises:
            NilDereference: if an element on the way has no ``sub`` link.
        """
        net = self.net
        goal_name = part_name(goal.name)
        net.clock.advance(0.5)
        element = start
        while True:
            recorded = element.axon[Axon.SUB].first
            if recorded is None:
                raise NilDereference(f"LookFor: {element!r} has no sub link")
            if breakpoints.find(recorded.target) is not None:
                return None
            if recorded.target is goal or part_name(recorded.target.name) == goal_name:  # type: ignore[union-attr]
                net.clock.advance(0.5)
                return element
            nxt = element.axon[direction].first
            if nxt is None:
                return None
            net.clock.advance(0.5)
            if net.transmit(element, nxt.target, direction) is None:  # type: ignore[arg-type]
                return None
            element = nxt.target  # type: ignore[assignment]

    # --- persistence -----------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        """State besides the network itself (which ``MemoryNetwork.snapshot`` covers)."""
        index = {id(n): i for i, n in enumerate(self.net.neurons)}
        return {"kzg": [index[id(n)] for n in self.kzg], "last_protocol_time": self.last_protocol_time,
                "names": self.names.snapshot()}

    @classmethod
    def restore(cls, data: dict[str, Any], net: MemoryNetwork) -> "ProtocolMemory":
        mem = cls(net, NameGenerator.restore(data["names"]), [net.neurons[i] for i in data["kzg"]])
        mem.last_protocol_time = data["last_protocol_time"]
        return mem
