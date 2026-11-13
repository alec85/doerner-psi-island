"""The complete state of one Psi (ADR 0010).

``PsiState`` replaces the global variables of the original. It is built like
``InitPsi`` (UStrukturen.Pas, line 2643) builds Psi's initial structures and
in the same order, so neurons are created in the original sequence:

1. ``ARaS``, the arousal neuron,
2. the eight locomotion actors ``lO``, ``lNO``, ..., ``lSO``,
3. the aggression and regression actors ``AAgg`` and ``AReg``,
4. the need indicators ``Hunger1`` ... ``Affiliation7``,
5. the short-term memory neurons ``ShortTerm0`` ... ``ShortTerm7``,
6. the control neurons ``Control0`` ... ``Control9`` („Prefront“).

Lists built with ``AddListEl`` have the reverse order of creation, as in the
original (``LocoActor`` starts with ``lSO``).

The state grows with the port; parts of the original not yet ported
(perception, action regulation, world) add their state here. ``snapshot``
must cover everything, which the acceptance test checks.
"""

from __future__ import annotations

import copy
from typing import Any

from psi_gw.clock import Clock
from psi_gw.counters import Counters
from psi_gw.memory.lists import Synapse, SynapseList
from psi_gw.memory.names import NameGenerator
from psi_gw.memory.network import MemoryNetwork, Neuron
from psi_gw.memory.protocol import ProtocolMemory
from psi_gw.motivation.needs import NEEDS
from psi_gw.motivation.system import Motivation
from psi_gw.params import PsiParams, read_param_dat
from psi_gw.prn import Prn
from psi_gw.random_source import DelphiRandom, RandomSource, restore_source
from psi_gw.variant import Variant
from psi_gw.workspace import Workspace

DIRECTIONS = ("O", "NO", "N", "NW", "W", "SW", "S", "SO")
"""``DirArt`` in order, as ``DirToString`` spells them."""

MAX_CONTROL = 9
"""Highest index of the control neurons („MaxControl“)."""


def _front_list(neurons: list[Neuron]) -> SynapseList:
    """List built by repeated ``AddListEl`` (newest first)."""
    lst = SynapseList()
    for n in neurons:
        lst.add_front(Synapse(n))
    return lst


class PsiState:
    """Everything one Psi knows and is, apart from the world."""

    def __init__(self, params: PsiParams | None = None, rng: RandomSource | None = None,
                 seed: int = 2, variant: Variant | None = None) -> None:
        """Build the initial state like ``InitPsi``.

        Args:
            params: parameters; default the island ``Param.Dat``.
            rng: random source; default ``DelphiRandom(seed)``. The original
                reads ``RandSeed`` from ``Psi.Ini`` (default 2) or the run file.
        """
        self.variant = variant if variant is not None else Variant()
        """Artefacts of the original that are switched off (ADR 0015); default: none."""
        self.params = params if params is not None else read_param_dat()
        self.rng = rng if rng is not None else DelphiRandom(seed)
        self.clock = Clock()
        self.counters = Counters()
        self.net = MemoryNetwork(self.params.memory, self.rng, self.clock)
        net = self.net

        # Line sensors, created in TFPsi.FormCreate before InitPsi (UFPsi.pas, line 207)
        from psi_gw.perception.percept import SENSOR_NAMES, Sen2
        self.sensor2 = {s: net.new_neuron(SENSOR_NAMES[s]) for s in (Sen2.VER2, Sen2.HOR2, Sen2.DIA2, Sen2.ADI2)}
        """„Sensor2“: the four line sensors."""
        self.sen2 = _front_list(list(self.sensor2.values()))
        """„Sen2“: list of the line sensors (``Adi2`` first)."""

        self.aras = net.new_neuron("")
        self.aras.activity = 0.0
        loco = [net.new_neuron("l" + d) for d in DIRECTIONS]
        self.loco_actors = _front_list(loco)
        """„LocoActor“: locomotion operators."""
        self.aggressio = net.new_neuron("AAgg")
        self.regressio = net.new_neuron("AReg")
        self.approach_actors = _front_list([self.aggressio, self.regressio])
        """„ApproachActor“: aggression and regression."""
        self.all_actors = SynapseList()
        """„AllActors“: all operators; manipulation operators are added from prior knowledge."""
        self.all_actors.merge(self.loco_actors)
        self.all_actors.merge(self.approach_actors)
        self.mani_actors = SynapseList()
        """„ManiActor“: manipulation operators, set from prior knowledge (``OnManipulationen``)."""

        self.motivation = Motivation(self.params, net, self.counters, self.aras)
        self.motive_list = _front_list([self.motivation.need_in[m] for m in NEEDS])
        """„MotivList“."""
        self.protocol = ProtocolMemory(net, NameGenerator())
        self.short_term_list = _front_list(self.protocol.kzg)
        self.prefront = [net.new_neuron(f"Control{i}") for i in range(MAX_CONTROL + 1)]
        """„Prefront“: control neurons."""
        self.control_list = _front_list(self.prefront)

        # Working memory („Arbeitsgedächtnis“)
        self.situation: Neuron | None = None
        self.objekt: Neuron | None = None
        self.goal_list = SynapseList()
        """„GoalList“: current goals."""
        self.main_goal = False
        """„MainGoal“: a goal of the current motive was found (``GoalGen``)."""
        self.cycle = 0
        """„cnr“: number of the behaviour cycle."""
        self.loc_sit = (0, 0)
        """„LocSit“: place of the first object of the current situation."""
        self.loc_ob = (0, 0)
        """„LocOb“: place of the current object."""
        self.perception_time = 0
        """„Wahrnehmungszeit“."""
        self.n_manipul = 0
        """„NManipul“: number of manipulation kinds."""
        self.n_nukleo = 5
        """„NNukleo“: nucleotides collected (InitPsi sets 5)."""
        self.start_activity = 0
        """„StartActivity“: age at the start of the current regulation step."""
        self.auto = False
        """„auto“: an automatism was found."""
        self.just_satisfied = False
        """„JustSatisfied“."""
        self.motiv_liste: list[list] = []
        """„MotivListe“: need effects reported by the world, ``[name, value]``, consumed after an action."""
        self.body = None
        """The body (``PsiClient`` in the original); not part of the snapshot."""
        self.prn = Prn()
        self.protocol.prn = self.prn
        self.motivation.prn = self.prn
        """Lines the original writes to its activity protocol (``prn``, ``actu<seed>.Prt``);
        output for comparisons, not part of the snapshot."""

        # Bookkeeping of the behaviour cycle (TFPsi.Simulation, InitPsi)
        self.lta = 0
        """„LTA“: age at the start of the previous cycle."""
        self.need_ext_vers = 0
        """„NeedExtVers“: time spent with an empty store of hunger, thirst or damage."""
        self.limit = 100000
        """„limit“: time Psi survives with an empty store („ohne externe Versorgung“)."""
        self.n_exitus = 0
        """„NExitus“: number of deaths (typed constant in the original, never reset)."""
        self.new_oriented = False
        """„NewOriented“: the situation was perceived anew during the last cycle."""
        self.e_look_around = False
        """„ELookAround“: LookAround ran in this cycle."""
        self.quick_move = False
        """„QuickMove“."""
        self.satisfaction = 0.0
        self.furcht = 0.0
        """„furcht“: fear."""
        self.hilflosigkeit = 0.0
        """„hilflosigkeit“: helplessness."""
        self.sum_leist = [0] * 14
        """„SumLeist“: sums of the performance counters over cycles."""
        self.int_times = [0] * 4
        """„IntTimes“: time spent in internal processes per cycle."""
        self.sum_int_time = 0
        self.n_react = 0
        self.n_activities = 0
        self.activities = ""
        self.locations: list[list] = []
        """„LocList“: visited places, ``[name, visits]``."""
        self.max_life = 0
        """„MaxLife“: end of life (``CheckMaxLife``); 0 = unlimited. Read from the run file in the original."""
        self.ach_log: list[str] = []
        """Data lines of the ach file (``<Param>.Prt``), one per cycle; output, not part of the snapshot."""
        self.int_times_log: list[str] = []
        """Data lines of ``IntTimes.Txt``; output, not part of the snapshot."""
        self.in_activity = ""
        """„InActivity“: the regulation step that is running (for the activities file)."""
        self.activity_log: list[str] = []
        """Lines the original writes to ``Activities.Txt`` (``OutActivities``); output, not part of the snapshot."""
        self.eliminated = SynapseList()
        """„Eliminated“: objects WhatCouldBeDone has given up on in this step."""
        self.n_tri_err = 0
        self.workspace = Workspace(mode=self.variant.workspace, fixed_bonus=self.variant.workspace_fixed_bonus,
                                   ties=self.variant.workspace_ties, tie_seed=seed)
        """Global Workspace (ADR 0016); ``mode == "off"`` only logs."""
        self.motivation.switch_bonus = self.workspace.motive_switch_bonus()
        self.ws_events = {"motive_switches": 0, "plans_carried_out": 0, "plans_aborted": 0, "opportunistic": 0}
        """Event counters for W2 to W4 (analysis plan for the workspace), counted in every condition."""
        self.n_guarded = 0
        """Nil accesses ended as failed steps (switch ``guard_nil_dereferences``)."""
        """„NTriErr“: number of trial-and-error manipulations."""

    def add_to_act(self, act: str, time: int) -> None:
        """``AddToAct`` (UStrukturen 447): note a step and its duration for the activities file."""
        self.activities += f"{act};{time};"
        self.n_activities += 1

    def out_activities(self, kind: str) -> None:
        """``OutActivities`` (UStrukturen 436): before an action, write the steps since the last one.

        Also restarts ``StartActivity``, which the time protocol of the
        regulation steps reads.
        """
        self.activity_log.append(f"{self.cycle};{self.n_react};{kind};{self.clock.age};"
                                 + self.activities + ";;" * max(0, 20 - self.n_activities))
        self.start_activity = self.clock.age
        self.activities = ""
        self.n_activities = 0

    def attach_body(self, body) -> None:
        """Connect a body as the original connects ``PsiClient`` (``TFPsi.WMFirst``, UFPsi.pas line 656).

        Manipulation kinds create actor neurons (``OnManipulationen``); need
        effects are collected in ``MotivListe`` (``OnMotivation``).
        """
        from psi_gw.action import on_manipulations
        self.body = body
        self.protocol.part_name = body.client.get_part_name
        body.client.on_manipulations = lambda kinds: on_manipulations(self, kinds)
        body.client.on_motivation = lambda name, value: self.motiv_liste.append([name, value])

    # --- persistence ---------------------------------------------------------------------

    _LISTS = ("sen2", "loco_actors", "approach_actors", "all_actors", "mani_actors", "motive_list",
              "short_term_list", "control_list", "goal_list", "eliminated")
    _NEURONS = ("aras", "aggressio", "regressio", "situation", "objekt")
    _SCALARS = ("lta", "need_ext_vers", "limit", "n_exitus", "new_oriented", "e_look_around",
                "quick_move", "satisfaction", "furcht", "hilflosigkeit", "sum_leist", "int_times",
                "sum_int_time", "n_react", "n_activities", "activities", "locations",
                "loc_sit", "loc_ob", "perception_time", "n_manipul", "n_nukleo", "just_satisfied", "start_activity", "auto", "n_tri_err", "n_guarded", "in_activity", "max_life",
                "motiv_liste")

    def snapshot(self) -> dict[str, Any]:
        """Complete state as a JSON compatible dict."""
        extra = [s.target for k in self._LISTS for s in getattr(self, k)]
        extra += [getattr(self, k) for k in self._NEURONS] + list(self.prefront) + list(self.sensor2.values())
        extra += [c.neuron for c in self.workspace.contents] + [n for pair in self.workspace.memories for n in pair]
        extra += [self.workspace.plan_goal, self.workspace.plan_target]
        network = self.net.snapshot(extra)
        index = self.net.snapshot_ids
        ref = lambda n: None if n is None else index[id(n)]  # noqa: E731
        return {
            "params": self.params.snapshot(),
            "variant": self.variant.to_dict(),
            "rng": self.rng.snapshot(),  # type: ignore[attr-defined]
            "clock": self.clock.snapshot(),
            "counters": self.counters.snapshot(),
            "network": network,
            "motivation": self.motivation.snapshot(),
            "protocol": self.protocol.snapshot(),
            "prefront": [ref(n) for n in self.prefront],
            "sensor2": {s.name: ref(n) for s, n in self.sensor2.items()},
            "neurons": {k: ref(getattr(self, k)) for k in self._NEURONS},
            "lists": {k: getattr(self, k).snapshot(index) for k in self._LISTS},
            "cycle": self.cycle,
            "main_goal": self.main_goal,
            "scalars": copy.deepcopy({k: getattr(self, k) for k in self._SCALARS}),
            "workspace": self.workspace.snapshot(index),
            "ws_events": dict(self.ws_events),
        }

    @classmethod
    def restore(cls, data: dict[str, Any], wrap=None) -> "PsiState":
        """Rebuild a state from ``snapshot()``.

        Args:
            wrap: optional function applied to the restored random source,
                e.g. ``RecordingSource``.
        """
        obj = cls.__new__(cls)
        obj.params = PsiParams.restore(data["params"])
        obj.variant = Variant(**data.get("variant", {}))
        rng = restore_source(data["rng"])
        obj.rng = wrap(rng) if wrap is not None else rng
        obj.clock = Clock.restore(data["clock"])
        obj.counters = Counters.restore(data["counters"])
        obj.net = MemoryNetwork.restore(data["network"], obj.rng, obj.clock)
        neurons = obj.net.restored_neurons
        obj.motivation = Motivation.restore(data["motivation"], obj.params, obj.net, obj.counters)
        obj.protocol = ProtocolMemory.restore(data["protocol"], obj.net)
        obj.prefront = [neurons[i] for i in data["prefront"]]
        from psi_gw.perception.percept import Sen2
        obj.sensor2 = {Sen2[k]: neurons[i] for k, i in data["sensor2"].items()}
        obj.body = None
        obj.prn = Prn()
        obj.activity_log = []
        obj.ach_log = []
        obj.int_times_log = []
        obj.protocol.prn = obj.prn
        obj.motivation.prn = obj.prn
        for k, i in data["neurons"].items():
            setattr(obj, k, None if i is None else neurons[i])
        for k, items in data["lists"].items():
            setattr(obj, k, SynapseList.restore(items, neurons))
        obj.cycle = data["cycle"]
        obj.main_goal = data["main_goal"]
        if "workspace" in data:
            obj.workspace = Workspace.restore(data["workspace"], neurons)
        else:
            obj.workspace = Workspace(mode=obj.variant.workspace, fixed_bonus=obj.variant.workspace_fixed_bonus,
                                      ties=obj.variant.workspace_ties)
        obj.motivation.switch_bonus = obj.workspace.motive_switch_bonus()
        obj.ws_events = dict(data.get("ws_events", {"motive_switches": 0, "plans_carried_out": 0,
                                                    "plans_aborted": 0, "opportunistic": 0}))
        for k, v in copy.deepcopy(data["scalars"]).items():
            setattr(obj, k, v)
        return obj
