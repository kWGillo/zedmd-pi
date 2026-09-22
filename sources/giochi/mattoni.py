# -*- coding: utf-8 -*-
"""Breakout, riscritto per 256x64 -- e rifatto una seconda volta per il suono.

Di tutti e tre e' quello che soffre meno il pannello: il muro e' largo per
natura, e la racchetta si muove sull'asse in cui lo spazio ce l'abbiamo. Quello
che cambia rispetto a un Breakout su schermo normale e' il **tempo di volo**:
fra il muro e la racchetta ci sono trenta pixel invece di duecento, quindi la
palla torna addosso in fretta e il gioco diventa di riflessi.

Per questo la palla parte lenta e accelera a ogni fila sfondata invece di
partire alla velocita' finale: se comincia gia' veloce, su questo schermo non
si capisce cosa e' successo.

Perche' questo file e' stato rifatto
------------------------------------
Per settimane Breakout e' stato l'unico gioco a cui mancavano dei suoni. Le
misure dicevano che la logica li chiedeva tutti -- 510 contatti rilevati dalla
fisica, 510 chiamate a `suona` -- ma quelle misure le avevo scritte io, e a un
certo punto difendere il proprio codice vale meno che rifare la parte che ha
qualcosa di unico.

E qualcosa di unico ce l'aveva, ed e' **da dove** usciva il suono. Il passo di
Breakout si spezza in micro-passi piu' corti di un pixel, altrimenti una palla
veloce attraverserebbe un mattone senza accorgersene; e i suoni partivano da
*dentro* quel ciclo. Era l'unico gioco del progetto in cui una sola chiamata a
`passo()` poteva emetterne tre o quattro, in un ordine deciso dalla fisica
invece che dal fotogramma. Invaders, che i suoi li emette una volta per
fotogramma, non ha mai avuto il problema.

Adesso la fisica non suona: **registra**. Un mattone, una sponda, la racchetta
finiscono in una lista, e a fine `passo()` escono insieme, in un ordine deciso
qui e senza ripetizioni. Il suono diventa un'uscita del fotogramma, come
l'immagine -- si guarda la stessa lista che ha disegnato il quadro. Nessuna
riga della fisica chiama piu' `suona` direttamente, e c'e' una prova che lo
verifica leggendo il sorgente.
"""

import math
import random

from .base import ALTEZZA, CAMPO, Gioco, centra

MATTONE_L = 19
MATTONE_H = 3
COLONNE = 10
FILE = 5
MURO_X = 5
MURO_Y = 6
COLORI = ((255, 60, 60), (255, 150, 40), (255, 220, 40),
          (90, 220, 110), (90, 170, 255))
PUNTI = (50, 40, 30, 20, 10)

RACCHETTA_Y = 60
RACCHETTA_H = 2
RACCHETTA_L = 22
RACCHETTA_V = 88.0              # pixel al secondo, con il tasto premuto
PALLA = 2

# Oltre i 60 gradi dalla verticale la palla rimbalza quasi in orizzontale e
# non arriva mai al muro: su un campo alto trenta pixel e' una partita bloccata.
ANGOLO_MAX = math.radians(62)

# E sotto i 9 gradi succede il contrario, ed e' peggio: colpita esattamente al
# centro la palla salirebbe e scenderebbe sulla stessa colonna all'infinito,
# e finita quella colonna la partita non e' piu' vincibile. Non e' un caso di
# scuola -- un giocatore che insegue bene la palla la centra quasi sempre -- e
# infatti l'ha trovato la prova automatica, non una partita a mano.
ANGOLO_MIN = math.radians(9)

# L'ordine in cui escono i suoni quando in un fotogramma succede piu' di una
# cosa. E' una scala di importanza, non l'ordine cronologico: dentro trenta
# millesimi di secondo l'orecchio non distingue chi e' arrivato prima, ma
# distingue benissimo se la palla persa e' stata coperta da un rimbalzo.
ORDINE = ("persa", "livello", "lancio", "mattone1", "mattone2", "mattone3",
          "mattone4", "mattone5", "racchetta", "muro")

# Quanti suoni al massimo per fotogramma. Due, e non e' una rinuncia: misurando
# quattro partite intere il gioco non ne ha mai chiesti piu' di uno per
# fotogramma. Il tetto e' un freno per un caso che nessuno ha mai visto, non
# una regola che tocca le partite vere -- e sopra i due, dentro trenta
# millesimi, non si sentirebbero come suoni separati ma come un unico schiocco.
SUONI_PER_FRAME = 2


class Mattoni(Gioco):
    nome = "breakout"
    etichetta = "Breakout"
    MUSICA = "breakout_musica"
    colore_hud = (90, 170, 255)

    # -------------------------------------------------------------- partita

    def avvia_partita(self, seme=None):
        self._rnd = random.Random(seme)
        self.punteggio = 0
        self.vite = 3
        self.livello = 1
        self.finita = False
        # Gli eventi sonori di **questo** fotogramma. Vivono un `passo()` e
        # poi si svuotano: non e' una coda e non deve diventarlo, perche' un
        # suono che arriva un fotogramma dopo il suo colpo e' gia' in ritardo.
        self._eventi = []
        # L'ultima lista emessa. Serve alle prove e alla diagnosi: e' l'unico
        # modo di vedere da fuori cosa ha chiesto il gioco senza mettersi in
        # mezzo a `suona`.
        self.suoni_del_frame = ()
        self._nuovo_livello()

    def _nuovo_livello(self):
        self.mattoni = {(c, f): True for c in range(COLONNE)
                        for f in range(FILE)}
        self._riparti()

    def _riparti(self):
        self.racchetta = CAMPO / 2.0 - RACCHETTA_L / 2
        self.attaccata = True          # la palla parte ferma sulla racchetta
        self.bx = self.racchetta + RACCHETTA_L / 2
        self.by = float(RACCHETTA_Y - PALLA)
        self.vx, self.vy = 0.0, 0.0
        self.velocita = 46.0 + 5.0 * (self.livello - 1)
        self._colpi = 0

    def _lancia(self):
        angolo = self._rnd.uniform(-0.5, 0.5)
        self.vx = math.sin(angolo) * self.velocita
        self.vy = -math.cos(angolo) * self.velocita
        self.attaccata = False
        self._segna("lancio")

    def rimasti(self):
        return sum(1 for v in self.mattoni.values() if v)

    # ---------------------------------------------------------------- suono

    def _segna(self, nome):
        """Registra un evento sonoro del fotogramma. Non suona: annota.

        E' l'unica porta. Nessun punto della fisica chiama `suona`
        direttamente, e cosi' *quando* un suono parte lo decide una riga sola
        -- `_emetti`, a fine fotogramma -- invece di dipendere da quanti
        micro-passi ha fatto la palla in quel trentesimo di secondo.
        """
        self._eventi.append(nome)

    def _emetti(self):
        """Manda fuori i suoni del fotogramma: ordinati e senza ripetizioni.

        Le ripetizioni si tolgono perche' due click identici dentro lo stesso
        trentesimo di secondo non si sentono come due: si sommano in uno solo
        piu' forte. Emetterli entrambi costerebbe il doppio e renderebbe meno.
        """
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
        """Un fotogramma: prima la fisica, poi -- una volta sola -- il suono."""
        self._eventi = []
        try:
            self._fisica(dt, tasti)
        finally:
            # Anche se la fisica dovesse sollevare, quello che era gia'
            # successo si sente: l'eccezione chiude la partita, ma il colpo
            # che l'ha preceduta era vero e merita il suo suono.
            self._emetti()

    def _fisica(self, dt, tasti):
        if self.finita:
            if "fuoco" in tasti:
                self.avvia_partita()
            return

        if "sinistra" in tasti:
            self.racchetta -= RACCHETTA_V * dt
        if "destra" in tasti:
            self.racchetta += RACCHETTA_V * dt
        self.racchetta = max(0.0, min(CAMPO - RACCHETTA_L, self.racchetta))

        if self.attaccata:
            # La palla segue la racchetta e non succede niente: nessun evento.
            # Una versione precedente suonava la racchetta anche qui, trenta
            # volte al secondo: un ronzio continuo prima del lancio e, per il
            # resto della partita, un mixer sempre pieno che copriva i
            # mattoni. Il suono del lancio c'e' gia' e arriva quando premi.
            self.bx = self.racchetta + RACCHETTA_L / 2
            self.by = float(RACCHETTA_Y - PALLA)
            if "fuoco" in tasti:
                self._lancia()
            return

        # Il passo si spezza in tratti piu' corti di un pixel: con trenta
        # pixel di campo e una palla veloce, muoversi tutto in una volta vuol
        # dire attraversare un mattone senza accorgersene.
        distanza = math.hypot(self.vx, self.vy) * dt
        passi = max(1, int(distanza) + 1)
        for _ in range(passi):
            if self.finita or self.attaccata:
                break
            self._micro_passo(dt / passi)

        # Muro finito. Il controllo sta qui e non dentro il ciclo perche' e'
        # una conclusione del fotogramma, non di un micro-passo. E si arriva
        # a leggerlo anche quando la palla e' appena caduta, perche' il ciclo
        # qui sopra esce con `break` e non con `return`: prima, rompere
        # l'ultimo mattone e perdere la palla nello stesso fotogramma lasciava
        # il livello a meta' fino al lancio successivo.
        if self.rimasti() == 0 and not self.finita:
            self.livello += 1
            self.punteggio += 100
            self._aggiorna_record()
            self._segna("livello")
            self._nuovo_livello()

    def _micro_passo(self, dt):
        """Un tratto lungo meno di un pixel. Registra gli eventi, non suona."""
        self.bx += self.vx * dt
        self.by += self.vy * dt

        if self.bx <= 0:
            self.bx = 0.0
            self.vx = abs(self.vx)
            self._segna("muro")
        elif self.bx >= CAMPO - PALLA:
            self.bx = CAMPO - PALLA
            self.vx = -abs(self.vx)
            self._segna("muro")
        if self.by <= 0:
            self.by = 0.0
            self.vy = abs(self.vy)
            self._segna("muro")

        self._colpisci_mattone()

        if (self.vy > 0
                and RACCHETTA_Y - PALLA <= self.by <= RACCHETTA_Y + RACCHETTA_H
                and self.racchetta - 1 <= self.bx + PALLA / 2
                <= self.racchetta + RACCHETTA_L + 1):
            self.by = float(RACCHETTA_Y - PALLA)
            self._segna("racchetta")
            # L'angolo dipende da dove si colpisce: e' quello che trasforma la
            # racchetta da muro a strumento di mira.
            centro = self.racchetta + RACCHETTA_L / 2
            scarto = (self.bx + PALLA / 2 - centro) / (RACCHETTA_L / 2)
            angolo = max(-1.0, min(1.0, scarto)) * ANGOLO_MAX
            if abs(angolo) < ANGOLO_MIN:
                # Verso in cui stava gia' andando, cosi' un colpo al centro
                # non fa cambiare lato alla palla di punto in bianco.
                verso = 1 if (self.vx > 0
                              or (self.vx == 0 and scarto >= 0)) else -1
                # Con un angolo minimo *fisso* la traiettoria diventa
                # periodica e certi mattoni non li raggiunge mai: un filo di
                # caso rompe il ciclo, e a occhio non si vede.
                angolo = self._rnd.uniform(ANGOLO_MIN, ANGOLO_MIN * 1.7) * verso
            self.vx = math.sin(angolo) * self.velocita
            self.vy = -math.cos(angolo) * self.velocita

        if self.by > ALTEZZA:
            self.vite -= 1
            self._segna("persa")
            if self.vite <= 0:
                self.vite = 0
                self.finita = True
                self._aggiorna_record()
            else:
                self._riparti()

    def _colpisci_mattone(self):
        if self.by > MURO_Y + FILE * MATTONE_H:
            return
        colonna = int((self.bx - MURO_X) // MATTONE_L)
        fila = int((self.by - MURO_Y) // MATTONE_H)
        if not (0 <= colonna < COLONNE and 0 <= fila < FILE):
            return
        if not self.mattoni.get((colonna, fila)):
            return
        self.mattoni[(colonna, fila)] = False
        # Una nota per fila, e sale scavando verso l'alto. E' il suono che il
        # Breakout del 1976 usava per dire, senza scriverlo, a che punto sei
        # arrivato: la fila 0 e' quella in cima, quella che vale di piu'.
        self._segna("mattone%d" % (fila + 1))
        self.punteggio += PUNTI[fila]
        self._aggiorna_record()
        self.vy = -self.vy
        self.by += (1 if self.vy > 0 else -1)
        # Ogni quattro mattoni la palla accelera: senza, la seconda meta' del
        # muro e' solo lavoro di braccia.
        self._colpi += 1
        if self._colpi % 4 == 0:
            self.velocita = min(96.0, self.velocita * 1.06)
            fattore = self.velocita / max(1e-6, math.hypot(self.vx, self.vy))
            self.vx *= fattore
            self.vy *= fattore

    # -------------------------------------------------------------- disegno

    def disegna_campo(self, img, px):
        for (colonna, fila), vivo in self.mattoni.items():
            if not vivo:
                continue
            x0 = MURO_X + colonna * MATTONE_L
            y0 = MURO_Y + fila * MATTONE_H
            for x in range(x0, min(CAMPO, x0 + MATTONE_L - 1)):
                for y in range(y0, min(ALTEZZA, y0 + MATTONE_H - 1)):
                    px[x, y] = COLORI[fila]

        if not self.finita:
            for x in range(int(self.racchetta),
                           min(CAMPO, int(self.racchetta) + RACCHETTA_L)):
                for y in range(RACCHETTA_Y, RACCHETTA_Y + RACCHETTA_H):
                    px[x, y] = (255, 140, 26)

        for dx in range(PALLA):
            for dy in range(PALLA):
                x, y = int(self.bx) + dx, int(self.by) + dy
                if 0 <= x < CAMPO and 0 <= y < ALTEZZA:
                    px[x, y] = (255, 255, 255)

        if self.attaccata and not self.finita:
            centra(px, "FUOCO PER LANCIARE", 40, (150, 150, 160))
