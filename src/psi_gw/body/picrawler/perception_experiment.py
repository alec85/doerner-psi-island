"""Independent labelled sensor sequences; compare single-frame and temporal data."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path
from typing import Any

from psi_gw.random_source import NumpySource

from .perception import camera_features, range_features
from .temporal import SensorMemory
from .validation_io import canonical, source_info, write_json

RANGE_CASES = ("noise", "outliers", "short_dropout", "long_dropout", "stale", "duplicates")
CAMERA_CASES = ("clean", "occlusion", "dim", "blackout")


def range_sequence(seed: int, kind: str) -> list[dict[str, Any]]:
    if kind not in RANGE_CASES:
        raise ValueError("unknown range sequence")
    rng = NumpySource(seed)
    frames, last = [], None
    for tick in range(120):
        now = tick * .05
        truth = .32 - .025 * now
        sample = {"status": "ok", "distance_m": truth + .003 * (2 * rng.random(site="picrawler.corpus.range") - 1),
                  "captured_at_s": now}
        if kind == "outliers" and tick > 30 and tick % 17 == 0:
            sample["distance_m"] += .25
        if (kind == "short_dropout" and tick in (40, 41)) or (kind == "long_dropout" and 40 <= tick <= 55):
            sample.update(distance_m=None, status="dropout")
        if kind == "stale" and 40 <= tick <= 70:
            sample.update(distance_m=.32 - .025 * (now - .5), captured_at_s=now - .5)
        if kind == "duplicates" and last is not None and tick % 3:
            sample = last.copy()
        else:
            last = sample.copy()
        frames.append({"time_s": now, "truth_distance_m": truth, "sample": sample})
    return frames


def camera_sequence(seed: int, kind: str) -> list[dict[str, Any]]:
    if kind not in CAMERA_CASES:
        raise ValueError("unknown camera sequence")
    rng = NumpySource(seed)
    frames = []
    for tick in range(60):
        x = 4 + (tick // 4) % 10
        image = [[[20, 20, 20] for _ in range(24)] for _ in range(16)]
        hidden = kind == "occlusion" and 16 <= tick <= 18
        brightness = .2 if kind == "dim" and 16 <= tick <= 18 else 1
        if not hidden:
            for yy in range(5, 9):
                for xx in range(x, x + 4):
                    image[yy][xx] = [int(230 * brightness), int(20 * brightness), int(20 * brightness)]
        # Isolated background speckles stay below the connected-region pixel threshold.
        sx, sy = rng.randint(24, site="picrawler.corpus.pixel"), rng.randint(3, site="picrawler.corpus.pixel")
        image[sy][sx] = [230, 20, 20]
        sample = {"rgb": image, "encoding": "rgb8", "width": 24, "height": 16, "captured_at_s": tick * .05}
        if kind == "blackout" and 15 <= tick <= 30:
            sample = None
        frames.append({"time_s": tick * .05, "truth_centroid_x": (x + 2) / 24,
                       "physically_visible": not hidden, "sample": sample})
    return frames


def run_perception_experiment(output: str | Path, seeds: tuple[int, ...] = (0, 1, 42)) -> dict[str, Any]:
    output = Path(output)
    if not seeds or any(type(s) is not int or s < 0 for s in seeds) or len(set(seeds)) != len(seeds):
        raise ValueError("distinct nonnegative seeds required")
    if output.exists() and any(output.iterdir()):
        raise ValueError("perception experiment output must be new or empty")
    range_results, camera_results = [], []
    for seed in seeds:
        for kind in RANGE_CASES:
            sequence = range_sequence(seed, kind)
            memory = SensorMemory()
            scores = {policy: {"usable_frames": 0, "false_clear_frames": 0, "absolute_error_sum_m": 0.0}
                      for policy in ("single", "temporal")}
            estimates = []
            for frame in sequence:
                single = range_features(frame["sample"], now_s=frame["time_s"])
                temporal = memory.update({"ultrasonic": frame["sample"]}, now_s=frame["time_s"])
                values = {"single": single.distance_m if single.usable else None, "temporal": temporal["distance_m"]}
                estimates.append({"time_s": frame["time_s"], **values})
                for policy, value in values.items():
                    if value is not None:
                        score = scores[policy]
                        score["usable_frames"] += 1
                        score["false_clear_frames"] += int(frame["truth_distance_m"] < .27 and value >= .27)
                        score["absolute_error_sum_m"] += abs(value - frame["truth_distance_m"])
            for score in scores.values():
                score["mean_absolute_error_m"] = score.pop("absolute_error_sum_m") / max(1, score["usable_frames"])
            range_results.append({"seed": seed, "case": kind, "frames": len(sequence), "scores": scores})
            write_json(output / "range" / f"s{seed}-{kind}.json", {"origin": "synthetic", "frames": sequence, "estimates": estimates})
        for kind in CAMERA_CASES:
            sequence = camera_sequence(seed, kind)
            memory = SensorMemory()
            scores = {policy: {"available_frames": 0, "absolute_centroid_error_sum": 0.0}
                      for policy in ("single", "temporal")}
            active_ids, estimates = set(), []
            for frame in sequence:
                feature = camera_features(frame["sample"], now_s=frame["time_s"])
                blobs = [asdict(b) for b in feature.blobs if b.color == "red"] if feature.usable else []
                tracks = memory.update({"camera": frame["sample"]}, now_s=frame["time_s"])["tracks"]
                current = [t for t in tracks if t["color"] == "red" and t["confidence"] > 0]
                # Ground truth is used solely to score matching observed regions.
                chosen = {"single": min(blobs, key=lambda b: abs(b["centroid_x"] - frame["truth_centroid_x"])) if blobs else None,
                          "temporal": min(current, key=lambda t: abs(t["centroid_x"] - frame["truth_centroid_x"])) if current else None}
                estimates.append({"time_s": frame["time_s"], "single_regions": blobs, "tracks": tracks})
                for policy, item in chosen.items():
                    if item is not None:
                        scores[policy]["available_frames"] += 1
                        scores[policy]["absolute_centroid_error_sum"] += abs(item["centroid_x"] - frame["truth_centroid_x"])
                        if policy == "temporal":
                            active_ids.add(item["id"])
            for score in scores.values():
                score["mean_absolute_centroid_error"] = score.pop("absolute_centroid_error_sum") / max(1, score["available_frames"])
            camera_results.append({"seed": seed, "case": kind, "frames": len(sequence), "scores": scores,
                                   "temporal_region_ids": sorted(active_ids)})
            write_json(output / "camera" / f"s{seed}-{kind}.json", {"origin": "synthetic", "frames": sequence, "estimates": estimates})
    summary = {"type": "psi_gw.picrawler.temporal_comparison", "version": 1, "origin": "synthetic",
        "runtime": source_info(), "seeds": list(seeds), "range": range_results, "camera": camera_results,
        "limits": ["Synthetic labelled sequences; descriptive results only.",
            "Held range assumes bounded closing speed and no rotation; not protection against unseen moving obstacles.",
            "Colour-region IDs are associations, not object identities; held positions do not predict hidden motion."]}
    write_json(output / "summary.json", summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 42])
    args = parser.parse_args(argv)
    try:
        summary = run_perception_experiment(args.output, tuple(args.seeds))
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(canonical({"range_sequences": len(summary["range"]), "camera_sequences": len(summary["camera"]), "origin": "synthetic"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
