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
cp -r "$SRC_DIR"/*.py "$SRC_DIR"/templates "$SRC_DIR"/static /opt/dmd/
cp -r "$SRC_DIR"/sources /opt/dmd/
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

with open(path, "w") as handle:
    json.dump(cfg, handle, indent=2)
print("    configurazione aggiornata")
PYEOF

echo "==> Dipendenze per il Media Player"
MISSING=""
command -v ffmpeg >/dev/null 2>&1 || MISSING="$MISSING ffmpeg"
command -v smbd  >/dev/null 2>&1 || MISSING="$MISSING samba samba-common-bin"
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
