# -*- coding: utf-8 -*-
"""Kingo Bongo: due gorilla sui tetti di una citta', che si tirano banane.

Da dove viene
-------------
Con il DOS 5 arrivava un gioco in QBasic in cui due gorilla, in piedi sui
palazzi, si lanciavano banane esplosive scegliendo angolo e velocita', col
vento di mezzo. Il nome e il disegno erano di chi l'aveva scritto e restano
suoi. Lo schema -- un tiro a parabola per volta, il vento, i palazzi che si
bucano -- non e' di nessuno. Questo e' Kingo Bongo, disegnato qui.

Tu contro il computer
---------------------
Tu a sinistra, il computer a destra. Nell'originale si scrivevano angolo e
velocita' con la tastiera; qui ci sono solo un pad e una pulsantiera, quindi:

* **su / giu'** cambiano l'angolo (0-90 gradi), **destra / sinistra** la
  velocita' (5-100). Tenendo premuto il numero corre, sempre piu' svelto.
* **fuoco** lancia. Una puntina di linea tratteggiata indica direzione e
  forza, e i due numeri stanno sul tabellone.

Il computer fa come farebbe una persona: sceglie un angolo e prova. Il primo
tiro e' largo, poi si corregge, e a ogni tiro sbaglia meno. Quanto largo e'
il primo tiro dipende dal livello: a ogni partita vinta il computer migliora.

La partita
----------
Vince la ripresa chi colpisce l'altro gorilla. Chi colpisce se stesso regala
la ripresa all'avversario, come nell'originale. Alla terza ripresa vinta la
partita e' tua, e se ne comincia una nuova col computer piu' bravo; se le tre
le vince lui, e' GAME OVER.

Punti: 1000 per ripresa, piu' 250 per ogni tiro risparmiato sotto i quattro,
e 2000 per ogni partita vinta.

Niente campiture
----------------
I palazzi sono **contorni con le finestre**, non blocchi pieni: la lezione di
Squadriglia e Gnam Gnam, un'area grande di colore basso sul pannello mostra
le righe del refresh. Un buco nel palazzo si vede lo stesso, perche' il
contorno lo segue.
"""

import math
import random

from PIL import Image

from .base import ALTEZZA, LARGHEZZA, Gioco, centra, larghezza_testo, scrivi

# ------------------------------------------------------------------ il campo

CIMA = 7                        # sopra, il tabellone
FONDO = ALTEZZA - 1             # l'ultima riga: la strada

# La fisica. Tutto in pixel e secondi. La velocita' sul tabellone va da 5 a
# 100; per 1,7 diventa pixel al secondo. Con queste due costanti un tiro a
# 45 gradi e velocita' 60 fa circa 130 pixel: meta' pannello.
GRAVITA = 80.0
SCALA_VELOCITA = 1.7
VENTO_MAX = 12                  # accelerazione orizzontale, pixel/s2
PASSO_FISICA = 1.0 / 120        # il volo si calcola a passi fissi: il computer
                                # simula con gli stessi, e trova gli stessi tiri
VOLO_MAX = 8.0                  # oltre, la banana si considera persa

ANGOLO_INIZIALE = 45
VELOCITA_INIZIALE = 50
ANGOLO_MIN, ANGOLO_MAX = 0, 90
VEL_MIN, VEL_MAX = 5, 100
RIPETI_DOPO = 0.35              # tenendo premuto, il numero corre da qui
RIPETI_VELOCE = 18.0            # unita' al secondo all'inizio della corsa
RIPETI_ACCELERA = 50.0          # e quanto accelera, al secondo

BUCO = 4.5                      # raggio del buco di una banana su un palazzo
BUCO_GORILLA = 8.0              # raggio del botto quando si prende un gorilla

RIPRESE_PER_VINCERE = 3
PUNTI_RIPRESA = 1000
PUNTI_TIRO_RISPARMIATO = 250
TIRI_BONUS = 4
PUNTI_PARTITA = 2000

DURATA_BOTTO = 0.45
DURATA_BOTTO_GORILLA = 1.0
DURATA_FESTA = 1.8
PENSA_MIN = 0.9                 # il computer "pensa" almeno cosi'
SIMULAZIONI_PER_FRAME = 3

ORDINE = ("colpito", "persa", "livello", "punto", "tonfo", "lancio")
SUONI_PER_FRAME = 2
MUSICA = "bongo_musica"

# ------------------------------------------------------------------ i colori

COLORE_TU = (215, 130, 55)
COLORE_CPU = (160, 120, 95)
COLORE_FACCIA = (235, 190, 130)
COLORE_BANANA = (255, 225, 40)
COLORE_MIRA = (120, 120, 145)
COLORE_VENTO = (80, 200, 230)
COLORE_HUD = (150, 150, 165)
COLORE_TITOLO = (255, 200, 60)
COLORE_RECORD = (90, 150, 220)
COLORE_FINE = (255, 60, 60)
COLORE_STELLA = (70, 70, 100)
COLORI_PALAZZI = ((70, 100, 170), (150, 70, 70), (70, 140, 140),
                  (130, 115, 90), (110, 80, 150))
COLORE_FINESTRA = (210, 185, 70)
COLORI_BOTTO = ((255, 240, 150), (255, 160, 40), (255, 70, 30))

# ------------------------------------------------------------------ gli sprite

# Il gorilla, 9x10, disegnato qui. B il pelo, F muso e petto, K gli occhi.
# Tre pose: fermo, un braccio su (quello del lancio), tutti e due su (festa).
GORILLA = (
    "...BBB...",
    "..BFFFB..",
    "..BKFKB..",
    "...BFB...",
    ".BBFFFBB.",
    "BBBFFFBBB",
    "B.BBBBB.B",
    "B.BBBBB.B",
    "..BB.BB..",
    ".BB...BB.",
)


def _braccio_su(righe, destra):
    r = [list(riga) for riga in righe]
    x, xi = (8, 7) if destra else (0, 1)
    for y in (6, 7):
        r[y][x] = "."
    r[2][x] = "B"
    r[3][x] = "B"
    r[4][xi] = "B"
    r[4][x] = "B"
    r[5][x] = "."
    return tuple("".join(riga) for riga in r)


GORILLA_LANCIO_DX = _braccio_su(GORILLA, True)
GORILLA_LANCIO_SX = _braccio_su(GORILLA, False)
GORILLA_FESTA = _braccio_su(GORILLA_LANCIO_DX, False)
LARGO_G = len(GORILLA[0])
ALTO_G = len(GORILLA)

# La banana: una curva di tre pixel, in quattro rotazioni.
_BANANA = ("Y..", "Y..", ".YY")


def _ruota(righe):
    n = len(righe)
    return tuple("".join(righe[n - 1 - c][r] for c in range(n)) for r in range(n))


BANANE = [_BANANA]
for _ in range(3):
    BANANE.append(_ruota(BANANE[-1]))


def _pixel(sprite):
    return tuple((x, y, c) for y, riga in enumerate(sprite)
                 for x, c in enumerate(riga) if c != ".")


# ------------------------------------------------------------------ la citta'

class Citta(object):
    """I palazzi come maschera di pixel pieni, con il disegno in cache.

    La maschera serve alle collisioni e ai buchi; il disegno -- contorni e
    finestre -- si rifa' solo quando un buco la cambia, non a ogni
    fotogramma: sul Raspberry 14 mila pixel da ricontrollare trenta volte al
    secondo sarebbero tempo rubato al pannello.
    """

    def __init__(self, rnd):
        self.pieno = [bytearray(LARGHEZZA) for _ in range(ALTEZZA)]
        self.proprietario = [0] * LARGHEZZA       # quale palazzo, per colonna
        self.palazzi = []                         # (x, larghezza, cima)
        self.finestre = {}                        # (x, y) -> accesa
        x = 0
        indice = 0
        while x < LARGHEZZA:
            largo = rnd.randint(16, 27)
            if LARGHEZZA - (x + largo) < 14:
                largo = LARGHEZZA - x
            alto = rnd.randint(12, 42)
            cima = FONDO - alto + 1
            self.palazzi.append((x, largo, cima))
            colore = indice % len(COLORI_PALAZZI)
            for xx in range(x, min(LARGHEZZA, x + largo - 1)):   # un pixel di vicolo
                self.proprietario[xx] = colore
                for yy in range(cima, ALTEZZA):
                    self.pieno[yy][xx] = 1
            # Le finestre: colonne ogni tre pixel, piani ogni quattro, alte due.
            for fx in range(x + 2, x + largo - 3, 3):
                for fy in range(cima + 3, FONDO - 1, 4):
                    accesa = rnd.random() < 0.45
                    if accesa:
                        self.finestre[(fx, fy)] = True
                        self.finestre[(fx, fy + 1)] = True
            x += largo
            indice += 1
        self.stelle = [(rnd.randint(0, LARGHEZZA - 1), rnd.randint(CIMA + 1, 30))
                       for _ in range(26)]
        self._img = None

    def solido(self, x, y):
        xi, yi = int(math.floor(x)), int(math.floor(y))
        if xi < 0 or xi >= LARGHEZZA or yi < 0:
            return False
        if yi >= ALTEZZA:
            return True
        return self.pieno[yi][xi] == 1

    def cima(self, x):
        """La prima riga piena della colonna, o FONDO."""
        for y in range(CIMA, ALTEZZA):
            if self.pieno[y][x]:
                return y
        return FONDO

    def buca(self, cx, cy, raggio):
        r2 = raggio * raggio
        for y in range(int(cy - raggio) - 1, int(cy + raggio) + 2):
            if not 0 <= y < ALTEZZA:
                continue
            for x in range(int(cx - raggio) - 1, int(cx + raggio) + 2):
                if 0 <= x < LARGHEZZA and (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= r2:
                    self.pieno[y][x] = 0
        self._img = None

    def immagine(self):
        if self._img is not None:
            return self._img
        img = Image.new("RGB", (LARGHEZZA, ALTEZZA), (0, 0, 0))
        px = img.load()
        for x, y in self.stelle:
            if not self.pieno[y][x]:
                px[x, y] = COLORE_STELLA
        p = self.pieno
        for y in range(CIMA, ALTEZZA):
            riga = p[y]
            su = p[y - 1]
            giu = p[y + 1] if y + 1 < ALTEZZA else None
            for x in range(LARGHEZZA):
                if not riga[x]:
                    continue
                bordo = (not su[x]
                         or (x == 0 or not riga[x - 1])
                         or (x == LARGHEZZA - 1 or not riga[x + 1])
                         or (giu is not None and not giu[x]))
                if bordo:
                    px[x, y] = COLORI_PALAZZI[self.proprietario[x]]
                elif (x, y) in self.finestre:
                    px[x, y] = COLORE_FINESTRA
        self._img = img
        return img


# ------------------------------------------------------------------ il volo

class Banana(object):
    """Una banana in volo, a passi fissi. La stessa per il tiro vero e per le
    prove del computer: cosi' quello che il computer calcola e' quello che
    succede."""

    __slots__ = ("x", "y", "vx", "vy", "vento", "t", "lanciatore", "uscita", "_resto")

    def __init__(self, x, y, angolo, velocita, verso, vento, lanciatore):
        a = math.radians(angolo)
        v = velocita * SCALA_VELOCITA
        self.x, self.y = float(x), float(y)
        self.vx = math.cos(a) * v * verso
        self.vy = -math.sin(a) * v
        self.vento = vento
        self.t = 0.0
        self.lanciatore = lanciatore
        self.uscita = False       # e' uscita dalla sagoma di chi l'ha lanciata
        self._resto = 0.0

    def un_passo(self, citta, gorilla):
        """Un passo fisso. Torna None se vola ancora, altrimenti
        ("gorilla", indice), ("palazzo", None) o ("fuori", None)."""
        h = PASSO_FISICA
        self.vx += self.vento * h
        self.vy += GRAVITA * h
        self.x += self.vx * h
        self.y += self.vy * h
        self.t += h
        for i, g in enumerate(gorilla):
            if g is None:
                continue
            dentro = g.contiene(self.x, self.y)
            if i == self.lanciatore and not self.uscita:
                if not dentro:
                    self.uscita = True
                continue
            if dentro:
                return ("gorilla", i)
        if self.x < -12 or self.x > LARGHEZZA + 12 or self.t > VOLO_MAX:
            return ("fuori", None)
        if self.y >= FONDO:
            return ("palazzo", None)
        if self.y >= CIMA and citta.solido(self.x, self.y):
            return ("palazzo", None)
        return None

    def avanza(self, dt, citta, gorilla):
        self._resto += dt
        while self._resto >= PASSO_FISICA:
            self._resto -= PASSO_FISICA
            esito = self.un_passo(citta, gorilla)
            if esito is not None:
                return esito
        return None


class Gorilla(object):
    __slots__ = ("x", "y", "verso", "colore")

    def __init__(self, x, y, verso, colore):
        self.x, self.y = x, y         # angolo in alto a sinistra della sagoma
        self.verso = verso            # +1 lancia verso destra, -1 verso sinistra
        self.colore = colore

    def contiene(self, x, y):
        return (self.x - 0.5 <= x < self.x + LARGO_G + 0.5
                and self.y - 0.5 <= y < self.y + ALTO_G + 0.5)

    def mano(self):
        """Da dove parte la banana: sopra la spalla del braccio che lancia."""
        if self.verso > 0:
            return self.x + LARGO_G - 1, self.y + 1
        return self.x, self.y + 1

    def centro(self):
        return self.x + LARGO_G / 2.0, self.y + ALTO_G / 2.0


# ------------------------------------------------------------------ il gioco

TU, CPU = 0, 1


class Bongo(Gioco):
    nome = "bongo"
    etichetta = "Kingo Bongo"
    colore_hud = COLORE_TITOLO
    MUSICA = MUSICA

    COMANDI = ("su", "giu", "sinistra", "destra", "fuoco", "avvia", "esci")

    # ---------------------------------------------------------------- partita

    def avvia_partita(self, seme=None):
        if seme is not None or not hasattr(self, "_rnd"):
            self._rnd = random.Random(seme)
        self.punteggio = 0
        self.vite = 0
        self.livello = 1
        self.finita = False
        self.iniziata = False
        self.angolo = ANGOLO_INIZIALE
        self.velocita = VELOCITA_INIZIALE
        self._eventi = []
        self.suoni_del_frame = ()
        self._prima = set()
        self._tenuto = {}
        self._frazione = 0.0
        self.riprese = [0, 0]
        self._nuova_ripresa(TU)

    def _nuova_ripresa(self, chi_comincia):
        self.citta = Citta(self._rnd)
        n = len(self.citta.palazzi)
        self.gorilla = [self._metti_gorilla(1 if n > 3 else 0, +1, COLORE_TU),
                        self._metti_gorilla(n - 2 if n > 3 else n - 1, -1, COLORE_CPU)]
        v = self._rnd.triangular(-VENTO_MAX, VENTO_MAX, 0)
        self.vento = int(round(v)) if abs(v) >= 1.5 else 0
        self.turno = chi_comincia
        self.tiri = [0, 0]
        self.banana = None
        self.botti = []
        self._festa = 0.0
        self._vincitore = None
        self._alzato = [0.0, 0.0]
        self._scritta = None
        self._cpu_angolo = None
        self._tiro_cpu = None
        self._mostra = [float(self.angolo), float(self.velocita)]
        self._inizia_turno()

    def _metti_gorilla(self, indice, verso, colore):
        x0, largo, cima = self.citta.palazzi[indice]
        x = x0 + (largo - 1 - LARGO_G) // 2
        return Gorilla(x, cima - ALTO_G, verso, colore)

    def _inizia_turno(self):
        self.fase = "mira" if self.turno == TU else "pensa"
        if self.turno == CPU:
            self._pensa = 0.0
            self._pensiero = self._cerca_tiro()
            self._tiro_cpu = None
            self._mostra = [float(self.angolo), float(self.velocita)]

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

    def _fisica(self, dt, tasti, premuti_ora):
        self._tempo = getattr(self, "_tempo", 0.0) + dt
        if self.finita:
            if "fuoco" in premuti_ora:
                self.avvia_partita()
                self.iniziata = True
            return
        if not self.iniziata:
            if "fuoco" in premuti_ora:
                self.iniziata = True
            return

        self._alzato = [max(0.0, a - dt) for a in self._alzato]
        self.botti = [b[:4] + [b[4] - dt] for b in self.botti if b[4] - dt > 0]
        if self._scritta is not None:
            testo, resta = self._scritta
            self._scritta = (testo, resta - dt) if resta - dt > 0 else None

        if self.fase == "mira":
            self._mira(dt, tasti, premuti_ora)
        elif self.fase == "pensa":
            self._pensa_cpu(dt)
        elif self.fase == "volo":
            self._vola(dt)
        elif self.fase == "botto":
            if not self.botti:
                self.turno = 1 - self.turno
                self._inizia_turno()
        elif self.fase == "festa":
            self._festa -= dt
            if self._festa <= 0:
                self._fine_ripresa()
        self._aggiorna_record()

    # ------------------------------------------------------------------ mira

    def _mira(self, dt, tasti, premuti_ora):
        for tasto, (campo, verso) in (("su", ("angolo", +1)), ("giu", ("angolo", -1)),
                                      ("destra", ("velocita", +1)),
                                      ("sinistra", ("velocita", -1))):
            if tasto in premuti_ora:
                self._cambia(campo, verso)
                self._tenuto[tasto] = 0.0
                self._frazione = 0.0
            elif tasto in tasti:
                t = self._tenuto.get(tasto, 0.0) + dt
                self._tenuto[tasto] = t
                if t > RIPETI_DOPO:
                    ritmo = RIPETI_VELOCE + RIPETI_ACCELERA * (t - RIPETI_DOPO)
                    self._frazione += ritmo * dt
                    while self._frazione >= 1.0:
                        self._frazione -= 1.0
                        self._cambia(campo, verso)
            else:
                self._tenuto.pop(tasto, None)
        if "fuoco" in premuti_ora:
            self._lancia(TU, self.angolo, self.velocita)

    def _cambia(self, campo, verso):
        if campo == "angolo":
            self.angolo = max(ANGOLO_MIN, min(ANGOLO_MAX, self.angolo + verso))
        else:
            self.velocita = max(VEL_MIN, min(VEL_MAX, self.velocita + verso))

    def _lancia(self, chi, angolo, velocita):
        g = self.gorilla[chi]
        x, y = g.mano()
        self.banana = Banana(x, y, angolo, velocita, g.verso, self.vento, chi)
        self.tiri[chi] += 1
        self._alzato[chi] = 0.3
        self.fase = "volo"
        self._segna("lancio")

    # ------------------------------------------------------------ il computer

    def errore_cpu(self):
        """Di quanto sbaglia la velocita' il computer, come deviazione tipica:
        largo al primo tiro, sempre meno ai tiri dopo, e meno a ogni livello."""
        base = max(2.2, 9.0 - 1.4 * (self.livello - 1))
        return max(0.7, base * (0.62 ** self.tiri[CPU]))

    def _simula(self, angolo, velocita):
        """Dove va a finire un tiro del computer: (esito, x, y)."""
        g = self.gorilla[CPU]
        x, y = g.mano()
        b = Banana(x, y, angolo, velocita, g.verso, self.vento, CPU)
        while True:
            esito = b.un_passo(self.citta, self.gorilla)
            if esito is not None:
                return esito, b.x, b.y

    def _quanto_lontano(self, angolo, velocita):
        esito, x, y = self._simula(angolo, velocita)
        if esito == ("gorilla", TU):
            return 0.0
        if esito == ("gorilla", CPU):
            return 999.0
        cx, cy = self.gorilla[TU].centro()
        if esito[0] == "fuori":
            # Uscita di lato o persa: conta da che parte, per correggersi.
            return 300.0 + abs(x - cx)
        return math.hypot(x - cx, (y - cy) * 0.5)

    def _cerca_tiro(self):
        """Il ragionamento del computer, un pezzo per fotogramma: un
        generatore che a ogni `next` fa qualche simulazione, e alla fine
        lascia in `_tiro_cpu` l'angolo e la velocita' giusti."""
        if self._cpu_angolo is None:
            self._cpu_angolo = self._rnd.randint(25, 50)   # tiri tesi: restano sul pannello
        angoli = [self._cpu_angolo] + [a for a in range(20, 81, 5)
                                       if a != self._cpu_angolo]
        migliore = (1e9, self._cpu_angolo, VELOCITA_INIZIALE)
        fatte = 0
        for angolo in angoli:
            for vel in range(VEL_MIN, VEL_MAX + 1, 2):
                d = self._quanto_lontano(angolo, vel)
                if d < migliore[0]:
                    migliore = (d, angolo, vel)
                fatte += 1
                if fatte % SIMULAZIONI_PER_FRAME == 0:
                    yield
            # Rifinitura attorno al migliore di questo angolo.
            if migliore[1] == angolo:
                centro = migliore[2]
                v = centro - 2.0
                while v <= centro + 2.0:
                    if VEL_MIN <= v <= VEL_MAX:
                        d = self._quanto_lontano(angolo, v)
                        if d < migliore[0]:
                            migliore = (d, angolo, v)
                    v += 0.25
                    fatte += 1
                    if fatte % SIMULAZIONI_PER_FRAME == 0:
                        yield
            if migliore[0] < 4.0:
                break
        _d, angolo, vel = migliore
        self._cpu_angolo = angolo
        errore = self._rnd.gauss(0.0, self.errore_cpu())
        self._tiro_cpu = (angolo, max(VEL_MIN, min(VEL_MAX, vel + errore)))

    def _pensa_cpu(self, dt):
        self._pensa += dt
        if self._tiro_cpu is None:
            try:
                next(self._pensiero)
            except StopIteration:
                pass
        if self._tiro_cpu is None:
            return
        # I numeri sul tabellone corrono verso quelli scelti, come se li
        # stesse scrivendo.
        bersaglio = self._tiro_cpu
        for i in (0, 1):
            diff = bersaglio[i] - self._mostra[i]
            passo = 60.0 * dt
            self._mostra[i] += max(-passo, min(passo, diff))
        if self._pensa >= PENSA_MIN and all(abs(bersaglio[i] - self._mostra[i]) < 0.01
                                            for i in (0, 1)):
            self._lancia(CPU, bersaglio[0], bersaglio[1])

    # ------------------------------------------------------------------ volo

    def _vola(self, dt):
        esito = self.banana.avanza(dt, self.citta, self.gorilla)
        if esito is None:
            return
        tipo, chi = esito
        x, y = self.banana.x, self.banana.y
        lanciatore = self.banana.lanciatore
        self.banana = None
        if tipo == "gorilla":
            g = self.gorilla[chi]
            cx, cy = g.centro()
            self.citta.buca(cx, cy + 2, BUCO_GORILLA)
            self.botti.append([cx, cy, BUCO_GORILLA + 3, DURATA_BOTTO_GORILLA, DURATA_BOTTO_GORILLA])
            self.gorilla[chi] = None
            vincitore = 1 - chi          # chi colpisce se stesso regala la ripresa
            self._vincitore = vincitore
            self.riprese[vincitore] += 1
            self._segna("colpito")
            if vincitore == TU:
                risparmiati = max(0, TIRI_BONUS - self.tiri[TU])
                self.punteggio += PUNTI_RIPRESA + PUNTI_TIRO_RISPARMIATO * risparmiati
                self._segna("punto")
                self._scritta = ("PRESO!", DURATA_FESTA + DURATA_BOTTO_GORILLA)
            else:
                self._segna("persa")
                self._scritta = ("PRESO TU!" if lanciatore == TU else "TI HA PRESO",
                                 DURATA_FESTA + DURATA_BOTTO_GORILLA)
            self._festa = DURATA_FESTA + DURATA_BOTTO_GORILLA
            self.fase = "festa"
        elif tipo == "palazzo":
            self.citta.buca(x, y, BUCO)
            self.botti.append([x, y, BUCO + 1.5, DURATA_BOTTO, DURATA_BOTTO])
            self._segna("tonfo")
            self.fase = "botto"
        else:
            self.fase = "botto"          # persa: nessun botto, si passa la mano

    def _fine_ripresa(self):
        vincitore = self._vincitore
        if self.riprese[vincitore] >= RIPRESE_PER_VINCERE:
            if vincitore == TU:
                self.punteggio += PUNTI_PARTITA
                self.livello += 1
                self.riprese = [0, 0]
                self._segna("livello")
                self._nuova_ripresa(TU)
                self._scritta = ("LIVELLO %d" % self.livello, 2.0)
            else:
                self.finita = True
                self._aggiorna_record()
            return
        # Comincia chi ha perso la ripresa.
        self._nuova_ripresa(1 - vincitore)

    # -------------------------------------------------------------- disegno

    def disegna_campo(self, img, px):          # pragma: no cover - non usata
        pass

    def _sprite(self, px, pixel, x0, y0, colore):
        for x, y, c in pixel:
            xx, yy = int(x0) + x, int(y0) + y
            if 0 <= xx < LARGHEZZA and CIMA <= yy < ALTEZZA:
                if c == "B":
                    px[xx, yy] = colore
                elif c == "F":
                    px[xx, yy] = COLORE_FACCIA
                elif c == "Y":
                    px[xx, yy] = COLORE_BANANA
                elif c == "K":
                    px[xx, yy] = (0, 0, 0)

    def _posa(self, chi):
        g = self.gorilla[chi]
        if self.fase == "festa" and chi == self._vincitore:
            # Balla: braccia su e giu', alternate.
            fase = int(self._festa * 4) % 3
            return (GORILLA_FESTA, GORILLA_LANCIO_DX, GORILLA_LANCIO_SX)[fase]
        if self._alzato[chi] > 0:
            return GORILLA_LANCIO_DX if g.verso > 0 else GORILLA_LANCIO_SX
        return GORILLA

    def disegna(self):
        img = self.citta.immagine().copy()
        px = img.load()
        for chi in (TU, CPU):
            g = self.gorilla[chi]
            if g is not None:
                self._sprite(px, _pixel(self._posa(chi)), g.x, g.y, g.colore)
        # A chi tocca: un triangolino sopra la testa, che lampeggia.
        if self.iniziata and not self.finita and self.fase in ("mira", "pensa"):
            g = self.gorilla[self.turno]
            if g is not None and int(self._rnd_fase() * 3) % 2 == 0:
                cx = g.x + LARGO_G // 2
                for dy, larga in ((0, 2), (1, 1), (2, 0)):
                    for dx in range(-larga, larga + 1):
                        yy = g.y - 5 + dy
                        if CIMA <= yy < ALTEZZA:
                            px[cx + dx, yy] = COLORE_HUD
        if self.fase == "mira" and self.iniziata and not self.finita:
            self._disegna_mira(px)
        if self.banana is not None:
            b = self.banana
            f = int(b.t * 12) % 4
            if b.y < CIMA:
                # Fuori dallo schermo in alto: un segno sulla prima riga.
                xx = int(b.x)
                if 0 <= xx < LARGHEZZA:
                    px[xx, CIMA] = COLORE_BANANA
            else:
                self._sprite(px, _pixel(BANANE[f]), b.x - 1, b.y - 1, None)
        for x, y, grande, durata, resta in self.botti:
            quota = 1.0 - resta / durata
            r = grande * (0.4 + 0.6 * quota)
            colore = COLORI_BOTTO[min(2, int(quota * 3))]
            passi = max(12, int(r * 6))
            for k in range(passi):
                a = 2 * math.pi * k / passi
                xx, yy = int(round(x + math.cos(a) * r)), int(round(y + math.sin(a) * r))
                if 0 <= xx < LARGHEZZA and CIMA <= yy < ALTEZZA:
                    px[xx, yy] = colore
        self._disegna_hud(px)
        return img

    def _rnd_fase(self):
        """Un orologio per i lampeggi, che non tocca il caso del gioco."""
        return getattr(self, "_tempo", 0.0)

    def _disegna_mira(self, px):
        g = self.gorilla[TU]
        if g is None:
            return
        x0, y0 = g.mano()
        a = math.radians(self.angolo)
        lungo = 3 + self.velocita * 0.13
        d = 2.0
        while d <= lungo:
            xx = int(round(x0 + math.cos(a) * d))
            yy = int(round(y0 - math.sin(a) * d))
            if 0 <= xx < LARGHEZZA and CIMA <= yy < ALTEZZA:
                px[xx, yy] = COLORE_MIRA
            d += 2.0

    def _disegna_hud(self, px):
        scrivi(px, "%06d" % self.punteggio, 1, 1, COLORE_TITOLO)
        scrivi(px, "HI %06d" % self.record(), 28, 1, COLORE_RECORD)
        if self.turno == CPU and self.fase in ("pensa", "volo") and self._tiro_cpu is not None:
            ang, vel = int(round(self._mostra[0])), int(round(self._mostra[1]))
            colore = COLORE_CPU
        elif self.turno == CPU and self.fase == "pensa":
            ang, vel = "--", "--"
            colore = COLORE_CPU
        else:
            ang, vel = self.angolo, self.velocita
            colore = COLORE_TU
        scrivi(px, "ANG %2s VEL %3s" % (ang, vel), 70, 1, colore)
        self._disegna_vento(px, 150, 3)
        scrivi(px, "LIV %d" % self.livello, 176, 1, COLORE_HUD)
        punti = "TU %d-%d CPU" % (self.riprese[TU], self.riprese[CPU])
        scrivi(px, punti, LARGHEZZA - larghezza_testo(punti) - 1, 1, COLORE_HUD)

        if self._scritta is not None and self.iniziata and not self.finita:
            centra(px, self._scritta[0], 10, COLORE_TITOLO, larghezza=LARGHEZZA)
        if not self.iniziata and not self.finita:
            self._riquadro(px, 18)
            centra(px, "KINGO BONGO", 20, COLORE_TITOLO, larghezza=LARGHEZZA)
            centra(px, "FUOCO PER PARTIRE", 28, COLORE_HUD, larghezza=LARGHEZZA)
        if self.finita:
            self._riquadro(px, 18)
            centra(px, "GAME OVER", 20, COLORE_FINE, larghezza=LARGHEZZA)
            centra(px, "FUOCO PER RIGIOCARE", 28, COLORE_HUD, larghezza=LARGHEZZA)

    @staticmethod
    def _riquadro(px, y0):
        for y in range(y0, y0 + 17):
            for x in range(84, 172):
                px[x, y] = (0, 0, 0)

    def _disegna_vento(self, px, cx, cy):
        """Il vento: una freccia lunga quanto soffia, verso dove soffia."""
        if self.vento == 0:
            px[cx, cy] = COLORE_VENTO
            return
        lungo = max(2, int(round(abs(self.vento) * 18.0 / VENTO_MAX)))
        verso = 1 if self.vento > 0 else -1
        x0 = cx - verso * lungo // 2
        for k in range(lungo + 1):
            px[x0 + verso * k, cy] = COLORE_VENTO
        punta = x0 + verso * lungo
        for d in (1, 2):
            px[punta - verso * d, cy - d] = COLORE_VENTO
            px[punta - verso * d, cy + d] = COLORE_VENTO
