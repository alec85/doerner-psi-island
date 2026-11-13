"""Perception: Psi scans a picture for black lines and recognises schemas (``UPercept.Pas``; ADR 0012).

Port of ``Percept`` and its helpers. Line numbers refer to
``reference/delphi-original/PsiCode/UPercept.Pas``.

How the original perceives. Starting in the middle of the picture, Psi scans
in a square spiral. At the first black pixel not yet part of a known line it
follows the line pattern: it picks the longest straight line through the
point (horizontal, vertical, diagonal or antidiagonal, the four line sensors
``Hor2``, ``Ver2``, ``Dia2``, ``Adi2``), tries to recognise it as part of a
known schema („HyPercept“, hypothesis-driven perception), and otherwise
records it as a new line. Connection points to further lines („Anschluss“)
are followed until the pattern is exhausted. Each pattern becomes an object
schema in protocol layer 2, the sequence of objects a situation schema in
layer 1 (``ProtocolMemory`` layers, ``kzg[1..3]``).

Faithfulness notes:

* Pixel tests outside the picture return a non-black colour, as GDI does.
* ``TXYList`` is a sorted ``TStringList`` of ``'%3u %3u'`` strings; its order
  and lookups are reproduced with those strings.
* Angle comparisons use the x87-exact geometry (:mod:`geometry`).
* Perception assigns the global ``Objekt`` while trying hypotheses and
  leaves it ``nil`` (``state.objekt = None``) whenever it recognised
  anything; callers in the original rely on that.
* ``DisposeNeuron`` removes one-part schemas, as in the original.
"""

from __future__ import annotations

from bisect import bisect_left, insort
from dataclasses import dataclass
from enum import IntEnum
from fractions import Fraction
from typing import TYPE_CHECKING

import numpy as np

from psi_gw.memory.lists import NilDereference, Spat, SynapseList
from psi_gw.memory.network import Axon, MemoryNetwork, Neuron
from psi_gw.perception.geometry import PI_EXT, distanz, real_const, winkel, winkel_differenz

if TYPE_CHECKING:
    from psi_gw.state import PsiState

CL_BLACK = 0


class Sen2(IntEnum):
    """Line sensors („2er-Strukturelemente“, ``TSen2El``)."""

    NO_SEN = 0
    VER2 = 1
    HOR2 = 2
    DIA2 = 3
    ADI2 = 4


SENSOR_NAMES = {Sen2.VER2: "Ver2", Sen2.HOR2: "Hor2", Sen2.DIA2: "Dia2", Sen2.ADI2: "Adi2"}
"""``PattId2``: names of the sensor neurons."""

STEP = {Sen2.HOR2: (1, 0), Sen2.VER2: (0, 1), Sen2.DIA2: (1, -1), Sen2.ADI2: (1, 1)}

_CONTINUE = {
    Sen2.HOR2: (real_const(Fraction(0)), real_const(PI_EXT)),
    Sen2.VER2: (real_const(PI_EXT / 2), real_const(Fraction(3, 2) * PI_EXT)),
    Sen2.DIA2: (real_const(Fraction(1, 4) * PI_EXT), real_const(Fraction(5, 4) * PI_EXT)),
    Sen2.ADI2: (real_const(Fraction(3, 4) * PI_EXT), real_const(Fraction(7, 4) * PI_EXT)),
}
"""``NextCont``: preferred directions to continue a line and the opposite ones (as reals)."""


def id_patt2(name: str) -> Sen2:
    """``IdPatt2`` (UStrukturen 576): sensor type from the first letter of a name."""
    return {"H": Sen2.HOR2, "V": Sen2.VER2, "D": Sen2.DIA2, "A": Sen2.ADI2}.get(name[:1], Sen2.NO_SEN)


class XYList:
    """``TXYList`` (UStrukturen 412): sorted string list of points, duplicates ignored."""

    __slots__ = ("_keys",)

    def __init__(self) -> None:
        self._keys: list[str] = []

    def __len__(self) -> int:
        return len(self._keys)

    def add_xy(self, x: int, y: int) -> None:
        key = f"{x & 0xFFFFFFFF:3d} {y & 0xFFFFFFFF:3d}"  # Format('%3u')
        i = bisect_left(self._keys, key)
        if i == len(self._keys) or self._keys[i] != key:
            self._keys.insert(i, key)

    def find_xy(self, x: int, y: int) -> tuple[bool, int]:
        """``FindXY``: found and index (insertion point if not found)."""
        key = f"{x:3d} {y:3d}"
        i = bisect_left(self._keys, key)
        return (i < len(self._keys) and self._keys[i] == key), i

    def __getitem__(self, i: int) -> tuple[int, int]:
        s = self._keys[i]
        return int(s[0:3]), int(s[4:7])

    def delete(self, i: int) -> None:
        del self._keys[i]


@dataclass
class Line:
    """``TLinie``: a straight line from ``pl`` (left or top) to ``pr`` (right or bottom)."""

    pl: tuple[int, int]
    pr: tuple[int, int]
    kind: Sen2
    length: float


def spat_add(a: Spat, b: Spat) -> Spat:
    """``SpaTAdd``: adds x and y only."""
    return Spat(a.x + b.x, a.y + b.y, 0, 0)


class Perception:
    """``Percept`` with the state it reads and writes."""

    def __init__(self, state: "PsiState", picture: np.ndarray) -> None:
        self.state = state
        self.net: MemoryNetwork = state.net
        self.img = picture
        self.h, self.w = picture.shape

    # --- pixels ------------------------------------------------------------------------------

    def black(self, x: int, y: int) -> bool:
        return 0 <= x < self.w and 0 <= y < self.h and int(self.img[y, x]) == CL_BLACK

    def lift(self, inc: float) -> None:
        self.state.clock.advance(inc)

    # --- line helpers ------------------------------------------------------------------------

    def find_side_conts(self, sensor: Sen2, loc: tuple[int, int]) -> list[tuple[int, int]]:
        """``FindSideConts`` (line 61): black neighbours beside a line point."""
        xi, yi = loc
        out = []
        if sensor is Sen2.HOR2:
            cand = [(xi, yi - 1), (xi, yi + 1)]
        elif sensor is Sen2.VER2:
            cand = [(xi - 1, yi), (xi + 1, yi)]
        elif sensor is Sen2.DIA2:
            cand = [(xi - 1, yi - 1), (xi - 1, yi), (xi, yi + 1), (xi + 1, yi + 1)]
        elif sensor is Sen2.ADI2:
            cand = [(xi - 1, yi), (xi - 1, yi + 1), (xi, yi - 1), (xi + 1, yi - 1)]
        else:
            cand = []
        for p in cand:
            if self.black(*p):
                out.append(p)
        return out

    def add_line_points(self, line: Line, pattern: XYList, conns: XYList) -> None:
        """``AddLinePointsTo`` (line 100): put a line into the pattern, update connection points."""
        s2 = line.kind
        x, y = STEP.get(s2, (0, 0))
        xi, yi = line.pl
        xo, yo = line.pr
        ends: list[tuple[int, int]] = []
        if s2 is Sen2.HOR2:
            for i in range(yi - 1, yi + 2):
                if self.black(xi - 1, i):
                    ends.append((xi - 1, i))
                if self.black(xo + 1, i):
                    ends.append((xo + 1, i))
        elif s2 is Sen2.VER2:
            for i in range(xi - 1, xi + 2):
                if self.black(i, yi - 1):
                    ends.append((i, yi - 1))
                if self.black(i, yo + 1):
                    ends.append((i, yo + 1))
        elif s2 is Sen2.DIA2:
            if self.black(xi - 1, yi + 1):
                ends.append((xi - 1, yi + 1))
            for i in range(xo, xo + 2):
                if self.black(i, yo - 1):
                    ends.append((i, yo - 1))
            if self.black(xo + 1, yo):
                ends.append((xo + 1, yo))
        elif s2 is Sen2.ADI2:
            if self.black(xi - 1, yi - 1):
                ends.append((xi - 1, yi - 1))
            for i in range(yo, yo + 2):
                if self.black(xo + 1, i):
                    ends.append((xo + 1, i))
            if self.black(xo, yo + 1):
                ends.append((xo, yo + 1))
        # Contins is itself a sorted TXYList: duplicates vanish, order is sorted
        tmp = XYList()
        for p in ends:
            tmp.add_xy(*p)
        for k in range(len(tmp)):
            p = tmp[k]
            if not pattern.find_xy(*p)[0]:
                conns.add_xy(*p)
        while True:
            pattern.add_xy(xi, yi)
            found, index = conns.find_xy(xi, yi)
            if found:
                conns.delete(index)
            side = XYList()
            for p in self.find_side_conts(s2, (xi, yi)):
                side.add_xy(*p)
            for k in range(len(side)):
                p = side[k]
                if not pattern.find_xy(*p)[0]:
                    conns.add_xy(*p)
            xi += x
            yi += y
            if xi > xo or (s2 is Sen2.VER2 and yi > yo):
                break

    def contingencies(self, p: tuple[int, int]) -> XYList:
        """``Contingencies`` (line 201): black neighbours of a point, without opposite pairs."""
        result = XYList()
        px, py = p
        for xi in range(px - 1, px + 2):
            for yi in range(py - 1, py + 2):
                if (xi, yi) == p or not self.black(xi, yi):
                    continue
                xj = px - 1 if xi > px else (px + 1 if xi < px else xi)
                yj = py - 1 if yi > py else (py + 1 if yi < py else yi)
                if not result.find_xy(xj, yj)[0]:
                    result.add_xy(xi, yi)
        return result

    @staticmethod
    def next_cont(last: Line, conts: XYList) -> int:
        """``NextCont`` (line 239): index of the connection point to follow next."""
        cont, anti = _CONTINUE.get(last.kind, (0.0, 0.0))
        ii = 0
        min_wi = 8.0
        min_di = 100000.0
        for i in range(len(conts)):
            pp = conts[i]
            for pj in (last.pl, last.pr):
                wi = winkel(pj, pp)
                di = distanz(pj, pp)
                if winkel_differenz(wi, cont) <= min_wi or winkel_differenz(wi, anti) <= min_wi:
                    if di <= min_di:
                        ii = i
                        min_wi = wi  # sic: the original stores the angle, not the difference
                        min_di = di
        return ii

    @staticmethod
    def sensor(p1: tuple[int, int], p2: tuple[int, int]) -> tuple[Sen2, tuple[int, int], tuple[int, int]]:
        """``Sensor`` (line 297): line type of two neighbours, ordered left/top first."""
        if p1[0] == p2[0]:
            pi, pj = (p1, p2) if p1[1] < p2[1] else (p2, p1)
        else:
            pi, pj = (p2, p1) if p1[0] > p2[0] else (p1, p2)
        if pi[0] < pj[0]:
            if pi[1] == pj[1]:
                return Sen2.HOR2, pi, pj
            return (Sen2.DIA2 if pi[1] > pj[1] else Sen2.ADI2), pi, pj
        return Sen2.VER2, pi, pj

    def get_line(self, sensor: Sen2, loc: tuple[int, int]) -> Line:
        """``GetLine`` (line 336): the longest black line of a type through ``loc``."""
        x, y = STEP.get(sensor, (0, 0))
        pp = []
        for _ in range(2):
            xi, yi = loc
            while self.black(xi, yi):
                xi += x
                yi += y
            pp.append((xi - x, yi - y))
            x, y = -x, -y
        return Line(pp[1], pp[0], sensor, distanz(pp[0], pp[1]))

    # --- schemas ------------------------------------------------------------------------------

    def line_detector(self, neuron: Neuron) -> bool:
        """``LineDetector`` (UStrukturen 815): the schema element's first part is a sensor."""
        sub = neuron.axon[Axon.SUB].first
        return sub is not None and self.state.sen2.find(sub.target) is not None

    @staticmethod
    def count_parts(head: Neuron) -> int:
        """``CountParts`` (line 388): length of the ``por`` chain."""
        n, cur, por = 0, head, Axon.POR
        while cur is not None:
            n += 1
            items = cur.axon[por]._items  # hot path: list access without the property
            cur = items[0].target if items else None
        return n

    def head(self, neuron: Neuron) -> tuple[Neuron, Spat]:
        return self.net.head(neuron)

    def trace_schema_lines(self, head: Neuron, dort: Spat, pattern: XYList, conns: XYList) -> None:
        """``TraceSchemaLines`` (line 404): mark the lines of a recognised schema as seen."""
        akt: Neuron | None = head
        locus = dort
        while akt is not None:
            if self._add_schema_lines(akt, locus, pattern, conns):
                return
            por = akt.axon[Axon.POR].first
            if por is None:
                return
            akt = por.target
            self.lift(0.01)
            locus = spat_add(locus, por.spat)

    def _add_schema_lines(self, schema: Neuron, locus: Spat, pattern: XYList, conns: XYList) -> bool:
        sub = schema.axon[Axon.SUB].first
        if sub is None:
            raise NilDereference(f"AddSchemaLines: {schema!r} has no sub link")
        sensor = sub.target
        if self.state.sen2.find(sensor) is not None:
            por = schema.axon[Axon.POR].first
            if por is None:
                raise NilDereference(f"AddSchemaLines: line schema {schema!r} without por")
            kind = id_patt2(sensor.name)
            x, y = STEP.get(kind, (0, 0))
            line = Line((locus.x, locus.y), (locus.x + por.spat.x + x, locus.y + por.spat.y + y), kind, 0.0)
            self.add_line_points(line, pattern, conns)
            return True
        self.trace_schema_lines(sub.target, locus, pattern, conns)
        return False

    def check_schema(self, head: Neuron, dort: Spat, skip: Neuron | None, skip_spat: Spat) -> bool:
        """``CheckSchema`` (line 482): is the schema present at ``dort``?"""
        akt = head
        locus = dort
        while True:
            if not self._ist_da(akt, locus, skip, skip_spat, dort):
                return False
            por = akt.axon[Axon.POR].first
            if not self.line_detector(akt) and por is not None:
                akt = por.target
                self.lift(0.1)
                locus = spat_add(locus, por.spat)
            else:
                return True

    def _ist_da(self, sensor: Neuron, locus: Spat, skip: Neuron | None, skip_spat: Spat, dort: Spat) -> bool:
        """``IstDa`` (line 490), nested in ``CheckSchema``."""
        if self.line_detector(sensor):
            hubel_wiesel = sensor.axon[Axon.SUB].first.target  # type: ignore[union-attr]
            por = sensor.axon[Axon.POR].first
            if por is None:
                raise NilDereference(f"IstDa: line schema {sensor!r} without por")
            end = por.spat
            s2 = id_patt2(hubel_wiesel.name)
            xi, yi = STEP.get(s2, (0, 0))
            pa = (locus.x, locus.y)
            px, py = pa
            pe = (px + end.x, py + end.y)
            while True:
                self.lift(0.01)
                e = self.black(px, py)
                px += xi
                py += yi
                if not e or px > pe[0] + xi or (s2 is Sen2.VER2 and py > pe[1] + yi):
                    break
            e = e and not self.black(pa[0] - xi, pa[1] - yi) and not self.black(pe[0] + 2 * xi, pe[1] + 2 * yi)
            return e
        result = False
        for si in list(sensor.axon[Axon.SUB]):
            if result:
                break
            check = si.target
            self.lift(0.01)
            if skip is not None and skip is check and locus.x == skip_spat.x and locus.y == skip_spat.y:
                result = True
            else:
                result = self.check_schema(check, locus, sensor, dort)
        return result

    def hy_percept(self, sensor: Neuron, dort: Spat, locked: Neuron | None) -> tuple[Neuron | None, Spat]:
        """``HyPercept`` (line 588): find a known schema the element at ``dort`` belongs to.

        Returns the schema's head (or ``None``) and its location (``OutputSpat``,
        unchanged input if no candidate was tried).
        """
        output = dort
        head, hier = self.head(sensor)
        main_loc = spat_add(dort, hier)
        sur = head.axon[Axon.SUR].copy_targets()
        self.lift(0.1)
        found = False
        akt: Neuron | None = None
        while sur and not found:
            akt = sur.first.target  # type: ignore[union-attr]
            self.lift(0.1)
            sur.remove(akt)
            akt, hier = self.head(akt)
            if akt.name[:1] != "P" and akt is not locked:
                if self.count_parts(akt) > 1:
                    locus = spat_add(main_loc, hier)
                    output = locus
                    self.lift(0.1)
                    found = self.check_schema(akt, locus, sensor, dort)
                else:
                    found = False
        return (akt if found else None), output

    def schema_gravity(self, head: Neuron) -> tuple[int, int]:
        """``SchemaGravity`` (UStrukturen 1675): mean position of the schema's parts."""
        akt: Neuron | None = head
        rx = ry = 0
        px = py = 0
        n = 1
        while akt is not None:
            por = akt.axon[Axon.POR].first
            if por is None:
                break
            n += 1
            px += por.spat.x
            py += por.spat.y
            rx += px
            ry += py
            akt = por.target
        return round(Fraction(rx, n)), round(Fraction(ry, n))

    # --- Percept ------------------------------------------------------------------------------------

    def run(self, rect: tuple[int, int, int, int], zoom: bool) -> tuple[Neuron, tuple[int, int] | None]:
        """``Percept`` (line 694). Returns the perceived schema and the new ``LocSit`` (or ``None``)."""
        st = self.state
        pm = st.protocol
        pf = st.params.memory.protocol_factor
        body = st.body
        st.prn.writeln("  -? PERCEPTION: Was ist der Fall?")
        pattern = XYList()
        akt_schema_head: Neuron | None = None
        pm.new_protocol(1)
        last1 = (0, 0)
        last2 = (0, 0)
        loc_sit: tuple[int, int] | None = None
        first_prot = True
        start_age = st.clock.age
        left, top, right, bottom = rect
        start = (round(Fraction(right - left, 2)), round(Fraction(bottom - top, 2)))
        acorner = list(start)
        ocorner = list(start)
        n, dist, along_x, sign, n_tast = 1, 1, False, 1, 0
        through = False
        spat = Spat()
        maxline: Line | None = None
        while not through:
            along_x = not along_x
            if along_x:
                ocorner[0] = acorner[0] + n * sign * dist
            else:
                ocorner[1] = acorner[1] + n * sign * dist
                sign = -sign
                n += 1
            xa, xo = sorted((ocorner[0], acorner[0]))
            ya, yo = sorted((ocorner[1], acorner[1]))
            acorner = list(ocorner)
            if (along_x and top <= ya <= bottom) or (not along_x and left <= xa <= right):
                tast, n_tast = True, 0
            else:
                tast = False
                n_tast += 1
                through = n_tast == 4
            if not tast:
                continue
            for xi in range(xa, xo + 1):
                for yi in range(ya, yo + 1):
                    if not (self.black(xi, yi) and not pattern.find_xy(xi, yi)[0]):
                        continue
                    aktp = (xi, yi)
                    points = self.contingencies(aktp)
                    self.lift(0.01)
                    if len(points) == 0:
                        continue
                    anfang = True
                    conns = XYList()
                    pm.new_protocol(2)
                    last2 = (0, 0)
                    while anfang or len(conns) > 0:
                        if not anfang:
                            index = self.next_cont(maxline, conns)  # type: ignore[arg-type]
                            aktp = conns[index]
                            conns.delete(index)
                        points = self.contingencies(aktp)
                        best = 0.0
                        for k in range(len(points)):
                            kind, pl, pr = self.sensor(aktp, points[k])
                            line = self.get_line(kind, pl)
                            self.lift(0.01)
                            if line.length > best:
                                best = line.length
                                maxline = line
                        detected = False
                        assert maxline is not None
                        spat = Spat(maxline.pl[0], maxline.pl[1], spat.z, spat.t)
                        sen_schem = st.sensor2[maxline.kind]
                        while True:
                            obj, obj_spat = self.hy_percept(sen_schem, spat, akt_schema_head)
                            st.objekt = obj  # the original assigns the global Objekt here
                            if obj is None:
                                break
                            detected = True
                            sen_schem = obj
                            spat = obj_spat
                        if not detected:
                            self.add_line_points(maxline, pattern, conns)
                            sx = maxline.pr[0] - maxline.pl[0]
                            if sx > 0:
                                sx -= 1
                            sy = maxline.pr[1] - maxline.pl[1]
                            if sy > 0:
                                sy -= 1
                            if sy < 0:
                                sy += 1
                            spat = Spat(sx, sy, spat.z, spat.t)
                            sensel = maxline.kind
                            pm.new_protocol(3)
                            pm.protocol(3, st.sensor2[sensel], "S", pf, spat)
                            pm.protocol(3, st.sensor2[sensel], "S", pf, spat)
                            loc_objekt = maxline.pl
                            prot_objekt, spat = self.head(pm.head(3))  # type: ignore[arg-type]
                        else:
                            loc_objekt = (spat.x, spat.y)
                            prot_objekt = sen_schem
                            self.trace_schema_lines(sen_schem, spat, pattern, conns)
                        lin = Spat(loc_objekt[0] - last2[0], loc_objekt[1] - last2[1])
                        pm.protocol(2, prot_objekt, "S", pf, lin)
                        last2 = loc_objekt
                        if anfang:
                            akt_schema_head = pm.head(2)
                            anfang = False
                    head2 = pm.head(2)
                    if head2 is None:
                        raise NilDereference("Percept: kzg[2] empty")
                    prot_objekt, spat = self.head(head2)
                    spat = spat_add(spat, Spat(last2[0], last2[1]))
                    loc_objekt = (spat.x, spat.y)
                    if self.count_parts(prot_objekt) == 1:
                        sub = prot_objekt.axon[Axon.SUB].first.target  # type: ignore[union-attr]
                        self.net.dispose_neuron(prot_objekt)
                        prot_objekt = sub
                        st.prn.writeln(f"      2-: Wiedererkannt: {prot_objekt.name} "
                                      f"{body.client.get_part_name(prot_objekt.name)}"
                                      f"[{loc_objekt[0]:4d}{loc_objekt[1]:5d}]")
                    else:
                        gx, gy = self.schema_gravity(prot_objekt)
                        if zoom:
                            gx, gy = st.loc_ob[0] + gx, st.loc_ob[1] + gy
                        else:
                            gx, gy = loc_objekt[0] + gx, loc_objekt[1] + gy
                        if body.object_name == "-":
                            part = body.client.find_in_part_list((gx - 3, gy - 3, gx + 3, gy + 3))
                        else:
                            part = body.object_name
                        body.client.part_list.new_name(part, prot_objekt.name)
                        st.prn.writeln(f"      2-: Neues Objekt:  {prot_objekt.name} "
                                      f"{body.client.get_part_name(prot_objekt.name)}"
                                      f"[{loc_objekt[0]:4d}{loc_objekt[1]:5d}]")
                    lin = Spat(loc_objekt[0] - last1[0], loc_objekt[1] - last1[1])
                    pm.protocol(1, prot_objekt, "S", pf, lin)
                    last1 = loc_objekt
                    if first_prot:
                        first_prot = False
                        loc_sit = loc_objekt
        head1 = pm.head(1)
        if head1 is None:
            raise NilDereference("Percept: nothing perceived, kzg[1] empty")
        prot_objekt, spat = self.head(head1)
        spat = spat_add(spat, Spat(last2[0], last2[1]))
        loc = (spat.x, spat.y)
        if self.count_parts(prot_objekt) == 1:
            sub = prot_objekt.axon[Axon.SUB].first.target  # type: ignore[union-attr]
            self.net.dispose_neuron(prot_objekt)
            prot_objekt = sub
            st.prn.writeln(f"     1-: Wiedererkannt: {prot_objekt.name} "
                          f"{body.client.get_part_name(prot_objekt.name)}[{loc[0]:4d}{loc[1]:5d}]")
        elif not zoom:
            body.client.part_list.new_name(body.situation_name, prot_objekt.name)
            st.prn.writeln(f"     1-: Neue Situation: {body.client.get_part_name(prot_objekt.name)}"
                          f"[{loc[0]:4d}{loc[1]:5d}]")
        st.perception_time = st.clock.age - start_age
        return prot_objekt, loc_sit


def percept(state: "PsiState", rect: tuple[int, int, int, int], zoom: bool) -> tuple[Neuron, tuple[int, int] | None]:
    """Perceive the picture the body currently shows (``Percept``)."""
    return Perception(state, state.body.act_sit()).run(rect, zoom)
