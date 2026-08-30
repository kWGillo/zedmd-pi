"""Doom sul pannello.

Doom gira come **processo separato** — `doom/doom-dmd`, doomgeneric con
l'uscita ritagliata a 256x64 — e non come libreria dentro il servizio. Tre
ragioni, in ordine di importanza:

  1. **Licenza.** doomgeneric discende dai sorgenti di Doom, che sono GPL
     versione 2. Questo progetto e' GPLv3, e GPL2-only dentro un lavoro GPLv3
     non ci sta. Due processi che si parlano da una pipe non si "collegano":
     restano due programmi distinti, ciascuno con la sua licenza.
  2. **Isolamento.** Doom del 1993 e' solido ma non e' scritto per non morire
     mai. Se cade, cade lui: il pannello torna all'orologio e il servizio non
     se ne accorge.
  3. **Semplicita'.** Nessun binding, nessuna GIL da contendere: si legge un
     fotogramma da una pipe e lo si pubblica.

Il protocollo e' volutamente stupido — stdout porta fotogrammi grezzi di
dimensione fissa, stdin porta coppie [stato, tasto] — ed e' descritto per
esteso in `doom/doomgeneric_dmd.c`.

**Doom non e' un servizio: e' una sessione.** Si preme "Gioca", tutto il resto
si ferma, si gioca; si esce, e tutto riprende da dove stava. Fine.

Nella 3.0 c'era anche un attract mode — Doom che gioca da solo con i propri
demo quando nessuno tocca niente — e nella 3.1 una deroga apposta nell'arbitro
per farlo comparire su un cabinato acceso, dove ZeDMD non molla mai il
pannello. Non ha funzionato in nessuna delle due versioni: prima non si vedeva
mai, poi restava a schermo dopo l'uscita da una partita, con il Media Player
che spuntava ogni tanto perche' aveva la priorita' piu' alta. Tre meccanismi
per una funzione che nessuno aveva chiesto.

Tolti tutti. Il processo esiste **solo mentre si gioca**, e in quel periodo il
pannello e' suo per presa esclusiva — lo stesso meccanismo della gestione
media — non per punteggio di priorita'. Chiusa la sessione il processo muore e
le sorgenti riprendono il loro giro senza essersi accorte di niente.
"""

import os
import select
import struct
import subprocess
import threading
import time

from PIL import Image

from .base import Source

LARGHEZZA = 256
ALTEZZA = 64
BYTE_FOTOGRAMMA = LARGHEZZA * ALTEZZA * 3

# Codici tasto di Doom (doomkeys.h). Non sono ASCII e non sono quelli di
# Linux: sono una numerazione sua, e questa tabella e' l'unico posto del
# progetto che deve saperlo.
DOOM_TASTI = {
    "su": 0xad,
    "giu": 0xaf,
    "sinistra": 0xac,
    "destra": 0xae,
    "lato_sx": 0xa0,
    "lato_dx": 0xa1,
    "fuoco": 0xa3,
    "usa": 0xa2,
    "corsa": 0x80 + 0x36,   # shift destro
    "mappa": 9,             # tab
    "menu": 27,             # escape
    "invio": 13,
    "arma1": ord("1"),
    "arma2": ord("2"),
    "arma3": ord("3"),
    "arma4": ord("4"),
    "arma5": ord("5"),
    "arma6": ord("6"),
    "arma7": ord("7"),
}

# I tasti che la pagina web mostra come pulsanti, nell'ordine in cui li
# disegna. Il resto della tabella resta raggiungibile da tastiera vera.
PULSANTI = ("su", "giu", "sinistra", "destra", "lato_sx", "lato_dx",
            "fuoco", "usa", "corsa", "menu", "invio", "mappa")

# Tastiera vera: codici Linux (input-event-codes.h) verso le nostre azioni.
# WASD accanto alle frecce perche' su una tastiera da cabinato le frecce
# stanno spesso dalla parte sbagliata.
LINUX_TASTI = {
    103: "su", 108: "giu", 105: "sinistra", 106: "destra",
    17: "su", 31: "giu", 30: "lato_sx", 32: "lato_dx",      # W S A D
    29: "fuoco", 97: "fuoco", 56: "fuoco",                   # ctrl, alt
    57: "usa",                                               # spazio
    42: "corsa", 54: "corsa",                                # shift
    15: "mappa", 1: "menu", 28: "invio",
    2: "arma1", 3: "arma2", 4: "arma3", 5: "arma4",
    6: "arma5", 7: "arma6", 8: "arma7",
}

EV_KEY = 0x01
EV_ABS = 0x03
# struct input_event: due campi di timeval, poi tipo, codice e valore. Le
# dimensioni cambiano fra 32 e 64 bit, e su un Pi capitano entrambe: si
# lasciano calcolare a struct invece di scriverle a mano.
FORMATO_EVENTO = "@llHHi"
DIM_EVENTO = struct.calcsize(FORMATO_EVENTO)

# ------------------------------------------------------------------ joystick
#
# Un pad PS4, o un pad da PC come il Nacon, sotto Linux e' un dispositivo di
# /dev/input come una tastiera: stessi eventi, stessa struttura, nessuna
# libreria in piu'. Cambiano due cose. I **pulsanti** hanno codici sopra 0x130
# invece dei codici dei tasti. E ci sono gli **assi**, EV_ABS, che non sono
# premuti o rilasciati ma hanno un valore: la croce direzionale vale -1, 0 o
# +1, le levette un numero dentro un intervallo che cambia da pad a pad.
#
# Doom pero' capisce solo tasti premuti e rilasciati, e il lavoro vero e' li':
# trasformare una posizione in un premuto/rilasciato senza che il personaggio
# tremi quando la levetta e' quasi al centro.

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

# I nomi sulle plastiche cambiano da un pad all'altro, e negli anni qualche
# kernel ha scambiato triangolo e quadrato: per questo le azioni importanti
# stanno su piu' pulsanti. Sparare con R2 *e* con la croce non da' fastidio a
# nessuno, e salva chi ha un pad che si dichiara diversamente.
PAD_PULSANTI = {
    BTN_SOUTH: "fuoco", BTN_TR2: "fuoco", BTN_TR: "fuoco",
    BTN_EAST: "usa", BTN_WEST: "usa",
    BTN_TL: "corsa", BTN_TL2: "corsa",
    BTN_NORTH: "mappa",
    BTN_START: "menu", BTN_MODE: "menu",
    BTN_SELECT: "invio",
    BTN_THUMBL: "arma1", BTN_THUMBR: "arma2",
}

# Il pulsante che puo' *far cominciare* una partita: Options o il tasto PS,
# che nessuno preme per sbaglio sfiorando un pad appoggiato al cabinato.
PAD_AVVIO = (BTN_START, BTN_MODE)

ABS_X = 0x00
ABS_Y = 0x01
ABS_RX = 0x03
ABS_RY = 0x04
ABS_HAT0X = 0x10
ABS_HAT0Y = 0x11

# Assi -> coppia di azioni (valore negativo, valore positivo).
# Levetta sinistra: camminare e passo laterale. Levetta destra: girare. E' la
# disposizione a due levette a cui e' abituato chiunque abbia avuto un pad in
# mano negli ultimi vent'anni. La croce direzionale fa le stesse cose della
# levetta sinistra, ma gira invece di fare il passo laterale: su una croce il
# passo laterale non serve, e girare si'.
PAD_ASSI = {
    ABS_Y: ("su", "giu"),
    ABS_X: ("lato_sx", "lato_dx"),
    ABS_RY: ("su", "giu"),
    ABS_RX: ("sinistra", "destra"),
    ABS_HAT0Y: ("su", "giu"),
    ABS_HAT0X: ("sinistra", "destra"),
}

# Zona morta come frazione della corsa, e isteresi. Si preme al 40% e si
# rilascia al 28%: senza la differenza fra le due soglie una levetta tenuta
# appena oltre il limite genera una raffica di premuto/rilasciato, e in Doom
# quello si vede come un personaggio che scatta invece di camminare.
ZONA_MORTA = 0.40
ZONA_RILASCIO = 0.28

# EVIOCGABS(asse): chiede al kernel l'intervallo vero di un asse. Serve perche'
# un intervallo standard non esiste — un DualShock 4 riporta 0..255, molti pad
# da PC -32768..32767 — e darne per scontato uno vuol dire che sull'altro la
# levetta risulta sempre a fondo corsa oppure sempre ferma.
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


def controlla_wad(percorso):
    """Motivo per cui questo WAD non va bene, o '' se va bene.

    Che il file esista non basta. I primi quattro byte di un WAD dicono che
    cos'e': `IWAD` e' un gioco completo, `PWAD` e' un'estensione che da sola
    non parte. Un file scaricato a meta' o rinominato per sbaglio supererebbe
    il controllo del nome, e poi Doom si fermerebbe con un messaggio che non
    aiuta nessuno.
    """
    percorso = percorso or ""
    if not percorso:
        return "nessun WAD indicato"
    if not os.path.isfile(percorso):
        return "WAD non trovato: %s" % percorso
    try:
        with open(percorso, "rb") as handle:
            tipo = handle.read(4).decode("ascii", "replace")
        dimensione = os.path.getsize(percorso)
    except OSError as exc:
        return "WAD illeggibile: %s" % exc
    if tipo == "PWAD":
        return "%s e' un'estensione, non un gioco completo" % \
            os.path.basename(percorso)
    if tipo != "IWAD":
        return "%s non e' un WAD" % os.path.basename(percorso)
    if dimensione < 2 * 1024 * 1024:
        return "%s e' troppo piccolo: forse scaricato a meta'" % \
            os.path.basename(percorso)
    return ""


def _dispositivi_input(marcatore):
    """I dispositivi di /dev/input che il kernel affida a un dato gestore.

    Si legge /proc/bus/input/devices invece di aprire tutto: un mouse o un
    sensore di temperatura hanno anch'essi degli eventi, e aprirli a caso vuol
    dire tenere descrittori inutili su hardware che non c'entra. Il gestore
    `kbd` sono le tastiere, `js` i joystick — lo dice il kernel, non noi, e va
    bene per qualunque pad che lui riconosca come tale.
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


class DoomSource(Source):
    name = "doom"
    label = "Doom"
    # La priorita' non serve a niente e resta a zero: Doom non partecipa alla
    # gara. O e' in sessione, e allora il pannello e' preso — e la presa non
    # si discute — oppure non esiste proprio. `enabled` resta False per
    # sempre, cosi' non c'e' nessuna strada per cui possa comparire per sbaglio.
    priority = 0

    def __init__(self, cfg, width, height, arbiter=None):
        super().__init__(cfg, width, height)
        self.arbiter = arbiter

        self._lock = threading.Lock()
        self._image = None
        self._dirty = False

        self._proc = None
        self._thread = None
        self._tastiera_thread = None
        self._stop = threading.Event()

        self._running = False
        self._fotogrammi = 0
        self._ultimo_frame = 0.0
        self._errore = ""

        # Sessione: o e' aperta — processo vivo, pannello preso, tasti che
        # arrivano a Doom — oppure non c'e' niente di Doom in esecuzione.
        self._sessione = False
        self._ultimo_tasto = 0.0
        self._premuti = set()
        self._ultimo_tentativo = 0.0
        # Assi dei joystick: intervallo dichiarato dal kernel e direzione in
        # cui l'asse si trova adesso, per dispositivo. L'isteresi ha bisogno
        # di sapere da dove si viene.
        self._intervalli = {}
        self._direzioni = {}

    # ------------------------------------------------------------ ciclo di vita

    def start(self):
        """Rende Doom *disponibile*, non lo avvia.

        Non e' un servizio e non compare fra gli interruttori: finche' nessuno
        preme "Gioca" non gira niente. L'unica cosa che parte qui e' la lettura
        della tastiera, e solo se e' stato chiesto di poter cominciare una
        partita premendo un tasto sul cabinato.
        """
        self._stop.clear()
        self._errore = ""
        if (self.cfg["doom"].get("keyboard", True)
                and self._tastiera_thread is None):
            self._tastiera_thread = threading.Thread(
                target=self._leggi_tastiere, name="doom-tastiera", daemon=True)
            self._tastiera_thread.start()

    def stop(self):
        self._stop.set()
        self.chiudi_sessione()
        self._tastiera_thread = None

    def avvia_da_tastiera(self):
        """Se un tasto sul cabinato puo' far cominciare una partita.

        Predefinito spento: il DMD sta in mezzo a un flipper, e un tasto
        sfiorato per caso non deve portarsi via il pannello a meta' partita.
        """
        return bool(self.cfg["doom"].get("keyboard_starts", False))

    def avvia_da_pad(self):
        """Se Options sul pad puo' far cominciare una partita.

        Qui il predefinito e' **acceso**, al contrario della tastiera, e la
        differenza non e' un capriccio: un tasto qualunque su una tastiera si
        preme per sbaglio, un pulsante preciso su un pad che si tiene in mano
        no. Ed e' il gesto che uno fa istintivamente — prendi il pad, premi
        Start — senza andare a cercare una pagina web.
        """
        return bool(self.cfg["doom"].get("joystick_starts", True))

    # ------------------------------------------------------------------ processo

    def _comando(self, gioca=False):
        """La riga di comando, diversa fra attract e partita.

        Senza `-warp` Doom fa quello che ha sempre fatto: titolo, poi i suoi
        demo, in un ciclo infinito. E' l'attract mode, gratis.

        Con `-warp` entra dritto nel livello. E' il modo affidabile di far
        cominciare una partita: premere un tasto durante un demo dovrebbe
        riportare al menu, ma poi bisognerebbe navigarlo a colpi di frecce
        per scegliere episodio e difficolta' — su un cabinato, con un pannello
        alto sessantaquattro pixel, e' una via crucis. Far ripartire il
        processo dentro il livello costa un secondo e non sbaglia mai.
        """
        conf = self.cfg["doom"]
        args = [conf["binary"],
                "-iwad", conf["wad"],
                "--fascia-alto=%d" % int(conf.get("band_top", 36)),
                "--fascia-altezza=%d" % int(conf.get("band_height", 96)),
                "--gamma=%.2f" % float(conf.get("gamma", 1.15)),
                # Nessun suono: l'audio del cabinato e' di Batocera, e un
                # secondo canale sarebbe solo rumore sopra al gioco vero.
                "-nosound", "-nomusic"]
        if not gioca:
            return args

        try:
            skill = int(conf.get("skill", 3))
        except (TypeError, ValueError):
            skill = 3
        if 1 <= skill <= 5:
            args += ["-skill", str(skill)]
        mappa = str(conf.get("start_map", "") or "1 1").strip()
        if mappa:
            args += ["-warp"] + mappa.split()[:2]
        return args

    def _avvia_processo(self, gioca=False):
        conf = self.cfg["doom"]
        if not os.path.isfile(conf["binary"]):
            self._errore = "binario non trovato: %s" % conf["binary"]
            return False
        problema = controlla_wad(conf["wad"])
        if problema:
            self._errore = problema
            return False

        # Doom scrive configurazione e salvataggi nella cartella di lavoro.
        # Lasciargli /opt/dmd vorrebbe dire sporcare l'installazione e far
        # fallire la verifica delle impronte al prossimo aggiornamento.
        lavoro = conf.get("work_dir") or "/var/lib/dmd/doom/stato"
        try:
            os.makedirs(lavoro, exist_ok=True)
        except OSError as exc:
            self._errore = str(exc)
            return False

        try:
            self._proc = subprocess.Popen(
                self._comando(gioca), cwd=lavoro,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                bufsize=0)
        except OSError as exc:
            self._errore = str(exc)
            self._proc = None
            return False

        self._errore = ""
        self._fotogrammi = 0
        self._thread = threading.Thread(target=self._leggi_fotogrammi,
                                        name="doom-video", daemon=True)
        self._thread.start()
        return True

    def _ferma_processo(self):
        proc, self._proc = self._proc, None
        if proc is None:
            return
        try:
            if proc.stdin:
                proc.stdin.close()
        except Exception:
            pass
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
                proc.wait(timeout=2)
            except Exception:
                pass
        with self._lock:
            self._image = None
            self._dirty = False

    def riavvia(self, gioca=False):
        """Riparte: dal titolo e dai demo, oppure dentro il livello."""
        self._ferma_processo()
        if self._running:
            return self._avvia_processo(gioca)
        return False

    # ------------------------------------------------------------------ video

    def _leggi_fotogrammi(self):
        proc = self._proc
        if proc is None or proc.stdout is None:
            return
        buffer = bytearray(BYTE_FOTOGRAMMA)
        vista = memoryview(buffer)
        while self._running and proc.poll() is None:
            riempito = 0
            # Una pipe consegna quel che ha, non quel che si chiede: il
            # fotogramma si ricompone qui, altrimenti bastano due letture
            # corte per sfasare tutto il flusso che segue.
            while riempito < BYTE_FOTOGRAMMA:
                try:
                    letti = proc.stdout.readinto(vista[riempito:])
                except (OSError, ValueError):
                    letti = 0
                if not letti:
                    return
                riempito += letti
            try:
                immagine = Image.frombytes("RGB", (LARGHEZZA, ALTEZZA),
                                           bytes(buffer))
            except ValueError:
                continue
            if (LARGHEZZA, ALTEZZA) != (self.width, self.height):
                immagine = immagine.resize((self.width, self.height))
            with self._lock:
                self._image = immagine
                self._dirty = True
            self._fotogrammi += 1
            self._ultimo_frame = time.time()

    # ------------------------------------------------------------------ arbitro

    def active(self):
        if not self._sessione or self._proc is None:
            return False
        if self._proc.poll() is not None:
            return False
        # Un processo vivo che non manda fotogrammi da qualche secondo e'
        # bloccato: meglio lasciare il pannello a chi ha qualcosa da mostrare.
        return bool(self._image is not None
                    and time.time() - self._ultimo_frame < 5.0)

    def frame(self):
        with self._lock:
            if not self._dirty or self._image is None:
                return None
            self._dirty = False
            return self._image

    def invalidate(self):
        with self._lock:
            if self._image is not None:
                self._dirty = True

    def status(self, lang=None):
        if self._errore:
            return self.t("status.doom.error", lang, error=self._errore)
        if not self._sessione:
            return self.t("status.doom.idle", lang)
        if self._proc is None or self._proc.poll() is not None:
            return self.t("status.doom.stopped", lang)
        return self.t("status.doom.playing", lang,
                      seconds=int(self.inattivita()))

    # ---------------------------------------------------------------- sessione

    def in_sessione(self):
        return self._sessione

    def inattivita(self):
        if not self._ultimo_tasto:
            return 0.0
        return time.time() - self._ultimo_tasto

    def apri_sessione(self):
        """Avvia Doom, prende il pannello e comincia a passargli i tasti.

        E' l'unico modo in cui Doom finisce a schermo. Prima di questo momento
        non c'e' nessun processo in esecuzione: non e' un servizio in attesa,
        e' un programma che parte quando lo chiedi.
        """
        self._ultimo_tasto = time.time()
        if self._sessione:
            return True
        self._running = True
        self._errore = ""
        self._ultimo_tentativo = time.time()
        # Si parte dentro il livello invece che dal menu: vedi `_comando`.
        if not self.riavvia(gioca=True):
            self._running = False
            return False
        self._sessione = True
        if self.arbiter is not None:
            # Senza scadenza: chi gioca puo' stare fermo un minuto davanti a
            # una porta senza che il pannello gli torni all'orologio. A
            # chiudere ci pensa il tempo di inattivita', o il pulsante.
            self.arbiter.hold_on(self.name)
        return True

    def chiudi_sessione(self, riavvia=False):
        """Spegne Doom e restituisce il pannello alle sorgenti.

        `riavvia` esiste solo per non rompere i richiami esistenti: non si
        riparte mai. Fuori da una sessione Doom non deve esistere — restare
        acceso a priorita' bassa voleva dire, dopo l'uscita, un pannello che
        continuava a mostrare Doom con il Media Player che spuntava ogni
        tanto. Era il difetto segnalato, ed era la conseguenza diretta di
        tenere in piedi un attract mode che nessuno aveva chiesto.
        """
        aperta = self._sessione
        self._sessione = False
        self._running = False
        self._premuti.clear()
        if self.arbiter is not None:
            self.arbiter.hold_off(self.name)
        self._ferma_processo()
        return aperta

    # Ogni quanto si riprova ad avviare Doom quando l'avvio e' fallito. Non
    # troppo spesso: se manca il binario, riprovare dieci volte al secondo
    # riempie il log e non risolve niente.
    RIPROVA_OGNI = 30

    def mantieni(self):
        """Rimette in piedi Doom se e' morto durante una partita.

        Vale solo a sessione aperta: fuori non c'e' niente da mantenere. Se il
        processo cade da solo — o non e' mai partito perche' un percorso era
        sbagliato — si ritenta, cosi' correggere l'errore dalla pagina basta a
        rimettere in moto senza uscire e rientrare.
        """
        if not self._sessione:
            return False
        if self._proc is not None and self._proc.poll() is None:
            return False
        adesso = time.time()
        if adesso - self._ultimo_tentativo < self.RIPROVA_OGNI:
            return False
        self._ultimo_tentativo = adesso
        return self._avvia_processo(gioca=True)

    def controlla_inattivita(self):
        """Chiude la sessione se non tocca nessuno da abbastanza tempo.

        La chiama il ciclo di rendering: non serve un thread per un confronto
        fra due numeri.
        """
        if not self._sessione:
            return
        try:
            limite = int(self.cfg["doom"].get("session_timeout", 180))
        except (TypeError, ValueError):
            limite = 180
        if limite > 0 and self.inattivita() > limite:
            print("[doom] sessione chiusa dopo %d s senza comandi" % limite)
            self.chiudi_sessione()

    # ------------------------------------------------------------------ tasti

    def premi(self, azione, giu=True, apri=True):
        """Manda un tasto a Doom.

        `apri` decide se un tasto puo' *cominciare* una partita. Dai pulsanti
        della pagina Doom si', perche' chi li preme sta guardando quella
        pagina. Dalla tastiera del cabinato solo se e' stato chiesto: il DMD
        sta in mezzo a un flipper, e un tasto sfiorato per caso non deve
        portarsi via il pannello a meta' partita.
        """
        codice = DOOM_TASTI.get(azione)
        if codice is None:
            return False
        if not self._sessione:
            if not apri or not self.apri_sessione():
                return False
        self._ultimo_tasto = time.time()

        if giu:
            self._premuti.add(azione)
        else:
            self._premuti.discard(azione)

        proc = self._proc
        if proc is None or proc.stdin is None or proc.poll() is not None:
            return False
        try:
            proc.stdin.write(bytes((1 if giu else 0, codice)))
            proc.stdin.flush()
        except (OSError, ValueError) as exc:
            self._errore = str(exc)
            return False
        return True

    def tocca(self, azione, durata=0.12):
        """Premi e rilascia: e' quello che fa un pulsante della pagina web.

        Un pulsante su un telefono non ha un "rilascio" affidabile — un dito
        che scivola fuori dal pulsante non genera niente — e un tasto rimasto
        premuto in Doom vuol dire camminare nel muro per sempre.
        """
        if not self.premi(azione, True):
            return False
        timer = threading.Timer(max(0.02, min(1.0, durata)),
                                lambda: self.premi(azione, False))
        timer.daemon = True
        timer.start()
        return True

    def premuti(self):
        return sorted(self._premuti)

    # ------------------------------------------------------------ tastiera vera

    def _leggi_tastiere(self):
        """Legge tastiere e joystick collegati al Pi, senza librerie in piu'.

        `evdev` sarebbe piu' comodo ma e' un pacchetto da installare, e qui
        serve solo leggere una struttura di ventiquattro byte: si fa con
        `struct`, che c'e' sempre. Tastiere e pad passano dallo stesso ciclo
        perche' sotto Linux sono la stessa cosa — cambia solo cosa mandano.
        """
        aperti = {}
        while not self._stop.is_set():
            voluti = self._dispositivi()
            for percorso in voluti:
                if percorso in aperti:
                    continue
                try:
                    aperti[percorso] = os.open(percorso, os.O_RDONLY | os.O_NONBLOCK)
                    print("[doom] comando: %s" % percorso)
                except OSError:
                    # Un pad staccato o senza permessi non e' un guasto: si
                    # riprova al prossimo giro, e intanto resta il web.
                    aperti[percorso] = None
            for percorso in list(aperti):
                if percorso not in voluti:
                    fd = aperti.pop(percorso)
                    if fd is not None:
                        try:
                            os.close(fd)
                        except OSError:
                            pass

            fd_attivi = [fd for fd in aperti.values() if fd is not None]
            if not fd_attivi:
                self._stop.wait(3.0)
                continue
            try:
                pronti, _, _ = select.select(fd_attivi, [], [], 1.0)
            except (OSError, ValueError):
                pronti = []
            for fd in pronti:
                self._svuota(fd, aperti)

        for fd in aperti.values():
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass

    def _dispositivi(self):
        """Tutto quello da cui accettare comandi, in questo momento."""
        elenco = []
        conf = self.cfg["doom"]
        scelto = str(conf.get("keyboard_device", "")).strip()
        if conf.get("keyboard", True):
            elenco.extend([scelto] if scelto else tastiere())
        if conf.get("joystick", True):
            scelto = str(conf.get("joystick_device", "")).strip()
            elenco.extend([scelto] if scelto else joystick())
        # Un pad che si dichiara anche tastiera comparirebbe due volte, e ogni
        # evento arriverebbe doppio.
        senza_ripetizioni = []
        for percorso in elenco:
            if percorso not in senza_ripetizioni:
                senza_ripetizioni.append(percorso)
        return senza_ripetizioni

    def _svuota(self, fd, aperti):
        try:
            dati = os.read(fd, DIM_EVENTO * 64)
        except OSError:
            for percorso, altro in list(aperti.items()):
                if altro == fd:
                    aperti[percorso] = None
                    try:
                        os.close(fd)
                    except OSError:
                        pass
            return
        for inizio in range(0, len(dati) - DIM_EVENTO + 1, DIM_EVENTO):
            _, _, tipo, codice, valore = struct.unpack(
                FORMATO_EVENTO, dati[inizio:inizio + DIM_EVENTO])
            if tipo == EV_KEY:
                self._evento_tasto(fd, codice, valore)
            elif tipo == EV_ABS:
                self._evento_asse(fd, codice, valore)

    def _evento_tasto(self, fd, codice, valore):
        # valore 2 e' la ripetizione automatica del kernel: Doom la sua se la
        # fa da solo, e sommarle vuol dire un personaggio che scatta invece di
        # camminare.
        if valore not in (0, 1):
            return
        pulsante = PAD_PULSANTI.get(codice)
        if pulsante is not None:
            # Il pad puo' far cominciare una partita, ma solo con Options: e'
            # un gesto deliberato, mentre un pad appoggiato al cabinato puo'
            # benissimo prendere una gomitata.
            apri = (self.avvia_da_pad() and codice in PAD_AVVIO)
            self.premi(pulsante, valore == 1, apri=apri)
            return
        azione = LINUX_TASTI.get(codice)
        if azione:
            self.premi(azione, valore == 1, apri=self.avvia_da_tastiera())

    def _evento_asse(self, fd, asse, valore):
        """Una levetta o la croce direzionale diventano premuto/rilasciato."""
        coppia = PAD_ASSI.get(asse)
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
            self.premi(negativa if prima < 0 else positiva, False, apri=False)
        if adesso:
            self.premi(negativa if adesso < 0 else positiva, True,
                       apri=False)
