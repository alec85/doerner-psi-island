"""Names of new neurons (``NextName``, UStrukturen.Pas line 857).

Psi names the neurons it creates while living: a kind letter followed by a
counter of three letters, e.g. ``Paaa``, ``Paab`` for protocol elements. The
counter is kept per letter („lastname[...]“). Sensory protocol elements of
deeper layers count under the letters after ``S``: layer 1 under ``S``, layer
2 under ``T``, layer 3 under ``U`` (and 4 under ``V``), and these counters
start at different offsets (``daa``, ``gaa``, ``maa``, set in ``InitPsi``,
line 2826), so the layer of an ``S`` neuron can be read from its name.
"""

from __future__ import annotations

from typing import Any

DIGITS = 3
"""Number of counter letters („NStellen“, set to 3 in ``InitPsi``)."""

LETTERS = "PQRSTUV"
"""Index range of ``lastname`` (``array['P'..'V'] of string``)."""

INITIAL = {"T": "daa", "U": "gaa", "V": "maa"}


class NameGenerator:
    """Per-letter name counters (global ``lastname`` of the original)."""

    def __init__(self) -> None:
        self.last: dict[str, str] = {c: INITIAL.get(c, "") for c in LETTERS}

    def next_name(self, kind: str, layer: int) -> str:
        """Return the next counter for ``kind`` (``NextName``).

        The caller prefixes the kind letter (``GenProtEl``). If the counter is
        exhausted (``zzz``) the original returns it unchanged; so does this.
        """
        key = chr(ord("S") + layer - 1) if kind == "S" else kind
        if key not in self.last:
            # The original is compiled with range checks ($R+ in Psi.cfg).
            raise IndexError(f"lastname[{key!r}] is out of range 'P'..'V'")
        current = self.last[key]
        if current == "":
            current = "a" * DIGITS
        else:
            chars = list(current)
            j = DIGITS - 1
            while j >= 0:
                if chars[j] == "z":
                    j -= 1
                else:
                    chars[j] = chr(ord(chars[j]) + 1)
                    for k in range(j + 1, DIGITS):
                        chars[k] = "a"
                    break
            current = "".join(chars)
        self.last[key] = current
        return current

    def snapshot(self) -> dict[str, Any]:
        return dict(self.last)

    @classmethod
    def restore(cls, data: dict[str, Any]) -> "NameGenerator":
        gen = cls()
        gen.last = dict(data)
        return gen
