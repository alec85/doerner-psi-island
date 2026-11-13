"""Plane geometry of the original as computed on the x87 FPU (``Menue.Pas``; ADR 0005, 0012).

Perception chooses the next line point by comparing angle differences for
``<=`` (``NextCont`` in ``UPercept.Pas``). Exact ties are common, and whether
a tie survives depends on 80-bit rounding: for example ``2*pi`` stored as a
64-bit real and compared with ``2*pi`` in 80 bits differs by about 2e-16.
These functions reproduce the FPU results exactly:

* ``winkel``: ``Winkel``, an angle in [0, 2 pi) as a 64-bit real. The FPU's
  ``FPATAN`` is not always correctly rounded; for all integer vectors in
  [-160, 160]^2 it differs from correct rounding only for the direction
  (13, -17) and its multiples (checked on the x87 under Wine with
  ``scripts/x87_winkel.c``, control word $1332 as set by Delphi).
* ``winkel_differenz``: ``WinkelDifferenz`` with 80-bit intermediates.
* ``distanz``: ``Distanz``, with the square root rounded to 80 and then to
  64 bits.
"""

from __future__ import annotations

import math
from decimal import Decimal, localcontext
from fractions import Fraction
from functools import lru_cache

from psi_gw.body.island.x87 import round_bits

_PREC = 70


def _decimal_pi() -> Decimal:
    def arctan_inv(n: int) -> Decimal:
        x = Decimal(1) / n
        x2, s, t, k = x * x, x, x, 1
        eps = Decimal(10) ** -(_PREC - 2)
        while True:
            t *= -x2
            k += 2
            d = t / k
            if abs(d) < eps:
                return s
            s += d
    with localcontext() as ctx:
        ctx.prec = _PREC
        return 4 * (4 * arctan_inv(5) - arctan_inv(239))


_PI_DEC = _decimal_pi()
PI_EXT = round_bits(Fraction(_PI_DEC), 64)
"""``pi`` as the FPU loads it (``FLDPI``), exactly."""


def _datan(x: Fraction) -> Fraction:
    with localcontext() as ctx:
        ctx.prec = _PREC
        d = Decimal(x.numerator) / Decimal(x.denominator)
        neg, d = d < 0, abs(d)
        inv = d > 1
        if inv:
            d = 1 / d
        for _ in range(3):
            d = d / (1 + (1 + d * d).sqrt())
        x2, s, t, k = d * d, d, d, 1
        eps = Decimal(10) ** -(_PREC - 2)
        while True:
            t *= -x2
            k += 2
            term = t / k
            if abs(term) < eps:
                break
            s += term
        s *= 8
        if inv:
            s = _PI_DEC / 2 - s
        return Fraction(-s if neg else s)


# FPATAN results that differ from correct rounding, keyed by the reduced
# quotient ordinate/abscissa: 64-bit real result of Winkel as hex.
_FPATAN_EXCEPTIONS = {Fraction(-13, 17): 0x3FE4E41E9E3C3616}


def _from_bits(bits: int) -> float:
    return float.fromhex(f"0x1.{bits & ((1 << 52) - 1):013x}p{((bits >> 52) & 0x7FF) - 1023}")


@lru_cache(maxsize=None)
def _winkel(ordinate: int, abszisse: int) -> float:
    if abszisse != 0:
        q = Fraction(ordinate, abszisse)
        if q in _FPATAN_EXCEPTIONS:
            return _from_bits(_FPATAN_EXCEPTIONS[q])
        qe = round_bits(q, 64)
        w = round_bits(_datan(qe), 64)
        if ordinate > 0:
            res = round_bits(PI_EXT - w, 64) if abszisse > 0 else abs(w)
        else:
            res = round_bits(PI_EXT + abs(w), 64) if abszisse > 0 else round_bits(2 * PI_EXT - w, 64)
    else:
        res = PI_EXT / 2 if ordinate > 0 else round_bits(3 * PI_EXT, 64) / 2
    return float(round_bits(res, 53))


def winkel(p0: tuple[int, int], p1: tuple[int, int]) -> float:
    """``Winkel``: angle of the vector from ``p0`` to ``p1`` (0 right, pi/2 up, ...)."""
    return _winkel(p0[1] - p1[1], p0[0] - p1[0])


TWO_PI_EXT = 2 * PI_EXT


@lru_cache(maxsize=None)
def winkel_differenz(w1: float, w2: float) -> float:
    """``WinkelDifferenz``: difference of two angles in [0, pi], 80-bit intermediates."""
    r = abs(round_bits(Fraction(w1) - Fraction(w2), 64))
    if r > PI_EXT:
        r = abs(round_bits(r - TWO_PI_EXT, 64))
    return float(round_bits(r, 53))


def real_const(x: Fraction) -> float:
    """An 80-bit constant expression stored in a 64-bit real variable."""
    return float(round_bits(round_bits(x, 64), 53))


@lru_cache(maxsize=None)
def _sqrt_x87(n: int) -> float:
    if n == 0:
        return 0.0
    # floor(sqrt(n) * 2^k) with enough bits, then round to 64 and to 53 bits
    k = 80
    root = math.isqrt(n << (2 * k))
    exact = root * root == n << (2 * k)
    value = Fraction(root, 1 << k)
    if not exact:
        # nudge below the next representable step so that rounding sees "above root"
        value += Fraction(1, 1 << (k + 1))
    return float(round_bits(round_bits(value, 64), 53))


def distanz(p1: tuple[int, int], p2: tuple[int, int]) -> float:
    """``Distanz``: Euclidean distance as a 64-bit real."""
    if p1 == p2:
        return 0.0
    return _sqrt_x87((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)
