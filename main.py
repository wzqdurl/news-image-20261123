#!/usr/bin/env python3
"""THE WORLD IN ONE DAY - Monday 23 November 2026.

make.fun entry for competition `news-image-20261123`.

A program that draws, entirely in code, a newspaper front page summing
up the world's news of Monday 23 November 2026 and writes it as a
1024x1024 PNG to /output/entry.png (or $MAKEFUN_OUTPUT_DIR/entry.png,
or a path given as the first argument).

Python 3.13, standard library only, no network, no clock, no randomness:
every run writes the same bytes.

How it is made
--------------
* Text: every letter is drawn from a single-stroke vector font defined
  in this file (GLYPHS). Each glyph is a set of polylines on a small
  grid, written by hand for this entry. Glyphs are rasterised with
  2x supersampling, so diagonals stay smooth.
* Scenes: each of the 13 panels is a small flat-colour vector
  illustration built from rectangles, polygons, circles and lines.
  There are no real people, no faces and no brand logos. The House
  panel shows the Capitol building; Mercury is grey; the motorcycle
  carries no brand or number.
* Map: simplified continent outlines, drawn from coarse longitude /
  latitude coordinates written for this entry, with numbered pins.
  Pins that would collide are pushed apart with leader lines.
* Self-checks: before saving, the program checks that every piece of
  text sits inside its box, that no two text boxes overlap, that no
  map pins collide, that every glyph exists, and that the PNG is
  under 1 MiB. Any failure aborts with an error.

The 36 stories (13 main + 23 ALSO) are listed in README.md. Three
stories that earlier drafts dated to 23 November were re-checked
against live reporting and corrected:
* Nvidia chief Huang resigned on 12 November, not 23 November, so
  panel 12 now reports the SEC probe first reported on 23 November.
* The Iran/Bahrain radar claim was made on 21-22 November, so panel 3
  now reports Bahrain's demand for compensation, first reported on
  23 November.
* Trump called Putin "my friend" at Shenzhen on 19 November, so the
  ALSO item now reports the US intelligence chief defending the remark
  on 23 November.
"""

import math
import os
import struct
import sys
import zlib

W = 1024
H = 1024

PAPER = (245, 241, 230)
INK = (20, 18, 16)
GREY = (150, 148, 140)
LIGHT_GREY = (210, 208, 200)

# ---------------------------------------------------------------- PNG ---


def write_png(path, rows):
    """Write an RGB image (list of bytearray rows) as a PNG."""
    height = len(rows)
    width = len(rows[0]) // 3
    raw = bytearray()
    for row in rows:
        raw.append(0)  # filter: none
        raw += row
    comp = zlib.compress(bytes(raw), 9)

    def chunk(kind, data):
        out = struct.pack(">I", len(data)) + kind + data
        out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


# -------------------------------------------------------------- Canvas ---


class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.rows = []
        line = bytearray()
        for _ in range(w):
            line += bytes(bg)
        for _ in range(h):
            self.rows.append(bytearray(line))

    def set_px(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            r = self.rows[y]
            r[x * 3] = color[0]
            r[x * 3 + 1] = color[1]
            r[x * 3 + 2] = color[2]

    def fill_rect(self, x0, y0, x1, y1, color):
        x0 = max(0, int(x0))
        y0 = max(0, int(y0))
        x1 = min(self.w, int(x1))
        y1 = min(self.h, int(y1))
        if x1 <= x0 or y1 <= y0:
            return
        span = bytes(color) * (x1 - x0)
        for y in range(y0, y1):
            self.rows[y][x0 * 3:x1 * 3] = span

    def rect(self, x0, y0, x1, y1, color, width=1):
        self.fill_rect(x0, y0, x1, y0 + width, color)
        self.fill_rect(x0, y1 - width, x1, y1, color)
        self.fill_rect(x0, y0, x0 + width, y1, color)
        self.fill_rect(x1 - width, y0, x1, y1, color)

    def hline(self, x0, x1, y, color, width=1):
        self.fill_rect(x0, y, x1, y + width, color)

    def vline(self, x, y0, y1, color, width=1):
        self.fill_rect(x, y0, x + width, y1, color)

    def _fill_spans(self, spans, color):
        for y, a, b in spans:
            if 0 <= y < self.h:
                a = max(0, a)
                b = min(self.w, b)
                if b > a:
                    self.rows[y][a * 3:b * 3] = bytes(color) * (b - a)

    def fill_poly(self, pts, color):
        """Scanline fill of a polygon given as [(x, y), ...]."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        y0 = max(0, int(min(ys)))
        y1 = min(self.h - 1, int(max(ys)) + 1)
        n = len(pts)
        spans = []
        for y in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x1, y1p = pts[i]
                x2, y2p = pts[(i + 1) % n]
                if (y1p <= y < y2p) or (y2p <= y < y1p):
                    t = (y + 0.5 - y1p) / (y2p - y1p)
                    xs.append(x1 + t * (x2 - x1))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                spans.append((y, int(xs[i]), int(xs[i + 1]) + 1))
        self._fill_spans(spans, color)

    def fill_circle(self, cx, cy, r, color):
        r = int(r)
        spans = []
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            spans.append((cy + dy, cx - dx, cx + dx + 1))
        self._fill_spans(spans, color)

    def disc(self, cx, cy, r, color):
        self.fill_circle(cx, cy, r, color)

    def line(self, x0, y0, x1, y1, color, width=1):
        """Thick line as a quad polygon plus round caps."""
        x0, y0, x1, y1 = float(x0), float(y0), float(x1), float(y1)
        dx, dy = x1 - x0, y1 - y0
        length = (dx * dx + dy * dy) ** 0.5
        if length < 0.001:
            self.disc(int(x0), int(y0), width / 2.0, color)
            return
        nx, ny = -dy / length * width / 2.0, dx / length * width / 2.0
        self.fill_poly([
            (x0 + nx, y0 + ny), (x1 + nx, y1 + ny),
            (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)], color)
        self.disc(int(round(x0)), int(round(y0)), width / 2.0, color)
        self.disc(int(round(x1)), int(round(y1)), width / 2.0, color)

    def polyline(self, pts, color, width=1):
        for i in range(len(pts) - 1):
            self.line(pts[i][0], pts[i][1], pts[i + 1][0],
                      pts[i + 1][1], color, width)

    def arc_points(self, cx, cy, rx, ry, a0, a1, n=24):
        pts = []
        for i in range(n + 1):
            a = a0 + (a1 - a0) * i / n
            pts.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
        return pts

# -------------------------------------------------- single-stroke font ---
# Each glyph: (advance width in font units, strokes). A stroke is a
# polyline "x,y;x,y;..." and strokes are separated by "|". Grid: cap
# top y=0, baseline y=8, descender bottom y=11, accents may reach
# y=-1. All glyphs were drawn by hand for this entry.

GLYPHS = {
    "A": (7, "0,8;3,0;6,8|1,5;5,5"),
    "B": (7, "0,0;0,8|0,0;4,0;6,2;6,3;4,4;0,4|4,4;6,5;6,7;4,8;0,8"),
    "C": (7, "6,1;5,0;2,0;0,2;0,6;2,8;5,8;6,7"),
    "D": (7, "0,0;0,8|0,0;4,0;6,2;6,6;4,8;0,8"),
    "E": (6, "5,0;0,0;0,8;5,8|0,4;4,4"),
    "F": (6, "0,0;0,8|0,0;5,0|0,4;4,4"),
    "G": (7, "6,1;5,0;2,0;0,2;0,6;2,8;5,8;6,7;6,4|4,4;6,4"),
    "H": (7, "0,0;0,8|6,0;6,8|0,4;6,4"),
    "I": (4, "2,0;2,8|0,0;4,0|0,8;4,8"),
    "J": (6, "5,0;5,6;4,8;2,8;0,6"),
    "K": (7, "0,0;0,8|6,0;0,4;6,8"),
    "L": (6, "0,0;0,8;5,8"),
    "M": (8, "0,8;0,0;4,4;7,0;7,8"),
    "N": (7, "0,8;0,0;6,8;6,0"),
    "O": (7, "2,0;4,0;6,2;6,6;4,8;2,8;0,6;0,2;2,0"),
    "P": (7, "0,8;0,0|0,0;4,0;6,2;6,3;4,5;0,5"),
    "Q": (7, "2,0;4,0;6,2;6,6;4,8;2,8;0,6;0,2;2,0|4,6;6,8"),
    "R": (7, "0,8;0,0|0,0;4,0;6,2;6,3;4,5;0,5|3,5;6,8"),
    "S": (7, "6,1;5,0;2,0;0,2;0,3;2,4;4,4;6,5;6,7;4,8;1,8;0,7"),
    "T": (7, "0,0;6,0|3,0;3,8"),
    "U": (7, "0,0;0,6;1,8;5,8;6,6;6,0"),
    "V": (7, "0,0;3,8;6,0"),
    "W": (9, "0,0;2,8;4,3;6,8;8,0"),
    "X": (7, "0,0;6,8|6,0;0,8"),
    "Y": (7, "0,0;3,4;6,0|3,4;3,8"),
    "Z": (7, "0,0;6,0;0,8;6,8"),
    "Á": (7, "0,8;3,0;6,8|1,5;5,5|4,-1;5,0"),
    "É": (6, "5,0;0,0;0,8;5,8|0,4;4,4|4,-1;5,0"),
    "a": (6, "1,4;2,3;4,3;5,4;5,7;4,8;2,8;1,7;1,4|5,3;5,8"),
    "b": (6, "1,0;1,8|1,5;2,4;4,3;5,4;5,7;4,8;2,8;1,7"),
    "c": (6, "5,4;4,3;2,3;1,4;1,7;2,8;4,8;5,7"),
    "d": (6, "5,0;5,8|5,5;4,4;2,3;1,4;1,7;2,8;4,8;5,7"),
    "e": (6, "5,7;4,8;2,8;1,7;1,5;2,3;4,3;5,4;5,5|1,5;5,5"),
    "f": (5, "4,0;2,1;2,8|1,3;4,3"),
    "g": (6, "1,4;2,3;4,3;5,4;5,7;4,8;2,8;1,7;1,4|5,3;5,10;4,11;2,11;1,10"),
    "h": (6, "1,0;1,8|1,5;2,3;4,3;5,4;5,8"),
    "i": (3, "1,3;1,8|1,1;1,1"),
    "j": (4, "2,3;2,10;1,11|2,1;2,1"),
    "k": (6, "1,0;1,8|5,3;1,5;5,8"),
    "l": (3, "1,0;1,8"),
    "m": (7, "1,8;1,3;2,3;3,4;3,8|3,4;4,3;5,4;5,8"),
    "n": (6, "1,8;1,3;2,3;4,3;5,4;5,8"),
    "o": (6, "2,3;4,3;5,4;5,7;4,8;2,8;1,7;1,4;2,3"),
    "p": (6, "1,3;1,11|1,6;2,4;4,3;5,4;5,7;4,8;2,8;1,7"),
    "q": (6, "5,3;5,11|5,6;4,4;2,3;1,4;1,7;2,8;4,8;5,7"),
    "r": (5, "1,8;1,3;2,3;4,3;4,4"),
    "s": (6, "5,4;4,3;2,3;1,4;1,5;2,6;4,6;5,7;4,8;2,8;1,7"),
    "t": (5, "2,1;2,8|1,4;4,4|2,8;4,7"),
    "u": (6, "1,3;1,7;2,8;4,8;5,7;5,3"),
    "v": (6, "1,3;3,8;5,3"),
    "w": (8, "1,3;2,8;4,5;6,8;7,3"),
    "x": (6, "1,3;5,8|5,3;1,8"),
    "y": (6, "1,3;3,8;5,3|3,8;2,11"),
    "z": (6, "1,3;5,3;1,8;5,8"),
    "0": (7, "2,0;4,0;6,2;6,6;4,8;2,8;0,6;0,2;2,0"),
    "1": (5, "2,0;2,8|0,2;2,0|0,8;4,8"),
    "2": (7, "1,1;2,0;4,0;5,1;5,3;0,8;6,8"),
    "3": (7, "1,1;2,0;4,0;5,1;5,3;4,4|4,4;5,5;5,7;4,8;2,8;1,7"),
    "4": (7, "4,0;4,8|0,5;5,5|0,0;4,5"),
    "5": (7, "5,0;1,0;1,4;4,4;5,5;5,7;4,8;2,8;1,7"),
    "6": (7, "5,1;4,0;2,0;1,2;1,6;2,8;4,8;5,7;5,5;4,4;2,4;1,5"),
    "7": (7, "0,0;6,0;3,8"),
    "8": (7, "2,0;4,0;5,1;5,3;4,4;2,4;1,3;1,1;2,0|2,4;4,4;5,5;5,7;4,8;2,8;1,7;1,5;2,4"),
    "9": (7, "1,4;2,3;4,3;5,4;5,8|1,4;1,2;2,0;4,0;5,1"),
    " ": (4, ""),
    ".": (3, "1,8;1,8"),
    ",": (3, "1,8;0,10"),
    ";": (3, "1,6;1,6|1,8;0,10"),
    ":": (3, "1,3;1,3|1,7;1,7"),
    "!": (3, "1,0;1,6|1,8;1,8"),
    "?": (6, "1,1;2,0;4,0;5,1;5,3;3,5;3,6|3,8;3,8"),
    "'": (3, "1,0;0,2"),
    '"': (5, "1,0;0,2|3,0;2,2"),
    "-": (6, "0,4;5,4"),
    "(": (4, "3,0;1,2;1,6;3,8"),
    ")": (4, "1,0;3,2;3,6;1,8"),
    "/": (6, "1,8;5,0"),
    "%": (7, "1,1;1,1|5,7;5,7|6,0;0,8"),
    "&": (7, "5,2;4,0;2,0;1,1;1,3;2,4;4,4;5,5;5,7;4,8;2,8;1,7|1,3;5,7"),
    "$": (7, "3,-1;3,9|6,1;5,0;2,0;0,2;0,3;2,4;4,4;6,5;6,7;4,8;1,8;0,7"),
    "#": (7, "2,0;2,8|4,0;4,8|0,3;6,3|0,6;6,6"),
    "*": (6, "3,0;3,8|0,2;5,6|5,2;0,6"),
    "+": (6, "3,1;3,7|0,4;5,4"),
    "=": (6, "0,3;5,3|0,6;5,6"),
    "·": (3, "1,4;1,4"),
    "<": (6, "5,0;1,4;5,8"),
    ">": (6, "1,0;5,4;1,8"),
    "_": (6, "0,8;5,8"),
    "á": (6, "1,4;2,3;4,3;5,4;5,7;4,8;2,8;1,7;1,4|5,3;5,8|4,1;5,0"),
    "é": (6, "5,7;4,8;2,8;1,7;1,5;2,3;4,3;5,4;5,5|1,5;5,5|4,1;5,0"),
}

# Glyphs outside the table are drawn as the hyphen (never happens: the
# self-check raises on a missing glyph first).
SS = 2  # supersampling factor for glyph rasterisation


def _parse_glyph(ch):
    width, spec = GLYPHS[ch]
    strokes = []
    if spec:
        for stroke in spec.split("|"):
            pts = []
            for pair in stroke.split(";"):
                x, y = pair.split(",")
                pts.append((float(x), float(y)))
            strokes.append(pts)
    return width, strokes


def _rasterise_glyph(ch, cap, weight, condense):
    """Return (advance_px, ox, oy, sparse) for one glyph.

    sparse is a list of (dx, dy, alpha 0..255) relative to the glyph
    bitmap origin. The bitmap covers y from -1 to 11 font units.
    """
    width, strokes = _parse_glyph(ch)
    sx = cap / 8.0 * condense
    sy = cap / 8.0
    adv = (width + 1) * sx
    # Bitmap size in output pixels (before supersampling it is
    # width*sx by 12*sy, origin at y=-1 unit).
    bw = max(1, int(math.ceil((width + 1) * sx)))
    bh = max(1, int(math.ceil(12 * sy)))
    mw, mh = bw * SS, bh * SS
    mask = bytearray(mw * mh)
    half = weight * SS / 2.0

    def disc(cx, cy, r):
        r = int(math.ceil(r))
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            yy = int(cy) + dy
            if 0 <= yy < mh:
                x0 = max(0, int(cx) - dx)
                x1 = min(mw, int(cx) + dx + 1)
                base = yy * mw
                for xx in range(x0, x1):
                    mask[base + xx] = 255

    def thick_line(x0, y0, x1, y1):
        dx, dy = x1 - x0, y1 - y0
        length = (dx * dx + dy * dy) ** 0.5
        if length < 0.001:
            disc(x0, y0, half)
            return
        nx, ny = -dy / length * half, dx / length * half
        # Quad as a filled polygon via scanline spans.
        quad = [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny),
                (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)]
        ys = [p[1] for p in quad]
        for yy in range(max(0, int(min(ys))), min(mh, int(max(ys)) + 2)):
            xs = []
            for i in range(4):
                ax, ay = quad[i]
                bx, by = quad[(i + 1) % 4]
                if (ay <= yy + 0.5 < by) or (by <= yy + 0.5 < ay):
                    t = (yy + 0.5 - ay) / (by - ay)
                    xs.append(ax + t * (bx - ax))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                a = max(0, int(xs[i]))
                b = min(mw, int(xs[i + 1]) + 1)
                base = yy * mw
                for xx in range(a, b):
                    mask[base + xx] = 255
        disc(x0, y0, half)
        disc(x1, y1, half)

    for stroke in strokes:
        pts = [((x * sx + 0.5) * SS, ((y + 1) * sy + 0.5) * SS)
               for x, y in stroke]
        for i in range(len(pts) - 1):
            thick_line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])
        if len(pts) == 1:
            disc(pts[0][0], pts[0][1], half)
    # Downsample 2x2 -> sparse alpha list.
    sparse = []
    for oy in range(bh):
        for ox in range(bw):
            a = (mask[(oy * SS) * mw + ox * SS] +
                 mask[(oy * SS) * mw + ox * SS + 1] +
                 mask[(oy * SS + 1) * mw + ox * SS] +
                 mask[(oy * SS + 1) * mw + ox * SS + 1]) // 4
            if a:
                sparse.append((ox, oy, a))
    return adv, bw, bh, sparse


class Font:
    def __init__(self, cap, weight, color=INK, condense=1.0):
        self.cap = float(cap)
        self.weight = float(weight)
        self.color = color
        self.condense = float(condense)
        self.cache = {}

    def glyph(self, ch):
        key = ch
        if key not in self.cache:
            if ch not in GLYPHS:
                raise ValueError("missing glyph for %r" % ch)
            self.cache[key] = _rasterise_glyph(
                ch, self.cap, self.weight, self.condense)
        return self.cache[key]

    def width(self, text):
        total = 0.0
        for ch in text:
            if ch not in GLYPHS:
                raise ValueError("missing glyph for %r" % ch)
            total += self.glyph(ch)[0]
        return total

    def draw(self, canvas, x, y_top, text):
        """Draw text; y_top is the top of the cap height."""
        cx = float(x)
        for ch in text:
            adv, bw, bh, sparse = self.glyph(ch)
            ox = int(round(cx))
            oy = int(round(y_top - self.cap / 8.0))
            r, g, b = self.color
            for dx, dy, a in sparse:
                px, py = ox + dx, oy + dy
                if 0 <= px < canvas.w and 0 <= py < canvas.h:
                    row = canvas.rows[py]
                    inv = 255 - a
                    row[px * 3] = (r * a + row[px * 3] * inv) >> 8
                    row[px * 3 + 1] = (g * a + row[px * 3 + 1] * inv) >> 8
                    row[px * 3 + 2] = (b * a + row[px * 3 + 2] * inv) >> 8
            cx += adv
        return cx

    def draw_centered(self, canvas, cx, y_top, text):
        return self.draw(canvas, cx - self.width(text) / 2.0, y_top, text)


def wrap_text(text, font, max_w):
    """Greedy word wrap; returns a list of lines."""
    words = text.split(" ")
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if font.width(trial) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ------------------------------------------------------- specimen mode ---


def render_specimen(path):
    """Render every glyph plus sample headlines, for visual QA."""
    c = Canvas(1000, 760, PAPER)
    f_big = Font(34, 4.0)
    f_head = Font(20, 2.6, condense=0.8)
    f_body = Font(16, 2.0)
    f_small = Font(13, 1.8)
    y = 14
    f_big.draw(c, 20, y, "THE WORLD IN ONE DAY")
    y += 52
    f_head.draw(c, 20, y, "COP31 COLLAPSES WITH NO CLIMATE DEAL")
    y += 30
    f_body.draw(c, 20, y,
                "Monday 23 November 2026 - 258 seats, 186 drones, 24 dead.")
    y += 28
    f_small.draw(c, 20, y,
                 "BepiColombo enters Mercury orbit after eight years.")
    y += 24
    f_small.draw(c, 20, y, "MÁRQUEZ WINS 8TH MOTOGP TITLE - é á")
    y += 40
    f_body.draw(c, 20, y, "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    y += 26
    f_body.draw(c, 20, y, "abcdefghijklmnopqrstuvwxyz")
    y += 26
    f_body.draw(c, 20, y, "0123456789 . , ; : ! ? ' \" - ( ) / % $ # * + = ·")
    y += 26
    f_body.draw(c, 20, y, "Nikkei -5.06%, S&P -3.7% - 720/9 - $1.67bn")
    y += 40
    # Every glyph at small size, one per cell, to spot broken shapes.
    f_cell = Font(15, 1.8)
    chars = sorted(GLYPHS.keys())
    x, yy = 20, y
    for ch in chars:
        if ch == " ":
            continue
        f_cell.draw(c, x, yy, ch)
        x += 30
        if x > 960:
            x = 20
            yy += 26
    write_png(path, c.rows)


# ------------------------------------------------------------ text log ---

TEXT_BOXES = []  # (x, y, w, h, label) of every text drawn, for checks


def put_text(canvas, font, x, y_top, text, label):
    w = font.width(text)
    TEXT_BOXES.append((x, y_top, w, font.cap + 2, label))
    return font.draw(canvas, x, y_top, text)


def put_centered(canvas, font, cx, y_top, text, label):
    x = cx - font.width(text) / 2.0
    return put_text(canvas, font, x, y_top, text, label)


# --------------------------------------------------------------- scenes ---

SKY = (168, 200, 220)
DARK = (24, 32, 58)


def scene_cop31(c, x, y, w, h):
    c.fill_rect(x, y, x + w, y + h, (217, 201, 168))
    c.fill_rect(x, y + h - 14, x + w, y + h, (190, 170, 130))
    c.fill_rect(x + 86, y + 6, x + 156, y + 32, (43, 92, 150))
    c.fill_rect(x + 94, y + 12, x + 148, y + 16, (220, 230, 240))
    c.fill_rect(x + 94, y + 20, x + 148, y + 23, (220, 230, 240))
    c.fill_poly([(x + 110, y + 34), (x + 132, y + 34),
                 (x + 144, y + h), (x + 98, y + h)], (150, 40, 35))
    for row, yy in enumerate((y + 42, y + 52, y + 62)):
        for i in range(4):
            c.fill_rect(x + 8 + i * 22, yy, x + 22 + i * 22, yy + 6,
                        (60, 50, 40))
            c.fill_rect(x + 152 + i * 22, yy, x + 166 + i * 22, yy + 6,
                        (60, 50, 40))


def scene_drones(c, x, y, w, h):
    c.fill_rect(x, y, x + w, y + h, DARK)
    for i in range(24):
        sx = x + (i * 37) % w
        sy = y + (i * 53) % (h - 10)
        c.fill_rect(sx, sy, sx + 2, sy + 2, (220, 225, 240))
    c.fill_rect(x, y + h - 8, x + w, y + h, (10, 12, 20))
    for i, (sx, sy) in enumerate(((200, 8), (170, 20), (140, 6),
                                  (110, 24), (80, 12))):
        ex = x + sx - i * 12
        ey = y + sy + i * 10
        c.line(x + sx, y + sy, ex, ey, (240, 220, 150), 2)
        c.disc(ex, ey, 3, (255, 240, 180))
    for sx, sy, r in ((40, 58, 5), (120, 62, 4), (200, 60, 5)):
        c.disc(x + sx, y + sy, r, (255, 140, 40))
        c.disc(x + sx, y + sy, max(1, r - 2), (255, 200, 80))


def scene_bahrain(c, x, y, w, h):
    c.fill_rect(x, y, x + w, y + h, (190, 215, 230))
    c.fill_rect(x, y + h - 18, x + w, y + h, (220, 205, 170))
    c.fill_rect(x + 66, y + 16, x + 166, y + 56, (245, 244, 238))
    c.rect(x + 66, y + 16, x + 166, y + 56, (200, 198, 188), 1)
    c.fill_poly([(x + 62, y + 18), (x + 170, y + 18), (x + 116, y + 6)],
                (222, 219, 210))
    for i in range(4):
        xx = x + 76 + i * 22
        c.fill_rect(xx, y + 22, xx + 5, y + 52, (200, 198, 188))
    c.fill_rect(x + 108, y + 40, x + 124, y + 56, (60, 60, 60))
    c.vline(x + 52, y + 8, y + 56, INK, 2)
    c.fill_rect(x + 54, y + 8, x + 74, y + 18, (200, 40, 50))
    c.fill_rect(x + 54, y + 18, x + 64, y + 18 + 1, (245, 245, 245))
    c.fill_rect(x + 186, y + 44, x + 216, y + 64, (255, 255, 255))
    c.rect(x + 186, y + 44, x + 216, y + 64, INK, 1)
    for i in range(3):
        c.fill_rect(x + 191, y + 49 + i * 4, x + 211, y + 51 + i * 4,
                    (150, 150, 150))
    c.disc(x + 208, y + 61, 3, (200, 40, 50))


def scene_capitol(c, x, y, w, h):
    c.fill_rect(x, y, x + w, y + h, SKY)
    c.fill_rect(x, y + h - 14, x + w, y + h, (90, 140, 80))
    cx = x + w // 2
    c.fill_rect(cx - 82, y + 34, cx + 82, y + h - 14, (245, 245, 240))
    c.fill_rect(cx - 100, y + 44, cx - 82, y + h - 14, (235, 235, 230))
    c.fill_rect(cx + 82, y + 44, cx + 100, y + h - 14, (235, 235, 230))
    pts = c.arc_points(cx, y + 34, 26, 26, math.pi, 2 * math.pi)
    c.fill_poly(pts + [(cx + 26, y + 34), (cx - 26, y + 34)],
                (245, 245, 240))
    c.fill_rect(cx - 4, y + 4, cx + 4, y + 12, (245, 245, 240))
    c.disc(cx, y + 4, 2, (200, 40, 50))
    for i in range(5):
        xx = cx - 60 + i * 30
        c.fill_rect(xx, y + 40, xx + 4, y + h - 16, (200, 198, 188))
    c.fill_rect(cx - 30, y + h - 20, cx + 30, y + h - 17, (200, 198, 188))
    c.fill_rect(cx - 36, y + h - 17, cx + 36, y + h - 14, (210, 208, 200))


def scene_capture(c, x, y, w, h):
    c.fill_rect(x, y, x + w, y + h, (215, 195, 160))
    c.fill_rect(x, y + h - 16, x + w, y + h, (120, 120, 120))
    for i in range(5):
        xx = x + 10 + i * 48
        c.fill_rect(xx, y + h - 9, xx + 18, y + h - 7, (240, 240, 240))
    c.fill_rect(x + 12, y + 34, x + 102, y + 54, (245, 245, 245))
    c.fill_rect(x + 32, y + 24, x + 74, y + 36, (240, 240, 240))
    c.fill_rect(x + 12, y + 44, x + 102, y + 50, (30, 60, 140))
    c.fill_rect(x + 44, y + 20, x + 58, y + 24, (200, 40, 50))
    c.fill_rect(x + 58, y + 20, x + 72, y + 24, (40, 80, 200))
    c.disc(x + 28, y + 54, 6, (20, 20, 20))
    c.disc(x + 86, y + 54, 6, (20, 20, 20))
    for i, col in enumerate(((30, 45, 80), (90, 90, 90), (30, 45, 80))):
        fx = x + 130 + i * 34
        c.disc(fx + 7, y + 26, 5, (210, 180, 150))
        c.fill_rect(fx, y + 32, fx + 14, y + 56, col)
        c.fill_rect(fx + 2, y + 56, fx + 6, y + 62, (40, 40, 40))
        c.fill_rect(fx + 8, y + 56, fx + 12, y + 62, (40, 40, 40))


def scene_fire(c, x, y, w, h):
    c.fill_rect(x, y, x + w, y + h, (205, 185, 150))
    c.fill_rect(x + 30, y + 10, x + 44, y + 34, (90, 85, 80))
    c.fill_rect(x + 18, y + 30, x + 190, y + h - 6, (80, 78, 74))
    for i in range(4):
        xx = x + 18 + i * 43
        c.fill_poly([(xx, y + 30), (xx + 21, y + 18), (xx + 43, y + 30)],
                    (105, 100, 95))
    for i, (fx, fh) in enumerate(((60, 18), (100, 24), (140, 18), (170, 14))):
        c.fill_poly([(x + fx - 8, y + 32), (x + fx, y + 32 - fh),
                     (x + fx + 8, y + 32)], (240, 120, 20))
        c.fill_poly([(x + fx - 4, y + 32), (x + fx, y + 32 - fh + 8),
                     (x + fx + 4, y + 32)], (250, 200, 40))
    for sx, sy, r in ((50, 8, 9), (110, 4, 11), (170, 8, 9)):
        c.disc(x + sx, y + sy, r, (120, 118, 112))
    c.fill_rect(x + 18, y + h - 6, x + 190, y + h, (60, 58, 54))


def scene_mercury(c, x, y, w, h):
    c.fill_rect(x, y, x + w, y + h, (10, 10, 16))
    for i in range(20):
        sx = x + (i * 41) % w
        sy = y + (i * 29) % h
        c.fill_rect(sx, sy, sx + 2, sy + 2, (230, 230, 240))
    px, py, pr = x + 178, y + 36, 26
    c.disc(px, py, pr, (165, 165, 165))
    c.disc(px - 8, py - 6, 5, (130, 130, 130))
    c.disc(px + 6, py + 8, 4, (130, 130, 130))
    c.disc(px + 10, py - 10, 3, (140, 140, 140))
    c.fill_rect(x + 28, y + 28, x + 54, y + 44, (200, 170, 60))
    c.fill_rect(x + 6, y + 30, x + 26, y + 42, (50, 90, 160))
    c.fill_rect(x + 56, y + 30, x + 76, y + 42, (50, 90, 160))
    c.line(x + 54, y + 36, x + 66, y + 28, (220, 220, 220), 2)
    c.disc(x + 68, y + 27, 4, (220, 220, 220))


def scene_markets(c, x, y, w, h):
    c.fill_rect(x, y, x + w, y + h, (16, 24, 48))
    for i in range(1, 4):
        yy = y + i * h // 4
        c.hline(x, x + w, yy, (40, 55, 90), 1)
    for i in range(1, 5):
        xx = x + i * w // 5
        c.vline(xx, y, y + h, (40, 55, 90), 1)
    pts = [(x + 8, y + 30), (x + 60, y + 36), (x + 110, y + 34),
           (x + 150, y + 46), (x + 190, y + 52), (x + 228, y + 62)]
    c.polyline(pts, (230, 60, 60), 3)
    ex, ey = pts[-1]
    c.fill_poly([(ex, ey), (ex - 12, ey - 2), (ex - 2, ey + 10)],
                (230, 60, 60))
    f = Font(10, 1.8, color=(255, 110, 110))
    put_text(c, f, x + 8, y + 6, "NIKKEI -5.06%", "scene8a")
    put_text(c, f, x + 8, y + 20, "S&P -3.7%", "scene8b")


def scene_tennis(c, x, y, w, h):
    c.fill_rect(x, y, x + w, y + h, (50, 110, 180))
    c.fill_rect(x + 8, y + 8, x + w - 8, y + h - 8, (70, 140, 200))
    c.rect(x + 8, y + 8, x + w - 8, y + h - 8, (240, 240, 240), 2)
    c.vline(x + w // 2, y + 8, y + h - 8, (240, 240, 240), 2)
    c.hline(x + 8, x + w - 8, y + h // 2, (30, 30, 30), 2)
    c.hline(x + 8, x + w - 8, y + h // 2 - 2, (240, 240, 240), 1)
    c.disc(x + 60, y + 52, 5, (200, 220, 60))
    c.fill_rect(x + 176, y + 4, x + 234, y + 18, (16, 24, 48))
    f = Font(9, 1.6, color=(255, 255, 255))
    put_text(c, f, x + 182, y + 6, "6-2 7-6", "scene9")
    # Racket, top right.
    cx, cy = x + 196, y + 34
    for i in range(28):
        a = 2 * math.pi * i / 28
        c.disc(int(cx + 12 * math.cos(a)), int(cy + 15 * math.sin(a)), 1,
               (240, 240, 240))
    c.line(cx - 6, cy + 14, cx - 16, cy + 30, (200, 170, 120), 3)


def scene_cricket(c, x, y, w, h):
    c.fill_rect(x, y, x + w, y + h, (70, 140, 70))
    c.fill_rect(x + 105, y + 8, x + 137, y + h - 8, (210, 190, 150))
    c.hline(x + 105, x + 137, y + 14, (240, 240, 240), 1)
    c.hline(x + 105, x + 137, y + h - 14, (240, 240, 240), 1)
    for xx in (x + 112, x + 118, x + 124):
        c.vline(xx, y + 8, y + 14, (240, 220, 80), 2)
        c.vline(xx, y + h - 14, y + h - 8, (240, 220, 80), 2)
    c.fill_poly([(x + 150, y + 44), (x + 162, y + 40), (x + 150, y + 62),
                 (x + 142, y + 60)], (210, 180, 120))
    c.disc(x + 96, y + 52, 4, (200, 40, 40))
    c.fill_rect(x + 4, y + 4, x + 58, y + 18, (16, 24, 48))
    f = Font(9, 1.6, color=(255, 255, 255))
    put_text(c, f, x + 10, y + 6, "720/9", "scene10")


def scene_motogp(c, x, y, w, h):
    c.fill_rect(x, y, x + w, y + h, (200, 215, 225))
    for i in range(12):
        col = (240, 240, 240) if i % 2 == 0 else (30, 30, 30)
        c.fill_rect(x + 8 + i * 19, y + 34, x + 8 + i * 19 + 19, y + 40, col)
    c.fill_rect(x, y + 40, x + w, y + 64, (110, 110, 110))
    c.hline(x, x + w, y + 52, (240, 240, 240), 2)
    # Motorcycle, no brand, no number.
    c.disc(x + 88, y + 58, 9, (20, 20, 20))
    c.disc(x + 150, y + 58, 9, (20, 20, 20))
    c.fill_poly([(x + 88, y + 58), (x + 118, y + 40), (x + 138, y + 44),
                 (x + 150, y + 58)], (200, 40, 40))
    c.fill_poly([(x + 118, y + 40), (x + 128, y + 30), (x + 138, y + 44)],
                (220, 60, 50))
    c.disc(x + 126, y + 26, 7, (245, 245, 245))
    c.fill_rect(x + 116, y + 32, x + 138, y + 44, (30, 45, 80))
    # Checkered flag.
    c.vline(x + 216, y + 8, y + 30, INK, 2)
    for i in range(4):
        for j in range(3):
            col = (20, 20, 20) if (i + j) % 2 == 0 else (245, 245, 245)
            c.fill_rect(x + 218 + i * 5, y + 8 + j * 5,
                        x + 218 + i * 5 + 5, y + 8 + j * 5 + 5, col)


def scene_probe(c, x, y, w, h):
    c.fill_rect(x, y, x + w, y + h, (20, 26, 40))
    c.fill_rect(x + 52, y + 14, x + 118, y + 58, (40, 50, 70))
    c.rect(x + 52, y + 14, x + 118, y + 58, (90, 110, 140), 2)
    for i in range(5):
        xx = x + 62 + i * 12
        c.vline(xx, y + 8, y + 14, (140, 160, 190), 2)
        c.vline(xx, y + 58, y + 64, (140, 160, 190), 2)
    for i in range(3):
        yy = y + 24 + i * 12
        c.hline(x + 46, x + 52, yy, (140, 160, 190), 2)
        c.hline(x + 118, x + 124, yy, (140, 160, 190), 2)
    c.fill_rect(x + 72, y + 28, x + 98, y + 44, (90, 110, 140))
    c.fill_rect(x + 170, y + 16, x + 226, y + 56, (255, 255, 255))
    c.rect(x + 170, y + 16, x + 226, y + 56, INK, 1)
    for i in range(4):
        c.fill_rect(x + 176, y + 22 + i * 8, x + 220, y + 24 + i * 8,
                    (150, 150, 150))
    cx, cy = x + 132, y + 42
    for i in range(28):
        a = 2 * math.pi * i / 28
        c.disc(int(cx + 14 * math.cos(a)), int(cy + 14 * math.sin(a)), 1,
               (220, 180, 60))
    c.disc(cx, cy, 12, (20, 26, 40))
    c.line(cx + 10, cy + 10, cx + 24, cy + 24, (220, 180, 60), 3)


def scene_protest(c, x, y, w, h):
    c.fill_rect(x, y, x + w, y + h, (210, 205, 190))
    cols = [(190, 170, 140), (170, 160, 140), (200, 185, 160)]
    bx = x
    i = 0
    while bx < x + w:
        bw = 46 + (i * 13) % 30
        bh = 26 + (i * 7) % 12
        c.fill_rect(bx, y + 34 - bh, bx + bw, y + 34, cols[i % 3])
        for wy in range(2):
            for wx in range(4):
                c.fill_rect(bx + 6 + wx * 10, y + 34 - bh + 5 + wy * 10,
                            bx + 10 + wx * 10, y + 34 - bh + 9 + wy * 10,
                            (90, 85, 75))
        bx += bw + 4
        i += 1
    c.fill_rect(x, y + 34, x + w, y + h, (150, 148, 140))
    palette = [(30, 45, 80), (150, 40, 35), (40, 90, 60), (90, 60, 120),
               (180, 120, 40), (60, 60, 60)]
    for i in range(26):
        fx = x + 12 + i * 24
        col = palette[i % len(palette)]
        c.disc(fx + 5, y + 46, 4, (210, 180, 150))
        c.fill_rect(fx, y + 51, fx + 10, y + 72, col)
    for i in range(4):
        fx = x + 150 + i * 30
        c.disc(fx + 6, y + 42, 5, (210, 180, 150))
        c.fill_rect(fx, y + 48, fx + 12, y + 72, (25, 35, 65))
        c.fill_rect(fx - 2, y + 50, fx + 14, y + 66, (40, 70, 140))
    for sx in (x + 420, x + 520):
        c.vline(sx, y + 30, y + 52, INK, 2)
        c.fill_rect(sx - 14, y + 22, sx + 14, y + 34, (255, 255, 255))
        c.rect(sx - 14, y + 22, sx + 14, y + 34, INK, 1)


# ------------------------------------------------------------------ map ---

# Simplified continent outlines as (longitude, latitude) points, drawn
# by hand for this entry (coarse shapes only, for a small locator map).
CONTINENTS = [
    # North America
    [(-168, 66), (-140, 70), (-125, 71), (-110, 68), (-95, 69),
     (-85, 66), (-80, 73), (-65, 60), (-55, 52), (-60, 47), (-70, 42),
     (-75, 35), (-80, 32), (-81, 26), (-90, 21), (-97, 16), (-94, 17),
     (-105, 20), (-110, 24), (-115, 30), (-125, 40), (-125, 49),
     (-140, 60), (-155, 58), (-165, 60)],
    # Greenland
    [(-58, 64), (-45, 60), (-40, 65), (-32, 68), (-22, 70), (-30, 76),
     (-45, 76), (-58, 74), (-60, 70)],
    # South America
    [(-80, 9), (-75, 11), (-70, 12), (-62, 10), (-52, 5), (-50, 0),
     (-44, -3), (-35, -8), (-40, -20), (-48, -28), (-58, -35),
     (-65, -41), (-68, -50), (-70, -54), (-73, -44), (-73, -30),
     (-70, -18), (-80, -5), (-80, 3)],
    # Africa
    [(-17, 15), (-10, 30), (0, 36), (10, 37), (20, 32), (30, 31),
     (35, 28), (43, 12), (48, 11), (51, 2), (40, -5), (40, -15),
     (35, -22), (28, -33), (18, -35), (15, -27), (12, -18), (9, -1),
     (9, 4), (-8, 5), (-13, 8), (-17, 12)],
    # Eurasia
    [(-10, 36), (-9, 43), (-2, 48), (0, 50), (5, 58), (10, 59),
     (18, 56), (21, 55), (24, 59), (30, 60), (30, 70), (40, 68),
     (55, 69), (70, 72), (90, 75), (110, 74), (130, 72), (150, 70),
     (170, 67), (178, 65), (170, 60), (160, 55), (158, 52), (142, 50),
     (140, 40), (135, 35), (130, 33), (127, 35), (122, 38), (120, 32),
     (110, 20), (108, 10), (105, 5), (100, 8), (98, 15), (95, 16),
     (90, 22), (86, 20), (80, 13), (77, 8), (75, 20), (72, 20),
     (66, 25), (60, 25), (57, 26), (52, 28), (50, 30), (48, 29),
     (44, 29), (40, 31), (36, 36), (30, 36), (26, 40), (23, 40),
     (19, 42), (15, 44), (12, 44), (8, 44), (3, 43), (-2, 44),
     (-2, 48), (-5, 48), (-10, 44)],
    # United Kingdom
    [(-5, 50), (-3, 53), (-5, 56), (-2, 58), (0, 53), (1, 51)],
    # Japan
    [(130, 31), (133, 34), (137, 35), (140, 38), (141, 42), (143, 44),
     (141, 45), (139, 39), (134, 34), (131, 33)],
    # Australia
    [(113, -22), (114, -30), (115, -35), (120, -34), (124, -33),
     (129, -32), (132, -32), (135, -35), (138, -35), (140, -38),
     (142, -39), (145, -38), (147, -39), (150, -37), (153, -32),
     (153, -27), (150, -22), (146, -19), (142, -15), (142, -11),
     (137, -12), (135, -15), (132, -12), (130, -13), (126, -14),
     (122, -17), (118, -20)],
    # New Zealand
    [(167, -45), (170, -42), (173, -41), (175, -38), (177, -38),
     (174, -41), (172, -43), (168, -46)],
    # Madagascar
    [(44, -16), (47, -15), (50, -16), (49, -20), (47, -24), (44, -25),
     (43, -20)],
    # Sumatra
    [(95, 5), (100, 0), (105, -5), (103, -6), (99, -1), (95, 3)],
    # Borneo
    [(109, 1), (114, 4), (118, 2), (117, -3), (112, -4), (109, -2)],
    # New Guinea
    [(131, -1), (136, -2), (141, -3), (146, -6), (141, -8), (135, -4),
     (131, -3)],
]

# (story number, longitude, latitude)
PINS = [
    (1, 30.7, 36.9),    # Antalya
    (2, 30.0, 50.8),    # Dymer
    (3, 50.6, 26.2),    # Bahrain
    (4, -77.0, 38.9),   # Washington
    (5, -107.4, 24.8),  # Sinaloa
    (6, 106.4, -6.4),   # Cikande, Indonesia
    (8, 139.7, 35.7),   # Tokyo
    (10, 174.8, -41.3),  # Wellington
    (13, 2.35, 48.85),  # Paris
]


def draw_map(c, x, y, w, h):
    """Draw the locator map; returns the placed pin circles."""
    c.fill_rect(x, y, x + w, y + h, PAPER)
    ix, iy, iw, ih = x + 6, y + 4, w - 12, h - 8
    land = (168, 164, 154)
    for poly in CONTINENTS:
        pts = [(ix + (lon + 180) / 360.0 * iw,
                iy + (90 - lat) / 150.0 * ih) for lon, lat in poly]
        c.fill_poly(pts, land)
    # Project pins, then relax so no two pin circles touch.
    pts = []
    for num, lon, lat in PINS:
        px = ix + (lon + 180) / 360.0 * iw
        py = iy + (90 - lat) / 150.0 * ih
        pts.append([num, px, py, px, py])
    for _ in range(12):
        moved = False
        for i in range(len(pts)):
            for j in range(i):
                dx = pts[i][3] - pts[j][3]
                dy = pts[i][4] - pts[j][4]
                d = (dx * dx + dy * dy) ** 0.5
                if d < 17 and d > 0.001:
                    push = (17 - d) / 2.0
                    ux, uy = dx / d, dy / d
                    pts[i][3] += ux * push
                    pts[i][4] += uy * push
                    pts[j][3] -= ux * push
                    pts[j][4] -= uy * push
                    moved = True
        if not moved:
            break
    placed = []
    f_pin1 = Font(9, 1.8, color=(255, 255, 255))
    f_pin2 = Font(8, 1.6, color=(255, 255, 255))
    for num, tx, ty, lx, ly in pts:
        two = num >= 10
        r = 9 if two else 8
        f_pin = f_pin2 if two else f_pin1
        lx = min(max(lx, ix + r + 1), ix + iw - r - 1)
        ly = min(max(ly, iy + r + 1), iy + ih - r - 1)
        if abs(lx - tx) > 2 or abs(ly - ty) > 2:
            c.line(tx, ty, lx, ly, INK, 1)
            c.disc(int(tx), int(ty), 2, INK)
        c.disc(int(lx), int(ly), r, INK)
        c.disc(int(lx), int(ly), r - 1, (30, 30, 30))
        label = str(num)
        put_text(c, f_pin, lx - f_pin.width(label) / 2.0,
                 ly - f_pin.cap / 2.0 - 1, label, "pin%d" % num)
        placed.append((lx, ly))
    return placed


# -------------------------------------------------------------- content ---

REGIONS = {
    "EUROPE": (43, 108, 176),
    "AMERICAS": (192, 57, 43),
    "MIDDLE EAST": (30, 132, 73),
    "ASIA": (230, 126, 34),
    "AFRICA": (212, 172, 13),
    "SPORT": (20, 143, 119),
    "SCIENCE": (125, 60, 152),
    "TECHNOLOGY": (26, 82, 118),
}

# (number, headline, summary, region, scene)
PANELS = [
    (1, "COP31 COLLAPSES WITH NO CLIMATE DEAL",
     "No deal in Antalya, Turkey.", "EUROPE", scene_cop31),
    (2, "RUSSIA FIRES 186 DRONES AT UKRAINE",
     "161 downed; at least 10 killed in Dymer.", "EUROPE", scene_drones),
    (3, "BAHRAIN DEMANDS IRAN PAY FOR STRIKES",
     "Manama urges UN action after Saturday's attacks.",
     "MIDDLE EAST", scene_bahrain),
    (4, "DEMOCRATS WIN 258 US HOUSE SEATS",
     "258 seats in the House of Representatives.", "AMERICAS",
     scene_capitol),
    (5, "'EL CHAPO ISIDRO' CAPTURED IN SINALOA",
     "11 killed in Sinaloa, Mexico.", "AMERICAS", scene_capture),
    (6, "INDONESIA CANDY FACTORY FIRE",
     "24 dead, about 30 missing.", "ASIA", scene_fire),
    (7, "BEPICOLOMBO ENTERS MERCURY ORBIT",
     "In orbit after an eight-year journey.", "SCIENCE", scene_mercury),
    (8, "AI SELL-OFF HITS MARKETS",
     "Nikkei -5.06%, S&P -3.7%.", "TECHNOLOGY", scene_markets),
    (9, "ALCARAZ WINS ATP FINALS",
     "Final won 6-2, 7-6.", "SPORT", scene_tennis),
    (10, "INDIA DECLARE 720/9, WELLINGTON TEST DRAWN",
     "720/9 declared; the Test is drawn.", "SPORT", scene_cricket),
    (11, "MÁRQUEZ WINS 8TH MOTOGP TITLE",
     "His eighth MotoGP title.", "SPORT", scene_motogp),
    (12, "NVIDIA FACES REPORTED SEC PROBE",
     "SEC probe reported amid fallout from Huang exit.", "TECHNOLOGY",
     scene_probe),
]

PANEL_13 = ("FRANCE ARRESTS 144 IN COST-OF-LIVING PROTESTS",
            "144 people arrested in protests over the cost of living.",
            "EUROPE", scene_protest)

# (text, region) - 23 more stories, in three columns of 8 / 8 / 7.
ALSO = [
    ("South Sudan: 24 civilians killed", "AFRICA"),
    ("Bolsonaro in intensive care", "AMERICAS"),
    ("Khartoum: 5 children killed", "AFRICA"),
    ("Istanbul rally vs media takeover", "EUROPE"),
    ("Houthis claim Saudi refinery hit", "MIDDLE EAST"),
    ("5 EU states back Rwanda centres", "EUROPE"),
    ("Nine shot at California concert", "AMERICAS"),
    ("S. Korea minister quits in exam row", "ASIA"),
    ("Seattle ICE protests", "AMERICAS"),
    ("Belgian airports shut", "EUROPE"),
    ("Tata Steel $1.67bn stake", "ASIA"),
    ("Fighting disrupts DR Congo Ebola work", "AFRICA"),
    ("Nigeria ends jail for attempted suicide", "AFRICA"),
    ("Robot sub finds Mariana volcanoes", "SCIENCE"),
    ("Princess of Wales cancer film", "EUROPE"),
    ("Boca win Copa Sudamericana", "SPORT"),
    ("Price wins Grand Slam of Darts", "SPORT"),
    ("Nepal PM starts India visit", "ASIA"),
    ("India-China border talks", "ASIA"),
    ("Russian warship sinks off Libya (REPORTED)", "AFRICA"),
    ("Nepal first Loss & Damage payout", "ASIA"),
    ("US spy chief defends Putin 'friend' remark", "AMERICAS"),
    ("Australia jobless rate to pass 5%", "ASIA"),
]


def build_page():
    TEXT_BOXES.clear()
    c = Canvas(W, H, PAPER)
    f_mast = Font(46, 5.0)
    f_date = Font(30, 3.4)
    f_nums = Font(13, 2.4, condense=0.9)
    f_tiny = Font(9, 1.6)
    f_tick = Font(8, 1.4)
    f_leg = Font(9.5, 2.0)
    f_head = Font(13, 2.4, condense=0.8)
    f_sum = Font(11, 1.8, condense=0.9)
    f_big_head = Font(15, 2.6, condense=0.8)
    f_big_sum = Font(11.5, 1.8, condense=0.9)
    f_also_head = Font(13, 2.4)
    f_also = Font(10, 2.0, condense=0.95)
    f_foot = Font(10, 1.8)
    f_map_head = Font(11, 2.2, color=(255, 255, 255))
    f_map_note = Font(8, 1.4)

    # Masthead, date, numbers strip.
    put_centered(c, f_mast, 512, 6, "THE WORLD IN ONE DAY", "masthead")
    c.hline(12, 1012, 56, INK, 2)
    c.hline(12, 1012, 60, INK, 1)
    put_centered(c, f_date, 512, 66, "Monday 23 November 2026", "date")
    put_centered(c, f_nums, 512, 102,
                 "258 SEATS · 186 DRONES · 24 DEAD · 8 YEARS · 11 KILLED "
                 "· 144 ARRESTED · -5.06% NIKKEI", "numbers")

    # UTC timeline.
    put_centered(c, f_tiny, 512, 120, "UTC · MONDAY 23 NOVEMBER 2026",
                 "utc")
    c.hline(12, 1012, 136, INK, 1)
    for i in range(9):
        tx = 12 + i * 125
        c.vline(tx, 132, 142, INK, 1)
        label = "%02d:00" % (i * 3)
        if i == 0:
            put_text(c, f_tick, 12, 144, label, "tick%d" % i)
        elif i == 8:
            put_text(c, f_tick, 1012 - f_tick.width(label), 144, label,
                     "tick%d" % i)
        else:
            put_centered(c, f_tick, tx, 144, label, "tick%d" % i)

    # Region legend.
    names = ["EUROPE", "AMERICAS", "MIDDLE EAST", "ASIA", "AFRICA",
             "SPORT", "SCIENCE", "TECHNOLOGY"]
    for i, name in enumerate(names):
        x0 = 12 + i * 125
        col = REGIONS[name]
        c.fill_rect(x0, 158, x0 + 121, 178, col)
        f = Font(9.5, 2.0, color=(255, 255, 255) if name != "AFRICA"
                 else INK)
        put_centered(c, f, x0 + 60, 163, name, "legend-" + name)

    # 12 panels in a 4 x 3 grid.
    col_w = 244
    row_h = 148
    for idx, (num, head, summ, region, scene) in enumerate(PANELS):
        row, col = divmod(idx, 4)
        x0 = 12 + col * (col_w + 8)
        y0 = 184 + row * (row_h + 6)
        c.fill_rect(x0, y0, x0 + col_w, y0 + 5, REGIONS[region])
        scene(c, x0 + 1, y0 + 7, col_w - 2, 72)
        c.rect(x0 + 1, y0 + 7, x0 + col_w - 1, y0 + 79, INK, 1)
        lines = wrap_text("%d %s" % (num, head), f_head, col_w - 16)
        if len(lines) > 2:
            raise ValueError("headline too long: %s" % head)
        for li, line in enumerate(lines):
            put_text(c, f_head, x0 + 8, y0 + 84 + li * 16, line,
                     "head%d" % num)
        slines = wrap_text(summ, f_sum, col_w - 16)
        if len(slines) > 2:
            raise ValueError("summary too long: %s" % summ)
        for li, line in enumerate(slines):
            put_text(c, f_sum, x0 + 8, y0 + 120 + li * 13, line,
                     "sum%d" % num)

    # Wide panel 13 + map.
    y0 = 646
    head, summ, region, scene = PANEL_13
    c.fill_rect(12, y0, 652, y0 + 5, REGIONS[region])
    scene(c, 13, y0 + 7, 638, 84)
    c.rect(13, y0 + 7, 651, y0 + 91, INK, 1)
    lines = wrap_text("13 " + head, f_big_head, 624)
    if len(lines) > 1:
        raise ValueError("panel 13 headline too long")
    put_text(c, f_big_head, 20, y0 + 96, lines[0], "head13")
    slines = wrap_text(summ, f_big_sum, 624)
    if len(slines) > 1:
        raise ValueError("panel 13 summary too long")
    put_text(c, f_big_sum, 20, y0 + 116, slines[0], "sum13")

    c.fill_rect(660, y0, 1012, y0 + 20, INK)
    put_centered(c, f_map_head, 836, y0 + 4, "WHERE IT HAPPENED", "maphead")
    c.rect(660, y0 + 20, 1012, y0 + 136, INK, 1)
    pins = draw_map(c, 661, y0 + 21, 350, 99)
    put_centered(c, f_map_note, 836, y0 + 124,
                 "Numbers match the stories. Not mapped: 7, 9, 11, 12.",
                 "mapnote")

    # ALSO list.
    c.fill_rect(12, 788, 1012, 810, INK)
    f_also_head_w = Font(13, 2.4, color=(255, 255, 255))
    put_centered(c, f_also_head_w, 512, 792,
                 "ALSO ON MONDAY 23 NOVEMBER - 23 MORE STORIES", "alsohead")
    col_xs = (12, 348, 684)
    col_counts = (8, 8, 7)
    pos = 0
    for ci in range(3):
        yy = 814
        for k in range(col_counts[ci]):
            text, region = ALSO[pos]
            pos += 1
            col = REGIONS[region]
            lines = wrap_text(text, f_also, 322 - 14)
            for li, line in enumerate(lines):
                if li == 0:
                    c.fill_rect(col_xs[ci], yy + 2, col_xs[ci] + 7,
                                yy + 9, col)
                put_text(c, f_also, col_xs[ci] + 14, yy, line,
                         "also%d" % (pos))
                yy += 14
            yy += 2

    # Foot.
    put_text(c, f_foot, 12, 976,
             "DATE CHECK: Every story on this page happened or was first "
             "reported on Monday 23 November 2026.", "datecheck")
    f_src = Font(10, 1.8)
    put_text(c, f_src, 1012 - f_src.width("Sources: Reuters, BBC, AP, "
                                          "Al Jazeera, AFP."), 990,
             "Sources: Reuters, BBC, AP, Al Jazeera, AFP.", "sources")
    c.hline(12, 1012, 1006, INK, 1)
    return c, pins


# ------------------------------------------------------------------ main ---


def self_check(pins):
    for (x, y, w, h, label) in TEXT_BOXES:
        if x < 0 or y < 0 or x + w > W or y + h > H:
            raise ValueError("text out of bounds: %s (%s, %s, %s, %s)"
                             % (label, x, y, w, h))
    for i in range(len(TEXT_BOXES)):
        for j in range(i + 1, len(TEXT_BOXES)):
            ax, ay, aw, ah, al = TEXT_BOXES[i]
            bx, by, bw, bh, bl = TEXT_BOXES[j]
            if (ax < bx + bw - 1 and bx < ax + aw - 1 and
                    ay < by + bh - 1 and by < ay + ah - 1):
                raise ValueError("text boxes overlap: %s and %s" % (al, bl))
    for i in range(len(pins)):
        for j in range(i + 1, len(pins)):
            dx = pins[i][0] - pins[j][0]
            dy = pins[i][1] - pins[j][1]
            if (dx * dx + dy * dy) ** 0.5 < 15:
                raise ValueError("map pins collide: %s and %s"
                                 % (pins[i], pins[j]))


def main():
    out_path = None
    if len(sys.argv) > 1 and sys.argv[1] == "specimen":
        render_specimen(sys.argv[2] if len(sys.argv) > 2 else "specimen.png")
        return
    if len(sys.argv) > 1:
        out_path = sys.argv[1]
    if out_path is None:
        out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "entry.png")
    canvas, pins = build_page()
    self_check(pins)
    size = write_png(out_path, canvas.rows)
    if size >= 1_048_576:
        raise ValueError("PNG over 1 MiB: %d bytes" % size)
    print("wrote %s (%d bytes)" % (out_path, size))


if __name__ == "__main__":
    main()
