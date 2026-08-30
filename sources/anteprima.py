"""Anteprima di un file della libreria sul pannello.

Serve a una cosa sola: prima di cancellare un file bisogna poter vedere che
cos'e', e il nome raramente basta. Guardarlo sul computer non risponde alla
domanda vera — come viene su *quel* pannello, con quella scala e quei colori —
quindi l'anteprima si mostra dove andra' a finire.

Vive dentro la **gestione media**: finche' quella pagina e' aperta il pannello
e' suo e nessun'altra sorgente lo tocca. E' una scelta diversa da quella della
2.0.2, dove l'anteprima si limitava ad avere una priorita' alta e si
contendeva il pannello con le altre sorgenti a colpi di priorita'. Non
funzionava: fra un file e l'altro c'era sempre una finestra in cui qualcun
altro poteva infilarsi, e i tempi di ciascuno erano diversi.

Il disegno delle immagini lo fa il Media Player — scala, ritaglio e ripiego su
ffmpeg sono gia' li' e ben tarati. La riproduzione dei video invece e' sua:
prima riusava `media._show_video` dirottandogli il buffer di uscita, e quel
ciclo guarda solo i flag del Media Player, quindi non c'era modo di
interromperlo. Chi premeva "Vedi" su un secondo file continuava a vedere il
primo finche' non finiva, e due dirottamenti annidati lasciavano il buffer del
Media Player puntato qui per sempre.
"""

import os
import subprocess
import threading
import time

from PIL import Image, ImageDraw

from .base import Source
from .clock import _load_font
from .media import IMAGE_EXT, have_ffmpeg

# Quanto resta a schermo, se non viene chiesto altrimenti. Dieci secondi
# bastano a giudicare un'immagine e a far ripartire una GIF corta piu' volte.
DEFAULT_SECONDS = 10
MAX_SECONDS = 120

# In gestione media non c'e' fretta: il file resta finche' non se ne chiede un
# altro, e una GIF continua a girare invece di fermarsi dopo dieci secondi.
HOLD_SECONDS = MAX_SECONDS


class PreviewSource(Source):
    name = "preview"
    label = "Anteprima"
    priority = 90   # conta solo fuori dalla gestione media

    def __init__(self, cfg, width, height, media):
        super().__init__(cfg, width, height)
        # Il Media Player e' il motore per le immagini: stessa scala, stesso
        # ritaglio, stesso ripiego su ffmpeg.
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
        self._font = None

    # ------------------------------------------------------------ ciclo di vita

    def start(self):
        # Non ha un ciclo suo: vive solo quando qualcuno chiede un'anteprima.
        self._running = True

    def stop(self):
        self._running = False
        self._interrompi()

    # ------------------------------------------------------------------ arbitro

    def active(self):
        return self._running and self._showing

    def frame(self):
        with self._lock:
            if not self._dirty or self._image is None:
                return None
            self._dirty = False
            return self._image

    def invalidate(self):
        """Ridisegna alla prossima occasione: l'arbitro la chiama al subentro."""
        with self._lock:
            if self._image is not None:
                self._dirty = True

    def status(self, lang=None):
        if self._error:
            return self.t("status.preview.error", lang, error=self._error)
        if self._showing:
            return self.t("status.preview.showing", lang, name=self._current)
        return self.t("status.preview.idle", lang, count=self._shown)

    @property
    def current(self):
        return self._current

    # ------------------------------------------------------------------ azione

    def show(self, path, name, seconds=None):
        """Mostra subito il file indicato. Restituisce un errore o ''.

        Una richiesta nuova interrompe quella in corso: se stai passando in
        rassegna la libreria vuoi vedere l'ultimo file su cui hai premuto, non
        aspettare che finisca il precedente.
        """
        seconds = max(1, min(MAX_SECONDS, int(seconds or DEFAULT_SECONDS)))
        self._interrompi()

        # Il pannello si svuota subito. Caricare un file puo' prendere qualche
        # decimo di secondo, e in quel buco restava a schermo il file
        # precedente: chi ha appena premuto lo legge come "non ha funzionato".
        self._pubblica(Image.new("RGB", (self.width, self.height), (0, 0, 0)))

        self._error = ""
        self._current = name
        self._running = True
        self._stop.clear()
        self._showing = True
        self._thread = threading.Thread(
            target=self._mostra, args=(path, seconds), name="anteprima",
            daemon=True)
        self._thread.start()
        return ""

    def cancel(self):
        self._interrompi()
        self._current = ""

    def _interrompi(self):
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            # Il ciclo dei video controlla `_stop` a ogni fotogramma: un
            # secondo e' molto piu' del necessario.
            thread.join(timeout=2)
        self._thread = None
        self._showing = False

    # ------------------------------------------------------------------ cartello

    def hold(self):
        """Cartello di attesa all'ingresso nella gestione media.

        Entrando in gestione i servizi si fermano tutti: senza un segno il
        pannello sembrerebbe semplicemente spento, e a quel punto uno va a
        cercare il guasto dove non c'e'.
        """
        image = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        draw = ImageDraw.Draw(image)
        if self._font is None:
            self._font = _load_font(max(8, int(self.height * 0.22)))
        testo = self.t("panel.manager")
        box = draw.textbbox((0, 0), testo, font=self._font)
        draw.text(((self.width - (box[2] - box[0])) // 2,
                   (self.height - (box[3] - box[1])) // 2 - box[1]),
                  testo, font=self._font, fill=(0, 140, 200))
        self._current = ""
        self._pubblica(image)

    # ------------------------------------------------------------------ disegno

    def _pubblica(self, image):
        with self._lock:
            self._image = image
            self._dirty = True

    def _mostra(self, path, seconds):
        cfg = self.cfg["mediaplayer"]
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
        scadenza = time.time() + seconds
        while self._running and not self._stop.is_set() and time.time() < scadenza:
            time.sleep(0.05)

    def _video(self, path, cfg, seconds):
        """Riproduce con un ffmpeg tutto suo, interrompibile a ogni fotogramma.

        Non si riusa `media._show_video`: quel ciclo guarda i flag del Media
        Player e pubblica sul suo buffer, quindi da qui non lo si puo' ne'
        fermare ne' leggere senza dirottarglieli sotto — che e' esattamente il
        pasticcio della 2.0.2.
        """
        if not have_ffmpeg():
            raise RuntimeError("ffmpeg non installato")

        fps = max(5, int(cfg["video_fps"]))
        frame_bytes = self.width * self.height * 3
        periodo = 1.0 / fps
        scadenza = time.time() + seconds

        # -stream_loop -1 fa ripetere le animazioni brevi finche' c'e' tempo:
        # una GIF di due secondi va guardata piu' di una volta.
        proc = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-stream_loop", "-1", "-i", path, "-an",
             "-vf", self.media._filter(cfg), "-r", str(fps),
             "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            while (self._running and not self._stop.is_set()
                   and time.time() < scadenza):
                inizio = time.time()
                raw = proc.stdout.read(frame_bytes)
                if not raw or len(raw) < frame_bytes:
                    break
                self._pubblica(
                    Image.frombytes("RGB", (self.width, self.height), raw))
                trascorso = time.time() - inizio
                if trascorso < periodo:
                    time.sleep(periodo - trascorso)
        finally:
            try:
                proc.kill()
                proc.stdout.close()
            except Exception:
                pass
            try:
                proc.wait(timeout=5)
            except Exception:
                pass
