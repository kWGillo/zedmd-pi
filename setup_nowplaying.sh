#!/bin/bash
#
# Prepara il sistema per Now Playing: broker MQTT, shairport-sync con
# AirPlay 2 e metadati, scheda audio fittizia, e configurazione del DMD.
#
#   sudo /opt/dmd/setup_nowplaying.sh              interattivo
#   sudo /opt/dmd/setup_nowplaying.sh --verifica   controlla e basta
#   sudo /opt/dmd/setup_nowplaying.sh --aiuto      elenco delle opzioni
#
# Viene installato insieme al resto, ma non viene mai lanciato da solo: e' una
# funzione facoltativa, e la sola compilazione di shairport-sync porta via un
# quarto d'ora. Nessun aggiornamento ordinario deve trovarselo dentro.
#
# Non dipende da nessun altro file del pacchetto: si puo' anche scaricare da
# solo ed eseguire dovunque.
#
# Ogni passo e' ripetibile: se una cosa e' gia' fatta, lo script lo dice e
# passa oltre invece di rifarla. Si puo' rilanciare senza paura.
#
set -u

NOME_CASSA="DMD"
BROKER_HOST=""
BROKER_PORT="1883"
BROKER_USER=""
BROKER_PASS=""
TOPIC="shairport"
INTERATTIVO="si"
SOLO_VERIFICA="no"
FORZA_COMPILAZIONE="no"

LOG="/var/log/dmd-nowplaying-setup.log"
SORGENTI="${SORGENTI:-/usr/local/src}"
SPAZIO_MINIMO_MB=1200

# --------------------------------------------------------------------- stile

rosso()  { printf '\033[31m%s\033[0m\n' "$*"; }
verde()  { printf '\033[32m%s\033[0m\n' "$*"; }
giallo() { printf '\033[33m%s\033[0m\n' "$*"; }
titolo() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
passo()  { printf '    %s\n' "$*"; }

fallisci() {
    echo
    rosso "ERRORE: $*"
    # Citare il registro senza mostrarlo costringe a un secondo giro di
    # comandi proprio quando si e' gia' fermi. La riga che spiega il motivo
    # va stampata qui, adesso.
    if [ -s "$LOG" ]; then
        MOTIVO="$(grep -aE "configure: error:|No package .* found|were not met|Error 1$|command not found" "$LOG" | tail -4)"
        if [ -n "$MOTIVO" ]; then
            echo
            giallo "  Il registro dice questo:"
            echo "$MOTIVO" | sed 's/^/    /'
        fi
        echo
        echo "  Ultime righe del registro:"
        tail -12 "$LOG" | sed 's/^/    /'
    fi
    echo
    echo "Niente e' stato lasciato a meta': i passi gia' completati restano"
    echo "validi e rilanciare lo script riprende da dove si e' fermato."
    echo "Registro completo: $LOG"
    exit 1
}

aiuto() {
    cat <<'FINE'
setup_nowplaying.sh — prepara il sistema per Now Playing

  --nome NOME          nome con cui il DMD compare fra le casse AirPlay
  --broker INDIRIZZO   broker MQTT (vuoto o 127.0.0.1 = installa Mosquitto qui)
  --porta N            porta del broker (predefinita 1883)
  --utente NOME        utente del broker, se richiesto
  --password PAROLA    password del broker, se richiesta
  --topic NOME         topic su cui shairport-sync pubblica (predefinito shairport)
  --non-interattivo    non fa domande, usa i valori qui sopra
  --verifica           controlla lo stato senza modificare nulla
  --ricompila          ricompila shairport-sync anche se e' gia' a posto
  --aiuto              questo testo

Esempio, broker sotto Home Assistant:
  sudo /opt/dmd/setup_nowplaying.sh --broker 192.168.0.20 --utente dmd --password xxx
FINE
    exit 0
}

while [ $# -gt 0 ]; do
    case "$1" in
        --nome)             NOME_CASSA="${2:-DMD}"; shift 2 ;;
        --broker)           BROKER_HOST="${2:-}"; shift 2 ;;
        --porta)            BROKER_PORT="${2:-1883}"; shift 2 ;;
        --utente)           BROKER_USER="${2:-}"; shift 2 ;;
        --password)         BROKER_PASS="${2:-}"; shift 2 ;;
        --topic)            TOPIC="${2:-shairport}"; shift 2 ;;
        --non-interattivo)  INTERATTIVO="no"; shift ;;
        --verifica)         SOLO_VERIFICA="si"; INTERATTIVO="no"; shift ;;
        --ricompila)        FORZA_COMPILAZIONE="si"; shift ;;
        --aiuto|-h|--help)  aiuto ;;
        *) fallisci "opzione sconosciuta: $1  (--aiuto per l'elenco)" ;;
    esac
done

[ "$(id -u)" = "0" ] || fallisci "va lanciato con sudo"

mkdir -p "$(dirname "$LOG")" 2>/dev/null || true
echo "===== $(date '+%Y-%m-%d %H:%M:%S') =====" >> "$LOG"
esegui() {
    echo "+ $*" >> "$LOG"
    "$@" >> "$LOG" 2>&1
}

# --------------------------------------------------------- stato del sistema

versione_shairport() {
    command -v shairport-sync >/dev/null 2>&1 || return 1
    shairport-sync -V 2>&1 | head -1
}

ha_shairport_giusto() {
    local versione
    versione="$(versione_shairport)" || return 1
    # La stringa di versione elenca le funzioni compilate separandole con
    # trattini, ma la grafia cambia fra le versioni: "AirPlay2", "AirPlay-2",
    # "airplay-2". Si normalizza tutto in minuscolo togliendo trattini e
    # spazi, cosi' il confronto non dipende da come e' scritta oggi.
    local piatta
    # Il trattino va per ultimo: in mezzo, tr lo interpreta come intervallo
    # (' -_' vale da spazio a underscore, cifre comprese) e "AirPlay2"
    # diventerebbe "airplay", senza il 2 da cercare.
    piatta="$(printf '%s' "$versione" | tr 'A-Z' 'a-z' | tr -d ' _-')"
    case "$piatta" in
        *airplay2*) ;;
        *) return 1 ;;
    esac
    case "$piatta" in
        *mqtt*) return 0 ;;
        *) return 1 ;;
    esac
}

attivo() { systemctl is-active --quiet "$1"; }

riepilogo() {
    titolo "Stato attuale"
    if command -v shairport-sync >/dev/null 2>&1; then
        passo "shairport-sync: $(shairport-sync -V 2>&1 | head -c 160)"
        if ha_shairport_giusto; then
            verde "    -> ha AirPlay 2 e MQTT"
        else
            giallo "    -> manca AirPlay 2 o MQTT: va ricompilato"
        fi
    else
        giallo "    shairport-sync: non installato"
    fi

    for servizio in nqptp shairport-sync mosquitto avahi-daemon dmd; do
        if systemctl list-unit-files 2>/dev/null | grep -q "^${servizio}\."; then
            if attivo "$servizio"; then
                verde "    $servizio: attivo"
            else
                giallo "    $servizio: presente ma fermo"
            fi
        else
            giallo "    $servizio: non installato"
        fi
    done

    if aplay -l 2>/dev/null | grep -qi dummy; then
        verde "    scheda audio fittizia: presente"
    else
        giallo "    scheda audio fittizia: assente"
    fi

    if python3 -c "import paho.mqtt.client" >/dev/null 2>&1; then
        verde "    libreria MQTT di Python: presente"
    else
        giallo "    libreria MQTT di Python: assente"
    fi
}

if [ "$SOLO_VERIFICA" = "si" ]; then
    riepilogo
    titolo "Prova del percorso dei metadati"
    if command -v mosquitto_sub >/dev/null 2>&1; then
        HOST_PROVA="${BROKER_HOST:-127.0.0.1}"
        passo "ascolto '$TOPIC/#' su $HOST_PROVA per 15 secondi"
        passo "metti musica dall'iPhone scegliendo la cassa AirPlay, adesso"
        RISULTATO="$(timeout 15 mosquitto_sub -h "$HOST_PROVA" -p "$BROKER_PORT" \
                     -t "$TOPIC/#" -v 2>/dev/null | head -20)"
        if [ -n "$RISULTATO" ]; then
            verde "    arrivano messaggi:"
            echo "$RISULTATO" | sed 's/^/      /'
        else
            giallo "    nessun messaggio: vedi il capitolo 10 della guida"
        fi
    else
        giallo "    mosquitto-clients non installato, prova non eseguita"
    fi
    echo
    exit 0
fi

# ------------------------------------------------------------------ domande

echo
echo "  Preparazione di Now Playing"
echo "  ---------------------------"
echo "  Il Raspberry diventera' una cassa AirPlay che non suona: accetta il"
echo "  flusso, scarta l'audio e tiene i metadati per il pannello."
echo

if [ "$INTERATTIVO" = "si" ]; then
    read -r -p "  Nome con cui comparire fra le casse [$NOME_CASSA]: " risposta
    NOME_CASSA="${risposta:-$NOME_CASSA}"

    echo
    echo "  Il broker MQTT e' il punto d'incontro fra shairport-sync e il DMD."
    echo "  Lascia vuoto per installarne uno qui sul Raspberry (consigliato se"
    echo "  non hai Home Assistant), oppure scrivi l'indirizzo del tuo."
    read -r -p "  Indirizzo del broker [locale]: " risposta
    BROKER_HOST="${risposta:-}"

    if [ -n "$BROKER_HOST" ] && [ "$BROKER_HOST" != "127.0.0.1" ]; then
        read -r -p "  Porta [$BROKER_PORT]: " risposta
        BROKER_PORT="${risposta:-$BROKER_PORT}"
        read -r -p "  Utente (vuoto se non serve): " BROKER_USER
        if [ -n "$BROKER_USER" ]; then
            read -r -s -p "  Password: " BROKER_PASS; echo
        fi
    fi
fi

if [ -z "$BROKER_HOST" ] || [ "$BROKER_HOST" = "127.0.0.1" ]; then
    BROKER_HOST="127.0.0.1"
    BROKER_LOCALE="si"
else
    BROKER_LOCALE="no"
fi

echo
passo "nome della cassa: $NOME_CASSA"
if [ "$BROKER_LOCALE" = "si" ]; then
    passo "broker: Mosquitto locale, installato da questo script"
else
    passo "broker: $BROKER_HOST:$BROKER_PORT${BROKER_USER:+ (utente $BROKER_USER)}"
fi
passo "topic dei metadati: $TOPIC"
passo "registro dettagliato: $LOG"

if [ "$INTERATTIVO" = "si" ]; then
    echo
    if ha_shairport_giusto && [ "$FORZA_COMPILAZIONE" = "no" ]; then
        echo "  shairport-sync e' gia' adatto: niente compilazione, saranno"
        echo "  pochi minuti."
    else
        echo "  shairport-sync va compilato: sul Pi 4 conta un quarto d'ora."
        echo "  La compilazione gira a priorita' bassa per non disturbare il"
        echo "  pannello ne' affaticare la scheda SD."
    fi
    read -r -p "  Procedo? [S/n] " risposta
    case "${risposta:-s}" in
        [nN]*) echo "  Annullato."; exit 0 ;;
    esac
fi

# ------------------------------------------------------ controlli preliminari

titolo "Controlli preliminari"

LIBERI_MB="$(df -Pm / | awk 'NR==2 {print $4}')"
passo "spazio libero: ${LIBERI_MB} MB"
if [ "$LIBERI_MB" -lt "$SPAZIO_MINIMO_MB" ] && ! ha_shairport_giusto; then
    fallisci "servono almeno ${SPAZIO_MINIMO_MB} MB liberi per compilare"
fi

if ! ping -c1 -W3 deb.debian.org >/dev/null 2>&1 && \
   ! ping -c1 -W3 8.8.8.8 >/dev/null 2>&1; then
    fallisci "nessuna connessione a internet"
fi
passo "rete raggiungibile"

# Trappola vera: il pacchetto della distribuzione mette il binario in
# /usr/bin, la compilazione lo mette in /usr/local/bin. Convivono, con due
# unita' systemd omonime, e si finisce per avviare quello sbagliato senza
# capire perche' manchi AirPlay 2.
if dpkg -l shairport-sync 2>/dev/null | grep -q '^ii' && ! ha_shairport_giusto; then
    echo
    giallo "  C'e' il pacchetto shairport-sync della distribuzione, e non ha"
    giallo "  quello che serve. Se compilo senza toglierlo restano due"
    giallo "  installazioni sovrapposte e due unita' systemd omonime."
    if [ "$INTERATTIVO" = "si" ]; then
        read -r -p "  Lo rimuovo? [S/n] " risposta
        case "${risposta:-s}" in
            [nN]*) fallisci "rimuovi il pacchetto e rilancia: sudo apt purge shairport-sync" ;;
        esac
    fi
    esegui systemctl disable --now shairport-sync
    esegui apt-get purge -y shairport-sync
    passo "pacchetto della distribuzione rimosso"
fi

# ---------------------------------------------------------------- Mosquitto

if [ "$BROKER_LOCALE" = "si" ]; then
    titolo "Broker MQTT locale"
    if command -v mosquitto >/dev/null 2>&1; then
        passo "mosquitto gia' installato"
    else
        passo "installazione di mosquitto"
        esegui apt-get update
        esegui apt-get install -y mosquitto mosquitto-clients \
            || fallisci "installazione di mosquitto non riuscita (vedi $LOG)"
    fi

    CONF_MOSQ="/etc/mosquitto/conf.d/dmd.conf"
    if [ -f "$CONF_MOSQ" ]; then
        passo "configurazione gia' presente: $CONF_MOSQ (lasciata com'e')"
    else
        # Mosquitto 2.x non accetta connessioni anonime se non glielo si dice.
        cat > "$CONF_MOSQ" <<'FINE'
# Scritto da setup_nowplaying.sh del DMD Controller.
# Uso domestico: rete locale dietro un router. Se il broker diventa
# raggiungibile da fuori, sostituisci allow_anonymous con utenti veri
# (mosquitto_passwd) e riporta le credenziali nella pagina Musica del DMD.
listener 1883
allow_anonymous true
FINE
        passo "scritto $CONF_MOSQ"
    fi
    esegui systemctl enable mosquitto
    esegui systemctl restart mosquitto
    sleep 1
    attivo mosquitto || fallisci "mosquitto non parte (vedi $LOG)"
    verde "    mosquitto attivo"
else
    titolo "Broker MQTT remoto"
    if ! command -v mosquitto_pub >/dev/null 2>&1; then
        esegui apt-get update
        esegui apt-get install -y mosquitto-clients
    fi
    passo "prova di connessione a $BROKER_HOST:$BROKER_PORT"
    if mosquitto_pub -h "$BROKER_HOST" -p "$BROKER_PORT" \
        ${BROKER_USER:+-u "$BROKER_USER"} ${BROKER_PASS:+-P "$BROKER_PASS"} \
        -t "dmd/prova" -m "setup" >>"$LOG" 2>&1; then
        verde "    broker raggiungibile"
    else
        fallisci "il broker non risponde: controlla indirizzo, porta e credenziali"
    fi
fi

# ------------------------------------------------------- libreria MQTT Python

titolo "Libreria MQTT per il DMD"
if python3 -c "import paho.mqtt.client" >/dev/null 2>&1; then
    passo "gia' presente"
else
    esegui apt-get install -y python3-paho-mqtt \
        || esegui pip3 install paho-mqtt --break-system-packages
    python3 -c "import paho.mqtt.client" >/dev/null 2>&1 \
        || fallisci "paho-mqtt non installabile (vedi $LOG)"
    verde "    installata"
fi

# ------------------------------------------------------- scheda audio fittizia

titolo "Scheda audio fittizia"
# Non /dev/null e non il plugin null di ALSA: quelli non limitano il ritmo,
# shairport-sync perderebbe il riferimento temporale e in un gruppo
# multi-room farebbe singhiozzare tutte le casse, non solo questa.
if aplay -l 2>/dev/null | grep -qi dummy; then
    passo "gia' caricata"
else
    esegui modprobe snd_dummy || fallisci "modulo snd_dummy non caricabile"
    sleep 1
    aplay -l 2>/dev/null | grep -qi dummy || fallisci "la scheda fittizia non compare"
    verde "    caricata"
fi
echo snd_dummy > /etc/modules-load.d/snd-dummy.conf
passo "caricamento automatico all'avvio impostato"

# ------------------------------------------------------------- shairport-sync

if ha_shairport_giusto && [ "$FORZA_COMPILAZIONE" = "no" ]; then
    titolo "shairport-sync"
    verde "    gia' compilato con AirPlay 2 e MQTT: salto la compilazione"
else
    titolo "Dipendenze di compilazione"
    esegui apt-get update
    esegui apt-get install -y --no-install-recommends \
        build-essential git autoconf automake libtool pkg-config \
        libpopt-dev libconfig-dev libasound2-dev avahi-daemon \
        libavahi-client-dev libssl-dev libsoxr-dev libplist-dev libsodium-dev \
        libavutil-dev libavcodec-dev libavformat-dev uuid-dev libgcrypt-dev \
        xxd libplist-utils libmosquitto-dev libswresample-dev \
        || fallisci "installazione delle dipendenze non riuscita"
    # Il file pkg-config di systemd sta in systemd-dev sulle distribuzioni
    # recenti e in libsystemd-dev su quelle precedenti. Si tentano entrambi
    # senza pretendere che esistano tutti e due.
    for pacchetto in systemd-dev libsystemd-dev; do
        esegui apt-get install -y "$pacchetto" || true
    done
    verde "    installate"

    # Il controllo che segue costa due secondi e fa risparmiare un quarto
    # d'ora: senza, ogni dipendenza mancante si scopre a compilazione avviata,
    # una per volta, e ogni giro e' un altro tentativo da capo.
    titolo "Verifica delle dipendenze prima di compilare"
    MANCANTI=""
    for coppia in "libplist-2.0:libplist-dev" "libsodium:libsodium-dev" \
                  "libavutil:libavutil-dev" "libavcodec:libavcodec-dev" \
                  "libavformat:libavformat-dev" \
                  "libswresample:libswresample-dev" \
                  "systemd:systemd-dev (oppure libsystemd-dev)"; do
        modulo="${coppia%%:*}"
        pacchetto="${coppia#*:}"
        if ! pkg-config --exists "$modulo" 2>/dev/null; then
            MANCANTI="$MANCANTI\n      $modulo -> $pacchetto"
        fi
    done
    for coppia in "plistutil:libplist-utils" "xxd:xxd" "autoreconf:autoconf"; do
        programma="${coppia%%:*}"
        pacchetto="${coppia#*:}"
        if ! command -v "$programma" >/dev/null 2>&1; then
            MANCANTI="$MANCANTI\n      $programma -> $pacchetto"
        fi
    done
    if [ -n "$MANCANTI" ]; then
        echo
        giallo "  Manca ancora qualcosa che configure andra' a cercare:"
        printf "%b\n" "$MANCANTI"
        fallisci "installa i pacchetti elencati qui sopra e rilancia"
    fi
    verde "    tutto quello che configure cerchera' e' presente"

    mkdir -p "$SORGENTI"

    # La compilazione gira a priorita' bassa di CPU e di I/O. Non e' pignoleria:
    # su questo sistema il pannello ha bisogno di tempi regolari, e una scheda
    # SD sotto sforzo e' gia' stata la causa di guasti reali.
    if command -v ionice >/dev/null 2>&1; then
        GENTILE="nice -n 15 ionice -c3"
    else
        GENTILE="nice -n 15"
    fi
    # Un lavoro in meno del numero di core: uno resta libero per il pannello.
    CORE="$(nproc)"
    LAVORI="$(( CORE > 1 ? CORE - 1 : 1 ))"

    titolo "nqptp (sincronizzazione PTP di AirPlay 2)"
    if command -v nqptp >/dev/null 2>&1 && attivo nqptp; then
        passo "gia' compilato e attivo: salto"
    elif [ -d "$SORGENTI/nqptp/.git" ]; then
        passo "sorgenti gia' presenti, aggiorno"
        esegui git -C "$SORGENTI/nqptp" pull --ff-only
    else
        esegui git clone --depth 1 https://github.com/mikebrady/nqptp.git \
            "$SORGENTI/nqptp" || fallisci "clone di nqptp non riuscito"
    fi
    if ! command -v nqptp >/dev/null 2>&1 || ! attivo nqptp; then
        cd "$SORGENTI/nqptp" || fallisci "cartella di nqptp irraggiungibile"
        passo "compilazione"
        esegui autoreconf -fi
        esegui ./configure --with-systemd-startup || fallisci "configure di nqptp non riuscito"
        $GENTILE make -j"$LAVORI" >>"$LOG" 2>&1 || fallisci "compilazione di nqptp fallita"
        esegui make install
        esegui systemctl enable nqptp
        esegui systemctl reset-failed nqptp
        esegui systemctl restart nqptp
        sleep 1
        attivo nqptp || fallisci "nqptp non parte"
    fi
    verde "    nqptp attivo"

    titolo "shairport-sync (un quarto d'ora circa)"
    if [ -d "$SORGENTI/shairport-sync/.git" ]; then
        passo "sorgenti gia' presenti, aggiorno"
        esegui git -C "$SORGENTI/shairport-sync" pull --ff-only
    else
        esegui git clone --depth 1 https://github.com/mikebrady/shairport-sync.git \
            "$SORGENTI/shairport-sync" || fallisci "clone di shairport-sync non riuscito"
    fi
    cd "$SORGENTI/shairport-sync" || fallisci "cartella di shairport-sync irraggiungibile"
    esegui autoreconf -fi
    passo "configurazione con AirPlay 2, metadati e MQTT"
    esegui ./configure --sysconfdir=/etc --with-alsa --with-avahi \
        --with-ssl=openssl --with-soxr --with-airplay-2 \
        --with-metadata --with-mqtt-client --with-systemd-startup \
        || fallisci "configure di shairport-sync non e' andato a buon fine"
    passo "compilazione con $LAVORI lavori, a priorita' bassa"
    $GENTILE make -j"$LAVORI" >>"$LOG" 2>&1 \
        || fallisci "compilazione di shairport-sync fallita (vedi $LOG)"
    esegui make install
    if ! ha_shairport_giusto; then
        echo
        giallo "  La compilazione e' andata a termine, ma il binario non"
        giallo "  dichiara quello che serve. Ecco che cosa dice di se':"
        echo "    $(versione_shairport || echo 'shairport-sync non trovato')"
        echo "    binari trovati: $(command -v -a shairport-sync 2>/dev/null | tr '\n' ' ')"
        fallisci "manca AirPlay 2 o MQTT fra le funzioni compilate"
    fi
    verde "    compilato: $(shairport-sync -V 2>&1 | head -c 100)"
fi

# --------------------------------------------------- configurazione di shairport

titolo "Configurazione di shairport-sync"
CONF_SHAIRPORT="/etc/shairport-sync.conf"
if [ -f "$CONF_SHAIRPORT" ]; then
    COPIA="$CONF_SHAIRPORT.$(date +%Y%m%d-%H%M%S).bak"
    cp -p "$CONF_SHAIRPORT" "$COPIA"
    passo "copia della configurazione precedente: $COPIA"
fi

{
    echo "// Scritto da setup_nowplaying.sh del DMD Controller."
    echo "// La copia precedente, se c'era, e' accanto con estensione .bak"
    echo
    echo "general = {"
    echo "    name = \"$NOME_CASSA\";"
    echo "    output_backend = \"alsa\";"
    echo "};"
    echo
    echo "// L'audio finisce nella scheda fittizia del kernel: ha un orologio"
    echo "// vero, a differenza di /dev/null e del plugin null di ALSA, ed e'"
    echo "// quella differenza a tenere sincronizzato un gruppo multi-room."
    echo "alsa = {"
    echo "    output_device = \"hw:CARD=Dummy\";"
    echo "};"
    echo
    echo "mqtt = {"
    echo "    enabled = \"yes\";"
    echo "    hostname = \"$BROKER_HOST\";"
    echo "    port = $BROKER_PORT;"
    if [ -n "$BROKER_USER" ]; then
        echo "    username = \"$BROKER_USER\";"
        echo "    password = \"$BROKER_PASS\";"
    fi
    echo "    topic = \"$TOPIC\";"
    echo "    publish_parsed = \"yes\";"
    echo "    // publish_raw serve per prgr, cioe' la posizione nel brano:"
    echo "    // senza, niente barra di avanzamento."
    echo "    publish_raw = \"yes\";"
    echo "    publish_cover = \"no\";"
    echo "};"
} > "$CONF_SHAIRPORT"
chmod 644 "$CONF_SHAIRPORT"

# La password del broker finisce qui dentro, quindi il file non deve restare
# leggibile da chiunque. Ma stringere i permessi senza dare il file al gruppo
# del demone lo rende illeggibile anche a lui: shairport-sync non gira come
# root, e un file 640 root:root gli fa fallire l'avvio senza spiegazioni.
if [ -n "$BROKER_PASS" ]; then
    UTENTE_SPS="$(systemctl show -p User --value shairport-sync 2>/dev/null)"
    GRUPPO_SPS="$(systemctl show -p Group --value shairport-sync 2>/dev/null)"
    [ -z "$GRUPPO_SPS" ] && GRUPPO_SPS="$UTENTE_SPS"

    if [ -n "$GRUPPO_SPS" ] && getent group "$GRUPPO_SPS" >/dev/null 2>&1; then
        chgrp "$GRUPPO_SPS" "$CONF_SHAIRPORT"
        chmod 640 "$CONF_SHAIRPORT"
        passo "permessi root:$GRUPPO_SPS — il file contiene la password del broker"
    fi

    # Verifica invece di dare per scontato: si prova davvero a leggerlo con
    # l'identita' del demone. Se non ci riesce, meglio un file leggibile e un
    # servizio funzionante che il contrario, ma dicendolo a voce alta.
    if [ -n "$UTENTE_SPS" ] && [ "$UTENTE_SPS" != "root" ]; then
        if ! sudo -n -u "$UTENTE_SPS" test -r "$CONF_SHAIRPORT" 2>/dev/null; then
            chmod 644 "$CONF_SHAIRPORT"
            giallo "    ATTENZIONE: l'utente $UTENTE_SPS non riusciva a leggere la"
            giallo "    configurazione, quindi resta leggibile da tutti. Dentro"
            giallo "    c'e' la password del broker: valuta un utente MQTT"
            giallo "    dedicato al DMD, con i soli permessi che gli servono."
        fi
    fi
fi
verde "    scritto $CONF_SHAIRPORT"

# ------------------------------------------------------------ core riservato

titolo "Core riservato al pannello"
# Il DMD gira inchiodato al core 3 con priorita' realtime. Tutto il resto sta
# fuori: il pannello ha bisogno di tempi regolari piu' di quanto l'audio abbia
# bisogno di un core in piu'.
CORE_TOT="$(nproc)"
if [ "$CORE_TOT" -ge 4 ]; then
    for servizio in shairport-sync nqptp; do
        mkdir -p "/etc/systemd/system/${servizio}.service.d"
        cat > "/etc/systemd/system/${servizio}.service.d/dmd.conf" <<'FINE'
# Scritto da setup_nowplaying.sh: il core 3 e' del pannello.
[Service]
AllowedCPUs=0-2
Nice=5
FINE
        passo "$servizio confinato ai core 0-2"
    done
    esegui systemctl daemon-reload
else
    passo "$CORE_TOT core disponibili: nessun confinamento da impostare"
    passo "se hai isolcpus nel cmdline, il core riservato non viene contato"
    passo "qui e non e' comunque raggiungibile: il lavoro e' gia' fatto"
fi

esegui systemctl enable shairport-sync
esegui systemctl reset-failed shairport-sync
esegui systemctl restart shairport-sync
sleep 2
if ! attivo shairport-sync; then
    echo
    giallo "  Le ultime righe del suo journal:"
    journalctl -u shairport-sync -n 12 --no-pager 2>/dev/null | sed 's/^/    /'
    fallisci "shairport-sync non parte"
fi
verde "    shairport-sync attivo"

if ! attivo avahi-daemon; then
    esegui systemctl enable --now avahi-daemon
fi
attivo avahi-daemon || giallo "    avahi-daemon fermo: il DMD non comparira' fra le casse"

# ------------------------------------------------------------ lato DMD

titolo "Configurazione del DMD"
CONF_DMD="/etc/dmd/config.json"
if [ ! -f "$CONF_DMD" ]; then
    giallo "    $CONF_DMD non trovato: installa prima il DMD Controller."
    giallo "    Poi apri la pagina Musica e scrivi li' broker e topic."
else
    python3 - "$CONF_DMD" "$BROKER_HOST" "$BROKER_PORT" "$BROKER_USER" \
             "$BROKER_PASS" "$TOPIC" <<'PYFINE'
import json, sys
percorso, host, porta, utente, password, topic = sys.argv[1:7]
with open(percorso) as handle:
    cfg = json.load(handle)

mqtt = cfg.setdefault("mqtt", {})
mqtt["enabled"] = True
mqtt["host"] = host
mqtt["port"] = int(porta)
mqtt["username"] = utente
mqtt["password"] = password
mqtt["shairport_topic"] = topic
mqtt.setdefault("base_topic", "dmd")
mqtt.setdefault("client_id", "dmd")
mqtt.setdefault("external_topic", "dmd/external/nowplaying")
mqtt.setdefault("discovery", True)
mqtt.setdefault("discovery_prefix", "homeassistant")
mqtt.setdefault("node_id", "dmd")
mqtt.setdefault("device_name", "DMD Controller")
cfg.setdefault("services", {})["nowplaying"] = True

with open(percorso + ".tmp", "w") as handle:
    json.dump(cfg, handle, indent=2)
import os
os.replace(percorso + ".tmp", percorso)
print("    broker, topic e servizio Now Playing scritti in configurazione")
PYFINE
    if systemctl list-unit-files 2>/dev/null | grep -q '^dmd\.service'; then
        esegui systemctl restart dmd
        sleep 2
        if attivo dmd; then
            verde "    servizio dmd riavviato"
        else
            giallo "    il servizio dmd non e' ripartito: journalctl -u dmd -n 30"
        fi
    fi
fi

# ------------------------------------------------------------------ verifica

riepilogo

titolo "Prova finale"
echo
echo "  Sul telefono: metti musica e scegli \"$NOME_CASSA\" fra le casse."
echo "  Hai 30 secondi. Ascolto che cosa arriva sul broker."
echo
RISULTATO="$(timeout 30 mosquitto_sub -h "$BROKER_HOST" -p "$BROKER_PORT" \
             ${BROKER_USER:+-u "$BROKER_USER"} ${BROKER_PASS:+-P "$BROKER_PASS"} \
             -t "$TOPIC/#" -v 2>/dev/null | head -25)"
if [ -n "$RISULTATO" ]; then
    verde "  Arrivano i metadati:"
    echo "$RISULTATO" | sed 's/^/    /'
    echo
    verde "  Fatto. Il pannello dovrebbe gia' mostrare il brano."
else
    echo
    giallo "  Nessun messaggio ricevuto."
    echo "  Non vuol dire per forza che sia rotto: magari non hai fatto in"
    echo "  tempo. Per riprovare senza rifare nulla:"
    echo
    echo "      sudo $0 --verifica"
    echo
    echo "  Se anche cosi' non arriva niente, vedi il capitolo 10 della guida"
    echo "  DMD_now_playing: i sospetti in ordine sono avahi-daemon, nqptp e"
    echo "  il blocco mqtt in $CONF_SHAIRPORT."
fi

echo
echo "  Restano da fare a mano solo due cose, e solo se ti servono:"
echo "    - collegare l'account Spotify (pagina Musica, serve un browser)"
echo "    - le automazioni di Home Assistant per HomePod ed Echo"
echo
echo "  Registro completo di questa esecuzione: $LOG"
echo
