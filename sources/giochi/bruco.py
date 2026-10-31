# -*- coding: utf-8 -*-
# fix-v3 2026-10-31
"""Bruco: il verme a pezzi che scende fra i funghi.

Il nome
-------
Il gioco del millepiedi che scende a zigzag in un campo di funghi ha un
nome suo, e resta suo. Lo schema -- un verme fatto di segmenti che scende
una riga ogni volta che trova un ostacolo, funghi che fanno da labirinto,
un cannoncino che lo spezza pezzo a pezzo -- non e' di nessuno. Questo e'
Bruco: codice scritto da zero contro il contratto di `Gioco`, nome nostro,
disegno nostro.

Il gioco
--------
* Il campo e' una griglia di celle sopra il pannello: in basso, quattro
  righe sono la **zona del giocatore**, segnata da una riga tratteggiata.
  Li' dentro il cannoncino si muove libero, nelle quattro direzioni.
* I **funghi** stanno sparsi per il campo, una trentina: ognuno regge
  quattro colpi e si consuma a vista, sempre piu' piccolo e piu' spento.
  Distruggerne uno fino in fondo vale un punto.
* Il **bruco** nasce in cima, undici segmenti in fila, e cammina di cella
  in cella: dritto finche' puo', e quando trova un fungo o il bordo scende
  di una riga e torna indietro. Nella zona del giocatore non esce piu':
  al fondo la sua deriva si inverte e rimbalza li' dentro.
* **Fuoco** spara un dardo verso l'alto, al massimo due per volta. Un
  segmento colpito muore, al suo posto nasce un fungo, e la fila si
  **spezza**: la parte dietro diventa un bruco nuovo, con una testa nuova.
  La testa vale 100, il corpo 10.
* Dal livello 2 un **ragno** attraversa ogni tanto la zona in diagonale,
  mangiando i funghi che incontra: vale 300, e toccarlo costa una vita.
* Toccare un segmento o il ragno costa una vita: le catene ricominciano
  da capo e i funghi danneggiati tornano interi, come in sala giochi.
  Finite le vite, finita la partita.
* Ripuliti tutti i segmenti il livello sale: bruco nuovo, qualche fungo
  in piu', e il passo un poco piu' svelto.
* All'apertura la partita sta ferma sulla schermata del titolo -- il
  nome e «FUOCO PER PARTIRE», come nei giochi di serie: il bruco
  cammina solo quando si preme fuoco, e quella pressione e' spesa li',
  non spara nessun dardo.
"""

import random

from PIL import ImageDraw

from .base import Gioco, centra, larghezza_testo

ZONA = 4                # le righe in basso dove si muove il giocatore
LUNGHEZZA = 11          # i segmenti del bruco quando nasce
TIC_BASE = 0.14         # secondi per cella, al livello 1
TIC_MIN = 0.05          # piu' svelto di cosi' il bruco non cammina
FATTORE_LIVELLO = 0.92  # ogni livello il passo si accorcia dell'8%
VEL_GIOCATORE = 55.0    # pixel al secondo, nelle quattro direzioni
VEL_COLPO = 150.0       # pixel al secondo, il dardo che sale
MAX_COLPI = 2           # i dardi vivi insieme
CADENZA = 0.18          # secondi fra un dardo e l'altro
VEL_RAGNO = 45.0        # pixel al secondo, in orizzontale
PUNTI_TESTA = 100
PUNTI_CORPO = 10
PUNTI_RAGNO = 300
PUNTI_FUNGO = 1

COLORE_FUNGO = (216, 122, 40)
COLORE_TESTA = (90, 255, 100)
COLORE_CORPO = (40, 180, 70)
COLORE_CORPO_ALT = (28, 130, 50)
COLORE_GIOCATORE = (140, 225, 255)
COLORE_COLPO = (255, 240, 180)
COLORE_RAGNO = (255, 77, 94)


class Bruco(Gioco):
    nome = "bruco"
    etichetta = "Bruco"
    colore_hud = (64, 214, 120)
    COMANDI = ("sinistra", "destra", "su", "giu", "fuoco", "avvia", "esci")
    TELA_LIBERA = True
    MUSICA = None

    # ------------------------------------------------------------- la partita

    def avvia_partita(self, seme=None):
        self._rng = random.Random(seme)
        self.punteggio = 0
        self.vite = 3
        self.livello = 1
        self.finita = False
        self.iniziata = False
        self._prec = set()
        # Il fuoco che ha fatto partire (o ripartire) la partita e'
        # ancora giu': finche' non si molla non spara, e' gia' speso.
        self._partenza = False
        self._posa_geometria()
        self.funghi = {}
        self._semina_funghi((self.colonne * self.righe) // 22)
        self._accum = 0.0
        self._sparo_tra = 0.0
        self.colpi = []
        self.ragno = None
        self._ragno_tra = self._rng.uniform(5.0, 10.0)
        self._posa_giocatore()
        self._nuovo_bruco()

    def ignora_tasti(self, premuti):
        """Il tasto che ha aperto la partita non deve sparare il primo dardo."""
        self._prec = set(premuti)

    def _posa_geometria(self):
        """La griglia la decide la tela: celle da almeno 36x14 sul pannello.

        La cella e' il lato del quadrato: sul pannello ne vengono cinquanta
        colonne per sedici righe da quattro pixel, sullo schermo alto la
        griglia respira (42x24 da sei). La zona del giocatore sono le
        ultime `ZONA` righe, qualunque tela ci sia sotto.
        """
        self.cella = max(3, min(self.campo_l // 40, self.campo_a // 16))
        self.colonne = self.campo_l // self.cella
        self.righe = self.campo_a // self.cella
        self.griglia_l = self.colonne * self.cella
        self.griglia_a = self.righe * self.cella
        self.gx0 = self.campo_x + (self.campo_l - self.griglia_l) // 2
        self.gy0 = self.campo_y + (self.campo_a - self.griglia_a) // 2
        self.riga_zona = self.righe - ZONA

    def _posa_giocatore(self):
        """Il cannoncino in mezzo alla zona, appoggiato sul fondo."""
        self.gx = self.gx0 + (self.griglia_l - self.cella) / 2.0
        self.gy = float(self.gy0 + self.griglia_a - self.cella)

    def _nuovo_bruco(self):
        """Una catena sola, in cima, testa in testa e corpo dietro."""
        testa = self.colonne // 2
        celle = [(testa - i, 0) for i in range(LUNGHEZZA)]
        self.catene = [{"celle": celle, "dc": 1, "dv": 1}]
        self._accum = 0.0

    def _semina_funghi(self, quanti):
        """Funghi nuovi dove ce' posto: mai sulla riga del fondo della zona.

        E mai sulla riga dove nasce il bruco: li' la testa deve trovare la
        strada libera, o la partita comincia con una deviazione a vuoto.
        """
        tentativi = quanti * 30
        while quanti > 0 and tentativi > 0:
            tentativi -= 1
            cella = (self._rng.randrange(self.colonne),
                     self._rng.randrange(1, self.righe - 1))
            if cella in self.funghi:
                continue
            self.funghi[cella] = 4
            quanti -= 1

    def _intervallo(self):
        return max(TIC_MIN,
                   TIC_BASE * (FATTORE_LIVELLO ** (self.livello - 1)))

    # ------------------------------------------------------------- il bruco

    def _passo_catene(self):
        for cat in self.catene:
            self._avanza(cat)

    def _avanza(self, cat):
        """Un passo di una catena: dritto, o giu' di una riga e indietro.

        L'ostacolo e' il bordo o un fungo davanti alla testa. Nella zona
        del giocatore la discesa si ferma al fondo e la deriva si inverte:
        il bruco rimbalza fra il fondo e il bordo della zona, e da li' non
        esce -- e' la parte cattiva del gioco, ed e' voluta.
        """
        celle = cat["celle"]
        tc, tr = celle[0]
        nc, nr = tc + cat["dc"], tr
        if nc < 0 or nc >= self.colonne or (nc, nr) in self.funghi:
            nr = tr + cat["dv"]
            if nr < 0:
                nr = tr + 1
                cat["dv"] = 1
            elif nr >= self.righe:
                nr = tr - 1
                cat["dv"] = -1
            if tr >= self.riga_zona and nr < self.riga_zona:
                nr = tr + 1
                cat["dv"] = 1
            nc = tc
            cat["dc"] = -cat["dc"]
        cat["celle"] = [(nc, nr)] + celle[:-1]

    def _segmenti(self):
        """Tutte le celle occupate da un segmento, di tutte le catene."""
        fuori = set()
        for cat in self.catene:
            fuori.update(cat["celle"])
        return fuori

    def _colpisci_segmento(self, indice_catena, indice, cella):
        """Un segmento muore: fungo al suo posto, e la fila si spezza.

        La parte dietro il colpito diventa una catena sua, e la sua testa
        e' il segmento che stava subito dopo. Se il colpito era la testa,
        la parte davanti non c'e': resta solo la catena nuova.
        """
        cat = self.catene[indice_catena]
        celle = cat["celle"]
        self.punteggio += PUNTI_TESTA if indice == 0 else PUNTI_CORPO
        self.suona("colpito")
        self.funghi[cella] = 4
        dietro = celle[indice + 1:]
        cat["celle"] = celle[:indice]
        if not cat["celle"]:
            self.catene.pop(indice_catena)
        if dietro:
            self.catene.append({"celle": dietro, "dc": cat["dc"],
                                "dv": cat["dv"]})

    # ------------------------------------------------------------- i colpi

    def _cella_a(self, x, y):
        """La cella della griglia sotto un punto in pixel, o None fuori."""
        c = int((x - self.gx0) // self.cella)
        r = int((y - self.gy0) // self.cella)
        if 0 <= c < self.colonne and 0 <= r < self.righe:
            return (c, r)
        return None

    def _muovi_colpi(self, dt):
        """I dardi salgono, a passetti: sotto la meta' cella, per non saltare
        mai un bersaglio in mezzo a due fotogrammi."""
        vivi = []
        for bx, by in self.colpi:
            resta = VEL_COLPO * dt
            colpito = False
            while resta > 0 and not colpito:
                passo = min(self.cella / 2.0, resta)
                by -= passo
                resta -= passo
                if by < self.gy0:
                    colpito = True            # uscito dal campo, in alto
                    break
                cella = self._cella_a(bx, by)
                if cella is None:
                    continue
                if self.ragno is not None and \
                        cella == self._cella_a(self.ragno["x"],
                                               self.ragno["y"]):
                    self.punteggio += PUNTI_RAGNO
                    self.suona("punto")
                    self.ragno = None
                    self._ragno_tra = self._rng.uniform(6.0, 14.0)
                    colpito = True
                    break
                for ci, cat in enumerate(self.catene):
                    if cella in cat["celle"]:
                        self._colpisci_segmento(
                            ci, cat["celle"].index(cella), cella)
                        colpito = True
                        break
                if colpito:
                    break
                if cella in self.funghi:
                    stadio = self.funghi[cella] - 1
                    if stadio <= 0:
                        del self.funghi[cella]
                        self.punteggio += PUNTI_FUNGO
                    else:
                        self.funghi[cella] = stadio
                    colpito = True
            if not colpito:
                vivi.append([bx, by])
        self.colpi = vivi

    # ------------------------------------------------------------- il ragno

    def _muovi_ragno(self, dt):
        """Il ragno attraversa la zona in diagonale, a zigzag.

        Entra da un lato a un'altezza a caso della zona, rimbalza fra il
        bordo della zona e il fondo, e mangia i funghi che gli capitano
        sotto. Dall'altro lato esce, e la zona torna tranquilla.
        """
        if self.ragno is None:
            if self.livello < 2:
                return
            self._ragno_tra -= dt
            if self._ragno_tra > 0:
                return
            lato = self._rng.choice((-1, 1))
            x = self.gx0 - self.cella if lato > 0 \
                else self.gx0 + self.griglia_l
            self.ragno = {
                "x": float(x),
                "y": float(self.gy0 + self._rng.randrange(
                    self.riga_zona, self.righe) * self.cella),
                "dx": lato,
                "dy": self._rng.choice((-1, 1)),
                "gira": 0.0,
            }
            return
        ragno = self.ragno
        ragno["x"] += ragno["dx"] * VEL_RAGNO * dt
        ragno["gira"] -= dt
        if ragno["gira"] <= 0:
            ragno["gira"] = self._rng.uniform(0.3, 0.7)
            if self._rng.random() < 0.5:
                ragno["dy"] = -ragno["dy"]
        ragno["y"] += ragno["dy"] * VEL_RAGNO * 0.6 * dt
        alto = float(self.gy0 + self.riga_zona * self.cella)
        basso = float(self.gy0 + self.griglia_a - self.cella)
        if ragno["y"] < alto:
            ragno["y"] = alto
            ragno["dy"] = 1
        elif ragno["y"] > basso:
            ragno["y"] = basso
            ragno["dy"] = -1
        cella = self._cella_a(ragno["x"] + self.cella / 2.0,
                              ragno["y"] + self.cella / 2.0)
        if cella is not None and cella in self.funghi:
            del self.funghi[cella]
        if ragno["x"] < self.gx0 - self.cella or \
                ragno["x"] > self.gx0 + self.griglia_l:
            self.ragno = None
            self._ragno_tra = self._rng.uniform(6.0, 14.0)

    # ------------------------------------------------------------- la morte

    def _morte(self):
        self.suona("persa")
        self.vite -= 1
        if self.vite <= 0:
            self.vite = 0
            self.finita = True
            return
        # Come in sala giochi: i funghi danneggiati tornano interi, il
        # bruco ricomincia dalla cima, la zona si svuota.
        for cella in self.funghi:
            self.funghi[cella] = 4
        self.colpi = []
        self.ragno = None
        self._ragno_tra = self._rng.uniform(5.0, 10.0)
        self._posa_giocatore()
        self._nuovo_bruco()

    def _controlla_morte(self):
        """Il cannoncino contro i segmenti e contro il ragno."""
        c = self.cella
        c0 = int((self.gx - self.gx0) // c)
        c1 = int((self.gx + c - 1 - self.gx0) // c)
        r0 = int((self.gy - self.gy0) // c)
        r1 = int((self.gy + c - 1 - self.gy0) // c)
        segmenti = self._segmenti()
        for cc in range(c0, c1 + 1):
            for rr in range(r0, r1 + 1):
                if (cc, rr) in segmenti:
                    self._morte()
                    return
        if self.ragno is not None:
            r = self.ragno
            if self.gx < r["x"] + c and r["x"] < self.gx + c and \
                    self.gy < r["y"] + c and r["y"] < self.gy + c:
                self._morte()

    # ---------------------------------------------------------------- passo

    def passo(self, dt, tasti):
        if self.finita:
            # Partita finita: fuoco la ricomincia da capo, e la stessa
            # pressione non vale nella partita nuova (si torna subito).
            if "fuoco" in tasti:
                self.avvia_partita()
                self.iniziata = True
                self._prec = set(tasti)
                self._partenza = True
            return
        nuovi = tasti - self._prec
        self._prec = set(tasti)
        if not self.iniziata:
            # La schermata del titolo, come nei giochi di serie: il campo
            # sta fermo e si parte solo col fuoco, sul fronte di salita.
            if "fuoco" in nuovi:
                self.iniziata = True
                self._partenza = True
            return
        if "fuoco" not in tasti:
            self._partenza = False
        c = self.cella
        # Il giocatore: libero dentro la zona, e solo li' dentro.
        dx = (1 if "destra" in tasti else 0) - (1 if "sinistra" in tasti else 0)
        dy = (1 if "giu" in tasti else 0) - (1 if "su" in tasti else 0)
        self.gx = min(max(self.gx + dx * VEL_GIOCATORE * dt,
                          float(self.gx0)),
                      float(self.gx0 + self.griglia_l - c))
        self.gy = min(max(self.gy + dy * VEL_GIOCATORE * dt,
                          float(self.gy0 + self.riga_zona * c)),
                      float(self.gy0 + self.griglia_a - c))
        # Il fuoco: cadenza breve e due dardi al massimo, come la macchina
        # originale -- sparare a raffica svuoterebbe il campo in un attimo.
        # Il fuoco della partenza non conta: e' quello che ha aperto la
        # partita, e finche' resta giu' non spara.
        self._sparo_tra -= dt
        if "fuoco" in tasti and not self._partenza \
                and self._sparo_tra <= 0 and len(self.colpi) < MAX_COLPI:
            self.colpi.append([self.gx + c / 2.0, self.gy])
            self._sparo_tra = CADENZA
            self.suona("sparo")
        self._muovi_colpi(dt)
        self._muovi_ragno(dt)
        # Il bruco cammina a tempo, non a fotogrammi: un accumulatore, e i
        # passi avanzano di cella in cella qualunque sia il giro del motore.
        self._accum += dt
        intervallo = self._intervallo()
        while self._accum >= intervallo:
            self._accum -= intervallo
            self._passo_catene()
        if not self._segmenti():
            # Campo ripulito: livello nuovo, bruco nuovo, funghi rabboccati.
            self.livello += 1
            self.suona("livello")
            self._semina_funghi((self.colonne * self.righe) // 44)
            self._nuovo_bruco()
            return
        self._controlla_morte()

    # --------------------------------------------------------------- disegno

    def _disegna_fungo(self, dis, c, r, stadio):
        """Un fungo in una cella: cappello e gambo, e si consuma a vista.

        Quattro stadi: a ogni colpo il cappello si assottiglia e il colore
        si spegne, cosi' si capisce a occhio quanto manca a farlo sparire.
        """
        x0 = self.gx0 + c * self.cella
        y0 = self.gy0 + r * self.cella
        lato = self.cella
        fattore = 0.35 + 0.65 * stadio / 4.0
        colore = tuple(int(v * fattore) for v in COLORE_FUNGO)
        larg = max(1, int(lato * (0.45 + 0.55 * stadio / 4.0)))
        x1 = x0 + (lato - larg) // 2
        dis.rectangle([x1, y0, x1 + larg - 1, y0 + max(0, lato // 2 - 1)],
                      fill=colore)
        if stadio >= 3:
            xm = x0 + lato // 2
            dis.rectangle([xm, y0 + lato // 2, xm, y0 + lato - 1],
                          fill=colore)

    def disegna_campo(self, img, px):
        dis = ImageDraw.Draw(img)
        c = self.cella
        # L'arena: un filo di bordo, e la zona del giocatore appena tinta,
        # con il suo confine tratteggiato. Sul pannello ogni pixel acceso e'
        # un impegno: qui sono pochi e dicono dove comincia casa propria.
        dis.rectangle([self.gx0 - 1, self.gy0 - 1,
                       self.gx0 + self.griglia_l, self.gy0 + self.griglia_a],
                      fill=(3, 5, 3), outline=(36, 48, 36))
        zy = self.gy0 + self.riga_zona * c
        dis.rectangle([self.gx0, zy, self.gx0 + self.griglia_l - 1,
                       self.gy0 + self.griglia_a - 1], fill=(6, 10, 7))
        for x in range(self.gx0, self.gx0 + self.griglia_l, 2):
            dis.point((x, zy - 1), fill=(60, 90, 60))
        for (fc, fr), stadio in self.funghi.items():
            self._disegna_fungo(dis, fc, fr, stadio)
        for cat in self.catene:
            for si, (sc, sr) in enumerate(cat["celle"]):
                x0 = self.gx0 + sc * c
                y0 = self.gy0 + sr * c
                if si == 0:
                    dis.rectangle([x0, y0, x0 + c - 1, y0 + c - 1],
                                  fill=COLORE_TESTA)
                    if c >= 5:
                        dis.point((x0 + 1, y0 + 1), fill=(0, 60, 0))
                        dis.point((x0 + c - 2, y0 + 1), fill=(0, 60, 0))
                else:
                    inset = 1 if c >= 5 else 0
                    colore = COLORE_CORPO if si % 2 else COLORE_CORPO_ALT
                    dis.rectangle([x0 + inset, y0 + inset,
                                   x0 + c - 1 - inset, y0 + c - 1 - inset],
                                  fill=colore)
        if self.ragno is not None:
            x0 = int(self.ragno["x"])
            y0 = int(self.ragno["y"])
            dis.rectangle([x0 + 1, y0 + 1, x0 + c - 2, y0 + c - 2],
                          fill=COLORE_RAGNO)
            for lx, ly in ((0, 0), (c - 1, 0), (0, c - 1), (c - 1, c - 1)):
                dis.point((x0 + lx, y0 + ly), fill=COLORE_RAGNO)
        for bx, by in self.colpi:
            larg = 1 if c < 6 else 2
            dis.rectangle([int(bx), int(by), int(bx) + larg - 1,
                           int(by) + max(2, c - 1)], fill=COLORE_COLPO)
        # Il cannoncino: base larga e canna in mezzo, disegnato a rettangoli
        # come tutto il resto. Sta nella zona e non la lascia mai.
        x0, y0 = int(self.gx), int(self.gy)
        meta = x0 + c // 2
        dis.rectangle([x0, y0 + c - 2, x0 + c - 1, y0 + c - 1],
                      fill=COLORE_GIOCATORE)
        dis.rectangle([meta - (1 if c >= 6 else 0), y0,
                       meta, y0 + c - 3], fill=COLORE_GIOCATORE)
        if not self.iniziata and not self.finita:
            self._disegna_titolo(dis, px)

    def _disegna_titolo(self, dis, px):
        """La schermata del titolo: nome e invito, come nei giochi di serie.

        Il campo resta disegnato sotto, fermo al fotogramma zero, e sopra
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
        centra(px, "BRUCO", meta - 5, self.colore_hud)
        centra(px, "FUOCO PER PARTIRE", meta + 3, (150, 150, 160))
