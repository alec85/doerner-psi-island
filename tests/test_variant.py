"""Switches for artefacts of the original (ADR 0015)."""

import pytest

from psi_gw.life import IslandLife
from psi_gw.state import PsiState
from psi_gw.variant import Variant


def test_reference_is_default_and_names_are_checked():
    assert Variant().active() == []
    assert Variant.from_names("all").active() == [
        "no_display_side_effects", "clean_direction_names", "goal_in_current_situation",
        "aversion_check_in_aversions", "background_goals_as_described", "guard_nil_dereferences",
        "real_umlaut_bitmaps"]
    with pytest.raises(ValueError):
        Variant.from_names("no_such_switch")


def test_variant_survives_a_snapshot():
    st = PsiState(seed=16, variant=Variant(clean_direction_names=True))
    assert PsiState.restore(st.snapshot()).variant == Variant(clean_direction_names=True)


def test_display_switch_skips_the_value_display(monkeypatch):
    import psi_gw.agent as agent
    calls = []
    monkeypatch.setattr(agent, "value_display", lambda st: calls.append(st.cycle))
    IslandLife(seed=16, variant=Variant(no_display_side_effects=True)).run(3)
    assert calls == []
    IslandLife(seed=16).run(3)
    assert calls == [1, 2, 3]


def test_all_switches_run_a_life_segment():
    life = IslandLife(seed=16, variant=Variant.from_names("all"))
    life.run(40)
    assert life.state.cycle == 40


def test_umlaut_switch_uses_the_files():
    life = IslandLife(seed=16, variant=Variant(real_umlaut_bitmaps=True))
    bm = life.state.body.bitmaps.get("Bergdurchhämmern1")
    ref = IslandLife(seed=16).state.body.bitmaps.get("Bergdurchhämmern1")
    assert (bm.bitmap.pixels != ref.bitmap.pixels).any()
