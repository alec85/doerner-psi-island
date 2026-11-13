"""Action regulation along the Rasmussen ladder (``UPSIMain.Pas``; ADR 0010).

Port of the procedures that ``TFPsi.Simulation`` calls after goal selection:
``LookAround``, ``Automatismus``, ``PlanenUndTun``, ``WhatCouldBeDone`` and
``Ruhe``, with everything they use (``Confirmation``, ``Association``,
``ActiVerPro``, ``Planen``, ``Actiplan``, ``ConSumFin`` and others).

Line numbers refer to ``reference/delphi-original/PsiCode/UPSIMain.Pas``.
Protocol lines of the original are written to ``state.prn``.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from psi_gw.counters import IntProc
from psi_gw.memory.lists import NilDereference, Synapse, SynapseList
from psi_gw.memory.network import Axon, Neuron
from psi_gw.motivation.needs import NEEDS, Modulator, Motive
from psi_gw.regulation.recall import Recall
from psi_gw.triple import Triple

if TYPE_CHECKING:
    from psi_gw.state import PsiState

SENSORY, MOTOR, NEED, PROTOCOL, CONTROL, SHORT_TERM = range(6)
"""``TNeuron``."""


def _first(neuron: Neuron | None, axon: Axon, where: str) -> Neuron:
    if neuron is None:
        raise NilDereference(f"{where}: nil neuron")
    syn = neuron.axon[axon].first
    if syn is None:
        raise NilDereference(f"{where}: {neuron!r} has no {axon.name} link")
    return syn.target  # type: ignore[return-value]


class Regulation(Recall):
    """The procedures of ``UPSIMain`` bound to one Psi's state."""

    def __init__(self, st: "PsiState") -> None:
        super().__init__(st)
        self.prn = st.prn
        self.plan_target: Neuron | None = None
        """Goal reached by the last ``Planen`` (workspace, kind plan); output only."""

    # --- small helpers -----------------------------------------------------------------------

    def rnd(self, site: str) -> float:
        return self.st.rng.random(site=site)

    @property
    def resolution_level(self) -> float:
        return self.st.motivation.modulators[Modulator.RESOLUTION_LEVEL]

    def part_name(self, name: str) -> str:
        return self.st.body.client.get_part_name(name)

    def neuron_typ(self, neuron: Neuron) -> int:
        """``NeuronenTyp`` (UStrukturen 782)."""
        st = self.st
        if st.all_actors.find(neuron) is not None:
            return MOTOR
        if st.motive_list.find(neuron) is not None:
            return NEED
        if st.short_term_list.find(neuron) is not None:
            return SHORT_TERM
        if st.control_list.find(neuron) is not None:
            return CONTROL
        return SENSORY if neuron.name[:1] == "S" else PROTOCOL

    def out_proto(self, prot_a: Neuron, prot_o: Neuron, direction: Axon) -> None:
        """``OutProto`` (UStrukturen 880): print a protocol chain."""
        arrow = " -> " if direction is Axon.POR else " <- "
        self.prn.write("    !--: ")
        nn: Neuron | None = None
        i = 0
        while True:
            if i == 0:
                nn = prot_a
            elif prot_a is not prot_o:
                nn = _first(nn, direction, "OutProto")
            i += 1
            aaa = _first(nn, Axon.SUB, "OutProto").name
            self.prn.write(nn.name + "\\" + aaa)  # type: ignore[union-attr]
            if aaa[:1] == "S":
                self.prn.write(" " + self.part_name(aaa))
            if nn is not prot_o:
                self.prn.write(arrow)
            if i % 4 == 0 and nn is not prot_o:
                self.prn.writeln()
                self.prn.write("         ")
            if nn is prot_o:
                break
        self.prn.writeln()

    def look_for_in(self, npart: Neuron, nsit: Neuron) -> tuple[int, int]:
        """``LookForIn`` (UStrukturen 1640): position of ``npart`` in the situation ``nsit``, else (-1, -1)."""
        st = self.st
        ni: Neuron | None = nsit
        self.lift(1)
        px, py = st.loc_sit
        found = False
        while ni is not None and not found:
            sub = ni.axon[Axon.SUB].first
            if sub is not None:
                nj = sub.target
                self.lift(0.5)
                self.lift(0.5)
                if self.transmit(ni, nj, Axon.SUB) is not None and nj is npart:  # type: ignore[arg-type]
                    found = True
            por = ni.axon[Axon.POR].first
            if not found and por is not None:
                self.lift(0.5)
                px += por.spat.x
                py += por.spat.y
                ni = por.target
            else:
                ni = None
        return (px, py) if found else (-1, -1)

    # --- Confirmation (line 155) -------------------------------------------------------------------

    def confirmation(self, ap: Neuron, op: Neuron, direction: Axon) -> bool:
        """``Confirmation``: test a remembered sequence against other occurrences of its start."""
        st = self.st
        refutation = 0.0
        kind = " "
        b = " "
        disproved = False
        n_result: Neuron | None = None
        n_check_aktion: Neuron | None = None
        n_check_result: Neuron | None = None
        n_aktion: Neuron | None = None
        ni: Neuron | None = ap
        self.prn.writeln("  ??-- Confirmation der Zielassoziation")
        self.out_proto(ap, op, direction)
        st.counters.count(IntProc.SCon)
        while not disproved and ni is not op and ni is not None:
            first = ni.axon[direction].first
            if first is not None and self.transmit(ni, first.target, direction) is not None:  # type: ignore[arg-type]
                nxt = _first(ni, direction, "Confirmation")
                self.lift(1)
                if self.neuron_typ(_first(nxt, Axon.SUB, "Confirmation")) != SENSORY:
                    kind = "A"
                    n_aktion = _first(nxt, Axon.SUB, "Confirmation")
                    n_result = _first(_first(nxt, direction, "Confirmation"), Axon.SUB, "Confirmation")
                    remembered = (self.transmit(nxt, n_aktion, Axon.SUB) is not None
                                  and self.transmit(_first(nxt, direction, "Confirmation"), n_result, Axon.SUB) is not None)
                    self.lift(1)
                    self.lift(1)
                    self.prn.writeln("   ?--> Prüfung von " + _first(ni, Axon.SUB, "Confirmation").name + " "
                                     + n_aktion.name + " " + n_result.name)
                else:
                    kind = "S"
                    n_result = _first(nxt, Axon.SUB, "Confirmation")
                    self.lift(1)
                    remembered = self.transmit(nxt, n_result, Axon.SUB) is not None
                    self.prn.writeln("   ?--> Prüfung von " + _first(ni, Axon.SUB, "Confirmation").name + " "
                                     + n_result.name)
                if remembered:
                    supra = SynapseList()
                    for li in _first(ni, Axon.SUB, "Confirmation").axon[Axon.SUR]:
                        if li.weight > 0:
                            supra.add_front(li)
                    while supra and not disproved:
                        li = supra.max_choice()
                        if li is None:
                            raise NilDereference("Confirmation: MaxChoice gave nil")
                        n_check_start = li.target
                        supra.remove(li.target)
                        if self.rnd("UPSIMain.Confirmation#1") < self.resolution_level:
                            d = n_check_start.axon[direction].first  # type: ignore[union-attr]
                            n_check_next = d.target if d is not None else None
                            if n_check_next is not None:
                                b = "S" if self.neuron_typ(_first(n_check_next, Axon.SUB, "Confirmation")) == SENSORY else "A"
                            self.lift(1)
                            if (kind == b and n_check_next is not None
                                    and self.transmit(n_check_start, n_check_next, direction) is not None):  # type: ignore[arg-type]
                                self.lift(1)
                                if kind == "A":
                                    n_check_aktion = _first(n_check_next, Axon.SUB, "Confirmation")
                                    n_check_result = _first(_first(n_check_next, direction, "Confirmation"), Axon.SUB, "Confirmation")
                                    remembered = (self.transmit(n_check_next, n_check_aktion, Axon.SUB) is not None
                                                  and self.transmit(_first(n_check_next, direction, "Confirmation"),
                                                                    n_check_result, Axon.SUB) is not None)
                                    self.lift(1)
                                    self.lift(1)
                                else:
                                    n_check_result = _first(_first(n_check_next, direction, "Confirmation"), Axon.SUB, "Confirmation")
                                    remembered = self.transmit(_first(n_check_next, direction, "Confirmation"),
                                                               n_check_result, Axon.SUB) is not None
                                    self.lift(1)
                                if remembered:
                                    if kind == "A":
                                        if n_check_aktion is n_aktion:
                                            if n_check_aktion.name != "AAgg":  # type: ignore[union-attr]
                                                h = n_check_result is n_result
                                            else:
                                                h = self.look_for_in(n_check_start, n_result)[0] > 0  # type: ignore[arg-type]
                                            if not h:
                                                weight = 0.33 if n_check_aktion.name == "AReg" else 1.0  # type: ignore[union-attr]
                                                refutation = refutation + self.rnd("UPSIMain.Confirmation#2") * weight
                                                disproved = refutation > 2
                                    else:
                                        h = n_check_result is n_result
                                        if not h:
                                            refutation = refutation + self.rnd("UPSIMain.Confirmation#3") * 0.5
                                        disproved = refutation > 2
                                else:
                                    self.prn.writeln(f" !-Vergessen oder inkompatible Assoziation {refutation:7.4f}")
            d = ni.axon[direction].first
            if d is not None:
                if kind == "A":
                    dd = d.target.axon[direction].first  # type: ignore[union-attr]
                    if dd is not None:
                        ni = dd.target
                    self.lift(1)
                else:
                    ni = d.target
                    self.lift(1)
            else:
                ni = None
        if disproved:
            self.prn.writeln(f"     !--: wiederlegt!{refutation:7.4f}")
            st.counters.count(IntProc.FcAu)
        else:
            self.prn.writeln(f"     !--: nicht wiederlegt!{refutation:7.4f}")
        return not disproved

    # --- Association (line 345) ----------------------------------------------------------------------

    def pump(self) -> None:
        """``Application.ProcessMessages``."""
        self.st.body.pump()

    def association(self, sit_objekt: Neuron, direction: Axon, goals: SynapseList,
                    depth: float) -> tuple[SynapseList, SynapseList]:
        """``Association``: search the protocol from occurrences of ``sit_objekt`` towards a goal.

        Returns ``(startprot, zielprot)``: starts and ends of unrefuted
        sequences leading to a goal (newest first).
        """
        st = self.st
        part_start = st.clock.age
        startprot, zielprot = SynapseList(), SynapseList()
        recalled: list[tuple[Neuron, Neuron]] = []  # (remembered situation, goal it holds), workspace
        richtung = "Pro" if direction is Axon.POR else "Retro"
        self.lift(0.5)
        if not goals:
            st.add_to_act("<Asso>", st.clock.age - part_start)
            st.counters.proc_times[0] += st.clock.age - part_start
            return startprot, zielprot
        self.prn.writeln(f"    -? Assoziationsfächer {richtung} für {sit_objekt.name} "
                         f"{self.part_name(sit_objekt.name)} Tiefe:{depth:8.2f}")
        sur_list = sit_objekt.axon[Axon.SUR].copy_targets()
        if sit_objekt is not st.situation:
            sur_list.merge(st.situation.axon[Axon.SUR])
        items = list(sur_list)
        k: int | None = 0 if items else None
        first = True
        branch_depth = depth / len(items)
        while k is not None:
            if first:
                first = False
            else:
                k = k + 1 if k + 1 < len(items) else None
            if k is None or self.neuron_typ(items[k].target) != PROTOCOL:  # type: ignore[arg-type]
                continue
            self.lift(1)
            while True:
                f = False
                cur = items[k].target
                d = cur.axon[direction].first  # type: ignore[union-attr]
                if d is not None:
                    np_ = d.target
                    self.lift(1)
                    g = True
                    while g and np_ is not None and _first(np_, Axon.SUB, "Association").name[:1] != "S":
                        nd = np_.axon[direction].first
                        if nd is not None and self.transmit(np_, nd.target, direction) is not None:  # type: ignore[arg-type]
                            np_ = _first(np_, direction, "Association")
                        else:
                            g = False
                    if not g or _first(np_, Axon.SUB, "Association") is sit_objekt:
                        k = k + 1 if k + 1 < len(items) else None
                    else:
                        f = True
                else:
                    k = k + 1 if k + 1 < len(items) else None
                if f or k is None:
                    break
            if k is None or self.neuron_typ(items[k].target) != PROTOCOL:  # type: ignore[arg-type]
                continue
            np_ = items[k].target
            start = np_
            f = False
            p = 1.0
            step = 0
            while not f:
                npa = _first(np_, Axon.SUB, "Association")
                self.lift(1)
                go_on = False
                if self.transmit(np_, npa, Axon.SUB) is not None:  # type: ignore[arg-type]
                    goal_as_part = False
                    held_goal = npa
                    for li in goals:
                        if goal_as_part:
                            break
                        if self.rnd("UPSIMain.Association#1") < self.resolution_level:
                            goal_as_part = self.look_for_in(li.target, npa)[0] >= 0  # type: ignore[arg-type]
                            if goal_as_part:
                                held_goal = li.target
                                aaa = li.target.name  # type: ignore[union-attr]
                                self.prn.writeln(f"      -! Sit mit Ziel gefunden: {aaa} {self.part_name(aaa)}")
                    if goals.find(npa) is not None or goal_as_part:
                        f = True
                        g = True
                        for s_el, z_el in zip(list(startprot), list(zielprot)):
                            if self.chain_includes(s_el.target, z_el.target, start, np_):  # type: ignore[arg-type]
                                g = False
                                break
                        g = g and self.confirmation(start, np_, direction)  # type: ignore[arg-type]
                        if g:
                            self.prn.writeln(f"      !!! AssoLänge:{step:5d}")
                            startprot.add_front(Synapse(start))
                            zielprot.add_front(Synapse(np_))
                            recalled.insert(0, (npa, held_goal))  # type: ignore[arg-type]
                    else:
                        go_on = True
                else:
                    go_on = True
                if go_on:
                    step += 1
                    p = p - self.rnd("UPSIMain.Association#2") * (2 / branch_depth)
                    if p > 0:
                        d = np_.axon[direction].first  # type: ignore[union-attr]
                        if d is not None and self.transmit(np_, d.target, direction) is not None:  # type: ignore[arg-type]
                            self.lift(1)
                            last_p = np_
                            np_ = _first(np_, direction, "Association")
                            npa = _first(np_, Axon.SUB, "Association")
                            f = _first(last_p, Axon.SUB, "Association").name == "AReg" and npa is not st.situation  # type: ignore[arg-type]
                            f = f or self.expect_pain(npa)
                            if f:
                                mot = st.motivation
                                st.furcht = mot.activity(Motive.KOMPETENZ) * mot.activity(Motive.BESTIMMTHEIT) * 2
                        else:
                            f = True
                    else:
                        f = True
                    self.pump()
        st.add_to_act("<Asso>", st.clock.age - part_start)
        st.counters.proc_times[0] += st.clock.age - part_start
        if recalled:
            # what was recalled becomes a candidate for the workspace (kind memory):
            # the remembered situation, valued by the goal it holds
            st.workspace.memories = recalled
        return startprot, zielprot

    # --- ActiVerPro (line 571) ---------------------------------------------------------------------

    def _is_actor(self, neuron: Neuron) -> bool:
        st = self.st
        return (st.approach_actors.find(neuron) is not None or st.loco_actors.find(neuron) is not None
                or st.mani_actors.find(neuron) is not None)

    def acti_ver_pro(self, startprot: Neuron, zielprot: Neuron) -> Triple:
        """``ActiVerPro``: carry out a remembered behaviour program from ``startprot`` to ``zielprot``."""
        from psi_gw import action
        st = self.st
        tf = Triple.FALSE
        self.prn.writeln(f"  ## ActiVerPro ##  Also! Dann mal los mit {startprot.name}!")
        sitprot: Neuron | None = startprot
        zprot: Neuron | None = zielprot
        n_ziel = _first(zielprot, Axon.SUB, "ActiVerPro")
        motiv = self.seek_motive_for_goal(n_ziel)
        if sitprot is zielprot:
            self.con_sum_fin(st.loc_ob, n_ziel, motiv)
            return Triple.TRUE
        nxt = _first(sitprot, Axon.POR, "ActiVerPro")
        motprot: Neuron | None = nxt if self.transmit(sitprot, nxt, Axon.POR) is not None else None  # type: ignore[arg-type]
        e = True
        while e and _first(sitprot, Axon.SUB, "ActiVerPro") is not _first(zielprot, Axon.SUB, "ActiVerPro"):
            self.lift(1)
            while (motprot is not None and zprot is not None
                   and not self._is_actor(_first(motprot, Axon.SUB, "ActiVerPro"))):
                self.lift(1)
                subs = motprot.axon[Axon.SUB]
                if len(subs) < 2:
                    raise NilDereference("ActiVerPro: second sub link missing")
                zwin = subs[1].target
                zprot = zwin if self.transmit(motprot, zwin, Axon.SUB) is not None else None  # type: ignore[arg-type]
                zwin = subs.first.target  # type: ignore[union-attr]
                motprot = zwin if self.transmit(motprot, zwin, Axon.SUB) is not None else None  # type: ignore[arg-type]
                if motprot is not None:
                    zwin = _first(motprot, Axon.POR, "ActiVerPro")
                    motprot = zwin if self.transmit(motprot, zwin, Axon.POR) is not None else None
                self.lift(3)
            if motprot is None or zprot is None:
                e = False
                continue
            aktion = _first(motprot, Axon.SUB, "ActiVerPro")
            zwin = _first(motprot, Axon.POR, "ActiVerPro")
            sitprot = zwin if self.transmit(motprot, zwin, Axon.POR) is not None else None
            self.lift(1)
            if st.loco_actors.find(aktion) is not None:
                alt = st.situation
                action.singular_locomot(st, aktion)
                if st.situation is not alt:
                    tf = Triple.PARTIAL
                self.lift(2)
            elif st.approach_actors.find(aktion) is not None:
                if aktion.name == "AAgg":
                    target = _first(zwin, Axon.SUB, "ActiVerPro")
                    pos = self.look_for_in(target, st.situation)  # type: ignore[arg-type]
                    if pos[0] >= 0:
                        action.aggress(st, target, pos)
                        tf = Triple.PARTIAL
                    else:
                        self.prn.writeln("    AVP: gesuchtes Objekt nicht in Situation!")
                        e = False
                elif st.objekt is not None:
                    action.regress(st)
                    tf = Triple.PARTIAL
            else:
                old = st.objekt
                action.singular_manipul(st, st.objekt, st.loc_ob, aktion)
                if old is not st.objekt:
                    tf = Triple.PARTIAL
                self.lift(2)
            if not e:
                continue
            if aktion.name != "AReg" and sitprot is not None:
                expected = _first(sitprot, Axon.SUB, "ActiVerPro")
                if (st.objekt is None and expected is not st.situation) or \
                        (st.objekt is not None and expected is not st.objekt):
                    e = False
                    head = st.protocol.head(0)
                    self.prn.writeln(f"  -> Nicht erwartet: {head.name} "  # type: ignore[union-attr]
                                     f"{_first(head, Axon.SUB, 'ActiVerPro').name}")
                else:
                    self.prn.writeln(f"  -> So war`s erwartet! {expected.name}")
                    if expected is not _first(zielprot, Axon.SUB, "ActiVerPro"):
                        if sitprot is zprot:
                            up = _first(_first(sitprot, Axon.SUR, "ActiVerPro"), Axon.POR, "ActiVerPro")
                            zprot = up
                            sitprot = up
                            self.lift(2)
                            if sitprot is not zielprot:
                                motprot = _first(sitprot, Axon.POR, "ActiVerPro")
                        else:
                            motprot = _first(sitprot, Axon.POR, "ActiVerPro")
                            self.lift(1)
                    else:
                        tf = Triple.TRUE
            else:
                sitprot = zwin
                motprot = _first(sitprot, Axon.POR, "ActiVerPro")
                if aktion.name == "AReg":
                    self.prn.writeln("  -> erst mal zurück!")
                else:
                    self.prn.writeln("  -> das sollte es ja wohl gewesen sein?!")
        if e and startprot is not zielprot:
            st.new_oriented = True
            self.con_sum_fin(st.loc_ob, n_ziel, motiv)
        return tf

    # --- ActivateAuto (line 766) -------------------------------------------------------------------

    _INVERSE = {"lN": "lS", "lNO": "lSW", "lO": "lW", "lSO": "lNW", "lS": "lN", "lSW": "lNO",
                "lW": "lO", "lNW": "lSO"}

    def invert_direction(self, locomot: Neuron) -> Neuron | None:
        """``InvertDirection`` (line 778): the opposite locomotion actor."""
        for li in self.st.loco_actors:
            if self._INVERSE.get(li.target.name) == locomot.name:  # type: ignore[union-attr]
                return li.target
        return None

    def activate_auto(self, direction: Axon, start_prot: Synapse, goal_prot: Synapse, motiv) -> Triple:
        """``ActivateAuto``: run an automatism found by association."""
        from psi_gw import action
        st = self.st
        tf = Triple.FALSE
        sp = start_prot.target
        condition = True
        self.prn.writeln("    -> Aktiviere den Automatismus!")
        if st.situation is not _first(sp, Axon.SUB, "ActivateAuto"):
            while True:
                if st.objekt is None:
                    target = _first(sp, Axon.SUB, "ActivateAuto")
                    locus = self.look_for_in(target, st.situation)
                    if locus[0] >= 0:
                        action.aggress(st, target, locus)
                        self.prn.writeln("    -: Herstellung der Condition")
                    else:
                        condition = False
                elif st.objekt is not sp:
                    action.regress(st)
                if not condition or st.objekt is not None:
                    break
        if not condition:
            self.prn.writeln("    :- Bedingung nicht vorhanden!")
            return Triple.FALSE
        goal = _first(goal_prot.target, Axon.SUB, "ActivateAuto")
        gp = goal_prot.target
        as_expected = True
        at_goal = False
        effect = effect_p = expected = expected_p = None
        while not at_goal and as_expected:
            if sp is not gp:
                lp = sp
                while True:
                    while True:
                        if lp is not gp:
                            lp = _first(lp, direction, "ActivateAuto")
                        equal_s = _first(lp, Axon.SUB, "ActivateAuto") is _first(sp, Axon.SUB, "ActivateAuto")
                        if lp is gp or equal_s:
                            break
                    if equal_s:
                        sp = lp
                    if not equal_s or lp is gp:
                        break
                mp = _first(sp, direction, "ActivateAuto")
                aktion = _first(mp, Axon.SUB, "ActivateAuto")
                expected_p = _first(mp, direction, "ActivateAuto")
                expected = _first(expected_p, Axon.SUB, "ActivateAuto")
                if st.loco_actors.find(aktion) is not None:
                    alt = st.situation
                    if direction is Axon.RET:
                        aktion = self.invert_direction(aktion)
                        if aktion is None:
                            raise NilDereference("ActivateAuto: no inverse locomotion")
                    action.singular_locomot(st, aktion)
                    effect = st.situation
                    at_goal = effect is goal
                    effect_p = st.protocol.head(0)
                    if st.situation is not alt:
                        tf = Triple.PARTIAL
                    self.lift(2)
                elif st.approach_actors.find(aktion) is not None:
                    if aktion.name == "AAgg":
                        if st.objekt is not None:
                            action.regress(st)
                        pos = self.look_for_in(expected, st.situation)
                        effect = st.objekt
                        effect_p = st.protocol.head(0)
                        if pos[0] >= 0:
                            action.aggress(st, expected, pos)
                            self.lift(1)
                            effect = st.objekt
                            at_goal = effect is goal
                            effect_p = st.protocol.head(0)
                            tf = Triple.PARTIAL
                        else:
                            self.prn.writeln("    ActAss: gesuchtes Objekt nicht in Situation!")
                            as_expected = False
                    else:
                        effect = st.situation
                        effect_p = st.protocol.head(0)
                        if st.objekt is not None:
                            action.regress(st)
                            self.lift(1)
                            effect = st.situation
                            at_goal = effect is goal
                            tf = Triple.PARTIAL
                else:
                    if st.objekt is None:
                        target = _first(sp, Axon.SUB, "ActivateAuto")
                        pos = self.look_for_in(target, st.situation)
                        if pos[0] >= 0:
                            action.aggress(st, target, pos)
                            self.lift(1)
                        else:
                            as_expected = False
                    if as_expected:
                        alt_objekt = st.objekt
                        if direction is Axon.POR:
                            action.singular_manipul(st, st.objekt, st.loc_ob, aktion)
                        effect = st.objekt
                        at_goal = effect is goal
                        effect_p = st.protocol.head(0)
                        if alt_objekt is not st.objekt:
                            tf = Triple.PARTIAL
                        self.lift(2)
            else:
                expected_p = sp
                effect_p = sp
                expected = _first(sp, Axon.SUB, "ActivateAuto")
                effect = expected
                if st.objekt is not None:
                    action.regress(st)
            if not as_expected:
                continue
            if effect is None or expected is None:
                raise NilDereference("ActivateAuto: Effect is nil")
            aaa, bbb = effect.name, expected.name
            effect_name, expect_name = self.part_name(aaa), self.part_name(bbb)
            if not (expected is effect or effect_name == expect_name):
                as_expected = False
                self.prn.writeln(f"  -> Nicht erwartet: {effect_p.name} {aaa} {effect_name}; "  # type: ignore[union-attr]
                                 f"erwartet war: {bbb} {expect_name}")
                continue
            self.prn.writeln(f"  -> So war`s erwartet! {effect_p.name} {aaa} {effect_name}")  # type: ignore[union-attr]
            if effect is not goal:
                sp = expected_p
                self.prn.writeln("    Aber noch nicht fertig!")
                continue
            if st.objekt is None:
                pos = (-1, -1)
                head = None
                for si in st.goal_list:
                    pos = self.look_for_in(si.target, st.situation)  # type: ignore[arg-type]
                    if pos[0] >= 0:
                        head = si.target
                        break
                if pos[0] >= 0:
                    action.aggress(st, head, pos)
                    tf = Triple.PARTIAL
                else:
                    as_expected = False
                    self.prn.writeln("    -> Nicht erwartet! Kein Ziel in Situation!")
            if as_expected:
                tf = Triple.TRUE
                at_goal = True
                self.prn.writeln("    -! Hurra! Ziel erreicht!")
                self.con_sum_fin(st.loc_ob, st.objekt, motiv)
        return tf

    # --- Planen (line 1035) -------------------------------------------------------------------------

    def list_out(self, title: str, lst: SynapseList) -> None:
        """``ListOut``/``LiO`` (UStrukturen): title, colon, names separated by blanks."""
        self.prn.write(title + ": ")
        self.prn.writeln("".join(s.target.name + " " for s in lst))  # type: ignore[union-attr]

    def planen(self, situation: Neuron, depth: int, goals: SynapseList) -> SynapseList | None:
        """``Planen``: search forward through remembered action schemas towards a goal (depth first)."""
        self.plan_target = None
        st = self.st
        start_time = st.clock.age
        lanfp: dict[int, Synapse] = {}
        lactor: dict[int, SynapseList] = {}
        start: dict[int, Neuron] = {}
        success = failure = False
        g = True
        start[0] = situation if st.objekt is None else _first(situation, Axon.SUR, "Planen")
        self.prn.writeln(f"  -! Ich plane jetzt! Ausgangspunkt: {start[0].name}")
        i = 0
        while True:
            if g:
                lactor[i] = self.liste_s_actor_prot(start[i])
                self.lift(3)
            self.prn.write(f"  -> Tiefe: {i:2d}")
            self.list_out("  Aktorenliste: ", lactor[i])
            if lactor[i]:
                pp = lactor[i].first.target  # type: ignore[union-attr]
                schem_name = _first(pp, Axon.SUB, "Planen").name
                ob_name = self.part_name(schem_name)
                pad = " " * max(0, 15 - len(ob_name))
                self.prn.write(f"  -> von {schem_name} {ob_name}{pad} (~ {pp.name}) mit "
                               + _first(_first(pp, Axon.POR, "Planen"), Axon.SUB, "Planen").name)
                lanfp[i] = Synapse(pp, 1.0)
                lactor[i].remove(pp)
                stuck = False
                self.lift(2)
                e = True
                while e:
                    ni = _first(pp, Axon.POR, "Planen")
                    if self.transmit(pp, ni, Axon.POR) is not None:
                        pp = ni
                        self.lift(1)
                        e = _first(pp, Axon.SUB, "Planen").name[:1] != "S"
                    else:
                        e = False
                        stuck = True
                        self.prn.writeln("      -! Geht nicht mehr weiter beim Planen!")
                        st.motivation.competence_certainty(28, st.motivation.needs_index(), 0)
                if not stuck:
                    circle = False
                    new_branch = _first(pp, Axon.SUB, "Planen")
                    for j in range(i, -1, -1):
                        if new_branch is start.get(j):
                            self.lift(1)
                            circle = True
                            self.prn.writeln("      -! Kreis gefunden!")
                            break
                    if not circle:
                        start[i + 1] = new_branch
                        schem_name = new_branch.name
                        self.prn.writeln(f" zu {schem_name} {self.part_name(schem_name)}")
                        success = goals.find(new_branch) is not None
                        if success:
                            self.plan_target = new_branch  # workspace: goal the plan reaches
                        if not success:
                            for li in goals:
                                if success:
                                    break
                                success = self.look_for_in(li.target, new_branch)[0] >= 0  # type: ignore[arg-type]
                                if success:
                                    self.plan_target = li.target
                                    aaa = li.target.name  # type: ignore[union-attr]
                                    self.prn.writeln(f"      -! beim Planen Teilziel gefunden: {aaa} {self.part_name(aaa)}")
                    else:
                        success = False
                        stuck = True
                    # DEVIATION(ADR-0010): after a circle the original tests start[i+1],
                    # which may still be an uninitialised array slot; no pain is assumed then.
                    nxt = start.get(i + 1)
                    if nxt is not None and self.expect_pain(nxt):
                        stuck = True
                        success = False
                        mot = st.motivation
                        st.furcht = mot.activity(Motive.KOMPETENZ) * mot.activity(Motive.BESTIMMTHEIT) * 2
                    self.lift(2)
                if not success:
                    if i > depth - 1 or stuck:
                        self.lift(1)
                        g = False
                    else:
                        i += 1
                        g = True
            else:
                g = False
                i -= 1
                self.lift(1)
                failure = i < 0
            self.pump()
            if failure or success:
                break
        plan = None
        if success:
            plan = SynapseList()
            for j in range(0, i + 1):
                plan.append_copy(lanfp.get(j))
            self.prn.writeln(f"    -> Planungstiefe = {i}")
        st.counters.proc_times[1] += st.clock.age - start_time
        return plan

    # --- Actiplan (line 1243) and TryAsso (line 1595) -------------------------------------------------

    def acti_plan(self, plan: SynapseList, motiv) -> Triple:
        """``Actiplan``: carry out a plan step by step and compare each result with the expectation."""
        from psi_gw import action
        st = self.st
        te = Triple.TRUE
        items = list(plan)
        k = 0
        while k < len(items) and te is Triple.TRUE:
            el = items[k].target
            aktorprot = _first(el, Axon.POR, "Actiplan")
            aktor = _first(aktorprot, Axon.SUB, "Actiplan")
            self.lift(2)
            expected_syn = _first(aktorprot, Axon.POR, "Actiplan").axon[Axon.SUB].first
            if expected_syn is None:
                raise NilDereference("Actiplan: expected result missing")
            expected = expected_syn.target
            self.lift(3)
            erwartungsnam = expected.name  # type: ignore[union-attr]
            expect_name = self.part_name(erwartungsnam)
            if st.all_actors.find(aktor) is not None:
                if st.loco_actors.find(aktor) is not None:
                    action.singular_locomot(st, aktor)
                elif st.approach_actors.find(aktor) is not None:
                    if aktor.name == "AAgg":
                        pos = self.look_for_in(expected, st.situation)  # type: ignore[arg-type]
                        if pos[0] >= 0:
                            action.aggress(st, expected, pos)
                        else:
                            self.prn.writeln("    gesuchtes Objekt in dieser Situation nicht gefunden!")
                    elif st.objekt is not None:
                        action.regress(st)
                else:
                    action.singular_manipul(st, st.objekt, st.loc_ob, aktor)
            else:
                subs = aktorprot.axon[Axon.SUB]
                if len(subs) < 2:
                    raise NilDereference("Actiplan: macro action without goal")
                te = self.acti_ver_pro(subs[0].target, subs[1].target)  # type: ignore[arg-type]
            self.lift(2)
            current = st.objekt if st.objekt is not None else st.situation
            ergebnisnam = current.name
            effect_name = self.part_name(ergebnisnam)
            te = Triple.TRUE if (expected is current or effect_name == expect_name) else Triple.FALSE
            if te is Triple.TRUE:
                self.prn.writeln(f"  -: {ergebnisnam} = {erwartungsnam} Genau! So geht`s!")
                k += 1
                self.lift(1)
            else:
                self.prn.writeln(f"  -: {ergebnisnam} <> {erwartungsnam} So nicht erwartet!")
        return te

    def try_asso(self, direction: Axon, startprot: Synapse, goalprot: Synapse, motiv) -> Triple:
        """``TryAsso``: run an association as automatism, or consume directly at the goal."""
        from psi_gw import action
        st = self.st
        if startprot.target.name[:1] == "P":  # type: ignore[union-attr]
            te = self.activate_auto(direction, startprot, goalprot, motiv)
        else:
            ziel = _first(goalprot.target, Axon.SUB, "TryAsso")
            pz = self.look_for_in(ziel, st.situation)
            if pz[0] >= 0:
                if st.objekt is not None and st.objekt is not ziel:
                    action.regress(st)
                    action.aggress(st, ziel, pz)
                te = self.con_sum_fin(pz, ziel, motiv)
            else:
                te = Triple.FALSE
        self.prn.writeln("    -! Hat geklappt!" if te is Triple.TRUE else "    -! Hat nicht geklappt!")
        return te

    # --- Automatismus (line 1623) -----------------------------------------------------------------------

    def write_time_prot(self, name: str, t: int) -> None:
        """``WriteTimeProt`` (UStrukturen 478)."""
        self.prn.writeln(f"> > > > {name:>20} {t:10d}")

    def _sequence_measures(self, s: Synapse, z: Synapse, d: Axon) -> tuple[float, float]:
        """Arguments of ``KompBestConsumption(3 or 6, N*G/A, N*G)``, evaluated left to right."""
        a = self.s_nutzen(s.target, z.target, d) * self.s_gewissheit(s.target, z.target, d) \
            / self.s_aufwand(s.target, z.target, d)  # type: ignore[arg-type]
        b = self.s_nutzen(s.target, z.target, d) * self.s_gewissheit(s.target, z.target, d)  # type: ignore[arg-type]
        return a, b

    def automatismus(self, sit_or_ob: Neuron | None, goals: SynapseList) -> Triple:
        """``Automatismus``: look for a remembered sequence leading to a goal and run it."""
        st = self.st
        mot = st.motivation
        motiv = Motive.NIL
        st.start_activity = st.clock.age
        st.in_activity = "Auto"
        if goals.find(st.situation) is not None:
            te = Triple.TRUE
            motiv = self.seek_motive_for_goal(sit_or_ob)  # type: ignore[arg-type]
            self.con_sum_fin(st.loc_ob, st.situation, motiv)
        else:
            self.prn.writeln("  -? AUTOMATISMUS Gibt es zielführende Assoziationen")
            startprot, zielprot = self.association(st.situation, Axon.POR, goals, 10 * self.resolution_level)
            st.counters.count(IntProc.SfAu)
            self.pump()
            retro_start, retro_ziel = self.association(st.situation, Axon.RET, goals, 10 * self.resolution_level)
            st.counters.count(IntProc.SbAu)
            if retro_ziel:
                st.counters.count(IntProc.FbAu)
            self.pump()
            if zielprot:
                st.counters.count(IntProc.FfAu)
                st.auto = True
                self.prn.writeln("  -! Porro fällt mir ein!")
                for s, z in zip(list(startprot), list(zielprot)):
                    self.out_proto(s.target, z.target, Axon.POR)  # type: ignore[arg-type]
                s0, z0 = startprot.first, zielprot.first
                a, b = self._sequence_measures(s0, z0, Axon.POR)  # type: ignore[arg-type]
                mot.competence_certainty(3, a, b)
                te = self.try_asso(Axon.POR, s0, z0, motiv)  # type: ignore[arg-type]
                if te is not Triple.TRUE:
                    self.prn.writeln("    ! Erfolglos probiert!")
                    st.counters.count(IntProc.MfAu)
                    a, b = self._sequence_measures(s0, z0, Axon.POR)  # type: ignore[arg-type]
                    mot.competence_certainty(6, a, b)
                else:
                    st.counters.count(IntProc.MfAs)
                    mot.competence_certainty(5, self.s_nutzen(s0.target, z0.target, Axon.POR), 0)  # type: ignore[union-attr,arg-type]
            elif retro_ziel:
                st.counters.count(IntProc.FbAu)
                self.prn.writeln("  -: Retro fällt mir ein!")
                for s, z in zip(list(retro_start), list(retro_ziel)):
                    self.out_proto(s.target, z.target, Axon.RET)  # type: ignore[arg-type]
                s0, z0 = retro_start.first, retro_ziel.first
                te = self.try_asso(Axon.RET, s0, z0, motiv)  # type: ignore[arg-type]
                if te is not Triple.TRUE:
                    self.prn.writeln("    ! Erfolglos probiert!")
                    st.counters.count(IntProc.MbAu)
                    a, b = self._sequence_measures(s0, z0, Axon.RET)  # type: ignore[arg-type]
                    mot.competence_certainty(6, a, b)
                else:
                    st.counters.count(IntProc.MbAs)
                    mot.competence_certainty(5, self.s_nutzen(s0.target, z0.target, Axon.RET), 0)  # type: ignore[union-attr,arg-type]
            else:
                self.prn.writeln("    -! nichts eingefallen!")
                te = Triple.FALSE
                idx = mot.needs_index()
                mot.competence_certainty(7, idx, idx)
        st.int_times[1] = st.clock.age - st.start_activity
        self.write_time_prot("Automat", st.int_times[1])
        st.add_to_act("Automat", st.int_times[1])
        return te

    # --- PlanenUndTun (line 1758) -------------------------------------------------------------------------

    def _plan_measures(self, plan: SynapseList) -> tuple[float, float]:
        a = self.s_plan_nutzen(plan) * self.s_plan_gewissheit(plan) / self.s_plan_aufwand(plan)
        b = self.s_plan_nutzen(plan) * self.s_plan_gewissheit(plan)
        return a, b

    def planen_und_tun(self, situation: Neuron | None, goals: SynapseList) -> Triple:
        """``PlanenUndTun``: plan towards a goal and carry the plan out."""
        from psi_gw import action
        st = self.st
        mot = st.motivation
        st.start_activity = st.clock.age
        st.in_activity = "PlaDo"
        self.prn.writeln("  -? Plan")
        depth = round(20 * self.resolution_level)
        self.prn.writeln(f"    -> Maximale Planungstiefe = {depth}")
        plan = self.planen(situation, depth, goals)  # type: ignore[arg-type]
        st.counters.count(IntProc.SPla)
        if plan:
            a, b = self._plan_measures(plan)
            mot.competence_certainty(8, a, b)
            self.prn.writeln("    -! Das habe ich geplant: ")
            st.counters.count(IntProc.FPla)
            self.prn.write("  -: Plan: ")
            items = list(plan)
            for k, syni in enumerate(items):
                nps = syni.target
                npa = _first(nps, Axon.POR, "PlanenUndTun")
                npsub = _first(npa, Axon.SUB, "PlanenUndTun")
                zi = npsub.name[1:2] if st.approach_actors.find(npsub) is not None else npsub.name
                self.prn.writeln(f"        {nps.name:>5}\\{npsub.name:>5}({self.part_name(npsub.name):>15}) -{zi:>3}->")  # type: ignore[union-attr]
                if k == len(items) - 1:
                    end = _first(_first(_first(nps, Axon.POR, "PlanenUndTun"), Axon.POR, "PlanenUndTun"),
                                 Axon.SUB, "PlanenUndTun")  # type: ignore[arg-type]
                    self.prn.writeln(f"        {end.name:>5}\\{self.part_name(end.name)}")
            self.prn.writeln("  -! Und jetzt tue ich es!")
            st.ws_events["plans_carried_out"] += 1
            st.workspace.plan_goal = end  # end of the plan becomes a candidate (kind plan)
            st.workspace.plan_target = self.plan_target
            te = self.acti_plan(plan, Motive.NIL)
            if te is Triple.TRUE:
                as_expected = True
                self.prn.writeln("  -: Prima, so geht es!")
                st.counters.count(IntProc.MPls)
                if st.objekt is None:
                    pos, head = (-1, -1), None
                    for si in goals:
                        # the parameter "situation" shadows the global Situation here: after a
                        # locomotion the goal is still looked for in the old situation
                        where = st.situation if st.variant.goal_in_current_situation else situation
                        pos = self.look_for_in(si.target, where)  # type: ignore[arg-type]
                        if pos[0] >= 0:
                            head = si.target
                            break
                    if pos[0] >= 0:
                        action.aggress(st, head, pos)
                    else:
                        as_expected = False
                        te = Triple.FALSE
                        self.prn.writeln("    -> Nicht erwartet! Kein Ziel in Situation!")
                        st.counters.count(IntProc.MPld)
                if as_expected:
                    self.prn.writeln("    -! Hurra! Ziel für Plan erreicht!")
                    motiv = self.seek_motive_for_goal(st.objekt)  # type: ignore[arg-type]
                    self.con_sum_fin(st.loc_ob, st.objekt, motiv)
                mot.competence_certainty(10, mot.needs_index(), 0)
            else:
                self.prn.writeln("  -: Plan geht nicht!")
                st.counters.count(IntProc.MPlu)
                a, b = self._plan_measures(plan)
                mot.competence_certainty(11, a, b)
        else:
            te = Triple.FALSE
            self.prn.writeln("  Keinen Plan gefunden!")
            idx = mot.needs_index()
            mot.competence_certainty(12, idx, idx)
        if plan and te is not Triple.TRUE:
            st.ws_events["plans_aborted"] += 1
        st.int_times[2] = st.clock.age - st.start_activity
        self.write_time_prot("PlanandDo", st.int_times[2])
        st.add_to_act("PlanAndDo", st.int_times[2])
        return te

    # --- ConSumFin (line 39) ---------------------------------------------------------------------------

    def con_sum_fin(self, ort: tuple[int, int], obj: Neuron, motiv: Motive) -> Triple:
        """``ConSumFin``: try a consummatory final action on ``obj`` at ``ort``.

        If ``obj`` is only an intermediate goal, first try the operators that
        once turned it into something else.
        """
        from psi_gw import action
        from psi_gw.motivation.system import _motive_name
        st = self.st
        mot = st.motivation
        te = Triple.FALSE
        abbruch = False
        pain = SynapseList()
        self.prn.writeln(f"  ConsumFin mit: {obj.name} [{ort[0]:3d},{ort[1]:3d}]")
        goal_object: Neuron | None = None
        goal_motiv = Motive.NIL
        moti = self.seek_motive_for_goal(obj)
        if moti is Motive.NIL:
            li = list(self.rem_spec_succ_op(obj, False, pain))
            if li:
                k = 0
                erfolg = False
                while k < len(li) and not erfolg:
                    alt = st.objekt
                    action.singular_manipul(st, obj, ort, li[k].target)  # type: ignore[arg-type]
                    self.prn.write(f"    Zwischenziel: {li[k].target.name} wird angewendet")  # type: ignore[union-attr]
                    if alt is not st.objekt:
                        self.prn.writeln("      -! Genau! jetzt haben wir es!")
                        erfolg = True
                        goal_object = st.objekt
                        goal_motiv = self.seek_motive_for_goal(goal_object)  # type: ignore[arg-type]
                    else:
                        self.prn.writeln("      -! Das geht nicht!")
                        k += 1
                        abbruch = k >= len(li)
            else:
                self.prn.writeln("      -? Weiß nicht, was ich hier tun soll!")
                abbruch = True
        else:
            goal_object = obj
            goal_motiv = moti
        if abbruch:
            # DEVIATION(ADR-0010): the result is an uninitialised stack byte
            # ([ebp-0xd]) in the original when ConSumFin gives up; FALSE here.
            return Triple.FALSE
        before = {m: mot.activity(m) for m in NEEDS}
        consum = list(self.liste_consum_aktionen(goal_object, goal_motiv, False, pain))  # type: ignore[arg-type]
        motname = ""
        if not consum:
            st.new_oriented = True
        for syn in consum:
            if te is Triple.TRUE:
                break
            self.prn.writeln(f" {syn.target.name} wird angewendet")  # type: ignore[union-attr]
            alt = st.objekt
            action.singular_manipul(st, st.objekt, ort, syn.target)  # type: ignore[arg-type]
            motname = ""
            if st.objekt is not alt:
                te = Triple.TRUE
                for m in NEEDS:
                    if before[m] > mot.activity(m):
                        motname = _motive_name(m)
                        break
            else:
                st.new_oriented = True
        if te is not Triple.TRUE:
            self.prn.writeln("  -> Keine Befriedigung!")
            return Triple.FALSE
        self.prn.writeln("  -> Ah, Prima! Befriedigung von " + motname)
        return Triple.TRUE

    # --- WhatCouldBeDone (line 1892) ------------------------------------------------------------------

    def _eliminate(self, neuron: Neuron) -> None:
        self.st.eliminated.add_front(Synapse(neuron))

    def what_could_be_done(self) -> None:
        """``WhatCouldBeDone``: explore objects by trial and error, else move on."""
        from psi_gw import action
        from psi_gw.body.island.delphi_strings import compare_text
        from psi_gw.body.island.x87 import float_to_str
        st = self.st
        mot = st.motivation
        cf = st.counters.check_freq
        st.start_activity = st.clock.age
        st.in_activity = "WCBD"
        pain = SynapseList()
        st.eliminated = SynapseList()
        progress = Triple.FALSE
        self.prn.writeln("  -? WAS TUN?")
        weiter = st.objekt is not None
        sitsub: Neuron | None = None
        ort = (0, 0)
        best = 0.0
        if weiter or not st.quick_move:
            while True:
                if weiter:
                    sitsub = st.objekt
                    ort = st.loc_ob
                    self.prn.writeln("    -! Mache weiter mit " + sitsub.name)  # type: ignore[union-attr]
                else:
                    sitsub = None
                    best = 0.0
                    to_sit: Neuron | None = st.situation
                    ax, ay = st.loc_sit
                    while to_sit is not None:
                        sub_n = _first(to_sit, Axon.SUB, "WhatCouldBeDone")
                        tni = st.protocol.look_for(st.protocol.head(0), Axon.RET, sub_n, st.loco_actors,  # type: ignore[arg-type]
                                                   self.part_name)
                        if tni is None and st.eliminated.find(sub_n) is None:
                            if self.transmit(to_sit, sub_n, Axon.SUB) is not None:
                                r = self.manip_uncertainty(sub_n)
                                # Broadcast (ADR 0016): an object in the workspace is considered
                                # whenever it is not fully explored, and always approached.
                                attended = st.workspace.enabled and st.workspace.attends(sub_n)
                                if r >= best and (r > (1 - self.resolution_level) or (attended and r > 0)):
                                    if attended:
                                        s = 1.0
                                    elif (self.rem_spec_succ_op(sub_n, True, SynapseList())
                                            or not self.rem_not_yet_applied_to("Manipul", sub_n)):
                                        s = 0.05 * self.resolution_level
                                    else:
                                        s = self.resolution_level
                                    if self.rnd("UPSIMain.WhatCouldBeDone#1") < s:
                                        best = r
                                        sitsub = sub_n
                                        ort = (ax, ay)
                                    else:
                                        self._eliminate(sub_n)
                                elif r == 0:
                                    self._eliminate(sub_n)
                        por = to_sit.axon[Axon.POR].first
                        if por is not None:
                            ax += por.spat.x
                            ay += por.spat.y
                            to_sit = por.target
                        else:
                            to_sit = None
                    if sitsub is not None:
                        aaa = self.part_name(sitsub.name)
                        self.prn.writeln(f"    -! Annäherung erwogen an {aaa} ({sitsub.name}) U={float_to_str(best)} "
                                         f"[{ort[0]:3d},{ort[1]:3d}]")
                        if "~~~" in aaa:
                            self.prn.writeln("  !!! Annäherung an NichtObjekt !!!")
                self.pump()
                if st.goal_list and sitsub is not None and not st.e_look_around:
                    start, goal = self.association(sitsub, Axon.POR, st.goal_list, 5 * self.resolution_level)
                    if goal:
                        self.prn.writeln("    || Das ist mir eingefallen!")
                        for s_el, g_el in zip(list(start), list(goal)):
                            self.out_proto(s_el.target, g_el.target, Axon.POR)  # type: ignore[arg-type]
                        pairs = list(zip(list(start), list(goal)))
                        k = 0
                        motiv = Motive.NIL
                        while True:
                            akt_start, akt_goal = pairs[k][0].target, pairs[k][1].target
                            e = False
                            if akt_goal.name[:1] == "P":  # type: ignore[union-attr]
                                self.prn.writeln("  -! Mal sehen, ob ich da hin komme!")
                                if st.objekt is not None and st.objekt is not sitsub:
                                    action.regress(st)
                                    progress = Triple.PARTIAL
                                if st.objekt is None:
                                    ass_ort = self.look_for_in(sitsub, st.situation)
                                    if ass_ort[0] > 0:
                                        e = True
                                        motiv = self.seek_motive_for_goal(sitsub)
                                        self.prn.writeln(f"  -! Aggr an {sitsub.name} am Ort [{ass_ort[0]:3d},{ass_ort[1]:3d}]")
                                        action.aggress(st, sitsub, ass_ort)
                                        progress = Triple.PARTIAL
                                    else:
                                        e = False
                                        self.prn.writeln("    -! Finde ich nicht mehr!")
                                if e:
                                    progress = self.acti_ver_pro(akt_start, akt_goal)  # type: ignore[arg-type]
                            else:
                                self.prn.writeln("  -! Mal sehen, ob ich es finde!")
                                if st.objekt is not None:
                                    action.regress(st)
                                nj = _first(akt_goal, Axon.SUB, "WhatCouldBeDone")
                                ass_ort = self.look_for_in(nj, st.situation)
                                if ass_ort[0] > 0:
                                    motiv = self.seek_motive_for_goal(nj)
                                    progress = self.con_sum_fin(ass_ort, nj, motiv)
                                else:
                                    self.prn.writeln("  -: Nix gefunden!")
                                    progress = Triple.FALSE
                            if progress is Triple.FALSE and k + 1 < len(pairs):
                                k += 1
                            else:
                                self.prn.writeln({Triple.TRUE: "    -! Fortschritt",
                                                  Triple.FALSE: "    -! Zielassoziationen unergiebig!",
                                                  Triple.PARTIAL: "    -! Voran ohne Erfolg!"}[progress])
                                break
                    else:
                        self.prn.writeln("    -! Kein Ziel eingefallen!")
                        st.hilflosigkeit = mot.activity(Motive.KOMPETENZ)
                if sitsub is not None and progress is Triple.FALSE:
                    applicable = SynapseList()
                    for name in st.body.client.get_vorwissen(sitsub.name):
                        for li in st.mani_actors:
                            if compare_text(li.target.name, name) == 0:  # type: ignore[union-attr]
                                applicable.add_front(li)
                                break
                    curious = self.manip_uncertainty(sitsub) > 0 and mot.activity(Motive.KOMPETENZ) < 0.7
                    if curious:
                        self.prn.writeln("    -? Was kann man tun?")
                        if not weiter and st.objekt is not None and st.objekt is not sitsub:
                            self.prn.writeln("    -! Erst mal weg hier!")
                            action.regress(st)
                        try_these = SynapseList()
                        succ = self.rem_spec_succ_op(sitsub, True, pain)
                        if not succ:
                            li = self.rem_gen_succ_op("Manipul", pain)
                            try_these = applicable.section(li, 0, st.rng)
                            try_all = True
                            cf[0] += 1
                            if not try_these:
                                li = applicable
                                cf[1] += 1
                                if not li:
                                    cf[2] += 1
                                    lj = self.rem_not_yet_applied_to("Manipul", sitsub)
                                    n = len(lj)
                                    for _ in range(round(n * 0.1 * self.resolution_level)):
                                        lk = lj.random_choice(st.rng)
                                        if lk is None:
                                            raise NilDereference("WhatCouldBeDone: RandomChoice of empty list")
                                        if li.find(lk.target) is None:
                                            li.add_front(lk)
                                        lj.remove(lk.target)
                                try_these = li
                            self.prn.write(" Was geht? ")
                        else:
                            cf[3] += 1
                            if self.rnd("UPSIMain.WhatCouldBeDone#2") < mot.activity(Motive.KOMPETENZ) * 3:
                                cf[4] += 1
                                if self.rnd("UPSIMain.WhatCouldBeDone#3") > mot.activity(Motive.KOMPETENZ) / 10:
                                    try_these = succ
                                    try_all = True
                                    self.prn.write(" Aggr ")
                                    cf[5] += 1
                                    if self.rnd("UPSIMain.WhatCouldBeDone#4") < self.resolution_level:
                                        cf[6] += 1
                                        li = self.rem_gen_succ_op("Manipul", pain)
                                        n = len(li)
                                        for _ in range(round(n * self.resolution_level)):
                                            lk = li.random_choice(st.rng)
                                            if lk is None:
                                                raise NilDereference("WhatCouldBeDone: RandomChoice of empty list")
                                            if try_these.find(lk.target) is None:
                                                try_these.add_front(lk)
                                            li.remove(lk.target)
                                    st.counters.count(IntProc.SaOp)
                                else:
                                    self.prn.write(" DivEx ")
                                    cf[7] += 1
                                    try_these = self.rem_gen_succ_op("Manipul", pain)
                                    self.prn.write(" GErfolg ")
                                    if self.rnd("UPSIMain.WhatCouldBeDone#5") < self.resolution_level:
                                        cf[8] += 1
                                        lj = self.rem_not_yet_applied_to("Manipul", sitsub)
                                        n = len(lj)
                                        for _ in range(round(n * 0.3 * self.resolution_level)):
                                            lk = lj.random_choice(st.rng)
                                            if lk is None:
                                                raise NilDereference("WhatCouldBeDone: RandomChoice of empty list")
                                            if try_these.find(lk.target) is None:
                                                try_these.add_front(lk)
                                            lj.remove(lk.target)
                                    try_all = False
                            else:
                                try_all = False  # uninitialised in the original; TryThese stays nil
                        self.list_out("      ! TryThese: ", try_these)
                        if try_these:
                            if st.objekt is None:
                                action.aggress(st, sitsub, ort)
                                self.prn.writeln(f"    -! Aggr an {sitsub.name} am Ort [{ort[0]:3d},{ort[1]:3d}]")
                            while True:
                                choice = try_these.random_choice(st.rng)
                                aktion = choice.target  # type: ignore[union-attr]
                                try_these.remove(aktion)
                                alt = st.objekt
                                st.n_tri_err += 1
                                action.singular_manipul(st, st.objekt, st.loc_ob, aktion)
                                if alt is not st.objekt:
                                    progress = Triple.TRUE
                                if (not try_these
                                        or (not try_all and self.rnd("UPSIMain.WhatCouldBeDone#6") > self.resolution_level)
                                        or progress is not Triple.FALSE):
                                    break
                        else:
                            self._eliminate(sitsub)
                        pain = SynapseList()
                        weiter = False
                    else:
                        weiter = False
                        self.prn.writeln("  -: Kenn´ ich! Zwecklos!")
                        if st.objekt is not None:
                            action.regress(st)
                        sitsub = None
                if sitsub is None or progress is not Triple.FALSE:
                    break
        if progress is Triple.FALSE:
            self.prn.writeln("  -? TriErr LocoMot: Wie komme ich hier weg?")
            if st.objekt is not None:
                action.regress(st)
            li = self.rem_not_yet_applied_to("Locomot", st.situation)
            self.list_out("      -!", li)
            if not li:
                li = st.loco_actors.copy_targets()
            old_dir = self.remember_dir(st.situation)
            from psi_gw.regulation.recall import DIR_ART, winkel_wert
            self.prn.write(f"{DIR_ART.index(old_dir):3d} OD:{winkel_wert(old_dir):5.3f} LokoMotion: ")
            while True:
                choice = self.continue_direction(winkel_wert(old_dir), li)
                if choice is None:
                    raise NilDereference("WhatCouldBeDone: ContinueDirection gave nil")
                aktion = choice.target
                self.prn.writeln(f"      {aktion.name}")  # type: ignore[union-attr]
                li.remove(aktion)
                alt = st.situation
                action.singular_locomot(st, aktion)  # type: ignore[arg-type]
                if alt is not st.situation:
                    progress = Triple.TRUE
                if not li or progress is not Triple.FALSE:
                    break
            if progress is Triple.FALSE:
                self.prn.writeln("    -! WaCoBeDo ohne Fortschritt beendet!")
                st.hilflosigkeit = math.sqrt(mot.activity(Motive.KOMPETENZ))
        st.eliminated = SynapseList()
        st.int_times[3] = st.clock.age - st.start_activity
        self.write_time_prot("WaCoBeDo", st.int_times[3])
        st.add_to_act("WaCoBeDo", st.int_times[3])

    # --- LookAround (line 2436) and Ruhe (line 2549) ------------------------------------------------

    def look_around(self) -> Triple:
        """``LookAround``: look for goal objects in the situation, then for paths to goals."""
        st = self.st
        st.start_activity = st.clock.age
        st.in_activity = "LkA"
        ort = st.loc_sit
        sitlist = st.net.situation_list(st.situation, st.loc_sit)
        te = Triple.FALSE
        # DEVIATION(ADR-0010): Motiv is uninitialised in the original until a
        # goal is seen; it only reaches ConSumFin, which does not read it.
        motiv = Motive.NIL
        self.prn.writeln("  -?  LOOKAROUND")
        if st.workspace.enabled:
            # Broadcast (ADR 0016): goal objects in the workspace are checked first.
            for li in list(sitlist):
                nobj = li.target
                if st.workspace.attends(nobj) and st.goal_list.find(nobj) is not None:
                    ort = (li.spat.x, li.spat.y)
                    self.prn.writeln(f"  -!  Ziel im Workspace! {nobj.name} {self.part_name(nobj.name)}")  # type: ignore[union-attr]
                    motiv = self.seek_motive_for_goal(nobj)  # type: ignore[arg-type]
                    te = self.con_sum_fin(ort, nobj, motiv)  # type: ignore[arg-type]
                    st.counters.count(IntProc.FmGo if motiv is st.motivation.actual_motive else IntProc.FbGo)
                    sitlist.remove(nobj)  # type: ignore[arg-type]
                    if te is not Triple.FALSE:
                        break
        while te is Triple.FALSE:
            li = sitlist.random_choice(st.rng)
            if self.add_to_fan(True) and li is not None:
                ort = (li.spat.x, li.spat.y)
                nobj = li.target
                if st.goal_list.find(nobj) is not None:
                    aaa = self.part_name(nobj.name)  # type: ignore[union-attr]
                    self.prn.writeln(f"  -!  Ziel entdeckt! {nobj.name} {aaa}")  # type: ignore[union-attr]
                    motiv = self.seek_motive_for_goal(nobj)  # type: ignore[arg-type]
                    te = self.con_sum_fin(ort, nobj, motiv)  # type: ignore[arg-type]
                    st.counters.count(IntProc.FmGo if motiv is st.motivation.actual_motive else IntProc.FbGo)
                self.pump()
            if li is not None:
                sitlist.remove(li.target)
            if li is None or te is not Triple.FALSE \
                    or self.rnd("UPSIMain.LookAround#1") > self.resolution_level:
                break
        st.int_times[0] = st.clock.age - st.start_activity
        self.write_time_prot("LookAr", st.int_times[0])
        st.add_to_act("LookAr", st.int_times[0])
        if te is Triple.FALSE:
            st.start_activity = st.clock.age
            st.in_activity = "LaRAss"
            self.prn.writeln("    !! Keine Ziele! Aber ma gucken, was man machen kann!")
            sitlist = st.net.situation_list(st.situation, st.loc_sit)
            while True:
                li = sitlist.random_choice(st.rng)
                if self.add_to_fan(True) and li is not None:
                    ort = (li.spat.x, li.spat.y)
                    nobj = li.target
                    start, goal = self.association(nobj, Axon.POR, st.goal_list,  # type: ignore[arg-type]
                                                   5 * self.resolution_level)
                    if goal:
                        self.prn.writeln('  -! Zwischenziel + "Instrumente":')
                        st.counters.count(IntProc.FbGo)
                        for s_el, g_el in zip(list(start), list(goal)):
                            self.out_proto(s_el.target, g_el.target, Axon.POR)  # type: ignore[arg-type]
                        # sic: the output loop above leaves li at nil, which ends the outer loop
                        li = None
                        pairs = list(zip(list(start), list(goal)))
                        for s_el, g_el in pairs:
                            self.prn.writeln("  -! In Orient: Mal sehen, ob ich da hin komme!")
                            te = self.try_asso(Axon.POR, s_el, g_el, motiv)
                            if te is not Triple.FALSE:
                                break
                if li is not None:
                    sitlist.remove(li.target)
                if li is None or te is not Triple.FALSE \
                        or self.rnd("UPSIMain.LookAround#2") > self.resolution_level:
                    break
            st.int_times[0] = st.clock.age - st.start_activity
            self.write_time_prot("LookArAss", st.int_times[0])
            st.add_to_act("LookArAss", st.int_times[0])
        return te

    def ruhe(self) -> None:
        """``Ruhe``: rest; time passes."""
        self.lift(5)
