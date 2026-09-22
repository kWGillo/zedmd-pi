# -*- coding: utf-8 -*-
"""Mine vaganti: una nave, un campo minato nello spazio, disegnato a linee.

Il nome
-------
Il gioco che veniva di serie dentro il Vectrex ha un nome suo, e resta suo.
Lo schema -- una posamine che semina, mine che si schiudono e si dividono,
una nave che ruota, spinge e spara -- non e' di nessuno. Questo e' Mine
vaganti.

Lo stile
--------
Solo **linee luminose su nero**, con un bagliore tenue sotto ognuna: il
fosforo che sbava. Sul pannello e' anche la scelta giusta per un altro motivo:
nessuna campitura, quindi nessuna riga di refresh (la lezione di Squadriglia).

Il gioco
--------
* All'inizio di ogni livello passa la **posamine** e lascia i **semi**: i
  puntini fiochi. Tre si schiudono subito in mine grandi.
* Ogni mina abbattuta ne fa schiudere **due piu' piccole** da altri semi,
  sparsi nel campo: grande, media, piccola. Finiti semi e mine, livello nuovo.
* Le mine sono di quattro specie, una in piu' a ogni livello:
  **galleggianti** (vanno dritte), **di fuoco** (abbattute sparano una palla
  di fuoco verso di te), **magnetiche** (ti inseguono), **magnetiche di
  fuoco** (tutte e due le cose).
* Sinistra e destra ruotano, su spinge, fuoco spara, il tasto speciale
  (cerchio) e' il **salto**: sparisci e ricompari altrove -- non si sa dove.

Il campo e' tutto il pannello sotto una riga di tabellone, e i bordi si
riattaccano: quello che esce a destra rientra a sinistra. Il 4:1 qui aiuta:
256 pixel di corsa sono tanto spazio per vedere arrivare una mina.
"""

import math
import random

from PIL import Image, ImageDraw

from .base import ALTEZZA, LARGHEZZA, Gioco, centra, scrivi

# ------------------------------------------------------------------ il campo

CIMA = 7                               # sopra, il tabellone
ALTO = ALTEZZA - CIMA                  # 57 righe di spazio
LARGO = LARGHEZZA

# La nave
ROTAZIONE = 4.2                        # radianti al secondo
SPINTA = 95.0                          # pixel al secondo quadrato
VELOCITA_MAX = 60.0
ATTRITO = 0.55                         # quanto la nave rallenta da sola, al secondo
RAGGIO_NAVE = 2.5
VITE = 3
VITA_OGNI = 10000

# Il fuoco
VELOCITA_COLPO = 150.0
DURATA_COLPO = 0.7
COLPI_MAX = 4
CADENZA = 0.18

# Il salto
DURATA_SALTO = 0.6
RIPOSO_SALTO = 2.5

# Le mine
SEMI = 21                  # tre mine grandi, sei medie, dodici piccole
RAGGIO = {3: 7.5, 2: 5.0, 1: 3.0}
VELOCITA_MINA = {3: 9.0, 2: 14.0, 1: 20.0}
SCHIUSA = 0.7              # mentre si schiude la mina non fa male e non si colpisce
LONTANO_DA_TE = 20.0       # nessuna mina si schiude piu' vicino di cosi'
ATTRAZIONE = 22.0          # le magnetiche: pixel al secondo quadrato verso di te

GALLEGGIANTE = "galleggiante"
FUOCO = "fuoco"
MAGNETICA = "magnetica"
MAGNETICA_FUOCO = "magnetica_fuoco"
SPECIE = (GALLEGGIANTE, FUOCO, MAGNETICA, MAGNETICA_FUOCO)
PUNTI_SPECIE = {GALLEGGIANTE: 100, FUOCO: 150, MAGNETICA: 200, MAGNETICA_FUOCO: 250}
PUNTI_TAGLIA = {3: 1.0, 2: 1.5, 1: 2.0}   # le piccole valgono di piu': sono difficili
PUNTI_PALLA = 110
PUNTI_LIVELLO = 1000

# Le palle di fuoco
VELOCITA_PALLA = 48.0
DURATA_PALLA = 3.5
RAGGIO_PALLA = 1.5

# La posamine
DURATA_POSAMINE = 3.0

# Dopo la morte
DURATA_MORTE = 1.6
PROTEZIONE = 1.6

COLORE_NAVE = (200, 240, 255)
COLORE_FIAMMA = (255, 150, 60)
COLORE_COLPO = (255, 255, 255)
COLORE_MINA = {GALLEGGIANTE: (90, 170, 255), FUOCO: (255, 140, 50),
               MAGNETICA: (90, 255, 140), MAGNETICA_FUOCO: (255, 80, 200)}
COLORE_PALLA = (255, 200, 60)
COLORE_SEME = (70, 90, 130)
COLORE_POSAMINE = (160, 160, 255)
COLORE_HUD = (150, 150, 165)
COLORE_TITOLO = (90, 170, 255)
COLORE_FINE = (255, 60, 60)

ORDINE = ("persa", "livello", "colpito", "lancio", "tonfo", "sparo")
SUONI_PER_FRAME = 2
MUSICA = "mine_musica"


def _stella(punte, interno):
    """Una stella di `punte` punte: coppie (angolo, raggio relativo)."""
    pts = []
    for k in range(punte * 2):
        pts.append((k * math.pi / punte - math.pi / 2, 1.0 if k % 2 == 0 else interno))
    return pts


# Le sagome delle mine, in coordinate polari relative al raggio. Diverse di
# forma e non solo di colore: su un pannello visto da lontano il colore da
# solo non basta.
SAGOMA = {
    GALLEGGIANTE: _stella(3, 0.3),
    FUOCO: _stella(4, 0.3),
    MAGNETICA: _stella(3, 0.55),
    MAGNETICA_FUOCO: _stella(4, 0.55),
}


def _avvolgi(d, lato):
    """La distanza piu' corta su un campo che si riattacca."""
    d = (d + lato / 2.0) % lato - lato / 2.0
    return d


class Mina(object):
    __slots__ = ("x", "y", "vx", "vy", "taglia", "specie", "schiusa", "angolo", "giro")

    def __init__(self, x, y, taglia, specie, rnd, fattore):
        self.x, self.y = x, y
        self.taglia = taglia
        self.specie = specie
        direzione = rnd.uniform(0, 2 * math.pi)
        v = VELOCITA_MINA[taglia] * fattore
        self.vx, self.vy = math.cos(direzione) * v, math.sin(direzione) * v * 0.6
        self.schiusa = SCHIUSA
        self.angolo = rnd.uniform(0, 2 * math.pi)
        self.giro = rnd.choice((-1, 1)) * rnd.uniform(0.4, 1.0)

    @property
    def raggio(self):
        return RAGGIO[self.taglia]

    def attiva(self):
        return self.schiusa <= 0

    def magnetica(self):
        return self.specie in (MAGNETICA, MAGNETICA_FUOCO)

    def di_fuoco(self):
        return self.specie in (FUOCO, MAGNETICA_FUOCO)


class Mine(Gioco):
    nome = "mine"
    etichetta = "Mine vaganti"
    colore_hud = COLORE_TITOLO
    MUSICA = MUSICA

    COMANDI = ("su", "sinistra", "destra", "fuoco", "speciale", "avvia", "esci")

    # ---------------------------------------------------------------- partita

    def avvia_partita(self, seme=None):
        if seme is not None or not hasattr(self, "_rnd"):
            self._rnd = random.Random(seme)
        self.punteggio = 0
        self.vite = VITE
        self.livello = 1
        self.finita = False
        self.iniziata = False
        self._prossima_vita = VITA_OGNI
        self._eventi = []
        self.suoni_del_frame = ()
        self._prima = set()
        self._nave_al_centro()
        self._nuovo_livello()

    def _nave_al_centro(self):
        self.x, self.y = LARGO / 2.0, ALTO / 2.0
        self.vx = self.vy = 0.0
        self.angolo = -math.pi / 2          # la punta in su
        self.spinge = False
        self._salto = 0.0
        self._riposo_salto = 0.0
        self._protetto = PROTEZIONE
        self._morto = 0.0

    def _nuovo_livello(self):
        self.mine = []
        self.palle = []
        self.colpi = []
        self._esplosioni = []
        self._da_colpo = 0.0
        self.semi = []
        self._da_seminare = []
        self._posamine = DURATA_POSAMINE
        self._scritta = ("LIVELLO %d" % self.livello, 2.0)
        # I semi: sparsi, ma nessuno addosso al centro, dove sei tu.
        while len(self._da_seminare) < SEMI:
            x = self._rnd.uniform(4, LARGO - 4)
            y = self._rnd.uniform(3, ALTO - 3)
            if math.hypot(_avvolgi(x - self.x, LARGO), _avvolgi(y - self.y, ALTO)) > 28:
                self._da_seminare.append((x, y))
        self._da_seminare.sort()
        self._riga_posamine = self._rnd.uniform(8, ALTO - 8)

    def fattore(self):
        """Quanto vanno piu' veloci le mine, livello dopo livello."""
        return 1.0 + 0.1 * min(10, self.livello - 1)

    def specie_ammesse(self):
        return SPECIE[:min(len(SPECIE), self.livello)]

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
        premuti_ora = set(tasti) - self._prima
        self._prima = set(tasti)
        try:
            self._fisica(dt, set(tasti), premuti_ora)
        finally:
            self._emetti()

    def _fisica(self, dt, tasti, premuti_ora):
        if self.finita:
            if "fuoco" in premuti_ora:
                self.avvia_partita()
                self.iniziata = True
            return
        if not self.iniziata:
            if "fuoco" in premuti_ora:
                self.iniziata = True
            return

        testo, resta = self._scritta
        self._scritta = (testo, resta - dt)
        self._esplosioni = [e[:4] + [e[4] - dt] for e in self._esplosioni if e[4] - dt > 0]

        if self._morto > 0:
            self._morto -= dt
            if self._morto <= 0:
                self._rinasci()
        else:
            self._muovi_nave(dt, tasti, premuti_ora)

        self._semina(dt)
        self._muovi_colpi(dt)
        self._muovi_mine(dt)
        self._muovi_palle(dt)
        self._urti()
        self._schiudi_se_serve()
        self._fine_livello()
        if self.punteggio >= self._prossima_vita:
            self._prossima_vita += VITA_OGNI
            self.vite += 1
            self._segna("livello")
        self._aggiorna_record()

    # ------------------------------------------------------------------ nave

    def in_gioco(self):
        """La nave c'e': non esplosa e non nel mezzo di un salto."""
        return self._morto <= 0 and self._salto <= 0

    def _muovi_nave(self, dt, tasti, premuti_ora):
        self._riposo_salto = max(0.0, self._riposo_salto - dt)
        self._protetto = max(0.0, self._protetto - dt)
        self._da_colpo = max(0.0, self._da_colpo - dt)
        if self._salto > 0:
            self._salto -= dt
            if self._salto <= 0:
                self._atterra()
            return
        if "sinistra" in tasti:
            self.angolo -= ROTAZIONE * dt
        if "destra" in tasti:
            self.angolo += ROTAZIONE * dt
        self.spinge = "su" in tasti
        if self.spinge:
            self.vx += math.cos(self.angolo) * SPINTA * dt
            self.vy += math.sin(self.angolo) * SPINTA * dt
        smorza = math.exp(-ATTRITO * dt)
        self.vx *= smorza
        self.vy *= smorza
        v = math.hypot(self.vx, self.vy)
        if v > VELOCITA_MAX:
            self.vx *= VELOCITA_MAX / v
            self.vy *= VELOCITA_MAX / v
        self.x = (self.x + self.vx * dt) % LARGO
        self.y = (self.y + self.vy * dt) % ALTO
        if "speciale" in premuti_ora and self._riposo_salto <= 0:
            self._salto = DURATA_SALTO
            self._riposo_salto = RIPOSO_SALTO + DURATA_SALTO
            self.spinge = False
            self._segna("lancio")
            return
        if "fuoco" in tasti and self._da_colpo <= 0 and len(self.colpi) < COLPI_MAX:
            self._spara()

    def _spara(self):
        c, s = math.cos(self.angolo), math.sin(self.angolo)
        self.colpi.append([self.x + c * 4, self.y + s * 4,
                           c * VELOCITA_COLPO + self.vx * 0.5,
                           s * VELOCITA_COLPO + self.vy * 0.5, DURATA_COLPO])
        self._da_colpo = CADENZA
        self._segna("sparo")

    def _atterra(self):
        """Il salto: dove si ricompare non lo decide nessuno. Si pescano due
        punti a caso e si prende il meno affollato: un aiuto, non una
        garanzia -- nel gioco originale il salto e' un azzardo, e qui pure."""
        migliore, distanza = None, -1.0
        for _ in range(2):
            x, y = self._rnd.uniform(0, LARGO), self._rnd.uniform(0, ALTO)
            d = min([self._distanza(x, y, m.x, m.y) - m.raggio
                     for m in self.mine] or [999.0])
            if d > distanza:
                migliore, distanza = (x, y), d
        self.x, self.y = migliore
        self.vx = self.vy = 0.0

    def _distanza(self, x1, y1, x2, y2):
        return math.hypot(_avvolgi(x2 - x1, LARGO), _avvolgi(y2 - y1, ALTO))

    def _perdi(self):
        self._morto = DURATA_MORTE
        self.spinge = False
        self.vite -= 1
        self._esplosioni.append([self.x, self.y, COLORE_NAVE, 9.0, 1.0])
        self._segna("persa")
        if self.vite <= 0:
            self.finita = True
            self._morto = 0.0
            self._aggiorna_record()

    def _rinasci(self):
        # Si rinasce al centro, ma solo quando li' non c'e' niente: altrimenti
        # si aspetta ancora un po', come nell'originale.
        cx, cy = LARGO / 2.0, ALTO / 2.0
        libero = all(self._distanza(cx, cy, m.x, m.y) > m.raggio + 16 for m in self.mine) \
            and all(self._distanza(cx, cy, p[0], p[1]) > 16 for p in self.palle)
        if not libero:
            self._morto = 0.2
            return
        self._nave_al_centro()

    # ------------------------------------------------------------------ colpi

    def _muovi_colpi(self, dt):
        vivi = []
        for c in self.colpi:
            c[0] = (c[0] + c[2] * dt) % LARGO
            c[1] = (c[1] + c[3] * dt) % ALTO
            c[4] -= dt
            if c[4] > 0:
                vivi.append(c)
        self.colpi = vivi

    # ------------------------------------------------------------------ mine

    def _semina(self, dt):
        if self._posamine <= 0:
            return
        self._posamine -= dt
        fronte = LARGO * (1.0 - max(0.0, self._posamine) / DURATA_POSAMINE)
        while self._da_seminare and self._da_seminare[0][0] <= fronte:
            self.semi.append(self._da_seminare.pop(0))
        if self._posamine <= 0:
            self.semi.extend(self._da_seminare)
            self._da_seminare = []
            self._schiudi(3, min(3, len(self.semi)), None)

    def posamine(self):
        """Dove sta la posamine, o None se e' gia' passata."""
        if self._posamine <= 0:
            return None
        return LARGO * (1.0 - self._posamine / DURATA_POSAMINE), self._riga_posamine

    def _schiudi(self, taglia, quante, specie):
        for _ in range(quante):
            if not self.semi:
                return
            # Mai addosso alla nave: si sceglie fra i semi abbastanza lontani,
            # e solo se non ce n'e' nessuno si prende il piu' lontano.
            lontani = [s for s in self.semi
                       if self._distanza(s[0], s[1], self.x, self.y) > LONTANO_DA_TE]
            if lontani:
                seme = self._rnd.choice(lontani)
            else:
                seme = max(self.semi, key=lambda s: self._distanza(s[0], s[1], self.x, self.y))
            self.semi.remove(seme)
            quale = specie
            if quale is None:
                ammesse = self.specie_ammesse()
                # La specie nuova del livello si fa vedere di piu'.
                quale = ammesse[-1] if self._rnd.random() < 0.5 else self._rnd.choice(ammesse)
            self.mine.append(Mina(seme[0], seme[1], taglia, quale, self._rnd, self.fattore()))

    def _schiudi_se_serve(self):
        if self._posamine > 0 or self.mine or not self.semi:
            return
        self._schiudi(3, min(3, len(self.semi)), None)

    def _muovi_mine(self, dt):
        for m in self.mine:
            if m.schiusa > 0:
                m.schiusa -= dt
                continue
            m.angolo += m.giro * dt
            if m.magnetica() and self.in_gioco():
                dx = _avvolgi(self.x - m.x, LARGO)
                dy = _avvolgi(self.y - m.y, ALTO)
                d = math.hypot(dx, dy) or 1.0
                m.vx += dx / d * ATTRAZIONE * dt
                m.vy += dy / d * ATTRAZIONE * dt
                limite = VELOCITA_MINA[m.taglia] * self.fattore() * 1.4
                v = math.hypot(m.vx, m.vy)
                if v > limite:
                    m.vx *= limite / v
                    m.vy *= limite / v
            m.x = (m.x + m.vx * dt) % LARGO
            m.y = (m.y + m.vy * dt) % ALTO

    def _muovi_palle(self, dt):
        vive = []
        for p in self.palle:
            p[0] = (p[0] + p[2] * dt) % LARGO
            p[1] = (p[1] + p[3] * dt) % ALTO
            p[4] -= dt
            if p[4] > 0:
                vive.append(p)
        self.palle = vive

    def _lancia_palla(self, m):
        dx = _avvolgi(self.x - m.x, LARGO)
        dy = _avvolgi(self.y - m.y, ALTO)
        d = math.hypot(dx, dy) or 1.0
        v = VELOCITA_PALLA * self.fattore()
        self.palle.append([m.x, m.y, dx / d * v, dy / d * v, DURATA_PALLA])
        self._segna("tonfo")

    # ------------------------------------------------------------------ urti

    def _urti(self):
        for c in list(self.colpi):
            for m in self.mine:
                if m.attiva() and self._distanza(c[0], c[1], m.x, m.y) < m.raggio + 1.0:
                    self._abbatti(m)
                    self.colpi.remove(c)
                    break
            else:
                for p in self.palle:
                    if self._distanza(c[0], c[1], p[0], p[1]) < RAGGIO_PALLA + 1.5:
                        self.palle.remove(p)
                        self.colpi.remove(c)
                        self.punteggio += PUNTI_PALLA
                        self._esplosioni.append([p[0], p[1], COLORE_PALLA, 3.0, 0.4])
                        self._segna("colpito")
                        break
        if not self.in_gioco() or self._protetto > 0:
            return
        for m in self.mine:
            if m.attiva() and self._distanza(self.x, self.y, m.x, m.y) < m.raggio * 0.8 + RAGGIO_NAVE:
                self._abbatti(m, da_urto=True)
                self._perdi()
                return
        for p in self.palle:
            if self._distanza(self.x, self.y, p[0], p[1]) < RAGGIO_PALLA + RAGGIO_NAVE:
                self.palle.remove(p)
                self._perdi()
                return

    def _abbatti(self, m, da_urto=False):
        self.mine.remove(m)
        if not da_urto:
            self.punteggio += int(PUNTI_SPECIE[m.specie] * PUNTI_TAGLIA[m.taglia])
        self._esplosioni.append([m.x, m.y, COLORE_MINA[m.specie], m.raggio + 3, 0.5])
        self._segna("colpito")
        if m.di_fuoco() and not da_urto and self.in_gioco():
            self._lancia_palla(m)
        if m.taglia > 1:
            self._schiudi(m.taglia - 1, 2, m.specie)

    def _fine_livello(self):
        if self._posamine > 0 or self.mine or self.semi or self.palle:
            return
        if self._morto > 0:
            return
        self.punteggio += PUNTI_LIVELLO
        self.livello += 1
        self._segna("livello")
        self._nuovo_livello()

    # -------------------------------------------------------------- disegno

    def disegna_campo(self, img, px):          # pragma: no cover - non usata
        pass

    def _sagoma_nave(self, x, y, angolo, scala=1.0):
        c, s = math.cos(angolo), math.sin(angolo)

        def p(a, b):
            return (x + (a * c - b * s) * scala, y + (a * s + b * c) * scala)
        punta, sx, dx, coda = p(4.5, 0), p(-3, -3), p(-3, 3), p(-1.5, 0)
        return [(punta, sx), (sx, coda), (coda, dx), (dx, punta)]

    def _tratti_campo(self):
        """I segmenti del campo, in coordinate del campo (senza tabellone)."""
        t = []
        # La posamine: un'astronave larga che passa.
        pm = self.posamine() if self.iniziata else None
        if pm is not None:
            x, y = pm
            forma = ((-7, 0), (-3, -3), (5, -3), (8, 0), (5, 3), (-3, 3))
            for i in range(len(forma)):
                a, b = forma[i], forma[(i + 1) % len(forma)]
                t.append(((x + a[0], y + a[1]), (x + b[0], y + b[1]), COLORE_POSAMINE))
        for m in self.mine:
            r = m.raggio
            colore = COLORE_MINA[m.specie]
            if m.schiusa > 0:
                # Mentre si schiude: cresce e si accende piano.
                quota = 1.0 - m.schiusa / SCHIUSA
                r *= 0.3 + 0.7 * quota
                colore = tuple(int(c * (0.25 + 0.4 * quota)) for c in colore)
            pts = [(m.x + math.cos(a + m.angolo) * r * k,
                    m.y + math.sin(a + m.angolo) * r * k)
                   for a, k in SAGOMA[m.specie]]
            for i in range(len(pts)):
                t.append((pts[i], pts[(i + 1) % len(pts)], colore))
        for p in self.palle:
            x, y = p[0], p[1]
            r = RAGGIO_PALLA
            t.append(((x - r, y), (x + r, y), COLORE_PALLA))
            t.append(((x, y - r), (x, y + r), COLORE_PALLA))
        for c in self.colpi:
            v = math.hypot(c[2], c[3]) or 1.0
            t.append(((c[0], c[1]), (c[0] - c[2] / v * 1.5, c[1] - c[3] / v * 1.5), COLORE_COLPO))
        for x, y, colore, grande, resta in self._esplosioni:
            r = grande * (1.2 - min(1.0, resta * 2))
            for k in range(8):
                a = k * math.pi / 4 + 0.4
                t.append(((x + math.cos(a) * r * 0.5, y + math.sin(a) * r * 0.5),
                          (x + math.cos(a) * r, y + math.sin(a) * r), colore))
        if self.iniziata and not self.finita and self.in_gioco():
            lampeggia = self._protetto > 0 and int(self._protetto * 8) % 2 == 0
            if not lampeggia:
                t.extend((a, b, COLORE_NAVE) for a, b in self._sagoma_nave(self.x, self.y, self.angolo))
                if self.spinge:
                    c, s = math.cos(self.angolo), math.sin(self.angolo)
                    lungo = 5.0 + (int(self._riposo_salto * 30 + self.x) % 2)
                    t.append(((self.x - c * 2.5, self.y - s * 2.5),
                              (self.x - c * lungo, self.y - s * lungo), COLORE_FIAMMA))
        return t

    def disegna(self):
        img = Image.new("RGB", (LARGHEZZA, ALTEZZA), (0, 0, 0))
        campo = Image.new("RGB", (LARGO, ALTO), (0, 0, 0))
        d = ImageDraw.Draw(campo)
        tratti = self._tratti_campo()
        # Il campo si riattacca: chi e' vicino a un bordo si disegna anche
        # dall'altra parte. Il ritaglio dell'immagine fa il resto.
        copie = []
        for a, b, colore in tratti:
            xs, ys = (a[0], b[0]), (a[1], b[1])
            spost_x = [0]
            if min(xs) < 0:
                spost_x.append(LARGO)
            if max(xs) >= LARGO - 1:
                spost_x.append(-LARGO)
            spost_y = [0]
            if min(ys) < 0:
                spost_y.append(ALTO)
            if max(ys) >= ALTO - 1:
                spost_y.append(-ALTO)
            for ox in spost_x:
                for oy in spost_y:
                    copie.append(((a[0] + ox, a[1] + oy), (b[0] + ox, b[1] + oy), colore))
        for a, b, colore in copie:
            d.line([a, b], fill=tuple(int(c * 0.22) for c in colore), width=3)
        pc = campo.load()
        # I semi: un puntino fioco ciascuno, come sul fosforo.
        for x, y in self.semi:
            pc[int(x) % LARGO, int(y) % ALTO] = COLORE_SEME
        for a, b, colore in copie:
            d.line([a, b], fill=colore, width=1)
        img.paste(campo, (0, CIMA))
        px = img.load()
        self._disegna_hud(ImageDraw.Draw(img), px)
        return img

    def _disegna_hud(self, d, px):
        scrivi(px, "%06d" % self.punteggio, 1, 1, COLORE_TITOLO)
        scrivi(px, "HI %06d" % self.record(), 32, 1, (90, 150, 220))
        scrivi(px, "LIV %d" % self.livello, 76, 1, COLORE_HUD)
        # Le vite: navette a destra.
        for i in range(max(0, min(8, self.vite))):
            x0 = LARGHEZZA - 5 - i * 7
            for (a, b) in self._sagoma_nave(x0, 3, -math.pi / 2, 0.6):
                d.line([a, b], fill=COLORE_NAVE, width=1)
        testo, resta = self._scritta
        if resta > 0 and self.iniziata and not self.finita:
            centra(px, testo, 1, COLORE_HUD, sinistra=100, larghezza=80)
        if not self.iniziata and not self.finita:
            d.rectangle([80, 22, 176, 45], fill=(0, 0, 0))
            centra(px, "MINE VAGANTI", 26, COLORE_TITOLO, larghezza=LARGHEZZA)
            centra(px, "FUOCO PER PARTIRE", 36, COLORE_HUD, larghezza=LARGHEZZA)
            # Le quattro specie, come promemoria, ai lati del titolo.
            for i, specie in enumerate(SPECIE):
                x = (30, 55, 201, 226)[i]
                pts = [(x + math.cos(a) * 6 * k, 34 + math.sin(a) * 6 * k)
                       for a, k in SAGOMA[specie]]
                for j in range(len(pts)):
                    d.line([pts[j], pts[(j + 1) % len(pts)]], fill=COLORE_MINA[specie])
        if self.finita:
            d.rectangle([80, 24, 176, 45], fill=(0, 0, 0))
            centra(px, "GAME OVER", 27, COLORE_FINE, larghezza=LARGHEZZA)
            centra(px, "FUOCO PER RIGIOCARE", 36, COLORE_HUD, larghezza=LARGHEZZA)
