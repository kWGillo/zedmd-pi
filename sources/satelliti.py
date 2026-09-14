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
        # Il cancello si dice, non si subisce. Un servizio acceso che non
        # mostra niente e non spiega perche' sembra rotto, ed e' la ragione per
        # cui questa riga esiste: «in attesa del tramonto» e' un'informazione,
        # il silenzio no.
        coda = ""
        if not self.e_notte():
            lat, lon = self._coordinate()
            alto = (satelliti.elevazione_sole(datetime.now(timezone.utc),
                                              lat, lon)
                    if lat is not None else 0.0)
            coda = " · " + self.t("satelliti.attesa.buio", lang,
                                  sole=int(round(alto)),
                                  soglia=int(round(self.sole_massimo())))
        if prossimo is None:
            return self.t("status.satelliti.none", lang) + coda
        quando = prossimo["sorge"].astimezone()
        return self.t("status.satelliti.next", lang,
                      name=prossimo.get("breve", prossimo["nome"]),
                      time=quando.strftime("%H:%M"),
                      elev=int(round(prossimo["elevazione_massima"]))) + coda

    def _conf(self):
        return self.cfg.get("satelliti", {})

    def sole_massimo(self):
        """Quanto in alto puo' stare il Sole perche' il pannello parli ancora.

        In gradi sopra l'orizzonte: a `3` il servizio si apre un quarto d'ora
        prima del tramonto, a `0` esattamente al tramonto, a `90` non si chiude
        mai -- che e' il comportamento di prima della 7.2.
        """
        try:
            return float(self._conf().get("sole_massimo", 3.0))
        except (TypeError, ValueError):
            return 3.0

    def e_notte(self, adesso=None):
        """Vero se il pannello puo' mostrare i satelliti, adesso.

        **Perche' la soglia non e' quella della visibilita'.** Verrebbe
        naturale riusare i −6 gradi con cui si decide se un passaggio si vede,
        e sarebbe un difetto: il preavviso scatta dieci minuti prima che il
        satellite sorga, e in dieci minuti il Sole scende di due o tre gradi.
        Un passaggio che diventa visibile appena sotto i −6 avrebbe il suo
        preavviso soppresso, perche' dieci minuti prima il Sole stava a −3 --
        cioe' proprio l'avviso della prima sera, quello piu' comodo, sparirebbe
        e nessuno saprebbe dire perche'.

        Quindi il cancello sta **piu' in alto** della visibilita', con il
        margine dalla parte giusta: si apre presto e lascia che sia la
        visibilita' vera a decidere se c'e' qualcosa da dire.
        """
        soglia = self.sole_massimo()
        if soglia >= 90.0:
            return True
        lat, lon = self._coordinate()
        if lat is None:
            # Senza coordinate non si sa dove sia il Sole. Il servizio non ha
            # comunque niente da dire, e questo non e' il posto per decidere
            # perche': si lascia passare e ci pensa chi cerca i passaggi.
            return True
        adesso = adesso or datetime.now(timezone.utc)
        return satelliti.elevazione_sole(adesso, lat, lon) <= soglia

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

    # ------------------------------------------------------- per Home Assistant

    def riepilogo(self, ore=24):
        """I passaggi delle prossime ore, in forma pubblicabile.

        Senza l'oggetto orbitale, che non e' serializzabile e non serve a
        nessuno di la'. Con **tutti** i passaggi e non solo i visibili: chi
        costruisce un'automazione decide da se', e la differenza e' scritta
        in ogni voce.

        E' la risposta a una richiesta precisa: sapere dei passaggi **anche
        con un giorno di anticipo**, non solo dieci minuti prima. Il calcolo
        c'e' gia' -- la finestra e' di ventiquattro ore -- mancava solo il
        modo di guardarlo da fuori.
        """
        adesso = datetime.now(timezone.utc)
        limite = adesso + timedelta(hours=max(1, int(ore)))
        fuori = []
        for p in self._passaggi:
            if p["tramonta"] < adesso or p["sorge"] > limite:
                continue
            spegnimento = p.get("spegnimento")
            fuori.append({
                "nome": p.get("breve") or p["nome"],
                "norad": p.get("norad"),
                "sorge": p["sorge"].astimezone().isoformat(),
                "culmine": p["culmine"].astimezone().isoformat(),
                "tramonta": p["tramonta"].astimezone().isoformat(),
                "durata_min": round(p["durata_min"], 1),
                "durata_visibile_s": int(round(self.durata_visibile(p))),
                "elevazione_massima": int(round(p["elevazione_massima"])),
                "da": bussola(p.get("azimut_sorge")),
                "a": bussola(p.get("azimut_tramonta")),
                "visibile": bool(p.get("visibile")),
                "sparisce": (spegnimento.astimezone().isoformat()
                             if spegnimento else None),
            })
        return fuori

    # ------------------------------------------------------------------ ciclo

    def _loop(self):
        while self._running:
            # Tre passi separati, e tre reti separate. Prima erano dentro un
            # unico `try`: un errore nello scaricamento o nella scrittura del
            # registro -- due cose che non riguardano il vetro -- saltava il
            # disegno, e il pannello restava fermo sull'ultimo fotogramma senza
            # che niente lo dicesse.
            for passo in (self._aggiorna_dati,
                          lambda: self._registra_conclusi(
                              datetime.now(timezone.utc)),
                          self._disegna_se_serve):
                try:
                    passo()
                except Exception as exc:      # noqa: BLE001
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
        # Dalla 7.0 la posizione non e' piu' una voce del radar ma del
        # progetto: la usano in tre, e cercarla nella pagina del radar era il
        # modo piu' rapido per non trovarla.
        import dmdconf
        dove = dmdconf.posizione(self.cfg)
        return dove if dove is not None else (None, None)

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
        # Il cancello sul buio sta **qui** e non piu' in su, ed e' voluto: i
        # due passi precedenti del ciclo -- calcolare i passaggi e scrivere il
        # registro -- continuano anche di giorno.
        #
        # Se si fermasse tutto, al tramonto il servizio si sveglierebbe senza
        # sapere niente e perderebbe il primo passaggio della sera, che e'
        # proprio quello per cui esiste. E la pagina Satelliti deve poter
        # rispondere alle nove del mattino alla domanda "quando passa stasera".
        # Il filtro e' una scelta di cosa **mostrare**, non di cosa **sapere**.
        if not self.e_notte(adesso):
            self._stato = ""
            return
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
        secondi_mancanti = (passaggio["sorge"] - adesso).total_seconds()
        mancano = int(round(secondi_mancanti / 60.0))
        # Cintura di sicurezza, chiesta dal campo: un conto alla rovescia su
        # un passaggio gia' sorto e' una bugia, e sul vetro una bugia non si
        # distingue da un guasto. Lo stato "avviso" non dovrebbe mai arrivare
        # qui con l'ora passata -- ci pensa `satelliti.stato` -- ma se un
        # giorno ci arrivasse, meglio niente che "fra 5 min" accanto a
        # "sorge 22:48" quando sono le 22:49.
        if stato == "avviso" and secondi_mancanti <= 0:
            self._stato = ""
            return
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

        try:
            if stato == "adesso":
                img = self._adesso(passaggio, adesso, acceso)
            elif stato == "spento":
                # L'ora non lampeggia: non sta succedendo niente che tu possa
                # vedere, e un lampeggio direbbe il contrario.
                img = self._adesso(passaggio, adesso, True, visibile=False)
            else:
                img = self._avviso(passaggio, mancano)
        except Exception as exc:              # noqa: BLE001
            # **Un disegno che fallisce deve mollare il pannello.** E' la
            # lezione di una fotografia: alle 22:49:17 il pannello mostrava il
            # promemoria "fra 5 minuti" di un passaggio sorto alle 22:48:06.
            # Non era il conto alla rovescia sbagliato: era un fotogramma di
            # sei minuti prima, rimasto li'. La sorgente aveva gia' scritto
            # `_stato = "adesso"`, il disegno sollevava `KeyError: 'sat'`, e
            # con lo stato acceso continuava a dichiararsi attiva: nessun'altra
            # sorgente poteva prendere il posto, e l'ultimo fotogramma buono
            # restava congelato sul vetro.
            # Chi non riesce a disegnare non ha diritto di occupare lo schermo.
            self._stato = ""
            self._ultima_firma = None
            self._errore = "disegno: %s" % exc
            print("[satelliti] disegno fallito, pannello rilasciato: %s" % exc)
            return
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

    def _nome_che_entra(self, d, nome, disponibile):
        """Il nome del satellite e il corpo con cui ci sta. Torna (testo, font).

        Segnalato dal campo con una foto: `OKEAN-O` scritto a corpo pieno
        finiva **sopra l'arco**. Il difetto era vecchio quanto la funzione e non
        si era mai visto, perche' l'unico nome mai comparso era `ISS` -- tre
        caratteri, che ci stanno ovunque. E' bastato accendere «tutti gli
        oggetti» perche' saltasse fuori.

        La lezione e' sempre la stessa: il troncamento a otto caratteri che
        c'era prima non e' una misura, e' una speranza. Otto caratteri stretti
        e otto larghi occupano larghezze diverse, e su un pannello non c'e'
        margine per sbagliare. Qui si misura davvero: prima si prova a
        rimpicciolire il corpo -- un nome piccolo si legge ancora -- e solo
        all'ultimo si taglia, perche' un nome tagliato e' un nome che non si
        riconosce.
        """
        nome = (nome or "").strip()
        for font in (self._font_grande, self._font_medio, self._font_piccolo):
            if self._larghezza(d, nome, font) <= disponibile:
                return nome, font
        # Quando si taglia, si dice che si e' tagliato. `SPACEMOBILE-00` e'
        # un nome plausibile e sbagliato; `SPACEMOBILE-0…` e' un nome
        # incompleto, e si vede. Su un pannello che serve a far riconoscere
        # una cosa in cielo, la differenza conta.
        font = self._font_piccolo
        accorciato = nome
        while accorciato and self._larghezza(d, accorciato + "…",
                                             font) > disponibile:
            accorciato = accorciato[:-1]
        return (accorciato.rstrip() + "…") if accorciato else "", font

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
        conto = self.t("satelliti.in", None, min=max(0, mancano))

        # Il conto alla rovescia e' la cosa che serve davvero in questo
        # momento, quindi si prende lo spazio per primo e il nome si adatta a
        # quello che resta. Prima era il contrario -- nome a corpo pieno e
        # conto rimpicciolito -- e con un nome lungo si rimpiccioliva la cosa
        # importante per far posto a quella di contorno.
        font_conto = self._font_grande
        largo_conto = self._larghezza(d, conto, font_conto)
        nome, font_nome = self._nome_che_entra(
            d, passaggio.get("breve", passaggio["nome"]),
            L - largo_conto - 18)

        # Allineati sulla linea di base e non sul bordo superiore: con due
        # corpi diversi il pareggio in alto si vede storto.
        base = int(A * 0.02) + self._font_grande.getmetrics()[0]
        self._testo(d, 4, base, nome, font_nome, VERDE, ancora="ls")
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

        # Lo spazio del nome finisce dove comincia l'arco, e l'arco comincia a
        # `L * 0.41`. Il valore si ricava da li' invece di essere scritto due
        # volte: se un giorno l'arco si sposta, il nome lo segue da solo.
        x0_arco = int(L * 0.41)
        nome, font_nome = self._nome_che_entra(
            d, passaggio.get("breve", passaggio["nome"]), x0_arco - 10)
        self._testo(d, 4, int(A * 0.01), nome, font_nome, testo_primo)
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

        x0, x1 = x0_arco, L - int(L * 0.06)
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
