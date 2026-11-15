# -*- coding: utf-8 -*-
# fix-v3 2026-10-31
"""Blocchi: pezzi che cadono, righe che si chiudono.

Il nome
-------
Il gioco dei blocchi che cadono ha un nome suo, ed e' un marchio: resta suo.
Lo schema -- pezzi da quattro celle che cadono in un pozzo, righe complete
che si chiudono -- non e' di nessuno, come per tutti gli altri giochi del
catalogo. Questo e' Blocchi: codice scritto da zero contro il contratto di
`Gioco`, nome nostro, tavolozza nostra, pozzo nostro (10x18, non 10x20),
punteggi nostri, nessuna musica presa in prestito.

Il gioco
--------
* Sette pezzi da quattro celle, estratti a sacco: il sacco si mescola e si
  svuota prima di ricominciare, cosi' nessun pezzo resta via per sempre e
  nessuno arriva tre volte di fila per puro caso.
* Sinistra e destra muovono (con ripetizione: scatto, pausa, scorrimento),
  giu' e' la discesa morbida e vale un punto a cella, fuoco ruota -- solo
  fuoco: il su non ruota, e fra una rotazione e l'altra passa almeno un
  attimo, cosi' un fuoco rimbalzato non gira due volte -- il tasto
  speciale e' la caduta secca e vale due punti a cella.
* Il pezzo a terra non si fissa subito: mezzo secondo di grazia, e muoverlo
  o ruotarlo lo prolunga -- fino a quindici volte, poi basta.
* L'ombra sul fondo dice dove il pezzo andra' a finire se lo si lascia.
* Una riga chiusa lampeggia e sparisce: 100, 300, 600, 1000 punti per una,
  due, tre, quattro righe, moltiplicati per il livello. Ogni dieci righe il
  livello sale e la caduta accelera.
* Si perde quando un pezzo nuovo non ha posto per nascere.
* All'apertura la partita sta ferma sulla schermata del titolo -- il
  nome e «FUOCO PER PARTIRE», come nei giochi di serie: il primo pezzo
  cade solo quando si preme fuoco, e quella pressione e' spesa li',
  non ruota niente.
"""

import random

from PIL import ImageDraw

from .base import Gioco, centra, larghezza_testo, scrivi

COLONNE = 10
RIGHE = 18

# Le forme: sette pezzi da quattro celle, coordinate (x, y) dello stato zero.
# Le rotazioni si **calcolano** -- si gira la figura dentro il suo rettangolo
# e si riporta l'angolo a zero -- non si copiano da nessuna tabella.
FORME = {
    "I": ((0, 1), (1, 1), (2, 1), (3, 1)),
    "O": ((1, 0), (2, 0), (1, 1), (2, 1)),
    "T": ((1, 0), (0, 1), (1, 1), (2, 1)),
    "S": ((1, 0), (2, 0), (0, 1), (1, 1)),
    "Z": ((0, 0), (1, 0), (1, 1), (2, 1)),
    "J": ((0, 0), (0, 1), (1, 1), (2, 1)),
    "L": ((2, 0), (0, 1), (1, 1), (2, 1)),
}

# Una tavolozza nostra: nessun colore sta sul pezzo dove lo mette il gioco
# famoso. I colori pieni e accesi sono anche la scelta giusta sul pannello:
# le intensita' intermedie sono la causa dello sfarfallio, non il numero dei
# colori.
COLORI = {
    "I": (255, 122, 26),
    "O": (240, 216, 84),
    "T": (168, 96, 255),
    "S": (64, 214, 120),
    "Z": (255, 77, 94),
    "J": (64, 120, 255),
    "L": (38, 214, 205),
}

# I punti delle righe chiuse in un colpo solo, per livello.
PUNTI_RIGHE = {1: 100, 2: 300, 3: 600, 4: 1000}

CADUTA_BASE = 0.80        # secondi per cella, al livello 1
CADUTA_MIN = 0.05         # piu' veloce di cosi' non si cade
FATTORE_LIVELLO = 0.85    # ogni livello la caduta si accorcia del 15%
DISCESA_MORBIDA = 0.03    # secondi per cella col giu' premuto
RITARDO_BLOCCO = 0.50     # la grazia del pezzo a terra, in secondi
MAX_RESET_BLOCCO = 15     # quante volte la grazia si puo' prolungare
PAUSA_RIGHE = 0.18        # quanto lampeggiano le righe prima di sparire
RITARDO_RIPETIZIONE = 0.17
PASSO_RIPETIZIONE = 0.05
ATTESA_ROTAZIONE = 0.18   # fra una rotazione e l'altra, in secondi


def _normalizza(celle):
    """Porta l'angolo alto-sinistra della figura a (0, 0)."""
    mx = min(x for x, _y in celle)
    my = min(y for _x, y in celle)
    return tuple(sorted((x - mx, y - my) for x, y in celle))


def _ruota(celle):
    """La figura girata di un quarto, dentro il suo rettangolo."""
    altezza = max(y for _x, y in celle) + 1
    return _normalizza(tuple((altezza - 1 - y, x) for x, y in celle))


def _stati(celle):
    """Gli stati di rotazione distinti di una forma, in ordine."""
    stati = []
    corrente = _normalizza(celle)
    for _ in range(4):
        if corrente in stati:
            break
        stati.append(corrente)
        corrente = _ruota(corrente)
    return stati


STATI = {nome: _stati(celle) for nome, celle in FORME.items()}


class Blocchi(Gioco):
    nome = "blocchi"
    etichetta = "Blocchi"
    colore_hud = (255, 122, 26)
    COMANDI = ("sinistra", "destra", "su", "giu", "fuoco", "speciale",
               "avvia", "esci")
    TELA_LIBERA = True

    # ------------------------------------------------------------- la partita

    def avvia_partita(self, seme=None):
        self._rng = random.Random(seme)
        self.griglia = [[None] * COLONNE for _ in range(RIGHE)]
        self.righe = 0
        self.punteggio = 0
        self.livello = 1
        self.vite = 1
        self.finita = False
        self.iniziata = False
        self._sacco = []
        self._prec = set()
        self._rip = {}
        self._caduta = 0.0
        self._blocco = 0.0
        self._reset = 0
        self._attesa = 0.0
        self._attesa_rotazione = 0.0
        self._da_togliere = []
        self._posa_geometria()
        self.prossimo = self._pesca()
        self._nuovo_pezzo()

    def ignora_tasti(self, premuti):
        """Il tasto che ha aperto la partita non deve ruotare il primo pezzo."""
        self._prec = set(premuti)

    def _posa_geometria(self):
        """La cella la decide la tela: il pozzo e il suo fianco devono starci.

        Cinque colonne di riserva nel conto della larghezza: quattro per il
        pezzo in anteprima e una di aria. La cella non e' quadrata: l'altezza
        viene dalle righe, e la larghezza la segue allungata del 70% --
        finche' pozzo e fianco stanno nel campo -- cosi' i mattoni sono
        rettangoli e il pozzo si allarga. Sul pannello la cella viene da
        5x3 pixel (pozzo 50x54), sullo schermo alto da 14x8 (pozzo 140x144).
        """
        self.cella_a = max(2, self.campo_a // RIGHE)
        self.cella_l = max(2, min(self.campo_l // (COLONNE + 5),
                                  round(self.cella_a * 1.7)))
        self.pozzo_l = COLONNE * self.cella_l
        self.pozzo_a = RIGHE * self.cella_a
        self.laterale = 4 * self.cella_l + 6
        gruppo = self.pozzo_l + 4 + self.laterale
        self.ox = self.campo_x + max(0, (self.campo_l - gruppo) // 2)
        self.ox = max(self.campo_x + 1, self.ox)
        # Un pixel di bordo anche sotto: il pozzo sta un pixel sopra il fondo
        # del campo, cosi' il suo bordo inferiore non cade fuori dalla tela.
        self.oy = max(self.campo_y, self.campo_y + self.campo_a
                      - self.pozzo_a - 1)
        self.px0 = self.ox + self.pozzo_l + 4

    # ------------------------------------------------------------- i pezzi

    def _pesca(self):
        if not self._sacco:
            self._sacco = list(FORME)
            self._rng.shuffle(self._sacco)
        return self._sacco.pop()

    def _celle(self):
        return STATI[self.pezzo][self.stato]

    def _collide(self, celle, x, y):
        for cx, cy in celle:
            gx, gy = x + cx, y + cy
            if gx < 0 or gx >= COLONNE or gy >= RIGHE:
                return True
            if gy >= 0 and self.griglia[gy][gx] is not None:
                return True
        return False

    def _nuovo_pezzo(self):
        self.pezzo = self.prossimo
        self.prossimo = self._pesca()
        self.stato = 0
        celle = self._celle()
        larg = max(x for x, _y in celle) + 1
        self.x = (COLONNE - larg) // 2
        self.y = 0
        self._caduta = 0.0
        self._blocco = 0.0
        self._reset = 0
        # Gli stati sono normalizzati -- ogni pezzo ha una cella nella sua
        # riga zero -- quindi se alla nascita il posto e' preso non c'e' un
        # "piano di sopra" dove rifugiarsi: la partita e' finita.
        if self._collide(celle, self.x, self.y):
            self.finita = True
            self.suona("persa")

    def _a_terra(self):
        return self._collide(self._celle(), self.x, self.y + 1)

    def _tocco_terra(self):
        """Muovere o ruotare un pezzo a terra prolunga la grazia -- con misura."""
        if self._a_terra() and self._reset < MAX_RESET_BLOCCO:
            self._blocco = 0.0
            self._reset += 1

    def _muovi(self, dx):
        if self._collide(self._celle(), self.x + dx, self.y):
            return False
        self.x += dx
        self._tocco_terra()
        return True

    def _ruota_pezzo(self):
        stati = STATI[self.pezzo]
        nuovo = (self.stato + 1) % len(stati)
        # Se contro il muro la rotazione non ci sta, il pezzo si sposta di
        # quello che serve: sono i calci alle pareti, ridotti all'osso.
        for dx in (0, -1, 1, -2, 2):
            if not self._collide(stati[nuovo], self.x + dx, self.y):
                self.stato = nuovo
                self.x += dx
                self._tocco_terra()
                return True
        return False

    def _intervallo(self):
        return max(CADUTA_MIN,
                   CADUTA_BASE * (FATTORE_LIVELLO ** (self.livello - 1)))

    def _caduta_secca(self):
        celle = self._celle()
        passi = 0
        while not self._collide(celle, self.x, self.y + 1):
            self.y += 1
            passi += 1
        self.punteggio += 2 * passi
        self._fissa()

    def _fissa(self):
        """Il pezzo diventa pozzo. Poi: righe chiuse, o pezzo nuovo."""
        colore = COLORI[self.pezzo]
        for cx, cy in self._celle():
            gx, gy = self.x + cx, self.y + cy
            if 0 <= gx < COLONNE and 0 <= gy < RIGHE:
                self.griglia[gy][gx] = colore
        self.suona("muro")
        piene = [r for r in range(RIGHE)
                 if all(self.griglia[r][c] is not None
                        for c in range(COLONNE))]
        if not piene:
            self._nuovo_pezzo()
            return
        prima = self.livello
        self.punteggio += PUNTI_RIGHE[len(piene)] * self.livello
        self.righe += len(piene)
        self.livello = 1 + self.righe // 10
        self._da_togliere = piene
        self._attesa = PAUSA_RIGHE
        self.suona("mattone%d" % self._rng.randint(1, 5))
        if self.livello > prima:
            self.suona("livello")

    def _chiudi_righe(self):
        restano = [self.griglia[r] for r in range(RIGHE)
                   if r not in self._da_togliere]
        vuote = [[None] * COLONNE for _ in self._da_togliere]
        self.griglia = vuote + restano
        self._da_togliere = []
        self._nuovo_pezzo()

    # ---------------------------------------------------------------- passo

    def passo(self, dt, tasti):
        if self.finita:
            if "fuoco" in tasti:
                self.avvia_partita()
                self.iniziata = True
                # Il fuoco che riapre la partita e' gia' speso: resta fra
                # i precedenti, cosi' tenerlo premuto non ruota il primo
                # pezzo della partita nuova.
                self._prec = set(tasti)
            return
        if not self.iniziata:
            # La schermata del titolo, come nei giochi di serie: il pozzo
            # sta fermo e si parte solo col fuoco, sul fronte di salita.
            # La pressione che fa partire e' spesa li': resta fra i
            # precedenti, e il primo pezzo non ruota da solo.
            if "fuoco" in tasti - self._prec:
                self.iniziata = True
            self._prec = set(tasti)
            return
        if self._attesa > 0.0:
            # Le righe chiuse lampeggiano: il mondo si ferma un istante.
            self._attesa -= dt
            if self._attesa <= 0.0:
                self._chiudi_righe()
            self._prec = set(tasti)
            return
        nuovi = tasti - self._prec
        # Ruota solo il fuoco, e non a raffica: fra una rotazione e l'altra
        # deve passare ATTESA_ROTAZIONE. Un fuoco che arriva dentro
        # l'attesa non ruota e non si mette in coda: e' perso, come un
        # rimbalzo del pulsante.
        if self._attesa_rotazione > 0.0:
            self._attesa_rotazione = max(0.0, self._attesa_rotazione - dt)
        if "fuoco" in nuovi and self._attesa_rotazione <= 0.0:
            if self._ruota_pezzo():
                self._attesa_rotazione = ATTESA_ROTAZIONE
        if "speciale" in nuovi:
            self._caduta_secca()
            self._prec = set(tasti)
            return
        for comando, dx in (("sinistra", -1), ("destra", 1)):
            if comando not in tasti:
                self._rip.pop(comando, None)
                continue
            if comando in nuovi:
                self._muovi(dx)
                self._rip[comando] = RITARDO_RIPETIZIONE
            else:
                conto = self._rip.get(comando, RITARDO_RIPETIZIONE) - dt
                while conto <= 0.0:
                    self._muovi(dx)
                    conto += PASSO_RIPETIZIONE
                self._rip[comando] = conto
        morbida = "giu" in tasti
        intervallo = self._intervallo()
        if morbida:
            intervallo = min(intervallo, DISCESA_MORBIDA)
        self._caduta += dt
        while self._caduta >= intervallo:
            self._caduta -= intervallo
            if self._collide(self._celle(), self.x, self.y + 1):
                self._caduta = 0.0
                break
            self.y += 1
            self._blocco = 0.0
            if morbida:
                self.punteggio += 1
        if self._a_terra():
            self._blocco += dt
            if self._blocco >= RITARDO_BLOCCO:
                self._fissa()
        self._prec = set(tasti)

    # --------------------------------------------------------------- disegno

    def _cella_a(self, dis, x0, y0, colore):
        """Una cella piena alle coordinate date, con bordo e luce se ci stanno."""
        larg, alto = self.cella_l, self.cella_a
        dis.rectangle([x0, y0, x0 + larg - 1, y0 + alto - 1], fill=colore)
        # Bordo e luce si giudicano dal lato corto: e' lui che decide se
        # dentro la cella c'e' posto per disegnarli.
        piccola = min(larg, alto)
        if piccola >= 4:
            scuro = tuple(v // 3 for v in colore)
            dis.rectangle([x0, y0, x0 + larg - 1, y0 + alto - 1],
                          outline=scuro)
        if piccola >= 6:
            chiaro = tuple(min(255, v + 60) for v in colore)
            dis.point((x0 + 1, y0 + 1), fill=chiaro)

    def _cella_griglia(self, dis, gx, gy, colore):
        self._cella_a(dis, self.ox + gx * self.cella_l,
                      self.oy + gy * self.cella_a, colore)

    def _fantasma(self, dis, gx, gy):
        if gy < 0:
            return
        x0 = self.ox + gx * self.cella_l
        y0 = self.oy + gy * self.cella_a
        dis.rectangle([x0, y0, x0 + self.cella_l - 1, y0 + self.cella_a - 1],
                      outline=(52, 52, 62))

    def _y_fantasma(self):
        celle = self._celle()
        y = self.y
        while not self._collide(celle, self.x, y + 1):
            y += 1
        return y

    def disegna_campo(self, img, px):
        dis = ImageDraw.Draw(img)
        dis.rectangle([self.ox - 1, self.oy - 1,
                       self.ox + self.pozzo_l, self.oy + self.pozzo_a],
                      fill=(8, 8, 12), outline=(64, 64, 76))
        lampeggio = self._attesa > 0.0
        for gy in range(RIGHE):
            for gx in range(COLONNE):
                colore = self.griglia[gy][gx]
                if colore is None:
                    continue
                if lampeggio and gy in self._da_togliere:
                    colore = (255, 255, 255)
                self._cella_griglia(dis, gx, gy, colore)
        if not self.finita and not lampeggio:
            celle = self._celle()
            yf = self._y_fantasma()
            if yf != self.y:
                for cx, cy in celle:
                    self._fantasma(dis, self.x + cx, yf + cy)
            for cx, cy in celle:
                if self.y + cy >= 0:
                    self._cella_griglia(dis, self.x + cx, self.y + cy,
                                        COLORI[self.pezzo])
        # Il fianco: il prossimo pezzo, e le righe chiuse finora.
        scrivi(px, "NEXT", self.px0, self.oy + 1, (120, 120, 130))
        celle = STATI[self.prossimo][0]
        larg = (max(x for x, _y in celle) + 1) * self.cella_l
        alto = (max(y for _x, y in celle) + 1) * self.cella_a
        bx = self.px0 + (4 * self.cella_l - larg) // 2
        by = self.oy + 8 + (2 * self.cella_a - alto) // 2
        for cx, cy in celle:
            self._cella_a(dis, bx + cx * self.cella_l,
                          by + cy * self.cella_a, COLORI[self.prossimo])
        fine = self.oy + 8 + 2 * self.cella_a
        scrivi(px, "LIN", self.px0, fine + 3, (120, 120, 130))
        scrivi(px, "%d" % self.righe, self.px0, fine + 10, self.colore_hud)
        if not self.iniziata and not self.finita:
            self._disegna_titolo(dis, px)

    def _disegna_titolo(self, dis, px):
        """La schermata del titolo: nome e invito, come nei giochi di serie.

        Il pozzo resta disegnato sotto, fermo al fotogramma zero, e sopra
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
        centra(px, "BLOCCHI", meta - 5, self.colore_hud)
        centra(px, "FUOCO PER PARTIRE", meta + 3, (150, 150, 160))
