"""Optional Matplotlib rendering of already recorded PiCrawler frames.

This is an offline data renderer, not another simulator. It reads the embedded
JSON in a replay HTML file without executing HTML or JavaScript. Matplotlib is
imported only when rendering; MP4 additionally needs ffmpeg with H.264 support.
Neither is a dependency of the simulator or the ordinary HTML replay.

Example::

    PYTHONPATH=src python -m psi_gw.body.picrawler.render_video run/replay.html \
        --png preview.png --video preview.mp4 --speed 3 --fps 12
"""

from __future__ import annotations

import argparse
from bisect import bisect_right
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
from typing import Any


def load_recording(path: Path | str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Extract the recorded JSON; never execute markup or embedded scripts."""
    path = Path(path)
    if path.is_dir():
        path = path / "replay.html"
    text = path.read_text(encoding="utf-8")
    match = re.search(r'<script\s+id="replay-data"\s+type="application/json">(.*?)</script>', text, re.S)
    if not match:
        raise ValueError("recording does not contain a replay-data JSON element")
    data = json.loads(match.group(1))
    frames = data["frames"]
    if not frames:
        raise ValueError("recording contains no frames")
    times = [f["time_s"] for f in frames]
    if any(isinstance(t, bool) or not isinstance(t, (int, float)) or not math.isfinite(t) for t in times):
        raise ValueError("recording times must be finite numbers")
    if times[0] < 0 or any(a > b for a, b in zip(times, times[1:])):
        raise ValueError("recording times must be nonnegative and ordered")
    return data["metadata"], frames


def render_recording(path: Path | str, *, png: Path | str,
                     video: Path | str | None = None, speed: float = 3.0,
                     fps: int = 12, width: int = 1600, height: int = 900,
                     preview_time_s: float | None = None) -> dict[str, Any]:
    """Render exact saved samples, using zero-order hold between samples.

    A requested MP4 is skipped if ffmpeg is unavailable, while the PNG remains
    available. The video is labelled with its simulation/playback time factor.
    No state advancement, sensor calls, interpolation or random draws occur.
    """
    if isinstance(speed, bool) or not isinstance(speed, (int, float)) or not math.isfinite(speed) or speed <= 0:
        raise ValueError("speed must be finite and positive")
    if type(fps) is not int or fps < 1 or fps > 60:
        raise ValueError("fps must be an integer in [1, 60]")
    if any(type(v) is not int or v < 600 or v % 2 for v in (width, height)):
        raise ValueError("even width and height of at least 600 pixels are required")
    meta, frames = load_recording(path)
    if preview_time_s is not None and (not isinstance(preview_time_s, (int, float)) or not math.isfinite(preview_time_s)):
        raise ValueError("preview_time_s must be finite")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.animation import FFMpegWriter
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
        import numpy as np
    except ImportError as error:
        raise RuntimeError("optional rendering requires Matplotlib and its dependencies") from error

    palette = {"bg": "#0b1420", "panel": "#142235", "line": "#31465b", "text": "#edf4fb",
               "muted": "#a8b9ca", "cyan": "#5de0cf", "gold": "#ffd182", "red": "#ff8c9f", "blue": "#83a8ff"}
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "text.color": palette["text"],
                         "axes.labelcolor": palette["muted"], "xtick.color": palette["muted"],
                         "ytick.color": palette["muted"], "axes.edgecolor": palette["line"]})
    dpi = 100
    fig = plt.figure(figsize=(width / dpi, height / dpi), dpi=dpi, facecolor=palette["bg"])
    fig.text(.035, .945, "PiCrawler · Wärme, Energie und Wahrnehmung", fontsize=25, weight="bold")
    fig.text(.035, .907, str(meta.get("initial_conditions", "Gespeicherte Simulation; kein Hardwareversuch.")),
             fontsize=11, color=palette["muted"])
    fig.text(.715, .945, "MODELLDATEN · 3D-REPLAY", fontsize=11, color=palette["cyan"],
             bbox={"boxstyle": "round,pad=.55", "facecolor": "#183637", "edgecolor": "#39656a"})

    world = meta["world"]
    xmin, ymin, xmax, ymax = world["bounds"]
    # Diagnostic drawing layers keep the large floor behind the saved limbs.
    # Translucent obstacles and the ray/path overlays are deliberate; this is
    # a coordinate-faithful data view, not a photorealistic occlusion renderer.
    ax = fig.add_axes([.015, .205, .635, .68], projection="3d", facecolor=palette["bg"], computed_zorder=False)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_zlim(0, .40)
    ax.set_box_aspect((xmax - xmin, ymax - ymin, .40))
    ax.view_init(elev=31, azim=-61)
    ax.set_axis_off()
    floor = [[xmin, ymin, 0], [xmax, ymin, 0], [xmax, ymax, 0], [xmin, ymax, 0]]
    ax.add_collection3d(Poly3DCollection([floor], facecolor="#1b3044", edgecolor="#48627c", linewidth=.9, zorder=0))
    spacing = .20
    for x in np.arange(math.ceil(xmin / spacing) * spacing, xmax + .001, spacing):
        ax.plot([x, x], [ymin, ymax], [.0001, .0001], color="#355069", lw=.6, zorder=1)
    for y in np.arange(math.ceil(ymin / spacing) * spacing, ymax + .001, spacing):
        ax.plot([xmin, xmax], [y, y], [.0001, .0001], color="#355069", lw=.6, zorder=1)
    for obstacle in world.get("obstacles", []):
        x0, x1, y0, y1, z = (obstacle[k] for k in ("x_min", "x_max", "y_min", "y_max", "height_m"))
        a, b, c, d = [x0, y0, 0], [x1, y0, 0], [x1, y1, 0], [x0, y1, 0]
        A, B, C, D = [x0, y0, z], [x1, y0, z], [x1, y1, z], [x0, y1, z]
        base = np.asarray(obstacle.get("color", [93, 120, 145])) / 255
        faces = [[a, b, B, A], [b, c, C, B], [c, d, D, C], [d, a, A, D], [A, B, C, D]]
        shades = [tuple(base * n) for n in (.65, .85, .60, .80, 1.0)]
        ax.add_collection3d(Poly3DCollection(faces, facecolors=shades, edgecolor="#c4c1ab", linewidth=.55, alpha=.85, zorder=3))
    axis_origin = [xmin + .12, ymin + .12, .004]
    ax.plot([axis_origin[0], axis_origin[0] + .25], [axis_origin[1]] * 2, [axis_origin[2]] * 2, color="#df9aa9", lw=1.8)
    ax.plot([axis_origin[0]] * 2, [axis_origin[1], axis_origin[1] + .25], [axis_origin[2]] * 2, color="#91d8c0", lw=1.8)
    ax.text(axis_origin[0] + .28, axis_origin[1], .006, "x", color="#df9aa9", fontsize=9)
    ax.text(axis_origin[0], axis_origin[1] + .28, .006, "y", color="#91d8c0", fontsize=9)
    ax.text2D(.11, .055, "Arena in Metern · Bodenraster 20 cm", transform=ax.transAxes, fontsize=10, color=palette["muted"])

    # The inset translates the same coordinates to the body origin for detail;
    # joint geometry, height, orientation and scale remain unmodified.
    detail = fig.add_axes([.035, .66, .185, .18], projection="3d", facecolor=palette["panel"], computed_zorder=False)
    detail.set_xlim(-.16, .16)
    detail.set_ylim(-.16, .16)
    detail.set_zlim(0, .16)
    detail.set_box_aspect((.32, .32, .16))
    detail.view_init(elev=28, azim=-57)
    detail.set_axis_off()
    detail.text2D(.03, .92, "Beinmechanik · Nahansicht", transform=detail.transAxes, fontsize=9, color=palette["muted"])

    def robot_artists(target):
        links = [target.plot([], [], [], "o-", color=palette["cyan"], lw=3.0,
                             markersize=4.5, markerfacecolor="#caffeb", markeredgecolor="#367d80", zorder=5)[0] for _ in range(4)]
        chassis = Poly3DCollection([[[0, 0, 0], [0, 0, 0], [0, 0, 0]]], facecolor="#299e98", edgecolor="#b5fbe7", linewidth=1, zorder=4)
        heading = Poly3DCollection([[[0, 0, 0], [0, 0, 0], [0, 0, 0]]], facecolor="#d9fff2", edgecolor="none", zorder=6)
        target.add_collection3d(chassis)
        target.add_collection3d(heading)
        return links, chassis, heading

    robot = robot_artists(ax)
    close_robot = robot_artists(detail)
    path_line, = ax.plot([], [], [], color=palette["blue"], lw=2.0, alpha=.9, zorder=2)
    ray, = ax.plot([], [], [], color=palette["gold"], lw=2, marker="o", markersize=3, zorder=7)
    contact, = ax.plot([], [], [], color=palette["red"], lw=1.4, ls="--", zorder=4)
    time_text = fig.text(.245, .845, "", fontsize=12, weight="bold", color=palette["text"])
    distance_text = fig.text(.245, .817, "", fontsize=10, color=palette["gold"])
    status_text = fig.text(.035, .205, "", fontsize=11, color=palette["gold"])

    camera_ax = fig.add_axes([.735, .705, .21, .17], facecolor=palette["panel"])
    camera_ax.set_xticks([])
    camera_ax.set_yticks([])
    camera_ax.set_title("Synthetisches Kamerabild", loc="left", fontsize=11, pad=8)
    first_rgb = next((f.get("camera_rgb") for f in frames if f.get("camera_rgb") is not None), None)
    camera_image = camera_ax.imshow(first_rgb if first_rgb is not None else np.zeros((32, 48, 3), dtype=np.uint8), interpolation="nearest")
    camera_caption = fig.text(.705, .674, "", fontsize=9, color=palette["muted"])

    times = np.asarray([f["time_s"] for f in frames], dtype=float)
    def number(value):
        return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else math.nan

    charge = np.asarray([number(f.get("telemetry", {}).get("state_of_charge")) * 100 for f in frames])
    temperature = np.asarray([number(f.get("telemetry", {}).get("cpu_temperature_c")) for f in frames])
    hunger = np.asarray([number(f.get("needs", {}).get("hunger")) for f in frames])
    damage = np.asarray([number(f.get("needs", {}).get("damage")) for f in frames])
    first_time, last_time = times[0], times[-1]
    span = max(last_time - first_time, .001)

    def chart(rect, title, ylim):
        chart_ax = fig.add_axes(rect, facecolor=palette["panel"])
        chart_ax.set_title(title, loc="left", fontsize=11, pad=8)
        chart_ax.set_xlim(first_time, last_time if last_time > first_time else first_time + 1)
        chart_ax.set_ylim(*ylim)
        chart_ax.grid(True, color="#2d4258", linewidth=.6, alpha=.8)
        chart_ax.tick_params(labelsize=9, length=0)
        chart_ax.spines[["top", "right"]].set_visible(False)
        cursor = chart_ax.axvline(first_time, color="#c4d4e6", ls=":", lw=.8)
        return chart_ax, cursor

    finite_charge = charge[np.isfinite(charge)]
    q_max = max(20, float(finite_charge.max()) + 2) if len(finite_charge) else 100
    q_ax, q_cursor = chart([.705, .485, .265, .135], "Akku-Ladestand [%]", (0, q_max))
    q_line, = q_ax.plot([], [], color=palette["cyan"], lw=2.2)
    finite_temperature = temperature[np.isfinite(temperature)]
    limits = (float(finite_temperature.min()) - 1, float(finite_temperature.max()) + 1) if len(finite_temperature) else (0, 100)
    t_ax, t_cursor = chart([.705, .295, .265, .135], "CPU-Temperatur [°C]", limits)
    t_line, = t_ax.plot([], [], color=palette["gold"], lw=2.2)
    threshold = meta.get("energy_config", {}).get("temperature_throttle_c")
    if isinstance(threshold, (int, float)) and limits[0] <= threshold <= limits[1]:
        t_ax.axhline(threshold, color="#ba8b91", ls="--", lw=.8)
        t_ax.text(last_time, threshold + .08, f"Modell: Drosselung ab {threshold:g} °C", ha="right", fontsize=8, color="#d6aeb8")
    n_ax, n_cursor = chart([.705, .105, .265, .135], "Bedürfnisse · 0 kein Bedarf / 1 maximal", (0, 1))
    h_line, = n_ax.plot([], [], color=palette["gold"], lw=2.2, label="Hunger")
    d_line, = n_ax.plot([], [], color=palette["red"], lw=2.2, label="Schaden")
    n_ax.legend(loc="lower right", fontsize=8, frameon=False, labelcolor=palette["text"], ncol=2)
    n_ax.set_xlabel("Simulationszeit [s]", fontsize=9)

    fig.text(.035, .148, "AKKU / VERSORGUNG", fontsize=9, color=palette["muted"])
    fig.text(.250, .148, "CPU / LAST", fontsize=9, color=palette["muted"])
    fig.text(.455, .148, "HUNGER / SCHADEN", fontsize=9, color=palette["muted"])
    battery_text = fig.text(.035, .108, "", fontsize=21, weight="bold")
    cpu_text = fig.text(.250, .108, "", fontsize=21, weight="bold")
    need_text = fig.text(.455, .108, "", fontsize=21, weight="bold")
    supply_text = fig.text(.035, .077, "", fontsize=10, color=palette["muted"])
    power_text = fig.text(.250, .077, "", fontsize=10, color=palette["muted"])
    fig.text(.455, .077, "lokale Abbildung · noch keine PSI-Rückwirkung", fontsize=8, color=palette["muted"])
    fig.text(.035, .034, "Kinematik + parametrierte Betriebswerte · keine Hardwaremessung · CPU-Kernspannung nicht modelliert", fontsize=10, color=palette["muted"])
    speed_text = fig.text(.705, .034, f"Wiedergabe {speed:g}× · Seed {meta.get('seed', '—')}", fontsize=10, color=palette["cyan"])

    fmt = lambda value, digits=2: f"{float(value):.{digits}f}".replace(".", ",") if math.isfinite(number(value)) else "—"

    def update_robot(artists, frame, offset):
        links, chassis, heading = artists
        for line, leg in zip(links, frame["legs"]):
            points = np.asarray(leg["points"]) - offset
            line.set_data_3d(points[:, 0], points[:, 1], points[:, 2])
        hips = np.asarray([leg["points"][0] for leg in frame["legs"]]) - offset
        chassis.set_verts([hips])
        p = frame["pose"]
        c, s, h = math.cos(p["yaw_rad"]), math.sin(p["yaw_rad"]), p["height_m"] + .001
        triangle = np.asarray([[p["x_m"] + c * x - s * y, p["y_m"] + s * x + c * y, h]
                               for x, y in ((.031, 0), (-.010, -.017), (-.010, .017))]) - offset
        heading.set_verts([triangle])

    def update(index):
        frame = frames[index]
        pose, telemetry, needs = frame["pose"], frame.get("telemetry", {}), frame.get("needs", {})
        update_robot(robot, frame, np.zeros(3))
        update_robot(close_robot, frame, np.asarray([pose["x_m"], pose["y_m"], 0]))
        previous = frames[:index + 1]
        path_line.set_data_3d([f["pose"]["x_m"] for f in previous], [f["pose"]["y_m"] for f in previous], [.002] * len(previous))
        sensor = frame["sensor"]
        distance = sensor.get("distance_m")
        origin = np.asarray(sensor["origin"])
        ray_length = distance if distance is not None else sensor["max_range_m"]
        end = origin + np.asarray(sensor["direction"]) * ray_length
        ray.set_data_3d([origin[0], end[0]], [origin[1], end[1]], [origin[2], end[2]])
        ray.set_linestyle("-" if distance is not None else "--")
        ray.set_alpha(.9 if distance is not None else .3)
        blocked = frame.get("collision") or frame.get("workspace_limited")
        angle = np.linspace(0, 2 * math.pi, 50)
        radius = meta.get("collision_radius_m", .18)
        contact.set_data_3d(pose["x_m"] + radius * np.cos(angle), pose["y_m"] + radius * np.sin(angle), np.full(50, .003))
        contact.set_visible(bool(blocked))
        time_text.set_text(f"Simulationszeit {fmt(frame['time_s'], 2)} s · Tick {frame['tick']}")
        distance_text.set_text("Ultraschall: " + (fmt(distance, 3) + " m" if distance is not None else "kein gültiges Echo"))
        states = []
        if blocked:
            states.append("Hindernisgrenze")
        if telemetry.get("thermal_throttled"):
            states.append("CPU im Modell gedrosselt")
        if telemetry.get("undervoltage"):
            states.append("Unterspannung im Modell")
        status_text.set_text(" · ".join(states) if states else "Bewegung und Betriebswerte aus dem gespeicherten Lauf")
        if frame.get("camera_rgb") is not None:
            camera_image.set_data(frame["camera_rgb"])
        regions = frame.get("perception", {}).get("camera", {}).get("blobs", [])
        camera_caption.set_text(f"{len(regions)} Farbflächen · keine Objektidentitäten")
        stop = index + 1
        for line, values in ((q_line, charge), (t_line, temperature), (h_line, hunger), (d_line, damage)):
            line.set_data(times[:stop], values[:stop])
        for cursor in (q_cursor, t_cursor, n_cursor):
            cursor.set_xdata([frame["time_s"], frame["time_s"]])
        battery_text.set_text(f"{fmt(number(telemetry.get('state_of_charge')) * 100, 1)} % · {fmt(telemetry.get('battery_voltage_v'))} V")
        supply_text.set_text(f"Versorgung {fmt(telemetry.get('supply_voltage_v', math.nan))} V")
        cpu_text.set_text(f"{fmt(telemetry.get('cpu_temperature_c', math.nan), 1)} °C")
        power_text.set_text(f"{fmt(telemetry.get('current_a', math.nan))} A · {fmt(telemetry.get('power_w', math.nan), 1)} W")
        need_text.set_text(f"{fmt(needs.get('hunger', math.nan))} / {fmt(needs.get('damage', math.nan))}")

    preview_index = len(frames) - 1 if preview_time_s is None else max(0, min(len(frames) - 1, bisect_right(times, preview_time_s) - 1))
    update(preview_index)
    png = Path(png)
    png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png, dpi=dpi, facecolor=palette["bg"], metadata={"Description": "Exact saved PiCrawler geometry and telemetry; no hardware measurements."})
    report: dict[str, Any] = {"png": str(png), "recorded_frames": len(frames), "preview_tick": frames[preview_index]["tick"],
                              "simulation_time_s": float(last_time - first_time), "speed": speed,
                              "video": None, "source_metadata": meta}
    if video is not None:
        if shutil.which("ffmpeg") is None:
            report["video_skipped"] = "ffmpeg is unavailable; PNG rendered"
        else:
            video = Path(video)
            video.parent.mkdir(parents=True, exist_ok=True)
            count = max(1, math.ceil(span / speed * fps) + 1)
            writer = FFMpegWriter(fps=fps, codec="libx264", bitrate=2400,
                                 extra_args=["-pix_fmt", "yuv420p", "-movflags", "+faststart"],
                                 metadata={"title": "PiCrawler recorded model data", "comment": f"Playback factor {speed:g}; no hardware measurements"})
            with writer.saving(fig, str(video), dpi=dpi):
                for movie_index in range(count):
                    moment = min(last_time, first_time + movie_index * speed / fps)
                    index = max(0, min(len(frames) - 1, bisect_right(times, moment + 1e-10) - 1))
                    update(index)
                    writer.grab_frame(facecolor=palette["bg"])
            report.update(video=str(video), video_frames=count, video_duration_s=count / fps, fps=fps)
    plt.close(fig)
    report["png_sha256"] = hashlib.sha256(png.read_bytes()).hexdigest()
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recording", type=Path)
    parser.add_argument("--png", type=Path, required=True)
    parser.add_argument("--video", type=Path)
    parser.add_argument("--speed", type=float, default=3.0)
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--height", type=int, default=900)
    parser.add_argument("--preview-time-s", type=float)
    args = parser.parse_args()
    try:
        report = render_recording(args.recording, png=args.png, video=args.video,
                                  speed=args.speed, fps=args.fps, width=args.width, height=args.height,
                                  preview_time_s=args.preview_time_s)
    except (ValueError, OSError, RuntimeError) as error:
        parser.error(str(error))
    print(json.dumps({key: value for key, value in report.items() if key != "source_metadata"}, indent=2))


if __name__ == "__main__":
    main()
