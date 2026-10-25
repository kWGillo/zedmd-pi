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

from .base import Gioco, centra

# La casella sul pannello. Quattro pixel e' il compromesso: a tre il serpente
# e' un filo che da tre metri non si segue, a cinque la griglia scende a 39x12
# e il gioco diventa stretto. Dalla 17.4 e' il valore di riferimento e non piu'
# la misura vera: `_misura_griglia` la ricalcola dal campo, e su 200x64 torna
# esattamente quattro.
LATO = 4

# Il margine esiste per una ragione che si vede solo guardando il pannello: se
# la griglia riempie i 64 pixel esatti, la cornice cade **dentro** la prima e
# l'ultima casella, e il serpente ci viaggia sopra cancellandola. Due pixel
# per lato tolgono una riga e una colonna e danno alla cornice un posto suo.
MARGINE = 2

# Sul pannello la griglia e' 49x15, e dalla 17.4 non e' piu' una costante:
# si calcola dal campo. Su 200x64 ridanno esattamente 4, 49 e 15, cioe' il
# gioco di sempre; su una tela alta la casella resta quadrata -- il lato e'
# uno solo per tutti e due gli assi, altrimenti il serpente diventa una fila
# di mattoni e va piu' veloce in una direzione che nell'altra -- e le righe
# crescono.

# Il corpo si disegna 3x3 dentro la casella da 4: il pixel di margine fa da
# giunzione fra un anello e l'altro, e da lontano e' quello che fa leggere il
# serpente come un serpente invece che come una striscia continua. Anche
# questo si calcola: sempre un pixel meno del lato.

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
    TELA_LIBERA = True

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
        self._misura_griglia()
        self._riparti()

    def _misura_griglia(self):
        """La casella, e quante ce ne stanno. Su 200x64 torna il gioco di sempre.

        Il lato lo decide il lato piu' stretto in proporzione: cosi' la
        casella resta **quadrata** su qualunque tela. La griglia poi si
        centra in quello che avanza, invece di appoggiarsi al margine
        sinistro e lasciare il resto della divisione tutto a destra.
        """
        self.lato = max(3, int(round(LATO * min(self.campo_l / 200.0,
                                                self.campo_a / 64.0))))
        self.corpo_lato = max(1, self.lato - 1)
        self.colonne = (self.campo_l - 2 * MARGINE) // self.lato
        self.righe = (self.campo_a - 2 * MARGINE) // self.lato
        larga = self.colonne * self.lato
        alta = self.righe * self.lato
        self.griglia_x = self.campo_x + (self.campo_l - larga) // 2
        self.griglia_y = self.campo_y + (self.campo_a - alta) // 2

    def _riparti(self):
        """Rimette il serpente al centro, corto, fermo e rivolto a destra."""
        centro_y = self.righe // 2
        partenza = self.colonne // 4
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
        libere = [(x, y) for x in range(self.colonne)
                  for y in range(self.righe)
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

        if not (0 <= nuova[0] < self.colonne
                and 0 <= nuova[1] < self.righe):
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
        x0, y0 = self.griglia_x, self.griglia_y
        x1 = x0 + self.colonne * self.lato
        y1 = y0 + self.righe * self.lato
        for x in range(x0 - 1, min(self.largo, x1 + 1)):
            px[x, y0 - 1] = COLORE_BORDO
            px[x, min(self.alto - 1, y1)] = COLORE_BORDO
        for y in range(y0 - 1, min(self.alto, y1 + 1)):
            px[x0 - 1, y] = COLORE_BORDO
            px[min(self.largo - 1, x1), y] = COLORE_BORDO

        if self.cibo is not None:
            self._casella(px, self.cibo, COLORE_CIBO)

        for pezzo in self.corpo[:-1]:
            self._casella(px, pezzo, COLORE_CORPO)
        self._casella(px, self.corpo[-1], COLORE_TESTA)

        if self._ferma and not self.finita:
            centra(px, "FUOCO PER PARTIRE",
                   self.campo_y + self.campo_a * 5 // 8, (150, 150, 160))

    def _casella(self, px, cella, colore):
        x0 = self.griglia_x + cella[0] * self.lato
        y0 = self.griglia_y + cella[1] * self.lato
        for dx in range(self.corpo_lato):
            for dy in range(self.corpo_lato):
                x, y = x0 + dx, y0 + dy
                if 0 <= x < self.largo and 0 <= y < self.alto:
                    px[x, y] = colore
