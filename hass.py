"""Il DMD visto da Home Assistant.

Home Assistant sa creare da solo le entita' di un dispositivo MQTT, se questo
si presenta pubblicando la propria descrizione su topic dal nome convenuto
(`MQTT Discovery`). Qui si fa esattamente questo: alla connessione il DMD
dichiara che cosa sa fare, e da quel momento in Home Assistant compare un
dispositivo con dentro il brano in riproduzione, un interruttore per ogni
servizio e la luminosita'.

Niente di tutto cio' e' necessario al funzionamento: se Home Assistant non
c'e', questi messaggi non li legge nessuno e il DMD lavora comunque. La
funzione si spegne da sola disattivando `mqtt.discovery`.

Le entita' sono legate alla disponibilita' del DMD: il testamento MQTT
registrato da `mqttbus` fa diventare tutto "non disponibile" quando il
servizio si ferma, invece di lasciare in Home Assistant valori congelati che
sembrano veri.
"""

import json
import random
import threading
import time

from version import __version__

# Servizi esposti come interruttori. La chiave e' quella in `cfg["services"]`.
SWITCHES = [
    ("zedmd", "ZeDMD"),
    ("mediaplayer", "Media Player"),
    ("banner", "Rolling Banner"),
    ("nowplaying", "Now Playing"),
    ("birthdays", "Compleanni"),
    ("air_radar", "Air Radar"),
    ("clock", "Orologio"),
    ("scadenze", "Scadenze"),
    ("calendario", "Calendario"),
    # Una telecamera si spegne anche da lontano: e' la ragione principale per
    # cui questo interruttore vale la pena averlo in Home Assistant.
    ("webcam", "Funcam"),
]

# Night mode e Sleep mode non sono servizi: sono modi del display, e stanno in
# un'altra sezione della configurazione. Da Home Assistant pero' si comandano
# allo stesso modo, quindi hanno gli stessi topic e la stessa forma — cambia
# solo dove va scritto il valore.
MODES = [
    ("night_enabled", "Night mode"),
    ("sleep_enabled", "Sleep mode"),
]

# Interruttori che non corrispondono a una voce di configurazione ma a
# **qualcosa che sta succedendo**. Doom non e' un servizio da accendere: e' una
# partita che comincia e finisce, e puo' finire da sola per inattivita'. Lo
# stato quindi non si legge dalla configurazione — li' non c'e' — ma dal
# runtime, e va ripubblicato quando cambia da solo, altrimenti Home Assistant
# resta convinto che si stia ancora giocando.
AZIONI = [
    ("doom", "Doom", "mdi:pistol"),
]

# I giochi scritti per il pannello sono azioni come Doom: una partita che
# comincia e finisce, non un servizio da accendere. Un interruttore per gioco,
# costruito dall'elenco dei giochi invece che scritto a mano — aggiungerne uno
# domani deve bastare a farlo comparire anche in Home Assistant.
#
# Sono mutuamente esclusivi per costruzione: la sessione e' una sola, quindi
# accendendone uno gli altri tornano OFF da soli al primo stato pubblicato.
GIOCO_PREFISSO = "gioco_"
ICONE_GIOCHI = {
    "breakout": "mdi:view-grid",
    "invaders": "mdi:space-invaders",
}

try:
    from sources.giochi import elenco as _elenco_giochi
    for _nome, _etichetta in _elenco_giochi():
        AZIONI.append((GIOCO_PREFISSO + _nome, _etichetta,
                       ICONE_GIOCHI.get(_nome, "mdi:gamepad-variant")))
except Exception as _exc:      # pragma: no cover - solo se manca il pacchetto
    print("[hass] giochi non annunciati: %s" % _exc)

# Icone delle voci del calendario rifiuti, per nome noto. Chi ne inventa una
# sua si prende il cassonetto generico: meglio un'icona banale che nessuna.
ICONE_RIFIUTI = {
    "carta": "mdi:newspaper-variant",
    "plastica": "mdi:bottle-soda-classic-outline",
    "vetro": "mdi:bottle-wine-outline",
    "umido": "mdi:leaf",
    "secco": "mdi:trash-can-outline",
    "sosta": "mdi:car-off",
}


def slug(nome):
    """Nome della voce -> identificativo buono per un topic MQTT."""
    pulito = "".join(c.lower() if c.isalnum() else "_" for c in (nome or ""))
    while "__" in pulito:
        pulito = pulito.replace("__", "_")
    return pulito.strip("_") or "voce"

# Ogni quanto si ripubblica lo stato anche se non e' cambiato nulla: serve a
# ripopolare Home Assistant dopo un suo riavvio.
HEARTBEAT = 30

# Ritardo prima di rispondere al messaggio di nascita di Home Assistant. La
# sua documentazione lo raccomanda: al riavvio tutti i dispositivi MQTT della
# casa sentono lo stesso annuncio nello stesso istante, e se rispondessero
# tutti insieme il broker prenderebbe una raffica. Un ritardo casuale li
# sparpaglia. Con un dispositivo solo e' ininfluente, ma costa due righe.
BIRTH_DELAY = (0.5, 2.5)


def _slug(text):
    out = "".join(ch if ch.isalnum() else "_" for ch in str(text).lower())
    while "__" in out:
        out = out.replace("__", "_")
    return out.strip("_") or "dmd"


class HassBridge:
    """Pubblica le entita' del DMD e riceve i comandi che tornano indietro."""

    def __init__(self, cfg, bus, runtime):
        self.cfg = cfg
        self.bus = bus
        self.runtime = runtime
        self._thread = None
        self._running = False
        self._last = {}
        self._last_publish = 0.0
        self.announced = False
        # Le voci del calendario rifiuti gia' dichiarate. Le voci le decide
        # l'utente, quindi l'elenco delle entita' cambia nel tempo e va
        # ricordato: una voce rinominata lascerebbe in Home Assistant
        # un'entita' orfana che non si aggiorna piu'.
        self._rifiuti_noti = []

    # ------------------------------------------------------------------ topic

    def settings(self):
        return self.cfg.get("mqtt") or {}

    def enabled(self):
        conf = self.settings()
        return bool(conf.get("enabled") and conf.get("discovery"))

    def base(self):
        return str(self.settings().get("base_topic") or "dmd").strip("/")

    def node(self):
        return _slug(self.settings().get("node_id") or self.base())

    def prefix(self):
        return str(self.settings().get("discovery_prefix")
                   or "homeassistant").strip("/")

    def _device(self):
        return {
            "identifiers": [self.node()],
            "name": str(self.settings().get("device_name") or "kWGillo DMD Server"),
            "manufacturer": "kWGillo",
            "model": "zedmd-pi",
            "sw_version": __version__,
        }

    # -------------------------------------------------------------- discovery

    def announce(self):
        """Dichiara tutte le entita'. Ripetibile senza danni."""
        if not self.enabled():
            return False
        base, node, prefix = self.base(), self.node(), self.prefix()
        device = self._device()
        availability = getattr(self.bus, "availability_topic",
                               "%s/availability" % base)
        common = {
            "device": device,
            "availability_topic": availability,
            "payload_available": "online",
            "payload_not_available": "offline",
        }

        track = dict(common)
        track.update({
            "name": "Now Playing",
            "unique_id": "%s_nowplaying" % node,
            "object_id": "%s_nowplaying" % node,
            "state_topic": "%s/nowplaying/state" % base,
            "value_template": "{{ value_json.title | default('', true) }}",
            "json_attributes_topic": "%s/nowplaying/state" % base,
            "icon": "mdi:music-note",
        })
        self._config("sensor", "nowplaying", track)

        for key, label in SWITCHES:
            entity = dict(common)
            entity.update({
                "name": label,
                "unique_id": "%s_%s" % (node, key),
                "object_id": "%s_%s" % (node, key),
                "state_topic": "%s/service/%s/state" % (base, key),
                "command_topic": "%s/service/%s/set" % (base, key),
                "payload_on": "ON",
                "payload_off": "OFF",
                "icon": "mdi:television",
            })
            self._config("switch", key, entity)

        for key, label, icona in AZIONI:
            entity = dict(common)
            entity.update({
                "name": label,
                "unique_id": "%s_%s" % (node, key),
                "object_id": "%s_%s" % (node, key),
                "state_topic": "%s/service/%s/state" % (base, key),
                "command_topic": "%s/service/%s/set" % (base, key),
                "payload_on": "ON",
                "payload_off": "OFF",
                "icon": icona,
            })
            self._config("switch", key, entity)

        self._annuncia_rifiuti(common, base, node)
        self._annuncia_scadenze(common, base, node)

        for key, label in MODES:
            entity = dict(common)
            entity.update({
                "name": label,
                "unique_id": "%s_%s" % (node, key),
                "object_id": "%s_%s" % (node, key),
                "state_topic": "%s/service/%s/state" % (base, key),
                "command_topic": "%s/service/%s/set" % (base, key),
                "payload_on": "ON",
                "payload_off": "OFF",
                "icon": "mdi:weather-night" if key.startswith("night")
                        else "mdi:power-sleep",
            })
            self._config("switch", key, entity)

        brightness = dict(common)
        brightness.update({
            "name": "Luminosità",
            "unique_id": "%s_brightness" % node,
            "object_id": "%s_brightness" % node,
            "state_topic": "%s/brightness/state" % base,
            "command_topic": "%s/brightness/set" % base,
            "min": 0, "max": 100, "step": 1,
            "unit_of_measurement": "%",
            "icon": "mdi:brightness-6",
        })
        self._config("number", "brightness", brightness)

        self.announced = True
        return True

    def _config(self, component, object_id, payload):
        topic = "%s/%s/%s/%s/config" % (self.prefix(), component,
                                        self.node(), object_id)
        self.bus.publish(topic, json.dumps(payload, ensure_ascii=False),
                         retain=True)

    def remove(self):
        """Cancella le entita' da Home Assistant (payload vuoto e ritenuto)."""
        # Le voci del calendario si prendono da _rifiuti_noti e non dalla
        # configurazione di adesso: da cancellare e' quello che e' stato
        # davvero dichiarato, anche se nel frattempo una voce e' sparita.
        noti = list(self._rifiuti_noti)
        scad = [("sensor", "scad_%s" % k) for k, _, _, _ in self.SCADENZE]
        for component, object_id in ([("sensor", "nowplaying"),
                                      ("number", "brightness")] +
                                     [("switch", key) for key, _ in SWITCHES] +
                                     [("switch", key) for key, _ in MODES] +
                                     [("switch", key) for key, _, _ in AZIONI] +
                                     [("binary_sensor", "rif_%s" % c) for c in noti] +
                                     [("sensor", "rifdata_%s" % c) for c in noti] +
                                     scad):
            topic = "%s/%s/%s/%s/config" % (self.prefix(), component,
                                            self.node(), object_id)
            self.bus.publish(topic, "", retain=True)
        self._rifiuti_noti = []
        self.announced = False

    # ------------------------------------------------------------------ stato

    def publish_state(self, force=False):
        if not self.enabled():
            return
        base = self.base()
        state = self.runtime.nowplaying.snapshot()
        payload = json.dumps({
            "title": state["title"],
            "artist": state["artist"],
            "album": state["album"],
            "playing": state["playing"],
            "source": state["source"],
            "client": state["client"],
            "position": round(state["position"], 1),
            "duration": round(state["duration"], 1),
        }, ensure_ascii=False)
        self._send("%s/nowplaying/state" % base, payload, force)

        services = self.cfg.get("services") or {}
        for key, _label in SWITCHES:
            value = "ON" if services.get(key) else "OFF"
            self._send("%s/service/%s/state" % (base, key), value, force)

        display = self.cfg.get("display") or {}
        for key, _label in MODES:
            value = "ON" if display.get(key) else "OFF"
            self._send("%s/service/%s/state" % (base, key), value, force)

        for key, _label, _icona in AZIONI:
            self._send("%s/service/%s/state" % (base, key),
                       "ON" if self._azione_accesa(key) else "OFF", force)

        self._pubblica_rifiuti(base, force)
        self._pubblica_scadenze(base, force)

        self._send("%s/brightness/state" % base,
                   str(self.cfg["display"]["brightness"]), force)

    def _send(self, topic, payload, force):
        """Pubblica solo se il valore e' cambiato, salvo battito periodico.

        Su un broker condiviso con Home Assistant, ripubblicare venti volte
        al secondo lo stesso testo e' rumore inutile.
        """
        if not force and self._last.get(topic) == payload:
            return
        self._last[topic] = payload
        self.bus.publish(topic, payload, retain=True)

    # ------------------------------------------------------------------ comandi

    def subscribe(self):
        base = self.base()
        self.bus.subscribe("%s/service/+/set" % base, self._on_service)
        self.bus.subscribe("%s/brightness/set" % base, self._on_brightness)
        # Le scadenze si possono anche **inserire** da Home Assistant: e' la
        # sola parte del progetto in cui i dati viaggiano anche all'indietro.
        self.bus.subscribe("%s/scadenze/aggiungi" % base, self._on_scadenza)
        self.bus.subscribe("%s/scadenze/completa" % base, self._on_scadenza_fatta)
        # Home Assistant annuncia da solo quando riparte: pubblica "online"
        # su <prefisso>/status. E' il segnale esatto per ridichiarare le
        # entita', e non richiede di sapere dove sia ne' di sorvegliarlo.
        self.bus.subscribe("%s/status" % self.prefix(), self._on_hass_status)

    def _on_hass_status(self, _topic, payload):
        raw = payload.decode("utf-8", "replace") if isinstance(payload, bytes) \
            else str(payload)
        if raw.strip().lower() != "online":
            return
        print("[hass] Home Assistant e' ripartito: ridichiaro le entita'")
        threading.Timer(random.uniform(*BIRTH_DELAY), self.reannounce).start()

    def reannounce(self):
        """Ridichiara tutto e ripubblica lo stato per intero.

        Serve al messaggio di nascita di Home Assistant e al pulsante della
        web UI. `_last` viene svuotato apposta: senza, la pubblicazione
        selettiva salterebbe i valori che a noi risultano gia' inviati ma che
        dall'altra parte nessuno ha piu'.
        """
        if not self.enabled():
            return False
        self._last.clear()
        if not self.announce():
            return False
        self.publish_state(force=True)
        return True

    # ------------------------------------------------------------- rifiuti

    def _rifiuti(self):
        """Lo stato del calendario, o una lista vuota se qualcosa non va.

        Home Assistant e' un accessorio: un file delle eccezioni scritto male
        non deve far cadere il ponte e portarsi via anche la musica.
        """
        try:
            import rifiuti
            return rifiuti.stato(self.cfg)
        except Exception as exc:
            print("[hass] calendario rifiuti: %s" % exc)
            return []

    # ------------------------------------------------------------- scadenze
    #
    # Qui la scelta e' l'opposto di quella dei rifiuti. Le frazioni sono sei e
    # non cambiano mai, quindi hanno un'entita' ciascuna. Le scadenze nascono e
    # muoiono, e una entita' per scadenza vorrebbe dire un elenco che si
    # sporca di entita' orfane a ogni bolletta pagata.
    #
    # Quindi: **poche entita' fisse piu' un attributo JSON con l'elenco**. E'
    # il modo con cui Home Assistant fa queste cose, e permette a una card o a
    # un template di leggere tutto senza che noi si debba indovinare in
    # anticipo che cosa serve.
    SCADENZE = (
        ("prossima", "Prossima scadenza", "mdi:calendar-clock", "date"),
        ("titolo", "Prossima scadenza (titolo)", "mdi:label-outline", ""),
        ("giorni", "Giorni alla scadenza", "mdi:calendar-range", ""),
        ("semaforo", "Semaforo scadenze", "mdi:traffic-light", ""),
        ("aperte", "Scadenze aperte", "mdi:format-list-checks", ""),
    )

    def _annuncia_scadenze(self, common, base, node):
        for chiave, etichetta, icona, classe in self.SCADENZE:
            entita = dict(common)
            entita.update({
                "name": etichetta,
                "unique_id": "%s_scad_%s" % (node, chiave),
                "object_id": "%s_scad_%s" % (node, chiave),
                "state_topic": "%s/scadenze/%s" % (base, chiave),
                "icon": icona,
            })
            if classe:
                entita["device_class"] = classe
            if chiave == "aperte":
                # L'elenco completo viaggia come attributi di questa entita':
                # un solo topic, e in Home Assistant si legge con
                # state_attr('sensor.dmd_scad_aperte', 'elenco').
                entita["json_attributes_topic"] = "%s/scadenze/elenco" % base
                entita["unit_of_measurement"] = ""
            self._config("sensor", "scad_%s" % chiave, entita)

    def _pubblica_scadenze(self, base, force):
        try:
            import json as _json
            import scadenze
            elenco = scadenze.elenco(self.cfg)
            stato = scadenze.semaforo(self.cfg)
        except Exception as exc:
            print("[hass] scadenze non leggibili: %s" % exc)
            return
        prima = elenco[0] if elenco else None
        # In ISO, non nel formato italiano: e' quello che Home Assistant si
        # aspetta da un sensore con device_class "date".
        self._send("%s/scadenze/prossima" % base,
                   prima["data"].isoformat() if prima else "", force)
        self._send("%s/scadenze/titolo" % base,
                   prima["titolo"] if prima else "", force)
        self._send("%s/scadenze/giorni" % base,
                   str(prima["giorni"]) if prima else "", force)
        self._send("%s/scadenze/semaforo" % base, stato, force)
        self._send("%s/scadenze/aperte" % base, str(len(elenco)), force)
        self._send("%s/scadenze/elenco" % base, _json.dumps({
            "elenco": [{
                "id": v["id"], "titolo": v["titolo"],
                "descrizione": v["descrizione"],
                "data": v["data"].isoformat(), "giorni": v["giorni"],
                "stato": v["stato"], "cadenza": v["cadenza"],
            } for v in elenco],
        }, ensure_ascii=False), force)

    def _on_scadenza(self, topic, payload):
        """Una scadenza che arriva **da** Home Assistant.

        Il payload e' JSON: {"titolo": ..., "data": "gg/mm/aaaa",
        "cadenza": "mensile", "descrizione": ...}. Serve a creare una scadenza
        da un'automazione o da un assistente vocale, senza aprire la pagina.

        Tutto avvolto: un payload sbagliato non deve fermare il ponte, e
        nemmeno finire in configurazione come una scadenza senza data.
        """
        try:
            import json as _json
            import scadenze
            grezzo = payload.decode("utf-8", "replace") if isinstance(payload, bytes) \
                else str(payload)
            dati = _json.loads(grezzo)
            if not isinstance(dati, dict):
                raise ValueError("payload non e' un oggetto")
            voce = scadenze.aggiungi(dati.get("titolo", ""), dati.get("data", ""),
                                     dati.get("cadenza", ""),
                                     dati.get("descrizione", ""),
                                     str(dati.get("id", "")))
            if voce is None:
                print("[hass] scadenza rifiutata: data mancante o illeggibile")
            else:
                print("[hass] scadenza aggiunta da Home Assistant: %s" % voce["titolo"])
        except Exception as exc:
            print("[hass] scadenza non aggiunta: %s" % exc)
        self.publish_state(force=True)

    def _on_scadenza_fatta(self, topic, payload):
        """Segna completata una scadenza, dal suo id."""
        try:
            import scadenze
            identificativo = payload.decode("utf-8", "replace").strip() \
                if isinstance(payload, bytes) else str(payload).strip()
            if scadenze.completa(identificativo):
                print("[hass] scadenza completata da Home Assistant: %s"
                      % identificativo)
            else:
                print("[hass] scadenza %r non trovata" % identificativo)
        except Exception as exc:
            print("[hass] completamento non riuscito: %s" % exc)
        self.publish_state(force=True)

    def _annuncia_rifiuti(self, common, base, node):
        """Un binary_sensor e un sensor per ogni voce del calendario.

        Non si manda il calendario, si manda **l'evento**: il binary_sensor
        dice se in questo momento va esposto, il sensor quando tocca la
        prossima volta. Con quei due si scrive un'automazione in tre righe,
        senza integrazioni aggiuntive e senza un secondo posto in cui i dati
        possano divergere dal pannello.
        """
        visti = []
        for voce in self._rifiuti():
            chiave = slug(voce["nome"])
            visti.append(chiave)
            icona = ICONE_RIFIUTI.get(voce["nome"].strip().lower(),
                                      "mdi:trash-can-outline")
            esposizione = dict(common)
            esposizione.update({
                "name": voce["nome"],
                "unique_id": "%s_rif_%s" % (node, chiave),
                "object_id": "%s_rif_%s" % (node, chiave),
                "state_topic": "%s/rifiuti/%s/state" % (base, chiave),
                "payload_on": "ON", "payload_off": "OFF",
                "icon": icona,
            })
            self._config("binary_sensor", "rif_%s" % chiave, esposizione)

            prossima = dict(common)
            prossima.update({
                "name": "%s prossima" % voce["nome"],
                "unique_id": "%s_rifdata_%s" % (node, chiave),
                "object_id": "%s_rifdata_%s" % (node, chiave),
                "state_topic": "%s/rifiuti/%s/prossima" % (base, chiave),
                "device_class": "date",
                "icon": icona,
            })
            self._config("sensor", "rifdata_%s" % chiave, prossima)
        # Una voce rinominata o tolta lascerebbe in Home Assistant un'entita'
        # che non si aggiorna piu' e che nessuno sa da dove viene.
        for vecchia in [c for c in self._rifiuti_noti if c not in visti]:
            for componente, prefisso in (("binary_sensor", "rif_"),
                                         ("sensor", "rifdata_")):
                self.bus.publish("%s/%s/%s/%s%s/config"
                                 % (self.prefix(), componente, self.node(),
                                    prefisso, vecchia), "", retain=True)
        self._rifiuti_noti = visti

    def _pubblica_rifiuti(self, base, force):
        for voce in self._rifiuti():
            chiave = slug(voce["nome"])
            self._send("%s/rifiuti/%s/state" % (base, chiave),
                       "ON" if voce["esposizione"] else "OFF", force)
            self._send("%s/rifiuti/%s/prossima" % (base, chiave),
                       voce["prossima"].isoformat() if voce["prossima"] else "",
                       force)

    def _azione_accesa(self, key):
        """Stato di un'azione, chiesto a chi la sta facendo.

        Non si legge dalla configurazione, perche' li' non c'e' niente: una
        partita e' qualcosa che sta succedendo. Cosi' una chiusura per
        inattivita' o un avvio fallito riportano l'interruttore a OFF da soli.
        """
        try:
            if key == "doom":
                doom = getattr(self.runtime, "doom", None)
                return bool(doom and doom.in_sessione())
            if key.startswith(GIOCO_PREFISSO):
                giochi = getattr(self.runtime, "giochi", None)
                if giochi is None or not giochi.in_sessione():
                    return False
                return giochi.gioco_corrente() == key[len(GIOCO_PREFISSO):]
        except Exception:
            return False
        return False

    def _azione(self, key, acceso):
        """Esegue un'azione. Restituisce True se e' stata gestita."""
        if key == "doom":
            cosa, nome = "doom", ""
        elif key.startswith(GIOCO_PREFISSO):
            cosa, nome = "giochi", key[len(GIOCO_PREFISSO):]
        else:
            return False
        try:
            if acceso:
                # Non si apre la sessione direttamente: passa dal runtime, che
                # e' l'unico a sapere che Doom e i giochi si contendono la
                # stessa presa del pannello e che aprirne una vuol dire
                # chiudere l'altra.
                self.runtime.gioca(cosa, nome)
            else:
                self.runtime.smetti(cosa)
        except Exception as exc:
            print("[hass] %s: %s" % (key, exc))
        # Lo stato vero lo dice la sorgente, non il comando: se la partita non
        # e' partita — WAD sbagliato, programma non compilato — Home Assistant
        # deve tornare a OFF da solo invece di restare acceso a vuoto.
        self.publish_state(force=True)
        return True

    def _on_service(self, topic, payload):
        parts = topic.split("/")
        if len(parts) < 3:
            return
        key = parts[-2]
        wanted = payload.decode("utf-8", "replace").strip().upper() \
            if isinstance(payload, bytes) else str(payload).strip().upper()
        acceso = wanted in ("ON", "1", "TRUE")

        if self._azione(key, acceso):
            return

        modi = dict(MODES)
        if key in modi:
            # Night e Sleep non sono servizi da avviare o fermare: sono modi
            # del display, che il ciclo di rendering rilegge da solo a ogni
            # secondo. Qui basta scrivere il valore.
            self.cfg["display"][key] = acceso
        elif key in self.cfg.get("services", {}):
            self.cfg["services"][key] = acceso
        else:
            return

        try:
            import dmdconf
            dmdconf.save()
            if key not in modi:
                self.runtime.arbiter.apply_services()
        except Exception as exc:
            print("[hass] comando su %s non applicato: %s" % (key, exc))
        self.publish_state(force=True)

    def _on_brightness(self, _topic, payload):
        raw = payload.decode("utf-8", "replace") if isinstance(payload, bytes) \
            else str(payload)
        try:
            self.runtime.set_brightness(int(float(raw.strip())))
        except (TypeError, ValueError):
            return
        self.publish_state(force=True)

    # ------------------------------------------------------------------ ciclo

    def start(self):
        """Avvia il ponte, oppure ne riallinea le sottoscrizioni.

        E' richiamabile piu' volte: dopo un cambio di impostazioni il bus
        viene ricostruito e le sottoscrizioni vanno rifatte, ma il thread di
        pubblicazione deve restare uno solo.
        """
        self.subscribe()
        self.bus.on_connect(self._on_connect)
        # Il bus puo' essere gia' connesso quando si arriva qui: in quel caso
        # la callback di connessione non scattera' mai piu' da sola, e senza
        # questa riga le entita' non verrebbero mai dichiarate.
        if getattr(self.bus, "connected", False):
            self._on_connect()
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="hass",
                                        daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _on_connect(self):
        # Alla riconnessione Home Assistant potrebbe aver dimenticato tutto:
        # si ridichiara e si ripubblica lo stato per intero.
        self.reannounce()

    def _loop(self):
        while self._running:
            try:
                now = time.time()
                force = now - self._last_publish >= HEARTBEAT
                if force:
                    self._last_publish = now
                self.publish_state(force=force)
            except Exception as exc:
                print("[hass] errore nella pubblicazione: %s" % exc)
            time.sleep(2)
