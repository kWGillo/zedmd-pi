#!/bin/bash
#
# Rigenera le impronte md5 dei due manifest, dalla radice del progetto.
#
#   bash diagnostica/rifai_manifest.sh          nella cartella del progetto
#   bash diagnostica/rifai_manifest.sh /percorso
#
# `verify.sh` controlla le impronte; fino alla 16.4 nessuno nel repository le
# **generava**: la regola viveva in uno script di servizio fuori dal progetto,
# e quando quella cartella e' sparita si e' portata via l'unico posto in cui
# era scritta. Adesso sta qui, accanto agli altri attrezzi da scrivania.
#
# Le due liste, e perche' sono due:
#
#   manifest.md5          tutto cio' che sta nel pacchetto, meno docs/, .git,
#                         __pycache__, i .pyc, i manifest stessi e i tre file
#                         del repository (README, CHANGELOG, LICENSE)
#   manifest-install.md5  come sopra, meno i sei file che in /opt/dmd non
#                         vengono copiati: l'installazione non contiene gli
#                         script che la installano.
#
set -eu

RADICE="$(cd "${1:-$(dirname "$0")/..}" && pwd)"
cd "$RADICE"

ESCLUSI_INSTALL=".gitignore config.json dmd.service install.sh update.sh verify.sh"

elenco() {
    find . -type f \
        -not -path "./.git/*" -not -path "./docs/*" \
        -not -path "*/__pycache__/*" -not -name "*.pyc" \
        -not -name "manifest.md5" -not -name "manifest-install.md5" \
        -not -name "README.md" -not -name "CHANGELOG.md" -not -name "LICENSE" \
        | sed 's|^\./||' | LC_ALL=C sort
}

impronte() {
    while read -r nome; do
        printf "%s  %s\n" "$(md5sum "$nome" | cut -d' ' -f1)" "$nome"
    done
}

elenco | impronte > manifest.md5

elenco | while read -r nome; do
    salta=""
    for escluso in $ESCLUSI_INSTALL; do
        [ "$nome" = "$escluso" ] && salta=1
    done
    [ -z "$salta" ] && printf "%s\n" "$nome"
done | impronte > manifest-install.md5

printf "manifest.md5:         %d file\n" "$(wc -l < manifest.md5)"
printf "manifest-install.md5: %d file\n" "$(wc -l < manifest-install.md5)"
