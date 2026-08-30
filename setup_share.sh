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

if grep -q "^\[$SHARE_NAME\]" /etc/samba/smb.conf 2>/dev/null; then
    echo "    condivisione SMB $SHARE_NAME già presente"
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
EOF

# Consente l'accesso ospite senza password.
if ! grep -q "map to guest" /etc/samba/smb.conf; then
    sed -i '/^\[global\]/a\   map to guest = bad user' /etc/samba/smb.conf
fi

systemctl enable smbd >/dev/null 2>&1 || true
systemctl restart smbd >/dev/null 2>&1 || true
echo "    condivisione SMB creata: \\\\<ip-del-pi>\\$SHARE_NAME"
