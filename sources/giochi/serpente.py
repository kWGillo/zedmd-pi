# -*- coding: utf-8 -*-
"""Snake, quello dei Nokia, su un pannello che e' largo quattro volte l'altezza.

Il gioco e' quello che sanno tutti: un serpente che si allunga mangiando, e
che muore se sbatte contro il bordo o contro se stesso. Quello che cambia qui
sono due cose, e nessuna delle due e' un dettaglio.

**La forma del campo.** Il pannello da' 200x64 pixel al gioco, cioe' un
rettangolo 3:1. Con caselle da 4 pixel e due pixel di cornice viene una
griglia di **49x15**: molto larga e poco alta, il contrario degli undici
quadrati per lato del 3310. Un serpente che cresce qui riempie prima
l'altezza che la larghezza, quindi la partita e' fatta di corridoi
orizzontali -- e per questo il cibo non compare mai nella riga in cui il
serpente sta gia' viaggiando, che su quindici righe sarebbe mezzo regalo.

**I comandi sono quattro direzioni, come sul telefono.** La prima stesura
sterzava in relativo -- sinistra gira a sinistra rispetto a dove stai andando
-- perche' avevo dato per scontato un cabinato con i due pulsanti del flipper.
Quel cabinato non esiste: questo e' un pannello che sta su una mensola, e chi
gioca ha un controller PS4 in mano. Un controller ha la croce direzionale. Con quattro direzioni vere lo sterzo relativo non e' una
soluzione, e' un indovinello -- premendo sinistra mentre si va in giu' il
serpente girava a destra, che e' l'opposto di quello che dice il pollice.

Quindi: ogni tasto punta dove dice. Il dietrofront si ignora, perche' un
serpente non torna nella casella da cui e' appena uscito, e la direzione
chiesta si applica **al prossimo spostamento**, non subito: a trenta
fotogrammi al secondo e sei caselle al secondo, un tasto tenuto premuto un
decimo di secondo vale tre fotogrammi, e senza questa regola chi sfiora due
tasti in sequenza otterrebbe una piega che non ha chiesto.

Il suono, come in Breakout dalla 8.7, non esce dalla fisica: gli eventi si
registrano durante il passo e si emettono **una volta sola** a fine
fotogramma, ordinati per importanza. E' la regola del progetto, non una
preferenza di questo file.
"""

import random

from .base import ALTEZZA, CAMPO, Gioco, centra

# La casella. Quattro pixel e' il compromesso: a tre il serpente e' un filo
# che da tre metri non si segue, a cinque la griglia scende a 39x12 e il gioco
# diventa stretto.
LATO = 4

# Il margine esiste per una ragione che si vede solo guardando il pannello: se
# la griglia riempie i 64 pixel esatti, la cornice cade **dentro** la prima e
# l'ultima casella, e il serpente ci viaggia sopra cancellandola. Due pixel
# per lato tolgono una riga e una colonna e danno alla cornice un posto suo.
MARGINE = 2
COLONNE = (CAMPO - 2 * MARGINE) // LATO      # 49
RIGHE = (ALTEZZA - 2 * MARGINE) // LATO      # 15

# Il corpo si disegna 3x3 dentro la casella da 4: il pixel di margine fa da
# giunzione fra un anello e l'altro, e da lontano e' quello che fa leggere il
# serpente come un serpente invece che come una striscia continua.
CORPO = 3

COLORE_TESTA = (120, 255, 140)
COLORE_CORPO = (40, 180, 70)
COLORE_CIBO = (255, 80, 80)
COLORE_BORDO = (40, 40, 48)

# Quante caselle al secondo, per livello. Si parte piano perche' il pannello
# si guarda da lontano e la casella e' quattro pixel: a quindici al secondo il
# serpente e' gia' un guizzo. Si sale ogni CIBI_PER_LIVELLO bocconi.
VELOCITA = (6.0, 7.5, 9.0, 11.0, 13.0, 15.0)
CIBI_PER_LIVELLO = 5

PUNTI_CIBO = 10

# Le quattro direzioni in senso orario. L'ordine conta: due indici che
# distano 2 sono opposti, quindi il dietrofront si riconosce con un resto
# invece che con una tabella.
DIREZIONI = ((1, 0), (0, 1), (-1, 0), (0, -1))
NOMI_DIREZIONE = ("destra", "giu", "sinistra", "su")
# Il tasto e la direzione che punta. L'ordine e' quello in cui si guardano
# quando ne risultano premuti due insieme -- succede con una leva analogica
# tenuta in diagonale, e bisogna pur sceglierne uno.
TASTI_DIREZIONE = (("su", 3), ("giu", 1), ("sinistra", 2), ("destra", 0))

# Ordine di importanza dei suoni dentro un fotogramma, come in Breakout.
ORDINE = ("persa", "livello", "mangia3", "mangia2", "mangia1", "tonfo",
          "lancio")
SUONI_PER_FRAME = 2


class Serpente(Gioco):
    nome = "snake"
    etichetta = "Snake"
    MUSICA = "snake_musica"

    def musica_di_adesso(self):
        # Parte con il primo fuoco, come il serpente.
        if self.finita or self._ferma:
            return None
        return self.MUSICA
    colore_hud = (90, 220, 110)

    # -------------------------------------------------------------- partita

    def avvia_partita(self, seme=None):
        self._rnd = random.Random(seme)
        self.punteggio = 0
        self.vite = 3
        self.livello = 1
        self.finita = False
        self._cibi = 0
        self._eventi = []
        self.suoni_del_frame = ()
        self._ferma = True          # in attesa del primo FUOCO
        self._riparti()

    def _riparti(self):
        """Rimette il serpente al centro, corto, fermo e rivolto a destra."""
        centro_y = RIGHE // 2
        partenza = COLONNE // 4
        # Dalla coda alla testa: l'ultimo elemento e' la testa, cosi' crescere
        # e' un `append` e muoversi e' un `append` piu' un `pop(0)`.
        self.corpo = [(partenza - 2, centro_y), (partenza - 1, centro_y),
                      (partenza, centro_y)]
        self.direzione = 0          # destra
        self._voluta = None         # la direzione chiesta per il prossimo passo
        self._avanzo = 0.0          # frazione di casella accumulata
        self._ferma = True
        self.cibo = self._nuovo_cibo()

    def _nuovo_cibo(self):
        """Una casella libera a caso, ma non davanti al muso.

        Su quindici righe, un cibo che nasce nella riga in cui il serpente sta
        gia' viaggiando e' mezzo regalo: basta non toccare i pulsanti. Si
        evita la riga della testa quando si puo' -- e quando non si puo',
        perche' il serpente e' lunghissimo, si prende quello che c'e'.
        """
        occupate = set(self.corpo)
        testa = self.corpo[-1]
        libere = [(x, y) for x in range(COLONNE) for y in range(RIGHE)
                  if (x, y) not in occupate]
        if not libere:
            return None             # vinto: il serpente riempie la griglia
        lontane = [c for c in libere if c[1] != testa[1]]
        return self._rnd.choice(lontane or libere)

    def velocita(self):
        return VELOCITA[min(self.livello - 1, len(VELOCITA) - 1)]

    # ---------------------------------------------------------------- suono

    def _segna(self, nome):
        self._eventi.append(nome)

    def _emetti(self):
        eventi, self._eventi = self._eventi, []
        if not eventi:
            self.suoni_del_frame = ()
            return
        scelti = []
        for nome in ORDINE:
            if nome in eventi:
                scelti.append(nome)
                if len(scelti) >= SUONI_PER_FRAME:
                    break
        self.suoni_del_frame = tuple(scelti)
        for nome in scelti:
            self.suona(nome)

    # ---------------------------------------------------------------- passo

    def passo(self, dt, tasti):
        self._eventi = []
        try:
            self._fisica(dt, tasti)
        finally:
            self._emetti()

    def _fisica(self, dt, tasti):
        if self.finita:
            if "fuoco" in tasti:
                self.avvia_partita()
            return

        self._leggi_comandi(tasti)

        if self._ferma:
            # Fermo in attesa del via: il tempo non scorre e non si accumula,
            # altrimenti al primo FUOCO il serpente schizzerebbe via di tre
            # caselle insieme.
            return

        self._avanzo += dt * self.velocita()
        # Un solo passo per fotogramma anche se il tempo accumulato ne
        # varrebbe due: a quindici caselle al secondo un fotogramma vale mezza
        # casella, e saltarne due vorrebbe dire attraversare il proprio corpo
        # senza toccarlo. Il resto si perde, ed e' meglio di un serpente che
        # teletrasporta.
        if self._avanzo < 1.0:
            return
        self._avanzo = 0.0
        self._avanza()

    def _leggi_comandi(self, tasti):
        """Legge la direzione chiesta. Non la applica: quello tocca al passo.

        Si tiene solo l'**ultima** chiesta, e la si verifica al momento di
        muoversi. Applicarla subito sarebbe un difetto in un caso preciso:
        andando a destra, premere su e poi sinistra dentro lo stesso
        trentesimo di secondo farebbe un mezzo giro e il serpente si
        morderebbe da solo, perche' il dietrofront verrebbe controllato
        contro una direzione che non ha ancora percorso nemmeno una casella.
        """
        if "fuoco" in tasti and self._ferma:
            self._ferma = False
            self._segna("lancio")

        for nome, indice in TASTI_DIREZIONE:
            if nome in tasti:
                self._voluta = indice
                break

    def _avanza(self):
        if self._voluta is not None:
            # Il dietrofront si scarta qui e non alla pressione: e' qui che si
            # sa qual e' la direzione **vera** da cui si sta uscendo.
            if (self._voluta - self.direzione) % 4 != 2:
                self.direzione = self._voluta
            self._voluta = None
        dx, dy = DIREZIONI[self.direzione]
        x, y = self.corpo[-1]
        nuova = (x + dx, y + dy)

        if not (0 <= nuova[0] < COLONNE and 0 <= nuova[1] < RIGHE):
            self._muori("tonfo")
            return
        # La coda si libera nello stesso istante in cui la testa avanza:
        # inseguire la propria coda e' lecito, e in un gioco di serpenti e'
        # meta' del mestiere.
        if nuova in self.corpo[1:]:
            self._muori("tonfo")
            return

        self.corpo.append(nuova)
        if self.cibo is not None and nuova == self.cibo:
            self._mangia()
        else:
            self.corpo.pop(0)

    def _mangia(self):
        self.punteggio += PUNTI_CIBO * self.livello
        self._aggiorna_record()
        self._cibi += 1
        # La nota sale con il livello: e' il modo in cui il gioco dice "stai
        # andando bene" senza scrivere niente sul pannello.
        indice = min(3, 1 + (self.livello - 1) // 2)
        self._segna("mangia%d" % indice)
        if self._cibi % CIBI_PER_LIVELLO == 0 and self.livello < len(VELOCITA):
            self.livello += 1
            self._segna("livello")
        self.cibo = self._nuovo_cibo()

    def _muori(self, effetto):
        self._segna(effetto)
        self.vite -= 1
        self._segna("persa")
        if self.vite <= 0:
            self.vite = 0
            self.finita = True
            self._aggiorna_record()
        else:
            self._riparti()

    # -------------------------------------------------------------- disegno

    def disegna_campo(self, img, px):
        # La cornice si disegna perche' qui uccide: un campo senza confine
        # visibile su un pannello nero vuol dire morire contro un muro che non
        # si vedeva, che e' la peggiore delle morti.
        x1 = MARGINE + COLONNE * LATO
        y1 = MARGINE + RIGHE * LATO
        for x in range(MARGINE - 1, min(CAMPO, x1 + 1)):
            px[x, MARGINE - 1] = COLORE_BORDO
            px[x, min(ALTEZZA - 1, y1)] = COLORE_BORDO
        for y in range(MARGINE - 1, min(ALTEZZA, y1 + 1)):
            px[MARGINE - 1, y] = COLORE_BORDO
            px[min(CAMPO - 1, x1), y] = COLORE_BORDO

        if self.cibo is not None:
            self._casella(px, self.cibo, COLORE_CIBO)

        for pezzo in self.corpo[:-1]:
            self._casella(px, pezzo, COLORE_CORPO)
        self._casella(px, self.corpo[-1], COLORE_TESTA)

        if self._ferma and not self.finita:
            centra(px, "FUOCO PER PARTIRE", 40, (150, 150, 160))

    @staticmethod
    def _casella(px, cella, colore):
        x0 = MARGINE + cella[0] * LATO
        y0 = MARGINE + cella[1] * LATO
        for dx in range(CORPO):
            for dy in range(CORPO):
                x, y = x0 + dx, y0 + dy
                if 0 <= x < CAMPO and 0 <= y < ALTEZZA:
                    px[x, y] = colore
