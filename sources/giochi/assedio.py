# -*- coding: utf-8 -*-
# fix-v3 2026-10-31
"""Assedio: missili che piovono, citta' da tenere in piedi.

Il nome
-------
Il gioco dei missili che piovono sulle citta' ha un nome suo, e resta suo.
Lo schema -- un mirino, tre basi che sparano intercettori, ondate di
missili nemici che si fermano solo nelle palle di fuoco -- non e' di
nessuno, come per tutti gli altri giochi del catalogo. Questo e' Assedio:
codice scritto da zero contro il contratto di `Gioco`, nome nostro,
disegno nostro, numeri nostri.

Il gioco
--------
* In basso, su una striscia di terra, stanno **sei citta' e tre basi**,
  alternate: base, due citta', base, due citta', base, due citta'.
  Ogni base ha dieci intercettori per ondata.
* La croce direzionale muove il mirino nel cielo. Fuoco lancia un
  intercettore dalla base piu' vicina che ha ancora munizioni: viaggia
  veloce, lascia una scia che svanisce, e dove arriva **detona**: una
  palla di fuoco che cresce, tiene, si spegne. Dura poco piu' di un
  secondo, ed e' l'unico muro che c'e' fra i missili e le citta'.
* I missili nemici scendono a filo d'acqua per tutta l'ondata, e puntano
  soprattutto quello che e' ancora in piedi. Chi arriva distrugge la
  citta' o la base che trova: una base distrutta perde le sue munizioni,
  e non torna. Un missile preso in una palla di fuoco vale 25 punti.
* Dal livello tre in poi qualche missile **si divide in tre** a meta'
  discesa.
* Finita l'ondata: 100 punti per ogni citta' rimasta, 5 per ogni
  intercettore non speso, munizioni di nuovo piene, ondata dopo.
  Si perde quando l'ultima citta' cade.
* All'apertura la partita sta ferma sulla schermata del titolo -- il
  nome e «FUOCO PER PARTIRE», come nei giochi di serie: il primo
  missile scende solo quando si preme fuoco, e quella pressione e'
  spesa li', non lancia nessun intercettore.
"""

import math
import random

from PIL import ImageDraw

from .base import Gioco, centra, larghezza_testo

# Le nove posizioni sulla striscia di terra, da sinistra: le basi stanno
# agli indici 0, 3, 6 e le citta' in tutti gli altri. E' la disposizione
# che mette una base a tiro di mirino da qualunque punto del cielo.
TIPI = ("base", "citta", "citta", "base", "citta", "citta",
        "base", "citta", "citta")
MUNIZIONI = 10                  # intercettori per base, per ondata

PAUSA_SPARO = 0.25              # secondi fra un lancio riuscito e il prossimo

VELOCITA_MIRINO = 95.0          # pixel al secondo
VELOCITA_INTERCETTORE = 320.0   # deve arrivare prima del nemico, sempre
VELOCITA_NEMICO = 18.0          # pixel al secondo, all'ondata uno
CRESCITA_NEMICO = 1.08          # ogni ondata i missili scendono piu' forte

DURATA_PALLA = 1.2              # la vita di una palla di fuoco, in secondi
CRESCITA_PALLA = 0.35           # quanto impiega a aprirsi tutta
PIENA_PALLA = 0.8               # fino a quando resta aperta

PUNTI_MISSILE = 25
PUNTI_CITTA = 100
PUNTI_MUNIZIONE = 5

COLORI = {
    "terra": (52, 58, 22),
    "citta": (84, 156, 255),
    "macerie": (70, 64, 58),
    "base": (216, 164, 74),
    "nemico": (255, 70, 50),
    "testa": (255, 170, 130),
    "scia": (52, 110, 128),
    "intercettore": (150, 235, 255),
    "bersaglio": (90, 140, 150),
    "mirino": (240, 240, 240),
    "palla1": (255, 226, 160),
    "palla2": (255, 150, 50),
    "palla3": (206, 70, 34),
}


class Assedio(Gioco):
    nome = "assedio"
    etichetta = "Assedio"
    colore_hud = (255, 170, 40)
    COMANDI = ("sinistra", "destra", "su", "giu", "fuoco", "avvia", "esci")
    TELA_LIBERA = True

    # ------------------------------------------------------------- la partita

    def avvia_partita(self, seme=None):
        self._rng = random.Random(seme)
        self.punteggio = 0
        self.livello = 1
        # Le vite non sono la posta di questo gioco: la posta sono le
        # citta'. Zero vite e il tabellone non disegna simboli a vuoto.
        self.vite = 0
        self.finita = False
        self.iniziata = False
        self._prec = set()
        self._tempo = 0.0
        # La pausa fra un lancio e il prossimo: a zero a inizio partita,
        # cosi' il primo intercettore parte subito.
        self._attesa_sparo = 0.0
        self.nemici = []
        self.intercettori = []
        self.palle = []
        self._posa_geometria()
        self.strutture = []
        for i, tipo in enumerate(TIPI):
            self.strutture.append({
                "tipo": tipo,
                "x": self.campo_x + (i + 0.5) * self.passo_slot,
                "viva": True,
                "munizioni": MUNIZIONI if tipo == "base" else 0,
            })
        self.mirino_x = self.campo_x + self.campo_l / 2.0
        self.mirino_y = self.campo_y + self.campo_a / 3.0
        self._inizia_ondata()

    def ignora_tasti(self, premuti):
        """Il tasto che ha aperto la partita non deve lanciare un intercettore."""
        self._prec = set(premuti)

    def _posa_geometria(self):
        """Tutto si misura sul campo di adesso, pannello o schermo alto.

        La terra e' una striscia sul fondo del campo e le strutture ci
        stanno dentro in piedi: sul pannello sono disegni da quattro
        pixel, sullo schermo alto diventano palazzi. Il raggio della
        palla di fuoco e' un quinto dell'altezza del campo, col minimo
        di nove: abbastanza da chiudere un corridoio di cielo.
        """
        self.passo_slot = self.campo_l / float(len(TIPI))
        self.suolo_a = max(6, self.campo_a // 10)
        self.fondo = self.campo_y + self.campo_a     # la prima riga fuori
        self.terra_y = self.fondo - self.suolo_a     # dove comincia la terra
        self.citta_l = max(6, self.campo_l // 28)
        self.citta_a = max(4, self.campo_a // 13)
        self.base_l = self.citta_l + 6
        self.base_a = self.citta_a + 2
        self.raggio_max = max(9, self.campo_a // 5)

    # ------------------------------------------------------------- le ondate

    def _inizia_ondata(self):
        """Prepara l'ondata numero `livello`: quanti missili, e munizioni piene.

        Le basi distrutte non tornano e non ricevono niente: la loro
        striscia di terra resta vuota per il resto della partita.
        """
        self._da_lanciare = 8 + 4 * self.livello
        self._attesa_lancio = 0.8
        for s in self.strutture:
            if s["tipo"] == "base" and s["viva"]:
                s["munizioni"] = MUNIZIONI

    def _fine_ondata(self):
        """Il conto della sopravvivenza, poi l'ondata dopo."""
        vive = sum(1 for s in self.strutture
                   if s["tipo"] == "citta" and s["viva"])
        restanti = sum(s["munizioni"] for s in self.strutture
                       if s["tipo"] == "base" and s["viva"])
        self.punteggio += (PUNTI_CITTA * vive
                           + PUNTI_MUNIZIONE * restanti)
        self.livello += 1
        self.suona("livello")
        self._inizia_ondata()

    def _velocita_nemico(self):
        return (VELOCITA_NEMICO * (CRESCITA_NEMICO ** (self.livello - 1))
                * self._rng.uniform(0.8, 1.25))

    def _crea_nemico(self, x0, y0, x1, velocita=None):
        """Un missile nemico: nasce in alto e punta un punto sulla terra."""
        y1 = float(self.fondo - 2)
        dist = max(1.0, math.hypot(x1 - x0, y1 - y0))
        if velocita is None:
            velocita = self._velocita_nemico()
        return {
            "x": float(x0), "y": float(y0),
            "x0": float(x0), "y0": float(y0),
            "dx": (x1 - x0) / dist, "dy": (y1 - y0) / dist,
            "y1": y1, "velocita": velocita,
            "divisore": (self.livello >= 3
                         and self._rng.random() < 0.35),
            "soglia": y0 + (y1 - y0) * self._rng.uniform(0.35, 0.6),
            "diviso": False,
        }

    def _lancia_nemico(self):
        """Un missile nuovo: tre volte su quattro punta qualcosa di vivo."""
        vive = [i for i, s in enumerate(self.strutture) if s["viva"]]
        if vive and self._rng.random() < 0.75:
            i = self._rng.choice(vive)
        else:
            i = self._rng.randrange(len(TIPI))
        x1 = (self.strutture[i]["x"]
              + self._rng.uniform(-self.passo_slot / 3.0,
                                  self.passo_slot / 3.0))
        x0 = self.campo_x + self._rng.uniform(2, self.campo_l - 3)
        self.nemici.append(self._crea_nemico(x0, float(self.campo_y), x1))

    def _dividi(self, m):
        """Il missile divisore si apre in tre: lui e due figli nuovi."""
        m["diviso"] = True
        for _ in range(2):
            vive = [s for s in self.strutture if s["viva"]]
            if vive and self._rng.random() < 0.75:
                bersaglio = self._rng.choice(vive)["x"]
            else:
                bersaglio = self._rng.uniform(self.campo_x + 4,
                                              self.campo_x + self.campo_l - 5)
            bersaglio += self._rng.uniform(-self.passo_slot / 3.0,
                                           self.passo_slot / 3.0)
            figlio = self._crea_nemico(m["x"], m["y"], bersaglio,
                                       velocita=m["velocita"])
            figlio["divisore"] = False
            self.nemici.append(figlio)

    # ------------------------------------------------------------- il fuoco

    def _spara(self):
        """Lancia dalla base viva piu' vicina al mirino che ha munizioni."""
        basi = [s for s in self.strutture
                if s["tipo"] == "base" and s["viva"] and s["munizioni"] > 0]
        if not basi:
            return False
        base = min(basi, key=lambda s: abs(s["x"] - self.mirino_x))
        base["munizioni"] -= 1
        x0, y0 = base["x"], float(self.fondo - self.base_a)
        x1, y1 = self.mirino_x, self.mirino_y
        dist = max(1.0, math.hypot(x1 - x0, y1 - y0))
        self.intercettori.append({
            "x": x0, "y": y0, "x0": x0, "y0": y0, "x1": x1, "y1": y1,
            "dx": (x1 - x0) / dist, "dy": (y1 - y0) / dist,
            "dist": dist, "percorso": 0.0,
            "scia": [(x0, y0, self._tempo)],
        })
        self.suona("lancio")
        return True

    def _raggio(self, palla):
        """Il raggio di adesso di una palla: cresce, tiene, si spegne."""
        eta = palla["eta"]
        if eta < CRESCITA_PALLA:
            return self.raggio_max * eta / CRESCITA_PALLA
        if eta < PIENA_PALLA:
            return float(self.raggio_max)
        return self.raggio_max * max(
            0.0, (DURATA_PALLA - eta) / (DURATA_PALLA - PIENA_PALLA))

    def _impatto(self, m):
        """Il missile nemico e' arrivato: quello che trova, lo distrugge."""
        i = min(range(len(TIPI)),
                key=lambda j: abs(self.strutture[j]["x"] - m["x"]))
        if abs(self.strutture[i]["x"] - m["x"]) > self.passo_slot * 0.6:
            return                      # terra libera: fumo e niente punti
        s = self.strutture[i]
        if not s["viva"]:
            return
        s["viva"] = False
        s["munizioni"] = 0
        self.suona("persa")
        if s["tipo"] == "citta" and not any(
                t["viva"] for t in self.strutture if t["tipo"] == "citta"):
            self.finita = True

    # ---------------------------------------------------------------- passo

    def passo(self, dt, tasti):
        if self.finita:
            if "fuoco" in tasti:
                self.avvia_partita()
                self.iniziata = True
                # La pressione che ricomincia resta nei precedenti,
                # come gia' premuta: non deve sparare nella partita nuova.
                self._prec = set(tasti)
            return
        if not self.iniziata:
            # La schermata del titolo, come nei giochi di serie: il cielo
            # sta fermo e si parte solo col fuoco, sul fronte di salita.
            # La pressione che fa partire e' spesa li': resta fra i
            # precedenti, e il primo intercettore non parte da solo.
            if "fuoco" in tasti - self._prec:
                self.iniziata = True
            self._prec = set(tasti)
            return
        self._tempo += dt
        if self._attesa_sparo > 0.0:
            self._attesa_sparo = max(0.0, self._attesa_sparo - dt)
        nuovi = tasti - self._prec

        # Il mirino: libero nel cielo, mai dentro la terra.
        if "sinistra" in tasti:
            self.mirino_x -= VELOCITA_MIRINO * dt
        if "destra" in tasti:
            self.mirino_x += VELOCITA_MIRINO * dt
        if "su" in tasti:
            self.mirino_y -= VELOCITA_MIRINO * dt
        if "giu" in tasti:
            self.mirino_y += VELOCITA_MIRINO * dt
        self.mirino_x = max(self.campo_x + 3,
                            min(self.campo_x + self.campo_l - 4,
                                self.mirino_x))
        self.mirino_y = max(self.campo_y + 3,
                            min(self.terra_y - 5, self.mirino_y))

        if "fuoco" in nuovi and self._attesa_sparo <= 0.0:
            # Solo un lancio riuscito fa partire la pausa: un tentativo
            # a vuoto, senza basi o senza munizioni, non blocca il colpo
            # dopo.
            if self._spara():
                self._attesa_sparo = PAUSA_SPARO

        # Senza difesa l'attesa non ha senso: se le basi vive non hanno
        # piu' munizioni e nessun intercettore e' in volo, i missili che
        # restano partono tutti insieme, cosi' l'ondata si chiude per la
        # strada di sempre invece di scendere a goccia davanti a un
        # giocatore che puo' solo guardare.
        if (self._da_lanciare > 0 and not self.intercettori
                and sum(s["munizioni"] for s in self.strutture
                        if s["tipo"] == "base" and s["viva"]) == 0):
            while self._da_lanciare > 0:
                self._lancia_nemico()
                self._da_lanciare -= 1

        # L'ondata scende a filo: un missile ogni tanto, non tutti insieme.
        if self._da_lanciare > 0:
            self._attesa_lancio -= dt
            if self._attesa_lancio <= 0.0:
                self._lancia_nemico()
                self._da_lanciare -= 1
                intervallo = self._rng.uniform(0.3, 1.4)
                self._attesa_lancio = intervallo / (
                    1.0 + 0.06 * (self.livello - 1))

        # Gli intercettori viaggiano; dove arrivano, detonano.
        for it in list(self.intercettori):
            it["percorso"] += VELOCITA_INTERCETTORE * dt
            if it["percorso"] >= it["dist"]:
                self.intercettori.remove(it)
                self.palle.append({"x": it["x1"], "y": it["y1"], "eta": 0.0})
                continue
            it["x"] = it["x0"] + it["dx"] * it["percorso"]
            it["y"] = it["y0"] + it["dy"] * it["percorso"]
            it["scia"].append((it["x"], it["y"], self._tempo))
            it["scia"] = [p for p in it["scia"]
                          if self._tempo - p[2] <= 0.35]

        # I nemici scendono; qualcuno si divide; chi arriva, colpisce.
        for m in list(self.nemici):
            m["x"] += m["dx"] * m["velocita"] * dt
            m["y"] += m["dy"] * m["velocita"] * dt
            if m["divisore"] and not m["diviso"] and m["y"] >= m["soglia"]:
                self._dividi(m)
            if m["y"] >= m["y1"]:
                self.nemici.remove(m)
                self._impatto(m)

        # Le palle di fuoco invecchiano e mangiano quello che ci passa.
        for palla in list(self.palle):
            palla["eta"] += dt
            if palla["eta"] >= DURATA_PALLA:
                self.palle.remove(palla)
                continue
            raggio = self._raggio(palla)
            if raggio <= 0.0:
                continue
            for m in list(self.nemici):
                if math.hypot(m["x"] - palla["x"],
                              m["y"] - palla["y"]) <= raggio:
                    self.nemici.remove(m)
                    self.punteggio += PUNTI_MISSILE
                    self.suona("colpito")

        # Ondata finita solo quando il cielo e' davvero vuoto.
        if (self._da_lanciare == 0 and not self.nemici
                and not self.intercettori and not self.palle
                and not self.finita):
            self._fine_ondata()

        self._prec = set(tasti)

    # --------------------------------------------------------------- disegno

    def _struttura(self, dis, s):
        cx = int(round(s["x"]))
        fondo = self.fondo
        if s["tipo"] == "citta":
            if not s["viva"]:
                # Macerie: due pixel bassi e spenti dove stava la citta'.
                dis.rectangle([cx - 2, fondo - 2, cx + 2, fondo - 1],
                              fill=COLORI["macerie"])
                dis.point((cx, fondo - 3), fill=COLORI["macerie"])
                return
            l, a = self.citta_l, self.citta_a
            dis.rectangle([cx - l // 2, fondo - a // 2 - 1,
                           cx - l // 2 + l - 1, fondo - 1],
                          fill=COLORI["citta"])
            torre = max(2, l // 3)
            dis.rectangle([cx - torre // 2, fondo - a,
                           cx - torre // 2 + torre - 1, fondo - a // 2 - 2],
                          fill=COLORI["citta"])
            return
        # La base: un dosso largo con la rampa in cima. Distrutta, resta
        # solo il dosso, spento.
        l, a = self.base_l, self.base_a
        colore = COLORI["base"] if s["viva"] else COLORI["macerie"]
        dis.rectangle([cx - l // 2, fondo - a // 2,
                       cx - l // 2 + l - 1, fondo - 1], fill=colore)
        rampa = max(3, l // 2)
        dis.rectangle([cx - rampa // 2, fondo - a,
                       cx - rampa // 2 + rampa - 1, fondo - a // 2 - 1],
                      fill=colore)
        if s["viva"]:
            # Le munizioni: una fila di punti sotto la base, sul fondo.
            passo = max(2, int(self.passo_slot) // 10)
            inizio = cx - (MUNIZIONI * passo) // 2
            for i in range(s["munizioni"]):
                x = inizio + i * passo
                dis.rectangle([x, fondo - 2, x, fondo - 1],
                              fill=COLORI["intercettore"])

    def disegna_campo(self, img, px):
        dis = ImageDraw.Draw(img)
        # La terra, e sopra la terra le strutture.
        dis.rectangle([self.campo_x, self.terra_y,
                       self.campo_x + self.campo_l - 1, self.fondo - 1],
                      fill=COLORI["terra"])
        for s in self.strutture:
            self._struttura(dis, s)
        # I nemici: una linea dalla partenza alla testa.
        for m in self.nemici:
            dis.line([m["x0"], m["y0"], m["x"], m["y"]],
                     fill=COLORI["nemico"])
            dis.point((int(m["x"]), int(m["y"])), fill=COLORI["testa"])
        # Gli intercettori: la scia che svanisce, la testa, il bersaglio.
        for it in self.intercettori:
            if len(it["scia"]) > 1:
                dis.line([(p[0], p[1]) for p in it["scia"]],
                         fill=COLORI["scia"])
            tx, ty = int(it["x1"]), int(it["y1"])
            dis.point((tx, ty), fill=COLORI["bersaglio"])
            dis.point((tx - 1, ty), fill=COLORI["bersaglio"])
            dis.point((tx + 1, ty), fill=COLORI["bersaglio"])
            dis.point((int(it["x"]), int(it["y"])),
                      fill=COLORI["intercettore"])
        # Le palle di fuoco: il colore dice in che momento sono.
        for palla in self.palle:
            r = self._raggio(palla)
            if r < 0.5:
                continue
            if palla["eta"] < CRESCITA_PALLA:
                colore = COLORI["palla1"]
            elif palla["eta"] < PIENA_PALLA:
                colore = COLORI["palla2"]
            else:
                colore = COLORI["palla3"]
            dis.ellipse([palla["x"] - r, palla["y"] - r,
                         palla["x"] + r, palla["y"] + r], fill=colore)
        # Il mirino: una croce con il centro vuoto.
        mx, my = int(round(self.mirino_x)), int(round(self.mirino_y))
        braccio = max(2, self.campo_a // 32)
        c = COLORI["mirino"]
        for d in range(2, braccio + 2):
            dis.point((mx - d, my), fill=c)
            dis.point((mx + d, my), fill=c)
            dis.point((mx, my - d), fill=c)
            dis.point((mx, my + d), fill=c)
        if not self.iniziata and not self.finita:
            self._disegna_titolo(dis, px)

    def _disegna_titolo(self, dis, px):
        """La schermata del titolo: nome e invito, come nei giochi di serie.

        Il cielo resta disegnato sotto, fermo al fotogramma zero, e sopra
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
        centra(px, "ASSEDIO", meta - 5, self.colore_hud)
        centra(px, "FUOCO PER PARTIRE", meta + 3, (150, 150, 160))
