"""Psi's side of the island connection (``TPsiClient``, ``UPsiClient.pas``; ADR 0012).

The client turns the world's messages into what Psi can perceive and use:
the picture of the current situation, the name of the object Psi stands at,
the list of delayed object changes, and the names of objects (``PartList``),
which the original's cognition uses for some decisions (``GetPartName``).

Display-only parts of the original are not ported: zoom and walking
animations, the island map, sounds. Where they influence the order of events
(``Busy`` while an animation runs), the port completes them at once; the
original's cognition waits for them in ``UAction.Wait`` and does not run in
the meantime.

Line numbers refer to ``reference/delphi-original/PsiCode/UPsiClient.pas``.
"""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from typing import Callable

import numpy as np

from psi_gw.body.island.bitmaps import BitmapStore, draw_mask_and_sprite, fill_polygon
from psi_gw.body.island.delphi_strings import ansi_compare_text, equal, equal_part
from psi_gw.body.island.world import split_lines


def _space_split(s: str) -> list[str]:
    return [p for p in (x.strip() for x in s.split(" ")) if p]


def _first_word(s: str) -> str:
    p = s.find(" ")
    return s[:p].strip() if p >= 0 else ""


def _delete_first_word(s: str) -> str:
    p = s.find(" ")
    return s[p + 1:].strip() if p >= 0 else ""


def _delphi_round(x: Fraction) -> int:
    """``Round`` on an exact value: halves to even."""
    return round(x)


class NameValue:
    """``TNameValue`` (``UStrList.Pas``): pairs ``Name=Value``, looked up by value."""

    def __init__(self) -> None:
        self.items: list[tuple[str, str]] = []

    def new_name(self, name: str, value: str) -> None:
        """``NewName``. Duplicate values are only reported to the debug file in the original."""
        self.items.append((name, value))

    def get_name(self, value: str) -> str:
        """``GetName``: name of the first pair with this value (``AnsiCompareText``)."""
        for n, v in self.items:
            if ansi_compare_text(v, value) == 0:
                return n
        return f"~~~ [{value}]"


VORWISSEN = Path(__file__).resolve().parents[4] / "reference" / "delphi-original" / "PsiCode" / "PsiDaten" / "Vorwissen.Dat"
"""``PsiDaten\\Vorwissen.Dat``: manipulations Psi knows in advance per object."""


def values_lookup(lines: list[str], name: str) -> str:
    """``TStrings.Values[Name]``: value of the first line whose name matches (``AnsiCompareText``)."""
    for line in lines:
        p = line.find("=")
        if p >= 0 and ansi_compare_text(line[:p], name) == 0:
            return line[p + 1:]
    return ""


class IslandClient:
    """World-facing state of ``TPsiClient``."""

    def __init__(self, bitmaps: BitmapStore, send: Callable[[str], None], age: Callable[[], int]) -> None:
        self.bitmaps = bitmaps
        self.send = send
        self.age = age
        self.object_name = "-"
        """``FObjectName``: the object Psi stands at, ``'-'`` if none."""
        self.position = ";"
        self.situation_name = ""
        """``FSituationName``."""
        self.situations_can_move: list[str] = []
        self.behaviour: list[str] = []
        self.info_text = ""
        self.change_objects: list[str] = []
        """``ChangeObjectList``: ``"dueAge Situation Index Object"``."""
        self.part_list = NameValue()
        """``PartList``: names of the world's objects for Psi's neurons."""
        self.tmp_part_list: list[tuple[int, int, str]] = []
        """``TmpPartList``: objects of the current picture with their positions."""
        self.bm_act_sit = np.zeros((0, 0), dtype=np.uint32)
        """``bmActSit``: the picture of the situation Psi perceives."""
        self.waiting_ok = False
        """``bWait``: the world's ``OK`` has arrived."""
        self.success_manipulation = False
        """``bErfolgManipulation``."""
        self.success_locomotion = False
        """``bErfolgLocomotion``."""
        self.on_manipulations: Callable[[list[str]], None] | None = None
        """``FOnManipulationen`` (``TFPsi.OnManipulationen``)."""
        self.on_motivation: Callable[[str, float], None] | None = None
        """``FOnMotivation`` (``TFPsi.OnMotivation``)."""
        self.vorwissen = split_lines(VORWISSEN.read_text(encoding="cp1252"))
        """``Vorwissen``: lines ``Object=Manipulation ...``."""

    # --- pictures ------------------------------------------------------------------------

    def build_act_sit(self, text: str) -> None:
        """``BuildbmActSit`` (line 587): draw the situation and cut out the part Psi sees."""
        lines = split_lines(text)
        if not text:
            return
        i = 0

        def eof() -> bool:
            return i > len(lines) - 1

        def eoln() -> bool:
            return eof() or len(lines[i]) == 0

        def gs() -> str:
            nonlocal i
            s = lines[i]
            i += 1
            return s

        def gpoint() -> tuple[int, int]:
            a, _, b = gs().partition(" ")
            return int(a), int(b)

        def gln() -> None:
            nonlocal i
            while not eof() and eoln():
                i += 1

        w, h = gpoint()
        i += 1  # g
        ground = int(gs())
        sky = int(gs())
        points = []
        while not eoln():
            points.append(gpoint())
        gln()
        canvas = np.zeros((h, w), dtype=np.uint32)
        fill_polygon(canvas, [(0, h - 1), *points, (w - 1, h - 1)], ground)
        fill_polygon(canvas, [(0, 0), *points, (w - 1, 0)], sky)
        self.tmp_part_list = []
        while not eoln():
            p = _space_split(gs())
            x, y, name = int(p[0]), int(p[1]), p[2]
            if name != "-":
                draw_mask_and_sprite(canvas, x, y, self.bitmaps.get(name))
            self.tmp_part_list.append((x, y, name))
        gln()
        r = [int(v) for v in _space_split(gs())]
        s = gs()
        if s != "-":
            p = _space_split(s)
            self.object_name = p[0]
            self.position = f"{int(p[1])};{int(p[2])}"
        else:
            self.object_name = "-"
            self.position = ";"
        left, top, right, bottom = r
        if (right - left, bottom - top) == (w, h):
            self.bm_act_sit = canvas[top:bottom, left:right].copy()
        else:
            # Psi stands at an object; the original stretches the cut-out for
            # the display, but perception then uses the object's own bitmap
            # (act_sit). Kept unstretched here.
            self.bm_act_sit = canvas[top:bottom, left:right].copy()

    def act_sit(self) -> np.ndarray:
        """``ActSit`` (line 1188): the object's bitmap at an object, else the situation picture."""
        if self.object_name != "-":
            return self.bitmaps.get(self.object_name).bitmap.pixels.copy()
        return self.bm_act_sit.copy()

    def find_in_part_list(self, rect: tuple[int, int, int, int]) -> str:
        """``FindInPartList`` (line 1651): name of the object whose centre is nearest to the rectangle's."""
        left, top, right, bottom = rect
        mx, my = left + (right - left) // 2, top + (bottom - top) // 2
        best, d = 0, 0.0
        for k, (x, y, _) in enumerate(self.tmp_part_list):
            dh = ((mx - (x + 25)) ** 2 + (my - (y + 25)) ** 2) ** 0.5
            if k == 0:
                d = dh
            elif dh < d:
                best, d = k, dh
        return self.tmp_part_list[best][2]

    def get_part_name(self, neuron_name: str) -> str:
        """``GetPartName`` in ``UStrukturen``."""
        return self.part_list.get_name(neuron_name)

    def get_vorwissen(self, neuron_name: str) -> list[str]:
        """``GetVorwissen`` (line 1734): manipulations known in advance for the object of a neuron."""
        return _space_split(values_lookup(self.vorwissen, self.get_part_name(neuron_name)))

    def add_list_to_part_list(self, names: list[str]) -> None:
        """``AddListToPartList`` (line 1750): actors are their own part names."""
        for s in names:
            self.part_list.new_name(s, s)

    # --- incoming messages -----------------------------------------------------------------

    def receive(self, message: str) -> None:
        """One message from the world (``ReceiveText``, line 393)."""
        lines = split_lines(message)
        text = "".join(line + "\r\n" for line in lines)
        if equal_part(text, "SituationChanged"):
            self.build_act_sit("".join(line + "\r\n" for line in lines[1:]))
            self.success_manipulation = True
        elif equal_part(text, "ChangeObject"):
            p = _space_split(text.replace("\r\n", " "))
            msec, index, situation, to_object = int(p[1]), int(p[2]), p[3], p[5]
            due = _delphi_round(Fraction(self.age()) + Fraction(msec * 3600000, 2500000))
            self.change_objects.append(f"{due} {situation} {index} {to_object}")
        elif equal_part(text, "SetManipulationen"):
            if self.on_manipulations is not None:
                self.on_manipulations(lines[1:])
        elif equal_part(text, "NewSituation"):
            raise NotImplementedError("NewSituation is never sent by the island world")
        elif equal_part(text, "SetUmgebung"):
            pass  # island map of the display
        elif equal_part(text, "SetMotivation"):
            p = _space_split(text.replace("\r\n", " "))
            if self.on_motivation is not None:
                self.on_motivation(p[1], float(p[2]))
        elif equal_part(text, "UmgebungChanged"):
            self.situation_name = lines[1]
            self.situations_can_move = lines[2:]
            self.success_locomotion = True
        elif equal_part(text, "Sound"):
            pass  # sound is off in the reference runs
        elif equal_part(text, "Info"):
            self.info_text = "".join(line + "\r\n" for line in lines[1:])
        elif equal_part(text, "Echo") or equal_part(text, "SetID"):
            pass
        elif equal_part(text, "SetBehaviour"):
            self.behaviour = lines[1:]
        elif equal_part(text, "DoManipuliere"):
            self.do_manipulate(_space_split(text.replace("\r\n", " "))[1])
        elif equal_part(text, "OK"):
            self.waiting_ok = True
        elif equal_part(text, "Moved"):
            pass  # FOnMoved is not assigned
        else:
            raise ValueError(f"client: unexpected message {message!r}")

    def do_manipulate(self, action: str) -> None:
        """``DoManipuliere`` (line 1156) with its animation (``OnTimer2``) completed at once."""
        if not any(equal(_first_word(b), action) for b in self.behaviour):
            raise ValueError(f"DoManipuliere: no behaviour for {action!r} (the original shows a message box)")
        self.send("Manipuliere " + action)

    def timer3(self) -> None:
        """``OnTimer3`` (line 1259): send delayed object changes that are due."""
        for k in range(len(self.change_objects) - 1, -1, -1):
            p = _space_split(self.change_objects[k])
            if self.age() >= int(p[0]):
                self.send(f"ChangeObject {p[1]} {int(p[2])} {p[3]}")
                del self.change_objects[k]
