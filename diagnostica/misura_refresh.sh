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
# regime il valore e' fermo, ma ogni tanto crolla: un tuffo a 18,6 vuol dire
# un fotogramma durato 53 ms invece di 34, cioe' diciannove millisecondi
# spesi ad aspettare la memoria mentre una riga restava accesa. Quello e' il
# difetto, misurato invece che guardato.
#
# Due colonne, e vanno lette insieme: **media** e' quanto refresh hai,
# **disturbati** e' quanti fotogrammi si sono rovinati. Un parametro che
# dimezza i disturbati facendoti scendere a 22 Hz non e' un affare: hai
# scambiato un difetto raro con uno continuo.
#
# Uso
# ---
#   sudo /opt/dmd/diagnostica/misura_refresh.sh
#   sudo /opt/dmd/diagnostica/misura_refresh.sh --confronto
#   sudo /opt/dmd/diagnostica/misura_refresh.sh --chiave slowdown --sweep "4 5 6 7 8"
#   sudo /opt/dmd/diagnostica/misura_refresh.sh --chiave slowdown --sweep "4 5 6 7 8" --giri 2
#
#   --minuti N     durata di ogni finestra (2)
#   --chiave K     quale parametro di `panel` far variare (pwm_bits)
#   --sweep "..."  i valori da provare
#   --giri N       ripete lo sweep N volte **a giro**, non in fila (1)
#   --confronto    misura a riposo e poi sotto carico, generando lei la zavorra
#   --carico       aggiunge la zavorra a ogni misura
#   --soglia HZ    sotto quanti Hz un fotogramma si dice disturbato (28)
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
CHIAVE=pwm_bits
SWEEP=""
GIRI=1
CONFRONTO=0
CARICO=0
ASSESTAMENTO="${DMD_ASSESTAMENTO:-12}"   # secondi buttati via dopo ogni riavvio

# La zavorra va su disco **vero**: su Raspberry Pi OS /tmp e' in RAM, e
# scriverci non produrrebbe il traffico DMA verso la scheda che e' il
# disturbo da riprodurre.
ZAVORRA_DIR="${DMD_ZAVORRA_DIR:-/var/lib/dmd}"
ZAVORRA_MB="${DMD_ZAVORRA_MB:-100}"

LUCCHETTO="${DMD_LUCCHETTO:-/run/dmd-misura.lock}"

# ------------------------------------------------------------------ argomenti

while [ $# -gt 0 ]; do
    case "$1" in
        --minuti)     MINUTI="$2"; shift 2 ;;
        --soglia)     SOGLIA="$2"; shift 2 ;;
        --chiave)     CHIAVE="$2"; shift 2 ;;
        --sweep)      SWEEP="$2"; shift 2 ;;
        --giri)       GIRI="$2"; shift 2 ;;
        --confronto)  CONFRONTO=1; shift ;;
        --carico)     CARICO=1; shift ;;
        --aiuto|-h|--help)
            sed -n '2,42p' "$0" | sed 's/^# \{0,1\}//'
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

# ------------------------------------------------------------------ lucchetto
#
# Due istanze insieme non misurano due cose: leggono lo stesso journal e
# stampano lo stesso numero, dandoti l'illusione di un confronto. E si
# pestano i piedi, perche' ognuna riavvia il servizio in mezzo alla finestra
# dell'altra. E' successo davvero, ed e' il motivo per cui questo pezzo c'e'.
#
# `mkdir` e non un file: e' atomico, quindi non esiste la finestra fra
# «guardo se c'e'» e «lo creo» in cui due processi passano entrambi.
if ! mkdir "$LUCCHETTO" 2>/dev/null; then
    echo "un'altra misura e' gia' in corso ($LUCCHETTO)." >&2
    echo "aspetta che finisca; se e' rimasto li' da una sessione andata male:" >&2
    echo "  sudo rmdir $LUCCHETTO" >&2
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
import json, os, sys
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
os.replace(tmp, percorso)
PY
}

VALORE_ORIGINALE="$(leggi panel "$CHIAVE")"
SHOW_ORIGINALE="$(leggi panel show_refresh)"

if [ -n "$SWEEP" ] && [ -z "$VALORE_ORIGINALE" ]; then
    rmdir "$LUCCHETTO" 2>/dev/null
    echo "in panel non c'e' nessuna chiave '$CHIAVE': controlla il nome" >&2
    exit 1
fi

ATTESA=""
ZAVORRA="$ZAVORRA_DIR/zavorra"
SENTINELLA="$ZAVORRA_DIR/.zavorra-attiva"
CARICO_PID=""

# ------------------------------------------------------------------- zavorra

carico_avvia() {
    : > "$SENTINELLA"
    (
        while [ -f "$SENTINELLA" ]; do
            dd if=/dev/zero of="$ZAVORRA" bs=1M count="$ZAVORRA_MB" \
               oflag=direct 2>/dev/null
            rm -f "$ZAVORRA"
        done
    ) &
    CARICO_PID=$!
}

carico_ferma() {
    [ -n "$CARICO_PID" ] || return 0
    # Prima la sentinella: il ciclo esce da solo appena finisce il `dd` in
    # corso, senza lasciare un `dd` orfano che continua a scrivere.
    rm -f "$SENTINELLA"
    local attesa=0
    while kill -0 "$CARICO_PID" 2>/dev/null && [ "$attesa" -lt 30 ]; do
        sleep 1
        attesa=$((attesa + 1))
    done
    kill "$CARICO_PID" 2>/dev/null
    wait "$CARICO_PID" 2>/dev/null
    CARICO_PID=""
    rm -f "$ZAVORRA"
}

# ---------------------------------------------------------------- ripristino

ripristina() {
    [ -n "$ATTESA" ] && kill "$ATTESA" 2>/dev/null
    carico_ferma
    echo
    echo "-- rimetto la configurazione com'era"
    [ -n "$VALORE_ORIGINALE" ] && scrivi panel "$CHIAVE" "$VALORE_ORIGINALE"
    if [ "$SHOW_ORIGINALE" != "True" ]; then
        scrivi panel show_refresh false
    fi
    systemctl restart dmd
    rmdir "$LUCCHETTO" 2>/dev/null
    echo "   $CHIAVE=$VALORE_ORIGINALE  show_refresh=$SHOW_ORIGINALE  servizio riavviato"
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

RACCOLTA="$(mktemp)"

misura() {   # misura <etichetta> [carico]
    local etichetta="$1" con_carico="${2:-0}" inizio fine
    [ "$con_carico" = "1" ] && carico_avvia
    inizio=$(date +%s)
    attendi "$SECONDI"
    fine=$(date +%s)
    [ "$con_carico" = "1" ] && carico_ferma
    local dati
    dati="$(statistiche "$inizio" "$fine")"
    echo "$etichetta $dati" >> "$RACCOLTA"
    riga_tabella "$etichetta" "$dati"
}

riga_tabella() {   # riga_tabella <etichetta> "<n media min max sotto gravi>"
    local etichetta="$1"
    set -- $2
    local n="$1" media="$2" min="$3" sotto="$5"
    if [ "$n" = "0" ]; then
        printf '%-14s  %8s  %7s  %7s  %14s  %8s\n' \
               "$etichetta" "—" "—" "—" "nessun campione" "—"
        return
    fi
    local perc al_minuto
    perc=$(awk -v a="$sotto" -v b="$n" 'BEGIN{printf "%.2f", 100*a/b}')
    al_minuto=$(awk -v a="$sotto" -v m="$MINUTI" 'BEGIN{printf "%.0f", a/m}')
    printf '%-14s  %8d  %7s  %7s  %6s (%5s%%)  %8s\n' \
           "$etichetta" "$n" "$media" "$min" "$sotto" "$perc" "$al_minuto"
}

intestazione() {
    printf '\n%-14s  %8s  %7s  %7s  %14s  %8s\n' \
           "config" "campioni" "media" "minimo" "disturbati" "al min."
    printf '%s\n' "------------------------------------------------------------------------------"
}

riepilogo() {
    # Con piu' giri le righe singole non bastano: quello che conta e' il
    # totale per configurazione, perche' e' li' che il rumore di fondo —
    # spalmato apposta su tutti i giri — si media invece di appiccicarsi
    # alla prima misura.
    [ "$GIRI" -gt 1 ] || return 0
    echo
    echo "riepilogo per configurazione ($GIRI giri):"
    printf '%-14s  %8s  %7s  %7s  %14s\n' \
           "config" "campioni" "media" "minimo" "disturbati"
    printf '%s\n' "----------------------------------------------------------------"
    awk '
        { split($1, p, "/"); c = p[1]
          n[c] += $2; somma[c] += $3 * $2; s[c] += $6
          if (!(c in mn) || $4 < mn[c]) mn[c] = $4
          if (!(c in ordine)) { ordine[c] = ++k; nomi[k] = c } }
        END { for (i = 1; i <= k; i++) { c = nomi[i]
                  if (n[c] == 0) { printf "%-14s  %8s\n", c, "—"; continue }
                  printf "%-14s  %8d  %7.1f  %7.1f  %6d (%5.2f%%)\n",
                         c, n[c], somma[c]/n[c], mn[c], s[c], 100*s[c]/n[c] } }
    ' "$RACCOLTA"
}

# ----------------------------------------------------------------- esecuzione

SECONDI=$(awk -v m="$MINUTI" 'BEGIN{printf "%d", m*60}')

echo "=== misura del refresh — $(date '+%Y-%m-%d %H:%M') ==="
echo "pannello:  pwm_bits=$(leggi panel pwm_bits)  slowdown=$(leggi panel slowdown)" \
     " lsb_ns=$(leggi panel pwm_lsb_nanoseconds)  dither=$(leggi panel pwm_dither_bits)"
echo "cablaggio: $(leggi panel hardware_mapping)   registri: profilo $(leggi panel spwm_register_config)"
echo "soglie:    disturbato sotto ${SOGLIA} Hz, grave sotto ${SOGLIA_GRAVE} Hz"
echo "finestra:  ${MINUTI} min per misura"
if [ "$CONFRONTO" = "1" ] || [ "$CARICO" = "1" ]; then
    echo "zavorra:   ${ZAVORRA_MB} MB per giro su $ZAVORRA_DIR (disco, non RAM)"
fi
echo
echo "NON aprire la web UI durante la misura."

# Il refresh nel log serve, e se e' spento lo accendo io (e lo rispengo dopo).
if [ "$SHOW_ORIGINALE" != "True" ]; then
    echo "-- accendo la scrittura del refresh nel log"
    scrivi panel show_refresh true
    systemctl restart dmd
    sleep "$ASSESTAMENTO"
fi

if [ "$CONFRONTO" = "1" ]; then
    # L'esperimento della contesa sul bus, in un comando: le due finestre
    # sono consecutive e la zavorra la genera lei, cosi' non serve
    # coordinare due terminali a mano — che e' come si sbaglia.
    intestazione
    misura "riposo" 0
    misura "carico" 1
elif [ -z "$SWEEP" ]; then
    intestazione
    misura "attuale" "$CARICO"
else
    intestazione
    giro=1
    while [ "$giro" -le "$GIRI" ]; do
        for valore in $SWEEP; do
            scrivi panel "$CHIAVE" "$valore"
            systemctl restart dmd
            sleep "$ASSESTAMENTO"
            if [ "$GIRI" -gt 1 ]; then
                misura "$CHIAVE=$valore/$giro" "$CARICO"
            else
                misura "$CHIAVE=$valore" "$CARICO"
            fi
        done
        giro=$((giro + 1))
    done
    riepilogo
fi

rm -f "$RACCOLTA"

echo
echo "«disturbati» = fotogrammi sotto ${SOGLIA} Hz, cioe' quelli in cui la"
echo "libreria ha aspettato la memoria mentre una riga restava accesa."
echo "Leggi «media» e «disturbati» insieme: meno disturbi pagati con dieci Hz"
echo "in meno non sono un affare."
