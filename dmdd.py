#!/usr/bin/env python3
"""Servizio principale del DMD.

Un solo processo possiede il pannello. Dentro ci sono le sorgenti
(ZeDMD, Media Player, orologio, in futuro aerei e punteggi) e un arbitro
che decide chi va sullo schermo, con prelazione e tempo di grazia.

Sopra a tutto agiscono due fasce orarie: Night mode abbassa la luminosita',
Sleep mode spegne il display. Sleep ha la precedenza su Night.

Avvio manuale:  sudo python3 /opt/dmd/dmdd.py
Come servizio:  systemctl start dmd
"""

import os
import signal
import sys
import threading
import time

import dmdconf
import fasce
import hass
import libcheck
import metadati
import mqttbus
import nowplaying
import ota
import pulizia
import pulsante
import spotifyapi
import cassa
import suoni
from display import Display
from sources import (AirRadarSource, BannerSource, BirthdaysSource,
                     CalendarioSource, CieloSource, ClockSource, DoomSource, GameBoySource,
                     GiochiSource, InutiliSource, MediaPlayerSource, MeteoSource,
                     NowPlayingSource,
                     NotificheSource, OnAirSource, PreviewSource,
                     SatellitiSource,
                     ScadenzeSource, SvegliaSource,
                     TelecameraSource,
                     ZeDMDSource, controlla_rom, controlla_wad)
from sources.turni import Turni
from version import __version__
from zedmd_http import ZeDMDHttpServer

# 30 fps: sufficienti per un DMD e lasciano CPU al ricevitore ZeDMD,
# che non deve mai risultare lento al client (altrimenti scarta frame).
FPS = 30


# La regola delle fasce sta in fasce.py, dove la raggiungono anche le
# sorgenti: qui restano i nomi di sempre, cosi' il resto del file e chi li
# importa non si accorgono dello spostamento.
parse_hhmm = fasce.parse_hhmm
in_window = fasce.in_window


def modi_effettivi(sleeping, spento, night, squilla):
    """Le tre fasce dopo che la sveglia ha detto la sua. (dorme, spento, notte).

    Sta fuori dalla classe per una ragione sola: **una regola che si puo'
    chiamare si puo' anche provare.** Dentro `_update_modes` sarebbe rimasta
    in mezzo alla lettura dell'orologio e al calcolo della luminosita', e
    l'unico modo di verificarla sarebbe stato mettere una sveglia vera e
    aspettare le sette.

    La regola in se' e' di una riga: mentre la sveglia squilla non c'e'
    nessuna fascia. Non dorme, non e' spento, e la luminosita' torna quella di
    giorno -- una sveglia che si vede al quindici per cento e' mezza sveglia.
    """
    if not squilla:
        return (sleeping, spento, night)
    return (False, False, False)


# Quanto dura la gestione media senza notizie dal browser. La pagina manda un
# battito ogni dieci secondi: se ne saltano tre, la scheda e' stata chiusa (o
# il wifi e' caduto) e il pannello deve tornare al suo lavoro da solo.
MANAGER_TIMEOUT = 30


class Arbiter:
    """Sceglie quale sorgente ha diritto al display in questo istante."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.sources = {}
        self.current = None
        # Presa del pannello: il nome della sorgente che se l'e' preso, e fino
        # a quando. Nata per la gestione media, serve identica a una sessione
        # di Doom — sono la stessa cosa, "questa cosa qui tiene il pannello
        # finche' non ha finito".
        #
        # Due sapori. **A scadenza** (gestione media): la pagina web manda un
        # battito e se tace la presa cade da sola, cosi' una scheda chiusa non
        # lascia il pannello fermo per sempre. **Senza scadenza** (Doom): chi
        # gioca puo' stare fermo a guardare una porta senza che il pannello
        # gli torni all'orologio, e a chiudere ci pensa la sorgente.
        self.hold_name = ""
        self.hold_until = 0.0

    def register(self, source):
        self.sources[source.name] = source

    def apply_services(self):
        """Allinea lo stato di avvio delle sorgenti ai toggle di configurazione."""
        services = self.cfg["services"]
        for name, source in self.sources.items():
            # Una sorgente che non compare fra i servizi non si accende e non
            # si spegne: e' sempre disponibile. E' il caso dell'anteprima, che
            # non fa niente finche' nessuno la chiama e non ha senso come
            # interruttore in una pagina.
            if name not in services:
                continue
            wanted = bool(services.get(name, False)) and self.consentito(name)
            if wanted and not source.enabled:
                source.enabled = True
                source.start()
            elif not wanted and source.enabled:
                source.enabled = False
                source.stop()

    def consentito(self, name):
        """La fascia oraria del servizio, se ne ha una.

        Sta qui e non nel ciclo di rendering perche' l'interruttore e la
        fascia sono la stessa domanda — *questo servizio deve lavorare
        adesso?* — e chiunque chiami apply_services (la pagina web, Home
        Assistant, l'avvio) deve ottenere la stessa risposta. La differenza
        e' che l'interruttore lo gira una persona e la fascia scade da sola,
        quindi il ciclo richiama apply_services una volta al secondo: e'
        idempotente, agisce solo quando lo stato cambia davvero.

        Dalla 8.1 la fascia ce l'hanno **tutti** i servizi, non solo il Media
        Player, e questa riga e' rimasta una sola: era gia' il cancello unico,
        bastava generalizzare la regola invece di aggiungerne un'altra.
        """
        return fasce.consentito(self.cfg, name)

    # ------------------------------------------------------- presa del pannello

    def holding(self, name=None):
        if not self.hold_name:
            return False
        if self.hold_until and time.time() >= self.hold_until:
            return False
        return name is None or self.hold_name == name

    def hold_on(self, name, seconds=None):
        """Assegna il pannello a una sorgente. `seconds=None` = senza scadenza."""
        self.hold_name = name
        self.hold_until = time.time() + seconds if seconds else 0.0

    def hold_off(self, name=None):
        """Rilascia la presa. Con un nome, solo se e' di quella sorgente.

        Il nome serve a non far chiudere a una pagina la presa di un'altra:
        uscendo dalla gestione media mentre qualcuno gioca a Doom, il gioco
        non si deve spegnere.
        """
        if name is not None and self.hold_name != name:
            return False
        self.hold_name = ""
        self.hold_until = 0.0
        return True

    def hold_left(self):
        """Secondi che mancano al rilascio automatico, per la web UI."""
        if not self.hold_until:
            return 0
        return max(0, int(self.hold_until - time.time()))

    # La gestione media e' il primo cliente della presa, e la web UI la
    # chiama con il suo nome: questi tre nomi restano quelli.
    def manager(self):
        return self.holding("preview")

    def manager_on(self):
        self.hold_on("preview", MANAGER_TIMEOUT)

    def manager_off(self):
        return self.hold_off("preview")

    def manager_left(self):
        return self.hold_left() if self.manager() else 0

    def pick(self):
        # Chi ha preso il pannello lo tiene, e non c'e' nessuna gara di
        # priorita' da vincere: le sorgenti restano accese e continuano a
        # lavorare, semplicemente non vanno a schermo. Nemmeno ZeDMD —
        # sospendere tutto tranne uno vuol dire che con una partita aperta le
        # anteprime non si vedrebbero mai, e che una sessione di Doom
        # sparirebbe appena Batocera manda un fotogramma.
        if self.holding():
            preso = self.sources.get(self.hold_name)
            if preso is not None:
                return preso
            # La sorgente non c'e' piu': meglio lasciar perdere la presa che
            # tenere il pannello nero in attesa di nessuno.
            self.hold_off()

        forced = self.cfg["arbiter"]["force_source"]
        if forced != "auto":
            source = self.sources.get(forced)
            if source and source.enabled:
                return source
            return None

        return self._migliore()

    def _migliore(self, escluso=None):
        best = None
        for source in self.sources.values():
            if source is escluso or not source.enabled or not source.active():
                continue
            if best is None or source.priority > best.priority:
                best = source
        return best


class Runtime:
    """Stato condiviso tra il ciclo di rendering e la web UI."""

    def __init__(self):
        self.cfg = dmdconf.get()
        self.display = Display(self.cfg)
        self.arbiter = Arbiter(self.cfg)

        self.zedmd = ZeDMDSource(
            self.cfg,
            self.display.width,
            self.display.height,
            on_brightness=self.set_brightness,
        )
        self.media = MediaPlayerSource(self.cfg, self.display.width, self.display.height)
        self.banner = BannerSource(self.cfg, self.display.width, self.display.height)
        self.birthdays = BirthdaysSource(self.cfg, self.display.width,
                                         self.display.height)
        # L'anteprima ha la precedenza su tutto tranne ZeDMD: chi ha appena
        # premuto "Vedi" sta guardando il pannello adesso.
        self.preview = PreviewSource(self.cfg, self.display.width,
                                     self.display.height, self.media)
        self.radar = AirRadarSource(self.cfg, self.display.width, self.display.height)
        # I passaggi visibili della Stazione Spaziale. Priorita' 61, appena
        # sopra il radar: un passaggio ha un orario, un aereo no.
        self.satelliti = SatellitiSource(self.cfg, self.display.width,
                                         self.display.height)
        # Le notifiche da Home Assistant. Priorita' 70, sopra tutte le
        # sorgenti che "tornano" (radar, satelliti, foto) perche' una notifica
        # succede adesso o non succede piu'. Conosce l'arbitro come Doom e il
        # Game Boy: serve al solo livello `allarme`, l'unico che puo'
        # interrompere una partita.
        self.notifiche = NotificheSource(self.cfg, self.display.width,
                                         self.display.height)
        self.notifiche.arbiter = self.arbiter
        self.notifiche.suona = self._suona_notifica
        # OnAir. Priorita' 52, appena sopra il Media Player: quando tocca a
        # lui vince la sua fetta di rotazione, ma un aereo o un compleanno
        # gli passano davanti e una partita non la interrompe mai. Chi ha
        # chiuso la porta lo sa gia'.
        self.onair = OnAirSource(self.cfg, self.display.width,
                                 self.display.height)
        self.onair.suona = self._suona_onair
        # Il meteo. Priorita' 54, sotto il Rolling Banner: fra due cose non
        # urgenti ha la precedenza quella che una persona ha scritto apposta.
        self.meteo = MeteoSource(self.cfg, self.display.width,
                                 self.display.height)
        # Il Cielo. Priorita' 53, fra OnAir e il meteo. Non decide da solo
        # quando mostrarsi: lo decide il turno qui sotto, che lo alterna con
        # il meteo ogni due media. Gli serve il meteo per le nuvole della
        # serata buona, e lo si attacca qui come per gli altri.
        self.cielo = CieloSource(self.cfg, self.display.width,
                                 self.display.height)
        self.cielo.meteo = self.meteo
        # Info inutili. Priorita' 49: non se la gioca con nessuno, perche'
        # il pannello glielo da' il turno qui sotto, attaccato alla coda del
        # meteo -- «subito dopo il meteo stesso», come e' stato chiesto.
        self.inutili = InutiliSource(self.cfg, self.display.width,
                                     self.display.height)
        # Doom prende e restituisce il pannello da solo, quindi conosce
        # l'arbitro: e' l'unica sorgente che lo fa. Non e' un servizio e non
        # compare fra gli interruttori — `enabled` resta False per sempre — e
        # va a schermo solo quando ha la presa, cioe' solo durante una partita.
        self.doom = DoomSource(self.cfg, self.display.width,
                               self.display.height, self.arbiter)
        # Il Game Boy e' la terza partita: stessa presa del pannello, stesso
        # arbitro, stessa regola. Non e' un servizio.
        #
        # Si costruisce **prima** dei giochi, non dopo: la sorgente dei giochi
        # riceve qui sotto due funzioni che lo interrogano, e assegnarle prima
        # che l'oggetto esista faceva morire il servizio all'avvio. Sembrava
        # innocuo perche' quelle funzioni si chiamano solo dopo, ma
        # `self.gameboy.in_sessione` si valuta subito.
        self.gameboy = GameBoySource(self.cfg, self.display.width,
                                     self.display.height, self.arbiter)
        # Stessa storia per i giochi scritti per il pannello: partita, non
        # servizio. Prendono la presa allo stesso modo e con lo stesso arbitro.
        self.giochi = GiochiSource(self.cfg, self.display.width,
                                   self.display.height, self.arbiter)
        # Il giro dei giochi puo' comprendere Doom, ma la sorgente dei giochi
        # non deve conoscerlo: le si danno due funzioni e le basta.
        self.giochi.doom_pronto = lambda: not controlla_wad(
            self.cfg["doom"].get("wad", ""))
        # Le aperture che vengono dal giro portano `da_giro`: un Gioca scelto
        # a mano pochi istanti prima ha la precedenza su di loro (vedi gioca).
        self.giochi.apri_doom = lambda: self.gioca("doom", da_giro=True)
        # Anche aprire un gioco passa di qui: e' l'unico punto che sa che
        # Doom e i giochi si contendono la stessa presa del pannello.
        self.giochi.apri_partita = (
            lambda cosa, nome="": self.gioca(cosa, nome, da_giro=True))
        # Select esce da qualunque partita, Doom compreso.
        self.giochi.chiudi_partita = self.smetti
        # Il Game Boy entra nel giro come Doom: se PyBoy c'e' ed e' stata
        # scelta una cartuccia valida, il tasto Start lo raggiunge.
        self.giochi.gb_pronto = lambda: (
            self.gameboy.pronto()
            and not controlla_rom(self.cfg["gameboy"].get("rom", "")))
        self.giochi.apri_gameboy = lambda: self.gioca("gameboy", da_giro=True)
        # E mentre il Game Boy gioca, i pulsanti sono suoi: il lettore dei
        # giochi si fa da parte e tiene solo PS per uscire.
        # Lambda e non il metodo diretto: cosi' `self.gameboy` si legge quando
        # la funzione viene chiamata, non ora. Le altre due qui sopra lo erano
        # gia', e infatti non si erano rotte. Cintura e bretelle — l'ordine di
        # costruzione e' corretto — ma un cablaggio che dipende dall'ordine
        # delle righe e' una trappola per il prossimo che le sposta.
        self.giochi.esclusiva = lambda: self.gameboy.in_sessione()
        self.scadenze = ScadenzeSource(self.cfg, self.display.width,
                                       self.display.height)
        self.calendario = CalendarioSource(self.cfg, self.display.width,
                                           self.display.height)
        self.clock = ClockSource(self.cfg, self.display.width, self.display.height)
        self.telecamera = TelecameraSource(self.cfg, self.display.width,
                                           self.display.height)
        self.sveglia = SvegliaSource(self.cfg, self.display.width,
                                     self.display.height)
        # Chi suona, e chi si prende il pulsante. Gli stessi due ganci di
        # sempre: la sveglia non sa come e' fatto l'audio e la telecamera non
        # sa che esista una sveglia -- li mette in comunicazione il runtime,
        # che e' l'unico a conoscerle entrambe.
        self.sveglia.suona = self._suona_sveglia
        self.telecamera.intercetta = self.sveglia.zittisci
        # E l'orologio mostra in fondo quanto manca al timer: il timer si mette
        # da una pagina web, ma la pasta si guarda in cucina, e in cucina
        # l'unica cosa che si guarda e' il pannello.
        self.clock.timer = self.sveglia.timer_quota
        # Se ci sono partite congelate adesso. Serve ad agire solo sui cambi
        # di stato invece che a ogni giro del ciclo.
        self._partite_congelate = False
        # Il pulsante che la sveglia si apre da sola quando squilla e la
        # telecamera non lo sta gia' tenendo. Vedi `_pulsante_di_turno`.
        self._pulsante_sveglia = None

        # Il brano corrente e chi lo disegna sono due cose distinte: lo stato
        # viene aggiornato anche a servizio spento, cosi' Home Assistant lo
        # vede lo stesso e accendendo il player non si parte da zero.
        self.nowplaying = nowplaying.NowPlaying(self.cfg)
        self.player = NowPlayingSource(self.cfg, self.display.width,
                                       self.display.height, self.nowplaying)
        # Il Media Player, per la rotazione: Now Playing deve poter chiedere
        # quante foto sono passate. Il collegamento si fa qui e non dentro la
        # sorgente, come per l'arbitro delle notifiche: una sorgente non deve
        # sapere come si costruisce un'altra, solo chiederle un numero.
        self.player.media = self.media
        # Stessa strada per OnAir: gli serve solo sapere quante foto sono
        # passate, per ricomparire ogni due.
        self.onair.media = self.media
        # E l'orologio deve sapere se siamo in diretta, per il trattino
        # rosso in cima. Come per il timer: un si' o un no, niente di piu'.
        self.clock.onair = self._onair_in_onda
        # Stessa forma per il puntino verde della versione nuova: l'orologio
        # chiede, il runtime risponde, e nessuno dei due sa cosa sia GitHub.
        self.clock.aggiornamento = self._aggiornamento_disponibile
        self.mqtt = mqttbus.MqttBus(self.cfg)
        # Nasce qui e non in `_start_metadati` perche' `shutdown` la nomina:
        # un arresto che arriva mentre l'avvio e' ancora a meta' non deve
        # inciampare su un attributo che non esiste ancora.
        self.metadati = None
        self.spotify = spotifyapi.SpotifyPoller(self.cfg, self.nowplaying)
        self.hass = hass.HassBridge(self.cfg, self.mqtt, self)

        # Quando la musica esce dalla nostra scheda, la scheda e' di
        # shairport-sync: gli avvisi tacciono finche' dura il brano. Il
        # collegamento si fa qui perche' `suoni` non deve sapere che esiste
        # Now Playing, e Now Playing non deve sapere che esiste il suono.
        suoni.musica_in_corso = self._musica_in_corso
        # E la fascia notturna, con lo stesso patto: `suoni` non sa che cosa
        # sia il night mode, sa solo che ogni tanto deve abbassare la voce.
        # La fascia la calcola gia' `_update_modes` per la luminosita'.
        # `getattr` e non `self.night`: questa riga sta **prima** del punto in
        # cui l'attributo nasce, qualche decina di righe piu' in giu'. Oggi
        # nessuno la chiama cosi' presto, ma una riga che si rompe se qualcuno
        # sposta un blocco e' una trappola per il prossimo.
        suoni.notte_in_corso = lambda: getattr(self, "night", False)

        for source in (self.sveglia,
                       self.zedmd, self.preview, self.notifiche,
                       self.satelliti, self.radar,
                       self.meteo, self.cielo, self.inutili,
                       self.player,
                       self.birthdays, self.scadenze, self.calendario,
                       self.banner, self.onair, self.telecamera, self.media,
                       self.doom, self.giochi, self.gameboy,
                       self.clock):
            self.arbiter.register(source)
        self.arbiter.apply_services()
        # Il turno fra meteo e cielo: uno ogni due media, a turno. Parte
        # sempre, anche con il Cielo spento -- allora da' tutto lo spazio al
        # meteo -- perche' la regola dei due media vale per il meteo comunque.
        # Il wifi sempre sveglio. In un thread: `nmcli` puo' prendersi
        # qualche secondo, e l'avvio del pannello non aspetta la radio.
        threading.Thread(target=self._wifi_sveglio, name="wifi",
                         daemon=True).start()
        self.turni = Turni(self.cfg, self.meteo, self.cielo, self.media,
                           self.inutili)
        self.turni.start()
        # Doom non passa da apply_services: non e' un servizio. Qui parte solo
        # la lettura della tastiera, se e' stata chiesta.
        self.doom.start()
        # Nemmeno i giochi sono un servizio: qui parte solo la lettura dei
        # comandi, per chi ha chiesto di poter cominciare dal cabinato.
        self.giochi.start()
        # E nemmeno il Game Boy: qui parte solo la lettura dei comandi.
        self.gameboy.start()

        self._start_audio()
        self._start_metadati()
        self._riallinea_cassa()

        # Handshake ZeDMD sulla porta 80: server dedicato, non Flask.
        self.zedmd_http = ZeDMDHttpServer(
            self,
            port=self.cfg["zedmd"]["http_port"],
            ui_port=self.cfg["web"]["port"],
        )
        self.zedmd_http.start()

        self.running = True
        self.update_info = ota._esito(__version__)
        self.update_info["checked"] = 0
        # Non si interroga GitHub all'avvio: il controllo della libreria e'
        # su richiesta, dal pulsante nella pagina Impostazioni.
        self.lib_info = {"ok": False, "error": "", "path": "",
                         "repo": libcheck.REPO, "branch": libcheck.BRANCH,
                         "local": {}, "remote": {}, "behind": False, "checked": 0}
        self._ota_thread = threading.Thread(target=self._ota_loop, name="ota", daemon=True)
        self._ota_thread.start()

        # Le briciole dei Mac nelle condivisioni. Vive qui dentro e non in un
        # timer di systemd perche' l'aggiornamento via rete non esegue
        # install.sh: un'unita' nuova non arriverebbe mai sulle macchine gia'
        # installate, e la funzione resterebbe spenta senza dirlo.
        self.pulitore = pulizia.Pulitore(self.cfg)
        self.pulitore.start()
        self._blank_shown = False
        self._applied_brightness = None
        self.sleeping = False
        self.display_off = bool((self.cfg.get("display") or {}).get("off"))
        self.night = False
        # Impronta dell'ultimo frame mandato al pannello, e due contatori per
        # sapere quanto lavoro ci stiamo risparmiando. Vedi _cambiato().
        self._ultimo_frame = None
        self.frame_mostrati = 0
        self.frame_saltati = 0

    # ------------------------------------------------------------------ musica

    def _pulsante_di_turno(self, squilla):
        """Mentre la sveglia suona il pulsante fisico e' suo, sempre.

        Il difetto che questa funzione ripara e' di quelli che si vedono solo
        montando la macchina. Il pulsante veniva aperto da `start()` della
        **telecamera**, quindi esisteva solo mentre il servizio Funcam era
        acceso. Con la Funcam spenta -- che e' il caso normale di chi la
        webcam non la usa -- nessuno leggeva quel piedino: la sveglia
        squillava, il testo della pagina diceva di premere il pulsante, e
        premerlo non faceva niente. Da fuori sembrava una saldatura sbagliata,
        e invece era un pulsante che non apparteneva a nessuno.

        Adesso e' del DMD. Se la telecamera lo sta gia' tenendo non glielo si
        strappa -- il suo `intercetta` manda comunque il clic alla sveglia, ed
        e' la stessa cosa con un oggetto in meno. Se invece e' libero lo apre
        la sveglia, e lo richiude quando ha smesso di squillare.

        La chiusura avviene **qui**, dal ciclo principale, e non dentro
        `zittisci`: `zittisci` la chiama il callback del pulsante stesso, e
        chiudere un oggetto `gpiozero` da dentro il suo gestore di eventi e' il
        modo piu' rapido di piantare un thread.
        """
        conf = self.cfg.get("sveglia") or {}
        if squilla and conf.get("pulsante", True):
            if self._pulsante_sveglia is not None:
                return
            gpio = pulsante.piedino(self.cfg)
            if pulsante.occupato(gpio) is not None:
                return
            bottone = pulsante.Pulsante(gpio, su_clic=self.sveglia.zittisci,
                                        su_tenuta=self.sveglia.zittisci)
            aperto, motivo = bottone.avvia()
            if not aperto:
                # Si dice e si va avanti: la sveglia si ferma comunque da
                # sola dopo la durata, e dalla pagina.
                print("[sveglia] pulsante non disponibile: %s" % motivo)
                return
            self._pulsante_sveglia = bottone
            print("[sveglia] pulsante preso (GPIO %d)" % gpio)
            return
        if self._pulsante_sveglia is not None:
            self._pulsante_sveglia.ferma()
            self._pulsante_sveglia = None
            print("[sveglia] pulsante rilasciato")

    def _congela_partite(self, squilla):
        """Mentre la sveglia suona, le partite aperte stanno ferme.

        La prima stesura di questa funzione non esisteva, e il motivo era un
        ragionamento sbagliato: «le sveglie suonano al mattino, chi sta
        giocando a Doom alle sette?». La risposta e' arrivata in una frase --
        *metti che devo ricordarmi di scolare la pasta e mentre cucino decido
        di giocare a Doom* -- e ha demolito la premessa: una sveglia serve
        soprattutto **mentre si e' occupati a fare altro**.

        Peggio, si diceva che i giochi scritti per il pannello si congelassero
        da soli perche' li disegna il ciclo principale. Non e' vero: hanno un
        thread loro, come Doom e il Game Boy, e continuano a giocare anche a
        pannello altrui. Tornavi e ti trovavi morto in tutti e tre i casi.

        Si agisce solo sui **cambi di stato**: sospendere un processo gia'
        sospeso, trenta volte al secondo, sarebbe traffico di segnali per
        niente.
        """
        if squilla == self._partite_congelate:
            return
        self._partite_congelate = squilla
        for nome in ("giochi", "doom", "gameboy"):
            sorgente = getattr(self, nome, None)
            if sorgente is None:
                continue
            try:
                if squilla:
                    sorgente.sospendi()
                else:
                    sorgente.riprendi()
            except Exception as exc:      # pragma: no cover
                # Una partita che non si lascia congelare non deve impedire
                # alla sveglia di suonare: al massimo si perde quella partita.
                print("[sveglia] %s non congelato: %s" % (nome, exc))

    def _suona_notifica(self, livello):
        """Il campanello di una notifica, scelto dal suo livello.

        Tre file distinti e non uno solo, e la ragione sta nel momento in cui
        una notifica arriva: e' l'unica cosa del pannello che succede **mentre
        non lo stai guardando**. Un campanello unico dice «e' successo
        qualcosa» e ti obbliga ad andare a vedere; tre dicono se vale la pena
        alzarsi, e lo dicono dall'altra stanza.

        Passa dalla strada normale degli avvisi, quindi rispetta l'interruttore
        generale dell'audio e il volume notturno. E' la differenza voluta con
        la sveglia, che il volume notturno lo ignora: una notifica alle tre di
        notte puo' parlare piano, una sveglia no.
        """
        chiave = suoni.chiave_notifica(livello)
        if not chiave:
            return False
        try:
            return suoni.suona_servizio(self.cfg, chiave)
        except Exception as exc:          # pragma: no cover
            print("[notifiche] avviso non riprodotto: %s" % exc)
            return False

    def _onair_in_onda(self):
        """Se siamo in diretta. Lo chiede l'orologio per il suo trattino."""
        return bool(self.onair.enabled and self.onair.in_onda())

    def _aggiornamento_disponibile(self):
        """Se c'e' una versione nuova. Lo chiede l'orologio per il suo puntino.

        Legge l'esito del controllo gia' fatto, non ne fa uno nuovo: questa
        funzione viene chiamata a ogni fotogramma dell'orologio, e interrogare
        GitHub venti volte al secondo sarebbe un modo creativo di farsi
        bloccare dall'API.
        """
        info = self.update_info or {}
        return bool(info.get("ok") and info.get("available"))

    def _suona_onair(self):
        """Il campanello della diretta: **una volta sola**, alla chiusura.

        Non a ogni ricomparsa della scritta. Con la cadenza dei media una
        diretta di un'ora vorrebbe dire trenta din-don, e a quel punto il
        suono non annuncia piu' niente: e' rumore. Una spia annuncia il
        **cambio** di stato, non lo stato.
        """
        try:
            return suoni.suona_servizio(self.cfg, "onair")
        except Exception as exc:          # pragma: no cover
            print("[onair] avviso non riprodotto: %s" % exc)
            return False

    def _suona_sveglia(self, scelto):
        """Il suono della sveglia. (partito, motivo).

        Due differenze da tutti gli altri avvisi, e sono volute.

        **Il volume e' quello di giorno**, sempre: `volume_impostato` e non
        `volume`. Il night mode abbassa la voce del DMD perche' un aereo alle
        tre di notte non merita di svegliarti — una sveglia si mette apposta
        per farlo, e sarebbe l'unico caso in cui quel silenzio fa danno.

        **Passa sopra la musica** con `forza`, che salta anche il controllo
        "un brano sta suonando". Ma prima si guarda l'interruttore generale
        dell'audio a mano: chi ha spento il suono non vuole sentire niente, e
        quella regola vale anche per la sveglia. Il pannello lampeggia lo
        stesso, che e' meta' della funzione.
        """
        if not suoni.acceso(self.cfg):
            return False, "audio spento"
        percorso = suoni.percorso_media(self.cfg, scelto)
        if not percorso:
            # Nessun file scelto, o scelto e poi cancellato dalla libreria:
            # si usa un effetto del programma, che c'e' sempre. Una sveglia
            # muta perche' manca un file non e' una sveglia.
            percorso = suoni.effetto("livello")
        return suoni.riproduci(self.cfg, percorso, forza=True,
                               vol=suoni.volume_impostato(self.cfg))

    def _musica_in_corso(self):
        """Vero se un brano AirPlay sta uscendo dalla nostra scheda audio.

        Due condizioni, e servono entrambe. Se l'uscita musicale e' spenta la
        musica va nella scheda fittizia e non da' fastidio a nessuno, quindi
        gli avvisi devono suonare come sempre. E fra le tre sorgenti di Now
        Playing conta solo AirPlay: Spotify racconta un brano che sta suonando
        altrove, e da un racconto non esce audio.
        """
        try:
            if not cassa.attiva():
                return False
            brano = self.nowplaying.snapshot()
            return brano["source"] == "airplay" and brano["playing"]
        except Exception:
            return False

    def _start_metadati(self):
        """La pipe locale di shairport-sync: i metadati presi dove nascono.

        Due programmi sulla stessa macchina non hanno motivo di parlarsi
        attraverso un server di rete. Questa strada e' la principale dalla
        7.4; MQTT resta acceso accanto e continua a funzionare, e chi ha gia'
        tutto configurato non si accorge del cambio — le due strade finiscono
        nella stessa funzione.

        Se shairport-sync c'e' ma non scrive ancora nella pipe, glielo si
        chiede: e' una scrittura sola nella sua configurazione e un riavvio,
        e la volta dopo non serve piu'. E' anche l'unico modo perche' una
        macchina gia' installata riceva la funzione, visto che
        l'aggiornamento via rete non esegue nessuno script.
        """
        self.metadati = metadati.Metadati(self.cfg,
                                          self.nowplaying.handle_shairport)
        if not self.metadati.voluta():
            return
        percorso = self.metadati.percorso()
        try:
            if cassa.installato() and not cassa.metadati_attivi(percorso):
                ok, motivo = cassa.abilita_metadati(percorso)
                if ok:
                    print("[dmd] shairport-sync ora scrive i metadati in %s"
                          % percorso)
                else:
                    print("[dmd] pipe dei metadati non attivata: %s" % motivo)
        except Exception as exc:
            print("[dmd] pipe dei metadati non attivata: %s" % exc)
        try:
            self.metadati.start()
        except Exception as exc:
            print("[dmd] lettore dei metadati non avviato: %s" % exc)

    def _riallinea_cassa(self):
        """L'uscita musicale segue la scheda scelta in Impostazioni.

        All'avvio e non solo alla pressione dell'interruttore: una scheda
        cambiata a servizio fermo, o un file di configurazione ripristinato da
        un backup, non lasciano nessuno a riallineare.
        """
        try:
            fatto, motivo = cassa.riconcilia(suoni.uscita(self.cfg))
            if fatto:
                print("[dmd] uscita musicale riportata su %s"
                      % cassa.uscita_attuale())
            elif motivo:
                print("[dmd] uscita musicale non riallineata: %s" % motivo)
        except Exception as exc:
            print("[dmd] uscita musicale non riallineata: %s" % exc)

    def _start_audio(self):
        """Collega il bus MQTT, le sottoscrizioni e il poller di Spotify.

        Tutto avvolto: un broker irraggiungibile o una libreria mancante non
        devono impedire al pannello di accendersi. E' la stessa lezione della
        1.7.1 sull'interfaccia web, applicata a un accessorio in piu'.
        """
        try:
            self._subscribe_audio()
            if self.mqtt.start():
                self.hass.start()
        except Exception:
            import traceback
            print("[dmd] ATTENZIONE: MQTT non avviato", flush=True)
            traceback.print_exc()
        try:
            self.spotify.start()
        except Exception as exc:
            print("[dmd] Spotify non avviato: %s" % exc)

    def _subscribe_audio(self):
        conf = self.cfg.get("mqtt") or {}
        shairport = str(conf.get("shairport_topic") or "").strip("/")
        if shairport:
            # Non `#`: con publish_raw attivo quel ramo porta anche le
            # copertine, centinaia di kilobyte di JPEG per ogni brano che
            # attraverserebbero il broker e la rete per essere poi buttati.
            # `+` prende il solo livello leggibile (title, artist, playing,
            # active, play_*), e i due codici grezzi che servono davvero si
            # chiedono per nome.
            self.mqtt.subscribe("%s/+" % shairport,
                                self.nowplaying.handle_shairport)
            for codice in ("prgr", "paus"):
                self.mqtt.subscribe("%s/ssnc/%s" % (shairport, codice),
                                    self.nowplaying.handle_shairport)
        external = str(conf.get("external_topic") or "").strip("/")
        if external:
            self.mqtt.subscribe(external, self.nowplaying.handle_external)

        # Il topic delle notifiche da Home Assistant. Sta qui e non dentro la
        # sorgente perche' le iscrizioni si rifanno tutte insieme quando la
        # connessione al broker viene riaperta dalla pagina web.
        notifiche = str((self.cfg.get("notifiche") or {}).get("topic")
                        or "").strip("/")
        if notifiche:
            self.mqtt.subscribe(notifiche, self.notifiche.handle_mqtt)
            # Un topic per livello, accanto a quello principale. Sono le tre
            # entita' notify che Home Assistant vede nella tendina dei
            # bersagli. Tre iscrizioni esplicite e non `notifiche + "/#"`:
            # il carattere jolly, per come e' scritta la specifica, coprirebbe
            # anche il topic padre e ogni messaggio arriverebbe due volte.
            for livello in ("info", "avviso", "allarme"):
                self.mqtt.subscribe("%s/%s" % (notifiche, livello),
                                    self.notifiche.handle_mqtt)

    def reconnect_mqtt(self):
        """Riapre la connessione dopo un cambio di impostazioni dalla web UI."""
        try:
            self.mqtt.stop()
            self.mqtt._handlers = []
            self._subscribe_audio()
            if self.mqtt.start():
                self.hass.start()
            else:
                # Spento vuol dire spento: senza questa riga il thread del
                # ponte Home Assistant continuava a girare a vuoto, a
                # pubblicare su un client che non c'e' piu'. Non si vedeva —
                # le pubblicazioni cadono in silenzio — ma «spegnere» deve
                # fermare qualcosa, non solo smettere di collegarsi.
                self.hass.stop()
            self.player.invalidate()
            return True
        except Exception as exc:
            print("[mqtt] riconnessione fallita: %s" % exc)
            return False

    # ------------------------------------------------------------ gestione media

    def manager_enter(self):
        """Entra (o resta) in gestione media. La chiama la pagina, e il battito.

        Sospendere davvero le sorgenti — fermarne i thread — costerebbe la
        riconnessione di ZeDMD e la ripartenza del radar per due minuti di
        libreria. Qui si sospende solo l'accesso al pannello: chi lavora
        continua a lavorare, e quando si esce riprende il suo posto senza
        essersi accorto di niente.
        """
        primo = not self.arbiter.manager()
        self.arbiter.manager_on()
        if primo:
            # Un pannello nero e muto sembra guasto: meglio dire perche'.
            self.preview.hold()
        return primo

    def manager_leave(self):
        """Esce dalla gestione e restituisce il pannello alle sorgenti."""
        if not self.arbiter.manager():
            return False
        self.arbiter.manager_off()
        self.preview.cancel()
        # Chi subentra ridisegna: senza questo l'ultima anteprima resterebbe
        # a schermo finche' il vincitore non ha qualcosa di nuovo da dire.
        self.arbiter.current = None
        self._blank_shown = False
        return True

    def manager_state(self):
        return {"on": self.arbiter.manager(),
                "timeout": MANAGER_TIMEOUT,
                "left": self.arbiter.manager_left(),
                "showing": self.preview.current,
                "status": self.preview.status()}

    # -------------------------------------------------------------------- doom

    # ------------------------------------------------------------------ partite

    # Una partita alla volta si apre o si chiude. Senza, due richieste nello
    # stesso momento -- il tasto Start del pad e il pulsante Gioca della
    # pagina -- si intrecciavano dentro `apri_sessione`: la seconda apriva il
    # suo gioco, la prima, ancora a meta', gli sostituiva il gioco sotto i
    # piedi. Sul pannello partiva Squadriglia e un attimo dopo compariva il
    # gioco del giro. Rientrante perche' il giro apre passando di nuovo di qui.
    _partite = threading.RLock()

    def gioca(self, cosa, nome="", da_giro=False):
        """Apre una partita, chiudendo quella eventualmente in corso.

        **Una scelta esplicita vince sul giro.** Gioca nella pagina, un
        interruttore di Home Assistant: chi li preme ha scelto quel gioco. Una
        pressione di Start arrivata insieme, o in coda subito dopo, non se lo
        deve portare via: per qualche secondo il giro si ferma, e quando
        riparte riparte **dal gioco scelto**.

        Doom e i giochi si contendono **la stessa presa del pannello**, e
        aprirne una senza chiudere l'altra non da' un errore: da' un processo
        Doom vivo dietro le quinte che nessuno vede piu', con Home Assistant
        convinto che si stia ancora giocando a Doom mentre sul pannello c'e'
        Breakout. Il runtime e' l'unico punto che conosce entrambe, quindi la
        regola sta qui e non dentro le due sorgenti.
        """
        with self._partite:
            if da_giro and self.giochi.scelta_recente():
                print("[giochi] giro ignorato: c'e' appena stata una scelta")
                return None
            if not da_giro:
                self.giochi.scelta_esplicita(
                    cosa if cosa in ("doom", "gameboy") else nome)
            return self._apri_partita(cosa, nome)

    def _apri_partita(self, cosa, nome=""):
        if cosa == "doom":
            self.giochi.chiudi_sessione()
            self.gameboy.chiudi_sessione()
            return self.doom.apri_sessione()
        if cosa == "gameboy":
            self.giochi.chiudi_sessione()
            self.doom.chiudi_sessione()
            return self.gameboy.apri_sessione(nome)
        self.doom.chiudi_sessione()
        self.gameboy.chiudi_sessione()
        return self.giochi.apri_sessione(nome)

    def smetti(self, cosa=""):
        """Chiude la partita in corso. Senza argomenti, qualunque essa sia."""
        with self._partite:
            return self._smetti(cosa)

    def _smetti(self, cosa=""):
        chiuse = False
        if cosa in ("", "giochi"):
            chiuse = self.giochi.chiudi_sessione() or chiuse
        if cosa in ("", "doom"):
            chiuse = self.doom.chiudi_sessione() or chiuse
        if cosa in ("", "gameboy"):
            chiuse = self.gameboy.chiudi_sessione() or chiuse
        return chiuse

    def giochi_state(self):
        return self.giochi.stato()

    def gameboy_state(self):
        return {"running": self.gameboy.active(),
                "session": self.gameboy.in_sessione(),
                "ready": self.gameboy.pronto(),
                "rom": os.path.basename(self.gameboy.rom_corrente() or ""),
                "keys": self.gameboy.premuti(),
                "status": self.gameboy.status()}

    def doom_state(self):
        return {"running": self.doom.active(),
                "session": self.doom.in_sessione(),
                "idle": int(self.doom.inattivita()),
                "keys": self.doom.premuti(),
                "status": self.doom.status()}

    # ------------------------------------------------------------------ aggiornamenti

    def check_library(self):
        """Confronta la libreria della matrice con il ramo remoto.

        Solo controllo: l'aggiornamento resta un'operazione manuale, perche'
        richiede una ricompilazione lunga e puo' cambiare il comportamento di
        una taratura funzionante.
        """
        try:
            self.lib_info = libcheck.check(self.cfg)
        except Exception as exc:
            self.lib_info = {"ok": False, "error": str(exc), "path": "",
                             "repo": libcheck.REPO, "branch": libcheck.BRANCH,
                             "local": {}, "remote": {}, "behind": False,
                             "checked": time.time()}
        return self.lib_info

    def check_update(self):
        """Interroga GitHub e memorizza l'esito per la web UI."""
        try:
            self.update_info = ota.check(self.cfg)
        except Exception as exc:
            self.update_info = ota._esito(__version__)
            self.update_info["error"] = str(exc)
        return self.update_info

    def _ota_loop(self):
        # Un attimo di attesa: alla partenza la rete potrebbe non esserci ancora.
        time.sleep(30)
        while self.running:
            if self.cfg["ota"]["auto_check"]:
                info = self.check_update()
                if info.get("available"):
                    print("[ota] disponibile la versione %s (installata %s, da %s)"
                          % (info["latest"], info["current"],
                             info.get("fonte") or "?"))
            hours = max(1, int(self.cfg["ota"]["check_interval_hours"]))
            for _ in range(hours * 60):
                if not self.running:
                    return
                time.sleep(60)

    # ------------------------------------------------------------------ luminosita'

    def set_brightness(self, percent):
        """Luminosita' scelta dall'utente: e' il valore diurno di riferimento."""
        value = max(0, min(100, int(percent)))
        self.cfg["display"]["brightness"] = value
        dmdconf.save()
        self._applied_brightness = None  # forza il riallineamento al prossimo giro
        return value

    def _update_modes(self):
        """Calcola Sleep e Night e applica la luminosita' corrispondente."""
        # Le fasce dei servizi scadono da sole e non le gira nessuno: senza
        # questa chiamata il Media Player resterebbe come l'ha lasciato
        # l'ultima persona che ha toccato una pagina web. E' idempotente.
        try:
            self.arbiter.apply_services()
        except Exception as exc:
            print("[dmd] fasce dei servizi non applicate: %s" % exc)

        # Cane da guardia del radar. Un ciclo fermo non puo' accorgersi da
        # solo di essere fermo: qualcuno deve guardarlo da fuori, e questo
        # giro passa una volta al secondo.
        #
        # Non e' una cura ed e' importante dirlo: il difetto, se esiste, resta
        # da trovare. Ma un sintomo che si presenta ogni tre giorni non si
        # insegue a mano, e ogni rianimazione lascia una riga nel registro con
        # un orario sopra. Se il contatore resta a zero, il blocco non c'era.
        try:
            radar = self.radar
            if (radar.enabled and radar._running
                    and radar.fermo_da() > radar.soglia_blocco(
                        self.cfg["air_radar"])):
                radar.rianima()
        except Exception as exc:
            print("[dmd] cane da guardia del radar: %s" % exc)

        display = self.cfg["display"]
        now = time.localtime()
        minute = now.tm_hour * 60 + now.tm_min

        sleeping = display["sleep_enabled"] and in_window(
            minute, parse_hhmm(display["sleep_start"]), parse_hhmm(display["sleep_end"]))
        # Se arrivano frame da Batocera nel cuore della notte, il display si sveglia.
        if sleeping and display["sleep_wake_on_zedmd"]:
            if self.zedmd.enabled and self.zedmd.active():
                sleeping = False

        # Chi ha preso il pannello lo sta guardando adesso — sta scegliendo un
        # file o sta giocando: se capita nella fascia notturna, spegnerglielo
        # in faccia non aiuta.
        #
        # Dalla 8.1 questa eccezione ha una casella, accanto a quella dei frame
        # da Batocera. Sono due cose diverse e meritavano due interruttori: i
        # frame arrivano da soli, una partita la apre qualcuno che e' li'
        # davanti. Chi la spegne vuole che alle due di notte il pannello resti
        # nero comunque, ed e' una scelta legittima.
        if sleeping and self.arbiter.holding():
            if display.get("sleep_wake_on_giochi", True):
                sleeping = False

        # Lo spegnimento a mano viene **dopo** tutte le eccezioni, e vince su
        # tutte: se qualcuno ha deciso adesso che il pannello deve stare
        # spento, non lo risveglia ne' un frame da Batocera ne' una partita
        # aperta. Sleep mode e' un orario, questo e' una decisione.
        spento = bool(display.get("off"))
        if spento:
            sleeping = True

        night = display["night_enabled"] and in_window(
            minute, parse_hhmm(display["night_start"]), parse_hhmm(display["night_end"]))

        # **La sveglia viene dopo tutto e vince su tutto**, spegnimento a mano
        # compreso. Tre motivi, e nessuno e' una comodita':
        #
        # 1. Il ciclo principale, quando dorme, si ferma *prima* di chiedere
        #    all'arbitro chi debba comparire. Una sorgente qualunque, per
        #    quanto prioritaria, non verrebbe nemmeno interrogata: una sveglia
        #    alle 7 con lo Sleep fino alle 8 non suonerebbe mai, cioe' proprio
        #    nel caso in cui serve.
        # 2. Spegnere il pannello e' una decisione sul presente; mettere una
        #    sveglia e' una promessa fatta prima per dopo. Fra le due vince la
        #    promessa -- e chi non la vuole spegne la sveglia, non il display.
        # 3. Anche la luminosita' torna quella di giorno: una sveglia che si
        #    vede al quindici per cento e' mezza sveglia.
        #
        # `controlla()` non e' solo una domanda: e' anche il punto in cui la
        # sveglia parte. Deve quindi essere chiamata **sempre**, anche mentre
        # si dorme, ed e' l'unica ragione per cui sta qui e non nell'arbitro.
        try:
            squilla = self.sveglia.controlla()
        except Exception as exc:          # pragma: no cover
            print("[sveglia] controllo fallito: %s" % exc)
            squilla = False
        self._pulsante_di_turno(squilla)
        self._congela_partite(squilla)
        sleeping, spento, night = modi_effettivi(sleeping, spento, night,
                                                 squilla)

        self.sleeping = sleeping
        self.display_off = spento
        self.night = night

        target = display["night_brightness"] if night else display["brightness"]
        if target != self._applied_brightness:
            self.display.set_brightness(target)
            self._applied_brightness = target

    # ------------------------------------------------------------------ rendering

    def _cambiato(self, image):
        """Vero se questa immagine e' diversa dall'ultima gia' sul pannello.

        Perche' esiste. Mandare un frame al pannello non e' gratis: la
        libreria riscrive l'intero buffer dei piani di bit, e quelle scritture
        contendono il bus di memoria alle letture del thread che aggiorna il
        display riga per riga. Quando il bus e' occupato la lettura di una
        riga si ferma per qualche microsecondo, e quella riga resta accesa
        piu' delle altre: e' la riga chiara che compare in un punto sempre
        diverso.

        L'orologio fermo cambia una volta al secondo, ma il ciclo gira a 30
        fps: senza questo controllo scriveremmo trenta volte al secondo la
        stessa identica immagine, creando da soli il disturbo che poi andiamo
        a cercare. Il confronto costa un `tobytes` (49 KB per un 256x64), che
        e' una frazione di quello che costa la riscrittura evitata.
        """
        impronta = image.tobytes()
        if impronta == self._ultimo_frame:
            self.frame_saltati += 1
            return False
        self._ultimo_frame = impronta
        self.frame_mostrati += 1
        return True

    def _ridisegna(self):
        """Dimentica l'ultimo frame: il prossimo si manda comunque.

        Serve dopo ogni cosa che tocca il pannello alle spalle del ciclo —
        cambio di sorgente, schermo nero, risveglio — perche' li' l'immagine
        che sta sul pannello non e' piu' quella che credevamo.
        """
        self._ultimo_frame = None

    def render_loop(self):
        from PIL import Image

        blank = Image.new("RGB", (self.display.width, self.display.height), (0, 0, 0))
        period = 1.0 / FPS
        last_mode_check = 0.0

        while self.running:
            started = time.time()

            if started - last_mode_check >= 1.0:
                self._update_modes()
                # Una sessione di Doom lasciata a meta' non deve tenersi il
                # pannello per sempre: il controllo e' un confronto fra due
                # numeri, e non merita un thread suo.
                try:
                    self.doom.controlla_inattivita()
                    self.giochi.controlla_inattivita()
                    self.gameboy.controlla_inattivita()
                    # E se una partita e' aperta ma il processo e' morto, si
                    # ritenta: correggere un percorso sbagliato dalla pagina
                    # deve bastare a rimettere in moto.
                    self.doom.mantieni()
                except Exception:
                    pass
                last_mode_check = started

            if self.sleeping:
                if not self._blank_shown:
                    self.display.show(blank)
                    self._blank_shown = True
                    self.arbiter.current = None
                    self._ridisegna()
                time.sleep(0.2)
                continue

            winner = self.arbiter.pick()

            if winner is not self.arbiter.current:
                # Il **momento della notifica** e' questo, e non ce n'e' un
                # altro: la sorgente ha appena preso il pannello, cioe' ha
                # qualcosa da dire adesso. Agganciare il suono all'interruttore
                # del servizio suonerebbe quando lo si accende — che non e'
                # una notizia — e agganciarlo al disegno del fotogramma
                # suonerebbe trenta volte al secondo.
                # Chi si suona da solo non passa di qui: OnAir ricompare ogni
                # due foto per tutta la diretta, e il suo campanello deve
                # suonare una volta sola, quando la porta si chiude. Senza
                # questa riga suonerebbe a ogni ricomparsa.
                if winner is not None and winner.name not in suoni.SUONO_PROPRIO:
                    try:
                        suoni.suona_servizio(self.cfg, winner.name)
                    except Exception as exc:      # pragma: no cover
                        print("[suoni] avviso non riprodotto: %s" % exc)
                self.arbiter.current = winner
                self._blank_shown = False
                self._ridisegna()
                if winner is not None:
                    # Alla presa di controllo la sorgente deve ridisegnare tutto.
                    if hasattr(winner, "_dirty"):
                        winner._dirty = True
                    if hasattr(winner, "invalidate"):
                        winner.invalidate()
                    # E deve sapere che adesso la stanno guardando davvero.
                    # E' l'unico istante in cui questo si sa, ed e' diverso
                    # da "ha qualcosa da mostrare": fra i due c'e' l'arbitro.
                    try:
                        winner.in_onda()
                    except Exception as exc:      # pragma: no cover
                        print("[arbitro] in_onda fallita per %s: %s"
                              % (winner.name, exc))

            if winner is None:
                if not self._blank_shown:
                    self.display.show(blank)
                    self._blank_shown = True
                    self._ridisegna()
            else:
                image = winner.frame()
                if image is not None and self._cambiato(image):
                    self.display.show(image)

            elapsed = time.time() - started
            if elapsed < period:
                time.sleep(period - elapsed)

    def _wifi_sveglio(self):
        """Spegne il risparmio energetico della radio, se e' stato chiesto.

        Si fa a **ogni avvio** e non una volta sola: la preferenza salvata in
        NetworkManager si perde se la connessione viene rifatta, e una
        reinstallazione ripartirebbe con il risparmio acceso -- cioe' con il
        difetto che ha reso il pannello irraggiungibile pur restando acceso.
        """
        if not (self.cfg.get("rete") or {}).get("wifi_sveglio", True):
            return
        try:
            import rete
            if rete.risparmio() is False:
                return                      # gia' sveglio: niente da fare
            fatto, dettaglio = rete.spegni_risparmio()
            print("[rete] risparmio wifi: %s (%s)"
                  % ("spento" if fatto else "non spento", dettaglio))
        except Exception as exc:                  # pragma: no cover - difensivo
            print("[rete] risparmio wifi non applicato: %s" % exc)

    def shutdown(self, *_args):
        if not self.running:
            return
        self.running = False
        for closing in (self.zedmd_http, self.spotify, self.hass, self.mqtt,
                        self.metadati, getattr(self, "turni", None)):
            try:
                if closing is not None:
                    closing.stop()
            except Exception:
                pass
        for source in self.arbiter.sources.values():
            try:
                source.stop()
            except Exception:
                pass
        try:
            self.display.clear()
        except Exception:
            pass


def main():
    print("[dmd] kWGillo DMD Server %s" % __version__)
    runtime = Runtime()

    signal.signal(signal.SIGTERM, runtime.shutdown)
    signal.signal(signal.SIGINT, runtime.shutdown)

    # L'interfaccia web e' un accessorio: se non parte, il pannello deve
    # comunque accendersi. Prima l'errore faceva uscire il processo e systemd
    # lo riavviava all'infinito, lasciando il display spento e nessun modo
    # comodo di capire perche'.
    try:
        import webui

        app = webui.create_app(runtime)
        port = runtime.cfg["web"]["port"]

        web_thread = threading.Thread(
            target=lambda: app.run(host="0.0.0.0", port=port, threaded=True,
                                   use_reloader=False, debug=False),
            name="webui",
            daemon=True,
        )
        web_thread.start()
        print("[dmd] web UI su http://0.0.0.0:%d" % port)
    except Exception:
        import traceback
        print("[dmd] ATTENZIONE: interfaccia web non avviata", flush=True)
        traceback.print_exc()
        print("[dmd] il pannello continua a funzionare; "
              "correggi l'errore qui sopra e riavvia il servizio", flush=True)

    try:
        runtime.render_loop()
    except KeyboardInterrupt:
        pass
    finally:
        runtime.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
