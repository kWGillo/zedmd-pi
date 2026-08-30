"""Preparazione di Doom, dalla web UI invece che da SSH.

Doom ha bisogno di due cose che non arrivano con il pacchetto: il programma,
che va compilato da sorgenti scaricati al momento (sono GPL2, e questo
progetto e' GPLv3 — vedi `doom/setup_doom.sh`), e un WAD, che e' il file con
i livelli, la grafica e i suoni.

Il perche' di questo modulo e' semplice: senza, per accendere una funzione
bisognava aprire una sessione SSH, mentre in questo progetto tutto il resto —
aggiornamenti compresi — si fa dalla pagina web. Qui si lancia lo stesso
script in sottofondo e se ne mostra il log, esattamente come fa l'OTA.

Sui WAD c'e' una cosa da sapere. Il pacchetto scarica **Freedoom**, che e'
libero e si puo' ridistribuire. I WAD di id Software no: chi ha comprato Doom
copia il suo — `doom1.wad` (lo shareware), `doom.wad` (Ultimate Doom),
`doom2.wad`, `plutonia.wad`, `tnt.wad` — nella cartella e lo sceglie dalla
pagina. Qui si guarda cosa c'e' davvero, e si guarda **dentro** il file: un
nome giusto non garantisce niente, mentre i primi quattro byte di un WAD sono
`IWAD` o `PWAD`, e un file troncato o rinominato per sbaglio si riconosce
subito invece di far fallire Doom con un messaggio incomprensibile.
"""

import os
import subprocess
import threading
import time

LOG_PATH = "/var/lib/dmd/doom-setup.log"

# Nome della condivisione SMB creata da setup_doom.sh. I WAD sono l'unica cosa
# di Doom che si mette e si toglie a mano, e chiedere una sessione SSH per
# copiare un file non e' un modo di lavorare: stanno in una cartella
# condivisa in rete, come la libreria dei media.
CONDIVISIONE = "dmd-doom"

# La cartella che la condivisione espone. E' anche il posto dove si cercano i
# WAD *oltre* a quello scritto in configurazione: dopo un aggiornamento che
# sposta i file, il percorso configurato punta ancora alla vecchia posizione,
# e cercare solo li' vorrebbe dire non trovare niente proprio quando serve.
CARTELLA_CONDIVISA = "/srv/dmd/doom"

# I WAD che sappiamo riconoscere, dal piu' completo al piu' piccolo. L'ordine
# conta: e' quello con cui si propone il predefinito a chi non ha ancora
# scelto. Il gioco vero, se c'e', viene prima di Freedoom.
WAD_NOTI = (
    ("doom.wad", "Ultimate Doom", False),
    ("doom2.wad", "Doom II", False),
    ("plutonia.wad", "Final Doom: Plutonia", False),
    ("tnt.wad", "Final Doom: TNT", False),
    ("doom1.wad", "Doom shareware", False),
    ("freedoom1.wad", "Freedoom: Phase 1", True),
    ("freedoom2.wad", "Freedoom: Phase 2", True),
)

_proc = None
_lock = threading.Lock()


# ------------------------------------------------------------------------ wad

def _intestazione(percorso):
    """I primi quattro byte del file: `IWAD`, `PWAD`, o qualcos'altro."""
    try:
        with open(percorso, "rb") as handle:
            return handle.read(4).decode("ascii", "replace")
    except OSError:
        return ""


def descrivi_wad(percorso):
    """Che cos'e' questo file, per davvero.

    Non basta che esista e non basta che si chiami bene: un WAD scaricato a
    meta' o un file di testo rinominato passerebbero il controllo del nome e
    poi Doom si fermerebbe con un errore che non spiega niente.
    """
    nome = os.path.basename(percorso).lower()
    noto = next((v for v in WAD_NOTI if v[0] == nome), None)
    info = {"path": percorso, "name": os.path.basename(percorso),
            "label": noto[1] if noto else "", "free": bool(noto and noto[2]),
            "known": noto is not None, "exists": os.path.isfile(percorso),
            "size": 0, "kind": "", "ok": False, "problem": ""}
    if not info["exists"]:
        info["problem"] = "assente"
        return info
    try:
        info["size"] = os.path.getsize(percorso)
    except OSError:
        info["size"] = 0
    info["kind"] = _intestazione(percorso)
    if info["kind"] not in ("IWAD", "PWAD"):
        info["problem"] = "non e' un WAD"
        return info
    if info["kind"] == "PWAD":
        # Un PWAD e' una modifica, non un gioco completo: da solo Doom non
        # parte, e dirlo adesso costa meno che scoprirlo dal log.
        info["problem"] = "e' un'estensione, non un gioco completo"
        return info
    # Un IWAD vero sta sopra i quattro megabyte anche nella versione shareware.
    if info["size"] < 2 * 1024 * 1024:
        info["problem"] = "troppo piccolo, forse scaricato a meta'"
        return info
    info["ok"] = True
    return info


def cartella_wad(cfg):
    """Dove si copiano i WAD: la cartella condivisa in rete."""
    return CARTELLA_CONDIVISA


def cartelle(cfg):
    """Tutte le cartelle in cui cercare, senza ripetizioni.

    Prima quella condivisa, che e' il posto giusto; poi quella del WAD
    configurato, se e' un'altra — chi ha scelto un percorso suo deve
    continuare a vederlo elencato.
    """
    elenco = [CARTELLA_CONDIVISA]
    configurata = os.path.dirname(cfg["doom"].get("wad") or "")
    if configurata and configurata not in elenco:
        elenco.append(configurata)
    return [c for c in elenco if os.path.isdir(c)]


def wad_disponibili(cfg):
    """I WAD trovati, in ordine di preferenza.

    Si guardano prima i nomi noti, poi tutto il resto: chi ha rinominato il
    proprio WAD deve poterlo comunque scegliere.
    """
    trovati = []
    visti = set()
    elenco = cartelle(cfg)
    # Il nome nel giro esterno e la cartella in quello interno: cosi' l'ordine
    # e' quello della preferenza — il gioco vero prima di Freedoom — e non
    # quello delle cartelle. Un doom2.wad in una cartella tua deve venire
    # prima di un freedoom1.wad in quella condivisa, non dopo.
    for nome, _, _ in WAD_NOTI:
        for cartella in elenco:
            percorso = os.path.join(cartella, nome)
            if os.path.isfile(percorso) and percorso not in visti:
                trovati.append(descrivi_wad(percorso))
                visti.add(percorso)
    for cartella in cartelle(cfg):
        try:
            nomi = sorted(os.listdir(cartella))
        except OSError:
            continue
        for nome in nomi:
            percorso = os.path.join(cartella, nome)
            if not nome.lower().endswith(".wad") or percorso in visti:
                continue
            trovati.append(descrivi_wad(percorso))
            visti.add(percorso)
    return trovati


def wad_consigliato(cfg):
    """Il WAD da usare se quello configurato non c'e' o non va."""
    for info in wad_disponibili(cfg):
        if info["ok"]:
            return info["path"]
    return ""


# ------------------------------------------------------------------ programma

def script(cfg=None):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "doom", "setup_doom.sh")


def binario_pronto(cfg):
    percorso = cfg["doom"].get("binary") or ""
    return bool(percorso and os.path.isfile(percorso)
                and os.access(percorso, os.X_OK))


def binario_vecchio(cfg):
    """True se il sorgente C e' piu' recente del binario compilato.

    Capita dopo un aggiornamento che tocca `doomgeneric_dmd.c`: il programma
    continua a funzionare, ma non e' quello che dice il sorgente installato, e
    chi cerca una modifica che non vede impazzisce.
    """
    binario = cfg["doom"].get("binary") or ""
    sorgente = os.path.join(os.path.dirname(script()), "doomgeneric_dmd.c")
    try:
        return os.path.getmtime(sorgente) > os.path.getmtime(binario)
    except OSError:
        return False


def log(messaggio):
    riga = "%s  %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), messaggio)
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a") as handle:
            handle.write(riga + "\n")
    except OSError:
        pass


def tail_log(lines=40):
    try:
        with open(LOG_PATH) as handle:
            return "".join(handle.readlines()[-lines:])
    except OSError:
        return ""


def in_corso():
    with _lock:
        return _proc is not None and _proc.poll() is None


def avvia(cfg):
    """Lancia la preparazione in sottofondo. Restituisce un errore o ''.

    Non si aspetta: compilare Doom su un Pi 3B+ prende un paio di minuti, e
    una richiesta web che resta aperta due minuti e' una richiesta che scade.
    La pagina guarda il log.
    """
    global _proc
    with _lock:
        if _proc is not None and _proc.poll() is None:
            return "gia' in corso"
        percorso = script()
        if not os.path.isfile(percorso):
            return "script non trovato: %s" % percorso

        stato = os.path.dirname(cfg["doom"].get("binary") or "") \
            or "/var/lib/dmd/doom"
        ambiente = dict(os.environ, STATO=stato)
        log("preparazione avviata (destinazione %s)" % stato)
        try:
            handle = open(LOG_PATH, "a")
        except OSError as exc:
            return str(exc)
        try:
            _proc = subprocess.Popen(
                ["bash", percorso], env=ambiente,
                stdout=handle, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, start_new_session=True)
        except OSError as exc:
            handle.close()
            return str(exc)
        atteso = _proc

    # La preparazione puo' spostare i WAD — chi arriva dalla 3.0.1 li ha
    # insieme al binario — e a quel punto il percorso in configurazione punta
    # a un file che non c'e' piu'. Si riallinea qui, nel processo che possiede
    # davvero la configurazione: farlo dallo script vorrebbe dire scrivere il
    # file JSON sotto il naso del servizio, che lo tiene in memoria e lo
    # risalverebbe com'era al primo salvataggio successivo.
    threading.Thread(target=_al_termine, args=(atteso, cfg),
                     name="doom-setup", daemon=True).start()
    return ""


def _al_termine(proc, cfg):
    proc.wait()
    if proc.returncode != 0:
        log("preparazione fallita (codice %s)" % proc.returncode)
        return
    if riallinea(cfg):
        log("WAD in configurazione aggiornato: %s" % cfg["doom"]["wad"])
    log("preparazione conclusa")


def riallinea(cfg):
    """Fa puntare la configurazione a un WAD che esiste davvero.

    Restituisce True se ha cambiato qualcosa. Non si tocca niente se il WAD
    configurato e' a posto: la scelta dell'utente vale piu' della nostra.
    """
    corrente = cfg["doom"].get("wad") or ""
    if corrente and descrivi_wad(corrente)["ok"]:
        return False        # quello scelto va bene: la scelta dell'utente vale
    scelto = wad_consigliato(cfg)
    if not scelto or scelto == corrente:
        return False
    cfg["doom"]["wad"] = scelto
    try:
        import dmdconf
        dmdconf.save()
    except Exception as exc:      # pragma: no cover
        log("configurazione non salvata: %s" % exc)
    return True


def stato(cfg):
    """Quello che serve alla pagina per raccontare a che punto siamo."""
    with _lock:
        corso = _proc is not None and _proc.poll() is None
        esito = None if _proc is None or corso else _proc.returncode
    wad = wad_disponibili(cfg)
    return {
        "running": corso,
        "returncode": esito,
        "binary": cfg["doom"].get("binary", ""),
        "binary_ready": binario_pronto(cfg),
        "binary_stale": binario_vecchio(cfg),
        "wad_dir": cartella_wad(cfg),
        "share": CONDIVISIONE,
        "wads": wad,
        "wad_current": cfg["doom"].get("wad", ""),
        "wad_ok": any(w["ok"] and w["path"] == cfg["doom"].get("wad")
                      for w in wad),
        "suggested": wad_consigliato(cfg),
        "log": tail_log(),
    }
