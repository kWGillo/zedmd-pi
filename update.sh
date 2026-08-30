#!/bin/bash
#
# Aggiornamento di un'installazione esistente.
# Copia i file, adegua la configurazione e riavvia il servizio.
#   sudo ./update.sh
#
set -e

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

# Prima di toccare l'installazione funzionante, controlla che il pacchetto sia
# arrivato intero. Un file corrotto in silenzio costa molto piu' tempo di
# questa verifica.
if [ -f "$SRC_DIR/manifest.md5" ]; then
    bash "$SRC_DIR/verify.sh" "$SRC_DIR" || {
        echo
        echo "Aggiornamento interrotto: l'installazione attuale non e' stata toccata."
        exit 1
    }
fi

echo "==> Copia dei file in /opt/dmd"
mkdir -p /opt/dmd
cp -r "$SRC_DIR"/*.py "$SRC_DIR"/*.csv "$SRC_DIR"/templates \
      "$SRC_DIR"/static /opt/dmd/
cp -r "$SRC_DIR"/sources /opt/dmd/
# 3.0: sorgenti e script di Doom. Il binario compilato non si tocca — sta
# nella stessa cartella ma non e' nostro, e ricompilarlo a ogni aggiornamento
# vorrebbe dire due minuti di attesa per niente.
if [ -d "$SRC_DIR/doom" ]; then
    mkdir -p /opt/dmd/doom
    cp "$SRC_DIR"/doom/doomgeneric_dmd.c "$SRC_DIR"/doom/Makefile \
       "$SRC_DIR"/doom/setup_doom.sh /opt/dmd/doom/
    chmod +x /opt/dmd/doom/setup_doom.sh
fi
mkdir -p /var/lib/dmd

echo "==> Adeguamento della configurazione"
python3 - <<'PYEOF'
import json, os

path = "/etc/dmd/config.json"
if not os.path.exists(path):
    print("    nessuna configurazione esistente, verrà creata al primo avvio")
    raise SystemExit(0)

with open(path) as handle:
    cfg = json.load(handle)

web = cfg.setdefault("web", {})
zedmd = cfg.setdefault("zedmd", {})

# La porta 80 ora è del server dell'handshake ZeDMD: la web UI trasloca.
if web.get("port", 8080) == 80:
    web["port"] = 8080
    print("    web.port: 80 -> 8080")
zedmd.setdefault("http_port", 80)
zedmd.setdefault("transport", "TCP")

# 1.7: lingua della web UI. Vuoto = la decide il browser.
if "language" not in web:
    web["language"] = ""
    print("    web.language: aggiunta (rilevata dal browser)")

# 1.0 aveva un unico servizio "mediaplayer_clock": ora sono due.
services = cfg.setdefault("services", {})
if "mediaplayer_clock" in services:
    legacy = bool(services.pop("mediaplayer_clock"))
    services.setdefault("clock", legacy)
    services.setdefault("mediaplayer", False)
    print("    servizi: mediaplayer_clock -> clock + mediaplayer")
if cfg.get("arbiter", {}).get("force_source") == "mediaplayer_clock":
    cfg["arbiter"]["force_source"] = "clock"

# 1.9: servizio Rolling banner e cartella della libreria matrice.
# Va dopo la creazione di `services`, non prima.
if "banner" not in services:
    services["banner"] = False
    print("    servizi: aggiunto il Rolling banner")
cfg.setdefault("banner", {})
cfg.setdefault("panel", {}).setdefault("library_dir", "")

# 1.9.4: leve per alzare il refresh senza perdere profondita' di colore.
cfg.setdefault("panel", {}).setdefault("pwm_lsb_nanoseconds", 130)
cfg["panel"].setdefault("pwm_dither_bits", 0)

# 1.10: Now Playing, bus MQTT, Spotify. Il broker predefinito e' locale,
# cosi' la funzione lavora anche senza Home Assistant.
if "nowplaying" not in services:
    services["nowplaying"] = False
    print("    servizi: aggiunto Now Playing")
for section, values in (
    ("mqtt", {"enabled": False, "host": "127.0.0.1", "port": 1883,
              "username": "", "password": "", "client_id": "dmd",
              "base_topic": "dmd", "shairport_topic": "shairport",
              "external_topic": "dmd/external/nowplaying",
              "discovery": True, "discovery_prefix": "homeassistant",
              "node_id": "dmd", "device_name": "DMD Controller"}),
    ("nowplaying", {"hold_seconds": 90, "advance_timeout": 600,
                    "title_color": "#ffffff",
                    "artist_color": "#00ffff", "album_color": "#0000ff",
                    "bar_color": "#ffff00", "safe_colors": True}),
    ("spotify", {"enabled": False, "client_id": "", "poll_interval": 8,
                 "redirect_uri": "http://127.0.0.1:8080/api/spotify/callback"}),
):
    branch = cfg.setdefault(section, {})
    for key, value in values.items():
        branch.setdefault(key, value)

# 2.0: compleanni, profilo hardware, unita' di misura del radar.
if "birthdays" not in services:
    services["birthdays"] = False
    print("    servizi: aggiunto Compleanni")
cfg.setdefault("birthdays", {})
panel = cfg.setdefault("panel", {})
panel.setdefault("preset", "custom")
radar = cfg.setdefault("air_radar", {})
radar.setdefault("unit_altitude", "ft")
radar.setdefault("unit_speed", "kt")
radar.setdefault("unit_distance", "km")

# 3.0: Doom. Il servizio nasce spento: prima va compilato, e finche' non c'e'
# il binario accenderlo non servirebbe a niente.
doom = cfg.setdefault("doom", {})
for chiave, valore in (("binary", "/var/lib/dmd/doom/doom-dmd"),
                       ("wad", "/srv/dmd/doom/freedoom1.wad"),
                       ("work_dir", "/var/lib/dmd/doom/stato"),
                       ("band_top", 36), ("band_height", 96),
                       ("gamma", 0.70), ("keyboard", True),
                       ("keyboard_device", ""), ("session_timeout", 180),
                       ("skill", 3), ("start_map", "1 1"),
                       ("keyboard_starts", False)):
    doom.setdefault(chiave, valore)

# 3.0.2: i WAD traslocano in una cartella condivisa in rete. Si corregge solo
# chi ha ancora il percorso predefinito della 3.0/3.0.1: un percorso scelto
# dall'utente non si tocca, e a spostare i file ci pensa setup_doom.sh.
if doom.get("wad") == "/var/lib/dmd/doom/freedoom1.wad":
    doom["wad"] = "/srv/dmd/doom/freedoom1.wad"
    print("    doom: i WAD passano alla cartella condivisa /srv/dmd/doom")

# 3.2: Doom non e' piu' un servizio ma una sessione. L'interruttore e la
# deroga dell'attract mode non servono piu' e vanno tolti, altrimenti restano
# a confondere chi guarda la configurazione.
services.pop("doom", None)
zedmd.pop("idle_seconds", None)

with open(path, "w") as handle:
    json.dump(cfg, handle, indent=2)
print("    configurazione aggiornata")
PYEOF

echo "==> Dipendenze per il Media Player"
MISSING=""
command -v ffmpeg >/dev/null 2>&1 || MISSING="$MISSING ffmpeg"
command -v smbd  >/dev/null 2>&1 || MISSING="$MISSING samba samba-common-bin"
# 1.10: libreria MQTT. Se manca, Now Playing resta spento e la sua pagina lo
# dice: il resto del DMD non se ne accorge nemmeno.
python3 -c "import paho.mqtt.client" >/dev/null 2>&1 || MISSING="$MISSING python3-paho-mqtt"
if [ -n "$MISSING" ]; then
    echo "    da installare:$MISSING"
    apt update
    apt install -y $MISSING
else
    echo "    ffmpeg e samba già presenti"
fi

echo "==> Libreria media e condivisione SMB"
bash "$SRC_DIR/setup_share.sh" /srv/dmd/media || true

echo "==> Verifica dei file installati"
bash "$SRC_DIR/verify.sh" /opt/dmd || {
    echo
    echo "I file sono stati scritti male durante la copia."
    echo "Non riavvio il servizio: correggi il problema e rilancia update.sh."
    exit 1
}

echo "==> Riavvio del servizio"
systemctl restart dmd
sleep 2
systemctl --no-pager --lines=15 status dmd || true

echo
echo "Aggiornamento completato."
echo "Interfaccia web:  http://<ip-del-pi>:8080/"
echo "Handshake ZeDMD:  http://<ip-del-pi>/handshake"
