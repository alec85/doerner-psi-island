"""Behaviour cycle (TFPsi.Simulation, UFPsi.pas line 232) with stand-ins for unported parts."""

import csv
import gzip
from pathlib import Path

from psi_gw.agent import run_cycle, value_display
from psi_gw.counters import Performance
from psi_gw.memory import Axon, Spat
from psi_gw.motivation import Motive
from psi_gw.random_source import RecordingSource, ReplaySource
from psi_gw.state import PsiState
from psi_gw.triple import Triple

ROOT = Path(__file__).resolve().parents[1]
TRACE = ROOT / "traces" / "original-runs" / "2026-11-10-zufallsmitschnitt" / "random_draws.tsv.gz"


class Stub:
    """Records calls; perception returns a fixed situation neuron."""

    def __init__(self, state, look_around=Triple.FALSE, automatism=Triple.FALSE, plan=Triple.FALSE):
        self.calls = []
        self.situation = state.net.new_neuron("Ssit")
        self.results = {"look_around": look_around, "automatism": automatism, "plan_and_do": plan}

    def pump(self, state):
        self.calls.append("pump")

    def percept_reorientation(self, state):
        self.calls.append("percept")
        return self.situation, Spat()

    def situation_name(self, state):
        return "Haselwald"

    def object_name(self, state):
        return "-"

    def part_name(self, state, name):
        return name

    def look_around(self, state):
        self.calls.append("look_around")
        return self.results["look_around"]

    def regress(self, state):
        self.calls.append("regress")

    def automatism(self, state, aspect):
        self.calls.append("automatism")
        return self.results["automatism"]

    def plan_and_do(self, state, aspect):
        self.calls.append("plan_and_do")
        return self.results["plan_and_do"]

    def what_could_be_done(self, state):
        self.calls.append("what_could_be_done")

    def rest(self, state):
        self.calls.append("rest")


def test_first_cycle_without_goals():
    st = PsiState(seed=16)
    stub = Stub(st)
    run_cycle(st, stub)
    assert st.cycle == 1
    assert stub.calls == ["pump", "percept", "pump", "pump", "what_could_be_done", "pump", "pump"]
    assert st.protocol.head(0).axon[Axon.SUB].first.target is stub.situation
    assert st.situation is stub.situation
    assert st.motivation.actual_motive is Motive.NUKLEO and not st.goal_list
    assert st.locations == [["Haselwald", 1]] and st.counters.performance[Performance.NLoc] == 1
    assert st.rng.draws == 0  # nothing learned yet, nothing to traverse


def test_no_reorientation_after_new_orientation():
    st = PsiState(seed=16)
    stub = Stub(st)
    st.new_oriented = True
    st.situation = stub.situation
    run_cycle(st, stub)
    assert "percept" not in stub.calls and st.new_oriented is False


def test_exitus_resupplies():
    st = PsiState(seed=16)
    stub = Stub(st)
    st.motivation.store[Motive.DURST] = 0.0005
    st.need_ext_vers = 99_000
    st.clock.age = 2_000
    run_cycle(st, stub)
    assert st.n_exitus == 1 and st.counters.performance[Performance.NExit] == 1
    assert st.need_ext_vers == 0
    assert st.motivation.store[Motive.DURST] > 0.99  # refilled, then thirst grows again in Motivation
    assert st.counters.performance[Performance.DiffLife] == 2_000


def with_goal(stream):
    """Nukleo knows goal G, preceded by a sensory neuron (EpiKomp = log10(1 + 0.2))."""
    st = PsiState(seed=16)
    st.net.rng = RecordingSource(ReplaySource(stream))
    st.rng = st.net.rng
    pre, goal = st.net.new_neuron("Spre"), st.net.new_neuron("Sgoal")
    st.net.connect(pre, goal, Axon.POR, 1)
    st.net.connect(st.motivation.need_in[Motive.NUKLEO], goal, Axon.TO_GOAL, 1)
    return st


def test_quick_move_draw_order():
    """EpiKomp draws before the first random of the QuickMove test (order seen in the trace)."""
    st = with_goal([0, 0, 0, 0, 0, 0, 0, 0.05, 0.1, 0, 0])
    stub = Stub(st)
    run_cycle(st, stub)
    assert st.quick_move is True and st.main_goal is True
    assert stub.calls == ["pump", "percept", "pump", "look_around", "pump", "what_could_be_done", "pump", "pump"]
    assert [d.site for d in st.rng.log] == [
        "UStrukturen.Decay#1", "UStrukturen.Junction#1",                        # MotiveStrength(Nukleo)
        "UStrukturen.Decay#1", "UStrukturen.Junction#1", "UPSIMain.GoalGen#1",  # GoalGen
        "UStrukturen.Decay#1", "UStrukturen.Junction#1",                        # EpiKomp(Nukleo)
        "UFPsi.TFPsi.Simulation#1", "UFPsi.TFPsi.Simulation#2",                 # QuickMove
        "UStrukturen.Decay#1", "UStrukturen.Junction#1",                        # value display
    ]


def test_ladder_without_quick_move():
    st = with_goal([0, 0, 0, 0, 0, 0, 0, 0.5, 0, 0])
    stub = Stub(st, automatism=Triple.FALSE, plan=Triple.FALSE)
    run_cycle(st, stub)
    assert st.quick_move is False
    assert stub.calls == ["pump", "percept", "pump", "look_around", "pump",
                          "automatism", "plan_and_do", "what_could_be_done", "pump", "pump"]


def test_successful_look_around_skips_ladder():
    st = with_goal([0, 0, 0, 0, 0, 0, 0])
    stub = Stub(st, look_around=Triple.TRUE)
    run_cycle(st, stub)
    assert stub.calls == ["pump", "percept", "pump", "look_around", "pump", "pump", "pump"]


def test_value_display_changes_memory_and_time():
    st = with_goal([0.5, 0.5])
    age = st.clock.age
    value_display(st)
    assert st.rng.draws == 2 and st.clock.age - age == 2  # one per goal link, one for its ret link


def test_original_quick_move_test_preceded_by_epikomp():
    """In the trace, every draw of TFPsi.Simulation#1 directly follows a Decay/Junction pair of
    EpiKomp called from the main loop (return address 0x49F593 of that call)."""
    with gzip.open(TRACE, "rt", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    hits = [i for i, r in enumerate(rows) if r["site"] == "UFPsi.TFPsi.Simulation#1"]
    assert len(hits) == 21
    for i in hits:
        decay, junction = rows[i - 2], rows[i - 1]
        assert (decay["site"], junction["site"]) == ("UStrukturen.Decay#1", "UStrukturen.Junction#1")
        assert junction["ret2"] == "0049F593"


def test_original_value_display_draws():
    """The trace contains Junction draws of EpiKomp called from the value display (0x49F95F ff.)."""
    with gzip.open(TRACE, "rt", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    display = {"0049F95F", "0049F990", "0049F9C1", "0049F9F2", "0049FA23", "0049FA54", "0049FA85"}
    n = sum(1 for r in rows if r["site"] == "UStrukturen.Junction#1" and r["ret2"] in display)
    assert n == 101


def _code_bytes(exe: Path, start: int, end: int) -> bytes:
    """Bytes of Psi.exe between two virtual addresses (minimal PE section lookup)."""
    import struct
    data = exe.read_bytes()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    n_sections = struct.unpack_from("<H", data, pe + 6)[0]
    opt_size = struct.unpack_from("<H", data, pe + 20)[0]
    image_base = struct.unpack_from("<I", data, pe + 24 + 28)[0]
    table = pe + 24 + opt_size
    for i in range(n_sections):
        _, vsize, vaddr, rsize, raddr = struct.unpack_from("<8sIIII", data, table + 40 * i)
        lo = image_base + vaddr
        if lo <= start and end <= lo + max(vsize, rsize):
            return data[raddr + start - lo: raddr + end - lo]
    raise ValueError("address range not in one section")


def test_value_display_order_in_machine_code():
    """The display calls EpiKomp (0x47B250) with motives 1, 2, 3, 4, 6, 5, 7 (``mov al, n; call``)."""
    exe = ROOT / "reference" / "delphi-runtime" / "PsiCode" / "Psi.exe"
    start, end = 0x49F940, 0x49FA90
    code = _code_bytes(exe, start, end)
    motives = []
    for i in range(len(code) - 7):
        if code[i] == 0xB0 and code[i + 2] == 0xE8:
            rel = int.from_bytes(code[i + 3:i + 7], "little", signed=True)
            if start + i + 7 + rel == 0x47B250:
                motives.append(Motive(code[i + 1]))
    from psi_gw.agent import DISPLAY_ORDER
    assert tuple(motives) == DISPLAY_ORDER
