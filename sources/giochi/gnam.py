# -*- coding: utf-8 -*-
"""Gnam Gnam: il labirinto, le palline, quattro fantasmi con un carattere.

Il nome
-------
Pac-Man e' di Bandai Namco: nome, personaggio, labirinto e fantasmi. Il
meccanismo -- mangiare le palline di un labirinto scappando da chi ti insegue,
e girare la caccia con una pillola -- non e' di nessuno. Questo e' Gnam Gnam,
con un labirinto suo e fantasmi con nomi suoi.

Un labirinto largo e basso
--------------------------
Il labirinto originale e' verticale. Qui non lo si schiaccia: se ne disegna
uno per il pannello, **50 caselle per 16**, da quattro pixel l'una -- i 200
pixel di sinistra, come gli altri giochi, con il tabellone nei 56 di destra.
Corridoi larghi una casella, un tunnel che esce da un lato e rientra
dall'altro, la casa dei fantasmi in mezzo. E' simmetrico, e ogni pallina e'
raggiungibile: lo verifica una prova, non l'occhio.

I fantasmi
----------
Quattro, e ognuno insegue a modo suo -- e' l'idea che ha reso famoso
l'originale, e senza la quale il gioco e' solo scappare:

* **Rosso**, il cacciatore: punta dritto alla tua casella.
* **Rosa**, l'agguato: punta quattro caselle davanti a te, dove stai andando.
* **Azzurro**, l'imprevedibile: punta al simmetrico del rosso rispetto a un
  punto due caselle davanti a te. Da solo non fa paura; insieme al rosso ti
  chiude in mezzo.
* **Arancio**, il timido: ti insegue da lontano, ma quando ti arriva a otto
  caselle torna nel suo angolo.

E non inseguono sempre: a fasi si ritirano ognuno nel suo angolo, e il
labirinto respira. Una **pillola** grande li fa diventare blu e lenti per
qualche secondo: mangiarli vale 200, 400, 800 e 1600 punti, e i loro occhi
tornano a casa per rinascere.
"""

import math
import random

from PIL import Image

from .base import ALTEZZA, CAMPO, Gioco, centra

# ------------------------------------------------------------ il labirinto

# La meta' sinistra: la destra e' lo specchio. `#` muro, `.` pallina,
# `o` pillola, `-` porta della casa dei fantasmi, spazio vuoto.
SINISTRA = (
    "#########################",
    "#o..........#............",
    "#.####.####.#.#####.####.",
    "#.#.............#........",
    "#.#.###.#.#####.#.#####.#",
    "#.......#.....#.........#",
    "####.##.###.#.#.###.##---",
    ".....#......#.#.#...#    ",
    "####.#.####.#...#.#.#    ",
    "####.#.#......#.#.#.#####",
    "#...........#.#...#......",
    "#.###.#####.#.###.#.####.",
    "#.#.......#.......#......",
    "#.#.#####.#.#####.#.####.",
    "#o.......................",
    "#########################",
)
LABIRINTO = tuple(r + r[::-1] for r in SINISTRA)
COLONNE = len(LABIRINTO[0])          # 50
RIGHE = len(LABIRINTO)               # 16
CASELLA = 4                          # pixel
RIGA_TUNNEL = 7

# La casa: dentro, e la casella appena fuori dalla porta.
CASA = {(x, y) for y in (7, 8) for x in range(21, 29)}
USCITA = (23, 5)
DENTRO = (23, 7)
PARTENZA = (24, 14)

SU, GIU, SIN, DES = (0, -1), (0, 1), (-1, 0), (1, 0)
DIREZIONI = {"su": SU, "giu": GIU, "sinistra": SIN, "destra": DES}
# L'ordine di preferenza a parita' di distanza, come nell'originale.
ORDINE_DIR = (SU, SIN, GIU, DES)

# ------------------------------------------------------------ le regole

VELOCITA_TU = 7.5                    # caselle al secondo
VELOCITA_FANTASMA = 7.0
VELOCITA_PAURA = 4.5
VELOCITA_OCCHI = 14.0
VELOCITA_TUNNEL = 3.5

PUNTI_PALLINA = 10
PUNTI_PILLOLA = 50
PUNTI_FANTASMA = (200, 400, 800, 1600)
VITE = 3

# Dispersione e caccia, in secondi. L'ultima caccia non finisce.
FASI = (("disperdi", 7.0), ("caccia", 20.0), ("disperdi", 7.0),
        ("caccia", 20.0), ("disperdi", 5.0), ("caccia", 1e9))

PAURA = 6.0                          # secondi, al primo livello
LAMPEGGIO = 2.0                      # gli ultimi secondi, per avvisare
MORTE = 1.3                          # secondi di animazione
FINE_LIVELLO = 1.6

COLORE_MURO = (40, 70, 255)
COLORE_PORTA = (255, 170, 200)
COLORE_PALLINA = (255, 190, 160)
COLORE_TU = (255, 230, 0)
COLORE_PAURA = (60, 60, 255)
COLORE_PAURA_FINE = (230, 230, 255)
COLORE_OCCHI = (255, 255, 255)

ORDINE = ("persa", "livello", "mangia3", "lancio", "mangia1", "mangia2")

# Il motivo di sottofondo, scritto apposta (vedi diagnostica/genera_suoni.py):
# suona mentre si gioca, tace nella schermata iniziale, quando ti prendono,
# mentre il labirinto lampeggia a fine livello e a partita finita. I silenzi
# sono la meta' dell'effetto: la musica che si ferma quando ti prendono dice
# "fermo" meglio di qualunque scritta.
MUSICA = "gnam_musica"
SUONI_PER_FRAME = 2


def muro(x, y, fantasma=False):
    """La casella e' chiusa? Fuori dalle righe e' muro; fuori dalle colonne
    e' il tunnel, che fa il giro. La porta e' aperta solo ai fantasmi."""
    if not 0 <= y < RIGHE:
        return True
    c = LABIRINTO[y][x % COLONNE]
    if c == "#":
        return True
    if c == "-":
        return not fantasma
    return False


def _disegna_muri():
    """I muri come contorni di un pixel, non come blocchi pieni.

    Un'area grande di colore uniforme e basso, sul pannello, mostra le
    righe del refresh -- e' la lezione di Squadriglia. Il contorno e' quello
    dell'originale, e tiene acceso un pixel su quattro invece di tutti.
    """
    img = Image.new("RGB", (CAMPO, ALTEZZA), (0, 0, 0))
    px = img.load()
    for y in range(RIGHE):
        for x in range(COLONNE):
            c = LABIRINTO[y][x]
            x0, y0 = x * CASELLA, y * CASELLA
            if c == "-":
                for dx in range(CASELLA):
                    px[x0 + dx, y0 + 2] = COLORE_PORTA
                continue
            if c != "#":
                continue

            def aperto(nx, ny):
                if not 0 <= ny < RIGHE or not 0 <= nx < COLONNE:
                    return False
                return LABIRINTO[ny][nx] != "#"
            if aperto(x, y - 1):
                for dx in range(CASELLA):
                    px[x0 + dx, y0] = COLORE_MURO
            if aperto(x, y + 1):
                for dx in range(CASELLA):
                    px[x0 + dx, y0 + CASELLA - 1] = COLORE_MURO
            if aperto(x - 1, y):
                for dy in range(CASELLA):
                    px[x0, y0 + dy] = COLORE_MURO
            if aperto(x + 1, y):
                for dy in range(CASELLA):
                    px[x0 + CASELLA - 1, y0 + dy] = COLORE_MURO
            # Gli spigoli interni: un muro che tocca in diagonale un
            # corridoio, altrimenti gli angoli restano bucati.
            for ddx, ddy, cx, cy in ((-1, -1, 0, 0), (1, -1, 3, 0),
                                     (-1, 1, 0, 3), (1, 1, 3, 3)):
                if aperto(x + ddx, y + ddy) and not aperto(x + ddx, y) \
                        and not aperto(x, y + ddy):
                    px[x0 + cx, y0 + cy] = COLORE_MURO
    return img


_MURI = None


def muri():
    global _MURI
    if _MURI is None:
        _MURI = _disegna_muri()
    return _MURI


# Gli sprite, 4x4.
BOCCA = {
    DES: ((".##.", "##..", "##..", ".##."), (".##.", "###.", "###.", ".##.")),
    SIN: ((".##.", "..##", "..##", ".##."), (".##.", ".###", ".###", ".##.")),
    SU: (("#..#", "#..#", "####", ".##."), ("#..#", "##.#", "####", ".##.")),
    GIU: ((".##.", "####", "#..#", "#..#"), (".##.", "####", "#.##", "#..#")),
}
CHIUSA = (".##.", "####", "####", ".##.")
FANTASMA = ((".##.", "####", "####", "#.#."), (".##.", "####", "####", ".#.#"))
OCCHI = ("....", "#..#", "....", "....")


class Fantasma(object):
    def __init__(self, nome, colore, angolo, casella, attesa):
        self.nome = nome
        self.colore = colore
        self.angolo = angolo
        self.partenza = casella
        self.attesa_iniziale = attesa
        self.rimetti()

    def rimetti(self):
        self.x, self.y = float(self.partenza[0]), float(self.partenza[1])
        self.dir = SIN
        # casa -> esce -> labirinto; mangiato -> occhi -> rientra -> esce
        self.stato = "labirinto" if self.partenza == USCITA else "casa"
        self.attesa = self.attesa_iniziale
        self.paura = False

    def casella(self):
        return (int(round(self.x)) % COLONNE, int(round(self.y)))


class Gnam(Gioco):
    nome = "gnam"
    etichetta = "Gnam Gnam"
    colore_hud = COLORE_TU

    COMANDI = ("su", "giu", "sinistra", "destra", "fuoco", "avvia", "esci")

    # ---------------------------------------------------------------- partita

    def avvia_partita(self, seme=None):
        if seme is not None or not hasattr(self, "_rnd"):
            self._rnd = random.Random(seme)
        self.punteggio = 0
        self.vite = VITE
        self.livello = 1
        self.finita = False
        self.iniziata = False
        self._eventi = []
        self.suoni_del_frame = ()
        # Quale musica e' stata chiesta per ultima: si richiede solo quando
        # cambia, non a ogni fotogramma.
        self._musica_voluta = None
        self._nuovo_livello()

    def _nuovo_livello(self):
        self.palline = {(x, y): LABIRINTO[y][x]
                        for y in range(RIGHE) for x in range(COLONNE)
                        if LABIRINTO[y][x] in ".o"}
        self._fine_livello = 0.0
        self._riparti()

    def _riparti(self):
        self.x, self.y = float(PARTENZA[0]), float(PARTENZA[1])
        self.dir = SIN
        self.voluta = SIN
        self._fermo = False
        self._bocca = 0.0
        self._morte = 0.0
        self.fantasmi = [
            Fantasma("rosso", (255, 40, 40), (COLONNE - 2, -2), USCITA, 0.0),
            Fantasma("rosa", (255, 150, 220), (1, -2), (22, 7), 1.0),
            Fantasma("azzurro", (60, 230, 255), (COLONNE - 2, RIGHE + 1), (24, 7), 5.0),
            Fantasma("arancio", (255, 160, 40), (1, RIGHE + 1), (26, 7), 9.0),
        ]
        self._fase = 0
        self._tempo_fase = 0.0
        self._paura = 0.0
        self._mangiati = 0
        self._nota = 0

    def modo(self):
        return FASI[min(self._fase, len(FASI) - 1)][0]

    def _fattore(self):
        return 1.0 + 0.05 * min(6, self.livello - 1)

    def durata_paura(self):
        return max(2.0, PAURA - 0.5 * (self.livello - 1))

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
        try:
            self._fisica(dt, tasti)
        finally:
            self._emetti()
            self._accompagna()

    def musica_di_adesso(self):
        """La musica che ci vuole in questo istante: il motivo, o silenzio."""
        in_gioco = (self.iniziata and not self.finita and self._morte <= 0
                    and self._fine_livello <= 0)
        return MUSICA if in_gioco else None

    def _accompagna(self):
        voluta = self.musica_di_adesso()
        if voluta != self._musica_voluta:
            self._musica_voluta = voluta
            self.musica(voluta)

    def _fisica(self, dt, tasti):
        if self.finita:
            if "fuoco" in tasti:
                self.avvia_partita()
                self.iniziata = True
            return
        for nome, d in DIREZIONI.items():
            if nome in tasti:
                self.voluta = d
        if not self.iniziata:
            if "fuoco" in tasti:
                self.iniziata = True
            return
        if self._morte > 0:
            self._morte -= dt
            if self._morte <= 0:
                if self.vite <= 0:
                    self.finita = True
                    self._aggiorna_record()
                else:
                    self._riparti()
            return
        if self._fine_livello > 0:
            self._fine_livello -= dt
            if self._fine_livello <= 0:
                self.livello += 1
                self._nuovo_livello()
            return

        # Le fasi si fermano mentre i fantasmi hanno paura, come
        # nell'originale: la pillola non accorcia la caccia che segue.
        if self._paura > 0:
            self._paura = max(0.0, self._paura - dt)
            if self._paura == 0:
                for f in self.fantasmi:
                    f.paura = False
        else:
            self._tempo_fase += dt
            if self._tempo_fase >= FASI[min(self._fase, len(FASI) - 1)][1]:
                self._tempo_fase = 0.0
                self._fase += 1
                for f in self.fantasmi:
                    if f.stato == "labirinto":
                        f.dir = (-f.dir[0], -f.dir[1])

        self._muovi_tu(dt)
        self._mangia()
        if self._fine_livello > 0:
            return
        for f in self.fantasmi:
            self._muovi_fantasma(f, dt)
        self._scontri()

    # ------------------------------------------------------------- il tuo

    def _muovi_tu(self, dt):
        # Invertire si puo' sempre, anche a meta' corridoio: e' la prima
        # cosa che si fa scappando.
        if self.voluta == (-self.dir[0], -self.dir[1]):
            self.dir = self.voluta
            self._fermo = False
        resto = VELOCITA_TU * self._fattore() * dt
        mosso = False
        while resto > 1e-9:
            if self._al_centro(self.x, self.y):
                self.x, self.y = float(round(self.x)), float(round(self.y))
                cx, cy = int(self.x), int(self.y)
                if not muro(cx + self.voluta[0], cy + self.voluta[1]):
                    self.dir = self.voluta
                if muro(cx + self.dir[0], cy + self.dir[1]):
                    self._fermo = True
                    break
            self._fermo = False
            passo = min(resto, self._al_prossimo(self.x, self.y, self.dir))
            self.x += self.dir[0] * passo
            self.y += self.dir[1] * passo
            self.x = self._avvolgi(self.x)
            resto -= passo
            mosso = True
        if mosso:
            self._bocca += dt

    @staticmethod
    def _al_centro(x, y):
        return abs(x - round(x)) < 1e-6 and abs(y - round(y)) < 1e-6

    @staticmethod
    def _al_prossimo(x, y, d):
        """Quanto manca al prossimo centro di casella, nella direzione d."""
        v = x if d[0] else y
        s = d[0] or d[1]
        f = v - math.floor(v)
        if f < 1e-6:
            return 1.0
        return (1.0 - f) if s > 0 else f

    @staticmethod
    def _avvolgi(x):
        if x < -0.5:
            x += COLONNE
        elif x > COLONNE - 0.5:
            x -= COLONNE
        return x

    def casella_tu(self):
        return (int(round(self.x)) % COLONNE, int(round(self.y)))

    def _mangia(self):
        c = self.casella_tu()
        cosa = self.palline.pop(c, None)
        if cosa is None:
            return
        if cosa == "o":
            self.punteggio += PUNTI_PILLOLA
            self._paura = self.durata_paura()
            self._mangiati = 0
            self._segna("lancio")
            for f in self.fantasmi:
                if f.stato == "labirinto":
                    f.paura = True
                    f.dir = (-f.dir[0], -f.dir[1])
        else:
            self.punteggio += PUNTI_PALLINA
            self._nota = 1 - self._nota
            self._segna("mangia%d" % (self._nota + 1))
        self._aggiorna_record()
        if not self.palline:
            self._segna("livello")
            self._fine_livello = FINE_LIVELLO

    # ----------------------------------------------------------- i fantasmi

    def bersaglio(self, f):
        """La casella a cui punta un fantasma, secondo il suo carattere."""
        if self.modo() == "disperdi":
            return f.angolo
        tx, ty = self.casella_tu()
        d = self.dir
        if f.nome == "rosso":
            return (tx, ty)
        if f.nome == "rosa":
            return (tx + 4 * d[0], ty + 4 * d[1])
        if f.nome == "azzurro":
            rosso = self.fantasmi[0].casella()
            px, py = tx + 2 * d[0], ty + 2 * d[1]
            return (2 * px - rosso[0], 2 * py - rosso[1])
        # arancio
        if (tx - f.x) ** 2 + (ty - f.y) ** 2 > 64:
            return (tx, ty)
        return f.angolo

    def _velocita(self, f):
        if f.stato == "occhi":
            return VELOCITA_OCCHI
        if f.stato in ("casa", "uscita", "rientro"):
            return 3.0
        if int(round(f.y)) == RIGA_TUNNEL and (f.x < 5 or f.x > COLONNE - 6):
            return VELOCITA_TUNNEL
        if f.paura:
            return VELOCITA_PAURA
        return VELOCITA_FANTASMA * self._fattore()

    def _muovi_fantasma(self, f, dt):
        v = self._velocita(f) * dt
        if f.stato == "casa":
            f.attesa -= dt
            if f.attesa <= 0:
                f.stato = "uscita"
            # Nella casa si dondola su e giu', in attesa.
            f.y = 7.0 + 0.4 * math.sin(f.attesa * 6.0)
            return
        if f.stato == "uscita":
            if abs(f.x - USCITA[0]) > 1e-6:
                self._verso(f, (USCITA[0], 7), v)
            else:
                self._verso(f, USCITA, v)
            if (f.x, f.y) == (float(USCITA[0]), float(USCITA[1])):
                f.stato = "labirinto"
                f.dir = SIN
            return
        if f.stato == "rientro":
            self._verso(f, DENTRO, v)
            if (f.x, f.y) == (float(DENTRO[0]), float(DENTRO[1])):
                f.stato = "uscita"
                f.paura = False
            return
        resto = v
        while resto > 1e-9:
            if self._al_centro(f.x, f.y):
                f.x, f.y = float(round(f.x)), float(round(f.y))
                c = (int(f.x) % COLONNE, int(f.y))
                if f.stato == "occhi" and c == USCITA:
                    f.stato = "rientro"
                    return
                f.dir = self._scegli(f, c)
            passo = min(resto, self._al_prossimo(f.x, f.y, f.dir))
            f.x += f.dir[0] * passo
            f.y += f.dir[1] * passo
            f.x = self._avvolgi(f.x)
            resto -= passo

    @staticmethod
    def _verso(f, meta, v):
        """Movimento libero, dentro e davanti alla casa: prima in orizzontale,
        poi in verticale. Li' non ci sono corridoi da rispettare."""
        mx, my = float(meta[0]), float(meta[1])
        if f.x != mx:
            d = mx - f.x
            f.x += max(-v, min(v, d))
            f.dir = DES if d > 0 else SIN
        elif f.y != my:
            d = my - f.y
            f.y += max(-v, min(v, d))
            f.dir = GIU if d > 0 else SU

    def _scegli(self, f, c):
        indietro = (-f.dir[0], -f.dir[1])
        porta = f.stato == "occhi"
        possibili = [d for d in ORDINE_DIR
                     if d != indietro and not muro(c[0] + d[0], c[1] + d[1], porta)
                     and (c[0] + d[0], c[1] + d[1]) not in CASA]
        if not possibili:
            return indietro
        if f.paura and f.stato == "labirinto":
            return self._rnd.choice(possibili)
        meta = USCITA if f.stato == "occhi" else self.bersaglio(f)

        def distanza(d):
            nx, ny = c[0] + d[0], c[1] + d[1]
            return (nx - meta[0]) ** 2 + (ny - meta[1]) ** 2
        return min(possibili, key=distanza)

    def _scontri(self):
        tx, ty = self.x, self.y
        for f in self.fantasmi:
            if f.stato != "labirinto":
                continue
            dx = abs(f.x - tx)
            dx = min(dx, COLONNE - dx)
            if dx < 0.6 and abs(f.y - ty) < 0.6:
                if f.paura:
                    f.paura = False
                    f.stato = "occhi"
                    self.punteggio += PUNTI_FANTASMA[min(self._mangiati, 3)]
                    self._mangiati += 1
                    self._aggiorna_record()
                    self._segna("mangia3")
                else:
                    self.vite -= 1
                    self._morte = MORTE
                    self._segna("persa")
                    return

    # -------------------------------------------------------------- disegno

    def _sprite(self, px, righe, x, y, colore):
        x0 = int(round(x * CASELLA))
        y0 = int(round(y * CASELLA))
        for r, riga in enumerate(righe):
            for c, ch in enumerate(riga):
                if ch == "#":
                    # Nel tunnel lo sprite esce da un lato e rientra
                    # dall'altro, un pixel alla volta.
                    xx = (x0 + c) % CAMPO
                    yy = y0 + r
                    if 0 <= xx < CAMPO and 0 <= yy < ALTEZZA:
                        px[xx, yy] = colore

    def disegna_campo(self, img, px):
        lampo = self._fine_livello > 0 and int(self._fine_livello * 6) % 2 == 0
        if not lampo:
            img.paste(muri(), (0, 0))
        for (x, y), cosa in self.palline.items():
            x0, y0 = x * CASELLA, y * CASELLA
            if cosa == "o":
                if int(self._bocca * 4) % 2 == 0 or not self.iniziata:
                    for dx in (1, 2):
                        for dy in (1, 2):
                            px[x0 + dx, y0 + dy] = COLORE_PALLINA
            else:
                px[x0 + 1, y0 + 1] = COLORE_PALLINA

        if not self.finita:
            for f in self.fantasmi:
                if self._morte > 0 or self._fine_livello > 0:
                    break
                if f.stato in ("occhi", "rientro"):
                    self._sprite(px, OCCHI, f.x, f.y, COLORE_OCCHI)
                    continue
                if f.paura:
                    fine = self._paura < LAMPEGGIO and int(self._paura * 6) % 2 == 0
                    colore = COLORE_PAURA_FINE if fine else COLORE_PAURA
                else:
                    colore = f.colore
                self._sprite(px, FANTASMA[int(self._bocca * 8) % 2], f.x, f.y, colore)
            if self._morte > 0:
                # Si richiude su se stesso: sempre meno pixel.
                quanti = int(4 * self._morte / MORTE)
                righe = CHIUSA[:max(0, quanti)]
                self._sprite(px, righe, self.x, self.y + (4 - len(righe)) / 4.0,
                             COLORE_TU)
            else:
                aperta = int(self._bocca * 12) % 2 == 0 and not self._fermo
                forma = BOCCA[self.dir][0] if aperta else CHIUSA
                self._sprite(px, forma, self.x, self.y, COLORE_TU)

        if not self.iniziata and not self.finita:
            for y in range(28, 36):
                for x in range(86, 114):
                    px[x, y] = (0, 0, 0)
            centra(px, "FUOCO", 30, COLORE_TU)
