# -*- coding: utf-8 -*-
"""I motori del pad: far sentire un colpo invece di farlo solo vedere.

Perche' esiste
--------------
Un pannello da 256x64 e' piccolo. Quando la palla prende la racchetta ci sono
due pixel che cambiano, e in mezzo a un campo pieno di mattoncini non si
vedono: il colpo si capisce **dopo**, da come riparte la palla. Un DualShock
ha due motori dentro, e un tonfo di centoventi millesimi lo dice prima che
l'occhio se ne accorga.

Come si comanda un motore, sotto Linux
--------------------------------------
Non esiste un file da scrivere. Il pad e' lo stesso dispositivo di
`/dev/input` da cui si leggono i tasti — vedi `sources/comandi.py` — e i
motori si comandano in due tempi:

1. si **carica un effetto** nel pad, con una ioctl (`EVIOCSFF`) che prende una
   `struct ff_effect`. Il kernel risponde assegnandogli un numero;
2. si **suona** quell'effetto scrivendo un evento normale sul dispositivo,
   con tipo `EV_FF` e codice uguale a quel numero.

Il pad tiene in memoria un pugno di effetti, non infiniti: si caricano una
volta e si risuonano, invece di caricarne uno nuovo a ogni colpo e riempire
gli slot in mezzo minuto di partita.

La parte noiosa e' la `struct ff_effect`, che contiene una union con dentro un
puntatore: la sua dimensione cambia fra 32 e 64 bit, e **il numero della ioctl
dipende da quella dimensione**. Su un Raspberry capitano tutte e due le cose
-- Raspberry Pi OS a 32 bit su un Pi a 64 -- quindi la misura si calcola
invece di scriverla a mano. Le due misure giuste sono 44 e 48 byte, e le due
ioctl 0x402c4580 e 0x40304580: sono nelle prove, perche' un numero sbagliato
li' dentro non da' un errore, da' un pad che non vibra.

Cosa non fa
-----------
Non apre niente da solo e non cerca pad in giro: chi apre una partita gli
dice su quali dispositivi lavorare, come si fa con la scheda audio. Un pad
senza motori -- e ce ne sono -- non e' un errore: non si trova nell'elenco e
la partita va avanti muta di vibrazioni, esattamente come va avanti muta
quando la scheda audio e' occupata.
"""

import fcntl
import os
import struct
import threading

# Dal kernel: include/uapi/linux/input.h e input-event-codes.h
EV_FF = 0x15
FF_RUMBLE = 0x50

# struct input_event, la stessa che `sources/comandi.py` legge.
FORMATO_EVENTO = "@llHHi"

# La union dentro `struct ff_effect`, nella sua forma piu' grande
# (`ff_periodic_effect`): due contatori, la busta, la lunghezza e un
# puntatore. Serve solo la **misura**, non i campi.
_UNIONE = "@HHhhH" "HHHH" "I" "P"


def _dimensione_effetto():
    """sizeof(struct ff_effect) su questa macchina: 44 a 32 bit, 48 a 64."""
    unione = struct.calcsize(_UNIONE)
    allineamento = struct.calcsize("@P")
    testa = struct.calcsize("@HhHHHHH")          # 14 byte, sempre
    riempimento = (-testa) % allineamento
    return testa + riempimento + unione


DIM_EFFETTO = _dimensione_effetto()

# _IOW('E', 0x80, struct ff_effect) e _IOW('E', 0x81, int).
EVIOCSFF = (1 << 30) | (DIM_EFFETTO << 16) | (ord("E") << 8) | 0x80
EVIOCRMFF = (1 << 30) | (4 << 16) | (ord("E") << 8) | 0x81

# Quanti effetti diversi tenere caricati nel pad. Un DualShock 4 ne regge
# sedici; quattro bastano per i colpi che usiamo e lasciano spazio a chi
# arrivera' dopo.
SLOT = 4

PROC = "/proc/bus/input/devices"


# --------------------------------------------------------- quali pad vibrano

def _blocchi(testo):
    """I blocchi di /proc/bus/input/devices, uno per dispositivo."""
    return [b for b in (testo or "").split("\n\n") if b.strip()]


def _bit_acceso(riga, bit, bit_totali=128):
    """Vero se nella maschera scritta in `riga` quel bit e' acceso.

    Le maschere del kernel si leggono **da destra**: l'ultima parola porta i
    bit da 0 in su, quella prima i successivi. Ogni parola vale 32 o 64 bit
    secondo la macchina che ha scritto il file, e su un Raspberry capitano
    tutte e due -- Raspberry Pi OS a 32 bit su un processore a 64.

    La larghezza **non** si indovina dalla lunghezza della scrittura: il
    kernel stampa le parole senza zeri davanti, e una riga che finisce con
    «0 0» non dice niente su quanto e' larga. Si ricava dal conto: il campo
    dei motori e' lungo 128 bit sempre, quindi due parole vogliono dire 64
    bit l'una e quattro ne vogliono dire 32.
    """
    parole = (riga or "").split()
    if not parole:
        return False
    larghezza = max(1, bit_totali // len(parole))
    intero = 0
    for indice, parola in enumerate(reversed(parole)):
        try:
            intero |= int(parola, 16) << (indice * larghezza)
        except ValueError:
            return False
    return bool(intero >> bit & 1)


def motori(testo=None, con_nome=False):
    """I dispositivi che hanno un motore da far girare.

    Si legge lo stesso file da cui `sources/comandi.py` ricava i pad, e per lo
    stesso motivo: aprire mezzo `/dev/input` per chiedere a ognuno se vibra
    vuol dire tenere descrittori su hardware che non c'entra.
    """
    if testo is None:
        try:
            with open(PROC) as handle:
                testo = handle.read()
        except OSError:
            return []
    trovati = []
    for blocco in _blocchi(testo):
        righe = blocco.splitlines()
        ff = next((r.split("=", 1)[1] for r in righe if r.startswith("B: FF=")), "")
        if not _bit_acceso(ff, FF_RUMBLE):
            continue
        nome = next((r.split('"')[1] for r in righe if r.startswith('N: Name="')), "")
        handlers = next((r.split("=", 1)[1] for r in righe
                         if r.startswith("H: Handlers=")), "")
        for campo in handlers.split():
            if campo.startswith("event"):
                trovati.append(("/dev/input/" + campo, nome))
                break
    return trovati if con_nome else [p for p, _ in trovati]


# ------------------------------------------------------------------ un motore

def effetto(forte, debole, durata_ms, numero=-1):
    """I byte di una `struct ff_effect` di tipo rumble.

    `forte` e `debole` sono i due motori, da 0 a 65535: quello grande fa il
    tonfo, quello piccolo il tremolio. Sono due perche' sui pad veri sono due,
    e mescolarli in un numero solo vorrebbe dire scegliere per chi usa questo
    modulo.
    """
    testa = struct.pack("@HhHHHHH", FF_RUMBLE, numero, 0, 0, 0,
                        max(0, min(0xFFFF, int(durata_ms))), 0)
    # Il riempimento fra la testa e la union: lo vuole il compilatore C, non
    # noi, ed e' la ragione per cui questa struttura non si scrive a mano.
    riempimento = b"\0" * ((-len(testa)) % struct.calcsize("@P"))
    corpo = struct.pack("@HH", max(0, min(0xFFFF, int(forte))),
                        max(0, min(0xFFFF, int(debole))))
    coda = b"\0" * (DIM_EFFETTO - len(testa) - len(riempimento) - len(corpo))
    return testa + riempimento + corpo + coda


class Motore:
    """Un pad aperto, con i suoi effetti gia' caricati dentro."""

    def __init__(self, percorso):
        self.percorso = percorso
        self.errore = ""
        self._fd = None
        self._slot = {}          # (forte, debole, durata) -> numero
        self._ordine = []
        self._lucchetto = threading.Lock()

    def apri(self):
        if self._fd is not None:
            return True
        try:
            # In lettura **e** scrittura: la ioctl che carica l'effetto vuole
            # poter scrivere, e leggere i tasti lo fa gia' qualcun altro.
            self._fd = os.open(self.percorso, os.O_RDWR)
            self.errore = ""
            return True
        except OSError as exc:
            self._fd = None
            self.errore = str(exc)
            return False

    def chiudi(self):
        with self._lucchetto:
            if self._fd is not None:
                try:
                    os.close(self._fd)
                except OSError:
                    pass
            self._fd = None
            self._slot.clear()
            self._ordine = []

    def _numero(self, chiave):
        """Il numero dell'effetto, caricandolo nel pad se non c'e' gia'."""
        numero = self._slot.get(chiave)
        if numero is not None:
            return numero
        forte, debole, durata = chiave
        dati = bytearray(effetto(forte, debole, durata))
        try:
            fcntl.ioctl(self._fd, EVIOCSFF, dati)
        except OSError as exc:
            self.errore = str(exc)
            return None
        numero = struct.unpack_from("@Hh", bytes(dati))[1]
        # Gli slot del pad sono pochi: quando sono pieni si butta il piu'
        # vecchio invece di smettere di vibrare a meta' partita.
        if len(self._ordine) >= SLOT:
            vecchia = self._ordine.pop(0)
            try:
                fcntl.ioctl(self._fd, EVIOCRMFF, self._slot.pop(vecchia))
            except (OSError, KeyError):
                pass
        self._slot[chiave] = numero
        self._ordine.append(chiave)
        return numero

    def colpo(self, forte, debole, durata_ms):
        """Fa girare i motori. Torna vero se il pad ha accettato."""
        with self._lucchetto:
            if self._fd is None and not self.apri():
                return False
            numero = self._numero((int(forte), int(debole), int(durata_ms)))
            if numero is None:
                return False
            evento = struct.pack(FORMATO_EVENTO, 0, 0, EV_FF, numero, 1)
            try:
                os.write(self._fd, evento)
                return True
            except OSError as exc:
                self.errore = str(exc)
                # Il pad staccato a meta' partita: si chiude e si riapre alla
                # prossima, invece di tenere un descrittore morto.
                self.chiudi_non_bloccante()
                return False

    def chiudi_non_bloccante(self):
        """Come `chiudi`, ma da dentro il lucchetto gia' preso."""
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
        self._fd = None
        self._slot.clear()
        self._ordine = []


# ------------------------------------------------------- quello che usa il DMD

_aperti = []
_lucchetto = threading.Lock()


def apri(percorsi=None):
    """Prende in mano i pad che vibrano. Torna quanti ne ha trovati."""
    chiudi()
    trovati = [p for p in (percorsi if percorsi is not None else motori()) if p]
    with _lucchetto:
        _aperti.extend(Motore(p) for p in trovati)
    return len(trovati)


def chiudi():
    with _lucchetto:
        aperti, _aperti[:] = list(_aperti), []
    for motore in aperti:
        motore.chiudi()


def aperti():
    with _lucchetto:
        return list(_aperti)


def colpo(forza=1.0, durata=0.12, tremolio=0.0):
    """Un colpo su tutti i pad aperti.

    `forza` e `tremolio` vanno da 0 a 1 e sono i due motori; `durata` e' in
    secondi. Si torna quanti pad hanno vibrato: zero non e' un errore, vuol
    dire che nessuno dei pad collegati ha i motori.
    """
    forza = max(0.0, min(1.0, float(forza)))
    tremolio = max(0.0, min(1.0, float(tremolio)))
    durata_ms = max(1, min(5000, int(float(durata) * 1000)))
    fatti = 0
    for motore in aperti():
        if motore.colpo(forza * 0xFFFF, tremolio * 0xFFFF, durata_ms):
            fatti += 1
    return fatti
