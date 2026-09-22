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

import ota
from version import __version__

# Servizi esposti come interruttori. La chiave e' quella in `cfg["services"]`.
# Come si dice "non lo so" a Home Assistant. Non e' la stringa vuota: per un
# sensore tipizzato `""` e' un errore, e per uno non tipizzato diventa uno
# stato vuoto invece che sconosciuto. La documentazione dell'integrazione MQTT
# dice che la stringa `None` porta il sensore a `unknown`, ed e' questa.
NIENTE = "None"


# I tre livelli, come entita' notify separate. Il nome e' quello che si legge
# nella tendina di Home Assistant: "DMD - avviso" dice da solo cosa fara' il
# pannello, mentre un unico "DMD" avrebbe richiesto di ricordare un campo.
NOTIFY = [
    ("info", "DMD - info", "mdi:message-outline"),
    ("avviso", "DMD - avviso", "mdi:alert-outline"),
    ("allarme", "DMD - allarme", "mdi:alert"),
]

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
    ("satelliti", "Satelliti"),
    ("notifiche", "Notifiche"),
    ("meteo", "Meteo"),
    # La sveglia e' un servizio come gli altri: l'interruttore dice se gli
    # orari valgono, non se sta squillando adesso. Per fermare uno squillo in
    # corso c'e' l'azione, piu' sotto -- sono due cose diverse e vanno tenute
    # separate, altrimenti spegnere la sveglia di stamattina cancellerebbe
    # anche quella di domani.
    ("sveglia", "Sveglia"),
    # Il servizio OnAir: dice se il pannello deve occuparsi della diretta,
    # non se la diretta e' in corso. Per quello c'e' `onair_diretta`, piu'
    # sotto -- sono due cose diverse, come la sveglia e il suo squillo.
    ("onair", "OnAir"),
    ("moon", "Moon"),
]

# Night mode e Sleep mode non sono servizi: sono modi del display, e stanno in
# un'altra sezione della configurazione. Da Home Assistant pero' si comandano
# allo stesso modo, quindi hanno gli stessi topic e la stessa forma — cambia
# solo dove va scritto il valore.
#
# Ogni riga: chiave del topic, etichetta, chiave nella configurazione, e se
# **ON in Home Assistant corrisponde a falso** nella configurazione. Il
# rovesciamento serve a una sola voce ed e' l'unico modo onesto di scriverla:
# la configurazione dice `off`, perche' il valore normale di un impianto e'
# "acceso" e le impostazioni si scrivono come eccezioni; Home Assistant invece
# deve mostrare un interruttore che si chiama "Display" e che quando e' ON
# significa che il pannello e' acceso. Nessuno accetterebbe un interruttore
# chiamato "Display spento" da tenere OFF.
MODES = [
    ("night_enabled", "Night mode", "night_enabled", False),
    ("sleep_enabled", "Sleep mode", "sleep_enabled", False),
    ("display_acceso", "Display", "off", True),
]

# Le icone dei modi, per chiave.
ICONE_MODI = {
    "night_enabled": "mdi:weather-night",
    "sleep_enabled": "mdi:power-sleep",
    "display_acceso": "mdi:monitor",
}

# Interruttori che non corrispondono a una voce di configurazione ma a
# **qualcosa che sta succedendo**. Doom non e' un servizio da accendere: e' una
# partita che comincia e finisce, e puo' finire da sola per inattivita'. Lo
# stato quindi non si legge dalla configurazione — li' non c'e' — ma dal
# runtime, e va ripubblicato quando cambia da solo, altrimenti Home Assistant
# resta convinto che si stia ancora giocando.
AZIONI = [
    ("doom", "Doom", "mdi:pistol"),
    # Il Game Boy era rimasto fuori, e per una ragione che si vede solo
    # guardando da dove arrivano gli altri: i giochi scritti per il pannello
    # si costruiscono dall'elenco di `sources.giochi`, e PyBoy non e' in
    # quell'elenco -- e' un runtime a se', con il suo processo e le sue
    # cartucce. Acceso da qui parte con la ROM configurata, come premere il
    # tasto della console senza cambiare cartuccia.
    ("gameboy", "Game Boy", "mdi:nintendo-game-boy"),
    # Fermare la sveglia che sta squillando. E' un'azione e non un
    # interruttore perche' non ha uno stato da mantenere: si preme mentre
    # suona, e dopo non c'e' niente da tenere acceso. Il pulsante fisico della
    # Funcam fa la stessa cosa; questo serve dall'altra stanza.
    ("sveglia_stop", "Ferma la sveglia", "mdi:alarm-off"),
    # La diretta. E' l'entita' che un'automazione di Home Assistant accende
    # quando il sensore della porta si chiude: il DMD non sa che esista una
    # porta, sa solo se e' in onda. Sta fra le azioni e non fra i servizi
    # perche' non e' una voce di configurazione da accendere una volta -- e'
    # uno stato che va e viene, e che si legge dalla sorgente.
    ("onair_diretta", "In onda", "mdi:record-circle"),
]

# I volumi come cursori: (chiave, nome in Home Assistant, icona) e dove stanno
# in configurazione. Tutti fra 0 e 1 in configurazione, in percento fuori.
VOLUMI = [
    ("avvisi", "Volume avvisi", "mdi:volume-medium"),
    ("giochi", "Volume giochi", "mdi:gamepad-variant"),
    ("notte", "Volume notturno", "mdi:volume-low"),
]
VOLUMI_DOVE = {
    "avvisi": ("audio", "volume", 0.7),
    "giochi": ("audio", "volume_giochi", 0.9),
    "notte": ("display", "night_volume", 0.0),
}

# Il computer di Pongo, come tendina: le voci sono quelle della pagina Giochi.
PONGO_LIVELLI = (("facile", "Facile"), ("normale", "Normale"),
                 ("difficile", "Difficile"))

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
    "snake": "mdi:snake",
    "pongo": "mdi:table-tennis",
    "squadriglia": "mdi:airplane",
    "gnam": "mdi:pac-man",
    "mine": "mdi:star-four-points-outline",
    "trex": "mdi:run-fast",
    "bongo": "mdi:city-variant-outline",
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
        # Un aggiornamento e' gia' stato avviato da qui. Non torna mai a
        # falso da solo, e va bene cosi': o il servizio riparte -- e allora
        # questo oggetto e' nuovo -- oppure non riparte, e non c'e' nessuno
        # che possa premere un pulsante due volte.
        self._ota_in_corso = False

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
            # Quando non suona niente il titolo e' vuoto, e un sensore con
            # stato "" in Home Assistant compare bianco, come se fosse rotto.
            # Si dice `None`, come gli altri: HA lo traduce in *sconosciuto*.
            # E' l'ultimo pezzo della correzione della 6.1, che allora si era
            # fermata ai topic e non aveva guardato i template.
            "value_template": "{{ value_json.title | default('%s', true) }}" % NIENTE,
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

        for key, label, _chiave, _rovescio in MODES:
            entity = dict(common)
            entity.update({
                "name": label,
                "unique_id": "%s_%s" % (node, key),
                "object_id": "%s_%s" % (node, key),
                "state_topic": "%s/service/%s/state" % (base, key),
                "command_topic": "%s/service/%s/set" % (base, key),
                "payload_on": "ON",
                "payload_off": "OFF",
                "icon": ICONE_MODI.get(key, "mdi:toggle-switch"),
            })
            self._config("switch", key, entity)

        # La luminosita' e' l'unica entita' con **due** condizioni di
        # disponibilita', e non e' un vezzo: e' la correzione di un comando che
        # mentiva. Con Night mode acceso il pannello usa la luminosita'
        # notturna, e quello principale non fa niente -- si muoveva, non
        # cambiava niente, e faceva pensare che il pannello fosse guasto. Un
        # comando che non agisce e' peggio di un comando assente.
        #
        # `availability_mode: all` vuol dire che devono valere tutte e due: il
        # DMD acceso **e** il Night mode spento. In Home Assistant il cursore
        # diventa grigio per la durata della fascia notturna, che e'
        # esattamente quello che sta succedendo.
        brightness = dict(common)
        brightness.pop("availability_topic", None)
        brightness.update({
            "name": "Luminosità",
            "unique_id": "%s_brightness" % node,
            "object_id": "%s_brightness" % node,
            "state_topic": "%s/brightness/state" % base,
            "command_topic": "%s/brightness/set" % base,
            "min": 0, "max": 100, "step": 1,
            "unit_of_measurement": "%",
            "icon": "mdi:brightness-6",
            "availability_mode": "all",
            "availability": [
                {"topic": availability,
                 "payload_available": "online",
                 "payload_not_available": "offline"},
                {"topic": "%s/brightness/available" % base,
                 "payload_available": "online",
                 "payload_not_available": "offline"},
            ],
        })
        self._config("number", "brightness", brightness)

        # I tre volumi, come cursori. Sono quelli della pagina Impostazioni e
        # della scheda Timing, con la stessa scala in percento: un'automazione
        # che abbassa gli avvisi la sera o alza i giochi quando si gioca non
        # deve passare dalla pagina web.
        for chiave, nome, icona in VOLUMI:
            entity = dict(common)
            entity.update({
                "name": nome,
                "unique_id": "%s_volume_%s" % (node, chiave),
                "object_id": "%s_volume_%s" % (node, chiave),
                "state_topic": "%s/volume/%s/state" % (base, chiave),
                "command_topic": "%s/volume/%s/set" % (base, chiave),
                "min": 0, "max": 100, "step": 5,
                "unit_of_measurement": "%",
                "icon": icona,
            })
            self._config("number", "volume_%s" % chiave, entity)

        # Il livello del computer di Pongo, come tendina: la stessa della
        # pagina Giochi, e vale anche a partita aperta dalla battuta dopo.
        pongo = dict(common)
        pongo.update({
            "name": "Pongo: computer",
            "unique_id": "%s_pongo_livello" % node,
            "object_id": "%s_pongo_livello" % node,
            "state_topic": "%s/pongo/livello/state" % base,
            "command_topic": "%s/pongo/livello/set" % base,
            "options": [etichetta for _chiave, etichetta in PONGO_LIVELLI],
            "icon": "mdi:table-tennis",
        })
        self._config("select", "pongo_livello", pongo)

        # ------------------------------------------------- aerei e satelliti
        #
        # I numeri che il DMD gia' conosce e teneva per se'. Il radar scrive
        # un registro da millesettecento righe e i satelliti calcolano
        # ventiquattro ore di passaggi: fino a qui si vedevano solo sul
        # pannello e nella pagina web, cioe' solo se eri li' a guardare.
        radar = dict(common)
        radar.update({
            "name": "Aerei oggi",
            "unique_id": "%s_aerei_oggi" % node,
            "object_id": "%s_aerei_oggi" % node,
            "state_topic": "%s/radar/oggi" % base,
            "state_class": "total_increasing",
            "icon": "mdi:airplane",
        })
        self._config("sensor", "aerei_oggi", radar)

        # Il totale del registro. `aerei_oggi` risponde a "che giornata e'
        # stata", questo a "quanti ne ho visti da quando l'ho acceso": e' il
        # numero che cresce e non torna indietro, quello da mettere su una
        # scheda e guardare ogni tanto.
        totale = dict(common)
        totale.update({
            "name": "Aerei in totale",
            "unique_id": "%s_aerei_totale" % node,
            "object_id": "%s_aerei_totale" % node,
            "state_topic": "%s/radar/totale" % base,
            "state_class": "total_increasing",
            "icon": "mdi:counter",
        })
        self._config("sensor", "aerei_totale", totale)

        # Il meteo. Cinque valori, e nessuno di questi e' un doppione di quello
        # che Home Assistant sa gia': chi ha una stazione meteo in giardino ha
        # il dato **misurato** in un punto, questo e' quello **previsto** per le
        # prossime ore, che e' la cosa su cui si costruiscono le automazioni --
        # chiudere la tapparella prima del temporale, non dopo.
        for chiave, etichetta, topic, extra in (
                ("meteo_temperatura", "Temperatura", "adesso",
                 {"device_class": "temperature", "unit_of_measurement": "°C",
                  "state_class": "measurement"}),
                ("meteo_umidita", "Umidità", "umidita",
                 {"device_class": "humidity", "unit_of_measurement": "%",
                  "state_class": "measurement"}),
                ("meteo_massima", "Massima di oggi", "massima",
                 {"device_class": "temperature", "unit_of_measurement": "°C"}),
                ("meteo_minima", "Minima di oggi", "minima",
                 {"device_class": "temperature", "unit_of_measurement": "°C"}),
                ("meteo_condizione", "Condizione", "condizione",
                 {"icon": "mdi:weather-partly-cloudy",
                  "json_attributes_topic": "%s/meteo/dettaglio" % base}),
                # L'allerta e' l'unica entita' meteo per cui valga la pena
                # scrivere un'automazione che **fa** qualcosa invece di
                # mostrare un numero: chiudere una tapparella, spegnere
                # l'irrigazione, mandare un messaggio a chi e' fuori.
                ("meteo_allerta", "Allerta", "allerta",
                 {"icon": "mdi:weather-lightning-rainy",
                  "json_attributes_topic": "%s/meteo/allerta_dettaglio" % base}),
        ):
            entity = dict(common)
            entity.update({
                "name": etichetta,
                "unique_id": "%s_%s" % (node, chiave),
                "object_id": "%s_%s" % (node, chiave),
                "state_topic": "%s/meteo/%s" % (base, topic),
            })
            entity.update(extra)
            self._config("sensor", chiave, entity)

        raggio = dict(common)
        raggio.update({
            "name": "Aerei nel raggio",
            "unique_id": "%s_aerei_raggio" % node,
            "object_id": "%s_aerei_raggio" % node,
            "state_topic": "%s/radar/raggio" % base,
            "state_class": "measurement",
            "icon": "mdi:radar",
        })
        self._config("sensor", "aerei_raggio", raggio)

        ultimo = dict(common)
        ultimo.update({
            "name": "Ultimo aereo",
            "unique_id": "%s_ultimo_aereo" % node,
            "object_id": "%s_ultimo_aereo" % node,
            "state_topic": "%s/radar/ultimo" % base,
            "value_template": "{{ value_json.volo | default('%s', true) }}" % NIENTE,
            "json_attributes_topic": "%s/radar/ultimo" % base,
            "icon": "mdi:airplane-marker",
        })
        self._config("sensor", "ultimo_aereo", ultimo)

        # Il passaggio della Stazione: lo **stato e' l'orario**, cosi' in Home
        # Assistant si legge "fra due ore" invece di una stringa da
        # interpretare, e un'automazione puo' agganciarcisi con un trigger
        # sull'ora. Gli attributi portano l'elenco delle prossime ventiquattro
        # ore: e' la richiesta -- sapere dei passaggi **con un giorno di
        # anticipo** e non dieci minuti prima.
        iss = dict(common)
        iss.update({
            "name": "Prossimo passaggio",
            "unique_id": "%s_iss_prossimo" % node,
            "object_id": "%s_iss_prossimo" % node,
            "state_topic": "%s/satelliti/prossimo" % base,
            "device_class": "timestamp",
            "json_attributes_topic": "%s/satelliti/elenco" % base,
            "icon": "mdi:satellite-variant",
        })
        self._config("sensor", "iss_prossimo", iss)

        quanti = dict(common)
        quanti.update({
            "name": "Passaggi in 24 ore",
            "unique_id": "%s_iss_quanti" % node,
            "object_id": "%s_iss_quanti" % node,
            "state_topic": "%s/satelliti/quanti" % base,
            "state_class": "measurement",
            "icon": "mdi:orbit",
        })
        self._config("sensor", "iss_quanti", quanti)

        # --------------------------------------------------------- notifiche
        #
        # Il pannello si dichiara come **entita' notify**, una per livello.
        # Cosi' in Home Assistant compare accanto al telefono nel selettore
        # dei bersagli: si sceglie da una tendina invece di chiamare uno
        # script, e il livello e' la scelta del bersaglio invece di un campo
        # da ricordare.
        #
        # Tre topic invece di un `command_template` che costruisca il JSON:
        # il DMD accetta **testo semplice** come notifica valida, quindi il
        # livello puo' stare nel topic e non serve nessun template. Una cosa
        # in meno che possa avere un errore di battitura, e una prova in meno
        # da scrivere.
        for livello, etichetta, icona in NOTIFY:
            voce = dict(common)
            voce.update({
                "name": etichetta,
                "unique_id": "%s_notify_%s" % (node, livello),
                "object_id": "%s_notify_%s" % (node, livello),
                "command_topic": "%s/%s" % (self._topic_notifiche(), livello),
                "icon": icona,
            })
            self._config("notify", "notify_%s" % livello, voce)

        # ---------------------------------------------------- aggiornamenti
        #
        # Home Assistant ha un tipo di entita' fatto apposta, `update`, e usarlo
        # invece di un sensore acceso/spento cambia parecchio: il pannello
        # finisce nella stessa lista in cui HA mette gli aggiornamenti del
        # sistema e degli add-on, con "installata 9.9 -> disponibile 9.10", le
        # note di rilascio e il pulsante. Un `binary_sensor` chiamato
        # "Aggiornamento disponibile" avrebbe fatto sapere la stessa cosa e
        # sarebbe stato in un posto dove nessuno la cerca.
        #
        # Il `command_topic` c'e' e il pulsante funziona. **Non e' un
        # aggiornamento automatico**: e' una pressione, come quella sulla
        # pagina web, solo fatta dal divano. Che poi qualcuno possa scriverci
        # sopra un'automazione e' vero, ed e' una sua scelta da prendere con
        # gli occhi aperti -- non una che prendiamo noi di nascosto ogni notte.
        aggiornamento = dict(common)
        aggiornamento.update({
            "name": "Aggiornamento",
            "unique_id": "%s_aggiornamento" % node,
            "object_id": "%s_aggiornamento" % node,
            "state_topic": "%s/ota/state" % base,
            "command_topic": "%s/ota/install" % base,
            "payload_install": "INSTALL",
            "device_class": "firmware",
        })
        self._config("update", "aggiornamento", aggiornamento)

        # Com'e' finito l'ultimo aggiornamento. Esiste per una ragione sola:
        # il ripristino automatico funziona, e proprio per questo un
        # aggiornamento fallito non si vedeva -- il pannello la mattina dopo
        # era acceso e sulla versione di prima, identico a uno che non era
        # mai partito. Qui si vede, e ci si puo' attaccare un'automazione.
        esito = dict(common)
        esito.update({
            "name": "Ultimo aggiornamento",
            "unique_id": "%s_ota_esito" % node,
            "object_id": "%s_ota_esito" % node,
            "state_topic": "%s/ota/esito" % base,
            "json_attributes_topic": "%s/ota/esito_dettaglio" % base,
            "icon": "mdi:history",
        })
        self._config("sensor", "ota_esito", esito)

        self.announced = True
        return True

    def _topic_notifiche(self):
        """Il topic delle notifiche, senza barre di troppo."""
        conf = self.cfg.get("notifiche") or {}
        return str(conf.get("topic") or "dmd/notifica").strip("/")

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
                                      ("number", "brightness"),
                                      ("number", "volume_avvisi"),
                                      ("number", "volume_giochi"),
                                      ("number", "volume_notte"),
                                      ("update", "aggiornamento"),
                                      ("sensor", "ota_esito")] +
                                     [("notify", "notify_%s" % k)
                                      for k, _, _ in NOTIFY] +
                                     [("sensor", k) for k in
                                      ("aerei_oggi", "aerei_totale",
                                       "aerei_raggio", "ultimo_aereo",
                                       "iss_prossimo", "iss_quanti",
                                       "meteo_temperatura", "meteo_umidita",
                                       "meteo_massima", "meteo_minima",
                                       "meteo_condizione", "meteo_allerta")] +
                                     [("switch", key) for key, _ in SWITCHES] +
                                     [("switch", key) for key, _, _, _ in MODES] +
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

        self._pubblica_cielo(base, force)

        services = self.cfg.get("services") or {}
        for key, _label in SWITCHES:
            value = "ON" if services.get(key) else "OFF"
            self._send("%s/service/%s/state" % (base, key), value, force)

        display = self.cfg.get("display") or {}
        for key, _label, chiave, rovescio in MODES:
            acceso = bool(display.get(chiave))
            if rovescio:
                acceso = not acceso
            self._send("%s/service/%s/state" % (base, key),
                       "ON" if acceso else "OFF", force)

        for key, _label, _icona in AZIONI:
            self._send("%s/service/%s/state" % (base, key),
                       "ON" if self._azione_accesa(key) else "OFF", force)

        self._pubblica_rifiuti(base, force)
        self._pubblica_scadenze(base, force)

        self._send("%s/brightness/state" % base,
                   str(self.cfg["display"]["brightness"]), force)
        # Durante il Night mode il cursore non ha effetto, e lo si dice invece
        # di lasciarlo muovere a vuoto. Si guarda il **runtime**, non la
        # configurazione: `night_enabled` e' solo la fascia oraria, `night` e'
        # se in questo momento ci siamo dentro davvero.
        notte = bool(getattr(self.runtime, "night", False))
        self._send("%s/brightness/available" % base,
                   "offline" if notte else "online", force)

        for chiave, _nome, _icona in VOLUMI:
            self._send("%s/volume/%s/state" % (base, chiave),
                       str(self._volume(chiave)), force)
        self._send("%s/pongo/livello/state" % base, self._pongo_livello(), force)

        self._pubblica_ota(base, force)

    def _pongo_livello(self):
        """Il livello del computer di Pongo, con l'etichetta della tendina."""
        scelto = (self.cfg.get("giochi") or {}).get("pongo_livello", "normale")
        for chiave, etichetta in PONGO_LIVELLI:
            if chiave == scelto:
                return etichetta
        return "Normale"

    def _volume(self, chiave):
        """Un volume in percento, intero, come lo mostra la pagina."""
        sezione, campo, predefinito = VOLUMI_DOVE[chiave]
        try:
            valore = float((self.cfg.get(sezione) or {}).get(campo, predefinito))
        except (TypeError, ValueError):
            valore = predefinito
        return int(round(max(0.0, min(1.0, valore)) * 100))

    def _pubblica_ota(self, base, force):
        """Versione installata, versione disponibile, esito dell'ultima volta."""
        info = getattr(self.runtime, "update_info", None) or {}
        installata = str(info.get("current") or __version__)
        # Quando il controllo non e' riuscito -- rete assente, API a limite --
        # si dice che l'ultima disponibile **e' quella installata**, non una
        # stringa vuota. Un'entita' update senza `latest_version` in Home
        # Assistant compare come guasta, e un controllo non riuscito non e' un
        # guasto del pannello: e' semplicemente una notizia che non e'
        # arrivata, e nel dubbio la cosa onesta e' non annunciare niente.
        stato = {"installed_version": installata,
                 "latest_version": str(info.get("latest") or installata)}
        if info.get("url"):
            stato["release_url"] = str(info["url"])
        note = ota.riassunto(info.get("note") or "")
        if note:
            stato["release_summary"] = note
        self._send("%s/ota/state" % base,
                   json.dumps(stato, ensure_ascii=False), force)

        ultimo = ota.ultimo_esito() or {}
        self._send("%s/ota/esito" % base, str(ultimo.get("esito") or NIENTE), force)
        self._send("%s/ota/esito_dettaglio" % base,
                   json.dumps({"atteso": ultimo.get("atteso", ""),
                               "attiva": ultimo.get("attiva", ""),
                               "motivo": ultimo.get("motivo", ""),
                               "quando": ultimo.get("quando", 0)},
                              ensure_ascii=False), force)

    def _pubblica_cielo(self, base, force):
        """Aerei e satelliti verso Home Assistant.

        Non fa cadere niente se una sorgente non c'e' o non e' pronta: questi
        sono numeri di contorno, e un servizio spento non deve impedire la
        pubblicazione di tutto il resto.
        """
        try:
            radar = self.runtime.radar.riepilogo()
        except Exception:                       # noqa: BLE001
            radar = None
        if radar is not None:
            self._send("%s/radar/oggi" % base, str(radar["oggi"]), force)
            self._send("%s/radar/raggio" % base, str(radar["nel_raggio"]), force)
            self._send("%s/radar/totale" % base,
                       str(radar.get("totale") or 0), force)
            # Un oggetto JSON anche quando e' vuoto: gli attributi di Home
            # Assistant devono essere un oggetto, e `{}` e' un oggetto.
            self._send("%s/radar/ultimo" % base,
                       json.dumps(radar["ultimo"] or {}, ensure_ascii=False),
                       force)

        try:
            previsione = self.runtime.meteo.riepilogo()
        except Exception:                       # noqa: BLE001
            previsione = None
        if previsione is not None:
            for topic, chiave in (("adesso", "temperatura"),
                                  ("umidita", "umidita"),
                                  ("massima", "massima"),
                                  ("minima", "minima")):
                valore = previsione.get(chiave)
                # `None` e non stringa vuota: e' la lezione della 6.1, pagata
                # con cinquanta righe di registro in Home Assistant al giorno.
                self._send("%s/meteo/%s" % (base, topic),
                           NIENTE if valore is None else str(valore), force)
            self._send("%s/meteo/condizione" % base,
                       previsione.get("descrizione") or NIENTE, force)
            self._send("%s/meteo/dettaglio" % base,
                       json.dumps(previsione, ensure_ascii=False), force)
            # Lo stato dell'allerta e' il **livello**, non il testo: e' la
            # parola su cui si scrive una condizione in un'automazione, ed e'
            # normalizzata. Il testo, la zona e gli orari stanno negli
            # attributi, dove servono a chi legge e non a chi decide.
            avviso = previsione.get("allerta")
            self._send("%s/meteo/allerta" % base,
                       (avviso or {}).get("livello") or NIENTE, force)
            self._send("%s/meteo/allerta_dettaglio" % base,
                       json.dumps(avviso or {}, ensure_ascii=False), force)

        try:
            passaggi = self.runtime.satelliti.riepilogo()
        except Exception:                       # noqa: BLE001
            passaggi = None
        if passaggi is not None:
            visibili = [p for p in passaggi if p["visibile"]]
            prossimo = visibili[0] if visibili else None
            # Lo stato e' l'orario in ISO con il fuso: e' quello che vuole un
            # sensore `device_class: timestamp`, ed e' cio' che permette a Home
            # Assistant di scrivere "fra due ore" da solo. Niente passaggi
            # visibili: `None`, che diventa *sconosciuto*.
            self._send("%s/satelliti/prossimo" % base,
                       prossimo["sorge"] if prossimo else NIENTE, force)
            self._send("%s/satelliti/quanti" % base, str(len(passaggi)), force)
            self._send("%s/satelliti/elenco" % base, json.dumps({
                "prossimo": prossimo or {},
                "visibili": len(visibili),
                "passaggi": passaggi,
            }, ensure_ascii=False), force)

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
        self.bus.subscribe("%s/volume/+/set" % base, self._on_volume)
        self.bus.subscribe("%s/pongo/livello/set" % base, self._on_pongo_livello)
        # Le scadenze si possono anche **inserire** da Home Assistant: e' la
        # sola parte del progetto in cui i dati viaggiano anche all'indietro.
        self.bus.subscribe("%s/scadenze/aggiungi" % base, self._on_scadenza)
        self.bus.subscribe("%s/scadenze/completa" % base, self._on_scadenza_fatta)
        self.bus.subscribe("%s/ota/install" % base, self._on_ota_install)
        # Home Assistant annuncia da solo quando riparte: pubblica "online"
        # su <prefisso>/status. E' il segnale esatto per ridichiarare le
        # entita', e non richiede di sapere dove sia ne' di sorvegliarlo.
        self.bus.subscribe("%s/status" % self.prefix(), self._on_hass_status)

    def _on_ota_install(self, _topic, payload):
        """Il pulsante Installa dell'entita' update.

        Due rifiuti espliciti, ed e' la parte importante. Non si installa se
        il controllo non ha trovato niente di nuovo -- un topic ritenuto o un
        pulsante premuto due volte non deve riscrivere `/opt/dmd` per il gusto
        di farlo. E non si installa se un aggiornamento e' gia' in corso.
        """
        raw = payload.decode("utf-8", "replace") if isinstance(payload, bytes) \
            else str(payload)
        if raw.strip().upper() not in ("INSTALL", "ON", "PRESS"):
            return
        info = getattr(self.runtime, "update_info", None) or {}
        if not info.get("available"):
            print("[hass] installazione richiesta, ma non risulta niente di nuovo")
            return
        if self._ota_in_corso:
            print("[hass] installazione gia' in corso, richiesta ignorata")
            return
        self._ota_in_corso = True
        print("[hass] installazione della versione %s richiesta da Home Assistant"
              % info.get("latest"))
        try:
            ota.dimentica_esito()
            ota.start_update(self.cfg, info.get("tag", ""))
        except Exception as exc:                # noqa: BLE001
            self._ota_in_corso = False
            print("[hass] non riesco ad avviare l'aggiornamento: %s" % exc)

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
        # Due regole, tutte e due di Home Assistant e tutte e due imparate a
        # spese nostre.
        #
        # **In ISO**, non nel formato italiano: e' quello che si aspetta un
        # sensore con device_class "date".
        #
        # **Il niente si dice `None`, non stringa vuota.** Per un sensore
        # tipizzato `""` non e' una data, e Home Assistant scrive
        # `Invalid state message '' from 'dmd/scadenze/prossima'` -- cinquanta
        # righe di registro in dieci minuti, viste sul campo. La
        # documentazione dice che il valore che porta un sensore a `unknown`
        # e' la stringa `None`.
        #
        # Vale anche per i sensori **senza** device_class, dove non da'
        # errore: con `""` lo stato diventa una stringa vuota invece di
        # `unknown`, e sono due cose diverse: chi scrive
        # `is_state(..., 'unknown')` in un'automazione non lo vedrebbe
        # scattare mai.
        self._send("%s/scadenze/prossima" % base,
                   prima["data"].isoformat() if prima else NIENTE, force)
        self._send("%s/scadenze/titolo" % base,
                   prima["titolo"] if prima else NIENTE, force)
        self._send("%s/scadenze/giorni" % base,
                   str(prima["giorni"]) if prima else NIENTE, force)
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
                       voce["prossima"].isoformat() if voce["prossima"]
                       else NIENTE, force)

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
            if key == "gameboy":
                gameboy = getattr(self.runtime, "gameboy", None)
                return bool(gameboy and gameboy.in_sessione())
            if key == "onair_diretta":
                onair = getattr(self.runtime, "onair", None)
                return bool(onair and onair.in_onda())
            if key == "sveglia_stop":
                # Acceso vuol dire "c'e' qualcosa da fermare": cosi' in Home
                # Assistant l'interruttore si accende da solo quando la
                # sveglia squilla, e si puo' costruirci sopra un'automazione
                # senza dover inventare un sensore in piu'.
                sveglia = getattr(self.runtime, "sveglia", None)
                return bool(sveglia and sveglia.suonando())
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
        if key == "onair_diretta":
            # Qui l'interruttore vale nei due versi, al contrario di
            # `sveglia_stop`: non e' un pulsante, e' lo specchio della porta.
            # Spegnendolo la diretta finisce davvero.
            onair = getattr(self.runtime, "onair", None)
            if onair is not None:
                onair.imposta(acceso)
            self.publish_state(force=True)
            return True
        if key == "sveglia_stop":
            # Solo lo spegnimento fa qualcosa: "accendere" una sveglia da qui
            # vorrebbe dire farla squillare adesso, che non e' quello che
            # chiede chi tocca un interruttore chiamato "ferma la sveglia".
            if not acceso:
                sveglia = getattr(self.runtime, "sveglia", None)
                if sveglia is not None:
                    sveglia.zittisci()
            self.publish_state(force=True)
            return True
        if key == "doom":
            cosa, nome = "doom", ""
        elif key == "gameboy":
            # Nome vuoto: la sorgente prende la cartuccia gia' configurata.
            cosa, nome = "gameboy", ""
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

        modi = {k: (chiave, rovescio) for k, _l, chiave, rovescio in MODES}
        if key in modi:
            # Night, Sleep e l'accensione del pannello non sono servizi da
            # avviare o fermare: sono modi del display, che il ciclo di
            # rendering rilegge da solo a ogni secondo. Qui basta scrivere il
            # valore, eventualmente rovesciato.
            chiave, rovescio = modi[key]
            self.cfg["display"][chiave] = (not acceso) if rovescio else acceso
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
        # Dichiarare l'entita' non disponibile ferma l'interfaccia di Home
        # Assistant, non un'automazione che pubblichi sul topic lo stesso.
        # Qui si rifiuta comunque: accettare e non applicare sarebbe di nuovo
        # il comando che mente, solo un piano piu' sotto.
        if getattr(self.runtime, "night", False):
            print("[hass] luminosita' ignorata: Night mode attivo")
            self.publish_state(force=True)
            return
        try:
            self.runtime.set_brightness(int(float(raw.strip())))
        except (TypeError, ValueError):
            return
        self.publish_state(force=True)

    def _on_volume(self, topic, payload):
        """Un volume da Home Assistant: si salva e vale subito.

        Il volume dei giochi arriva anche alle partite aperte, per la stessa
        strada della pagina Impostazioni.
        """
        chiave = topic.rsplit("/", 2)[-2] if "/" in topic else ""
        if chiave not in VOLUMI_DOVE:
            return
        raw = payload.decode("utf-8", "replace") if isinstance(payload, bytes) \
            else str(payload)
        try:
            percento = max(0.0, min(100.0, float(raw.strip())))
        except (TypeError, ValueError):
            return
        sezione, campo, _predefinito = VOLUMI_DOVE[chiave]
        try:
            self.cfg.setdefault(sezione, {})[campo] = round(percento / 100.0, 2)
            import dmdconf
            dmdconf.save()
            if chiave == "giochi":
                import suoni
                suoni.diffondi_volume_giochi(self.cfg, self.runtime)
        except Exception as exc:
            print("[hass] volume %s non applicato: %s" % (chiave, exc))
        self.publish_state(force=True)

    def _on_pongo_livello(self, _topic, payload):
        """Il livello di Pongo da Home Assistant: come la tendina della
        pagina, si salva e vale dalla battuta successiva."""
        raw = payload.decode("utf-8", "replace") if isinstance(payload, bytes) \
            else str(payload)
        voluto = raw.strip().lower()
        if voluto not in [chiave for chiave, _e in PONGO_LIVELLI]:
            return
        try:
            self.cfg.setdefault("giochi", {})["pongo_livello"] = voluto
            import dmdconf
            dmdconf.save()
            giochi = getattr(self.runtime, "giochi", None)
            if hasattr(giochi, "riconfigura"):
                giochi.riconfigura()
        except Exception as exc:
            print("[hass] livello di Pongo non applicato: %s" % exc)
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
