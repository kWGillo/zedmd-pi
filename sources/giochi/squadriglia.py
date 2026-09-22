# -*- coding: utf-8 -*-
"""Squadriglia: uno sparatutto aereo in stile 1942, girato in orizzontale.

Il nome
-------
1942 e' di Capcom, nome e gioco. Il tema -- un caccia della Seconda guerra
mondiale contro squadriglie nemiche, sopra il mare -- non e' di nessuno.
Questo e' Squadriglia.

Perche' in orizzontale
----------------------
1942 scorre in verticale: l'aereo sta in basso e sale. Sul pannello
resterebbero 64 righe di cielo, e un nemico comparirebbe e sarebbe addosso
nello stesso istante. Girato, i 256 pixel diventano profondita': tu voli verso
destra dal lato sinistro, i nemici entrano da destra, e fra le due cose passano
tre secondi buoni. E' lo stesso ragionamento che ha messo Pongo di traverso.

Cosa viene dall'originale
-------------------------
* **Le squadriglie in formazione.** I nemici arrivano a gruppi e disegnano
  una traiettoria: in fila, a onda, in picchiata verso di te, o con un giro
  della morte prima di passare.
* **Il looping.** Con il tasto speciale l'aereo fa una capriola ed e'
  intoccabile per un secondo. Tre per livello: e' la mossa che salva la
  partita, e se la sprechi non c'e' piu'.
* **Il POW.** Una squadriglia rossa abbattuta **per intero** lascia un
  potenziamento: prima il doppio colpo, poi due aerei di scorta che sparano
  con te e ti fanno da scudo. Se ti abbattono li perdi.
* **Il bombardiere** a fine livello: largo, lento, e da colpire molte volte
  mentre ti spara a ventaglio.

Il tabellone sta in una riga in alto, e il resto e' cielo: gli altri giochi
tengono la striscia di destra, ma qui e' proprio da destra che entrano i
nemici.
"""

import math
import random

from .base import ALTEZZA, LARGHEZZA, Gioco, centra, scrivi

# ------------------------------------------------------------------ il campo

CIMA = 8                        # sopra c'e' il tabellone
ALTEZZA_CAMPO = ALTEZZA - CIMA

# Il tuo aereo, 9x5, che guarda a destra. Due pose per l'elica.
AEREO = (
    (0b011000000, 0b001100110, 0b111111111, 0b001100110, 0b011000000),
    (0b011000000, 0b001100100, 0b111111111, 0b001100010, 0b011000000),
)
# Durante il looping: l'aereo visto di taglio, poi capovolto, poi di taglio.
AEREO_LOOP = (
    (0b000010000, 0b000111000, 0b111111111, 0b000111000, 0b000010000),
    (0b000000011, 0b011001100, 0b111111111, 0b011001100, 0b000000011),
)
LARGO_AEREO = 9
ALTO_AEREO = 5

# La scorta: piccola, 5x3.
SCORTA = (0b01100, 0b11111, 0b01100)

# I caccia nemici, 7x5, che guardano a sinistra.
CACCIA = (0b0000110, 0b0110100, 0b1111111, 0b0110100, 0b0000110)
LARGO_CACCIA = 7
ALTO_CACCIA = 5

# Il bombardiere, 36x12, disegnato a righe.
BOMBARDIERE = (
    "..........##..........##............",
    ".........####........####...........",
    "......##########################....",
    "..####################################",
    "######################################",
    "..#################################.",
    "......##########################....",
    ".........####........####...........",
    "..........##..........##............",
)
LARGO_BOMBARDIERE = max(len(r) for r in BOMBARDIERE)
ALTO_BOMBARDIERE = len(BOMBARDIERE)

COLORE_TU = (255, 140, 26)
COLORE_SCORTA = (255, 190, 90)
COLORE_CACCIA = (150, 170, 150)
COLORE_ROSSO = (255, 60, 50)
COLORE_BOMBARDIERE = (120, 130, 110)
COLORE_COLPITO = (255, 255, 255)
COLORE_COLPO = (255, 240, 120)
COLORE_NEMICO = (255, 90, 200)       # i proiettili nemici: rosa, non si
                                     # confondono ne' col mare ne' coi tuoi
# Il mare e' **nero**, e non per gusto. Il blu della 10.4 (0,14,40) sul
# pannello vero mostrava le righe orizzontali del refresh: su un'area grande
# e uniforme, un colore basso ma non nullo e' esattamente dove quelle righe si
# vedono. Il quasi nero della 10.6 (0,4,14) le mostrava ancora. Il nero vero
# e' LED spenti: niente da rinfrescare, niente righe. Il mare resta nelle
# onde e nelle isole che scorrono.
COLORE_MARE = (0, 0, 0)
COLORE_ONDA = (10, 28, 56)
COLORE_ISOLA = (30, 90, 40)
COLORE_SABBIA = (120, 110, 60)
COLORE_POW = (255, 230, 60)
COLORE_HUD = (150, 150, 165)

# ------------------------------------------------------------------ le regole

VELOCITA = 72.0                 # il tuo aereo, pixel al secondo
X_MASSIMA = 120                 # oltre meta' pannello non si va: e' il cielo loro
CADENZA = 0.14                  # secondi fra due colpi, con il tasto tenuto
VELOCITA_COLPO = 230.0
COLPI_MASSIMI = 6

LOOP_DURATA = 1.0
LOOP_PER_LIVELLO = 3
INVULNERABILE_RINASCITA = 2.0

VITE = 3
DURATA_LIVELLO = 70.0           # secondi di squadriglie prima del bombardiere
PUNTI_CACCIA = 100
PUNTI_ROSSO = 150
PUNTI_POW_EXTRA = 1000
PUNTI_BOMBARDIERE = 5000

SCORRIMENTO = 18.0              # il mare, pixel al secondo

ORDINE = ("persa", "livello", "colpito", "mangia3", "lancio", "sparo", "muro")
SUONI_PER_FRAME = 2


def _bit(riga, larghezza, colonna):
    return (riga >> (larghezza - 1 - colonna)) & 1


class Caccia(object):
    """Un aereo nemico. La traiettoria dipende da `tipo` e dall'eta'."""

    def __init__(self, tipo, y0, velocita, ritardo, squadriglia, rosso, rnd):
        self.tipo = tipo
        self.y0 = y0
        self.v = velocita
        self.eta = -ritardo              # negativo: non e' ancora entrato
        self.squadriglia = squadriglia
        self.rosso = rosso
        self.x = LARGHEZZA + 2.0
        self.y = y0
        self.vivo = True
        self._bersaglio = None
        self._fase = rnd.uniform(0, math.pi)
        self._spara_fra = rnd.uniform(1.0, 3.0)

    def entrato(self):
        return self.eta >= 0

    def muovi(self, dt, y_giocatore):
        self.eta += dt
        if self.eta < 0:
            return
        a = self.eta
        x_ingresso = LARGHEZZA + 2.0
        if self.tipo == "fila":
            self.x = x_ingresso - self.v * a
            self.y = self.y0
        elif self.tipo == "onda":
            self.x = x_ingresso - self.v * a
            self.y = self.y0 + 9.0 * math.sin(a * 3.0 + self._fase)
        elif self.tipo == "picchiata":
            self.x = x_ingresso - self.v * a
            if self.x < 190 and self._bersaglio is None:
                self._bersaglio = y_giocatore
            if self._bersaglio is not None:
                passo = 30.0 * dt
                d = self._bersaglio - self.y
                self.y += max(-passo, min(passo, d))
        else:                                   # "giro"
            centro_x, raggio = 150.0, 11.0
            arrivo = (x_ingresso - (centro_x + raggio)) / self.v
            giro = 2.0 * math.pi * raggio / self.v
            if a < arrivo:
                self.x = x_ingresso - self.v * a
                self.y = self.y0
            elif a < arrivo + giro:
                angolo = (a - arrivo) / giro * 2.0 * math.pi
                self.x = centro_x + raggio * math.cos(angolo)
                self.y = self.y0 - raggio * math.sin(angolo)
            else:
                self.x = centro_x + raggio - self.v * (a - arrivo - giro)
                self.y = self.y0
        self.y = max(float(CIMA), min(float(ALTEZZA - ALTO_CACCIA), self.y))

    def fuori(self):
        return self.entrato() and self.x < -LARGO_CACCIA - 2


class Squadriglia(Gioco):
    nome = "squadriglia"
    etichetta = "Squadriglia"
    MUSICA = "squadriglia_musica"

    def musica_di_adesso(self):
        return self.MUSICA if (self.iniziata and not self.finita) else None
    colore_hud = COLORE_TU

    COMANDI = ("su", "giu", "sinistra", "destra", "fuoco", "speciale",
               "avvia", "esci")

    # ---------------------------------------------------------------- partita

    def avvia_partita(self, seme=None):
        if seme is not None or not hasattr(self, "_rnd"):
            self._rnd = random.Random(seme)
        self.punteggio = 0
        self.vite = VITE
        self.livello = 1
        self.finita = False
        self.iniziata = False
        self.potenza = 0                 # 0 niente, 1 doppio colpo, 2 scorta
        self._eventi = []
        self.suoni_del_frame = ()
        self._prima = set()
        self._onde = [(self._rnd.uniform(0, LARGHEZZA),
                       self._rnd.randint(CIMA + 1, ALTEZZA - 2))
                      for _ in range(26)]
        self._isole = []
        self._da_isola = self._rnd.uniform(4, 10)
        self._nuovo_livello()

    def _nuovo_livello(self):
        self.x = 12.0
        self.y = CIMA + (ALTEZZA_CAMPO - ALTO_AEREO) / 2.0
        self.loop = LOOP_PER_LIVELLO
        self._in_loop = 0.0
        self._protetto = INVULNERABILE_RINASCITA
        self._morto = 0.0
        self._esplosioni = []
        self.colpi = []
        self.bombe = []
        self.nemici = []
        self.pow = None
        self.bombardiere = None
        self._tempo = 0.0
        self._da_squadriglia = 1.5
        self._squadriglie = 0
        self._conti = {}             # squadriglia -> [totale, abbattuti, fuggiti, rossa]
        self._da_colpo = 0.0
        self._elica = 0.0

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
        premuti_ora = set(tasti) - self._prima
        self._prima = set(tasti)
        try:
            self._fisica(dt, tasti, premuti_ora)
        finally:
            self._emetti()

    def _fisica(self, dt, tasti, premuti_ora):
        self._scorri_mare(dt)
        if self.finita:
            if "fuoco" in premuti_ora:
                self.avvia_partita()
                self.iniziata = True
            return
        if not self.iniziata:
            if "fuoco" in premuti_ora:
                self.iniziata = True
            return

        self._elica += dt
        self._tempo += dt
        self._esplosioni = [[x, y, t - dt] for x, y, t in self._esplosioni
                            if t - dt > 0]

        if self._morto > 0:
            self._morto -= dt
            if self._morto <= 0:
                self._rinasci()
        else:
            self._muovi_tu(dt, tasti, premuti_ora)

        self._muovi_colpi(dt)
        self._muovi_nemici(dt)
        self._muovi_bombe(dt)
        self._muovi_pow(dt)
        self._genera(dt)
        self._urti()

    # ------------------------------------------------------------- il mare

    def _scorri_mare(self, dt):
        onde = []
        for x, y in self._onde:
            x -= SCORRIMENTO * dt
            if x < -3:
                x = LARGHEZZA + self._rnd.uniform(0, 20)
                y = self._rnd.randint(CIMA + 1, ALTEZZA - 2)
            onde.append((x, y))
        self._onde = onde
        self._isole = [[x - SCORRIMENTO * dt, y, l, a]
                       for x, y, l, a in self._isole if x + l > -2]
        self._da_isola -= dt
        if self._da_isola <= 0:
            self._da_isola = self._rnd.uniform(9, 18)
            larga = self._rnd.randint(12, 22)
            alta = self._rnd.randint(8, 13)
            self._isole.append([float(LARGHEZZA + 2),
                                self._rnd.randint(CIMA + 2, ALTEZZA - alta - 1),
                                larga, alta])

    # ------------------------------------------------------------- il tuo aereo

    def _muovi_tu(self, dt, tasti, premuti_ora):
        dx = (("destra" in tasti) - ("sinistra" in tasti))
        dy = (("giu" in tasti) - ("su" in tasti))
        if dx and dy:
            # In diagonale non si va piu' veloci: e' un aereo, non un cursore.
            dx *= 0.7071
            dy *= 0.7071
        self.x = max(1.0, min(float(X_MASSIMA), self.x + dx * VELOCITA * dt))
        self.y = max(float(CIMA), min(float(ALTEZZA - ALTO_AEREO),
                                      self.y + dy * VELOCITA * dt))

        if self._in_loop > 0:
            self._in_loop = max(0.0, self._in_loop - dt)
        elif "speciale" in premuti_ora and self.loop > 0:
            self.loop -= 1
            self._in_loop = LOOP_DURATA
            self._segna("lancio")
        if self._protetto > 0:
            self._protetto = max(0.0, self._protetto - dt)

        self._da_colpo -= dt
        if "fuoco" in premuti_ora:
            self._da_colpo = 0.0
        if "fuoco" in tasti and self._da_colpo <= 0 and self._in_loop <= 0:
            self._spara()
            self._da_colpo = CADENZA

    def _spara(self):
        if len(self.colpi) >= COLPI_MASSIMI:
            return
        naso_x = self.x + LARGO_AEREO
        centro_y = self.y + ALTO_AEREO // 2
        if self.potenza >= 1:
            self.colpi.append([naso_x, centro_y - 1])
            self.colpi.append([naso_x, centro_y + 1])
        else:
            self.colpi.append([naso_x, centro_y])
        if self.potenza >= 2:
            for sy in self._posizioni_scorta():
                self.colpi.append([self.x + 5, sy + 1])
        self._segna("sparo")

    def _posizioni_scorta(self):
        if self.potenza < 2:
            return []
        return [self.y - 5, self.y + ALTO_AEREO + 2]

    def intoccabile(self):
        return self._in_loop > 0 or self._protetto > 0 or self._morto > 0

    def _abbattuto(self):
        if self.intoccabile():
            return
        if self.potenza >= 2:
            # La scorta fa da scudo: si perde lei, non l'aereo.
            self.potenza = 1
            self._protetto = 1.0
            self._esplosioni.append([self.x, self.y - 5, 0.4])
            self._segna("colpito")
            return
        self._esplosioni.append([self.x + 3, self.y, 0.8])
        self.vite -= 1
        self.potenza = 0
        self._segna("persa")
        if self.vite <= 0:
            self.vite = 0
            self.finita = True
            return
        self._morto = 1.0

    def _rinasci(self):
        self.x = 12.0
        self.y = CIMA + (ALTEZZA_CAMPO - ALTO_AEREO) / 2.0
        self._protetto = INVULNERABILE_RINASCITA
        self.bombe = []

    # ------------------------------------------------------------- i colpi

    def _muovi_colpi(self, dt):
        self.colpi = [[x + VELOCITA_COLPO * dt, y] for x, y in self.colpi
                      if x + VELOCITA_COLPO * dt < LARGHEZZA]

    def _muovi_bombe(self, dt):
        rimaste = []
        for b in self.bombe:
            b[0] += b[2] * dt
            b[1] += b[3] * dt
            if -2 < b[0] < LARGHEZZA + 2 and CIMA - 2 < b[1] < ALTEZZA + 2:
                rimaste.append(b)
        self.bombe = rimaste

    def _spara_nemico(self, x, y, velocita=70.0):
        """Un colpo mirato verso di te, con un filo di imprecisione."""
        dx = (self.x + LARGO_AEREO / 2.0) - x
        dy = (self.y + ALTO_AEREO / 2.0) - y
        d = math.hypot(dx, dy) or 1.0
        angolo = math.atan2(dy, dx) + self._rnd.uniform(-0.12, 0.12)
        self.bombe.append([x, y, math.cos(angolo) * velocita,
                           math.sin(angolo) * velocita])

    # ------------------------------------------------------------- i nemici

    def _fattore(self):
        """Quanto si accelera a ogni livello."""
        return 1.0 + 0.12 * min(8, self.livello - 1)

    def _genera(self, dt):
        if self.bombardiere is not None:
            self._muovi_bombardiere(dt)
            return
        if self._tempo >= DURATA_LIVELLO:
            # Finite le squadriglie: quando il cielo e' vuoto, il bombardiere.
            if not self.nemici:
                self._arriva_bombardiere()
            return
        self._da_squadriglia -= dt
        if self._da_squadriglia > 0:
            return
        self._da_squadriglia = max(1.2, 2.6 - 0.15 * (self.livello - 1))
        self._squadriglie += 1
        rossa = self._squadriglie % 4 == 0
        tipo = self._rnd.choice(("fila", "onda", "picchiata", "giro"))
        quanti = 5 if tipo != "giro" else 4
        y0 = self._rnd.uniform(CIMA + 10, ALTEZZA - 14)
        v = self._rnd.uniform(55, 70) * self._fattore()
        chiave = self._squadriglie
        self._conti[chiave] = [quanti, 0, 0, rossa]
        for i in range(quanti):
            self.nemici.append(Caccia(tipo, y0, v, i * 0.22, chiave, rossa,
                                      self._rnd))

    def _muovi_nemici(self, dt):
        rimasti = []
        for n in self.nemici:
            n.muovi(dt, self.y)
            if n.fuori():
                self._conti[n.squadriglia][2] += 1
                continue
            if n.entrato() and 0 < n.x < LARGHEZZA - 10:
                n._spara_fra -= dt * self._fattore()
                if n._spara_fra <= 0:
                    n._spara_fra = self._rnd.uniform(2.5, 5.0)
                    if n.x > self.x + 20:
                        self._spara_nemico(n.x, n.y + 2)
            rimasti.append(n)
        self.nemici = rimasti

    def _arriva_bombardiere(self):
        self.bombardiere = {
            "x": float(LARGHEZZA + 2), "y": CIMA + 10.0,
            "vita": 30 + 10 * min(8, self.livello - 1),
            "t": 0.0, "da_sparo": 2.0, "lampo": 0.0,
        }

    def _muovi_bombardiere(self, dt):
        b = self.bombardiere
        b["t"] += dt
        b["lampo"] = max(0.0, b["lampo"] - dt)
        arrivo = LARGHEZZA - LARGO_BOMBARDIERE - 14
        if b["x"] > arrivo:
            b["x"] = max(float(arrivo), b["x"] - 30.0 * dt)
        meta = CIMA + (ALTEZZA_CAMPO - ALTO_BOMBARDIERE) / 2.0
        # Sale e scende, ma piano: i tuoi colpi ci mettono quasi un secondo ad
        # attraversare il pannello, e un bombardiere che in quel secondo si e'
        # spostato di piu' della sua altezza non si colpisce mai.
        b["y"] = meta + (ALTEZZA_CAMPO - ALTO_BOMBARDIERE) / 2.0 * 0.6 * \
            math.sin(b["t"] * 0.7)
        b["da_sparo"] -= dt * self._fattore()
        if b["da_sparo"] <= 0 and b["x"] <= arrivo + 1:
            b["da_sparo"] = 1.4
            # Il ventaglio: tre colpi, quello di mezzo mirato.
            bx, by = b["x"], b["y"] + ALTO_BOMBARDIERE / 2.0
            dx = (self.x + LARGO_AEREO / 2.0) - bx
            dy = (self.y + ALTO_AEREO / 2.0) - by
            base = math.atan2(dy, dx)
            for scarto in (-0.28, 0.0, 0.28):
                self.bombe.append([bx, by, math.cos(base + scarto) * 60.0,
                                   math.sin(base + scarto) * 60.0])

    # ------------------------------------------------------------- il POW

    def _muovi_pow(self, dt):
        if self.pow is None:
            return
        self.pow[0] -= 20.0 * dt
        self.pow[2] += dt
        if self.pow[0] < -6:
            self.pow = None

    def _prendi_pow(self):
        self.pow = None
        self._segna("mangia3")
        if self.potenza < 2:
            self.potenza += 1
        else:
            self.punteggio += PUNTI_POW_EXTRA
            self._aggiorna_record()

    # ------------------------------------------------------------- gli urti

    @staticmethod
    def _dentro(px, py, x, y, larga, alta):
        return x <= px < x + larga and y <= py < y + alta

    def _urti(self):
        # I tuoi colpi contro i caccia e il bombardiere.
        rimasti = []
        for c in self.colpi:
            preso = False
            for n in self.nemici:
                if not n.vivo or not n.entrato():
                    continue
                if self._dentro(c[0] + 2, c[1], n.x, n.y, LARGO_CACCIA, ALTO_CACCIA) or \
                        self._dentro(c[0], c[1], n.x, n.y, LARGO_CACCIA, ALTO_CACCIA):
                    n.vivo = False
                    preso = True
                    self._caccia_abbattuto(n)
                    break
            if not preso and self.bombardiere is not None:
                b = self.bombardiere
                if self._dentro(c[0] + 2, c[1], b["x"], b["y"],
                                LARGO_BOMBARDIERE, ALTO_BOMBARDIERE):
                    preso = True
                    b["vita"] -= 1
                    b["lampo"] = 0.08
                    self._segna("muro")
                    if b["vita"] <= 0:
                        self._bombardiere_abbattuto()
            if not preso:
                rimasti.append(c)
        self.colpi = rimasti
        self.nemici = [n for n in self.nemici if n.vivo]

        if self._morto > 0:
            return
        # Il tuo aereo: la sagoma che conta e' il centro, 5x3. I bordi delle
        # ali non uccidono: su 64 righe un urto di striscio sarebbe ingiusto.
        cx, cy = self.x + 2, self.y + 1
        for n in self.nemici:
            if n.entrato() and abs((n.x + 3) - (cx + 2)) < 5 and \
                    abs((n.y + 2) - (cy + 1)) < 4:
                if not self.intoccabile():
                    n.vivo = False
                    self._caccia_abbattuto(n, punti=False)
                self._abbattuto()
                break
        self.nemici = [n for n in self.nemici if n.vivo]
        colpite = []
        for b in self.bombe:
            if self._dentro(b[0], b[1], cx, cy, 5, 3):
                colpite.append(b)
                self._abbattuto()
                break
            for sy in self._posizioni_scorta():
                if self._dentro(b[0], b[1], self.x + 1, sy, 5, 3):
                    colpite.append(b)
                    self._abbattuto()
                    break
        if colpite:
            self.bombe = [b for b in self.bombe if b not in colpite]
        if self.bombardiere is not None and not self.intoccabile():
            b = self.bombardiere
            if self._dentro(cx + 4, cy + 1, b["x"], b["y"],
                            LARGO_BOMBARDIERE, ALTO_BOMBARDIERE):
                self._abbattuto()
        if self.pow is not None and abs(self.pow[0] - (self.x + 4)) < 6 and \
                abs(self.pow[1] - (self.y + 2)) < 5:
            self._prendi_pow()

    def _caccia_abbattuto(self, n, punti=True):
        self._esplosioni.append([n.x + 2, n.y + 1, 0.3])
        self._segna("colpito")
        if punti:
            self.punteggio += PUNTI_ROSSO if n.rosso else PUNTI_CACCIA
            self._aggiorna_record()
        conto = self._conti.get(n.squadriglia)
        if conto is None:
            return
        conto[1] += 1
        if conto[3] and conto[1] == conto[0] and punti:
            # L'intera squadriglia rossa: il POW, dove e' caduto l'ultimo.
            self.pow = [n.x, n.y + 2, 0.0]

    def _bombardiere_abbattuto(self):
        b = self.bombardiere
        for i in range(5):
            self._esplosioni.append([b["x"] + 6 * i, b["y"] + (i % 3) * 3, 0.9])
        self.bombardiere = None
        self.punteggio += PUNTI_BOMBARDIERE
        self._aggiorna_record()
        self._segna("livello")
        self.livello += 1
        vite, potenza, punteggio = self.vite, self.potenza, self.punteggio
        esplosioni = self._esplosioni
        self._nuovo_livello()
        self.vite, self.potenza, self.punteggio = vite, potenza, punteggio
        self._esplosioni = esplosioni

    # -------------------------------------------------------------- disegno

    def disegna(self):
        from PIL import Image
        # Il mare si fa con un colpo solo, non pixel per pixel: sono 14.000
        # pixel, e su un Raspberry un ciclo Python che li scrive uno a uno si
        # mangia mezzo fotogramma prima di disegnare qualunque cosa.
        img = Image.new("RGB", (LARGHEZZA, ALTEZZA), COLORE_MARE)
        img.paste((0, 0, 0), (0, 0, LARGHEZZA, CIMA))
        px = img.load()
        self.disegna_campo(img, px)
        self._disegna_tabellone(px)
        if self.finita:
            self._disegna_fine(px)
        return img

    def _metti(self, px, x, y, colore):
        if 0 <= x < LARGHEZZA and CIMA <= y < ALTEZZA:
            px[x, y] = colore

    def _sprite(self, px, righe, larga, x, y, colore):
        x, y = int(round(x)), int(round(y))
        for r, riga in enumerate(righe):
            for c in range(larga):
                if _bit(riga, larga, c):
                    self._metti(px, x + c, y + r, colore)

    def disegna_campo(self, img, px):
        for x, y in self._onde:
            self._metti(px, int(x), y, COLORE_ONDA)
            self._metti(px, int(x) + 1, y, COLORE_ONDA)
        for x, y, larga, alta in self._isole:
            for dx in range(larga):
                for dy in range(alta):
                    # Un'isola ovale, con il bordo di sabbia.
                    nx = (dx - larga / 2.0) / (larga / 2.0)
                    ny = (dy - alta / 2.0) / (alta / 2.0)
                    d = nx * nx + ny * ny
                    if d <= 1.0:
                        self._metti(px, int(x) + dx, y + dy,
                                    COLORE_SABBIA if d > 0.6 else COLORE_ISOLA)

        if self.pow is not None and int(self.pow[2] * 6) % 2 == 0:
            scrivi(px, "P", int(self.pow[0]), int(self.pow[1]) - 2, COLORE_POW)

        for n in self.nemici:
            if n.entrato():
                self._sprite(px, CACCIA, LARGO_CACCIA, n.x, n.y,
                             COLORE_ROSSO if n.rosso else COLORE_CACCIA)

        if self.bombardiere is not None:
            b = self.bombardiere
            colore = COLORE_COLPITO if b["lampo"] > 0 else COLORE_BOMBARDIERE
            for r, riga in enumerate(BOMBARDIERE):
                for c, ch in enumerate(riga):
                    if ch == "#":
                        self._metti(px, int(b["x"]) + c, int(b["y"]) + r, colore)
            # La vita rimasta, una barra sotto il tabellone.
            quota = max(0, b["vita"]) / float(30 + 10 * min(8, self.livello - 1))
            for x in range(int(60 * quota)):
                self._metti(px, LARGHEZZA - 62 + x, CIMA, COLORE_ROSSO)

        for x, y in self.colpi:
            for dx in range(3):
                self._metti(px, int(x) + dx, int(y), COLORE_COLPO)
        for x, y, _vx, _vy in self.bombe:
            for dx in (0, 1):
                for dy in (0, 1):
                    self._metti(px, int(x) + dx, int(y) + dy, COLORE_NEMICO)

        for x, y, t in self._esplosioni:
            raggio = 1 + int((1.0 - min(1.0, t)) * 3)
            for a in range(8):
                ang = a * math.pi / 4
                self._metti(px, int(x + math.cos(ang) * raggio),
                            int(y + math.sin(ang) * raggio), (255, 200, 80))

        if self._morto <= 0 and not self.finita and self.iniziata:
            lampeggia = self._protetto > 0 and int(self._protetto * 10) % 2 == 0
            if not lampeggia:
                if self._in_loop > 0:
                    posa = AEREO_LOOP[int((LOOP_DURATA - self._in_loop) * 4) % 2]
                else:
                    posa = AEREO[int(self._elica * 12) % 2]
                self._sprite(px, posa, LARGO_AEREO, self.x, self.y, COLORE_TU)
                for sy in self._posizioni_scorta():
                    self._sprite(px, SCORTA, 5, self.x + 1, sy, COLORE_SCORTA)

        if not self.iniziata and not self.finita:
            self._riquadro(px, 30, 48)
            centra(px, "SQUADRIGLIA", 32, COLORE_TU, larghezza=LARGHEZZA)
            centra(px, "FUOCO PER DECOLLARE", 40, COLORE_HUD,
                   larghezza=LARGHEZZA)

    def _riquadro(self, px, alto, basso):
        for y in range(alto, basso):
            for x in range(50, LARGHEZZA - 50):
                px[x, y] = (0, 0, 0)

    def _disegna_tabellone(self, px):
        scrivi(px, "%06d" % self.punteggio, 1, 1, COLORE_TU)
        scrivi(px, "HI %06d" % self.record(), 32, 1, (90, 150, 220))
        scrivi(px, "LIV %d" % self.livello, 76, 1, COLORE_HUD)
        # Le vite: aeroplanini. I looping: cerchietti.
        for i in range(max(0, min(5, self.vite))):
            x0 = 108 + i * 8
            for c in range(5):
                for r, riga in enumerate(SCORTA):
                    if _bit(riga, 5, c):
                        px[x0 + c, 2 + r] = COLORE_TU
        for i in range(max(0, min(5, self.loop))):
            x0 = 152 + i * 6
            for dx, dy in ((1, 0), (2, 0), (0, 1), (3, 1), (0, 2), (3, 2),
                           (1, 3), (2, 3)):
                px[x0 + dx, 1 + dy] = (90, 170, 255)
        if self.bombardiere is None:
            # Quanto manca al bombardiere: una barra che si riempie.
            quota = min(1.0, self._tempo / DURATA_LIVELLO)
            for x in range(int(60 * quota)):
                px[LARGHEZZA - 62 + x, 3] = (70, 70, 85)

    def _disegna_fine(self, px):
        self._riquadro(px, 28, 48)
        centra(px, "GAME OVER", 31, COLORE_ROSSO, larghezza=LARGHEZZA)
        centra(px, "FUOCO PER RIGIOCARE", 40, COLORE_HUD, larghezza=LARGHEZZA)
