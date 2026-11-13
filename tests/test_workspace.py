"""Global Workspace with hysteresis (ADR 0016, docs/analyseplan-workspace.md)."""

import json

import pytest

from psi_gw.analysis.workspace_metrics import lead_goal_switches, spells, workspace_metrics
from psi_gw.life import IslandLife
from psi_gw.memory.network import Neuron
from psi_gw.variant import Variant
from psi_gw.workspace import K_MAX, K_MIN, Workspace


def test_variant_parses_workspace_conditions():
    v = Variant.from_names("all,workspace=threshold")
    assert v.workspace == "threshold" and v.no_display_side_effects
    assert v.active()[-1] == "workspace=threshold"
    d = Variant.from_names("all,workspace=fixed,workspace_fixed_bonus=0.066")
    assert d.workspace_fixed_bonus == pytest.approx(0.066)
    assert d.active()[-2:] == ["workspace=fixed", "workspace_fixed_bonus=0.066"]
    assert Variant.from_names("all").workspace == "off"
    with pytest.raises(ValueError):
        Variant.from_names("workspace=sometimes")


def test_capacity_grows_with_resolution_level():
    assert Workspace.capacity(0.0) == K_MIN
    assert Workspace.capacity(1.0) == K_MAX
    assert Workspace.capacity(-1) == K_MIN and Workspace.capacity(2) == K_MAX
    ks = [Workspace.capacity(x / 20) for x in range(21)]
    assert ks == sorted(ks)


@pytest.mark.parametrize("mode, motive, goal", [
    ("threshold", 0.05, 0.05), ("motive_only", 0.05, 0.0), ("fixed", 0.3, 0.3), ("none", 0.0, 0.0)])
def test_bonus_by_condition(mode, motive, goal):
    ws = Workspace(mode=mode, fixed_bonus=0.3)
    assert ws.bonus("motive", 0.05) == motive
    assert ws.bonus("goal", 0.05) == goal


def test_motive_switch_bonus_replaces_the_threshold_only_where_planned():
    assert Workspace(mode="off").motive_switch_bonus() is None
    assert Workspace(mode="threshold").motive_switch_bonus() is None
    assert Workspace(mode="motive_only").motive_switch_bonus() is None
    assert Workspace(mode="fixed", fixed_bonus=0.2).motive_switch_bonus()(0.05) == 0.2
    assert Workspace(mode="none").motive_switch_bonus()(0.05) == 0.0


def test_incumbent_keeps_its_place_against_a_slightly_stronger_newcomer():
    old, new, weak = Neuron("Sold"), Neuron("Snew"), Neuron("Sweak")
    cands = [("goal", new, 0.48), ("goal", old, 0.45), ("object", weak, 0.1)]
    with_bonus = Workspace.choose(cands, {id(old)}, 1, lambda kind: 0.05)
    assert [n for _, n, _ in with_bonus] == [old]
    without = Workspace.choose(cands, {id(old)}, 1, lambda kind: 0.0)
    assert [n for _, n, _ in without] == [new]
    # a clearly stronger newcomer wins anyway
    assert Workspace.choose([("goal", new, 0.6), ("goal", old, 0.45)], {id(old)}, 1,
                            lambda kind: 0.05)[0][1] is new


def test_switched_off_workspace_only_logs():
    life = IslandLife(seed=16, variant=Variant.from_names("all"))
    life.run(15)
    st = life.state
    assert st.workspace.contents == [] and st.motivation.switch_bonus is None
    assert len(st.workspace.log) == 15 and "contents" not in st.workspace.log[0]
    assert not any("Workspace" in line for line in st.prn.lines)


def test_workspace_holds_the_current_motive_and_at_most_k_contents():
    life = IslandLife(seed=16, variant=Variant.from_names("all,workspace=threshold"))
    life.run(25)
    for r in life.state.workspace.log:
        assert len(r["contents"]) <= r["k"]
        if r["motive"] != "NIL":
            assert r["contents"][0]["kind"] == "motive"


def test_resumed_workspace_life_equals_an_uninterrupted_one():
    v = Variant.from_names("all,workspace=threshold")
    a = IslandLife(seed=16, variant=v)
    a.run(20)
    data = json.loads(json.dumps(a.snapshot()))
    a.run(10)
    b = IslandLife.restore(data)
    b.run(10)
    tail = b.state.prn.lines
    assert tail and tail == a.state.prn.lines[-len(tail):]
    assert [(c.kind, c.neuron.name, c.since) for c in b.state.workspace.contents] == \
        [(c.kind, c.neuron.name, c.since) for c in a.state.workspace.contents]
    assert b.state.ws_events == a.state.ws_events


def _rec(cycle, contents, lead=None, arousal=0.5, differs=False):
    return {"cycle": cycle, "arousal": arousal, "lead_goal": lead, "differs_from_memoryless": differs,
            "contents": [{"kind": k, "name": n} for k, n in contents]}


def test_spells_and_goal_switches():
    recs = [_rec(1, [("motive", "M"), ("goal", "A")], "A", arousal=0.2),
            _rec(2, [("motive", "M"), ("goal", "A")], "A"),
            _rec(3, [("motive", "M"), ("goal", "B")], "B", arousal=0.9),
            _rec(4, [("motive", "M"), ("goal", "A")], None)]
    sp = sorted((s["name"], s["length"], s["arousal"]) for s in spells(recs))
    assert sp == [("A", 1, 0.5), ("A", 2, 0.2), ("B", 1, 0.9), ("M", 4, 0.2)]
    assert lead_goal_switches(recs) == 1


def test_workspace_metrics_from_a_log_file(tmp_path):
    recs = [_rec(i, [("motive", "M"), ("goal", "A" if i < 6 else "B")], "A" if i < 6 else "B",
                 differs=i % 2 == 0) for i in range(1, 11)]
    final = {"final": True, "cycles": 10,
             "events": {"motive_switches": 1, "plans_carried_out": 4, "plans_aborted": 2, "opportunistic": 3}}
    path = tmp_path / "Workspace(1).jsonl"
    path.write_bytes(("\r\n".join(json.dumps(r) for r in [*recs, final]) + "\r\n").encode("cp1252"))
    m = workspace_metrics(path)
    assert m["W1_dwell_motive"] == 10 and m["W1_dwell_goal"] == 5
    assert m["W2_motive_switches_per_100"] == 10
    assert m["W2b_lead_goal_switches_per_100"] == 10
    assert m["W3_plans_aborted_per_100"] == 20
    assert m["W4_opportunistic_per_100"] == 30
    assert m["W6_share_history_dependent"] == 0.5


# --- ADR 0018: random tie-breaking, and selection diagnostics (revision 2026-11-12) -------------

def test_random_ties_draw_only_at_a_boundary_tie_and_are_reproducible():
    import numpy as np
    a, b, c = Neuron("Sa"), Neuron("Sb"), Neuron("Sc")
    no_tie = [("goal", a, 0.5), ("goal", b, 0.4), ("goal", c, 0.3)]
    rng = np.random.default_rng(1)
    state = rng.bit_generator.state
    assert [n for _, n, _ in Workspace.choose(no_tie, set(), 1, lambda k: 0.0, rng=rng)] == [a]
    assert rng.bit_generator.state == state  # no draw without a tie
    tie = [("goal", a, 0.5), ("goal", b, 0.5), ("goal", c, 0.5)]
    picks = {Workspace.choose(tie, set(), 1, lambda k: 0.0, rng=np.random.default_rng(s))[0][1].name
             for s in range(30)}
    assert picks == {"Sa", "Sb", "Sc"}
    first = [Workspace.choose(tie, set(), 2, lambda k: 0.0, rng=np.random.default_rng(7)) for _ in range(2)]
    assert [n for _, n, _ in first[0]] == [n for _, n, _ in first[1]]


def test_selection_diagnostics_and_memoryless_compatibility():
    a, b, c, d = Neuron("Sa"), Neuron("Sb"), Neuron("Sc"), Neuron("Sd")
    cands = [("goal", a, 0.6), ("goal", b, 0.5), ("goal", c, 0.5), ("object", d, 0.1)]
    diag = {}
    won = Workspace.choose(cands, {id(c)}, 2, lambda k: 0.05, diag=diag)
    assert [n for _, n, _ in won] == [a, c]
    assert diag["n_candidates"] == 4 and diag["slots"] == 2
    assert diag["margin"] == pytest.approx(0.05) and not diag["tie_at_boundary"]
    # {a, c} is a possible memoryless choice (b and c tie without bonus); {a, d} is not
    assert Workspace.memoryless_compatible({id(a), id(c)}, cands, 2)
    assert not Workspace.memoryless_compatible({id(a), id(d)}, cands, 2)


def test_variant_parses_tie_rule():
    v = Variant.from_names("all,workspace=none,workspace_ties=random")
    assert v.workspace_ties == "random" and v.active()[-1] == "workspace_ties=random"
    with pytest.raises(ValueError):
        Variant.from_names("all,workspace=none,workspace_ties=coin")


def test_resumed_life_with_random_ties_equals_an_uninterrupted_one():
    v = Variant.from_names("all,workspace=none,workspace_ties=random")
    a = IslandLife(seed=16, variant=v)
    a.run(20)
    data = json.loads(json.dumps(a.snapshot()))
    a.run(10)
    b = IslandLife.restore(data)
    b.run(10)
    tail = b.state.prn.lines
    assert tail and tail == a.state.prn.lines[-len(tail):]
    assert [(c.kind, c.neuron.name) for c in b.state.workspace.contents] == \
        [(c.kind, c.neuron.name) for c in a.state.workspace.contents]
