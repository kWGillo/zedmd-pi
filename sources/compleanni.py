"""Promemoria dei compleanni sul pannello.

Riusa l'impianto del Rolling banner — testo che scorre da destra a sinistra —
perche' il problema e' lo stesso: una frase piu' larga del pannello che deve
restare leggibile. Cambia da dove viene il testo, e quando.

Priorita' 56: sopra il banner (55), perche' un compleanno e' un evento datato
e i banner sono decorazione permanente; sotto Now Playing (58), Air Radar (60)
e ZeDMD (100), che sono eventi del momento. Se stai giocando a flipper, il
promemoria aspetta il prossimo giro: manca ancora un giorno, non un minuto.
"""

import threading
import time

from PIL import Image, ImageDraw

import compleanni

from .banner import BLINK_PERIOD
from .base import Source
from .clock import _load_font, parse_color

SIZES = {"small": 0.34, "medium": 0.50, "large": 0.72}


def frase(voce, mostra_eta=True, lang="it"):
    """Il testo del promemoria: dipende da quanto manca e da che cosa si festeggia.

    "Oggi" e "domani" si dicono cosi': scrivere "fra 0 giorni" sarebbe
    corretto e illeggibile. E di un anniversario non si dice che "compie gli
    anni": si dice che lo festeggia.
    """
    nome = voce["nome"]
    mancano = voce.get("mancano", 0)
    anni = voce.get("eta") if mostra_eta else None
    anniversario = voce.get("tipo") == "anniversario"

    if lang == "en":
        cosa = "anniversary" if anniversario else "birthday"
        if mancano == 0:
            testo = "Today %s's %s" % (nome, cosa)
        elif mancano == 1:
            testo = "Tomorrow %s's %s" % (nome, cosa)
        else:
            testo = "%s's %s in %d days" % (nome, cosa, mancano)
        if anni:
            testo += " - %d years" % anni if anniversario else " - turns %d" % anni
        return testo

    if anniversario:
        quando = {0: "Oggi", 1: "Domani"}.get(mancano, "Fra %d giorni" % mancano)
        testo = "%s l'anniversario di %s" % (quando, nome)
        if anni:
            testo += " - %d anni" % anni
        return testo

    if mancano == 0:
        testo = "Oggi compie gli anni %s" % nome
    elif mancano == 1:
        testo = "Domani compie gli anni %s" % nome
    else:
        testo = "Fra %d giorni compie gli anni %s" % (mancano, nome)
    if anni:
        testo += " - %d anni" % anni
    return testo


class BirthdaysSource(Source):
    name = "birthdays"
    label = "Compleanni"
    priority = 56

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
        self._indice = 0
        self._fonts = {}

    # ------------------------------------------------------------ ciclo di vita

    def start(self):
        if self._running:
            return
        self._running = True
        self._wake.clear()
        self._thread = threading.Thread(target=self._loop, name="compleanni",
                                        daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._showing = False
        self._wake.set()

    def trigger_now(self):
        """Mostra subito il prossimo promemoria, senza aspettare l'intervallo."""
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
        cfg = self.cfg["birthdays"]
        prossimi = self.imminenti()
        if not prossimi:
            return self.t("status.birthdays.none", lang,
                          hours=int(cfg["lead_hours"]))
        primo = prossimi[0]
        return self.t("status.birthdays.next", lang,
                      name=primo["nome"], days=primo["mancano"],
                      count=len(prossimi), shown=self._shown)

    # ------------------------------------------------------------------ dati

    def imminenti(self):
        try:
            return compleanni.imminenti(self.cfg["birthdays"]["lead_hours"])
        except Exception as exc:
            print("[compleanni] elenco non leggibile: %s" % exc)
            return []

    # ------------------------------------------------------------------ ciclo

    def _loop(self):
        while self._running:
            cfg = self.cfg["birthdays"]
            elenco = self.imminenti()
            if elenco:
                if self._indice >= len(elenco):
                    self._indice = 0
                try:
                    self._scorri(elenco[self._indice], cfg)
                except Exception as exc:
                    print("[compleanni] %s" % exc)
                self._indice += 1
            # L'attesa e' la stessa anche senza compleanni in vista: il file
            # puo' cambiare, e rileggerlo ogni tanto costa niente.
            attesa = max(60, int(cfg["interval_minutes"]) * 60)
            if elenco and self._indice < len(elenco):
                # Fra due promemoria dello stesso giro basta una pausa breve:
                # l'intervallo lungo separa i giri, non le persone.
                attesa = 5
            self._wake.wait(attesa)
            self._wake.clear()

    def _font(self, size):
        if size not in self._fonts:
            frazione = SIZES.get(size, SIZES["medium"])
            self._fonts[size] = _load_font(max(8, int(self.height * frazione)))
        return self._fonts[size]

    def _striscia(self, testo, cfg):
        font = self._font(cfg.get("size", "medium"))
        colore = parse_color(cfg.get("color", "#ff40a0"), (255, 64, 160))
        probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        box = probe.textbbox((0, 0), testo, font=font)
        larghezza = max(1, box[2] - box[0])
        altezza_testo = box[3] - box[1]
        strip = Image.new("RGB", (larghezza, self.height), (0, 0, 0))
        ImageDraw.Draw(strip).text(
            (-box[0], (self.height - altezza_testo) // 2 - box[1]),
            testo, font=font, fill=colore)
        return strip

    def _pubblica(self, image):
        with self._lock:
            self._image = image
            self._dirty = True

    def _scorri(self, voce, cfg):
        # La lingua del pannello e' quella scelta nella web UI; vuota
        # significa "decidila tu", e per un display fisso l'italiano e' la
        # scelta giusta.
        lingua = (self.cfg.get("web") or {}).get("language") or "it"
        testo = frase(voce, cfg.get("show_age", True), lingua)
        strip = self._striscia(testo, cfg)

        velocita = max(10, int(cfg.get("speed", 40)))
        fps = 30
        passo = velocita / float(fps)

        self._current = testo
        self._showing = True
        inizio = time.time()
        limite = inizio + max(3, int(cfg.get("seconds", 12)))

        posizione = float(self.width)
        fine = -float(strip.width)
        while self._running and posizione > fine and time.time() < limite:
            tela = Image.new("RGB", (self.width, self.height), (0, 0, 0))
            visibile = True
            if cfg.get("blink"):
                fase = (time.time() - inizio) % BLINK_PERIOD
                visibile = fase < BLINK_PERIOD / 2
            if visibile:
                tela.paste(strip, (int(round(posizione)), 0))
            self._pubblica(tela)
            posizione -= passo
            time.sleep(1.0 / fps)

        self._shown += 1
        self._showing = False
