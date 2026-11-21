"""Passport spread of the Republic of Kalvera -- pure-stdlib renderer.

Draws an invented passport (data page + visa page, 1024x1024) using only
the Python standard library: a small raster canvas, an embedded 5x7
bitmap font, real ICAO 9303 check digits for the machine-readable zone,
and a PNG encoder built on zlib + struct. No third-party imports.
"""

import math
import os
import struct
import zlib

W = H = 1024

# ---------------------------------------------------------------- canvas

class Canvas:
    """A minimal RGB raster canvas backed by a bytearray."""

    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bytes(bg) * (w * h))

    def rect(self, x, y, w, h, c):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        n = len(row)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + n] = row

    def circle(self, cx, cy, r, c):
        for dy in range(-r, r + 1):
            dx = int(math.sqrt(r * r - dy * dy))
            self.rect(cx - dx, cy + dy, 2 * dx + 1, 1, c)

    def ellipse(self, cx, cy, rx, ry, c):
        if ry <= 0:
            return
        for dy in range(-ry, ry + 1):
            t = 1.0 - (dy / ry) ** 2
            dx = int(rx * math.sqrt(t)) if t > 0 else 0
            self.rect(cx - dx, cy + dy, 2 * dx + 1, 1, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        off = t // 2
        while True:
            self.rect(x - off, y - off, t, t, c)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def ring(self, cx, cy, r, c, t=3):
        steps = int(2 * math.pi * r) + 1
        off = t // 2
        for i in range(steps):
            a = 2 * math.pi * i / steps
            x = int(cx + r * math.cos(a))
            y = int(cy + r * math.sin(a))
            self.rect(x - off, y - off, t, t, c)

    def poly(self, pts, c):
        ys = [p[1] for p in pts]
        n = len(pts)
        for yy in range(min(ys), max(ys) + 1):
            xs = []
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= yy < y1) or (y1 <= yy < y0):
                    xs.append(int(x0 + (yy - y0) * (x1 - x0) / (y1 - y0)))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.rect(xs[i], yy, xs[i + 1] - xs[i] + 1, 1, c)

    def outline(self, x, y, w, h, c, t=2):
        self.rect(x, y, w, t, c)
        self.rect(x, y + h - t, w, t, c)
        self.rect(x, y, t, h, c)
        self.rect(x + w - t, y, t, h, c)

# ------------------------------------------------------------------ font
# 5x7 bitmap glyphs, rows top to bottom, '#' = ink.

FONT = {
    'A': (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'B': ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    'C': (".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."),
    'D': ("####.", "#..##", "#...#", "#...#", "#...#", "#..##", "####."),
    'E': ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    'F': ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    'G': (".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".####"),
    'H': ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'I': (".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    'J': ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    'K': ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    'L': ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    'M': ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    'N': ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    'O': (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'P': ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    'Q': (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    'R': ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    'S': (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    'T': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    'U': ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'V': ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    'W': ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#."),
    'X': ("#...#", ".#.#.", "..#..", "..#..", "..#..", ".#.#.", "#...#"),
    'Y': ("#...#", ".#.#.", "..#..", "..#..", "..#..", "..#..", "..#.."),
    'Z': ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    '0': (".###.", "#..##", "#.#.#", "#.#.#", "##..#", "#...#", ".###."),
    '1': ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    '2': (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    '3': ("#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."),
    '4': ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    '5': ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    '6': (".##..", ".#...", "#....", "####.", "#...#", "#...#", ".###."),
    '7': ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
    '8': (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    '9': (".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."),
    ' ': (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    '.': (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ',': (".....", ".....", ".....", ".....", ".##..", ".#...", "#...."),
    '/': ("....#", "...#.", "...#.", "..#..", ".#...", ".#...", "#...."),
    '-': (".....", ".....", ".....", ".###.", ".....", ".....", "....."),
    ':': (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    "'": (".#...", ".#...", "#....", ".....", ".....", ".....", "....."),
    '(': ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ')': (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    '<': ("...#.", "..#..", ".#...", "#....", ".#...", "..#..", "...#."),
    '>': (".#...", "..#..", "...#.", "....#", "...#.", "..#..", ".#..."),
}


def text_w(s, scale, tracking=None):
    if tracking is None:
        tracking = scale
    if not s:
        return 0
    return len(s) * (5 * scale + tracking) - tracking


def draw_text(cv, x, y, s, scale, c, tracking=None):
    if tracking is None:
        tracking = scale
    cx = x
    for ch in s.upper():
        g = FONT.get(ch, FONT[' '])
        for gy, row in enumerate(g):
            for gx, bit in enumerate(row):
                if bit == '#':
                    cv.rect(cx + gx * scale, y + gy * scale, scale, scale, c)
        cx += 5 * scale + tracking
    return cx


def draw_centered(cv, center_x, y, s, scale, c, tracking=None):
    x = center_x - text_w(s, scale, tracking) // 2
    return draw_text(cv, x, y, s, scale, c, tracking)


def wrap(s, max_chars):
    words = s.split()
    lines = []
    cur = ""
    for w_ in words:
        trial = (cur + " " + w_).strip()
        if len(trial) <= max_chars:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines

# ------------------------------------------------------- ICAO 9303 MRZ

_VALS = {str(d): d for d in range(10)}
_VALS.update({chr(ord('A') + i): 10 + i for i in range(26)})
_VALS['<'] = 0


def check_digit(s):
    total = 0
    for i, ch in enumerate(s):
        total += _VALS[ch] * (7, 3, 1)[i % 3]
    return str(total % 10)


def mrz_lines():
    line1 = "P<KVAVOSS<<ELENA<MARA"
    line1 = line1 + "<" * (44 - len(line1))
    doc = "KVA084173"
    body = (doc + check_digit(doc) + "KVA"
            + "910704" + check_digit("910704") + "F"
            + "340311" + check_digit("340311")
            + "<" * 14 + check_digit("<" * 14))
    comp_src = body[0:10] + body[13:20] + body[21:28] + body[28:43]
    line2 = body + check_digit(comp_src)
    return line1, line2

# ------------------------------------------------------------- drawing

DESK = (64, 56, 48)
SHADOW = (28, 24, 20)
PAGE = (243, 238, 224)
PAGE_LINE = (196, 190, 172)
GUIL = (216, 221, 231)
GUIL_R = (230, 230, 220)
INK = (38, 38, 46)
GRAY = (110, 106, 96)
NAVY = (26, 50, 96)
GOLD = (196, 158, 52)
TEAL = (24, 92, 104)
WAVE = (92, 150, 196)


def guilloche(cv, x0, x1, y0, y1, color, step=30):
    i = 0
    y = y0
    while y < y1:
        prev = None
        x = x0
        while x <= x1:
            yy = y + int(6 * math.sin(x * 0.021 + i * 0.7))
            if prev is not None:
                cv.line(prev[0], prev[1], x, yy, color, 1)
            prev = (x, yy)
            x += 6
        y += step
        i += 1


def star_pts(cx, cy, r_out, r_in):
    pts = []
    for i in range(10):
        r = r_out if i % 2 == 0 else r_in
        a = -math.pi / 2 + i * math.pi / 5
        pts.append((int(cx + r * math.cos(a)), int(cy + r * math.sin(a))))
    return pts


def coat_of_arms(cv, cx, top):
    # faint rosette rings behind the shield
    cv.ring(cx, top + 62, 78, GUIL, 1)
    cv.ring(cx, top + 62, 92, GUIL, 1)
    # shield: gold back plate, navy face
    gold = [(cx - 48, top), (cx + 48, top), (cx + 48, top + 62),
            (cx, top + 116), (cx - 48, top + 62)]
    navy = [(cx - 42, top + 6), (cx + 42, top + 6), (cx + 42, top + 60),
            (cx, top + 106), (cx - 42, top + 60)]
    cv.poly(gold, GOLD)
    cv.poly(navy, NAVY)
    # gold star in the upper field
    cv.poly(star_pts(cx, top + 36, 19, 8), GOLD)
    # three reef waves across the lower field
    for k in range(3):
        wy = top + 66 + k * 11
        prev = None
        x = cx - 32
        while x <= cx + 32:
            yy = wy + int(3 * math.sin((x - cx) * 0.16 + k * 0.9))
            if prev is not None:
                cv.line(prev[0], prev[1], x, yy, WAVE, 2)
            prev = (x, yy)
            x += 4


def portrait(cv, x, y, w, h):
    skin = (233, 196, 161)
    skin_sh = (214, 172, 134)
    hair = (82, 56, 38)
    top_c = (36, 102, 116)
    cv.rect(x, y, w, h, (172, 192, 203))
    cx = x + w // 2
    # hair mass behind the head (bob silhouette)
    cv.ellipse(cx, y + 74, 52, 58, hair)
    cv.rect(x + 14, y + 74, 22, 74, hair)
    cv.rect(x + w - 36, y + 74, 22, 74, hair)
    # shoulders / blouse
    cv.poly([(x + 18, y + h), (x + 34, y + 138), (cx, y + 124),
             (x + w - 34, y + 138), (x + w - 18, y + h)], top_c)
    # neck
    cv.rect(cx - 11, y + 104, 22, 26, skin_sh)
    # face
    cv.ellipse(cx, y + 72, 36, 46, skin)
    # fringe across the forehead
    cv.ellipse(cx, y + 34, 40, 18, hair)
    cv.rect(cx - 40, y + 30, 80, 10, hair)
    # brows, eyes, nose, mouth
    cv.line(cx - 22, y + 66, cx - 9, y + 64, hair, 2)
    cv.line(cx + 9, y + 64, cx + 22, y + 66, hair, 2)
    cv.rect(cx - 19, y + 72, 8, 3, INK)
    cv.rect(cx + 11, y + 72, 8, 3, INK)
    cv.line(cx, y + 78, cx - 2, y + 88, skin_sh, 2)
    cv.line(cx - 9, y + 98, cx + 9, y + 98, (168, 92, 88), 2)
    # frame
    cv.outline(x, y, w, h, (90, 88, 80), 2)


def signature(cv, x, y, w, c):
    prev = None
    for i in range(w):
        yy = y + int(9 * math.sin(i * 0.16) + 5 * math.sin(i * 0.05 + 1.3))
        if prev is not None:
            cv.line(prev[0], prev[1], x + i, yy, c, 2)
        prev = (x + i, yy)
    cv.line(x - 4, y + 20, x + w + 16, y + 13, c, 2)


def stamp(cv, cx, cy, r, ink, name, kind, date):
    cv.ring(cx, cy, r, ink, 4)
    cv.ring(cx, cy, r - 9, ink, 2)
    # bold name: two passes offset by one pixel
    draw_centered(cv, cx + 1, cy - 22, name, 1, ink, 1)
    draw_centered(cv, cx, cy - 22, name, 1, ink, 1)
    cv.rect(cx - 26, cy - 11, 52, 2, ink)
    draw_centered(cv, cx, cy - 6, kind, 1, ink, 1)
    draw_centered(cv, cx, cy + 6, date, 1, ink, 1)
    cv.rect(cx - 26, cy + 18, 52, 2, ink)


def left_page(cv):
    cv.rect(38, 42, 480, 960, SHADOW)
    cv.rect(28, 32, 480, 960, PAGE)
    guilloche(cv, 44, 494, 116, 986, GUIL)
    cv.outline(40, 44, 456, 936, PAGE_LINE, 1)
    cx = 268
    draw_centered(cv, cx, 54, "REPUBLIC OF KALVERA", 3, NAVY)
    draw_centered(cv, cx, 88, "PASSPORT", 2, GRAY, 4)
    coat_of_arms(cv, cx, 118)
    # document identifiers
    draw_text(cv, 62, 252, "TYPE", 1, GRAY)
    draw_text(cv, 62, 264, "P", 2, INK)
    draw_text(cv, 150, 252, "CODE", 1, GRAY)
    draw_text(cv, 150, 264, "KVA", 2, INK)
    draw_text(cv, 262, 252, "PASSPORT NO.", 1, GRAY)
    draw_text(cv, 262, 264, "KVA084173", 2, INK)
    cv.line(60, 292, 476, 292, PAGE_LINE, 1)
    # portrait + holder block
    portrait(cv, 60, 306, 150, 190)
    draw_text(cv, 228, 312, "SIGNATURE OF HOLDER", 1, GRAY)
    signature(cv, 232, 344, 150, (30, 40, 110))
    cv.line(228, 380, 470, 380, PAGE_LINE, 1)
    draw_text(cv, 228, 396, "THIS PASSPORT CONTAINS", 1, GRAY)
    draw_text(cv, 228, 410, "32 PAGES", 1, GRAY)
    # gold hologram disc
    cv.circle(300, 452, 25, GOLD)
    cv.ring(300, 452, 18, (240, 214, 130), 2)
    cv.poly(star_pts(300, 452, 11, 5), (240, 214, 130))
    # data block, two columns then full-width rows
    fields2 = [
        ("SURNAME", "VOSS", "GIVEN NAMES", "ELENA MARA"),
        ("NATIONALITY", "KALVERAN", "SEX", "F"),
        ("DATE OF BIRTH", "04 JUL 1991", "PLACE OF BIRTH", "PORT AURELIA"),
        ("DATE OF ISSUE", "12 MAR 2024", "DATE OF EXPIRY", "11 MAR 2034"),
    ]
    y = 522
    for l1, v1, l2, v2 in fields2:
        draw_text(cv, 60, y, l1, 1, GRAY)
        draw_text(cv, 60, y + 11, v1, 2, INK)
        draw_text(cv, 276, y, l2, 1, GRAY)
        draw_text(cv, 276, y + 11, v2, 2, INK)
        y += 46
    for lab, val in [("AUTHORITY", "MINISTRY OF THE INTERIOR"),
                     ("LANGUAGES", "KALVERAN - ENGLISH")]:
        draw_text(cv, 60, y, lab, 1, GRAY)
        draw_text(cv, 60, y + 11, val, 2, INK)
        y += 46
    # microprint strip
    micro = "KALVERA " * 8
    draw_text(cv, 60, y + 8, micro[:66], 1, (198, 202, 210), 1)
    draw_text(cv, 60, 838, "ENDORSEMENTS", 1, GRAY)
    cv.line(60, 856, 476, 856, PAGE_LINE, 1)
    cv.line(60, 872, 476, 872, PAGE_LINE, 1)
    # machine-readable zone
    line1, line2 = mrz_lines()
    draw_text(cv, 48, 896, line1, 2, INK, 0)
    draw_text(cv, 48, 928, line2, 2, INK, 0)
    # page number, bottom outer corner
    draw_text(cv, 478, 962, "7", 2, GRAY)


def right_page(cv):
    cv.rect(526, 42, 480, 960, SHADOW)
    cv.rect(516, 32, 480, 960, PAGE)
    guilloche(cv, 532, 982, 116, 986, GUIL_R, 34)
    cv.outline(528, 44, 456, 936, PAGE_LINE, 1)
    cx = 756
    draw_centered(cv, cx, 54, "VISAS", 3, NAVY)
    # Tarnovia entry visa
    vx, vy, vw, vh = 548, 104, 320, 168
    cv.rect(vx, vy, vw, vh, (238, 231, 206))
    cv.outline(vx, vy, vw, vh, TEAL, 3)
    cv.outline(vx + 7, vy + 7, vw - 14, vh - 14, TEAL, 1)
    draw_centered(cv, vx + vw // 2, vy + 18, "TARNOVIA", 3, TEAL)
    draw_centered(cv, vx + vw // 2, vy + 46, "ENTRY VISA", 2, INK)
    draw_centered(cv, vx + vw // 2, vy + 76, "FROM 02 JUN 2024", 1, INK, 1)
    draw_centered(cv, vx + vw // 2, vy + 92, "SINGLE ENTRY - 30 DAYS", 1, INK, 1)
    draw_centered(cv, vx + vw // 2, vy + 108, "VISA NO. TV-2024-08817", 1, INK, 1)
    draw_centered(cv, vx + vw // 2, vy + 124, "ISSUED AT PORT AURELIA", 1, GRAY, 1)
    cv.poly(star_pts(vx + vw // 2, vy + 148, 8, 3), TEAL)
    # entry / exit stamps in chronological order of the journey
    stamp(cv, 648, 428, 64, (36, 84, 160), "TARNOVIA", "DEPARTURE", "15 JUN 2024")
    stamp(cv, 856, 306, 58, (110, 60, 150), "KALVERA", "ENTRY", "18 JUN 2024")
    stamp(cv, 652, 618, 64, (178, 44, 52), "MERROW ISLES", "ARRIVAL", "09 JAN 2025")
    stamp(cv, 852, 612, 64, (36, 84, 160), "MERROW ISLES", "DEPARTURE", "03 FEB 2025")
    stamp(cv, 640, 812, 62, (30, 120, 80), "SABLE COAST", "ARRIVAL", "22 AUG 2025")
    # reef conservation fee stamp
    fx, fy, fw, fh = 786, 736, 172, 100
    cv.outline(fx, fy, fw, fh, TEAL, 3)
    cv.outline(fx + 5, fy + 5, fw - 10, fh - 10, TEAL, 1)
    draw_centered(cv, fx + fw // 2, fy + 12, "REEF CONSERVATION", 1, TEAL, 1)
    draw_centered(cv, fx + fw // 2, fy + 28, "FEE PAID", 1, TEAL, 1)
    draw_centered(cv, fx + fw // 2, fy + 48, "25 KAL", 2, TEAL)
    # Condition 7 box
    bx, by, bw, bh = 548, 884, 400, 92
    cv.outline(bx, by, bw, bh, INK, 2)
    draw_text(cv, bx + 12, by + 10, "CONDITION 7", 2, INK)
    en = "REEF PERMIT REQUIRED BEFORE LANDING ON THE NORTHERN ATOLLS."
    fr = "PERMIS RECIFAL REQUIS AVANT DEBARQUEMENT AUX ATOLLS DU NORD."
    yy = by + 34
    for line_ in wrap(en, 62) + wrap(fr, 62):
        draw_text(cv, bx + 12, yy, line_, 1, INK, 1)
        yy += 12
    # page number, bottom outer corner
    draw_text(cv, 532, 962, "8", 2, GRAY)

# -------------------------------------------------------------- PNG out

def png_bytes(cv):
    raw = bytearray()
    stride = cv.w * 3
    for yy in range(cv.h):
        raw.append(0)
        i = yy * stride
        raw += cv.px[i:i + stride]
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
            + chunk(b"IEND", b""))


def main():
    cv = Canvas(W, H, DESK)
    left_page(cv)
    right_page(cv)
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "entry.png"), "wb") as f:
        f.write(png_bytes(cv))


if __name__ == "__main__":
    main()
