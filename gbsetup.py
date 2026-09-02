# -*- coding: utf-8 -*-
"""Preparazione del Game Boy: installa PyBoy e apre la condivisione ROM.

Perche' un pulsante e non una riga di istruzioni. L'aggiornamento del DMD
passa dalla rete e non tocca il sistema: PyBoy non arriva con l'aggiornamento
e la condivisione delle ROM non si crea da sola. Senza questo pulsante, per
accendere una funzione bisognerebbe aprire una sessione SSH — e chi ha
aggiornato dal telefono non ce l'ha.

La preparazione gira **in sottofondo**: `pip install` su un Pi puo' prendere
un minuto abbondante, e una richiesta web che resta aperta un minuto e' una
richiesta che scade. La pagina guarda il log, come per Doom.
"""

import os
import subprocess
import threading
import time

LOG_PATH = "/var/lib/dmd/gb-setup.log"

_lock = threading.Lock()
_proc = None


def script(cfg=None):
    """Lo script di preparazione, accanto al programma che ospita PyBoy."""
    host = (cfg or {}).get("gameboy", {}).get("host") or "/opt/dmd/gb/gb_dmd.py"
    return os.path.join(os.path.dirname(host) or "/opt/dmd/gb", "setup_gb.sh")


def pyboy_pronto():
    try:
        import pyboy  # noqa: F401
    except Exception:
        return False
    return True


def versione_pyboy():
    try:
        import pyboy
        return getattr(pyboy, "__version__", "") or "installato"
    except Exception:
        return ""


SMB_CONF = "/etc/samba/smb.conf"
NOME_CONDIVISIONE = "dmd-rom"


def condivisione_attiva(nome=NOME_CONDIVISIONE):
    """Se la condivisione SMB esiste davvero.

    Guardare solo la cartella non basta: la cartella la crea anche un
    `mkdir`, ma dal Mac non si vede niente se in smb.conf non c'e' la
    sezione. Era la differenza fra "l'ho preparato" e "non trovo la
    condivisione", e la pagina deve saperla distinguere.
    """
    try:
        with open(SMB_CONF) as handle:
            for riga in handle:
                if riga.strip().lower() == ("[%s]" % nome).lower():
                    return True
    except OSError:
        return False
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
    """Lancia la preparazione in sottofondo. Restituisce un errore o ''."""
    global _proc
    with _lock:
        if _proc is not None and _proc.poll() is None:
            return "gia' in corso"
        percorso = script(cfg)
        if not os.path.isfile(percorso):
            return "script non trovato: %s" % percorso
        cartella = cfg.get("gameboy", {}).get("rom_dir") or "/srv/dmd/rom"
        nome = cfg.get("gameboy", {}).get("share") or NOME_CONDIVISIONE
        ambiente = dict(os.environ, ROM_DIR=cartella, SHARE_NAME=nome)
        log("preparazione avviata (ROM in %s)" % cartella)
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
    return ""


def stato(cfg):
    """Quel che serve alla pagina per decidere cosa mostrare."""
    cartella = cfg.get("gameboy", {}).get("rom_dir") or "/srv/dmd/rom"
    nome = cfg.get("gameboy", {}).get("share") or NOME_CONDIVISIONE
    return {
        "pyboy": pyboy_pronto(),
        "versione": versione_pyboy(),
        "host": os.path.isfile(cfg.get("gameboy", {}).get("host") or ""),
        "cartella": cartella,
        "cartella_c_e": os.path.isdir(cartella),
        "condivisione": nome,
        "condivisa": condivisione_attiva(nome),
        "in_corso": in_corso(),
        "log": tail_log(),
        "script": os.path.isfile(script(cfg)),
    }
