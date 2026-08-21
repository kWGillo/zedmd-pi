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
    ("air_radar", "Air Radar"),
    ("clock", "Orologio"),
]

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
            "name": str(self.settings().get("device_name") or "DMD Controller"),
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
        for component, object_id in ([("sensor", "nowplaying"),
                                      ("number", "brightness")] +
                                     [("switch", key) for key, _ in SWITCHES]):
            topic = "%s/%s/%s/%s/config" % (self.prefix(), component,
                                            self.node(), object_id)
            self.bus.publish(topic, "", retain=True)
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

    def _on_service(self, topic, payload):
        parts = topic.split("/")
        if len(parts) < 3:
            return
        key = parts[-2]
        if key not in self.cfg.get("services", {}):
            return
        wanted = payload.decode("utf-8", "replace").strip().upper() \
            if isinstance(payload, bytes) else str(payload).strip().upper()
        self.cfg["services"][key] = wanted in ("ON", "1", "TRUE")
        try:
            import dmdconf
            dmdconf.save()
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
