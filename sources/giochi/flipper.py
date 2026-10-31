# -*- coding: utf-8 -*-
# fix-v3 2026-10-31
"""Flipper: una biglia, due alette, tre respingenti.

Il nome
-------
Il flipper e' il gioco di casa di questo pannello -- il DMD nasce nei
flipper veri -- e il nome italiano e' quello di tutti: resta nostro perche'
e' la parola di tutti. Lo schema -- una biglia d'acciaio, la gravita', due
alette e cose che rimbalzano -- non e' di nessuno. Questo e' Flipper:
codice scritto da zero contro il contratto di `Gioco`, tavolo nostro,
fisica nostra, ridotta all'osso per stare in un pannello.

Il tavolo
--------
Il tavolo prende il campo com'e': tutta la larghezza e tutta l'altezza
che il campo gli da', senza ritagliarsi un quadrato nel mezzo. Le misure
che contano -- biglia, alette, corsia, respingenti -- nascono
dall'altezza e non dalla larghezza, cosi' allargare il tavolo allarga il
campo di gioco, non gli attrezzi: sullo schermo alto il tavolo e' largo
256 e alto 146, sul pannello viene 200 per 64 -- piu' largo che alto,
stesse proporzioni di fisica, biglia identica. Si gioca su tutti e due,
ma il tavolo vero e' quello alto, e va detto.

A destra corre la **corsia di lancio**, un decimo del tavolo, separata da
un divisore che si ferma prima della cima. Sopra la bocca della corsia due
deflettori corti fanno la curva che nei tavoli veri e' tonda: la biglia
sale, sbatte sul diagonale e viene buttata a sinistra, nel campo. Sulla
bocca della corsia, appeso alla curva, un **cancello a senso unico**
come quello dei tavoli veri: la biglia lanciata esce senza sentirlo,
quella che dal campo vorrebbe rientrare nella corsia ci sbatte e resta
in gioco. Senza cancello la biglia rientrata scivolava giu' dalla
corsia, passava sotto la fine del divisore e cadeva nel buco: una palla
persa senza colpa.

La fisica
--------
Niente motore fisico: la biglia e' un cerchio, il mondo e' segmenti, e si
avanza a **sottopassi fissi da 1/240 di secondo**, cosi' la biglia non
passa mai attraverso un muro (a 570 pixel al secondo, in un sottoppasso si
muove di due pixel e rotti: meno del suo raggio). Le pareti restituiscono
il 35% della velocita' normale. Le alette sono segmenti che ruotano: la
collisione usa la velocita' del punto di contatto, come fa una parete che
si muove -- ed e' per quello che un colpo preso in punta di aletta parte
piu' forte di uno preso vicino al perno.

* Tre **respingenti** tondi: respingono forte, 100 punti, «ping».
* Due **calci** (le fionde sopra le alette): sono l'ultimo tratto delle
  guide laterali, e quando la biglia ci rotola sopra la rilanciano verso
  il campo, 50 punti, «colpito». Nei tavoli veri le fionde sono triangoli
  separati dalle guide; qui guida e fionda sono un segmento solo in due
  pezzi, perche' a queste misure un triangolo separato non si leggerebbe.
* Tre **corsie** in alto, sensori che si accendono al passaggio: 250 punti
  l'una, e tutte e tre accese fanno 1000 e si rispegnono.
* Il **lanciatore**: la biglia nasce in fondo alla corsia. Si tiene
  premuto giu' o fuoco per caricare (la barra nella corsia si riempie,
  0,8 secondi per il pieno), si mollano tutti e due e la biglia parte:
  a piena carica parte a 1,55 volte la velocita' di riferimento, supera
  la curva in cima con un margine vero e spazza l'arco fino a meta'
  campo; a poca carica ricade nella corsia e si rilancia. Il tasto
  speciale e' la **spinta**: una scossa
  laterale alla biglia, una al secondo, per salvarla dai rimbalzi
  stupidi.
* Le vite sono le biglie: tre. La biglia che esce dal buco in fondo --
  fra le alette, o sotto una delle due -- e' persa, «persa», e ne nasce
  un'altra in corsia. Alla terza il tabellone scrive GAME OVER.
* All'apertura il tavolo sta fermo sulla schermata del titolo -- il
  nome e «FUOCO PER PARTIRE», come nei giochi di serie: la biglia
  aspetta in corsia e le alette non si muovono finche' non si preme
  fuoco, e quella pressione e' spesa li', non carica il lanciatore.
"""

import math
import random

from PIL import ImageDraw

from .base import Gioco, centra, larghezza_testo, scrivi

# ------------------------------------------------------------------- fisica

SOTTOPASSO = 1.0 / 240.0     # la fisica avanza a passi fissi: niente tunnel
GRAVITA_A_146 = 260.0        # pixel al secondo quadrato, su un campo di 146
REST_PARETI = 0.35           # quanto rimbalza una parete
REST_DEFLETTORE = 0.55       # i deflettori dell'arco: piu' vivi, la
                             # biglia lanciata tiene la velocita' in curva
REST_ALETTA = 0.25           # l'aletta, oltre alla sua velocita' di punto
REST_RESPINGENTE = 0.9       # il respingente, che deve buttare fuori
SPINTA_RESPINGENTE = 150.0   # velocita' radiale minima in uscita, a scala 1
FORZA_CALCIO = 130.0         # la spinta della fionda, a scala 1
ATTESA_CALCIO = 0.25         # secondi fra un calcio e l'altro della stessa
ANGOLO_RIPOSO = 28.0         # gradi sotto l'orizzontale, alette a riposo
ESCURSIONE = 32.0            # gradi di corsa dell'aletta
TEMPO_SALITA = 0.05          # l'aletta sale in un battito
TEMPO_DISCESA = 0.12         # e torna giu' piu' piano
TEMPO_CARICA = 0.8           # 0,8 secondi di giu' o fuoco = piena carica
ATTESA_SPINTA = 1.0          # secondi fra una spinta e l'altra

PUNTI_RESPINGENTE = 100
PUNTI_CALCIO = 50
PUNTI_CORSIA = 250
PUNTI_TUTTE_CORSIE = 1000

COLORI_RESPINGENTI = ((255, 84, 84), (84, 220, 130), (96, 156, 255))


def _limita(valore, minimo, massimo):
    return max(minimo, min(massimo, valore))


class Flipper(Gioco):
    nome = "flipper"
    etichetta = "Flipper"
    colore_hud = (80, 180, 255)
    COMANDI = ("sinistra", "destra", "su", "giu", "fuoco", "speciale",
               "avvia", "esci")
    TELA_LIBERA = True

    # ------------------------------------------------------------- la partita

    def avvia_partita(self, seme=None):
        self._rng = random.Random(seme)
        self.punteggio = 0
        self.vite = 3
        self.livello = 1
        self.finita = False
        self.iniziata = False
        self.carica = 0.0
        self._prec = set()
        self._cd_spinta = 0.0
        self._posa_tavolo()
        self._rimetti_biglia()

    # ------------------------------------------------------------ il tavolo

    def _posa_tavolo(self):
        """Tutta la geometria nasce qui, dal rettangolo del campo.

        Nessuna misura e' scritta altrove: muri, respingenti, corsie e
        alette stanno in frazioni del tavolo, cosi' lo stesso codice
        disegna il mini-tavolo del pannello e quello dello schermo alto.
        """
        ca = self.campo_a
        self.scala = ca / 146.0
        self.gravita = GRAVITA_A_146 * self.scala
        # Il tavolo prende tutta la larghezza del campo. Le misure che
        # contano nascono dall'altezza H, come quando il tavolo era
        # quadrato e largo quanto alto: allargarlo allarga il campo di
        # gioco, non gonfia biglia, alette e corsia.
        self.tav_l = int(_limita(self.campo_l, 40, self.campo_l))
        self.tav_a = ca
        self.tav_x = self.campo_x + (self.campo_l - self.tav_l) // 2
        self.tav_y = self.campo_y
        x0, y0 = self.tav_x, self.tav_y
        W, H = self.tav_l, self.tav_a

        self.raggio = max(2.0, H / 26.0)
        # La corsia deve far passare la biglia: il nove per cento
        # dell'altezza, ma mai meno di biglia e un pixel d'aria per parte.
        self.corsia_l = max(2.0 * self.raggio + 2.0, round(H * 0.09))
        self.div_x = x0 + W - self.corsia_l
        div_x = self.div_x
        campo_l = div_x - x0                    # il campo da gioco vero
        cx = x0 + campo_l / 2.0                 # il suo centro

        self._vel_lancio = math.sqrt(2.0 * self.gravita * (H * 1.04))
        self._vel_max = max(160.0, 2.0 * self._vel_lancio)

        gh = H * 0.20                           # dove cominciano le guide
        cima_div = H * 0.30                     # dove si ferma il divisore:
        # basso, cosi' la biglia che esce dalla curva passa sopra
        # la sua cima senza sbatterci; la bocca che si apre la
        # chiude il cancello

        # Le alette: perni simmetrici, la luce fra le punte a riposo poco
        # piu' di due biglie -- larga da farci passare una biglia distratta,
        # stretta da prenderne una attenta.
        self.lun_aletta = max(5.0, H * 0.17)
        luce = 4.4 * self.raggio
        meta = luce / 2.0 + self.lun_aletta * math.cos(
            math.radians(ANGOLO_RIPOSO))
        perno_y = y0 + H - max(4.0, H * 0.05)
        self.aletta_sx = {"perno": (cx - meta, perno_y),
                          "riposo": math.radians(ANGOLO_RIPOSO),
                          "escursione": math.radians(-ESCURSIONE),
                          "f": 0.0}
        self.aletta_dx = {"perno": (cx + meta, perno_y),
                          "riposo": math.radians(180.0 - ANGOLO_RIPOSO),
                          "escursione": math.radians(ESCURSIONE),
                          "f": 0.0}
        self.ang_sx = self.aletta_sx["riposo"]
        self.ang_dx = self.aletta_dx["riposo"]

        medio_sx = (x0 + (cx - meta)) / 2.0, (y0 + H - gh + perno_y) / 2.0
        medio_dx = (div_x + (cx + meta)) / 2.0, (y0 + H - gh + perno_y) / 2.0

        # I muri fermi. Le guide laterali sono in due pezzi: quello alto e'
        # un muro, quello basso e' la fionda (sta in `calci`).
        self.muri = [
            (x0, y0, x0 + W, y0),                              # cima
            (x0, y0, x0, y0 + H - gh),                         # sinistra
            (x0 + W, y0, x0 + W, y0 + H),                      # destra corsia
            (div_x, y0 + H, x0 + W, y0 + H),                   # fondo corsia
            (div_x, y0 + cima_div, div_x, y0 + H - gh),        # divisore
            # Le guide alte, fino a meta' strada verso le alette.
            (x0, y0 + H - gh, medio_sx[0], medio_sx[1]),
            (div_x, y0 + H - gh, medio_dx[0], medio_dx[1]),
            # I paletti che separano le corsie in alto.
            (x0 + campo_l * 0.385, y0 + 1.0, x0 + campo_l * 0.385,
             y0 + H * 0.13),
            (x0 + campo_l * 0.555, y0 + 1.0, x0 + campo_l * 0.555,
             y0 + H * 0.13),
        ]

        # I deflettori, la curva sopra la corsia in due pezzi: il primo
        # scende dalla parete -- a 0,20 dell'altezza, non piu' a 0,14 --
        # quasi verticale, abbracciando la parete, cosi' la biglia che
        # sale debole nella corsia non lo tocca nemmeno e ricade sul
        # lanciatore; il secondo e' il diagonale che la biglia lanciata
        # colpisce e che la butta in campo. Il rimbalzo e' piu' vivo
        # dei muri (REST_DEFLETTORE), cosi' in curva la velocita' si
        # tiene. Le misure guardano la corsia e l'altezza, non la
        # larghezza del tavolo.
        self.deflettori = [
            (x0 + W, y0 + H * 0.20, x0 + W - H * 0.004, y0 + H * 0.13),
            (x0 + W - H * 0.004, y0 + H * 0.13, div_x - H * 0.09,
             y0 + H * 0.036),
        ]

        # Il cancello a senso unico: un segmento che pende dalla curva
        # e chiude la bocca della corsia in diagonale, da sotto la
        # bocca fin quasi al soffitto sopra la cima del divisore --
        # come il filo dei tavoli veri, appeso alla parete dell'orbita.
        # Non sta nei muri perche' un muro ferma da entrambi i lati e
        # lui no: vale solo per la biglia che dal campo si muove verso
        # la corsia (vedi `_urto_cancello`).
        self.cancello = (div_x - H * 0.08, y0 + H * 0.33,
                         div_x + H * 0.015, y0 + H * 0.089)

        # Le fionde: l'ultimo tratto di guida, con la sua direzione di
        # calcio -- la normale che guarda dentro il campo.
        self.calci = []
        for medio, aletta in ((medio_sx, self.aletta_sx),
                              (medio_dx, self.aletta_dx)):
            px, py = aletta["perno"]
            dx, dy = px - medio[0], py - medio[1]
            lung = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / lung, dx / lung
            if nx * (cx - medio[0]) < 0:
                nx, ny = -nx, -ny
            self.calci.append({"a": medio, "b": (px, py),
                               "n": (nx, ny), "cd": 0.0})

        # I respingenti: tre cerchi nel terzo alto del campo.
        r_res = max(2.5, H * 0.075)
        self.respingenti = [
            (x0 + campo_l * fx, y0 + H * fy, r_res)
            for fx, fy in ((0.32, 0.30), (0.62, 0.24), (0.47, 0.42))]
        self._lampeggi = [0.0, 0.0, 0.0]

        # Le corsie in alto: sensori, non muri. Si accendono al passaggio.
        meta_corsia = campo_l * 0.055
        self.corsie = [(x0 + campo_l * f - meta_corsia,
                        y0 + H * 0.06,
                        x0 + campo_l * f + meta_corsia,
                        y0 + H * 0.16)
                       for f in (0.30, 0.47, 0.64)]
        self.corsie_accese = [False, False, False]

    def _rimetti_biglia(self):
        """La biglia nuova nasce in fondo alla corsia, ferma."""
        self.bx = self.div_x + self.corsia_l / 2.0
        self.by = self.tav_y + self.tav_a - self.raggio - 0.5
        self.vx = 0.0
        self.vy = 0.0
        self.carica = 0.0

    def _in_corsia(self):
        return self.bx > self.div_x

    # ---------------------------------------------------------------- passo

    def passo(self, dt, tasti):
        if self.finita:
            # Partita finita: fuoco la ricomincia da capo, come negli
            # altri giochi, e la stessa pressione non vale nella partita
            # nuova: resta nei `_prec`, cosi' non carica il lanciatore
            # ne' muove le alette in questo fotogramma (si torna subito).
            if "fuoco" in tasti:
                self.avvia_partita()
                self.iniziata = True
                self._prec = set(tasti)
            return
        if not self.iniziata:
            # La schermata del titolo, come nei giochi di serie: il
            # tavolo sta fermo, la biglia aspetta in corsia, e si parte
            # solo col fuoco, sul fronte di salita. La pressione che fa
            # partire e' spesa li': resta fra i precedenti, cosi' non
            # carica il lanciatore e non muove le alette.
            if "fuoco" in tasti and "fuoco" not in self._prec:
                self.iniziata = True
            self._prec = set(tasti)
            return
        dt = min(max(dt, 0.0), 0.05)

        # Le alette: dove sono e dove saranno a fine fotogramma. La fisica
        # interpola l'angolo nei sottopassi e ne ricava la velocita'.
        ang_sx0, ang_dx0 = self.ang_sx, self.ang_dx
        for aletta, attiva in (
                (self.aletta_sx, "sinistra" in tasti or "fuoco" in tasti),
                (self.aletta_dx, "destra" in tasti or "fuoco" in tasti)):
            if attiva:
                aletta["f"] = min(1.0, aletta["f"] + dt / TEMPO_SALITA)
            else:
                aletta["f"] = max(0.0, aletta["f"] - dt / TEMPO_DISCESA)
        self.ang_sx = (self.aletta_sx["riposo"]
                       + self.aletta_sx["escursione"] * self.aletta_sx["f"])
        self.ang_dx = (self.aletta_dx["riposo"]
                       + self.aletta_dx["escursione"] * self.aletta_dx["f"])
        om_sx = (self.ang_sx - ang_sx0) / dt if dt > 0 else 0.0
        om_dx = (self.ang_dx - ang_dx0) / dt if dt > 0 else 0.0

        # I tempi di attesa scorrono col fotogramma, non coi sottopassi.
        self._cd_spinta = max(0.0, self._cd_spinta - dt)
        for calcio in self.calci:
            calcio["cd"] = max(0.0, calcio["cd"] - dt)
        self._lampeggi = [max(0.0, t - dt) for t in self._lampeggi]

        # Il lanciatore: giu' o fuoco caricano (fuoco muove anche le
        # alette, come sopra), mollare tutti e due lancia.
        if self._in_corsia():
            if "giu" in tasti or "fuoco" in tasti:
                self.carica = min(1.0, self.carica + dt / TEMPO_CARICA)
            elif self.carica > 0.0:
                self.vy = -(0.60 + 0.95 * self.carica) * self._vel_lancio
                self.vx = 0.0
                self.carica = 0.0
                self.suona("lancio")
        else:
            self.carica = 0.0

        # La spinta: sul fronte di salita, mai in corsia, una al secondo.
        if ("speciale" in tasti and "speciale" not in self._prec
                and self._cd_spinta <= 0.0 and not self._in_corsia()):
            self.vx += (self._rng.choice((-1.0, 1.0)) * 90.0
                        * max(self.scala, 0.5))
            self._cd_spinta = ATTESA_SPINTA

        # La fisica, a sottopassi fissi.
        n = max(1, int(math.ceil(dt / SOTTOPASSO))) if dt > 0 else 1
        h = dt / n if dt > 0 else 0.0
        for i in range(n):
            fr = (i + 1.0) / n
            a_sx = ang_sx0 + (self.ang_sx - ang_sx0) * fr
            a_dx = ang_dx0 + (self.ang_dx - ang_dx0) * fr
            self._fisica(h, a_sx, a_dx, om_sx, om_dx)
            if self.by - self.raggio > self.tav_y + self.tav_a + 3.0:
                self._perdi_biglia()
                break
        self._prec = set(tasti)

    def _perdi_biglia(self):
        self.suona("persa")
        self.vite -= 1
        if self.vite <= 0:
            self.vite = 0
            self.finita = True
        else:
            self._rimetti_biglia()

    # --------------------------------------------------------------- fisica

    def _fisica(self, h, ang_sx, ang_dx, om_sx, om_dx):
        if h <= 0.0:
            return
        self.vy += self.gravita * h
        vel = math.hypot(self.vx, self.vy)
        if vel > self._vel_max:
            self.vx *= self._vel_max / vel
            self.vy *= self._vel_max / vel
        self.bx += self.vx * h
        self.by += self.vy * h
        # Due giri di collisioni: un angolo puo' chiedere due risposte.
        for _ in range(2):
            for seg in self.muri:
                self._urto_segmento(seg, REST_PARETI)
            for seg in self.deflettori:
                self._urto_segmento(seg, REST_DEFLETTORE)
            self._urto_cancello()
            for calcio in self.calci:
                self._urto_calcio(calcio)
        for i, (cx, cy, cr) in enumerate(self.respingenti):
            self._urto_respingente(i, cx, cy, cr)
        self._urto_aletta(self.aletta_sx, ang_sx, om_sx)
        self._urto_aletta(self.aletta_dx, ang_dx, om_dx)
        # I sensori delle corsie: si accendono al passaggio della biglia.
        for i, (sx0, sy0, sx1, sy1) in enumerate(self.corsie):
            if (not self.corsie_accese[i]
                    and sx0 <= self.bx <= sx1 and sy0 <= self.by <= sy1):
                self.corsie_accese[i] = True
                self.punteggio += PUNTI_CORSIA
                self.suona("punto")
                if all(self.corsie_accese):
                    self.punteggio += PUNTI_TUTTE_CORSIE
                    self.corsie_accese = [False, False, False]
                    self.suona("livello")

    def _contatto_segmento(self, ax, ay, bx2, by2):
        """Il contatto biglia-segmento, se c'e': (normale, t) e biglia fuori.

        Sposta la biglia sulla superficie e dice da che parte sta il fuori,
        senza toccare la velocita': cosa farne lo decidono il muro, la
        fionda e l'aletta, ognuno a modo suo.
        """
        dx, dy = bx2 - ax, by2 - ay
        lung2 = dx * dx + dy * dy
        if lung2 <= 0.0:
            return None
        t = ((self.bx - ax) * dx + (self.by - ay) * dy) / lung2
        t = _limita(t, 0.0, 1.0)
        cx, cy = ax + t * dx, ay + t * dy
        ex, ey = self.bx - cx, self.by - cy
        d2 = ex * ex + ey * ey
        r = self.raggio
        if d2 >= r * r:
            return None
        d = math.sqrt(d2)
        if d < 1e-9:
            lung = math.sqrt(lung2)
            nx, ny = -dy / lung, dx / lung
            if (self.bx - ax) * nx + (self.by - ay) * ny < 0:
                nx, ny = -nx, -ny
        else:
            nx, ny = ex / d, ey / d
        self.bx = cx + nx * r
        self.by = cy + ny * r
        return (nx, ny, t)

    def _rimbalza(self, nx, ny, restituzione):
        vn = self.vx * nx + self.vy * ny
        if vn < 0.0:
            self.vx -= (1.0 + restituzione) * vn * nx
            self.vy -= (1.0 + restituzione) * vn * ny

    def _urto_segmento(self, seg, restituzione):
        contatto = self._contatto_segmento(*seg)
        if contatto is not None:
            self._rimbalza(contatto[0], contatto[1], restituzione)

    def _urto_cancello(self):
        """Il cancello a senso unico sulla bocca della corsia.

        Un muro ferma la biglia da entrambi i lati; il cancello solo
        quella che sta dal lato del campo e si muove verso la corsia.
        Il lato si decide col segno del prodotto vettoriale fra il
        segmento -- dalla bocca alla cima del divisore -- e la
        posizione della biglia: positivo e' il campo, negativo la
        corsia. Il verso si decide da come quel segno cambia: se il
        prodotto sta calando, la biglia sta attraversando il piano del
        cancello verso la corsia. La biglia in corsia -- quella che
        esce lanciata e quella debole che ricade per rilanciarsi -- sta
        dal lato negativo o si allontana dal piano, e per lei il
        cancello non esiste.
        """
        ax, ay, bx2, by2 = self.cancello
        dx, dy = bx2 - ax, by2 - ay
        lato = (self.bx - ax) * dy - (self.by - ay) * dx
        if lato <= 0.0:
            return
        if self.vx * dy - self.vy * dx >= 0.0:
            return
        # E come il filo dei tavoli veri, spinto dalla biglia che esce
        # si apre: una biglia che corre verso il campo -- quella debole
        # che ha toccato il deflettore e ricade sopra la bocca andando
        # dall'altra parte -- lo attraversa senza sentirlo.
        if self.vx < -25.0 * max(self.scala, 0.5):
            return
        self._urto_segmento(self.cancello, REST_PARETI)

    def _urto_calcio(self, calcio):
        contatto = self._contatto_segmento(calcio["a"][0], calcio["a"][1],
                                           calcio["b"][0], calcio["b"][1])
        if contatto is None:
            return
        nx, ny = contatto[0], contatto[1]
        vn_prima = self.vx * nx + self.vy * ny
        self._rimbalza(nx, ny, REST_PARETI)
        if vn_prima >= 0.0 or calcio["cd"] > 0.0:
            return
        # La fionda non si limita a rimbalzare: rilancia.
        kx, ky = calcio["n"]
        forza = FORZA_CALCIO * max(self.scala, 0.55)
        self.vx += kx * forza
        self.vy += ky * forza
        calcio["cd"] = ATTESA_CALCIO
        self.punteggio += PUNTI_CALCIO
        self.suona("colpito")

    def _urto_respingente(self, i, cx, cy, cr):
        ex, ey = self.bx - cx, self.by - cy
        d = math.hypot(ex, ey)
        if d >= self.raggio + cr:
            return
        if d < 1e-9:
            # Centro contro centro: non succede, ma se succede si esce
            # da sopra invece di restare incastrati nel respingente.
            ex, ey, d = 0.0, -1.0, 1.0
        nx, ny = ex / d, ey / d
        self.bx = cx + nx * (self.raggio + cr)
        self.by = cy + ny * (self.raggio + cr)
        vn = self.vx * nx + self.vy * ny
        if vn >= 0.0:
            return
        self._rimbalza(nx, ny, REST_RESPINGENTE)
        # E se il rimbalzo non basta, il respingente spinge lui.
        vn = self.vx * nx + self.vy * ny
        spinta = SPINTA_RESPINGENTE * self.scala + 50.0
        if vn < spinta:
            self.vx += nx * (spinta - vn)
            self.vy += ny * (spinta - vn)
        self.punteggio += PUNTI_RESPINGENTE
        self._lampeggi[i] = 0.12
        self.suona("ping")

    def _urto_aletta(self, aletta, angolo, omega):
        px, py = aletta["perno"]
        dx, dy = math.cos(angolo), math.sin(angolo)
        contatto = self._contatto_segmento(
            px, py, px + dx * self.lun_aletta, py + dy * self.lun_aletta)
        if contatto is None:
            return
        nx, ny, t = contatto
        # La velocita' del punto dell'aletta che la biglia ha toccato: e'
        # quello che trasforma un rimbalzo in un tiro. In punta vale il
        # doppio che a meta', e a meta' il doppio che al perno.
        s = t * self.lun_aletta
        vpx, vpy = omega * s * (-dy), omega * s * dx
        rvx, rvy = self.vx - vpx, self.vy - vpy
        vn = rvx * nx + rvy * ny
        if vn < 0.0:
            rvx -= (1.0 + REST_ALETTA) * vn * nx
            rvy -= (1.0 + REST_ALETTA) * vn * ny
            self.vx, self.vy = rvx + vpx, rvy + vpy

    # --------------------------------------------------------------- disegno

    def segmento_aletta(self, aletta, angolo):
        """Le due estremita' dell'aletta a un angolo dato."""
        px, py = aletta["perno"]
        return (px, py,
                px + math.cos(angolo) * self.lun_aletta,
                py + math.sin(angolo) * self.lun_aletta)

    def disegna_campo(self, img, px):
        dis = ImageDraw.Draw(img)
        x0, y0 = self.tav_x, self.tav_y
        W, H = self.tav_l, self.tav_a
        dis.rectangle([x0, y0, x0 + W - 1, y0 + H - 1], fill=(6, 6, 12))
        dis.rectangle([x0, y0, x0 + W - 1, y0 + H - 1],
                      outline=(52, 62, 92))
        # L'arte del piano, sotto tutto: il medaglione centrale con gli
        # anelli, le frecce verso le corsie, la firma sull'apron. Colori
        # bassi apposta: il piano si legge come un tavolo vero, ma la
        # biglia e i colpi restano i protagonisti.
        cxm, cym = x0 + W // 2, y0 + int(H * 0.46)
        rm = max(6, int(min(W, H) * 0.20))
        for rr, col in ((rm, (16, 20, 36)), (int(rm * 0.72), (20, 26, 46)),
                        (int(rm * 0.44), (16, 20, 36))):
            dis.ellipse([cxm - rr, cym - rr, cxm + rr, cym + rr],
                        outline=col, width=2)
        dis.polygon([(cxm, cym - rm // 3), (cxm + rm // 3, cym),
                     (cxm, cym + rm // 3), (cxm - rm // 3, cym)],
                    outline=(64, 84, 128))
        for sx0, sy0, sx1, sy1 in self.corsie:
            fx = (sx0 + sx1) // 2
            fy = sy1 + max(6, H // 14)
            dis.polygon([(fx, fy - 4), (fx - 4, fy + 3), (fx + 4, fy + 3)],
                        fill=(74, 60, 26))
        if H >= 100:
            centra(px, "FLIPPER", int(y0 + H * 0.80), (58, 68, 96),
                   sinistra=int(x0), larghezza=int(W))
        # I pannelli laterali, solo se la tela e' piu' larga del tavolo:
        # a sinistra il titolo e le biglie rimaste, a destra le corsie.
        mx0 = self.campo_x
        mx1 = self.campo_x + self.campo_l
        if x0 - mx0 >= 40:
            centra(px, "FLIPPER", int(self.campo_y + 10), (255, 140, 26),
                   sinistra=int(mx0), larghezza=int(x0 - mx0))
            for i in range(3):
                byy = self.campo_y + 34 + i * 16
                bxx = mx0 + (x0 - mx0) // 2
                dis.ellipse([bxx - 4, byy - 4, bxx + 4, byy + 4],
                            fill=(235, 235, 240) if i < self.vite
                            else (30, 30, 44),
                            outline=(120, 120, 132))
        if mx1 - (x0 + W) >= 40:
            centra(px, "CORSIE", int(self.campo_y + 10), (255, 200, 60),
                   sinistra=int(x0 + W), larghezza=int(mx1 - x0 - W))
            for i in range(3):
                byy = self.campo_y + 34 + i * 16
                bxx = (x0 + W + mx1) // 2
                dis.rectangle([bxx - 5, byy - 5, bxx + 5, byy + 5],
                              fill=(255, 200, 60) if self.corsie_accese[i]
                              else (30, 30, 44), outline=(110, 94, 40))
        # Le corsie: spente un contorno fioco, accese piene.
        for i, (sx0, sy0, sx1, sy1) in enumerate(self.corsie):
            if self.corsie_accese[i]:
                dis.rectangle([sx0, sy0, sx1, sy1], fill=(255, 200, 60))
            else:
                dis.rectangle([sx0, sy0, sx1, sy1], outline=(110, 94, 40))
        # I muri.
        for seg in self.muri:
            dis.line([seg[0], seg[1], seg[2], seg[3]], fill=(96, 96, 116))
        # I deflettori dell'arco, un filo piu' chiari dei muri.
        for seg in self.deflettori:
            dis.line([seg[0], seg[1], seg[2], seg[3]], fill=(140, 150, 180))
        # Il cancello sulla bocca della corsia, in giallo come le alette.
        dis.line([self.cancello[0], self.cancello[1], self.cancello[2],
                  self.cancello[3]], fill=(240, 216, 84))
        # Le fionde: un triangolo pieno dietro il segmento, in accento.
        for calcio in self.calci:
            ax, ay = calcio["a"]
            bx2, by2 = calcio["b"]
            nx, ny = calcio["n"]
            dis.polygon([(ax, ay), (bx2, by2),
                         (bx2 - nx * 5, by2 - ny * 5),
                         (ax - nx * 5, ay - ny * 5)], fill=(64, 40, 14))
            dis.line([ax, ay, bx2, by2], fill=(255, 140, 26))
        # I respingenti: pieni e colorati solo nell'istante del colpo.
        for i, (cx, cy, cr) in enumerate(self.respingenti):
            pieno = (COLORI_RESPINGENTI[i] if self._lampeggi[i] > 0.0
                     else tuple(c // 3 for c in COLORI_RESPINGENTI[i]))
            dis.ellipse([cx - cr, cy - cr, cx + cr, cy + cr],
                        fill=pieno, outline=(200, 200, 210))
            dis.point((int(cx), int(cy)), fill=(200, 200, 210))
        # Le alette e i loro perni.
        for aletta, angolo in ((self.aletta_sx, self.ang_sx),
                               (self.aletta_dx, self.ang_dx)):
            seg = self.segmento_aletta(aletta, angolo)
            dis.line([seg[0], seg[1], seg[2], seg[3]],
                     fill=(240, 216, 84), width=2)
            dis.point((int(aletta["perno"][0]), int(aletta["perno"][1])),
                      fill=(235, 235, 240))
        # La barra di carica, nella corsia, quando la biglia aspetta.
        if self._in_corsia() and not self.finita:
            alto_barra = int(H * 0.30)
            bx0 = x0 + W - 3
            dis.rectangle([bx0, y0 + H - 1 - alto_barra, x0 + W - 1,
                           y0 + H - 1], outline=(70, 70, 84))
            if self.carica > 0.0:
                riempi = int(alto_barra * self.carica)
                colore = (255, 84, 84) if self.carica >= 0.99 else (
                    255, 200, 60)
                dis.rectangle([bx0, y0 + H - 1 - riempi, x0 + W - 1,
                               y0 + H - 1], fill=colore)
            elif self.tav_l >= 90 and self.iniziata:
                centra(px, "GIU PER LANCIARE",
                       int(y0 + H * 0.55), (110, 110, 125),
                       sinistra=int(x0), larghezza=int(self.div_x - x0))
        # La biglia.
        if not self.finita:
            r = self.raggio
            dis.ellipse([self.bx - r, self.by - r, self.bx + r,
                         self.by + r],
                        fill=(235, 235, 240), outline=(120, 120, 132))
        if not self.iniziata and not self.finita:
            self._disegna_titolo(dis, px)

    def _disegna_titolo(self, dis, px):
        """La schermata del titolo: nome e invito, come nei giochi di serie.

        Il tavolo resta disegnato sotto, fermo al fotogramma zero, e sopra
        un riquadro nero porta le due scritte, centrate sul campo: il nome
        nel colore del tabellone, «FUOCO PER PARTIRE» in grigio, col font
        3x5 del quadro. Le righe stanno a meta' campo, alla maniera della
        scritta di fine partita: nome a meta' meno cinque, invito a
        meta' piu' tre.
        """
        meta = self.campo_y + self.campo_a // 2
        larga = larghezza_testo("FUOCO PER PARTIRE") + 12
        x0 = self.campo_x + (self.campo_l - larga) // 2
        dis.rectangle([x0, meta - 8, x0 + larga - 1, meta + 8],
                      fill=(0, 0, 0))
        centra(px, "FLIPPER", meta - 5, self.colore_hud)
        centra(px, "FUOCO PER PARTIRE", meta + 3, (150, 150, 160))
