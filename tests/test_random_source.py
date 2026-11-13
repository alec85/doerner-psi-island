"""Tests for the sources of randomness (ADR 0005, ADR 0008)."""

import math

import pytest

from psi_gw.random_source import DelphiRandom, NumpySource, RandomSource, ReplaySource


def test_all_sources_satisfy_protocol():
    for source in (NumpySource(1), DelphiRandom(16), ReplaySource([0.5])):
        assert isinstance(source, RandomSource)


def test_delphi_recurrence_by_hand():
    rng = DelphiRandom(0)
    assert rng.random() == 1 * 2.0 ** -32          # 0 * $08088405 + 1 = 1
    assert rng.rand_seed == 1
    rng.random()                                    # 1 * $08088405 + 1
    assert rng.rand_seed == 0x08088406
    assert rng.draws == 2


def test_delphi_wraps_at_32_bit_and_reports_signed_seed():
    rng = DelphiRandom(-1)                          # $FFFFFFFF
    expected = (0xFFFFFFFF * 0x08088405 + 1) & 0xFFFFFFFF
    rng.random()
    assert rng._state == expected
    signed = expected - (1 << 32) if expected >= 1 << 31 else expected
    assert rng.rand_seed == signed


def test_delphi_integer_draw_equals_floor_of_real_draw():
    """Random(n) = (n * RandSeed) shr 32 must equal floor(Random * n)."""
    for n in (1, 2, 7, 10, 100, 1000, 2**31 - 1):
        a, b = DelphiRandom(16), DelphiRandom(16)
        for _ in range(500):
            assert a.randint(n) == math.floor(b.random() * n)


def test_delphi_values_in_unit_interval_and_replay_matches():
    rng = DelphiRandom(16)
    values = [rng.random() for _ in range(1000)]
    assert all(0.0 <= v < 1.0 for v in values)

    replay, again = ReplaySource(values), DelphiRandom(16)
    for i in range(1000):
        if i % 3:
            assert replay.random() == again.random()
        else:
            assert replay.randint(37) == again.randint(37)
    with pytest.raises(IndexError):
        replay.random()


def test_randint_zero_consumes_a_draw_like_delphi():
    rng = DelphiRandom(5)
    assert rng.randint(0) == 0
    assert rng.draws == 1


def test_numpy_source_is_reproducible():
    a, b = NumpySource(42), NumpySource(42)
    assert [a.random() for _ in range(5)] == [b.random() for _ in range(5)]
    assert 0 <= a.randint(10) < 10
    assert a.draws == 6


# --- RecordingSource and snapshots (ADR 0010) ---------------------------------

import json

from psi_gw.random_source import RecordingSource, restore_source


def test_recording_source_logs_kind_site_and_randseed():
    rec = RecordingSource(DelphiRandom(16))
    plain = DelphiRandom(16)
    before = plain.state
    assert rec.random(site="UStrukturen.Decay#1") == plain.random()
    middle = plain.state
    assert rec.randint(7, site="UStrukturen.RandomChoice#1") == plain.randint(7)
    assert [(d.nr, d.kind, d.n, d.site) for d in rec.log] == [
        (1, "R", None, "UStrukturen.Decay#1"),
        (2, "I", 7, "UStrukturen.RandomChoice#1"),
    ]
    assert [d.state_before for d in rec.log] == [before, middle]
    assert rec.draws == 2


def test_recording_source_without_delphi_has_no_randseed():
    rec = RecordingSource(NumpySource(1))
    rec.random()
    assert rec.log[0].state_before is None


@pytest.mark.parametrize("make", [
    lambda: DelphiRandom(16),
    lambda: NumpySource(42),
    lambda: ReplaySource([0.1, 0.5, 0.9, 0.3, 0.7, 0.2]),
])
def test_snapshot_restore_continues_identically(make):
    src = make()
    src.random()
    src.randint(10)
    data = json.loads(json.dumps(src.snapshot()))
    copy = restore_source(data)
    assert copy.draws == src.draws
    assert [copy.random(), copy.randint(5)] == [src.random(), src.randint(5)]
