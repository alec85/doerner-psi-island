"""Sources of randomness (ADR 0005, ADR 0008).

All randomness in psi_gw flows through an explicitly passed ``RandomSource``.
There is no global random state.

* ``NumpySource``: the default for new experiments.
* ``DelphiRandom``: bit-exact emulation of the Delphi runtime generator used by
  the original (``System.Random``), for exact whole-run comparisons.
* ``ReplaySource``: replays a recorded stream, for procedure test cases.
* ``RecordingSource``: wraps another source and logs every draw with its call
  site, for draw-by-draw comparison with the random trace of the original
  (ADR 0010, docs/zufallsmitschnitt.md).

Every draw method takes an optional keyword ``site``: the label of the call
site in the original, spelled as in ``psi_gw.tracing.delphi_random_sites``
(for example ``"UStrukturen.Decay#1"``). Plain sources ignore it.

Sources that take part in a simulation state provide ``snapshot()`` (a JSON
compatible dict) and a matching ``restore()`` class method, so a run can be
resumed exactly (ADR 0010, persistence).

The Delphi generator was verified against the machine code of
``reference/delphi-runtime/PsiCode/Psi.exe``::

    0x402B88  Random(n):  RandSeed := RandSeed * $08088405 + 1;
                          result := (n * RandSeed) shr 32      (unsigned)
    0x402BA0  Random:     RandSeed := RandSeed * $08088405 + 1;
                          result := RandSeed * 2^-32            (unsigned RandSeed)

Because the real value is exactly ``RandSeed / 2**32``, ``Random(n)`` equals
``floor(Random * n)``, the integer rule of procedure test cases (ADR 0006).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Protocol, Sequence, runtime_checkable

import numpy as np

_MULTIPLIER = 0x08088405
_MASK = 0xFFFFFFFF
_TWO_NEG_32 = 2.0 ** -32


@runtime_checkable
class RandomSource(Protocol):
    """Interface every source of randomness implements."""

    @property
    def draws(self) -> int:
        """Number of values drawn so far."""
        ...

    def random(self, site: str | None = None) -> float:
        """Return a float in [0, 1) (Delphi: ``Random``)."""
        ...

    def randint(self, n: int, site: str | None = None) -> int:
        """Return an int in [0, n) (Delphi: ``Random(n)``); ``randint(0)`` returns 0."""
        ...


class NumpySource:
    """Default source backed by ``numpy.random.Generator``."""

    def __init__(self, seed: int | np.random.Generator) -> None:
        self._gen = seed if isinstance(seed, np.random.Generator) else np.random.default_rng(seed)
        self._draws = 0

    @property
    def draws(self) -> int:
        return self._draws

    def random(self, site: str | None = None) -> float:
        self._draws += 1
        return float(self._gen.random())

    def randint(self, n: int, site: str | None = None) -> int:
        if n < 0:
            raise ValueError("n must be >= 0")
        self._draws += 1
        return int(self._gen.integers(n)) if n > 0 else 0

    def snapshot(self) -> dict[str, Any]:
        return {"type": "numpy", "draws": self._draws, "bit_generator": self._gen.bit_generator.state}

    @classmethod
    def restore(cls, data: dict[str, Any]) -> "NumpySource":
        name = data["bit_generator"]["bit_generator"]
        gen = np.random.Generator(getattr(np.random, name)())
        gen.bit_generator.state = data["bit_generator"]
        src = cls(gen)
        src._draws = data["draws"]
        return src


class DelphiRandom:
    """Bit-exact emulation of Delphi's ``System.Random`` (linear congruential, 32 bit).

    Args:
        rand_seed: Initial ``RandSeed``. The original reads it from the parameter
            file or ``Psi.Ini`` (key ``RandSeed``) and never calls ``Randomize``.
    """

    def __init__(self, rand_seed: int) -> None:
        self._state = rand_seed & _MASK
        self._draws = 0

    @property
    def draws(self) -> int:
        return self._draws

    @property
    def rand_seed(self) -> int:
        """Current ``RandSeed`` as Delphi's signed 32-bit ``Longint``."""
        return self._state - (1 << 32) if self._state & 0x80000000 else self._state

    def _next(self) -> int:
        self._state = (self._state * _MULTIPLIER + 1) & _MASK
        self._draws += 1
        return self._state

    @property
    def state(self) -> int:
        """Current ``RandSeed`` as unsigned 32-bit value (column ``randseed`` of the trace)."""
        return self._state

    def random(self, site: str | None = None) -> float:
        return self._next() * _TWO_NEG_32

    def randint(self, n: int, site: str | None = None) -> int:
        if n < 0:
            raise ValueError("n must be >= 0")
        return (n * self._next()) >> 32

    def snapshot(self) -> dict[str, Any]:
        return {"type": "delphi", "draws": self._draws, "randseed": self._state}

    @classmethod
    def restore(cls, data: dict[str, Any]) -> "DelphiRandom":
        src = cls(data["randseed"])
        src._draws = data["draws"]
        return src


class ReplaySource:
    """Replay a recorded stream of floats in [0, 1).

    Integer draws use ``floor(value * n)`` (ADR 0006), which matches Delphi's
    ``Random(n)`` for values produced by the Delphi generator.
    """

    def __init__(self, stream: Sequence[float]) -> None:
        if any(not (0.0 <= v < 1.0) for v in stream):
            raise ValueError("stream values must lie in [0, 1)")
        self._stream = list(stream)
        self._draws = 0

    @property
    def draws(self) -> int:
        return self._draws

    def _next(self) -> float:
        if self._draws >= len(self._stream):
            raise IndexError(f"random stream exhausted after {self._draws} draws")
        value = self._stream[self._draws]
        self._draws += 1
        return value

    def random(self, site: str | None = None) -> float:
        return self._next()

    def randint(self, n: int, site: str | None = None) -> int:
        if n < 0:
            raise ValueError("n must be >= 0")
        return math.floor(self._next() * n)

    def snapshot(self) -> dict[str, Any]:
        return {"type": "replay", "draws": self._draws, "stream": self._stream}

    @classmethod
    def restore(cls, data: dict[str, Any]) -> "ReplaySource":
        src = cls(data["stream"])
        src._draws = data["draws"]
        return src


@dataclass(frozen=True, slots=True)
class Draw:
    """One logged draw of a ``RecordingSource``.

    ``kind`` is ``"R"`` for ``Random`` and ``"I"`` for ``Random(n)`` as in the
    trace of the original; ``state_before`` is ``RandSeed`` before the draw if
    the wrapped source is a ``DelphiRandom``, else ``None``.
    """

    nr: int
    kind: str
    n: int | None
    site: str | None
    value: float | int
    state_before: int | None


class RecordingSource:
    """Wrap a source and log every draw with its call site (ADR 0010).

    The log lines up with ``random_draws.tsv.gz`` of the original
    (columns ``nr``, ``kind``, ``n``, ``randseed``, ``site``), so the first
    differing draw shows the procedure in which a port deviates.
    """

    def __init__(self, inner: RandomSource) -> None:
        self.inner = inner
        self.log: list[Draw] = []

    @property
    def draws(self) -> int:
        return self.inner.draws

    def _state(self) -> int | None:
        return self.inner.state if isinstance(self.inner, DelphiRandom) else None

    def random(self, site: str | None = None) -> float:
        before = self._state()
        value = self.inner.random(site=site)
        self.log.append(Draw(self.inner.draws, "R", None, site, value, before))
        return value

    def randint(self, n: int, site: str | None = None) -> int:
        before = self._state()
        value = self.inner.randint(n, site=site)
        self.log.append(Draw(self.inner.draws, "I", n, site, value, before))
        return value

    def snapshot(self) -> dict[str, Any]:
        """Snapshot of the wrapped source; the log is output, not state, and is not saved."""
        return self.inner.snapshot()  # type: ignore[attr-defined]


_SOURCE_TYPES: dict[str, Any] = {"numpy": NumpySource, "delphi": DelphiRandom, "replay": ReplaySource}


def restore_source(data: dict[str, Any]) -> RandomSource:
    """Rebuild a source from ``snapshot()`` output."""
    return _SOURCE_TYPES[data["type"]].restore(data)
