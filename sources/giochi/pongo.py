# -*- coding: utf-8 -*-
"""Pongo: due racchette, una pallina, tu contro il pannello.

Il nome
-------
Il gioco del 1972 si chiamava PONG, e **PONG e' un marchio di Atari**. Il
meccanismo -- due racchette, una pallina, un punto a chi non la prende -- non
e' di nessuno e si rifa' liberamente; il nome invece e' loro. Questo e' Pongo.

Un giocatore, contro il computer
--------------------------------
Tu a sinistra, il computer a destra. Contro un muro Pong diventa una gara di
resistenza e annoia in un minuto; contro un avversario che non sbaglia mai non
si vince. Il computer quindi ha **tre difetti umani**, e il livello di
difficolta' li dosa:

* **reagisce in ritardo**: comincia a pensare a dove andare solo un po' dopo
  che la pallina ha cambiato direzione;
* **ha una velocita' massima**: se la pallina arriva lontana e veloce, non ci
  arriva;
* **mira male**: stima il punto di arrivo con un errore, piu' grande quando
  la pallina va veloce -- che e' esattamente quando sbaglia anche una persona.

Il secondo giocatore non c'e', ma i due lati sono gia' separati: `passo`
riceve i tasti del giocatore di sinistra, e la racchetta di destra si muove
da `_mossa_destra`. Un giorno, con il lettore dei comandi capace di dire da
quale pad arriva un tasto, la mossa di destra potra' venire da li'.

Si puo' andare avanti
---------------------
La tua racchetta non sta inchiodata al bordo: con sinistra e destra si muove
anche in orizzontale, fino a meta' del tuo campo. Avanzare chiude gli angoli
e, se colpisci mentre avanzi, **schiacci**: la pallina riparte piu' veloce.
In cambio hai meno tempo per reagire. Il computer resta sul fondo: e' il tuo
vantaggio, e lo paghi in tempo di reazione.

Il campo e' tutto il pannello
-----------------------------
Gli altri giochi tengono i 56 pixel di destra per il tabellone. Qui no: il
punteggio di Pong sta **al centro, in alto**, grande, uno per parte della
rete -- ed e' quello che uno si aspetta di vedere. Tenere il tabellone a
destra vorrebbe dire mettere la racchetta del computer contro una colonna di
numeri.
"""

import math
import random

from .base import ALTEZZA, LARGHEZZA, Gioco, _F, centra

# ---------------------------------------------------------------- il campo

RACCHETTA_H = 12
RACCHETTA_L = 2
X_SINISTRA = 4                          # colonna della racchetta tua, a riposo
# Fin dove puo' avanzare: la prima meta' del tuo campo, cioe' un quarto del
# pannello. Avanzare accorcia gli angoli all'avversario ma toglie a te il
# tempo di reagire: a meta' campo una pallina veloce arriva in un terzo di
# secondo. E' uno scambio, non un vantaggio gratis.
X_AVANTI = LARGHEZZA // 4 - RACCHETTA_L  # 62: la racchetta finisce a 64
X_DESTRA = LARGHEZZA - 4 - RACCHETTA_L  # colonna di quella del computer
PALLA = 2
RACCHETTA_V = 95.0      # pixel al secondo, tasto premuto: 0,55 s da un bordo all'altro
RACCHETTA_VX = 95.0     # in avanti e indietro, alla stessa velocita'
# La schiacciata: colpire mentre si avanza da' alla pallina un 15% in piu',
# oltre all'accelerazione normale di ogni colpo. E' il motivo per avanzare.
SCHIACCIATA = 1.15

VELOCITA_INIZIALE = 90.0     # quasi tre secondi da una racchetta all'altra
VELOCITA_MASSIMA = 210.0     # oltre, su 64 righe la pallina non si segue
ACCELERAZIONE = 1.05         # a ogni colpo di racchetta

# L'angolo di uscita dipende da dove si colpisce: al centro esce dritta, sul
# bordo inclinata. Oltre i 50 gradi, su un campo alto 64 pixel, la pallina
# rimbalza fra le sponde piu' che andare avanti.
ANGOLO_MAX = math.radians(50)

PUNTI_PER_VINCERE = 11        # come il cabinato del 1972: undici, senza vantaggi
PAUSA_SERVIZIO = 1.2          # secondi fra un punto e la battuta successiva

# Rosso e non arancione: sul pannello vero l'arancione su due pixel di
# larghezza, in movimento, si leggeva poco -- diventava un giallo sbiadito.
COLORE_TU = (255, 40, 40)
COLORE_CPU = (90, 170, 255)
COLORE_PALLA = (255, 255, 255)
COLORE_RETE = (60, 60, 70)
COLORE_PUNTI = (110, 110, 125)

# --------------------------------------------------------------- il computer

# reazione: secondi prima di accorgersi che la pallina viene verso di lui.
# velocita: pixel al secondo della sua racchetta.
# errore: di quanti pixel sbaglia la stima, alla velocita' iniziale; cresce
#         in proporzione alla velocita' della pallina.
LIVELLI = {
    "facile": {"reazione": 0.30, "velocita": 48.0, "errore": 7.0},
    "normale": {"reazione": 0.18, "velocita": 62.0, "errore": 4.5},
    "difficile": {"reazione": 0.10, "velocita": 80.0, "errore": 2.5},
}
LIVELLO_PREDEFINITO = "normale"
NUMERO_LIVELLO = {"facile": 1, "normale": 2, "difficile": 3}

ORDINE = ("persa", "punto", "ping", "sponda")
SUONI_PER_FRAME = 2


def cifra_grande(px, testo, x, y, colore, scala=2):
    """Il font 3x5 del progetto, ingrandito: ogni pixel diventa un quadrato.

    Non un TTF: un carattere vettoriale rimpicciolito su un pannello LED
    diventa poltiglia. Ingrandire un font a pixel lo lascia netto.
    """
    for carattere in str(testo):
        glifo = _F.get(carattere)
        if glifo is not None:
            for riga, bit in enumerate(glifo):
                for colonna in range(3):
                    if bit & (1 << (2 - colonna)):
                        for dx in range(scala):
                            for dy in range(scala):
                                xx = x + colonna * scala + dx
                                yy = y + riga * scala + dy
                                if 0 <= xx < LARGHEZZA and 0 <= yy < ALTEZZA:
                                    px[xx, yy] = colore
        x += 4 * scala


def larghezza_grande(testo, scala=2):
    return max(0, len(str(testo)) * 4 * scala - scala)


class Pongo(Gioco):
    nome = "pongo"
    etichetta = "Pongo"
    colore_hud = COLORE_TU

    COMANDI = ("su", "giu", "sinistra", "destra", "fuoco", "avvia", "esci")

    def __init__(self, seme=None, livello=LIVELLO_PREDEFINITO):
        self.difficolta = livello if livello in LIVELLI else LIVELLO_PREDEFINITO
        super().__init__(seme)

    # ------------------------------------------------------------ impostazioni

    def configura(self, conf):
        """Il livello dalla pagina Giochi. Vale dalla prossima battuta."""
        scelto = str((conf or {}).get("pongo_livello") or LIVELLO_PREDEFINITO)
        self.difficolta = scelto if scelto in LIVELLI else LIVELLO_PREDEFINITO
        self.livello = NUMERO_LIVELLO[self.difficolta]

    def parametri(self):
        return LIVELLI[self.difficolta]

    # --------------------------------------------------------------- partita

    def avvia_partita(self, seme=None):
        if seme is not None or not hasattr(self, "_rnd"):
            self._rnd = random.Random(seme)
        self.tu = 0
        self.cpu = 0
        self.punteggio = 0
        # Nessuna vita: in Pong si perde a punti. Il tabellone comune le
        # mostrerebbe, qui non c'e' e restano a zero.
        self.vite = 0
        self.livello = NUMERO_LIVELLO[self.difficolta]
        self.finita = False
        self.iniziata = False
        self.scambio = 0            # colpi di racchetta di questo scambio
        self.y_tu = (ALTEZZA - RACCHETTA_H) / 2.0
        self.x_tu = float(X_SINISTRA)
        self._avanza = False
        self.y_cpu = (ALTEZZA - RACCHETTA_H) / 2.0
        self._eventi = []
        self.suoni_del_frame = ()
        # Il primo servizio va verso di te: e' la tua partita, cominci a
        # rispondere tu.
        self._metti_in_campo(verso=-1)

    def _metti_in_campo(self, verso):
        """La pallina al centro, ferma, in attesa della battuta."""
        self.bx = (LARGHEZZA - PALLA) / 2.0
        self.by = (ALTEZZA - PALLA) / 2.0
        self.vx = 0.0
        self.vy = 0.0
        self.velocita = VELOCITA_INIZIALE
        self._verso_battuta = verso
        self._attesa = PAUSA_SERVIZIO
        self.scambio = 0
        self._bersaglio = None
        self._pensa_fra = None

    def _battuta(self):
        angolo = self._rnd.uniform(-0.45, 0.45)
        self.vx = math.cos(angolo) * self.velocita * self._verso_battuta
        self.vy = math.sin(angolo) * self.velocita
        # Si parte da un punto a caso della rete: sempre dal centro
        # esatto, dopo tre battute il giocatore sa gia' dove andare.
        self.by = self._rnd.uniform(12, ALTEZZA - 12 - PALLA)
        self._pensa_fra = None
        self._bersaglio = None
        if self.vx > 0:
            self._verso_cpu()

    def in_gioco(self):
        return self.vx != 0.0

    # --------------------------------------------------------------- record

    # Il record di Pongo e' lo **scambio piu' lungo**: e' l'unico numero che
    # cresce con la bravura e non con il tempo passato a giocare.
    def record(self):
        return max(self._record, self.scambio)

    def _aggiorna_record(self):
        self._record = max(self._record, self.scambio)

    def stato(self):
        fuori = super().stato()
        fuori.update({"tu": self.tu, "cpu": self.cpu,
                      "difficolta": self.difficolta, "scambio": self.scambio})
        return fuori

    # ---------------------------------------------------------------- suono

    def _segna(self, nome):
        self._eventi.append(nome)

    def _emetti(self):
        eventi, self._eventi = self._eventi, []
        scelti = [n for n in ORDINE if n in eventi][:SUONI_PER_FRAME]
        self.suoni_del_frame = tuple(scelti)
        for nome in scelti:
            self.suona(nome)

    # ---------------------------------------------------------------- passo

    def passo(self, dt, tasti):
        self._dt_corrente = dt
        self._eventi = []
        try:
            self._fisica(dt, tasti)
        finally:
            self._emetti()

    def _fisica(self, dt, tasti):
        if self.finita:
            if "fuoco" in tasti:
                self.avvia_partita()
                self.iniziata = True
            return

        # Prima di cominciare la racchetta sta ferma. Fino alla 10.5 si
        # muoveva anche li', sotto la scritta centrale: il riquadro nero della
        # scritta la copriva, e sul pannello sembravano zone oscurate che
        # mangiavano il cursore. La scritta e' un invito a premere fuoco, non
        # un campo di gioco.
        if not self.iniziata:
            if "fuoco" in tasti:
                self.iniziata = True
            return

        # Da qui si muove sempre, anche fra un punto e l'altro: e' li' che
        # ci si rimette in posizione.
        self.y_tu = self._muovi(self.y_tu, tasti)
        self.x_tu = self._avanti(self.x_tu, tasti)

        self._mossa_destra(dt)

        if not self.in_gioco():
            self._attesa -= dt
            if self._attesa <= 0:
                self._battuta()
            return

        distanza = math.hypot(self.vx, self.vy) * dt
        passi = max(1, int(distanza) + 1)
        for _ in range(passi):
            if not self.in_gioco() or self.finita:
                break
            self._micro_passo(dt / passi)

    def _muovi(self, y, tasti):
        dt = self._dt_corrente
        if "su" in tasti:
            y -= RACCHETTA_V * dt
        if "giu" in tasti:
            y += RACCHETTA_V * dt
        return max(0.0, min(ALTEZZA - RACCHETTA_H, y))

    def _avanti(self, x, tasti):
        """Avanti e indietro, dentro la prima meta' del tuo campo."""
        dt = self._dt_corrente
        self._avanza = "destra" in tasti and "sinistra" not in tasti
        if "destra" in tasti:
            x += RACCHETTA_VX * dt
        if "sinistra" in tasti:
            x -= RACCHETTA_VX * dt
        return max(float(X_SINISTRA), min(float(X_AVANTI), x))

    # `_muovi` usa il dt del fotogramma, annotato da `passo`: cosi' ha la
    # stessa firma per le due racchette, e servira' al secondo giocatore.
    _dt_corrente = 1.0 / 30

    def _micro_passo(self, dt):
        self.bx += self.vx * dt
        self.by += self.vy * dt

        if self.by <= 0:
            self.by = 0.0
            self.vy = abs(self.vy)
            self._segna("sponda")
        elif self.by >= ALTEZZA - PALLA:
            self.by = float(ALTEZZA - PALLA)
            self.vy = -abs(self.vy)
            self._segna("sponda")

        colonna_tu = int(round(self.x_tu))
        if self.vx < 0 and self._tocca(colonna_tu, self.y_tu):
            self.bx = float(colonna_tu + RACCHETTA_L)
            self._rimanda(self.y_tu, verso=1, schiaccia=self._avanza)
        elif self.vx > 0 and self._tocca(X_DESTRA, self.y_cpu):
            self.bx = float(X_DESTRA - PALLA)
            self._rimanda(self.y_cpu, verso=-1)

        if self.bx + PALLA < 0:
            self._punto(chi="cpu")
        elif self.bx > LARGHEZZA:
            self._punto(chi="tu")

    def _tocca(self, x, y):
        """La pallina e' sulla colonna della racchetta e ne copre l'altezza."""
        if not (x - PALLA <= self.bx <= x + RACCHETTA_L):
            return False
        return y - PALLA < self.by < y + RACCHETTA_H

    def _rimanda(self, y_racchetta, verso, schiaccia=False):
        centro = y_racchetta + RACCHETTA_H / 2.0
        scarto = (self.by + PALLA / 2.0 - centro) / (RACCHETTA_H / 2.0)
        angolo = max(-1.0, min(1.0, scarto)) * ANGOLO_MAX
        spinta = ACCELERAZIONE * (SCHIACCIATA if schiaccia else 1.0)
        self.velocita = min(VELOCITA_MASSIMA, self.velocita * spinta)
        self.vx = math.cos(angolo) * self.velocita * verso
        self.vy = math.sin(angolo) * self.velocita
        self.scambio += 1
        self._aggiorna_record()
        self._segna("ping")
        if verso > 0:
            self._verso_cpu()
        else:
            self._bersaglio = None
            self._pensa_fra = None

    def _punto(self, chi):
        if chi == "tu":
            self.tu += 1
            self._segna("punto")
            verso = 1               # la battuta va verso chi ha perso il punto
        else:
            self.cpu += 1
            self._segna("persa")
            verso = -1
        self.punteggio = self.tu
        self._aggiorna_record()
        if max(self.tu, self.cpu) >= PUNTI_PER_VINCERE:
            self.finita = True
            self.vx = self.vy = 0.0
            return
        self._metti_in_campo(verso)

    # ------------------------------------------------------------ il computer

    def _verso_cpu(self):
        """La pallina ha appena preso la strada del computer."""
        self._pensa_fra = self.parametri()["reazione"]
        self._bersaglio = None

    def arrivo(self):
        """Dove arrivera' la pallina sulla colonna del computer, sponde comprese.

        E' il conto esatto: l'errore lo aggiunge `_mossa_destra`, una volta
        per scambio. Un errore ricalcolato a ogni fotogramma farebbe tremare
        la racchetta invece di mandarla nel posto sbagliato con convinzione.
        """
        if self.vx <= 0:
            return None
        tempo = (X_DESTRA - PALLA - self.bx) / self.vx
        y = self.by + self.vy * tempo
        alto = ALTEZZA - PALLA
        # Le sponde riflettono: si "srotola" il campo in una striscia infinita
        # e si ripiega. Periodo: due altezze.
        periodo = 2.0 * alto
        y = y % periodo
        if y > alto:
            y = periodo - y
        return y

    def _mossa_destra(self, dt):
        p = self.parametri()
        obiettivo = (ALTEZZA - RACCHETTA_H) / 2.0       # a riposo, al centro
        if self.in_gioco() and self.vx > 0:
            if self._pensa_fra is not None:
                self._pensa_fra -= dt
                if self._pensa_fra <= 0:
                    self._pensa_fra = None
                    stima = self.arrivo()
                    if stima is not None:
                        rapporto = self.velocita / VELOCITA_INIZIALE
                        errore = self._rnd.gauss(0.0, p["errore"] * rapporto)
                        self._bersaglio = stima + errore
            if self._bersaglio is not None:
                obiettivo = self._bersaglio + PALLA / 2.0 - RACCHETTA_H / 2.0
            else:
                obiettivo = self.y_cpu        # non ha ancora deciso: sta fermo
        passo = p["velocita"] * dt
        differenza = obiettivo - self.y_cpu
        if abs(differenza) <= passo:
            self.y_cpu = obiettivo
        else:
            self.y_cpu += passo if differenza > 0 else -passo
        self.y_cpu = max(0.0, min(ALTEZZA - RACCHETTA_H, self.y_cpu))

    # -------------------------------------------------------------- disegno

    def disegna(self):
        # Senza il tabellone comune: vedi l'intestazione.
        from PIL import Image
        img = Image.new("RGB", (LARGHEZZA, ALTEZZA), (0, 0, 0))
        px = img.load()
        self.disegna_campo(img, px)
        if self.finita:
            self._disegna_fine(px)
        return img

    def disegna_campo(self, img, px):
        meta = LARGHEZZA // 2
        # La rete: trattini di due pixel, uno si' e uno no.
        for y in range(0, ALTEZZA, 4):
            for dy in range(2):
                px[meta - 1, y + dy] = COLORE_RETE
                px[meta, y + dy] = COLORE_RETE

        # I punti, grandi e un po' spenti: la pallina ci passa sopra e deve
        # restare lei la cosa piu' luminosa del pannello.
        sinistro = str(self.tu)
        cifra_grande(px, sinistro, meta - 8 - larghezza_grande(sinistro), 3,
                     COLORE_PUNTI)
        cifra_grande(px, str(self.cpu), meta + 8, 3, COLORE_PUNTI)

        for colonna, y, colore in ((int(round(self.x_tu)), self.y_tu, COLORE_TU),
                                   (X_DESTRA, self.y_cpu, COLORE_CPU)):
            for dx in range(RACCHETTA_L):
                for dy in range(RACCHETTA_H):
                    yy = int(round(y)) + dy
                    if 0 <= yy < ALTEZZA:
                        px[colonna + dx, yy] = colore

        if not self.finita and (self.in_gioco() or self.iniziata):
            for dx in range(PALLA):
                for dy in range(PALLA):
                    x, y = int(self.bx) + dx, int(self.by) + dy
                    if 0 <= x < LARGHEZZA and 0 <= y < ALTEZZA:
                        px[x, y] = COLORE_PALLA

        if not self.iniziata and not self.finita:
            self._riquadro(px, 36, 52)
            centra(px, "FUOCO PER INIZIARE", 39, (150, 150, 160),
                   larghezza=LARGHEZZA)
            centra(px, self.difficolta.upper(), 47, COLORE_CPU,
                   larghezza=LARGHEZZA)

    def _riquadro(self, px, alto, basso):
        """Il fondo nero delle scritte, largo quanto la scritta piu' lunga
        (19 caratteri, 75 pixel) e non di piu': dalla colonna 86 alla 170.
        Tu arrivi al massimo alla 64, il computer sta alla 250, quindi il
        riquadro non copre mai una racchetta."""
        for y in range(alto, basso):
            for x in range(86, 171):
                px[x, y] = (0, 0, 0)

    def _disegna_fine(self, px):
        self._riquadro(px, 34, 54)
        if self.tu > self.cpu:
            centra(px, "HAI VINTO!", 37, COLORE_TU, larghezza=LARGHEZZA)
        else:
            centra(px, "VINCE IL PANNELLO", 37, COLORE_CPU,
                   larghezza=LARGHEZZA)
        centra(px, "FUOCO PER RIGIOCARE", 45, (150, 150, 160),
               larghezza=LARGHEZZA)

