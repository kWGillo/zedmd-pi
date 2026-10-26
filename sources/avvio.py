# -*- coding: utf-8 -*-
"""I primi cinque secondi: dove trovare questo apparecchio.

La richiesta
------------
*«Sarebbe utile che all'avvio sia il DMD sia il monitor pubblichino per 5
secondi il loro IP o il loro indirizzo .local.»*

E' la domanda che si fa ogni volta che si sposta l'apparecchio di stanza, si
cambia router o si riaccende dopo mesi: *dove sta adesso?* Finora la risposta
era un altro computer -- la pagina del router, un `arp-scan`, un monitor
attaccato apposta. Ma l'apparecchio **ha** uno schermo, e lo accende prima
di qualunque altra cosa: che lo dica lui.

Cinque secondi, e poi via
-------------------------
Non e' una schermata che resta: e' un cartello all'ingresso. Cinque secondi
sono il tempo di leggerli, due indirizzi corti, e non abbastanza da far
pensare che il DMD si sia impallato sulla schermata di avvio. Dopo, il
pannello fa quello che ha sempre fatto.

La presa, non la priorita'
--------------------------
Il cartello prende il pannello con `hold_on("avvio", 5)` invece di vincere
una gara di priorita'. La differenza conta: con la presa il pannello e'
**suo** e basta -- niente regioni, niente orologio sopra e media sotto,
nessuna sorgente che arriva e lo scavalca. Un indirizzo letto a meta' perche'
e' passato un aereo non serve a niente.

Gli indirizzi, senza dipendere da niente
----------------------------------------
Il nome `.local` lo pubblica avahi dalla 17.4.6 ed e' il modo piu' comodo per
tornare qui: non cambia quando cambia il DHCP. L'IPv4 si trova **senza**
interrogare `nmcli`, che su una Debian minimale puo' non esserci: si apre un
socket UDP verso un indirizzo qualunque e si guarda da che parte il kernel
sarebbe uscito. Non parte un pacchetto, e la risposta e' l'indirizzo della
scheda che tiene la rotta buona -- cioe' proprio quello da digitare.
"""

import socket
import time

from PIL import Image, ImageDraw

from .base import Source
from .clock import _load_font

# Quanto resta a schermo. Chiesto cosi': cinque secondi.
DURATA = 5.0

NOME = (0xFF, 0x8C, 0x1A)       # il nome .local: ambra, come l'ora
IP = (0xE0, 0xE4, 0xF0)         # l'indirizzo numerico
ETICHETTA = (0x78, 0x80, 0x90)  # le due paroline grigie


def nome_locale():
    """Il nome mDNS di questa macchina, con il `.local` in fondo."""
    nome = (socket.gethostname() or "").split(".")[0].strip()
    return ("%s.local" % nome) if nome else ""


def indirizzo_ipv4():
    """L'IPv4 della scheda che tiene la rotta verso fuori.

    Non si manda niente: `connect` su un socket UDP non apre nessuna
    connessione, sceglie soltanto la rotta, e `getsockname` dice da quale
    indirizzo sarebbe partito il pacchetto. E' il modo piu' corto di
    rispondere a *«che IP ho?»* senza dipendere da `nmcli`, da `ip`, o da
    quale delle due schede e' attaccata.
    """
    presa = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        presa.settimeout(0.2)
        presa.connect(("192.0.2.1", 9))   # TEST-NET-1: non esiste, non serve
        return presa.getsockname()[0]
    except OSError:
        return ""
    finally:
        presa.close()


class AvvioSource(Source):
    name = "avvio"
    label = "Avvio"
    # Sopra tutto, ma la gara non la gioca comunque: prende la presa del
    # pannello per i suoi cinque secondi. La priorita' alta serve solo
    # perche' nessuno gli passi davanti se la presa non si potesse prendere.
    priority = 99
    # Non e' una fascia: e' una schermata intera, come Doom e i giochi. Un
    # indirizzo IP dentro un terzo di schermo e' un indirizzo che non si
    # legge.
    in_fascia = False

    def __init__(self, cfg, width, height, durata=DURATA):
        Source.__init__(self, cfg, width, height)
        # Si accende da sola: non e' un servizio e non ha un interruttore
        # nella pagina Servizi. Esiste per cinque secondi e poi si spegne.
        self.enabled = True
        self._fino_a = time.monotonic() + max(0.0, durata)
        self._immagine = None
        self._disegnata = False
        self._qo = width / 256.0
        self._qv = height / 64.0
        self._corpo = max(8, int(round(14 * min(self._qo, self._qv))))
        self._piccolo = max(6, int(round(9 * min(self._qo, self._qv))))

    # ------------------------------------------------------------- l'arbitro

    def active(self):
        return self.enabled and time.monotonic() < self._fino_a

    def scaduta(self):
        """Vero quando i cinque secondi sono finiti. Lo guarda `dmdd`."""
        return time.monotonic() >= self._fino_a

    def frame(self):
        if not self.active():
            return None
        if self._disegnata:
            # Il cartello non cambia: disegnarlo trenta volte al secondo
            # sarebbe lavoro per niente, e `None` vuol dire gia' «lascia
            # quello che c'e'».
            return None
        self._disegnata = True
        return self._disegna()

    # ------------------------------------------------------------- il disegno

    def _disegna(self):
        immagine = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        d = ImageDraw.Draw(immagine)
        font = _load_font(self._corpo)
        minuto = _load_font(self._piccolo)
        nome = nome_locale()
        ip = indirizzo_ipv4()
        righe = []
        if nome:
            righe.append((nome, NOME, font))
        if ip:
            righe.append((ip, IP, font))
        if not righe:
            # Nessuna rete: e' un'informazione anche quella, e vale il
            # cartello piu' della schermata nera.
            righe.append((self.t("avvio.senza_rete"), IP, font))

        etichetta = self.t("avvio.titolo")
        alto_etichetta = self._alto(d, etichetta, minuto)
        alte = [self._alto(d, testo, f) for testo, _c, f in righe]
        stacco = max(2, int(round(3 * self._qv)))
        totale = alto_etichetta + stacco + sum(alte) + stacco * (len(alte) - 1)
        y = max(0, (self.height - totale) // 2)
        self._centra(d, etichetta, minuto, y, ETICHETTA)
        y += alto_etichetta + stacco
        for (testo, colore, f), alta in zip(righe, alte):
            self._centra(d, testo, f, y, colore)
            y += alta + stacco
        return immagine

    def _alto(self, d, testo, font):
        riquadro = d.textbbox((0, 0), testo, font=font)
        return max(1, riquadro[3] - riquadro[1])

    def _centra(self, d, testo, font, y, colore):
        riquadro = d.textbbox((0, 0), testo, font=font)
        x = max(0, (self.width - (riquadro[2] - riquadro[0])) // 2)
        d.text((x - riquadro[0], y - riquadro[1]), testo, font=font,
               fill=colore)

    # --------------------------------------------------------------- lo stato

    def status(self, lang=None):
        if self.active():
            return self.t("avvio.in_corso")
        return self.t("avvio.finito", nome=nome_locale() or "-",
                      ip=indirizzo_ipv4() or "-")
