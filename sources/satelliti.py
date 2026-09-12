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

import csv
import os
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

# Il terzo stato: un passaggio che c'e' ma non si vede. Grigio-azzurro spento,
# niente preavviso, niente lampeggio. Il colore e l'assenza di lampeggio dicono
# da soli che non e' un invito a uscire -- e intanto l'arco, che e' la parte
# piu' bella da guardare, resta. Sono quattro comparse al giorno contro una.
SPENTO = (0x50, 0x62, 0x88)
SPENTO_CUPO = (0x2A, 0x34, 0x4C)
ARCO_SPENTO = (0x22, 0x30, 0x50)

# Dove il puntino sparisce entrando nell'ombra della Terra: un taglio sull'arco
# e il resto disegnato in tono minore, perche' da li' in poi non c'e' piu'
# niente da vedere.
OMBRA = (0x80, 0x40, 0x30)

# Le colonne del registro. L'ordine non si cambia a cuor leggero: un file gia'
# scritto ha le sue, e aggiungerne una in mezzo produce righe disallineate.
# Come per il radar, se cambiano il vecchio registro si mette da parte con la
# data nel nome invece di rovinarlo.
COLONNE_CSV = ["sorge", "nome", "norad", "gruppo", "durata_min",
               "elevazione_massima", "azimut_sorge", "azimut_tramonta",
               "magnitudine", "visibile", "sole_gradi"]

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
        # I passaggi gia' scritti nel registro, per non riscriverli a ogni
        # ricalcolo. La chiave e' il satellite piu' l'istante del sorgere al
        # minuto: lo stesso passaggio ricalcolato sei ore dopo cade sullo
        # stesso minuto.
        self._registrati = set()
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

    def _prossimo(self, adesso=None, solo_visibili=True):
        """Il primo passaggio non ancora finito.

        Sul pannello vanno solo i visibili: annunciare un passaggio diurno
        manderebbe qualcuno a cercare un puntino che non c'e'. Nel registro ci
        finiscono tutti.
        """
        adesso = adesso or datetime.now(timezone.utc)
        for p in self._passaggi:
            if p["tramonta"] < adesso:
                continue
            if solo_visibili and not p.get("visibile"):
                continue
            return p
        return None

    # ------------------------------------------------------------------ ciclo

    def _loop(self):
        while self._running:
            try:
                self._aggiorna_dati()
                self._registra_conclusi(datetime.now(timezone.utc))
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
        # **Tutti** i passaggi, non solo quelli visibili. Il filtro della
        # visibilita' e' una scelta di cosa *mostrare*, non di cosa *sapere*:
        # con due soli oggetti calcolarli tutti costa niente, e il registro
        # puo' rispondere alla domanda vera -- "perche' stasera il DMD non ha
        # detto niente?" -- con "perche' e' passata a 70 gradi alle 14:20, in
        # pieno giorno".
        self._passaggi = satelliti.prossimi(
            elenco, lat, lon, datetime.now(timezone.utc),
            ore=int(conf.get("finestra_ore", 24)),
            elevazione_minima=float(conf.get("elevazione_minima", 10.0)),
            solo_visibili=False, massimo=40,
            solo_noti=not bool(conf.get("tutti_gli_oggetti", False)))

    def ricalcola(self):
        """Butta via i passaggi e li rifa' al prossimo giro.

        La chiama la pagina web dopo un salvataggio: elevazione minima e
        gruppi cambiano l'elenco, e mostrare i passaggi vecchi accanto ai
        valori nuovi e' il modo piu' rapido per far credere che il
        salvataggio non abbia funzionato.
        """
        self._ultimo_calcolo = 0.0
        self._passaggi = []
        self._ultima_firma = None
        self._wake.set()

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

    # -------------------------------------------------------------- registro

    def percorso_registro(self):
        return self._conf().get("log_path", "/var/lib/dmd/satelliti.csv")

    def _chiave(self, passaggio):
        return (passaggio["norad"], passaggio["sorge"].strftime("%Y%m%d%H%M"))

    def _registra_conclusi(self, adesso):
        """Scrive nel registro i passaggi che sono appena finiti.

        Si scrive **a cose fatte**, non al calcolo: un passaggio previsto non
        e' un passaggio avvenuto, e un registro che mescola le due cose non
        risponde piu' a nessuna domanda. E' la stessa regola del registro dei
        voli: dentro c'e' quello che il DMD ha visto passare, non quello che
        si aspettava.

        Ci finiscono anche i **non visibili**, con la colonna che lo dice e
        l'altezza del Sole che spiega perche'. E' l'unico modo per rispondere
        a "stasera il pannello non ha detto niente": perche' la Stazione e'
        passata alle due del pomeriggio.
        """
        if not self._conf().get("log_enabled", True):
            return
        nuovi = [p for p in self._passaggi
                 if p["tramonta"] <= adesso and self._chiave(p) not in self._registrati]
        if not nuovi:
            return
        percorso = self.percorso_registro()
        try:
            cartella = os.path.dirname(percorso)
            if cartella:
                os.makedirs(cartella, exist_ok=True)
            nuovo_file = (not os.path.exists(percorso)
                          or os.path.getsize(percorso) == 0)
            if not nuovo_file and self._intestazione_cambiata(percorso):
                storico = "%s.%s.csv" % (
                    percorso[:-4] if percorso.endswith(".csv") else percorso,
                    time.strftime("%Y%m%d-%H%M%S"))
                try:
                    os.rename(percorso, storico)
                    print("[satelliti] registro precedente in %s" % storico)
                    nuovo_file = True
                except OSError:
                    pass
            with open(percorso, "a", newline="") as fh:
                scrittore = csv.writer(fh)
                if nuovo_file:
                    scrittore.writerow(COLONNE_CSV)
                for p in sorted(nuovi, key=lambda q: q["sorge"]):
                    self._registrati.add(self._chiave(p))
                    lat, lon = self._coordinate()
                    sole = ""
                    if lat is not None:
                        sole = "%.1f" % satelliti.elevazione_sole(
                            p["culmine"], lat, lon)
                    scrittore.writerow([
                        p["sorge"].astimezone().strftime("%Y-%m-%dT%H:%M:%S"),
                        p.get("breve", p["nome"]),
                        p["norad"],
                        p.get("gruppo", ""),
                        "%.1f" % p["durata_min"],
                        "%.0f" % p["elevazione_massima"],
                        bussola(p["azimut_sorge"]),
                        bussola(p["azimut_tramonta"]),
                        "" if p.get("magnitudine") is None else "%.1f" % p["magnitudine"],
                        "si" if p.get("visibile") else "no",
                        sole,
                    ])
        except OSError as exc:
            print("[satelliti] registro non scrivibile: %s" % exc)

    @staticmethod
    def _intestazione_cambiata(percorso):
        try:
            with open(percorso, newline="") as fh:
                prima = next(csv.reader(fh), [])
        except (OSError, StopIteration):
            return False
        return prima != COLONNE_CSV

    def info_registro(self):
        """Quante righe ha il registro e quanto pesa, per la pagina web."""
        percorso = self.percorso_registro()
        try:
            with open(percorso, newline="") as fh:
                righe = max(0, sum(1 for _ in fh) - 1)
            return {"path": percorso, "rows": righe,
                    "size": os.path.getsize(percorso)}
        except OSError:
            return {"path": percorso, "rows": 0, "size": 0}

    def svuota_registro(self):
        try:
            os.remove(self.percorso_registro())
            self._registrati.clear()
            return True
        except OSError:
            return False

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
        if not stato and conf.get("mostra_non_visibili", True):
            # Nessun passaggio visibile da annunciare: c'e' per caso qualcosa
            # che sta passando adesso senza vedersi? Si mostra solo attorno al
            # culmine, e per pochi secondi: e' una cartolina, non un avviso, e
            # non deve tenere il pannello per sei minuti.
            invisibile = self._invisibile_adesso(adesso)
            if invisibile is not None:
                passaggio, stato = invisibile, "spento"
        self._stato = stato
        if not stato:
            return

        acceso = (adesso.second % 2 == 0)
        mancano = int(round(
            (passaggio["sorge"] - adesso).total_seconds() / 60.0))
        # La firma evita di ridisegnare cinquanta volte lo stesso fotogramma:
        # cambia quando cambia qualcosa che si vede.
        if stato in ("adesso", "spento"):
            firma = (stato, passaggio["sorge"], acceso and stato == "adesso",
                     int((adesso - passaggio["sorge"]).total_seconds()))
        else:
            firma = ("avviso", passaggio["sorge"], mancano)
        if firma == self._ultima_firma:
            return
        self._ultima_firma = firma

        if stato == "adesso":
            img = self._adesso(passaggio, adesso, acceso)
        elif stato == "spento":
            # L'ora non lampeggia: non sta succedendo niente che tu possa
            # vedere, e un lampeggio direbbe il contrario.
            img = self._adesso(passaggio, adesso, True, visibile=False)
        else:
            img = self._avviso(passaggio, mancano)
        with self._lock:
            self._image = img
            self._dirty = True

    def _invisibile_adesso(self, adesso):
        """Un passaggio non visibile che sta culminando proprio ora.

        Si mostra attorno al **culmine** e non dal sorgere: e' l'istante in cui
        il puntino sarebbe piu' alto, l'arco e' piu' bello da guardare, e
        soprattutto dura pochi secondi invece di sei minuti. Il pannello ha
        altre cose da dire.
        """
        durata = max(5, int(self._conf().get("durata_spento_secondi", 25)))
        meta = timedelta(seconds=durata / 2.0)
        for p in self._passaggi:
            if p.get("visibile"):
                continue
            if p["culmine"] - meta <= adesso <= p["culmine"] + meta:
                return p
        return None

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

    def _larghezza(self, d, s, font):
        riquadro = d.textbbox((0, 0), s, font=font)
        return riquadro[2] - riquadro[0]

    def durata_visibile(self, passaggio):
        """Quanti secondi dura davvero la parte che si vede.

        **Non e' la durata geometrica**, ed e' la lezione di una sera vera:
        il passaggio delle 22:48 del 12 settembre durava 5,9 minuti sopra
        l'orizzonte, ma la Stazione entrava nell'ombra della Terra quaranta
        secondi dopo essere sorta. Scrivere "6 MIN" su quel passaggio sarebbe
        stato un invito a uscire per qualcosa che non c'era piu'.
        """
        fine = passaggio.get("spegnimento") or passaggio["tramonta"]
        if fine > passaggio["tramonta"]:
            fine = passaggio["tramonta"]
        return max(0.0, (fine - passaggio["sorge"]).total_seconds())

    def durata_breve(self, secondi, lang=None):
        """La durata in una manciata di caratteri.

        Sotto il minuto e mezzo si scrivono i secondi, arrotondati a cinque:
        la differenza fra 38 e 43 secondi non cambia niente per chi sta
        infilandosi le scarpe, e la falsa precisione occupa spazio.
        """
        if secondi < 90:
            return self.t("satelliti.lasts.sec", lang,
                          sec=int(round(secondi / 5.0) * 5))
        return self.t("satelliti.lasts.min", lang,
                      min=max(1, int(round(secondi / 60.0))))

    def _avviso(self, passaggio, mancano):
        """Il preavviso: fra quanto, di chi, dove guardare e per quanto.

        La versione precedente scriveva l'**ora di sorgere** in grande a
        destra -- stessa posizione, stesso corpo e quasi stesso colore
        dell'orologio che questo pannello mostra tutto il resto del tempo.
        Chi passava in salotto leggeva `21:10` come "sono le 21:10" e `FRA 5
        MIN` come "allora passa alle 21:15". Segnalato dal campo, ed era
        l'unica lettura ragionevole: avevo messo un orario di evento nel posto
        dell'orologio.

        Adesso il posto grande lo prende il **conto alla rovescia**, che e'
        anche l'unica cosa che serve davvero in quel momento, e l'ora scende
        sulla riga piccola con l'etichetta `SORGE` davanti, dove non puo'
        essere scambiata per altro.

        La quarta informazione -- la durata -- prima non c'era apposta, per
        non affollare una riga che si legge da tre metri. Ci torna perche'
        decide se vale la pena uscire, e perche' e' quella **visibile**: vedi
        `durata_visibile`.
        """
        L, A = self.width, self.height
        img = Image.new("RGB", (L, A), (0, 0, 0))
        d = ImageDraw.Draw(img)
        nome = passaggio.get("breve", passaggio["nome"])[:12]
        conto = self.t("satelliti.in", None, min=max(0, mancano))

        # I nomi corti stanno tutti, ma `breve` arriva fino a dodici caratteri
        # e in inglese il conto e' piu' lungo. Invece di fidarsi, si misura: se
        # le due parole si toccherebbero, il conto scende di corpo. Meglio un
        # numero piu' piccolo che due parole sovrapposte.
        font_conto = self._font_grande
        if (self._larghezza(d, nome, self._font_grande)
                + self._larghezza(d, conto, font_conto) + 14 > L):
            font_conto = self._font_medio

        # Allineati sulla linea di base e non sul bordo superiore: con due
        # corpi diversi il pareggio in alto si vede storto.
        base = int(A * 0.02) + self._font_grande.getmetrics()[0]
        self._testo(d, 4, base, nome, self._font_grande, VERDE, ancora="ls")
        self._testo(d, L - 4, base, conto, font_conto, VERDE, ancora="rs")

        sorge = self.t("satelliti.rises", None,
                       time=passaggio["sorge"].astimezone().strftime("%H:%M"))
        self._testo(d, 4, int(A * 0.66), sorge, self._font_piccolo, VERDE_CUPO)
        dove = "%s  %d°  %s" % (
            bussola(passaggio["azimut_sorge"]),
            round(passaggio["elevazione_massima"]),
            self.durata_breve(self.durata_visibile(passaggio)))
        self._testo(d, L - 4, int(A * 0.66), dove, self._font_piccolo,
                    VERDE_CUPO, ancora="ra")
        return img

    def _adesso(self, passaggio, quando, acceso, visibile=True):
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

        testo_primo = BIANCO if visibile else SPENTO
        testo_sotto = GRIGIO if visibile else SPENTO_CUPO
        colore_arco = ARCO if visibile else ARCO_SPENTO
        colore_punto = PUNTO if visibile else SPENTO

        nome = passaggio.get("breve", passaggio["nome"])[:8]
        self._testo(d, 4, int(A * 0.01), nome, self._font_grande, testo_primo)
        if acceso:
            self._testo(d, 4, int(A * 0.47),
                        quando.astimezone().strftime("%H:%M"),
                        self._font_medio, testo_primo)
        if visibile:
            sotto = "ALT %d°" % round(vista["elevazione"])
            spegne = passaggio.get("spegnimento")
            if spegne is not None and quando <= spegne:
                # Negli ultimi secondi prima che sparisca, il pannello smette
                # di dire quanto e' alta e dice quello che sta per succedere.
                if (spegne - quando).total_seconds() <= 45:
                    sotto = "SPARISCE %s" % spegne.astimezone().strftime("%H:%M")
        else:
            # Perche' non si vede: quasi sempre perche' c'e' ancora il Sole.
            lat_s, lon_s = self._coordinate()
            alt_sole = satelliti.elevazione_sole(quando, lat_s, lon_s)
            sotto = ("SOLE %+d°" % round(alt_sole)) if alt_sole > -6 \
                else "IN OMBRA"
        self._testo(d, 4, int(A * 0.73), sotto, self._font_piccolo, testo_sotto)

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
        spegne = passaggio.get("spegnimento") if visibile else None
        if len(punti) > 1 and spegne is not None:
            # L'arco si disegna in due pezzi: fino allo spegnimento com'e', da
            # li' in poi in tono minore. Non e' decorazione -- dice che da quel
            # punto non c'e' piu' niente da guardare.
            quota_sp = (spegne - passaggio["sorge"]).total_seconds() / max(durata, 1.0)
            taglio = min(max(quota_sp, 0.0), 1.0)
            i_taglio = max(1, min(len(punti) - 1, int(round(taglio * (len(punti) - 1)))))
            d.line(punti[:i_taglio + 1], fill=colore_arco, width=1)
            d.line(punti[i_taglio:], fill=SPENTO_CUPO, width=1)
            xs = punti[i_taglio][0]
            d.line([(xs, cima - 2), (xs, base)], fill=OMBRA)
        elif len(punti) > 1:
            d.line(punti, fill=colore_arco, width=1)

        fatto = (quando - passaggio["sorge"]).total_seconds() / max(durata, 1.0)
        fatto = min(max(fatto, 0.0), 1.0)
        px = x0 + (x1 - x0) * fatto
        py = base - (base - cima) * max(0.0, vista["elevazione"]) / massima
        d.line([(px, base), (px, py)], fill=(0x22, 0x30, 0x48))
        d.ellipse([px - 2, py - 2, px + 2, py + 2], fill=colore_punto)

        self._testo(d, x0 - 4, base + 2, bussola(passaggio["azimut_sorge"]),
                    self._font_piccolo, testo_sotto)
        self._testo(d, x1 + 4, base + 2, bussola(passaggio["azimut_tramonta"]),
                    self._font_piccolo, testo_sotto, ancora="ra")
        return img
