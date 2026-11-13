"""Carrying out actions in the world (``UAction.pas``; ADR 0010).

Port of ``Consum``, ``ConsumMotivListe``, ``Aggress``, ``Regress``,
``SingularLocoMot`` and ``SingularManipul`` together with the handler that
creates the manipulation actors (``TFPsi.OnManipulationen``, UFPsi.pas line
690). Every action goes through the body (``state.body``, the island in the
reference mode), is perceived anew, and is entered into the protocol.

Line numbers refer to ``reference/delphi-original/PsiCode/UAction.pas``.

``UAction.Wait`` runs the message loop while the client animates (zoom,
walking). The island completes animations at once, and at that point Psi's
age has not changed since the last pass of the loop, so the extra passes of
the original change nothing; the port leaves them out.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from psi_gw.counters import IntProc, Performance
from psi_gw.memory.lists import NilDereference, Spat, Synapse
from psi_gw.memory.network import Axon, Neuron
from psi_gw.motivation.needs import NEEDS, Motive
from psi_gw.perception.percept import Perception

if TYPE_CHECKING:
    from psi_gw.state import PsiState

TOTAL_VIEW = (0, 0, 159, 159)
"""``TotalViewRect``."""
PART_RECT = (0, 0, 49, 49)
"""``PartRect``."""

NUCLEOTIDES = {"Fisch1": 1, "Fels3": 1, "Bauma": 1, "Baumawelk-": 1, "Wrack1": 1, "Aeste": 1,
               "TeddyF": 1, "Due2-": 2, "Hoehle": 2, "BergsprengungNuc3a": 5}
"""Nucleotides found per object (``Consum``, line 96)."""

_MOTIVE_BY_LETTER = {"n": Motive.NIL, "H": Motive.HUNGER, "D": Motive.DURST, "N": Motive.NUKLEO,
                     "S": Motive.SCHADEN, "B": Motive.BESTIMMTHEIT, "K": Motive.KOMPETENZ,
                     "A": Motive.AFFILI}


def this_motiv(name: str) -> Motive:
    """``ThisMotiv`` (UStrukturen 822): motive from the first letter of its name."""
    return _MOTIVE_BY_LETTER.get(name[:1], Motive.NIL)


def on_manipulations(st: "PsiState", kinds: list[str]) -> None:
    """``TFPsi.OnManipulationen``: one actor neuron per manipulation kind.

    Each is put in front of ``ManiActor``; then ``AllActors`` is extended and
    the actors are registered as their own part names.
    """
    st.n_manipul = len(kinds)
    for kind in kinds:
        st.mani_actors.add_front(Synapse(st.net.new_neuron(kind)))
    st.all_actors.merge(st.mani_actors)
    st.body.client.add_list_to_part_list([s.target.name for s in st.all_actors])


def _percept(st: "PsiState", rect, zoom: bool) -> tuple[Neuron, tuple[int, int] | None]:
    return Perception(st, st.body.act_sit()).run(rect, zoom)


def _after_percept(st: "PsiState", indent: str) -> None:
    st.prn.writeln(f"{indent}PerceptZeit = {st.perception_time:8d}")
    st.clock.age = st.clock.age - st.perception_time + 120


def _out_activities(st: "PsiState", kind: str) -> None:
    """``AddToAct(InActivity, ...)``, ``NReact`` and ``OutActivities`` before an action."""
    st.add_to_act(st.in_activity, st.clock.age - st.start_activity)
    st.n_react += 1
    st.out_activities(kind)


def _protocol(st: "PsiState", neuron: Neuron, spat: Spat) -> None:
    st.protocol.protocol(0, neuron, "P", st.params.memory.protocol_factor, spat)


def consum(st: "PsiState", motive_effect: str, extent: float, objekt_name: str,
           objekt: Neuron | None, back_objekt: Neuron) -> None:
    """``Consum`` (line 41): a need is satisfied (``extent`` < 0) or hurt by an object."""
    mot = st.motivation
    actual = back_objekt if objekt is None else objekt
    # DEVIATION(ADR-0010): spati is an uninitialised local in the original; zero here.
    spati = Spat()
    for m in NEEDS:
        if this_motiv(motive_effect) is not m:
            continue
        need = mot.need_in[m]
        if extent < 0:
            if m is not mot.actual_motive:
                st.ws_events["opportunistic"] += 1  # W4: satisfaction of a need other than the motive
            st.prn.writeln(f"    *** Bedürfnisbefriedigung  {motive_effect} MotivEffekt: {extent:5.3f}")
            if need.axon[Axon.TO_GOAL].find(back_objekt) is None:
                st.net.connect(need, back_objekt, Axon.TO_GOAL, 1, spati)
                st.prn.writeln(f"    <> Lernen eines Ziels {back_objekt.name}  "
                              f"{st.body.client.get_part_name(back_objekt.name)}")
                st.counters.count(IntProc.MapG)
            else:
                st.net.reinforce(need, back_objekt, Axon.TO_GOAL, st.params.memory.base_reinforcement)
            satisfaction = 1.0
            st.just_satisfied = True
            st.protocol.reinforce_retro(st.situation, 1)
            mot.consumption(Motive.KOMPETENZ, -3 * satisfaction)
            mot.consumption(Motive.BESTIMMTHEIT, -1 * satisfaction)
            if m is Motive.NUKLEO:
                ii = NUCLEOTIDES.get(objekt_name, 0)
                st.n_nukleo += ii
                mot.consumption(Motive.NUKLEO, -ii)
                st.counters.performance[Performance.NNukleotide] += ii
                st.satisfaction = 1.0
            else:
                mot.consumption(m, extent)
                if satisfaction > st.satisfaction:
                    st.satisfaction = 1.0
        else:
            effect = extent / 10 if m is Motive.SCHADEN else extent
            st.prn.writeln(f"    *** Bedürfniserzeugung  {motive_effect}MotivEffekt: {effect:5.3f}")
            # sic: the original looks in the goal list but links an aversion
            known = Axon.TO_AVERS if st.variant.aversion_check_in_aversions else Axon.TO_GOAL
            if need.axon[known].find(actual) is None:
                st.net.connect(need, actual, Axon.TO_AVERS, 1, spati)
                st.prn.writeln(f"   <> Lernen einer Aversion: {actual.name}  "
                              f"{st.body.client.get_part_name(actual.name)}")
                st.counters.count(IntProc.MavG)
            else:
                st.net.reinforce(need, actual, Axon.TO_AVERS, st.params.memory.base_reinforcement)
            st.protocol.reinforce_retro(st.situation, 0.5)
            mot.consumption(m, effect)
            r = 1 - mot.store[m]
            satisfaction = effect if r > effect else r
            mot.consumption(Motive.KOMPETENZ, 1.5 * satisfaction)
            mot.consumption(Motive.BESTIMMTHEIT, 1 * satisfaction)
        if need.activity > 1:
            need.activity = 1.0
        if need.activity < 0:
            need.activity = 0.0


def consum_motiv_liste(st: "PsiState", back_objekt: Neuron) -> None:
    """``ConsumMotivListe`` (line 251): apply the need effects the world reported."""
    if st.motiv_liste:
        for name, value in list(st.motiv_liste):
            consum(st, name, value, st.body.object_name, st.objekt, back_objekt)
        st.motiv_liste.clear()


def aggress(st: "PsiState", schema: Neuron | None, locus: tuple[int, int]) -> None:
    """``Aggress`` (line 167): approach an object of the situation."""
    st.loc_ob = locus
    # SchemaGravity(nil) is (0, 0): ConSumFin can approach with Objekt = nil
    gx, gy = Perception(st, st.body.act_sit()).schema_gravity(schema)  # type: ignore[arg-type]
    perloc = (locus[0] + gx, locus[1] + gy)
    _out_activities(st, "Aggr")
    st.body.aggression(*perloc)
    st.counters.count(IntProc.MAgg)
    st.objekt, _ = _percept(st, PART_RECT, True)
    _after_percept(st, " ")
    if schema is not None and st.objekt is not schema:
        st.objekt = schema
    spati = Spat(locus[0], locus[1], st.clock.age, 0)
    st.counters.performance[Performance.NAgg] += 1
    st.clock.advance(50)
    _protocol(st, st.aggressio, spati)
    _protocol(st, st.objekt, spati)


def regress(st: "PsiState") -> None:
    """``Regress`` (line 219): step back from the object to the whole situation."""
    if st.objekt is None:
        return
    st.counters.count(IntProc.MReg)
    _out_activities(st, "Regr")
    st.body.regression()
    st.objekt = None
    situation, loc = _percept(st, TOTAL_VIEW, False)
    st.situation = situation
    if loc is not None:
        st.loc_sit = loc
    _after_percept(st, "  ")
    st.clock.advance(50)
    spati = Spat(st.loc_sit[0], st.loc_sit[1], 0, st.clock.age)
    _protocol(st, st.regressio, spati)
    st.new_oriented = True
    _protocol(st, st.situation, spati)


def singular_locomot(st: "PsiState", locomotion: Neuron) -> None:
    """``SingularLocoMot`` (line 266): move to a neighbouring situation."""
    spati = Spat(st.loc_sit[0], st.loc_sit[1], st.clock.age, 0)
    if st.loco_actors.find(locomotion) is None:
        return
    if st.objekt is not None:
        regress(st)
        _protocol(st, st.regressio, spati)
        _protocol(st, st.situation, spati)
    _out_activities(st, "Loco")
    st.body.move_to_situation(locomotion.name[1:])
    _protocol(st, locomotion, spati)
    st.clock.advance(50)
    old_situation = st.situation
    bbb = st.body.client.get_part_name(st.situation.name)
    situation, loc = _percept(st, TOTAL_VIEW, False)
    st.situation = situation
    if loc is not None:
        st.loc_sit = loc
    _after_percept(st, "  ")
    aaa = st.body.client.get_part_name(st.situation.name)
    if bbb != aaa:
        consum_motiv_liste(st, old_situation)
        st.motivation.competence_certainty(23, 0.9, 0)
        st.new_oriented = True
        st.eliminated.clear()
        st.counters.count(IntProc.MaLs)
        st.counters.performance[Performance.NSucLoc] += 1
        for entry in st.locations:
            if entry[0] == aaa:
                entry[1] += 1
                break
        else:
            st.locations.append([aaa, 1])
            st.counters.performance[Performance.NLoc] += 1
    else:
        st.prn.writeln(" Geht nicht!")
        st.motivation.competence_certainty(24, 0.9, 0)
        st.counters.count(IntProc.MaLu)
        st.counters.performance[Performance.NUsuLoc] += 1
    _protocol(st, st.situation, spati)
    st.new_oriented = True


def singular_manipul(st: "PsiState", schema: Neuron | None, locus: tuple[int, int], action: Neuron) -> None:
    """``SingularManipul`` (line 361): handle the object with a manipulation."""
    spati = Spat(st.loc_sit[0], st.loc_sit[1], 0, st.clock.age)
    if st.mani_actors.find(action) is None:
        return
    if st.objekt is None:
        aggress(st, schema, locus)
    st.clock.advance(50)
    _out_activities(st, "Mani")
    st.body.manipulate(action.name)
    _protocol(st, action, spati)
    st.motivation.consumption(Motive.HUNGER, 0.008)
    st.motivation.consumption(Motive.DURST, 0.008)
    st.prn.write(f"  auf {st.objekt.name} erzeugt  [{st.loc_ob[0]:3d},{st.loc_ob[1]:3d}]")
    back = st.objekt
    objekt, loc = _percept(st, PART_RECT, True)
    st.objekt = objekt
    _after_percept(st, "  ")
    if st.objekt is not back:
        st.motivation.competence_certainty(23, 1, 0)
        st.counters.count(IntProc.MaMs)
        st.counters.performance[Performance.NSucMan] += 1
        st.prn.writeln("  Das ändert was!")
        st.prn.writeln(f"  :- das ist {st.body.object_name}")
        consum_motiv_liste(st, back)
    else:
        st.motivation.competence_certainty(24, 1, 0)
        st.counters.count(IntProc.MaMu)
        st.prn.writeln(", also erfolglos!")
        st.counters.performance[Performance.NuSuMan] += 1
    _protocol(st, st.objekt, spati)
    st.new_oriented = True
