#!/usr/bin/env python3
"""The Passport Page of a Country That Isn't There.

Writes one image, /output/entry.png (1024x1024, deterministic, no network):
an open passport spread for the invented Republic of Kalvera — data page
with portrait + machine-readable zone on the left, visa/stamp page on the
right. Every date is internally consistent: the passport is issued
12 MAR 2024, expires 11 MAR 2034, and every stamp falls between them in
chronological order.
"""

import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W = H = 1024

# ---------------------------------------------------------------- fonts
def _font(names, size):
    for name in names:
        for base in ("/usr/share/fonts/truetype/liberation/",
                     "/usr/share/fonts/truetype/dejavu/"):
            path = os.path.join(base, name)
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


def serif_b(size):
    return _font(["LiberationSerif-Bold.ttf", "DejaVuSerif-Bold.ttf"], size)


def serif(size):
    return _font(["LiberationSerif-Regular.ttf", "DejaVuSerif.ttf"], size)


def sans(size):
    return _font(["LiberationSans-Regular.ttf", "DejaVuSans.ttf"], size)


def sans_b(size):
    return _font(["LiberationSans-Bold.ttf", "DejaVuSans-Bold.ttf"], size)


def mono(size):
    return _font(["LiberationMono-Regular.ttf", "DejaVuSansMono.ttf"], size)


def mono_b(size):
    return _font(["LiberationMono-Bold.ttf", "DejaVuSansMono-Bold.ttf"], size)


# ---------------------------------------------------------------- colours
INK = (26, 34, 44)          # near-black text
NAVY = (31, 58, 95)         # official navy
GOLD = (138, 109, 59)       # rule gold
PAGE = (247, 243, 232)      # cream page
PAGE_EDGE = (232, 226, 208)
DESK = (34, 48, 58)         # dark desk
DESK2 = (26, 38, 46)
LABEL = (96, 104, 110)      # small-caps labels
SKIN = (217, 169, 134)
SKIN_D = (198, 148, 112)
HAIR = (58, 42, 34)
BLAZER = (36, 68, 88)
SAGE1 = (184, 196, 168)
SAGE2 = (157, 176, 140)

STAMP_BLUE = (28, 68, 138)
STAMP_GREEN = (28, 108, 68)
STAMP_PURPLE = (108, 58, 128)
STAMP_RED = (148, 58, 48)


# ---------------------------------------------------------------- MRZ
def mrz_check(text):
    """ICAO 9303 check digit: weights 7,3,1; A=10..Z=35, '<'=0."""
    total = 0
    for i, ch in enumerate(text):
        if ch == "<":
            v = 0
        elif ch.isdigit():
            v = int(ch)
        else:
            v = ord(ch) - 55
        total += v * (7, 3, 1)[i % 3]
    return str(total % 10)


def mrz_check_fields(fields):
    """Composite check digit: same weights, restarting at 7 for each
    data element (ICAO 9303 — verified against its worked example,
    whose composite digit is 0)."""
    total = 0
    for field in fields:
        for i, ch in enumerate(field):
            if ch == "<":
                v = 0
            elif ch.isdigit():
                v = int(ch)
            else:
                v = ord(ch) - 55
            total += v * (7, 3, 1)[i % 3]
    return str(total % 10)


def build_mrz():
    # Line 1: P<KVA + VOSS<<ELENA<MARA, padded with '<' to 44.
    line1 = ("P<KVA" + "VOSS<<ELENA<MARA").ljust(44, "<")
    doc = "KVA084173"
    dob = "910704"          # 04 JUL 1991
    expiry = "340311"       # 11 MAR 2034
    personal = "<" * 14
    composite = mrz_check_fields([
        doc + mrz_check(doc), "KVA", dob + mrz_check(dob), "F",
        expiry + mrz_check(expiry), personal + mrz_check(personal)])
    line2 = (doc + mrz_check(doc) + "KVA" + dob + mrz_check(dob)
             + "F" + expiry + mrz_check(expiry)
             + personal + mrz_check(personal) + composite)
    assert len(line1) == 44 and len(line2) == 44, (line1, line2)
    return line1, line2


# ---------------------------------------------------------------- helpers
def center_text(d, cx, y, text, font, fill):
    w = d.textlength(text, font=font)
    d.text((cx - w / 2, y), text, font=font, fill=fill)


def spaced_text(d, x, y, text, font, fill, tracking=3):
    """Draw text with extra letter-spacing (passport headers)."""
    cx = x
    for ch in text:
        d.text((cx, y), ch, font=font, fill=fill)
        cx += d.textlength(ch, font=font) + tracking
    return cx


def centered_spaced(d, cx, y, text, font, fill, tracking=3):
    total = sum(d.textlength(ch, font=font) + tracking for ch in text) - tracking
    spaced_text(d, cx - total / 2, y, text, font, fill, tracking)


def field(d, x, y, label, value, vfont=None, label_size=10, value_size=15,
          width=200):
    d.text((x, y), label, font=sans(label_size), fill=LABEL)
    d.text((x, y + 13), value, font=vfont or sans_b(value_size), fill=INK)


def circular_text(base, cx, cy, radius, text, font, color, start_deg=-90,
                  sweep=300, flip=False):
    """Draw text along a circle, letters rotated tangentially."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    n = len(text)
    for i, ch in enumerate(text):
        ang = math.radians(start_deg + sweep * (i / max(n - 1, 1)))
        x = cx + radius * math.cos(ang)
        y = cy + radius * math.sin(ang)
        glyph = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glyph)
        gd.text((20, 20), ch, font=font, fill=color, anchor="mm")
        rot = math.degrees(ang) + (90 if not flip else -90)
        glyph = glyph.rotate(-rot, resample=Image.BICUBIC, center=(20, 20))
        layer.alpha_composite(glyph, (int(x - 20), int(y - 20)))
    base.alpha_composite(layer)


def stamp_circle(base, cx, cy, r, top, mid, bottom, color, rotate=0,
                 alpha=205):
    """Circular date stamp, drawn on its own layer then rotated."""
    size = r * 2 + 24
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    c = size // 2
    ink = color + (alpha,)
    ld.ellipse([c - r, c - r, c + r, c + r], outline=ink, width=3)
    ld.ellipse([c - r + 9, c - r + 9, c + r - 9, c + r - 9],
               outline=ink, width=1)
    circular_text(layer, c, c, r - 20, top, sans_b(11), ink,
                  start_deg=-150, sweep=120)
    center_text(ld, c, c - 12, mid, sans_b(14), ink)
    center_text(ld, c, c + 8, bottom, sans_b(13), ink)
    layer = layer.rotate(rotate, resample=Image.BICUBIC, center=(c, c))
    base.alpha_composite(layer, (int(cx - size / 2), int(cy - size / 2)))


def stamp_rect(base, box, lines, color, rotate=0, alpha=200, title_size=15):
    """Rectangular visa / fee stamp with a double border."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    layer = Image.new("RGBA", (w + 24, h + 24), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ink = color + (alpha,)
    ld.rectangle([12, 12, w + 11, h + 11], outline=ink, width=3)
    ld.rectangle([16, 16, w + 7, h + 7], outline=ink, width=1)
    cy = 12 + 12
    for i, (text, size) in enumerate(lines):
        f = sans_b(size) if i == 0 else sans(size)
        center_text(ld, (w + 24) // 2, cy, text, f, ink)
        cy += size + 5
    layer = layer.rotate(rotate, resample=Image.BICUBIC,
                         center=((w + 24) // 2, (h + 24) // 2))
    base.alpha_composite(layer, (x0 - 12, y0 - 12))


# ---------------------------------------------------------------- portrait
def draw_portrait(d, x0, y0, w, h):
    """Stylised flat-illustration passport portrait (drawn, not pasted)."""
    # backdrop: soft sage gradient
    for i in range(h):
        t = i / h
        col = tuple(int(SAGE1[j] + (SAGE2[j] - SAGE1[j]) * t)
                    for j in range(3))
        d.line([(x0, y0 + i), (x0 + w, y0 + i)], fill=col)
    cx = x0 + w // 2
    # shoulders / blazer
    d.pieslice([cx - 78, y0 + h - 78, cx + 78, y0 + h + 60],
               start=180, end=360, fill=BLAZER)
    d.polygon([(cx - 26, y0 + h - 40), (cx, y0 + h - 22),
               (cx + 26, y0 + h - 40), (cx + 14, y0 + h),
               (cx - 14, y0 + h)], fill=(242, 238, 226))  # shirt V
    # neck + shadow under chin
    d.rectangle([cx - 13, y0 + 108, cx + 13, y0 + 138], fill=SKIN_D)
    d.rectangle([cx - 13, y0 + 108, cx + 13, y0 + 116],
                fill=(178, 128, 96))
    # hair back (bob framing the face)
    d.ellipse([cx - 46, y0 + 8, cx + 46, y0 + 128], fill=HAIR)
    # face
    d.ellipse([cx - 34, y0 + 22, cx + 34, y0 + 116], fill=SKIN)
    # fringe: a clean band across the forehead only
    d.pieslice([cx - 36, y0 + 10, cx + 36, y0 + 58],
               start=180, end=360, fill=HAIR)
    d.rectangle([cx - 36, y0 + 30, cx + 36, y0 + 40], fill=HAIR)
    # side locks of the bob, framing the cheeks
    d.rounded_rectangle([cx - 42, y0 + 34, cx - 30, y0 + 104],
                        radius=6, fill=HAIR)
    d.rounded_rectangle([cx + 30, y0 + 34, cx + 42, y0 + 104],
                        radius=6, fill=HAIR)
    # eyebrows: short, straight, neutral
    d.line([(cx - 23, y0 + 60), (cx - 8, y0 + 59)], fill=HAIR, width=3)
    d.line([(cx + 8, y0 + 59), (cx + 23, y0 + 60)], fill=HAIR, width=3)
    # eyes: small, level, neutral
    for ex in (cx - 16, cx + 16):
        d.ellipse([ex - 4, y0 + 66, ex + 4, y0 + 73], fill=(38, 30, 26))
        d.line([(ex - 6, y0 + 65), (ex + 6, y0 + 65)],
               fill=(38, 30, 26), width=2)
    # nose + closed, neutral mouth
    d.line([(cx, y0 + 76), (cx - 2, y0 + 90), (cx + 3, y0 + 92)],
           fill=SKIN_D, width=2)
    d.arc([cx - 9, y0 + 96, cx + 9, y0 + 106], start=15, end=165,
          fill=(168, 92, 84), width=2)
    # blazer lapels
    d.line([(cx - 22, y0 + h - 34), (cx, y0 + h - 14)], fill=(24, 48, 64),
           width=3)
    d.line([(cx + 22, y0 + h - 34), (cx, y0 + h - 14)], fill=(24, 48, 64),
           width=3)


def draw_emblem(d, cx, y, s=34):
    """Kalvera arms: shield, eight-point star, three waves."""
    d.polygon([(cx - s, y), (cx + s, y), (cx + s * 0.82, y + s * 1.05),
               (cx, y + s * 1.35), (cx - s * 0.82, y + s * 1.05)],
              outline=NAVY, width=3)
    d.polygon([(cx - s + 6, y + 5), (cx + s - 6, y + 5),
               (cx + (s - 6) * 0.82, y + s * 0.95),
               (cx, y + s * 1.2), (cx - (s - 6) * 0.82, y + s * 0.95)],
              outline=GOLD, width=1)
    # eight-point star
    for k in range(8):
        a = math.radians(k * 45 - 90)
        a2 = math.radians(k * 45 - 90 + 22.5)
        d.line([(cx, y + s * 0.42),
                (cx + s * 0.30 * math.cos(a), y + s * 0.42 + s * 0.30 * math.sin(a))],
               fill=GOLD, width=3)
        d.line([(cx, y + s * 0.42),
                (cx + s * 0.16 * math.cos(a2), y + s * 0.42 + s * 0.16 * math.sin(a2))],
               fill=GOLD, width=2)
    d.ellipse([cx - 4, y + s * 0.36, cx + 4, y + s * 0.48], fill=GOLD)
    # three waves
    for j, wy in enumerate((0.72, 0.86, 1.00)):
        yy = y + s * wy
        pts = []
        for t in range(0, 25):
            px = cx - s * 0.62 + (s * 1.24) * t / 24
            py = yy + 3 * math.sin(t * math.pi * 2 / 6)
            pts.append((px, py))
        d.line(pts, fill=NAVY, width=2)


# ---------------------------------------------------------------- pages
def draw_data_page(img, x0, y0, w, h):
    d = ImageDraw.Draw(img, "RGBA")
    # page body
    d.rectangle([x0, y0, x0 + w, y0 + h], fill=PAGE + (255,))
    d.rectangle([x0, y0, x0 + w, y0 + h], outline=(120, 110, 88), width=1)
    # faint guilloche: fine diagonal lines, clipped to the page
    guil = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(guil)
    for i in range(-h, w, 12):
        gd.line([(i, h), (i + h, 0)], fill=(190, 200, 210, 20), width=1)
    img.alpha_composite(guil, (x0, y0))
    # inner gold rule frame
    d.rectangle([x0 + 9, y0 + 9, x0 + w - 9, y0 + h - 9],
                outline=GOLD + (255,), width=1)

    cx = x0 + w // 2
    # emblem + country
    draw_emblem(d, cx, y0 + 26, s=30)
    centered_spaced(d, cx, y0 + 96, "REPUBLIC OF KALVERA",
                    serif_b(23), NAVY, tracking=2)
    centered_spaced(d, cx, y0 + 126, "PASSPORT", sans_b(15), INK, tracking=8)
    center_text(d, cx, y0 + 148, "PASSEPORT", sans(10), LABEL)
    d.line([(x0 + 30, y0 + 170), (x0 + w - 30, y0 + 170)],
           fill=NAVY + (255,), width=2)

    # type / code / number row
    y = y0 + 184
    cols = [("Type", "P", x0 + 30), ("Code", "KVA", x0 + 150),
            ("Passport No.", "KVA084173", x0 + 250)]
    for label, value, fx in cols:
        d.text((fx, y), label, font=sans(10), fill=LABEL)
        d.text((fx, y + 13), value, font=sans_b(16), fill=INK)
    d.line([(x0 + 30, y + 36), (x0 + w - 30, y + 36)],
           fill=(150, 140, 118, 255), width=1)

    # portrait + signature
    px, py, pw, ph = x0 + 30, y0 + 244, 150, 185
    draw_portrait(d, px, py, pw, ph)
    d.rectangle([px, py, px + pw, py + ph], outline=NAVY + (255,), width=2)
    sy = py + ph + 12
    d.text((px, sy), "Signature of bearer", font=sans(9), fill=LABEL)
    # flowing signature in dark blue ink
    sig = Image.new("RGBA", (pw, 34), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sig)
    pts = [(4 + t, 18 + 6 * math.sin(t / 20.0)) for t in range(0, 141, 3)]
    sd.line(pts, fill=(30, 50, 110, 235), width=2)
    pts2 = [(4 + t, 24 + 4 * math.sin(t / 14.0 + 1.5))
            for t in range(0, 121, 3)]
    sd.line(pts2, fill=(30, 50, 110, 200), width=1)
    sd.line([(4, 30), (146, 30)], fill=(30, 50, 110, 200), width=1)
    img.alpha_composite(sig, (px, sy + 12))

    # personal data fields
    fx = x0 + 204
    fy = y0 + 244
    field(d, fx, fy, "Surname / Nom", "VOSS")
    field(d, fx, fy + 40, "Given names / Prénoms", "ELENA MARA")
    field(d, fx, fy + 80, "Nationality / Nationalité", "KALVERAN")
    field(d, fx, fy + 120, "Date of birth / Date de naissance",
          "04 JUL 1991")
    field(d, fx, fy + 160, "Place of birth / Lieu de naissance",
          "PORT AURELIA")
    field(d, fx, fy + 200, "Sex / Sexe", "F")

    # issue / expiry / authority
    y2 = y0 + 496
    d.text((x0 + 30, y2), "Date of issue / Date de délivrance",
           font=sans(10), fill=LABEL)
    d.text((x0 + 30, y2 + 13), "12 MAR 2024", font=sans_b(15), fill=INK)
    d.text((x0 + 220, y2), "Date of expiry / Date d'expiration",
           font=sans(10), fill=LABEL)
    d.text((x0 + 220, y2 + 13), "11 MAR 2034", font=sans_b(15), fill=INK)
    d.text((x0 + 30, y2 + 40),
           "Authority / Autorité", font=sans(10), fill=LABEL)
    d.text((x0 + 30, y2 + 53),
           "MINISTRY OF THE INTERIOR — PORT AURELIA",
           font=sans_b(13), fill=INK)
    d.text((x0 + 30, y2 + 74),
           "Languages / Langues:  KALVERAN — ENGLISH",
           font=sans(11), fill=INK)
    d.line([(x0 + 30, y2 + 94), (x0 + w - 30, y2 + 94)],
           fill=(150, 140, 118, 255), width=1)

    # machine-readable zone (real ICAO check digits)
    mrz1, mrz2 = build_mrz()
    my = y0 + h - 62
    d.rectangle([x0 + 20, my - 6, x0 + w - 20, my + 44],
                fill=(255, 255, 255, 255))
    d.text((x0 + 24, my), mrz1, font=mono(16), fill=INK)
    d.text((x0 + 24, my + 21), mrz2, font=mono(16), fill=INK)


def draw_visa_page(img, x0, y0, w, h):
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([x0, y0, x0 + w, y0 + h], fill=PAGE + (255,))
    d.rectangle([x0, y0, x0 + w, y0 + h], outline=(120, 110, 88), width=1)
    d.rectangle([x0 + 9, y0 + 9, x0 + w - 9, y0 + h - 9],
                outline=GOLD + (255,), width=1)
    cx = x0 + w // 2
    centered_spaced(d, cx, y0 + 26, "VISAS", sans_b(16), NAVY, tracking=10)
    d.line([(x0 + 30, y0 + 52), (x0 + w - 30, y0 + 52)],
           fill=NAVY + (255,), width=2)

    # Tarnovia entry visa (rectangular, top)
    stamp_rect(img, (x0 + 34, y0 + 72, x0 + w - 34, y0 + 158),
               [("TARNOVIA — ENTRY VISA", 15),
                ("Valid 90 days · Single entry", 12),
                ("Issued 02 JUN 2024 · Port Aurelia Consulate", 12),
                ("No. TV-2024-1187", 12)],
               STAMP_BLUE, rotate=-2)

    # circular stamps, two columns
    stamp_circle(img, x0 + 108, y0 + 248, 62,
                 "TARNOVIA", "15 JUN 2024", "DEPARTURE",
                 STAMP_PURPLE, rotate=8)
    stamp_circle(img, x0 + w - 108, y0 + 248, 62,
                 "PORT AURELIA", "18 JUN 2024", "ENTRY",
                 STAMP_GREEN, rotate=-7)
    stamp_circle(img, x0 + 108, y0 + 386, 62,
                 "MERROW ISLES", "09 JAN 2025", "ARRIVAL",
                 STAMP_RED, rotate=-5)
    stamp_circle(img, x0 + w - 108, y0 + 386, 62,
                 "MERROW ISLES", "03 FEB 2025", "DEPARTURE",
                 STAMP_RED, rotate=6)
    stamp_circle(img, x0 + 108, y0 + 512, 62,
                 "SABLE COAST", "22 AUG 2025", "ARRIVAL",
                 STAMP_BLUE, rotate=4)

    # reef conservation fee stamp (the telling detail)
    stamp_rect(img, (x0 + 196, y0 + 452, x0 + w - 30, y0 + 566),
               [("REEF CONSERVATION FEE", 14),
                ("PAID — 25 KAL", 15),
                ("PORT AURELIA · 22 AUG 2025", 11)],
               STAMP_GREEN, rotate=3)

    # visa condition box (the telling detail, in the document's own words)
    bx0, by0, bx1, by1 = x0 + 30, y0 + 596, x0 + w - 30, y0 + 676
    d.rectangle([bx0, by0, bx1, by1], outline=NAVY + (255,), width=1)
    d.rectangle([bx0 + 3, by0 + 3, bx1 - 3, by1 - 3],
                outline=(150, 140, 118, 255), width=1)
    d.text((bx0 + 12, by0 + 8), "CONDITION 7", font=sans_b(11), fill=NAVY)
    d.text((bx0 + 12, by0 + 24),
           "Holder must present a reef permit before landing",
           font=sans(11), fill=INK)
    d.text((bx0 + 12, by0 + 39),
           "on the Northern Atolls. Permit office: Port Aurelia.",
           font=sans(11), fill=INK)
    d.text((bx0 + 12, by0 + 56),
           "Le titulaire doit présenter un permis de récif.",
           font=sans(10), fill=LABEL)


# ---------------------------------------------------------------- main
def main():
    img = Image.new("RGBA", (W, H), DESK + (255,))
    d = ImageDraw.Draw(img, "RGBA")
    # soft glow behind the spread: one big blurred ellipse, no banding
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([112, 72, 912, 952], fill=(58, 78, 92, 255))
    glow = glow.filter(ImageFilter.GaussianBlur(90))
    img.alpha_composite(glow)

    # spread shadow + pages
    d.rectangle([40, 158, 984, 872], fill=(0, 0, 0, 90))
    draw_data_page(img, 48, 162, 452, 700)
    draw_visa_page(img, 524, 162, 452, 700)
    # spine shadow between the pages
    sp = Image.new("RGBA", (24, 700), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sp)
    for i in range(24):
        a = int(70 * (1 - abs(i - 11) / 12))
        sd.line([(i, 0), (i, 700)], fill=(0, 0, 0, a))
    img.alpha_composite(sp, (500, 162))

    # caption strip under the spread (document label, not a caption)
    d.text((512, 894), "KVA084173  ·  VOSS, ELENA MARA",
           font=mono(13), fill=(200, 208, 214), anchor="ma")

    out = os.environ.get("OUTPUT_PATH", "/output/entry.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.convert("RGB").save(out, "PNG", optimize=True)
    print("wrote", out, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()
