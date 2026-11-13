"""The island world as Psi's body (ADR 0010, ADR 0012).

Joins the world (:mod:`world`) and Psi's client (:mod:`client`) through two
message queues instead of the original's socket. Messages keep the original
text format.

``pump`` stands for one pass of the original's message loop
(``Application.ProcessMessages``): all waiting messages are delivered in both
directions until none is left, then the timer for delayed object changes
fires, and the resulting messages are delivered as well (ADR 0012, decision
3; the timer runs with 1 ms in the reference runs).

The request methods (``aggression``, ``regression``, ``move_to_situation``,
``manipulate``) are the client functions the original's cognition calls
(``UAction.pas``). Each sends its request and waits for the world's ``OK``
(``TPsiClient.Wait``).
"""

from __future__ import annotations

from typing import Callable

import numpy as np

from psi_gw.body.island.bitmaps import BitmapStore
from psi_gw.body.island.client import IslandClient
from psi_gw.body.island.world import Reality, WorldPsi
from psi_gw.random_source import RandomSource

MAX_ROUNDS = 1000


class IslandBody:
    """World plus client, connected by in-process queues."""

    def __init__(self, rng: RandomSource, age: Callable[[], int], reality: Reality | None = None) -> None:
        self.reality = reality if reality is not None else Reality()
        self.bitmaps: BitmapStore = self.reality.bitmaps
        self.to_world: list[str] = []
        self.to_client: list[str] = []
        self.world = WorldPsi(self.reality, rng, self.to_client.append)
        self.client = IslandClient(self.bitmaps, self.to_world.append, age)
        self.log: list[tuple[str, str]] = []
        """Every delivered message as ``(direction, text)``, for tests and tracing."""

    # --- message loop ------------------------------------------------------------------------

    def _deliver(self) -> None:
        for _ in range(MAX_ROUNDS):
            if not self.to_world and not self.to_client:
                return
            while self.to_world:
                msg = self.to_world.pop(0)
                self.log.append((">", msg))
                self.world.receive(msg)
            while self.to_client:
                msg = self.to_client.pop(0)
                self.log.append(("<", msg))
                self.client.receive(msg)
        raise RuntimeError("island messages do not settle")

    def pump(self) -> None:
        """One pass of the message loop (``Application.ProcessMessages``)."""
        self._deliver()
        self.client.timer3()
        self._deliver()

    def wait(self) -> None:
        """``TPsiClient.Wait``: run the message loop until the world's ``OK`` arrives."""
        self.client.waiting_ok = False
        for _ in range(MAX_ROUNDS):
            self.pump()
            if self.client.waiting_ok:
                return
        raise RuntimeError("no OK from the island (the original gives up after 30 s)")

    # --- requests (TPsiClient) ------------------------------------------------------------------

    def start(self) -> None:
        """``TPsiClient.Start``."""
        self.to_world.append("Start")
        self.wait()

    def aggression(self, x: int, y: int) -> bool:
        """``TPsiClient.Aggression`` (line 746): approach the object at (x, y)."""
        if self.client.object_name != "-":
            return False
        self.to_world.append(f"Aggression {x} {y}")
        self.wait()
        return True

    def regression(self) -> bool:
        """``TPsiClient.Regression`` (line 763): step back from the object."""
        if self.client.object_name == "-":
            return False
        self.to_world.append("Regression")
        self.wait()
        return True

    def move_to_situation(self, direction: str) -> bool:
        """``TPsiClient.MoveToSituationWithDirection`` (line 803)."""
        if self.client.object_name != "-":
            return False
        self.client.success_locomotion = False
        self.to_world.append("MoveToSituationWithDirection " + direction)
        self.to_world.append("Info")
        self.wait()
        return self.client.success_locomotion

    def manipulate(self, action: str, report_success: bool = False) -> bool:
        """``TPsiClient.Manipuliere1`` (line 1505)."""
        if self.client.object_name == "-":
            return False
        self.client.success_manipulation = False
        self.to_world.append("CanManipuliere " + action)
        self.wait()
        return self.client.success_manipulation if report_success else True

    # --- what Psi perceives -----------------------------------------------------------------------

    def act_sit(self) -> np.ndarray:
        return self.client.act_sit()

    @property
    def object_name(self) -> str:
        return self.client.object_name

    @property
    def situation_name(self) -> str:
        return self.client.situation_name

    # --- persistence ----------------------------------------------------------------------------

    def snapshot(self) -> dict:
        """Everything about the island and the client that changes during a life, JSON compatible.

        Static data (situations as read from the files, bitmaps, prior knowledge)
        is not stored; it comes from the reference files when restoring.
        """
        import base64
        c, w = self.client, self.world
        pic = np.ascontiguousarray(c.bm_act_sit, dtype=np.uint32)
        return {
            "world": {"situation": w.situation, "x": w.x, "y": w.y, "manipulating": w.manipulating, "id": w.id,
                      "objects": {s.name: list(s.objects) for s in self.reality.situations}},
            "client": {"object_name": c.object_name, "position": c.position, "situation_name": c.situation_name,
                       "situations_can_move": list(c.situations_can_move), "behaviour": list(c.behaviour),
                       "info_text": c.info_text, "change_objects": list(c.change_objects),
                       "part_list": [list(p) for p in c.part_list.items],
                       "tmp_part_list": [list(p) for p in c.tmp_part_list],
                       "bm_act_sit": {"shape": list(pic.shape), "data": base64.b64encode(pic.tobytes()).decode()},
                       "waiting_ok": c.waiting_ok, "success_manipulation": c.success_manipulation,
                       "success_locomotion": c.success_locomotion},
            "to_world": list(self.to_world), "to_client": list(self.to_client),
        }

    def restore_from(self, data: dict) -> None:
        """Apply a :meth:`snapshot` to a freshly built body (same reference files and variant)."""
        import base64
        w, c = self.world, self.client
        dw, dc = data["world"], data["client"]
        w.situation, w.x, w.y, w.manipulating, w.id = dw["situation"], dw["x"], dw["y"], dw["manipulating"], dw["id"]
        for s in self.reality.situations:
            s.objects = list(dw["objects"][s.name])
        c.object_name, c.position, c.situation_name = dc["object_name"], dc["position"], dc["situation_name"]
        c.situations_can_move, c.behaviour = list(dc["situations_can_move"]), list(dc["behaviour"])
        c.info_text, c.change_objects = dc["info_text"], list(dc["change_objects"])
        c.part_list.items = [tuple(p) for p in dc["part_list"]]
        c.tmp_part_list = [tuple(p) for p in dc["tmp_part_list"]]
        pic = dc["bm_act_sit"]
        c.bm_act_sit = np.frombuffer(base64.b64decode(pic["data"]), dtype=np.uint32).reshape(pic["shape"]).copy()
        c.waiting_ok, c.success_manipulation = dc["waiting_ok"], dc["success_manipulation"]
        c.success_locomotion = dc["success_locomotion"]
        self.to_world[:] = data["to_world"]
        self.to_client[:] = data["to_client"]
