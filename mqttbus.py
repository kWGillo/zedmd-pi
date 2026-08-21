"""Collegamento MQTT del DMD.

Un solo client per tutto il sistema. Da qui passano due flussi opposti:

  in ingresso   i metadati di shairport-sync (che cosa sta suonando)
  in uscita     le entita' di Home Assistant (che cosa sta facendo il DMD)

Il broker puo' essere ovunque. Il predefinito e' `127.0.0.1`, cioe' un
Mosquitto installato sul Raspberry stesso: cosi' la funzione lavora senza
Home Assistant, che resta una possibilita' e non un requisito. Chi invece ha
gia' Mosquitto sotto Home Assistant scrive quell'indirizzo e ottiene le due
cose insieme.

`paho-mqtt` e' una dipendenza facoltativa: se manca, il modulo non solleva
nulla all'importazione e `available()` risponde di no. Il resto del DMD
continua a funzionare, e la pagina web spiega che cosa installare invece di
mostrare una schermata di errore.
"""

import threading
import time

# La libreria puo' non esserci: e' una dipendenza in piu' rispetto a un DMD
# che non usa MQTT, e non deve impedire l'avvio del servizio.
try:
    import paho.mqtt.client as mqtt
    _IMPORT_ERROR = ""
except Exception as exc:            # pragma: no cover - dipende dal sistema
    mqtt = None
    _IMPORT_ERROR = str(exc)

# Pacchetto da installare quando manca, mostrato nella web UI.
PACKAGE = "python3-paho-mqtt"

# Tempo massimo fra due tentativi di riconnessione.
RECONNECT_MAX = 60


def available():
    """True se la libreria MQTT e' installata."""
    return mqtt is not None


def import_error():
    return _IMPORT_ERROR


def _new_client(client_id):
    """Client compatibile con paho-mqtt 1.x e 2.x.

    La 2.0 ha cambiato la firma delle callback e pretende che si dichiari
    quale versione dell'API si vuole. Chiedendo esplicitamente la 1 il resto
    del modulo resta uguale su entrambe, invece di avere due rami di codice.
    """
    try:
        return mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=client_id)
    except (AttributeError, TypeError):
        return mqtt.Client(client_id=client_id)


class MqttBus:
    """Client MQTT con riconnessione automatica e sottoscrizioni per prefisso."""

    def __init__(self, cfg):
        self.cfg = cfg
        self._client = None
        self._lock = threading.Lock()
        self._handlers = []            # (topic con caratteri jolly, funzione)
        self._on_connect = []          # da richiamare a ogni (ri)connessione

        self.connected = False
        self.error = ""
        self.last_message = 0.0
        self.messages = 0
        self.started = False

    # ------------------------------------------------------------------ stato

    def settings(self):
        return self.cfg.get("mqtt") or {}

    def status(self):
        """Riepilogo per la pagina web."""
        conf = self.settings()
        return {
            "available": available(),
            "package": PACKAGE,
            "import_error": import_error(),
            "enabled": bool(conf.get("enabled")),
            "host": conf.get("host", ""),
            "port": conf.get("port", 1883),
            "connected": self.connected,
            "error": self.error,
            "messages": self.messages,
            "last_message": self.last_message,
        }

    # ------------------------------------------------------------ registrazioni

    def subscribe(self, topic, handler):
        """Registra un gestore per un topic, anche con caratteri jolly.

        Si puo' chiamare prima di `start()`: le sottoscrizioni vengono
        rifatte a ogni riconnessione, quindi l'ordine non conta. Registrare
        due volte la stessa coppia non la duplica: chi riallinea le proprie
        sottoscrizioni dopo un cambio di impostazioni non deve preoccuparsi
        di averlo gia' fatto.
        """
        with self._lock:
            if (topic, handler) in self._handlers:
                return
            self._handlers.append((topic, handler))
        client = self._client
        if client is not None and self.connected:
            try:
                client.subscribe(topic)
            except Exception:
                pass

    def on_connect(self, callback):
        """Da eseguire a ogni connessione riuscita (es. discovery di HA)."""
        if callback not in self._on_connect:
            self._on_connect.append(callback)

    # ------------------------------------------------------------------ avvio

    def start(self):
        conf = self.settings()
        if not conf.get("enabled"):
            return False
        if not available():
            self.error = "paho-mqtt non installato"
            return False
        if self.started:
            return True

        host = str(conf.get("host") or "").strip()
        if not host:
            self.error = "indirizzo del broker non impostato"
            return False

        client = _new_client(str(conf.get("client_id") or "dmd"))
        user = str(conf.get("username") or "")
        if user:
            client.username_pw_set(user, str(conf.get("password") or ""))

        # Testamento: se il DMD sparisce senza salutare, il broker avvisa al
        # posto suo e in Home Assistant le entita' diventano "non disponibili"
        # invece di restare congelate sull'ultimo valore.
        base = str(conf.get("base_topic") or "dmd").strip("/")
        self.availability_topic = "%s/availability" % base
        client.will_set(self.availability_topic, "offline", retain=True)

        client.on_connect = self._handle_connect
        client.on_disconnect = self._handle_disconnect
        client.on_message = self._handle_message
        try:
            client.reconnect_delay_set(min_delay=1, max_delay=RECONNECT_MAX)
        except Exception:
            pass

        self._client = client
        self.error = ""
        try:
            client.connect_async(host, int(conf.get("port") or 1883),
                                 keepalive=60)
            client.loop_start()
        except Exception as exc:
            self.error = str(exc)
            self._client = None
            return False

        self.started = True
        return True

    def stop(self):
        client, self._client = self._client, None
        self.started = False
        self.connected = False
        if client is None:
            return
        try:
            client.publish(getattr(self, "availability_topic", "dmd/availability"),
                           "offline", retain=True)
            client.loop_stop()
            client.disconnect()
        except Exception:
            pass

    def restart(self):
        """Riapre la connessione dopo un cambio di impostazioni."""
        self.stop()
        time.sleep(0.1)
        return self.start()

    # ------------------------------------------------------------------ invio

    def publish(self, topic, payload, retain=False, qos=0):
        client = self._client
        if client is None:
            return False
        try:
            client.publish(topic, payload, qos=qos, retain=retain)
            return True
        except Exception as exc:
            self.error = str(exc)
            return False

    # ------------------------------------------------------------------ callback

    def _handle_connect(self, client, _userdata, _flags, rc, *_args):
        if rc != 0:
            self.connected = False
            self.error = "connessione rifiutata (codice %s)" % rc
            return
        self.connected = True
        self.error = ""
        print("[mqtt] connesso a %s:%s" % (self.settings().get("host"),
                                           self.settings().get("port")))
        try:
            client.publish(self.availability_topic, "online", retain=True)
        except Exception:
            pass
        with self._lock:
            topics = [topic for topic, _ in self._handlers]
        for topic in topics:
            try:
                client.subscribe(topic)
            except Exception:
                pass
        for callback in list(self._on_connect):
            try:
                callback()
            except Exception as exc:
                print("[mqtt] errore in una callback di connessione: %s" % exc)

    def _handle_disconnect(self, _client, _userdata, rc, *_args):
        self.connected = False
        if rc != 0:
            self.error = "connessione caduta (codice %s)" % rc
            print("[mqtt] disconnesso (codice %s), riprovo" % rc)

    def _handle_message(self, _client, _userdata, message):
        self.messages += 1
        self.last_message = time.time()
        with self._lock:
            handlers = list(self._handlers)
        for topic, handler in handlers:
            if _matches(topic, message.topic):
                try:
                    handler(message.topic, message.payload)
                except Exception as exc:
                    print("[mqtt] errore su %s: %s" % (message.topic, exc))


def _matches(pattern, topic):
    """Confronto fra un topic e un filtro MQTT con `+` e `#`."""
    if pattern == topic:
        return True
    parts = pattern.split("/")
    actual = topic.split("/")
    for index, part in enumerate(parts):
        if part == "#":
            # `#` copre tutto il resto, ma solo se e' l'ultimo livello.
            return index == len(parts) - 1
        if index >= len(actual):
            return False
        if part != "+" and part != actual[index]:
            return False
    return len(parts) == len(actual)
