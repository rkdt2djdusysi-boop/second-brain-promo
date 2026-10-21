"""Compose the 'Projects progress rollup' TikTok promo (1080x1920, ~20 s, no voice).

Usage: python3 tools/projects_video.py <shots_dir> <out.mp4>
Shots come from tools/projects_pages.py (real Notion data).
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
       ["projects_table", "projects_gallery", "project", "task_todo", "task_done", "home"]}
sheet = Image.open(f"{SH}/sheet.png").convert("RGBA")
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

def progress(fr, name, scroll, pct):
    x, y, w, h = G[name]["progval"]; y = TOP + y - scroll
    d = ImageDraw.Draw(fr)
    bw = 330; by = y + h / 2 - 9
    d.rounded_rectangle([x, by, x + bw, by + 18], 9, fill=(51, 51, 51))
    if pct > 0: d.rounded_rectangle([x, by, x + max(18, bw * pct / 100), by + 18], 9, fill=(79, 163, 111))
    d.text((x + bw + 22, y + h / 2 - 25), f"{int(round(pct))}%", font=f_pct, fill=(207, 207, 207))

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

# ---------------- timeline ----------------
T_TOTAL = 20.0
S2_SCROLL = G["projects_table"]["b3"][1] - 760          # bullet lands mid-screen
S3_SCROLL = G["projects_table"]["db"][1] - 300          # database just under the nav
TAB_T, CARD_T = 6.9, 8.55
FILM_T, STATUS_T, DONE_T = 11.55, 12.75, 13.65
PROJ_SCROLL = 600

def scene(t):
    # S1 hook: top of Projects page, slow hand-held push-in
    if t < 3.0:
        fr = view("projects_table", 0, "Projects")
        u = t / 3.0; z = 1 + 0.045 * u; cw, ch = int(W / z), int(H / z)
        fr = fr.crop(((W - cw) // 2, (H - ch) // 3, (W - cw) // 2 + cw, (H - ch) // 3 + ch)).resize((W, H), Image.LANCZOS)
        caption(fr, ["stop updating", "progress bars by hand"], 740)
        return fr
    # S2 scroll to the rule in "How to use it"
    if t < 5.6:
        u = ease((t - 3.0) / 1.2); s = S2_SCROLL * u
        fr = view("projects_table", s, "Projects")
        if 3.05 < t < 4.3: touch(fr, 780, 1550 - 520 * ease((t - 3.05) / 1.2), 0.85)
        if t > 4.2:  # marker highlight on the real bullet
            x, y, w, h = G["projects_table"]["b3"]; a = ease((t - 4.2) / 0.35)
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
            d.rounded_rectangle([x - 70, TOP + y - s - 10, x + w + 8, TOP + y - s + h + 10], 14,
                                outline=(255, 214, 10, int(255 * a)), width=7)
            fr = Image.alpha_composite(fr.convert("RGBA"), ov).convert("RGB")
            caption(fr, ["the only rule:"], 1350)
        return fr
    # S3 database: Default view -> tap Gallery
    if t < 9.0:
        u = ease((t - 5.6) / 0.9); s = S2_SCROLL + (S3_SCROLL - S2_SCROLL) * u
        name = "projects_gallery" if t >= TAB_T else "projects_table"
        fr = view(name, s, "Projects")
        if 5.62 < t < 6.5: touch(fr, 760, 1500 - 480 * ease((t - 5.62) / 0.9), 0.85)
        tx, ty = scy("projects_table", "tab1", s); tap(fr, t, TAB_T, tx, ty)
        cx_, cy_ = scy("projects_gallery", "card-launch", s); tap(fr, t, CARD_T, cx_ - 80, cy_ - 150)
        if t >= TAB_T + 0.15:
            caption(fr, ["% done + days left,", "on every project"], 1500)
        return fr
    # S4 project page (push in), progress 25 %
    if t < 12.0:
        s = PROJ_SCROLL * ease((t - 9.4) / 0.8)
        fr = view("project", s, "Launch my Notion template")
        progress(fr, "project", s, 25)
        if 9.42 < t < 10.25: touch(fr, 760, 1500 - 380 * ease((t - 9.42) / 0.8), 0.85)
        if t > 9.6: caption(fr, ["4 linked tasks, 1 done", "= 25%"], 300)
        fx, fy = scy("project", "task-film", s); tap(fr, t, FILM_T, fx + 40, fy - 40)
        return fr
    # S5 task page: Status To do -> Done via the status sheet
    if t < 14.4:
        name = "task_done" if t >= DONE_T + 0.1 else "task_todo"
        fr = view(name, 0, "Film the 3D brain for TikTok")
        sx_, sy_ = scy("task_todo", "status", 0)
        caption(fr, ["mark one task Done..."], 1620)
        tap(fr, t, STATUS_T, 760, sy_)
        if STATUS_T + 0.05 < t < DONE_T + 0.45:
            up = ease((t - STATUS_T - 0.05) / 0.3) if t < DONE_T + 0.1 else 1 - ease((t - DONE_T - 0.1) / 0.3)
            dim = Image.new("RGBA", (W, H), (0, 0, 0, int(120 * up)))
            fr = Image.alpha_composite(fr.convert("RGBA"), dim)
            y0 = int(H - sheet.height * up); fr.alpha_composite(sheet, (0, y0)); fr = fr.convert("RGB")
            ox, oy, ow, oh = G["sheet"]["opt-done"]; tap(fr, t, DONE_T, 300, y0 + oy + oh / 2)
        return fr
    # S6 back to the project: rollup recalculates 25 -> 50 %
    if t < 17.2:
        fr = view("project", PROJ_SCROLL, "Launch my Notion template")
        pct = 25 + 25 * ease((t - 15.0) / 0.9)
        progress(fr, "project", PROJ_SCROLL, pct)
        if t > 14.9:
            x, y, w, h = G["project"]["prog"]; y = TOP + y - PROJ_SCROLL
            a = ease((t - 14.9) / 0.3)
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
            d.rounded_rectangle([x - 20, y - 6, x + w + 20, y + h + 6], 14, outline=(255, 214, 10, int(255 * a)), width=7)
            fr = Image.alpha_composite(fr.convert("RGBA"), ov).convert("RGB")
        caption(fr, ["...the bar moves", "on its own"], 300)
        return fr
    # S7 end card: home page with the brain
    fr = view("home", 0, "Second Brain OS")
    brain(fr, t, TOP + by_)
    caption(fr, ["Second Brain OS"], 1590, f_big, 32)
    caption(fr, ["Notion template"], 1735)
    return fr

CUTS = [(9.0, +1), (12.0, +1), (14.4, -1), (17.2, +1)]  # (time, direction) iOS push / pop
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
            if dirn > 0:
                cv.paste(prev, (int(-W * 0.3 * u), 0)); cv.paste(fr, (int(W * (1 - u)), 0))
            else:
                cv.paste(fr, (int(-W * 0.3 * (1 - u)), 0)); cv.paste(prev, (int(W * u), 0))
            fr = cv
    p.stdin.write(fr.tobytes())
p.stdin.close(); p.wait()
print("done", OUT)
