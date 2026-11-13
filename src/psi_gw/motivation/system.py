"""Needs, modulators and motive selection (ADR 0010, Issue #18).

Port of the motivational core of the original:

* ``Consumption`` (UStrukturen.Pas, line 1710): needs rise and fall,
* ``NeedAndCompetence`` (UPSIMain.Pas, line 139): competence decays with
  the needs Psi carries around,
* ``EpiKomp`` and ``MotiveStrength`` (UStrukturen.Pas, lines 2151 and 2210),
* ``SetModulat`` (UStrukturen.Pas, line 463),
* ``S_Beduerfnisse`` and ``KompBestConsumption`` (UStrukturen.Pas, lines
  2406 and 2594, with the weights from ``KompBestGewichtungenInitialisieren``,
  line 2326),
* ``Motivation`` (UPSIMain.Pas, line 1341): arousal, modulators, action
  tendencies and motive selection with lateral inhibition.

Every need has a need indicator neuron („Bedarfsindikator“, ``BedIn``)
whose activity is the strength of the need, and a store („Speicher“,
``store``) between 0 (empty) and 1 (full). For most needs the activity is
``sqrt(1 - store)``.

Not ported: speech output (``Utter``) and display updates. ``Utter`` draws
random numbers only if sound is switched on (``bSound``); in the reference
runs it is off and the trace shows no such draws.
"""

from __future__ import annotations

import math
from typing import Any

from psi_gw.clock import Clock
from psi_gw.counters import Counters, IntProc
from psi_gw.memory.lists import NilDereference, SynapseList
from psi_gw.memory.network import Axon, MemoryNetwork, Neuron
from psi_gw.motivation.needs import NEEDS, Modulator, Motive, Tendency
from psi_gw.body.island.x87 import str_real
from psi_gw.params import PsiParams
from psi_gw.prn import Prn

MAX_NUKLEO = 104
"""Normalisation of nucleotide consumption („MaxNukleo“, set in ``InitPsi``)."""

STATIONS = 29
"""Number of stations of action regulation with competence/certainty effects."""

COMPETENCE_WEIGHTS = (
    0.06, -0.07, -0.05, -0.06, -0.08, 0.07, 0.08, -0.05, -0.05, -0.07,
    0.07, 0.07, 0.045, -0.052, 0.07, 0, 0.04, 0.01, -0.012, 0.07,
    0, 0, -0.04, 0.02, -0.045, 0.1, -0.062, 0.014, 0.03,
)
"""``KompGewichtung[1..29]``: competence consumption per station; negative is gain."""

CERTAINTY_WEIGHTS = (
    0.1, -0.1, -0.15, -0.05, 0, 0.2, 0.1, -0.15, -0.05, 0,
    0.2, 0.1, -0.08, -0.03, 0, 0, 0.05, -0.05, -0.02, 0.2,
    0, 0, 0, 0, -0.01, 0.15, 0.01, 0, -0.12,
)
"""``BestGewichtung[1..29]``: certainty consumption per station; negative is gain."""


def _clamp_strength(x: float) -> float:
    """Clamp a nonzero strength to [0.6, 1.3] in magnitude (``KompBestConsumption``)."""
    if x > 0:
        return min(1.3, max(0.6, x))
    if x < 0:
        return min(-0.6, max(-1.3, x))
    return x


def action_tendencies(certainty: float, competence: float) -> dict[Tendency, float]:
    """Strength of the action tendencies from the certainty and competence needs (``Motivation``)."""
    return {
        Tendency.AGGRESSION: certainty * (1 - competence),
        Tendency.FLIGHT: certainty * competence,
        Tendency.SAFEGUARD: certainty * competence,
        Tendency.DIV_EXPLO: competence * (1 - competence),
        Tendency.SPEC_EXPLO: certainty * (1 - competence),
    }


def select_motive(current: Motive, strongest: Motive, max_strength: float,
                  current_strength: float, arousal: float, threshold: float) -> tuple[Motive, bool]:
    """Motive selection with lateral inhibition (end of ``Motivation``).

    No motive if arousal is below the selection threshold. Otherwise the
    strongest motive wins if there was none, and replaces the current one only
    if its strength minus the threshold exceeds the current motive's strength.
    Returns the motive and whether it changed by inhibition being overcome.
    """
    if arousal < threshold:
        return Motive.NIL, False
    if current is Motive.NIL:
        return strongest, False
    if strongest is not current and (max_strength - threshold) > current_strength:
        return strongest, True
    return current, False


class Motivation:
    """Need indicators, stores, modulators and the current motive of one Psi."""

    def __init__(self, params: PsiParams, net: MemoryNetwork, counters: Counters, aras: Neuron) -> None:
        self.params = params
        self.net = net
        self.counters = counters
        self.aras = aras
        """„ARaS“: arousal system neuron; its activity is the arousal."""
        # InitPsi, line 2785 ff.
        self.need_in: dict[Motive, Neuron] = {}
        self.store: dict[Motive, float] = {}
        self.total_consum = {m: 0.0 for m in NEEDS}
        self.total_in = {m: 0.0 for m in NEEDS}
        for m in NEEDS:
            neuron = net.new_neuron(_motive_name(m) + str(int(m)))
            neuron.activity = 0.0
            self.need_in[m] = neuron
            self.store[m] = 1.0 if params.needs[m].weight > 0 else 0.0
        self.need_in[Motive.NUKLEO].activity = params.needs[Motive.NUKLEO].weight
        self.previous_need = {m: 0.0 for m in NEEDS}
        """``altbed``: activities before the last update."""
        self.modulators = {m: 0.0 for m in Modulator}
        self.tendencies = {t: 0.0 for t in Tendency}
        self.actual_motive = Motive.NIL
        self.previous_arousal = 0.0
        self.age_mot_old = 0
        """``AgeMotOld``: age at the last ``NeedAndCompetence``."""
        self.last_time = 0
        self.prn = Prn()
        """Activity protocol (``prn``); the state replaces it with its own."""
        self.switch_bonus = None
        """Bonus the current motive keeps over a challenger, as a function of the selection
        threshold. ``None``: the threshold itself (the original). Set from the workspace
        mode of the variant (ADR 0016); not part of the snapshot."""
        self.last_strengths: dict[Motive, float] = {}
        """Motive strengths computed by the last ``motivation`` call (read by the workspace)."""
        """``lasttime``: age at the last ``Motivation``."""
        self.competence_sum = [0.0] * STATIONS
        self.certainty_sum = [0.0] * STATIONS
        self.station_count = [0] * STATIONS

    @property
    def clock(self) -> Clock:
        return self.net.clock

    def activity(self, motive: Motive) -> float:
        return self.need_in[motive].activity

    # --- needs -------------------------------------------------------------------------

    def consumption(self, motive: Motive, extent: float) -> None:
        """Raise (``extent`` > 0) or satisfy (``extent`` <= 0) a need (``Consumption``, UStrukturen 1710).

        Changes the store and recomputes the activity of the need indicator:
        ``sqrt(1 - store)`` for all needs but nucleotides, whose activity moves
        towards its weight on consumption and decays on satisfaction.
        """
        p = self.params.needs[motive]
        if extent > 0:
            consum = extent if motive is Motive.NUKLEO else p.increment * extent
            self.total_consum[motive] = self.total_consum[motive] + consum
        else:
            consum = extent if motive is Motive.NUKLEO else p.decrement * extent
            self.total_in[motive] = self.total_in[motive] - consum
        if motive is Motive.NUKLEO:
            consum = consum / MAX_NUKLEO
        store = self.store[motive] - consum
        if store < 0:
            store = 0.0
        if store > 1:
            store = 1.0
        self.store[motive] = store
        neuron = self.need_in[motive]
        if motive is not Motive.NUKLEO:
            neuron.activity = math.sqrt(1 - store)
        elif consum >= 0:
            neuron.activity = neuron.activity + (p.weight - neuron.activity) * p.increment
        else:
            neuron.activity = neuron.activity - neuron.activity * p.decrement

    def need_and_competence(self) -> None:
        """Competence store sinks with the needs carried since the last call (``NeedAndCompetence``, UPSIMain 139).

        ``r = sum(activity * weight * (age - AgeMotOld))`` over all needs except
        nucleotides; ``store[Kompetenz] -= r / 500000 * Inkrement[Kompetenz]``.
        Only the store changes, not the indicator's activity.
        """
        age = self.clock.age
        r = 0.0
        for m in NEEDS:
            if m is not Motive.NUKLEO:
                r = r + self.need_in[m].activity * self.params.needs[m].weight * (age - self.age_mot_old)
        store = self.store[Motive.KOMPETENZ] - (r / 500000) * self.params.needs[Motive.KOMPETENZ].increment
        self.store[Motive.KOMPETENZ] = 0.0 if store < 0 else store
        self.age_mot_old = age

    def set_modulator(self, modulator: Modulator, value: float) -> None:
        """Set a modulator within its bounds (``SetModulat``, UStrukturen 463)."""
        p = self.params.modulators[modulator]
        if value > p.maximum:
            value = p.maximum
        if value < p.minimum:
            value = p.minimum
        self.modulators[modulator] = value

    def epistemic_competence(self, motive: Motive) -> float:
        """Knowledge of ways to satisfy a need („epistemische Kompetenz“, ``EpiKomp``, UStrukturen 2151).

        Goes through the goals of the need (``toGoal``). For each goal it can
        reach (``transmit``), it looks at the first predecessor: an action
        recorded in the protocol counts 0.4 times the link weight (once per
        action), any other predecessor 0.2 times. Result ``log10(1 + s)``,
        at most ``max_weight``. Draws random numbers through ``transmit``.
        """
        if motive is Motive.NIL:
            return 0.0
        net, clock = self.net, self.clock
        source = self.need_in[motive]
        already = SynapseList()
        s = 0.0
        for goal_syn in list(source.axon[Axon.TO_GOAL]):
            clock.advance(1)
            goal = goal_syn.target
            if net.transmit(source, goal, Axon.TO_GOAL) is None:
                continue
            ret = goal.axon[Axon.RET].first
            if ret is None:
                continue
            clock.advance(1)
            before = ret.target
            if before.name[:1] == "P":
                act_syn = before.axon[Axon.SUB].first
                if act_syn is None:
                    raise NilDereference(f"EpiKomp: {before!r} has no sub link")
                act = act_syn.target
                clock.advance(1)
                if net.transmit(before, act, Axon.SUB) is not None and already.find(act) is None:
                    already.add_front(act_syn)
                    factor = 0.4
                else:
                    factor = 0.0
            else:
                factor = 0.2
            s = s + ret.weight * factor
        # DEVIATION(ADR-0005): log10 in 64 instead of 80 bit.
        result = math.log10(1 + s)
        cap = self.net.params.max_weight
        return cap if result > cap else result

    def motive_strength(self, motive: Motive) -> float:
        """Strength of a motive (``MotiveStrength``, UStrukturen 2210).

        ``activity * weight * min(1, (1 - competence) + epistemic competence)``.
        """
        s = (1 - self.need_in[Motive.KOMPETENZ].activity) + self.epistemic_competence(motive)
        if s > 1:
            s = 1.0
        return self.need_in[motive].activity * self.params.needs[motive].weight * s

    def needs_index(self) -> float:
        """Mean need activity over five, clamped to [0.5, 2] (``S_Beduerfnisse``, UStrukturen 2406)."""
        total = 0.0
        for m in NEEDS:
            total = total + self.need_in[m].activity
        return min(2.0, max(0.5, total / 5))

    def competence_certainty(self, station: int, competence: float, certainty: float) -> None:
        """Weighted change of competence and certainty at a station of action regulation (``KompBestConsumption``).

        Args:
            station: 1 to 29, number of the station in Dörner's diagram.
            competence, certainty: strength, clamped to [0.6, 1.3] in
                magnitude unless 0.
        """
        i = station - 1
        competence = _clamp_strength(competence)
        self.consumption(Motive.KOMPETENZ, COMPETENCE_WEIGHTS[i] * competence)
        self.competence_sum[i] = self.competence_sum[i] + COMPETENCE_WEIGHTS[i] * competence
        certainty = _clamp_strength(certainty)
        self.consumption(Motive.BESTIMMTHEIT, -CERTAINTY_WEIGHTS[i] * certainty)
        self.certainty_sum[i] = self.certainty_sum[i] + CERTAINTY_WEIGHTS[i] * certainty
        self.station_count[i] += 1

    # --- motive selection ---------------------------------------------------------------

    def motivation(self) -> Motive:
        """Update needs and modulators and select the motive (``Motivation``, UPSIMain 1341).

        The caller stores the result as the current motive
        (``ActualMotiv := Motivation`` in ``TFPsi.Simulation``).
        """
        clock = self.clock
        weights = self.params.needs
        max_activity = 0.0
        max_strength = 0.0
        current_strength = 0.0
        strongest = Motive.NIL
        motive = self.actual_motive
        self.previous_arousal = self.aras.activity
        diff_time = clock.age - self.last_time
        self.last_time = clock.age
        weighted_sum = 0.0
        self.prn.writeln("  --> BedIn:  Activity MotiveStrength")
        for m in NEEDS:
            neuron = self.need_in[m]
            self.previous_need[m] = neuron.activity
            if m in (Motive.HUNGER, Motive.DURST, Motive.AFFILI):
                self.consumption(m, diff_time * 0.01)  # processes of life
            elif m is Motive.NUKLEO:  # recovery of the need for nucleotides
                if neuron.activity < weights[m].weight:
                    neuron.activity = neuron.activity + (weights[m].weight - neuron.activity) * diff_time * 0.001
                if neuron.activity > weights[m].weight:
                    neuron.activity = weights[m].weight
            elif m is Motive.SCHADEN:
                self.consumption(m, diff_time * -0.000001)
            s = neuron.activity
            sw = self.motive_strength(m)
            self.last_strengths[m] = sw
            if m is self.actual_motive:
                current_strength = sw
            if s > max_activity:
                max_activity = s
            weighted_sum = weighted_sum + neuron.activity * weights[m].weight
            if sw > max_strength:
                strongest, max_strength = m, sw
            self.prn.writeln(f"    {_motive_name(m):>14} {str_real(neuron.activity, 7, 3)}{str_real(sw, 7, 3)}")
        self.prn.writeln()

        g = self.params.modulators
        # DEVIATION(ADR-0005): ln in 64 instead of 80 bit.
        self.aras.activity = min(1.0, math.log(1 + g[Modulator.AROUSAL].gain * weighted_sum))
        r = self.aras.activity
        self.modulators[Modulator.AROUSAL] = r
        self.set_modulator(Modulator.RESOLUTION_LEVEL, 1 - (r * g[Modulator.RESOLUTION_LEVEL].gain))
        self.set_modulator(Modulator.SELECT_THRESHOLD, r * g[Modulator.SELECT_THRESHOLD].gain)

        self.tendencies = action_tendencies(self.activity(Motive.BESTIMMTHEIT), self.activity(Motive.KOMPETENZ))

        threshold = self.modulators[Modulator.SELECT_THRESHOLD]
        if self.switch_bonus is None:
            motive, changed = select_motive(motive, strongest, max_strength, current_strength, r, threshold)
        elif r < threshold:  # release of a motive stays bound to the threshold in every condition
            motive, changed = Motive.NIL, False
        else:
            motive, changed = select_motive(motive, strongest, max_strength, current_strength, math.inf,
                                            self.switch_bonus(threshold))
        if changed:
            self.counters.count(IntProc.MchM)
            clock.advance(3)

        self.prn.writeln(f"  AktMot: {_motive_name(motive)}")
        if motive is Motive.NIL:
            self.competence_certainty(17, 1, 1)
        else:
            self.competence_certainty(18, self.needs_index(), 0)
        return motive

    # --- persistence -------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        index = {id(n): i for i, n in enumerate(self.net.neurons)}
        names = lambda d: {m.name: v for m, v in d.items()}  # noqa: E731
        return {
            "aras": index[id(self.aras)],
            "need_in": {m.name: index[id(n)] for m, n in self.need_in.items()},
            "store": names(self.store), "total_consum": names(self.total_consum),
            "total_in": names(self.total_in), "previous_need": names(self.previous_need),
            "modulators": names(self.modulators), "tendencies": names(self.tendencies),
            "actual_motive": self.actual_motive.name, "previous_arousal": self.previous_arousal,
            "age_mot_old": self.age_mot_old, "last_time": self.last_time,
            "competence_sum": list(self.competence_sum), "certainty_sum": list(self.certainty_sum),
            "station_count": list(self.station_count),
        }

    @classmethod
    def restore(cls, data: dict[str, Any], params: PsiParams, net: MemoryNetwork,
                counters: Counters) -> "Motivation":
        obj = cls.__new__(cls)
        obj.params, obj.net, obj.counters = params, net, counters
        obj.aras = net.neurons[data["aras"]]
        obj.need_in = {Motive[k]: net.neurons[i] for k, i in data["need_in"].items()}
        for key in ("store", "total_consum", "total_in", "previous_need"):
            setattr(obj, key, {Motive[k]: v for k, v in data[key].items()})
        obj.modulators = {Modulator[k]: v for k, v in data["modulators"].items()}
        obj.tendencies = {Tendency[k]: v for k, v in data["tendencies"].items()}
        obj.actual_motive = Motive[data["actual_motive"]]
        obj.previous_arousal = data["previous_arousal"]
        obj.age_mot_old, obj.last_time = data["age_mot_old"], data["last_time"]
        obj.competence_sum = list(data["competence_sum"])
        obj.certainty_sum = list(data["certainty_sum"])
        obj.station_count = list(data["station_count"])
        obj.switch_bonus = None  # set by the state from its variant
        obj.last_strengths = {}
        return obj


def _motive_name(m: Motive) -> str:
    """``MotivName`` (UStrukturen, line 836); the need neuron is named this plus the ordinal."""
    return {Motive.NIL: "nilMotiv", Motive.HUNGER: "Hunger", Motive.DURST: "Durst",
            Motive.NUKLEO: "Nukleo", Motive.SCHADEN: "Schaden", Motive.BESTIMMTHEIT: "Bestimmtheit",
            Motive.KOMPETENZ: "Kompetenz", Motive.AFFILI: "Affiliation"}[m]
