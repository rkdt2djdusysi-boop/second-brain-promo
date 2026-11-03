# -*- coding: utf-8 -*-
"""
generer_video.py  -  Resume du livre "$100M Offers" (Alex Hormozi) en 60 secondes
Video TikTok verticale (9:16), style minimaliste noir et blanc, sous-titres jaunes.

Pour fabriquer la video :      python generer_video.py
Pour un apercu rapide (images) : python generer_video.py --apercu

Si un fichier "voix_100m.mp3" (ElevenLabs) est dans le meme dossier, il est ajoute automatiquement.
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
VOIX_FICHIER = "voix_100m.mp3"
VITESSE_VOIX = 1.06                 # 1.0 = vitesse normale ; 1.06 = 6 % plus rapide (plus dynamique)
FICHIER_SORTIE = "video_100m_offers.mp4"
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


# ------------------------------------------------------------------ pictogrammes en plus
def arc_pts(x, y, r, a0, a1, n=48):
    return [(x + r * math.cos(a0 + (a1 - a0) * i / n), y + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]

def fleche(p, x0, y0, x1, y1, col, w, tete=None):
    tete = tete or w * 2.6
    a = math.atan2(y1 - y0, x1 - x0)
    bx, by = x1 - math.cos(a) * tete * 0.8, y1 - math.sin(a) * tete * 0.8
    p.ligne([(x0, y0), (bx, by)], col, w)
    nx, ny = -math.sin(a), math.cos(a)
    p.poly([(x1, y1), (bx + nx * tete * 0.7, by + ny * tete * 0.7), (bx - nx * tete * 0.7, by - ny * tete * 0.7)], col)

def tuile(p, x, y, s, demi=70):
    p.rrect(x - demi * s, y - demi * s, x + demi * s, y + demi * s, 28 * s, fill=g(255))

def eclair(p, x, y, s, col):
    pts = [(10, -48), (-24, 8), (-2, 8), (-12, 48), (24, -10), (2, -10), (16, -48)]
    p.poly([(x + a * s, y + b * s) for a, b in pts], col)

def cible(p, x, y, r):
    p.cercle(x, y, r, fill=g(0)); p.cercle(x, y, r * 0.7, fill=g(255))
    p.cercle(x, y, r * 0.42, fill=g(0)); p.cercle(x, y, r * 0.16, fill=g(255))

def horloge(p, x, y, r, ang, col, fond):
    p.cercle(x, y, r, fill=col); p.cercle(x, y, r * 0.8, fill=fond)
    p.ligne([(x, y), (x + r * 0.62 * math.cos(ang), y + r * 0.62 * math.sin(ang))], col, r * 0.12)
    p.ligne([(x, y), (x + r * 0.42 * math.cos(ang / 12 - 1), y + r * 0.42 * math.sin(ang / 12 - 1))], col, r * 0.14)
    p.cercle(x, y, r * 0.1, fill=col)

def poids(p, x, y, s, col, fond):
    p.cercle(x, y - 22 * s, 22 * s, outline=col, w=9 * s)
    p.cercle(x, y + 12 * s, 32 * s, fill=col)
    p.texte(x, y + 14 * s, "KG", 22 * s, fond, "black")

def cadeau(p, x, y, s, col, fond):
    p.ellipse(x - 14 * s, y - 36 * s, 14 * s, 9 * s, outline=col, w=6 * s)
    p.ellipse(x + 14 * s, y - 36 * s, 14 * s, 9 * s, outline=col, w=6 * s)
    p.rrect(x - 44 * s, y - 28 * s, x + 44 * s, y - 8 * s, 4 * s, fill=col)
    p.rrect(x - 38 * s, y - 4 * s, x + 38 * s, y + 42 * s, 4 * s, fill=col)
    p.rrect(x - 6 * s, y - 28 * s, x + 6 * s, y + 42 * s, 0, fill=fond)

def bouclier(p, x, y, s, col, fond):
    pts = [(0, -48), (40, -34), (38, 6), (0, 48), (-38, 6), (-40, -34)]
    p.poly([(x + a * s, y + b * s) for a, b in pts], col)
    coche(p, x, y, 40 * s, 1, fond, 8 * s)

def etiquette_prix(p, x, y, s, txt, k=1.0):
    if s <= 0.01: return
    col = g(255, k)
    p.poly([(x - 60 * s, y - 40 * s), (x - 104 * s, y), (x - 60 * s, y + 40 * s)], col)
    p.rrect(x - 64 * s, y - 40 * s, x + 104 * s, y + 40 * s, 14 * s, fill=col)
    p.cercle(x - 66 * s, y, 9 * s, fill=g(0))
    p.texte(x + 22 * s, y + 2 * s, txt, 50 * s, g(0), "black")

def cube(p, x0, y1, cote, kf=1.0, prog=1.0, col=(255, 255, 255), w=4):
    o = cote * 0.3; x1 = x0 + cote; y0 = y1 - cote
    if kf > 0:
        p.poly([(x0, y0), (x1, y0), (x1 + o, y0 - o), (x0 + o, y0 - o)], g(195, kf))
        p.poly([(x1, y0), (x1 + o, y0 - o), (x1 + o, y1 - o), (x1, y1)], g(130, kf))
        p.rrect(x0, y0, x1, y1, 0, fill=g(255, kf))
    aretes = [[(x0, y1), (x1, y1)], [(x0, y1), (x0, y0)], [(x1, y1), (x1, y0)], [(x0, y0), (x1, y0)],
              [(x0, y0), (x0 + o, y0 - o)], [(x1, y0), (x1 + o, y0 - o)], [(x0 + o, y0 - o), (x1 + o, y0 - o)],
              [(x1 + o, y0 - o), (x1 + o, y1 - o)], [(x1, y1), (x1 + o, y1 - o)]]
    pb = cl(prog) * len(aretes)
    for i, a in enumerate(aretes):
        tracer(p, a, pb - i, col, w)

def badge_ok(p, x, y, s):
    if s <= 0.01: return
    p.cercle(x, y, 25 * s, fill=JAUNE, outline=g(0), w=4)
    coche(p, x, y + 2, 26 * s, 1, g(0), 6 * s)

def foule(p, t, y, xs, taille, pleins=()):
    for i, x in enumerate(xs):
        b = abs(math.sin(t * 5 + i * 1.3)) * 5
        bonhomme(p, x, y - b, taille, col=g(255) if i in pleins else g(150), plein=i in pleins, humeur=0.8)

POS4 = [(230, 400), (490, 400), (230, 620), (490, 620)]


# ------------------------------------------------------------------ SCENE 1 : l'accroche
def scene_accroche(p, t, D):
    k = 1 - pr(t, 2.55, 2.85)
    if k > 0:
        s = pop(t, 0) * k
        cx, cy = 360, 520
        p.rrect(cx - 220 * s, cy - 160 * s, cx + 220 * s, cy + 160 * s, 36 * s, outline=g(255, k), w=5)
        p.texte(cx, cy - 92 * s, "THE OFFER", 48 * s, g(255, k), "black")
        clic = 1 - 0.1 * math.sin(math.pi * pr(t, 2.05, 2.25))
        sy = (1 + 0.45 * e_inout(pr(t, 0.3, 2.0))) * clic * s
        yx, yy = 300, 560
        p.rrect(yx - 70 * sy, yy - 36 * sy, yx + 70 * sy, yy + 36 * sy, 30 * sy, fill=g(255, k))
        p.texte(yx, yy + 2, "YES", 42 * sy, g(0), "black")
        sn = (1 - 0.65 * e_inout(pr(t, 0.3, 2.0))) * s
        p.rrect(475 - 45 * sn, 560 - 25 * sn, 475 + 45 * sn, 560 + 25 * sn, 20 * sn, outline=g(110, k), w=3)
        p.texte(475, 562, "no", 26 * sn, g(130, k), "medium")
        if t < 2.55:
            u = e_inout(pr(t, 0.6, 1.9))
            curseur(p, 620 - 300 * u, 820 - 240 * u, clic)
        if t > 2.15:   # pluie de pieces
            u = t - 2.15
            for i in range(7):
                a = -math.pi / 2 + (i - 3) * 0.42
                x = yx + math.cos(a) * 260 * u
                y = yy + math.sin(a) * 300 * u + 520 * u * u
                piece(p, x, y, 22, k)
        xs = [360 + b * (1 - 0.3 * e_out(pr(t, 0.2, 2.4))) for b in (-280, -200, -120, 120, 200, 280)]
        foule(p, t, 840, xs, 34)
    if t > 2.7:
        z1 = 1 + 1.5 * (1 - e_out(pr(t, 2.7, 3.05)))
        p.texte(360, 380, "$100M", 165 * z1, g(255, pr(t, 2.7, 2.8)), "black", contour=4)
        z2 = 1 + 1.5 * (1 - e_out(pr(t, 2.85, 3.2)))
        p.texte(360, 530, "OFFERS", 115 * z2, g(255, pr(t, 2.85, 2.95)), "black", contour=4)
        kr = pr(t, 3.0, 3.2)
        if kr > 0:
            p.cercle(360, 740, 80, outline=g(60, kr), w=10)
            tracer(p, arc_pts(360, 740, 80, -math.pi / 2, 1.5 * math.pi, 64), pr(t, 3.1, 4.5), mul(JAUNE, kr), 10)
            p.texte(360, 742, "60s", 46, g(255, kr), "black")


# ------------------------------------------------------------------ SCENE 2 : ne jamais se battre sur le prix
def scene_prix(p, t, D):
    kt = 1 - 0.6 * pr(t, 2.5, 2.9)
    courbe = [(110, 250), (240, 320), (320, 290), (460, 440), (610, 530)]
    tracer(p, courbe, pr(t, 0.3, 2.0), mul(ROUGE, kt * 0.8), 8)
    if t > 2.0:
        fleche(p, 540, 488, 625, 540, mul(ROUGE, kt * 0.8), 8, 26)
    prix = 99 - int(90 * e_inout(pr(t, 0.4, 2.0)))
    etiquette_prix(p, 360, 400, 1.4 * pop(t, 0.1), f"${prix}", kt)
    tracer(p, [(270, 330), (450, 470)], pr(t, 2.0, 2.15), mul(ROUGE, kt), 18)
    tracer(p, [(450, 330), (270, 470)], pr(t, 2.15, 2.3), mul(ROUGE, kt), 18)
    kc = pr(t, 3.5, 3.8)
    if kc > 0:
        p.texte(360, 640, "= COMMODITY", 54, g(220, kc), "black")
    for i in range(5):
        x0 = 75 + i * 120
        cube(p, x0, 820, 70, 0, pr(t, 2.65 + 0.15 * i, 3.05 + 0.15 * i), g(150), 3)
        kk = pr(t, 3.0 + 0.15 * i, 3.2 + 0.15 * i)
        if kk > 0:
            p.texte(x0 + 40, 860, "$1", 28, g(150, kk), "bold")


# ------------------------------------------------------------------ SCENE 3 : la foule affamee
def scene_foule(p, t, D):
    s = pop(t, 0.1)
    if s > 0.01:
        p.texte(360, 210, "STARVING CROWD", 64 * s, g(255), "black")
    labels = ["PAIN", "MONEY", "EASY TO FIND", "GROWING"]
    temps = [2.0, 2.9, 3.8, 4.8]
    for i, (x, y) in enumerate(POS4):
        si = pop(t, temps[i])
        if si <= 0.01: continue
        tuile(p, x, y, si)
        if i == 0:
            eclair(p, x, y, si, g(0))
        elif i == 1:
            p.cercle(x, y, 42 * si, fill=g(0)); p.texte(x, y + 2, DEVISE, 52 * si, g(255), "black")
        elif i == 2:
            cible(p, x, y, 44 * si)
        else:
            pts = [(x - 42 * si, y + 30 * si), (x - 14 * si, y), (x + 6 * si, y + 14 * si), (x + 30 * si, y - 12 * si)]
            p.ligne(pts, g(0), 9 * si)
            fleche(p, x + 26 * si, y - 8 * si, x + 46 * si, y - 32 * si, g(0), 9 * si, 22 * si)
        p.texte(x, y + 100, labels[i], 28 * si, g(220), "bold")
        badge_ok(p, x + 55, y + 55, pop(t, temps[i] + 0.25, 0.25))
    vis = pop(t, 0.3, 0.5)
    if vis > 0.01:
        n_plein = int(pr(t, 5.6, 6.4) * 7.999)
        foule(p, t, 840, [120 + 80 * i for i in range(7)], 34 * vis, pleins=range(n_plein))


# ------------------------------------------------------------------ SCENE 4 : l'equation de la valeur
def element_eq(p, x, y, s, genre, t, demi=58, label=None):
    if s <= 0.01: return
    tuile(p, x, y, s, demi)
    f = s * demi / 70
    if genre == "reve":
        etoile(p, x, y + 3 * f, 42 * f, g(0))
    elif genre == "chance":
        cible(p, x, y, 42 * f)
    elif genre == "temps":
        horloge(p, x, y, 44 * f, t * 3, g(0), g(255))
    else:
        poids(p, x, y + 4 * f, f, g(0), g(255))
    if label:
        p.texte(x, y + 88, label, 25 * s, g(220), "bold")

def scene_equation(p, t, D):
    s = pop(t, 0.2)
    if s > 0.01:
        p.texte(360, 220, "VALUE =", 76 * s, g(255), "black")
    tracer(p, [(110, 545), (610, 545)], pr(t, 0.6, 1.2), g(255), 6)
    element_eq(p, 230, 410, pop(t, 1.8), "reve", t, label="DREAM OUTCOME")
    sx = pop(t, 3.0, 0.3)
    if sx > 0.01: p.texte(360, 410, "×", 64 * sx, g(255), "black")
    element_eq(p, 490, 410, pop(t, 3.15), "chance", t, label="LIKELIHOOD")
    element_eq(p, 230, 690, pop(t, 5.0), "temps", t, label="TIME DELAY")
    sx = pop(t, 6.4, 0.3)
    if sx > 0.01: p.texte(360, 690, "×", 64 * sx, g(255), "black")
    element_eq(p, 490, 690, pop(t, 6.55), "effort", t, label="EFFORT")


# ------------------------------------------------------------------ SCENE 5 : monter le haut, baisser le bas
def scene_leviers(p, t, D):
    su = 1 + 0.35 * e_inout(pr(t, 0.3, 1.4))
    sd = 1 - 0.45 * e_inout(pr(t, 1.6, 2.8))
    element_eq(p, 250, 290, su, "reve", t, demi=46)
    element_eq(p, 470, 290, su, "chance", t, demi=46)
    p.texte(360, 290, "×", 48, g(255), "black")
    p.ligne([(130, 395), (590, 395)], g(255), 5)
    element_eq(p, 250, 490, sd, "temps", t, demi=46)
    element_eq(p, 470, 490, sd, "effort", t, demi=46)
    p.texte(360, 490, "×", 48 * sd, g(255), "black")
    ku = pr(t, 0.3, 0.6)
    if ku > 0:
        for x in (165, 555):
            yy = 300 - 20 * math.sin(t * 6) * ku
            fleche(p, x, yy + 40, x, yy - 40, mul(JAUNE, ku), 10, 28)
    kd = pr(t, 1.6, 1.9)
    if kd > 0:
        for x in (165, 555):
            yy = 480 + 20 * math.sin(t * 6) * kd
            fleche(p, x, yy - 40, x, yy + 40, mul(JAUNE, kd), 10, 28)
    base = 880
    hp = 150 * e_out(pr(t, 3.1, 3.8))
    hv = 270 * e_out(pr(t, 3.6, 4.8))
    if hp > 2:
        p.rrect(205, base - hp, 295, base, 16, fill=g(140))
        p.texte(250, base - hp - 26, "PRICE", 28, g(170), "bold")
    if hv > 2:
        p.rrect(425, base - hv, 515, base, 16, fill=g(255))
        p.texte(470, base - hv - 26, "VALUE", 28, JAUNE, "black")
    sg = pop(t, 5.0, 0.3)
    if sg > 0.01:
        p.texte(360, 800, "<", 80 * sg, g(255), "black")


# ------------------------------------------------------------------ SCENE 6 : construire l'offre
def scene_construire(p, t, D):
    for i in range(4):
        y = 260 + 90 * i
        s = pop(t, 0.5 + 0.45 * i)
        if s <= 0.01: continue
        tf = 3.1 + 0.45 * i
        f = pr(t, tf, tf + 0.3)
        sol = f >= 0.5
        sy = abs(math.cos(math.pi * f))
        ts = 5.3 + 0.12 * i
        m = e_inout(pr(t, ts, ts + 0.45))
        if m >= 1: continue
        cx = 360; cy = y + (760 - y) * m
        sc = s * (1 - 0.7 * m); kk = 1 - m
        h = 35 * sc * max(sy, 0.04); w = 220 * sc
        if sol:
            p.rrect(cx - w, cy - h, cx + w, cy + h, 18 * sc, fill=g(255, kk))
            if sy > 0.3:
                badge_ok(p, cx - w + 40 * sc, cy, 0.8 * sc * sy)
                p.texte(cx - w + 80 * sc, cy, f"SOLUTION #{i + 1}", 32 * sc * sy, g(0), "black", anchor="lm")
        else:
            p.rrect(cx - w, cy - h, cx + w, cy + h, 18 * sc, fill=g(20, kk), outline=g(170, kk), w=3)
            if sy > 0.3:
                xx = cx - w + 40 * sc
                p.ligne([(xx - 12 * sc, cy - 12 * sc * sy), (xx + 12 * sc, cy + 12 * sc * sy)], mul(ROUGE, kk), 7 * sc)
                p.ligne([(xx + 12 * sc, cy - 12 * sc * sy), (xx - 12 * sc, cy + 12 * sc * sy)], mul(ROUGE, kk), 7 * sc)
                p.texte(cx - w + 80 * sc, cy, f"PROBLEM #{i + 1}", 32 * sc * sy, g(255, kk), "bold", anchor="lm")
    if t > 5.6:
        cube(p, 290, 830, 140, pr(t, 6.2, 6.45), pr(t, 5.6, 6.2), g(255), 5)
        if t > 6.3:
            etoile(p, 360, 760, 38 * pop(t, 6.3), g(0))
        kl = pr(t, 6.4, 6.7)
        if kl > 0:
            p.texte(360, 880, "GRAND SLAM OFFER", 44, mul(JAUNE, kl), "black")
        if 6.4 < t < 7.4:
            u = pr(t, 6.4, 7.4)
            for i, (ex, ey) in enumerate([(270, 650), (480, 630), (470, 800), (255, 790)]):
                r = 16 * math.sin(math.pi * cl(u * 1.4 - i * 0.12))
                if r > 1: etoile(p, ex, ey, r, g(255), 4, 0.25, 0)


# ------------------------------------------------------------------ SCENE 7 : rendre l'offre irresistible
def scene_irresistible(p, t, D):
    s = pop(t, 0.1)
    if s > 0.01:
        puls = 1 + 0.04 * math.sin(t * 7) if t > 5.2 else 1
        p.texte(360, 210, "IRRESISTIBLE", 70 * s * puls, g(255), "black")
    labels = ["SCARCITY", "URGENCY", "BONUSES", "GUARANTEE"]
    temps = [1.7, 2.5, 3.4, 4.8]
    nb = 0
    for i, (x, y) in enumerate(POS4):
        si = pop(t, temps[i])
        if si <= 0.01: continue
        nb += e_out(pr(t, temps[i], temps[i] + 0.4))
        tuile(p, x, y, si)
        if i == 0:
            for j in range(5):
                p.cercle(x + (j - 2) * 22 * si, y - 20 * si, 8 * si, fill=g(185) if j < 3 else g(0))
            p.texte(x, y + 24 * si, "2 LEFT", 30 * si, g(0), "black")
        elif i == 1:
            horloge(p, x, y, 44 * si, t * 7, g(0), g(255))
        elif i == 2:
            cadeau(p, x, y, si, g(0), g(255))
        else:
            bouclier(p, x, y, si, g(0), g(255))
        p.texte(x, y + 100, labels[i], 28 * si, g(220), "bold")
    kb = pop(t, 1.2, 0.3)
    if kb > 0.01:
        p.rrect(110, 820, 610, 856, 18, outline=g(130), w=3)
        rempli = nb / 4
        if rempli > 0.03:
            p.rrect(116, 826, 116 + 488 * rempli, 850, 12, fill=JAUNE)


# ------------------------------------------------------------------ SCENE 8 : un nom qui vend le resultat
NOM_OFFRE = "10 CLIENTS IN 30 DAYS"

def scene_nom(p, t, D):
    s = pop(t, 0.1)
    if s > 0.01:
        p.texte(360, 240, "NAME IT", 72 * s, g(255), "black")
    st = pop(t, 0.3)
    if st > 0.01:
        p.rrect(360 - 280 * st, 440 - 62 * st, 360 + 280 * st, 440 + 62 * st, 30 * st, fill=g(255))
        p.cercle(360 - 248 * st, 440, 10 * st, fill=g(0))
        n = int(pr(t, 0.7, 2.3) * len(NOM_OFFRE) + 0.001)
        txt = NOM_OFFRE[:n]
        p.texte(375, 442, txt, 38 * st, g(0), "black")
        if t < 2.6 and int(t * 4) % 2 == 0:
            xc = 375 + p.largeur(txt, 38, "black") / 2 + 6
            p.ligne([(xc, 420), (xc, 464)], g(0), 4)
    if 2.4 < t < 3.6:
        u = pr(t, 2.4, 3.6)
        for i, (ex, ey) in enumerate([(100, 370), (620, 360), (640, 510), (90, 520)]):
            r = 18 * math.sin(math.pi * cl(u * 1.4 - i * 0.12))
            if r > 1: etoile(p, ex, ey, r, JAUNE, 4, 0.25, 0)
    vis = pop(t, 0.5, 0.4)
    if vis > 0.01:
        n_plein = int(pr(t, 2.6, 3.6) * 5.999)
        foule(p, t, 780, [160 + 100 * i for i in range(5)], 40 * vis, pleins=range(n_plein))


# ------------------------------------------------------------------ SCENE 9 : fin + follow
def scene_fin_livres(p, t, D):
    s = pop(t, 0, 0.4)
    if s > 0.01:
        for j, (dx, w, v) in enumerate([(-6, 200, 255), (10, 180, 150), (-2, 210, 255)]):
            y = 380 - j * 46 * s
            p.rrect(360 + dx * s - w / 2 * s, y - 20 * s, 360 + dx * s + w / 2 * s, y + 20 * s, 8 * s, fill=g(v))
            p.ligne([(360 + dx * s - w / 2 * s + 22 * s, y - 20 * s), (360 + dx * s - w / 2 * s + 22 * s, y + 20 * s)],
                    g(0), 4 * s)
    ki = pr(t, 0.3, 0.55)
    if ki > 0:
        p.texte(360, 490, "1 BOOK = 60 SECONDS", 40, mul(JAUNE, ki), "black")
    ks = pr(t, 0.45, 0.7)
    if ks > 0:
        p.rrect(140, 625, 580, 695, 35, outline=g(150, ks), w=3)
        p.cercle(182, 656, 13, outline=g(200, ks), w=4)
        p.ligne([(192, 667), (204, 679)], g(200, ks), 5)
        n = int(pr(t, 0.6, 1.3) * len(PSEUDO) + 0.001)
        p.texte(222, 660, PSEUDO[:n], 36, g(255, ks), "bold", anchor="lm")
        if int(t * 3) % 2 == 0:
            xc = 226 + p.largeur(PSEUDO[:n], 36, "bold")
            p.ligne([(xc, 642), (xc, 678)], g(255, ks), 3)
    sf = pop(t, 1.4, 0.35)
    if sf > 0.01:
        y = 820 - (abs(math.sin((t - 1.75) * 7)) * 18 if t > 1.75 else 0)
        p.rrect(470 - 120 * sf, y - 43 * sf, 470 + 120 * sf, y + 43 * sf, 43 * sf, fill=g(255))
        p.texte(470, y + 2, APPEL_FIN, 38 * sf, g(0), "black")


# ------------------------------------------------------------------ LES SCENES
# textes = (debut, fin, "sous-titre") en secondes dans la scene
# voix   = (moment_dans_scene, debut_dans_mp3, fin_dans_mp3)
# cles   = (temps_video, temps_animation) : accelere/ralentit l'animation pour suivre la voix
# sons   = bruitages (moment, type)
SCENES = [
    dict(f=scene_accroche, duree=6.5, fondu_entree=False,
         cles=[(0, 0), (3.0, 2.05), (3.35, 2.7), (3.75, 3.08), (4.95, 3.1), (6.5, 4.5)],
         textes=[(0.0, 1.7, 'How do you make an offer so good'),
                 (1.7, 3.3, 'people feel stupid saying no?'),
                 (3.3, 6.5, "Here's $100M Offers in 60 seconds.")],
         voix=[(0.05, 0.0, 1.66), (1.78, 2.5, 3.97), (3.35, 4.4, 6.0), (5.0, 6.97, 8.28)],
         sons=[(0.0, "boum"), (2.05, "clic"), (2.15, "piece"), (2.7, "boum"), (2.85, "boum"), (3.1, "bip")]),
    dict(f=scene_prix, duree=4.8,
         cles=[(0, 0), (1.95, 2.0), (3.1, 2.65), (3.85, 3.5), (4.8, 4.45)],
         textes=[(0.0, 2.4, 'Rule number one: never compete on price.'),
                 (2.4, 4.8, "If you're the cheapest, you're just another commodity.")],
         voix=[(0.05, 9.37, 10.22), (1.0, 10.71, 12.03), (2.45, 12.43, 14.43)],
         sons=[(0.1, "pop")] + [(0.4 + 0.1 * i, "clic") for i in range(16)] + [(2.0, "erreur"), (2.15, "boum")]
              + [(2.65 + 0.15 * i, "pop") for i in range(5)] + [(3.5, "bip")]),
    dict(f=scene_foule, duree=5.8,
         cles=[(0, 0), (1.6, 2.0), (2.65, 2.9), (3.4, 3.8), (4.5, 4.8), (5.0, 5.6), (5.6, 6.4), (5.8, 7.0)],
         textes=[(0.0, 1.5, 'Sell to a starving crowd:'),
                 (1.5, 4.3, 'people in pain, with money, easy to find,'),
                 (4.3, 5.8, 'in a growing market.')],
         voix=[(0.05, 15.92, 17.34), (1.55, 17.76, 18.71), (2.6, 18.91, 19.54), (3.35, 20.04, 20.91), (4.35, 21.12, 21.96)],
         sons=[(0.1, "boum")] + [(x, "pop") for x in (2.0, 2.9, 3.8, 4.8)] + [(x + 0.25, "bip") for x in (2.0, 2.9, 3.8, 4.8)]
              + [(5.6 + 0.11 * i, "clic") for i in range(7)]),
    dict(f=scene_equation, duree=7.4,
         cles=[(0, 0), (0.6, 0.2), (1.0, 0.6), (1.85, 1.8), (2.95, 3.0), (4.9, 5.0), (5.65, 6.4), (7.4, 9.0)],
         textes=[(0.0, 1.8, 'Then, the value equation.'),
                 (1.8, 4.4, 'Dream outcome, times the chance it works...'),
                 (4.4, 7.4, 'divided by the time it takes, and the effort it costs.')],
         voix=[(0.05, 23.46, 25.25), (1.85, 25.8, 26.75), (2.95, 27.18, 28.56), (4.45, 29.2, 31.75)],
         sons=[(0.2, "boum"), (0.6, "souffle"), (1.8, "pop"), (3.0, "bip"), (3.15, "pop"), (5.0, "pop"), (6.4, "bip"),
               (6.55, "pop")]),
    dict(f=scene_leviers, duree=5.3,
         cles=[(0, 0), (0.1, 0.3), (1.05, 1.6), (1.9, 2.8), (2.5, 3.1), (3.2, 3.6), (4.0, 4.8), (4.4, 5.0), (5.3, 7.0)],
         textes=[(0.0, 2.15, 'Push the top up. Push the bottom down.'),
                 (2.15, 5.3, 'Now you can charge more... and it still feels like a steal.')],
         voix=[(0.05, 32.46, 33.34), (1.05, 33.79, 34.78), (2.2, 35.3, 38.11)],
         sons=[(0.3, "bip"), (1.6, "bip"), (3.1, "pop"), (3.6, "pop"), (5.0, "boum")]),
    dict(f=scene_construire, duree=6.6,
         cles=[(0, 0), (0.75, 0.5), (2.1, 1.85), (3.05, 3.1), (4.45, 4.75), (4.95, 5.3), (5.75, 6.4), (6.6, 7.25)],
         textes=[(0.0, 2.9, 'To build it: list every problem your customer faces...'),
                 (2.9, 4.65, 'turn each one into a solution...'),
                 (4.65, 6.6, 'and stack them into one offer.')],
         voix=[(0.05, 39.18, 39.69), (0.7, 40.38, 42.6), (2.95, 43.3, 44.98), (4.7, 45.64, 47.08)],
         sons=[(0.5 + 0.45 * i, "pop") for i in range(4)] + [(3.25 + 0.45 * i, "bip") for i in range(4)]
              + [(5.3, "souffle"), (6.4, "boum"), (6.5, "piece")]),
    dict(f=scene_irresistible, duree=5.8,
         cles=[(0, 0), (1.0, 1.2), (1.5, 1.7), (2.3, 2.5), (2.95, 3.4), (3.9, 4.8), (5.8, 6.7)],
         textes=[(0.0, 1.45, 'Then make it irresistible:'),
                 (1.45, 3.7, 'scarcity, urgency, bonuses...'),
                 (3.7, 5.8, 'and a guarantee that removes the risk.')],
         voix=[(0.05, 47.96, 49.34), (1.5, 49.79, 50.45), (2.3, 50.68, 52.0), (3.75, 52.73, 54.39)],
         sons=[(0.1, "boum")] + [(x, "pop") for x in (1.7, 2.5, 3.4, 4.8)] + [(5.2, "piece")]),
    dict(f=scene_nom, duree=3.2,
         cles=[(0, 0), (0.3, 0.5), (1.4, 2.3), (2.4, 3.6), (3.2, 4.5)],
         textes=[(0.0, 3.2, 'And give it a name that sells the result.')],
         voix=[(0.05, 55.31, 56.98)],
         sons=[(0.3, "pop")] + [(0.7 + 0.076 * i, "clic") for i in range(21)] + [(2.4, "bip")]),
    dict(f=scene_fin_livres, duree=3.5,
         textes=[(0.0, 3.5, 'Follow for more books in 60 seconds.')],
         voix=[(0.05, 58.49, 60.18)],
         sons=[(0.0, "boum")] + [(0.6 + 0.15 * i, "clic") for i in range(4)] + [(1.4, "pop")]),
]


# ------------------------------------------------------------------ rendu d'une image
def temps_anim(sc, t):
    """Convertit le temps de la video en temps d'animation (pour suivre le rythme de la voix)."""
    if "cles" not in sc: return t
    n, a = zip(*sc["cles"])
    return float(np.interp(t, n, a))

def temps_son(sc, t):
    """Inverse : place un bruitage (ecrit en temps d'animation) au bon moment de la video."""
    if "cles" not in sc: return t
    n, a = zip(*sc["cles"])
    return float(np.interp(t, a, n))
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
    sc["f"](Stylo(grand), temps_anim(sc, t), D)
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
            ajouter(musique, bruitage(nom), debut + temps_son(s, t))
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
