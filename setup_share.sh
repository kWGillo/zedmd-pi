#!/bin/bash
#
# Prepara la cartella della libreria media e la condivisione SMB.
# Richiamato da install.sh e update.sh, ma si puo' lanciare da solo.
#
set -e

MEDIA_DIR="${1:-/srv/dmd/media}"
MARKER="# --- dmd-media (gestito da DMD Controller) ---"

mkdir -p "$MEDIA_DIR"
chmod 0777 "$MEDIA_DIR"

if ! command -v smbd >/dev/null 2>&1; then
    echo "    Samba non installato: condivisione SMB saltata"
    exit 0
fi

if grep -q "^\[dmd-media\]" /etc/samba/smb.conf 2>/dev/null; then
    echo "    condivisione SMB già presente"
    exit 0
fi

cat >> /etc/samba/smb.conf <<EOF

$MARKER
[dmd-media]
   comment = Libreria media del DMD
   path = $MEDIA_DIR
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
echo "    condivisione SMB creata: \\\\<ip-del-pi>\\dmd-media"
