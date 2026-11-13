"""Bitmaps of the island world (``UBitmaps.pas``; ADR 0012).

Objects of the island are 50 x 50 pixel Windows bitmaps with 256 colours
(``reference/delphi-runtime/PsiCode/Bitmaps``). White is transparent. The
original prepares two derived images per bitmap (``Tbm.Create``):

* the mask: every non-white pixel black, white stays white,
* the sprite: every white pixel black, the rest unchanged,

and draws an object by AND-ing the mask and OR-ing the sprite onto the canvas
(``DrawBitmapMaskAndSprite``). The result is the object's colours where it is
not white and the old canvas elsewhere.

Images are NumPy arrays of Delphi ``TColor`` values (``$00BBGGRR``), so
``clBlack`` is 0 and ``clWhite`` is ``0xFFFFFF`` as in the original's pixel
tests.
"""

from __future__ import annotations

import os
import struct
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
BITMAP_DIR = ROOT / "reference" / "delphi-runtime" / "PsiCode" / "Bitmaps"
TEXT_BITMAPS = Path(__file__).resolve().parent / "data" / "wine_text_bitmaps.txt"

CL_BLACK = 0x000000
CL_WHITE = 0xFFFFFF


def tcolor(r: int, g: int, b: int) -> int:
    """Delphi ``TColor`` (``RGB``) from components."""
    return r | (g << 8) | (b << 16)


@dataclass
class Bitmap:
    """A bitmap as the original holds it.

    Attributes:
        pixels: ``(height, width)`` array of ``TColor`` values.
        indices: palette indices for 8-bit bitmaps, else ``None``.
        palette: ``TColor`` per palette index for 8-bit bitmaps.
    """

    pixels: np.ndarray
    indices: np.ndarray | None = None
    palette: list[int] = field(default_factory=list)

    @property
    def width(self) -> int:
        return int(self.pixels.shape[1])

    @property
    def height(self) -> int:
        return int(self.pixels.shape[0])

    def copy(self) -> "Bitmap":
        return Bitmap(self.pixels.copy(), None if self.indices is None else self.indices.copy(),
                      list(self.palette))


def read_bmp(path: Path) -> Bitmap:
    """Read an uncompressed 8- or 24-bit Windows bitmap (the formats in the runtime folder)."""
    data = path.read_bytes()
    if data[:2] != b"BM":
        raise ValueError(f"{path} is not a bitmap")
    offset = struct.unpack_from("<I", data, 10)[0]
    header = struct.unpack_from("<I", data, 14)[0]
    width, height, _, bpp, compression = struct.unpack_from("<iiHHI", data, 18)
    if compression != 0:
        raise ValueError(f"{path}: compressed bitmaps are not supported")
    bottom_up = height > 0
    height = abs(height)
    stride = ((width * bpp + 31) // 32) * 4
    rows = [data[offset + y * stride: offset + y * stride + stride] for y in range(height)]
    if bottom_up:
        rows.reverse()
    if bpp == 8:
        n_colors = struct.unpack_from("<I", data, 46)[0] or 256
        pal_raw = data[14 + header: 14 + header + 4 * n_colors]
        palette = [tcolor(pal_raw[4 * i + 2], pal_raw[4 * i + 1], pal_raw[4 * i]) for i in range(n_colors)]
        palette += [0] * (256 - len(palette))
        indices = np.array([list(r[:width]) for r in rows], dtype=np.uint8)
        pixels = np.array(palette, dtype=np.uint32)[indices]
        return Bitmap(pixels, indices, palette)
    if bpp == 24:
        arr = np.frombuffer(b"".join(r[:width * 3] for r in rows), dtype=np.uint8).reshape(height, width, 3)
        b, g, r = (arr[..., k].astype(np.uint32) for k in range(3))
        return Bitmap(r | (g << 8) | (b << 16))
    raise ValueError(f"{path}: {bpp} bits per pixel not supported")


def _round_half_even(x: float) -> int:
    return int(round(x))


@dataclass
class ObjectBitmap:
    """``Tbm``: bitmap, mask, sprite and centre of gravity of one object."""

    name: str
    bitmap: Bitmap
    mask: np.ndarray
    sprite: np.ndarray
    gravity: tuple[int, int]


def _gravity(bm: Bitmap) -> tuple[int, int]:
    """``CalcGravityPoint``: mean position of the pixels with the first black palette index.

    Only for 8-bit 50 x 50 bitmaps; otherwise (0, 0) as in the original.
    """
    if bm.indices is None or bm.width != 50 or bm.height != 50:
        return (0, 0)
    i_black = next((i for i, c in enumerate(bm.palette) if c == CL_BLACK), 0)
    ys, xs = np.nonzero(bm.indices == i_black)
    n = len(xs)
    if n == 0:
        return (0, 0)
    # Delphi's Round rounds halves to even, as Python's round does.
    return (_round_half_even(int(xs.sum()) / n), _round_half_even(int(ys.sum()) / n))


def read_text_bitmaps(path: Path = TEXT_BITMAPS) -> dict[str, Bitmap]:
    """Bitmaps ``BuildBitmap`` drew under Wine (black frame and the name as text), by lower-case name."""
    result: dict[str, Bitmap] = {}
    lines = [line for line in path.read_text(encoding="utf-8").split("\n") if not line.startswith(";")]
    i = 0
    while i < len(lines):
        if lines[i].startswith("name "):
            name = lines[i][5:]
            rows = lines[i + 2:i + 52]
            black = np.array([[c == "#" for c in row] for row in rows])
            indices = np.where(black, 0, 255).astype(np.uint8)
            palette = [CL_BLACK] + [0x010101 * k for k in range(1, 255)] + [CL_WHITE]
            pixels = np.array(palette, dtype=np.uint32)[indices]
            result[name.lower()] = Bitmap(pixels, indices, palette)
            i += 52
        else:
            i += 1
    return result


class BitmapStore:
    """Cache of object bitmaps by name (``FindBitmap``), case-insensitive like Windows file names.

    Under Wine the original cannot open bitmap files whose names contain an
    umlaut (they are stored in code page 437; Wine looks for the UTF-8 form of
    the code page 1252 name). ``Tbm.Create`` then draws the name as text
    (``BuildBitmap``). With ``wine_names`` (the reference mode, ADR 0013) these
    objects get the bitmaps the original drew under Wine.
    """

    def __init__(self, directory: Path = BITMAP_DIR, wine_names: bool = True) -> None:
        self.directory = directory
        self._generated = read_text_bitmaps() if wine_names else {}
        self._files: dict[str, Path] = {}
        for entry in os.listdir(directory):
            stem, ext = os.path.splitext(entry)
            if ext.lower() != ".bmp":
                continue
            # Names with umlauts were extracted in code page 437.
            raw = os.fsencode(stem)
            name = raw.decode("cp437") if any(b > 127 for b in raw) else stem
            self._files[name.lower()] = directory / entry
        self._cache: dict[str, ObjectBitmap] = {}

    def __contains__(self, name: str) -> bool:
        return name.lower() in self._files

    def get(self, name: str) -> ObjectBitmap:
        key = name.lower()
        if key not in self._cache and key in self._generated:
            bm = self._generated[key]
            white = bm.pixels == CL_WHITE
            mask = np.where(white, CL_WHITE, CL_BLACK).astype(np.uint32)
            sprite = np.where(white, CL_BLACK, bm.pixels).astype(np.uint32)
            self._cache[key] = ObjectBitmap(name, bm, mask, sprite, _gravity(bm))
        if key not in self._cache:
            path = self._files.get(key)
            if path is None:
                # The original draws the name as text on a white 50 x 50 bitmap
                # (BuildBitmap). Text rendering is not ported; no object of the
                # island that can appear in a situation lacks a file.
                raise FileNotFoundError(f"no bitmap for {name!r}")
            bm = read_bmp(path)
            white = bm.pixels == CL_WHITE
            mask = np.where(white, CL_WHITE, CL_BLACK).astype(np.uint32)
            sprite = np.where(white, CL_BLACK, bm.pixels).astype(np.uint32)
            self._cache[key] = ObjectBitmap(name, bm, mask, sprite, _gravity(bm))
        return self._cache[key]

    def gravity_point(self, name: str) -> tuple[int, int]:
        """``GravityPoint``."""
        return self.get(name).gravity


def draw_mask_and_sprite(canvas: np.ndarray, x: int, y: int, obj: ObjectBitmap) -> None:
    """``DrawBitmapMaskAndSprite``: AND the mask, then OR the sprite, clipped to the canvas."""
    h, w = obj.mask.shape
    ch, cw = canvas.shape
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, cw), min(y + h, ch)
    if x0 >= x1 or y0 >= y1:
        return
    region = canvas[y0:y1, x0:x1]
    m = obj.mask[y0 - y:y1 - y, x0 - x:x1 - x]
    s = obj.sprite[y0 - y:y1 - y, x0 - x:x1 - x]
    canvas[y0:y1, x0:x1] = (region & m) | s


def fill_polygon(canvas: np.ndarray, points: list[tuple[int, int]], color: int) -> None:
    """Fill a polygon and draw its outline in ``color`` (GDI ``Polygon`` with equal pen and brush).

    DEVIATION(ADR-0012): approximates GDI's rasterisation (alternate fill at
    pixel centres, outline by Bresenham lines). Only the non-black ground and
    sky are drawn this way; the black pixels that perception reads come from
    the object bitmaps drawn afterwards.
    """
    h, w = canvas.shape
    n = len(points)
    for yy in range(h):
        cy = yy + 0.5
        xs = []
        for i in range(n):
            (xa, ya), (xb, yb) = points[i], points[(i + 1) % n]
            if (ya <= cy < yb) or (yb <= cy < ya):
                xs.append(xa + (cy - ya) * (xb - xa) / (yb - ya))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            lo = max(int(np.ceil(xs[k] - 0.5)), 0)
            hi = min(int(np.ceil(xs[k + 1] - 0.5)), w)
            if lo < hi:
                canvas[yy, lo:hi] = color
    for i in range(n):
        _line(canvas, points[i], points[(i + 1) % n], color)


def _line(canvas: np.ndarray, a: tuple[int, int], b: tuple[int, int], color: int) -> None:
    h, w = canvas.shape
    (x0, y0), (x1, y1) = a, b
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        if 0 <= x0 < w and 0 <= y0 < h:
            canvas[y0, x0] = color
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy
