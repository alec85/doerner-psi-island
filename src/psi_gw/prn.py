"""The original's activity protocol (``prn``, ``actu<seed>.Prt``) as an in-memory text sink.

The original writes this protocol with Pascal ``write`` and ``writeln`` from
everywhere in the cognition. The port keeps the text so that runs can be
compared line by line with the original; the core writes no files (ADR 0010).
"""

from __future__ import annotations


class Prn:
    """Collects lines; ``write`` continues the current line, ``writeln`` ends it."""

    def __init__(self) -> None:
        self.lines: list[str] = []
        self._open = ""

    def write(self, text: str) -> None:
        self._open += text

    def writeln(self, text: str = "") -> None:
        self.lines.append(self._open + text)
        self._open = ""

    def append(self, line: str) -> None:
        self.writeln(line)

    def clear(self) -> None:
        self.lines.clear()
        self._open = ""

    def __eq__(self, other) -> bool:
        return self.lines == other if isinstance(other, list) else NotImplemented

    def __iter__(self):
        return iter(self.lines)
