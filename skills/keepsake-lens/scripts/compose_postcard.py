#!/usr/bin/env python3
"""
compose_postcard.py — turn a captured frame into a keepsake postcard, laid out like a real one
(photo and message on the left, a divider, then "POST CARD", stamp, postmark and address lines on the right).

    python3 compose_postcard.py spec.json            # one card, or a list of cards
    python3 compose_postcard.py spec.json --out-dir out/

spec.json (one object or a list):
{
  "photo": "shot.png",                 # the captured frame (capture at 4K for 4K cards)
  "out": "postcard.png",
  "scale": 2.1333,                     # 1 = 1800x1200; 2.1333 = 3840x2560 (4K). Match it to the photo's size
  "title": "Lena to the rescue",       # headline (each word gets a capital unless "title_case": false)
  "meta": "Day 4 · 10:40 · The beach", # short line: day · time · place / conditions
  "note": "Old Tom capsized ...",      # one or two sentences, facts only (kept as a normal sentence)
  "tag": "Brave moment",               # small label above the headline
  "motif": "rescue",                   # surf | slide | rescue | reef | star — the card's own stamp art and corner sticker
  "badge": "Hero",                     # short text on the corner sticker (optional)
  "accent": [196, 72, 60],             # the card's accent colour (tag, sticker, tape)
  "warmth": 0.3,                       # -1 cool … 0 neutral … 1 golden hour
  "focus": [0.5, 0.5], "zoom": 1.0,    # crop around the subject: focus point (0–1) and zoom (≥ 1)
  "stamp": { "label": "RESCUE", "sky": [230,120,110], "sea": [150,210,215] },
  "postmark": { "top": "OCEAN JELLY", "middle": "DAY 4", "bottom": "2026" },
  "kicker": "Wish You Were Here",      # small line under POST CARD
  "address": ["To: Future Me", "C/O The Keepsake Box", "Ocean Jelly Beach", "Day 4 · 2026"],
  "footer": "Keepsake Lens · your day in a postcard",
  "palette": { "paper": [246,240,229], "ink": [40,36,32], "muted": [118,108,96] }
}
Needs Pillow (pip install pillow). Uses DejaVu fonts when present, else the default font.
"""
import json, math, random, sys, os, re
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

FONT_DIRS = ['/usr/share/fonts/truetype/dejavu/', '/Library/Fonts/', '/System/Library/Fonts/Supplemental/', 'C:/Windows/Fonts/', os.path.join(os.path.dirname(__file__), '..', 'assets', 'fonts')]
_cache = {}
def font(names, size):
    key = (tuple(names), int(size))
    if key in _cache: return _cache[key]
    f = None
    for d in FONT_DIRS:
        for n in names:
            p = os.path.join(d, n)
            if os.path.exists(p):
                try: f = ImageFont.truetype(p, int(size)); break
                except Exception: pass
        if f: break
    if not f:
        try: f = ImageFont.load_default(int(size))
        except TypeError: f = ImageFont.load_default()
    _cache[key] = f; return f
SERIF_I = ['DejaVuSerif-Italic.ttf', 'Georgia Italic.ttf', 'georgiai.ttf']
SERIF = ['DejaVuSerif.ttf', 'Georgia.ttf', 'georgia.ttf']
SANS = ['DejaVuSans.ttf', 'Arial.ttf', 'arial.ttf']
SANS_B = ['DejaVuSans-Bold.ttf', 'Arial Bold.ttf', 'arialbd.ttf']

def title_case(s):
    """capital at the start of every word (keeps the rest of each word as written, e.g. Kai’s, ZYN, C/O)"""
    return re.sub(r"(^|[\s/(\-–—·])([a-z])", lambda m: m.group(1) + m.group(2).upper(), s or '')

def grade(im, warm, k):
    r, g, b = im.split()
    r = r.point(lambda v: max(0, min(255, int(v * (1 + 0.10 * warm) + 6 * warm))))
    b = b.point(lambda v: max(0, min(255, int(v * (1 - 0.10 * warm)))))
    im = Image.merge('RGB', (r, g, b))
    im = ImageEnhance.Contrast(im).enhance(1.08); im = ImageEnhance.Color(im).enhance(1.12)
    im = ImageEnhance.Sharpness(im).enhance(1.15)                                  # crisp, never soft
    w, h = im.size; v = Image.new('L', (w, h), 0)
    ImageDraw.Draw(v).ellipse((-w * 0.15, -h * 0.2, w * 1.15, h * 1.2), fill=255); v = v.filter(ImageFilter.GaussianBlur(120 * k))
    return Image.composite(im, ImageEnhance.Brightness(im).enhance(0.8), v)

# ---- little hand-drawn icons for each motif (drawn into a box x, y, size) --------------------------
def icon(d, motif, x, y, s, col, light=(255, 255, 255), bg=None):
    cx, cy = x + s / 2, y + s / 2
    if motif == 'surf':      # a surfboard riding a curling wave
        d.arc((x + s * 0.05, y + s * 0.45, x + s * 0.95, y + s * 1.15), 190, 350, fill=col, width=max(2, int(s * 0.07)))
        board = Image.new('RGBA', (int(s), int(s)), (0, 0, 0, 0)); bd = ImageDraw.Draw(board)
        bd.ellipse((s * 0.15, s * 0.38, s * 0.85, s * 0.56), fill=col); bd.line((s * 0.2, s * 0.47, s * 0.8, s * 0.47), fill=light, width=max(1, int(s * 0.03)))
        board = board.rotate(18, resample=Image.BICUBIC); d._image.paste(board, (int(x), int(y - s * 0.1)), board)
    elif motif == 'slide':   # a curling water slide with a splash
        w = max(2, int(s * 0.09))
        d.arc((x + s * 0.12, y + s * 0.05, x + s * 0.72, y + s * 0.55), 180, 450, fill=col, width=w)
        d.line((x + s * 0.42, y + s * 0.55, x + s * 0.82, y + s * 0.85), fill=col, width=w)
        for i, (dx, dy, r) in enumerate([(0.78, 0.92, 0.06), (0.9, 0.82, 0.045), (0.68, 0.95, 0.04)]):
            d.ellipse((x + s * (dx - r), y + s * (dy - r), x + s * (dx + r), y + s * (dy + r)), fill=col)
    elif motif == 'rescue':  # a lifebuoy
        r1, r2 = s * 0.42, s * 0.22
        d.ellipse((cx - r1, cy - r1, cx + r1, cy + r1), fill=col)
        for a in (45, 135, 225, 315):
            d.pieslice((cx - r1, cy - r1, cx + r1, cy + r1), a - 14, a + 14, fill=light)
        d.ellipse((cx - r2, cy - r2, cx + r2, cy + r2), fill=bg if bg else (0, 0, 0, 0))
    elif motif == 'reef':    # a little fish with bubbles
        d.ellipse((x + s * 0.18, y + s * 0.35, x + s * 0.7, y + s * 0.68), fill=col)
        d.polygon([(x + s * 0.68, y + s * 0.515), (x + s * 0.9, y + s * 0.36), (x + s * 0.9, y + s * 0.67)], fill=col)
        d.ellipse((x + s * 0.27, y + s * 0.45, x + s * 0.33, y + s * 0.51), fill=light)
        for (dx, dy, r) in [(0.18, 0.22, 0.05), (0.28, 0.1, 0.035), (0.1, 0.08, 0.025)]:
            d.ellipse((x + s * (dx - r), y + s * (dy - r), x + s * (dx + r), y + s * (dy + r)), outline=col, width=max(1, int(s * 0.025)))
    else:                    # a star
        pts = []
        for i in range(10):
            a = -math.pi / 2 + i * math.pi / 5; rr = s * (0.45 if i % 2 == 0 else 0.2)
            pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
        d.polygon(pts, fill=col)

def stamp(d, x, y, w, h, st, ink, motif, k):
    hole = (244, 238, 226)
    d.rectangle((x, y, x + w, y + h), fill=(250, 247, 240))
    step = 12 * k
    i = 0
    while i <= w + 0.1:
        for yy in (y, y + h): d.ellipse((x + i - 4 * k, yy - 4 * k, x + i + 4 * k, yy + 4 * k), fill=hole)
        i += step
    j = 0
    while j <= h + 0.1:
        for xx in (x, x + w): d.ellipse((xx - 4 * k, y + j - 4 * k, xx + 4 * k, y + j + 4 * k), fill=hole)
        j += step
    ix, iy, iw, ih = x + 12 * k, y + 12 * k, w - 24 * k, h - 42 * k
    d.rectangle((ix, iy, ix + iw, iy + ih), fill=tuple(st.get('sky', [232, 170, 120])))
    top = iy + ih * 0.62
    pts = [(ix, iy + ih)] + [(ix + t, top + math.sin(t / (14 * k)) * 5 * k) for t in range(0, int(iw) + 1, max(1, int(4 * k)))] + [(ix + iw, iy + ih)]
    d.polygon(pts, fill=tuple(st.get('sea', [150, 210, 215])))
    d.ellipse((ix + iw * 0.7, iy + ih * 0.08, ix + iw * 0.7 + 20 * k, iy + ih * 0.08 + 20 * k), fill=(255, 232, 170))
    sky = tuple(st.get('sky', [232, 170, 120]))
    if motif == 'rescue': icon(d, motif, ix + iw * 0.14, iy + ih * 0.12, iw * 0.7, (225, 70, 55), (255, 255, 255), sky)
    else: icon(d, motif, ix + iw * 0.14, iy + ih * 0.2, iw * 0.7, (255, 255, 255), sky, sky)
    d.text((x + w / 2, y + h - 17 * k), st.get('label', ''), font=font(SANS_B, 15 * k), fill=ink, anchor='mm')

def postmark(d, cx, cy, pm, k):
    col = (70, 90, 110)
    for r in (58, 50): d.ellipse((cx - r * k, cy - r * k, cx + r * k, cy + r * k), outline=col, width=max(2, int(2 * k)))
    d.text((cx, cy - 16 * k), pm.get('top', ''), font=font(SANS_B, 13 * k), fill=col, anchor='mm')
    d.text((cx, cy + 4 * k), pm.get('middle', ''), font=font(SANS_B, 17 * k), fill=col, anchor='mm')
    d.text((cx, cy + 22 * k), pm.get('bottom', ''), font=font(SANS, 12 * k), fill=col, anchor='mm')
    for n in range(4):
        y0 = cy - 24 * k + n * 16 * k
        d.line([(cx + 62 * k + t, y0 + math.sin(t / (16 * k)) * 5 * k) for t in range(0, int(150 * k), max(1, int(4 * k)))], fill=(70, 90, 110, 200), width=max(2, int(2 * k)))

def sticker(card, cx, cy, r, motif, text, accent, k):
    """a round sticker with the motif's icon and a short badge, slightly tilted, with a soft shadow"""
    size = int(r * 2 + 40 * k)
    lay = Image.new('RGBA', (size, size), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    c = size / 2
    sh = Image.new('RGBA', (size, size), (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse((c - r + 4 * k, c - r + 8 * k, c + r + 4 * k, c + r + 8 * k), fill=(0, 0, 0, 70))
    sh = sh.filter(ImageFilter.GaussianBlur(7 * k)); lay.alpha_composite(sh)
    ld.ellipse((c - r, c - r, c + r, c + r), fill=(255, 253, 247))
    ld.ellipse((c - r * 0.9, c - r * 0.9, c + r * 0.9, c + r * 0.9), fill=tuple(accent))
    ld.ellipse((c - r * 0.84, c - r * 0.84, c + r * 0.84, c + r * 0.84), outline=(255, 255, 255, 170), width=max(1, int(1.5 * k)))
    icon(ld, motif, c - r * 0.42, c - r * 0.66, r * 0.84, (255, 255, 255), tuple(accent), tuple(accent))
    if text:
        t, size_ = text.upper(), 17 * k
        while size_ > 8 and ld.textlength(t, font=font(SANS_B, size_)) > r * 1.3: size_ -= 0.5   # shrink to fit inside the sticker
        ld.text((c, c + r * 0.42), t, font=font(SANS_B, size_), fill=(255, 255, 255), anchor='mm')
    lay = lay.rotate(-8, resample=Image.BICUBIC)
    card.paste(lay, (int(cx - size / 2), int(cy - size / 2)), lay)

def tape(card, x, y, w, h, accent, angle, k):
    """a strip of translucent washi tape holding the photo"""
    lay = Image.new('RGBA', (int(w), int(h)), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    ld.rectangle((0, 0, w, h), fill=tuple(accent) + (150,))
    for i in range(0, int(w), max(2, int(14 * k))): ld.line((i, 0, i + h * 0.6, h), fill=(255, 255, 255, 40), width=max(1, int(3 * k)))
    lay = lay.rotate(angle, resample=Image.BICUBIC, expand=True)
    card.paste(lay, (int(x - lay.size[0] / 2), int(y - lay.size[1] / 2)), lay)

def spaced(d, xy, text, f, fill, gap, anchor='la'):
    w = sum(d.textlength(ch, font=f) for ch in text) + gap * max(0, len(text) - 1)
    x, y = xy
    if anchor == 'ma': x -= w / 2
    elif anchor == 'ra': x -= w
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill); x += d.textlength(ch, font=f) + gap
    return w

def wrap(text, f, width, d):
    words, lines, cur = (text or '').split(), [], ''
    for wd in words:
        t = (cur + ' ' + wd).strip()
        if d.textlength(t, font=f) <= width: cur = t
        else: lines.append(cur); cur = wd
    if cur: lines.append(cur)
    return lines

def make(spec, out_dir=None):
    k = float(spec.get('scale', 1.0))
    pal = spec.get('palette', {})
    paper = tuple(pal.get('paper', [246, 240, 229])); ink = tuple(pal.get('ink', [40, 36, 32]))
    muted = tuple(pal.get('muted', [118, 108, 96])); rule = (214, 204, 190)
    accent = tuple(spec.get('accent', pal.get('accent', [31, 92, 84])))
    motif = spec.get('motif', 'star'); tc = title_case if spec.get('title_case', True) else (lambda s: s)
    W, H, M = int(round(1800 * k)), int(round(1200 * k)), 72 * k
    LX0, LX1, DIV, RX0, RX1 = M, 1000 * k, 1060 * k, 1120 * k, W - M
    card = Image.new('RGB', (W, H), paper); d = ImageDraw.Draw(card, 'RGBA')
    random.seed(spec.get('out', 'card'))
    for _ in range(int(4000 * k * k)):
        x, y = random.randrange(W), random.randrange(H); c = random.randint(-10, 6)
        d.point((x, y), fill=(max(0, paper[0] - 6 + c), max(0, paper[1] - 7 + c), max(0, paper[2] - 9 + c)))
    d.rounded_rectangle((26 * k, 26 * k, W - 26 * k, H - 26 * k), radius=18 * k, outline=rule, width=max(2, int(2 * k)))

    # ---- photo, cropped around the subject; always scaled down, never up, so it stays sharp
    pw, phh = int(LX1 - LX0), int((LX1 - LX0) / 1.5)
    ph = Image.open(spec['photo']).convert('RGB')
    zoom = float(spec.get('zoom', 1.0)); fx, fy = spec.get('focus', [0.5, 0.5])
    cw, ch_ = ph.size[0] / zoom, ph.size[0] / zoom / (pw / phh)
    if ch_ > ph.size[1]: ch_ = ph.size[1] / zoom; cw = ch_ * (pw / phh)
    x0 = min(max(fx * ph.size[0] - cw / 2, 0), ph.size[0] - cw); y0 = min(max(fy * ph.size[1] - ch_ / 2, 0), ph.size[1] - ch_)
    ph = ph.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch_))).resize((pw, phh), Image.LANCZOS)
    if cw < pw * 0.98: print(f"  note: photo upscaled ({int(cw)}px → {pw}px); capture larger for a sharper card", file=sys.stderr)
    ph = grade(ph, float(spec.get('warmth', 0)), k)
    py = int(M + 8 * k)
    shadow = Image.new('RGBA', (pw + int(60 * k), phh + int(60 * k)), (0, 0, 0, 0)); ImageDraw.Draw(shadow).rectangle((18 * k, 24 * k, pw + 42 * k, phh + 46 * k), fill=(0, 0, 0, 55))
    shadow = shadow.filter(ImageFilter.GaussianBlur(12 * k)); card.paste(shadow, (int(LX0 - 30 * k), int(py - 30 * k)), shadow)
    d.rectangle((LX0 - 14 * k, py - 14 * k, LX1 + 14 * k, py + phh + 14 * k), fill=(255, 255, 253))
    card.paste(ph, (int(LX0), py))
    tape(card, LX0 + 40 * k, py - 6 * k, 150 * k, 34 * k, accent, 28, k)                 # tape on the top-left corner
    sticker(card, LX1 - 30 * k, py + 34 * k, 74 * k, motif, spec.get('badge', ''), accent, k)   # the card's own sticker

    # ---- message block
    y = py + phh + 14 * k + 70 * k
    if spec.get('tag'):
        spaced(d, (LX0, y - 22 * k), spec['tag'].upper(), font(SANS_B, 17 * k), accent, 3 * k)
    y += 58 * k
    d.text((LX0, y), tc(spec.get('title', '')), font=font(SERIF_I, 62 * k), fill=ink, anchor='ls')
    y += 48 * k
    spaced(d, (LX0, y - 18 * k), spec.get('meta', '').upper(), font(SANS_B, 18 * k), muted, 2 * k)
    y += 52 * k
    for line in wrap(spec.get('note', ''), font(SERIF, 28 * k), pw, d)[:3]:
        d.text((LX0, y), line, font=font(SERIF, 28 * k), fill=ink, anchor='ls'); y += 42 * k

    # ---- divider and right column
    d.line((DIV, M + 70 * k, DIV, H - M - 40 * k), fill=rule, width=max(2, int(2 * k)))
    spaced(d, ((RX0 + RX1) / 2, M + 20 * k), 'POST CARD', font(SERIF, 34 * k), ink, 12 * k, anchor='ma')
    spaced(d, ((RX0 + RX1) / 2, M + 70 * k), spec.get('kicker', 'Wish You Were Here').upper(), font(SANS_B, 14 * k), accent, 4 * k, anchor='ma')
    sw_, sh_ = 176 * k, 214 * k
    sx, sy = RX1 - sw_, M + 130 * k
    stamp(d, sx, sy, sw_, sh_, spec.get('stamp', {}), ink, motif, k)
    pm = spec.get('postmark', {})
    postmark(d, sx - 64 * k, sy + sh_ / 2 + 10 * k, pm, k)
    lines = spec.get('address') or ['To: Future Me', 'C/O The Keepsake Box', pm.get('top', '').title(), ' · '.join(x for x in [pm.get('middle', '').title(), pm.get('bottom', '')] if x)]
    ay0 = py + phh + 14 * k + 92 * k
    for n in range(4):
        ly = ay0 + n * 84 * k
        d.line((RX0, ly, RX1, ly), fill=rule, width=max(2, int(2 * k)))
        if n < len(lines) and lines[n]:
            d.text((RX0 + 8 * k, ly - 14 * k), tc(lines[n]), font=font(SERIF_I, 34 * k), fill=(52, 64, 92), anchor='ls')
    d.text((RX1, H - M + 6 * k), spec.get('footer', 'Keepsake Lens · your day in a postcard'), font=font(SANS, 15 * k), fill=(160, 150, 136), anchor='rs')

    out = spec.get('out', 'postcard.png')
    if out_dir: out = os.path.join(out_dir, os.path.basename(out))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    card.save(out, optimize=True); return out

if __name__ == '__main__':
    if len(sys.argv) < 2: print(__doc__); sys.exit(1)
    out_dir = sys.argv[sys.argv.index('--out-dir') + 1] if '--out-dir' in sys.argv else None
    base = os.path.dirname(os.path.abspath(sys.argv[1]))
    specs = json.load(open(sys.argv[1]))
    for sp in (specs if isinstance(specs, list) else [specs]):
        if not os.path.isabs(sp['photo']): sp['photo'] = os.path.join(base, sp['photo'])
        print(make(sp, out_dir))
