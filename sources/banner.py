"""Rolling banner.

Fino a dieci testi scorrevoli, ognuno con colore, dimensione, velocita' e
lampeggio propri. Compaiono a intervalli casuali come i contenuti del Media
Player: il testo entra da destra, attraversa il pannello ed esce a sinistra,
poi la sorgente restituisce il display.

Il banner sta un gradino sopra il Media Player nella scala delle priorita'.
La ragione e' pratica: un testo scorre una volta sola e dura pochi secondi,
mentre una foto puo' restare a schermo a lungo. Se il banner stesse sotto,
con entrambi i servizi attivi non comparirebbe quasi mai.
"""

import random
import threading
import time

from PIL import Image, ImageDraw

from .base import Source
from .clock import _load_font, parse_color

# Numero di caselle nella pagina di configurazione. Fisso: dieci sono
# abbastanza per un cabinato e tengono la pagina leggibile.
SLOTS = 10

# Dimensioni disponibili, espresse come frazione dell'altezza del pannello.
SIZES = [("small", 0.34), ("medium", 0.50), ("large", 0.72)]
SIZE_KEYS = [key for key, _ in SIZES]

# Periodo del lampeggio, in secondi: acceso per meta', spento per l'altra.
BLINK_PERIOD = 0.8


def default_banner():
    return {
        "text": "",
        "color": "#ff8c1a",
        "size": "medium",
        "blink": False,
        "speed": 60,          # pixel al secondo
        "enabled": False,
    }


def default_list():
    return [default_banner() for _ in range(SLOTS)]


def normalize(entry):
    """Riporta una voce a una forma valida, qualunque cosa arrivi."""
    base = default_banner()
    if isinstance(entry, dict):
        base["text"] = str(entry.get("text", ""))[:120]
        base["color"] = str(entry.get("color", base["color"]))
        size = str(entry.get("size", "medium"))
        base["size"] = size if size in SIZE_KEYS else "medium"
        base["blink"] = bool(entry.get("blink", False))
        try:
            base["speed"] = max(10, min(300, int(entry.get("speed", 60))))
        except (TypeError, ValueError):
            base["speed"] = 60
        base["enabled"] = bool(entry.get("enabled", False))
    return base


def normalize_list(items):
    """Sempre SLOTS voci: le mancanti vuote, le eccedenti scartate."""
    source = items if isinstance(items, list) else []
    out = [normalize(source[i]) if i < len(source) else default_banner()
           for i in range(SLOTS)]
    return out


def usable(items):
    """Le voci attive e con del testo dentro: le uniche mostrabili."""
    return [b for b in normalize_list(items)
            if b["enabled"] and b["text"].strip()]


class BannerSource(Source):
    name = "banner"
    label = "Rolling Banner"
    priority = 55   # sopra il Media Player (50), sotto Air Radar (60)

    def __init__(self, cfg, width, height):
        super().__init__(cfg, width, height)
        self._running = False
        self._thread = None
        self._wake = threading.Event()

        self._lock = threading.Lock()
        self._image = None
        self._dirty = False

        self._showing = False
        self._current = ""
        self._shown = 0
        self._next_index = 0
        self._fonts = {}

    # ------------------------------------------------------------------ ciclo di vita

    def start(self):
        if self._running:
            return
        self._running = True
        self._wake.clear()
        self._thread = threading.Thread(target=self._loop, name="banner", daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._showing = False
        self._wake.set()

    def trigger_now(self):
        """Salta l'attesa e manda subito in scorrimento il testo successivo."""
        self._wake.set()

    # ------------------------------------------------------------------ arbitro

    def active(self):
        return self._running and self._showing

    def frame(self):
        with self._lock:
            if not self._dirty or self._image is None:
                return None
            self._dirty = False
            return self._image

    def status(self, lang=None):
        if not self._running:
            return self.t("status.disabled", lang)
        count = len(usable(self.cfg["banner"]["items"]))
        if self._showing and self._current:
            return self.t("status.banner.showing", lang, text=self._current[:40])
        if count == 0:
            return self.t("status.banner.empty", lang)
        return self.t("status.banner.waiting", lang, count=count, shown=self._shown)

    # ------------------------------------------------------------------ ciclo principale

    def _loop(self):
        while self._running:
            cfg = self.cfg["banner"]
            low = max(3, int(cfg["min_interval"]))
            high = max(low, int(cfg["max_interval"]))

            self._wake.wait(random.uniform(low, high))
            self._wake.clear()
            if not self._running:
                return

            items = usable(cfg["items"])
            if not items:
                continue

            entry = self._pick(items, cfg)
            try:
                self._scroll(entry, cfg)
            except Exception as exc:   # un testo strano non deve fermare il servizio
                print("[banner] errore su %r: %s" % (entry["text"][:30], exc))
            finally:
                self._showing = False
                self._current = ""

    def _pick(self, items, cfg):
        """In ordine oppure a caso, secondo la configurazione."""
        if cfg.get("shuffle"):
            return random.choice(items)
        entry = items[self._next_index % len(items)]
        self._next_index = (self._next_index + 1) % len(items)
        return entry

    # ------------------------------------------------------------------ resa

    def _font(self, size_key):
        """I font si caricano una volta sola: crearli a ogni banner costa."""
        if size_key not in self._fonts:
            fraction = dict(SIZES).get(size_key, 0.50)
            self._fonts[size_key] = _load_font(max(8, int(self.height * fraction)))
        return self._fonts[size_key]

    def render_text(self, entry):
        """Immagine del solo testo, larga quanto serve, su fondo nero."""
        text = entry["text"].strip()
        font = self._font(entry["size"])
        color = parse_color(entry["color"])

        # Misura prima di disegnare: la larghezza determina la corsa.
        probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        box = probe.textbbox((0, 0), text, font=font)
        text_w = max(1, box[2] - box[0])
        text_h = max(1, box[3] - box[1])

        image = Image.new("RGB", (text_w, self.height), (0, 0, 0))
        draw = ImageDraw.Draw(image)
        # Centrato verticalmente tenendo conto dello scarto del riquadro.
        draw.text((-box[0], (self.height - text_h) // 2 - box[1]), text,
                  font=font, fill=color)
        return image

    def _publish(self, image):
        with self._lock:
            self._image = image
            self._dirty = True

    def _scroll(self, entry, cfg):
        """Fa attraversare il testo da destra a sinistra, una volta sola."""
        strip = self.render_text(entry)
        speed = max(10, int(entry["speed"]))
        fps = max(10, min(60, int(cfg.get("fps", 30))))
        step = speed / float(fps)

        self._current = entry["text"].strip()
        self._showing = True
        started = time.time()

        # Da fuori a destra fino a completamente uscito a sinistra.
        position = float(self.width)
        end = -float(strip.width)

        while self._running and position > end:
            canvas = Image.new("RGB", (self.width, self.height), (0, 0, 0))
            visible = True
            if entry["blink"]:
                phase = (time.time() - started) % BLINK_PERIOD
                visible = phase < BLINK_PERIOD / 2
            if visible:
                canvas.paste(strip, (int(round(position)), 0))
            self._publish(canvas)

            position -= step
            time.sleep(1.0 / fps)

        self._shown += 1
