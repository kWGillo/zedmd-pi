#!/bin/bash
#
# Prepara una cartella condivisa e la relativa condivisione SMB.
# Richiamato da install.sh, update.sh e setup_doom.sh, ma si puo' lanciare
# da solo:
#
#   ./setup_share.sh                                   libreria media
#   ./setup_share.sh /srv/dmd/doom dmd-doom "WAD"      WAD di Doom
#
set -e

SHARE_DIR="${1:-/srv/dmd/media}"
SHARE_NAME="${2:-dmd-media}"
SHARE_DESC="${3:-Libreria media del DMD}"
MARKER="# --- $SHARE_NAME (gestito da DMD Controller) ---"

mkdir -p "$SHARE_DIR"
chmod 0777 "$SHARE_DIR"

if ! command -v smbd >/dev/null 2>&1; then
    echo "    Samba non installato: condivisione SMB saltata"
    exit 0
fi

# Gli scarti che macOS semina copiando su una condivisione di rete: per ogni
# `foo.png` un `._foo.png` con i metadati, piu' i `.DS_Store` delle cartelle.
# Vietandoli, il client non li vede e non li puo' creare — quindi smettono di
# comparire invece di essere cancellati dopo.
VETO='veto files = /._*/.DS_Store/.AppleDouble/.AppleDB/.AppleDesktop/.TemporaryItems/.Trashes/.fseventsd/.Spotlight-V100/'

pulisci() {
    # Quelli gia' copiati restano sul disco: vietarli li rende invisibili, non
    # li toglie. Si buttano qui, una volta, e sono scarti per definizione.
    local quanti
    quanti=$(find "$1" \( -name '._*' -o -name '.DS_Store' \) -type f 2>/dev/null | wc -l)
    if [ "$quanti" -gt 0 ]; then
        find "$1" \( -name '._*' -o -name '.DS_Store' \) -type f -delete 2>/dev/null || true
        echo "    tolti $quanti file di servizio di macOS"
    fi
}

if grep -q "^\[$SHARE_NAME\]" /etc/samba/smb.conf 2>/dev/null; then
    echo "    condivisione SMB $SHARE_NAME già presente"
    # Una condivisione creata da una versione precedente non ha il divieto:
    # si aggiunge alla sezione che c'e' gia', invece di chiedere all'utente di
    # cancellarla e rifarla.
    if ! sed -n "/^\[$SHARE_NAME\]/,/^\[/p" /etc/samba/smb.conf | grep -q "veto files"; then
        sed -i "/^\[$SHARE_NAME\]/a\\   $VETO\\n   delete veto files = yes" \
            /etc/samba/smb.conf
        echo "    aggiunto il divieto dei file di servizio di macOS"
        systemctl restart smbd >/dev/null 2>&1 || true
    fi
    pulisci "$SHARE_DIR"
    exit 0
fi

cat >> /etc/samba/smb.conf <<EOF

$MARKER
[$SHARE_NAME]
   comment = $SHARE_DESC
   path = $SHARE_DIR
   browseable = yes
   read only = no
   guest ok = yes
   create mask = 0664
   directory mask = 0775
   force user = root
   $VETO
   delete veto files = yes
EOF
pulisci "$SHARE_DIR"

# Consente l'accesso ospite senza password.
if ! grep -q "map to guest" /etc/samba/smb.conf; then
    sed -i '/^\[global\]/a\   map to guest = bad user' /etc/samba/smb.conf
fi

systemctl enable smbd >/dev/null 2>&1 || true
systemctl restart smbd >/dev/null 2>&1 || true
echo "    condivisione SMB creata: \\\\<ip-del-pi>\\$SHARE_NAME"
