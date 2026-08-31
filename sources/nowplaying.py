"""Player sul pannello: che cosa sta suonando, a che punto, in quale stato.

Quattro righe su 64 pixel di altezza: titolo, artista, album, e una riga di
trasporto con il simbolo play/pausa, il tempo trascorso, la barra di
avanzamento e la durata. Il titolo scorre da solo quando non ci sta.

Due scelte di resa nascono dai limiti del pannello, non dal gusto:

**Niente antialiasing.** PIL sfuma i bordi delle lettere, e ogni sfumatura e'
un pixel a intensita' intermedia. Su una matrice a S-PWM con refresh basso
sono proprio le intensita' intermedie a produrre lo sfarfallio, mentre i
colori pieni restano fermi. Qui il testo si disegna passando da una maschera
in scala di grigi ridotta a due soli valori: acceso o spento.

**Colori saturi.** Con `safe_colors` attivo ogni componente viene portata a 0
o 255, il che lascia otto colori in tutto. Sembra poco, ma sono gli stessi
otto di una PNG a palette che sul pannello non trema, e la gerarchia fra le
righe si ottiene cambiando tinta invece che luminosita': bianco per il
titolo, ciano per l'artista, blu per l'album — che a parita' di saturazione
l'occhio legge come piu' scuro.

La copertina dell'album non c'e' apposta. A 64x64 pixel sarebbe illeggibile,
e soprattutto una miniatura e' fatta quasi solo di mezzi toni: significherebbe
tenere in permanenza sullo schermo il contenuto peggiore per questo pannello.
"""

import time

from PIL import Image, ImageDraw, ImageFont

from .base import Source
from .clock import _load_font, parse_color

# Font a larghezza fissa per la riga dei tempi. L'ordine non e' casuale: il
# monospace di DejaVu, ridotto a due livelli a questa dimensione, disegna la
# cifra 1 come una parentesi quadra e "13:31" si legge "]3:3]". Quello di
# Liberation tiene la bandierina e la base, e le cifre restano distinte.
MONO_CANDIDATES = [
    "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationMono-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
]

# Corpo dei font come frazione dell'altezza del pannello.
TITLE_RATIO = 0.28
ARTIST_RATIO = 0.22
ALBUM_RATIO = 0.17
TIME_RATIO = 0.175


def _load_mono(size):
    for path in MONO_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return _load_font(size)

# Sotto queste altezze si semplifica invece di sovrapporre le righe.
COMPACT_HEIGHT = 48     # sparisce l'album
MINIMAL_HEIGHT = 30     # restano titolo e barra

# Scorrimento del titolo.
SCROLL_SPEED = 24       # pixel al secondo
SCROLL_GAP = 0.25       # spazio fra la fine e il ricomincio, in frazioni di pannello
SCROLL_HOLD = 1.5       # secondi di fermo prima di partire

DEFAULT_COLORS = {
    "title_color": "#ffffff",
    "artist_color": "#00ffff",
    "album_color": "#0000ff",
    "bar_color": "#ffff00",
}


def snap_color(rgb):
    """Porta ogni componente a 0 o 255: restano gli otto colori pieni."""
    return tuple(255 if value >= 128 else 0 for value in rgb)


def draw_text(image, xy, text, font, color, threshold=128):
    """Scrive senza antialiasing.

    `font.getmask` restituisce una maschera in scala di grigi: i pixel di
    bordo valgono le vie di mezzo. Riducendola a due soli livelli si ottiene
    un testo netto, che a questa dimensione si legge anche meglio, e
    soprattutto non introduce intensita' intermedie sul pannello.
    """
    if not text:
        return
    mask = font.getmask(str(text), mode="L")
    if mask.size[0] <= 0 or mask.size[1] <= 0:
        return
    binary = Image.frombytes("L", mask.size, bytes(mask)).point(
        lambda value: 255 if value >= threshold else 0)
    image.paste(color, (int(xy[0]), int(xy[1])), binary)


def text_width(text, font):
    if not text:
        return 0
    return font.getmask(str(text), mode="L").size[0]


class NowPlayingSource(Source):
    name = "nowplaying"
    label = "Now Playing"
    # Sopra il Media Player (50) e il Rolling Banner (55): mentre suona
    # qualcosa il player resta a schermo invece di alternarsi alle foto.
    # Sotto Air Radar (60), che dura pochi secondi, e sotto ZeDMD (100),
    # perche' durante una partita comanda il flipper.
    priority = 58

    def __init__(self, cfg, width, height, state=None):
        super().__init__(cfg, width, height)
        self.state = state
        self._running = False
        self._signature = None
        self._scroll_start = 0.0
        self._scroll_key = None

        self._font_title = _load_font(max(8, int(height * TITLE_RATIO)))
        self._font_artist = _load_font(max(7, int(height * ARTIST_RATIO)))
        self._font_album = _load_font(max(6, int(height * ALBUM_RATIO)))
        self._font_time = _load_mono(max(6, int(height * TIME_RATIO)))

    # ------------------------------------------------------------------ ciclo

    def start(self):
        self._running = True
        self._signature = None

    def stop(self):
        self._running = False

    def invalidate(self):
        self._signature = None

    def settings(self):
        return self.cfg.get("nowplaying") or {}

    def color(self, key):
        raw = self.settings().get(key, DEFAULT_COLORS[key])
        rgb = parse_color(raw, parse_color(DEFAULT_COLORS[key]))
        if self.settings().get("safe_colors", True):
            return snap_color(rgb)
        return rgb

    # ------------------------------------------------------------------ arbitro

    def active(self):
        if not self._running or self.state is None:
            return False
        track = self.state.snapshot()
        return bool(track["title"] or track["artist"])

    def status(self, lang=None):
        if not self._running:
            return self.t("status.disabled", lang)
        if self.state is None:
            return self.t("status.nowplaying.idle", lang)
        track = self.state.snapshot()
        if not (track["title"] or track["artist"]):
            return self.t("status.nowplaying.idle", lang)
        key = "status.nowplaying.playing" if track["playing"] \
            else "status.nowplaying.paused"
        return self.t(key, lang,
                      title=track["title"] or "—",
                      artist=track["artist"] or "—",
                      source=track["source"])

    # ------------------------------------------------------------------ resa

    def frame(self):
        if not self._running or self.state is None:
            return None
        track = self.state.snapshot()
        if not (track["title"] or track["artist"]):
            return None

        title_width = text_width(track["title"], self._font_title)
        scrolling = title_width > self.width - 6

        # Il titolo che scorre va ridisegnato a ogni giro; tutto il resto solo
        # quando cambia qualcosa di visibile. Il tempo si arrotonda al secondo
        # perche' e' la risoluzione con cui viene scritto.
        signature = (track["title"], track["artist"], track["album"],
                     track["playing"], int(track["position"]),
                     int(track["duration"]))
        if not scrolling and signature == self._signature:
            return None
        self._signature = signature

        return self.render(track, scrolling)

    def render(self, track, scrolling=None):
        image = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        draw = ImageDraw.Draw(image)
        margin = max(1, self.width // 85)          # 3 px su un pannello da 256

        rows = self._layout()
        self._draw_title(image, track, margin, rows, scrolling)

        if rows["artist"] is not None:
            draw_text(image, (margin, rows["artist"]), track["artist"],
                      self._font_artist, self.color("artist_color"))
        if rows["album"] is not None:
            draw_text(image, (margin, rows["album"]), track["album"],
                      self._font_album, self.color("album_color"))

        self._draw_transport(image, draw, track, margin, rows)
        return image

    @staticmethod
    def _riga_alta(font):
        """Quanto spazio verticale occupa davvero una riga di questo font.

        `getmetrics()` da' ascendente e discendente, cioe' lo spazio che il
        font si riserva sopra e sotto la linea di base. E' la misura giusta
        perche' non dipende dal testo: una riga senza discendenti non deve
        avere un'altezza diversa da una con la `g` di Agostino, altrimenti il
        layout cambia da un brano all'altro.
        """
        try:
            ascendente, discendente = font.getmetrics()
            return max(1, ascendente + discendente)
        except Exception:
            return max(1, getattr(font, "size", 8))

    def _layout(self):
        """Righe disponibili in base all'altezza del pannello.

        Le righe si impilano a partire dalle **metriche dei font**, non da
        frazioni fisse dell'altezza. Con le frazioni (0,33 e 0,56) su un
        pannello da 64 righe l'artista finiva a y=37 e l'album cominciava a
        y=37: si toccavano esattamente, e la `g` di "D'Agostino" entrava nel
        titolo dell'album. Non era un errore di un pixel da correggere a mano:
        era che nessuno aveva chiesto ai font quanto spazio volessero.
        """
        height = self.height
        if height < MINIMAL_HEIGHT:
            return {"title": 0, "artist": None, "album": None,
                    "transport": height - max(5, int(height * 0.30))}

        # Lo spazio che serve alla barra in fondo, e quello di ogni riga.
        barra = max(6, int(height * TIME_RATIO) + 2)
        alte = {"title": self._riga_alta(self._font_title),
                "artist": self._riga_alta(self._font_artist),
                "album": self._riga_alta(self._font_album)}
        righe = ["title", "artist"] + ([] if height < COMPACT_HEIGHT else ["album"])

        # Si parte con un pixel di respiro fra le righe e si stringe solo se
        # non ci sta: meglio righe attaccate che una riga tagliata via.
        for spazio in (2, 1, 0):
            totale = sum(alte[r] for r in righe) + spazio * len(righe)
            if totale + barra <= height:
                break

        posizioni, y = {}, 0
        for nome in righe:
            posizioni[nome] = y
            y += alte[nome] + spazio
        for nome in ("artist", "album"):
            posizioni.setdefault(nome, None)
        # La barra sta in fondo, non subito sotto l'ultima riga: se avanza
        # spazio lo si lascia in mezzo invece che sotto la barra.
        posizioni["transport"] = max(y, height - barra)
        return posizioni

    # ------------------------------------------------------------------ titolo

    def _draw_title(self, image, track, margin, rows, scrolling):
        title = track["title"] or track["artist"]
        area = self.width - 2 * margin
        width = text_width(title, self._font_title)
        band = max(1, int(self.height * TITLE_RATIO) + 3)

        if scrolling is None:
            scrolling = width > area
        if not scrolling:
            draw_text(image, (margin, rows["title"]), title,
                      self._font_title, self.color("title_color"))
            return

        # Il conto della corsa riparte quando cambia il brano, non a ogni
        # fotogramma: altrimenti un titolo lungo ricomincerebbe da capo di
        # continuo senza mai farsi leggere per intero.
        if self._scroll_key != title:
            self._scroll_key = title
            self._scroll_start = time.monotonic()

        gap = max(12, int(self.width * SCROLL_GAP))
        period = width + gap
        elapsed = max(0.0, time.monotonic() - self._scroll_start - SCROLL_HOLD)
        offset = int(elapsed * SCROLL_SPEED) % period

        strip = Image.new("RGB", (area, band), (0, 0, 0))
        color = self.color("title_color")
        draw_text(strip, (-offset, 0), title, self._font_title, color)
        # Seconda copia dietro la prima: la coda rientra da destra senza salti.
        if period - offset < area:
            draw_text(strip, (period - offset, 0), title,
                      self._font_title, color)
        image.paste(strip, (margin, rows["title"]))

    # ------------------------------------------------------------- trasporto

    def _draw_transport(self, image, draw, track, margin, rows):
        from nowplaying import format_time

        y = rows["transport"]
        glyph_h = max(5, int(self.height * TIME_RATIO) + 1)
        color = self.color("bar_color")
        title_color = self.color("title_color")
        artist_color = self.color("artist_color")
        album_color = self.color("album_color")

        if track["playing"]:
            self._glyph_play(draw, margin, y, glyph_h, title_color)
        else:
            self._glyph_pause(draw, margin, y, glyph_h, color)

        left = margin + max(7, glyph_h) + max(2, margin)
        if track["duration"] <= 0:
            # Alcune sorgenti non mandano la posizione: si dice lo stato a
            # parole invece di disegnare una barra che non significa nulla.
            # La lingua e' quella del pannello, non quella della web UI: chi
            # guarda il cabinato non e' per forza chi lo configura.
            panel_lang = (self.cfg.get("clock") or {}).get("language") or ""
            key = "nowplaying.panel.playing" if track["playing"] \
                else "nowplaying.panel.paused"
            draw_text(image, (left, y), self.t(key, panel_lang),
                      self._font_time, album_color)
            return

        elapsed = format_time(track["position"])
        total = format_time(track["duration"])
        total_w = text_width(total, self._font_time)

        draw_text(image, (left, y), elapsed, self._font_time, artist_color)
        right = self.width - margin - total_w
        draw_text(image, (right, y), total, self._font_time, album_color)

        # Lo spazio riservato al tempo trascorso e' quello della durata, non
        # quello del testo corrente: cosi' gli estremi della barra restano
        # fermi per tutto il brano invece di spostarsi da 9:59 a 10:00.
        bar0 = left + max(total_w, text_width(elapsed, self._font_time)) \
            + max(3, margin)
        bar1 = right - max(3, margin)
        if bar1 - bar0 < 8:
            return
        bar_y = y + glyph_h // 2
        draw.line([(bar0, bar_y), (bar1, bar_y)], fill=album_color)
        done = track["position"] / track["duration"]
        end = bar0 + int((bar1 - bar0) * max(0.0, min(1.0, done)))
        if end > bar0:
            draw.line([(bar0, bar_y), (end, bar_y)], fill=color)

    @staticmethod
    def _glyph_play(draw, x, y, size, color):
        half = size // 2
        for step in range(half + 1):
            draw.line([(x + step, y + step), (x + step, y + size - step)],
                      fill=color)

    @staticmethod
    def _glyph_pause(draw, x, y, size, color):
        bar = max(1, size // 5)
        draw.rectangle([x, y, x + bar - 1, y + size], fill=color)
        draw.rectangle([x + bar * 2 + 1, y, x + bar * 3, y + size], fill=color)
