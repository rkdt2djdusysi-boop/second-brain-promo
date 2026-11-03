# -*- coding: utf-8 -*-
"""
generer_video_rich_dad.py  -  Resume du livre "Rich Dad Poor Dad" (Robert Kiyosaki)
Video YouTube 16:9 en Full HD, 100 % noir et blanc.

Pour fabriquer la video :        python generer_video_rich_dad.py
Pour un apercu rapide (images) : python generer_video_rich_dad.py --apercu

Si un fichier "voix_rich_dad.mp3" (ElevenLabs) est dans le meme dossier, il est ajoute automatiquement.
"""
import math, os, sys, subprocess, wave
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# =========================== REGLAGES (modifiables) ===========================
LARGEUR, HAUTEUR = 1920, 1080       # YouTube Full HD (mettre 1280, 720 pour aller plus vite)
FPS = 30
QUALITE = 16                        # plus petit = plus beau (et plus lourd)
PSEUDO = "@MTM"
DEVISE = "$"
VOIX_FICHIER = "voix_rich_dad.mp3"
VITESSE_VOIX = 1.06                 # 1.0 = vitesse normale ; 1.06 = 6 % plus rapide
FICHIER_SORTIE = "video_rich_dad_poor_dad.mp4"
SOUS_TITRE_Y = 662                  # hauteur des sous-titres (repere 1280 x 720)
# ==============================================================================

BASE_L, BASE_H = 1280, 720          # tout est dessine dans ce repere, puis mis a l'echelle
ECHELLE = LARGEUR / BASE_L
SS = 2                              # sur-echantillonnage (bords lisses)
SR = 44100


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
    """Niveau de gris : 0 = noir, 255 = blanc."""
    return int(cl(v * k, 0, 255))

def lerp(a, b, u):
    return a + (b - a) * u


# ------------------------------------------------------------------ polices
_D = "/usr/share/fonts/opentype/inter/"
_W = "C:/Windows/Fonts/"
POLICES = {
    "black":  ["Inter-Black.otf", _D + "Inter-Black.otf", _D + "Inter-ExtraBold.otf", _W + "Inter-Black.ttf",
               _W + "ariblk.ttf", _W + "seguibl.ttf", _W + "arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "bold":   ["Inter-Bold.otf", _D + "Inter-Bold.otf", _W + "Inter-Bold.ttf", _W + "segoeuib.ttf", _W + "arialbd.ttf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "semi":   ["Inter-SemiBold.otf", _D + "Inter-SemiBold.otf", _W + "Inter-SemiBold.ttf", _W + "seguisb.ttf",
               _W + "arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
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


# ------------------------------------------------------------------ stylo (niveaux de gris)
class Stylo:
    def __init__(s, img, k):
        s.d = ImageDraw.Draw(img); s.k = k

    def _w(s, w):
        return max(1, int(round(w * s.k)))

    def cercle(s, x, y, r, fill=None, outline=None, w=1):
        k = s.k; r = max(r, 0.5)
        s.d.ellipse([(x - r) * k, (y - r) * k, (x + r) * k, (y + r) * k], fill=fill, outline=outline, width=s._w(w))

    def ellipse(s, x, y, rx, ry, fill=None, outline=None, w=1):
        k = s.k; rx = max(rx, 0.5); ry = max(ry, 0.5)
        s.d.ellipse([(x - rx) * k, (y - ry) * k, (x + rx) * k, (y + ry) * k], fill=fill, outline=outline, width=s._w(w))

    def rrect(s, x0, y0, x1, y1, r, fill=None, outline=None, w=1):
        k = s.k
        if x1 < x0: x0, x1 = x1, x0
        if y1 < y0: y0, y1 = y1, y0
        if x1 - x0 < 1 or y1 - y0 < 1: return
        r = max(0, min(r, (x1 - x0) / 2 - 0.6, (y1 - y0) / 2 - 0.6))
        s.d.rounded_rectangle([x0 * k, y0 * k, x1 * k, y1 * k], radius=r * k, fill=fill, outline=outline, width=s._w(w))

    def ligne(s, pts, col, w):
        if len(pts) < 2: return
        k = s.k
        s.d.line([(x * k, y * k) for x, y in pts], fill=col, width=s._w(w), joint="curve")
        for x, y in (pts[0], pts[-1]):
            s.cercle(x, y, w / 2, fill=col)

    def poly(s, pts, fill):
        s.d.polygon([(x * s.k, y * s.k) for x, y in pts], fill=fill)

    def texte(s, x, y, txt, taille, col, nom="bold", anchor="mm", contour=0, col_contour=0):
        if taille < 1 or not txt: return
        s.d.text((x * s.k, y * s.k), txt, font=police(nom, taille * s.k), fill=col, anchor=anchor,
                 stroke_width=int(round(contour * s.k)), stroke_fill=col_contour)

    def largeur(s, txt, taille, nom="bold"):
        return s.d.textlength(txt, font=police(nom, taille * s.k)) / s.k


# ------------------------------------------------------------------ pictogrammes
def tracer(p, pts, prog, col, w):
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

def point_sur(pts, u):
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    reste = sum(seg) * cl(u)
    for i, l in enumerate(seg):
        if reste <= l or i == len(seg) - 1:
            a = reste / l if l > 0 else 0
            return (lerp(pts[i][0], pts[i + 1][0], cl(a)), lerp(pts[i][1], pts[i + 1][1], cl(a)))
        reste -= l
    return pts[-1]

def arc_pts(x, y, r, a0, a1, n=48):
    return [(x + r * math.cos(a0 + (a1 - a0) * i / n), y + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]

def fleche(p, x0, y0, x1, y1, col, w, tete=None):
    tete = tete or w * 2.6
    a = math.atan2(y1 - y0, x1 - x0)
    bx, by = x1 - math.cos(a) * tete * 0.8, y1 - math.sin(a) * tete * 0.8
    p.ligne([(x0, y0), (bx, by)], col, w)
    nx, ny = -math.sin(a), math.cos(a)
    p.poly([(x1, y1), (bx + nx * tete * 0.7, by + ny * tete * 0.7), (bx - nx * tete * 0.7, by - ny * tete * 0.7)], col)

def fleche_progressive(p, x0, y0, x1, y1, prog, col, w):
    prog = cl(prog)
    if prog <= 0: return
    fleche(p, x0, y0, lerp(x0, x1, prog), lerp(y0, y1, prog), col, w)

def bonhomme(p, x, y, t, col=255, plein=True, humeur=1.0, regard=0.0, lunettes=False):
    """(x, y) = centre du buste ; t = taille ; humeur 1 = sourire, -1 = triste."""
    if t <= 0.5: return
    if plein:
        p.rrect(x - 0.62 * t, y - 0.35 * t, x + 0.62 * t, y + 0.95 * t, 0.55 * t, fill=col)
        p.cercle(x, y - 0.85 * t, 0.42 * t, fill=col)
        ox = regard * 0.13 * t
        for dx in (-0.14, 0.14):
            p.cercle(x + dx * t + ox, y - 0.92 * t, 0.055 * t, fill=0)
            if lunettes:
                p.cercle(x + dx * t + ox, y - 0.92 * t, 0.115 * t, outline=0, w=0.035 * t)
        if lunettes:
            p.ligne([(x - 0.03 * t + ox, y - 0.93 * t), (x + 0.03 * t + ox, y - 0.93 * t)], 0, 0.035 * t)
        pts = []
        for i in range(9):
            u = -1 + i / 4
            pts.append((x + u * 0.15 * t + ox * 0.8, y - 0.74 * t + humeur * 0.08 * t * (1 - u * u)))
        p.ligne(pts, 0, 0.05 * t)
    else:
        w = max(2, 0.07 * t)
        p.rrect(x - 0.62 * t, y - 0.35 * t, x + 0.62 * t, y + 0.95 * t, 0.55 * t, outline=col, w=w)
        p.cercle(x, y - 0.85 * t, 0.42 * t, outline=col, w=w)

def piece(p, x, y, r, k=1.0, sx=1.0):
    if k <= 0.01 or r <= 0.5: return
    sx = max(0.08, abs(sx))
    p.ellipse(x, y, r * 1.35 * sx, r * 1.35, fill=g(40, k))
    p.ellipse(x, y, r * sx, r, fill=g(255, k))
    p.ellipse(x, y, r * 0.78 * sx, r * 0.78, outline=0, w=r * 0.08)
    if sx > 0.55:
        p.texte(x, y + r * 0.04, DEVISE, r * 1.05, 0, "black")

def piece_plate(p, x, y, r):
    p.ellipse(x, y + 5, r, r * 0.32, fill=g(150))
    p.ellipse(x, y, r, r * 0.32, fill=255, outline=0, w=2)

def engrenage(p, x, y, r, rot, col, trou=0):
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
    if s <= 0.01: return
    w, h = w * s, h * s
    dx, dy = cible[0] - x, cible[1] - y
    n = math.hypot(dx, dy) or 1; dx, dy = dx / n, dy / n
    px, py = -dy, dx
    base = (x + dx * h * 0.3, y + dy * h * 0.3)
    pointe = (x + dx * (h * 0.5 + 34 * s), y + dy * (h * 0.5 + 34 * s))
    p.poly([(base[0] + px * 18 * s, base[1] + py * 18 * s), (base[0] - px * 18 * s, base[1] - py * 18 * s), pointe], bord)
    p.rrect(x - w / 2, y - h / 2, x + w / 2, y + h / 2, min(w, h) * 0.3, fill=fond, outline=bord, w=epais)

def curseur(p, x, y, s=1.0):
    forme = [(0, 0), (0, 46), (12, 35), (21, 55), (29, 51), (20, 32), (36, 32)]
    pts = [(x + a * s, y + b * s) for a, b in forme]
    p.poly([(a + 3, b + 3) for a, b in pts], 0)
    p.poly(pts, 255)

def tuile(p, x, y, s, demi=70, col=255):
    if s <= 0.01: return
    p.rrect(x - demi * s, y - demi * s, x + demi * s, y + demi * s, 0.4 * demi * s, fill=col)

def maison(p, x, y, s, col, fond):
    p.poly([(x - 52 * s, y - 4 * s), (x, y - 50 * s), (x + 52 * s, y - 4 * s)], col)
    p.rrect(x - 38 * s, y - 10 * s, x + 38 * s, y + 42 * s, 4 * s, fill=col)
    p.rrect(x - 10 * s, y + 12 * s, x + 10 * s, y + 42 * s, 3 * s, fill=fond)

def voiture(p, x, y, s, col, fond):
    p.rrect(x - 30 * s, y - 34 * s, x + 26 * s, y - 4 * s, 12 * s, fill=col)
    p.rrect(x - 20 * s, y - 27 * s, x - 3 * s, y - 10 * s, 3 * s, fill=fond)
    p.rrect(x + 2 * s, y - 27 * s, x + 18 * s, y - 10 * s, 3 * s, fill=fond)
    p.rrect(x - 52 * s, y - 10 * s, x + 52 * s, y + 20 * s, 10 * s, fill=col)
    for dx in (-28, 28):
        p.cercle(x + dx * s, y + 22 * s, 14 * s, fill=col, outline=fond, w=4 * s)

def graphe_hausse(p, x, y, s, col):
    for i, h in enumerate((22, 40, 62)):
        bx = x - 34 * s + i * 26 * s
        p.rrect(bx - 9 * s, y + 34 * s - h * s, bx + 9 * s, y + 34 * s, 4 * s, fill=col)
    fleche(p, x - 44 * s, y - 2 * s, x + 40 * s, y - 40 * s, col, 6 * s, 20 * s)

def mallette(p, x, y, s, col, fond):
    p.rrect(x - 17 * s, y - 36 * s, x + 17 * s, y - 12 * s, 8 * s, outline=col, w=7 * s)
    p.rrect(x - 48 * s, y - 20 * s, x + 48 * s, y + 34 * s, 10 * s, fill=col)
    p.ligne([(x - 48 * s, y + 2 * s), (x + 48 * s, y + 2 * s)], fond, 4 * s)
    p.rrect(x - 8 * s, y - 4 * s, x + 8 * s, y + 8 * s, 3 * s, fill=col, outline=fond, w=3 * s)

def diplome(p, x, y, s, col, fond):
    p.rrect(x - 52 * s, y - 18 * s, x + 52 * s, y + 18 * s, 17 * s, fill=col)
    p.ellipse(x - 52 * s, y, 8 * s, 18 * s, fill=fond)
    p.ligne([(x + 14 * s, y - 18 * s), (x + 14 * s, y + 18 * s)], fond, 6 * s)
    p.poly([(x + 6 * s, y + 16 * s), (x + 22 * s, y + 16 * s), (x + 26 * s, y + 40 * s), (x + 14 * s, y + 32 * s),
            (x + 2 * s, y + 40 * s)], col)

def facture(p, x, y, s, col):
    pts = [(x - 32 * s, y - 42 * s), (x + 32 * s, y - 42 * s), (x + 32 * s, y + 42 * s)]
    for i in range(6):
        pts.append((x + 32 * s - (i + 0.5) * 64 / 6 * s, y + (36 if i % 2 == 0 else 44) * s))
    pts.append((x - 32 * s, y + 42 * s))
    p.poly(pts, col)
    for i, l in enumerate((40, 30, 40, 22)):
        yy = y - 26 * s + i * 15 * s
        p.ligne([(x - 20 * s, yy), (x - 20 * s + l * s, yy)], 0, 4 * s)

def etiquette(p, x, y, s, col, fond):
    p.poly([(x - 26 * s, y - 24 * s), (x - 50 * s, y), (x - 26 * s, y + 24 * s)], col)
    p.rrect(x - 30 * s, y - 24 * s, x + 46 * s, y + 24 * s, 8 * s, fill=col)
    p.cercle(x - 30 * s, y, 5 * s, fill=fond)
    p.texte(x + 10 * s, y + 2 * s, DEVISE, 34 * s, fond, "black")

def petite_bulle(p, x, y, s, col, fond):
    p.poly([(x - 18 * s, y + 18 * s), (x - 30 * s, y + 40 * s), (x - 2 * s, y + 22 * s)], col)
    p.rrect(x - 44 * s, y - 32 * s, x + 44 * s, y + 26 * s, 22 * s, fill=col)
    for j in range(3):
        p.cercle(x + (j - 1) * 20 * s, y - 3 * s, 6 * s, fill=fond)

def groupe(p, x, y, s, col, fond):
    for dx in (-30, 30):
        bonhomme(p, x + dx * s, y + 6 * s, 20 * s, col=g(130), plein=True, humeur=0.8)
    bonhomme(p, x, y + 12 * s, 26 * s, col=col, plein=True, humeur=1)

def etincelles(p, t, a, b, pos, r=16, col=255):
    if not (a < t < b): return
    u = pr(t, a, b)
    for i, (ex, ey) in enumerate(pos):
        rr = r * math.sin(math.pi * cl(u * 1.4 - i * 0.12))
        if rr > 1: etoile(p, ex, ey, rr, col, 4, 0.25, 0)


# ================================================================== LES SCENES
# ------------------------------------------------------------------ 1. deux peres
def scene_deux_peres(p, t, D):
    kt = pr(t, 3.3, 3.6)
    if kt > 0:
        z = 1 + 0.6 * (1 - e_out(pr(t, 3.3, 3.8)))
        p.texte(640, 92, "RICH DAD POOR DAD", 64 * z, g(255, kt), "black", contour=3)
        tracer(p, [(400, 140), (880, 140)], pr(t, 3.5, 4.1), g(110), 3)
    p.ligne([(200, 451), (1080, 451)], g(60), 3)
    humeur_g = 0.6 - 1.3 * e_inout(pr(t, 1.6, 2.4))
    bonhomme(p, 420, 360, 95 * pop(t, 0.2), humeur=humeur_g, regard=0.3, lunettes=True)
    bonhomme(p, 860, 360, 95 * pop(t, 0.5), humeur=1.0, regard=-0.3)
    for x, txt, v, ta in ((420, "POOR DAD", 150, 0.7), (860, "RICH DAD", 255, 1.0)):
        k = pr(t, ta, ta + 0.25)
        if k > 0: p.texte(x, 515, txt, 34, g(v, k), "black")
    n = int(pr(t, 1.2, 3.0) * 7.999)
    for i in range(n):
        piece_plate(p, 1000, 438 - i * 14, 34)
    if 1.3 < t < 3.0:
        u = pr(t, 1.3, 2.7)
        piece(p, 290, 330 + 110 * u * u, 24, 1 - u)


# ------------------------------------------------------------------ 2. les deux conseils
def scene_conseils(p, t, D):
    for x, lun, ta in ((330, True, 0.0), (950, False, 0.15)):
        bonhomme(p, x, 450, 85 * pop(t, ta), humeur=0.7 if lun else 1.0, regard=0.4 if lun else -0.4, lunettes=lun)
    p.ligne([(150, 531), (1130, 531)], g(60), 3)
    for x, txt, v in ((330, "POOR DAD", 150), (950, "RICH DAD", 255)):
        p.texte(x, 572, txt, 24, g(v), "black")
    kg = 1 - 0.55 * pr(t, 6.2, 6.7)
    s = pop(t, 0.4)
    if s > 0.01:
        bulle(p, 330, 195, 420, 175, s, (330, 360), g(14), g(235, kg))
        diplome(p, 270, 160, 0.95 * s, g(255, kg), g(14))
        mallette(p, 395, 165, 0.85 * s, g(255, kg), g(14))
        p.texte(330, 240, "STUDY HARD. GET A SAFE JOB.", 22 * s, g(255, kg), "semi")
    s = pop(t, 3.7)
    if s > 0.01:
        puls = 1 + 0.03 * math.sin((t - 6.2) * 7) if t > 6.2 else 1
        s2 = s * puls
        bulle(p, 950, 195, 420, 175, s2, (950, 360), g(14), g(255))
        piece(p, 885, 160, 30 * s2)
        engrenage(p, 1015, 160, 34 * s2, t * 1.5, g(255), trou=g(14))
        p.texte(950, 240, "LEARN HOW MONEY WORKS.", 22 * s2, g(255), "semi")


# ------------------------------------------------------------------ 3. la course du rat
def scene_rat_race(p, t, D):
    cx, cy, R = 640, 372, 180
    s = pop(t, 0.1, 0.45)
    if s > 0.01:
        rot = t * 2.4
        for i in range(8):
            a = rot + i * math.pi / 4
            p.ligne([(cx + R * 0.12 * s * math.cos(a), cy + R * 0.12 * s * math.sin(a)),
                     (cx + R * 0.96 * s * math.cos(a), cy + R * 0.96 * s * math.sin(a))], g(70), 3)
        p.cercle(cx, cy, R * s, outline=g(210), w=8)
        p.cercle(cx, cy, 13 * s, fill=g(210))
        bob = abs(math.sin(t * 14)) * 7
        bonhomme(p, cx - 6, cy + R * s - 72 - bob, 62 * s, humeur=-0.2, regard=0.9)
        for j in range(3):
            yy = cy + R * s - 120 + j * 22
            l = 26 + 10 * math.sin(t * 20 + j)
            p.ligne([(cx - 70 - l, yy), (cx - 62, yy)], g(110), 3)
    ks = pr(t, 2.5, 2.8)
    if ks > 0:
        piece(p, 175, 260, 30, ks)
        p.texte(175, 325, "SALARY", 28, g(230, ks), "black")
        facture(p, 1105, 262, 0.85, g(255, ks))
        p.texte(1105, 325, "BILLS", 28, g(230, ks), "black")
    for c in range(5):
        st = 2.7 + c * 1.05
        u = t - st
        if 0 < u < 1.0:
            if u < 0.5:
                x, y = lerp(215, cx, e_inout(u / 0.5)), lerp(260, cy - 40, e_inout(u / 0.5)) - 60 * math.sin(math.pi * u / 0.5)
                k = 1
            else:
                v = (u - 0.5) / 0.5
                x, y = lerp(cx, 1060, e_inout(v)), lerp(cy - 40, 262, e_inout(v)) - 60 * math.sin(math.pi * v)
                k = 1 - pr(v, 0.75, 1)
            piece(p, x, y, 20, k)
    sr = pop(t, 5.4, 0.4)
    if sr > 0.01:
        p.texte(640, 92, "THE RAT RACE", 60 * sr, g(255), "black", contour=3)


# ------------------------------------------------------------------ 4. actif ou passif
def scene_actif_passif(p, t, D):
    st = pop(t, 0.3, 0.4)
    if st > 0.01:
        p.texte(640, 125, "ASSET  vs  LIABILITY", 54 * st, g(255), "black", contour=3)
    sp = pop(t, 0.2)
    if sp > 0.01:
        p.rrect(640 - 110 * sp, 360 - 95 * sp, 640 + 110 * sp, 360 + 95 * sp, 34 * sp, outline=g(255), w=6)
        for i in range(10):
            xx = 545 + i * 20
            if xx < 640 + 95 * sp and xx > 640 - 95 * sp:
                p.ligne([(xx, 300), (xx + 9, 300)], g(150), 3)
        p.texte(640, 492, "YOUR POCKET", 24, g(190, pr(t, 0.4, 0.6)), "black")
    n_in = sum(1 for i in range(9) if t > 2.4 + 0.25 * i + 0.5)
    n_out = sum(1 for i in range(9) if t > 5.6 + 0.3 * i + 0.5)
    val = 150 * n_in - 125 * n_out
    kv = pr(t, 2.3, 2.5)
    if kv > 0:
        p.texte(640, 360, f"{DEVISE}{max(val, 0):,}", 46, g(255, kv), "black")
    sa = pop(t, 1.8)
    if sa > 0.01:
        tuile(p, 230, 340, sa)
        graphe_hausse(p, 230, 340, sa, 0)
        p.texte(230, 448, "ASSET", 34 * sa, g(255), "black")
        fleche_progressive(p, 320, 420, 525, 420, pr(t, 2.2, 2.6), g(110), 4)
        p.texte(420, 448, "MONEY IN", 18, g(150, pr(t, 2.4, 2.7)), "bold")
    sl = pop(t, 5.0)
    if sl > 0.01:
        tuile(p, 1050, 340, sl)
        voiture(p, 1050, 340, sl, 0, 255)
        p.texte(1050, 448, "LIABILITY", 34 * sl, g(255), "black")
        fleche_progressive(p, 755, 420, 960, 420, pr(t, 5.4, 5.8), g(110), 4)
        p.texte(860, 448, "MONEY OUT", 18, g(150, pr(t, 5.6, 5.9)), "bold")
    for i in range(9):
        u = pr(t, 2.4 + 0.25 * i, 2.9 + 0.25 * i)
        if 0 < u < 1:
            piece(p, lerp(310, 520, e_inout(u)), lerp(340, 360, u) - 45 * math.sin(math.pi * u), 17,
                  1 - pr(u, 0.85, 1))
        u = pr(t, 5.6 + 0.3 * i, 6.1 + 0.3 * i)
        if 0 < u < 1:
            piece(p, lerp(760, 970, e_inout(u)), lerp(360, 340, u) - 45 * math.sin(math.pi * u), 17,
                  1 - pr(u, 0.85, 1))


# ------------------------------------------------------------------ 5. les trois schemas de flux d'argent
def boite(p, x, y, txt, k, plein=False):
    if k <= 0.01: return
    s = e_back(k)
    if plein:
        p.rrect(x - 125 * s, y - 34 * s, x + 125 * s, y + 34 * s, 18 * s, fill=g(255))
        p.texte(x, y + 1, txt, 24 * s, 0, "black")
    else:
        p.rrect(x - 125 * s, y - 34 * s, x + 125 * s, y + 34 * s, 18 * s, fill=g(14), outline=g(200), w=3)
        p.texte(x, y + 1, txt, 24 * s, g(235), "black")

def flux(p, t, x0, y0, x1, y1, ta, col=255, periode=0.7):
    tracer(p, [(x0, y0), (x1, y1)], pr(t, ta, ta + 0.3), g(120), 3)
    if t > ta + 0.3:
        fleche(p, x1 - (x1 - x0) * 0.01, y1 - (y1 - y0) * 0.01, x1, y1, g(120), 3, 12)
        u = ((t - ta - 0.3) / periode) % 1
        p.cercle(lerp(x0, x1, u), lerp(y0, y1, u), 7, fill=g(col))

def scene_flux(p, t, D):
    cols = [(230, "POOR", 160, 0.2), (640, "MIDDLE CLASS", 205, 2.4), (1050, "RICH", 255, 6.2)]
    for x, titre, v, ta in cols:
        s = pop(t, ta)
        if s > 0.01: p.texte(x, 95, titre, 36 * s, g(v), "black")
    for x in (435, 845):
        tracer(p, [(x, 80), (x, 560)], pr(t, 0.1, 0.8), g(45), 2)
    # pauvres
    boite(p, 230, 190, "JOB", pr(t, 0.5, 0.85))
    flux(p, t, 230, 228, 230, 290, 0.9)
    boite(p, 230, 330, "EXPENSES", pr(t, 1.1, 1.45))
    flux(p, t, 230, 368, 230, 425, 1.5, 150)
    k = pr(t, 1.8, 2.1)
    if k > 0: p.texte(230, 460, f"{DEVISE}0 LEFT", 28, g(150, k), "black")
    # classe moyenne
    boite(p, 640, 190, "JOB", pr(t, 2.7, 3.05))
    flux(p, t, 640, 228, 640, 290, 3.1)
    boite(p, 640, 330, "LIABILITIES", pr(t, 3.4, 3.75))
    flux(p, t, 640, 368, 640, 430, 3.8)
    boite(p, 640, 470, "EXPENSES", pr(t, 4.0, 4.35))
    sm = pop(t, 4.9)
    if sm > 0.01:
        maison(p, 640, 555, 0.75 * sm, g(255), 0)
        p.texte(720, 568, "?", 34 * sm, g(255), "black")
    # riches
    boite(p, 1050, 190, "ASSETS", pr(t, 6.6, 6.95), plein=True)
    flux(p, t, 1050, 228, 1050, 290, 7.0)
    boite(p, 1050, 330, "INCOME", pr(t, 7.3, 7.65), plein=True)
    boucle = arc_pts(1180, 260, 70, math.pi / 2, -math.pi / 2, 40)
    pb = pr(t, 7.8, 8.4)
    tracer(p, boucle, pb, g(200), 4)
    if pb >= 1:
        fleche(p, 1186, 190, 1178, 190, g(200), 4, 16)
        u = ((t - 8.4) / 0.9) % 1
        x, y = point_sur(boucle, u)
        p.cercle(x, y, 7, fill=255)
    k = pr(t, 8.4, 8.7)
    if k > 0: p.texte(1050, 455, "MORE ASSETS", 26, g(255, k), "black")
    etincelles(p, t, 8.4, 9.4, [(930, 150), (1180, 150), (1200, 380), (920, 380)])


# ------------------------------------------------------------------ 6. la colonne des actifs
ACTIFS = [("STOCKS", "graphe"), ("REAL ESTATE", "maison"), ("BUSINESS", "engrenage")]

def scene_colonne(p, t, D):
    s = pop(t, 0.3)
    if s > 0.01:
        tuile(p, 260, 320, s)
        mallette(p, 260, 322, s, 0, 255)
        p.texte(260, 430, "KEEP YOUR JOB", 28 * s, g(230), "black")
    sc = pop(t, 1.0)
    if sc > 0.01:
        p.texte(890, 100, "ASSET COLUMN", 36 * sc, g(255), "black")
        p.rrect(890 - 130 * sc, 140, 890 + 130 * sc, 580, 22, outline=g(200), w=4)
    tracer(p, [(350, 320), (720, 320)], pr(t, 1.6, 2.0), g(110), 4)
    if t > 2.0:
        fleche(p, 712, 320, 730, 320, g(110), 4, 14)
        u = ((t - 2.0) / 0.8) % 1
        piece(p, lerp(370, 700, u), 320, 13, 1 - pr(u, 0.85, 1))
    for i, (nom, icone) in enumerate(ACTIFS):
        ta = (2.6, 4.0, 5.4)[i]
        if t < ta: continue
        cy_f = 505 - i * 145
        u = pr(t, ta, ta + 0.45)
        cy = -120 + (cy_f + 120) * e_back(u)
        p.rrect(775, cy - 64, 1005, cy + 64, 18, fill=g(255))
        if icone == "graphe":
            graphe_hausse(p, 890, cy - 16, 0.7, 0)
        elif icone == "maison":
            maison(p, 890, cy - 16, 0.62, 0, 255)
        else:
            engrenage(p, 890, cy - 16, 28, t * 1.6, 0, trou=255)
        p.texte(890, cy + 40, nom, 22, 0, "black")
    etincelles(p, t, 5.9, 6.9, [(760, 160), (1020, 150), (1035, 300), (745, 290)])


# ------------------------------------------------------------------ 7. l'argent travaille pour toi
GEN = [[(170, 335)], [(470, 210), (470, 460)], [(790, 120), (790, 265), (790, 405), (790, 550)]]
PARENT = {1: [0, 0], 2: [0, 0, 1, 1]}
DEPART = {1: 1.0, 2: 3.6}

def machine(p, x, y, s, t):
    if s <= 0.01: return
    tuile(p, x, y, s, 48)
    engrenage(p, x, y, 30 * s, t * 1.8 + x, 0, trou=255)

def scene_machines(p, t, D):
    for gen in (1, 2):
        ta = DEPART[gen]
        for j, (x, y) in enumerate(GEN[gen]):
            px, py = GEN[gen - 1][PARENT[gen][j]]
            d = ta + 0.12 * j
            tracer(p, [(px + 50, py), (x - 50, y)], pr(t, d, d + 0.5), g(70), 3)
            u = pr(t, d, d + 0.55)
            if 0 < u < 1:
                piece(p, lerp(px + 50, x - 50, e_inout(u)), lerp(py, y, e_inout(u)) - 40 * math.sin(math.pi * u), 16)
    machine(p, *GEN[0][0], pop(t, 0.2), t)
    for gen in (1, 2):
        for j, (x, y) in enumerate(GEN[gen]):
            machine(p, x, y, pop(t, DEPART[gen] + 0.12 * j + 0.5), t)
    kc = pr(t, 0.4, 0.7)
    if kc > 0:
        n = 1 + sum(1 for gen in (1, 2) for j in range(len(GEN[gen])) if t > DEPART[gen] + 0.12 * j + 0.55)
        p.texte(170, 450, f"ASSETS: {n}", 26, g(220, kc), "black")
    if t > 5.6:
        k = pr(t, 5.6, 5.9)
        p.texte(1120, 300, "INCOME", 40, g(255, k), "black")
        total = int(e_inout(pr(t, 5.9, 7.8)) * 48500)
        p.texte(1120, 360, f"+{DEVISE}{total:,}", 34, g(200, k), "black")
        for j, (x, y) in enumerate(GEN[2]):
            for c in range(4):
                u = ((t - 5.8 - c * 0.45 - j * 0.1) / 0.9)
                if 0 < u < 1:
                    piece(p, lerp(x + 50, 1030, u), lerp(y, 330, u), 12, 1 - pr(u, 0.8, 1))


# ------------------------------------------------------------------ 8. travailler pour apprendre
MARCHES = [(200, 450, 500), (450, 700, 410), (700, 950, 320)]
COMPETENCES = [("SELL", "etiquette"), ("COMMUNICATE", "bulle"), ("LEAD", "groupe")]

def scene_apprendre(p, t, D):
    s = pop(t, 0.2)
    if s > 0.01:
        p.texte(300, 80, "WORK TO LEARN", 48 * s, g(255), "black")
        p.texte(300, 128, "not just to earn", 26 * s, g(160), "semi")
    p.ligne([(110, 600), (1170, 600)], g(60), 3)
    for i, (x0, x1, yt) in enumerate(MARCHES):
        k = pr(t, 0.4 + 0.15 * i, 0.7 + 0.15 * i)
        if k > 0:
            p.rrect(x0, lerp(600, yt, e_out(k)), x1, 600, 10, fill=g(28), outline=g(150), w=3)
    pos = [(140, 600)] + [((x0 + x1) / 2, yt) for x0, x1, yt in MARCHES]
    sauts = [2.4, 3.6, 4.8]
    etape = sum(1 for s_ in sauts if t > s_ + 0.45)
    x, yb = pos[etape]
    if etape < 3 and t > sauts[etape]:
        u = pr(t, sauts[etape], sauts[etape] + 0.45)
        x0, y0 = pos[etape]; x1, y1 = pos[etape + 1]
        x = lerp(x0, x1, e_inout(u)); yb = lerp(y0, y1, u) - 70 * math.sin(math.pi * u)
    taille = 58
    bonhomme(p, x, yb - 0.95 * taille, taille, humeur=1.0, regard=0.7)
    for i, (nom, icone) in enumerate(COMPETENCES):
        x0, x1, yt = MARCHES[i]
        sb = pop(t, sauts[i] + 0.35)
        if sb <= 0.01: continue
        bx, by = (x0 + x1) / 2, yt - 205
        p.cercle(bx, by, 46 * sb, fill=g(255))
        if icone == "etiquette":
            etiquette(p, bx, by, 0.75 * sb, 0, 255)
        elif icone == "bulle":
            petite_bulle(p, bx, by, 0.75 * sb, 0, 255)
        else:
            groupe(p, bx, by - 6, 0.85 * sb, 0, 255)
        p.texte(bx, by - 72, nom, 24 * sb, g(255), "black")
    etincelles(p, t, 5.3, 6.3, [(760, 190), (900, 160), (930, 300), (720, 290)])


# ------------------------------------------------------------------ 9. se payer en premier
def scene_payer(p, t, D):
    k = pr(t, 0.1, 0.4)
    if k > 0: p.texte(640, 62, "PAYCHECK", 30, g(200, k), "black")
    depart = [(565 + (i % 4) * 50, 120 + (i // 4) * 48) for i in range(8)]
    jar_x, bill_x = 360, 920
    s = pop(t, 0.3)
    if s > 0.01:
        p.rrect(jar_x - 80 * s, 560 - 220 * s, jar_x + 80 * s, 560, 30 * s, outline=g(255), w=5)
        p.rrect(jar_x - 92 * s, 560 - 232 * s, jar_x + 92 * s, 560 - 214 * s, 6 * s, fill=g(255))
        facture(p, bill_x - 30, 450, 1.25 * s, g(110))
        facture(p, bill_x + 10, 440, 1.25 * s, g(170))
        facture(p, bill_x + 50, 455, 1.25 * s, g(235))
    arrivees = 0
    for i, (x0, y0) in enumerate(depart):
        ta = (1.0 + 0.3 * i) if i < 2 else (2.8 + 0.2 * (i - 2))
        cible = (jar_x, 470) if i < 2 else (bill_x + 10, 430)
        u = pr(t, ta, ta + 0.5)
        if u <= 0:
            piece(p, x0, y0, 20, pr(t, 0.2 + 0.04 * i, 0.4 + 0.04 * i))
        elif u < 1:
            piece(p, lerp(x0, cible[0], e_inout(u)), lerp(y0, cible[1], u) - 90 * math.sin(math.pi * u), 20)
        elif i < 2:
            arrivees += 1
    niveau = 0
    for i in range(2):
        niveau += e_out(pr(t, 1.5 + 0.3 * i, 1.8 + 0.3 * i))
    if niveau > 0.02:
        h = 90 * niveau
        p.rrect(jar_x - 72, 553 - h, jar_x + 72, 553, 24, fill=g(205))
        p.texte(jar_x, 553 - h / 2, DEVISE, 40, 0, "black")
    for x, txt, ta in ((jar_x, "1.  YOU", 1.6), (bill_x + 10, "2.  BILLS", 3.6)):
        sl = pop(t, ta)
        if sl > 0.01: p.texte(x, 608, txt, 30 * sl, g(255), "black")
    etincelles(p, t, 1.9, 2.9, [(260, 330), (460, 320), (470, 470), (250, 470)])


# ------------------------------------------------------------------ 10. resume + abonnement
LECONS = ["BUY ASSETS.", "GROW YOUR COLUMN.", "LET MONEY WORK FOR YOU."]

def scene_fin(p, t, D):
    sortie = e_inout(pr(t, 3.6, 4.1))
    for i, txt in enumerate(LECONS):
        s = pop(t, 0.2 + 0.85 * i)
        if s <= 0.01: continue
        y = 175 + 85 * i - 120 * sortie
        k = 1 - sortie * 0.75
        p.texte(640, y, txt, 52 * s, g(255, k), "black")
        if s > 0.6:
            coche(p, 640 - p.largeur(txt, 52, "black") / 2 - 40, y + 2, 34, pr(t, 0.35 + 0.85 * i, 0.6 + 0.85 * i),
                  g(255, k), 7)
    ks = pr(t, 4.0, 4.3)
    if ks > 0:
        p.rrect(420, 330, 860, 398, 34, outline=g(150, ks), w=3)
        p.cercle(462, 360, 13, outline=g(200, ks), w=4)
        p.ligne([(472, 371), (484, 383)], g(200, ks), 5)
        n = int(pr(t, 4.2, 4.9) * len(PSEUDO) + 0.001)
        p.texte(502, 365, PSEUDO[:n], 34, g(255, ks), "bold", anchor="lm")
        if int(t * 3) % 2 == 0:
            xc = 506 + p.largeur(PSEUDO[:n], 34, "bold")
            p.ligne([(xc, 347), (xc, 383)], g(255, ks), 3)
    sb = pop(t, 5.0, 0.35)
    if sb > 0.01:
        abonne = t > 6.35
        y = 488 - (abs(math.sin((t - 5.35) * 6)) * 12 if 5.35 < t < 6.2 else 0)
        clic = 1 - 0.07 * math.sin(math.pi * pr(t, 6.2, 6.4))
        w, h = 170 * sb * clic, 42 * sb * clic
        if abonne:
            p.rrect(640 - w, y - h, 640 + w, y + h, h, fill=g(30), outline=g(200), w=3)
            p.texte(655, y + 2, "SUBSCRIBED", 32 * sb, g(220), "black")
            coche(p, 518, y + 2, 26, pr(t, 6.35, 6.6), g(220), 6)
        else:
            p.rrect(640 - w, y - h, 640 + w, y + h, h, fill=g(255))
            p.texte(640, y + 2, "SUBSCRIBE", 36 * sb * clic, 0, "black")
        if t < 6.9:
            u = e_inout(pr(t, 5.5, 6.15))
            curseur(p, lerp(960, 690, u), lerp(560, 500, u), clic)


# ------------------------------------------------------------------ liste des scenes
# textes = (debut, fin, "sous-titre") en secondes dans la scene
# voix   = (moment_dans_scene, debut_dans_mp3, fin_dans_mp3)  -> rempli une fois la voix recue
# cles   = (temps_video, temps_animation) : pour accelerer/ralentir l'animation et suivre la voix
# sons   = bruitages (moment, type)
SCENES = [
    dict(f=scene_deux_peres, duree=6.0,
         textes=[(0.0, 3.2, "Two dads. One stayed poor. The other became rich."),
                 (3.2, 6.0, "Here's what Rich Dad Poor Dad teaches about money.")],
         voix=[], sons=[(0.2, "pop"), (0.5, "pop"), (1.3, "erreur")] + [(1.2 + 0.25 * i, "clic") for i in range(7)]
                       + [(3.3, "boum")]),
    dict(f=scene_conseils, duree=8.0,
         textes=[(0.0, 3.6, "One dad said: study hard, and get a safe job."),
                 (3.6, 8.0, "The other said: learn how money works.")],
         voix=[], sons=[(0.4, "pop"), (3.7, "pop"), (6.2, "bip")]),
    dict(f=scene_rat_race, duree=8.0,
         textes=[(0.0, 2.5, "Most people work for money."), (2.5, 5.3, "Earn. Pay the bills. Repeat."),
                 (5.3, 8.0, "That's the rat race.")],
         voix=[], sons=[(0.1, "souffle")] + [(2.7 + c * 1.05, "piece") for c in range(5)] + [(5.4, "boum")]),
    dict(f=scene_actif_passif, duree=9.0,
         textes=[(0.0, 1.8, "Rule one: know the difference."), (1.8, 5.0, "An asset puts money in your pocket."),
                 (5.0, 9.0, "A liability takes money out.")],
         voix=[], sons=[(0.2, "pop"), (1.8, "pop"), (5.0, "pop")] + [(2.9 + 0.25 * i, "clic") for i in range(9)]
                       + [(6.1 + 0.3 * i, "clic") for i in range(9)]),
    dict(f=scene_flux, duree=10.0,
         textes=[(0.0, 2.4, "The poor spend everything they earn."),
                 (2.4, 6.2, "The middle class buys liabilities they think are assets... like a bigger house."),
                 (6.2, 10.0, "The rich buy assets first.")],
         voix=[], sons=[(0.2, "pop"), (2.4, "pop"), (4.9, "erreur"), (6.2, "boum"), (8.4, "piece")]),
    dict(f=scene_colonne, duree=8.0,
         textes=[(0.0, 2.4, "Keep your job, but build your asset column:"),
                 (2.4, 8.0, "stocks, real estate, businesses that run without you.")],
         voix=[], sons=[(0.3, "pop"), (1.0, "pop"), (3.05, "boum"), (4.45, "boum"), (5.85, "boum"), (5.9, "piece")]),
    dict(f=scene_machines, duree=8.0,
         textes=[(0.0, 3.4, "Each asset pays you."),
                 (3.4, 8.0, "Then that money buys more assets. Now, money works for you.")],
         voix=[], sons=[(0.2, "pop"), (1.55, "pop"), (4.15, "pop"), (4.4, "pop"), (5.6, "boum"), (5.9, "piece"),
                        (6.8, "piece")]),
    dict(f=scene_apprendre, duree=7.0,
         textes=[(0.0, 2.2, "Work to learn, not just to earn."), (2.2, 7.0, "Learn to sell, to communicate, to lead.")],
         voix=[], sons=[(0.2, "pop"), (2.85, "bip"), (4.05, "bip"), (5.25, "bip"), (5.3, "piece")]),
    dict(f=scene_payer, duree=6.0,
         textes=[(0.0, 6.0, "And pay yourself first, before the bills.")],
         voix=[], sons=[(1.5, "piece"), (1.8, "piece"), (1.9, "bip")] + [(3.3 + 0.2 * i, "clic") for i in range(6)]),
    dict(f=scene_fin, duree=8.0,
         textes=[(0.0, 3.6, "Buy assets. Grow your column. Let money work for you."),
                 (3.6, 8.0, "Subscribe for more books explained simply.")],
         voix=[], sons=[(0.2, "pop"), (1.05, "pop"), (1.9, "pop")] + [(4.2 + 0.175 * i, "clic") for i in range(4)]
                       + [(5.0, "pop"), (6.2, "clic"), (6.35, "bip")]),
]


# ================================================================== RENDU
def temps_anim(sc, t):
    if not sc.get("cles"): return t
    n, a = zip(*sc["cles"])
    return float(np.interp(t, n, a))

def temps_son(sc, t):
    if not sc.get("cles"): return t
    n, a = zip(*sc["cles"])
    return float(np.interp(t, a, n))

def sous_titres(img, textes, t, D):
    p = Stylo(img, ECHELLE)
    taille, inter = 30, 40
    for a, b, txt in textes:
        if not (a <= t < b): continue
        k = pr(t, a, a + 0.15)
        if b < D - 0.05:
            k = min(k, pr(b - t, 0, 0.12))
        if k <= 0: continue
        mots = txt.split()
        lignes = [txt]
        if p.largeur(txt, taille, "semi") > 1000:
            coupes = [(" ".join(mots[:c]), " ".join(mots[c:])) for c in range(1, len(mots))]
            lignes = list(min(coupes, key=lambda c: max(p.largeur(c[0], taille, "semi"), p.largeur(c[1], taille, "semi"))))
        y0 = SOUS_TITRE_Y + (1 - e_out(k)) * 8 - (len(lignes) - 1) * inter / 2
        for i, l in enumerate(lignes):
            p.texte(640, y0 + i * inter, l, taille, g(255, k), "semi", contour=3, col_contour=0)

def image(i, t):
    sc = SCENES[i]; D = sc["duree"]
    grand = Image.new("L", (LARGEUR * SS, HAUTEUR * SS), 0)
    sc["f"](Stylo(grand, SS * ECHELLE), temps_anim(sc, t), D)
    img = grand.resize((LARGEUR, HAUTEUR), Image.LANCZOS)
    a = np.asarray(img).astype(np.float32)
    petit = img.resize((LARGEUR // 4, HAUTEUR // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(5 * ECHELLE))
    lueur = np.asarray(petit.resize((LARGEUR, HAUTEUR), Image.BILINEAR)).astype(np.float32)
    a = np.minimum(a + lueur * 0.75, 255)
    k = 1.0
    if sc.get("fondu_entree", True): k *= e_inout(pr(t, 0, 0.25))
    if sc.get("fondu_sortie", True): k *= e_inout(pr(D - t, 0, 0.25))
    if k < 1: a *= k
    img = Image.fromarray(a.astype(np.uint8))
    z = 1 + 0.035 * (1 - e_out(pr(t, 0, 0.5)))    # leger zoom d'entree, plus cinema
    if z > 1.001:
        w2, h2 = LARGEUR / z, HAUTEUR / z
        img = img.resize((LARGEUR, HAUTEUR), Image.BICUBIC,
                         box=((LARGEUR - w2) / 2, (HAUTEUR - h2) / 2, (LARGEUR + w2) / 2, (HAUTEUR + h2) / 2))
    sous_titres(img, sc["textes"], t, D)
    return img

def rendre_scene(i):
    sc = SCENES[i]
    nb = int(round(sc["duree"] * FPS))
    chemin = f"rd_scene_{i + 1:02d}.mp4"; tmp = chemin + ".tmp.mp4"
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{LARGEUR}x{HAUTEUR}",
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
        n = int(0.14 * SR); tt = np.arange(n) / SR
        return 0.2 * np.sin(2 * np.pi * 880 * tt) * _env(n, 0.05)
    if nom == "pop":
        n = int(0.12 * SR); tt = np.arange(n) / SR
        ph = 2 * np.pi * np.cumsum(380 + 820 * tt / 0.12) / SR
        return 0.25 * np.sin(ph) * _env(n, 0.05)
    if nom == "clic":
        n = int(0.03 * SR)
        return 0.2 * rng.uniform(-1, 1, n) * _env(n, 0.006)
    if nom == "piece":
        n = int(0.5 * SR); tt = np.arange(n) / SR
        return (0.14 * np.sin(2 * np.pi * 1320 * tt) + 0.1 * np.sin(2 * np.pi * 1760 * tt)
                + 0.05 * np.sin(2 * np.pi * 2640 * tt)) * _env(n, 0.13)
    if nom == "boum":
        n = int(0.6 * SR); tt = np.arange(n) / SR
        ph = 2 * np.pi * np.cumsum(38 + 100 * np.exp(-tt * 8)) / SR
        return 0.6 * np.sin(ph) * _env(n, 0.2)
    if nom == "erreur":
        n = int(0.22 * SR); tt = np.arange(n) / SR
        return 0.12 * (np.sin(2 * np.pi * 196 * tt) + 0.5 * np.sin(2 * np.pi * 588 * tt)) * _env(n, 0.09)
    if nom == "souffle":
        n = int(0.6 * SR); tt = np.arange(n) / SR
        b = np.convolve(rng.uniform(-1, 1, n), np.ones(30) / 30, mode="same")
        return 1.3 * b * np.sin(np.pi * tt / 0.6) ** 2
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

def fabriquer_son(chemin="rd_son.wav"):
    total = sum(s["duree"] for s in SCENES)
    n = int(total * SR); tt = np.arange(n) / SR
    # nappe grave, calme et "cinema"
    nappe = np.zeros(n)
    for f, a in [(55, 1.0), (82.5, 0.45), (110, 0.6), (165, 0.25), (220, 0.15)]:
        nappe += a * (np.sin(2 * np.pi * f * tt) + np.sin(2 * np.pi * f * 1.004 * tt))
    nappe *= 0.035 * (0.75 + 0.25 * np.sin(2 * np.pi * 0.2 * tt))
    musique = nappe
    kick = bruitage("boum") * 0.28
    for b in np.arange(0, total, 0.6):      # 100 bpm, pose
        ajouter(musique, kick[: int(0.3 * SR)], b)
        ajouter(musique, bruitage("clic") * 0.18, b + 0.3)
    debut = 0.0
    for s in SCENES:
        if debut > 0: ajouter(musique, bruitage("souffle") * 0.7, debut - 0.2)
        for t, nom in s["sons"]:
            ajouter(musique, bruitage(nom), debut + temps_son(s, t))
        debut += s["duree"]
    musique /= max(1e-6, np.abs(musique).max()) / 0.6
    fi, fo = int(0.8 * SR), int(2.0 * SR)
    musique[:fi] *= np.linspace(0, 1, fi)
    musique[-fo:] *= np.linspace(1, 0, fo)
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
            ajouter(piste_voix, voix.astype(np.float64), 0.3)
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
    os.makedirs("apercu_rd", exist_ok=True)
    for i, sc in enumerate(SCENES):
        for pc in (0.45, 0.85):
            image(i, sc["duree"] * pc).save(f"apercu_rd/scene{i + 1}_{int(pc * 100)}.png")
    print("Apercus enregistres dans le dossier 'apercu_rd'.")

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if "--apercu" in sys.argv:
        apercu(); sys.exit()
    print("Fabrication des scenes (cela peut prendre quelques minutes en Full HD)...")
    with ProcessPoolExecutor(max_workers=os.cpu_count() or 2) as ex:
        fichiers = list(ex.map(rendre_scene, range(len(SCENES))))
    with open("rd_liste.txt", "w") as f:
        for c in fichiers: f.write(f"file '{c}'\n")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", "rd_liste.txt",
                    "-c", "copy", "rd_sans_son.mp4"], check=True)
    print("Fabrication du son...")
    fabriquer_son("rd_son.wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", "rd_sans_son.mp4", "-i", "rd_son.wav", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", FICHIER_SORTIE], check=True)
    for c in fichiers + ["rd_liste.txt", "rd_sans_son.mp4", "rd_son.wav"]:
        try: os.remove(c)
        except OSError: pass
    print("Termine :", FICHIER_SORTIE)
