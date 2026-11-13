"""Island world (ADR 0012): world data, messages and a replay of the original's full life."""

import csv
from pathlib import Path

import pytest

from psi_gw.body.island.bitmaps import BitmapStore
from psi_gw.body.island.body import IslandBody
from psi_gw.body.island.world import Reality
from psi_gw.body.island.x87 import dbl, ext, format_f

ROOT = Path(__file__).resolve().parents[1]
FULL_LIFE = ROOT / "traces" / "original-runs" / "2026-11-10-volles-leben" / "raw" / "seed16" / "Protokoll(1).Dat"


def test_world_files():
    r = Reality()
    assert len(r.situations) == 101 and r.situations[0].name == "Nordkap"
    assert r.manipulation_kinds() == ["Blubb", "Hämmern", "Kuessen", "Nehmen", "Pusten", "Säen", "Saugen",
                                      "Schütteln", "Sieben", "Zuenden"]
    assert r.get_sit("HASELWALD").name == "Haselwald" and r.get_sit("nirgends") is r.situations[0]


def test_gravity_points_and_umlaut_file_names():
    s = BitmapStore()
    assert s.gravity_point("Hasel") == (25, 29)
    assert "Bergdurchhämmern1" in s and s.get("Bergdurchhämmern1").bitmap.width == 50


@pytest.mark.parametrize("value,text", [
    (dbl(ext(dbl(75) * ext("0.0002"))), "0.01"),                               # Hunger, 75 units
    (dbl(ext(ext(ext(1 - dbl("0.9")) * dbl(155)) * ext("0.07"))), "1.08"),     # Schaden, 155 units
    (dbl(ext(ext(ext(1 - dbl("0.7")) * dbl(45)) * ext("0.07"))), "0.95"),
    (dbl(ext(ext(ext(1 - dbl("0.9")) * dbl(35)) * ext("0.07"))), "0.24"),
    (dbl(ext(ext(ext(1 - dbl("0.9")) * dbl(45)) * ext("0.07"))), "0.31"),
])
def test_need_effects_formatted_like_the_original(value, text):
    """Boundary cases whose received values are in the event protocol of the full life."""
    assert format_f(value) == text


def test_start_and_first_actions():
    body = IslandBody(rng=None, age=lambda: 0)
    received = []
    body.client.on_motivation = lambda n, v: received.append((n, v))
    body.client.on_manipulations = lambda kinds: received.append(("kinds", len(kinds)))
    body.start()
    assert body.situation_name == "Haselwald" and body.object_name == "-"
    picture = body.act_sit()
    assert picture.shape == (160, 160) and (picture == 0).sum() > 0
    assert body.aggression(129, 133) and body.object_name == "Hasel"
    assert body.act_sit().shape == (50, 50)
    assert body.manipulate("Nehmen") and body.object_name == "Hasel-"
    assert received == [("kinds", 10), ("Hunger", -0.3)]
    assert body.client.change_objects and body.regression() and body.object_name == "-"


def _events(path):
    lines = path.read_text(encoding="cp1252").replace("\r", "").split("\n")
    header = next(i for i, line in enumerate(lines) if line.startswith("Nr;"))
    rows = list(csv.reader(lines[header:], delimiter=";"))
    return [dict(zip(rows[0], r)) for r in rows[1:] if len(r) > 5]


class _AccidentSource:
    """Random numbers for accidents: 0.0 where the protocol shows one, else 0.999."""

    def __init__(self):
        self.value = 0.999
        self.draws = 0

    def random(self, site=None):
        self.draws += 1
        return self.value

    def randint(self, n, site=None):
        raise AssertionError("the world draws only Random")


def test_replay_of_the_original_full_life():
    """All actions of the full life with seed 16, in order and at their age: after each one the
    situation, the object and the received need effects equal the original's event protocol.
    Exercises object changes due later (regrowth) and accidents."""
    rows = _events(FULL_LIFE)
    age = [0]
    rng = _AccidentSource()
    body = IslandBody(rng, lambda: age[0])
    effects = []
    body.client.on_motivation = lambda n, v: effects.append((n, v))
    body.client.on_manipulations = lambda kinds: None
    body.start()
    mismatches, actions, i = [], 0, 0
    while i < len(rows):
        r = rows[i]
        age[0] = int(r["Age"])
        if r["Status"] == "0":
            k = i + 1
            expected = []
            while not (rows[k]["Aktion"] == r["Aktion"] and rows[k]["Status"] == "1"):
                if rows[k]["Aktion"] == "Motivation":
                    expected.append((rows[k]["Para1"], float(rows[k]["Para2"])))
                k += 1
            accident = r["Aktion"] == "Locomotion" and expected[-1:] == [("Schaden", 0.07)]
            rng.value = 0.0 if accident else 0.999
            effects.clear()
            body.pump()
            if r["Aktion"] == "Aggression":
                body.aggression(int(r["Para1"]), int(r["Para2"]))
            elif r["Aktion"] == "Manipuliere":
                body.manipulate(r["Para1"])
            elif r["Aktion"] == "Locomotion":
                body.move_to_situation(r["Para1"])
            got = (body.situation_name, "" if body.object_name == "-" else body.object_name)
            if got != (rows[k]["Situation"], rows[k]["Objekt"]) or effects != expected:
                mismatches.append(r["Nr"])
            actions += 1
            i = k + 1
            continue
        if r["Aktion"] == "Regression":
            body.pump()
            body.regression()
            actions += 1
        i += 1
    changes = sum(1 for d, m in body.log if d == ">" and m.startswith("ChangeObject"))
    accidents = sum(1 for d, m in body.log if d == "<" and m == "SetMotivation Schaden 0.07")
    assert not mismatches
    assert actions == 2802 and changes == 58 and accidents == 99
