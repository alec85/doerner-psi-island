"""A whole Psi life on the island in reference mode (ADR 0010, ADR 0012).

Joins the ported parts the way the original's main form does
(``TFPsi.FormCreate``, ``TFPsi.WMFirst`` and the simulation timer,
``UFPsi.pas``): a :class:`~psi_gw.state.PsiState`, the island as its body,
and the regulation procedures of ``UPSIMain`` as the faculties of the
behaviour cycle (:func:`psi_gw.agent.run_cycle`).

Example::

    life = IslandLife(seed=16)
    life.run(cycles=29)
    life.state.prn.lines      # the activity protocol (actu16.Prt)
"""

from __future__ import annotations

import json

from psi_gw import action
from psi_gw.agent import run_cycle, write_int_times
from psi_gw.body.island.bitmaps import BitmapStore
from psi_gw.body.island.body import IslandBody
from psi_gw.body.island.world import Reality
from psi_gw.body.island.x87 import str_real
from psi_gw.counters import IntProc, Performance
from psi_gw.memory.lists import NilDereference, Spat
from psi_gw.memory.network import Neuron
from psi_gw.motivation.needs import NEEDS
from psi_gw.perception.percept import Perception
from psi_gw.random_source import RandomSource
from psi_gw.regulation.ladder import Regulation
from psi_gw.state import PsiState
from psi_gw.triple import Triple
from psi_gw.variant import Variant


class IslandFaculties:
    """The faculties of :func:`run_cycle` for a Psi living on the island."""

    def __init__(self, state: PsiState) -> None:
        self.reg = Regulation(state)

    def pump(self, state: PsiState) -> None:
        state.body.pump()

    def percept_reorientation(self, state: PsiState) -> tuple[Neuron, Spat]:
        situation, loc = Perception(state, state.body.act_sit()).run(action.TOTAL_VIEW, False)
        if loc is not None:
            state.loc_sit = loc
        # DEVIATION(ADR-0010): SpatSit is an uninitialised local of
        # TFPsi.Simulation; its x and y end up in the protocol links. Zero here.
        return situation, Spat()

    def situation_name(self, state: PsiState) -> str:
        return state.body.situation_name

    def object_name(self, state: PsiState) -> str:
        return state.body.object_name

    def part_name(self, state: PsiState, neuron_name: str) -> str:
        return state.body.client.get_part_name(neuron_name)

    def _guarded(self, state: PsiState, step, failed):
        """Run a regulation step. With ``guard_nil_dereferences`` a nil access, where the
        original would crash, ends the step as failed (ADR 0015)."""
        if not state.variant.guard_nil_dereferences:
            return step()
        try:
            return step()
        except NilDereference as exc:
            state.n_guarded += 1
            state.prn.writeln(f"  !!! nil abgefangen: {exc}")
            return failed

    def look_around(self, state: PsiState) -> Triple:
        return self._guarded(state, self.reg.look_around, Triple.FALSE)

    def regress(self, state: PsiState) -> None:
        action.regress(state)

    def automatism(self, state: PsiState, aspect: Neuron | None) -> Triple:
        return self._guarded(state, lambda: self.reg.automatismus(aspect, state.goal_list), Triple.FALSE)

    def plan_and_do(self, state: PsiState, aspect: Neuron | None) -> Triple:
        return self._guarded(state, lambda: self.reg.planen_und_tun(aspect, state.goal_list), Triple.FALSE)

    def what_could_be_done(self, state: PsiState) -> None:
        self._guarded(state, self.reg.what_could_be_done, None)

    def rest(self, state: PsiState) -> None:
        self.reg.ruhe()


class IslandLife:
    """One Psi on the island, started like the original."""

    def __init__(self, seed: int = 16, rng: RandomSource | None = None, max_life: int = 0,
                 variant: Variant | None = None) -> None:
        self.state = PsiState(seed=seed, rng=rng, variant=variant)
        st = self.state
        st.max_life = max_life
        reality = Reality(bitmaps=BitmapStore(wine_names=not st.variant.real_umlaut_bitmaps))
        st.attach_body(IslandBody(st.rng, lambda: st.clock.age, reality))
        st.body.start()
        self.faculties = IslandFaculties(st)

    # --- persistence ------------------------------------------------------------------------------

    def snapshot(self) -> dict:
        """Psi and the island between two cycles, JSON compatible (protocol texts are output, not state)."""
        return {"state": self.state.snapshot(), "body": self.state.body.snapshot(), "ended": self.ended}

    @classmethod
    def restore(cls, data: dict, rng_wrap=None) -> "IslandLife":
        """Continue a life from :meth:`snapshot`; the continuation equals an uninterrupted run.

        Args:
            rng_wrap: optional function applied to the restored random source,
                e.g. ``RecordingSource``.
        """
        life = cls.__new__(cls)
        st = PsiState.restore(data["state"], wrap=rng_wrap)
        life.state = st
        reality = Reality(bitmaps=BitmapStore(wine_names=not st.variant.real_umlaut_bitmaps))
        body = IslandBody(st.rng, lambda: st.clock.age, reality)
        st.attach_body(body)
        body.restore_from(data["body"])
        life.faculties = IslandFaculties(st)
        life.ended = data["ended"]
        return life

    def cycle(self) -> None:
        run_cycle(self.state, self.faculties)

    def run(self, cycles: int) -> None:
        for _ in range(cycles):
            self.cycle()

    def run_life(self, max_life: int, max_cycles: int | None = None) -> None:
        """Run cycles until the age reaches ``max_life`` (``CheckMaxLife``, UParam.pas line 27).

        The original checks at the start of each cycle, after a pass of the
        message loop, and ends the protocol with ``Ende der Simulation``.
        """
        n = 0
        while max_cycles is None or n < max_cycles:
            if self.check_max_life(max_life):
                return
            self.cycle()
            n += 1

    def check_max_life(self, max_life: int) -> bool:
        """``CheckMaxLife`` before a cycle: True (and the closing protocol line) if life is over."""
        st = self.state
        st.max_life = max_life
        if max_life > 0 and st.clock.age >= max_life:
            st.body.pump()
            st.prn.writeln("Ende der Simulation: <time>")
            # the cycle block is skipped, the time line of this call is still written
            write_int_times(st)
            self.ended = True
        return self.ended

    ended = False

    # --- protocol files -----------------------------------------------------------------------------

    def protocol_files(self, seed: int) -> dict[str, list[str]]:
        """All protocol files the original writes for one life, by file name, as lines.

        Wall clock times of the original are written as ``<time>``. Not produced:
        the event protocol ``Protokoll.Dat`` and the time series (``Motive.csv``
        and the like), which the original fills from a 500 ms wall clock timer.
        """
        st = self.state
        files = {
            f"actu{seed}(1).Prt": [f"Protokoll für Dietrich Dörner und Jürgen Gerdes: Psi 4.9.1.200, <time>",
                                   *st.prn.lines],
            f"seed{seed}.Prt": [f"PsiAlpha2 Probelauf: {seed:3d} <time>",
                                "       NsL  NuL NLoc  NEx  NAg  NsM  NuM  Nuk  Hun  Dur Scha  Affil  Age       Diff",
                                *st.ach_log],
            "IntTimes(1).Txt": ["Cycle     LookAr      Auto      Plan      WCBD        SS", *st.int_times_log],
            "Activities(1).Txt": list(st.activity_log),
            "Workspace(1).jsonl": [json.dumps(r, ensure_ascii=False) for r in st.workspace.log]
            + [json.dumps({"final": True, "cycles": st.cycle, "events": st.ws_events,
                           "variant": st.variant.active()}, ensure_ascii=False)],
        }
        if self.ended:
            files.update({f"{name}(1).Prt": lines for name, lines in self.summary_files(seed).items()})
        return files

    def write_protocols(self, directory, seed: int) -> list:
        """Write :meth:`protocol_files` like the original (code page 1252, CRLF)."""
        from pathlib import Path
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        paths = []
        for name, lines in self.protocol_files(seed).items():
            path = directory / name
            path.write_bytes(("\r\n".join(lines) + "\r\n").encode("cp1252"))
            paths.append(path)
        return paths

    # --- summary files written at the end of life (CheckMaxLife) -------------------------------------

    def summary_files(self, batnr: int) -> dict[str, list[str]]:
        """Lines of ``eAch``, ``Inpro`` and ``Consum`` as the original writes them at the end of life."""
        st = self.state
        c = st.counters
        perf = list(c.performance)
        for p in (Performance.Hun, Performance.Dur, Performance.Scha, Performance.Affil):
            # Delphi's Round rounds halves to even, like Python's round.
            perf[p] = round(st.sum_leist[p] / st.cycle)
        each = ["      NsL  NuL NLoc  NEx  NAg  NsM  NuM NNuk  Hun  Dur Scha  Affil",
                f"{batnr:4d}" + "".join(f"{perf[p]:5d}" for p in Performance if p <= Performance.Affil)]
        names = "; ".join(p.name for p in IntProc)
        inpro = [" " + names,
                 f"{batnr:5d};" + "".join(f"{v:5d};" for v in c.int_proc),
                 "".join(f"{v:7d};" for v in c.proc_times),
                 "".join(f"{v:7d};" for v in c.check_freq)]
        mot = st.motivation
        consum = ["        Hung   Durs    Nuk   Scha   Best   Komp   Affili  Hung   Durs    Nuk   Scha   Best   Komp  Affili",
                  f"{batnr:5d}" + "".join(str_real(mot.total_consum[m], 7, 2) for m in NEEDS)
                  + "".join(str_real(mot.total_in[m], 7, 2) for m in NEEDS)]
        return {"eAch": each, "Inpro": inpro, "Consum": consum}
