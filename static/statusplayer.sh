#!/bin/sh
#
# Status Player - l'agente da mettere su Batocera.
#
# EmulationStation esegue gli script che trova in
# /userdata/system/configs/emulationstation/scripts/<evento>/ e passa tre
# argomenti: il sistema, il file della rom, il nome del gioco. Lo stesso file
# sta in game-start e in game-end: l'evento si capisce dal nome della cartella
# in cui e' stato messo, quindi non ci sono due script da tenere allineati.
#
# Installazione (le righe esatte, con il tuo indirizzo e il tuo segreto gia'
# dentro, stanno nella pagina Status Player del pannello):
#
#   curl -o /userdata/system/statusplayer.sh http://PANNELLO:8080/static/statusplayer.sh
#   chmod +x /userdata/system/statusplayer.sh
#   ln -sf /userdata/system/statusplayer.sh \
#     /userdata/system/configs/emulationstation/scripts/game-start/statusplayer.sh
#   ln -sf /userdata/system/statusplayer.sh \
#     /userdata/system/configs/emulationstation/scripts/game-end/statusplayer.sh
#   batocera-save-overlay
#
# E il file dei tre dati, /userdata/system/statusplayer.conf:
#
#   PANNELLO=http://192.168.1.50:8080
#   TOKEN=quello-generato-dalla-pagina
#   NOME=MARCO
#
# Non manda niente di personale: il nome che hai scelto tu, il sistema e il
# titolo del gioco. Niente percorsi di file, niente indirizzi, niente altro.

CONF=/userdata/system/statusplayer.conf
[ -r "$CONF" ] || exit 0
. "$CONF"

[ -n "$PANNELLO" ] || exit 0
[ -n "$TOKEN" ] || exit 0
[ -n "$NOME" ] || exit 0

# L'evento e' il nome della cartella che ci contiene: game-start o game-end.
CARTELLA=$(basename "$(dirname "$(readlink -f "$0")")" 2>/dev/null)
case "$CARTELLA" in
    *end|*stop) EVENTO=fine ;;
    *) EVENTO=inizio ;;
esac

SISTEMA="$1"
GIOCO="$3"
[ -n "$GIOCO" ] || GIOCO=$(basename "$2" 2>/dev/null)

# Due secondi di attesa e via: se il pannello e' spento o irraggiungibile non
# si resta appesi. Un gioco non deve partire piu' tardi per colpa nostra.
if command -v curl >/dev/null 2>&1; then
    curl -s -m 2 -o /dev/null \
        --data-urlencode "token=$TOKEN" \
        --data-urlencode "nome=$NOME" \
        --data-urlencode "evento=$EVENTO" \
        --data-urlencode "sistema=$SISTEMA" \
        --data-urlencode "gioco=$GIOCO" \
        "$PANNELLO/api/status/evento" &
else
    # Busybox wget: non sa fare l'urlencode, quindi il minimo sindacale --
    # gli spazi. I titoli con la e commerciale li fa curl, che su Batocera
    # c'e' praticamente sempre.
    SPAZIO='%20'
    wget -q -T 2 -O /dev/null \
        --post-data "token=$TOKEN&nome=$(echo "$NOME" | sed "s/ /$SPAZIO/g")&evento=$EVENTO&sistema=$(echo "$SISTEMA" | sed "s/ /$SPAZIO/g")&gioco=$(echo "$GIOCO" | sed "s/ /$SPAZIO/g")" \
        "$PANNELLO/api/status/evento" &
fi

exit 0
