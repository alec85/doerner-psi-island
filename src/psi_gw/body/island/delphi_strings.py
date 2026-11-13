"""String semantics of the original's Delphi runtime under Wine (ADR 0012).

The world reads its data with Delphi ``TStringList`` objects. Two kinds of
comparison occur:

* ``CompareText`` (``Equal``, ``EqualPart`` in ``UStrList.Pas``): ASCII only,
  case-insensitive.
* ``AnsiCompareText`` (``TStringList.Sort``, ``IndexOf``, ``TNameValue``):
  ``CompareStringA(LOCALE_USER_DEFAULT, NORM_IGNORECASE)``. It ignores case,
  sorts umlauts with their base letter (``Säen`` before ``Saugen``), ignores
  hyphens and apostrophes unless everything else is equal, and orders
  whitespace, symbols, digits and letters in that order.

``ansi_compare_text`` emulates the second for the strings of the island
world. It was checked against Wine 9.0 (LCID 1033, the locale of the reference
runs) on all pairs of 453 strings from the world files
(``tests/data/wine_compare_*``, generated with ``scripts/wine_compare_strings.c``).

``string_list_sort`` is Delphi 7's ``TStringList.QuickSort``. It is not
stable, so the order of entries that compare equal follows the algorithm.
"""

from __future__ import annotations

import unicodedata
from functools import lru_cache
from typing import Callable, Sequence

_IGNORED = "-'"


def _class(ch: str) -> int:
    if ch.isspace():
        return 0
    if ch.isdigit():
        return 2
    if ch.isalpha():
        return 3
    return 1


@lru_cache(maxsize=None)
def ansi_sort_key(s: str) -> tuple:
    """Sort key equivalent to ``AnsiCompareText`` ordering (see module docstring).

    Cached: the world compares the same few hundred strings very often."""
    primary: list[tuple[int, str]] = []
    accents: list[bool] = []
    ignored: list[tuple[int, str]] = []
    for i, ch in enumerate(s):
        if ch in _IGNORED:
            ignored.append((i, ch))
            continue
        if ch == "ß":
            primary += [(3, "s"), (3, "s")]
            accents += [False, False]
            continue
        decomposed = unicodedata.normalize("NFD", ch)
        base = decomposed[0].lower()
        primary.append((_class(base), base))
        accents.append(len(decomposed) > 1)
    return (tuple(primary), tuple(accents), tuple(ignored))


def ansi_compare_text(a: str, b: str) -> int:
    """``AnsiCompareText``: negative, 0 or positive."""
    ka, kb = ansi_sort_key(a), ansi_sort_key(b)
    return -1 if ka < kb else (1 if ka > kb else 0)


def compare_text(a: str, b: str) -> int:
    """``CompareText``: ASCII case-insensitive, by character code."""
    fa = "".join(c.lower() if "A" <= c <= "Z" else c for c in a)
    fb = "".join(c.lower() if "A" <= c <= "Z" else c for c in b)
    return -1 if fa < fb else (1 if fa > fb else 0)


def equal(a: str, b: str) -> bool:
    """``Equal`` in ``UStrList.Pas``."""
    return compare_text(a, b) == 0


def equal_part(var_str: str, const_str: str) -> bool:
    """``EqualPart``: ``var_str`` starts with ``const_str`` (ASCII case-insensitive)."""
    return compare_text(var_str[:len(const_str)], const_str) == 0


def string_list_sort(items: Sequence[str],
                     compare: Callable[[str, str], int] = ansi_compare_text) -> list[str]:
    """``TStringList.Sort`` of Delphi 7 (``QuickSort`` in ``Classes.pas``)."""
    lst = list(items)

    def quick_sort(lo: int, hi: int) -> None:
        while True:
            i, j = lo, hi
            p = (lo + hi) >> 1
            while True:
                while compare(lst[i], lst[p]) < 0:
                    i += 1
                while compare(lst[j], lst[p]) > 0:
                    j -= 1
                if i <= j:
                    lst[i], lst[j] = lst[j], lst[i]
                    if p == i:
                        p = j
                    elif p == j:
                        p = i
                    i += 1
                    j -= 1
                if i > j:
                    break
            if lo < j:
                quick_sort(lo, j)
            lo = i
            if i >= hi:
                break

    if len(lst) > 1:
        quick_sort(0, len(lst) - 1)
    return lst
