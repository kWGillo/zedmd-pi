"""Gestione della configurazione persistente del DMD.

La configurazione vive in un unico file JSON. Ogni modifica dalla web UI
viene scritta subito su disco, cosi' sopravvive al riavvio.
"""

import json
import os
import threading

CONFIG_PATH = os.environ.get("DMD_CONFIG", "/etc/dmd/config.json")

DEFAULTS = {
    "panel": {
        "rows": 64,
        "cols": 128,
        "chain": 2,
        "parallel": 1,
        "hardware_mapping": "regular",
        "slowdown": 3,
        "panel_type": "fm6373",
        "spwm_row_address_type": 1,
        "spwm_scan_rows": 64,
        "spwm_data_layout": 0,
        "spwm_register_config": 2,
        "limit_refresh": 60,
        "pwm_bits": 11,
        # Durata del bit meno significativo. Accorciarla riduce il tempo di
        # un frame intero, quindi alza il refresh senza togliere profondita'.
        "pwm_lsb_nanoseconds": 130,
        # Bit bassi resi con dithering temporale invece che con tempo di
        # accensione: 1 bit di dithering raddoppia il refresh a parita' di
        # profondita' dichiarata.
        "pwm_dither_bits": 0,
        "profile_dir": "/home/gillo/rpi-rgb-led-matrix_pwm_experiment/lib/spwm/registertest/data",
        "show_refresh": False,
        # Cartella del fork della libreria matrice. Vuoto = dedotta da
        # profile_dir, che ne e' una sottocartella.
        "library_dir": "",
        # Regolazioni fini del driver S-PWM, applicate come variabili d'ambiente.
        # Vuoto = valore predefinito della libreria.
        "spwm_env": {
            "SPWM_END_OF_FRAME_EXTRA_ROW_CYCLES": "",
            "SPWM_FRAME_END_SLEEP_US": "",
        },
    },
    "display": {
        "brightness": 50,
        "night_enabled": False,
        "night_start": "22:00",
        "night_end": "07:00",
        "night_brightness": 15,
        "sleep_enabled": False,
        "sleep_start": "01:00",
        "sleep_end": "06:00",
        "sleep_wake_on_zedmd": True,
    },
    "clock": {
        "time_color": "#ff8c1a",
        "date_color": "#00a0d0",
        "format_24h": True,
        "show_date": True,
        "language": "it",
        "blink_colon": True,
    },
    "mediaplayer": {
        "media_dir": "/srv/dmd/media",
        "min_interval": 20,
        "max_interval": 30,
        "image_duration": 5,
        "video_duration": 8,
        "video_fps": 20,
        "scale_mode": "fit",
        "pixel_art": True,
    },
    "banner": {
        "min_interval": 30,
        "max_interval": 60,
        "fps": 30,
        "shuffle": False,
        # Dieci caselle, riempite al primo caricamento da sources.banner.
        "items": [],
    },
    "air_radar": {
        # Nessuna posizione preimpostata: va indicata dall'utente nella web UI.
        # Il servizio non interroga nulla finche' le coordinate sono a zero.
        "latitude": 0.0,
        "longitude": 0.0,
        "radius_km": 3.0,
        "provider": "adsb.fi",
        "poll_interval": 30,
        "display_seconds": 10,
        "cooldown": 600,
        "max_altitude_ft": 0,
        "log_route": True,
        "fields": ["route", "type", "altitude", "speed", "distance"],
        "log_enabled": True,
        "log_path": "/var/lib/dmd/flights.csv",
        "callsign_color": "#00d0ff",
        "info_color": "#ff8c1a",
    },
    "mqtt": {
        # Predefinito: un Mosquitto sul Raspberry stesso. Cosi' la funzione
        # lavora senza Home Assistant. Chi ha gia' un broker sotto Home
        # Assistant mette qui quell'indirizzo e ottiene le due cose insieme.
        "enabled": False,
        "host": "127.0.0.1",
        "port": 1883,
        "username": "",
        "password": "",
        "client_id": "dmd",
        "base_topic": "dmd",
        # Topic su cui shairport-sync pubblica i metadati AirPlay.
        "shairport_topic": "shairport",
        # Topic facoltativo su cui qualsiasi altra cosa (tipicamente
        # un'automazione di Home Assistant) puo' scrivere un JSON con il
        # brano corrente. Vuoto = non si ascolta nulla.
        "external_topic": "dmd/external/nowplaying",
        # Entita' create automaticamente in Home Assistant.
        "discovery": True,
        "discovery_prefix": "homeassistant",
        "node_id": "dmd",
        "device_name": "DMD Controller",
    },
    "nowplaying": {
        # Quanto resta a schermo un brano in pausa prima di lasciare il posto.
        "hold_seconds": 90,
        "title_color": "#ffffff",
        "artist_color": "#00ffff",
        "album_color": "#0000ff",
        "bar_color": "#ffff00",
        # Ogni componente portata a 0 o 255: restano gli otto colori pieni,
        # gli unici che su questo pannello non producono sfarfallio.
        "safe_colors": True,
    },
    "spotify": {
        # Copre la musica che non passa da AirPlay: Spotify Connect verso
        # casse vere, il computer, un Echo. I token non stanno qui ma in
        # /var/lib/dmd/spotify.json, per non finire in un export condiviso.
        "enabled": False,
        "client_id": "",
        "redirect_uri": "http://127.0.0.1:8080/api/spotify/callback",
        "poll_interval": 8,
    },
    "time": {
        "ntp_server": "pool.ntp.org",
        "timezone": "Europe/Rome",
        "dst_auto": True,
        "utc_offset": 1,
    },
    "web": {
        "port": 8080,
        # Lingua dell'interfaccia: "it", "en", oppure vuoto per lasciar
        # decidere al browser tramite Accept-Language. Non ha effetto sul
        # testo mostrato sul pannello, che segue clock.language.
        "language": "",
    },
    "ota": {
        "repo": "kWGillo/zedmd-pi",
        "branch": "main",
        "auto_check": True,
        "check_interval_hours": 24,
    },
    "services": {
        "zedmd": True,
        "clock": True,
        "mediaplayer": False,
        "banner": False,
        "nowplaying": False,
        "status_player": False,
        "air_radar": False,
    },
    "zedmd": {
        "stream_port": 3333,
        "http_port": 80,
        "transport": "TCP",
        "grace_seconds": 60,
        "client_timeout": 10,
        "device_name": "ZeDMD-Pi",
        "firmware_version": "6.0.0",
    },
    "arbiter": {
        "force_source": "auto",
    },
}

_lock = threading.Lock()
_config = None


def _merge(base, override):
    """Fonde ricorsivamente l'override sui default, senza perdere chiavi nuove."""
    out = {}
    for key, value in base.items():
        if isinstance(value, dict):
            out[key] = _merge(value, (override or {}).get(key, {}))
        else:
            out[key] = (override or {}).get(key, value)
    return out


def _migrate(raw):
    """Adegua configurazioni scritte da versioni precedenti."""
    services = raw.setdefault("services", {})
    # 1.0 aveva un unico servizio "mediaplayer_clock".
    if "mediaplayer_clock" in services:
        legacy = bool(services.pop("mediaplayer_clock"))
        services.setdefault("clock", legacy)
        services.setdefault("mediaplayer", False)
    if raw.get("arbiter", {}).get("force_source") == "mediaplayer_clock":
        raw["arbiter"]["force_source"] = "clock"
    if raw.get("web", {}).get("port") == 80:
        raw["web"]["port"] = 8080

    # 1.9: le dieci caselle del Rolling banner devono esserci sempre, anche
    # in una configurazione salvata prima che la funzione esistesse.
    from sources.banner import normalize_list
    banner = raw.setdefault("banner", {})
    banner["items"] = normalize_list(banner.get("items"))

    # 1.10: il servizio Now Playing deve comparire fra i toggle anche in una
    # configurazione salvata prima che esistesse, altrimenti la pagina Servizi
    # non lo mostra e non lo si puo' accendere.
    services.setdefault("nowplaying", False)
    return raw


def load():
    global _config
    with _lock:
        if _config is not None:
            return _config
        raw = {}
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH) as handle:
                    raw = json.load(handle)
            except (OSError, ValueError):
                raw = {}
        _config = _merge(DEFAULTS, _migrate(raw))
        return _config


def get():
    return load()


def _apply_in_place(target, source):
    """Riversa `source` dentro `target` senza cambiare l'identita' dei dizionari.

    Le sorgenti tengono un riferimento alla configurazione e ai suoi rami
    (`self.cfg`, `cfg["air_radar"]`, ...). Sostituire il dizionario con uno
    nuovo lascerebbe meta' del programma a guardare quello vecchio: qui si
    aggiorna il contenuto, non il contenitore.
    """
    for key in list(target):
        if key not in source:
            del target[key]
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _apply_in_place(target[key], value)
        else:
            target[key] = value


KNOWN_SECTIONS = set(DEFAULTS)


def looks_like_config(raw):
    """Un file di configurazione plausibile, non un JSON qualsiasi."""
    if not isinstance(raw, dict):
        return False
    return bool(KNOWN_SECTIONS & set(raw))


def replace(raw):
    """Sostituisce la configurazione con quella indicata e la salva.

    Il contenuto passa dagli stessi `_migrate` e `_merge` del caricamento
    normale: un file salvato da una versione precedente viene adeguato, e le
    chiavi che non conosciamo vengono ignorate invece di far danni.
    """
    if not looks_like_config(raw):
        raise ValueError("il file non contiene una configurazione del DMD")
    merged = _merge(DEFAULTS, _migrate(dict(raw)))
    with _lock:
        if _config is None:
            raise RuntimeError("configurazione non ancora caricata")
        _apply_in_place(_config, merged)
    save()
    return _config


def snapshot(include_position=True):
    """Copia della configurazione da esportare.

    Senza `include_position` le coordinate del radar tornano a zero: un file
    di configurazione condiviso o allegato a una segnalazione non deve
    portarsi dietro l'indirizzo di casa.

    La password del broker MQTT viene tolta sempre, senza opzione. Un file di
    configurazione gira: finisce in un backup, in un allegato, in una
    segnalazione. Chi lo reimporta riscrive la password una volta sola; se
    invece fosse dentro, basterebbe una disattenzione per regalarla. I token
    di Spotify non compaiono qui affatto: vivono in un file loro.
    """
    import copy
    data = copy.deepcopy(load())
    if not include_position:
        data["air_radar"]["latitude"] = 0.0
        data["air_radar"]["longitude"] = 0.0
    if isinstance(data.get("mqtt"), dict):
        data["mqtt"]["password"] = ""
    return data


def save():
    with _lock:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        tmp = CONFIG_PATH + ".tmp"
        with open(tmp, "w") as handle:
            json.dump(_config, handle, indent=2)
        os.replace(tmp, CONFIG_PATH)
