# -*- coding: utf-8 -*-
"""L'avviso periodico delle scadenze sul pannello.

Il semaforo nell'orologio dice *che c'e' qualcosa*; questo dice **che cosa**.
Compare a intervalli, come il promemoria dei compleanni, e resta pochi secondi:
tre righe, e la piu' importante e' la data.

  - in alto il titolo, che scorre se non ci sta;
  - sotto la data, **del colore del semaforo**: e' l'unico modo per far
    arrivare l'urgenza a chi legge di sfuggita passando davanti al cabinato;
  - sotto la descrizione, tagliata a quello che il pannello sa reggere.

Il titolo scorre e il resto no. Far scorrere tre righe insieme darebbe un
pannello che si muove tutto e non si legge niente: scorre la riga che puo'
essere lunga, le altre stanno ferme.
"""

import threading
import time

from PIL import Image, ImageDraw

import scadenze as modello

from .base import Source
from .nowplaying import draw_text, text_width

# Font come frazione dell'altezza, con la stessa logica del player: il titolo
# grande, la data media, la descrizione piccola.
TITOLO_RATIO = 0.28
DATA_RATIO = 0.25
DESCR_RATIO = 0.17


def _carica(size):
    from .clock import _load_font
    return _load_font(size)


class ScadenzeSource(Source):
    name = "scadenze"
    label = "Scadenze"
    # Sopra i compleanni (56) e sotto Air Radar (60): una scadenza scaduta e'
    # piu' urgente di un augurio, e meno di un aereo che passa in questo
    # istante e fra dieci secondi non c'e' piu'.
    priority = 57

    def __init__(self, cfg, width, height):
        super().__init__(cfg, width, height)
        self._running = False
        self._thread = None
        self._wake = threading.Event()

        self._lock = threading.Lock()
        self._image = None
        self._dirty = False

        self._showing = False
        self._voce = None
        self._indice = 0
        self._mostrate = 0
        self._offset = 0.0

        self._font_titolo = _carica(max(8, int(height * TITOLO_RATIO)))
        self._font_data = _carica(max(7, int(height * DATA_RATIO)))
        self._font_descr = _carica(max(6, int(height * DESCR_RATIO)))

    # ------------------------------------------------------------ ciclo di vita

    def start(self):
        if self._running:
            return
        self._running = True
        self._wake.clear()
        self._thread = threading.Thread(target=self._loop, name="scadenze",
                                        daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._showing = False
        self._wake.set()

    def trigger_now(self):
        """Mostra subito il prossimo avviso, senza aspettare l'intervallo."""
        self._wake.set()

    def conf(self):
        return self.cfg.get("scadenze") or {}

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
        try:
            aperte = modello.da_mostrare(self.cfg)
        except Exception as exc:
            return self.t("status.scadenze.errore", lang, error=str(exc))
        if self._showing and self._voce:
            return self.t("status.scadenze.mostra", lang,
                          titolo=self._voce["titolo"])
        if not aperte:
            return self.t("status.scadenze.nessuna", lang)
        return self.t("status.scadenze.attesa", lang, count=len(aperte),
                      shown=self._mostrate)

    # ------------------------------------------------------------------ ciclo

    def _intervallo(self):
        try:
            return max(1, int(self.conf().get("interval_minutes", 20))) * 60
        except (TypeError, ValueError):
            return 20 * 60

    def _durata(self):
        try:
            return max(2, min(60, int(self.conf().get("seconds", 10))))
        except (TypeError, ValueError):
            return 10

    def _loop(self):
        while self._running:
            if self._wake.wait(self._intervallo()):
                self._wake.clear()
            if not self._running:
                break
            try:
                self._mostra_prossima()
            except Exception as exc:
                print("[scadenze] avviso non mostrato: %s" % exc)
                self._showing = False

    def _mostra_prossima(self):
        aperte = modello.da_mostrare(self.cfg)
        if not aperte:
            self._showing = False
            return
        # A giro: se ce n'e' piu' di una, si alternano invece di mostrare
        # sempre la piu' urgente e non far sapere delle altre.
        self._indice %= len(aperte)
        self._voce = aperte[self._indice]
        self._indice += 1
        self._mostrate += 1

        self._offset = 0.0
        self._showing = True
        fine = time.time() + self._durata()
        periodo = 1.0 / 30
        while self._running and time.time() < fine:
            inizio = time.time()
            self._disegna()
            resto = periodo - (time.time() - inizio)
            if resto > 0:
                time.sleep(resto)
        self._showing = False

    # --------------------------------------------------------------- disegno

    def _velocita(self):
        try:
            return max(5, min(120, int(self.conf().get("speed", 40))))
        except (TypeError, ValueError):
            return 40

    def _disegna(self):
        voce = self._voce
        if voce is None:
            return
        immagine = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        colore = modello.COLORI.get(voce["stato"], (255, 255, 255))
        margine = max(1, self.width // 85)

        # --- titolo, che scorre solo se non ci sta
        larghezza = text_width(voce["titolo"], self._font_titolo)
        area = self.width - 2 * margine
        if larghezza <= area:
            draw_text(immagine, (margine, 0), voce["titolo"],
                      self._font_titolo, (255, 255, 255))
        else:
            passo = self._velocita() / 30.0
            self._offset += passo
            giro = larghezza + area // 2
            if self._offset > giro:
                self._offset = 0.0
            striscia = Image.new("RGB", (larghezza + area, self.height // 3),
                                 (0, 0, 0))
            draw_text(striscia, (0, 0), voce["titolo"], self._font_titolo,
                      (255, 255, 255))
            immagine.paste(striscia.crop((int(self._offset), 0,
                                          int(self._offset) + area,
                                          self.height // 3)), (margine, 0))

        # --- data, del colore del semaforo: e' l'informazione che conta
        testo = modello.scrivi_data(voce["data"])
        if voce["giorni"] < 0:
            testo += " !"
        draw_text(immagine, (margine, int(self.height * 0.33)), testo,
                  self._font_data, colore)

        # --- giorni che mancano, a destra della data
        conteggio = self._conteggio(voce)
        if conteggio:
            larghezza_c = text_width(conteggio, self._font_descr)
            draw_text(immagine,
                      (self.width - margine - larghezza_c,
                       int(self.height * 0.36)),
                      conteggio, self._font_descr, colore)

        # --- descrizione
        if voce["descrizione"]:
            draw_text(immagine, (margine, int(self.height * 0.62)),
                      voce["descrizione"][:modello.MAX_DESCRIZIONE],
                      self._font_descr, (150, 150, 160))

        with self._lock:
            self._image = immagine
            self._dirty = True

    def _conteggio(self, voce):
        lingua = (self.cfg.get("clock") or {}).get("language") or ""
        giorni = voce["giorni"]
        if giorni < 0:
            return self.t("scadenze.panel.scaduta", lingua, giorni=-giorni)
        if giorni == 0:
            return self.t("scadenze.panel.oggi", lingua)
        return self.t("scadenze.panel.mancano", lingua, giorni=giorni)
