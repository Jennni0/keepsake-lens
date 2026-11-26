#!/usr/bin/env python3
"""
contact_sheet.py — put captured frames or postcards side by side for review, and flag suspicious ones.

    python3 contact_sheet.py out/*.png -o sheet.png [--cols 2] [--width 600]

Flags printed per image:
  BLANK?      almost no variation (black canvas, early screenshot, lost device)
  BACKDROP?   most of the frame is one flat colour (camera outside the world / looking at the backdrop)
Needs Pillow.
"""
import sys, os
from PIL import Image, ImageDraw, ImageStat

def check(im):
    small = im.convert('RGB').resize((96, 64))
    st = ImageStat.Stat(small); spread = sum(st.stddev) / 3
    flags = []
    if spread < 6: flags.append('BLANK?')
    # share of pixels close to the most common colour
    q = small.quantize(colors=8); counts = sorted(q.getcolors(), reverse=True)
    if counts and counts[0][0] / (96 * 64) > 0.55 and spread < 40: flags.append('BACKDROP?')
    return flags, spread

def main(a):
    files = [x for x in a if not x.startswith('-') and x.lower().endswith(('.png', '.jpg', '.jpeg'))]
    out = a[a.index('-o') + 1] if '-o' in a else 'contact_sheet.png'
    cols = int(a[a.index('--cols') + 1]) if '--cols' in a else 2
    tw = int(a[a.index('--width') + 1]) if '--width' in a else 600
    files = [f for f in files if os.path.abspath(f) != os.path.abspath(out)]
    if not files: print(__doc__); return 1
    thumbs, bad = [], 0
    for f in files:
        im = Image.open(f).convert('RGB'); flags, spread = check(im)
        th = im.resize((tw, int(im.height * tw / im.width)))
        if flags:
            bad += 1; d = ImageDraw.Draw(th); d.rectangle((0, 0, tw - 1, th.height - 1), outline=(220, 40, 40), width=6)
            d.rectangle((8, 8, 8 + 12 * len(' '.join(flags)) + 16, 36), fill=(220, 40, 40)); d.text((16, 14), ' '.join(flags), fill=(255, 255, 255))
        print(f"{os.path.basename(f)}: {'OK' if not flags else ' '.join(flags)} (spread {spread:.1f})")
        thumbs.append(th)
    rows = (len(thumbs) + cols - 1) // cols; rh = max(t.height for t in thumbs)
    sheet = Image.new('RGB', (cols * (tw + 8) - 8, rows * (rh + 8) - 8), 'white')
    for i, t in enumerate(thumbs): sheet.paste(t, ((i % cols) * (tw + 8), (i // cols) * (rh + 8)))
    sheet.save(out); print('sheet:', out, f'({bad} flagged)')
    return 0

if __name__ == '__main__': sys.exit(main(sys.argv[1:]))
