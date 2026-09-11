"""Satelliti: i passaggi visibili della Stazione Spaziale sul pannello.

Non e' un radar. L'Air Radar racconta quello che passa sopra casa perche' e'
interessante saperlo; questa sorgente esiste per un motivo piu' stretto e piu'
bello: **farti uscire in terrazzo al momento giusto**.

Da qui discende tutto il resto.

*Perche' parla poco.* In cielo ci sono sedicimila oggetti attivi, e da un
punto a terra qualche centinaio sta sopra l'orizzonte in ogni istante. Ma a
occhio nudo se ne vedono pochissimi, e solo quando il satellite e' illuminato
dal Sole mentre qui e' gia' buio. Quella condizione, piu' la tabella dei
pochi oggetti di cui conosciamo davvero la luminosita', porta sedicimila a
**uno o due eventi al giorno**. E' una sorgente a eventi, come i Compleanni:
sta zitta finche' non ha qualcosa che vale la pena.

*Perche' avvisa prima.* Un passaggio della Stazione dura fra i due e i sette
minuti -- misurati, non stimati. Annunciarlo mentre sta succedendo vuol dire
arrivare in terrazzo a cose finite. Il preavviso e' di dieci minuti, con un
promemoria a cinque: il tempo di alzarsi, uscire, e lasciare che gli occhi si
abituino al buio prima che il puntino sorga.

*Perche' durante il passaggio cambia mestiere.* Nei minuti in cui la Stazione
e' in cielo il pannello non serve piu' a ricordare: serve a chi e' fuori e
sta cercando. Quindi mostra **dove guardare adesso** -- l'arco del passaggio
e il puntino che ci scorre sopra -- e l'ora lampeggia, perche' non e' piu' un
promemoria, sta succedendo.

Il lampeggio va a secondi pari, la stessa fase dei due punti dell'orologio:
due cose che lampeggiano insieme sembrano un battito, due sfasate sembrano un
guasto.
"""

import threading
import time
from datetime import datetime, timedelta, timezone

from PIL import Image, ImageDraw

import satelliti
from .base import Source
from .clock import _load_font

# --------------------------------------------------------------------- colori

# Il colore dice **che genere di evento e'**, il lampeggio dice che sta
# succedendo adesso. Due canali indipendenti: nessuna ridondanza, e chi guarda
# da lontano capisce a colpo d'occhio senza leggere.
VERDE = (0x30, 0xF0, 0x60)        # in arrivo
VERDE_CUPO = (0x18, 0x80, 0x38)
BIANCO = (0xFF, 0xFF, 0xFF)       # adesso
GRIGIO = (0x70, 0x78, 0x88)
ARCO = (0x40, 0x80, 0xD0)
PUNTO = (0xFF, 0xF0, 0xC0)

PUNTI_BUSSOLA = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                 "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO"]


def bussola(gradi):
    if gradi is None:
        return "?"
    return PUNTI_BUSSOLA[int((gradi + 11.25) % 360 / 22.5)]


class SatellitiSource(Source):
    name = "satelliti"
    label = "Satelliti"
    # Sopra l'Air Radar (60), sotto l'anteprima. Un passaggio ha un **orario**:
    # succede alle 21:10 o non succede piu'. Un aereo no, ne passa un altro fra
    # cinque minuti. Nessuna priorita' pareggia con un'altra, e una prova lo
    # pretende.
    priority = 61

    def __init__(self, cfg, width, height):
        super().__init__(cfg, width, height)
        self._running = False
        self._lock = threading.Lock()
        self._image = None
        self._dirty = False
        self._stato = ""
        self._passaggi = []
        self._errore = ""
        self._ultimo_calcolo = 0.0
        self._ultima_firma = None
        self._wake = threading.Event()
        self._thread = None
        self._font_grande = _load_font(max(12, int(height * 0.46)))
        self._font_medio = _load_font(max(9, int(height * 0.24)))
        self._font_piccolo = _load_font(max(7, int(height * 0.18)))

    # ------------------------------------------------------------- ciclo vita

    def start(self):
        if self._running:
            return
        self._running = True
        self._ultimo_calcolo = 0.0
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._wake.set()
        with self._lock:
            self._image = None
            self._dirty = False
        self._stato = ""

    def active(self):
        return self._running and bool(self._stato)

    def frame(self):
        with self._lock:
            if not self._dirty or self._image is None:
                return None
            self._dirty = False
            return self._image

    # ------------------------------------------------------------------ stato

    def status(self, lang=None):
        if not self._running:
            return self.t("status.disabled", lang)
        if not satelliti.DISPONIBILE:
            return self.t("satelliti.manca", lang)
        if self._errore:
            return self._errore
        prossimo = self._prossimo()
        if prossimo is None:
            return self.t("status.satelliti.none", lang)
        quando = prossimo["sorge"].astimezone()
        return self.t("status.satelliti.next", lang,
                      name=prossimo.get("breve", prossimo["nome"]),
                      time=quando.strftime("%H:%M"),
                      elev=int(round(prossimo["elevazione_massima"])))

    def _conf(self):
        return self.cfg.get("satelliti", {})

    def _prossimo(self, adesso=None):
        """Il primo passaggio non ancora finito."""
        adesso = adesso or datetime.now(timezone.utc)
        for p in self._passaggi:
            if p["tramonta"] >= adesso:
                return p
        return None

    # ------------------------------------------------------------------ ciclo

    def _loop(self):
        while self._running:
            try:
                self._aggiorna_dati()
                self._disegna_se_serve()
            except Exception as exc:          # noqa: BLE001
                # Un satellite che non si vede non deve spegnere il DMD.
                print("[satelliti] %s" % exc)
                self._errore = str(exc)
            # Mezzo secondo mentre c'e' qualcosa da mostrare: e' il ritmo del
            # lampeggio e dell'arco che si muove. Fuori dagli eventi non serve
            # affatto, e su un Pi il tempo di CPU sono righe chiare sul
            # pannello.
            self._wake.wait(0.5 if self._stato else 5.0)
            self._wake.clear()

    def _aggiorna_dati(self):
        """Riscarica i TLE e ricalcola i passaggi, quando e' il momento.

        Il calcolo e' la parte cara -- centinaia di propagazioni -- e si fa una
        volta ogni sei ore, non a ogni giro. I TLE se li gestisce `satelliti`,
        che non interroga CelesTrak piu' di quanto la loro politica consenta.
        """
        if not satelliti.DISPONIBILE:
            # Senza la libreria di calcolo orbitale non c'e' niente da fare, e
            # non e' un errore da ripetere nel registro mille volte al giorno:
            # e' una dipendenza che manca, e lo dice la riga di stato.
            self._passaggi = []
            self._ultimo_calcolo = time.time()
            return
        conf = self._conf()
        ogni = max(1800, int(conf.get("ricalcola_minuti", 360)) * 60)
        if self._passaggi and time.time() - self._ultimo_calcolo < ogni:
            return
        self._ultimo_calcolo = time.time()

        lat, lon = self._coordinate()
        if lat is None:
            self._errore = "coordinate non impostate"
            self._passaggi = []
            return

        cartella = conf.get("cartella_tle", "/var/lib/dmd/tle")
        gruppi = conf.get("gruppi") or list(satelliti.GRUPPI_PREDEFINITI)
        elenco = []
        for gruppo in gruppi:
            satelliti.scarica(gruppo, cartella)
            elenco = satelliti.unisci(elenco, satelliti.carica(gruppo, cartella))
        if not elenco:
            self._errore = "nessun elemento orbitale disponibile"
            self._passaggi = []
            return

        self._errore = ""
        self._passaggi = satelliti.prossimi(
            elenco, lat, lon, datetime.now(timezone.utc),
            ore=int(conf.get("finestra_ore", 24)),
            elevazione_minima=float(conf.get("elevazione_minima", 10.0)),
            solo_visibili=True, massimo=20,
            solo_noti=not bool(conf.get("tutti_gli_oggetti", False)))

    def _coordinate(self):
        """Le coordinate sono quelle del radar: una casa sola, un posto solo.

        Non entrano nel codice e non entrano nel repository: stanno solo nella
        configurazione locale. Per i satelliti possono anche essere volutamente
        imprecise -- spostarsi di undici chilometri cambia gli orari di due
        secondi, misurati.
        """
        radar = self.cfg.get("air_radar", {})
        lat = float(radar.get("latitude", 0.0) or 0.0)
        lon = float(radar.get("longitude", 0.0) or 0.0)
        if lat == 0.0 and lon == 0.0:
            return None, None
        return lat, lon

    # --------------------------------------------------------------- disegno

    def _disegna_se_serve(self):
        adesso = datetime.now(timezone.utc)
        passaggio = self._prossimo(adesso)
        conf = self._conf()
        preavviso = int(conf.get("preavviso_minuti", satelliti.PREAVVISO_MIN))
        cadenza = max(1, int(conf.get("cadenza_minuti", satelliti.CADENZA_MIN)))

        stato = ""
        if passaggio is not None:
            stato = satelliti.stato(passaggio, adesso, preavviso)
            if stato == "avviso" and not self._nella_finestra(
                    passaggio, adesso, preavviso, cadenza):
                stato = ""
        self._stato = stato
        if not stato:
            return

        acceso = (adesso.second % 2 == 0)
        mancano = int(round(
            (passaggio["sorge"] - adesso).total_seconds() / 60.0))
        # La firma evita di ridisegnare cinquanta volte lo stesso fotogramma:
        # cambia quando cambia qualcosa che si vede.
        if stato == "adesso":
            firma = ("adesso", passaggio["sorge"], acceso,
                     int((adesso - passaggio["sorge"]).total_seconds()))
        else:
            firma = ("avviso", passaggio["sorge"], mancano)
        if firma == self._ultima_firma:
            return
        self._ultima_firma = firma

        if stato == "adesso":
            img = self._adesso(passaggio, adesso, acceso)
        else:
            img = self._avviso(passaggio, mancano)
        with self._lock:
            self._image = img
            self._dirty = True

    def _nella_finestra(self, passaggio, adesso, preavviso, cadenza):
        """Il preavviso non resta appeso per dieci minuti.

        Compare a T-10 e torna a T-5: due lampi brevi, non una sorgente che
        occupa il pannello per un quarto d'ora. Fra un promemoria e l'altro
        lascia lavorare gli altri.
        """
        durata = int(self._conf().get("durata_avviso_secondi", 20))
        mancano = (passaggio["sorge"] - adesso).total_seconds()
        minuto = preavviso
        while minuto >= cadenza:
            inizio = minuto * 60.0
            if inizio >= mancano > inizio - durata:
                return True
            minuto -= cadenza
        return False

    def _testo(self, d, x, y, s, font, colore, ancora="la"):
        d.text((x, y), s, font=font, fill=colore, anchor=ancora)

    def _avviso(self, passaggio, mancano):
        """Tre informazioni e non una di piu': chi, a che ora, dove guardare.

        La quarta che verrebbe voglia di scrivere -- durata, magnitudine,
        numero di catalogo -- e' quella che rende la riga illeggibile da tre
        metri di distanza, che e' la distanza da cui questo pannello si
        guarda.
        """
        L, A = self.width, self.height
        img = Image.new("RGB", (L, A), (0, 0, 0))
        d = ImageDraw.Draw(img)
        nome = passaggio.get("breve", passaggio["nome"])[:12]
        self._testo(d, 4, int(A * 0.02), nome, self._font_grande, VERDE)
        ora = passaggio["sorge"].astimezone().strftime("%H:%M")
        self._testo(d, L - 4, int(A * 0.02), ora, self._font_grande, VERDE,
                    ancora="ra")
        self._testo(d, 4, int(A * 0.62),
                    self.t("satelliti.in", None, min=max(0, mancano)),
                    self._font_medio, VERDE_CUPO)
        dove = "%s  %d°" % (bussola(passaggio["azimut_sorge"]),
                                 round(passaggio["elevazione_massima"]))
        self._testo(d, L - 4, int(A * 0.66), dove, self._font_piccolo,
                    VERDE_CUPO, ancora="ra")
        return img

    def _adesso(self, passaggio, quando, acceso):
        """Durante il passaggio: dove guardare, adesso.

        A destra non c'e' un disegnino decorativo. L'asse orizzontale e' il
        tragitto da dove sorge a dove tramonta, quello verticale l'altezza
        sull'orizzonte, e il puntino sta dove sta adesso. Chi e' in terrazzo
        alza gli occhi e sa **quanto in alto** guardare, che e' l'informazione
        che manca sempre quando qualcuno ti dice "guarda, c'e' la Stazione".
        """
        L, A = self.width, self.height
        img = Image.new("RGB", (L, A), (0, 0, 0))
        d = ImageDraw.Draw(img)
        lat, lon = self._coordinate()
        vista = satelliti.guarda(passaggio["sat"], quando, lat, lon)
        if vista is None:
            return img

        nome = passaggio.get("breve", passaggio["nome"])[:8]
        self._testo(d, 4, int(A * 0.01), nome, self._font_grande, BIANCO)
        if acceso:
            self._testo(d, 4, int(A * 0.47),
                        quando.astimezone().strftime("%H:%M"),
                        self._font_medio, BIANCO)
        self._testo(d, 4, int(A * 0.73),
                    "ALT %d°" % round(vista["elevazione"]),
                    self._font_piccolo, GRIGIO)

        x0, x1 = int(L * 0.41), L - int(L * 0.06)
        # La base dell'arco lascia sotto lo spazio per le due sigle: su
        # sessantaquattro pixel un carattere che sborda non si vede "un po'",
        # sparisce.
        base, cima = int(A * 0.78), int(A * 0.09)

        durata = (passaggio["tramonta"] - passaggio["sorge"]).total_seconds()
        campioni = []
        for i in range(41):
            t = passaggio["sorge"] + timedelta(seconds=durata * i / 40.0)
            v = satelliti.guarda(passaggio["sat"], t, lat, lon)
            if v is not None:
                campioni.append((i / 40.0, max(0.0, v["elevazione"])))
        if not campioni:
            return img
        # La scala verticale viene dalla curva disegnata, non da un valore
        # calcolato altrove: se le due non coincidono il puntino esce dal
        # grafico, e si vede.
        massima = max([e for _, e in campioni] + [vista["elevazione"], 1.0])

        d.line([(x0 - 4, base), (x1 + 4, base)], fill=(0x30, 0x34, 0x3C))
        punti = [(x0 + (x1 - x0) * f, base - (base - cima) * e / massima)
                 for f, e in campioni]
        if len(punti) > 1:
            d.line(punti, fill=ARCO, width=1)

        fatto = (quando - passaggio["sorge"]).total_seconds() / max(durata, 1.0)
        fatto = min(max(fatto, 0.0), 1.0)
        px = x0 + (x1 - x0) * fatto
        py = base - (base - cima) * max(0.0, vista["elevazione"]) / massima
        d.line([(px, base), (px, py)], fill=(0x22, 0x30, 0x48))
        d.ellipse([px - 2, py - 2, px + 2, py + 2], fill=PUNTO)

        self._testo(d, x0 - 4, base + 2, bussola(passaggio["azimut_sorge"]),
                    self._font_piccolo, GRIGIO)
        self._testo(d, x1 + 4, base + 2, bussola(passaggio["azimut_tramonta"]),
                    self._font_piccolo, GRIGIO, ancora="ra")
        return img
