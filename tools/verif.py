#!/usr/bin/env python3
"""
CEFI2 — vérification des calculs et génération des corrigés.

Ce script :
  1. re-calcule les exemples chiffrés des slides et signale les coquilles ;
  2. calcule les corrections des 13 exercices (parties 1, 2 et 3) ;
  3. vérifie les réponses numériques du quiz (js/quiz-data.js) ;
  4. écrit js/exos-data.js, utilisé par exercices.html.

Usage :  python3 tools/verif.py            (depuis la racine du repo)
Aucune dépendance externe (Python 3.8+).

Conventions d'arrondi (identiques à celles affichées sur le site) :
  - montants arrondis à l'euro près (arrondi commercial, 0,5 -> au-dessus) ;
  - amortissements non ronds : arrondis à l'euro, la dernière annuité absorbe l'écart ;
  - actualisation : coefficient exact (1+i)^-t, chaque flux actualisé arrondi
    à l'euro (c'est la méthode des slides : 500 000 / 1,08 = 462 963) ;
    le coefficient est affiché au millième, et la VAN obtenue avec des
    coefficients arrondis au millième (méthode "table") est donnée en note ;
  - délai de récupération : flux cumulés NON actualisés (méthode du cours),
    interpolation linéaire dans l'année ; 1 mois = 30 jours.
"""
import json
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NNBSP = " "  # espace fine insécable (séparateur de milliers)

problems = []   # incohérences détectées (doivent rester vides)
report = []     # lignes du rapport console


def log(s=""):
    report.append(s)


def check(label, got, expected, tol=0.5):
    ok = abs(got - expected) <= tol
    if not ok:
        problems.append(f"{label}: obtenu {got}, attendu {expected}")
    return ok


# ---------------------------------------------------------------- utilitaires
def rnd(x, d=0):
    """Arrondi commercial (0,5 -> s'éloigne de zéro)."""
    m = 10 ** d
    v = math.floor(abs(x) * m + 0.5 + 1e-9) / m
    v = v if x >= 0 else -v
    return int(v) if d == 0 else v


def fr(x, d=0, sign=False):
    """Format français : 1 234 567,8 ; signe moins typographique."""
    if isinstance(x, str):
        return x
    v = rnd(x, d)
    s = f"{abs(v):,.{d}f}".replace(",", NNBSP).replace(".", ",")
    if v < 0:
        return "−" + s
    return ("+" if sign and v > 0 else "") + s


def pct(x, d=1):
    return fr(x * 100, d) + NNBSP + "%"


def eur(x, d=0):
    return fr(x, d) + NNBSP + "€"


def keur(x, d=1):
    return fr(x, d) + NNBSP + "k€"


def amort_lineaire(base, n):
    """Annuités arrondies à l'euro, la dernière absorbe l'écart."""
    a = rnd(base / n)
    return [a] * (n - 1) + [base - a * (n - 1)]


def is_tax(rai, taux=0.25, economie=True):
    """IS : si economie=True, un résultat négatif génère une économie d'IS
    (entreprise existante bénéficiaire par ailleurs) ; sinon IS = 0."""
    if rai < 0 and not economie:
        return 0
    return rnd(rai * taux)


def actualise(flux, i):
    """flux[0] = année 0. Renvoie lignes, VAN (flux actualisés arrondis à l'€)
    et VAN avec coefficients arrondis au millième."""
    lignes = []
    for t, f in enumerate(flux):
        c = (1 + i) ** -t
        lignes.append(dict(t=t, f=f, c=c, fa=rnd(f * c)))
    van = sum(l["fa"] for l in lignes)
    van_mill = sum(rnd(l["f"] * round(l["c"], 3)) for l in lignes)
    return lignes, van, van_mill


def delai(flux):
    """Délai de récupération simple (flux cumulés non actualisés)."""
    cum = 0
    cums = []
    res = None
    for t, f in enumerate(flux):
        prev = cum
        cum += f
        cums.append(cum)
        if res is None and t > 0 and prev < 0 <= cum:
            res = (t - 1) + (-prev) / f
    return res, cums


def duree_txt(d):
    if d is None:
        return "non récupéré sur la période"
    an = int(d)
    mois_f = (d - an) * 12
    mois = int(mois_f)
    jours = rnd((mois_f - mois) * 30)
    if jours == 30:
        mois, jours = mois + 1, 0
    if mois == 12:
        an, mois = an + 1, 0
    parts = [f"{an} an{'s' if an > 1 else ''}"]
    if mois:
        parts.append(f"{mois} mois")
    if jours:
        parts.append(f"{jours} jour{'s' if jours > 1 else ''}")
    return f"{fr(d, 2)} ans ≈ " + " ".join(parts)


def tri(flux, lo=-0.99, hi=10.0):
    def van(r):
        return sum(f / (1 + r) ** t for t, f in enumerate(flux))
    if van(lo) * van(hi) > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        if van(lo) * van(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


# ---------------------------------------------------------------- HTML
def cell(v, d=0):
    if isinstance(v, (int, float)):
        return f'<td class="n{" neg" if rnd(v, d) < 0 else ""}">{fr(v, d)}</td>'
    return f"<td>{v}</td>"


def table(head, rows, d=0, cap=None, total_rows=()):
    """rows : liste de listes ; 1re colonne = libellé. total_rows : index
    des lignes à mettre en gras."""
    h = "".join(f"<th>{x}</th>" for x in head)
    body = []
    for k, r in enumerate(rows):
        cls = ' class="tot"' if k in total_rows else ""
        tds = f"<th scope=\"row\">{r[0]}</th>" + "".join(cell(v, d) for v in r[1:])
        body.append(f"<tr{cls}>{tds}</tr>")
    c = f"<caption>{cap}</caption>" if cap else ""
    return (f'<div class="tw"><table>{c}<thead><tr>{h}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


def annees(n, start=0, label="Année"):
    return [f"{label} {t}" if label else str(t) for t in range(start, n + 1)]


def tableau_van(flux, i, unite="€"):
    """Tableau d'actualisation + délai, renvoie (html, infos)."""
    lignes, van, van_mill = actualise(flux, i)
    d, cums = delai(flux)
    div, dec = (1000, 1) if unite == "k€" else (1, 0)
    head = [unite] + [f"A{l['t']}" for l in lignes]
    rows = [
        ["Flux net"] + [l["f"] / div for l in lignes],
        ["Flux cumulés"] + [c / div for c in cums],
        [f"Coef. (1+{fr(i*100,0)}%)<sup>−t</sup>"] + [fr(l["c"], 3) for l in lignes],
        ["Flux actualisé"] + [l["fa"] / div for l in lignes],
    ]
    i0 = -flux[0]
    ip = 1 + van / i0
    return table(head, rows, d=dec), dict(van=van, van_mill=van_mill, delai=d,
                                          cums=cums, ip=ip, i0=i0,
                                          somme_act=van + i0, tri=tri(flux))


def money(x, unite="€"):
    return keur(x / 1000) if unite == "k€" else eur(x)


def bloc_criteres(flux, i, unite="€", nom=""):
    html, r = tableau_van(flux, i, unite)
    k = f" {nom}" if nom else ""
    d_txt = duree_txt(r["delai"])
    s = html
    s += "<ul>"
    if r["delai"] is not None:
        t = int(r["delai"])
        reste = -r["cums"][t]
        s += (f"<li><b>Délai de récupération{k}</b> : le cumul devient positif pendant "
              f"l'année {t+1}. Il manque {money(reste, unite)} à la fin de l'année {t}, "
              f"récupérés en {money(reste, unite)} / {money(flux[t+1], unite)} = "
              f"{fr(reste / flux[t+1], 3)} an → <b>{d_txt}</b>.</li>")
    else:
        s += f"<li><b>Délai de récupération{k}</b> : <b>non récupéré</b> sur la période étudiée.</li>"
    s += (f"<li><b>VAN{k}</b> = Σ flux actualisés − I<sub>0</sub> = "
          f"{money(r['somme_act'], unite)} − {money(r['i0'], unite)} = "
          f"<b>{money(r['van'], unite)}</b>"
          f"<span class=\"note-inline\"> (avec coefficients au millième : {money(r['van_mill'], unite)})</span></li>")
    s += (f"<li><b>IP{k}</b> = Σ flux actualisés / I<sub>0</sub> = "
          f"{money(r['somme_act'], unite)} / {money(r['i0'], unite)} = <b>{fr(r['ip'], 2)}</b></li>")
    if r["tri"] is not None:
        s += (f"<li class=\"compl\"><span class=\"tag\">complément</span> TRI{k} ≈ "
              f"{pct(r['tri'])} (taux qui annule la VAN, trouvé par itérations).</li>")
    s += "</ul>"
    return s, r


EXOS = []


def exo(id, partie, num, titre, enonce, etapes, conclusion, notes=None, tags=None):
    EXOS.append(dict(id=id, partie=partie, num=num, titre=titre, enonce=enonce,
                     etapes=[dict(t=t, h=h) for t, h in etapes],
                     conclusion=conclusion, notes=notes or [], tags=tags or []))


# =================================================================
# 0. EXEMPLES DES SLIDES
# =================================================================
SLIDES = []   # (partie, slide, constat, gravité) -> affiché sur le site

log("=== Vérification des exemples des slides ===")
# P1 slide 30 & 31
check("P1 s30 TCO A", 900 + 250, 1150)
check("P1 s30 TCO B", 500 + 950, 1450)
check("P1 s31 RUN A", 120 + 180 + 80 + 100, 480)
check("P1 s31 RUN B", 450 + 420 + 180 + 180, 1230)
check("P1 s31 TCO A", 900 + 480, 1380)
check("P1 s31 TCO B", 600 + 1230, 1830)
log("P1 s30/s31 TCO : OK")
# P1 slide 37 direct costing
ca = dict(A=550000, B=190000, C=200000)
cv = dict(A=260000, B=120000, C=202000)
for p in "ABC":
    log(f"P1 s37 TMCV {p} = {pct((ca[p]-cv[p])/ca[p])}")
check("P1 s37 MCV totale", sum(ca.values()) - sum(cv.values()), 358000)
check("P1 s37 Résultat", 358000 - 345000, 13000)
log(f"P1 s37 TMCV total = {pct(358000/940000)} (slide : 38 %) OK")
# P2 slide 4/6
check("P2 s4 délai", 150000 / 50000, 3)
check("P2 s4 cumul N8", -150000 + 8 * 50000, 250000)
check("P2 s6 cumul B N8", -100000 + 40000 + 40000 + 20000 * 6, 100000)
# P2 slide 10 : taux non affiché -> on vérifie qu'il s'agit de 8 %
fa = [rnd(f / 1.08 ** t) for t, f in enumerate([0, 500000, 500000, 350000, 250000])]
fb = [rnd(f / 1.08 ** t) for t, f in enumerate([0, 150000, 300000, 500000, 650000])]
for got, exp in zip(fa[1:] + fb[1:], [462963, 428669, 277841, 183757, 138889, 257202, 396916, 477769]):
    check("P2 s10 flux actualisés", got, exp)
check("P2 s10 somme A", sum(fa), 1353231, 1)
check("P2 s10 somme B", sum(fb), 1270776, 1)
log(f"P2 s10 : flux actualisés retrouvés avec i = 8 % ; VAN A = {fr(sum(fa)-1e6)}, VAN B = {fr(sum(fb)-1e6)}")
SLIDES.append(("P2", "10–11", "Le taux d'actualisation n'est pas écrit sur la slide : les valeurs actualisées "
               "(462 963 = 500 000 / 1,08…) correspondent à <b>i = 8 %</b>.", "info"))
SLIDES.append(("P2", "11", "Coquille : la 2ᵉ ligne indique « IP A = 1 270 776 / 1 000 000 = 1,27 » : il s'agit de "
               "<b>IP B</b>. IP A = 1,35 et IP B = 1,27 sont justes.", "warn"))
log(f"P2 s13 1/1,15 = {1/1.15:.5f} -> slide '0,869' (troncature ; arrondi au millième = 0,870)")
SLIDES.append(("P2", "13", f"1 / 1,15 = {fr(1/1.15, 4)} : la slide écrit 0,869 (troncature) ; "
               "arrondi au millième, c'est <b>0,870</b>. Écart sans importance, mais en examen arrondis correctement.", "warn"))
# P3 slide 11 : seuil de rentabilité
tm = (28000 - 20000) / 28000
sr = 5000 / tm
ms = 28000 - sr
sr2 = 6400 / tm
res2 = 33600 * tm - 6400
ms2 = 33600 - sr2
log(f"P3 s11 TMCV exact = {pct(tm, 2)} ; SR = {fr(sr)} ; MS = {fr(ms)} ({pct(ms/28000)})")
log(f"P3 s11 après invest. : SR = {fr(sr2)} ; résultat = {fr(res2)} ; MS = {fr(ms2)} ({pct(ms2/33600)})")
check("P3 s11 slide SR (avec 28,5%)", 5000 / 0.285, 17543.86, 1)
check("P3 s11 résultat initial", 28000 - 20000 - 5000, 3000)
SLIDES.append(("P3", "11", "Le taux de marge sur CV vaut 8 000 / 28 000 = <b>28,57 %</b>, arrondi à 28,5 % sur la slide "
               "(il fallait 28,6 %). Conséquences : SR = 5 000 / 0,2857 = <b>17 500 €</b> (et non 17 543), "
               "marge de sécurité = 10 500 € soit <b>37,5 %</b> ; après investissement : SR = 6 400 / 0,2857 = "
               "<b>22 400 €</b> (et non 22 456), résultat = 33 600 × 0,2857 − 6 400 = <b>3 200 €</b> (et non 3 176), "
               "marge de sécurité 11 200 € = <b>33,3 %</b>. Les conclusions (résultat ↑, sécurité ↓) sont inchangées. "
               "Astuce : garde le taux en fraction (8/28) dans la calculatrice.", "warn"))
# P3 slides 19-21
for (g, c, a, rex, m, rot, re_) in [(1500, 1350, 500, 150, .10, 3, .30), (600, 480, 800, 120, .20, .75, .15),
                                     (600, 540, 800, 60, .10, .75, .075)]:
    check("P3 s19-21 REX", g - c, rex)
    check("P3 s19-21 marge", rex / g, m, 1e-9)
    check("P3 s19-21 rotation", g / a, rot, 1e-9)
    check("P3 s19-21 Re", m * rot, re_, 1e-9)
    check("P3 s19-21 Re direct", rex / a, re_, 1e-9)
log("P3 s19–21 rentabilité économique : OK")
SLIDES.append(("P1", "37", "Taux de marge sur CV arrondis : A = 52,7 % (affiché 53 %), B = 36,8 % (37 %), total = 38,1 % (38 %). "
               "Corrects à l'arrondi près.", "info"))


# =================================================================
# PARTIE 1 — LES COÛTS
# =================================================================
# ---------------- Exercice 1 — GamaIA
users = [5000, 10000, 18000, 30000, 45000]
A_build = 600 + 80 + 70
A_runf = 45 + 35 + 20 + 150
B_build = 80
B_runf = 25 * 12 + 30
var_u = 0.35 * 12 / 1000          # k€ par utilisateur et par an
B_var = [u * var_u for u in users]
ext_year = next(t for t, u in enumerate(users, 1) if u > 30000)
A_run = [A_runf + (15 if t >= ext_year else 0) for t in range(1, 6)]
A_extra = [250 if t == ext_year else 0 for t in range(1, 6)]
B_run = [B_runf + v for v in B_var]
TCO_A = A_build + sum(A_run) + sum(A_extra)
TCO_B = B_build + sum(B_run)
cumA, cumB, ca_, cb_ = [], [], A_build, B_build
for t in range(5):
    ca_ += A_run[t] + A_extra[t]
    cb_ += B_run[t]
    cumA.append(ca_)
    cumB.append(cb_)
check("P1E1 TCO A", TCO_A, 2265)
check("P1E1 TCO B", TCO_B, 2183.6, 0.01)
log(f"P1 Ex1 : TCO A = {fr(TCO_A,1)} k€ ; TCO B = {fr(TCO_B,1)} k€ (extension A en année {ext_year})")

exo("p1e1", 1, 1, "GamaIA — infrastructure interne ou cloud public ?",
    f"""<p>La start-up GamaIA (plateforme d'aide au diagnostic médical par IA) prévoit
    5 000, 10 000, 18 000, 30 000 puis 45 000 utilisateurs actifs (années 1 à 5).</p>
    <p><b>Solution A – infrastructure interne</b> (k€) : serveurs 600, réseau 80, installation 70,
    maintenance constructeur 45/an, électricité 35, licences système 20, 2 administrateurs 150.
    Au-delà de 30 000 utilisateurs : achat de nouveaux serveurs (250 k€) et maintenance +15 k€/an.</p>
    <p><b>Solution B – cloud public</b> : configuration initiale 80 k€, abonnement fixe 25 k€/mois,
    0,35 €/utilisateur actif/mois, support Premium 30 k€/an.</p>
    <p>1) Classer les coûts en Build / Run fixe / Run variable. 2) Coût annuel du Run.
    3) TCO sur 5 ans. 4) Conclusion.</p>""",
    [
        ("1. Classer Build / Run fixe / Run variable",
         "<p>Build = dépenses de mise en place (une seule fois) ; Run = coûts d'exploitation récurrents. "
         "Électricité et licences sont ici considérées comme annuelles (le cours classe les « licences annuelles » "
         "dans l'exploitation).</p>"
         + table(["Solution A (k€)", "Build", "Run fixe", "Run variable"], [
             ["Serveurs", 600, "", ""], ["Réseau", 80, "", ""], ["Installation", 70, "", ""],
             ["Maintenance constructeur", "", 45, ""], ["Électricité", "", 35, ""],
             ["Licences système", "", 20, ""], ["2 administrateurs", "", 150, ""],
             ["Total", A_build, A_runf, "–"]], total_rows=(7,))
         + table(["Solution B", "Build", "Run fixe", "Run variable"], [
             ["Configuration initiale", 80, "", ""], ["Abonnement 25 k€ × 12", "", 300, ""],
             ["0,35 €/util./mois", "", "", "0,35 × 12 = 4,20 €/util./an"],
             ["Support Premium", "", 30, ""], ["Total", B_build, B_runf, "4,20 € × utilisateurs"]],
             total_rows=(4,))),
        ("2. Coût annuel du Run",
         f"<p>A : {A_runf} k€/an, puis {A_runf+15} k€ en année {ext_year} (seule année où l'on dépasse "
         f"30 000 utilisateurs : 30 000 en année 4 n'est pas « au-delà »). Les serveurs supplémentaires "
         f"(250 k€) sont un investissement : on les compte en Build complémentaire de l'année {ext_year}.</p>"
         f"<p>B : {B_runf} k€ + 4,20 € × utilisateurs. Ex. année 1 : 5 000 × 4,20 = 21 000 € = 21 k€.</p>"
         + table(["k€"] + [f"A{t}" for t in range(1, 6)] + ["Total"], [
             ["Utilisateurs"] + users + [""],
             ["A – Run fixe"] + A_run + [sum(A_run)],
             ["A – Serveurs suppl."] + A_extra + [sum(A_extra)],
             ["B – Run fixe"] + [B_runf] * 5 + [B_runf * 5],
             ["B – Run variable"] + B_var + [sum(B_var)],
             ["B – Run total"] + B_run + [sum(B_run)]], d=1, total_rows=(5,))),
        ("3. TCO sur 5 ans",
         f"<p>TCO = Build + Σ Run (+ investissements complémentaires).</p>"
         f"<p>TCO A = {A_build} + {sum(A_run)} + 250 = <b>{keur(TCO_A)}</b><br>"
         f"TCO B = {B_build} + {fr(sum(B_run),1)} = <b>{keur(TCO_B)}</b></p>"
         + table(["Coût cumulé (k€)", "Build"] + [f"A{t}" for t in range(1, 6)], [
             ["Solution A", A_build] + cumA, ["Solution B", B_build] + cumB], d=1)),
    ],
    f"""<p>Sur 5 ans, le cloud (B) coûte {keur(TCO_B)} contre {keur(TCO_A)} pour l'infrastructure
    interne (A), soit {keur(TCO_A-TCO_B)} de moins ({pct((TCO_A-TCO_B)/TCO_A)}). B demande en plus
    beaucoup moins d'investissement au départ (80 k€ contre 750 k€), ce qui préserve la trésorerie d'une start-up.</p>
    <p>Mais l'écart se réduit : le Run de B grimpe avec le nombre d'utilisateurs ({keur(B_run[0])} en
    année 1, {keur(B_run[4])} en année 5) alors que celui de A reste presque stable ({A_run[4]} k€).
    Si la croissance continue au-delà de 5 ans, A deviendrait moins chère. Le choix dépend donc de
    l'horizon, de la croissance réelle et de la capacité à financer 750 k€ au départ : à 5 ans,
    <b>on recommande B</b>, en surveillant le coût par utilisateur.</p>""",
    notes=["Hypothèse : électricité et licences système = coûts annuels. Si on les comptait une seule fois "
           f"(en Build), TCO A = {keur(TCO_A - 4*55)} : la conclusion ne change pas."],
    tags=["Build/Run", "TCO"])

# ---------------- Exercice 2 — Alpha authentification forte
s1_build = 3 * 75 * 8 / 12 + 40 + 20 + 35
s1_run = 35 + 25
s2_build = 80 + 15
s2_run = 90 + 20
n_eq = (s1_build - s2_build) / (s2_run - s1_run)
check("P1E2 build1", s1_build, 245)
log(f"P1 Ex2 : S1 build {s1_build} run {s1_run} TCO5 {s1_build+5*s1_run} ; S2 build {s2_build} run {s2_run} TCO5 {s2_build+5*s2_run} ; égalité à {n_eq} ans")
exo("p1e2", 1, 2, "Alpha — développer ou acheter le composant d'authentification ?",
    """<p>Plateforme de paiement : intégrer une authentification forte.</p>
    <p><b>Solution 1 – développement interne</b> : 3 développeurs à 75 k€/an pendant 8 mois, tests 40 k€,
    documentation 20 k€, audit de sécurité 35 k€ ; maintenance corrective 35 k€/an, évolutions réglementaires 25 k€/an.</p>
    <p><b>Solution 2 – composant du marché</b> : intégration 80 k€, formation 15 k€, licence 90 k€/an,
    support 20 k€/an (évolutions réglementaires incluses).</p>
    <p>1) Build, Run annuel et TCO sur 5 ans. 2) Que recommander pour une exploitation de plus de 10 ans ?</p>""",
    [
        ("1. Build de chaque solution",
         "<p>Piège : les salaires sont annuels → proratiser sur 8 mois.</p>"
         f"<p>S1 : 3 × 75 × 8/12 = 150 ; + 40 + 20 + 35 = <b>{keur(s1_build, 0)}</b><br>"
         f"S2 : 80 + 15 (la formation fait partie de la mise en place) = <b>{keur(s2_build, 0)}</b></p>"),
        ("2. Run annuel",
         f"<p>S1 : 35 + 25 = <b>{s1_run} k€/an</b> ; S2 : 90 + 20 = <b>{s2_run} k€/an</b></p>"),
        ("3. TCO sur 5 ans (et 10 ans)",
         table(["k€", "Build", "Run/an", "TCO 5 ans", "TCO 10 ans"], [
             ["Solution 1 (interne)", s1_build, s1_run, s1_build + 5 * s1_run, s1_build + 10 * s1_run],
             ["Solution 2 (achat)", s2_build, s2_run, s2_build + 5 * s2_run, s2_build + 10 * s2_run]])
         + f"<p>Point d'équilibre : 245 + 60 n = 95 + 110 n → n = 150 / 50 = <b>{fr(n_eq,0)} ans</b>. "
           "Au-delà de 3 ans d'exploitation, l'interne coûte moins cher.</p>"),
    ],
    f"""<p>La solution 2 est moins chère au départ ({s2_build} k€ contre {fr(s1_build)} k€) mais son Run est presque
    deux fois plus élevé. Dès 3 ans, la solution 1 devient moins chère : TCO 5 ans = {fr(s1_build+5*s1_run)} k€
    contre {fr(s2_build+5*s2_run)} k€, et sur 10 ans {fr(s1_build+10*s1_run)} k€ contre {fr(s2_build+10*s2_run)} k€
    (−{fr(s2_build+10*s2_run-(s1_build+10*s1_run))} k€). Pour une exploitation de plus de 10 ans, <b>on recommande le
    développement interne</b> : « une décision qui augmente le coût initial peut réduire fortement le coût global ».
    Il faudra toutefois conserver les compétences en interne et assumer seul la responsabilité de la sécurité et de la
    conformité réglementaire.</p>""",
    tags=["Build/Run", "TCO"])

# ---------------- Exercice 3 — Lambdacampus
n1_build, n1_run = 420 + 70, 120 + 90 + 35
n2s_build, n2s_run = 260 + 90 + 40, 55 + 60 + 35
n2_build, n2_run = n1_build + n2s_build, n1_run + n2s_run
dispo_h = lambda p: (1 - p) * 365 * 24
log(f"P1 Ex3 : N1 {n1_build}/{n1_run}/TCO {n1_build+5*n1_run} ; N2 (cumulatif) {n2_build}/{n2_run}/TCO {n2_build+5*n2_run}")
exo("p1e3", 1, 3, "Lambdacampus — quel niveau de disponibilité ?",
    """<p>Plateforme d'examens en ligne du groupe Forming.</p>
    <p><b>Niveau 1</b> (disponibilité 99,5 %, sauvegarde quotidienne, support heures ouvrées) : infrastructure 420 k€,
    déploiement 70 k€, hébergement 120 k€/an, support 90 k€/an, maintenance 35 k€/an.</p>
    <p><b>Niveau 2</b> (99,99 %, infrastructure redondante, sauvegarde temps réel, support 24h/24) : data center 260 k€,
    réplication temps réel 90 k€, configuration 40 k€, supervision 55 k€/an, astreintes 60 k€/an,
    maintenance supplémentaire 35 k€/an.</p>
    <p>1) Build, Run annuel, TCO 5 ans. 2) Choix argumenté avec au moins 2 critères non financiers.</p>""",
    [
        ("Interpréter l'énoncé",
         "<p>Le niveau 2 parle de « maintenance <i>supplémentaire</i> » et d'infrastructure « redondante » : ses "
         "coûts s'<b>ajoutent</b> à ceux du niveau 1 (on duplique et on renforce). C'est l'interprétation retenue. "
         f"Sinon le niveau 2 (TCO {fr(n2s_build+5*n2s_run)} k€) coûterait moins cher que le niveau 1 tout en offrant plus, "
         "ce qui n'aurait pas de sens économique.</p>"),
        ("1. Build, Run, TCO",
         table(["k€", "Build", "Run/an", "TCO 5 ans"], [
             ["Niveau 1", n1_build, n1_run, n1_build + 5 * n1_run],
             ["Suppléments niveau 2", n2s_build, n2s_run, n2s_build + 5 * n2s_run],
             ["Niveau 2 (total)", n2_build, n2_run, n2_build + 5 * n2_run]], total_rows=(2,))
         + f"<p>Build N1 = 420 + 70 = {n1_build} ; Run N1 = 120 + 90 + 35 = {n1_run}.<br>"
           f"Suppléments N2 : Build 260 + 90 + 40 = {n2s_build} ; Run 55 + 60 + 35 = {n2s_run}.<br>"
           f"Surcoût du niveau 2 sur 5 ans : <b>{keur(n2s_build+5*n2s_run,0)}</b>, soit {keur((n2s_build+5*n2s_run)/5,0)} par an.</p>"),
        ("2. Critères non financiers",
         f"<ul><li><b>Disponibilité</b> <span class=\"tag\">complément de calcul</span> : 99,5 % = {fr(dispo_h(.995),1)} h "
         f"d'indisponibilité possible par an ; 99,99 % = {fr(dispo_h(.9999)*60,0)} minutes. Une panne pendant une épreuve "
         "= examen annulé ou à reprogrammer.</li>"
         "<li><b>Perte de données</b> : sauvegarde quotidienne → on peut perdre une journée de copies ; temps réel → quasi rien.</li>"
         "<li><b>Support 24h/24</b> : examens en soirée, étudiants à l'étranger / autres fuseaux horaires.</li>"
         "<li><b>Image et confiance</b> des écoles et des étudiants, égalité de traitement entre candidats, risque de recours.</li></ul>"),
    ],
    f"""<p>Le niveau 2 coûte {fr(n2_build+5*n2_run)} k€ sur 5 ans contre {fr(n1_build+5*n1_run)} k€ pour le niveau 1,
    soit un surcoût de {fr(n2s_build+5*n2s_run)} k€ (+{pct((n2s_build+5*n2s_run)/(n1_build+5*n1_run),0)}).
    Pour une plateforme d'<b>examens</b>, une interruption ou une perte de copies a des conséquences graves (épreuves annulées,
    recours, image des écoles). La valeur perçue par le client (fiabilité, continuité, support permanent) justifie ce surcoût :
    <b>on recommande le niveau 2</b>, à condition que les écoles acceptent de le payer (raisonnement coût-valeur).
    Le niveau 1 pourrait suffire pour des usages non critiques (entraînements, quiz).</p>""",
    notes=[f"Si l'on considère le niveau 2 comme une solution autonome (coûts non cumulés) : Build {n2s_build}, "
           f"Run {n2s_run}/an, TCO {fr(n2s_build+5*n2s_run)} k€."],
    tags=["Build/Run", "TCO", "coût-valeur"])

# ---------------- Exercice 4 — ESN : acheter ou louer les PC
def esn(eff):
    """eff : effectif par année 1..5. Renvoie détails A et B (en €)."""
    A = dict(build=0, invest=[0] * 5, maint=[0] * 5, renouv=[0] * 5)
    B = dict(build=0, config=[0] * 5, loc=[0] * 5)
    parc = []   # (année d'achat, nb)
    prev = 0
    for t in range(5):
        new = eff[t] - prev
        if new > 0:
            if t == 0:
                A["build"] += new * (2200 + 200)
                B["build"] += new * 150
            else:
                A["invest"][t] += new * (2200 + 200)
                B["config"][t] += new * 150
            parc.append((t, new))
        prev = eff[t]
        for (ta, nb) in parc:
            if t - ta == 4:               # renouvellement après 4 ans d'usage
                A["renouv"][t] += nb * 2200
        A["maint"][t] = eff[t] * 120
        B["loc"][t] = eff[t] * 75 * 12
    A["tco"] = A["build"] + sum(A["invest"]) + sum(A["maint"]) + sum(A["renouv"])
    B["tco"] = B["build"] + sum(B["config"]) + sum(B["loc"])
    return A, B

A1, B1 = esn([60] * 5)
A2, B2 = esn([60, 60, 90, 90, 90])
check("P1E4 A1", A1["tco"], 312000)
check("P1E4 B1", B1["tco"], 279000)
log(f"P1 Ex4 : stable A {A1['tco']} B {B1['tco']} ; 90 dév. A {A2['tco']} B {B2['tco']}")

def esn_table(A, B, eff):
    yrs = [f"A{t}" for t in range(1, 6)]
    return table(["€", "Build (A0)"] + yrs + ["Total"], [
        ["Effectif", ""] + eff + [""],
        ["A – achat initial (2 200 + 200)", A["build"]] + [""] * 5 + [A["build"]],
        ["A – postes supplémentaires", ""] + [x or "" for x in A["invest"]] + [sum(A["invest"])],
        ["A – maintenance 120 €/poste", ""] + A["maint"] + [sum(A["maint"])],
        ["A – renouvellement", ""] + [x or "" for x in A["renouv"]] + [sum(A["renouv"])],
        ["<b>TCO A</b>", "", "", "", "", "", "", A["tco"]],
        ["B – configuration 150 €/poste", B["build"]] + [x or "" for x in B["config"]] + [B["build"] + sum(B["config"])],
        ["B – location 75 € × 12", ""] + B["loc"] + [sum(B["loc"])],
        ["<b>TCO B</b>", "", "", "", "", "", "", B["tco"]]], total_rows=(5, 8))

exo("p1e4", 1, 4, "ESN — acheter ou louer 60 ordinateurs ?",
    """<p>Une ESN équipe 60 développeurs.</p>
    <p><b>A – achat</b> : 2 200 €/PC, installation et configuration 200 €/poste, maintenance 120 €/PC/an,
    renouvellement après 4 ans à 2 200 € (pas de revente).</p>
    <p><b>B – location</b> : configuration 150 €/poste, 75 €/poste/mois maintenance incluse, engagement 12 mois renouvelable.</p>
    <p>1) Build, Run, TCO sur 5 ans à effectif stable (60). 2) Quelle solution si l'effectif passe à 90 à partir de l'année 3 ?</p>""",
    [
        ("1. Effectif stable : Build",
         f"<p>A : 60 × (2 200 + 200) = <b>{eur(A1['build'])}</b> ; B : 60 × 150 = <b>{eur(B1['build'])}</b></p>"),
        ("2. Effectif stable : Run",
         f"<p>A : maintenance 60 × 120 = 7 200 €/an, soit 36 000 € sur 5 ans, <b>+ renouvellement</b> des 60 PC après "
         f"4 ans d'utilisation, donc en année 5 : 60 × 2 200 = 132 000 € (comme dans le cours, le remplacement en fin de vie "
         f"est un coût de Run). Run A = {eur(sum(A1['maint'])+sum(A1['renouv']))}.</p>"
         f"<p>B : 60 × 75 × 12 = 54 000 €/an → Run B = {eur(sum(B1['loc']))}.</p>"),
        ("3. Effectif stable : TCO",
         esn_table(A1, B1, [60] * 5)
         + f"<p>TCO A = {eur(A1['tco'])} ; TCO B = {eur(B1['tco'])} → B moins cher de {eur(A1['tco']-B1['tco'])}.</p>"),
        ("4. Scénario 90 développeurs dès l'année 3",
         "<p>30 postes de plus au début de l'année 3. A : 30 × 2 400 = 72 000 € d'achat (renouvellement de ces postes en "
         "année 7, hors période) + maintenance sur 3 ans. B : 30 × 150 = 4 500 € de configuration + location sur 3 ans.</p>"
         + esn_table(A2, B2, [60, 60, 90, 90, 90])),
    ],
    f"""<p>À effectif stable, la location coûte {eur(B1['tco'])} sur 5 ans contre {eur(A1['tco'])} pour l'achat
    (−{eur(A1['tco']-B1['tco'])}), car l'achat impose de renouveler tout le parc en année 5. Avec 90 développeurs dès
    l'année 3, la location reste moins chère : {eur(B2['tco'])} contre {eur(A2['tco'])} (−{eur(A2['tco']-B2['tco'])}).
    La location apporte en plus de la <b>flexibilité</b> (engagement de 12 mois : on ajuste le parc si l'effectif varie),
    aucune immobilisation de trésorerie et la maintenance incluse. <b>On recommande la location (B)</b> dans les deux scénarios.</p>""",
    notes=[f"Sans le renouvellement en année 5, TCO A = {eur(A1['tco']-A1['renouv'][4])} < TCO B : le résultat dépend "
           "entièrement de cette ligne. Limite : en fin d'étude, les PC renouvelés ont encore de la valeur d'usage, mais l'énoncé "
           "ne donne pas de valeur de revente, donc on n'en tient pas compte.",
           "Hypothèse : pas de frais d'installation sur les PC de renouvellement (l'énoncé ne donne que 2 200 €)."],
    tags=["Build/Run", "TCO"])


# =================================================================
# PARTIE 2 — RENTABILITÉ DE PROJET
# =================================================================
# ---------------- Exercice 1
f = [-120000, 30000, 40000, 45000, 35000, 30000]
h, r = bloc_criteres(f, 0.08)
check("P2E1 délai", r["delai"], 3 + 5000 / 35000, 1e-9)
log(f"P2 Ex1 : délai {r['delai']:.4f} ; VAN {r['van']} (mill. {r['van_mill']}) ; IP {r['ip']:.4f} ; TRI {r['tri']:.4%}")
exo("p2e1", 2, 1, "ESN — passage au cloud hybride",
    """<p>Investissement initial 120 000 €, taux d'actualisation 8 %, flux nets de trésorerie :
    30 000 / 40 000 / 45 000 / 35 000 / 30 000 € (années 1 à 5).</p>
    <p>1) Délai de récupération simple. 2) VAN. 3) Indice de profitabilité. 4) Conclure.</p>""",
    [("Tableau des flux, délai, VAN, IP", h)],
    f"""<p>L'investissement est récupéré en {duree_txt(r['delai'])}, avant la fin de la période d'étude (5 ans).
    La VAN à 8 % est positive ({eur(r['van'])}) : le projet couvre le coût des capitaux (8 %) et crée
    {eur(r['van'])} de richesse en valeur d'aujourd'hui. IP = {fr(r['ip'],2)} : chaque euro investi rapporte
    {fr(r['ip'],2)} € en valeur actuelle, soit {fr(r['ip']-1,2)} € de richesse supplémentaire. <b>Le projet est rentable,
    on peut l'accepter</b>. Marge de sécurité : une baisse de tous les flux d'environ {pct(r['van']/r['somme_act'],0)}
    suffirait à annuler la VAN.</p>""",
    tags=["délai", "VAN", "IP"])

# ---------------- Exercice 2
fp1 = [-2600000, 500000, 700000, 900000, 1100000, 900000 + 250000]
fp2 = [-2600000, 1200000, 1100000, 600000, 400000, 250000 + 100000]
h1, r1 = bloc_criteres(fp1, 0.10, nom="P1")
h2, r2 = bloc_criteres(fp2, 0.10, nom="P2")
log(f"P2 Ex2 : P1 délai {r1['delai']:.4f} VAN {r1['van']} IP {r1['ip']:.4f} TRI {r1['tri']:.4%} ; "
    f"P2 délai {r2['delai']:.4f} VAN {r2['van']} IP {r2['ip']:.4f} TRI {r2['tri']:.4%}")
best = "projet 1" if r1["van"] > r2["van"] else "projet 2"
exo("p2e2", 2, 2, "ESN — deux projets d'IA générative",
    """<p>Taux d'actualisation 10 %. Investissement de 2 600 000 € pour chacun.</p>
    <p><b>Projet 1</b> : 500 000 / 700 000 / 900 000 / 1 100 000 / 900 000 €, valeur résiduelle 250 000 € en année 5.<br>
    <b>Projet 2</b> : 1 200 000 / 1 100 000 / 600 000 / 400 000 / 250 000 €, valeur résiduelle 100 000 € en année 5.</p>
    <p>1) Délai de récupération. 2) VAN et IP de chaque projet. 3) Conclure.</p>""",
    [
        ("Intégrer la valeur résiduelle",
         "<p>La valeur résiduelle est un encaissement de fin de période : on l'ajoute au flux de l'année 5 "
         "(P1 : 900 000 + 250 000 = 1 150 000 ; P2 : 250 000 + 100 000 = 350 000). L'énoncé ne donne pas de taux d'IS : "
         "on la prend telle quelle.</p>"),
        ("Projet 1", h1),
        ("Projet 2", h2),
        ("Comparaison",
         table(["", "Délai", "VAN", "IP"], [
             ["Projet 1", fr(r1["delai"], 2) + " ans", r1["van"], fr(r1["ip"], 2)],
             ["Projet 2", fr(r2["delai"], 2) + " ans", r2["van"], fr(r2["ip"], 2)]])),
    ],
    f"""<p>Les deux projets ont une VAN positive : ils sont rentables à 10 %. Le projet 2 est récupéré beaucoup plus vite
    ({fr(r2['delai'],2)} ans contre {fr(r1['delai'],2)} ans) car ses flux sont concentrés sur les premières années : il est
    meilleur en <b>liquidité</b> et moins exposé au risque d'obsolescence (critère important pour l'IA générative).
    Le projet {'1' if best == 'projet 1' else '2'} a la VAN la plus élevée ({eur(max(r1['van'], r2['van']))} contre
    {eur(min(r1['van'], r2['van']))}) et le meilleur IP ({fr(max(r1['ip'], r2['ip']),2)}).
    {"Le projet 2 cumule donc les deux avantages : <b>on choisit le projet 2</b>." if best == "projet 2" else
     "Arbitrage liquidité / rentabilité : à investissement égal, le critère de VAN privilégie le projet 1 ; une entreprise qui veut récupérer vite sa mise dans un secteur qui évolue très vite pourrait préférer le projet 2."}</p>""",
    tags=["délai", "VAN", "IP", "valeur résiduelle"])

# ---------------- Exercice 3 — DataFlow
IS = 0.25
inv0 = 300000 + 180000 + 120000
form = 50000
am0 = amort_lineaire(inv0, 5)
am3 = [0, 0] + amort_lineaire(100000, 3)
pers = [2 * 70000] * 5
prest = [0, 30000, 50000, 60000, 60000]
infra = [rnd((90000 + 50000 + 60000) * 0.40)] * 5
newc = [-(30000 + 25000)] * 5
gain = [pers[t] + prest[t] + infra[t] + newc[t] for t in range(5)]
amt = [am0[t] + am3[t] for t in range(5)]
rai = [gain[t] - amt[t] for t in range(5)]
ist = [is_tax(x) for x in rai]
rn = [rai[t] - ist[t] for t in range(5)]
caf = [rn[t] + amt[t] for t in range(5)]
form_net = -form + is_tax(form)      # charge déductible en T0 -> économie d'IS
vr = 50000
vr_net = vr - is_tax(vr)             # totalement amorti : plus-value = prix de cession
inv = [0, 0, -100000, 0, 0]
flux3 = [-inv0 + form_net] + [caf[t] + inv[t] + (vr_net if t == 4 else 0) for t in range(5)]
h3, r3 = bloc_criteres(flux3, 0.08)
# variantes
v_form = [-inv0 - form] + flux3[1:]
v_vr = flux3[:5] + [flux3[5] - vr_net + vr]
_, van_vform, _ = actualise(v_form, .08)
_, van_vvr, _ = actualise(v_vr, .08)
log(f"P2 Ex3 : flux {flux3} ; délai {r3['delai']:.4f} VAN {r3['van']} IP {r3['ip']:.4f} | var. formation brute {van_vform} ; VR non imposée {van_vvr}")

Y5 = [f"A{t}" for t in range(1, 6)]
exo("p2e3", 2, 3, "DataFlow — moderniser la plateforme",
    """<p>Étude sur 5 ans, IS 25 %, actualisation 8 %.</p>
    <p><b>Investissements en T0</b> amortis linéairement sur 5 ans : serveurs et stockage 300 000 €, automatisation
    180 000 €, migration et intégration 120 000 € ; <b>formation 50 000 €</b> passée immédiatement en charges en T0.
    Revente des investissements initiaux (totalement amortis) : 50 000 € fin d'année 5.
    <b>Année 3</b> : extension de stockage de 100 000 €, amortie sur 3 ans dès l'année 3.</p>
    <p><b>Économies</b> : personnel 6 ETP → 4 ETP dès l'année 1 (70 000 €/ETP) ; prestataires −30 000 € (A2),
    −50 000 € (A3), −60 000 € (A4 et A5) ; infrastructure (hébergement 90 000 + énergie 50 000 + maintenance
    60 000 €/an) réduite de 40 % dès l'année 1.<br><b>Nouveaux coûts</b> dès l'année 1 : licence 30 000 €/an, support 25 000 €/an.</p>
    <p>1) Construire les flux. 2) Délai, VAN à 8 %, IP. 3) Analyse et conclusion.</p>""",
    [
        ("1. Économies nettes annuelles (avant amortissements)",
         table(["€"] + Y5, [
             ["Personnel : 2 ETP × 70 000"] + pers,
             ["Prestataires extérieurs"] + prest,
             ["Infrastructure : 200 000 × 40 %"] + infra,
             ["Licence + support"] + newc,
             ["Économies nettes"] + gain], total_rows=(4,))),
        ("2. Amortissements",
         f"<p>Investissements amortissables T0 : 300 000 + 180 000 + 120 000 = {eur(inv0)} → {eur(am0[0])}/an.<br>"
         "Extension A3 : 100 000 / 3 = 33 333 €/an en A3, A4, A5 (dernière annuité 33 334 € pour tomber juste).<br>"
         "<b>Piège :</b> la formation n'est pas amortie, c'est une charge de T0.</p>"
         + table(["€"] + Y5, [["Amort. investissements T0"] + am0, ["Amort. extension"] + am3,
                              ["Total amortissements"] + amt], total_rows=(2,))),
        ("3. Résultat et CAF",
         table(["€"] + Y5, [
             ["Économies nettes"] + gain, ["− Amortissements"] + [-x for x in amt],
             ["Résultat avant IS"] + rai, ["− IS 25 %"] + [-x for x in ist],
             ["Résultat net"] + rn, ["+ Amortissements"] + amt,
             ["CAF"] + caf], total_rows=(6,))
         + "<p>L'amortissement n'est pas décaissé : il ne sert qu'à calculer l'IS, puis on le rajoute (CAF = RN + amortissements).</p>"),
        ("4. Tableau des flux",
         f"<p><b>T0</b> : investissements −{eur(inv0)} ; formation : charge déductible de 50 000 € qui fait économiser "
         f"25 % d'IS à DataFlow (entreprise existante, bénéficiaire) → coût net −{eur(-form_net)}. Flux T0 = {eur(flux3[0])}.<br>"
         f"<b>Valeur résiduelle</b> : les biens sont totalement amortis, donc le prix de cession (50 000 €) est une plus-value "
         f"imposable : VR nette = 50 000 × (1 − 25 %) = {eur(vr_net)}.</p>"
         + table(["€", "A0"] + Y5, [
             ["Investissements", -inv0] + inv,
             ["Formation (nette d'IS)", form_net, "", "", "", "", ""],
             ["CAF", ""] + caf,
             ["Valeur résiduelle nette", "", "", "", "", "", vr_net],
             ["Flux net", flux3[0]] + flux3[1:]], total_rows=(4,))),
        ("5. Délai, VAN, IP", h3),
    ],
    f"""<p>Le projet de modernisation est récupéré en {duree_txt(r3['delai'])}. Sa VAN à 8 % est positive
    ({eur(r3['van'])}) et l'IP vaut {fr(r3['ip'],2)} : chaque euro investi génère {fr(r3['ip'],2)} € de valeur actuelle.
    <b>Le projet est rentable et doit être réalisé.</b> Il repose surtout sur la baisse des coûts de personnel
    (140 000 €/an) et d'infrastructure ; il faudra s'assurer que la réduction de 6 à 4 ETP est réaliste
    (reclassement des équipes) et que les économies sur les prestataires se concrétisent. L'investissement de l'année 3
    pèse sur la trésorerie de cette année-là.</p>""",
    notes=[f"Si l'on ne compte pas l'économie d'IS sur la formation (flux T0 = −650 000 €) : VAN = {eur(van_vform)}.",
           f"Si la valeur résiduelle est prise sans IS (50 000 €) : VAN = {eur(van_vvr)}. Conclusion inchangée dans les deux cas.",
           "L'extension de stockage est placée dans la colonne de l'année 3 (« à partir de l'année 3 »)."],
    tags=["compte de résultat", "CAF", "IS", "valeur résiduelle", "VAN"])

# ---------------- Exercice 4 — Alpha infrastructure GPU
req = [12, 20, 32, 48, 65]
api = [r * 1e6 * 0.02 + 60000 + 75000 for r in req]
base = 100000 + 70000 + 40000 + 150000 + 40000
def tranches(r, mode):
    x = max(0, r - 10) / 10
    return math.floor(x + 1e-9) if mode == "floor" else math.ceil(x - 1e-9)
def interne(mode):
    out = []
    for t, r in enumerate(req, 1):
        c = base + 15000 * tranches(r, mode) + (25000 + 15000 if t >= 4 else 0)
        out.append(c)
    return out
int_f = interne("floor")
int_c = interne("ceil")
eco = [api[t] - int_f[t] for t in range(5)]
amg = [180000] * 5
ame = [0, 0, 0, 100000, 100000]
def flux_gpu(eco, ext_col=4):
    amt_ = [amg[t] + ame[t] for t in range(5)]
    rai_ = [eco[t] - amt_[t] for t in range(5)]
    is_ = [is_tax(x) for x in rai_]
    rn_ = [rai_[t] - is_[t] for t in range(5)]
    caf_ = [rn_[t] + amt_[t] for t in range(5)]
    vr_init = 120000 - is_tax(120000 - 0)            # VNC 0 -> plus-value imposée
    vnc_ext = 300000 - 200000
    vr_ext = 100000 - is_tax(100000 - vnc_ext)        # VNC 100 000 -> pas de plus-value
    fl = [-900000]
    for t in range(5):
        x = caf_[t] + (vr_init + vr_ext if t == 4 else 0)
        if t + 1 == ext_col:
            x -= 300000
        fl.append(x)
    if ext_col == 3.0:   # placeholder non utilisé
        pass
    return dict(amt=amt_, rai=rai_, is_=is_, rn=rn_, caf=caf_, vr_init=vr_init, vr_ext=vr_ext, flux=fl)
G = flux_gpu(eco)
h4, r4 = bloc_criteres(G["flux"], 0.09)
Gc = flux_gpu([api[t] - int_c[t] for t in range(5)])
_, van_c, _ = actualise(Gc["flux"], .09)
G3 = flux_gpu(eco, ext_col=3)          # extension décaissée fin d'année 3
_, van_e3, _ = actualise(G3["flux"], .09)
vr_brut = G["flux"][:5] + [G["flux"][5] - G["vr_init"] - G["vr_ext"] + 220000]
_, van_vrb, _ = actualise(vr_brut, .09)
log(f"P2 Ex4 : API {api} ; interne {int_f} ; éco {eco} ; flux {G['flux']}")
log(f"         délai {r4['delai']} VAN {r4['van']} IP {r4['ip']:.4f} | tranche entamée {van_c} ; ext. fin A3 {van_e3} ; VR brute {van_vrb}")
exo("p2e4", 2, 4, "Alpha — API externe ou infrastructure GPU interne ?",
    """<p>Requêtes annuelles (millions) : 12 / 20 / 32 / 48 / 65. Étude sur 5 ans, IS 25 %, actualisation 9 %.</p>
    <p><b>API externe</b> : 0,02 € par requête, abonnement 60 k€/an, 1 ETP de supervision 75 k€/an.</p>
    <p><b>Interne</b> : investissement 900 k€ amorti sur 5 ans (serveurs GPU 600, stockage 100, réseau 80,
    installation 70, sécurisation 50). Coûts annuels : électricité 100, maintenance 70, licences 40,
    2 ETP 150, refroidissement 40 k€ ; électricité + refroidissement : +15 k€/an par tranche supplémentaire
    de 10 M de requêtes au-delà de 10 M. Début d'année 4 : extension GPU 300 k€ (amortie sur 3 ans),
    maintenance +25 k€/an, licences +15 k€/an. Valeur de revente fin d'année 5 : GPU initiaux 120 k€, extension 100 k€.</p>
    <p>1) Coût annuel de chaque solution et économie brute. 2) Flux du projet. 3) Délai, VAN à 9 %, IP, conclusion.</p>""",
    [
        ("Interpréter les « tranches de 10 M »",
         "<p>Retenu : on compte les <b>tranches complètes</b> de 10 M au-delà de 10 M, soit ⌊(requêtes − 10) / 10⌋ : "
         + ", ".join(f"A{t} : {tranches(r,'floor')}" for t, r in enumerate(req, 1))
         + ". C'est cohérent avec l'énoncé (en année 1, 12 M ≈ capacité de base). Autre lecture possible (tranche entamée, "
         + ", ".join(f"{tranches(r,'ceil')}" for r in req) + ") : voir la note en bas.</p>"),
        ("1. Coût annuel des deux solutions et économie brute",
         table(["€"] + Y5, [
             ["Requêtes (M)"] + req,
             ["API : requêtes × 0,02 €"] + [r * 1e6 * 0.02 for r in req],
             ["API : abonnement + 1 ETP"] + [135000] * 5,
             ["<b>Coût API</b>"] + api,
             ["Interne : coûts de base"] + [base] * 5,
             ["Interne : tranches × 15 000"] + [15000 * tranches(r, "floor") for r in req],
             ["Interne : maint. + licences suppl."] + [0, 0, 0, 40000, 40000],
             ["<b>Coût interne (hors amort.)</b>"] + int_f,
             ["<b>Économie brute</b>"] + eco], total_rows=(3, 7, 8))
         + "<p>Le coût interne est un coût décaissé : les amortissements interviennent seulement à l'étape suivante, pour l'IS. "
           "En année 1 l'économie est négative : l'interne coûte plus cher tant que le volume est faible.</p>"),
        ("2. Amortissements, IS et CAF",
         "<p>Amortissements : 900 000 / 5 = 180 000 €/an ; extension 300 000 / 3 = 100 000 €/an en A4 et A5.<br>"
         "Résultat négatif en A1 → <b>économie d'IS</b> (Alpha est une entreprise existante dont les autres activités sont bénéficiaires).</p>"
         + table(["€"] + Y5, [
             ["Économie brute"] + eco, ["− Amortissements"] + [-x for x in G["amt"]],
             ["Résultat avant IS"] + G["rai"], ["− IS 25 %"] + [-x for x in G["is_"]],
             ["Résultat net"] + G["rn"], ["+ Amortissements"] + G["amt"],
             ["CAF"] + G["caf"]], total_rows=(6,))),
        ("3. Valeur résiduelle et flux",
         f"<p>GPU initiaux : totalement amortis (VNC = 0) → plus-value 120 000 € imposée : 120 000 − 30 000 = {eur(G['vr_init'])}.<br>"
         f"Extension : VNC fin A5 = 300 000 − 2 × 100 000 = 100 000 € = prix de revente → pas de plus-value, pas d'IS : {eur(G['vr_ext'])}.<br>"
         f"Total VR nette = {eur(G['vr_init'] + G['vr_ext'])}. L'extension (« début d'année 4 ») est placée dans la colonne A4.</p>"
         + table(["€", "A0"] + Y5, [
             ["Investissements", -900000, "", "", "", -300000, ""],
             ["CAF", ""] + G["caf"],
             ["Valeur résiduelle nette", "", "", "", "", "", G["vr_init"] + G["vr_ext"]],
             ["Flux net", G["flux"][0]] + G["flux"][1:]], total_rows=(3,))),
        ("4. Délai, VAN, IP", h4),
    ],
    f"""<p>Avec le volume de requêtes prévu, l'infrastructure interne devient vite moins chère que l'API (économie brute
    de {eur(eco[4])} en année 5). Le projet est récupéré en {duree_txt(r4['delai'])}, la VAN à 9 % est
    {"positive" if r4['van'] > 0 else "négative"} ({eur(r4['van'])}) et l'IP vaut {fr(r4['ip'],2)}.
    {"<b>Le projet est rentable : on recommande l'infrastructure interne.</b>" if r4['van'] > 0 else "<b>Le projet n'est pas rentable.</b>"}
    Points de vigilance : la rentabilité dépend fortement de la croissance des requêtes (si le volume stagne,
    l'API redevient compétitive), l'investissement est lourd (900 k€ + 300 k€) et le matériel GPU s'use vite
    (obsolescence) ; il faut aussi les compétences internes pour l'exploiter.</p>""",
    notes=[f"Lecture « tranche entamée » (⌈(requêtes − 10)/10⌉) : VAN = {eur(van_c)} (écart {eur(van_c - r4['van'])}).",
           f"Si l'extension est décaissée fin d'année 3 (= début d'année 4 au sens strict) : VAN = {eur(van_e3)}.",
           f"Valeur résiduelle sans IS (220 000 €) : VAN = {eur(van_vrb)}. Les conclusions ne changent pas."],
    tags=["économie de coûts", "CAF", "IS", "valeur résiduelle", "VAN"])

# ---------------- Exercice 5
fa5 = [x * 1000 for x in [-600, 250, 220, 180, 140, 100]]
fb5 = [x * 1000 for x in [-900, 100, 150, 250, 450, 700]]
ha, ra = bloc_criteres(fa5, 0.10, "k€", "A")
hb, rb = bloc_criteres(fb5, 0.10, "k€", "B")
log(f"P2 Ex5 : A délai {ra['delai']:.4f} VAN {ra['van']} IP {ra['ip']:.4f} ; B délai {rb['delai']:.4f} VAN {rb['van']} IP {rb['ip']:.4f}")
win = "B" if rb["van"] > ra["van"] else "A"
exo("p2e5", 2, 5, "Alpha — architecture interne (A) ou cloud hybride (B) ?",
    """<p>Étude sur 5 ans, IS 25 %, actualisation 10 %. Flux prévisionnels (k€) :</p>
    <p><b>A</b> (investissement faible, économies fortes au début, durée de vie courte) : −600 ; 250 ; 220 ; 180 ; 140 ; 100.<br>
    <b>B</b> (investissement plus élevé, gains forts à partir de l'année 3, durée de vie longue) : −900 ; 100 ; 150 ; 250 ; 450 ; 700.</p>
    <p>Délai de récupération, VAN, IP pour chaque projet, puis choix.</p>""",
    [
        ("Remarque sur l'IS", "<p>Les flux sont donnés « prévisionnels », donc déjà nets d'impôt : le taux d'IS n'a pas à être réutilisé "
                              "(sinon on compterait l'impôt deux fois).</p>"),
        ("Projet A", ha), ("Projet B", hb),
        ("Comparaison", table(["", "Délai", "VAN (k€)", "IP"], [
            ["A", fr(ra["delai"], 2) + " ans", ra["van"] / 1000, fr(ra["ip"], 2)],
            ["B", fr(rb["delai"], 2) + " ans", rb["van"] / 1000, fr(rb["ip"], 2)]], d=1)),
    ],
    f"""<p>A est récupéré plus vite ({fr(ra['delai'],2)} ans contre {fr(rb['delai'],2)}) : meilleur en liquidité et moins risqué.
    Mais B a la VAN la plus élevée ({keur(rb['van']/1000)} contre {keur(ra['van']/1000)}) et un IP de {fr(rb['ip'],2)} contre
    {fr(ra['ip'],2)}{" : il crée plus de valeur, y compris par euro investi" if rb['ip'] > ra['ip'] else ""}. De plus, l'étude s'arrête à 5 ans alors que
    B a une durée de vie plus longue et des flux encore croissants (700 k€ en année 5) : sa VAN réelle est sans doute sous-estimée,
    alors que A arrive en fin de vie. <b>On choisit le projet {win}</b>, si l'entreprise peut financer 900 k€ et accepter
    un retour plus lent.</p>""",
    tags=["délai", "VAN", "IP", "liquidité vs rentabilité"])

# ---------------- Exercice 6 — GSe migration cloud
capt = [50000, 65000, 85000, 110000, 140000]
actuel = 180000 + 55000 + 65000 + 140000
cloud = [90000 + 35000 + (0.8 + 1.2) * n for n in capt]
admin_new = 70000
eco6 = [actuel - (cloud[t] + admin_new) for t in range(5)]
inv6 = 180000 + 120000 + 80000
form6 = 40000
am6 = amort_lineaire(inv6, 5)
am6e = [0, 0, 0, 50000, 50000]
def flux6(taxe=True, vr_taxe=True, form_taxe=True):
    t_ = 0.25 if taxe else 0
    amt_ = [am6[t] + am6e[t] for t in range(5)]
    rai_ = [eco6[t] - amt_[t] for t in range(5)]
    is_ = [rnd(x * t_) for x in rai_]
    rn_ = [rai_[t] - is_[t] for t in range(5)]
    caf_ = [rn_[t] + amt_[t] for t in range(5)]
    vr = 30000 - (rnd(30000 * t_) if vr_taxe else 0)
    f0 = -inv6 - form6 + (rnd(form6 * t_) if form_taxe else 0)
    fl = [f0] + [caf_[t] - (150000 if t == 3 else 0) + (vr if t == 4 else 0) for t in range(5)]
    return dict(amt=amt_, rai=rai_, is_=is_, rn=rn_, caf=caf_, vr=vr, flux=fl, f0=f0)
F6 = flux6()
h6, r6 = bloc_criteres(F6["flux"], 0.08)
F6n = flux6(taxe=False)
_, van6n, _ = actualise(F6n["flux"], .08)
log(f"P2 Ex6 : actuel {actuel} ; cloud {cloud} ; éco {eco6} ; flux {F6['flux']} ; VAN {r6['van']} IP {r6['ip']:.4f} | sans IS {van6n}")
exo("p2e6", 2, 6, "GSe — migrer la plateforme de capteurs vers le cloud ?",
    """<p><b>Situation actuelle</b> (40 000 capteurs) : serveurs et stockage 180 k€, électricité et climatisation 55 k€,
    maintenance 65 k€, administration 2 ETP 140 k€ par an. Capteurs prévus : 50 000 / 65 000 / 85 000 / 110 000 / 140 000.</p>
    <p><b>Migration</b> : investissements en année 0 amortis sur 5 ans (outils de migration 180 k€, adaptation 120 k€,
    automatisation 80 k€) + formation 40 k€ non amortissable. Cloud : base 90 k€/an, stockage 0,8 €/capteur/an,
    traitement 1,2 €/capteur/an, support 35 k€/an. Administration : 1 ETP au lieu de 2. Début d'année 4 :
    investissement de 150 k€ amorti sur 3 ans (on ne retient que les années 4 et 5). Revente d'équipements fin d'année 5 : 30 k€.</p>
    <p>Coût actuel, coût du cloud, économies, flux, délai, VAN à 8 %, IP, décision.</p>""",
    [
        ("Hypothèses",
         "<p>• Le coût actuel (440 k€) est supposé constant : l'énoncé ne dit pas comment il évoluerait avec le nombre de capteurs.<br>"
         "• L'énoncé de l'exercice 6 ne donne pas de taux d'IS : on garde <b>25 %</b> comme dans les exercices 3 à 5 (les "
         "amortissements n'ont d'effet sur les flux qu'à travers l'IS). Résultat sans IS en note.<br>"
         "• GSe est une entreprise existante : un résultat négatif du projet génère une économie d'IS.</p>"),
        ("1. Coût actuel et coût du cloud",
         f"<p>Coût actuel = 180 + 55 + 65 + 140 = <b>{keur(actuel/1000,0)}/an</b>.<br>"
         "Coût du cloud = 90 000 + 35 000 + (0,8 + 1,2) × capteurs = 125 000 + 2 € × capteurs.</p>"
         + table(["€"] + Y5, [
             ["Capteurs"] + capt, ["Base + support"] + [125000] * 5,
             ["2 € × capteurs"] + [2 * n for n in capt], ["<b>Coût du cloud</b>"] + cloud,
             ["Administration 1 ETP"] + [admin_new] * 5,
             ["Nouveau coût total"] + [cloud[t] + admin_new for t in range(5)],
             ["Coût actuel"] + [actuel] * 5,
             ["<b>Économies</b>"] + eco6], total_rows=(3, 7))),
        ("2. Résultat, CAF",
         table(["€"] + Y5, [
             ["Économies"] + eco6,
             ["− Amortissements (76 000 + extension)"] + [-x for x in F6["amt"]],
             ["Résultat avant IS"] + F6["rai"], ["− IS 25 %"] + [-x for x in F6["is_"]],
             ["Résultat net"] + F6["rn"], ["+ Amortissements"] + F6["amt"], ["CAF"] + F6["caf"]], total_rows=(6,))),
        ("3. Tableau des flux",
         f"<p>A0 : −380 000 − 40 000 de formation (charge déductible → coût net 30 000) = {eur(F6['f0'])}.<br>"
         f"Revente fin A5 : 30 000 € supposés totalement amortis → nette d'IS {eur(F6['vr'])}.</p>"
         + table(["€", "A0"] + Y5, [
             ["Investissements + formation nette", F6["f0"], "", "", "", -150000, ""],
             ["CAF", ""] + F6["caf"], ["Valeur résiduelle nette", "", "", "", "", "", F6["vr"]],
             ["Flux net"] + F6["flux"]], total_rows=(3,))),
        ("4. Délai, VAN, IP", h6),
    ],
    f"""<p>Les économies diminuent chaque année ({eur(eco6[0])} en année 1, {eur(eco6[4])} en année 5) car le coût du cloud est
    variable et augmente avec le nombre de capteurs, alors que le coût actuel est supposé fixe. Le projet
    {"n'est pas récupéré sur 5 ans" if r6['delai'] is None else "est récupéré en " + duree_txt(r6['delai'])},
    la VAN à 8 % est {"négative" if r6['van'] < 0 else "positive"} ({eur(r6['van'])}) et l'IP vaut {fr(r6['ip'],2)}.
    {"<b>En l'état, le projet ne doit pas être réalisé.</b>" if r6['van'] < 0 else "<b>Le projet peut être réalisé.</b>"}
    Nuance importante : l'hypothèse d'un coût actuel constant est favorable à la situation actuelle ; avec 140 000 capteurs,
    l'infrastructure interne devrait elle aussi être renforcée. Il faut donc chiffrer ce scénario, ou renégocier le prix du cloud
    par capteur, avant de décider.</p>""",
    notes=[f"Sans IS (flux = économies − investissements) : VAN = {eur(van6n)}.",
           "Variante : sans économie d'IS sur la formation et sur la revente, la VAN baisse encore légèrement."],
    tags=["Build/Run", "coûts variables", "VAN"])


# =================================================================
# PARTIE 3 — BUSINESS PLAN
# =================================================================
# ---------------- Exercice 1 — start-up contrôle qualité
inv31 = 200000 + 130000 + 140000 + 30000
am31 = inv31 // 5
cf31 = 340000 + 60000 + 36000 + 24000
pv, cvu = 15000, 3000
clients = [30, 60, 100]
tmcv = (pv - cvu) / pv
sr_val = (cf31 + am31) / tmcv
sr_cli = (cf31 + am31) / (pv - cvu)
sr_val_tres = cf31 / tmcv
ca31 = [n * pv for n in clients]
cv31 = [n * cvu for n in clients]
rex31 = [ca31[t] - cv31[t] - cf31 - am31 for t in range(3)]
is31 = [is_tax(x, economie=False) for x in rex31]
rn31 = [rex31[t] - is31[t] for t in range(3)]
caf31 = [rn31[t] + am31 for t in range(3)]
apport = 4 * 40000
sub = 50000
bfr31 = [40000, 0, 25000]
res31 = [apport + sub + caf31[0], caf31[1], caf31[2]]
bes31 = [inv31 + bfr31[0], bfr31[1], bfr31[2]]
net31 = [res31[t] - bes31[t] for t in range(3)]
cum31 = [sum(net31[:t + 1]) for t in range(3)]
# variante report déficitaire
cum_def, is_rep = 0, []
for x in rex31:
    base_ = x + cum_def
    if base_ < 0:
        cum_def, is_rep_ = base_, 0
    else:
        cum_def, is_rep_ = 0, rnd(base_ * .25)
    is_rep.append(is_rep_)
log(f"P3 Ex1 : SR {sr_val} € = {sr_cli:.2f} clients ; REX {rex31} ; CAF {caf31} ; cumuls {cum31} ; IS avec report {is_rep}")
check("P3E1 SR", sr_val, 700000)

exo("p3e1", 3, 1, "Start-up — contrôle qualité par caméras et IA",
    """<p>Quatre ingénieurs créent une plateforme SaaS de contrôle qualité automatique (caméras intelligentes + IA).</p>
    <p><b>Investissements</b> amortis sur 5 ans : développement logiciel 200 k€, IA 130 k€, cloud initial 140 k€, caméras de
    démonstration 30 k€. <b>Charges fixes</b> : salaires 340 k€, marketing 60 k€, loyer 36 k€, autres 24 k€.
    <b>Charges variables</b> : cloud et support 3 000 €/client. <b>Prix</b> : 15 000 €/an/client. Clients : 30 / 60 / 100.
    Fournisseurs à 30 jours, clients à 60 jours ; BFR de démarrage 40 000 €, +25 000 € en année 3.
    Apports : 4 × 40 000 € ; subvention possible 50 000 €.</p>
    <p>1) Business Model Canvas. 2) a. Seuil de rentabilité ; b. résultat prévisionnel ; c. plan de financement sur 3 ans, commentaire.</p>""",
    [
        ("1. Business Model Canvas",
         '<div class="bmc">'
         "<div><b>Proposition de valeur</b> : contrôle automatique et continu de 100 % des pièces ; moins de défauts, "
         "productivité accrue, coût du contrôle qualité réduit (on résout un problème : contrôle manuel coûteux et imparfait).</div>"
         "<div><b>Segments de clientèle</b> : industriels avec chaînes de production (automobile, aéronautique, électronique, "
         "agroalimentaire…), PME et grands groupes.</div>"
         "<div><b>Relations clients</b> : abonnement annuel, accompagnement au déploiement, support technique, suivi de la performance.</div>"
         "<div><b>Canaux</b> : vente directe B2B, salons industriels, démonstrations sur site (caméras de démo), partenaires intégrateurs.</div>"
         "<div><b>Activités clés</b> : R&amp;D IA (vision), développement et maintenance de la plateforme, déploiement chez les clients, cybersécurité.</div>"
         "<div><b>Ressources clés</b> : compétences des 4 fondateurs (IA, cyber, cloud), algorithmes et données d'entraînement, plateforme logicielle.</div>"
         "<div><b>Partenaires clés</b> : fournisseur cloud, fabricants de caméras, intégrateurs de lignes de production, financeurs (banque, subvention).</div>"
         "<div><b>Sources de revenus</b> : abonnement SaaS de 15 000 €/an par client.</div>"
         "<div><b>Structure de coûts</b> : investissements (développement, IA, cloud initial, caméras), charges fixes (salaires, marketing, loyer), "
         "charges variables (cloud et support par client).</div></div>"),
        ("2a. Seuil de rentabilité",
         f"<p>MCV unitaire = 15 000 − 3 000 = 12 000 € ; TMCV = 12 000 / 15 000 = <b>{pct(tmcv,0)}</b>.<br>"
         f"Charges fixes = 460 000 + amortissements {eur(am31)} (500 000 / 5) = {eur(cf31+am31)}. "
         "<b>Piège :</b> les amortissements sont des charges fixes (cours, partie 1).<br>"
         f"SR = CF / TMCV = 560 000 / 0,80 = <b>{eur(sr_val)}</b> de CA, soit 700 000 / 15 000 = {fr(sr_cli,2)} → "
         f"<b>{math.ceil(sr_cli)} clients</b>.</p>"
         f"<p>Année 1 (30 clients) : sous le seuil ; année 2 (60 clients) : au-dessus ; marge de sécurité en année 3 = "
         f"(1 500 000 − 700 000) / 1 500 000 = {pct((ca31[2]-sr_val)/ca31[2])}.</p>"),
        ("2b. Résultat prévisionnel",
         "<p>Hypothèses : pas d'emprunt donc pas de frais financiers ; l'énoncé ne donne pas de taux d'IS → <b>25 %</b> comme en partie 2 ; "
         "start-up sans autre activité : <b>pas d'IS si le résultat est négatif</b> (et pas d'économie d'IS).</p>"
         + table(["€", "Année 1", "Année 2", "Année 3"], [
             ["Nombre de clients"] + clients, ["CA"] + ca31, ["− CV"] + [-x for x in cv31],
             ["− CF"] + [-cf31] * 3, ["− Amortissements"] + [-am31] * 3, ["REX"] + rex31,
             ["− Frais financiers", 0, 0, 0], ["Résultat avant IS"] + rex31, ["− IS 25 %"] + [-x for x in is31],
             ["Résultat net"] + rn31, ["CAF = RN + amortissements"] + caf31], total_rows=(5, 9, 10))),
        ("2c. Plan de financement",
         "<p>L'investissement et le BFR de démarrage sont placés en année 1 (début de projet). Le BFR est un <b>besoin</b> ; "
         "seule sa <b>variation</b> compte chaque année (40 000 puis 0 puis +25 000).</p>"
         + table(["€", "Année 1", "Année 2", "Année 3"], [
             ["Apports des associés", apport, "", ""], ["Subvention", sub, "", ""], ["Emprunts", "", "", ""],
             ["CAF"] + caf31, ["<b>Total ressources</b>"] + res31,
             ["Investissements", inv31, "", ""], ["Variation du BFR"] + bfr31, ["<b>Total besoins</b>"] + bes31,
             ["Flux net de trésorerie"] + net31, ["<b>Flux nets cumulés</b>"] + cum31], total_rows=(4, 7, 9))),
    ],
    f"""<p>Le projet devient rentable dès l'année 2 (seuil de {math.ceil(sr_cli)} clients, 60 prévus) et dégage un résultat net de
    {eur(rn31[2])} en année 3. En revanche, le plan de financement montre que les ressources prévues (160 000 € d'apports et
    50 000 € de subvention) sont très insuffisantes : la trésorerie cumulée est négative de {eur(-cum31[0])} en année 1 et
    encore de {eur(-cum31[1])} en année 2. Les fondateurs doivent trouver environ <b>{eur(-min(cum31))}</b> (plus une marge de
    sécurité) : emprunt bancaire (qui ajoutera des frais financiers) ou entrée d'investisseurs. Le projet est viable
    économiquement mais <b>pas finançable en l'état</b> ; il faut aussi sécuriser les 30 premiers clients, car l'année 1 est
    déficitaire.</p>""",
    notes=[f"Sans les amortissements dans les charges fixes : SR = 460 000 / 0,8 = {eur(sr_val_tres)} ({math.ceil(cf31/12000)} clients) — "
           "c'est le niveau qui couvre les seules charges décaissées.",
           f"<span class=\"tag\">complément</span> Avec report des déficits (la perte de l'année 1 s'impute sur les bénéfices suivants), "
           f"l'IS serait {', '.join(eur(x) for x in is_rep)}."],
    tags=["BMC", "seuil de rentabilité", "compte de résultat", "plan de financement"])

# ---------------- Exercice 2 — Alfa maintenance prédictive
build32 = 110000 + 30000 + 15000 + 10000 + 15000
am32 = amort_lineaire(build32, 3)
cf32 = 45000 + 25000 + 10000 + 10000
cl = [90, 160, 240]
new = [cl[0], cl[1] - cl[0], cl[2] - cl[1]]
abo = [n * 1800 for n in cl]
mes = [n * 400 for n in new]
ca32 = [abo[t] + mes[t] for t in range(3)]
cloud32 = [n * 220 for n in cl]
com32 = [rnd(a * .08) for a in abo]
pay32 = [rnd(c * .02) for c in ca32]
cv32 = [cloud32[t] + com32[t] + pay32[t] for t in range(3)]
run32 = [cf32 + cv32[t] for t in range(3)]
tco32 = build32 + sum(run32)
rex32 = [ca32[t] - cv32[t] - cf32 - am32[t] for t in range(3)]
is32 = [is_tax(x, economie=False) for x in rex32]
rn32 = [rex32[t] - is32[t] for t in range(3)]
caf32 = [rn32[t] + am32[t] for t in range(3)]
mcv_u = 1800 - 220 - 0.08 * 1800 - 0.02 * 1800
tm32 = mcv_u / 1800
cft32 = cf32 + am32[0]
sr32_cli = cft32 / mcv_u
sr32_val = cft32 / tm32
tm_y = [(ca32[t] - cv32[t]) / ca32[t] for t in range(3)]
mes_net = 400 * (1 - 0.02)
flux32 = [-build32] + caf32
h32, r32 = bloc_criteres(flux32, 0.10)
emp32 = 50000
res32 = [70000 + 30000 + emp32, caf32[0], caf32[1], caf32[2]]
bes32 = [build32, 0, 0, 0]
net32 = [res32[t] - bes32[t] for t in range(4)]
cum32 = [sum(net32[:t + 1]) for t in range(4)]
check("P3E2 MCV unitaire", mcv_u, 1400)
log(f"P3 Ex2 : CA {ca32} CV {cv32} TCO {tco32} REX {rex32} CAF {caf32} ; SR {sr32_cli:.3f} clients / {sr32_val:.2f} € ; "
    f"délai {r32['delai']:.4f} VAN {r32['van']} IP {r32['ip']:.4f} ; cumuls PF {cum32}")

exo("p3e2", 3, 2, "Alfa — service de maintenance prédictive par abonnement",
    """<p><b>Année 0</b> (amortissable sur 3 ans) : développement interne 110 000 €, prestations cybersécurité/audit 30 000 €,
    cloud de développement 15 000 €, matériel de test 10 000 €, conception et gestion de projet 15 000 €.</p>
    <p><b>Coûts annuels fixes</b> : support et administration 45 000 €, maintenance 25 000 €, outils et licences 10 000 €,
    supervision/sécurité/sauvegardes 10 000 €. <b>Par client actif</b> : cloud 220 €/an, commission 8 % du CA d'abonnement,
    frais de paiement 2 % du CA total facturé.</p>
    <p><b>Revenus</b> : abonnement 1 800 €/client/an + 400 € de mise en service par nouveau client. Clients : 90 / 160 / 240.</p>
    <p>1) Build, Run, TCO sur 3 ans. 2) Compte de résultat prévisionnel et flux. 3) Seuil de rentabilité en valeur et en clients.
    4) « Au-delà du seuil, chaque nouveau client rapporte 1 800 € » ? 5) Délai, VAN à 10 %, IP. 6) Commenter deux affirmations.
    7) Plan de financement (apports 70 000 €, subvention 30 000 €, emprunt 50 000 €). 8) Rentabilité / financement / trésorerie.</p>""",
    [
        ("1. Build, Run, TCO",
         f"<p>Build = 110 + 30 + 15 + 10 + 15 = <b>{eur(build32)}</b>. Run fixe = 45 + 25 + 10 + 10 = {eur(cf32)}/an. "
         "Run variable : cloud 220 €/client + commissions + frais de paiement. Nouveaux clients (sans résiliation) : 90, 70, 80.</p>"
         + table(["€", "Année 1", "Année 2", "Année 3", "Total"], [
             ["Clients actifs"] + cl + [""], ["Nouveaux clients"] + new + [""],
             ["Abonnements (1 800 €)"] + abo + [sum(abo)], ["Mises en service (400 €)"] + mes + [sum(mes)],
             ["<b>CA total</b>"] + ca32 + [sum(ca32)],
             ["Run fixe"] + [cf32] * 3 + [cf32 * 3], ["Cloud 220 €/client"] + cloud32 + [sum(cloud32)],
             ["Commission 8 % × abonnements"] + com32 + [sum(com32)], ["Frais de paiement 2 % × CA total"] + pay32 + [sum(pay32)],
             ["<b>Run total</b>"] + run32 + [sum(run32)]], total_rows=(4, 9))
         + f"<p>TCO 3 ans = Build + Σ Run = {eur(build32)} + {eur(sum(run32))} = <b>{eur(tco32)}</b>.</p>"),
        ("2. Compte de résultat et flux de trésorerie",
         "<p>Hypothèses : IS 25 % (non donné), pas d'IS sur une perte ; pas de frais financiers (l'emprunt n'apparaît qu'au point 7, sans taux).</p>"
         + table(["€", "Année 1", "Année 2", "Année 3"], [
             ["CA"] + ca32, ["− CV"] + [-x for x in cv32], ["− CF"] + [-cf32] * 3,
             ["− Amortissements (180 000 / 3)"] + [-x for x in am32], ["REX = Résultat avant IS"] + rex32,
             ["− IS 25 %"] + [-x for x in is32], ["Résultat net"] + rn32,
             ["<b>CAF = flux de trésorerie</b>"] + caf32], total_rows=(4, 7))),
        ("3. Seuil de rentabilité",
         f"<p>Par client récurrent : MCV = 1 800 − 220 − 8 % × 1 800 (144) − 2 % × 1 800 (36) = <b>{eur(mcv_u)}</b> ; "
         f"TMCV = 1 400 / 1 800 = {pct(tm32,2)}.<br>Charges fixes (amortissements compris) = 90 000 + 60 000 = {eur(cft32)}.<br>"
         f"SR en clients = 150 000 / 1 400 = {fr(sr32_cli,2)} → <b>{math.ceil(sr32_cli)} clients</b> ; "
         f"SR en valeur = 150 000 / {fr(tm32,4)} = <b>{eur(sr32_val)}</b> d'abonnements.</p>"
         f"<p>Comparaison : années 2 et 3 (160 et 240 clients) au-dessus du seuil. Année 1 : 90 clients &lt; {math.ceil(sr32_cli)}, et pourtant "
         f"le REX est positif ({eur(rex32[0])}) grâce aux frais de mise en service (90 × 392 € nets = {eur(90*mes_net)}), "
         "recette qui ne se répète pas. Sans eux : 90 × 1 400 − 150 000 = "
         f"{eur(90*1400-150000)}.</p>"
         + table(["Seuil avec le TMCV de chaque année", "Année 1", "Année 2", "Année 3"], [
             ["TMCV (MCV / CA)"] + [pct(x, 2) for x in tm_y], ["SR = 150 000 / TMCV"] + [cft32 / x for x in tm_y],
             ["CA prévu"] + ca32])),
        ("4. « Chaque nouveau client rapporte 1 800 € »",
         f"<p><b>Faux.</b> 1 800 € est le prix, pas ce que le client rapporte. Au-delà du seuil, un client supplémentaire rapporte sa "
         f"<b>marge sur coût variable</b> : 1 800 − 220 − 144 − 36 = <b>1 400 €</b> par an, plus {eur(mes_net)} la première année "
         f"(400 € de mise en service − 2 % de frais), soit {eur(mcv_u+mes_net)}. Après IS (25 %), il reste 1 050 € par an. "
         "Et ce n'est vrai que si les charges fixes n'augmentent pas (un gros afflux de clients peut exiger plus de support).</p>"),
        ("5. Délai, VAN, IP", h32),
        ("6. Commenter deux affirmations",
         "<p>a. <b>Non.</b> La VAN repose sur des <i>prévisions</i> (90, 160, 240 clients) : elle dit que le projet est rentable "
         "<i>si</i> les ventes se réalisent. Elle ne garantit ni le succès commercial, ni la trésorerie ; une VAN positive peut "
         "devenir négative si les ventes sont plus faibles (sensibilité à tester).</p>"
         "<p>b. <b>Non.</b> Le délai de récupération est un critère de liquidité : il ne mesure pas la rentabilité ni le risque. "
         "Il dépend lui aussi des prévisions ; il ignore les flux après récupération et la valeur temps de l'argent. "
         "Un délai court réduit l'exposition au risque, il ne la supprime pas (concurrence, perte de clients, obsolescence).</p>"),
        ("7. Plan de financement",
         "<p>Hypothèses : le remboursement de l'emprunt et les intérêts ne sont pas donnés → non intégrés (à ajouter aux besoins sinon). "
         "Pas de BFR donné dans l'énoncé.</p>"
         + table(["€", "Année 0", "Année 1", "Année 2", "Année 3"], [
             ["Apports des associés", 70000, "", "", ""], ["Subvention", 30000, "", "", ""], ["Emprunt", emp32, "", "", ""],
             ["CAF", ""] + caf32, ["<b>Total ressources</b>"] + res32,
             ["Investissements (Build)", build32, "", "", ""], ["<b>Total besoins</b>"] + bes32,
             ["Flux net de trésorerie"] + net32, ["<b>Flux nets cumulés</b>"] + cum32], total_rows=(4, 6, 8))),
        ("8. Rentabilité, financement, trésorerie",
         "<ul><li><b>Rentabilité</b> : le projet crée-t-il plus de valeur qu'il ne coûte ? (résultat, VAN, IP, rentabilité économique).</li>"
         "<li><b>Financement</b> : avec quelles ressources paie-t-on les investissements et le BFR ? (apports, subventions, emprunts, CAF).</li>"
         "<li><b>Trésorerie</b> : a-t-on assez d'argent disponible à chaque instant ? (flux nets cumulés, décalages de paiement). "
         "Un projet rentable peut manquer de trésorerie (ici : année 0 déficitaire), et un projet bien financé peut ne pas être rentable.</li></ul>"),
    ],
    f"""<p>Le projet est rentable : seuil de {math.ceil(sr32_cli)} clients dépassé dès l'année 2, VAN à 10 % de {eur(r32['van'])},
    IP de {fr(r32['ip'],2)}, récupération en {duree_txt(r32['delai'])}. L'année 1 n'est bénéficiaire que grâce aux frais de mise
    en service : le vrai enjeu est de <b>fidéliser et faire croître la base de clients</b>. Côté financement, les 150 000 €
    de ressources ne couvrent pas les 180 000 € de Build : il manque <b>{eur(-cum32[0])}</b> en année 0. Il faut augmenter
    l'emprunt ou les apports, ou étaler une partie des dépenses de développement ; la trésorerie devient ensuite largement
    positive grâce à la CAF.</p>""",
    notes=["Si l'on considère que commissions et frais de paiement ne sont pas des coûts « de la solution », le TCO technique "
           f"vaut {eur(build32 + 3*cf32 + sum(cloud32))}."],
    tags=["Build/Run/TCO", "seuil de rentabilité", "compte de résultat", "VAN", "plan de financement"])

# ---------------- Exercice 3 — AlfaM, deux architectures
bat = [40, 110, 200, 300, 410]
newb = [bat[0]] + [bat[t] - bat[t - 1] for t in range(1, 5)]
abo33 = [n * 1500 for n in bat]
inst33 = [n * 900 for n in newb]
integ33 = [rnd(n * 0.3 * 1200) for n in newb]
ca33 = [abo33[t] + inst33[t] + integ33[t] for t in range(5)]
ARCH = {
    "A": dict(build=120000 + 45000 + 15000 + 20000 + 10000, runf=28000 + 32000 + 12000 + 8000, var=420 + 80,
              am=amort_lineaire(210000, 3) + [0, 0]),
    "B": dict(build=120000 + 45000 + 15000 + 95000 + 25000 + 10000,
              runf=35000 + 32000 + 12000 + 18000 + 15000 + 10000, var=140),
}
amB_log = amort_lineaire(120000 + 45000 + 15000 + 10000, 3) + [0, 0]
amB_mat = amort_lineaire(95000 + 25000, 5)
ARCH["B"]["am"] = [amB_log[t] + amB_mat[t] for t in range(5)]
dbfr = [10000, 10000, 12000, 13000, 13000, 15000]   # années 0 à 5
for k, a in ARCH.items():
    a["cv"] = [n * a["var"] for n in bat]
    a["run"] = [a["runf"] + a["cv"][t] for t in range(5)]
    a["tco"] = a["build"] + sum(a["run"])
    a["rex"] = [ca33[t] - a["cv"][t] - a["runf"] - a["am"][t] for t in range(5)]
    a["is"] = [is_tax(x, economie=False) for x in a["rex"]]
    a["rn"] = [a["rex"][t] - a["is"][t] for t in range(5)]
    a["caf"] = [a["rn"][t] + a["am"][t] for t in range(5)]
    a["flux"] = [-a["build"] - dbfr[0]] + [a["caf"][t] - dbfr[t + 1] for t in range(5)]
    a["h"], a["r"] = bloc_criteres(a["flux"], 0.10, nom=k)
    rec = a["flux"][:5] + [a["flux"][5] + sum(dbfr)]
    _, a["van_rec"], _ = actualise(rec, .10)
    a["res"] = [180000 + 80000] + a["caf"]
    a["bes"] = [a["build"] + dbfr[0]] + dbfr[1:]
    a["net"] = [a["res"][t] - a["bes"][t] for t in range(6)]
    a["cum"] = [sum(a["net"][:t + 1]) for t in range(6)]
    cum_sans = [sum(([180000] + a["caf"])[:t + 1]) - sum(a["bes"][:t + 1]) for t in range(6)]
    a["besoin_emprunt"] = max(0, -min(cum_sans))
    log(f"P3 Ex3 {k} : build {a['build']} runf {a['runf']} TCO {a['tco']} REX {a['rex']} CAF {a['caf']} flux {a['flux']} "
        f"VAN {a['r']['van']} IP {a['r']['ip']:.4f} délai {a['r']['delai']} | BFR récupéré {a['van_rec']} | emprunt mini {a['besoin_emprunt']}")
A3, B3 = ARCH["A"], ARCH["B"]
check("P3E3 TCO A", A3["tco"], 1140000)
check("P3E3 TCO B", B3["tco"], 1068400)
Y5_0 = ["A0"] + Y5

def cr33(a, k):
    return table(["€"] + Y5, [
        ["CA"] + ca33, ["− CV"] + [-x for x in a["cv"]], ["− CF (Run fixe)"] + [-a["runf"]] * 5,
        ["− Amortissements"] + [-x for x in a["am"]], ["REX = Résultat avant IS"] + a["rex"],
        ["− IS 25 %"] + [-x for x in a["is"]], ["Résultat net"] + a["rn"], ["<b>CAF</b>"] + a["caf"]],
        total_rows=(4, 7), cap=f"Architecture {k}")

def pf33(a, k):
    return table(["€"] + Y5_0, [
        ["Fonds propres", 180000, "", "", "", "", ""], ["Emprunt bancaire", 80000, "", "", "", "", ""],
        ["CAF", ""] + a["caf"], ["<b>Total ressources</b>"] + a["res"],
        ["Investissements (Build)", a["build"], "", "", "", "", ""], ["Variation du BFR"] + dbfr,
        ["<b>Total besoins</b>"] + a["bes"], ["Flux net de trésorerie"] + a["net"],
        ["<b>Flux nets cumulés</b>"] + a["cum"]], total_rows=(3, 6, 8), cap=f"Architecture {k}")

def flux33(a, k):
    return table(["€"] + Y5_0, [
        ["Investissements", -a["build"], "", "", "", "", ""], ["CAF", ""] + a["caf"],
        ["− Variation du BFR"] + [-x for x in dbfr], ["<b>Flux net</b>"] + a["flux"]], total_rows=(3,),
        cap=f"Architecture {k}")

better_van = "A" if A3["r"]["van"] > B3["r"]["van"] else "B"
exo("p3e3", 3, 3, "AlfaM — cloud public (A) ou infrastructure dédiée (B) ?",
    """<p>Plateforme de suivi énergétique des bâtiments (tableaux de bord, alertes, indicateurs, rapports).
    Revenus : installation 900 €/nouveau bâtiment, abonnement 1 500 €/bâtiment/an, intégration spécifique 1 200 € pour 30 %
    des nouveaux bâtiments. Bâtiments : 40 / 110 / 200 / 300 / 410 (pas de résiliation, pas de valeur résiduelle).</p>
    <p><b>A – cloud public</b> : développement 120 000, connecteurs 45 000, audit 15 000, mise en place cloud 20 000, environnement
    de test 10 000 € ; par an : administration 28 000, maintenance 32 000, licences 12 000, sécurité 8 000 € ; hébergement
    420 € + stockage 80 € par bâtiment et par an. Amortissement sur 3 ans.</p>
    <p><b>B – infrastructure dédiée</b> : développement 120 000, connecteurs 45 000, audit 15 000, serveurs et réseau 95 000,
    installation 25 000, test 10 000 € ; par an : administration 35 000, maintenance 32 000, licences 12 000, maintenance matérielle
    18 000, électricité/locaux 15 000, sécurité 10 000 € ; stockage et traitements 140 €/bâtiment/an. Logiciel et développement
    amortis sur 3 ans, serveurs/équipements/installation sur 5 ans.</p>
    <p>Étude 5 ans, actualisation 10 %, fonds propres 180 000 €, emprunt bancaire 80 000 € maximum. Variation du BFR :
    10 000 (A0), 10 000 (A1), 12 000 (A2), 13 000 (A3 et A4), 15 000 (A5).</p>
    <p>1) Build, Run, TCO. 2) Exemples de coûts fixe/variable/direct/indirect. 3) Blocs « structure de coûts » et « sources de revenus ».
    4) Même canvas, résultats différents ? 5) Comptes de résultat. 6) Délai, VAN, IP. 7) Plans de financement.</p>""",
    [
        ("1. Build, Run, TCO sur 5 ans",
         f"<p>Build A = 120 + 45 + 15 + 20 + 10 = <b>{eur(A3['build'])}</b> ; Run fixe A = {eur(A3['runf'])}/an ; "
         f"variable A = 420 + 80 = 500 €/bâtiment.<br>Build B = 120 + 45 + 15 + 95 + 25 + 10 = <b>{eur(B3['build'])}</b> ; "
         f"Run fixe B = {eur(B3['runf'])}/an ; variable B = 140 €/bâtiment.</p>"
         + table(["€"] + Y5 + ["Total"], [
             ["Bâtiments"] + bat + [sum(bat)],
             ["A – Run fixe"] + [A3["runf"]] * 5 + [5 * A3["runf"]], ["A – Run variable"] + A3["cv"] + [sum(A3["cv"])],
             ["A – Run total"] + A3["run"] + [sum(A3["run"])],
             ["B – Run fixe"] + [B3["runf"]] * 5 + [5 * B3["runf"]], ["B – Run variable"] + B3["cv"] + [sum(B3["cv"])],
             ["B – Run total"] + B3["run"] + [sum(B3["run"])]], total_rows=(3, 6))
         + table(["€", "Build", "Run 5 ans", "TCO 5 ans"], [
             ["Architecture A", A3["build"], sum(A3["run"]), A3["tco"]],
             ["Architecture B", B3["build"], sum(B3["run"]), B3["tco"]]])
         + f"<p>B coûte plus cher au départ (+{eur(B3['build']-A3['build'])}) mais son TCO est plus faible de "
           f"{eur(A3['tco']-B3['tco'])} : son coût variable par bâtiment est 3,6 fois plus faible.</p>"),
        ("2. Exemples de coûts",
         "<ul><li><b>Fixe</b> : administration et supervision, licences, électricité/locaux (B).</li>"
         "<li><b>Variable</b> : hébergement cloud 420 €/bâtiment (A), stockage et traitements 140 €/bâtiment (B).</li>"
         "<li><b>Direct</b> : développement de la plateforme, connecteurs compteurs (propres au projet AlfaM).</li>"
         "<li><b>Indirect</b> : locaux, réseau informatique, direction et services support d'Alfa partagés avec d'autres projets "
         "(pas chiffrés dans l'énoncé).</li></ul>"),
        ("3. Blocs du Business Model Canvas",
         '<div class="bmc"><div><b>Structure de coûts</b> : Build (développement de la plateforme et des connecteurs, audit cyber, '
         "architecture cloud ou serveurs, test) ; Run fixe (administration, maintenance, licences, sécurité, + maintenance matérielle "
         "et énergie pour B) ; Run variable par bâtiment (hébergement et stockage pour A, stockage et traitements pour B).</div>"
         "<div><b>Sources de revenus</b> : frais d'installation (900 €/nouveau bâtiment, ponctuel), abonnement annuel récurrent "
         "(1 500 €/bâtiment), prestations d'intégration spécifiques (1 200 €, 30 % des nouveaux bâtiments).</div></div>"),
        ("4. Même canvas, résultats différents",
         "<p>Le canvas décrit <i>comment</i> l'entreprise crée et capte de la valeur : mêmes clients, même proposition de valeur, "
         "mêmes revenus. L'architecture technique ne change que la <b>structure des coûts</b> : A transforme des coûts en variables "
         "(cloud, peu d'investissement), B en coûts fixes et investissements (amortissements). À revenus égaux, le résultat, "
         "le seuil de rentabilité, les besoins de financement et le risque diffèrent : <b>la décision technique influe sur la structure des coûts</b>.</p>"),
        ("5. Chiffre d'affaires et comptes de résultat",
         "<p>Hypothèses : IS 25 % (non donné), pas d'IS sur une perte ; pas de frais financiers (taux de l'emprunt non donné). "
         "Amortissements A : 210 000 / 3 = 70 000 (A1–A3). B : (120 + 45 + 15 + 10) k€ / 3 = 63 333 (A1–A3, dernière 63 334) "
         "+ (95 + 25) k€ / 5 = 24 000 (A1–A5).</p>"
         + table(["€"] + Y5, [
             ["Bâtiments (nouveaux)"] + [f"{bat[t]} ({newb[t]})" for t in range(5)],
             ["Abonnements 1 500 €"] + abo33, ["Installations 900 €"] + inst33,
             ["Intégrations 1 200 € × 30 % des nouveaux"] + integ33, ["<b>CA</b>"] + ca33], total_rows=(4,))
         + cr33(A3, "A") + cr33(B3, "B")),
        ("6. Flux, délai, VAN, IP",
         "<p>Flux = CAF − variation du BFR − investissements. Le BFR n'est pas récupéré en fin de période (l'énoncé précise "
         "« pas de valeurs résiduelles ») ; voir la note pour l'autre hypothèse.</p>"
         + flux33(A3, "A") + A3["h"] + flux33(B3, "B") + B3["h"]),
        ("7. Plans de financement",
         "<p>On mobilise les fonds propres et l'emprunt maximal en A0. Remboursement de l'emprunt non précisé → non intégré.</p>"
         + pf33(A3, "A") + pf33(B3, "B")
         + f"<p>Emprunt réellement nécessaire (sans emprunt, plus forte trésorerie cumulée négative) : A = {eur(A3['besoin_emprunt'])}, "
           f"B = {eur(B3['besoin_emprunt'])}.</p>"),
    ],
    f"""<p>Les deux architectures servent le même business model mais pas avec la même structure de coûts. A (cloud) demande
    moins d'investissement ({eur(A3['build'])}) et un financement plus léger ; B (dédiée) coûte plus au départ ({eur(B3['build'])})
    mais son coût par bâtiment est bien plus bas : TCO 5 ans de {eur(B3['tco'])} contre {eur(A3['tco'])}.
    VAN à 10 % : A = {eur(A3['r']['van'])} (IP {fr(A3['r']['ip'],2)}), B = {eur(B3['r']['van'])} (IP {fr(B3['r']['ip'],2)}).
    {"Les deux projets sont rentables" if min(A3['r']['van'], B3['r']['van']) > 0 else "Attention : au moins une architecture a une VAN négative"} ;
    <b>l'architecture {better_van} crée le plus de valeur</b>, de peu. Le financement fait la différence : avec 180 000 € de
    fonds propres, A n'a besoin que de {eur(A3['besoin_emprunt'])} d'emprunt, alors que B aurait besoin de
    {eur(B3['besoin_emprunt'])} (investissement plus lourd et CAF négative en année 1) : c'est plus que les 80 000 € accordés
    par la banque, la trésorerie cumulée de B reste négative ({eur(min(B3['cum']))} au plus bas). <b>On recommande A</b>
    (cloud) : rentable, finançable, plus souple si la croissance est plus lente que prévu. B ne deviendrait intéressante
    qu'avec plus de fonds propres et une forte croissance du parc (son coût par bâtiment est bien plus bas).</p>""",
    notes=[f"Si le BFR cumulé ({eur(sum(dbfr))}) est récupéré fin d'année 5 : VAN A = {eur(A3['van_rec'])}, VAN B = {eur(B3['van_rec'])}.",
           "Les installations et intégrations sont des recettes ponctuelles liées aux nouveaux bâtiments ; l'abonnement est récurrent."],
    tags=["Build/Run/TCO", "BMC", "compte de résultat", "BFR", "VAN", "plan de financement"])


# =================================================================
# QUIZ : vérification des réponses numériques
# =================================================================
QUIZ_CHECKS = {
    # id de question : valeur attendue de la bonne réponse
    "q-tco": 900 + 250,
    "q-delai": 150000 / 50000,
    "q-van1": rnd(110000 / 1.1) - 100000,
    "q-ip": 1.2,
    "q-mcv": (100 - 60) / 100,
    "q-sr": 40000 / 0.4,
    "q-ms": (150000 - 100000) / 150000,
    "q-re": (150 / 1500) * (1500 / 500),
    "q-caf": 30000 + 20000,
    "q-salaire": 3 * 75 * 8 / 12,
    "q-coef": round(1 / 1.1 ** 2, 3),
    "q-delai2": 2 + 20000 / 40000,
    "q-vr": 50000 * 0.75,
    "q-is": (200 - 50) * 0.25,
    "q-rot": 600 / 800,
    "q-bfr": 25000,
    "q-srcli": math.ceil(61000 / (500 - 200)),
}
quiz_path = os.path.join(ROOT, "js", "quiz-data.js")
if os.path.exists(quiz_path):
    src = open(quiz_path, encoding="utf-8").read()
    for qid, val in QUIZ_CHECKS.items():
        m = re.search(r'id:\s*"' + re.escape(qid) + r'".*?check:\s*([-0-9.]+)', src, re.S)
        if not m:
            problems.append(f"quiz {qid} : question ou champ check introuvable")
            continue
        check(f"quiz {qid}", float(m.group(1)), val, 1e-6)
    nq = len(re.findall(r'\bid:\s*"q-', src))
    log(f"Quiz : {nq} questions, {len(QUIZ_CHECKS)} réponses chiffrées vérifiées")
    if nq < 40:
        problems.append(f"quiz : seulement {nq} questions (< 40)")
else:
    log("Quiz : js/quiz-data.js absent (non vérifié)")

# =================================================================
# ÉCRITURE
# =================================================================
out = {
    "genere": "tools/verif.py",
    "slides": [dict(partie=p, slide=s, texte=t, niveau=n) for p, s, t, n in SLIDES],
    "exos": EXOS,
}
path = os.path.join(ROOT, "js", "exos-data.js")
with open(path, "w", encoding="utf-8") as fh:
    fh.write("/* Fichier GÉNÉRÉ par tools/verif.py — ne pas modifier à la main. */\n")
    fh.write("window.CEFI_EXOS = ")
    json.dump(out, fh, ensure_ascii=False, indent=1)
    fh.write(";\n")

print("\n".join(report))
print(f"\n{len(EXOS)} exercices écrits dans js/exos-data.js")
if problems:
    print("\n!!! PROBLÈMES :")
    for p in problems:
        print("  -", p)
    sys.exit(1)
print("Toutes les vérifications sont OK.")
