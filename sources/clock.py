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

        # Ridisegna solo quando cambia qualcosa di visibile.
        signature = (shown, date if clock["show_date"] else "", meridiem,
                     clock["time_color"], clock["date_color"])
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

        if clock["show_date"]:
            box = draw.textbbox((0, 0), date, font=self._font_small)
            draw.text((self.width - (box[2] - box[0]) - 3, 2), date,
                      font=self._font_small, fill=date_color)

        if meridiem:
            draw.text((3, 2), meridiem, font=self._font_small, fill=date_color)

        return image
