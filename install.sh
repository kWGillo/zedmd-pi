#!/bin/bash
#
# Installazione del DMD Controller.
# Da lanciare dalla cartella scompattata:  sudo ./install.sh
#
set -e

MATRIX_DIR="${MATRIX_DIR:-$HOME/rpi-rgb-led-matrix_pwm_experiment}"
if [ -n "$SUDO_USER" ]; then
    REAL_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
    MATRIX_DIR="${MATRIX_DIR:-$REAL_HOME/rpi-rgb-led-matrix_pwm_experiment}"
    if [ ! -d "$MATRIX_DIR" ]; then
        MATRIX_DIR="$REAL_HOME/rpi-rgb-led-matrix_pwm_experiment"
    fi
fi

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Libreria matrice attesa in: $MATRIX_DIR"
if [ ! -d "$MATRIX_DIR" ]; then
    echo "ERRORE: cartella della libreria non trovata."
    echo "Impostala esplicitamente, ad esempio:"
    echo "  sudo MATRIX_DIR=/home/gillo/rpi-rgb-led-matrix_pwm_experiment ./install.sh"
    exit 1
fi

echo "==> Installazione pacchetti di sistema"
apt update
apt install -y python3 python3-pip python3-dev python3-numpy python3-pil \
               python3-flask cython3 fonts-dejavu-core tzdata ffmpeg samba samba-common-bin

echo "==> Compilazione dei binding Python della libreria matrice"
cd "$MATRIX_DIR"
pip install . --break-system-packages 2>/dev/null || pip install .

echo "==> Copia dei file in /opt/dmd"
mkdir -p /opt/dmd
cp -r "$SRC_DIR"/*.py "$SRC_DIR"/templates "$SRC_DIR"/static /opt/dmd/
cp -r "$SRC_DIR"/sources /opt/dmd/
mkdir -p /var/lib/dmd

echo "==> Configurazione iniziale in /etc/dmd/config.json"
mkdir -p /etc/dmd
if [ ! -f /etc/dmd/config.json ]; then
    cp "$SRC_DIR/config.json" /etc/dmd/config.json
    PROFILE_DIR="$MATRIX_DIR/lib/spwm/registertest/data"
    python3 - "$PROFILE_DIR" <<'PYEOF'
import json, sys
path = "/etc/dmd/config.json"
with open(path) as handle:
    cfg = json.load(handle)
cfg["panel"]["profile_dir"] = sys.argv[1]
with open(path, "w") as handle:
    json.dump(cfg, handle, indent=2)
print("profile_dir impostato su", sys.argv[1])
PYEOF
else
    echo "    configurazione già presente, lasciata invariata"
fi

echo "==> Libreria media e condivisione SMB"
bash "$SRC_DIR/setup_share.sh" /srv/dmd/media

echo "==> Installazione del servizio systemd"
cp "$SRC_DIR/dmd.service" /etc/systemd/system/dmd.service
systemctl daemon-reload
systemctl enable dmd

echo
echo "Installazione completata."
echo
echo "Prima di avviare, controlla i valori in /etc/dmd/config.json:"
echo "  panel.slowdown   -> 1 (Zero W) | 3 (Zero 2 W, Pi 3) | 5 (Pi 4)"
echo "  panel.chain      -> numero di pannelli in cascata"
echo
echo "Poi:   sudo systemctl start dmd"
echo "Log:   journalctl -u dmd -f"
