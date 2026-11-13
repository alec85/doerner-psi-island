"""Global Workspace with hysteresis (Phase 3, ADR 0016, ``docs/analyseplan-workspace.md``).

Once per cycle, after the goal list has been built, the modules offer
candidates with a strength: motives (motive strength), goals (value of the
goal link; an intermediate goal is worth the end goal it serves), objects of
the current situation (novelty or threat), situations recalled by
``Association`` (worth the goal they hold) and the end of the last plan (worth
the goal ``Planen`` found there). A neuron is offered once, with its strongest
reading, and on equal strength as its most specific kind (plan, memory, goal).
Ties between neurons go by name.
The current motive always holds one place; it is the winner of the motive
competition in ``Motivation``. The other ``K - 1`` places go to the strongest
remaining candidates, where contents already in the workspace get a bonus:

* ``threshold``: the selection threshold, for every kind of content (the
  hypothesis: Dörner's selection threshold is the special case for motives of
  this general bonus),
* ``motive_only``: the selection threshold for motives only,
* ``fixed``: a constant,
* ``none``: no bonus.

The capacity ``K`` grows with the resolution level (ADR 0016, question 3).

Strengths are read without side effects: no random draws, no time. The
workspace changes behaviour only through its broadcast, which the regulation
reads: goals in the workspace stand at the front of the goal list and are
always taken; objects in the workspace are checked first in ``LookAround`` and
always considered in ``WhatCouldBeDone``.

Every cycle is logged (``log``) for the measures W1 to W6 of the analysis plan.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

from psi_gw.memory.network import Axon, Neuron
from psi_gw.motivation.needs import NEEDS, Modulator, Motive

if TYPE_CHECKING:
    from psi_gw.state import PsiState

KINDS = ("motive", "goal", "object", "memory", "plan")
_SPECIFICITY = {"motive": 0, "object": 0, "goal": 1, "memory": 2, "plan": 3}
"""On equal strength a neuron is offered as its most specific kind: a goal that is the
end of the current plan is the plan, a goal recalled by ``Association`` a memory."""
K_MIN = 2
K_MAX = 7


@dataclass
class Content:
    """One content of the workspace."""

    kind: str
    neuron: Neuron
    strength: float
    since: int
    """Cycle in which it entered."""
    arousal_at_entry: float


@dataclass
class Workspace:
    """State of the workspace between two cycles."""

    mode: str = "off"
    fixed_bonus: float = 0.0
    ties: str = "name"
    """How equal effective strengths at the capacity boundary are resolved: ``name`` (neuron
    name, the rule of the confirmatory study) or ``random`` (ADR 0018, own random stream)."""
    tie_seed: int = 0
    """Seed of the own random stream for ``ties == "random"`` (the life's seed)."""
    contents: list[Content] = field(default_factory=list)
    memories: list[tuple[Neuron, Neuron]] = field(default_factory=list)
    """Situations recalled by the last ``Association`` with the goal each holds
    (candidates of kind memory, valued by that goal)."""
    plan_goal: Neuron | None = None
    """End of the last plan carried out (candidate of kind plan)."""
    plan_target: Neuron | None = None
    """The goal ``Planen`` found in that end; the plan is worth its goal value."""
    derived: dict[int, Neuron] = field(default_factory=dict)
    """Intermediate goal -> end goal it serves, filled by ``GoalGen`` each cycle (not saved:
    rebuilt before every competition)."""
    log: list[dict[str, Any]] = field(default_factory=list)
    """One record per cycle (output, not part of the snapshot)."""

    def __post_init__(self) -> None:
        self.tie_rng: np.random.Generator | None = None
        if self.ties == "random":
            # DEVIATION(ADR-0018): own stream, derived from the seed; Psi's random source is untouched.
            self.tie_rng = np.random.default_rng(np.random.SeedSequence(entropy=self.tie_seed, spawn_key=(18,)))
        elif self.ties != "name":
            raise ValueError(f"ties must be 'name' or 'random', not {self.ties!r}")

    @property
    def enabled(self) -> bool:
        return self.mode != "off"

    # --- reading ---------------------------------------------------------------------------------

    def attends(self, neuron: Neuron | None) -> bool:
        """Is ``neuron`` content of the workspace?"""
        return neuron is not None and any(c.neuron is neuron for c in self.contents)

    def goal_neurons(self) -> list[Neuron]:
        """Goal schemata in the workspace (goals, memories, plan), strongest first."""
        out = [c for c in self.contents if c.kind in ("goal", "memory", "plan")]
        out.sort(key=lambda c: (-c.strength, c.neuron.name))
        return [c.neuron for c in out]

    @staticmethod
    def capacity(resolution_level: float) -> int:
        """``K``: grows with the resolution level from ``K_MIN`` to ``K_MAX``."""
        rl = min(1.0, max(0.0, resolution_level))
        return round(K_MIN + (K_MAX - K_MIN) * rl)

    def bonus(self, kind: str, threshold: float) -> float:
        if self.mode == "threshold":
            return threshold
        if self.mode == "motive_only":
            return threshold if kind == "motive" else 0.0
        if self.mode == "fixed":
            return self.fixed_bonus
        return 0.0

    # --- candidates ------------------------------------------------------------------------------

    @staticmethod
    def goal_value(st: "PsiState", neuron: Neuron) -> float:
        """Value of a schema as a goal: the strongest need it satisfies, times link weight."""
        mot = st.motivation
        best = 0.0
        for m in NEEDS:
            need = mot.need_in[m]
            syn = need.axon[Axon.TO_GOAL].find(neuron)
            if syn is not None:
                best = max(best, need.activity * mot.params.needs[m].weight * syn.weight)
        return best

    def value_of_goal(self, st: "PsiState", neuron: Neuron) -> float:
        """Goal value; an intermediate goal without a link of its own is worth the end goal it serves."""
        direct = self.goal_value(st, neuron)
        end = self.derived.get(id(neuron))
        return max(direct, self.goal_value(st, end)) if end is not None else direct

    @classmethod
    def held_goal_value(cls, st: "PsiState", schema: Neuron, depth: int = 3) -> float:
        """Value of a situation as a goal: the best goal value among the schema itself and
        its parts (``sub`` links followed up to ``depth`` levels). The end of a plan is a
        place; it is worth what it holds."""
        best = cls.goal_value(st, schema)
        level, seen = [schema], {id(schema)}
        for _ in range(depth):
            nxt = []
            for n in level:
                for syn in n.axon[Axon.SUB]:
                    t = syn.target
                    if t is not None and id(t) not in seen:
                        seen.add(id(t))
                        nxt.append(t)
                        best = max(best, cls.goal_value(st, t))
            level = nxt
        return best

    @staticmethod
    def object_value(st: "PsiState", neuron: Neuron) -> float:
        """Salience of an object of the situation: novelty or threat, whichever is larger.

        Novelty: ``1 / (1 + n)`` with ``n`` the number of wholes (``sur``) the
        schema already belongs to, i.e. how often it has been seen. Threat: the
        strongest need with an aversion link to it, times link weight.
        """
        mot = st.motivation
        novelty = 1.0 / (1 + len(neuron.axon[Axon.SUR]))
        threat = 0.0
        for m in NEEDS:
            need = mot.need_in[m]
            syn = need.axon[Axon.TO_AVERS].find(neuron)
            if syn is not None:
                threat = max(threat, need.activity * mot.params.needs[m].weight * syn.weight)
        return max(novelty, threat)

    def candidates(self, st: "PsiState") -> list[tuple[str, Neuron, float]]:
        """All candidates except the current motive, one per neuron (the strongest reading)."""
        mot = st.motivation
        found: dict[int, tuple[str, Neuron, float]] = {}

        def offer(kind: str, neuron: Neuron | None, strength: float) -> None:
            if neuron is None or strength <= 0:
                return
            old = found.get(id(neuron))
            if old is None or strength > old[2] or (strength == old[2]
                                                    and _SPECIFICITY[kind] > _SPECIFICITY[old[0]]):
                found[id(neuron)] = (kind, neuron, strength)

        for m in NEEDS:
            if m is not mot.actual_motive:
                offer("motive", mot.need_in[m], mot.last_strengths.get(m, 0.0))
            need = mot.need_in[m]
            for syn in need.axon[Axon.TO_GOAL]:
                offer("goal", syn.target, need.activity * mot.params.needs[m].weight * syn.weight)
        for syn in st.goal_list:  # intermediate goals (InterMedGoals) and broadcast goals
            if syn.target is not None:
                offer("goal", syn.target, self.value_of_goal(st, syn.target))
        part = st.situation
        while part is not None:
            sub = part.axon[Axon.SUB].first
            if sub is not None and sub.target is not None:
                offer("object", sub.target, self.object_value(st, sub.target))
            por = part.axon[Axon.POR].first
            part = por.target if por is not None else None
        for situation, goal in self.memories:
            offer("memory", situation, self.value_of_goal(st, goal))
        if self.plan_goal is not None:
            value = (self.value_of_goal(st, self.plan_target) if self.plan_target is not None
                     else self.held_goal_value(st, self.plan_goal))
            offer("plan", self.plan_goal, value)
        return sorted(found.values(), key=lambda c: (-c[2], c[1].name))

    # --- competition ----------------------------------------------------------------------------

    def update(self, st: "PsiState") -> None:
        """Competition of one cycle; logs the result. Does nothing when off, except logging."""
        mot = st.motivation
        arousal = mot.aras.activity
        threshold = mot.modulators[Modulator.SELECT_THRESHOLD]
        rl = mot.modulators[Modulator.RESOLUTION_LEVEL]
        record: dict[str, Any] = {
            "cycle": st.cycle, "age": st.clock.age, "arousal": arousal, "threshold": threshold,
            "resolution": rl, "motive": mot.actual_motive.name,
            "events": dict(st.ws_events),
            "motive_strengths": {m.name: round(v, 6) for m, v in mot.last_strengths.items()},
            "lead_goal": (st.goal_list.first.target.name
                          if st.goal_list and st.goal_list.first.target is not None else None),
        }
        if not self.enabled:
            self.log.append(record)
            return
        k = self.capacity(rl)
        before = {id(c.neuron): c for c in self.contents}
        new: list[Content] = []
        if mot.actual_motive is not Motive.NIL:
            need = mot.need_in[mot.actual_motive]
            old = before.get(id(need))
            new.append(Content("motive", need, mot.last_strengths.get(mot.actual_motive, 0.0),
                               old.since if old else st.cycle, old.arousal_at_entry if old else arousal))
        slots = k - len(new)
        cands = self.candidates(st)
        diag: dict[str, Any] = {}
        for kind, neuron, strength in self.choose(cands, set(before), slots,
                                                  lambda kind: self.bonus(kind, threshold),
                                                  rng=self.tie_rng, diag=diag):
            old = before.get(id(neuron))
            new.append(Content(kind, neuron, strength, old.since if old else st.cycle,
                               old.arousal_at_entry if old else arousal))
        memoryless = {id(n) for _, n, _ in cands[:max(0, slots)]}
        others = new[1:] if mot.actual_motive is not Motive.NIL else new
        chosen = {id(c.neuron) for c in others}
        self.contents = new
        record.update({
            "k": k,
            "contents": [{"kind": c.kind, "name": c.neuron.name, "strength": round(c.strength, 6),
                          "since": c.since, "arousal_at_entry": round(c.arousal_at_entry, 6)} for c in new],
            "differs_from_memoryless": chosen != memoryless,
            # diagnostics (revision 2026-11-12); no effect on the selection
            "differs_from_any_memoryless": not self.memoryless_compatible(chosen, cands, slots),
            **diag,
        })
        self.log.append(record)

    @staticmethod
    def choose(candidates: list[tuple[str, Neuron, float]], incumbents: set[int], slots: int,
               bonus, rng: np.random.Generator | None = None,
               diag: dict[str, Any] | None = None) -> list[tuple[str, Neuron, float]]:
        """The ``slots`` winners among ``candidates`` (kind, neuron, strength).

        Candidates whose ``id(neuron)`` is in ``incumbents`` compete with
        ``strength + bonus(kind)``. Equal effective strengths go by neuron name;
        with ``rng`` (ADR 0018) the candidates tied at the capacity boundary are
        shuffled instead, and a draw happens only when such a tie exists.
        ``diag``, if given, receives the number of candidates, the free slots, the
        margin between the last winner and the first loser and whether they tie.
        """
        slots = max(0, slots)
        effective = []
        for kind, neuron, strength in candidates:
            b = bonus(kind) if id(neuron) in incumbents else 0.0
            effective.append((strength + b, kind, neuron, strength))
        effective.sort(key=lambda e: (-e[0], e[2].name))
        tie = 0 < slots < len(effective) and effective[slots - 1][0] == effective[slots][0]
        if diag is not None:
            diag["n_candidates"] = len(effective)
            diag["slots"] = slots
            diag["margin"] = (round(effective[slots - 1][0] - effective[slots][0], 9)
                              if 0 < slots < len(effective) else None)
            diag["tie_at_boundary"] = tie
        if tie and rng is not None:
            level = effective[slots - 1][0]
            group = [i for i, e in enumerate(effective) if e[0] == level]
            order = rng.permutation(len(group))
            shuffled = [effective[group[j]] for j in order]
            for i, e in zip(group, shuffled):
                effective[i] = e
        return [(kind, neuron, strength) for _, kind, neuron, strength in effective[:slots]]

    @staticmethod
    def memoryless_compatible(chosen: set[int], candidates: list[tuple[str, Neuron, float]], slots: int) -> bool:
        """Could a selection without bonus have chosen ``chosen`` (``id`` of neurons), with some
        resolution of ties at the boundary? Diagnostic for W6 independent of the tie rule."""
        slots = max(0, slots)
        if slots >= len(candidates):
            return chosen == {id(n) for _, n, _ in candidates}
        if slots == 0:
            return not chosen
        level = sorted((s for _, _, s in candidates), reverse=True)[slots - 1]
        above = {id(n) for _, n, s in candidates if s > level}
        at = {id(n) for _, n, s in candidates if s == level}
        return above <= chosen and chosen <= above | at and len(chosen) == min(slots, len(candidates))

    def motive_switch_bonus(self):
        """Bonus function for ``Motivation.switch_bonus``; ``None`` keeps the original rule."""
        if self.mode in ("off", "threshold", "motive_only"):
            return None
        if self.mode == "fixed":
            value = self.fixed_bonus
            return lambda threshold: value
        return lambda threshold: 0.0

    # --- persistence -----------------------------------------------------------------------------

    def snapshot(self, index: dict[int, int]) -> dict[str, Any]:
        return {"mode": self.mode, "fixed_bonus": self.fixed_bonus, "ties": self.ties, "tie_seed": self.tie_seed,
                "tie_rng": None if self.tie_rng is None else self.tie_rng.bit_generator.state,
                "contents": [{"kind": c.kind, "neuron": index[id(c.neuron)], "strength": c.strength,
                              "since": c.since, "arousal_at_entry": c.arousal_at_entry} for c in self.contents],
                "memories": [[index[id(s)], index[id(g)]] for s, g in self.memories],
                "plan_goal": None if self.plan_goal is None else index[id(self.plan_goal)],
                "plan_target": None if self.plan_target is None else index[id(self.plan_target)]}

    @classmethod
    def restore(cls, data: dict[str, Any], neurons: list[Neuron]) -> "Workspace":
        ws = cls(mode=data["mode"], fixed_bonus=data["fixed_bonus"], ties=data.get("ties", "name"),
                 tie_seed=data.get("tie_seed", 0))
        if data.get("tie_rng") is not None:
            ws.tie_rng.bit_generator.state = data["tie_rng"]
        ws.contents = [Content(c["kind"], neurons[c["neuron"]], c["strength"], c["since"], c["arousal_at_entry"])
                       for c in data["contents"]]
        ws.memories = [(neurons[s], neurons[g]) for s, g in data["memories"]]
        ws.plan_goal = None if data["plan_goal"] is None else neurons[data["plan_goal"]]
        ws.plan_target = None if data.get("plan_target") is None else neurons[data["plan_target"]]
        return ws
