# -*- coding: utf-8 -*-
"""OnAir: il pannello dice che si sta registrando.

Che cosa fa
-----------
Quando la porta dello studio si chiude, sul pannello compare **ON AIR** --
fondo rosso, lettere nere, ferme -- e da quel momento l'orologio porta un
trattino rosso in alto. La scritta ricompare ogni due contenuti del Media
Player, cosi' chi entra in soggiorno lo scopre anche se non era li' al
momento della chiusura. Quando la porta si riapre sparisce tutto.

Il DMD non sa che esiste una porta
----------------------------------
Sa solo se e' in onda, e lo chiede con un interruttore. Il sensore lo sceglie
Home Assistant, con un'automazione di tre righe, e questa e' la ragione per
cui il servizio si chiama OnAir e non «sensore porta»: domani il segnale
potra' venire da un pulsante, da un orario o da un mixer audio senza che qui
cambi niente.

L'interruttore ha anche il pregio di essere **comandabile a mano** -- dalla
pagina, da Home Assistant, e via HomeKit anche a voce -- il che rende OnAir
usabile subito, prima ancora di saldare qualcosa.

Perche' e' educato
------------------
Priorita' 52: appena sopra il Media Player (50) e la telecamera (51), sotto
il meteo (54) e tutto il resto. Quando tocca a lui vince la sua fetta di
rotazione, ma un aereo di passaggio o un compleanno gli passano davanti, e
soprattutto **non interrompe una partita**: chi sta giocando la porta l'ha
chiusa lui, e non ha bisogno che glielo si ricordi a meta' di un livello di
Doom. Per lo stesso motivo non riaccende un pannello spento e non scavalca lo
Sleep: la sveglia e' l'unica che ha il diritto di svegliare.

Il campanello suona **una volta sola**, alla chiusura. Un suono a ogni
ricomparsa vorrebbe dire un din-don ogni due minuti per tutta la durata della
diretta: una spia annuncia il cambio di stato, non lo stato.

Il tetto di tempo
-----------------
«Ogni due media» da solo non basta, e il caso si vede solo usandolo: se il
Media Player e' acceso ma non passa niente -- libreria vuota, fascia oraria,
Night mode -- il contatore non avanza e la scritta non compare mai, proprio
mentre la vorresti. Per questo c'e' anche `al_massimo_dopo`: passato quello,
si compare comunque.
"""

import random
import threading
import time

from PIL import Image, ImageDraw

from . import testo as impaginazione
from .base import Source
from .clock import parse_color

# Appena sopra il Media Player (50) e la telecamera (51), sotto il meteo (54).
# Nessuna priorita' pareggia con un'altra: e' la regola di casa.
PRIORITA = 52

# Il trattino sull'orologio: quanto largo e quanto alto, in pixel. Corto e
# centrato in cima, dalla parte opposta della barra del timer, che sta in
# fondo ed e' lunga: due segnali che non si possono confondere.
TRATTO_LARGO = 32
TRATTO_ALTO = 2

# Il margine che il testo lascia ai bordi del pannello.
MARGINE = 3

TESTO_PREDEFINITO = "ON AIR"
COLORE_SFONDO = "#c00000"
COLORE_TESTO = "#000000"


def conf_predefinita():
    return {
        "testo": TESTO_PREDEFINITO,
        "colore_sfondo": COLORE_SFONDO,
        "colore_testo": COLORE_TESTO,
        # Ogni quanti contenuti del Media Player si ricompare.
        "ogni_n_media": 2,
        # Il tetto di tempo, in secondi: se i media non passano, si compare
        # lo stesso. Zero disattiva il tetto.
        "al_massimo_dopo": 180,
        # Quanto resta a schermo. Zero vuol dire "quanto una foto", cioe'
        # `mediaplayer.image_duration`: entra nella rotazione senza sembrare
        # un corpo estraneo.
        "secondi": 0,
        # Lo stato: in onda o no. Sta in configurazione e non in memoria
        # perche' deve sopravvivere a un riavvio del servizio -- e perche'
        # l'interruttore di Home Assistant deve ritrovarlo dov'era.
        "in_onda": False,
    }


def normalizza(conf):
    """La configurazione con tutti i campi a posto, comunque sia scritta."""
    base = conf_predefinita()
    if not isinstance(conf, dict):
        return base
    base["testo"] = str(conf.get("testo") or TESTO_PREDEFINITO).strip()[:60] \
        or TESTO_PREDEFINITO
    base["colore_sfondo"] = str(conf.get("colore_sfondo") or COLORE_SFONDO)
    base["colore_testo"] = str(conf.get("colore_testo") or COLORE_TESTO)
    for chiave, minimo, massimo in (("ogni_n_media", 1, 50),
                                    ("al_massimo_dopo", 0, 3600),
                                    ("secondi", 0, 120)):
        try:
            base[chiave] = max(minimo, min(massimo, int(conf.get(chiave,
                                                                 base[chiave]))))
        except (TypeError, ValueError):
            pass
    base["in_onda"] = bool(conf.get("in_onda"))
    return base


class OnAirSource(Source):
    name = "onair"
    label = "OnAir"
    priority = PRIORITA

    def __init__(self, cfg, width, height):
        super().__init__(cfg, width, height)
        self._running = False
        self._thread = None
        self._sveglia = threading.Event()

        self._lock = threading.Lock()
        self._image = None
        self._dirty = False
        self._showing = False

        self._mostrate = 0
        self._da = 0.0            # da quando siamo in onda (monotonic)
        self._ultima = 0.0        # ultima comparsa (monotonic)
        self._ultimo_conteggio = 0
        self._subito = False      # la comparsa d'obbligo alla chiusura
        self._prossima_attesa = 0.0

        # Il Media Player, attaccato dal runtime: serve solo a leggergli il
        # contatore dei contenuti mostrati. Stessa strada che usa Now Playing
        # per la sua rotazione -- il contatore esiste gia', inventarne un
        # secondo vorrebbe dire due numeri che si rincorrono.
        self.media = None
        # Chi sa suonare il campanello. Lo attacca il runtime, come per la
        # sveglia e per le notifiche: qui non si sa com'e' fatto l'audio.
        self.suona = None

    # ------------------------------------------------------------ impostazioni

    def conf(self):
        return normalizza(self.cfg.get("onair"))

    def _durata(self):
        secondi = self.conf()["secondi"]
        if secondi:
            return secondi
        try:
            return max(2, int((self.cfg.get("mediaplayer") or {})
                              .get("image_duration", 5)))
        except (TypeError, ValueError):
            return 5

    # ------------------------------------------------------------ ciclo vita

    def start(self):
        if self._running:
            return
        self._running = True
        self._sveglia.clear()
        # Se il servizio si riavvia mentre la porta e' chiusa, si riparte in
        # onda: lo stato sta in configurazione apposta. Home Assistant lo
        # riafferma comunque appena il DMD torna disponibile, cosi' una porta
        # aperta nel frattempo non lascia acceso un ON AIR falso.
        if self.in_onda():
            self._da = time.monotonic()
            self._subito = True
        self._thread = threading.Thread(target=self._loop, name="onair",
                                        daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._showing = False
        self._sveglia.set()
        with self._lock:
            self._image = None
            self._dirty = False

    # ------------------------------------------------------------ lo stato

    def in_onda(self):
        """Vero se la porta e' chiusa, cioe' se siamo in diretta."""
        return bool((self.cfg.get("onair") or {}).get("in_onda"))

    def imposta(self, acceso, salva=True):
        """Accende o spegne la diretta. Restituisce True se e' cambiato.

        La chiamano l'interruttore di Home Assistant, la pagina web e -- il
        giorno che servira' -- qualunque altra cosa. Il campanello suona solo
        al **passaggio** da spento ad acceso: e' una spia, annuncia il cambio
        di stato e non lo stato.
        """
        acceso = bool(acceso)
        conf = self.cfg.setdefault("onair", conf_predefinita())
        prima = bool(conf.get("in_onda"))
        conf["in_onda"] = acceso
        if salva:
            try:
                import dmdconf
                dmdconf.save()
            except Exception as exc:          # pragma: no cover
                print("[onair] stato non salvato: %s" % exc)
        if acceso == prima:
            return False
        if acceso:
            self._da = time.monotonic()
            self._ultima = 0.0
            self._ultimo_conteggio = self._conteggio_media()
            self._prossima_attesa = 0.0
            # La comparsa d'obbligo: la scritta si vede **subito**, non al
            # prossimo giro dei media. Chi chiude la porta si aspetta una
            # conferma, e aspettarla due minuti vale come non averla.
            self._subito = True
            self._campanello()
        else:
            self._subito = False
            self._showing = False
            self._da = 0.0
        self._sveglia.set()
        return True

    def _campanello(self):
        if self.suona is None:
            return
        try:
            self.suona()
        except Exception as exc:              # pragma: no cover
            print("[onair] suono non riprodotto: %s" % exc)

    def da_quanto(self):
        """Secondi dall'inizio della diretta, o 0 se non siamo in onda."""
        if not self._da or not self.in_onda():
            return 0
        return int(time.monotonic() - self._da)

    # ------------------------------------------------------------ arbitro

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
        if not self.in_onda():
            return self.t("status.onair.riposo", lang)
        if self._showing:
            return self.t("status.onair.schermo", lang,
                          text=self.conf()["testo"][:30])
        return self.t("status.onair.attivo", lang,
                      minuti=max(0, self.da_quanto() // 60),
                      shown=self._mostrate)

    # ------------------------------------------------------------ cadenza

    def _conteggio_media(self):
        try:
            return int(getattr(self.media, "_shown", 0))
        except (TypeError, ValueError):       # pragma: no cover
            return 0

    def _media_acceso(self):
        return bool(getattr(self.media, "enabled", False))

    def _intervallo(self):
        """L'attesa fra una comparsa e l'altra quando i media sono spenti.

        Si prendono i tempi del Media Player invece di inventarne di nuovi:
        la richiesta era «con le regole di timing di media», e due manopole
        che dicono la stessa cosa sono una manopola di troppo.
        """
        conf = self.cfg.get("mediaplayer") or {}
        try:
            basso = max(3, int(conf.get("min_interval", 20)))
            alto = max(basso, int(conf.get("max_interval", 30)))
        except (TypeError, ValueError):       # pragma: no cover
            basso, alto = 20, 30
        return random.uniform(basso, alto)

    def _tocca(self):
        """Vero se e' il momento di far comparire la scritta."""
        if self._subito:
            self._subito = False
            return True
        adesso = time.monotonic()
        conf = self.conf()
        tetto = conf["al_massimo_dopo"]
        if self._media_acceso():
            passati = self._conteggio_media()
            if passati - self._ultimo_conteggio >= conf["ogni_n_media"]:
                return True
            # Il tetto di tempo esiste per il caso in cui i media sono accesi
            # e non passa niente: libreria vuota, fascia oraria, Night mode.
            # Senza, la scritta non comparirebbe mai proprio quando serve.
            return bool(tetto) and self._ultima and adesso - self._ultima >= tetto
        if not self._prossima_attesa:
            self._prossima_attesa = self._intervallo()
        return adesso - self._ultima >= self._prossima_attesa

    # ------------------------------------------------------------ ciclo

    def _loop(self):
        while self._running:
            self._sveglia.wait(0.5)
            self._sveglia.clear()
            if not self._running:
                return
            if not self.in_onda():
                self._showing = False
                continue
            if not self._tocca():
                continue
            try:
                self._mostra()
            except Exception as exc:          # pragma: no cover
                print("[onair] errore: %s" % exc)
            finally:
                self._showing = False

    def _mostra(self):
        conf = self.conf()
        tela = self.tela(conf["testo"], conf)
        self._pubblica(tela)
        self._showing = True
        self._mostrate += 1
        self._ultima = time.monotonic()
        self._ultimo_conteggio = self._conteggio_media()
        self._prossima_attesa = 0.0
        scadenza = time.time() + self._durata()
        while self._running and self.in_onda() and time.time() < scadenza:
            time.sleep(0.05)

    def _pubblica(self, immagine):
        with self._lock:
            self._image = immagine
            self._dirty = True

    # ------------------------------------------------------------ resa

    def tela(self, parole, conf=None):
        """Il fotogramma: fondo pieno e la scritta ferma al centro.

        Nessun bordo e nessun lampeggio. Il fondo pieno e' gia' il segnale
        piu' forte che questo pannello sappia fare, e una scritta che
        lampeggia mentre qualcuno registra e' esattamente la cosa che non
        vuoi vedere con la coda dell'occhio.
        """
        conf = conf or self.conf()
        sfondo = parse_color(conf["colore_sfondo"], (0xC0, 0, 0))
        inchiostro = parse_color(conf["colore_testo"], (0, 0, 0))
        righe, font = impaginazione.impagina(
            parole,
            larghezza=self.width - 2 * MARGINE,
            altezza=self.height - 2 * MARGINE,
            tetto=self.height)
        tela = Image.new("RGB", (self.width, self.height), sfondo)
        disegna = ImageDraw.Draw(tela)
        impaginazione.scrivi_centrato(disegna, righe, font,
                                      self.width, self.height, inchiostro,
                                      margine=MARGINE)
        return tela
