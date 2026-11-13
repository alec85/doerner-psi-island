"""Remembering for action regulation: what worked where (``UStrukturen.Pas``, lines 1564 to 2600).

Port of the memory searches that the Rasmussen ladder (``UPSIMain``) builds
on: which operators were applied successfully in a situation
(``RemSpecSuccOp``) or anywhere (``RemGenSuccOp``), which were not yet tried
(``RemNotYetAppliedTo``), which led to satisfaction (``ListeConsumAktionen``),
which protocol elements start action schemas (``ListeSActorProt``), whether a
pain is expected (``ExpectPain``), the remembered direction of travel
(``RememberDir``), and the standardised measures of the competence and
certainty bookkeeping (``S_Nutzen``, ``S_Aufwand`` and relatives).

All searches go through ``MemoryNetwork.transmit`` (``Junction``) and, where
the original does, ``add_to_fan`` (``AddToFan``): a random test against the
resolution level. Line numbers refer to ``UStrukturen.Pas``.
"""

from __future__ import annotations

from fractions import Fraction
from typing import TYPE_CHECKING

from psi_gw.counters import IntProc
from psi_gw.memory.lists import NilDereference, Synapse, SynapseList
from psi_gw.memory.network import Axon, Neuron
from psi_gw.motivation.needs import NEEDS, Modulator, Motive
from psi_gw.perception.geometry import PI_EXT, real_const, winkel_differenz

if TYPE_CHECKING:
    from psi_gw.state import PsiState

SITE_ADD_TO_FAN = "UStrukturen.AddToFan#1"
SITE_REMEMBER_DIR = "UStrukturen.RememberDir#1"

DIR_ART = ("O", "NO", "N", "NW", "W", "SW", "S", "SO")
"""``DirArt`` in order (counter-clockwise from east)."""

_WINKEL_WERT = {
    "N": real_const(PI_EXT / 2), "NO": real_const(PI_EXT * Fraction(1, 4)), "O": 0.0,
    "SO": real_const(2 * PI_EXT - PI_EXT * Fraction(1, 4)), "S": real_const(2 * PI_EXT - PI_EXT / 2),
    "SW": real_const(PI_EXT + PI_EXT * Fraction(1, 4)), "W": real_const(PI_EXT),
    "NW": real_const(PI_EXT * Fraction(3, 4)),
}


def _first_target(neuron: Neuron, axon: Axon, where: str) -> Neuron:
    syn = neuron.axon[axon].first
    if syn is None:
        raise NilDereference(f"{where}: {neuron!r} has no {axon.name} link")
    return syn.target  # type: ignore[return-value]


def winkel_wert(direction: str) -> float:
    """``WinkelWert`` (line 765): angle of a compass direction as a real."""
    return _WINKEL_WERT[direction]


def dir_art_wert(name: str, residue: str = "") -> str:
    """``DirArtWert`` (line 603): direction of a locomotion neuron (``lN``, ``lSO``, ...).

    The original copies the name into a local ``string[30]`` (only its
    length, machine code at 0x477D14) and then reads the third character. For
    the two-letter names ``lN`` and ``lS`` that byte is left over from the
    previous call at the same stack depth: in ``ContinueDirection`` the third
    letter of the last longer name in the loop (``residue``). The run with
    seed 16 shows it: after ``lSO``, ``lS`` counts as south-east (cycle 9).
    """
    c2 = name[1:2]
    c3 = name[2:3] if len(name) >= 3 else residue
    if c2 == "O":
        return "O"
    if c2 == "S":
        return "SW" if c3 == "W" else ("SO" if c3 == "O" else "S")
    if c2 == "W":
        return "W"
    if c2 == "N":
        return "NO" if c3 == "O" else ("NW" if c3 == "W" else "N")
    return "N"


def this_motiv(name: str) -> Motive:
    from psi_gw.action import this_motiv as tm
    return tm(name)


class Recall:
    """The memory searches, bound to one Psi's state."""

    def __init__(self, st: "PsiState") -> None:
        self.st = st
        self.net = st.net

    def lift(self, inc: float) -> None:
        self.st.clock.advance(inc)

    def transmit(self, a: Neuron, b: Neuron, axon: Axon) -> Synapse | None:
        return self.net.transmit(a, b, axon)

    # --- small helpers ----------------------------------------------------------------------

    def add_to_fan(self, works: bool) -> bool:
        """``AddToFan`` (line 2237): with ``works``, pass with probability of the resolution level."""
        if works:
            return self.st.rng.random(site=SITE_ADD_TO_FAN) < self.st.motivation.modulators[Modulator.RESOLUTION_LEVEL]
        return True

    def expect_pain(self, sit: Neuron) -> bool:
        """``ExpectPain`` (line 1774): ``sit`` is linked to damage and the link conducts."""
        schaden = self.st.motivation.need_in[Motive.SCHADEN]
        if schaden.axon[Axon.TO_AVERS].find(sit) is not None:
            return self.transmit(sit, schaden, Axon.TO_NEED) is not None
        return False

    def seek_motive_for_goal(self, ob: Neuron) -> Motive:
        """``SeekMotiveForGoal`` (line 2121)."""
        first = ob.axon[Axon.TO_SATIS].first
        return this_motiv(first.target.name) if first is not None else Motive.NIL  # type: ignore[union-attr]

    def last_action_repeated(self, action: Neuron) -> bool:
        """``LastActionRepeated`` (line 2129): the same action was the last one at this place."""
        st = self.st
        pi = st.situation if action.name[:1] == "l" else st.objekt
        pj = st.protocol.head(0)
        while pj is not None:
            ret = pj.axon[Axon.RET].first
            if ret is None:
                return False
            pk = ret.target
            if _first_target(pk, Axon.SUB, "LastActionRepeated") is pi:  # type: ignore[arg-type]
                return _first_target(pj, Axon.SUB, "LastActionRepeated") is action
            pj = pk
        return False

    def remember_dir(self, situation: Neuron) -> str:
        """``RememberDir`` (line 2244): direction of the last successful locomotion, else random."""
        da = DIR_ART[self.st.rng.randint(7, site=SITE_REMEMBER_DIR) + 1]
        p = _first_target(situation, Axon.SUR, "RememberDir")
        while True:
            ret = p.axon[Axon.RET].first
            if ret is None:
                return da
            lastp = ret.target
            if self.transmit(p, lastp, Axon.RET) is None:  # type: ignore[arg-type]
                return da
            lastname = _first_target(lastp, Axon.SUB, "RememberDir").name  # type: ignore[arg-type]
            # short-circuit "and": the element before lastp is only read for locomotions
            if lastname[:1] == "l" and _first_target(_first_target(lastp, Axon.RET, "RememberDir"),  # type: ignore[arg-type]
                                                     Axon.SUB, "RememberDir") is not situation:
                # DEVIATION(ADR-0014): for lN and lS the third byte is byte 2 of the heap
                # address of the synapse Junction just found; not predictable, none here.
                return dir_art_wert(lastname)
            p = lastp  # type: ignore[assignment]

    def continue_direction(self, old_dir: float, options: SynapseList) -> Synapse | None:
        """``ContinueDirection`` (line 2273): the locomotion closest to the old direction."""
        best, r = None, 1000.0
        # DEVIATION(ADR-0010): before the first longer name the byte is
        # residue of unrelated earlier calls; taken as no character here.
        residue = ""
        for li in options:
            name = li.target.name  # type: ignore[union-attr]
            s = winkel_differenz(old_dir, winkel_wert(dir_art_wert(name, residue)))
            if len(name) >= 3 and not self.st.variant.clean_direction_names:
                residue = name[2]
            if s < r:
                best, r = li, s
        return best

    @staticmethod
    def chain_includes(c1a: Neuron, c1o: Neuron, c2a: Neuron, c2o: Neuron) -> bool:
        """``ChainIncludes`` (line 2293): the protocol chain c1 contains chain c2 element by element."""
        n1: Neuron | None = c1a
        n2: Neuron | None = c2a
        e = f = True
        while e and f:
            e = _first_target(n1, Axon.SUB, "ChainIncludes") is _first_target(n2, Axon.SUB, "ChainIncludes")  # type: ignore[arg-type]
            if e:
                e = not (n1 is c1o and n2 is not c2o)
            if e:
                p1 = n1.axon[Axon.POR].first  # type: ignore[union-attr]
                n1 = p1.target if p1 is not None and n1 is not c1o else None
                p2 = n2.axon[Axon.POR].first  # type: ignore[union-attr]
                n2 = p2.target if p2 is not None and n2 is not c2o else None
                f = n1 is not None and n2 is not None
                if not f and n2 is not None:
                    e = False
        return e

    # --- operator searches -------------------------------------------------------------------------

    def rem_not_yet_applied_to(self, kind: str, sit: Neuron) -> SynapseList:
        """``RemNotYetAppliedTo`` (line 1829): actors not yet applied to this situation."""
        st = self.st
        lakt = (st.mani_actors if kind == "Manipul" else st.loco_actors).copy_targets()
        st.counters.count(IntProc.SnOp)
        self.lift(1)
        for lj in list(sit.axon[Axon.SUR]):
            self.lift(1)
            lk = self.transmit(sit, lj.target, Axon.SUR)  # type: ignore[arg-type]
            if lk is None or not self.add_to_fan(True):
                continue
            self.lift(1)
            por = lk.target.axon[Axon.POR].first  # type: ignore[union-attr]
            if por is None:
                continue
            nei = por.target
            lm = self.transmit(lk.target, nei, Axon.POR)  # type: ignore[arg-type]
            if lm is None or not self.add_to_fan(True):
                continue
            self.lift(1)
            nej = _first_target(lm.target, Axon.SUB, "RemNotYetAppliedTo")  # type: ignore[arg-type]
            ln = self.transmit(lm.target, nej, Axon.SUB)  # type: ignore[arg-type]
            if ln is not None:
                self.lift(3)
                lakt.remove(ln.target)
        st.counters.count(IntProc.FnOp, len(lakt))
        return lakt

    def liste_s_actor_prot(self, obsit: Neuron) -> SynapseList:
        """``ListeSActorProt`` (line 1872): protocol elements of ``obsit`` followed by an action that changed it."""
        st = self.st
        lac = SynapseList()
        lprot = SynapseList()
        for supra in list(obsit.axon[Axon.SUR]):
            if self.transmit(obsit, supra.target, Axon.SUR) is None:  # type: ignore[arg-type]
                continue
            protac = supra.target
            ni: Neuron | None = None
            por = protac.axon[Axon.POR].first  # type: ignore[union-attr]
            if protac.name[:1] == "P" and por is not None:  # type: ignore[union-attr]
                ni = por.target
                if self.transmit(protac, ni, Axon.POR) is None:  # type: ignore[arg-type]
                    ni = None
            self.lift(2)
            if ni is None:
                continue
            lnac: Synapse | None = None
            e = True
            last_op = _first_target(ni, Axon.SUB, "ListeSActorProt")
            name_of_sub = last_op.name
            while e and st.all_actors.find(last_op) is not None:
                if self.transmit(protac, ni, Axon.POR) is not None:  # type: ignore[arg-type]
                    if name_of_sub == "AAgg":
                        while e and last_op.name != "AReg":
                            nj = _first_target(ni, Axon.POR, "ListeSActorProt")
                            self.lift(1)
                            if self.transmit(ni, nj, Axon.POR) is not None:
                                ni = nj
                                last_op = _first_target(ni, Axon.SUB, "ListeSActorProt")
                            else:
                                e = False
                        if not e:
                            lnac = ni.axon[Axon.SUB].first
                            self.lift(1)
                            ni = _first_target(ni, Axon.POR, "ListeSActorProt")
                            self.lift(1)
                    else:
                        lnac = ni.axon[Axon.SUB].first
                        self.lift(1)
                        ni = _first_target(ni, Axon.POR, "ListeSActorProt")
                        self.lift(1)
                else:
                    e = False
            if lnac is not None and _first_target(ni, Axon.SUB, "ListeSActorProt") is not obsit:
                if lac.find(lnac.target) is None:
                    lac.add_front(lnac)
                    self.lift(1)
                    # DEVIATION(ADR-0010): the template's weight is uninitialised
                    # memory (InitSyn) in the original; 0 here.
                    lprot.add_front(Synapse(protac))
                    self.lift(1)
        return lprot

    def liste_consum_aktionen(self, sit_or_obj: Neuron, motive: Motive, res_lev_yes: bool,
                              pain_list: SynapseList) -> SynapseList:
        """``ListeConsumAktionen`` (line 1957): actions that once satisfied ``motive`` here."""
        st = self.st
        lakt = SynapseList()
        ll = sit_or_obj.axon[Axon.TO_SATIS]
        st.counters.count(IntProc.ScOp)
        if not ll:
            return lakt
        self.lift(1)
        need = st.motivation.need_in[motive]
        for lj in list(sit_or_obj.axon[Axon.SUR]):
            ne_p = lj.target
            self.lift(1)
            if self.transmit(sit_or_obj, ne_p, Axon.SUR) is None or not self.add_to_fan(res_lev_yes):  # type: ignore[arg-type]
                continue
            if ll.find(need) is None:
                continue
            self.lift(1)
            self.lift(1)
            if self.transmit(sit_or_obj, need, Axon.TO_SATIS) is None:
                continue
            lm = ne_p.axon[Axon.POR].first  # type: ignore[union-attr]
            self.lift(1)
            if lm is None:
                continue
            ne_pa = lm.target
            self.lift(1)
            if self.transmit(ne_p, ne_pa, Axon.POR) is None:  # type: ignore[arg-type]
                continue
            ne_a = _first_target(ne_pa, Axon.SUB, "ListeConsumAktionen")  # type: ignore[arg-type]
            ln = self.transmit(ne_pa, ne_a, Axon.SUB)  # type: ignore[arg-type]
            if ln is None:
                continue
            if lakt.find(ne_a) is None and (st.mani_actors.find(ne_a) is not None
                                             or st.loco_actors.find(ne_a) is not None):
                lakt.add_front(ln)
                self.lift(1)
                if self.expect_pain(ne_a):
                    pain_list.add_front(ln)
                st.counters.count(IntProc.FcOp)
        return lakt

    def rem_spec_succ_op(self, sit: Neuron, res_lev_yes: bool, pain_list: SynapseList) -> SynapseList:
        """``RemSpecSuccOp`` (line 2018): operators that once changed this situation."""
        st = self.st
        self.lift(1)
        lakt = SynapseList()
        st.counters.count(IntProc.SsOp)
        for lj in list(sit.axon[Axon.SUR]):
            self.lift(1)
            lk = self.transmit(sit, lj.target, Axon.SUR)  # type: ignore[arg-type]
            if lk is None or not self.add_to_fan(res_lev_yes):
                continue
            self.lift(1)
            por = lk.target.axon[Axon.POR].first  # type: ignore[union-attr]
            if por is None:
                continue
            nei = por.target
            lm = self.transmit(lk.target, nei, Axon.POR)  # type: ignore[arg-type]
            if lm is None:
                continue
            self.lift(1)
            nej = _first_target(lm.target, Axon.SUB, "RemSpecSuccOp")  # type: ignore[arg-type]
            ln = self.transmit(nei, nej, Axon.SUB)  # type: ignore[arg-type]
            if ln is None:
                continue
            self.lift(3)
            nei_por = nei.axon[Axon.POR].first  # type: ignore[union-attr]
            if nei_por is None:
                continue
            nek = nei_por.target
            nel = _first_target(nek, Axon.SUB, "RemSpecSuccOp")  # type: ignore[arg-type]
            if self.transmit(nei, nek, Axon.POR) is None or self.transmit(nek, nel, Axon.SUB) is None:  # type: ignore[arg-type]
                continue
            if (lakt.find(ln.target) is None and nel is not sit
                    and (st.mani_actors.find(nej) is not None or st.loco_actors.find(nej) is not None)):
                lakt.add_front(ln)
                if self.expect_pain(nel):
                    pain_list.add_front(nek.axon[Axon.SUB].first)  # type: ignore[union-attr]
                st.counters.count(IntProc.FsOp)
        return lakt

    def rem_gen_succ_op(self, kind: str, pain_list: SynapseList) -> SynapseList:
        """``RemGenSuccOp`` (line 2071): operators that changed something anywhere, back along the protocol."""
        st = self.st
        lakt = SynapseList()
        actors = st.mani_actors if kind[:1] == "M" else st.loco_actors
        st.counters.count(IntProc.SgOp)
        nei = st.protocol.head(0)
        if nei is None:
            raise NilDereference("RemGenSuccOp: kzg[0] empty")
        while True:
            ret = nei.axon[Axon.RET].first
            if ret is None:
                return lakt
            nej = ret.target
            self.lift(1)
            if self.transmit(nei, nej, Axon.RET) is None or not self.add_to_fan(True):  # type: ignore[arg-type]
                return lakt
            self.lift(1)
            ne_aktor = nej.axon[Axon.SUB].first  # type: ignore[union-attr]
            if ne_aktor is not None and actors.find(ne_aktor.target) is not None:
                self.lift(3)
                ne_input = _first_target(_first_target(nej, Axon.RET, "RemGenSuccOp"), Axon.SUB, "RemGenSuccOp")  # type: ignore[arg-type]
                ne_output = _first_target(_first_target(nej, Axon.POR, "RemGenSuccOp"), Axon.SUB, "RemGenSuccOp")  # type: ignore[arg-type]
                if ne_input is not ne_output:
                    self.lift(4)
                    if lakt.find(ne_aktor.target) is None:
                        lakt.add_front(ne_aktor)
                        st.counters.count(IntProc.FgOp)
                    if self.expect_pain(ne_output):
                        pain_list.add_front(ne_aktor)
            nei = nej  # type: ignore[assignment]

    def manip_uncertainty(self, neuron: Neuron) -> float:
        """``ManipUncertainty`` (line 1564): share of manipulations not yet known to work on ``neuron``."""
        st = self.st
        tried = SynapseList()
        i = 0
        for sup in list(neuron.axon[Axon.SUR]):
            super_n = sup.target
            self.lift(1)
            if self.transmit(neuron, super_n, Axon.SUR) is None:  # type: ignore[arg-type]
                continue
            por = super_n.axon[Axon.POR].first  # type: ignore[union-attr]
            if por is None:
                continue
            por_n = por.target
            self.lift(1)
            if self.transmit(super_n, por_n, Axon.POR) is None:  # type: ignore[arg-type]
                continue
            sub_por = _first_target(por_n, Axon.SUB, "ManipUncertainty")  # type: ignore[arg-type]
            self.lift(1)
            li = self.transmit(por_n, sub_por, Axon.SUB)  # type: ignore[arg-type]
            if li is not None and st.mani_actors.find(sub_por) is not None and tried.find(sub_por) is None:
                self.lift(3)
                tried.add_front(li)
                i += 1
        if i > 0:
            return 1 - i / st.n_manipul
        return 1.0

    # --- standardised measures (S_*) ------------------------------------------------------------------

    def s_nutzen(self, start: Neuron, end: Neuron, direction: Axon) -> float:
        """``S_Nutzen`` (line 2420): value of an action sequence for the needs."""
        st = self.st
        change = 3.0
        akt = start
        while True:
            target = _first_target(akt, Axon.SUB, "S_Nutzen")
            for m in NEEDS:
                syn = self.transmit(st.motivation.need_in[m], target, Axon.TO_GOAL)
                if syn is not None:
                    change = change + syn.weight
            if akt is not end:
                akt = _first_target(akt, direction, "S_Nutzen")
            if akt is end:
                break
        if change > 0:
            return min(2.0, 0.7 + change / 10)
        if change < 0:
            return max(-2.0, -0.7 + change / 10)
        return 0.0

    def s_plan_nutzen(self, plan: SynapseList) -> float:
        """``S_PlanNutzen`` (line 2448)."""
        st = self.st
        change = 1.0
        need = st.motivation.need_in[st.motivation.actual_motive]
        for syn in list(plan):
            link = self.transmit(need, syn.target, Axon.TO_GOAL)  # type: ignore[arg-type]
            if link is not None:
                change = change + link.weight
        if change > 0:
            return min(2.0, 0.7 + change / 10)
        if change < 0:
            return max(-2.0, -0.7 + change / 10)
        return 0.0

    @staticmethod
    def s_aufwand(start: Neuron, end: Neuron, direction: Axon) -> float:
        """``S_Aufwand`` (line 2469): effort; ``max`` as in the original, so at least 2."""
        n = 0
        akt = start
        while True:
            n += 1
            if akt is not end:
                akt = _first_target(akt, direction, "S_Aufwand")
            if akt is end:
                break
        return max(2.0, 0.5 + n / 8)

    @staticmethod
    def s_plan_aufwand(plan: SynapseList) -> float:
        return min(2.0, 0.5 + len(plan) / 8)

    @staticmethod
    def s_gewissheit(start: Neuron, end: Neuron, direction: Axon) -> float:
        """``S_Gewissheit`` (line 2505): mean weight of the links of a sequence."""
        total, n = 0.0, 0
        akt = start
        while True:
            d = akt.axon[direction].first
            s = akt.axon[Axon.SUB].first
            if d is None or s is None:
                raise NilDereference("S_Gewissheit: missing link")
            total = total + d.weight
            n += 1
            total = total + s.weight
            n += 1
            if akt is not end:
                akt = d.target  # type: ignore[assignment]
            if akt is end:
                break
        return min(2.0, max(0.5, total / n))

    @staticmethod
    def s_plan_gewissheit(plan: SynapseList) -> float:
        total, n = 0.0, 0
        for syn in plan:
            t = syn.target
            if t.axon[Axon.POR]:  # type: ignore[union-attr]
                total = total + t.axon[Axon.POR].first.weight  # type: ignore[union-attr]
                n += 1
            if t.axon[Axon.RET]:  # type: ignore[union-attr]
                total = total + t.axon[Axon.RET].first.weight  # type: ignore[union-attr]
                n += 1
            sub = t.axon[Axon.SUB].first  # type: ignore[union-attr]
            if sub is None:
                raise NilDereference("S_PlanGewissheit: missing sub link")
            total = total + sub.weight
            n += 1
        return max(0.5, min(2.0, total / n))

    @staticmethod
    def s_laenge(start: Neuron, end: Neuron, direction: Axon) -> float:
        n = 0
        akt = start
        while akt is not end:
            n += 1
            akt = _first_target(akt, direction, "S_Laenge")
        return float(n)

    @staticmethod
    def s_plan_laenge(plan: SynapseList) -> float:
        return float(len(plan))
