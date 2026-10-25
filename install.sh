#!/bin/bash
#
# Installazione del DMD Controller.
# Da lanciare dalla cartella scompattata:  sudo ./install.sh
#
set -e

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

# Che macchina e' questa. Dalla 17.0 l'installazione ha due strade, e la
# differenza non e' cosmetica: su un Raspberry 3 o 4 si compilano i binding
# della libreria matrice -- un passo che su un PC fallirebbe, perche' quella
# libreria pilota il blocco PWM del BCM -- e su tutto il resto si installa
# invece di che cosa serve per disegnare su un monitor.
#
# La domanda la fa `piattaforma.py`, lo stesso modulo che la fara' a ogni
# avvio: una risposta sola, scritta in un posto solo.
PANNELLO=$(python3 "$SRC_DIR/piattaforma.py" --pannello 2>/dev/null || echo no)
echo "==> Macchina: $(python3 "$SRC_DIR/piattaforma.py" --nome 2>/dev/null || echo sconosciuta)"

MATRIX_DIR="${MATRIX_DIR:-$HOME/rpi-rgb-led-matrix_pwm_experiment}"
if [ -n "$SUDO_USER" ]; then
    REAL_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
    MATRIX_DIR="${MATRIX_DIR:-$REAL_HOME/rpi-rgb-led-matrix_pwm_experiment}"
    if [ ! -d "$MATRIX_DIR" ]; then
        MATRIX_DIR="$REAL_HOME/rpi-rgb-led-matrix_pwm_experiment"
    fi
fi

if [ -f "$SRC_DIR/manifest.md5" ]; then
    bash "$SRC_DIR/verify.sh" "$SRC_DIR" || {
        echo
        echo "Il pacchetto non e' integro: ritrasferiscilo prima di installare."
        exit 1
    }
fi

if [ "$PANNELLO" = "si" ]; then
    echo "==> Libreria matrice attesa in: $MATRIX_DIR"
    if [ ! -d "$MATRIX_DIR" ]; then
        echo "ERRORE: cartella della libreria non trovata."
        echo "Impostala esplicitamente, ad esempio:"
        echo "  sudo MATRIX_DIR=/home/gillo/rpi-rgb-led-matrix_pwm_experiment ./install.sh"
        exit 1
    fi
else
    echo "==> Niente pannello LED su questa macchina: si disegna sul monitor"
fi

echo "==> Installazione pacchetti di sistema"
apt update
apt install -y python3 python3-pip python3-dev python3-numpy python3-pil \
               python3-flask python3-paho-mqtt cython3 fonts-dejavu-core \
               tzdata ffmpeg samba samba-common-bin

# ----------------------------------------------- il font dell'orologio
#
# L'orologio e' disegnato sulle larghezze di `DejaVuSansMono-Bold`. Non e'
# una preferenza estetica: a larghezza fissa `11:11` e `20:38` occupano lo
# stesso spazio, e un orologio centrato non si sposta a ogni minuto.
#
# Fino a Debian 12 quel font stava in `fonts-dejavu-core`, che si installa
# qui sopra. Dalla 13 le facce monospaziate sono in `fonts-dejavu-mono`, e
# su quelle macchine ci si ritrovava senza, con il ripiego sul font
# proporzionale. Quindi: si prova apt, e se il font non c'e' comunque si
# installa la copia che viaggia nel progetto. Niente rete, niente indirizzi
# che fra cinque anni potrebbero non rispondere piu'.
FONT_SISTEMA=/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf
FONT_NOSTRO="$SRC_DIR/font/DejaVuSansMono-Bold.ttf"
FONT_DEST=/usr/local/share/fonts/dmd

echo "==> Font dell'orologio"
if [ ! -f "$FONT_SISTEMA" ]; then
    apt install -y fonts-dejavu-mono 2>/dev/null || true
fi
if [ -f "$FONT_SISTEMA" ]; then
    echo "    c'e' gia' quello di sistema"
elif [ -f "$FONT_NOSTRO" ]; then
    mkdir -p "$FONT_DEST"
    cp "$FONT_NOSTRO" "$FONT_DEST/"
    command -v fc-cache >/dev/null 2>&1 && fc-cache -f "$FONT_DEST" >/dev/null 2>&1
    echo "    installata la copia del progetto in $FONT_DEST"
else
    echo "    non trovato: l'orologio usera' il font proporzionale"
fi

# Su un monitor il disegno esce da SDL: una finestra se c'e' un desktop
# avviato, il KMS se non c'e'. Se non si installa, `display.py` ripiega su
# /dev/fb0, che non ha bisogno di niente ma nemmeno di una finestra.
if [ "$PANNELLO" != "si" ]; then
    echo "==> Uscita su monitor (SDL)"
    apt install -y python3-pygame || \
      echo "    python3-pygame non installato: si usera' il framebuffer"
fi

# Calcolo orbitale per la sorgente Satelliti. Non e' in apt: si prende da pip,
# che sui Raspberry a 64 bit ha la ruota gia' compilata. Se fallisce non si
# ferma niente — il servizio parte lo stesso e la sorgente Satelliti dice da
# sola che cosa manca.
echo "==> Libreria di calcolo orbitale (sgp4)"
pip install sgp4 --break-system-packages 2>/dev/null || pip install sgp4 || \
  echo "    sgp4 non installata: la sorgente Satelliti restera' spenta"

if [ "$PANNELLO" = "si" ]; then
    echo "==> Compilazione dei binding Python della libreria matrice"
    cd "$MATRIX_DIR"
    pip install . --break-system-packages 2>/dev/null || pip install .
    cd "$SRC_DIR"
fi

echo "==> Copia dei file in /opt/dmd"
mkdir -p /opt/dmd
cp -r "$SRC_DIR"/*.py "$SRC_DIR"/*.csv "$SRC_DIR"/templates \
      "$SRC_DIR"/static /opt/dmd/
cp -r "$SRC_DIR"/sources /opt/dmd/
# Il font dell'orologio va accanto al programma: `sources/clock.py` lo cerca
# li' dentro, e da li' lo prende anche un aggiornamento OTA, che `install.sh`
# non lo lancia.
if [ -d "$SRC_DIR/font" ]; then
    cp -r "$SRC_DIR"/font /opt/dmd/
fi
# Doom: qui arrivano solo i sorgenti e lo script. Compilare richiede di
# scaricare doomgeneric e un paio di minuti di CPU, e non e' detto che chi
# installa il DMD voglia anche giocare: lo fa lui quando vuole, con
# `sudo /opt/dmd/doom/setup_doom.sh`.
if [ -d "$SRC_DIR/doom" ]; then
    mkdir -p /opt/dmd/doom
    cp "$SRC_DIR"/doom/doomgeneric_dmd.c "$SRC_DIR"/doom/Makefile \
       "$SRC_DIR"/doom/setup_doom.sh /opt/dmd/doom/
    chmod +x /opt/dmd/doom/setup_doom.sh
fi

# Il Game Boy: qui si copiano solo il programma che ospita PyBoy e il suo
# script di preparazione. PyBoy **non** si installa adesso — e' un pacchetto
# di sistema, e chi non vuole l'emulatore non deve trovarselo installato.
# Lo installa gb/setup_gb.sh, dal pulsante nella pagina Game Boy.
# Gli strumenti di misura e le prove: non servono al servizio, servono a chi
# lo tara e a chi cerca un difetto. Si copia la cartella **intera**: fino alla
# 16.5 si prendevano solo gli script di shell, mentre l'aggiornamento OTA
# copiava anche i `.py`, perche' li legge dal manifest. Due strade diverse per
# gli stessi file, e un'installazione nuova che `verify.sh` segnalava come
# incompleta.
if [ -d "$SRC_DIR/diagnostica" ]; then
    mkdir -p /opt/dmd/diagnostica
    cp -r "$SRC_DIR"/diagnostica/. /opt/dmd/diagnostica/
    chmod +x /opt/dmd/diagnostica/*.sh 2>/dev/null || true
fi

if [ -d "$SRC_DIR/gb" ]; then
    mkdir -p /opt/dmd/gb
    cp "$SRC_DIR"/gb/gb_dmd.py "$SRC_DIR"/gb/setup_gb.sh /opt/dmd/gb/
    chmod +x /opt/dmd/gb/setup_gb.sh /opt/dmd/gb/gb_dmd.py
fi

# 5.2: gli effetti sonori dei giochi. Sono nostri e stanno nel programma, non
# nella libreria media dell'utente: i suoni di Invaders e Breakout non devono
# comparire fra le cose che si scelgono per i servizi.
if [ -d "$SRC_DIR/suoni" ]; then
    mkdir -p /opt/dmd/suoni
    cp "$SRC_DIR"/suoni/*.wav /opt/dmd/suoni/
fi
mkdir -p /var/lib/dmd

echo "==> Configurazione iniziale in /etc/dmd/config.json"
mkdir -p /etc/dmd
if [ ! -f /etc/dmd/config.json ]; then
    cp "$SRC_DIR/config.json" /etc/dmd/config.json
    PROFILE_DIR="$MATRIX_DIR/lib/spwm/registertest/data"
    python3 - "$PROFILE_DIR" "$PANNELLO" <<'PYEOF'
import json, sys
path = "/etc/dmd/config.json"
with open(path) as handle:
    cfg = json.load(handle)
if sys.argv[2] == "si":
    cfg["panel"]["profile_dir"] = sys.argv[1]
    print("profile_dir impostato su", sys.argv[1])
else:
    # Senza pannello il catalogo dei profili di registro non esiste e non
    # serve: lasciarlo scritto farebbe cercare alla libreria una cartella
    # che non c'e', il giorno in cui qualcuno accendesse il pannello per
    # sbaglio.
    cfg["panel"]["profile_dir"] = ""
    cfg.setdefault("video", {})["uscita"] = "schermo"
    # E l'audio nasce acceso: su un PC la scheda integrata c'e' sempre, e un
    # DMD muto su una macchina che ha gli altoparlanti e' solo una casella
    # da trovare.
    cfg.setdefault("audio", {})["enabled"] = True
    print("uscita video: schermo; audio acceso sulla scheda integrata")
with open(path, "w") as handle:
    json.dump(cfg, handle, indent=2)
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
if [ "$PANNELLO" = "si" ]; then
    echo "Prima di avviare, controlla i valori in /etc/dmd/config.json:"
    echo "  panel.slowdown   -> 1 (Zero W) | 3 (Zero 2 W, Pi 3) | 5 (Pi 4)"
    echo "  panel.chain      -> numero di pannelli in cascata"
else
    echo "Il disegno uscira' sul monitor collegato. Dalla pagina Video puoi"
    echo "scegliere risoluzione, finestra e filtro DMD."
fi
echo
echo "Poi:   sudo systemctl start dmd"
echo "Log:   journalctl -u dmd -f"
