# -*- coding: utf-8 -*-
"""Quello che i giochi hanno in comune: il font, il quadro, le regole.

**Il font e' disegnato a mano, 3x5.** Non e' pigrizia al contrario: un TTF
rimpicciolito a sei pixel su un pannello LED diventa poltiglia, ed e' la
stessa lezione della 1.10 — le intensita' intermedie sono la causa dello
sfarfallio, non il numero di colori. Qui ogni pixel e' acceso o spento.

**Il pannello e' 4:1 e non si combatte.** Invece di far finta che sia 4:3, il
campo di gioco prende i 200 pixel di sinistra e i 56 di destra diventano un
tabellone: punteggio, vite, livello. Su uno schermo di un flipper e' esatta-
mente quello che uno si aspetta di vedere, ed e' spazio che altrimenti
resterebbe vuoto.
"""

from PIL import Image, ImageDraw

LARGHEZZA = 256
ALTEZZA = 64
CAMPO = 200                     # campo di gioco, a sinistra
HUD = LARGHEZZA - CAMPO         # tabellone, a destra

# Font 3x5: cinque righe da tre bit. Maiuscole e cifre bastano a un tabellone,
# e quello che manca diventa uno spazio invece di far cadere il disegno.
_F = {
    "0": (0b111, 0b101, 0b101, 0b101, 0b111),
    "1": (0b010, 0b110, 0b010, 0b010, 0b111),
    "2": (0b111, 0b001, 0b111, 0b100, 0b111),
    "3": (0b111, 0b001, 0b111, 0b001, 0b111),
    "4": (0b101, 0b101, 0b111, 0b001, 0b001),
    "5": (0b111, 0b100, 0b111, 0b001, 0b111),
    "6": (0b111, 0b100, 0b111, 0b101, 0b111),
    "7": (0b111, 0b001, 0b001, 0b001, 0b001),
    "8": (0b111, 0b101, 0b111, 0b101, 0b111),
    "9": (0b111, 0b101, 0b111, 0b001, 0b111),
    "A": (0b111, 0b101, 0b111, 0b101, 0b101),
    "B": (0b110, 0b101, 0b110, 0b101, 0b110),
    "C": (0b111, 0b100, 0b100, 0b100, 0b111),
    "D": (0b110, 0b101, 0b101, 0b101, 0b110),
    "E": (0b111, 0b100, 0b111, 0b100, 0b111),
    "F": (0b111, 0b100, 0b111, 0b100, 0b100),
    "G": (0b111, 0b100, 0b101, 0b101, 0b111),
    "H": (0b101, 0b101, 0b111, 0b101, 0b101),
    "I": (0b111, 0b010, 0b010, 0b010, 0b111),
    "J": (0b001, 0b001, 0b001, 0b101, 0b111),
    "K": (0b101, 0b101, 0b110, 0b101, 0b101),
    "L": (0b100, 0b100, 0b100, 0b100, 0b111),
    "M": (0b101, 0b111, 0b111, 0b101, 0b101),
    "N": (0b110, 0b101, 0b101, 0b101, 0b101),
    "O": (0b111, 0b101, 0b101, 0b101, 0b111),
    "P": (0b111, 0b101, 0b111, 0b100, 0b100),
    "Q": (0b111, 0b101, 0b101, 0b111, 0b011),
    "R": (0b111, 0b101, 0b111, 0b110, 0b101),
    "S": (0b111, 0b100, 0b111, 0b001, 0b111),
    "T": (0b111, 0b010, 0b010, 0b010, 0b010),
    "U": (0b101, 0b101, 0b101, 0b101, 0b111),
    "V": (0b101, 0b101, 0b101, 0b101, 0b010),
    "W": (0b101, 0b101, 0b111, 0b111, 0b101),
    "X": (0b101, 0b101, 0b010, 0b101, 0b101),
    "Y": (0b101, 0b101, 0b010, 0b010, 0b010),
    "Z": (0b111, 0b001, 0b010, 0b100, 0b111),
    " ": (0, 0, 0, 0, 0),
    "-": (0, 0, 0b111, 0, 0),
    ".": (0, 0, 0, 0, 0b010),
    ":": (0, 0b010, 0, 0b010, 0),
    "!": (0b010, 0b010, 0b010, 0, 0b010),
    # Dalla 13.0 anche la punteggiatura che serve a una **frase**, non a un
    # tabellone: fino a ieri qui si scrivevano punteggi e nomi di livello, e
    # un punto interrogativo non serviva a nessuno. Super Quiz fa domande, e
    # una domanda senza il punto interrogativo non e' una domanda.
    "?": (0b111, 0b001, 0b011, 0, 0b010),
    "'": (0b010, 0b010, 0, 0, 0),
    ",": (0, 0, 0, 0b010, 0b100),
    '"': (0b101, 0b101, 0, 0, 0),
    "(": (0b001, 0b010, 0b010, 0b010, 0b001),
    ")": (0b100, 0b010, 0b010, 0b010, 0b100),
    "/": (0b001, 0b001, 0b010, 0b100, 0b100),
    "+": (0, 0b010, 0b111, 0b010, 0),
    "%": (0b101, 0b001, 0b010, 0b100, 0b101),
    "\u00b0": (0b010, 0b101, 0b010, 0, 0),
    "\u2026": (0, 0, 0, 0, 0b111),
}

# Le lettere accentate diventano la lettera senza accento. Un font 3x5 non ha
# lo spazio per un accento -- sarebbe un pixel sopra una lettera alta cinque
# -- e in italiano una «e» al posto di una «è» si legge lo stesso, mentre un
# buco no: fino alla 12.6 «piu'» scritto con l'accento diventava «pi».
_EQUIVALENTI = {}
for _senza, _con in (("A", "ÀÁÂÃÄÅ"), ("E", "ÈÉÊË"), ("I", "ÌÍÎÏ"),
                     ("O", "ÒÓÔÕÖØ"), ("U", "ÙÚÛÜ"), ("C", "Ç"),
                     ("N", "Ñ"), ("Y", "Ý"), ("S", "Š"), ("Z", "Ž"),
                     ("AE", "Æ"), ("OE", "Œ"), ("SS", "ß"),
                     ("'", "\u2019\u02bc"), ('"', "\u201c\u201d\u00ab\u00bb"),
                     ("-", "\u2013\u2014")):
    for _lettera in _con:
        _EQUIVALENTI[_lettera] = _senza
PASSO = 4       # 3 pixel di glifo piu' uno di spazio
RIGA = 7        # 5 pixel di altezza piu' due di interlinea


def larghezza_testo(testo):
    # Sulla stringa **tradotta**: «Æ» diventa «AE» e occupa due posti, e una
    # riga centrata sul conto sbagliato esce dal pannello.
    return max(0, len(senza_accenti(testo)) * PASSO - 1)


def senza_accenti(testo):
    """Il testo come lo sa scrivere il font: maiuscolo e senza accenti."""
    fuori = []
    for carattere in str(testo).upper():
        fuori.append(_EQUIVALENTI.get(carattere, carattere))
    return "".join(fuori)


def scrivi(px, testo, x, y, colore):
    """Testo 3x5 pixel per pixel. `px` e' l'accesso ai pixel dell'immagine."""
    for carattere in senza_accenti(testo):
        glifo = _F.get(carattere)
        if glifo is not None:
            for riga, bit in enumerate(glifo):
                for colonna in range(3):
                    if bit & (1 << (2 - colonna)):
                        xx, yy = x + colonna, y + riga
                        if 0 <= xx < LARGHEZZA and 0 <= yy < ALTEZZA:
                            px[xx, yy] = colore
        x += PASSO


def centra(px, testo, y, colore, sinistra=0, larghezza=CAMPO):
    scrivi(px, testo, sinistra + (larghezza - larghezza_testo(testo)) // 2,
           y, colore)


# ------------------------------------------------------------------ il gioco

class Gioco:
    """Un gioco che sa disegnarsi su 256x64 e avanzare di un passo.

    `passo` riceve il tempo trascorso e l'insieme dei comandi premuti in
    questo istante, e non legge niente da solo: cosi' una partita intera si
    puo' far giocare da una prova, senza pannello e senza pad, e il risultato
    e' lo stesso che si vede sul cabinato.
    """
    nome = ""
    etichetta = ""
    colore_hud = (255, 140, 26)

    # Comandi che il gioco capisce, per la pagina web e per la tastiera.
    COMANDI = ("sinistra", "destra", "fuoco", "avvia", "esci")

    def __init__(self, seme=None):
        # Chi vuole sentire i suoni la sostituisce. Di suo non fa niente, e
        # non e' pigrizia: un gioco che sapesse di schede audio e di
        # configurazione non si potrebbe piu' far girare dentro una prova.
        self.suona = lambda nome: None
        # La musica di sottofondo, per chi ce l'ha: nome per farla partire,
        # None per fermarla. Come `suona`, la sostituisce chi apre la partita.
        self.musica = lambda nome: None
        self._musica_voluta = None
        self.punteggio = 0
        self.vite = 3
        self.livello = 1
        self.finita = False
        self._record = 0
        self.avvia_partita(seme)

    # --------------------------------------------------------------- da fare

    def avvia_partita(self, seme=None):
        """Riporta il gioco all'inizio. La chiama anche il pulsante Rigioca."""
        raise NotImplementedError

    def passo(self, dt, tasti):
        raise NotImplementedError

    def disegna_campo(self, img, px):
        raise NotImplementedError

    # --------------------------------------------------------------- musica

    # Il brano di sottofondo del gioco, un file in `suoni/` senza estensione.
    # None: il gioco non ne ha.
    MUSICA = None

    def musica_di_adesso(self):
        """La musica che ci vuole in questo istante. Di serie: il brano del
        gioco finche' si gioca, silenzio a partita finita. I giochi con una
        schermata iniziale o dei momenti muti la ridefiniscono."""
        return self.MUSICA if (self.MUSICA and not self.finita) else None

    def accompagna(self):
        """Chiede la musica giusta, ma solo quando cambia: non a ogni
        fotogramma, e senza farla ricominciare."""
        voluta = self.musica_di_adesso()
        if voluta != self._musica_voluta:
            self._musica_voluta = voluta
            self.musica(voluta)

    # --------------------------------------------------------------- comune

    def record(self):
        return max(self._record, self.punteggio)

    def _aggiorna_record(self):
        self._record = max(self._record, self.punteggio)

    def stato(self):
        return {"nome": self.nome, "punteggio": self.punteggio,
                "vite": self.vite, "livello": self.livello,
                "record": self.record(), "finita": self.finita}

    def disegna(self):
        img = Image.new("RGB", (LARGHEZZA, ALTEZZA), (0, 0, 0))
        px = img.load()
        self.disegna_campo(img, px)
        self._disegna_hud(px)
        if self.finita:
            self._disegna_fine(px)
        return img

    def _disegna_hud(self, px):
        """Il tabellone a destra: e' lo spazio che il 4:1 regala."""
        x = CAMPO + 4
        for colonna in range(ALTEZZA):
            px[CAMPO + 1, colonna] = (40, 40, 48)      # riga di separazione
        scrivi(px, "SCORE", x, 4, (120, 120, 130))
        scrivi(px, "%06d" % self.punteggio, x, 11, self.colore_hud)
        scrivi(px, "HI", x, 22, (120, 120, 130))
        scrivi(px, "%06d" % self.record(), x, 29, (90, 150, 220))
        scrivi(px, "LIV %d" % self.livello, x, 40, (120, 120, 130))
        # Le vite come simboli, non come numero: si contano in un'occhiata.
        for i in range(max(0, min(6, self.vite))):
            px[x + i * 5, 52] = self.colore_hud
            for dx in range(3):
                px[x + i * 5 - 1 + dx, 53] = self.colore_hud

    def _disegna_fine(self, px):
        for y in range(24, 40):
            for x in range(0, CAMPO):
                if (x + y) % 2 == 0:
                    px[x, y] = (0, 0, 0)
        centra(px, "GAME OVER", 27, (255, 60, 60))
        centra(px, "FUOCO PER RIGIOCARE", 35, (150, 150, 160))
