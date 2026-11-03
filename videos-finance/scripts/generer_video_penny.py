# -*- coding: utf-8 -*-
"""
generer_video_penny.py  -  "$1,000,000 now... or 1 penny doubled every day for 30 days?"
Video TikTok verticale 1080x1920, style minimaliste noir et blanc + accent jaune.
Sous-titres mot a mot (style karaoke), accroche immediate, fin qui boucle sur le debut.

Pour fabriquer la video :        python generer_video_penny.py
Pour un apercu rapide (images) : python generer_video_penny.py --apercu
Si "voix_penny.mp3" (ElevenLabs) est dans le meme dossier, il est ajoute automatiquement.
"""
import math, os, sys, subprocess, wave
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# =========================== REGLAGES (modifiables) ===========================
LARGEUR, HAUTEUR = 1080, 1920       # TikTok Full HD vertical
FPS = 30
QUALITE = 16
PSEUDO = "@MTM"
VOIX_FICHIER = "voix_penny.mp3"
VITESSE_VOIX = 1.06
FICHIER_SORTIE = "video_penny.mp4"
BLANC, NOIR = (255, 255, 255), (0, 0, 0)
JAUNE = (255, 212, 0)
ROUGE = (235, 55, 45)
SOUS_TITRE_Y = 905                  # repere 720 x 1280
# ==============================================================================

BASE_L, BASE_H = 720, 1280
ECHELLE = LARGEUR / BASE_L
SS = 2
SR = 44100

# ------------------------------------------------------------------ LE TEXTE (et son timing)
# (debut, fin, phrase) en secondes. Les sous-titres s'affichent mot par mot.
PHRASES = [
    (0.10, 1.70, "$1,000,000 right now..."),
    (1.80, 4.20, "or 1 penny that doubles every day for 30 days?"),
    (4.35, 5.60, "Pick one. Seriously."),
    (5.90, 7.10, "Day 1: 1 cent."),
    (7.30, 8.70, "Day 10: $5."),
    (8.90, 10.50, "Day 20: $5,000."),
    (10.70, 12.10, "You'd feel stupid right now."),
    (12.25, 13.00, "But watch."),
    (13.20, 15.60, "Day 25: $167,000."),
    (15.80, 18.00, "Day 28: $1.3 million."),
    (18.20, 19.20, "Day 30..."),
    (19.40, 21.40, "$5.3 million."),
    (21.60, 23.00, "That's compound growth."),
    (23.10, 25.20, "Almost all of it happens at the end."),
    (25.30, 27.10, "Most people quit on day 20."),
    (27.30, 29.40, "So... which one did you pick?"),
]
VOIX = []                            # (moment, debut_mp3, fin_mp3) -> rempli quand la voix arrive

# moments cles de l'animation (en secondes)
M = dict(chart=5.75, crossing=15.85, tension=18.2, day30=19.45, lecon=21.6, part97=23.1, quit=25.3,
         boucle=27.2, fin=29.8)
# jour de la courbe en fonction du temps : (temps, jour)
JOURS = [(0, 1), (6.95, 1), (7.45, 10), (8.95, 20), (12.9, 20), (13.25, 25), (15.85, 28), (18.2, 29.0),
         (19.3, 29.35), (19.45, 30), (99, 30)]
JOUR_AFFICHE = [(0, 1), (6.95, 1), (7.45, 10), (8.95, 20), (12.9, 20), (13.25, 25), (15.85, 28), (18.1, 28.99),
                (18.25, 30), (99, 30)]


# ------------------------------------------------------------------ outils
def cl(x, a=0.0, b=1.0): return max(a, min(b, x))
def pr(t, a, b):
    if b <= a: return 1.0 if t >= a else 0.0
    return cl((t - a) / (b - a))
def e_out(x): x = cl(x); return 1 - (1 - x) ** 3
def e_inout(x): x = cl(x); return 3 * x * x - 2 * x * x * x
def e_back(x):
    x = cl(x); c = 1.70158
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2
def pop(t, a, dur=0.35): return e_back(pr(t, a, a + dur))
def g(v, k=1.0): v = int(cl(v * k, 0, 255)); return (v, v, v)
def mul(c, k): return tuple(int(cl(x * k, 0, 255)) for x in c)
def lerp(a, b, u): return a + (b - a) * u
def interp(t, cles):
    n, v = zip(*cles); return float(np.interp(t, n, v))

def valeur(jour):
    return 0.01 * 2 ** (jour - 1)

def argent(v):
    return f"${v:,.2f}" if v < 1000 else f"${v:,.0f}"


# ------------------------------------------------------------------ polices
_D = "/usr/share/fonts/opentype/inter/"
_W = "C:/Windows/Fonts/"
POLICES = {
    "black": ["Inter-Black.otf", _D + "Inter-Black.otf", _D + "Inter-ExtraBold.otf", _W + "Inter-Black.ttf",
              _W + "ariblk.ttf", _W + "seguibl.ttf", _W + "arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "bold": ["Inter-Bold.otf", _D + "Inter-Bold.otf", _W + "Inter-Bold.ttf", _W + "segoeuib.ttf", _W + "arialbd.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
}
_cache = {}
def police(nom, taille):
    taille = max(1, int(round(taille))); cle = (nom, taille)
    if cle not in _cache:
        for chemin in POLICES[nom]:
            if os.path.exists(chemin):
                _cache[cle] = ImageFont.truetype(chemin, taille); break
        else:
            _cache[cle] = ImageFont.load_default()
    return _cache[cle]


# ------------------------------------------------------------------ stylo
class Stylo:
    def __init__(s, img, k): s.d = ImageDraw.Draw(img); s.k = k
    def _w(s, w): return max(1, int(round(w * s.k)))
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
        for x, y in (pts[0], pts[-1]): s.cercle(x, y, w / 2, fill=col)
    def poly(s, pts, fill): s.d.polygon([(x * s.k, y * s.k) for x, y in pts], fill=fill)
    def texte(s, x, y, txt, taille, col, nom="bold", anchor="mm", contour=0, col_contour=NOIR):
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
    reste = sum(seg) * prog; out = [pts[0]]
    for i, l in enumerate(seg):
        if reste >= l: out.append(pts[i + 1]); reste -= l
        else:
            a = reste / l if l > 0 else 0
            out.append((lerp(pts[i][0], pts[i + 1][0], a), lerp(pts[i][1], pts[i + 1][1], a))); break
    p.ligne(out, col, w)

def pointilles(p, x0, y0, x1, y1, col, w, tiret=14, trou=10):
    l = math.dist((x0, y0), (x1, y1)); n = int(l // (tiret + trou)) + 1
    for i in range(n):
        a = i * (tiret + trou) / l; b = min(1, (i * (tiret + trou) + tiret) / l)
        if a >= 1: break
        p.ligne([(lerp(x0, x1, a), lerp(y0, y1, a)), (lerp(x0, x1, b), lerp(y0, y1, b))], col, w)

def bonhomme(p, x, y, t, col=BLANC, humeur=1.0, regard=0.0):
    if t <= 0.5: return
    p.rrect(x - 0.62 * t, y - 0.35 * t, x + 0.62 * t, y + 0.95 * t, 0.55 * t, fill=col)
    p.cercle(x, y - 0.85 * t, 0.42 * t, fill=col)
    ox = regard * 0.13 * t
    for dx in (-0.14, 0.14): p.cercle(x + dx * t + ox, y - 0.92 * t, 0.055 * t, fill=NOIR)
    pts = [(x + (-1 + i / 4) * 0.15 * t + ox * 0.8, y - 0.74 * t + humeur * 0.08 * t * (1 - (-1 + i / 4) ** 2))
           for i in range(9)]
    p.ligne(pts, NOIR, 0.05 * t)

def piece(p, x, y, r, k=1.0, sx=1.0, txt="$"):
    if k <= 0.01 or r <= 0.5: return
    sx = max(0.08, abs(sx))
    p.ellipse(x, y, r * 1.3 * sx, r * 1.3, fill=g(40, k))
    p.ellipse(x, y, r * sx, r, fill=g(255, k))
    p.ellipse(x, y, r * 0.8 * sx, r * 0.8, outline=NOIR, w=r * 0.07)
    if sx > 0.55: p.texte(x, y + r * 0.04, txt, r * (0.95 if len(txt) == 1 else 0.75), NOIR, "black")

def piece_plate(p, x, y, r):
    p.ellipse(x, y + 5, r, r * 0.32, fill=g(140))
    p.ellipse(x, y, r, r * 0.32, fill=BLANC, outline=NOIR, w=2)

def etoile(p, x, y, r, col, branches=4, creux=0.25, rot=0):
    pts = []
    for i in range(branches * 2):
        rr = r if i % 2 == 0 else r * creux; a = rot + i * math.pi / branches
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    p.poly(pts, col)


# ------------------------------------------------------------------ partie 1 : A ou B ?
def dessine_choix(p, T, t0, premiere):
    u = T - t0
    s = 1 + 0.08 * (1 - e_out(pr(u, 0, 0.35)))
    p.texte(360, 165, "WHICH ONE?", 78 * s, BLANC, "black", contour=4)
    for cote, (x0, x1) in (("A", (58, 334)), ("B", (386, 662))):
        cx, cy = (x0 + x1) / 2, 490
        if premiere:
            hl = math.sin(math.pi * pr(T, 4.35, 4.95)) if cote == "A" else math.sin(math.pi * pr(T, 4.95, 5.6))
            hl = max(hl, 0.25 * (1 + math.sin(T * 5)) / 2 * (1 if (cote == "B" and 1.8 < T < 4.3) else 0))
        else:
            hl = 0.5 + 0.5 * math.sin(u * 6 + (0 if cote == "A" else math.pi))
        sc = (1 + 0.05 * hl) * s
        hw, hh = (x1 - x0) / 2 * sc, 205 * sc
        p.rrect(cx - hw, cy - hh, cx + hw, cy + hh, 30 * sc, fill=g(14), outline=mul(JAUNE, 0.5 + 0.5 * hl) if hl > 0.3 else g(235),
                w=5 + 2 * hl)
        p.cercle(cx, cy - hh, 30 * sc, fill=BLANC)
        p.texte(cx, cy - hh + 1, cote, 36 * sc, NOIR, "black")
        if cote == "A":
            p.texte(cx, cy - 45 * sc, "$1M", 92 * sc, BLANC, "black")
            p.texte(cx, cy + 32 * sc, "RIGHT NOW", 26 * sc, g(190), "bold")
            for j, (dx, n) in enumerate(((-62, 5), (0, 8), (62, 6))):
                for i in range(n):
                    piece_plate(p, cx + dx * sc, cy + (150 - i * 13) * sc, 26 * sc)
        else:
            piece(p, cx, cy - 62 * sc, 56 * sc, txt="1¢")
            p.texte(cx, cy + 32 * sc, "×2 EVERY DAY", 26 * sc, BLANC, "bold")
            p.texte(cx, cy + 68 * sc, "FOR 30 DAYS", 22 * sc, g(170), "bold")
            pts = [(cx - 80 * sc + i * 160 / 20 * sc, cy + (170 - 70 * (2 ** (i / 4) - 1) / 31) * sc) for i in range(21)]
            p.ligne(pts, BLANC, 5 * sc)
            p.cercle(pts[-1][0], pts[-1][1], 8 * sc, fill=JAUNE)
    p.cercle(360, 490, 34 * s, fill=NOIR, outline=BLANC, w=4)
    p.texte(360, 491, "VS", 28 * s, BLANC, "black")
    k = pr(T, 4.35, 4.6) if premiere else 1
    if k > 0:
        p.texte(360, 765, "COMMENT  A  OR  B", 36, g(255, k), "black", contour=3)


# ------------------------------------------------------------------ partie 2 : la courbe
CX0, CX1, CY0, CY1 = 90, 630, 425, 780
VMAX = 5.6e6
def xd(d): return CX0 + (d - 1) / 29 * (CX1 - CX0)
def yv(v): return CY1 - v / VMAX * (CY1 - CY0)

def courbe_pts(jusqua, depuis=1.0):
    pts = []; d = depuis
    while d < jusqua:
        pts.append((xd(d), yv(valeur(d)))); d += 0.25 if d < 22 else 0.05
    pts.append((xd(jusqua), yv(valeur(jusqua))))
    return pts

def dessine_courbe(p, T):
    u = T - M["chart"]
    jour = interp(T, JOURS)
    jour_aff = int(math.floor(interp(T, JOUR_AFFICHE) + 1e-6))
    v = valeur(jour)
    lecon = pr(T, M["lecon"], M["lecon"] + 0.3)
    # titre : jour, puis "compound growth"
    if lecon < 1:
        k = 1 - lecon
        p.texte(340, 150, f"DAY {jour_aff}", 64, g(255, k), "black", anchor="rm")
        p.texte(352, 155, "/ 30", 40, g(120, k), "black", anchor="lm")
    if lecon > 0:
        p.texte(360, 150, "COMPOUND GROWTH", 56 * e_back(lecon), BLANC, "black")
    # compteur d'argent
    puls = 1.0
    frac = interp(T, JOUR_AFFICHE) % 1
    if T > M["day30"]:
        puls = 1 + 0.25 * (1 - e_out(pr(T, M["day30"], M["day30"] + 0.5)))
    elif T > 5.95:
        puls = 1 + 0.06 * (1 - e_out(cl(frac * 6)))
    taille = 104 if valeur(jour_aff) < 1e6 else 96
    kj = 1 - 0.2 * lecon
    if M["tension"] <= T < M["day30"]:      # suspense : montant cache
        tremble = 1 + 0.03 * math.sin(T * 40)
        p.texte(360, 272, "$?,???,???", 96 * tremble, mul(JAUNE, 0.85), "black", contour=4)
    else:
        v_aff = valeur(30) if T >= M["day30"] else valeur(jour_aff)
        p.texte(360, 272, argent(v_aff), taille * puls, mul(JAUNE, kj), "black", contour=4)
    # axes
    ka = pr(u, 0, 0.3)
    p.ligne([(CX0, CY1), (CX1 + 10, CY1)], g(130, ka), 3)
    for d in (1, 10, 20, 30):
        p.texte(xd(d), CY1 + 26, str(d), 22, g(140, ka), "bold")
    y1m = yv(1e6)
    pointilles(p, CX0, y1m, CX1 + 10, y1m, g(150, ka), 3)
    p.texte(CX0 + 4, y1m - 20, "A = $1M", 24, g(180, ka), "black", anchor="lm")
    # zone des 5 derniers jours
    k97 = pr(T, M["part97"], M["part97"] + 0.6)
    if k97 > 0:
        fin_zone = lerp(25, 30, e_inout(k97))
        zone = courbe_pts(fin_zone, 25) + [(xd(fin_zone), CY1), (xd(25), CY1)]
        p.poly(zone, (70, 58, 0))
        dim = 1 - 0.7 * pr(T, M["quit"] - 0.1, M["quit"] + 0.2)
        s = pop(T, M["part97"] + 0.3)
        p.texte(400, 512, "97%", 76 * s, mul(JAUNE, dim), "black", contour=4)
        p.texte(400, 568, "OF THE MONEY IN THE LAST 5 DAYS", 21 * s, g(255, dim), "black", contour=3)
    # courbe
    pts = courbe_pts(jour)
    if len(pts) >= 2:
        p.ligne(pts, BLANC, 6)
    tx, ty = xd(jour), yv(v)
    if lecon < 1:
        pointilles(p, tx, ty + 14, tx, CY1 - 4, g(90, 1 - lecon), 2, 8, 8)
    p.cercle(tx, ty, 12, fill=JAUNE)
    p.cercle(tx, ty, 5, fill=BLANC)
    # "B > A" au croisement
    kb = pop(T, M["crossing"], 0.4) * (1 - pr(T, M["lecon"], M["lecon"] + 0.3))
    if kb > 0.01:
        p.rrect(440 - 85 * kb, 625 - 34 * kb, 440 + 85 * kb, 625 + 34 * kb, 30 * kb, fill=g(14), outline=JAUNE, w=4)
        p.texte(440, 627, "B  >  A", 40 * kb, JAUNE, "black")
    # le bonhomme (celui qui a choisi B)
    sb = pop(T, 10.7, 0.4)
    if sb > 0.01 and T < M["part97"] + 0.4:
        kq = 1 - pr(T, M["part97"], M["part97"] + 0.4)
        content = T > M["crossing"]
        saut = abs(math.sin((T - M["crossing"]) * 9)) * 16 if content and T < M["lecon"] else 0
        bonhomme(p, 175, 585 - saut, 54 * sb * kq, humeur=1.0 if content else -1.0, regard=0.8)
        if not content and kq > 0.5:
            p.ellipse(205, 518 + 8 * math.sin(T * 3), 6, 9, fill=g(200))
    # ceux qui abandonnent au jour 20
    kq = pr(T, M["quit"], M["quit"] + 0.4)
    if kq > 0:
        x20 = xd(20)
        tracer(p, [(x20, CY1), (x20, 655)], kq, ROUGE, 4)
        s = pop(T, M["quit"] + 0.2)
        p.ligne([(x20 - 12, CY1 - 12), (x20 + 12, CY1 + 12)], ROUGE, 6)
        p.ligne([(x20 + 12, CY1 - 12), (x20 - 12, CY1 + 12)], ROUGE, 6)
        p.texte(x20, 632, "MOST PEOPLE QUIT HERE", 26 * s, ROUGE, "black", contour=3)
    # pluie de pieces au jour 30
    if M["day30"] < T < M["day30"] + 2.6:
        w = T - M["day30"]
        rng = np.random.default_rng(3)
        for i in range(26):
            x = rng.uniform(40, 680); v0 = rng.uniform(250, 520); dl = rng.uniform(0, 0.6); r = rng.uniform(14, 24)
            tt = w - dl
            if tt <= 0: continue
            y = -40 + v0 * tt + 420 * tt * tt
            if y < 1340:
                piece(p, x, y, r, 1 - pr(tt, 1.6, 2.0), sx=math.cos(tt * 7 + i))


# ------------------------------------------------------------------ assemblage d'une image
def scene(p, T):
    if T < M["chart"]:
        dessine_choix(p, T, 0.0, True)
    elif T < M["boucle"]:
        dessine_courbe(p, T)
    else:
        dessine_choix(p, T, M["boucle"], False)

def mots_timing():
    """Decoupe chaque phrase en mots, repartit le temps selon la longueur des mots, puis en groupes de 1-3 mots."""
    groupes = []
    for a, b, txt in PHRASES:
        mots = txt.split()
        poids = [len(m.strip(".,?!:")) + 2 for m in mots]
        tot = sum(poids); t = a; ws = []
        for m, w_ in zip(mots, poids):
            d = (b - a) * w_ / tot; ws.append((t, t + d, m)); t += d
        cur = []
        for w_ in ws:
            cur.append(w_)
            if len(cur) == 3 or w_[2][-1] in ".,?!:" or (len(cur) == 2 and len(cur[0][2]) + len(cur[1][2]) > 13):
                groupes.append(cur); cur = []
        if cur: groupes.append(cur)
    out = []
    for i, gr in enumerate(groupes):
        debut = gr[0][0]
        fin = gr[-1][1]
        if i + 1 < len(groupes) and groupes[i + 1][0][0] - fin < 0.35:
            fin = groupes[i + 1][0][0]
        else:
            fin += 0.25
        out.append((debut, fin, gr))
    return out
GROUPES = mots_timing()

def sous_titres(img, T):
    p = Stylo(img, ECHELLE)
    for debut, fin, gr in GROUPES:
        if not (debut <= T < fin): continue
        taille = 60
        txts = [w[2] for w in gr]
        esp = 16
        while sum(p.largeur(m, taille, "black") for m in txts) + esp * (len(txts) - 1) > 620 and taille > 30:
            taille -= 2
        apparition = e_back(pr(T, debut, debut + 0.12))
        tot = sum(p.largeur(m, taille, "black") for m in txts) + esp * (len(txts) - 1)
        x = 360 - tot / 2
        for (a, b, m), lw in zip(gr, [p.largeur(m, taille, "black") for m in txts]):
            actif = a <= T < b + 0.05
            sc = (1.12 - 0.12 * e_out(pr(T, a, a + 0.15))) if actif else 1.0
            col = JAUNE if actif else BLANC
            y = SOUS_TITRE_Y + (1 - apparition) * 14
            p.texte(x + lw / 2, y, m, taille * sc * (0.85 + 0.15 * apparition), col, "black", contour=5)
            x += lw + esp

def secousse(T):
    if M["day30"] < T < M["day30"] + 0.35:
        a = 1 - pr(T, M["day30"], M["day30"] + 0.35)
        return int(9 * a * math.sin(T * 90)), int(7 * a * math.cos(T * 77))
    return 0, 0

def zoom_punch(T):
    z = 1.0
    for m, force in ((M["chart"], 0.09), (M["boucle"], 0.09), (M["day30"], 0.06), (M["crossing"], 0.04)):
        if m <= T < m + 0.35:
            z = max(z, 1 + force * (1 - e_out(pr(T, m, m + 0.35))))
    return z

def flash(T):
    f = 0
    for m, force in ((M["chart"], 0.7), (M["day30"], 0.55), (M["boucle"], 0.5)):
        if m <= T < m + 0.25:
            f = max(f, force * (1 - pr(T, m, m + 0.25)))
    return f

def image(T):
    grand = Image.new("RGB", (LARGEUR * SS, HAUTEUR * SS), NOIR)
    scene(Stylo(grand, SS * ECHELLE), T)
    img = grand.resize((LARGEUR, HAUTEUR), Image.LANCZOS)
    a = np.asarray(img).astype(np.float32)
    petit = img.resize((LARGEUR // 4, HAUTEUR // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(5 * ECHELLE))
    lueur = np.asarray(petit.resize((LARGEUR, HAUTEUR), Image.BILINEAR)).astype(np.float32)
    a = np.minimum(a + lueur * 0.75, 255)
    f = flash(T)
    if f > 0: a = a + (255 - a) * f
    img = Image.fromarray(a.astype(np.uint8))
    z = zoom_punch(T)
    if z > 1.001:
        w2, h2 = LARGEUR / z, HAUTEUR / z
        img = img.resize((LARGEUR, HAUTEUR), Image.BICUBIC,
                         box=((LARGEUR - w2) / 2, (HAUTEUR - h2) / 2, (LARGEUR + w2) / 2, (HAUTEUR + h2) / 2))
    dx, dy = secousse(T)
    if dx or dy:
        img = Image.fromarray(np.roll(np.roll(np.asarray(img), dy, axis=0), dx, axis=1))
    sous_titres(img, T)
    return img

def rendre_morceau(args):
    n0, n1, idx = args
    chemin = f"pn_morceau_{idx:02d}.mp4"; tmp = chemin + ".tmp.mp4"
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{LARGEUR}x{HAUTEUR}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(QUALITE),
           "-pix_fmt", "yuv420p", tmp]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for n in range(n0, n1):
        proc.stdin.write(image(n / FPS).tobytes())
    proc.stdin.close(); proc.wait()
    os.replace(tmp, chemin)
    return chemin


# ------------------------------------------------------------------ son
def _env(n, tau): return np.exp(-np.arange(n) / SR / tau)

def bruitage(nom, freq=880):
    rng = np.random.default_rng(len(nom))
    if nom == "tick":
        n = int(0.09 * SR); tt = np.arange(n) / SR
        return 0.16 * np.sin(2 * np.pi * freq * tt) * _env(n, 0.03)
    if nom == "pop":
        n = int(0.12 * SR); tt = np.arange(n) / SR
        return 0.26 * np.sin(2 * np.pi * np.cumsum(400 + 900 * tt / 0.12) / SR) * _env(n, 0.05)
    if nom == "piece":
        n = int(0.5 * SR); tt = np.arange(n) / SR
        return (0.15 * np.sin(2 * np.pi * 1320 * tt) + 0.11 * np.sin(2 * np.pi * 1760 * tt)
                + 0.06 * np.sin(2 * np.pi * 2640 * tt)) * _env(n, 0.13)
    if nom == "boum":
        n = int(0.6 * SR); tt = np.arange(n) / SR
        return 0.7 * np.sin(2 * np.pi * np.cumsum(38 + 120 * np.exp(-tt * 9)) / SR) * _env(n, 0.2)
    if nom == "erreur":
        n = int(0.3 * SR); tt = np.arange(n) / SR
        f = 260 - 90 * tt / 0.3
        return 0.13 * (np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.4 * np.sin(2 * np.pi * np.cumsum(3 * f) / SR)) * _env(n, 0.12)
    if nom == "souffle":
        n = int(0.5 * SR); tt = np.arange(n) / SR
        b = np.convolve(rng.uniform(-1, 1, n), np.ones(25) / 25, mode="same")
        return 1.4 * b * np.sin(np.pi * tt / 0.5) ** 2
    if nom == "montee":
        n = int(1.25 * SR); tt = np.arange(n) / SR
        b = rng.uniform(-1, 1, n)
        b = b - np.convolve(b, np.ones(12) / 12, mode="same")
        ton = 0.12 * np.sin(2 * np.pi * np.cumsum(200 + 900 * (tt / 1.25) ** 2) / SR)
        return (0.35 * b + ton) * (tt / 1.25) ** 2
    return np.zeros(1)

def ajouter(piste, son, t):
    d = int(t * SR)
    if d >= len(piste) or d < 0: return
    f = min(len(son), len(piste) - d)
    piste[d:d + f] += son[:f]

def sons():
    L = [(0.0, "boum"), (0.0, "souffle"), (1.8, "pop"), (4.35, "pop"), (4.95, "pop"),
         (M["chart"] - 0.15, "souffle"), (M["chart"], "boum"), (10.7, "erreur"),
         (M["crossing"], "boum"), (M["crossing"], "piece"), (M["tension"] + 0.05, "montee"),
         (M["day30"], "boum"), (M["lecon"] - 0.15, "souffle"), (M["part97"], "pop"), (M["quit"], "erreur"),
         (M["boucle"] - 0.15, "souffle"), (M["boucle"], "boum")]
    rng = np.random.default_rng(5)
    L += [(M["day30"] + rng.uniform(0, 1.8), "piece") for _ in range(9)]
    return L

def ticks_jours():
    out = []; precedent = 1
    for n in range(int(M["boucle"] * 100)):
        T = n / 100
        j = int(math.floor(interp(T, JOUR_AFFICHE) + 1e-6))
        if j > precedent and T > 5.9:
            for jj in range(precedent + 1, j + 1):
                out.append((T, 500 + jj * 38))
        precedent = max(precedent, j)
    return out

def charger_voix():
    if not os.path.exists(VOIX_FICHIER): return None
    cmd = ["ffmpeg", "-v", "error", "-i", VOIX_FICHIER, "-af", f"atempo={VITESSE_VOIX}",
           "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, dtype=np.float32).copy()

def fabriquer_son(chemin="pn_son.wav"):
    total = M["fin"]; n = int(total * SR); tt = np.arange(n) / SR
    nappe = np.zeros(n)
    for f, a in [(55, 1.0), (110, 0.6), (165, 0.3), (220, 0.2)]:
        nappe += a * (np.sin(2 * np.pi * f * tt) + np.sin(2 * np.pi * f * 1.004 * tt))
    nappe *= 0.035 * (0.75 + 0.25 * np.sin(2 * np.pi * 0.25 * tt))
    rythme = np.zeros(n)
    kick = bruitage("boum")[: int(0.25 * SR)] * 0.4
    for b in np.arange(0, total, 0.5):
        ajouter(rythme, kick, b)
        ajouter(rythme, bruitage("souffle")[: int(0.05 * SR)] * 0.12, b + 0.25)
    # coupure du rythme pendant la tension avant le jour 30, puis il repart plus fort
    env = np.ones(n)
    i0, i1 = int(M["tension"] * SR), int(M["day30"] * SR)
    env[i0:i1] = 0.0
    env[i1:int(M["lecon"] * SR)] = 1.35
    musique = nappe + rythme * env
    for t, nom in sons():
        ajouter(musique, bruitage(nom), t)
    for t, f in ticks_jours():
        ajouter(musique, bruitage("tick", f), t)
    musique /= max(1e-6, np.abs(musique).max()) / 0.6
    fo = int(0.6 * SR); musique[-fo:] *= np.linspace(1, 0.3, fo)
    voix = charger_voix()
    if voix is not None:
        pv = np.zeros(n)
        voix = voix / max(1e-6, np.abs(voix).max()) * 0.92
        if VOIX:
            for moment, d0, d1 in VOIX:
                i0 = max(0, int((d0 / VITESSE_VOIX - 0.04) * SR)); i1 = int((d1 / VITESSE_VOIX + 0.12) * SR)
                m = voix[i0:i1].astype(np.float64).copy()
                fd = min(int(0.02 * SR), len(m) // 2)
                if fd > 0: m[:fd] *= np.linspace(0, 1, fd); m[-fd:] *= np.linspace(1, 0, fd)
                ajouter(pv, m, moment - 0.04)
        else:
            ajouter(pv, voix.astype(np.float64), 0.1)
        mix = musique * 0.4 + pv
    else:
        mix = musique
    pic = np.abs(mix).max()
    if pic > 0.98: mix *= 0.98 / pic
    with wave.open(chemin, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())


# ------------------------------------------------------------------ programme principal
if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if "--apercu" in sys.argv:
        os.makedirs("apercu_penny", exist_ok=True)
        for T in [0.0, 2.5, 4.6, 6.5, 9.5, 11.5, 14.5, 16.5, 18.7, 20.0, 22.5, 24.5, 26.2, 28.3]:
            image(T).save(f"apercu_penny/t{T:05.1f}.png")
        image(3.0).save("couverture_penny.png")
        print("Apercus enregistres."); sys.exit()
    nb = int(round(M["fin"] * FPS)); n_morceaux = 6
    bornes = [round(i * nb / n_morceaux) for i in range(n_morceaux + 1)]
    print("Fabrication de la video...")
    with ProcessPoolExecutor(max_workers=os.cpu_count() or 2) as ex:
        fichiers = list(ex.map(rendre_morceau, [(bornes[i], bornes[i + 1], i) for i in range(n_morceaux)]))
    with open("pn_liste.txt", "w") as f:
        for c in fichiers: f.write(f"file '{c}'\n")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", "pn_liste.txt",
                    "-c", "copy", "pn_sans_son.mp4"], check=True)
    print("Fabrication du son...")
    fabriquer_son("pn_son.wav")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", "pn_sans_son.mp4", "-i", "pn_son.wav", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", FICHIER_SORTIE], check=True)
    image(3.0).save("couverture_penny.png")
    for c in fichiers + ["pn_liste.txt", "pn_sans_son.mp4", "pn_son.wav"]:
        try: os.remove(c)
        except OSError: pass
    print("Termine :", FICHIER_SORTIE)
