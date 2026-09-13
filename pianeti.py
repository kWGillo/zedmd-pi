"""Pianeti e Luna: che cosa si vede stasera, e da che parte guardare.

Come `satelliti.py`, questo modulo e' **solo** dati e matematica: non disegna
niente e non sa niente del pannello. Si verifica da solo, con uno script,
prima che una riga finisca sul display.

La differenza con i satelliti e' tutta a favore. Per un satellite servono gli
elementi orbitali, che invecchiano in giorni e vanno scaricati; per un pianeta
no. Le orbite dei pianeti si conoscono da tre secoli e cambiano cosi'
lentamente che una tabella di numeri fissi, con la loro deriva per secolo,
basta fino al 2050. Quindi:

* **nessuna rete, mai.** Niente TLE, niente fonti che possono spegnersi --
  come si e' spenta quella delle magnitudini dei satelliti;
* nessuna dipendenza nuova. Solo `math`, che c'e' sempre. L'aggiornamento via
  rete non esegue `install.sh`, e un Raspberry aggiornato da una versione
  precedente non installerebbe niente;
* e nessun caso in cui non si sa rispondere: i pianeti ci sono sempre.

## Da dove vengono i numeri

Gli elementi orbitali sono la tabella *Approximate Positions of the Major
Planets* del JPL, validita' 1800-2050. L'errore dichiarato e' di una decina di
secondi d'arco per i pianeti interni e di una decina di **primi** per Giove e
Saturno. Su un pannello che dice "OVEST, ALT 22 gradi" e' una precisione
ridicola in eccesso: mezzo grado non lo si distingue a occhio nudo, e la Luna
piena e' larga mezzo grado.

La Luna e' l'eccezione, e per due motivi opposti. E' vicina, quindi la sua
posizione dipende da **dove sei sulla Terra** e non solo da quando guardi: la
parallasse arriva a un grado, cioe' due lune piene, e va tolta. Ed e' l'oggetto
la cui orbita e' piu' disturbata dal Sole, quindi non bastano sei numeri: serve
una somma di termini periodici, che qui e' quella di Meeus ridotta ai piu'
grandi.

## Che cosa vuol dire "visibile"

La stessa domanda dei satelliti, e la stessa risposta severa: visibile vuol
dire che se esci lo **vedi**. Non basta che sia sopra l'orizzonte. Serve che
il cielo sia abbastanza scuro, che l'oggetto sia abbastanza alto da non stare
dietro i tetti, e che sia abbastanza luminoso. Mercurio soddisfa le prime due
condizioni molte sere l'anno e si vede pochissime volte nella vita, perche'
non si allontana mai dal Sole: per questo la sua soglia e' piu' dura delle
altre.
"""

import math
from datetime import datetime, timedelta, timezone

# ------------------------------------------------------------------ costanti

UA_KM = 149597870.7          # unita' astronomica in km
R_TERRA = 6378.137           # km, raggio equatoriale WGS84
OBLIQUITA = 23.439291111     # gradi, inclinazione dell'asse terrestre a J2000

# Quanto deve essere sceso il Sole perche' un pianeta si stacchi dal cielo.
# Il crepuscolo civile (-6) e' quando si accendono i lampioni e si vede gia'
# Venere; per gli altri serve piu' buio.
CREPUSCOLO_CIVILE = -6.0
CREPUSCOLO_NAUTICO = -12.0

# Sotto questa altezza non si guarda: ci sono i tetti, gli alberi e la foschia
# dell'orizzonte, che si mangia un paio di magnitudini.
ALTEZZA_MINIMA = 10.0

# Mercurio e' il caso speciale: sta sempre vicino al Sole, e quando e' visibile
# lo e' in un crepuscolo ancora chiaro. Chiedergli il buio pieno vorrebbe dire
# non annunciarlo mai.
ALTEZZA_MINIMA_MERCURIO = 5.0


# ---------------------------------------------------------- elementi orbitali

# Tabella JPL, validita' 1800-2050. Per ogni pianeta: valore a J2000 e deriva
# per secolo giuliano.
#   a      semiasse maggiore (UA)
#   e      eccentricita'
#   inc    inclinazione sull'eclittica (gradi)
#   L      longitudine media (gradi)
#   peri   longitudine del perielio (gradi)
#   nodo   longitudine del nodo ascendente (gradi)
#
# La Terra non c'e': c'e' il **baricentro Terra-Luna**, che e' quello che si
# muove su un'ellisse pulita. La differenza fra i due e' di 4700 km, cioe' tre
# centesimi di secondo d'arco visti da Giove.
ELEMENTI = {
    "mercurio": dict(
        a=(0.38709927, 0.00000037), e=(0.20563593, 0.00001906),
        inc=(7.00497902, -0.00594749), L=(252.25032350, 149472.67411175),
        peri=(77.45779628, 0.16047689), nodo=(48.33076593, -0.12534081)),
    "venere": dict(
        a=(0.72333566, 0.00000390), e=(0.00677672, -0.00004107),
        inc=(3.39467605, -0.00078890), L=(181.97909950, 58517.81538729),
        peri=(131.60246718, 0.00268329), nodo=(76.67984255, -0.27769418)),
    "terra": dict(
        a=(1.00000261, 0.00000562), e=(0.01671123, -0.00004392),
        inc=(-0.00001531, -0.01294668), L=(100.46457166, 35999.37244981),
        peri=(102.93768193, 0.32327364), nodo=(0.0, 0.0)),
    "marte": dict(
        a=(1.52371034, 0.00001847), e=(0.09339410, 0.00007882),
        inc=(1.84969142, -0.00813131), L=(-4.55343205, 19140.30268499),
        peri=(-23.94362959, 0.44441088), nodo=(49.55953891, -0.29257343)),
    "giove": dict(
        a=(5.20288700, -0.00011607), e=(0.04838624, -0.00013253),
        inc=(1.30439695, -0.00183714), L=(34.39644051, 3034.74612775),
        peri=(14.72847983, 0.21252668), nodo=(100.47390909, 0.20469106)),
    "saturno": dict(
        a=(9.53667594, -0.00125060), e=(0.05386179, -0.00050991),
        inc=(2.48599187, 0.00193609), L=(49.95424423, 1222.49362201),
        peri=(92.59887831, -0.41897216), nodo=(113.66242448, -0.28867794)),
}

# I cinque che si vedono a occhio nudo, nell'ordine in cui stanno nel cielo.
#
# Urano e Nettuno non ci sono, e non e' una svista: Urano e' di magnitudine
# 5,7, cioe' al limite assoluto dell'occhio in un cielo perfettamente buio, e
# in un paese con i lampioni non si vede. Vale la stessa regola dei satelliti:
# annunciare qualcosa di invisibile non e' un'imprecisione, e' una promessa
# mancata.
PIANETI = ("mercurio", "venere", "marte", "giove", "saturno")

NOMI = {
    "mercurio": ("Mercurio", "Mercury", "MERCURIO"),
    "venere": ("Venere", "Venus", "VENERE"),
    "marte": ("Marte", "Mars", "MARTE"),
    "giove": ("Giove", "Jupiter", "GIOVE"),
    "saturno": ("Saturno", "Saturn", "SATURNO"),
    "luna": ("Luna", "Moon", "LUNA"),
}

# Il colore con cui ciascuno va scritto sul pannello. Non e' decorazione: sono
# i colori veri, quelli che si vedono a occhio nudo o con un binocolo. Marte e'
# rosso, Saturno giallo paglierino, Venere bianco accecante.
COLORI = {
    "mercurio": "#c8c0b0",
    "venere": "#fff4d0",
    "marte": "#ff6a3c",
    "giove": "#ffd9a0",
    "saturno": "#f0d878",
    "luna": "#e8e8f0",
}


# ------------------------------------------------------------------- il tempo


def giuliano(quando=None):
    """datetime UTC -> giorno giuliano.

    Non si riusa quello di `satelliti.py` perche' quello arriva da `sgp4`, che
    e' una dipendenza facoltativa: un Raspberry senza `sgp4` deve comunque
    poter dire dov'e' la Luna.
    """
    quando = quando or datetime.now(timezone.utc)
    if quando.tzinfo is None:
        quando = quando.replace(tzinfo=timezone.utc)
    quando = quando.astimezone(timezone.utc)
    anno, mese = quando.year, quando.month
    giorno = (quando.day + quando.hour / 24.0 + quando.minute / 1440.0
              + (quando.second + quando.microsecond / 1e6) / 86400.0)
    if mese <= 2:
        anno -= 1
        mese += 12
    aa = anno // 100
    bb = 2 - aa + aa // 4          # correzione gregoriana
    return (math.floor(365.25 * (anno + 4716))
            + math.floor(30.6001 * (mese + 1)) + giorno + bb - 1524.5)


def secoli(jd):
    """Secoli giuliani da J2000. E' la variabile di tutte le formule."""
    return (jd - 2451545.0) / 36525.0


def gmst(jd):
    """Tempo siderale medio di Greenwich, in gradi.

    Quanto si e' girata la Terra. Serve per passare da "dove sta l'oggetto
    rispetto alle stelle" a "da che parte devo girarmi".
    """
    d = jd - 2451545.0
    t = d / 36525.0
    g = (280.46061837 + 360.98564736629 * d
         + 0.000387933 * t * t - t * t * t / 38710000.0)
    return g % 360.0


# --------------------------------------------------------------- i pianeti


def _kepler(anomalia, e):
    """Risolve M = E - e sin E, cioe' trova dove sta il pianeta sull'ellisse.

    Non ha soluzione in forma chiusa -- e' il problema che ha tenuto occupati
    gli astronomi per un secolo -- ma converge in tre o quattro passi con
    Newton. Il ciclo e' fermo a quindici per prudenza: con orbite planetarie
    (e < 0,21) ne bastano sempre meno di sei.
    """
    m = math.radians(anomalia)
    ecc = m + e * math.sin(m)
    for _ in range(15):
        dm = m - (ecc - e * math.sin(ecc))
        passo = dm / (1 - e * math.cos(ecc))
        ecc += passo
        if abs(passo) < 1e-12:
            break
    return ecc


def eliocentrico(nome, jd):
    """Dove sta un pianeta rispetto al Sole: (x, y, z) in UA, eclittica J2000."""
    el = ELEMENTI[nome]
    t = secoli(jd)
    a = el["a"][0] + el["a"][1] * t
    e = el["e"][0] + el["e"][1] * t
    inc = math.radians(el["inc"][0] + el["inc"][1] * t)
    lung = el["L"][0] + el["L"][1] * t
    peri = el["peri"][0] + el["peri"][1] * t
    nodo = el["nodo"][0] + el["nodo"][1] * t

    argomento = math.radians(peri - nodo)      # perielio contato dal nodo
    anomalia = (lung - peri + 180.0) % 360.0 - 180.0

    ecc = _kepler(anomalia, e)
    # Posizione nel piano dell'orbita, con il Sole in un fuoco.
    px = a * (math.cos(ecc) - e)
    py = a * math.sqrt(max(0.0, 1 - e * e)) * math.sin(ecc)

    ca, sa = math.cos(argomento), math.sin(argomento)
    cn, sn = math.cos(nodo * math.pi / 180.0), math.sin(nodo * math.pi / 180.0)
    ci, si = math.cos(inc), math.sin(inc)
    x = (ca * cn - sa * sn * ci) * px + (-sa * cn - ca * sn * ci) * py
    y = (ca * sn + sa * cn * ci) * px + (-sa * sn + ca * cn * ci) * py
    z = (sa * si) * px + (ca * si) * py
    return x, y, z


# La luce di Giove ci mette quaranta minuti ad arrivare, e in quaranta minuti
# Giove si sposta. Si guarda quindi dov'era quando e' partita la luce che
# vediamo adesso: un giro solo di correzione basta, il secondo cambierebbe le
# cose di un centesimo di secondo d'arco.
LUCE_GIORNI_PER_UA = 0.005775518331436995


def geocentrico(nome, jd):
    """Dove **si vede** un pianeta: (x, y, z) in UA, eclittica J2000, dalla Terra."""
    tx, ty, tz = eliocentrico("terra", jd)
    px, py, pz = eliocentrico(nome, jd)
    dx, dy, dz = px - tx, py - ty, pz - tz
    distanza = math.sqrt(dx * dx + dy * dy + dz * dz)
    if distanza > 0:
        jd2 = jd - distanza * LUCE_GIORNI_PER_UA
        px, py, pz = eliocentrico(nome, jd2)
        dx, dy, dz = px - tx, py - ty, pz - tz
    return dx, dy, dz


# ------------------------------------------------------------------- la Luna

# Termini periodici della longitudine e della distanza (Meeus, tavola 47.A),
# ridotti ai piu' grandi. Ogni riga: i coefficienti di D, M, M', F, poi il
# contributo alla longitudine (in milionesimi di grado) e alla distanza (in
# chilometri /1000).
#
# Il primo termine da solo vale 6,3 gradi: e' l'**equazione del centro**,
# cioe' il fatto che l'orbita e' un'ellisse. Il secondo, 1,3 gradi, e'
# l'evezione, che Tolomeo trovo' senza sapere perche'. Il terzo, 0,66 gradi,
# e' la variazione, scoperta da Tycho Brahe. Da li' in giu' si scende sotto il
# quinto di grado, che a occhio nudo non si distingue.
_LUNA_LON = (
    (0, 0, 1, 0, 6288774, -20905355),
    (2, 0, -1, 0, 1274027, -3699111),
    (2, 0, 0, 0, 658314, -2955968),
    (0, 0, 2, 0, 213618, -569925),
    (0, 1, 0, 0, -185116, 48888),
    (0, 0, 0, 2, -114332, -3149),
    (2, 0, -2, 0, 58793, 246158),
    (2, -1, -1, 0, 57066, -152138),
    (2, 0, 1, 0, 53322, -170733),
    (2, -1, 0, 0, 45758, -204586),
    (0, 1, -1, 0, -40923, -129620),
    (1, 0, 0, 0, -34720, 108743),
    (0, 1, 1, 0, -30383, 104755),
    (2, 0, 0, -2, 15327, 10321),
    (0, 0, 1, 2, -12528, 0),
    (0, 0, 1, -2, 10980, 79661),
    (4, 0, -1, 0, 10675, -34782),
    (0, 0, 3, 0, 10034, -23210),
    (4, 0, -2, 0, 8548, -21636),
    (2, 1, -1, 0, -7888, 24208),
    (2, 1, 0, 0, -6766, 30824),
    (1, 0, -1, 0, -5163, -8379),
    (1, 1, 0, 0, 4987, -16675),
    (2, -1, 1, 0, 4036, -12831),
    (2, 0, 2, 0, 3994, -10445),
    (4, 0, 0, 0, 3861, -11650),
    (2, 0, -3, 0, 3665, 14403),
    (0, 1, -2, 0, -2689, -7003),
    (2, 0, -1, 2, -2602, 0),
    (2, -1, -2, 0, 2390, 10056),
    (1, 0, 1, 0, -2348, 6322),
    (2, -2, 0, 0, 2236, -9884),
    (0, 1, 2, 0, -2120, 5751),
    (0, 2, 0, 0, -2069, 0),
    (2, -2, -1, 0, 2048, -4950),
    (2, 0, 1, -2, -1773, 4130),
    (2, 0, 0, 2, -1595, 0),
    (4, -1, -1, 0, 1215, -3958),
    (0, 0, 2, 2, -1110, 0),
    (3, 0, -1, 0, -892, 3258),
    (2, 1, 1, 0, -810, 2616),
    (4, -1, -2, 0, 759, -1897),
    (0, 2, -1, 0, -713, -2117),
    (2, 2, -1, 0, -700, 2354),
    (2, 1, -2, 0, 691, 0),
    (2, -1, 0, -2, 596, 0),
    (4, 0, 1, 0, 549, -1423),
    (0, 0, 4, 0, 537, -1117),
    (4, -1, 0, 0, 520, -1571),
    (1, 0, -2, 0, -487, -1739),
    (2, 1, 0, -2, -399, 0),
    (0, 0, 2, -2, -381, -4421),
    (1, 1, 1, 0, 351, 0),
    (3, 0, -2, 0, -340, 0),
    (4, 0, -3, 0, 330, 0),
    (2, -1, 2, 0, 327, 0),
    (0, 2, 1, 0, -323, 1165),
    (1, 1, -1, 0, 299, 0),
    (2, 0, 3, 0, 294, 0),
    (2, 0, -1, -2, 0, 8752),
)

# Termini della latitudine (tavola 47.B). Il primo, 5,1 gradi, e' tutta
# l'inclinazione dell'orbita lunare: e' il motivo per cui non c'e' un'eclissi
# ogni mese.
_LUNA_LAT = (
    (0, 0, 0, 1, 5128122),
    (0, 0, 1, 1, 280602),
    (0, 0, 1, -1, 277693),
    (2, 0, 0, -1, 173237),
    (2, 0, -1, 1, 55413),
    (2, 0, -1, -1, 46271),
    (2, 0, 0, 1, 32573),
    (0, 0, 2, 1, 17198),
    (2, 0, 1, -1, 9266),
    (0, 0, 2, -1, 8822),
    (2, -1, 0, -1, 8216),
    (2, 0, -2, -1, 4324),
    (2, 0, 1, 1, 4200),
    (2, 1, 0, -1, -3359),
    (2, -1, -1, 1, 2463),
    (2, -1, 0, 1, 2211),
    (2, -1, -1, -1, 2065),
    (0, 1, -1, -1, -1870),
    (4, 0, -1, -1, 1828),
    (0, 1, 0, 1, -1794),
    (0, 0, 0, 3, -1749),
    (0, 1, -1, 1, -1565),
    (1, 0, 0, 1, -1491),
    (0, 1, 1, 1, -1475),
    (0, 1, 1, -1, -1410),
    (0, 1, 0, -1, -1344),
    (1, 0, 0, -1, -1335),
    (0, 0, 3, 1, 1107),
    (4, 0, 0, -1, 1021),
    (4, 0, -1, 1, 833),
    (0, 0, 1, -3, 777),
    (4, 0, -2, 1, 671),
    (2, 0, 0, -3, 607),
    (2, 0, 2, -1, 596),
    (2, -1, 1, -1, 491),
    (2, 0, -2, 1, -451),
    (0, 0, 3, -1, 439),
    (2, 0, 2, 1, 422),
    (2, 0, -3, -1, 421),
    (2, 1, -1, 1, -366),
    (2, 1, 0, 1, -351),
    (4, 0, 0, 1, 331),
    (2, -1, 1, 1, 315),
    (2, -2, 0, -1, 302),
    (0, 0, 1, 3, -283),
    (2, 1, 1, -1, -229),
    (1, 1, 0, -1, 223),
    (1, 1, 0, 1, 223),
    (0, 1, -2, -1, -220),
    (2, 1, -1, -1, -220),
    (1, 0, 1, 1, -185),
    (2, -1, -2, -1, 181),
    (0, 1, 2, 1, -177),
    (4, 0, -2, -1, 176),
    (4, -1, -1, -1, 166),
    (1, 0, 1, -1, -164),
    (4, 0, 1, -1, 132),
    (1, 0, -1, -1, -119),
    (4, -1, 0, -1, 115),
    (2, -2, 0, 1, 107),
)


def luna_eclittica(jd):
    """Longitudine, latitudine (gradi) e distanza (km) della Luna, geocentriche."""
    t = secoli(jd)
    t2 = t * t
    t3 = t2 * t
    t4 = t3 * t

    # Longitudine media, elongazione dal Sole, le due anomalie e l'argomento
    # della latitudine. Sono i cinque angoli da cui dipende tutto il resto.
    lung = (218.3164477 + 481267.88123421 * t - 0.0015786 * t2
            + t3 / 538841.0 - t4 / 65194000.0) % 360.0
    elong = (297.8501921 + 445267.1114034 * t - 0.0018819 * t2
             + t3 / 545868.0 - t4 / 113065000.0) % 360.0
    sole_m = (357.5291092 + 35999.0502909 * t - 0.0001536 * t2
              + t3 / 24490000.0) % 360.0
    luna_m = (134.9633964 + 477198.8675055 * t + 0.0087414 * t2
              + t3 / 69699.0 - t4 / 14712000.0) % 360.0
    lat_arg = (93.2720950 + 483202.0175233 * t - 0.0036539 * t2
               - t3 / 3526000.0 + t4 / 863310000.0) % 360.0

    # I tre termini additivi: Venere, Giove e l'appiattimento della Terra.
    a1 = math.radians((119.75 + 131.849 * t) % 360.0)
    a2 = math.radians((53.09 + 479264.290 * t) % 360.0)
    a3 = math.radians((313.45 + 481266.484 * t) % 360.0)

    # L'eccentricita' dell'orbita terrestre cambia lentamente, e i termini che
    # dipendono dall'anomalia del Sole vanno corretti di conseguenza.
    ecc = 1 - 0.002516 * t - 0.0000074 * t2

    rd, rm, rmm, rf = (math.radians(elong), math.radians(sole_m),
                       math.radians(luna_m), math.radians(lat_arg))

    somma_l = somma_r = 0.0
    for d, m, mm, f, cl, cr in _LUNA_LON:
        arg = d * rd + m * rm + mm * rmm + f * rf
        fattore = ecc ** abs(m)
        somma_l += cl * fattore * math.sin(arg)
        somma_r += cr * fattore * math.cos(arg)

    somma_b = 0.0
    for d, m, mm, f, cb in _LUNA_LAT:
        arg = d * rd + m * rm + mm * rmm + f * rf
        somma_b += cb * (ecc ** abs(m)) * math.sin(arg)

    somma_l += (3958 * math.sin(a1) + 1962 * math.sin(rl_meno(lung, lat_arg))
                + 318 * math.sin(a2))
    somma_b += (-2235 * math.sin(math.radians(lung))
                + 382 * math.sin(a3)
                + 175 * math.sin(a1 - rf) + 175 * math.sin(a1 + rf)
                + 127 * math.sin(math.radians(lung) - rmm)
                - 115 * math.sin(math.radians(lung) + rmm))

    longitudine = (lung + somma_l / 1000000.0) % 360.0
    latitudine = somma_b / 1000000.0
    distanza = 385000.56 + somma_r / 1000.0
    return longitudine, latitudine, distanza


def rl_meno(lung, lat_arg):
    """L'argomento `L' - F` del termine additivo, in radianti."""
    return math.radians((lung - lat_arg) % 360.0)


# ------------------------------------------------- da dove sta a dove guardare


def _equatoriale(lon_ecl, lat_ecl, jd, precessione=True):
    """Da coordinate eclittiche a equatoriali (versore).

    `precessione` non e' una raffinatezza facoltativa: e' la differenza fra
    avere ragione e sbagliare di mezzo grado, e va accesa o spenta a seconda
    di **da dove arrivano** le coordinate.

    Gli elementi orbitali del JPL sono riferiti all'equinozio J2000, che e'
    fermo. L'asse terrestre pero' si sposta di un grado ogni 72 anni, quindi
    per sapere dove puntare adesso bisogna aggiungere la precessione accumulata
    da allora -- nel 2030 e' gia' mezzo grado, cioe' una luna piena.

    La serie lunare di Meeus no: e' gia' riferita all'equinozio **della data**,
    e aggiungerle la precessione la sposta di quel mezzo grado nel verso
    sbagliato. Non e' un ragionamento: e' il risultato del confronto con
    un'effemeride indipendente, che con la doppia precessione dava 25 primi
    d'arco di errore e senza ne' da' 1,4.
    """
    t = secoli(jd)
    # Obliquita' media, che cambia lentamente.
    eps = math.radians(OBLIQUITA - 0.0130042 * t)
    correzione = ((5029.0966 * t + 1.11113 * t * t) / 3600.0
                  if precessione else 0.0)
    lon = math.radians(lon_ecl + correzione)
    lat = math.radians(lat_ecl)
    x = math.cos(lat) * math.cos(lon)
    y = math.cos(lat) * math.sin(lon)
    z = math.sin(lat)
    return (x,
            math.cos(eps) * y - math.sin(eps) * z,
            math.sin(eps) * y + math.cos(eps) * z)


def _alt_az(versore, jd, lat, lon):
    """Versore equatoriale -> (altezza, azimut) in gradi, da qui e adesso."""
    theta = math.radians(gmst(jd) + lon)
    rlat = math.radians(lat)
    zenit = (math.cos(rlat) * math.cos(theta),
             math.cos(rlat) * math.sin(theta),
             math.sin(rlat))
    nord = (-math.sin(rlat) * math.cos(theta),
            -math.sin(rlat) * math.sin(theta),
            math.cos(rlat))
    est = (-math.sin(theta), math.cos(theta), 0.0)
    su = sum(a * b for a, b in zip(versore, zenit))
    vn = sum(a * b for a, b in zip(versore, nord))
    ve = sum(a * b for a, b in zip(versore, est))
    altezza = math.degrees(math.asin(max(-1.0, min(1.0, su))))
    azimut = math.degrees(math.atan2(ve, vn)) % 360.0
    return altezza, azimut


def _eclittiche(vettore):
    """(x, y, z) -> longitudine, latitudine eclittiche in gradi, e modulo."""
    x, y, z = vettore
    raggio = math.sqrt(x * x + y * y + z * z)
    if raggio <= 0:
        return 0.0, 0.0, 0.0
    return (math.degrees(math.atan2(y, x)) % 360.0,
            math.degrees(math.asin(z / raggio)),
            raggio)


def sole_eclittica(jd):
    """Longitudine del Sole e distanza Terra-Sole, dagli stessi elementi."""
    x, y, z = eliocentrico("terra", jd)
    return _eclittiche((-x, -y, -z))


# ------------------------------------------------------------- la luminosita'


def _magnitudine(nome, r, delta, fase):
    """Quanto appare luminoso, con le formule classiche di Meeus.

    `r` distanza dal Sole, `delta` distanza da noi (UA), `fase` l'angolo
    Sole-pianeta-Terra in gradi: e' quello che fa di Venere una falce.

    Per Saturno si ignora l'inclinazione degli anelli, che da sola vale quasi
    una magnitudine: aperti riflettono quanto il pianeta, di taglio spariscono.
    E' un'approssimazione che si puo' permettere perche' Saturno sta comunque
    fra 0 e +1,5, cioe' sempre e comunque a occhio nudo, e la magnitudine qui
    serve a decidere **se** annunciarlo, non a scriverla.
    """
    if r <= 0 or delta <= 0:
        return None
    base = 5.0 * math.log10(r * delta)
    i = fase
    if nome == "mercurio":
        return (-0.42 + base + 0.0380 * i - 0.000273 * i * i
                + 0.000002 * i ** 3)
    if nome == "venere":
        return (-4.40 + base + 0.0009 * i + 0.000239 * i * i
                - 0.00000065 * i ** 3)
    if nome == "marte":
        return -1.52 + base + 0.016 * i
    if nome == "giove":
        return -9.40 + base + 0.005 * i
    if nome == "saturno":
        return -8.88 + base
    return None


# ------------------------------------------------------------------ le viste


def dove(nome, quando=None, lat=0.0, lon=0.0):
    """Dove sta un oggetto adesso, visto da qui.

    Torna altezza e azimut in gradi, la distanza, la magnitudine, l'angolo di
    fase e l'elongazione dal Sole -- che e' la cosa che decide se si vede: un
    pianeta a dieci gradi dal Sole e' nel bagliore anche se e' luminosissimo.
    """
    jd = giuliano(quando)
    sole_lon, _sole_lat, sole_r = sole_eclittica(jd)

    if nome == "luna":
        lon_ecl, lat_ecl, dist_km = luna_eclittica(jd)
        versore = _equatoriale(lon_ecl, lat_ecl, jd, precessione=False)
        altezza, azimut = _alt_az(versore, jd, lat, lon)
        # La parallasse: la Luna e' cosi' vicina che da terra si vede fino a un
        # grado piu' in basso che dal centro del pianeta. Un grado sono due
        # lune piene, e all'orizzonte e' la differenza fra "sorge" e "e' gia'
        # sorta".
        seno_par = R_TERRA / dist_km
        altezza -= math.degrees(math.asin(
            max(-1.0, min(1.0, seno_par * math.cos(math.radians(altezza))))))
        elongazione = _differenza(lon_ecl, sole_lon)
        fase_angolo = 180.0 - abs(elongazione)
        return {
            "nome": "luna",
            "altezza": altezza,
            "azimut": azimut,
            "distanza_km": dist_km,
            "magnitudine": None,
            "fase_angolo": fase_angolo,
            "elongazione": abs(elongazione),
            "crescente": elongazione > 0,
        }

    geo = geocentrico(nome, jd)
    lon_ecl, lat_ecl, delta = _eclittiche(geo)
    versore = _equatoriale(lon_ecl, lat_ecl, jd)
    altezza, azimut = _alt_az(versore, jd, lat, lon)
    r = math.sqrt(sum(c * c for c in eliocentrico(nome, jd)))
    # Angolo di fase dal triangolo Sole-pianeta-Terra.
    coseno = ((r * r + delta * delta - sole_r * sole_r) / (2 * r * delta)
              if r > 0 and delta > 0 else 1.0)
    fase_angolo = math.degrees(math.acos(max(-1.0, min(1.0, coseno))))
    return {
        "nome": nome,
        "altezza": altezza,
        "azimut": azimut,
        "distanza_ua": delta,
        "magnitudine": _magnitudine(nome, r, delta, fase_angolo),
        "fase_angolo": fase_angolo,
        "elongazione": abs(_differenza(lon_ecl, sole_lon)),
        "crescente": _differenza(lon_ecl, sole_lon) > 0,
    }


def _differenza(a, b):
    """a - b, riportato fra -180 e +180 gradi."""
    return (a - b + 180.0) % 360.0 - 180.0


def altezza_sole(quando=None, lat=0.0, lon=0.0):
    """Quanto e' alto il Sole. Negativo vuol dire sotto l'orizzonte."""
    jd = giuliano(quando)
    lon_ecl, lat_ecl, _r = sole_eclittica(jd)
    return _alt_az(_equatoriale(lon_ecl, lat_ecl, jd), jd, lat, lon)[0]


# --------------------------------------------------------------- la fase lunare

# I nomi delle otto fasi. Non sono otto momenti ma otto tratti: "primo quarto"
# e' un istante preciso in astronomia e un paio di giorni per chi guarda in su.
FASI = (
    ("nuova", 0.0),
    ("crescente", 0.125),
    ("primo_quarto", 0.25),
    ("gibbosa_crescente", 0.375),
    ("piena", 0.5),
    ("gibbosa_calante", 0.625),
    ("ultimo_quarto", 0.75),
    ("calante", 0.875),
)

MESE_SINODICO = 29.530588861     # giorni fra due lune nuove


def fase_luna(quando=None):
    """La fase della Luna: quanta ne e' illuminata, e come si chiama.

    `frazione` va da 0 (nuova) a 1 (piena). `avanzamento` e' la posizione nel
    ciclo, da 0 a 1: serve a distinguere una falce crescente da una calante,
    che hanno la stessa frazione illuminata e sono due cose diverse -- una
    dice "domani sara' di piu'", l'altra il contrario.
    """
    jd = giuliano(quando)
    lon_ecl, lat_ecl, dist = luna_eclittica(jd)
    sole_lon, _sl, _sr = sole_eclittica(jd)
    elongazione = _differenza(lon_ecl, sole_lon)
    fase_angolo = 180.0 - abs(elongazione)
    frazione = (1 + math.cos(math.radians(fase_angolo))) / 2.0
    avanzamento = ((lon_ecl - sole_lon) % 360.0) / 360.0
    nome = FASI[0][0]
    for etichetta, soglia in FASI:
        if avanzamento >= soglia - 0.0625:
            nome = etichetta
    if avanzamento >= 1 - 0.0625:
        nome = "nuova"
    return {
        "frazione": frazione,
        "avanzamento": avanzamento,
        "fase": nome,
        "crescente": avanzamento < 0.5,
        "eta_giorni": avanzamento * MESE_SINODICO,
        "distanza_km": dist,
        "latitudine": lat_ecl,
    }


# ------------------------------------------------------- sorgere e tramontare


def _altezza_a(nome, quando, lat, lon):
    return dove(nome, quando, lat, lon)["altezza"]


def orizzonte(nome, quando=None, lat=0.0, lon=0.0, ore=24, soglia=0.0):
    """Quando questo oggetto attraversa una certa altezza, nelle prossime ore.

    Torna una lista di (istante, "sorge"/"tramonta"). Si campiona ogni dieci
    minuti e si stringe: i pianeti si muovono di pochi primi al giorno e in
    dieci minuti non possono sorgere e tramontare di nascosto. La Luna e' la
    piu' veloce e fa mezzo grado all'ora, quindi il campione e' abbondante.
    """
    quando = quando or datetime.now(timezone.utc)
    if quando.tzinfo is None:
        quando = quando.replace(tzinfo=timezone.utc)
    passo = timedelta(minutes=10)
    eventi = []
    t0 = quando
    a0 = _altezza_a(nome, t0, lat, lon) - soglia
    fine = quando + timedelta(hours=ore)
    while t0 < fine:
        t1 = t0 + passo
        a1 = _altezza_a(nome, t1, lat, lon) - soglia
        if (a0 < 0) != (a1 < 0):
            sinistra, destra = t0, t1
            for _ in range(20):
                meta = sinistra + (destra - sinistra) / 2
                if (_altezza_a(nome, meta, lat, lon) - soglia < 0) == (a0 < 0):
                    sinistra = meta
                else:
                    destra = meta
            eventi.append((sinistra + (destra - sinistra) / 2,
                           "sorge" if a1 > 0 else "tramonta"))
        t0, a0 = t1, a1
    return eventi


def prossimo_tramonto(nome, quando=None, lat=0.0, lon=0.0, ore=24):
    """Quando questo oggetto va sotto l'orizzonte. None se non succede."""
    for istante, tipo in orizzonte(nome, quando, lat, lon, ore):
        if tipo == "tramonta":
            return istante
    return None


# -------------------------------------------------------------- che c'e' stasera


def visibili(quando=None, lat=0.0, lon=0.0, altezza_minima=ALTEZZA_MINIMA):
    """I pianeti che in questo momento si vedono davvero, dal piu' luminoso.

    Tre condizioni, tutte necessarie:

    * **il cielo e' abbastanza scuro.** Di giorno i pianeti ci sono ma non si
      vedono, e annunciarli sarebbe come annunciare le stelle a mezzogiorno;
    * **sono abbastanza alti.** Sotto i dieci gradi ci sono i tetti e la
      foschia, che si mangia due magnitudini;
    * **non sono nel bagliore del Sole.** E' il caso di Mercurio quasi sempre,
      e di Venere quando passa dietro o davanti.

    La Luna non e' in questo elenco: e' talmente evidente che non ha bisogno
    di essere annunciata, e quando c'e' cancella tutto il resto. Sta a parte,
    con la sua fase.
    """
    quando = quando or datetime.now(timezone.utc)
    sole = altezza_sole(quando, lat, lon)
    fuori = []
    for nome in PIANETI:
        vista = dove(nome, quando, lat, lon)
        minima = (ALTEZZA_MINIMA_MERCURIO if nome == "mercurio"
                  else altezza_minima)
        if vista["altezza"] < minima:
            continue
        # Mercurio si vede solo nel crepuscolo: chiedergli il buio pieno
        # vorrebbe dire non vederlo mai, perche' quando il cielo e' nero lui e'
        # gia' tramontato.
        buio_richiesto = (CREPUSCOLO_CIVILE if nome in ("venere", "mercurio")
                          else CREPUSCOLO_NAUTICO)
        if sole > buio_richiesto:
            continue
        if vista["elongazione"] < 12.0:
            continue
        vista["colore"] = COLORI[nome]
        fuori.append(vista)
    fuori.sort(key=lambda v: (v["magnitudine"] if v["magnitudine"] is not None
                              else 99.0))
    return fuori


def riepilogo(quando=None, lat=0.0, lon=0.0):
    """Tutto quello che serve alla finestra del cielo, in un dizionario solo."""
    quando = quando or datetime.now(timezone.utc)
    elenco = visibili(quando, lat, lon)
    for vista in elenco:
        tramonto = prossimo_tramonto(vista["nome"], quando, lat, lon, ore=18)
        vista["tramonta"] = tramonto.isoformat() if tramonto else None
    luna = fase_luna(quando)
    vista_luna = dove("luna", quando, lat, lon)
    luna["altezza"] = vista_luna["altezza"]
    luna["azimut"] = vista_luna["azimut"]
    luna["sopra"] = vista_luna["altezza"] > 0
    return {
        "quando": quando.isoformat(),
        "altezza_sole": altezza_sole(quando, lat, lon),
        "pianeti": elenco,
        "luna": luna,
    }
