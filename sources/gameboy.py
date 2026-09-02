# -*- coding: utf-8 -*-
"""Game Boy sul pannello, con PyBoy.

Stessa forma di Doom, e per le stesse ragioni: **un processo separato** che
manda fotogrammi grezzi su una pipe (vedi `gb/gb_dmd.py`), e una sessione che
o e' aperta — pannello preso per presa esclusiva, tasti che arrivano al gioco
— oppure non esiste. Fuori dalla sessione non gira niente.

Due differenze rispetto a Doom, entrambe volute:

  - **Nessun pulsante del pad apre una sessione.** Start, PS e Select sono
    globali dalla 3.8.2 (scorrono i giochi ed escono), e un pulsante deve
    avere un significato solo: quella lezione e' costata tre giri di
    correzioni e non la rifacciamo. Il Game Boy si apre dalla sua pagina, o
    dalla tastiera se lo si e' chiesto.
  - **Start e Select del Game Boy stanno sulle levette premute** (L3 e R3).
    Sono due pulsanti che servono davvero a giocare — in molti giochi Start
    mette in pausa e Select cambia oggetto — e i pulsanti fisici con quel
    nome sono gia' impegnati.
"""

import os
import subprocess
import threading
import time

from PIL import Image

from .base import Source
from .comandi import (ABS_HAT0X, ABS_HAT0Y, ABS_RX, ABS_RY, ABS_X, ABS_Y,
                      BTN_EAST, BTN_NORTH, BTN_SELECT, BTN_SOUTH, BTN_START,
                      BTN_TL, BTN_TL2, BTN_TR, BTN_TR2, BTN_WEST, BTN_THUMBL,
                      BTN_THUMBR, Lettore, joystick, tastiere)

LARGHEZZA = 256
ALTEZZA = 64
BYTE_FOTOGRAMMA = LARGHEZZA * ALTEZZA * 3

ESTENSIONI = (".gb", ".gbc")

# I quattro livelli dello schermo, dal piu' chiaro al piu' scuro. Il Game Boy
# non ha colori: ha quattro gradazioni, e ogni schermo le rendeva a modo suo.
# Il verde e' quello del DMG del 1989; gli altri sono scelte nostre, e su un
# pannello LED arancione o ambra si leggono meglio del verde originale.
#
# Valgono per le cartucce Game Boy. Un gioco Game Boy Color porta i colori
# suoi e li ignora: e' la cartuccia a decidere, non lo schermo.
PALETTE = {
    "verde": ("Verde DMG", ("e0f8d0", "88c070", "346856", "081820")),
    "grigio": ("Grigio", ("ffffff", "aaaaaa", "555555", "000000")),
    "ambra": ("Ambra", ("ffd772", "d79a45", "8a5a1e", "2a1600")),
    "arancio": ("Arancione DMD", ("ffb060", "e07818", "8a3c00", "200c00")),
    "bianco_blu": ("Blu notte", ("dfeaff", "7aa0d0", "2a4a80", "0a1428")),
    "personalizzata": ("Personalizzata", ()),
}
PALETTE_PREDEFINITA = "verde"


def palette_scelte():
    """(chiave, etichetta) per il menu della pagina."""
    return [(chiave, valore[0]) for chiave, valore in PALETTE.items()]


def colori_palette(conf):
    """I quattro colori da passare al processo, come testo.

    Una palette con un nome vince sui colori scritti a mano: il menu e' quello
    che si guarda, e se dicesse "Ambra" mentre si vede il verde nessuno
    saprebbe piu' a cosa credere.
    """
    nome = (conf or {}).get("palette") or PALETTE_PREDEFINITA
    if nome != "personalizzata":
        colori = PALETTE.get(nome, PALETTE[PALETTE_PREDEFINITA])[1]
    else:
        colori = [str(c).lstrip("#") for c in (conf.get("palette_custom") or [])]
    colori = [c for c in colori if len(c) == 6]
    if len(colori) != 4:
        colori = PALETTE[PALETTE_PREDEFINITA][1]
    return ",".join(colori)

# Codici del protocollo verso gb_dmd.py. La tabella e' ripetuta la' dentro:
# sono due programmi separati, e un import fra i due sarebbe proprio il
# collegamento che il processo separato vuole evitare.
GB_TASTI = {
    "su": 1, "giu": 2, "sinistra": 3, "destra": 4,
    "a": 5, "b": 6, "start": 7, "select": 8,
}

# I pulsanti che la pagina web disegna, nell'ordine.
PULSANTI = ("su", "giu", "sinistra", "destra", "a", "b", "start", "select")

# Tastiera vera: codici Linux. Z e X per B e A e' la disposizione che usano
# tutti gli emulatori da vent'anni; le frecce e WASD fanno la stessa cosa.
LINUX_TASTI = {
    103: "su", 108: "giu", 105: "sinistra", 106: "destra",
    17: "su", 31: "giu", 30: "sinistra", 32: "destra",
    45: "a", 44: "b", 57: "a",                 # X, Z, spazio
    28: "start", 42: "select", 14: "select",   # invio, shift sinistro, backspace
    1: "esci",                                 # escape
}

# Pad. Croce e cerchio sono A e B; i dorsali fanno le stesse cose per chi ha
# le dita altrove. **Start e Select fisici sono quelli del Game Boy**: in
# Tetris si sceglie il numero di giocatori con Start, e senza non si gioca.
# Restano anche sulle levette premute, per chi ha un pad senza quei tasti.
#
# Perche' ora si puo'. Start e Select sono pulsanti globali del progetto —
# scorrono i giochi ed escono — ma a sessione aperta il lettore dei giochi si
# fa da parte (`GiochiSource.esclusiva`) e li lascia al Game Boy. La via
# d'uscita diventa **PS**, che sulla console vera vuol dire proprio quello.
PAD_PULSANTI = {
    BTN_SOUTH: "a", BTN_TR2: "a", BTN_TR: "a",
    BTN_EAST: "b", BTN_WEST: "b", BTN_TL: "b", BTN_TL2: "b",
    BTN_NORTH: "b",
    BTN_START: "start", BTN_THUMBL: "start",
    BTN_SELECT: "select", BTN_THUMBR: "select",
}

PAD_ASSI = {
    ABS_Y: ("su", "giu"),
    ABS_X: ("sinistra", "destra"),
    ABS_RY: ("su", "giu"),
    ABS_RX: ("sinistra", "destra"),
    ABS_HAT0Y: ("su", "giu"),
    ABS_HAT0X: ("sinistra", "destra"),
}


def controlla_rom(percorso):
    """Motivo per cui questa ROM non va bene, o '' se va bene.

    Non basta il nome del file. Ogni cartuccia Game Boy porta all'indirizzo
    0x104 il logo Nintendo, sempre gli stessi 48 byte: e' il controllo che
    faceva la console vera all'accensione, e distingue una ROM da un file
    scaricato a meta' o rinominato per sbaglio. Meglio dirlo qui che far
    partire l'emulatore su uno schermo nero.
    """
    percorso = percorso or ""
    if not percorso:
        return "nessuna ROM indicata"
    if not os.path.isfile(percorso):
        return "ROM non trovata: %s" % percorso
    nome = os.path.basename(percorso)
    if not nome.lower().endswith(ESTENSIONI):
        return "%s non ha estensione .gb o .gbc" % nome
    try:
        with open(percorso, "rb") as handle:
            handle.seek(0x104)
            logo = handle.read(48)
            intestazione = handle.read(0x14E - 0x134)
        dimensione = os.path.getsize(percorso)
    except OSError as exc:
        return "ROM illeggibile: %s" % exc
    if dimensione < 32 * 1024:
        return "%s e' troppo piccola per essere una cartuccia" % nome
    if logo[:8] != bytes.fromhex("CEED6666CC0D000B"):
        return "%s non ha il logo Nintendo: non e' una ROM valida" % nome
    # Somma di controllo dell'intestazione, byte 0x14D. La verificava la
    # console vera, e la verifica PyBoy: se non torna l'emulatore muore con
    # un'eccezione a schermo nero. Meglio dirlo qui, con il nome del file.
    if len(intestazione) >= 26:
        somma = 0
        for byte in intestazione[:25]:
            somma = (somma - byte - 1) & 0xFF
        if somma != intestazione[25]:
            return "%s ha l'intestazione corrotta: forse copiata a meta'" % nome
    return ""


def elenco_rom(cartella):
    """Le ROM presenti nella condivisione, in ordine alfabetico."""
    try:
        nomi = os.listdir(cartella)
    except OSError:
        return []
    fuori = []
    for nome in sorted(nomi, key=lambda s: s.lower()):
        if nome.startswith("."):
            continue
        if nome.lower().endswith(ESTENSIONI):
            intero = os.path.join(cartella, nome)
            fuori.append({"nome": nome, "percorso": intero,
                          "problema": controlla_rom(intero)})
    return fuori


class GameBoySource(Source):
    name = "gameboy"
    label = "Game Boy"
    # Come Doom: fuori dalla gara. O ha il pannello per presa esclusiva, o non
    # esiste. `enabled` resta False, cosi' non c'e' nessuna strada per cui
    # possa comparire per sbaglio.
    priority = 0

    def __init__(self, cfg, width, height, arbiter=None):
        super().__init__(cfg, width, height)
        self.arbiter = arbiter

        self._lock = threading.Lock()
        self._image = None
        self._dirty = False

        self._proc = None
        self._thread = None
        self._stop = threading.Event()

        self._running = False
        self._sessione = False
        self._rom = ""
        self._fotogrammi = 0
        self._ultimo_frame = 0.0
        self._ultimo_tasto = 0.0
        self._errore = ""
        self._premuti = set()

        self._lettore = Lettore(
            self._dispositivi, self._da_comando,
            tasti=LINUX_TASTI, pulsanti=PAD_PULSANTI, assi=PAD_ASSI,
            avvio=(), etichetta="gameboy")

    # ------------------------------------------------------------ ciclo di vita

    def start(self):
        """Rende il Game Boy *disponibile*, non lo avvia."""
        self._stop.clear()
        self._errore = ""
        if self.conf().get("keyboard", True):
            self._lettore.start()

    def stop(self):
        self._stop.set()
        self.chiudi_sessione()
        self._lettore.stop()

    def conf(self):
        return self.cfg.get("gameboy", {})

    def cartella(self):
        return self.conf().get("rom_dir") or "/srv/dmd/rom"

    def pronto(self):
        """Se l'emulatore e' installato. Senza PyBoy non c'e' niente da fare."""
        try:
            import pyboy  # noqa: F401
        except Exception:
            return False
        return os.path.isfile(self.conf().get("host", ""))

    # ------------------------------------------------------------------ processo

    def _comando(self, rom):
        conf = self.conf()
        return ["python3", conf["host"],
                "--rom", rom,
                "--larghezza", str(self.width),
                "--altezza", str(self.height),
                "--gamma", "%.2f" % float(conf.get("gamma", 1.0)),
                "--overscan", "%.0f" % float(conf.get("overscan", 0)),
                "--spostamento", "%d" % int(conf.get("spostamento", 0)),
                "--fps", "%.0f" % float(conf.get("fps", 30)),
                "--palette", colori_palette(conf)]

    def _avvia_processo(self, rom):
        problema = controlla_rom(rom)
        if problema:
            self._errore = problema
            return False
        if not os.path.isfile(self.conf().get("host", "")):
            self._errore = "manca %s" % self.conf().get("host", "")
            return False
        try:
            self._proc = subprocess.Popen(
                self._comando(rom), cwd=os.path.dirname(rom) or ".",
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                bufsize=0)
        except OSError as exc:
            self._errore = str(exc)
            self._proc = None
            return False

        self._errore = ""
        self._rom = rom
        self._fotogrammi = 0
        self._thread = threading.Thread(target=self._leggi_fotogrammi,
                                        name="gb-video", daemon=True)
        self._thread.start()
        return True

    def _ferma_processo(self):
        proc, self._proc = self._proc, None
        if proc is None:
            return
        # Prima si chiude stdin: l'emulatore lo legge come "e' finita" ed esce
        # da solo salvando la memoria della cartuccia. Il terminate arriva
        # dopo, per chi non se ne fosse accorto.
        try:
            if proc.stdin:
                proc.stdin.close()
        except Exception:
            pass
        try:
            proc.wait(timeout=2)
        except Exception:
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

    # ------------------------------------------------------------------ video

    def _leggi_fotogrammi(self):
        proc = self._proc
        if proc is None or proc.stdout is None:
            return
        buffer = bytearray(BYTE_FOTOGRAMMA)
        vista = memoryview(buffer)
        while self._running and proc.poll() is None:
            riempito = 0
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
            return self.t("status.gb.error", lang, error=self._errore)
        if not self.pronto():
            return self.t("status.gb.missing", lang)
        if not self._sessione:
            return self.t("status.gb.idle", lang,
                          count=len(elenco_rom(self.cartella())))
        if self._proc is None or self._proc.poll() is not None:
            return self.t("status.gb.stopped", lang)
        return self.t("status.gb.playing", lang,
                      name=os.path.basename(self._rom))

    # ---------------------------------------------------------------- sessione

    def in_sessione(self):
        return self._sessione

    def rom_corrente(self):
        return self._rom

    def inattivita(self):
        if not self._ultimo_tasto:
            return 0.0
        return time.time() - self._ultimo_tasto

    def apri_sessione(self, rom=""):
        """Avvia l'emulatore, prende il pannello e comincia a passargli i tasti."""
        rom = rom or self.conf().get("rom", "")
        self._ultimo_tasto = time.time()
        if self._sessione:
            if rom and rom != self._rom:
                # Cambiare cartuccia a sessione aperta: si spegne e si
                # riaccende, come si farebbe con la console vera.
                self._ferma_processo()
                if not self._avvia_processo(rom):
                    self.chiudi_sessione()
                    return False
            if self.arbiter is not None:
                self.arbiter.hold_on(self.name)
            return True

        self._running = True
        self._errore = ""
        if not self._avvia_processo(rom):
            self._running = False
            return False
        self._sessione = True
        if self.arbiter is not None:
            self.arbiter.hold_on(self.name)
        return True

    def chiudi_sessione(self):
        aperta = self._sessione
        self._sessione = False
        self._running = False
        self._premuti.clear()
        if self.arbiter is not None:
            self.arbiter.hold_off(self.name)
        self._ferma_processo()
        return aperta

    def controlla_inattivita(self):
        if not self._sessione:
            return
        try:
            limite = int(self.conf().get("session_timeout", 300))
        except (TypeError, ValueError):
            limite = 300
        if limite > 0 and self.inattivita() > limite:
            print("[gb] sessione chiusa dopo %d s senza comandi" % limite)
            self.chiudi_sessione()

    # ------------------------------------------------------------------ tasti

    def premi(self, azione, giu=True, apri=False):
        if azione == "esci":
            if giu:
                self.chiudi_sessione()
            return True
        codice = GB_TASTI.get(azione)
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
        """Premi e rilascia, per i pulsanti della pagina web.

        Un dito che scivola fuori da un pulsante su un telefono non genera
        nessun rilascio, e un tasto rimasto premuto vuol dire un personaggio
        che cammina nel muro finche' non si spegne tutto.
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

    def _dispositivi(self):
        elenco = []
        conf = self.conf()
        if conf.get("keyboard", True):
            scelto = str(conf.get("keyboard_device", "")).strip()
            elenco.extend([scelto] if scelto else tastiere())
        if conf.get("joystick", True):
            scelto = str(conf.get("joystick_device", "")).strip()
            elenco.extend([scelto] if scelto else joystick())
        senza_ripetizioni = []
        for percorso in elenco:
            if percorso not in senza_ripetizioni:
                senza_ripetizioni.append(percorso)
        return senza_ripetizioni

    def pannello_di_altri(self):
        arbitro = self.arbiter
        if arbitro is None:
            return False
        try:
            return bool(arbitro.holding()) and not arbitro.holding(self.name)
        except Exception:
            return False

    def _da_comando(self, azione, giu, avvio):
        """Un comando letto da tastiera o da pad diventa un tasto del Game Boy.

        **Dal pad non si apre mai una sessione.** Vale la regola imparata con
        Doom nella 3.8.2: i lettori ricevono tutti gli stessi eventi, e un
        pulsante che significa due cose diverse per due lettori apre due cose
        insieme. Dalla tastiera si puo', se e' stato chiesto, e mai mentre il
        pannello e' di qualcun altro.
        """
        if avvio or azione not in LINUX_TASTI.values():
            apri = False
        else:
            apri = bool(self.conf().get("keyboard_starts", False))
        if apri and self.pannello_di_altri():
            apri = False
        if not self._sessione and not apri:
            return
        self.premi(azione, giu, apri=apri)
