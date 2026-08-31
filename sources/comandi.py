# -*- coding: utf-8 -*-
"""Tastiere e pad: un lettore solo, per Doom e per i giochi.

Sotto Linux una tastiera da cabinato e un pad PS4 sono la stessa cosa — un
dispositivo di /dev/input che manda `struct input_event` da ventiquattro byte
— e questo modulo e' l'unico posto del progetto che lo sa.

Il lavoro non e' leggere: e' tradurre. I **pulsanti** sono premuti o
rilasciati e basta. Gli **assi** no: una levetta ha un valore dentro un
intervallo che cambia da pad a pad (0..255 su un DualShock 4, -32768..32767 su
molti pad da PC), e l'intervallo si chiede al kernel invece di darlo per
scontato. La conversione in premuto/rilasciato ha due soglie diverse, perche'
con una sola una levetta tenuta appena oltre il limite genera una raffica di
premuto/rilasciato — che in un gioco si vede come un personaggio che scatta
invece di camminare.

`Lettore` non sa niente di chi lo usa: riceve le tabelle (quale codice e'
quale azione) e una funzione da chiamare. Doom ci mappa dodici azioni, un
gioco ne mappa quattro, e il ciclo dei dispositivi resta scritto una volta.
"""

import os
import select
import struct
import threading

EV_KEY = 0x01
EV_ABS = 0x03

# struct input_event: due campi di timeval, poi tipo, codice e valore. Le
# dimensioni cambiano fra 32 e 64 bit, e su un Pi capitano entrambe: si
# lasciano calcolare a struct invece di scriverle a mano.
FORMATO_EVENTO = "@llHHi"
DIM_EVENTO = struct.calcsize(FORMATO_EVENTO)

# ------------------------------------------------------------------ pulsanti

BTN_SOUTH = 0x130   # croce su PS4, A su un pad XInput
BTN_EAST = 0x131    # cerchio, B
BTN_NORTH = 0x133   # triangolo, Y
BTN_WEST = 0x134    # quadrato, X
BTN_TL = 0x136      # L1
BTN_TR = 0x137      # R1
BTN_TL2 = 0x138     # L2 digitale
BTN_TR2 = 0x139     # R2 digitale
BTN_SELECT = 0x13a  # Share
BTN_START = 0x13b   # Options
BTN_MODE = 0x13c    # tasto PS
BTN_THUMBL = 0x13d
BTN_THUMBR = 0x13e

# Il pulsante che puo' *far cominciare* una partita: Options o il tasto PS,
# che nessuno preme per sbaglio sfiorando un pad appoggiato al cabinato.
PAD_AVVIO = (BTN_START, BTN_MODE)

ABS_X = 0x00
ABS_Y = 0x01
ABS_RX = 0x03
ABS_RY = 0x04
ABS_HAT0X = 0x10
ABS_HAT0Y = 0x11

# Zona morta come frazione della corsa, e isteresi: si preme al 40% e si
# rilascia al 28%.
ZONA_MORTA = 0.40
ZONA_RILASCIO = 0.28

# EVIOCGABS(asse): chiede al kernel l'intervallo vero di un asse.
_ABS_FORMATO = "@6i"          # value, minimum, maximum, fuzz, flat, resolution
_EVIOCGABS_BASE = 0x40


def _eviocgabs(asse):
    dim = struct.calcsize(_ABS_FORMATO)
    return (2 << 30) | (dim << 16) | (ord("E") << 8) | (_EVIOCGABS_BASE + asse)


def intervallo_asse(fd, asse):
    """(minimo, massimo) di un asse, chiesti al kernel. None se non si sa."""
    try:
        import fcntl
        grezzo = fcntl.ioctl(fd, _eviocgabs(asse),
                             b"\0" * struct.calcsize(_ABS_FORMATO))
        _, minimo, massimo = struct.unpack(_ABS_FORMATO, grezzo)[:3]
    except Exception:
        return None
    if massimo <= minimo:
        return None
    return (minimo, massimo)


def posizione_asse(valore, intervallo):
    """Da valore grezzo a frazione fra -1 e +1, con il centro a zero."""
    if not intervallo:
        # Senza intervallo noto si assume la croce direzionale, che vale
        # -1/0/+1: e' il caso in cui l'ioctl fallisce piu' spesso.
        return max(-1.0, min(1.0, float(valore)))
    minimo, massimo = intervallo
    centro = (minimo + massimo) / 2.0
    meta = (massimo - minimo) / 2.0
    if meta <= 0:
        return 0.0
    return max(-1.0, min(1.0, (valore - centro) / meta))


def direzione_asse(posizione, precedente=0):
    """-1, 0 o +1 dalla posizione di un asse, con isteresi.

    `precedente` e' la direzione in cui l'asse gia' era: serve a decidere se si
    sta entrando nella zona attiva (soglia alta) o uscendone (soglia bassa).
    E' una funzione pura, quindi si prova senza un pad in mano.
    """
    soglia = ZONA_RILASCIO if precedente else ZONA_MORTA
    if posizione <= -soglia:
        return -1
    if posizione >= soglia:
        return 1
    return 0


# ------------------------------------------------------------- i dispositivi

def _dispositivi_input(marcatore):
    """I dispositivi di /dev/input che il kernel affida a un dato gestore.

    Si legge /proc/bus/input/devices invece di aprire tutto: un mouse o un
    sensore di temperatura hanno anch'essi degli eventi, e aprirli a caso vuol
    dire tenere descrittori inutili su hardware che non c'entra. Il gestore
    `kbd` sono le tastiere, `js` i joystick — lo dice il kernel, non noi.
    """
    trovati = []
    try:
        with open("/proc/bus/input/devices") as handle:
            testo = handle.read()
    except OSError:
        return trovati
    for blocco in testo.split("\n\n"):
        righe = [r for r in blocco.splitlines() if r.startswith("H: Handlers=")]
        if not righe:
            continue
        campi = righe[0].split("=", 1)[1].split()
        if not any(c == marcatore or c.startswith(marcatore)
                   for c in campi if not c.startswith("event")):
            continue
        nome = ""
        for riga in blocco.splitlines():
            if riga.startswith('N: Name="'):
                nome = riga.split('"')[1]
        for campo in campi:
            if campo.startswith("event"):
                trovati.append(("/dev/input/" + campo, nome))
    return trovati


def tastiere():
    """I percorsi delle tastiere collegate."""
    return [percorso for percorso, _ in _dispositivi_input("kbd")]


def joystick(con_nome=False):
    """I joystick collegati. Con `con_nome`, coppie (percorso, nome).

    Il nome serve solo alla pagina web, per far vedere che il pad e' stato
    riconosciuto: «Wireless Controller» per un DualShock 4, il proprio nome
    per un Nacon o un pad generico.
    """
    trovati = _dispositivi_input("js")
    return trovati if con_nome else [percorso for percorso, _ in trovati]


# ------------------------------------------------------------------ il ciclo

class Lettore:
    """Legge i dispositivi scelti e riferisce le azioni a chi lo usa.

    `dispositivi` e' una funzione che dice, ogni volta, da quali percorsi
    accettare comandi: un pad si stacca e si riattacca, e la configurazione
    puo' cambiare mentre il servizio gira, quindi non si fotografa un elenco
    all'avvio.

    `azione(nome, giu, avvio)` viene chiamata a ogni cambiamento. `avvio` dice
    se il comando arriva da un pulsante che ha il diritto di *far cominciare*
    una partita: la distinzione appartiene a chi riceve, non a chi legge.
    """

    def __init__(self, dispositivi, azione, tasti=None, pulsanti=None,
                 assi=None, avvio=PAD_AVVIO, etichetta="comandi",
                 su_codice=None):
        self._dispositivi = dispositivi
        self._azione = azione
        # Chi vuole vedere i codici **prima** che diventino azioni: serve a
        # imparare quale tasto e' un pulsante del cabinato. Restituendo True
        # si ingoia l'evento, che altrimenti farebbe anche il suo mestiere.
        self._su_codice = su_codice
        self._tasti = tasti or {}
        self._pulsanti = pulsanti or {}
        self._assi = assi or {}
        self._avvio = tuple(avvio or ())
        self._etichetta = etichetta

        self._stop = threading.Event()
        self._thread = None
        # Intervallo e direzione per (fd, asse): un pad puo' avere assi con
        # intervalli diversi, e due pad collegati insieme di sicuro.
        self._intervalli = {}
        self._direzioni = {}

    # ------------------------------------------------------------ ciclo di vita

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._ciclo,
                                        name=self._etichetta, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(timeout=2.0)
        self._intervalli.clear()
        self._direzioni.clear()

    def attivo(self):
        return self._thread is not None and self._thread.is_alive()

    # ------------------------------------------------------------------ lettura

    def _ciclo(self):
        aperti = {}
        while not self._stop.is_set():
            try:
                voluti = list(self._dispositivi() or [])
            except Exception:
                voluti = []
            for percorso in voluti:
                if percorso in aperti:
                    continue
                try:
                    aperti[percorso] = os.open(percorso, os.O_RDONLY | os.O_NONBLOCK)
                    print("[%s] comando: %s" % (self._etichetta, percorso))
                except OSError:
                    # Un pad staccato o senza permessi non e' un guasto: si
                    # riprova al prossimo giro, e intanto resta il web.
                    aperti[percorso] = None
            for percorso in list(aperti):
                if percorso not in voluti:
                    fd = aperti.pop(percorso)
                    self._chiudi(fd)

            fd_attivi = [fd for fd in aperti.values() if fd is not None]
            if not fd_attivi:
                self._stop.wait(3.0)
                continue
            try:
                pronti, _, _ = select.select(fd_attivi, [], [], 1.0)
            except (OSError, ValueError):
                pronti = []
            for fd in pronti:
                self.svuota(fd, aperti)

        for fd in aperti.values():
            self._chiudi(fd)

    @staticmethod
    def _chiudi(fd):
        if fd is None:
            return
        try:
            os.close(fd)
        except OSError:
            pass

    def svuota(self, fd, aperti=None):
        """Consuma gli eventi pronti su un descrittore.

        Pubblica e non privata perche' e' il punto in cui si possono infilare
        eventi finti: una prova con eventi costruiti a mano vale piu' di una
        prova con un pad in mano, che nessuno rifara' mai allo stesso modo.
        """
        try:
            dati = os.read(fd, DIM_EVENTO * 64)
        except OSError:
            if aperti is not None:
                for percorso, altro in list(aperti.items()):
                    if altro == fd:
                        aperti[percorso] = None
                        self._chiudi(fd)
            return 0
        letti = 0
        for inizio in range(0, len(dati) - DIM_EVENTO + 1, DIM_EVENTO):
            _, _, tipo, codice, valore = struct.unpack(
                FORMATO_EVENTO, dati[inizio:inizio + DIM_EVENTO])
            if tipo == EV_KEY:
                self.evento_tasto(fd, codice, valore)
                letti += 1
            elif tipo == EV_ABS:
                self.evento_asse(fd, codice, valore)
                letti += 1
        return letti

    def evento_tasto(self, fd, codice, valore):
        # valore 2 e' la ripetizione automatica del kernel: chi riceve la sua
        # se la fa da solo, e sommarle vuol dire un comando che scatta.
        if valore not in (0, 1):
            return
        if self._su_codice is not None:
            try:
                if self._su_codice(codice, valore == 1):
                    return
            except Exception:
                pass
        pulsante = self._pulsanti.get(codice)
        if pulsante is not None:
            self._azione(pulsante, valore == 1, codice in self._avvio)
            return
        azione = self._tasti.get(codice)
        if azione:
            self._azione(azione, valore == 1, False)

    def evento_asse(self, fd, asse, valore):
        """Una levetta o la croce direzionale diventano premuto/rilasciato."""
        coppia = self._assi.get(asse)
        if coppia is None:
            return
        chiave = (fd, asse)
        if chiave not in self._intervalli:
            self._intervalli[chiave] = intervallo_asse(fd, asse)
        posizione = posizione_asse(valore, self._intervalli[chiave])
        prima = self._direzioni.get(chiave, 0)
        adesso = direzione_asse(posizione, prima)
        if adesso == prima:
            return
        self._direzioni[chiave] = adesso
        negativa, positiva = coppia
        # Passando da un estremo all'altro senza toccare il centro va
        # rilasciata la direzione vecchia, altrimenti resta premuta per sempre
        # e si cammina all'indietro mentre si va avanti.
        if prima:
            self._azione(negativa if prima < 0 else positiva, False, False)
        if adesso:
            self._azione(negativa if adesso < 0 else positiva, True, False)

    def dimentica(self):
        """Scorda lo stato degli assi: si usa chiudendo una sessione."""
        self._direzioni.clear()
