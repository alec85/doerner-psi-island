"""The island world: situations, objects, locomotion and manipulation (``UPsiServer.pas``; ADR 0012).

Port of ``TReality``, ``TSituation`` and the server side of ``TPsi``. The
world answers Psi's requests with the text messages of the original; the
transport between both sides is :class:`psi_gw.body.island.body.IslandBody`.

Line numbers refer to ``reference/delphi-original/PsiCode/UPsiServer.pas``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from psi_gw.body.island.bitmaps import BitmapStore
from psi_gw.body.island.delphi_strings import ansi_compare_text, equal, equal_part, string_list_sort
from psi_gw.body.island.x87 import dbl, ext, format_f
from psi_gw.random_source import RandomSource

ROOT = Path(__file__).resolve().parents[4]
WORLD_DIR = ROOT / "reference" / "delphi-original" / "PsiCode" / "Reality" / "InselIII"

SITE_ACCIDENT = "UPsiServer.SetMotivation#1"
CANVAS = 160
"""Size of the situation picture (``cw``, ``ch`` in ``TReality.GetSituation``)."""
NEAR = 50
"""Size of the cut-out around an object Psi stands at (``cx``, ``cy``)."""

DIRECTIONS = ("N", "NO", "O", "SO", "S", "SW", "W", "NW")


def split_lines(text: str) -> list[str]:
    """``TStrings.SetTextStr``: split at CR LF, CR or LF; a final line break adds no empty line."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def _read_lines(path: Path) -> list[str]:
    """``TStringList.LoadFromFile``."""
    return split_lines(path.read_text(encoding="cp1252"))


def _delete_empty(lines: list[str]) -> list[str]:
    return [line for line in lines if line.strip()]


def _space_split(s: str) -> list[str]:
    """``TStrList.SpaceText := s``: split at blanks, trim, drop empty parts."""
    return [p for p in (x.strip() for x in s.split(" ")) if p]


@dataclass
class Situation:
    """``TSituation``: one place of the island."""

    name: str
    position: str
    horizon: list[str] = field(default_factory=list)
    """Ground colour, sky colour, horizon polygon points (``Horizont``)."""
    objects: list[str] = field(default_factory=list)
    """``"x y Name"`` per object (``Objekte``)."""
    locomotions: list[str] = field(default_factory=list)
    """``"Direction Target Distance N Smooth"`` (``Locomotions``)."""

    def get_object(self, i: int) -> tuple[int, int, str]:
        """``GetObjekt``."""
        p = _space_split(self.objects[i])
        return int(p[0]), int(p[1]), p[2]

    def get_locomotion(self, i: int) -> tuple[str, str]:
        """``GetLocomotion``: direction and target situation."""
        p = _space_split(self.locomotions[i])
        return p[0], p[1]

    def get_distance(self, i: int) -> tuple[float, float, float]:
        """``GetDistanz``: distance, accident probability ``1/N`` (0 if N = 0), smoothness."""
        p = _space_split(self.locomotions[i])
        n = int(p[3])
        return float(p[2]), (1.0 / n if n > 0 else 0.0), float(p[4])

    def find_object(self, x: int, y: int, gravity: Callable[[str], tuple[int, int]]) -> int:
        """``FindObjekt`` (line 637): index of the object whose centre of gravity is nearest to (x, y)."""
        def centre(i: int) -> tuple[int, int]:
            ox, oy, name = self.get_object(i)
            gx, gy = gravity(name)
            return ox + gx, oy + gy
        cx, cy = centre(0)
        best, d1 = 0, math.sqrt((cx - x) ** 2 + (cy - y) ** 2)
        for i in range(1, len(self.objects)):
            cx, cy = centre(i)
            d2 = math.sqrt((cx - x) ** 2 + (cy - y) ** 2)
            if d2 < d1:
                best, d1 = i, d2
        return best


class Reality:
    """``TReality``: the island as read from its files (``ReadFiles``, line 506)."""

    def __init__(self, directory: Path = WORLD_DIR, bitmaps: BitmapStore | None = None) -> None:
        self.bitmaps = bitmaps if bitmaps is not None else BitmapStore()
        self.situations: list[Situation] = []
        lines = [line.strip() for line in _read_lines(directory / "Situationen.dat")]
        i = 0

        def eof() -> bool:
            return i > len(lines) - 1

        def eoln() -> bool:
            return eof() or len(lines[i]) == 0

        def gln() -> None:
            nonlocal i
            while not eof() and eoln():
                i += 1

        def gs() -> str:
            nonlocal i
            s = lines[i]
            i += 1
            return s

        while not eof():
            gln()
            name = gs().strip()
            sit = Situation(name, gs())
            gln()
            while not eoln():
                sit.horizon.append(gs())
            gln()
            while not eoln():
                sit.objects.append(gs())
            gln()
            while not eoln():
                loc = gs()
                d, _, rest = loc.partition(" ")
                if d.strip() not in DIRECTIONS or not rest.strip():
                    raise ValueError(f"bad locomotion {loc!r} in {name}")
                sit.locomotions.append(d.strip() + " " + rest.strip())
            gln()
            self.situations.append(sit)
        self.manipulations = string_list_sort(_delete_empty(_read_lines(directory / "Manipulation.Dat")))
        self.actions = string_list_sort(_delete_empty(_read_lines(directory / "Aktionen.Dat")))
        self.behaviour = _delete_empty(_read_lines(directory / "Behaviour.Dat"))

    def index_of(self, name: str) -> int:
        """``Situationen.IndexOf`` (unsorted list, ``AnsiCompareText``)."""
        return next((k for k, s in enumerate(self.situations) if ansi_compare_text(s.name, name) == 0), -1)

    def get_sit(self, name: str) -> Situation:
        """``GetSit`` (line 300); unknown names give the first situation."""
        k = self.index_of(name)
        return self.situations[k if k > -1 else 0]

    def get_manipulation(self, i: int) -> tuple[str, str, str, str]:
        """``GetManipulation``: kind, object before, object after, sound."""
        p = _space_split(self.manipulations[i])
        return p[0], p[1], p[2], (p[3] if len(p) > 3 else "-")

    def find_action(self, name: str) -> tuple[str, int] | None:
        """``FindAktion`` (line 256): delayed change of an object, as (goal, dt)."""
        for line in self.actions:
            p = _space_split(line)
            if equal(p[0], name):
                return p[1], int(p[2])
        return None

    def manipulation_kinds(self) -> list[str]:
        """``ListeDerManipulationen`` (line 360): kinds in order of first occurrence."""
        kinds: list[str] = []
        for i in range(len(self.manipulations)):
            kind = self.get_manipulation(i)[0]
            if not any(ansi_compare_text(k, kind) == 0 for k in kinds):
                kinds.append(kind)
        return kinds


def _text(lines: list[str]) -> str:
    """``TStringList.Text``: every line followed by CR LF."""
    return "".join(line + "\r\n" for line in lines)


class WorldPsi:
    """Server side of one Psi (``TPsi`` in ``UPsiServer.pas``): where it is and what it does."""

    def __init__(self, reality: Reality, rng: RandomSource, send: Callable[[str], None]) -> None:
        self.reality = reality
        self.rng = rng
        self.send = send
        self.situation = "Haselwald"
        self.x = -1
        self.y = -1
        self.manipulating = False
        """``bManipuliere``: a manipulation was granted and is being carried out."""
        self.id = 1

    # --- state queries -------------------------------------------------------------------

    def is_near(self) -> bool:
        return self.x != -1 or self.y != -1

    def gravity(self, name: str) -> tuple[int, int]:
        """``GetGravityPoint``. The original asks the client and caches; the value is the bitmap's."""
        return self.reality.bitmaps.gravity_point(name)

    def situation_text(self) -> str:
        """``TReality.GetSituation`` (line 313)."""
        sit = self.reality.get_sit(self.situation)
        lines = [f"{CANVAS} {CANVAS}", "", *sit.horizon, "", *sit.objects, ""]
        if self.is_near():
            x1, y1, name = sit.get_object(sit.find_object(self.x, self.y, self.gravity))
            x1, y1 = max(x1, 1), max(y1, 1)
            if x1 + NEAR > CANVAS - 1:
                x1 = CANVAS - NEAR - 1
            if y1 + NEAR > CANVAS - 1:
                y1 = CANVAS - NEAR - 1
            lines += [f"{x1} {y1} {x1 + NEAR} {y1 + NEAR}", f"{name} {x1 + NEAR // 2} {y1 + NEAR // 2}"]
        else:
            lines += [f"0 0 {CANVAS} {CANVAS}", "-"]
        lines.append("")
        return _text(lines)

    # --- outgoing ------------------------------------------------------------------------

    def situation_changed(self) -> None:
        self.send("SituationChanged\r\n" + self.situation_text())

    def ok(self) -> None:
        self.send("OK")

    def sound(self, name: str) -> None:
        if name not in ("", "-"):
            self.send("Sound " + name)

    def info(self) -> None:
        sit = self.reality.get_sit(self.situation)
        self.send(_text(["Info", self.situation, *sit.locomotions]))

    def umgebung_changed(self, situation: str) -> None:
        """``UmgebungChanged`` (line 786): Psi is now in ``situation``."""
        self.situation = situation
        sit = self.reality.get_sit(situation)
        lines = ["UmgebungChanged", situation, sit.position]
        for i in range(len(sit.locomotions)):
            target = sit.get_locomotion(i)[1]
            lines.append(self.reality.situations[self.reality.index_of(target)].position)
        self.send(_text(lines))

    def set_motivation(self, name: str, value_text: str) -> None:
        self.send(f"SetMotivation {name} {value_text}")

    # --- requests from Psi ----------------------------------------------------------------

    def start(self) -> None:
        self.send(f"SetID {self.id} 1")
        self.send("SetManipulationen\r\n" + _text(self.reality.manipulation_kinds()))
        self.send("SetBehaviour\r\n" + _text(self.reality.behaviour))
        # SetUmgebung only feeds the island map of the display; its text is not reproduced.
        self.send("SetUmgebung\r\n")
        self.umgebung_changed(self.situation)
        self.info()
        self.situation_changed()
        self.ok()

    def aggression(self, ax: int, ay: int) -> None:
        """Approach an object (line 747)."""
        if not self.manipulating and not self.is_near():
            self.x, self.y = ax, ay
            self.situation_changed()

    def regression(self) -> None:
        """Step back from an object (line 758)."""
        if not self.manipulating and self.is_near():
            self.x, self.y = -1, -1
            self.situation_changed()

    def move_to_object(self, ax: int, ay: int) -> None:
        if not self.manipulating:
            if self.is_near():
                self.x, self.y = -1, -1
            else:
                self.x, self.y = ax, ay
            self.situation_changed()

    def can_manipulate(self, kind: str) -> None:
        """``CanManipuliere`` (line 895)."""
        if self.is_near() and not self.manipulating:
            self.manipulating = True
            self.send("DoManipuliere " + kind)
        else:
            self.ok()

    def manipulate(self, kind: str) -> None:
        """``TPsi.Manipuliere`` and ``TReality.Manipuliere`` (lines 810, 403)."""
        self.manipulating = False
        reality = self.reality
        sit = reality.get_sit(self.situation)
        index = sit.find_object(self.x, self.y, self.gravity)
        x1, y1, name = sit.get_object(index)
        for i in range(len(reality.manipulations)):
            art, obj1, obj2, sound = reality.get_manipulation(i)
            if equal(art, kind) and equal(obj1, name):
                self.sound(sound)
                sit.objects[index] = f"{x1} {y1} {obj2}"
                found = reality.find_action(obj2)
                dt = found[1] if found else 0
                parts = _space_split(reality.manipulations[i])
                for n in range(4, len(parts) - 1, 2):
                    self.set_motivation(parts[n], parts[n + 1])
                self.situation_changed()
                if dt > 0:
                    self.send(f"ChangeObject {dt} {index} {self.situation} {obj2} {obj1}")

    def move_to_situation(self, name: str, by_direction: bool) -> None:
        """``TPsi.MoveToSituation`` and ``TReality.MoveToSituation`` (lines 730, 456)."""
        if self.manipulating or self.is_near():
            return
        sit = self.reality.get_sit(self.situation)
        for i in range(len(sit.locomotions)):
            direction, target = sit.get_locomotion(i)
            if (not by_direction and equal(target, name)) or (by_direction and equal(direction, name)):
                self.umgebung_changed(target)
                distance, accident, smooth = sit.get_distance(i)
                # Psi ignores "Moved" (no handler assigned); FloatToStr is approximated.
                self.send(_text(["Moved", repr(distance), repr(accident)]))
                d = dbl(distance)
                for need, value in (
                    ("Hunger", dbl(ext(d * ext("0.0002")))),
                    ("Durst", dbl(ext(d * ext("0.0004")))),
                    ("Schaden", dbl(ext(ext(ext(1 - dbl(smooth)) * d) * ext("0.07")))),
                ):
                    if value > 0:
                        self.set_motivation(need, format_f(value))
                if accident > self.rng.random(site=SITE_ACCIDENT):
                    self.set_motivation("Schaden", format_f(dbl(ext("0.07"))))
                self.situation_changed()
                return

    def change_object(self, situation: str, index: int, to_object: str) -> None:
        """``ReceiveChangeObject`` (line 934): a delayed change becomes due."""
        sit = self.reality.get_sit(situation)
        parts = _space_split(sit.objects[index])
        parts[2] = to_object
        sit.objects[index] = " ".join(parts)
        self.situation_changed()

    # --- message dispatch -----------------------------------------------------------------

    def receive(self, message: str) -> None:
        """One message from Psi (``TPsi.ReceiveText``, line 1072)."""
        p = _space_split(message)
        if equal_part(message, "GetSituation"):
            self.situation_changed()
        elif equal_part(message, "Start"):
            self.start()
        elif equal_part(message, "Aggression"):
            self.aggression(int(p[1]), int(p[2]))
            self.ok()
        elif equal_part(message, "Regression"):
            self.regression()
            self.ok()
        elif equal_part(message, "MoveToObjekt"):
            self.move_to_object(int(p[1]), int(p[2]))
            self.ok()
        elif equal_part(message, "CanManipuliere"):
            self.can_manipulate(p[1])
        elif equal_part(message, "Manipuliere"):
            self.manipulate(p[1])
            self.ok()
        elif equal_part(message, "MoveToSituationWithName"):
            self.move_to_situation(p[1], by_direction=False)
            self.ok()
        elif equal_part(message, "MoveToSituationWithDirection"):
            self.move_to_situation(p[1], by_direction=True)
            self.ok()
        elif equal_part(message, "ChangeObject"):
            self.change_object(p[1], int(p[2]), p[3])
        elif equal_part(message, "Info"):
            self.info()
        elif equal_part(message, "Echo"):
            self.send(message)
        elif equal_part(message, "OK"):
            pass
        else:
            raise ValueError(f"server: unexpected message {message!r}")
