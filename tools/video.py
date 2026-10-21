"""Compose a 'screen-recording' style TikTok promo from the page screenshots."""
import math, random, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

SH = sys.argv[1]; OUT = sys.argv[2]
W, H, FPS = 1080, 1920, 30
BOLD = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
EXTRA = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"

img = {n: Image.open(f"{SH}/{n}.png").convert("RGB") for n in ["home", "projects", "tasks", "habits", "more"]}
bx, by, bw, bh, mx, my = map(int, open(f"{SH}/home_geom.txt").read().split(","))

# ---------- brain (white bars in a side-profile brain shape) ----------
bm = Image.new("L", (bw, bh), 0); d = ImageDraw.Draw(bm)
cx, cy = bw // 2, bh // 2 - 30
d.ellipse([cx - 330, cy - 230, cx + 330, cy + 210], 255)           # cerebrum
d.ellipse([cx + 90, cy + 90, cx + 330, cy + 290], 255)             # cerebellum
d.rectangle([cx + 40, cy + 150, cx + 110, cy + 330], 255)          # stem
rows = []
rnd = random.Random(7)
for y in range(cy - 225, cy + 330, 17):
    xs = [x for x in range(bw) if bm.getpixel((x, y))]
    if not xs: continue
    l, r = xs[0], xs[-1]; segs = []; x = l
    while x < r:
        ln = rnd.randint(18, 95); segs.append((x, min(x + ln, r))); x += ln + rnd.randint(7, 16)
    rows.append((y, segs))

def draw_brain(fr, t, ox, oy):
    d = ImageDraw.Draw(fr)
    sx = 0.82 + 0.18 * math.cos(t * 1.1)
    ys = cy - 260 + ((t * 260) % 620)
    for y, segs in rows:
        g = int(120 + 135 * math.exp(-((y - ys) / 28) ** 2))
        for a, b in segs:
            xa, xb = cx + (a - cx) * sx, cx + (b - cx) * sx
            yy = oy + y
            if 0 <= yy < H: d.rectangle([ox + xa, yy, ox + xb, yy + 5], fill=(g, g, g))

# ---------- captions, TikTok "classic" white boxes ----------
def caption(fr, lines, y, size=58):
    f = ImageFont.truetype(EXTRA, size); d = ImageDraw.Draw(fr)
    lh = size + 26
    for i, line in enumerate(lines):
        w = d.textlength(line, font=f); x = (W - w) / 2; yy = y + i * lh
        d.rounded_rectangle([x - 24, yy - 12, x + w + 24, yy + size + 14], 16, fill=(255, 255, 255))
        d.text((x, yy - 4), line, font=f, fill=(0, 0, 0))

def touch(fr, x, y, a=1.0):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    d.ellipse([x - 42, y - 42, x + 42, y + 42], fill=(200, 200, 200, int(120 * a)), outline=(255, 255, 255, int(170 * a)), width=3)
    fr.paste(Image.alpha_composite(fr.convert("RGBA"), ov).convert("RGB"))

def ease(u): u = max(0, min(1, u)); return u * u * (3 - 2 * u)

def view(name, scroll):
    im = img[name]; s = int(min(scroll, im.height - H))
    return im.crop((0, s, W, s + H)).copy()

# ---------- timeline ----------
# (name, start, end, scroll_from, scroll_to, caption lines)
SC = [
    ("home",     0.0,  3.4,   0,   0, ["pov: you stopped using", "6 apps to run your life"]),
    ("home",     3.4,  4.8,   0, 333, None),
    ("projects", 4.8,  8.0,   0, 470, ["projects track their", "own progress"]),
    ("tasks",    8.0, 11.2,   0, 640, ["and it tells me", "when i'm late lol"]),
    ("habits",  11.2, 13.8,   0,   0, ["habits score themselves"]),
    ("more",    13.8, 16.0,   0, 640, ["+ inbox, notes, goals,", "journal, ideas..."]),
    ("home",    16.0, 19.0,   0,   0, ["Second Brain OS", "link in bio"]),
]
TOTAL = 19.0; TR = 0.28

def scene_at(t):
    for i, s in enumerate(SC):
        if s[1] <= t < s[2]: return i
    return len(SC) - 1

def render_scene(i, t):
    n, a, b, s0, s1, cap = SC[i]
    u = (t - a) / (b - a)
    scroll = s0 + (s1 - s0) * ease((u - 0.15) / 0.7) if s1 != s0 else 0
    fr = view(n, scroll)
    if n == "home":
        draw_brain(fr, t, bx, by - scroll)
        if i == 0 or i == len(SC) - 1:  # slow push-in, like a held phone zoom
            z = 1 + 0.05 * u; cw, ch = int(W / z), int(H / z)
            fr = fr.crop(((W - cw) // 2, (H - ch) // 3, (W - cw) // 2 + cw, (H - ch) // 3 + ch)).resize((W, H), Image.LANCZOS)
    if s1 != s0 and 0.1 < u < 0.9:  # finger dragging up while scrolling
        k = ease((u - 0.15) / 0.7); touch(fr, 760, 1500 - 420 * k, 0.9)
    if i == 1 and u > 0.82:         # tap on "Projects"
        touch(fr, mx, my - 333, 1.0)
    if cap:
        last = i == len(SC) - 1
        caption(fr, cap, 760 if last else 300, 74 if last else 58)
    return fr

p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                      "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                      "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
for f in range(int(TOTAL * FPS)):
    t = f / FPS; i = scene_at(t)
    fr = render_scene(i, t)
    if i > 0 and t - SC[i][1] < TR and SC[i][0] != SC[i - 1][0]:  # iOS-style push transition
        u = ease((t - SC[i][1]) / TR)
        prev = render_scene(i - 1, SC[i - 1][2] - 0.001)
        canvas = Image.new("RGB", (W, H)); canvas.paste(prev, (int(-W * 0.3 * u), 0)); canvas.paste(fr, (int(W * (1 - u)), 0)); fr = canvas
    p.stdin.write(fr.tobytes())
p.stdin.close(); p.wait()
print("done", OUT)
