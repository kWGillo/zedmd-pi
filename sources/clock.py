"""Orologio.

Sorgente a priorita' piu' bassa: riempie il display quando nessun altro
servizio ha qualcosa da mostrare. Colori di ora e data indipendenti,
formato 12 o 24 ore, nomi dei giorni in italiano, francese o inglese.
"""

import time

from PIL import Image, ImageDraw, ImageFont

from .base import Source

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]

# Indice 0 = lunedi', come time.struct_time.tm_wday
DAY_NAMES = {
    "it": ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"],
    "en": ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"],
    "fr": ["LUN", "MAR", "MER", "JEU", "VEN", "SAM", "DIM"],
}

LANGUAGES = [("it", "Italiano"), ("fr", "Français"), ("en", "English")]


def parse_color(value, fallback=(255, 140, 26)):
    """Converte '#rrggbb' in una tupla RGB."""
    try:
        text = str(value).strip().lstrip("#")
        if len(text) == 3:
            text = "".join(ch * 2 for ch in text)
        if len(text) != 6:
            return fallback
        return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))
    except (TypeError, ValueError):
        return fallback


def _load_font(size):
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


class ClockSource(Source):
    name = "clock"
    label = "Clock"
    priority = 10

    def __init__(self, cfg, width, height):
        super().__init__(cfg, width, height)
        self._running = False
        self._signature = None
        self._font = _load_font(max(12, int(height * 0.60)))
        self._font_small = _load_font(max(8, int(height * 0.20)))
        # Font della colonna dei rifiuti, dal piu' grande al piu' piccolo. Si
        # sceglie il primo in cui il nome piu' lungo sta nello spazio libero:
        # i nomi li scrive l'utente, e "Indifferenziato" non e' "Carta".
        self._font_rifiuti = [_load_font(max(6, int(height * f)))
                              for f in (0.170, 0.155, 0.140, 0.125, 0.110)]

    def start(self):
        self._running = True
        self._signature = None

    def stop(self):
        self._running = False

    def active(self):
        return self._running

    def status(self, lang=None):
        if not self._running:
            return self.t("status.disabled", lang)
        clock = self.cfg["clock"]
        return self.t("status.clock.active", lang,
                      format="24h" if clock["format_24h"] else "12h",
                      language=clock["language"].upper())

    def invalidate(self):
        """Forza il ridisegno, ad esempio dopo un cambio di impostazioni."""
        self._signature = None

    # ------------------------------------------------------------- rifiuti

    def _colonna(self):
        """Le voci da ricordare adesso. Mai un'eccezione fino al pannello.

        L'orologio e' la sorgente che si vede quasi sempre: un errore nel
        calendario dei rifiuti — un file scritto male, una data assurda — non
        deve portarsi via anche l'ora.
        """
        try:
            import rifiuti
            return rifiuti.attive(self.cfg)
        except Exception as exc:
            print("[clock] calendario rifiuti non leggibile: %s" % exc)
            return []

    def _disegna_colonna(self, draw, voci, limite):
        """Disegna le voci impilate a sinistra, dentro `limite` pixel.

        Impilate e non affiancate: i nomi hanno lunghezze diverse e in
        orizzontale si leggerebbero come una parola sola. In verticale ognuna
        ha la sua riga e il suo colore, che e' l'informazione vera — a colpo
        d'occhio si riconosce il colore prima ancora della parola.

        Lo spazio disponibile e' quello che l'ora lascia libero, e non e'
        negoziabile: se i nomi non ci stanno si rimpicciolisce il testo, e
        se non basta si taglia. Meglio "INDIFFERENZ" leggibile che una parola
        intera sopra le cifre dell'ora.
        """
        if not voci or limite < 12:
            return
        testi = [v["nome"].upper() for v in voci[:5]]
        larghezza_utile = limite - 2

        font = self._font_rifiuti[-1]
        for candidato in self._font_rifiuti:
            if all(draw.textlength(t, font=candidato) <= larghezza_utile
                   for t in testi):
                font = candidato
                break

        passo = max(7, self.height // max(len(testi), 4))
        box = draw.textbbox((0, 0), "AG", font=font)
        alto = box[3] - box[1]
        for indice, (testo, voce) in enumerate(zip(testi, voci)):
            while testo and draw.textlength(testo, font=font) > larghezza_utile:
                testo = testo[:-1]
            y = indice * passo + max(0, (passo - alto) // 2)
            draw.text((2, y), testo, font=font,
                      fill=parse_color(voce.get("colore"), (255, 255, 255)))

    def frame(self):
        if not self._running:
            return None

        clock = self.cfg["clock"]
        now = time.localtime()

        if clock["format_24h"]:
            text = time.strftime("%H:%M", now)
            meridiem = ""
        else:
            hour = now.tm_hour % 12 or 12
            text = "%d:%02d" % (hour, now.tm_min)
            meridiem = "AM" if now.tm_hour < 12 else "PM"

        second_even = (now.tm_sec % 2 == 0)
        if clock["blink_colon"] and not second_even:
            shown = text.replace(":", " ")
        else:
            shown = text

        days = DAY_NAMES.get(clock["language"], DAY_NAMES["it"])
        date = "%s %02d/%02d" % (days[now.tm_wday], now.tm_mday, now.tm_mon)

        colonna = self._colonna()

        # Ridisegna solo quando cambia qualcosa di visibile.
        signature = (shown, date if clock["show_date"] else "", meridiem,
                     clock["time_color"], clock["date_color"],
                     tuple((v["nome"], v["colore"]) for v in colonna))
        if signature == self._signature:
            return None
        self._signature = signature

        time_color = parse_color(clock["time_color"])
        date_color = parse_color(clock["date_color"], (0, 160, 208))

        image = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        draw = ImageDraw.Draw(image)

        box = draw.textbbox((0, 0), shown, font=self._font)
        x = (self.width - (box[2] - box[0])) // 2 - box[0]
        y = (self.height - (box[3] - box[1])) // 2 - box[1]
        draw.text((x, y), shown, font=self._font, fill=time_color)

        # L'ora resta al centro, sempre: la colonna vive nello spazio che
        # avanza alla sua sinistra e si adatta a quello. Un orologio che si
        # sposta quando arriva un promemoria e torna indietro quando se ne va
        # e' un orologio che si muove per conto suo.
        self._disegna_colonna(draw, colonna, limite=x - 3)

        if clock["show_date"]:
            box = draw.textbbox((0, 0), date, font=self._font_small)
            draw.text((self.width - (box[2] - box[0]) - 3, 2), date,
                      font=self._font_small, fill=date_color)

        if meridiem:
            draw.text((3, 2), meridiem, font=self._font_small, fill=date_color)

        return image
