"""Scored independent sequences, including explicit limits of temporal holding."""

import json

import pytest

from psi_gw.body.picrawler.perception_experiment import (
    CAMERA_CASES, RANGE_CASES, camera_sequence, range_sequence, run_perception_experiment,
)
from psi_gw.body.picrawler.temporal import SensorMemory
from psi_gw.body.picrawler.validation_io import canonical, digest


@pytest.mark.parametrize("case", RANGE_CASES)
def test_range_fixture_is_deterministic_and_memory_restores_exactly(case):
    sequence = range_sequence(42, case)
    assert sequence == range_sequence(42, case)
    memory = SensorMemory()
    restored = None
    for index, frame in enumerate(sequence):
        output = memory.update({"ultrasonic": frame["sample"]}, now_s=frame["time_s"])
        if restored is not None:
            assert output == restored.update({"ultrasonic": frame["sample"]}, now_s=frame["time_s"])
            assert digest(memory.snapshot()) == digest(restored.snapshot())
        if index == 40:
            restored = SensorMemory.restore(json.loads(canonical(memory.snapshot())))


@pytest.mark.parametrize("case", CAMERA_CASES)
def test_camera_fixture_is_deterministic_and_tracks_never_outlive_their_limit(case):
    frames = camera_sequence(7, case)
    assert frames == camera_sequence(7, case)
    memory = SensorMemory()
    for frame in frames:
        result = memory.update({"camera": frame["sample"]}, now_s=frame["time_s"])
        assert all(t["age_s"] <= .30 + 1e-9 for t in result["tracks"])
        assert len({t["id"] for t in result["tracks"]}) == len(result["tracks"])


def test_labelled_corpus_demonstrates_bounded_benefits_without_claiming_perfect_tracking(tmp_path):
    report = run_perception_experiment(tmp_path, (42,))
    ranges = {r["case"]: r for r in report["range"]}
    cameras = {r["case"]: r for r in report["camera"]}
    assert ranges["outliers"]["scores"]["single"]["false_clear_frames"] > 0
    assert ranges["outliers"]["scores"]["temporal"]["false_clear_frames"] == 0
    assert ranges["short_dropout"]["scores"]["temporal"]["usable_frames"] > ranges["short_dropout"]["scores"]["single"]["usable_frames"]
    assert ranges["long_dropout"]["scores"]["temporal"]["usable_frames"] < 120
    assert cameras["occlusion"]["scores"]["temporal"]["available_frames"] > cameras["occlusion"]["scores"]["single"]["available_frames"]
    assert len(cameras["blackout"]["temporal_region_ids"]) > 1
    assert cameras["occlusion"]["scores"]["temporal"]["mean_absolute_centroid_error"] > 0
    with pytest.raises(ValueError, match="new or empty"):
        run_perception_experiment(tmp_path, (42,))
