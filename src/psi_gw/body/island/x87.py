"""Exact emulation of the few 80-bit computations whose results the world prints (ADR 0005, 0012).

Delphi evaluates real expressions on the x87 FPU with a 64-bit mantissa,
treats real literals as ``Extended`` constants, and rounds to a 64-bit
``real`` (double) when a value is stored in or passed as a ``real``. For
need effects the world then prints the value with ``Format('%f')`` (two
decimals) and Psi parses the text again. Values near a rounding boundary
(e.g. 75 * 0.0002 = 0.015) depend on every one of these steps.

The functions here compute with exact fractions and round like the FPU.
They are used only where results are formatted to text, not in hot paths.

Checked against the event protocol of the full life with seed 16: Hunger
after 75 units of distance arrives as 0.01, Schaden after 155 units with
smoothness 0.9 as 1.08, after 45 and 35 units as 0.31, 0.95 and 0.24.
"""

from __future__ import annotations

from fractions import Fraction


def round_bits(x: Fraction, bits: int) -> Fraction:
    """Round to ``bits`` significant binary digits, ties to even (FPU default)."""
    if x == 0:
        return Fraction(0)
    sign = 1 if x > 0 else -1
    x = abs(x)
    e = x.numerator.bit_length() - x.denominator.bit_length()
    while Fraction(2) ** e > x:
        e -= 1
    while Fraction(2) ** (e + 1) <= x:
        e += 1
    scale = Fraction(2) ** (bits - 1 - e)
    m = x * scale
    fl = m.numerator // m.denominator
    rem = m - fl
    if rem > Fraction(1, 2) or (rem == Fraction(1, 2) and fl % 2):
        fl += 1
    return sign * Fraction(fl) / scale


def ext(x) -> Fraction:
    """Value as an 80-bit ``Extended`` (64-bit mantissa). Literals pass as strings: ``ext("0.0002")``."""
    return round_bits(Fraction(x), 64)


def dbl(x) -> Fraction:
    """Value as a 64-bit ``real``."""
    return round_bits(Fraction(x), 53)


def format_f(value: Fraction, decimals: int = 2) -> str:
    """``Format('%f', [value])`` with the default two decimals; halves round away from zero.

    Delphi converts to 18 significant decimal digits first; both steps round
    halves away from zero.
    """
    v = Fraction(value)
    sign = "-" if v < 0 else ""
    v = abs(v)
    if v != 0:
        e = len(str(v.numerator // v.denominator)) - 1 if v >= 1 else -_leading_zeros(v) - 1
        q = Fraction(10) ** (17 - e)
        v = Fraction(int(v * q + Fraction(1, 2))) / q
    scaled = int(v * 10 ** decimals + Fraction(1, 2))
    text = f"{scaled // 10 ** decimals}.{scaled % 10 ** decimals:0{decimals}d}" if decimals else str(scaled)
    return sign + text if scaled else text


def _leading_zeros(v: Fraction) -> int:
    n = 0
    while v * 10 < 1:
        v *= 10
        n += 1
    return n


def float_to_str(x: float) -> str:
    """``FloatToStr``: general format with 15 significant digits.

    Fixed notation unless the exponent is below -5 or at least 15; Delphi
    then writes the exponent without padding (``1E-6``).
    """
    if x == 0:
        return "0"
    s = f"{x:.15g}"
    if "e" in s:
        mant, exp = s.split("e")
        return f"{mant}E{int(exp)}"
    return s


def str_real(x: float, width: int, decimals: int) -> str:
    """Pascal ``write(x:width:decimals)`` for a real, as in the protocol files."""
    return format_f(Fraction(x), decimals).rjust(width)
