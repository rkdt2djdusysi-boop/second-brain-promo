# -*- coding: utf-8 -*-
"""
generer_video.py  -  "Stop Making This Mistake If You Want to Grow Your Business"
Video TikTok verticale (9:16), style minimaliste noir et blanc, sous-titres jaunes.

Pour fabriquer la video :      python generer_video.py
Pour un apercu rapide (images) : python generer_video.py --apercu

Si un fichier "voix.mp3" (ElevenLabs) est dans le meme dossier, il est ajoute automatiquement.
"""
import math, os, sys, subprocess, wave
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# =========================== REGLAGES (modifiables) ===========================
LARGEUR, HAUTEUR = 720, 1280        # format vertical TikTok
FPS = 30
QUALITE = 18                        # plus petit = plus beau (et plus lourd)
PSEUDO = "@MTM"
APPEL_FIN = "+ FOLLOW"
DEVISE = "$"
VOIX_FICHIER = "voix.mp3"
VITESSE_VOIX = 1.06                 # 1.0 = vitesse normale ; 1.06 = 6 % plus rapide (plus dynamique)
FICHIER_SORTIE = "video_mistake.mp4"
JAUNE = (255, 212, 0)               # couleur des sous-titres
ROUGE = (235, 55, 45)
SOUS_TITRE_Y = 1000                 # hauteur des sous-titres
# ==============================================================================

SS = 2          # sur-echantillonnage (bords lisses)
SR = 44100      # frequence audio


# ------------------------------------------------------------------ outils
def cl(x, a=0.0, b=1.0):
    return max(a, min(b, x))

def pr(t, a, b):
    if b <= a:
        return 1.0 if t >= a else 0.0
    return cl((t - a) / (b - a))

def e_out(x):
    x = cl(x); return 1 - (1 - x) ** 3

def e_inout(x):
    x = cl(x); return 3 * x * x - 2 * x * x * x

def e_back(x):
    x = cl(x); c = 1.70158
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2

def pop(t, a, dur=0.35):
    return e_back(pr(t, a, a + dur))

def g(v, k=1.0):
    v = int(cl(v * k, 0, 255)); return (v, v, v)

def mul(c, k):
    return tuple(int(cl(x * k, 0, 255)) for x in c)


# ------------------------------------------------------------------ polices
_D = "/usr/share/fonts/opentype/inter/"
_W = "C:/Windows/Fonts/"
POLICES = {
    "black":  ["Inter-Black.otf", _D + "Inter-Black.otf", _D + "Inter-ExtraBold.otf", _W + "Inter-Black.ttf",
               _W + "ariblk.ttf", _W + "seguibl.ttf", _W + "arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "bold":   ["Inter-Bold.otf", _D + "Inter-Bold.otf", _W + "Inter-Bold.ttf", _W + "segoeuib.ttf", _W + "arialbd.ttf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "medium": ["Inter-Medium.otf", _D + "Inter-Medium.otf", _W + "Inter-Medium.ttf", _W + "segoeui.ttf", _W + "arial.ttf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
}
_cache = {}

def police(nom, taille):
    taille = max(1, int(round(taille)))
    cle = (nom, taille)
    if cle not in _cache:
        for chemin in POLICES[nom]:
            if os.path.exists(chemin):
                _cache[cle] = ImageFont.truetype(chemin, taille)
                break
        else:
            _cache[cle] = ImageFont.load_default()
    return _cache[cle]


# ------------------------------------------------------------------ stylo
class Stylo:
    """Dessine dans un repere fixe 720x1280, quelle que soit la resolution reelle."""
    def __init__(s, img, k=SS):
        s.d = ImageDraw.Draw(img); s.k = k

    def cercle(s, x, y, r, fill=None, outline=None, w=1):
        k = s.k; r = max(r, 0.5)
        s.d.ellipse([(x - r) * k, (y - r) * k, (x + r) * k, (y + r) * k], fill=fill, outline=outline,
                    width=max(1, int(round(w * k))))

    def ellipse(s, x, y, rx, ry, fill=None, outline=None, w=1):
        k = s.k; rx = max(rx, 0.5); ry = max(ry, 0.5)
        s.d.ellipse([(x - rx) * k, (y - ry) * k, (x + rx) * k, (y + ry) * k], fill=fill, outline=outline,
                    width=max(1, int(round(w * k))))

    def rrect(s, x0, y0, x1, y1, r, fill=None, outline=None, w=1):
        k = s.k
        if x1 < x0: x0, x1 = x1, x0
        if y1 < y0: y0, y1 = y1, y0
        if x1 - x0 < 1 or y1 - y0 < 1:
            return
        r = max(0, min(r, (x1 - x0) / 2 - 0.6, (y1 - y0) / 2 - 0.6))
        s.d.rounded_rectangle([x0 * k, y0 * k, x1 * k, y1 * k], radius=r * k, fill=fill, outline=outline,
                              width=max(1, int(round(w * k))))

    def ligne(s, pts, col, w):
        if len(pts) < 2: return
        k = s.k
        s.d.line([(x * k, y * k) for x, y in pts], fill=col, width=max(1, int(round(w * k))), joint="curve")
        for x, y in (pts[0], pts[-1]):
            s.cercle(x, y, w / 2, fill=col)

    def poly(s, pts, fill):
        s.d.polygon([(x * s.k, y * s.k) for x, y in pts], fill=fill)

    def texte(s, x, y, txt, taille, col, nom="bold", anchor="mm", contour=0, col_contour=(0, 0, 0)):
        if taille < 1: return
        s.d.text((x * s.k, y * s.k), txt, font=police(nom, taille * s.k), fill=col, anchor=anchor,
                 stroke_width=int(round(contour * s.k)), stroke_fill=col_contour)

    def largeur(s, txt, taille, nom="bold"):
        return s.d.textlength(txt, font=police(nom, taille * s.k)) / s.k


# ------------------------------------------------------------------ pictogrammes
def tracer(p, pts, prog, col, w):
    """Ligne qui se dessine progressivement (prog de 0 a 1)."""
    prog = cl(prog)
    if prog <= 0: return
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    reste = sum(seg) * prog
    out = [pts[0]]
    for i, l in enumerate(seg):
        if reste >= l:
            out.append(pts[i + 1]); reste -= l
        else:
            a = reste / l if l > 0 else 0
            out.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * a, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * a))
            break
    p.ligne(out, col, w)

def bonhomme(p, x, y, t, col=(255, 255, 255), plein=True, humeur=1.0, regard=0.0):
    """(x, y) = centre du buste ; t = taille ; humeur 1 = sourire, -1 = triste."""
    if plein:
        p.rrect(x - 0.62 * t, y - 0.35 * t, x + 0.62 * t, y + 0.95 * t, 0.55 * t, fill=col)
        p.cercle(x, y - 0.85 * t, 0.42 * t, fill=col)
        ox = regard * 0.13 * t
        for dx in (-0.14, 0.14):
            p.cercle(x + dx * t + ox, y - 0.92 * t, 0.055 * t, fill=(0, 0, 0))
        pts = []
        for i in range(9):
            u = -1 + i / 4
            pts.append((x + u * 0.15 * t + ox * 0.8, y - 0.76 * t + humeur * 0.08 * t * (1 - u * u)))
        p.ligne(pts, (0, 0, 0), 0.05 * t)
    else:
        w = max(2, 0.07 * t)
        p.rrect(x - 0.62 * t, y - 0.35 * t, x + 0.62 * t, y + 0.95 * t, 0.55 * t, outline=col, w=w)
        p.cercle(x, y - 0.85 * t, 0.42 * t, outline=col, w=w)

def piece(p, x, y, r, k=1.0, sx=1.0):
    sx = max(0.08, abs(sx))
    p.ellipse(x, y, r * 1.35 * sx, r * 1.35, fill=g(45, k))          # halo
    p.ellipse(x, y, r * sx, r, fill=g(255, k))
    p.ellipse(x, y, r * 0.78 * sx, r * 0.78, outline=g(0), w=r * 0.08)
    if sx > 0.55:
        p.texte(x, y + r * 0.04, DEVISE, r * 1.05, g(0), "black")

def engrenage(p, x, y, r, rot, col, trou=(0, 0, 0)):
    pts = []; n = 9
    for i in range(n * 4):
        a = rot + i * 2 * math.pi / (n * 4)
        rr = r if (i % 4) in (1, 2) else r * 0.78
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    p.poly(pts, col)
    p.cercle(x, y, r * 0.32, fill=trou)

def etoile(p, x, y, r, col, branches=5, creux=0.45, rot=-math.pi / 2):
    pts = []
    for i in range(branches * 2):
        rr = r if i % 2 == 0 else r * creux
        a = rot + i * math.pi / branches
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    p.poly(pts, col)

def coche(p, x, y, s, prog, col, w):
    tracer(p, [(x - 0.5 * s, y), (x - 0.15 * s, y + 0.35 * s), (x + 0.55 * s, y - 0.4 * s)], prog, col, w)

def bulle(p, x, y, w, h, s, cible, fond, bord, epais=4):
    """Bulle de dialogue centree en (x, y), avec une pointe vers 'cible'."""
    if s <= 0.01: return
    w, h = w * s, h * s
    dx, dy = cible[0] - x, cible[1] - y
    n = math.hypot(dx, dy) or 1; dx, dy = dx / n, dy / n
    px, py = -dy, dx
    base = (x + dx * h * 0.3, y + dy * h * 0.3)
    pointe = (x + dx * (h * 0.5 + 34 * s), y + dy * (h * 0.5 + 34 * s))
    p.poly([(base[0] + px * 16 * s, base[1] + py * 16 * s), (base[0] - px * 16 * s, base[1] - py * 16 * s), pointe],
           bord)
    p.rrect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, min(w, h) * 0.45, fill=fond, outline=bord, w=epais)

def curseur(p, x, y, s=1.0):
    forme = [(0, 0), (0, 46), (12, 35), (21, 55), (29, 51), (20, 32), (36, 32)]
    pts = [(x + a * s, y + b * s) for a, b in forme]
    p.poly([(a + 3, b + 3) for a, b in pts], (0, 0, 0))
    p.poly(pts, (255, 255, 255))

def pouce(p, x, y, s, col=(255, 255, 255)):
    if s <= 0.01: return
    p.rrect(x - 45 * s, y - 10 * s, x + 45 * s, y + 70 * s, 18 * s, fill=col)          # poing
    p.rrect(x - 42 * s, y - 78 * s, x - 2 * s, y + 10 * s, 19 * s, fill=col)           # pouce
    p.rrect(x - 82 * s, y - 6 * s, x - 54 * s, y + 74 * s, 8 * s, fill=col)            # manche
    for dy in (14, 34, 54):
        p.ligne([(x - 4 * s, y + dy * s), (x + 44 * s, y + dy * s)], (0, 0, 0), 4 * s)


# ------------------------------------------------------------------ SCENE 1 : une annee partie en fumee
MOIS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
_rng = np.random.default_rng(7)
FUMEE = [(_rng.uniform(-150, 150), _rng.uniform(-120, 150), _rng.uniform(-60, 60), _rng.uniform(90, 230),
          _rng.uniform(7, 18), _rng.uniform(0.6, 1.0)) for _ in range(90)]

def calendrier(p, cx, cy, s, mois, f, k, cases):
    col = g(255, k)
    for dx in (-80, 80):
        p.rrect(cx + (dx - 9) * s, cy - 148 * s, cx + (dx + 9) * s, cy - 100 * s, 8 * s, fill=g(160, k))
    p.rrect(cx - 150 * s, cy - 125 * s, cx + 150 * s, cy + 150 * s, 26 * s, outline=col, w=5 * s)
    p.rrect(cx - 150 * s, cy - 125 * s, cx + 150 * s, cy - 50 * s, 26 * s, fill=col)
    p.rrect(cx - 150 * s, cy - 80 * s, cx + 150 * s, cy - 50 * s, 0, fill=col)
    p.texte(cx, cy - 87 * s, mois, 46 * s, g(0), "black")
    for i in range(28):
        r, c = divmod(i, 7)
        x = cx + (c - 3) * 38 * s; y = cy - 8 * s + r * 38 * s
        if i < cases:
            p.rrect(x - 13 * s, y - 13 * s, x + 13 * s, y + 13 * s, 5 * s, fill=g(235, k))
        else:
            p.rrect(x - 13 * s, y - 13 * s, x + 13 * s, y + 13 * s, 5 * s, outline=g(85, k), w=2 * s)
    if f < 0.3:   # page qui s'arrache
        hf = (1 - e_out(f / 0.3)) * 200 * s
        p.rrect(cx - 146 * s, cy - 50 * s, cx + 146 * s, cy - 50 * s + hf, 8 * s, fill=g(205, k))

def scene_annee(p, t, D):
    cx, cy = 360, 660
    s = pop(t, 0.2)
    fum = pr(t, 1.35, 1.7)
    if s > 0 and fum < 1:
        a = pr(t, 0.4, 1.3) * 12
        m = min(11, int(a)); f = a - int(a) if a < 12 else 1.0
        calendrier(p, cx, cy, s, MOIS[m], f, 1 - fum, int(f * 28) if a < 12 else 28)
    if t >= 1.35:
        u = t - 1.35
        for bx, by, dx, vy, r0, b in FUMEE:
            v = 200 * b * (1 - pr(u, 0.1, 1.1)) * pr(u, 0, 0.08)
            if v > 3:
                p.cercle(cx + bx + dx * u, cy + by - vy * u - 70 * u * u, r0 + 34 * u, fill=g(v))
    # gros texte qui zoome (dessine en dernier pour rester devant la fumee)
    z1 = 1 + 1.8 * (1 - e_out(pr(t, 0, 0.45)))
    p.texte(360, 205, "I WASTED", 96 * z1, g(255, pr(t, 0, 0.1)), "black", contour=4)
    z2 = 1 + 1.8 * (1 - e_out(pr(t, 0.15, 0.6)))
    p.texte(360, 330, "A YEAR", 150 * z2, g(255, pr(t, 0.15, 0.25)), "black", contour=5)


# ------------------------------------------------------------------ SCENE 2 : le produit que personne n'a demande
def scene_produit(p, t, D):
    sol = 787
    p.ligne([(60, sol), (660, sol)], g(70), 3)
    # cube
    x0, y0, x1, y1, o = 410, 667, 530, sol, 36
    kf = pr(t, 1.1, 1.3)
    if kf > 0:
        p.poly([(x0, y0), (x1, y0), (x1 + o, y0 - o), (x0 + o, y0 - o)], g(195, kf))
        p.poly([(x1, y0), (x1 + o, y0 - o), (x1 + o, y1 - o), (x1, y1)], g(130, kf))
        p.rrect(x0, y0, x1, y1, 0, fill=g(255, kf))
        if kf > 0.5:
            etoile(p, (x0 + x1) / 2, (y0 + y1) / 2, 34, (0, 0, 0))
    aretes = [[(x0, y1), (x1, y1)], [(x0, y1), (x0, y0)], [(x1, y1), (x1, y0)], [(x0, y0), (x1, y0)],
              [(x0, y0), (x0 + o, y0 - o)], [(x1, y0), (x1 + o, y0 - o)], [(x0 + o, y0 - o), (x1 + o, y0 - o)],
              [(x1 + o, y0 - o), (x1 + o, y1 - o)], [(x1, y1), (x1 + o, y1 - o)]]
    pb = pr(t, 0.1, 1.1) * len(aretes)
    for i, a in enumerate(aretes):
        tracer(p, a, pb - i, g(255), 4)
    if 1.25 < t < 1.9:   # petites etincelles
        u = pr(t, 1.25, 1.9)
        for i, (ex, ey) in enumerate([(395, 640), (570, 610), (560, 760), (470, 600)]):
            r = 14 * math.sin(math.pi * cl(u * 1.4 - i * 0.12))
            if r > 1: etoile(p, ex, ey, r, g(255), 4, 0.25, 0)
    # bonhomme
    abat = e_inout(pr(t, 2.0, 2.3))
    bx, by, tb = 225, 701 + 6 * abat, 90
    humeur = 1.0 - 1.8 * abat
    # bras + marteau
    if t < 1.1:
        ph = abs(math.sin(t * 12))
    else:
        ph = 0.15
    ang = -1.45 + 1.35 * ph
    mx, my = bx + 70, by + 10
    p.ligne([(bx + 30, by + 5), (mx, my)], g(255), 15)
    ex, ey = mx + 62 * math.cos(ang), my + 62 * math.sin(ang)
    p.ligne([(mx, my), (ex, ey)], g(200), 7)
    nx, ny = -math.sin(ang), math.cos(ang)
    p.ligne([(ex - nx * 17, ey - ny * 17), (ex + nx * 17, ey + ny * 17)], g(255), 15)
    bonhomme(p, bx, by, tb, humeur=humeur, regard=0.6 if t < 2.0 else 0.2)
    # panneau "0 customers"
    if t > 1.55:
        u = pr(t, 1.55, 1.95)
        yc = -150 + (525 + 150) * e_back(u)
        sw = 10 * math.sin((t - 1.95) * 7) * math.exp(-(t - 1.95) * 2.5) if t > 1.95 else 0
        x0s, x1s = 110 + sw, 610 + sw
        p.ligne([(230, 0), (x0s + 60, yc - 60)], g(130), 3)
        p.ligne([(490, 0), (x1s - 60, yc - 60)], g(130), 3)
        p.rrect(x0s, yc - 62, x1s, yc + 62, 22, fill=g(255))
        w0 = p.largeur("0", 62, "black"); w1 = p.largeur("CUSTOMERS", 56, "black")
        xd = (x0s + x1s) / 2 - (w0 + 18 + w1) / 2
        p.texte(xd, yc + 2, "0", 62, ROUGE, "black", anchor="lm")
        p.texte(xd + w0 + 18, yc + 2, "CUSTOMERS", 56, g(0), "black", anchor="lm")


# ------------------------------------------------------------------ SCENE 3 : 12 mois, zero vente
def icone(p, x, y, s, genre, t):
    if s <= 0.01: return
    h = 70 * s
    p.rrect(x - h, y - h, x + h, y + h, 28 * s, fill=g(255))
    if genre == "logo":
        etoile(p, x, y + 3 * s, 42 * s, (0, 0, 0))
    elif genre == "site":
        p.rrect(x - 44 * s, y - 34 * s, x + 44 * s, y + 36 * s, 10 * s, outline=g(0), w=5 * s)
        p.ligne([(x - 44 * s, y - 16 * s), (x + 44 * s, y - 16 * s)], g(0), 5 * s)
        for i in range(3):
            p.cercle(x - 33 * s + i * 10 * s, y - 25 * s, 3 * s, fill=g(0))
        p.ligne([(x - 30 * s, y + 2 * s), (x + 30 * s, y + 2 * s)], g(0), 5 * s)
        p.ligne([(x - 30 * s, y + 18 * s), (x + 10 * s, y + 18 * s)], g(0), 5 * s)
    else:
        engrenage(p, x, y, 44 * s, t * 1.5, g(0), trou=g(255))

def scene_ventes(p, t, D):
    k = 1 - 0.55 * pr(t, 1.4, 1.7)
    p.texte(360, 205, "12 MONTHS OF PERFECTING", 34, g(210, k), "bold")
    p.rrect(110, 245, 610, 281, 18, outline=g(130, k), w=3)
    rempli = e_inout(pr(t, 0.1, 1.35))
    if rempli > 0.04:
        p.rrect(116, 251, 116 + 488 * rempli, 275, 12, fill=g(255, k))
    p.texte(360, 318, f"{int(rempli * 100)}%", 30, g(160, k), "medium")
    for i, (x, genre) in enumerate([(150, "logo"), (360, "site"), (570, "engrenage")]):
        ta = (1.55, 2.1, 2.85)[i]
        icone(p, x, 480, pop(t, ta), genre, t)
        sb = pop(t, ta + 0.25, 0.25)
        if sb > 0.01:
            p.cercle(x + 55, 545, 25 * sb, fill=JAUNE, outline=g(0), w=4)
            coche(p, x + 55, 547, 26 * sb, pr(t, ta + 0.3, ta + 0.5), g(0), 6)
    sc = pop(t, 3.45)
    if sc > 0.01:
        p.texte(360, 680, "SALES", 42 * sc, g(170), "bold")
        if t < 3.65:
            col = g(255)
        else:
            col = ROUGE if int((t - 3.65) / 0.25) % 2 == 0 else (95, 22, 18)
        p.texte(360, 830, "0", 230 * sc, col, "black")


# ------------------------------------------------------------------ SCENE 4 : parler aux clients D'ABORD
def scene_clients(p, t, D):
    fl = 1 - pr(t, 0, 0.28)
    if fl > 0:
        p.rrect(0, 0, LARGEUR, HAUTEUR, 0, fill=g(255 * fl * 0.9))
    cx, cy = 360, 760
    regard = cl(math.sin(t * 2.3) * 1.2, -0.9, 0.9) if t > 0.3 else 0
    bonhomme(p, cx, cy, 100, humeur=0.6, regard=regard)
    pos = [(150, 560), (570, 560), (125, 790), (595, 790)]
    for i, (x, y) in enumerate(pos):
        s = pop(t, 0.4 + 0.25 * i)
        if s > 0.01:
            bulle(p, x, y, 150, 86, s, (cx, cy - 60), g(25), g(235))
            for j in range(3):
                bond = max(0, math.sin(t * 7 - j * 0.8 - i)) * 6
                p.cercle(x + (j - 1) * 26 * s, y - bond * s, 7 * s, fill=g(255))
    sf = pop(t, 1.85, 0.35)
    if sf > 0.01:
        puls = 1 + 0.07 * math.sin((t - 1.85) * 9) if t > 2.2 else 1
        p.texte(360, 320, "FIRST", 175 * sf * puls, g(255), "black")


# ------------------------------------------------------------------ SCENE 5 : une question, puis ecouter
REPONSES = ["Too expensive", "No time", "Can't find clients", "Too complicated", "Hard to get help"]

def scene_question(p, t, D):
    bulle(p, 360, 300, 250, 170, pop(t, 0.2), (215, 690), g(255), g(255))
    sq = pop(t, 0.35)
    if sq > 0.01:
        p.texte(360, 302, "?", 125 * sq, g(0), "black")
    bonhomme(p, 185, 800, 85, humeur=0.7, regard=0.7)
    # carnet
    p.rrect(262, 722, 386, 885, 14, fill=g(18), outline=g(235), w=4)
    for i in range(5):
        p.cercle(285 + i * 20, 722, 5, fill=g(235))
    ecrit = pr(t, 1.8, 4.2) * 6
    plume = None
    for i in range(6):
        u = cl(ecrit - i)
        if u > 0:
            y = 758 + i * 21
            xe = 280 + (88 if i % 2 == 0 else 62) * u
            p.ligne([(280, y), (xe, y)], g(220), 3)
            if u < 1: plume = (xe, y)
    if plume:
        x, y = plume
        p.ligne([(x + 4, y - 4), (x + 30, y - 40)], JAUNE, 6)
    # reponses qui defilent
    for i, txt in enumerate(REPONSES):
        ti = 1.6 + 0.45 * i
        if t < ti: continue
        y = 870 - 160 * (t - ti)
        k = pr(t, ti, ti + 0.25) * pr(y, 470, 560)
        if k <= 0: continue
        s = e_back(pr(t, ti, ti + 0.3))
        p.rrect(525 - 110 * s, y - 31 * s, 525 + 110 * s, y + 31 * s, 16, fill=g(22, k), outline=g(180, k), w=3)
        p.texte(525, y, txt, 26 * s, g(255, k), "medium")


# ------------------------------------------------------------------ SCENE 6 : vendre avant de construire
def scene_precommande(p, t, D):
    bx, by = 360, 300
    s = pop(t, 0) * (1 - 0.08 * math.sin(math.pi * pr(t, 0.85, 1.05)))
    if s > 0.01:
        p.rrect(bx - 190 * s, by - 55 * s, bx + 190 * s, by + 55 * s, 30 * s, fill=g(255))
        p.texte(bx, by + 2, "PRE-ORDER", 54 * s, g(0), "black")
    if t < 1.35:   # curseur qui clique
        u = e_inout(pr(t, 0.15, 0.75))
        curseur(p, 640 - 220 * u, 600 - 270 * u, 1.0 - 0.1 * math.sin(math.pi * pr(t, 0.85, 1.0)))
    if 0.85 < t < 1.4:
        u = pr(t, 0.85, 1.35)
        p.cercle(420, 330, 20 + 90 * u, outline=g(255 * (1 - u)), w=4)
    # piece qui tombe
    if t > 1.45:
        u = pr(t, 1.45, 1.8)
        y = 360 + 240 * u * u
        if t > 1.8:
            y -= abs(math.sin((t - 1.8) * math.pi / 0.3)) * 30 * math.exp(-(t - 1.8) * 5) if t < 2.4 else 0
        piece(p, 245, y, 46, pop(t, 1.45, 0.2), sx=math.cos(t * 9) if t < 1.85 else 1.0)
    pouce(p, 475, 610, pop(t, 2.0, 0.35))
    kp = pr(t, 2.1, 2.3)
    if kp > 0:
        p.texte(360, 725, "PAY = BUILD", 36, g(255, kp), "bold")
    tracer(p, [(80, 790), (640, 790)], pr(t, 2.45, 2.75), g(70), 3)
    tracer(p, [(140, 840), (200, 900)], pr(t, 2.75, 2.88), ROUGE, 14)
    tracer(p, [(200, 840), (140, 900)], pr(t, 2.88, 3.0), ROUGE, 14)
    kx = pr(t, 2.85, 3.05)
    if kx > 0:
        p.texte(235, 870, "NO PAY = PIVOT", 42, g(255, kx), "black", anchor="lm")


# ------------------------------------------------------------------ SCENE 7 : partie 2 + follow
def scene_fin(p, t, D):
    sp = pop(t, 0, 0.4)
    if sp > 0.01:
        p.texte(360, 380, "PART 2", 165 * sp, g(255), "black")
    sa = pr(t, 0.3, 0.6)
    if sa > 0:
        off = 22 * math.sin((t - 0.3) * 8)
        xe = 250 + (190 + off) * e_out(sa)
        p.ligne([(250, 530), (xe, 530)], JAUNE, 12)
        p.poly([(xe + 32, 530), (xe - 4, 506), (xe - 4, 554)], JAUNE)
    ks = pr(t, 0.45, 0.7)
    if ks > 0:
        p.rrect(140, 645, 580, 715, 35, outline=g(150, ks), w=3)
        p.cercle(182, 676, 13, outline=g(200, ks), w=4)
        p.ligne([(192, 687), (204, 699)], g(200, ks), 5)
        n = int(pr(t, 0.6, 1.3) * len(PSEUDO) + 0.001)
        p.texte(222, 680, PSEUDO[:n], 36, g(255, ks), "bold", anchor="lm")
        if int(t * 3) % 2 == 0:
            xc = 226 + p.largeur(PSEUDO[:n], 36, "bold")
            p.ligne([(xc, 662), (xc, 698)], g(255, ks), 3)
    sf = pop(t, 1.4, 0.35)
    if sf > 0.01:
        y = 840 - (abs(math.sin((t - 1.75) * 7)) * 18 if t > 1.75 else 0)
        p.rrect(470 - 120 * sf, y - 43 * sf, 470 + 120 * sf, y + 43 * sf, 43 * sf, fill=g(255))
        p.texte(470, y + 2, APPEL_FIN, 38 * sf, g(0), "black")


# ------------------------------------------------------------------ LES SCENES
# textes = (debut, fin, "sous-titre") en secondes dans la scene
# voix   = (moment_dans_scene, debut_dans_mp3, fin_dans_mp3)  -> a remplir une fois voix.mp3 recue
# sons   = bruitages (moment, type)
SCENES = [
    dict(f=scene_annee, duree=2.3, fondu_entree=False,
         textes=[(0.0, 1.3, "I wasted a year doing this,"), (1.3, 2.3, "so you don't have to.")],
         voix=[(0.05, 0.00, 1.18), (1.35, 2.04, 2.78)],
         sons=[(0.0, "boum"), (0.15, "boum")] + [(0.4 + i * 0.075, "clic") for i in range(12)] + [(1.35, "souffle")]),
    dict(f=scene_produit, duree=3.0,
         textes=[(0.0, 0.7, "The mistake?"), (0.7, 3.0, "Building a product nobody asked for.")],
         voix=[(0.10, 3.74, 4.26), (0.75, 5.08, 6.95)],
         sons=[((math.pi / 2 + math.pi * k) / 12, "clic") for k in range(4)] + [(1.3, "bip"), (1.9, "boum"), (2.05, "erreur")]),
    dict(f=scene_ventes, duree=4.8,
         textes=[(0.0, 1.5, "I spent twelve months perfecting it."), (1.5, 3.45, "Logo. Website. Features."),
                 (3.45, 4.8, "Zero sales.")],
         voix=[(0.05, 7.75, 9.18), (1.55, 9.97, 10.42), (2.10, 11.19, 11.85), (2.85, 12.70, 13.22), (3.55, 14.11, 15.00)],
         sons=[(1.55, "pop"), (2.1, "pop"), (2.85, "pop"), (1.8, "bip"), (2.35, "bip"), (3.1, "bip"), (3.45, "boum"),
               (3.65, "erreur"), (4.15, "erreur")]),
    dict(f=scene_clients, duree=3.2, fondu_entree=False,
         textes=[(0.0, 1.1, "Here's what I should have done:"), (1.1, 3.2, "talk to customers first.")],
         voix=[(0.10, 16.11, 17.03), (1.15, 17.91, 19.07)],
         sons=[(0.0, "boum")] + [(0.4 + 0.25 * i, "pop") for i in range(4)] + [(1.85, "boum")]),
    dict(f=scene_question, duree=4.4,
         textes=[(0.0, 1.15, "Ask one question:"), (1.15, 2.9, "what's your biggest problem right now?"),
                 (2.9, 4.4, "Then listen.")],
         voix=[(0.10, 19.91, 20.92), (1.25, 21.90, 23.40), (3.00, 24.63, 25.23)],
         sons=[(0.15, "pop")] + [(1.6 + 0.45 * i, "pop") for i in range(5)]),
    dict(f=scene_precommande, duree=4.2,
         textes=[(0.0, 1.35, "Then sell it before you build it."), (1.35, 2.7, "If they pay, you build."),
                 (2.7, 4.2, "If not, you move on.")],
         voix=[(0.05, 26.04, 27.30), (1.40, 28.27, 29.51), (2.75, 30.31, 31.45)],
         sons=[(0.0, "pop"), (0.85, "clic"), (1.8, "piece"), (2.0, "pop"), (2.75, "erreur")]),
    dict(f=scene_fin, duree=4.0,
         textes=[(0.0, 1.35, "Part 2 tomorrow:"), (1.35, 4.0, "how I got my first 10 customers.")],
         voix=[(0.05, 32.65, 33.15), (0.68, 34.12, 37.02)],
         sons=[(0.0, "boum")] + [(0.6 + 0.15 * i, "clic") for i in range(4)] + [(1.4, "pop")]),
]


# ------------------------------------------------------------------ rendu d'une image
def sous_titres(img, textes, t, D):
    p = Stylo(img, 1)
    taille, inter = 44, 56
    for a, b, txt in textes:
        if not (a <= t < b): continue
        k = pr(t, a, a + 0.12)
        if b < D - 0.05:
            k = min(k, pr(b - t, 0, 0.12))
        if k <= 0: continue
        mots, lignes, cur = txt.split(), [], ""
        for m in mots:
            essai = (cur + " " + m).strip()
            if p.largeur(essai, taille) > 640 and cur:
                lignes.append(cur); cur = m
            else:
                cur = essai
        lignes.append(cur)
        if len(lignes) == 2:   # deux lignes equilibrees (pas de mot tout seul)
            coupes = [(" ".join(mots[:c]), " ".join(mots[c:])) for c in range(1, len(mots))]
            lignes = list(min(coupes, key=lambda c: max(p.largeur(c[0], taille), p.largeur(c[1], taille))))
        lmax = max(p.largeur(l, taille) for l in lignes)
        y0 = SOUS_TITRE_Y + (1 - e_out(k)) * 12 - (len(lignes) - 1) * inter / 2
        p.rrect(360 - lmax / 2 - 26, y0 - inter / 2 - 8, 360 + lmax / 2 + 26, y0 + (len(lignes) - 0.5) * inter + 8,
                24, fill=g(16, k))
        for i, l in enumerate(lignes):
            p.texte(360, y0 + i * inter, l, taille, mul(JAUNE, k), "bold", contour=2, col_contour=g(0))

def image(i, t):
    sc = SCENES[i]; D = sc["duree"]
    grand = Image.new("RGB", (LARGEUR * SS, HAUTEUR * SS), (0, 0, 0))
    sc["f"](Stylo(grand), t, D)
    img = grand.resize((LARGEUR, HAUTEUR), Image.LANCZOS)
    a = np.asarray(img).astype(np.float32)
    petit = img.resize((LARGEUR // 4, HAUTEUR // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(5))
    lueur = np.asarray(petit.resize((LARGEUR, HAUTEUR), Image.BILINEAR)).astype(np.float32)
    a = np.minimum(a + lueur * 0.75, 255)
    k = 1.0
    if sc.get("fondu_entree", True): k *= e_inout(pr(t, 0, 0.08))
    if sc.get("fondu_sortie", True): k *= e_inout(pr(D - t, 0, 0.08))
    if k < 1: a *= k
    img = Image.fromarray(a.astype(np.uint8))
    z = 1 + 0.07 * (1 - e_out(pr(t, 0, 0.3)))   # petit zoom 'punch' au debut de chaque scene
    if z > 1.001:
        w2, h2 = LARGEUR / z, HAUTEUR / z
        img = img.resize((LARGEUR, HAUTEUR), Image.BICUBIC,
                         box=((LARGEUR - w2) / 2, (HAUTEUR - h2) / 2, (LARGEUR + w2) / 2, (HAUTEUR + h2) / 2))
    sous_titres(img, sc["textes"], t, D)
    return img

def rendre_scene(i):
    sc = SCENES[i]
    nb = int(round(sc["duree"] * FPS))
    chemin = f"scene_{i + 1:02d}.mp4"; tmp = chemin + ".tmp.mp4"
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{LARGEUR}x{HAUTEUR}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(QUALITE),
           "-pix_fmt", "yuv420p", tmp]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for n in range(nb):
        proc.stdin.write(image(i, n / FPS).tobytes())
    proc.stdin.close(); proc.wait()
    os.replace(tmp, chemin)
    return chemin


# ------------------------------------------------------------------ son
def _env(n, tau):
    return np.exp(-np.arange(n) / SR / tau)

def bruitage(nom):
    rng = np.random.default_rng(len(nom))
    if nom == "bip":
        n = int(0.12 * SR); tt = np.arange(n) / SR
        return 0.22 * np.sin(2 * np.pi * 880 * tt) * _env(n, 0.04)
    if nom == "pop":
        n = int(0.12 * SR); tt = np.arange(n) / SR
        ph = 2 * np.pi * np.cumsum(400 + 900 * tt / 0.12) / SR
        return 0.28 * np.sin(ph) * _env(n, 0.05)
    if nom == "clic":
        n = int(0.03 * SR)
        return 0.25 * rng.uniform(-1, 1, n) * _env(n, 0.006)
    if nom == "piece":
        n = int(0.5 * SR); tt = np.arange(n) / SR
        return (0.16 * np.sin(2 * np.pi * 1320 * tt) + 0.12 * np.sin(2 * np.pi * 1760 * tt)
                + 0.06 * np.sin(2 * np.pi * 2640 * tt)) * _env(n, 0.13)
    if nom == "boum":
        n = int(0.45 * SR); tt = np.arange(n) / SR
        ph = 2 * np.pi * np.cumsum(40 + 110 * np.exp(-tt * 9)) / SR
        return 0.6 * np.sin(ph) * _env(n, 0.14)
    if nom == "erreur":
        n = int(0.2 * SR); tt = np.arange(n) / SR
        return 0.14 * (np.sin(2 * np.pi * 196 * tt) + 0.5 * np.sin(2 * np.pi * 588 * tt)) * _env(n, 0.08)
    if nom == "souffle":
        n = int(0.5 * SR); tt = np.arange(n) / SR
        b = np.convolve(rng.uniform(-1, 1, n), np.ones(25) / 25, mode="same")
        return 1.4 * b * np.sin(np.pi * tt / 0.5) ** 2
    return np.zeros(1)

def ajouter(piste, son, t):
    d = int(t * SR)
    if d >= len(piste) or d < 0: return
    f = min(len(son), len(piste) - d)
    piste[d:d + f] += son[:f]

def charger_voix():
    if not os.path.exists(VOIX_FICHIER):
        return None
    cmd = ["ffmpeg", "-v", "error", "-i", VOIX_FICHIER, "-af", f"atempo={VITESSE_VOIX}",
           "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"]
    data = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(data, dtype=np.float32).copy()

def fabriquer_son(chemin="son.wav"):
    total = sum(s["duree"] for s in SCENES)
    n = int(total * SR); tt = np.arange(n) / SR
    # nappe grave
    nappe = np.zeros(n)
    for f, a in [(55, 1.0), (110, 0.6), (165, 0.3), (220, 0.2)]:
        nappe += a * (np.sin(2 * np.pi * f * tt) + np.sin(2 * np.pi * f * 1.004 * tt))
    nappe *= 0.035 * (0.75 + 0.25 * np.sin(2 * np.pi * 0.25 * tt))
    musique = nappe
    # petit rythme (120 bpm)
    kick = bruitage("boum") * 0.35
    for b in np.arange(0, total, 0.5):
        ajouter(musique, kick[: int(0.25 * SR)], b)
        ajouter(musique, bruitage("clic") * 0.25, b + 0.25)
    # bruitages
    debut = 0.0
    for s in SCENES:
        if debut > 0: ajouter(musique, bruitage("souffle") * 0.8, debut - 0.15)
        for t, nom in s["sons"]:
            ajouter(musique, bruitage(nom), debut + t)
        debut += s["duree"]
    musique /= max(1e-6, np.abs(musique).max()) / 0.6
    # fondus
    fi, fo = int(0.3 * SR), int(1.5 * SR)
    musique[:fi] *= np.linspace(0, 1, fi)
    musique[-fo:] *= np.linspace(1, 0, fo)
    # voix
    voix = charger_voix()
    if voix is not None:
        piste_voix = np.zeros(n)
        voix = voix / max(1e-6, np.abs(voix).max()) * 0.92
        a_placer = any(s["voix"] for s in SCENES)
        debut = 0.0
        for s in SCENES:
            for moment, d0, d1 in s["voix"]:
                i0 = max(0, int((d0 / VITESSE_VOIX - 0.04) * SR)); i1 = int((d1 / VITESSE_VOIX + 0.12) * SR)
                morceau = voix[i0:i1].astype(np.float64).copy()
                fd = min(int(0.02 * SR), len(morceau) // 2)
                if fd > 0:
                    morceau[:fd] *= np.linspace(0, 1, fd); morceau[-fd:] *= np.linspace(1, 0, fd)
                ajouter(piste_voix, morceau, debut + moment - 0.04)
            debut += s["duree"]
        if not a_placer:
            ajouter(piste_voix, voix.astype(np.float64), 0.1)
            if len(voix) / SR > total:
                print(f"Attention : la voix ({len(voix) / SR:.1f} s) est plus longue que la video ({total:.1f} s).")
        mix = musique * 0.4 + piste_voix
    else:
        mix = musique
    pic = np.abs(mix).max()
    if pic > 0.98: mix *= 0.98 / pic
    with wave.open(chemin, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    return chemin


# ------------------------------------------------------------------ programme principal
def apercu():
    os.makedirs("apercu", exist_ok=True)
    for i, sc in enumerate(SCENES):
        for pc in (0.45, 0.85):
            image(i, sc["duree"] * pc).save(f"apercu/scene{i + 1}_{int(pc * 100)}.png")
    print("Apercus enregistres dans le dossier 'apercu'.")

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if "--apercu" in sys.argv:
        apercu(); sys.exit()
    print("Fabrication des scenes...")
    with ProcessPoolExecutor(max_workers=os.cpu_count() or 2) as ex:
        fichiers = list(ex.map(rendre_scene, range(len(SCENES))))
    with open("liste.txt", "w") as f:
        for c in fichiers: f.write(f"file '{c}'\n")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", "liste.txt",
                    "-c", "copy", "sans_son.mp4"], check=True)
    print("Fabrication du son...")
    fabriquer_son("son.wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", "sans_son.mp4", "-i", "son.wav", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", FICHIER_SORTIE], check=True)
    for c in fichiers + ["liste.txt", "sans_son.mp4", "son.wav"]:
        try: os.remove(c)
        except OSError: pass
    print("Termine :", FICHIER_SORTIE)
