"""Anteprima di un file della libreria sul pannello.

Serve a una cosa sola: prima di cancellare un file bisogna poter vedere che
cos'e', e il nome raramente basta. Guardarlo sul computer non risponde alla
domanda vera — come viene su *quel* pannello, con quella scala e quei colori —
quindi l'anteprima si mostra dove andra' a finire.

E' una sorgente a se' e non un pezzo del Media Player perche' cambia solo la
priorita': **90**, sotto ZeDMD (100) e sopra tutto il resto. Chi ha appena
premuto "Vedi" sta guardando il pannello adesso, e un aereo di passaggio o un
compleanno non hanno motivo di scavalcarlo. ZeDMD si', perche' una partita in
corso viene prima di qualunque cosa.

Il disegno lo fa il Media Player: scala, ritaglio, riproduzione dei video e
delle GIF sono gia' li', ben tarati, e riscriverli qui significherebbe avere
due anteprime che col tempo divergono.
"""

import threading
import time

from .base import Source
from .media import IMAGE_EXT

# Quanto resta a schermo, se non viene chiesto altrimenti. Dieci secondi
# bastano a giudicare un'immagine e a far ripartire una GIF corta piu' volte.
DEFAULT_SECONDS = 10
MAX_SECONDS = 120


class PreviewSource(Source):
    name = "preview"
    label = "Anteprima"
    priority = 90   # sotto ZeDMD (100), sopra tutto il resto

    def __init__(self, cfg, width, height, media):
        super().__init__(cfg, width, height)
        # Il Media Player e' il motore: qui si riusa il suo caricamento, la
        # sua scala e la sua riproduzione video.
        self.media = media

        self._lock = threading.Lock()
        self._image = None
        self._dirty = False

        self._running = True
        self._showing = False
        self._thread = None
        self._stop = threading.Event()
        self._current = ""
        self._shown = 0
        self._error = ""

    # ------------------------------------------------------------ ciclo di vita

    def start(self):
        # Non ha un ciclo suo: vive solo quando qualcuno chiede un'anteprima.
        self._running = True

    def stop(self):
        self._running = False
        self._stop.set()
        self._showing = False

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
        if self._error:
            return self.t("status.preview.error", lang, error=self._error)
        if self._showing:
            return self.t("status.preview.showing", lang, name=self._current)
        return self.t("status.preview.idle", lang, count=self._shown)

    # ------------------------------------------------------------------ azione

    def show(self, path, name, seconds=DEFAULT_SECONDS):
        """Mostra subito il file indicato. Restituisce un errore o ''.

        Una richiesta nuova interrompe quella in corso: se stai passando in
        rassegna la libreria vuoi vedere l'ultimo file su cui hai premuto, non
        aspettare che finisca il precedente.
        """
        seconds = max(1, min(MAX_SECONDS, int(seconds or DEFAULT_SECONDS)))
        self._interrompi()

        self._error = ""
        self._current = name
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._mostra, args=(path, seconds), name="anteprima",
            daemon=True)
        self._thread.start()
        return ""

    def cancel(self):
        self._interrompi()

    def _interrompi(self):
        if self._thread and self._thread.is_alive():
            self._stop.set()
            self._thread.join(timeout=3)
        self._showing = False

    # ------------------------------------------------------------------ disegno

    def _pubblica(self, image):
        with self._lock:
            self._image = image
            self._dirty = True

    def _mostra(self, path, seconds):
        cfg = self.cfg["mediaplayer"]
        import os
        try:
            # Le GIF stanno fra i video: sono animate, e mostrarne il primo
            # fotogramma non direbbe quasi niente.
            if os.path.splitext(path)[1].lower() in IMAGE_EXT:
                self._immagine(path, cfg, seconds)
            else:
                self._video(path, cfg, seconds)
        except Exception as exc:
            self._error = str(exc)
            print("[anteprima] %s: %s" % (path, exc))
        finally:
            self._showing = False
            self._shown += 1

    def _immagine(self, path, cfg, seconds):
        immagine = self.media._load_image(path, cfg)
        self._pubblica(immagine)
        self._showing = True
        scadenza = time.time() + seconds
        while self._running and not self._stop.is_set() and time.time() < scadenza:
            time.sleep(0.1)

    def _video(self, path, cfg, seconds):
        """Riproduce come fa il Media Player, ma per il tempo chiesto qui.

        La configurazione viene copiata e ritoccata invece di essere
        modificata: il Media Player continua a usare la sua durata, e questa
        anteprima non gliela cambia sotto i piedi.
        """
        prova = dict(cfg)
        prova["video_duration"] = seconds

        # Il Media Player pubblica sul proprio buffer: qui lo si dirotta sul
        # nostro per la durata della riproduzione, poi lo si rimette a posto.
        originale_publish = self.media._publish
        originale_showing = self.media._showing
        originale_running = self.media._running
        self.media._publish = self._pubblica
        self.media._running = True
        self._showing = True
        try:
            self.media._show_video(path, prova)
        finally:
            self.media._publish = originale_publish
            self.media._showing = originale_showing
            self.media._running = originale_running
