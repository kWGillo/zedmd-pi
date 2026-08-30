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

import signal
import sys
import threading
import time

import dmdconf
import hass
import libcheck
import mqttbus
import nowplaying
import ota
import spotifyapi
from display import Display
from sources import (AirRadarSource, BannerSource, BirthdaysSource,
                     ClockSource, DoomSource, MediaPlayerSource,
                     NowPlayingSource, PreviewSource, ZeDMDSource)
from version import __version__
from zedmd_http import ZeDMDHttpServer

# 30 fps: sufficienti per un DMD e lasciano CPU al ricevitore ZeDMD,
# che non deve mai risultare lento al client (altrimenti scarta frame).
FPS = 30


def parse_hhmm(value, fallback=0):
    """'22:30' -> minuti dalla mezzanotte."""
    try:
        hours, minutes = str(value).split(":")
        return (int(hours) % 24) * 60 + (int(minutes) % 60)
    except (ValueError, AttributeError):
        return fallback


def in_window(minute, start, end):
    """True se `minute` cade nella fascia, gestendo il passaggio di mezzanotte."""
    if start == end:
        return False
    if start < end:
        return start <= minute < end
    return minute >= start or minute < end


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
            wanted = bool(services.get(name, False))
            if wanted and not source.enabled:
                source.enabled = True
                source.start()
            elif not wanted and source.enabled:
                source.enabled = False
                source.stop()

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
        # Doom prende e restituisce il pannello da solo, quindi conosce
        # l'arbitro: e' l'unica sorgente che lo fa. Non e' un servizio e non
        # compare fra gli interruttori — `enabled` resta False per sempre — e
        # va a schermo solo quando ha la presa, cioe' solo durante una partita.
        self.doom = DoomSource(self.cfg, self.display.width,
                               self.display.height, self.arbiter)
        self.clock = ClockSource(self.cfg, self.display.width, self.display.height)

        # Il brano corrente e chi lo disegna sono due cose distinte: lo stato
        # viene aggiornato anche a servizio spento, cosi' Home Assistant lo
        # vede lo stesso e accendendo il player non si parte da zero.
        self.nowplaying = nowplaying.NowPlaying(self.cfg)
        self.player = NowPlayingSource(self.cfg, self.display.width,
                                       self.display.height, self.nowplaying)
        self.mqtt = mqttbus.MqttBus(self.cfg)
        self.spotify = spotifyapi.SpotifyPoller(self.cfg, self.nowplaying)
        self.hass = hass.HassBridge(self.cfg, self.mqtt, self)

        for source in (self.zedmd, self.preview, self.radar, self.player,
                       self.birthdays, self.banner, self.media, self.doom,
                       self.clock):
            self.arbiter.register(source)
        self.arbiter.apply_services()
        # Doom non passa da apply_services: non e' un servizio. Qui parte solo
        # la lettura della tastiera, se e' stata chiesta.
        self.doom.start()

        self._start_audio()

        # Handshake ZeDMD sulla porta 80: server dedicato, non Flask.
        self.zedmd_http = ZeDMDHttpServer(
            self,
            port=self.cfg["zedmd"]["http_port"],
            ui_port=self.cfg["web"]["port"],
        )
        self.zedmd_http.start()

        self.running = True
        self.update_info = {"ok": False, "error": "", "current": __version__,
                            "latest": "", "available": False, "checked": 0}
        # Non si interroga GitHub all'avvio: il controllo della libreria e'
        # su richiesta, dal pulsante nella pagina Impostazioni.
        self.lib_info = {"ok": False, "error": "", "path": "",
                         "repo": libcheck.REPO, "branch": libcheck.BRANCH,
                         "local": {}, "remote": {}, "behind": False, "checked": 0}
        self._ota_thread = threading.Thread(target=self._ota_loop, name="ota", daemon=True)
        self._ota_thread.start()
        self._blank_shown = False
        self._applied_brightness = None
        self.sleeping = False
        self.night = False

    # ------------------------------------------------------------------ musica

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

    def reconnect_mqtt(self):
        """Riapre la connessione dopo un cambio di impostazioni dalla web UI."""
        try:
            self.mqtt.stop()
            self.mqtt._handlers = []
            self._subscribe_audio()
            if self.mqtt.start():
                self.hass.start()
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
            self.update_info = {"ok": False, "error": str(exc),
                                "current": __version__, "latest": "",
                                "available": False, "checked": time.time()}
        return self.update_info

    def _ota_loop(self):
        # Un attimo di attesa: alla partenza la rete potrebbe non esserci ancora.
        time.sleep(30)
        while self.running:
            if self.cfg["ota"]["auto_check"]:
                info = self.check_update()
                if info.get("available"):
                    print("[ota] disponibile la versione %s (installata %s)"
                          % (info["latest"], info["current"]))
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
        if self.arbiter.holding():
            sleeping = False

        night = display["night_enabled"] and in_window(
            minute, parse_hhmm(display["night_start"]), parse_hhmm(display["night_end"]))

        self.sleeping = sleeping
        self.night = night

        target = display["night_brightness"] if night else display["brightness"]
        if target != self._applied_brightness:
            self.display.set_brightness(target)
            self._applied_brightness = target

    # ------------------------------------------------------------------ rendering

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
                time.sleep(0.2)
                continue

            winner = self.arbiter.pick()

            if winner is not self.arbiter.current:
                self.arbiter.current = winner
                self._blank_shown = False
                if winner is not None:
                    # Alla presa di controllo la sorgente deve ridisegnare tutto.
                    if hasattr(winner, "_dirty"):
                        winner._dirty = True
                    if hasattr(winner, "invalidate"):
                        winner.invalidate()

            if winner is None:
                if not self._blank_shown:
                    self.display.show(blank)
                    self._blank_shown = True
            else:
                image = winner.frame()
                if image is not None:
                    self.display.show(image)

            elapsed = time.time() - started
            if elapsed < period:
                time.sleep(period - elapsed)

    def shutdown(self, *_args):
        if not self.running:
            return
        self.running = False
        for closing in (self.zedmd_http, self.spotify, self.hass, self.mqtt):
            try:
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
