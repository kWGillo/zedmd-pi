#!/bin/bash
#
# Prepara il Game Boy sul Pi: emulatore PyBoy e condivisione per le ROM.
#   sudo ./setup_gb.sh
#
# PyBoy e' LGPL-3.0 e si installa da PyPI come una qualunque libreria. Non
# viene installato dall'aggiornamento del DMD di proposito: l'aggiornamento
# passa dalla rete e non deve toccare i pacchetti di sistema. Chi vuole il
# Game Boy lo chiede, una volta.
#
# Le ROM non stanno qui dentro e non ci staranno mai: sono di chi le possiede.
# Questo script apre la cartella condivisa dove metterle, come per i WAD di
# Doom e per i media.
#
set -e

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
ROM_DIR=${ROM_DIR:-/srv/dmd/rom}
SHARE_NAME=${SHARE_NAME:-dmd-rom}

# La condivisione si prepara PRIMA dell'emulatore. Con `set -e`, un pip
# che fallisce fermerebbe lo script: se la cartella condivisa fosse in
# fondo non verrebbe mai creata, e non si potrebbero nemmeno copiare le
# ROM in attesa di risolvere. L'ordine e' quello che serve a chi guarda.
echo "==> Cartella delle ROM"
mkdir -p "$ROM_DIR"
chmod 0775 "$ROM_DIR"

CONDIVISIONE="$(dirname "$SRC_DIR")/setup_share.sh"
if [ -x "$CONDIVISIONE" ] || [ -f "$CONDIVISIONE" ]; then
    echo "==> Condivisione SMB '$SHARE_NAME'"
    bash "$CONDIVISIONE" "$ROM_DIR" "$SHARE_NAME" "ROM Game Boy"
else
    echo "    setup_share.sh non trovato: la cartella c'e', la condivisione no"
fi

echo "==> PyBoy"
if python3 -c "import pyboy" 2>/dev/null; then
    echo "    gia' installato: $(python3 -c 'import pyboy; print(getattr(pyboy, "__version__", "?"))')"
else
    # --break-system-packages: su Debian recente pip rifiuta di scrivere nei
    # pacchetti di sistema senza questo. E' la stessa scelta gia' fatta per le
    # altre dipendenze del progetto in install.sh.
    pip3 install pyboy --break-system-packages
fi

python3 - <<'EOF'
import sys
try:
    import pyboy
except Exception as exc:
    sys.stderr.write("PyBoy non importabile: %s\n" % exc)
    sys.exit(1)
print("    versione %s" % getattr(pyboy, "__version__", "?"))
EOF

echo
echo "Fatto. Copia le ROM (.gb o .gbc) nella condivisione \\\\<indirizzo>\\$SHARE_NAME"
echo "e scegli la cartuccia dalla pagina Game Boy."
