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
        "profile_dir": "/home/gillo/rpi-rgb-led-matrix_pwm_experiment/lib/spwm/registertest/data",
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
    "time": {
        "ntp_server": "pool.ntp.org",
        "timezone": "Europe/Rome",
        "dst_auto": True,
        "utc_offset": 1,
    },
    "web": {
        "port": 8080,
    },
    "services": {
        "zedmd": True,
        "clock": True,
        "mediaplayer": False,
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
    services = raw.get("services", {})
    # 1.0 aveva un unico servizio "mediaplayer_clock".
    if "mediaplayer_clock" in services:
        legacy = bool(services.pop("mediaplayer_clock"))
        services.setdefault("clock", legacy)
        services.setdefault("mediaplayer", False)
    if raw.get("arbiter", {}).get("force_source") == "mediaplayer_clock":
        raw["arbiter"]["force_source"] = "clock"
    if raw.get("web", {}).get("port") == 80:
        raw["web"]["port"] = 8080
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


def save():
    with _lock:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        tmp = CONFIG_PATH + ".tmp"
        with open(tmp, "w") as handle:
            json.dump(_config, handle, indent=2)
        os.replace(tmp, CONFIG_PATH)
