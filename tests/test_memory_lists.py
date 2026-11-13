"""Synapse lists: order semantics of UStrukturen.Pas (Issue #18).

Expected values follow the Pascal code; line numbers in the test names'
docstrings refer to reference/delphi-original/PsiCode/UStrukturen.Pas.
"""

import pytest

from psi_gw.memory import Neuron, Spat, Synapse, SynapseList
from psi_gw.random_source import RecordingSource, ReplaySource


def names(lst: SynapseList) -> list[str]:
    return [s.target.name for s in lst]


@pytest.fixture
def abc():
    return Neuron("A"), Neuron("B"), Neuron("C")


def test_add_front_copies_and_inserts_first(abc):
    """AddListEl (1217): copy target, weight, spat; new element becomes the list head."""
    a, b, _ = abc
    lst = SynapseList()
    tpl = Synapse(a, 0.5, timup=77, spat=Spat(1, 2, 3, 4))
    new = lst.add_front(tpl)
    lst.add_front(Synapse(b, 0.25))
    assert names(lst) == ["B", "A"]
    assert new is not tpl and new.target is a and new.weight == 0.5 and new.spat == Spat(1, 2, 3, 4)
    assert new.timup == 0
    assert lst.add_front(None) is None and len(lst) == 2


def test_append_copy_appends_last(abc):
    """AppListEl (1237)."""
    a, b, c = abc
    lst = SynapseList()
    for n in (a, b, c):
        lst.append_copy(Synapse(n, 0.1))
    assert names(lst) == ["A", "B", "C"]
    assert lst.last().target is c and lst.first.target is a


def test_find_and_remove_first_match(abc):
    """InList (972) and DeListEl (1170) act on the first element with the target."""
    a, b, _ = abc
    lst = SynapseList([Synapse(a, 0.1), Synapse(b, 0.2), Synapse(a, 0.3)])
    assert lst.find(a).weight == 0.1
    assert lst.remove(a) is True
    assert [s.weight for s in lst] == [0.2, 0.3]
    assert lst.remove(Neuron("X")) is False
    lst.clear()
    assert not lst and lst.first is None and lst.last() is None


def test_merge_appends_new_targets_once(abc):
    """LAddition (1272): append targets not yet present, skipping duplicates of the source too."""
    a, b, c = abc
    union = SynapseList([Synapse(a, 0.9)])
    union.merge([Synapse(b, 0.4), Synapse(a, 0.5), Synapse(c, 0.6), Synapse(b, 0.7)])
    assert names(union) == ["A", "B", "C"]
    assert union[0].weight == 0.9
    empty = SynapseList()
    empty.merge(SynapseList([Synapse(c), Synapse(c)]))
    assert names(empty) == ["C"]


def test_copy_targets_zeroes_everything_but_target(abc):
    """CopyList (1374): FillChar zero, then only ThisNeuron is set."""
    a, b, _ = abc
    src = SynapseList([Synapse(a, 0.5, 3, Spat(1, 1, 1, 1)), Synapse(b, 0.7)])
    cp = src.copy_targets()
    assert names(cp) == ["A", "B"]
    assert all(s.weight == 0 and s.timup == 0 and s.spat == Spat() for s in cp)
    assert cp[0] is not src[0]


def test_section_draws_once_per_element_and_reverses(abc):
    """LSection (1312): random drawn first for every element; selected ones go to the front."""
    a, b, c = abc
    list1 = SynapseList([Synapse(a), Synapse(b), Synapse(c)])
    list2 = SynapseList([Synapse(c)])
    # prob 0.5: A passes randomly (0.1), B fails (0.9) and is not in list2, C fails but is in list2
    rng = RecordingSource(ReplaySource([0.1, 0.9, 0.8]))
    result = list1.section(list2, 0.5, rng)
    assert names(result) == ["C", "A"]
    assert [d.site for d in rng.log] == ["UStrukturen.LSection#1"] * 3


def test_section_with_zero_probability_still_draws(abc):
    """Callers in UPSIMain use ProbSelect 0; the draw is consumed anyway."""
    a, b, _ = abc
    rng = ReplaySource([0.0, 0.0])
    result = SynapseList([Synapse(a), Synapse(b)]).section(SynapseList([Synapse(b)]), 0, rng)
    assert names(result) == ["B"] and rng.draws == 2


def test_random_choice_position(abc):
    """RandomChoice (670): j := Random(n) + 1, then the j-th element; no draw on an empty list."""
    a, b, c = abc
    lst = SynapseList([Synapse(a), Synapse(b), Synapse(c)])
    assert lst.random_choice(ReplaySource([0.5])).target is b  # floor(0.5*3) = 1
    assert lst.random_choice(ReplaySource([0.99])).target is c
    rng = ReplaySource([])
    assert SynapseList().random_choice(rng) is None and rng.draws == 0


def test_max_choice_strict_first_maximum(abc):
    """MaxChoice (652): first element with the largest weight, none if all weights <= 0."""
    a, b, c = abc
    lst = SynapseList([Synapse(a, 0.3), Synapse(b, 0.8), Synapse(c, 0.8)])
    assert lst.max_choice().target is b
    assert SynapseList([Synapse(a, 0.0)]).max_choice() is None


def test_has_type():
    """TypInList (624): first letter of a target's name."""
    lst = SynapseList([Synapse(Neuron("Sabc")), Synapse(Neuron("Pa"))])
    assert lst.has_type("P") and not lst.has_type("M")
