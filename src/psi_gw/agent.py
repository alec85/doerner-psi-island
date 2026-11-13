"""The behaviour cycle of Psi (``TFPsi.Simulation``, UFPsi.pas line 232; ADR 0010).

One call of :func:`run_cycle` is one cycle („Takt“) of the original without
its user interface, in the original order:

1. bookkeeping: cycle number, performance counters, age difference,
2. death („Exitus“) when hunger, thirst or damage have been empty too long;
   Psi is then resupplied and lives on,
3. perception of the situation, unless Psi reoriented during the last cycle,
   and its protocol entry,
4. ``NeedAndCompetence``, ``Motivation``, ``GoalGen``,
5. ``LookAround`` if there are goals and Psi is not at an object,
6. the Rasmussen ladder: possibly a quick move, then automatism, planning
   and doing, trial and error (``WhatCouldBeDone``); rest without a motive,
7. the value display, which in the original computes the epistemic
   competence of all needs and thereby changes memory (see below).

Perception, the regulation procedures and the exchange with the world are
not ported yet. They enter through the :class:`Faculties` interface; tests
use stand-ins. ``pump`` stands for ``Application.ProcessMessages``, where the
world's answers arrive (ADR 0010).

The value display. At the end of every cycle the original writes the
epistemic competence of each need into an edit field of the parameter window
(``FValChange``). ``EpiKomp`` is not a pure function: it traverses goal links
with ``Junction``, draws random numbers, changes weights and advances age.
The random trace of the original contains these draws (``EpiKomp`` called
from the display code, return addresses 0x49F95F ff.). The reference mode
therefore keeps them (ADR 0011); a later behaviour-changing stage can drop
them (ADR 0010, stage 2).
"""

from __future__ import annotations

from fractions import Fraction
from typing import Protocol

from psi_gw.body.island.x87 import ext, format_f, str_real
from psi_gw.counters import Performance
from psi_gw.memory.lists import Spat, Synapse
from psi_gw.memory.network import Axon, Neuron
from psi_gw.motivation.goals import goal_gen
from psi_gw.motivation.needs import Modulator, Motive
from psi_gw.state import PsiState
from psi_gw.triple import Triple

SITE_EPIKOMP_TEST = "UFPsi.TFPsi.Simulation#1"
SITE_QUICKMOVE = "UFPsi.TFPsi.Simulation#2"

DISPLAY_ORDER = (Motive.HUNGER, Motive.DURST, Motive.NUKLEO, Motive.SCHADEN,
                 Motive.KOMPETENZ, Motive.BESTIMMTHEIT, Motive.AFFILI)
"""Order of the ``EpiKomp`` calls of the value display (UFPsi.pas, lines 493 to 499)."""


class Faculties(Protocol):
    """Parts of Psi and its world that are not ported yet."""

    def pump(self, state: PsiState) -> None:
        """Let the world's answers in (``Application.ProcessMessages``)."""
        ...

    def percept_reorientation(self, state: PsiState) -> tuple[Neuron, Spat]:
        """Perceive the whole situation (``Percept('Neuorientierung', ...)``).

        Returns the situation neuron and the spatial relation passed to its
        protocol entry. In the original that relation is an uninitialised
        local variable (``SpatSit``); its x and y end up in the protocol
        links.
        """
        ...

    def situation_name(self, state: PsiState) -> str:
        """Name of the current place (``PsiClient.SituationName``)."""
        ...

    def object_name(self, state: PsiState) -> str:
        """Name of the object Psi stands at, ``'-'`` if none (``PsiClient.ObjectName``)."""
        ...

    def part_name(self, state: PsiState, neuron_name: str) -> str:
        """Name of the world object a neuron stands for (``GetPartName``)."""
        ...

    def look_around(self, state: PsiState) -> Triple: ...

    def regress(self, state: PsiState) -> None: ...

    def automatism(self, state: PsiState, aspect: Neuron | None) -> Triple: ...

    def plan_and_do(self, state: PsiState, aspect: Neuron | None) -> Triple: ...

    def what_could_be_done(self, state: PsiState) -> None: ...

    def rest(self, state: PsiState) -> None: ...


def current_aspect(state: PsiState) -> Neuron | None:
    """The object Psi is at, else the situation (``UpdateAktueller_Aspekt``, UStrukturen 1497)."""
    return state.objekt if state.objekt is not None else state.situation


CYCLE_RULE = "---------------<time>----------------------"
"""First line of every cycle in the protocol; the original writes the wall clock time here."""


def _start_bookkeeping(state: PsiState, faculties: Faculties) -> None:
    state.cycle += 1
    state.satisfaction = 0.0
    state.furcht = 0.0
    state.hilflosigkeit = 0.0
    state.int_times = [0] * 4
    prn = state.prn
    prn.writeln(CYCLE_RULE)
    prn.write(f"Takt: {state.cycle:4d} age: {state.clock.age:10d} in "
              f"{faculties.situation_name(state)} {faculties.object_name(state)}")
    if state.cycle > 1:
        head = state.protocol.head(0)
        prn.write(f" Prot: {head.name}->{head.axon[Axon.SUB].first.target.name}")  # type: ignore[union-attr]
        if current_aspect(state) is state.objekt:
            prn.writeln(" an " + faculties.part_name(state, state.objekt.name))  # type: ignore[union-attr]
        else:
            prn.writeln(" vor der Situation ")
        prn.writeln(f"   TriErr = {state.n_tri_err:5d}")
    else:
        prn.writeln()
    if state.cycle == 1:
        state.protocol.new_protocol(0)
        state.sum_int_time = 0
        state.n_react = 0
        state.activities = ""
        state.n_activities = 0
        state.locations.append([faculties.situation_name(state), 1])
        state.counters.performance[Performance.NLoc] += 1
        state.sum_leist = [0] * len(Performance)


def _performance_and_exitus(state: PsiState) -> None:
    mot = state.motivation
    age = state.clock.age
    age_diff = age - state.lta
    state.lta = age
    perf = state.counters.performance
    perf[Performance.Life] = age
    perf[Performance.DiffLife] = age_diff
    # Delphi's Round rounds halves to even, like Python's round.
    perf[Performance.Hun] = round((1 - mot.store[Motive.HUNGER]) * 100)
    perf[Performance.Dur] = round((1 - mot.store[Motive.DURST]) * 100)
    perf[Performance.Scha] = round((1 - mot.store[Motive.SCHADEN]) * 100)
    perf[Performance.Affil] = round((1 - mot.store[Motive.AFFILI]) * 100)
    for p in (Performance.Hun, Performance.Dur, Performance.Scha, Performance.Affil):
        state.sum_leist[p] += perf[p]
    # ach file: life percentage and the performance counters before death is checked
    pct = round((age / state.max_life) * 100) if state.max_life > 0 else 0
    state.ach_log.append(f"{pct:4d}" + "".join(
        f"{perf[p]:{9 if p in (Performance.Life, Performance.DiffLife) else 5}d}" for p in Performance))

    vital = (Motive.HUNGER, Motive.DURST, Motive.SCHADEN)
    if any(mot.store[m] < 0.001 for m in vital):
        state.need_ext_vers += age_diff
    if state.need_ext_vers > state.limit:
        names = {Motive.HUNGER: " Hunger", Motive.DURST: " Durst", Motive.SCHADEN: " Schaden"}
        state.prn.writeln("### Exitus -" + "".join(names[m] for m in vital if mot.store[m] < 0.001))
        perf[Performance.NExit] += 1
        for m in vital:
            mot.store[m] = 1.0
            mot.need_in[m].activity = 0.0
        state.need_ext_vers = 0
        state.n_exitus += 1


def _rasmussen_ladder(state: PsiState, faculties: Faculties, success: Triple, aspect: Neuron | None) -> None:
    mot = state.motivation
    actual = mot.actual_motive
    if success is Triple.FALSE and actual is not Motive.NIL:
        quick = False
        if state.main_goal and actual not in (Motive.BESTIMMTHEIT, Motive.KOMPETENZ):
            # The random trace shows the order: EpiKomp draws first, then random.
            competence = mot.epistemic_competence(actual)
            if state.rng.random(site=SITE_EPIKOMP_TEST) < competence:
                quick = state.rng.random(site=SITE_QUICKMOVE) < mot.activity(actual) - 0.2
        state.quick_move = quick
        if quick:
            state.prn.writeln("    -! Quickmove")
        if quick and state.objekt is not None:
            faculties.regress(state)
        if state.goal_list and not quick:
            if faculties.automatism(state, aspect) is Triple.FALSE:
                aspect = current_aspect(state)
                if faculties.plan_and_do(state, aspect) is Triple.FALSE:
                    faculties.what_could_be_done(state)
        else:
            faculties.what_could_be_done(state)
    elif actual is Motive.NIL:
        # Not reachable in the original: GoalGen fails on the nil motive first.
        faculties.rest(state)


def value_display(state: PsiState) -> None:
    """Side effects of the value display at the end of a cycle (see module docstring)."""
    for m in DISPLAY_ORDER:
        state.motivation.epistemic_competence(m)


def run_cycle(state: PsiState, faculties: Faculties) -> None:
    """One behaviour cycle (``TFPsi.Simulation``, the ``StartSimul`` part).

    ``CheckMaxLife`` (end of life at ``MaxLife``) is left to the caller.
    """
    faculties.pump(state)
    _start_bookkeeping(state, faculties)
    _performance_and_exitus(state)

    if not state.new_oriented:
        state.prn.writeln("  ~~~~~ Neuorientierung")
        situation, spat = faculties.percept_reorientation(state)
        state.situation = situation
        state.protocol.protocol(0, situation, "P", state.params.memory.protocol_factor, spat)
    state.new_oriented = False
    faculties.pump(state)

    mot = state.motivation
    mot.need_and_competence()
    previous_motive = mot.actual_motive
    mot.actual_motive = mot.motivation()
    if Motive.NIL not in (previous_motive, mot.actual_motive) and previous_motive is not mot.actual_motive:
        state.ws_events["motive_switches"] += 1
    state.workspace.derived.clear()
    state.main_goal = goal_gen(mot, state.goal_list, state.mani_actors,
                               lambda name: faculties.part_name(state, name),
                               background_as_described=state.variant.background_goals_as_described,
                               derived=state.workspace.derived)
    _broadcast_goals(state, faculties)
    state.workspace.update(state)
    state.prn.writeln(f"   --: Modulatoren: AR = {str_real(state.aras.activity, 6, 3)} RL = "
                      f"{str_real(mot.modulators[Modulator.RESOLUTION_LEVEL], 6, 3)} STh = "
                      f"{str_real(mot.modulators[Modulator.SELECT_THRESHOLD], 6, 3)}")

    if state.goal_list and state.objekt is None:
        success = faculties.look_around(state)
        state.e_look_around = True
    else:
        state.e_look_around = False
        success = Triple.FALSE
    aspect = current_aspect(state)
    faculties.pump(state)

    _rasmussen_ladder(state, faculties, success, aspect)

    faculties.pump(state)
    if not state.variant.no_display_side_effects:
        value_display(state)
    state.prn.writeln(f"Taktdauer: {state.clock.age - state.lta:15d}")
    write_int_times(state)
    faculties.pump(state)


def _broadcast_goals(state: PsiState, faculties: Faculties) -> None:
    """Broadcast of the workspace into the goal list (ADR 0016): goals in the workspace
    (from the competition of the previous cycle) are always taken and stand first."""
    ws = state.workspace
    if not ws.enabled:
        return
    goals = ws.goal_neurons()
    if not goals:
        return
    for neuron in reversed(goals):
        old = state.goal_list.find(neuron)
        if old is not None:
            state.goal_list.remove(neuron)
        # keep weight and spat of the goal link if goal_gen took it; new goals get weight 1
        state.goal_list.add_front(old if old is not None else Synapse(neuron, 1.0))
    state.prn.writeln("    -! Workspace: " + " ".join(faculties.part_name(state, n.name) for n in goals))


def write_int_times(state: PsiState) -> None:
    """One line of ``IntTimes.Txt`` (UFPsi.pas line 506), written after every call of the cycle."""
    j = sum(state.int_times)
    state.sum_int_time += j
    # SumIntTime/cnr is an 80-bit quotient in the original; written with 5 decimals, halves
    # round up (seed 1035, cycle 320: 220371/320 = 688.659375 is written as 688.65938)
    mean = format_f(ext(Fraction(state.sum_int_time, state.cycle)), 5).rjust(20)
    state.int_times_log.append(f"{state.cycle:4d}: " + "".join(f"{t:10d}" for t in state.int_times)
                               + f"{j:10d}" + mean)
