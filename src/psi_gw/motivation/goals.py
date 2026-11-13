"""Goal selection: ``GoalGen`` and ``InterMedGoals`` (UPSIMain.Pas, lines 1500 and 1453; ADR 0010).

Each need indicator is linked ``toGoal`` to the sensory schemata that once
satisfied it („Ziele“). ``GoalGen`` builds the current goal list: first the
goals of the current motive (main goals, „Hauptziele“), then those of the
other needs (background goals, „Hintergrundziele“). A goal enters the list if
the link still conducts and a random test passes; for background goals the
chance shrinks with the strength of the current motive and the selection
threshold. For every accepted goal, ``InterMedGoals`` adds intermediate goals
(„Zwischenziele“): situations from which a manipulation once led to it.
"""

from __future__ import annotations

from typing import Callable

from psi_gw.counters import IntProc
from psi_gw.memory.lists import NilDereference, SynapseList
from psi_gw.memory.network import Axon, Neuron
from psi_gw.motivation.needs import NEEDS, Modulator, Motive
from psi_gw.motivation.system import Motivation

SITE_GOALGEN = "UPSIMain.GoalGen#1"


def intermediate_goals(mot: Motivation, end_goal: Neuron, goal_list: SynapseList,
                       mani_actors: SynapseList, derived: dict | None = None) -> None:
    """Add intermediate goals for ``end_goal`` (``InterMedGoals``, UPSIMain 1453).

    For each protocol element recording ``end_goal`` (its ``sur`` list): if
    the element before it records a manipulation, and the element before that
    can be reached, the situation that element records becomes a goal (appended
    at the end of the list, if not yet in it). Each step goes through
    ``transmit`` and costs time.

    ``derived`` (optional, workspace): records ``id(intermediate goal) -> end_goal``;
    recording has no effect on Psi.
    """
    net, clock = mot.net, mot.clock
    for si in list(end_goal.axon[Axon.SUR]):
        sen_schema = si.target
        ret = sen_schema.axon[Axon.RET].first
        if ret is None:
            continue
        mot_schema = ret.target
        clock.advance(1)
        if net.transmit(sen_schema, mot_schema, Axon.RET) is None:
            continue
        clock.advance(1)
        sub = mot_schema.axon[Axon.SUB].first
        if sub is None:
            continue
        clock.advance(1)
        if mani_actors.find(sub.target) is None:
            continue
        ante = mot_schema.axon[Axon.RET].first
        if ante is None:
            continue
        clock.advance(1)
        ante_sen = ante.target
        if net.transmit(mot_schema, ante_sen, Axon.RET) is None:
            continue
        clock.advance(1)
        goal = ante_sen.axon[Axon.SUB].first
        if goal is None:
            raise NilDereference(f"InterMedGoals: {ante_sen!r} has no sub link")
        if derived is not None and goal.target is not None:
            derived.setdefault(id(goal.target), end_goal)
        if goal_list.find(goal.target) is None:
            goal_list.append_copy(goal)
            mot.counters.count(IntProc.MiGo)


def goal_gen(mot: Motivation, goal_list: SynapseList, mani_actors: SynapseList,
             part_name: Callable[[str], str] | None = None, background_as_described: bool = False,
             derived: dict | None = None) -> bool:
    """Build the goal list for the current motive (``GoalGen``, UPSIMain 1500).

    ``goal_list`` is cleared and refilled in place. Returns whether a main
    goal was considered (global ``MainGoal``; set as soon as a goal of the
    current motive passes the link test, before the random test).

    Per goal of a need with activity > 0 that is not yet in the list and
    whose ``toGoal`` link conducts: main goals pass ``random < 1`` (always,
    but a number is drawn); background goals pass
    ``random < r - (r - strength * threshold)`` with
    ``r = activity * old link weight * need weight``, which reduces to
    ``random < strength * threshold``.

    Raises:
        IndexError: if the current motive is ``NIL``. The original indexes
            ``BedIn[ActualMotiv]`` and is compiled with range checks
            (``$R+``); in the full life with seed 16 the motive was never nil.
    """
    if mot.actual_motive is Motive.NIL:
        raise IndexError("GoalGen: BedIn[NilMotiv] out of range ($R+)")
    net, clock = mot.net, mot.clock
    goal_list.clear()
    actual = mot.actual_motive
    current_strength = mot.activity(actual)
    mot.prn.write("  -? Was soll ich anstreben? (Ziele) ")
    main_goal = False
    mot.counters.count(IntProc.SGoa)
    threshold = mot.modulators[Modulator.SELECT_THRESHOLD]
    order = [actual] + [m for m in NEEDS if m is not actual]
    for motive in order:
        need = mot.need_in[motive]
        clock.advance(1)
        for li in list(need.axon[Axon.TO_GOAL]):
            clock.advance(1)
            r = li.weight  # read before transmit changes it
            goal = li.target
            if not (need.activity > 0 and goal_list.find(goal) is None
                    and net.transmit(need, goal, Axon.TO_GOAL) is not None):
                continue
            clock.advance(1)
            if motive is not actual:
                r = need.activity * r * mot.params.needs[motive].weight
                s = r - current_strength * threshold
                background = True
            else:
                r, s = 1.0, 0.0
                main_goal = True
                background = False
            # The book (Mechanik des Seelenwagens, p. 99) gives the rule for background
            # goals as random < BedIn - strength * threshold, i.e. random < s; the
            # program tests r - s = strength * threshold (ADR 0015, switch
            # background_goals_as_described). Main goals pass either way (r - s = 1).
            limit = s if (background and background_as_described) else r - s
            if mot.net.rng.random(site=SITE_GOALGEN) < limit:
                goal_list.append_copy(li)
                mot.counters.count(IntProc.MbGo if background else IntProc.MmGo)
                intermediate_goals(mot, li.target, goal_list, mani_actors, derived)
    index = mot.needs_index()
    mot.competence_certainty(1 if not goal_list else 2, index, index)
    names = part_name or (lambda n: n)
    mot.prn.writeln("    -! Ziele: " + "".join(" " + names(g.target.name) for g in goal_list))  # type: ignore[union-attr]
    return main_goal
