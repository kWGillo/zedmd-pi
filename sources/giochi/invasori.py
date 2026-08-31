# -*- coding: utf-8 -*-
"""Invaders, riscritto per 256x64.

Il gioco originale e' **verticale** — 224x256 — e la sua tensione sta tutta
nella discesa: cinque file che si avvicinano finche' non ti sono addosso. Su
sessantaquattro righe quella discesa non ci sta cinque volte, e schiacciarla
vorrebbe dire alieni alti due pixel.

Il compromesso e' dichiarato: **tre file invece di cinque**, sprite alti
cinque pixel, e una discesa di due pixel per sponda. Quello che si guadagna e'
la larghezza — otto colonne con spazio vero per schivare — e un tabellone che
sull'originale non c'era posto per mettere.
"""

import random

from .base import ALTEZZA, CAMPO, Gioco, centra

# Sprite 8x5, due pose per l'animazione: gli alieni dell'originale cambiano
# forma a ogni passo, ed e' quello che li fa sembrare vivi invece che
# trascinati.
ALIENI = (
    ((0b00111100, 0b01111110, 0b11011011, 0b01111110, 0b01000010),
     (0b00111100, 0b01111110, 0b11011011, 0b01111110, 0b10000001)),
    ((0b00011000, 0b00111100, 0b01111110, 0b11011011, 0b01000010),
     (0b00011000, 0b00111100, 0b01111110, 0b11011011, 0b00100100)),
    ((0b01000010, 0b00111100, 0b01111110, 0b01011010, 0b01100110),
     (0b01000010, 0b10111101, 0b11111111, 0b01011010, 0b00100100)),
)
COLORI = ((90, 200, 255), (120, 255, 120), (255, 200, 60))
PUNTI = (30, 20, 10)

NAVE = (0b00010000, 0b00111000, 0b01111100, 0b11111111)
NAVE_COLORE = (255, 140, 26)

COLONNE = 8
FILE = 3
PASSO_X = 18            # distanza fra due colonne
PASSO_Y = 10            # distanza fra due file
LARGO_ALIENO = 8
ALTO_ALIENO = 5

Y_NAVE = 58
ALTA_NAVE = 4
LARGA_NAVE = 8
Y_FONDO = Y_NAVE - 1    # sotto questa riga gli alieni hanno vinto

BUNKER_Y = 46
BUNKER_LARGO = 14
BUNKER_ALTO = 5


class Invasori(Gioco):
    nome = "invaders"
    etichetta = "Invaders"
    colore_hud = (120, 255, 120)

    def avvia_partita(self, seme=None):
        self._rnd = random.Random(seme)
        self.punteggio = 0
        self.vite = 3
        self.livello = 1
        self.finita = False
        self._nuovo_livello()

    def _nuovo_livello(self):
        # (colonna, fila) -> vivo. La fila 0 e' la piu' in alto e vale di piu'.
        self.alieni = {(c, f): True for c in range(COLONNE) for f in range(FILE)}
        self.ax = 8.0                       # angolo alto-sinistro della schiera
        self.ay = 3.0 + min(6, (self.livello - 1) * 2)
        self.dir = 1
        self.posa = 0
        self._da_passo = 0.0
        self.nave_x = CAMPO / 2.0 - LARGA_NAVE / 2
        self.colpo = None                   # [x, y] del proiettile del giocatore
        self.bombe = []                     # [[x, y], ...] degli alieni
        self._da_bomba = 0.0
        self._pausa = 1.0                   # un istante prima di cominciare
        self._bunker = self._nuovi_bunker()

    def _nuovi_bunker(self):
        """Tre ripari fatti di pixel: si consumano dove vengono colpiti."""
        ripari = []
        for i in range(3):
            x0 = 24 + i * 56
            blocchi = set()
            for x in range(BUNKER_LARGO):
                for y in range(BUNKER_ALTO):
                    # Un arco: la fila in basso al centro resta aperta.
                    if y >= BUNKER_ALTO - 2 and 5 <= x <= 8:
                        continue
                    blocchi.add((x0 + x, BUNKER_Y + y))
            ripari.append(blocchi)
        return ripari

    # ------------------------------------------------------------------ passo

    def vivi(self):
        return sum(1 for v in self.alieni.values() if v)

    def _pos(self, colonna, fila):
        return (self.ax + colonna * PASSO_X, self.ay + fila * PASSO_Y)

    def _intervallo_passo(self):
        """Piu' alieni restano, piu' la schiera e' lenta: e' il cuore del gioco.

        Nell'originale non e' una scelta di progetto ma un effetto del
        disegnarli uno per volta; qui si riproduce apposta, perche' senza
        quell'accelerazione finale il gioco non ha una fine emotiva.
        """
        rimasti = max(1, self.vivi())
        totale = COLONNE * FILE
        veloce = 0.055
        lento = 0.55 - 0.04 * min(5, self.livello - 1)
        return veloce + (lento - veloce) * (rimasti - 1) / max(1, totale - 1)

    def passo(self, dt, tasti):
        if self.finita:
            if "fuoco" in tasti:
                self.avvia_partita()
            return
        if self._pausa > 0:
            self._pausa -= dt
            return

        # --- la nave
        velocita = 62.0
        if "sinistra" in tasti:
            self.nave_x -= velocita * dt
        if "destra" in tasti:
            self.nave_x += velocita * dt
        self.nave_x = max(1.0, min(CAMPO - LARGA_NAVE - 1, self.nave_x))

        # Un colpo per volta, come nell'originale: e' quello che rende il
        # tempismo una scelta invece di una raffica.
        if "fuoco" in tasti and self.colpo is None:
            self.colpo = [self.nave_x + LARGA_NAVE / 2, float(Y_NAVE - 1)]

        # --- la schiera
        self._da_passo -= dt
        if self._da_passo <= 0:
            self._da_passo = self._intervallo_passo()
            self._muovi_schiera()

        # --- proiettili
        self._muovi_colpo(dt)
        self._muovi_bombe(dt)

        # --- fine livello
        if self.vivi() == 0:
            self.livello += 1
            self.punteggio += 50
            self._aggiorna_record()
            self._nuovo_livello()

    def _muovi_schiera(self):
        self.posa ^= 1
        colonne_vive = [c for c in range(COLONNE)
                        if any(self.alieni.get((c, f)) for f in range(FILE))]
        if not colonne_vive:
            return
        sinistra = self.ax + min(colonne_vive) * PASSO_X
        destra = self.ax + max(colonne_vive) * PASSO_X + LARGO_ALIENO
        if (self.dir > 0 and destra >= CAMPO - 2) or (self.dir < 0 and sinistra <= 2):
            self.dir *= -1
            self.ay += 2
        else:
            self.ax += 2 * self.dir

        # Arrivati in fondo hanno vinto loro, e la partita finisce: non e' una
        # vita persa, e' la fine. Toglierne una sola vorrebbe dire ricominciare
        # con la schiera gia' addosso.
        file_vive = [f for f in range(FILE)
                     if any(self.alieni.get((c, f)) for c in range(COLONNE))]
        if file_vive and self.ay + max(file_vive) * PASSO_Y + ALTO_ALIENO >= Y_FONDO:
            self.vite = 0
            self._muori()

    def _muovi_colpo(self, dt):
        if self.colpo is None:
            return
        self.colpo[1] -= 105.0 * dt
        x, y = int(self.colpo[0]), int(self.colpo[1])
        if y < 0:
            self.colpo = None
            return
        if self._colpisci_bunker(x, y):
            self.colpo = None
            return
        for (colonna, fila), vivo in self.alieni.items():
            if not vivo:
                continue
            ax, ay = self._pos(colonna, fila)
            if ax <= x < ax + LARGO_ALIENO and ay <= y < ay + ALTO_ALIENO:
                self.alieni[(colonna, fila)] = False
                self.punteggio += PUNTI[fila]
                self._aggiorna_record()
                self.colpo = None
                return

    def _muovi_bombe(self, dt):
        self._da_bomba -= dt
        if self._da_bomba <= 0:
            self._da_bomba = max(0.35, 1.6 - 0.12 * self.livello)
            self._sgancia()
        restano = []
        for bomba in self.bombe:
            bomba[1] += 46.0 * dt
            x, y = int(bomba[0]), int(bomba[1])
            if y >= ALTEZZA:
                continue
            if self._colpisci_bunker(x, y):
                continue
            if Y_NAVE <= y < Y_NAVE + ALTA_NAVE \
                    and self.nave_x - 1 <= x <= self.nave_x + LARGA_NAVE:
                self.vite -= 1
                self._muori()
                return
            restano.append(bomba)
        self.bombe = restano

    def _sgancia(self):
        """Spara l'alieno piu' in basso di una colonna a caso: gli altri sono
        coperti dai compagni, e vederli sparare attraverso non torna."""
        colonne = [c for c in range(COLONNE)
                   if any(self.alieni.get((c, f)) for f in range(FILE))]
        if not colonne or len(self.bombe) >= 3:
            return
        colonna = self._rnd.choice(colonne)
        fila = max(f for f in range(FILE) if self.alieni.get((colonna, f)))
        x, y = self._pos(colonna, fila)
        self.bombe.append([x + LARGO_ALIENO / 2, y + ALTO_ALIENO])

    def _colpisci_bunker(self, x, y):
        for blocchi in self._bunker:
            if (x, y) in blocchi:
                # Un colpo apre un buco, non cancella il riparo: e' quello che
                # rende i ripari una risorsa che si consuma.
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        blocchi.discard((x + dx, y + dy))
                return True
        return False

    def _muori(self):
        self.colpo = None
        self.bombe = []
        self._pausa = 1.2
        self.nave_x = CAMPO / 2.0 - LARGA_NAVE / 2
        if self.vite <= 0:
            self.vite = 0
            self.finita = True
            self._aggiorna_record()

    # --------------------------------------------------------------- disegno

    def disegna_campo(self, img, px):
        for (colonna, fila), vivo in self.alieni.items():
            if not vivo:
                continue
            x, y = self._pos(colonna, fila)
            self._sprite(px, ALIENI[fila][self.posa], int(x), int(y),
                         COLORI[fila], 8)
        for blocchi in self._bunker:
            for (x, y) in blocchi:
                if 0 <= x < CAMPO and 0 <= y < ALTEZZA:
                    px[x, y] = (90, 220, 110)
        if not self.finita:
            self._sprite(px, NAVE, int(self.nave_x), Y_NAVE, NAVE_COLORE, 8)
        if self.colpo is not None:
            x, y = int(self.colpo[0]), int(self.colpo[1])
            for dy in range(3):
                if 0 <= y + dy < ALTEZZA and 0 <= x < CAMPO:
                    px[x, y + dy] = (255, 255, 255)
        for bomba in self.bombe:
            x, y = int(bomba[0]), int(bomba[1])
            for dy in range(3):
                if 0 <= y + dy < ALTEZZA and 0 <= x < CAMPO:
                    px[x, y + dy] = (255, 80, 80)
        if self._pausa > 0 and not self.finita:
            centra(px, "PRONTO", 28, (255, 255, 255))

    @staticmethod
    def _sprite(px, righe, x0, y0, colore, larghezza):
        for dy, bit in enumerate(righe):
            for dx in range(larghezza):
                if bit & (1 << (larghezza - 1 - dx)):
                    x, y = x0 + dx, y0 + dy
                    if 0 <= x < CAMPO and 0 <= y < ALTEZZA:
                        px[x, y] = colore
