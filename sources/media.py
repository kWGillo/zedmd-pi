"""Media Player.

Ogni 20-30 secondi (intervallo casuale) nasconde l'orologio e mostra un
contenuto scelto a caso da una cartella: una foto per qualche secondo
oppure un video/animazione. Poi restituisce il display.

La cartella e' raggiungibile via SMB e via upload dalla web UI. I file
vengono adattati al pannello con ffmpeg, quindi si possono caricare i
principali formati senza preparazione manuale. Sono supportate anche le
raccolte scaricate da Pixelcade, tipicamente GIF animate a bassa
risoluzione: vengono usate anche quando Batocera non e' in funzione.
"""

import os
import random
import shutil
import subprocess
import threading
import time

from PIL import Image

from .base import Source

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".ppm", ".tif", ".tiff"}
VIDEO_EXT = {".gif", ".mp4", ".m4v", ".avi", ".mkv", ".mov", ".webm", ".mpg",
             ".mpeg", ".wmv", ".flv"}
ALL_EXT = IMAGE_EXT | VIDEO_EXT

# Cartelle di servizio create da Samba o dai sistemi operativi.
SKIP_DIRS = {".AppleDouble", ".Trashes", "__MACOSX", ".git", "@eaDir"}


def is_supported(name):
    return os.path.splitext(name)[1].lower() in ALL_EXT


def scan_media(root):
    """Elenca ricorsivamente i file utilizzabili sotto `root`."""
    found = []
    if not os.path.isdir(root):
        return found
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for name in files:
            if name.startswith("."):
                continue
            if is_supported(name):
                found.append(os.path.join(base, name))
    found.sort()
    return found


def have_ffmpeg():
    return shutil.which("ffmpeg") is not None


class MediaPlayerSource(Source):
    name = "mediaplayer"
    label = "Media Player"
    priority = 50

    def __init__(self, cfg, width, height):
        super().__init__(cfg, width, height)
        self._running = False
        self._thread = None
        self._wake = threading.Event()

        self._lock = threading.Lock()
        self._image = None
        self._dirty = False

        self._showing = False
        self._current = None
        self._shown = 0
        self._error = None

    # ------------------------------------------------------------------ ciclo di vita

    def start(self):
        if self._running:
            return
        self._running = True
        self._wake.clear()
        self._thread = threading.Thread(target=self._loop, name="mediaplayer", daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._showing = False
        self._wake.set()

    def trigger_now(self):
        """Salta l'attesa e mostra subito il contenuto successivo."""
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

    def status(self):
        if not self._running:
            return "disabilitato"
        if self._error:
            return self._error
        count = len(scan_media(self.cfg["mediaplayer"]["media_dir"]))
        if self._showing and self._current:
            return "in riproduzione: %s (%d file in libreria)" % (
                os.path.basename(self._current), count)
        if count == 0:
            return "nessun file nella libreria"
        return "in attesa, %d file in libreria, %d mostrati" % (count, self._shown)

    # ------------------------------------------------------------------ ciclo principale

    def _loop(self):
        while self._running:
            cfg = self.cfg["mediaplayer"]
            low = max(3, int(cfg["min_interval"]))
            high = max(low, int(cfg["max_interval"]))
            delay = random.uniform(low, high)

            # Attesa interrompibile: stop() o trigger_now() la accorciano.
            self._wake.wait(delay)
            self._wake.clear()
            if not self._running:
                return

            files = scan_media(cfg["media_dir"])
            if not files:
                self._error = None
                continue

            path = random.choice(files)
            self._current = path
            try:
                if os.path.splitext(path)[1].lower() in IMAGE_EXT:
                    self._show_image(path, cfg)
                else:
                    self._show_video(path, cfg)
                self._error = None
                self._shown += 1
            except Exception as exc:  # un file rovinato non deve fermare il servizio
                self._error = "errore su %s: %s" % (os.path.basename(path), exc)
                print("[media] %s" % self._error)
            finally:
                self._showing = False
                self._current = None

    # ------------------------------------------------------------------ riproduzione

    def _publish(self, image):
        with self._lock:
            self._image = image
            self._dirty = True

    def _show_image(self, path, cfg):
        image = self._load_image(path, cfg)
        self._publish(image)
        self._showing = True
        deadline = time.time() + max(1, int(cfg["image_duration"]))
        while self._running and time.time() < deadline:
            time.sleep(0.1)

    def _load_image(self, path, cfg):
        """Carica con Pillow; se il formato non e' gestito ripiega su ffmpeg."""
        try:
            with Image.open(path) as src:
                return self._fit(src.convert("RGB"), cfg)
        except Exception:
            if not have_ffmpeg():
                raise
            raw = subprocess.run(
                ["ffmpeg", "-v", "error", "-i", path, "-frames:v", "1",
                 "-vf", self._filter(cfg), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                capture_output=True, timeout=30).stdout
            expected = self.width * self.height * 3
            if len(raw) < expected:
                raise RuntimeError("ffmpeg non ha prodotto un fotogramma valido")
            return Image.frombytes("RGB", (self.width, self.height), raw[:expected])

    def _fit(self, image, cfg):
        """Adatta l'immagine al pannello secondo la modalita' configurata."""
        resample = Image.NEAREST if cfg["pixel_art"] else Image.LANCZOS
        target = self.width / self.height
        ratio = image.width / max(1, image.height)

        if cfg["scale_mode"] == "fill":
            if ratio > target:
                new_w = int(image.height * target)
                left = (image.width - new_w) // 2
                image = image.crop((left, 0, left + new_w, image.height))
            else:
                new_h = int(image.width / target)
                top = (image.height - new_h) // 2
                image = image.crop((0, top, image.width, top + new_h))
            return image.resize((self.width, self.height), resample)

        # fit: mantiene le proporzioni e centra su fondo nero
        scale = min(self.width / image.width, self.height / image.height)
        size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
        scaled = image.resize(size, resample)
        canvas = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        canvas.paste(scaled, ((self.width - size[0]) // 2, (self.height - size[1]) // 2))
        return canvas

    def _filter(self, cfg):
        flags = "neighbor" if cfg["pixel_art"] else "lanczos"
        if cfg["scale_mode"] == "fill":
            return ("scale=%d:%d:force_original_aspect_ratio=increase:flags=%s,"
                    "crop=%d:%d" % (self.width, self.height, flags, self.width, self.height))
        return ("scale=%d:%d:force_original_aspect_ratio=decrease:flags=%s,"
                "pad=%d:%d:(ow-iw)/2:(oh-ih)/2:black"
                % (self.width, self.height, flags, self.width, self.height))

    def _show_video(self, path, cfg):
        if not have_ffmpeg():
            raise RuntimeError("ffmpeg non installato")

        fps = max(5, int(cfg["video_fps"]))
        duration = max(1, int(cfg["video_duration"]))
        frame_bytes = self.width * self.height * 3

        # -stream_loop -1 fa ripetere le animazioni brevi (tipiche di Pixelcade)
        # fino a coprire l'intera durata prevista.
        proc = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-stream_loop", "-1", "-i", path, "-an",
             "-vf", self._filter(cfg), "-r", str(fps),
             "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

        self._showing = True
        period = 1.0 / fps
        deadline = time.time() + duration
        try:
            while self._running and time.time() < deadline:
                started = time.time()
                raw = proc.stdout.read(frame_bytes)
                if not raw or len(raw) < frame_bytes:
                    break
                self._publish(Image.frombytes("RGB", (self.width, self.height), raw))
                elapsed = time.time() - started
                if elapsed < period:
                    time.sleep(period - elapsed)
        finally:
            try:
                proc.kill()
                proc.stdout.close()
            except Exception:
                pass
            proc.wait(timeout=5)
