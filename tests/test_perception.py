"""Perception (UPercept.Pas) against the original's activity protocol."""

from pathlib import Path

from psi_gw.body.island.body import IslandBody
from psi_gw.perception.percept import XYList, percept
from psi_gw.state import PsiState

ROOT = Path(__file__).resolve().parents[1]
ACTU = ROOT / "traces" / "original-runs" / "2026-11-10-zufallsmitschnitt" / "raw" / "seed16" / "actu16(1).Prt"


def started_state():
    st = PsiState(seed=16)
    st.body = IslandBody(st.rng, lambda: st.clock.age)
    st.body.client.on_manipulations = lambda kinds: None
    st.body.client.on_motivation = lambda n, v: None
    st.body.start()
    return st


def test_xylist_order_and_unsigned_format():
    lst = XYList()
    for p in [(10, 5), (2, 7), (10, 5), (2, 3), (100, 0)]:
        lst.add_xy(*p)
    assert [lst[i] for i in range(len(lst))] == [(2, 3), (2, 7), (10, 5), (100, 0)]
    assert lst.find_xy(10, 5) == (True, 2) and lst.find_xy(3, 3)[0] is False


def test_first_perception_equals_original_protocol():
    """Cycle 1, seed 16, Haselwald: objects, neuron names, positions and the situation."""
    st = started_state()
    neuron, loc = percept(st, (0, 0, 159, 159), False)
    text = ACTU.read_text(encoding="cp1252").replace("\r", "")
    block = text[text.index("  -? PERCEPTION"):text.index("Paaa->")].rstrip("\n").split("\n")
    assert st.prn.lines == block
    assert neuron.name == "Saaa" and loc == (81, 81)
    assert st.objekt is None  # perception leaves the global Objekt nil
    assert st.rng.draws == 0


def test_first_manipulation_like_the_original():
    """Approach Sdab at [121,140] and take it (cycle 1 of the original): same protocol lines,
    same new object Sdjf Hasel-, same learned goal, ReInforceRetro draws 68 numbers."""
    from psi_gw import action
    from psi_gw.memory.lists import Spat
    st = PsiState(seed=16)
    st.attach_body(IslandBody(st.rng, lambda: st.clock.age))
    st.body.start()
    sit, loc = percept(st, (0, 0, 159, 159), False)
    st.situation, st.loc_sit = sit, loc
    st.protocol.new_protocol(0)
    st.protocol.protocol(0, sit, "P", 1000, Spat())
    st.prn.clear()
    sdab = next(n for n in st.net.neurons if n.name == "Sdab")
    nehmen = next(s.target for s in st.mani_actors if s.target.name == "Nehmen")
    action.singular_manipul(st, sdab, (121, 140), nehmen)
    lines = [line for line in st.prn.lines if "PerceptZeit" not in line]
    assert lines[3:] == [
        "Paab->AAgg AAgg 1.00000",
        "Paac->Sdab Hasel 1.00000",
        "Paad->Nehmen Nehmen 1.00000",
        "  auf Sdab erzeugt  [121,140]  -? PERCEPTION: Was ist der Fall?",
        "      2-: Neues Objekt:  Sdjf Hasel-[  23   25]",
        "     1-: Wiedererkannt: Sdjf Hasel-[  15   35]",
        "  Das ändert was!",
        "  :- das ist Hasel-",
        "    *** Bedürfnisbefriedigung  Hunger MotivEffekt: -0.300",
        "    <> Lernen eines Ziels Sdab  Hasel",
        "  -* Consum-Verstärkung ab Saaa",
        "Paae->Sdjf Hasel- 1.00000",
    ]
    assert st.rng.draws == 68
