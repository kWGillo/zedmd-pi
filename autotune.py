# -*- coding: utf-8 -*-
"""Taratura automatica del pannello: misurare invece di guardare.

Perche' esiste
--------------
La caccia alle righe chiare e' andata avanti per settimane a occhio: si
cambiava un parametro, si guardava il pannello, si decideva se sembrava
meglio. Con un difetto casuale, che non capita mai nello stesso punto, quel
metodo non distingue un miglioramento vero da una serie fortunata.

La libreria pero' scrive il refresh di **ogni fotogramma** nel log. In regime
il valore sta fermo; ogni tanto crolla, e un tuffo da 29,3 a 18,6 Hz vuol dire
un fotogramma durato 53 ms invece di 34 — diciannove millisecondi passati ad
aspettare la memoria mentre una riga del pannello restava accesa. Quello e'
il difetto, e si conta.

Come si legge il refresh
------------------------
Con `journalctl -a` e un `tr`. La libreria riscrive il valore sulla stessa
riga con un ritorno a capo, come una barra di avanzamento: journald riceve un
messaggio senza fine riga, decide che e' binario e mostra `[29.8K blob data]`.
E' il genere di cosa che fa credere per mesi che un'opzione non funzioni.

La soglia e' relativa
---------------------
Un fotogramma e' disturbato se sta piu' del 5% sotto il **regime della sua
configurazione** — il massimo della finestra, cioe' il valore che il pannello
tiene quando nessuno lo disturba. Con una soglia fissa in Hz, uno sweep che
muove il refresh stesso boccerebbe le configurazioni piu' lente per il solo
fatto di essere piu' lente: e' successo, e la tabella diceva 100%.

I fotogrammi contaminati
------------------------
Ogni richiesta alla web UI e' Python che lavora e rete che si muove, cioe'
esattamente il disturbo che si sta misurando. Non si puo' spegnere
l'interfaccia — servirebbe per far partire e per leggere i risultati — quindi
si fa l'altra cosa: si **conta** il traffico durante ogni finestra, e le
finestre sporcate si marcano e si buttano. Una misura sporca dichiarata vale
piu' di una misura che credi pulita.
"""

import datetime
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

DATA_DIR = os.environ.get("DMD_AUTOTUNE_DIR", "/var/lib/dmd")
STATO_PATH = os.path.join(DATA_DIR, "autotune.json")
LOG_PATH = os.path.join(DATA_DIR, "autotune.log")
STOP_PATH = os.path.join(DATA_DIR, "autotune.stop")

INSTALL_DIR = os.path.dirname(os.path.abspath(__file__))

# Secondi buttati via dopo ogni riavvio del servizio: il pannello ci mette un
# momento ad assestarsi, e i primi fotogrammi non sono rappresentativi.
ASSESTAMENTO = int(os.environ.get("DMD_ASSESTAMENTO", "12"))

# Finestra minima. Meno di mezzo minuto non e' una misura: a trenta fotogrammi
# al secondo servono migliaia di campioni perche' una frazione dello 0,1% sia
# distinguibile dal caso. Configurabile solo perche' le prove non possono
# aspettare mezzo minuto per riga.
MIN_FINESTRA = int(os.environ.get("DMD_MIN_FINESTRA", "30"))

# Di quanto un fotogramma deve stare sotto il regime per dirsi disturbato.
CALO = 5.0          # tremolio
CALO_GRAVE = 10.0   # tuffo vero

_HZ = re.compile(r"([0-9]+\.[0-9]+)Hz")


# --------------------------------------------------------------- i parametri
#
# Solo quelli che ha senso far variare da soli, con un intervallo entro cui
# non si rompe niente. Cambiare la geometria o il tipo di pannello non e'
# taratura: e' dire che pannello si ha, e sta nei profili.

PARAMETRI = {
    "slowdown": {
        "label": "Rallentamento GPIO",
        "valori": [4, 5, 6, 7, 8],
        "minimo": 1, "massimo": 10,
        "nota": ("La leva vera del refresh. Piu' basso vuol dire piu' Hz, ma "
                 "sotto un certo punto il ciclo gira al limite e non ha piu' "
                 "margine per assorbire i disturbi."),
    },
    "pwm_bits": {
        "label": "Profondita' PWM",
        "valori": [9, 10, 11],
        "minimo": 1, "massimo": 11,
        "nota": ("Su un pannello S-PWM come l'FM6373 la modulazione la fa il "
                 "chip, non il Raspberry: qui la profondita' quasi non muove "
                 "il refresh, ed e' una buona notizia."),
    },
    "pwm_lsb_nanoseconds": {
        "label": "Durata bit minimo (ns)",
        "valori": [100, 125, 150, 200],
        "minimo": 50, "massimo": 3000,
        "nota": ("Accorcia ogni sotto-frame. Sotto gli 80 ns i toni scuri "
                 "diventano imprecisi."),
    },
    "pwm_dither_bits": {
        "label": "Bit con dithering",
        "valori": [0, 1, 2],
        "minimo": 0, "massimo": 2,
        "nota": ("Alza il refresh a parita' di profondita' dichiarata, al "
                 "prezzo di un po' di brulichio sulle sfumature."),
    },
}


def parametro_valido(nome):
    return nome in PARAMETRI


def valori_validi(nome, valori):
    """Filtra e ordina i valori chiesti, tenendo solo quelli sensati."""
    regola = PARAMETRI.get(nome)
    if not regola:
        return []
    fuori = []
    for grezzo in valori:
        try:
            numero = int(str(grezzo).strip())
        except (TypeError, ValueError):
            continue
        if regola["minimo"] <= numero <= regola["massimo"] and numero not in fuori:
            fuori.append(numero)
    return sorted(fuori)


# ------------------------------------------------------------------- stato

def _scrivi_stato(dati):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = STATO_PATH + ".tmp"
    with open(tmp, "w") as handle:
        json.dump(dati, handle, indent=2)
    os.replace(tmp, STATO_PATH)


def stato():
    try:
        with open(STATO_PATH) as handle:
            dati = json.load(handle)
        return dati if isinstance(dati, dict) else {}
    except (OSError, ValueError):
        return {}


def _vivo(pid):
    """Vero se quel processo esiste **ed e' il nostro**.

    Il controllo sul nome del comando non e' pignoleria: dopo un riavvio i
    numeri di processo ricominciano da capo, e il 1234 di ieri oggi puo'
    essere il server web. Senza guardare cosa sta girando davvero, una
    taratura morta continuerebbe a sembrare viva a caso.
    """
    try:
        with open("/proc/%d/cmdline" % int(pid), "rb") as handle:
            argomenti = handle.read().split(b"\0")
    except (OSError, ValueError, TypeError):
        return False
    # Confronto sul nome del file, non sottostringa: `test_autotune.py`
    # contiene `autotune.py`, e passare per un sottoinsieme di nome sarebbe
    # il modo piu' sciocco di scambiare un processo per un altro.
    return any(os.path.basename(a.decode("utf-8", "replace")) == "autotune.py"
               for a in argomenti if a)


def _chiudi_orfana(dati):
    """Una taratura il cui processo non c'e' piu' e' finita, punto."""
    dati = dict(dati)
    dati.update({"in_corso": False, "interrotta": True,
                 "aggiornato": time.time()})
    _scrivi_stato(dati)
    log("taratura interrotta: il processo non c'e' piu' (riavvio o arresto)")


def in_corso():
    """Vero solo se una taratura sta **davvero** girando adesso.

    Fidarsi del flag scritto nel file era un difetto vero: spegnendo il
    Raspberry a meta' taratura, il processo moriva e il file restava a dire
    "in corso". Alla riaccensione l'interfaccia offriva «Ferma la taratura»
    per una taratura che non esisteva, e il pulsante per avviarne una non
    tornava piu'. Un flag su disco dice cosa e' successo, non cosa sta
    succedendo: quello lo dice solo il processo.
    """
    dati = stato()
    if not dati.get("in_corso"):
        return False
    if not _vivo(dati.get("pid")):
        _chiudi_orfana(dati)
        return False
    # Rete di sicurezza per il caso in cui il processo esista ma sia appeso:
    # una finestra dura minuti, non ore.
    if time.time() - float(dati.get("aggiornato", 0)) > 6 * 3600:
        _chiudi_orfana(dati)
        return False
    return True


def log(messaggio):
    riga = "%s  %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), messaggio)
    print(riga, flush=True)
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(LOG_PATH, "a") as handle:
            handle.write(riga + "\n")
    except OSError:
        pass


def coda_log(righe=30):
    try:
        with open(LOG_PATH) as handle:
            return "".join(handle.readlines()[-righe:])
    except OSError:
        return ""


# -------------------------------------------------------------- misurazione

def _campioni(inizio, fine):
    """I refresh scritti nel log fra due istanti. Lista di float."""
    try:
        grezzo = subprocess.run(
            ["journalctl", "-u", "dmd", "-a",
             "--since", "@%d" % inizio, "--until", "@%d" % fine],
            capture_output=True, timeout=120).stdout.decode("utf-8", "replace")
    except (OSError, subprocess.SubprocessError):
        return []
    # I ritorni a capo diventano righe vere: senza questo passaggio i valori
    # restano incollati fra loro e non si legge niente.
    testo = grezzo.replace("\r", "\n").replace("\b", "\n")
    return [float(v) for v in _HZ.findall(testo)]


def statistiche(valori, calo=CALO, calo_grave=CALO_GRAVE):
    """Da una lista di refresh alle cifre che contano.

    Due passate: la prima non puo' sapere quale sia il regime, che e' il
    massimo della finestra. La soglia si calcola dopo, e solo allora si
    contano i tuffi.
    """
    if not valori:
        return {"n": 0}
    regime = max(valori)
    soglia = regime * (1 - calo / 100.0)
    soglia_grave = regime * (1 - calo_grave / 100.0)
    disturbati = sum(1 for v in valori if v < soglia)
    gravi = sum(1 for v in valori if v < soglia_grave)
    return {
        "n": len(valori),
        "regime": round(regime, 1),
        "media": round(sum(valori) / len(valori), 1),
        "minimo": round(min(valori), 1),
        "soglia": round(soglia, 1),
        "disturbati": disturbati,
        "gravi": gravi,
        "percento": round(100.0 * disturbati / len(valori), 2),
        "percento_gravi": round(100.0 * gravi / len(valori), 2),
    }


def _richieste(porta):
    """Quante richieste ha servito la web UI finora. None se non risponde."""
    try:
        with urllib.request.urlopen(
                "http://127.0.0.1:%d/api/richieste" % porta, timeout=5) as r:
            return int(json.loads(r.read().decode("utf-8")).get("richieste", 0))
    except Exception:
        return None


def _servizio(azione):
    try:
        subprocess.run(["systemctl", azione, "dmd"], timeout=60)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


# ------------------------------------------------------------- la decisione

def scegli(riepilogo):
    """La configurazione consigliata, e perche'.

    La regola, in una riga: **fra quelle che si disturbano di meno, quella
    con il refresh piu' alto.** Non la piu' veloce e basta — il valore col
    refresh nominale piu' alto puo' essere quello che gira al limite e
    tremola — e nemmeno la piu' tranquilla e basta, che sarebbe sempre la
    piu' lenta.
    """
    valide = [r for r in riepilogo if r.get("n")]
    if not valide:
        return None
    minimo = min(r["percento"] for r in valide)
    # Mezzo punto di tolleranza: fra 0,07% e 0,18% non c'e' differenza vera,
    # e pretendere il minimo esatto vorrebbe dire farsi guidare dal rumore.
    vicine = [r for r in valide if r["percento"] <= minimo + 0.5]
    scelta = max(vicine, key=lambda r: r["regime"])
    return {
        "valore": scelta["valore"],
        "regime": scelta["regime"],
        "percento": scelta["percento"],
        "fra": len(vicine),
        "peggiore": max(r["percento"] for r in valide),
    }


def riassumi(righe):
    """Somma i giri per configurazione, buttando le finestre contaminate."""
    per_valore = {}
    for riga in righe:
        chiave = riga["valore"]
        voce = per_valore.setdefault(chiave, {
            "valore": chiave, "n": 0, "disturbati": 0, "gravi": 0,
            "regime": 0.0, "minimo": 0.0, "somma": 0.0,
            "scartate": 0, "vuote": 0})
        if riga.get("contaminata"):
            voce["scartate"] += 1
            continue
        if not riga.get("n"):
            voce["vuote"] += 1
            continue
        voce["n"] += riga["n"]
        voce["disturbati"] += riga["disturbati"]
        voce["gravi"] += riga["gravi"]
        voce["somma"] += riga["media"] * riga["n"]
        voce["regime"] = max(voce["regime"], riga["regime"])
        voce["minimo"] = (riga["minimo"] if not voce["minimo"]
                          else min(voce["minimo"], riga["minimo"]))
    fuori = []
    for voce in sorted(per_valore.values(), key=lambda v: v["valore"]):
        if voce["n"]:
            voce["media"] = round(voce["somma"] / voce["n"], 1)
            voce["percento"] = round(100.0 * voce["disturbati"] / voce["n"], 2)
            voce["percento_gravi"] = round(100.0 * voce["gravi"] / voce["n"], 2)
        else:
            voce["media"] = 0.0
            voce["percento"] = 0.0
            voce["percento_gravi"] = 0.0
        voce.pop("somma", None)
        fuori.append(voce)
    return fuori


# ---------------------------------------------------------------- esecuzione

def _leggi_config(percorso):
    with open(percorso) as handle:
        return json.load(handle)


def _scrivi_valore(percorso, chiave, valore):
    dati = _leggi_config(percorso)
    dati.setdefault("panel", {})[chiave] = valore
    tmp = percorso + ".tmp"
    with open(tmp, "w") as handle:
        json.dump(dati, handle, indent=2)
    os.replace(tmp, percorso)


def esegui(percorso_config, chiave, valori, minuti, giri, porta):
    """Lo sweep vero. Gira nel processo staccato, non nel servizio."""
    originale = (_leggi_config(percorso_config).get("panel") or {}).get(chiave)
    show_originale = bool(
        (_leggi_config(percorso_config).get("panel") or {}).get("show_refresh"))
    secondi = max(MIN_FINESTRA, int(float(minuti) * 60))
    totale = len(valori) * int(giri)
    righe = []
    fatte = 0

    def aggiorna(**extra):
        dati = {
            "in_corso": True, "chiave": chiave, "valori": valori,
            "minuti": minuti, "giri": giri,
            "fatte": fatte, "totale": totale,
            "iniziata": iniziata, "aggiornato": time.time(),
            "pid": os.getpid(),
            "righe": righe, "riepilogo": riassumi(righe),
            "originale": originale,
        }
        dati["consiglio"] = scegli(dati["riepilogo"])
        dati.update(extra)
        _scrivi_stato(dati)

    iniziata = time.time()
    try:
        os.remove(STOP_PATH)
    except OSError:
        pass

    log("=== taratura di %s su %s, %s min x %s giri ==="
        % (chiave, valori, minuti, giri))
    aggiorna()

    try:
        if not show_originale:
            _scrivi_valore(percorso_config, "show_refresh", True)
            _servizio("restart")
            time.sleep(ASSESTAMENTO)

        for giro in range(1, int(giri) + 1):
            for valore in valori:
                if os.path.exists(STOP_PATH):
                    log("fermata su richiesta")
                    return
                _scrivi_valore(percorso_config, chiave, valore)
                _servizio("restart")
                time.sleep(ASSESTAMENTO)

                prima = _richieste(porta)
                inizio = int(time.time())
                time.sleep(secondi)
                fine = int(time.time())
                dopo = _richieste(porta)

                misura = statistiche(_campioni(inizio, fine))
                # Contaminata: qualcuno ha usato la web UI mentre misuravamo.
                # Non e' un errore dell'utente — e' un fatto da dichiarare.
                traffico = (dopo - prima) if (prima is not None
                                              and dopo is not None) else 0
                riga = dict(misura)
                riga.update({"valore": valore, "giro": giro,
                             "richieste": max(0, traffico),
                             "contaminata": traffico > 0})
                righe.append(riga)
                fatte += 1
                log("%s=%s giro %d: regime %s, disturbati %s%%%s"
                    % (chiave, valore, giro, misura.get("regime", "—"),
                       misura.get("percento", "—"),
                       " [contaminata: %d richieste]" % traffico
                       if traffico > 0 else ""))
                aggiorna()
    finally:
        # Il pannello torna esattamente com'era: la taratura **propone**, non
        # decide. Il risultato compare come voce nel menu dei profili, e si
        # applica quando e se lo si vuole.
        if originale is not None:
            _scrivi_valore(percorso_config, chiave, originale)
        if not show_originale:
            _scrivi_valore(percorso_config, "show_refresh", False)
        riepilogo = riassumi(righe)
        consiglio = scegli(riepilogo)
        if consiglio:
            riga = next((r for r in riepilogo
                         if r.get("valore") == consiglio["valore"]), {})
            _scrivi_profilo(percorso_config,
                            profilo(chiave, consiglio["valore"], riga))
        _servizio("restart")
        dati = stato()
        dati.update({"in_corso": False, "finita": time.time(),
                     "righe": righe, "riepilogo": riassumi(righe),
                     "fatte": fatte, "totale": totale,
                     "chiave": chiave, "originale": originale,
                     "aggiornato": time.time()})
        dati["consiglio"] = scegli(dati["riepilogo"])
        _scrivi_stato(dati)
        log("finita: %d misure, consiglio %s" % (fatte, dati.get("consiglio")))


PREDEFINITO = "slowdown"


def avvia(cfg, chiave=None, valori=None, minuti=2, giri=2):
    """Lancia la taratura in un processo staccato, che sopravvive al riavvio.

    Deve essere staccato per forza: lo sweep riavvia il servizio a ogni
    configurazione, e un processo figlio di quel servizio morirebbe al primo
    riavvio portandosi via la taratura e lasciando il pannello sul valore di
    prova.
    """
    if in_corso():
        raise ValueError("una taratura e' gia' in corso")
    chiave = chiave or PREDEFINITO
    if valori is None:
        valori = PARAMETRI[chiave]["valori"]
    if not parametro_valido(chiave):
        raise ValueError("parametro non tarabile: %s" % chiave)
    valori = valori_validi(chiave, valori)
    if len(valori) < 2:
        raise ValueError("servono almeno due valori da confrontare")
    percorso = os.environ.get("DMD_CONFIG", "/etc/dmd/config.json")
    args = [sys.executable, os.path.join(INSTALL_DIR, "autotune.py"), "--run",
            "--config", percorso, "--chiave", chiave,
            "--valori", ",".join(str(v) for v in valori),
            "--minuti", str(minuti), "--giri", str(giri),
            "--porta", str((cfg.get("web") or {}).get("port", 8080))]
    processo = subprocess.Popen(args, start_new_session=True,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
    # Lo stato si scrive **qui**, non solo nel figlio: fra lo spawn e la sua
    # prima scrittura passano dei secondi, e in quel buco l'interfaccia
    # direbbe che non sta succedendo niente.
    _scrivi_stato({"in_corso": True, "pid": processo.pid, "chiave": chiave,
                   "valori": valori, "minuti": minuti, "giri": giri,
                   "fatte": 0, "totale": len(valori) * int(giri),
                   "iniziata": time.time(), "aggiornato": time.time(),
                   "righe": [], "riepilogo": [], "consiglio": None})
    return valori


def ferma():
    """Chiede alla taratura di fermarsi alla prossima configurazione.

    Se non ne sta girando nessuna, ripulisce lo stato invece di lasciare in
    giro un file di stop che fermerebbe la prossima.
    """
    if not in_corso():
        dati = stato()
        if dati:
            _chiudi_orfana(dati)
        try:
            os.remove(STOP_PATH)
        except OSError:
            pass
        return False
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STOP_PATH, "w") as handle:
        handle.write("%d\n" % time.time())
    return True


# ------------------------------------------------------------------ profilo

def etichetta_profilo(chiave, valore, quando=None):
    quando = quando or datetime.datetime.now()
    nome = PARAMETRI.get(chiave, {}).get("label", chiave)
    return "Autotune %s — %s %s" % (quando.strftime("%d/%m"), nome, valore)


def profilo(chiave, valore, riga=None):
    """Il blocco che finisce in `panel["autotune"]` e compare nel menu.

    Contiene **solo il parametro tarato**: la taratura non ha misurato
    righe, colonne e tipo di chip, e un profilo che li riscrivesse
    spegnerebbe il pannello.
    """
    riga = riga or {}
    return {
        "label": etichetta_profilo(chiave, valore),
        "chiave": chiave,
        "quando": time.time(),
        "misura": {"regime": riga.get("regime"), "media": riga.get("media"),
                   "percento": riga.get("percento"), "n": riga.get("n")},
        "values": {chiave: valore},
    }


def _scrivi_profilo(percorso, blocco):
    dati = _leggi_config(percorso)
    dati.setdefault("panel", {})["autotune"] = blocco
    tmp = percorso + ".tmp"
    with open(tmp, "w") as handle:
        json.dump(dati, handle, indent=2)
    os.replace(tmp, percorso)


# ---------------------------------------------------------------------- CLI

def main(argv):
    if "--run" not in argv:
        print("uso: autotune.py --run --config F --chiave K --valori 4,5,6 "
              "[--minuti 2] [--giri 2] [--porta 8080]")
        return 2

    def opzione(nome, predefinito):
        return argv[argv.index(nome) + 1] if nome in argv else predefinito

    esegui(opzione("--config", "/etc/dmd/config.json"),
           opzione("--chiave", "slowdown"),
           [int(v) for v in opzione("--valori", "").split(",") if v.strip()],
           float(opzione("--minuti", "2")),
           int(opzione("--giri", "2")),
           int(opzione("--porta", "8080")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
