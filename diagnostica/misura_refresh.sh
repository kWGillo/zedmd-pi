#!/bin/bash
# Misura il refresh reale del pannello, e conta i fotogrammi disturbati.
#
# Perche' esiste
# --------------
# La caccia alle righe chiare e' andata avanti per settimane a occhio: si
# cambiava un parametro, si guardava il pannello, e si decideva se sembrava
# meglio. Con un difetto casuale, che non capita mai nello stesso punto, quel
# metodo non distingue un miglioramento vero da una serie fortunata.
#
# La libreria pero' scrive il refresh di **ogni fotogramma** nel log. In
# regime il valore e' fermo (29,3 Hz), ma ogni tanto crolla: un tuffo a 18,9
# vuol dire un fotogramma durato 53 ms invece di 34, cioe' diciannove
# millisecondi spesi ad aspettare la memoria mentre una riga restava accesa.
# Quello e' il difetto, misurato invece che guardato.
#
# Quindi: **contare i tuffi** sostituisce il guardare il pannello. Un numero,
# confrontabile fra due configurazioni, ripetibile domani.
#
# Uso
# ---
#   sudo /opt/dmd/diagnostica/misura_refresh.sh
#   sudo /opt/dmd/diagnostica/misura_refresh.sh --minuti 3
#   sudo /opt/dmd/diagnostica/misura_refresh.sh --sweep "11 10 9"
#   sudo /opt/dmd/diagnostica/misura_refresh.sh --sweep "11 10 9" --minuti 3
#
# Durante la misura **non aprire la web UI**: ogni ricarica di pagina e'
# Python che lavora e rete che si muove, cioe' esattamente il disturbo che
# stiamo cercando di misurare. Lascia l'orologio a schermo e non toccare
# niente.
set -u

CONFIG="${DMD_CONFIG:-/etc/dmd/config.json}"
MINUTI=2
SOGLIA=28
SOGLIA_GRAVE=25
SWEEP=""
ASSESTAMENTO="${DMD_ASSESTAMENTO:-12}"   # secondi buttati via dopo ogni riavvio

# ------------------------------------------------------------------ argomenti

while [ $# -gt 0 ]; do
    case "$1" in
        --minuti)  MINUTI="$2"; shift 2 ;;
        --soglia)  SOGLIA="$2"; shift 2 ;;
        --sweep)   SWEEP="$2"; shift 2 ;;
        --aiuto|-h|--help)
            sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *) echo "argomento sconosciuto: $1 (--aiuto per l'uso)" >&2; exit 2 ;;
    esac
done

if [ "$(id -u)" != "0" ]; then
    echo "serve root: rilancia con sudo" >&2
    exit 1
fi
if [ ! -f "$CONFIG" ]; then
    echo "configurazione non trovata: $CONFIG" >&2
    exit 1
fi

# --------------------------------------------------------------- config.json
# Con python3 e non con sed: un file JSON si modifica leggendolo, non
# indovinando dove sta la virgola.

leggi() {   # leggi <sezione> <chiave>
    python3 - "$CONFIG" "$1" "$2" <<'PY'
import json, sys
try:
    with open(sys.argv[1]) as f:
        print(json.load(f).get(sys.argv[2], {}).get(sys.argv[3], ""))
except Exception:
    print("")
PY
}

scrivi() {  # scrivi <sezione> <chiave> <valore json>
    python3 - "$CONFIG" "$1" "$2" "$3" <<'PY'
import json, sys
percorso, sezione, chiave, valore = sys.argv[1:5]
with open(percorso) as f:
    dati = json.load(f)
try:
    valore = json.loads(valore)
except ValueError:
    pass
dati.setdefault(sezione, {})[chiave] = valore
tmp = percorso + ".tmp"
with open(tmp, "w") as f:
    json.dump(dati, f, indent=2)
import os
os.replace(tmp, percorso)
PY
}

PWM_ORIGINALE="$(leggi panel pwm_bits)"
SHOW_ORIGINALE="$(leggi panel show_refresh)"

ATTESA=""

ripristina() {
    [ -n "$ATTESA" ] && kill "$ATTESA" 2>/dev/null
    echo
    echo "-- rimetto la configurazione com'era"
    [ -n "$PWM_ORIGINALE" ] && scrivi panel pwm_bits "$PWM_ORIGINALE"
    if [ "$SHOW_ORIGINALE" != "True" ]; then
        scrivi panel show_refresh false
    fi
    systemctl restart dmd
    echo "   pwm_bits=$PWM_ORIGINALE  show_refresh=$SHOW_ORIGINALE  servizio riavviato"
}
# Due trap distinte, e non e' pignoleria: una trap su INT/TERM che si limita
# a ripulire **non ferma lo script** — bash riprende dalla riga dopo, e uno
# sweep interrotto proseguirebbe con le configurazioni successive. Quella sui
# segnali quindi esce, e l'uscita fa scattare quella su EXIT, che ripulisce
# una volta sola.
trap ripristina EXIT
trap 'echo; echo "-- interrotto"; exit 130' INT TERM

# ------------------------------------------------------------------- misura

# L'attesa sta **fuori** dalla sostituzione di comando, e usa `sleep &` +
# `wait`: un `sleep` in primo piano bloccherebbe la trap fino alla sua fine,
# e un Ctrl+C durante una finestra da tre minuti sembrerebbe ignorato per tre
# minuti. Con `wait` il segnale arriva subito e il ripristino parte.
attendi() {
    sleep "$1" &
    ATTESA=$!
    wait "$ATTESA"
    ATTESA=""
}

statistiche() {   # statistiche <inizio> <fine> -> "n media min max sotto gravi"
    local inizio="$1" fine="$2"
    journalctl -u dmd -a --since "@$inizio" --until "@$fine" 2>/dev/null \
        | tr '\r\b' '\n\n' \
        | grep -oE '[0-9]+\.[0-9]+Hz' | tr -d 'Hz' \
        | awk -v s="$SOGLIA" -v g="$SOGLIA_GRAVE" '
            { n++; tot+=$1
              if (!min || $1 < min) min = $1
              if ($1 > max) max = $1
              if ($1 < s) sotto++
              if ($1 < g) gravi++ }
            END { if (n == 0) { print "0 0 0 0 0 0"; exit }
                  printf "%d %.1f %.1f %.1f %d %d\n",
                         n, tot/n, min, max, sotto+0, gravi+0 }'
}

misura() {   # misura <etichetta>: aspetta la finestra e stampa la riga
    local inizio fine
    inizio=$(date +%s)
    attendi "$SECONDI"
    fine=$(date +%s)
    riga_tabella "$1" "$(statistiche "$inizio" "$fine")" "$MINUTI"
}

riga_tabella() {   # riga_tabella <etichetta> <risultato di statistiche> <minuti>
    local etichetta="$1" minuti="$3"
    set -- $2
    local n="$1" media="$2" min="$3" max="$4" sotto="$5" gravi="$6"
    if [ "$n" = "0" ]; then
        printf '%-10s  %8s  %7s  %7s  %10s  %8s\n' \
               "$etichetta" "—" "—" "—" "nessun campione" "—"
        return
    fi
    local perc al_minuto
    perc=$(awk -v a="$sotto" -v b="$n" 'BEGIN{printf "%.2f", 100*a/b}')
    al_minuto=$(awk -v a="$sotto" -v m="$minuti" 'BEGIN{printf "%.0f", a/m}')
    printf '%-10s  %8d  %7s  %7s  %6s (%s%%)  %8s\n' \
           "$etichetta" "$n" "$media" "$min" "$sotto" "$perc" "$al_minuto"
}

intestazione() {
    printf '\n%-10s  %8s  %7s  %7s  %14s  %8s\n' \
           "config" "campioni" "media" "minimo" "disturbati" "al min."
    printf '%s\n' "--------------------------------------------------------------------------"
}

# ----------------------------------------------------------------- esecuzione

SECONDI=$(awk -v m="$MINUTI" 'BEGIN{printf "%d", m*60}')

echo "=== misura del refresh — $(date '+%Y-%m-%d %H:%M') ==="
echo "pannello:  pwm_bits=$(leggi panel pwm_bits)  slowdown=$(leggi panel slowdown)" \
     " lsb_ns=$(leggi panel pwm_lsb_nanoseconds)  dither=$(leggi panel pwm_dither_bits)"
echo "cablaggio: $(leggi panel hardware_mapping)   registri: profilo $(leggi panel spwm_register_config)"
echo "soglie:    disturbato sotto ${SOGLIA} Hz, grave sotto ${SOGLIA_GRAVE} Hz"
echo "finestra:  ${MINUTI} min per configurazione"
echo
echo "NON aprire la web UI durante la misura."

# Il refresh nel log serve, e se e' spento lo accendo io (e lo rispengo dopo).
if [ "$SHOW_ORIGINALE" != "True" ]; then
    echo "-- accendo la scrittura del refresh nel log"
    scrivi panel show_refresh true
    systemctl restart dmd
    sleep "$ASSESTAMENTO"
fi

if [ -z "$SWEEP" ]; then
    intestazione
    misura "attuale"
else
    intestazione
    for valore in $SWEEP; do
        scrivi panel pwm_bits "$valore"
        systemctl restart dmd
        sleep "$ASSESTAMENTO"
        misura "pwm=$valore"
    done
fi

echo
echo "«disturbati» = fotogrammi sotto ${SOGLIA} Hz, cioe' quelli in cui la"
echo "libreria ha aspettato la memoria mentre una riga restava accesa."
echo "E' il conteggio da confrontare fra due configurazioni, non la media."
