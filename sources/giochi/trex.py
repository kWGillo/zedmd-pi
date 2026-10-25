# -*- coding: utf-8 -*-
"""T-Rex: un dinosauro che corre, salta i cactus e si abbassa sotto gli
pterodattili, sempre piu' veloce.

Il nome e il disegno
--------------------
Il gioco del browser senza rete ha un dinosauro suo, disegnato da altri, e
resta loro. Lo schema -- una corsa infinita, un tasto per saltare, uno per
abbassarsi, la velocita' che cresce -- non e' di nessuno. Questo T-Rex e'
disegnato qui: piu' tozzo, con le creste arancio sulla schiena e la pancia
chiara, a colori.

Il pannello 4:1 e' fatto per questo gioco
-----------------------------------------
Una corsa orizzontale vuole spazio davanti per vedere arrivare gli ostacoli:
256 pixel di pista sono quasi tre secondi di anticipo alla velocita' di
partenza. Il tabellone sta in una riga in alto, come in Mine vaganti, e la
pista prende tutto il resto.

Niente campiture
----------------
Il cielo e' **nero**: e' la lezione di Squadriglia, un'area grande di colore
basso sul pannello mostra le righe del refresh. Il giorno e la notte non si
fanno invertendo i colori come nell'originale, ma cambiando la tavolozza: di
notte escono la luna e le stelle, e tutto si fa piu' freddo.

Il gioco
--------
* **Fuoco** (o su, o cerchio) salta. Tenendolo premuto il salto e' piu' alto.
* **Giu'** abbassa il dinosauro, per passare sotto gli pterodattili; in aria
  lo fa ricadere piu' in fretta.
* Una vita sola, come nell'originale. Si fa punteggio correndo; ogni 100
  punti un segnale, e da 300 arrivano gli pterodattili, a tre quote diverse.
"""

import random

from PIL import Image

from .base import ALTEZZA as ALTEZZA_BASE
from .base import LARGHEZZA as LARGHEZZA_BASE
from .base import STRISCIA, Gioco, centra, imposta_tela, scrivi

# ------------------------------------------------------------------ la pista

CIMA = 7                        # sopra, il tabellone
SUOLO = 58                      # la riga della pista: i piedi stanno qui sopra
X_DINO = 18                     # il dinosauro non si muove: e' il mondo che scorre

# La corsa
VELOCITA_INIZIALE = 110.0       # pixel al secondo: 2,3 s per attraversare il pannello
VELOCITA_MASSIMA = 260.0
ACCELERAZIONE = 2.2             # pixel al secondo, ogni secondo
PASSI_PER_PUNTO = 14.0          # un punto ogni quattordici pixel: circa otto al secondo in partenza

# Il salto
SPINTA_SALTO = 150.0            # pixel al secondo verso l'alto
GRAVITA = 560.0
GRAVITA_TENUTO = 300.0          # col tasto tenuto, mentre sale: salto piu' alto
TENUTA_MAX = 0.22               # per quanto il tasto tenuto conta
GRAVITA_PICCHIATA = 1500.0      # giu' in aria: si ricade subito

# Gli ostacoli
PTERODATTILI_DA = 300           # punti da cui compaiono
NOTTE_OGNI = 700                # ogni tanti punti cambia fra giorno e notte
DURATA_NOTTE = 250              # e la notte dura tanti punti
SEGNALE_OGNI = 100
LIVELLO_OGNI = 500              # "LIV" sul tabellone: un gradino ogni tanti punti
RIPARTENZA = 0.6                # a partita finita, fuoco non vale prima di cosi'

ORDINE = ("persa", "punto", "salto")
SUONI_PER_FRAME = 2
MUSICA = "trex_musica"

# ------------------------------------------------------------------ i colori

GIORNO = {
    "G": (70, 210, 110), "D": (30, 130, 70), "L": (170, 240, 150),
    "S": (255, 150, 40), "W": (255, 255, 255), "X": (255, 60, 60),
    "cactus": (150, 200, 40), "cactus_scuro": (80, 120, 20),
    "ptero": (220, 110, 170), "ptero_scuro": (140, 60, 110),
    "suolo": (130, 95, 50), "sasso": (90, 70, 40),
    "nuvola": (70, 80, 95), "hud": (150, 150, 165), "titolo": (70, 210, 110),
    "record": (90, 150, 220),
}
NOTTE = dict(GIORNO)
NOTTE.update({
    "G": (60, 170, 150), "D": (25, 100, 90), "L": (140, 210, 200),
    "cactus": (90, 160, 130), "cactus_scuro": (40, 90, 70),
    "ptero": (170, 120, 220), "ptero_scuro": (100, 70, 150),
    "suolo": (70, 80, 120), "sasso": (45, 50, 80),
    "nuvola": (45, 50, 80),
})
COLORE_LUNA = (230, 230, 190)
COLORE_STELLA = (120, 120, 150)
COLORE_FINE = (255, 60, 60)

# ------------------------------------------------------------------ gli sprite
#
# Una lettera per colore della tavolozza, il punto e' trasparente. Disegnati
# per il pannello, pixel per pixel: nessuno e' ricavato da quello del browser.

_TESTA = (
    "..........GGGGGG..",
    ".........GGGGGGGG.",
    ".........GGWKGGGGG",
    "....S....GGGGGGGGG",
    "...SGS...GGGGGGDDD",
    "..SGGGS..GGGGG....",
    ".SGGGGGGGGGGGGGG..",
    "GGGGGGGGGGGGG..D..",
    ".GGGGGGGGLLGG.....",
    "..GGGGGGLLLGGD....",
    "...GGGGGLLLG......",
    "....GGGGGGGG......",
)
DINO_CORRE = (
    _TESTA + (".....GG...GG......",
              ".....G......G.....",
              ".....GG...........",),
    _TESTA + (".....GG...GG......",
              "......G....G......",
              "...........GG.....",),
)
DINO_FERMO = _TESTA + (".....GG...GG......",
                       ".....G.....G......",
                       ".....GG....GG.....",)
DINO_MORTO = tuple(r.replace("WK", "XX") for r in DINO_FERMO)
# Abbassato: lungo e basso, la testa avanti, le creste piatte.
DINO_GIU = (
    (".................GGGGG..",
     "..S.S.S.........GGWKGGG.",
     ".SGSGSGSGGGGGGGGGGGGGGGG",
     "GGGGGGGGGGGGGGGGGGGGGDDD",
     ".GGGGGGGGLLLLGGGGGGG....",
     "..GGGGGGGLLLLGGGD.......",
     "...GGGGGGGGGGGG.........",
     "....GG....GG............",
     "....G......G............",
     "....GG..................",),
    (".................GGGGG..",
     "..S.S.S.........GGWKGGG.",
     ".SGSGSGSGGGGGGGGGGGGGGGG",
     "GGGGGGGGGGGGGGGGGGGGGDDD",
     ".GGGGGGGGLLLLGGGGGGG....",
     "..GGGGGGGLLLLGGGD.......",
     "...GGGGGGGGGGGG.........",
     "....GG....GG............",
     ".....G.....G............",
     "...........GG...........",),
)

# I cactus: due taglie. C e' il colore pieno, c quello scuro dei bordi.
CACTUS_PICCOLO = (
    "..C..",
    "..C.C",
    "C.C.C",
    "C.CCc",
    "CcC..",
    "..C..",
    "..C..",
    "..C..",
    "..c..",
    "..c..",
)
CACTUS_GRANDE = (
    "...C...",
    "..CCc..",
    "..CCc.C",
    "C.CCc.C",
    "C.CCc.C",
    "C.CCc.C",
    "CcCCcCc",
    ".cCCc..",
    "..CCc..",
    "..CCc..",
    "..CCc..",
    "..CCc..",
    "..CCc..",
    "..cCc..",
    "..cc...",
)
# Lo pterodattilo, due battiti d'ala. P il corpo, p l'ala scura, W l'occhio.
PTERO = (
    ("....p........",
     "....pp.......",
     "..P.ppp......",
     ".PWPpppp.....",
     "PPPPPPPPPPPP.",
     "......PPPPPPP",
     ".......PPP...",),
    ("..P..........",
     ".PWP.........",
     "PPPPPPPPPPPP.",
     "....ppPPPPPPP",
     "....ppp......",
     "....pp.......",
     "....p........",),
)
# Le tre quote degli pterodattili, come distanza dal suolo della loro base:
# bassa (si salta), media (ci si abbassa, o si salta alto), alta (passa sopra).
QUOTE_PTERO = (3, 13, 24)

NUVOLA = (
    "...xxxx....",
    ".xx....xx..",
    "x........xx",
    "xxxxxxxxxxx",
)


def _pixel(sprite):
    """Le coordinate dei pixel accesi di uno sprite, con la loro lettera."""
    fuori = []
    for y, riga in enumerate(sprite):
        for x, c in enumerate(riga):
            if c != ".":
                fuori.append((x, y, c))
    return tuple(fuori)


def _maschera(sprite):
    return frozenset((x, y) for x, y, _c in _pixel(sprite))


P_CORRE = tuple(_pixel(s) for s in DINO_CORRE)
P_FERMO = _pixel(DINO_FERMO)
P_MORTO = _pixel(DINO_MORTO)
P_GIU = tuple(_pixel(s) for s in DINO_GIU)
P_CACTUS = {"piccolo": _pixel(CACTUS_PICCOLO), "grande": _pixel(CACTUS_GRANDE)}
P_PTERO = tuple(_pixel(s) for s in PTERO)
P_NUVOLA = _pixel(NUVOLA)

M_CORRE = tuple(_maschera(s) for s in DINO_CORRE)
M_GIU = tuple(_maschera(s) for s in DINO_GIU)
M_CACTUS = {"piccolo": _maschera(CACTUS_PICCOLO), "grande": _maschera(CACTUS_GRANDE)}
M_PTERO = tuple(_maschera(s) for s in PTERO)

ALTO_DINO = len(DINO_FERMO)
ALTO_GIU = len(DINO_GIU[0])
LARGO = {"piccolo": len(CACTUS_PICCOLO[0]), "grande": len(CACTUS_GRANDE[0])}
ALTO = {"piccolo": len(CACTUS_PICCOLO), "grande": len(CACTUS_GRANDE)}
LARGO_PTERO = len(PTERO[0][0])
ALTO_PTERO = len(PTERO[0])


class Ostacolo(object):
    __slots__ = ("tipo", "x", "y", "larghezza", "quanti", "quota", "ali")

    def __init__(self, tipo, x, quanti=1, quota=0, suolo=SUOLO):
        self.tipo = tipo
        self.x = float(x)
        self.quanti = quanti
        self.quota = quota
        self.ali = 0.0
        if tipo == "ptero":
            self.larghezza = LARGO_PTERO
            self.y = suolo - quota - ALTO_PTERO
        else:
            self.larghezza = quanti * (LARGO[tipo] + 1) - 1
            self.y = suolo - ALTO[tipo]

    def pezzi(self):
        """(maschera, pixel, x, y) di ogni sagoma dell'ostacolo."""
        if self.tipo == "ptero":
            f = int(self.ali * 6) % 2
            return [(M_PTERO[f], P_PTERO[f], int(self.x), int(self.y))]
        passo = LARGO[self.tipo] + 1
        return [(M_CACTUS[self.tipo], P_CACTUS[self.tipo],
                 int(self.x) + k * passo, int(self.y)) for k in range(self.quanti)]


class TRex(Gioco):
    nome = "trex"
    etichetta = "T-Rex"
    colore_hud = GIORNO["titolo"]
    MUSICA = MUSICA
    TELA_LIBERA = True

    COMANDI = ("su", "giu", "fuoco", "avvia", "esci")

    # Oltre questo la finestra sul mondo diventa troppo stretta: a zoom tre
    # un cactus attraversa lo schermo in otto decimi di secondo, e non si fa
    # piu' in tempo a saltarlo. Due e' la misura scelta: figure grandi il
    # doppio, poco piu' di un secondo per reagire invece di due e mezzo.
    ZOOM_MAX = 2

    def _misura(self):
        """Il mondo resta in unita' di pannello; cambia quanto se ne vede.

        E' la scelta che rende questa conversione sicura: la fisica, le
        velocita', i salti, le maschere di collisione restano **identici**
        -- il mondo e' sempre quello alto 64 e largo 256 unita'. Quello che
        cambia e' lo zoom con cui lo si disegna, e di conseguenza quante
        unita' di mondo ci stanno nella tela.

        A zoom due, su 256 colonne, la finestra e' larga 128 unita' invece
        di 256: il dinosauro e i cactus sono grandi il doppio, e si vedono
        arrivare per meta' tempo. E' lo scambio che il 4:3 impone a un gioco
        che scorre di lato, e il cielo in piu' resta cielo.
        """
        self.z = max(1, min(self.ZOOM_MAX, self.alto // ALTEZZA_BASE))
        self.largo_u = max(64, self.largo // self.z)
        self.alto_u = max(32, self.alto // self.z)
        # La striscia del tabellone si misura in pixel di tela, non in
        # unita': il font non si ingrandisce con lo zoom.
        self.cima_u = max(1, -(-STRISCIA // self.z))
        self.suolo_u = self.alto_u - 6

    # ---------------------------------------------------------------- partita

    def avvia_partita(self, seme=None):
        if seme is not None or not hasattr(self, "_rnd"):
            self._rnd = random.Random(seme)
        self.punteggio = 0
        self.vite = 1
        self.livello = 1
        self.finita = False
        self.iniziata = False
        self._misura()
        self.velocita = VELOCITA_INIZIALE
        self.strada = 0.0
        self.y = 0.0                 # altezza dei piedi sopra il suolo
        self.vy = 0.0
        self.in_aria = False
        self.giu = False
        self._tenuta = 0.0
        self._passo_zampe = 0.0
        self.ostacoli = []
        self._prossimo = 90.0        # pixel di strada prima del primo ostacolo
        cielo = self.suolo_u - self.cima_u
        self.nuvole = [[self._rnd.uniform(0, self.largo_u),
                        self._rnd.uniform(self.cima_u + cielo * 0.06,
                                          self.cima_u + cielo * 0.41)]
                       for _ in range(3)]
        self.sassi = [[self._rnd.uniform(0, self.largo_u),
                       self._rnd.randint(1, 4)]
                      for _ in range(18)]
        self.stelle = [(self._rnd.randint(0, self.largo_u - 1),
                        self._rnd.randint(self.cima_u + 1,
                                          self.cima_u + int(cielo * 0.57)))
                       for _ in range(22)]
        self._segnale = 0.0          # il lampeggio del punteggio ogni 100
        self._morto_da = 0.0
        self._eventi = []
        self.suoni_del_frame = ()
        self._prima = set()

    def notte(self):
        """Di notte da NOTTE_OGNI punti, per DURATA_NOTTE punti."""
        if self.punteggio < NOTTE_OGNI:
            return False
        return (self.punteggio % NOTTE_OGNI) < DURATA_NOTTE

    def musica_di_adesso(self):
        return self.MUSICA if (self.iniziata and not self.finita) else None

    # ----------------------------------------------------------------- suono

    def _segna(self, nome):
        self._eventi.append(nome)

    def _emetti(self):
        eventi, self._eventi = self._eventi, []
        scelti = [n for n in ORDINE if n in eventi][:SUONI_PER_FRAME]
        self.suoni_del_frame = tuple(scelti)
        for nome in scelti:
            self.suona(nome)

    # ----------------------------------------------------------------- passo

    def passo(self, dt, tasti):
        self._eventi = []
        tasti = set(tasti)
        premuti_ora = tasti - self._prima
        self._prima = tasti
        try:
            self._fisica(dt, tasti, premuti_ora)
        finally:
            self._emetti()

    @staticmethod
    def _salta_tasti(tasti):
        return bool(tasti & {"fuoco", "su"})

    def _fisica(self, dt, tasti, premuti_ora):
        if self.finita:
            self._morto_da += dt
            if self._salta_tasti(premuti_ora) and self._morto_da >= RIPARTENZA:
                self.avvia_partita()
                self.iniziata = True
                self._salta()
            return
        if not self.iniziata:
            if self._salta_tasti(premuti_ora):
                self.iniziata = True
                self._salta()
            return

        self._segnale = max(0.0, self._segnale - dt)
        self._muovi_dino(dt, tasti, premuti_ora)

        self.velocita = min(VELOCITA_MASSIMA, self.velocita + ACCELERAZIONE * dt)
        avanti = self.velocita * dt
        self.strada += avanti
        prima = self.punteggio
        self.punteggio = int(self.strada / PASSI_PER_PUNTO)
        if self.punteggio // SEGNALE_OGNI > prima // SEGNALE_OGNI:
            self._segnale = 1.0
            self._segna("punto")
        self.livello = 1 + self.punteggio // LIVELLO_OGNI

        self._scorri(avanti, dt)
        self._genera(avanti)
        if self._urto():
            self._perdi()
        self._aggiorna_record()

    def _salta(self):
        if self.in_aria:
            return
        self.in_aria = True
        self.giu = False
        self.vy = SPINTA_SALTO
        self._tenuta = 0.0
        self._segna("salto")

    def _muovi_dino(self, dt, tasti, premuti_ora):
        salta = self._salta_tasti(tasti)
        if not self.in_aria:
            self.giu = "giu" in tasti
            # Tenendo premuto si risalta appena toccato terra, come
            # nell'originale: chi tiene il tasto vuole saltare.
            if salta and not self.giu:
                self._salta()
                return
            self._passo_zampe += dt * (self.velocita / 110.0)
            return
        # In aria: il tasto tenuto allunga la salita, giu' fa ricadere.
        if "giu" in tasti:
            g = GRAVITA_PICCHIATA
        elif salta and self.vy > 0 and self._tenuta < TENUTA_MAX:
            g = GRAVITA_TENUTO
            self._tenuta += dt
        else:
            g = GRAVITA
            self._tenuta = TENUTA_MAX      # lasciato, non si riprende piu'
        self.vy -= g * dt
        self.y += self.vy * dt
        if self.y <= 0:
            self.y = 0.0
            self.vy = 0.0
            self.in_aria = False
            self.giu = "giu" in tasti

    def _scorri(self, avanti, dt):
        for o in self.ostacoli:
            o.x -= avanti
            if o.tipo == "ptero":
                # Gli pterodattili volano: vanno un po' piu' svelti della pista.
                o.x -= 12.0 * dt
                o.ali += dt
        self.ostacoli = [o for o in self.ostacoli if o.x + o.larghezza > -2]
        for n in self.nuvole:
            n[0] -= avanti * 0.2
            if n[0] < -12:
                cielo = self.suolo_u - self.cima_u
                n[0] = self.largo_u + self._rnd.uniform(0, 60)
                n[1] = self._rnd.uniform(self.cima_u + cielo * 0.06,
                                         self.cima_u + cielo * 0.41)
        for s in self.sassi:
            s[0] -= avanti
            if s[0] < 0:
                s[0] += self.largo_u + self._rnd.uniform(0, 8)
                s[1] = self._rnd.randint(1, 4)

    def _genera(self, avanti):
        self._prossimo -= avanti
        if self._prossimo > 0:
            return
        x = self.largo_u + 2
        if self.punteggio >= PTERODATTILI_DA and self._rnd.random() < 0.25:
            o = Ostacolo("ptero", x, quota=self._rnd.choice(QUOTE_PTERO),
                         suolo=self.suolo_u)
        else:
            # Da una certa velocita' i cactus grandi, e i gruppi fino a tre.
            grande = self.velocita > 135 and self._rnd.random() < 0.45
            tipo = "grande" if grande else "piccolo"
            massimo = 1 if self.velocita < 125 else (2 if grande else 3)
            o = Ostacolo(tipo, x, quanti=self._rnd.randint(1, massimo),
                         suolo=self.suolo_u)
        self.ostacoli.append(o)
        # Lo spazio al prossimo: tempo di reazione piu' la lunghezza del
        # salto, che a velocita' alta si fa piu' lungo in pixel.
        salto = self.velocita * 0.62
        self._prossimo = o.larghezza + salto + self.velocita * self._rnd.uniform(0.35, 1.1)

    # ------------------------------------------------------------------ urti

    def sagoma(self):
        """(maschera, pixel, x, y) del dinosauro adesso."""
        f = int(self._passo_zampe * 8) % 2
        if self.giu and not self.in_aria:
            return M_GIU[f], P_GIU[f], X_DINO, self.suolo_u - ALTO_GIU
        y = self.suolo_u - ALTO_DINO - int(round(self.y))
        if self.in_aria:
            return M_CORRE[0], P_FERMO, X_DINO, y
        return M_CORRE[f], P_CORRE[f], X_DINO, y

    def _urto(self):
        mdino, _p, dx, dy = self.sagoma()
        for o in self.ostacoli:
            if o.x > X_DINO + 26 or o.x + o.larghezza < X_DINO - 2:
                continue
            for mask, _pp, ox, oy in o.pezzi():
                sx, sy = ox - dx, oy - dy
                for (x, y) in mask:
                    if (x + sx, y + sy) in mdino:
                        return True
        return False

    def _perdi(self):
        self.finita = True
        self._morto_da = 0.0
        self._segna("persa")
        self._aggiorna_record()

    # -------------------------------------------------------------- disegno

    def disegna_campo(self, img, px):          # pragma: no cover - non usata
        pass

    def _metti(self, px, pixel, x0, y0, tavolozza, colori=None):
        """Uno sprite dal mondo alla tela: ogni unita' diventa un quadrato.

        E' l'unico posto in cui lo zoom esiste. Tutto il resto del gioco --
        la fisica, le maschere, le velocita' -- vive in unita' di mondo e
        non sa che la tela sia grande il doppio.
        """
        z = self.z
        for x, y, c in pixel:
            colore = (colori or {}).get(c) or tavolozza.get(c)
            if not colore:
                continue
            for dy in range(z):
                yy = (y0 + y) * z + dy
                if not (STRISCIA <= yy < self.alto):
                    continue
                for dx in range(z):
                    xx = (x0 + x) * z + dx
                    if 0 <= xx < self.largo:
                        px[xx, yy] = colore

    def _punto(self, px, x, y, colore):
        """Un pixel di mondo, ingrandito come gli sprite."""
        z = self.z
        for dy in range(z):
            yy = y * z + dy
            if not (STRISCIA <= yy < self.alto):
                continue
            for dx in range(z):
                xx = x * z + dx
                if 0 <= xx < self.largo:
                    px[xx, yy] = colore

    def disegna(self):
        img = Image.new("RGB", (self.largo, self.alto), (0, 0, 0))
        imposta_tela(self.largo, self.alto, (0, 0, self.largo, self.alto))
        px = img.load()
        t = NOTTE if self.notte() else GIORNO

        if self.notte():
            for x, y in self.stelle:
                self._punto(px, x, y, COLORE_STELLA)
            # La luna: una falce di contorno, in alto a destra.
            cielo = self.suolo_u - self.cima_u
            cx = int(self.largo_u * 0.867)
            cy = int(self.cima_u + cielo * 0.18)
            for yy in range(-5, 6):
                for xx in range(-5, 6):
                    d1 = xx * xx + yy * yy
                    d2 = (xx - 3) ** 2 + (yy + 1) ** 2
                    if 16 <= d1 <= 26 and d2 > 16:
                        self._punto(px, cx + xx, cy + yy, COLORE_LUNA)
        for n in self.nuvole:
            self._metti(px, P_NUVOLA, int(n[0]), int(n[1]), {"x": t["nuvola"]})

        # La pista: una riga, e i sassi sotto che scorrono.
        for x in range(self.largo_u):
            self._punto(px, x, self.suolo_u, t["suolo"])
        for sx, sy in self.sassi:
            xx = int(sx)
            if 0 <= xx < self.largo_u and self.suolo_u + sy < self.alto_u:
                self._punto(px, xx, self.suolo_u + sy, t["sasso"])

        for o in self.ostacoli:
            for _m, pixel, ox, oy in o.pezzi():
                if o.tipo == "ptero":
                    self._metti(px, pixel, ox, oy, t,
                                {"P": t["ptero"], "p": t["ptero_scuro"], "W": (255, 255, 255)})
                else:
                    self._metti(px, pixel, ox, oy, t,
                                {"C": t["cactus"], "c": t["cactus_scuro"]})

        if self.finita:
            self._metti(px, P_MORTO, X_DINO,
                        self.suolo_u - ALTO_DINO - int(round(self.y)), t)
        elif not self.iniziata:
            # In attesa: fermo sulla pista.
            self._metti(px, P_FERMO, X_DINO, self.suolo_u - ALTO_DINO, t)
        else:
            _m, pixel, x, y = self.sagoma()
            self._metti(px, pixel, x, y, t)

        self._disegna_hud(px, t)
        return img

    def _disegna_hud(self, px, t):
        lampeggia = self._segnale > 0 and int(self._segnale * 8) % 2 == 0
        if not lampeggia:
            scrivi(px, "%06d" % self.punteggio, 1, 1, t["titolo"])
        scrivi(px, "HI %06d" % self.record(), 32, 1, t["record"])
        scrivi(px, "LIV %d" % self.livello, 76, 1, t["hud"])
        scrivi(px, "T-REX", self.largo - 20, 1, t["hud"])
        if not self.iniziata and not self.finita:
            centra(px, "T-REX", self.alto * 24 // 64, t["titolo"], larghezza=self.largo)
            centra(px, "FUOCO PER PARTIRE", self.alto * 34 // 64, t["hud"], larghezza=self.largo)
        if self.finita:
            centra(px, "GAME OVER", self.alto * 24 // 64, COLORE_FINE, larghezza=self.largo)
            if self._morto_da >= RIPARTENZA:
                centra(px, "FUOCO PER RIGIOCARE", self.alto * 34 // 64, t["hud"], larghezza=self.largo)
