# -*- coding: utf-8 -*-
"""L'avviso periodico degli appuntamenti di Google Calendar.

Ha la stessa forma dell'avviso delle scadenze — compare ogni tanto, resta
pochi secondi, poi il pannello torna al suo lavoro — ma **niente semaforo**.
Il semaforo dice "manca poco": ha senso per una bolletta, che si può pagare
prima, e non per un appuntamento, che succede quando succede. Un appuntamento
o è nei prossimi tre giorni o non c'è: la lampadina non aggiungerebbe niente
che la data non dica già.

Il disegno è di tre pezzi, e l'ordine di lettura è voluto:

  - in alto a destra **quando**, nel colore che l'orologio usa per la data,
    perché è lì che l'occhio va a cercare le date su questo pannello;
  - al centro **che cosa**, grande, che scorre se non ci sta;
  - sotto **dove** — o, se il posto non c'è, la descrizione — piccolo e in
    grigio, che è un dettaglio e non deve rubare la scena al titolo.

Scorre solo il titolo. Far scorrere tre righe insieme darebbe un pannello che
si muove tutto e non si legge niente.
"""

import threading
import time

from PIL import Image

import gcalendar

from .base import Source
from .nowplaying import draw_text, text_width

# Font come frazione dell'altezza. La data è più piccola del titolo: qui
# l'informazione principale è *che cosa*, e il quando fa da etichetta.
QUANDO_RATIO = 0.22
TITOLO_RATIO = 0.30
SOTTO_RATIO = 0.20

# Righe, come frazione dell'altezza del pannello.
Y_TITOLO = 0.375
Y_SOTTO = 0.70

GRIGIO = (150, 150, 160)


def _carica(size):
    from .clock import _load_font
    return _load_font(size)


class CalendarioSource(Source):
    name = "calendario"
    label = "Calendario"
    # Sopra le scadenze (57): una scadenza ha un giorno, un appuntamento ha
    # anche un'ora, e chi passa davanti al pannello dieci minuti prima di
    # uscire di casa ha più bisogno del secondo. Sotto Air Radar (60), che
    # segnala un aereo che fra dieci secondi non c'è più.
    #
    # **59 e non 58**, che sarebbe stato il numero naturale, perché 58 è già
    # di Now Playing: a parità l'arbitro tiene chi ha registrato per primo —
    # il player — e l'avviso non sarebbe mai comparso mentre suona musica.
    # Un pareggio qui non è un dettaglio estetico: è una sorgente che tace.
    priority = 59

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
        self._mostrati = 0
        self._offset = 0.0

        self._font_quando = _carica(max(6, int(height * QUANDO_RATIO)))
        self._font_titolo = _carica(max(8, int(height * TITOLO_RATIO)))
        self._font_sotto = _carica(max(6, int(height * SOTTO_RATIO)))

    # --------------------------------------------------------- ciclo di vita

    def start(self):
        if self._running:
            return
        self._running = True
        self._wake.clear()
        self._thread = threading.Thread(target=self._loop, name="calendario",
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
        return self.cfg.get("google") or {}

    # ------------------------------------------------------------- arbitro

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
        if not gcalendar.connected():
            return self.t("status.calendario.scollegato", lang)
        errore = gcalendar.errore()
        if errore:
            return self.t("status.calendario.errore", lang, error=errore)
        if self._showing and self._voce:
            return self.t("status.calendario.mostra", lang,
                          titolo=self._voce["titolo"])
        # Solo la cache: una riga di stato non deve poter aprire una
        # connessione a Google e far aspettare la pagina Servizi.
        prossimi = gcalendar.in_cache()
        if not prossimi:
            return self.t("status.calendario.nessuno", lang,
                          giorni=gcalendar.giorni_finestra(self.cfg))
        return self.t("status.calendario.attesa", lang, count=len(prossimi),
                      shown=self._mostrati)

    # --------------------------------------------------------------- ciclo

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

    def _velocita(self):
        try:
            return max(5, min(120, int(self.conf().get("speed", 40))))
        except (TypeError, ValueError):
            return 40

    def _loop(self):
        while self._running:
            if self._wake.wait(self._intervallo()):
                self._wake.clear()
            if not self._running:
                break
            try:
                self._mostra_prossimo()
            except Exception as exc:
                print("[calendario] avviso non mostrato: %s" % exc)
                self._showing = False

    def _mostra_prossimo(self):
        # La rilettura da Google avviene qui, fuori dal ciclo di disegno: la
        # cache di gcalendar decide se serve davvero una chiamata di rete.
        prossimi = gcalendar.da_mostrare(self.cfg)
        if not prossimi:
            self._showing = False
            return
        # A giro, come le scadenze: se ce n'è più d'uno si alternano, invece
        # di mostrare sempre il primo e non far sapere degli altri.
        self._indice %= len(prossimi)
        self._voce = prossimi[self._indice]
        self._indice += 1
        self._mostrati += 1

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

    # ------------------------------------------------------------- disegno

    def _colore_data(self):
        """Lo stesso colore che l'orologio usa per la data."""
        from .clock import parse_color
        clock = self.cfg.get("clock") or {}
        return parse_color(clock.get("date_color"), (0, 160, 208))

    def _sotto(self, voce):
        return voce.get("luogo") or voce.get("descrizione") or ""

    def _disegna(self):
        voce = self._voce
        if voce is None:
            return
        immagine = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        margine = max(1, self.width // 85)

        # --- quando, in alto a destra, nel colore della data dell'orologio
        quando = voce.get("quando") or ""
        if quando:
            larghezza = text_width(quando, self._font_quando)
            draw_text(immagine, (self.width - margine - larghezza, 1), quando,
                      self._font_quando, self._colore_data())

        # --- titolo al centro, che scorre solo se non ci sta
        titolo = voce.get("titolo") or ""
        y_titolo = int(self.height * Y_TITOLO)
        altezza_riga = max(1, int(self.height * TITOLO_RATIO) + 4)
        larghezza = text_width(titolo, self._font_titolo)
        area = self.width - 2 * margine
        if larghezza <= area:
            draw_text(immagine, ((self.width - larghezza) // 2, y_titolo),
                      titolo, self._font_titolo, (255, 255, 255))
        else:
            passo = self._velocita() / 30.0
            self._offset += passo
            giro = larghezza + area // 2
            if self._offset > giro:
                self._offset = 0.0
            striscia = Image.new("RGB", (larghezza + area, altezza_riga),
                                 (0, 0, 0))
            draw_text(striscia, (0, 0), titolo, self._font_titolo,
                      (255, 255, 255))
            immagine.paste(striscia.crop((int(self._offset), 0,
                                          int(self._offset) + area,
                                          altezza_riga)),
                           (margine, y_titolo))

        # --- dove (o la descrizione), centrato sotto
        sotto = self._sotto(voce)
        if sotto:
            larghezza = text_width(sotto, self._font_sotto)
            while larghezza > area and len(sotto) > 4:
                sotto = sotto[:-2]
                larghezza = text_width(sotto, self._font_sotto)
            draw_text(immagine, ((self.width - larghezza) // 2,
                                 int(self.height * Y_SOTTO)),
                      sotto, self._font_sotto, GRIGIO)

        with self._lock:
            self._image = immagine
            self._dirty = True
