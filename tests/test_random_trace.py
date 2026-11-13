"""Random trace of the original (Issue #14, ADR 0009) and the call site table."""

import csv
import gzip
from collections import Counter
from pathlib import Path

from psi_gw.random_source import DelphiRandom
from psi_gw.tracing.delphi_random_sites import SITES, site_name

TRACE = (Path(__file__).resolve().parents[1] / "traces" / "original-runs"
         / "2026-11-10-zufallsmitschnitt" / "random_draws.tsv.gz")


def _rows():
    with gzip.open(TRACE, "rt", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def test_site_table_covers_all_static_calls():
    assert len(SITES) == 44
    kinds = Counter(site.kind for site in SITES.values())
    assert kinds == {"I": 21, "R": 23}
    assert Counter(s.role for s in SITES.values()) == {"interface": 19, "cognition": 24, "world": 1}
    assert site_name(0x47916F) == "UStrukturen.Junction#1"
    assert site_name(0x12345678) == "12345678"


def test_trace_is_complete_and_reproduces_the_generator():
    rows = _rows()
    assert len(rows) == 20000
    rng = DelphiRandom(16)
    for r in rows:
        assert int(r["randseed"]) == rng._state, r["nr"]
        if r["kind"] == "I":
            rng.randint(int(r["n"]))
        else:
            rng.random()


def test_trace_sites_are_known_and_kinds_match():
    for r in _rows():
        site = SITES[int(r["ret0"], 16)]
        assert site.kind == r["kind"]


def test_synaptic_transmission_dominates_the_draws():
    sites = Counter(r["site"] for r in _rows())
    assert sites["UStrukturen.Decay#1"] == 10017
    assert sites["UStrukturen.Junction#1"] == 8500
    assert not any(name.startswith(("UFEEG", "USound")) for name in sites)
