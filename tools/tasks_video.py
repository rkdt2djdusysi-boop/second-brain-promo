"""Compose the 'Tasks by energy' TikTok promo (1080x1920, ~19 s, no voice).

Usage: python3 tools/tasks_video.py <shots_dir> <out.mp4>
Shots come from tools/tasks_pages.py (real Notion data).
"""
import json, math, random, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

SH, OUT = sys.argv[1], sys.argv[2]
W, H, FPS = 1080, 1920, 30
TOP = 273                      # status bar + Notion nav bar height (px)
BG = (25, 25, 25)
F = "/usr/share/fonts/opentype/inter/"
f_cap = ImageFont.truetype(F + "Inter-ExtraBold.otf", 60)
f_big = ImageFont.truetype(F + "Inter-ExtraBold.otf", 84)
f_sb = ImageFont.truetype(F + "Inter-SemiBold.otf", 46)
f_nav = ImageFont.truetype(F + "Inter-Medium.otf", 42)
f_pct = ImageFont.truetype(F + "Inter-Regular.otf", 40)

img = {n: Image.open(f"{SH}/{n}.png").convert("RGB") for n in
       ["tasks_table", "tasks_energy", "home", "board"]}
G = json.load(open(f"{SH}/geom.json"))

def ease(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)

def chrome(fr, title):
    d = ImageDraw.Draw(fr)
    d.rectangle([0, 0, W, TOP], fill=BG)
    d.text((84, 50), "9:41", font=f_sb, fill=(255, 255, 255))
    for k in range(4):  # signal
        h = 14 + k * 8; d.rounded_rectangle([800 + k * 18, 92 - h, 811 + k * 18, 92], 3, fill=(255, 255, 255))
    d.rounded_rectangle([890, 60, 960, 94], 9, outline=(255, 255, 255), width=3)
    d.rounded_rectangle([897, 67, 940, 87], 5, fill=(255, 255, 255))
    d.rectangle([963, 70, 968, 84], fill=(255, 255, 255))
    d.text((40, 150), "‹", font=ImageFont.truetype(F + "Inter-Regular.otf", 96), fill=(207, 207, 207))
    tw = d.textlength(title, font=f_nav)
    d.text(((W - tw) / 2, 186), title, font=f_nav, fill=(207, 207, 207))
    d.text((960, 176), "···", font=f_sb, fill=(207, 207, 207))
    d.line([0, TOP - 1, W, TOP - 1], fill=(40, 40, 40), width=2)
    d.rectangle([0, H - 66, W, H], fill=BG)               # bottom safe area
    d.rounded_rectangle([W / 2 - 200, 1886, W / 2 + 200, 1900], 7, fill=(235, 235, 235))

def view(name, scroll, title):
    fr = Image.new("RGB", (W, H), BG)
    im = img[name]; s = int(max(0, scroll))
    fr.paste(im.crop((0, s, W, min(im.height, s + H - TOP))), (0, TOP))
    chrome(fr, title)
    return fr

def caption(fr, lines, y, font=f_cap, pad=26):
    d = ImageDraw.Draw(fr)
    lh = font.size + 30
    for i, line in enumerate(lines):
        w = d.textlength(line, font=font)
        assert w + 2 * pad < W - 60, f"caption too wide: {line}"
        x = (W - w) / 2; yy = y + i * lh
        d.rounded_rectangle([x - pad, yy - 14, x + w + pad, yy + font.size + 16], 18, fill=(255, 255, 255))
        d.text((x, yy - 4), line, font=font, fill=(0, 0, 0))

def touch(fr, x, y, a=1.0, r=44):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    d.ellipse([x - r, y - r, x + r, y + r], fill=(210, 210, 210, int(130 * a)), outline=(255, 255, 255, int(190 * a)), width=4)
    fr.paste(Image.alpha_composite(fr.convert("RGBA"), ov).convert("RGB"))

def tap(fr, t, t0, x, y):
    """finger dot visible ~0.35 s around a tap at t0, slight press ripple"""
    if t0 - 0.2 <= t <= t0 + 0.25:
        u = (t - t0 + 0.2) / 0.45
        touch(fr, x, y, 1.0 - 0.5 * max(0, u - 0.6) / 0.4, 44 - 8 * math.sin(min(1, u) * math.pi))

def scy(name, key, scroll):  # screen y of an element's center for a given scroll
    x, y, w, h = G[name][key]; return x + w / 2, TOP + y + h / 2 - scroll

# ---------------- brain for the end card (white bars, scan band) -----------
bx, by_, bw_, bh_ = G["home"]["brain"]
mask = Image.new("L", (bw_, bh_), 0); md = ImageDraw.Draw(mask)
cx, cy = bw_ // 2, bh_ // 2 - 50
md.ellipse([cx - 380, cy - 250, cx + 380, cy + 200], 255)
md.ellipse([cx + 110, cy + 90, cx + 340, cy + 270], 255)
md.rectangle([cx + 50, cy + 150, cx + 125, cy + 330], 255)
rnd = random.Random(11); rows = []
for yy in range(cy - 245, cy + 330, 18):
    xs = [x for x in range(bw_) if mask.getpixel((x, min(bh_ - 1, yy)))]
    if not xs: continue
    l, r = xs[0], xs[-1]; segs = []; x = l
    while x < r:
        ln = rnd.randint(18, 100); segs.append((x, min(x + ln, r))); x += ln + rnd.randint(8, 18)
    rows.append((yy, segs))

def brain(fr, t, oy):
    d = ImageDraw.Draw(fr)
    sx = 0.80 + 0.20 * math.cos(t * 1.3)
    band = cy - 280 + ((t * 330) % 700)
    for yy, segs in rows:
        g = int(115 + 140 * math.exp(-((yy - band) / 30) ** 2))
        for a, b in segs:
            xa, xb = cx + (a - cx) * sx, cx + (b - cx) * sx
            if xb - xa < 2: continue
            d.rectangle([bx + xa, oy + yy, bx + xb, oy + yy + 5], fill=(g, g, g))


def highlight(fr, box, s, a, pad=(70, 10, 8, 10)):
    x, y, w, h = box
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    d.rounded_rectangle([x - pad[0], TOP + y - s - pad[1], x + w + pad[2], TOP + y - s + h + pad[3]], 14,
                        outline=(255, 214, 10, int(255 * a)), width=7)
    return Image.alpha_composite(fr.convert("RGBA"), ov).convert("RGB")

T_TOTAL = 19.0
GT = G["tasks_table"]; GE = G["tasks_energy"]; GB = G["board"]
S2_SCROLL = GT["b3"][1] - 700
S3_SCROLL = GT["db"][1] - 330
TAB_T = 8.0
BW = img["board"].width
COLX = [0, GB["col1"][0] - 60, min(BW - W, GB["col2"][0] - 60)]
SW1, SW2 = 10.5, 12.2            # swipe start times (0.5 s each)

def board_view(t, s, bxo):
    fr = view("tasks_energy", s, "Tasks")
    x, y, w, h = GE["boardslot"]; yy = int(TOP + y - s)
    strip = img["board"].crop((int(bxo), 0, int(bxo) + W, img["board"].height))
    hh = min(strip.height, H - 66 - yy)
    fr.paste(Image.new("RGB", (W, hh), BG), (0, yy)); fr.paste(strip.crop((0, 0, W, hh)), (0, yy))
    chrome(fr, "Tasks")
    return fr, yy

def scene(t):
    # S1 hook: top of the Tasks page, slow hand-held push-in
    if t < 2.8:
        fr = view("tasks_table", 0, "Tasks")
        u = t / 2.8; z = 1 + 0.045 * u; cw, ch = int(W / z), int(H / z)
        fr = fr.crop(((W - cw) // 2, (H - ch) // 3, (W - cw) // 2 + cw, (H - ch) // 3 + ch)).resize((W, H), Image.LANCZOS)
        caption(fr, ["your to-do list ignores", "how tired you are"], 760)
        return fr
    # S2 scroll to the real rule in "How to use it"
    if t < 5.6:
        s = S2_SCROLL * ease((t - 2.8) / 1.1)
        fr = view("tasks_table", s, "Tasks")
        if 2.85 < t < 4.0: touch(fr, 800, 1550 - 520 * ease((t - 2.85) / 1.1), 0.85)
        if t > 4.0:
            fr = highlight(fr, GT["b3"], s, ease((t - 4.0) / 0.35))
            caption(fr, ["mine doesn't."], 1420)
        return fr
    # S3 database table (Alert column), then tap the "By energy" tab
    if t < 8.9:
        s = S2_SCROLL + (S3_SCROLL - S2_SCROLL) * ease((t - 5.6) / 0.9)
        if t < TAB_T:
            fr = view("tasks_table", s, "Tasks")
        else:
            fr, _ = board_view(t, s, 0)
        if 5.62 < t < 6.5: touch(fr, 800, 1500 - 480 * ease((t - 5.62) / 0.9), 0.85)
        tx, ty = scy("tasks_table", "tab2", s); tap(fr, t, TAB_T, tx, ty)
        if 6.3 < t < TAB_T:
            caption(fr, ["late tasks flag", "themselves"], 1590)
        if t >= TAB_T + 0.1:
            caption(fr, ["now sort by energy"], 340)
        return fr
    # S4 By energy board: swipe High -> Medium -> Low
    if t < 16.0:
        s = S3_SCROLL
        if t < SW1: bxo = 0
        elif t < SW1 + 0.5: bxo = COLX[0] + (COLX[1] - COLX[0]) * ease((t - SW1) / 0.5)
        elif t < SW2: bxo = COLX[1]
        elif t < SW2 + 0.5: bxo = COLX[1] + (COLX[2] - COLX[1]) * ease((t - SW2) / 0.5)
        else: bxo = COLX[2]
        fr, yy = board_view(t, s, bxo)
        for sw in (SW1, SW2):
            if sw - 0.1 < t < sw + 0.55:
                u = ease((t - sw + 0.1) / 0.6); touch(fr, 900 - 620 * u, yy + 700, 0.85)
        if t < SW1:
            caption(fr, ["full battery:", "the hard stuff"], 310)
        elif SW1 + 0.5 <= t < SW2:
            caption(fr, ["half battery:", "the in-between stuff"], 310)
        elif t >= SW2 + 0.5 and t < 14.2:
            caption(fr, ["drained:", "easy wins only"], 310)
        elif t >= 14.2:
            caption(fr, ["keep 3 that matter.", "the rest is a bonus"], 310)
        return fr
    # S5 end card: home page with the brain
    fr = view("home", 0, "Second Brain OS")
    brain(fr, t, TOP + by_)
    caption(fr, ["Second Brain OS"], 1590, f_big, 32)
    caption(fr, ["Notion template"], 1735)
    return fr

CUTS = [(16.0, +1)]
TR = 0.3

p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                      "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "21",
                      "-pix_fmt", "yuv420p", "-profile:v", "high", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
for f in range(int(T_TOTAL * FPS)):
    t = f / FPS
    fr = scene(t)
    for c, dirn in CUTS:
        if c <= t < c + TR:
            u = ease((t - c) / TR); prev = scene(c - 0.001)
            cv = Image.new("RGB", (W, H), BG)
            cv.paste(prev, (int(-W * 0.3 * u), 0)); cv.paste(fr, (int(W * (1 - u)), 0))
            fr = cv
    p.stdin.write(fr.tobytes())
p.stdin.close(); p.wait()
print("done", OUT)
