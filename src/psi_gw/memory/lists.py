"""Synapses and ordered synapse lists (ADR 0010, Issue #18).

In the original (``UStrukturen.Pas``) a synapse is an element of a doubly
linked list (record ``Syn``): every axon of a neuron is such a list, and the
same element type serves as a general list of neurons for working memory
(situation lists, candidate lists, ...). Order matters everywhere: searches
stop at the first match, ``RandomChoice`` counts positions, and the order in
which the network is traversed fixes the order of random draws
(docs/zufallsmitschnitt.md).

``SynapseList`` keeps that order semantics exactly, on top of a Python list:

* ``add_front`` is ``AddListEl`` (insert a copy at the front),
* ``append_copy`` is ``AppListEl`` (append a copy at the back),
* ``find`` is ``InList`` (first element pointing to a neuron),
* ``remove`` is ``DeListEl`` (remove the first such element).

Line numbers refer to ``reference/delphi-original/PsiCode/UStrukturen.Pas``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable, Iterator, NamedTuple

if TYPE_CHECKING:
    from psi_gw.memory.network import Neuron
    from psi_gw.random_source import RandomSource


class NilDereference(RuntimeError):
    """The original would dereference a nil pointer here (access violation).

    Raised where the Pascal code follows a pointer without checking it, so
    the situation becomes visible instead of being papered over. Whether the
    original ever reaches such a point is checked against its traces.
    """


class Spat(NamedTuple):
    """Spatial and temporal relation carried by a synapse („SpaT“, type ``TSpat``).

    ``x``, ``y``: spatial offset between the connected quads; ``z``: unused in
    the island world (set to 0 by ``Connect``); ``t``: age at connection time.
    """

    x: int = 0
    y: int = 0
    z: int = 0
    t: int = 0

    def __neg__(self) -> "Spat":
        return Spat(-self.x, -self.y, -self.z, -self.t)


ZERO_SPAT = Spat()


class Synapse:
    """Connection to a neuron, element of a synapse list (record ``Syn``).

    Attributes:
        target: neuron the synapse points to (``ThisNeuron``).
        weight: transmission weight („Gewicht“), in [0, ``maxweight``].
        timup: age of the last refresh („Auffrischung“); ``Decay`` forgets in
            proportion to ``age - timup``.
        spat: spatial and temporal relation („SpaT“).
    """

    __slots__ = ("target", "weight", "timup", "spat")

    # DEVIATION(ADR-0005): ``weight`` is ``extended`` (80 bit) in the original
    # and a 64-bit float here. Comparisons such as ``random < weight`` can
    # therefore tip in rare cases; draw-by-draw comparisons will show where.

    def __init__(self, target: Neuron | None = None, weight: float = 0.0,
                 timup: int = 0, spat: Spat = ZERO_SPAT) -> None:
        self.target = target
        self.weight = weight
        self.timup = timup
        self.spat = spat

    def __repr__(self) -> str:
        name = None if self.target is None else self.target.name
        return f"Synapse({name!r}, weight={self.weight!r}, timup={self.timup}, spat={tuple(self.spat)})"


class SynapseList:
    """Ordered list of synapses with the semantics of the original's linked lists."""

    __slots__ = ("_items",)

    def __init__(self, items: Iterable[Synapse] = ()) -> None:
        self._items: list[Synapse] = list(items)

    # --- inspection ------------------------------------------------------------

    def __iter__(self) -> Iterator[Synapse]:
        return iter(self._items)

    def __len__(self) -> int:
        """Number of elements (``NListEl``, line 1157)."""
        return len(self._items)

    def __bool__(self) -> bool:
        return bool(self._items)

    def __getitem__(self, index: int) -> Synapse:
        return self._items[index]

    def __repr__(self) -> str:
        return f"SynapseList({[None if s.target is None else s.target.name for s in self._items]})"

    @property
    def first(self) -> Synapse | None:
        """First element, the list pointer itself in the original; ``None`` if empty."""
        return self._items[0] if self._items else None

    def last(self) -> Synapse | None:
        """Last element (``EndeDerListe``, line 958); ``None`` if empty."""
        return self._items[-1] if self._items else None

    def targets(self) -> list[Neuron | None]:
        return [s.target for s in self._items]

    def find(self, neuron: Neuron | None) -> Synapse | None:
        """First element pointing to ``neuron`` (``InList``, line 972)."""
        for syn in self._items:
            if syn.target is neuron:
                return syn
        return None

    def index_of(self, neuron: Neuron | None) -> int:
        """Position of the first element pointing to ``neuron``, or -1."""
        for i, syn in enumerate(self._items):
            if syn.target is neuron:
                return i
        return -1

    def has_type(self, typ: str) -> bool:
        """True if a target's name starts with ``typ`` (``TypInList``, line 624).

        Neuron names start with a type letter, e.g. ``P`` for protocol neurons.
        """
        return any(s.target.name[:1] == typ for s in self._items)

    # --- changes in place --------------------------------------------------------

    def add_front(self, template: Synapse | None) -> Synapse | None:
        """Insert a copy of ``template`` at the front (``AddListEl``, line 1217).

        Copied are target, weight and spat. ``timup`` is not copied; it stays
        undefined in the original and is 0 here. Callers that create real
        synapses set it afterwards (``ConnectVonNach``). A ``None`` template
        does nothing, as in the original. Returns the new element.
        """
        if template is None:
            return None
        # DEVIATION(ADR-0010): timup of the copy is uninitialised heap memory in
        # the original; 0 here. Only Decay reads timup, and it runs only on
        # axon lists, whose elements all come from ConnectVonNach, which sets
        # timup (all writes to axon lists checked in the source).
        syn = Synapse(template.target, template.weight, 0, template.spat)
        self._items.insert(0, syn)
        return syn

    def append_copy(self, template: Synapse | None) -> Synapse | None:
        """Append a copy of ``template`` at the back (``AppListEl``, line 1237).

        Same copy rules as :meth:`add_front`.
        """
        if template is None:
            return None
        # DEVIATION(ADR-0010): timup uninitialised in the original; 0 here.
        syn = Synapse(template.target, template.weight, 0, template.spat)
        self._items.append(syn)
        return syn

    def remove(self, neuron: Neuron | None) -> bool:
        """Remove the first element pointing to ``neuron`` (``DeListEl``, line 1170).

        Returns True if an element was removed.
        """
        i = self.index_of(neuron)
        if i < 0:
            return False
        del self._items[i]
        return True

    def clear(self) -> None:
        """Remove all elements (``Delist``, line 1196)."""
        self._items.clear()

    def merge(self, other: Iterable[Synapse]) -> None:
        """Append targets of ``other`` not yet in this list (``LAddition``, line 1272).

        New elements carry only the target; duplicates within ``other`` are
        skipped as well, because each new element is linked into the list
        before the next one is checked.
        """
        for syn in other:
            if self.find(syn.target) is None:
                # DEVIATION(ADR-0010): weight and timup of the new element are
                # uninitialised heap memory in the original; 0 here. The
                # callers (Association in UPSIMain, InitPsi, TFPsi) read only
                # the targets of these lists.
                self._items.append(Synapse(syn.target))

    # --- new lists ---------------------------------------------------------------

    def copy_targets(self) -> "SynapseList":
        """New list with the same targets, weights and spat zero (``CopyList``, line 1374)."""
        return SynapseList(Synapse(s.target) for s in self._items)

    def section(self, other: "SynapseList", prob_select: float, rng: RandomSource) -> "SynapseList":
        """Elements of this list that are in ``other`` or pass a random test (``LSection``, line 1312).

        One random draw per element, always, even for ``prob_select`` 0
        (``random < ProbSelect`` is evaluated first). Selected elements are
        inserted at the front, so the result is in reverse order.
        """
        result = SynapseList()
        for syn in self._items:
            if rng.random(site="UStrukturen.LSection#1") < prob_select or other.find(syn.target) is not None:
                result.add_front(syn)
        return result

    def random_choice(self, rng: RandomSource) -> Synapse | None:
        """Element at a random position (``RandomChoice``, line 670); no draw if empty."""
        n = len(self._items)
        if n == 0:
            return None
        return self._items[rng.randint(n, site="UStrukturen.RandomChoice#1")]

    def max_choice(self) -> Synapse | None:
        """First element with the largest weight above 0 (``MaxChoice``, line 652)."""
        best, best_weight = None, 0.0
        for syn in self._items:
            if syn.weight > best_weight:
                best, best_weight = syn, syn.weight
        return best

    # --- persistence ---------------------------------------------------------------

    def snapshot(self, neuron_id: dict[int, int]) -> list[list[Any]]:
        """JSON compatible form; ``neuron_id`` maps ``id(neuron)`` to its index."""
        return [[None if s.target is None else neuron_id[id(s.target)], s.weight, s.timup, list(s.spat)]
                for s in self._items]

    @classmethod
    def restore(cls, data: list[list[Any]], neurons: list[Neuron]) -> "SynapseList":
        return cls(Synapse(None if t is None else neurons[t], w, timup, Spat(*spat))
                   for t, w, timup, spat in data)
