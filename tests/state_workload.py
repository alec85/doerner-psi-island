"""Deterministic workload on a PsiState for the snapshot acceptance test (ADR 0010).

All choices are drawn from the state's own random source, so the workload
depends on nothing but the saved state. Not a test module itself.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from typing import Any

from psi_gw.memory import Axon, NilDereference, Spat
from psi_gw.motivation import NEEDS, Motive
from psi_gw.motivation.goals import goal_gen
from psi_gw.params import read_param_dat
from psi_gw.random_source import DelphiRandom, RecordingSource
from psi_gw.state import PsiState

AXES = list(Axon)


def new_state(seed: int) -> PsiState:
    params = read_param_dat()
    # A non-zero forgetting rate, so that Decay really changes weights.
    params = replace(params, memory=replace(params.memory, forgetting_rate=1e-4))
    st = PsiState(params, RecordingSource(DelphiRandom(seed)))
    for i in range(6):
        st.net.new_neuron(f"S{i}")
    return st


def step(st: PsiState) -> None:
    net, rng, mot = st.net, st.rng, st.motivation
    pick = lambda: net.neurons[rng.randint(len(net.neurons), site="workload")]  # noqa: E731
    op = rng.randint(12, site="workload")
    a, b = pick(), pick()
    axon = AXES[rng.randint(len(AXES), site="workload")]
    if op in (1, 2, 3) and a.axon[axon]:
        # follow an existing link most of the time, so transmission really happens
        b = a.axon[axon][rng.randint(len(a.axon[axon]), site="workload")].target
    if op == 0:
        net.connect(a, b, axon, rng.random(site="workload"),
                    Spat(rng.randint(5, site="workload") - 2, rng.randint(5, site="workload") - 2))
    elif op in (1, 2):
        net.transmit(a, b, axon)
    elif op == 3:
        net.reinforce(a, b, axon, 0.01)
    elif op == 4:
        st.clock.advance(rng.random(site="workload") * 300)
    elif op == 5:
        a.axon[axon].section(b.axon[axon], 0.5, rng)
        a.axon[axon].random_choice(rng)
    elif op == 6:
        layer = rng.randint(4, site="workload")
        st.protocol.protocol(layer, a, "P" if layer == 0 else "S", 1000, Spat(1, 0))
    elif op == 7:
        st.protocol.new_protocol(rng.randint(4, site="workload"))
    elif op == 8:
        try:
            st.protocol.reinforce_retro(a, 0.5)
        except NilDereference:
            pass
    elif op == 9:
        # learn a goal for a need, so that EpiKomp has something to traverse
        need = NEEDS[rng.randint(len(NEEDS), site="workload")]
        net.connect(mot.need_in[need], a, Axon.TO_GOAL, 1)
    elif op == 10:
        need = NEEDS[rng.randint(len(NEEDS), site="workload")]
        mot.consumption(need, rng.random(site="workload") - 0.5)
        mot.competence_certainty(1 + rng.randint(29, site="workload"), rng.random(site="workload"), 0.5)
    else:
        st.cycle += 1
        mot.need_and_competence()
        try:
            mot.actual_motive = mot.motivation()
            if mot.actual_motive is not Motive.NIL:
                st.main_goal = goal_gen(mot, st.goal_list, st.mani_actors)
        except NilDereference:
            pass


def snapshot(st: PsiState) -> dict[str, Any]:
    return st.snapshot()


def restore(data: dict[str, Any]) -> PsiState:
    return PsiState.restore(data, wrap=RecordingSource)


def fingerprint(st: PsiState) -> str:
    """Hash of the complete state, to compare runs after every step."""
    return hashlib.sha256(json.dumps(st.snapshot(), sort_keys=True).encode()).hexdigest()


def run(st: PsiState, steps: int) -> list[str]:
    """Advance ``steps`` steps and return the state fingerprint after each."""
    prints = []
    for _ in range(steps):
        step(st)
        prints.append(fingerprint(st))
    return prints


def draw_log(st: PsiState) -> list[list[Any]]:
    return [[d.nr, d.kind, d.n, d.site, d.value, d.state_before] for d in st.rng.log]

