# -*- coding: utf-8 -*-
"""Che macchina e' questa.

Fino alla 16.5 la domanda non si poneva: il programma girava su un Raspberry
con un pannello LED attaccato ai GPIO, e tutto il resto del codice lo dava per
scontato in cento punti diversi -- l'installazione compilava i binding della
libreria matrice o si fermava, l'audio **scartava** di proposito le schede
HDMI e bcm2835 perche' sul Pi sono la scheda sbagliata, il servizio girava
come root perche' i GPIO lo vogliono.

Dalla 17.0 il programma gira anche su un PC con un monitor, e allora la
domanda va fatta una volta sola, in un posto solo, e risposta con quello che
la macchina dice di se':

    /proc/device-tree/model     "Raspberry Pi 4 Model B Rev 1.4"
    /proc/cpuinfo               la riga "Model" sui kernel che non hanno
                                il device tree montato

Non si guarda l'architettura (`uname -m`): un Pi 4 a 64 bit e un PC ARM
rispondono la stessa cosa, e la domanda vera non e' «che processore e'» ma
«c'e' un pannello LED che posso pilotare».

**Il pannello si offre solo su Pi 3 e 4.** Non e' una cautela generica: la
libreria matrice pilota il blocco PWM del BCM, e sulle altre macchine il
modulo `rgbmatrix` non c'e' nemmeno. Sul Pi 5 il controller GPIO e' un altro
(RP1) e la libreria di hzeller non lo supporta, quindi un Pi 5 qui vale come
un PC: monitor. Sullo Zero e sul Pi 2 il pannello funzionerebbe anche, ma
nessuno lo ha mai provato con questo programma e dichiararlo supportato
sarebbe una promessa che non possiamo tenere -- restano fra i Raspberry
riconosciuti, senza pannello.

Le risposte si calcolano una volta e si tengono: il file non cambia mentre il
programma gira, e tre decine di chiamanti non devono rileggere `/proc`.
"""

import os
import re

# I due posti dove una macchina dice come si chiama. Il device tree e' quello
# giusto -- lo riempie il firmware -- e cpuinfo e' la riserva per i kernel
# dove `/proc/device-tree` non e' montato.
MODELLO_DT = "/proc/device-tree/model"
MODELLO_CPUINFO = "/proc/cpuinfo"

# Le famiglie. Sono tre e non due perche' «Raspberry senza pannello» e «PC»
# vanno distinti: sul primo l'audio interno e' l'HDMI del Pi e il pulsante
# GPIO c'e', sul secondo no.
PI = "raspberry"
PC = "pc"
IGNOTA = "ignota"

# I modelli su cui il pannello LED si offre. Il numero e' quello che compare
# nel modello: "Raspberry Pi 4 Model B" -> "4".
PANNELLO_SU = ("3", "4")


def _prima_riga(percorso):
    try:
        with open(percorso, "rb") as f:
            # Il device tree e' terminato da uno zero, non da un fine riga.
            return f.read(256).split(b"\0")[0].decode("utf-8", "replace").strip()
    except OSError:
        return ""


def _modello_da_cpuinfo():
    try:
        with open(MODELLO_CPUINFO, encoding="utf-8", errors="replace") as f:
            for riga in f:
                if riga.lower().startswith("model") and ":" in riga:
                    valore = riga.split(":", 1)[1].strip()
                    # Su x86 la riga "model" e' un numero di famiglia del
                    # processore, non un nome di macchina: non serve.
                    if valore and not valore.isdigit():
                        return valore
    except OSError:
        pass
    return ""


def modello():
    """La riga che la macchina dice di se', o "" se non lo dice."""
    return _prima_riga(MODELLO_DT) or _modello_da_cpuinfo()


def _numero(testo):
    """Il numero di modello dentro la riga, quando c'e'.

    "Raspberry Pi 4 Model B" -> "4". Il Compute Module va riconosciuto a
    parte, perche' il numero arriva dopo due parole: un CM4 e' un Pi 4 con i
    GPIO su una scheda portante, e il pannello li' funziona.
    """
    cercato = re.search(r"compute\s*module\s*(\d+)", testo, re.I)
    if cercato:
        return cercato.group(1)
    cercato = re.search(r"raspberry\s*pi\s*(\d+)", testo, re.I)
    return cercato.group(1) if cercato else ""


def _leggi():
    testo = modello()
    if re.search(r"raspberry\s*pi", testo, re.I):
        numero = _numero(testo)
        return {"famiglia": PI,
                "modello": testo,
                "numero": numero,
                "pannello": numero in PANNELLO_SU}
    if testo:
        return {"famiglia": PC, "modello": testo, "numero": "",
                "pannello": False}
    # Nessuno dei due file dice niente: e' il caso di una macchina virtuale o
    # di un container. Non e' un Raspberry, quindi e' un PC -- la scelta
    # prudente qui e' quella che porta al monitor, non quella che prova a
    # pilotare dei GPIO che non ci sono.
    return {"famiglia": PC, "modello": "", "numero": "", "pannello": False}


_letto = None


def leggi(rileggi=False):
    """Il dizionario della macchina: famiglia, modello, numero, pannello."""
    global _letto
    if _letto is None or rileggi:
        _letto = _leggi()
    return dict(_letto)


def famiglia():
    return leggi()["famiglia"]


def e_raspberry():
    return famiglia() == PI


def pannello_possibile():
    """Si puo' offrire il pannello LED su questa macchina?

    Vero solo su Pi 3 e 4. Non dice che il pannello **c'e'**: dice che ha
    senso proporlo. Se poi la libreria manca o i cavi non ci sono, lo scopre
    `display.crea()`, e lo dice invece di morire.
    """
    return leggi()["pannello"]


def audio_interno_va_bene():
    """L'audio della macchina e' quello da usare?

    Sul Raspberry no, e per due motivi buoni: l'HDMI non ha un cavo attaccato
    (il pannello LED non e' un monitor) e `bcm2835` usa lo stesso blocco PWM
    della libreria matrice, quindi suonare da li' rovina il pannello. Per
    questo `suoni.py` le scarta e cerca una scheda USB.

    Su un PC quelle stesse schede sono **l'unica** cosa che c'e'. Lo scarto va
    quindi sotto questa condizione, non lasciato incondizionato.
    """
    return not e_raspberry()


def nome():
    """Come chiamare questa macchina in una pagina web."""
    dati = leggi()
    if dati["famiglia"] == PI:
        return dati["modello"] or "Raspberry Pi"
    return dati["modello"] or "PC"


def riepilogo():
    """Una riga per il giornale di bordo, all'avvio."""
    dati = leggi()
    return "%s (%s), pannello %s" % (
        nome(), dati["famiglia"],
        "possibile" if dati["pannello"] else "non disponibile")


def _forza(dati):
    """Solo per le prove: finge una macchina diversa."""
    global _letto
    _letto = dict(dati)


def _da_riga_di_comando(argomenti):
    """Le stesse risposte, per `install.sh`.

    L'installazione deve sapere se compilare i binding della libreria
    matrice, e la risposta e' la stessa che il programma dara' a ogni avvio.
    Scriverla due volte -- una in Python e una in bash, a colpi di grep su
    `/proc/cpuinfo` -- vorrebbe dire che un giorno le due si contraddicono.
    """
    if "--famiglia" in argomenti:
        print(famiglia())
    elif "--pannello" in argomenti:
        print("si" if pannello_possibile() else "no")
    elif "--nome" in argomenti:
        print(nome())
    else:
        print(riepilogo())
        print("modello:  %s" % (modello() or "(non dichiarato)"))
        print("famiglia: %s" % famiglia())
        print("pannello: %s" % ("si" if pannello_possibile() else "no"))
        print("audio interno: %s"
              % ("va bene" if audio_interno_va_bene() else "da scartare"))
    return 0


if __name__ == "__main__":          # pragma: no cover - attrezzo da scrivania
    import sys
    sys.exit(_da_riga_di_comando(sys.argv[1:]))
