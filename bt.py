# -*- coding: utf-8 -*-
"""Il Bluetooth visto e comandato dalla pagina web.

Perche' esiste
--------------
Per gli stessi motivi di `rete.py`, e la storia e' quasi identica. Fino alla
12.4 per collegare un pad al DMD bisognava aprire `bluetoothctl` e battere a
mano `scan on`, `pair`, `trust`, `connect` -- con un indirizzo di dodici cifre
esadecimali copiato da una riga che scorre. Per un oggetto che sta in
soggiorno serviva quindi un monitor, una tastiera e il manuale aperto:
esattamente la procedura che questo progetto continua a togliere di mezzo.

E c'e' un dettaglio che si dimentica sempre: **`trust`**. Senza, il pad si
collega adesso e non si riaggancia piu' dopo un riavvio, e nessuno capisce
perche'. Un pulsante che fa i tre passi nell'ordine giusto toglie il problema
invece di documentarlo.

Come parla con il sistema
-------------------------
Con `bluetoothctl`, e con nient'altro. E' lo stesso ragionamento di
NetworkManager per il wifi: BlueZ e' il proprietario del Bluetooth, e due
proprietari sono peggio di nessuno. Niente file scritti a mano, niente D-Bus
parlato da noi: i comandi non interattivi di `bluetoothctl` fanno tutto, e
quello che tornano si legge.

Il collegamento non si fa dentro la richiesta web
-------------------------------------------------
Accoppiare un pad prende dai cinque ai venti secondi, e una richiesta HTTP che
aspetta vuol dire una pagina bianca e un utente che ricarica a meta'. Quindi
il tentativo parte in un thread, la pagina risponde subito, e l'esito si
deposita qui: la pagina lo mostra al ricaricamento successivo, come fa gia'
per il wifi.

Cosa **non** fa
---------------
Non tocca l'audio. Un altoparlante Bluetooth e' un'altra cosa -- vuole
PulseAudio o PipeWire, un profilo A2DP e una scheda che non e' quella di
ALSA -- e mescolarlo qui vorrebbe dire due mestieri in un file solo. Qui si
accoppiano pad e telecomandi.
"""

import re
import shutil
import subprocess
import threading
import time

# `bluetoothctl` non ha fretta, ma neanche noi: una scansione dura quello che
# le si dice, e il resto sono comandi che tornano in un attimo.
TIMEOUT_COMANDO = 15
TIMEOUT_COLLEGAMENTO = 45
SCANSIONE = 8

# Quanto tenere l'esito dell'ultimo tentativo. Oltre, la pagina lo dimentica:
# un cartello di mezz'ora fa racconta una cosa che non riguarda piu' nessuno.
DURATA_ESITO = 300

_lucchetto = threading.Lock()
_esito = None            # (istante, riuscito, messaggio)
_in_corso = ""           # indirizzo del tentativo aperto, o ""

# Un indirizzo Bluetooth e nient'altro: quello che arriva dalla pagina finisce
# negli argomenti di un processo lanciato da root, e un campo libero li' in
# mezzo non ci va.
INDIRIZZO = re.compile(r"^([0-9A-F]{2}:){5}[0-9A-F]{2}$", re.I)


def disponibile():
    """Vero se su questa macchina si puo' comandare il Bluetooth."""
    return bool(shutil.which("bluetoothctl"))


def valido(indirizzo):
    return bool(INDIRIZZO.match((indirizzo or "").strip()))


def _esegui(argomenti, timeout=TIMEOUT_COMANDO):
    """Un comando di sistema: (codice, uscita, errore). Non solleva mai."""
    try:
        finito = subprocess.run(argomenti, capture_output=True, text=True,
                                timeout=timeout)
    except subprocess.TimeoutExpired:
        return 1, "", "tempo scaduto"
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, "", str(exc)
    return finito.returncode, finito.stdout or "", (finito.stderr or "").strip()


def _bctl(argomenti, timeout=TIMEOUT_COMANDO):
    if not disponibile():
        return 1, "", "bluetoothctl non installato"
    return _esegui(["bluetoothctl"] + list(argomenti), timeout)


# ------------------------------------------------------------------ lettura

def _righe_dispositivi(testo):
    """Da «Device AA:BB:.. Nome» a (indirizzo, nome)."""
    fuori = []
    for riga in (testo or "").splitlines():
        pezzi = riga.split()
        if len(pezzi) >= 2 and pezzi[0] == "Device" and valido(pezzi[1]):
            fuori.append((pezzi[1].upper(), " ".join(pezzi[2:]).strip()))
    return fuori


def _campi_info(testo):
    """Le proprieta' di `bluetoothctl info`, come dizionario."""
    dati = {}
    for riga in (testo or "").splitlines():
        if ":" not in riga:
            continue
        chiave, valore = riga.split(":", 1)
        dati[chiave.strip()] = valore.strip()
    return dati


def _batteria(campi):
    """La percentuale di carica, se il pad la dichiara.

    BlueZ la scrive come «Battery Percentage: 0x64 (100)»: si prende il numero
    fra parentesi, che e' quello in base dieci.
    """
    grezzo = campi.get("Battery Percentage", "")
    trovato = re.search(r"\((\d+)\)", grezzo)
    if trovato:
        return max(0, min(100, int(trovato.group(1))))
    return None


def info(indirizzo):
    """Tutto quello che BlueZ sa di un dispositivo."""
    dati = {"indirizzo": (indirizzo or "").upper(), "nome": "",
            "accoppiato": False, "fidato": False, "collegato": False,
            "batteria": None, "classe": ""}
    if not valido(indirizzo):
        return dati
    codice, uscita, _errore = _bctl(["info", indirizzo])
    if codice != 0:
        return dati
    campi = _campi_info(uscita)
    dati["nome"] = campi.get("Name") or campi.get("Alias") or ""
    dati["accoppiato"] = campi.get("Paired", "no") == "yes"
    dati["fidato"] = campi.get("Trusted", "no") == "yes"
    dati["collegato"] = campi.get("Connected", "no") == "yes"
    dati["batteria"] = _batteria(campi)
    dati["classe"] = campi.get("Icon", "")
    return dati


def elenco(dettagli=True, massimo=20):
    """I dispositivi che BlueZ conosce, i collegati per primi.

    `dettagli` chiede a `info` lo stato di ognuno: costa una chiamata a testa,
    quindi la pagina la fa e chi vuole solo i nomi no.
    """
    codice, uscita, _errore = _bctl(["devices"])
    if codice != 0:
        return []
    fuori = []
    for indirizzo, nome in _righe_dispositivi(uscita)[:massimo]:
        if dettagli:
            dati = info(indirizzo)
            dati["nome"] = dati["nome"] or nome
        else:
            dati = {"indirizzo": indirizzo, "nome": nome, "accoppiato": False,
                    "fidato": False, "collegato": False, "batteria": None,
                    "classe": ""}
        fuori.append(dati)
    fuori.sort(key=lambda d: (not d["collegato"], not d["accoppiato"],
                              d["nome"].lower()))
    return fuori


def cerca(secondi=SCANSIONE):
    """Accende la radio, guarda in giro per qualche secondo, e torna cosa vede.

    La scansione **non parte da sola**, come quella del wifi e per lo stesso
    motivo: muove traffico sulla stessa antenna del wifi -- su un Pi 3B+ e'
    davvero la stessa -- proprio mentre il pannello sta disegnando. Si fa
    quando la si chiede.
    """
    if not disponibile():
        return [], "bluetoothctl non installato"
    _bctl(["power", "on"])
    secondi = max(3, min(30, int(secondi)))
    codice, _uscita, errore = _bctl(["--timeout", str(secondi), "scan", "on"],
                                    timeout=secondi + 10)
    trovati = elenco()
    if codice != 0 and not trovati:
        return [], errore or "scansione non riuscita"
    return trovati, ""


def stato():
    """Fotografia per l'intestazione della pagina."""
    dati = {"disponibile": disponibile(), "acceso": False, "errore": "",
            "collegati": [], "in_corso": in_corso()}
    if not dati["disponibile"]:
        dati["errore"] = "bluetoothctl non installato"
        return dati
    codice, uscita, errore = _bctl(["show"])
    if codice != 0:
        dati["errore"] = errore or "adattatore non trovato"
        return dati
    campi = _campi_info(uscita)
    dati["acceso"] = campi.get("Powered", "no") == "yes"
    dati["collegati"] = [d for d in elenco() if d["collegato"]]
    return dati


# ---------------------------------------------------------------- scrittura

def accendi(acceso=True):
    codice, _u, errore = _bctl(["power", "on" if acceso else "off"])
    return codice == 0, errore


def collega(indirizzo):
    """Accoppia, fidati, collega. I tre passi nell'ordine giusto.

    Torna (fatto, messaggio). **`trust` non e' un extra**: senza, il pad si
    riaggancia finche' non riavvii il Pi, e dopo un riavvio bisogna rifare
    tutto. E' la riga che tutti dimenticano, e questo pulsante esiste anche
    per non fargliela piu' dimenticare.

    Un pad gia' accoppiato non si riaccoppia: `pair` risponderebbe
    «AlreadyExists», che non e' un errore ma lo sembra. Si guarda prima.
    """
    if not valido(indirizzo):
        return False, "indirizzo non valido"
    if not disponibile():
        return False, "bluetoothctl non installato"
    indirizzo = indirizzo.upper()
    _bctl(["power", "on"])
    passi = []
    if not info(indirizzo)["accoppiato"]:
        codice, uscita, errore = _bctl(["pair", indirizzo],
                                       timeout=TIMEOUT_COLLEGAMENTO)
        if codice != 0 and "AlreadyExists" not in (uscita + errore):
            return False, _motivo(uscita, errore) or "accoppiamento fallito"
        passi.append("accoppiato")
    codice, uscita, errore = _bctl(["trust", indirizzo])
    if codice == 0:
        passi.append("fidato")
    codice, uscita, errore = _bctl(["connect", indirizzo],
                                   timeout=TIMEOUT_COLLEGAMENTO)
    if codice != 0:
        return False, _motivo(uscita, errore) or "collegamento fallito"
    passi.append("collegato")
    return True, "; ".join(passi)


def scollega(indirizzo):
    if not valido(indirizzo):
        return False, "indirizzo non valido"
    codice, uscita, errore = _bctl(["disconnect", indirizzo])
    return codice == 0, _motivo(uscita, errore)


def dimentica(indirizzo):
    """Toglie del tutto il dispositivo: si ricomincia dall'accoppiamento."""
    if not valido(indirizzo):
        return False, "indirizzo non valido"
    codice, uscita, errore = _bctl(["remove", indirizzo])
    return codice == 0, _motivo(uscita, errore)


def _motivo(uscita, errore):
    """La riga che spiega cosa e' andato storto, se ce n'e' una.

    `bluetoothctl` scrive i suoi guai sull'uscita normale e non sull'errore,
    con una riga che comincia per «Failed to». Presa cosi' com'e' e' molto
    piu' utile di un codice di uscita.
    """
    for riga in (uscita or "").splitlines():
        spoglia = riga.strip()
        if spoglia.startswith("Failed") or "not available" in spoglia:
            return spoglia
    return (errore or "").strip()


# --------------------------------------------- il tentativo, in un thread

def in_corso():
    with _lucchetto:
        return _in_corso


def ultimo_esito():
    """L'esito dell'ultimo tentativo, se e' ancora fresco."""
    with _lucchetto:
        if _esito is None:
            return None
        quando, riuscito, messaggio = _esito
        if time.time() - quando > DURATA_ESITO:
            return None
        return {"riuscito": riuscito, "messaggio": messaggio,
                "quando": quando}


def dimentica_esito():
    global _esito
    with _lucchetto:
        _esito = None


def avvia_collegamento(indirizzo):
    """Fa partire il collegamento in un thread. Torna (partito, motivo)."""
    global _in_corso
    if not valido(indirizzo):
        return False, "indirizzo non valido"
    with _lucchetto:
        if _in_corso:
            return False, "c'e' gia' un collegamento in corso"
        _in_corso = indirizzo.upper()
    threading.Thread(target=_lavora, args=(indirizzo.upper(),),
                     name="bluetooth", daemon=True).start()
    return True, ""


def _lavora(indirizzo):
    global _esito, _in_corso
    try:
        fatto, messaggio = collega(indirizzo)
    except Exception as exc:                        # pragma: no cover
        fatto, messaggio = False, str(exc)
    with _lucchetto:
        _esito = (time.time(), fatto, messaggio)
        _in_corso = ""
    print("[bt] %s: %s (%s)" % (indirizzo, "collegato" if fatto else "non collegato",
                                messaggio))
