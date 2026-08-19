#!/bin/bash
#
# Verifica dell'integrita' dei file, contro le impronte dei manifest.
#
#   ./verify.sh            controlla il pacchetto  (manifest.md5)
#   ./verify.sh /opt/dmd   controlla l'installato  (manifest-install.md5)
#
# Nasce da un guasto reale: su una scheda SD in sofferenza un file era
# arrivato della lunghezza giusta ma pieno di byte nulli. Il trasferimento
# non aveva segnalato nulla e il servizio non partiva senza dire perche'.
#
set -u

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="$(cd "${1:-$SRC_DIR}" 2>/dev/null && pwd)" || {
    echo "cartella non raggiungibile: ${1:-$SRC_DIR}"; exit 2; }

# Il pacchetto contiene anche gli script di installazione; l'installazione in
# /opt/dmd no. Due elenchi, nessuna logica da indovinare.
if [ "$TARGET" = "$SRC_DIR" ]; then
    MANIFEST="$SRC_DIR/manifest.md5"
else
    MANIFEST="$SRC_DIR/manifest-install.md5"
fi

if [ ! -f "$MANIFEST" ]; then
    echo "$(basename "$MANIFEST") non trovato: verifica non possibile"
    exit 2
fi

cd "$TARGET" || exit 2
echo "==> Verifica di $TARGET"

bad=0
missing=0
checked=0

while read -r expected name; do
    [ -z "${name:-}" ] && continue
    checked=$((checked + 1))
    if [ ! -f "$name" ]; then
        echo "   MANCANTE   $name"
        missing=$((missing + 1))
        continue
    fi
    actual=$(md5sum "$name" | cut -d' ' -f1)
    if [ "$actual" != "$expected" ]; then
        echo "   ALTERATO   $name"
        if LC_ALL=C grep -qU $'\x00' "$name" 2>/dev/null; then
            echo "              contiene byte nulli: scrittura corrotta"
        fi
        bad=$((bad + 1))
    fi
done < "$MANIFEST"

echo "    $checked file controllati, $bad alterati, $missing mancanti"

if [ $bad -gt 0 ] || [ $missing -gt 0 ]; then
    echo
    echo "I file elencati sopra non corrispondono all'originale."
    echo "Ritrasferisci il pacchetto e riprova. Se l'errore si ripresenta,"
    echo "su file diversi a ogni tentativo, il problema e' la scheda SD o"
    echo "l'alimentazione: vedi la sezione 11 del manuale."
    exit 1
fi

echo "    tutto integro"
exit 0
