#!/bin/sh
#
# Scarica l'archivio di Open Trivia DB in una cartella di file JSON, uno per
# richiesta. Serve quando la macchina che genera le banche di Super Quiz non
# arriva a opentdb.com: si lancia questo dove la rete c'e', si portano i file
# dall'altra parte, e poi:
#
#     python3 diagnostica/genera_domande.py /percorso/OpenQuizzDB/data \
#         --tdb-da /percorso/della/cartella
#
# Uso:  sh diagnostica/scarica_tdb.sh [cartella]     (di serie: ./tdb)
#
# L'archivio ammette **una richiesta ogni cinque secondi**, e qui se ne
# aspettano sei: e' un servizio gratuito, e chi lo usa di corsa lo fa chiudere
# a tutti. Sono un paio di centinaia di richieste, quindi una ventina di
# minuti. Il gettone di sessione fa si' che non si ripeta niente: quando
# l'archivio e' finito risponde con il codice 4, e si smette.
set -e

CARTELLA="${1:-./tdb}"
mkdir -p "$CARTELLA"

GETTONE=$(curl -s "https://opentdb.com/api_token.php?command=request" \
    | sed -n 's/.*"token":"\([^"]*\)".*/\1/p')
if [ -z "$GETTONE" ]; then
    echo "non sono riuscito a farmi dare un gettone: c'e' rete?" >&2
    exit 1
fi

NUMERO=0
while [ "$NUMERO" -lt 300 ]; do
    NUMERO=$((NUMERO + 1))
    FILE=$(printf "%s/tdb-%03d.json" "$CARTELLA" "$NUMERO")
    curl -s -o "$FILE" \
        "https://opentdb.com/api.php?amount=50&type=multiple&encode=url3986&token=$GETTONE"
    CODICE=$(sed -n 's/.*"response_code":\([0-9]*\).*/\1/p' "$FILE")
    case "$CODICE" in
        0) echo "  $FILE" ;;
        4) rm -f "$FILE"; echo "archivio finito: $((NUMERO - 1)) file"; break ;;
        5) rm -f "$FILE"; NUMERO=$((NUMERO - 1)); sleep 12; continue ;;
        *) rm -f "$FILE"; echo "risposta inattesa (codice $CODICE)"; break ;;
    esac
    sleep 6
done

echo "fatto: $(ls "$CARTELLA" | wc -l) file in $CARTELLA"
