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

**Due modi, un solo processo.** Doom in attract mode gioca da solo: e' cio'
che fa da sempre quando nessuno tocca niente, mandando in onda i propri demo.
Li' e' una sorgente come le altre, con priorita' bassa: cede a un aereo, a un
compleanno e soprattutto a Batocera. Quando qualcuno preme un tasto comincia
una **sessione**, e allora il pannello e' suo — stesso meccanismo della
gestione media. Finita la sessione il processo riparte e si torna ai demo, che
e' esattamente come si comporta un cabinato da sala.
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
# struct input_event: due campi di timeval, poi tipo, codice e valore. Le
# dimensioni cambiano fra 32 e 64 bit, e su un Pi capitano entrambe: si
# lasciano calcolare a struct invece di scriverle a mano.
FORMATO_EVENTO = "@llHHi"
DIM_EVENTO = struct.calcsize(FORMATO_EVENTO)


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


def tastiere():
    """I dispositivi di /dev/input che sono davvero tastiere.

    Si legge /proc/bus/input/devices invece di aprire tutto: un mouse o un
    sensore di temperatura hanno anch'essi degli eventi, e aprirli a caso
    vuol dire tenere descrittori inutili su hardware che non c'entra.
    """
    trovate = []
    try:
        with open("/proc/bus/input/devices") as handle:
            testo = handle.read()
    except OSError:
        return trovate
    for blocco in testo.split("\n\n"):
        if "Handlers=" not in blocco:
            continue
        riga = [r for r in blocco.splitlines() if r.startswith("H: Handlers=")]
        if not riga:
            continue
        campi = riga[0].split("=", 1)[1].split()
        if "kbd" not in campi:
            continue
        for campo in campi:
            if campo.startswith("event"):
                trovate.append("/dev/input/" + campo)
    return trovate


class DoomSource(Source):
    name = "doom"
    label = "Doom"
    # Sotto a tutto quello che ha qualcosa da dire: in attract mode Doom e' un
    # riempitivo, e un compleanno o un aereo valgono di piu'. Durante una
    # sessione non e' la priorita' a farlo vincere ma la presa del pannello.
    priority = 40

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

        # Sessione: quando e' aperta i tasti arrivano a Doom e il pannello e'
        # suo. Chiusa, Doom gioca da solo e i tasti si buttano via.
        self._sessione = False
        self._ultimo_tasto = 0.0
        self._premuti = set()

    # ------------------------------------------------------------ ciclo di vita

    def start(self):
        if self._running:
            return
        self._stop.clear()
        self._running = True
        self._errore = ""
        self._avvia_processo()
        if self.cfg["doom"].get("keyboard", True):
            self._tastiera_thread = threading.Thread(
                target=self._leggi_tastiere, name="doom-tastiera", daemon=True)
            self._tastiera_thread.start()

    def stop(self):
        self._running = False
        self._stop.set()
        self.chiudi_sessione(riavvia=False)
        self._ferma_processo()

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
                "--gamma=%.2f" % float(conf.get("gamma", 0.70)),
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
        if not self._running or self._proc is None:
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
        if not self._running:
            return self.t("status.disabled", lang)
        if self._proc is None or self._proc.poll() is not None:
            return self.t("status.doom.stopped", lang)
        if self._sessione:
            return self.t("status.doom.playing", lang,
                          seconds=int(self.inattivita()))
        return self.t("status.doom.attract", lang, frames=self._fotogrammi)

    # ---------------------------------------------------------------- sessione

    def in_sessione(self):
        return self._sessione

    def inattivita(self):
        if not self._ultimo_tasto:
            return 0.0
        return time.time() - self._ultimo_tasto

    def apri_sessione(self):
        """Prende il pannello, entra nel livello e passa i tasti a Doom."""
        if not self._running:
            return False
        self._ultimo_tasto = time.time()
        if self._sessione:
            return True
        # Si riparte dentro il livello invece di aprire il menu: vedi
        # `_comando`. Costa un secondo di nero e non sbaglia mai.
        if not self.riavvia(gioca=True):
            return False
        self._sessione = True
        if self.arbiter is not None:
            # Senza scadenza: chi gioca puo' stare fermo un minuto a guardare
            # una porta senza che il pannello gli torni all'orologio. A
            # chiudere ci pensa il tempo di inattivita', che e' molto piu'
            # lungo, o il pulsante.
            self.arbiter.hold_on(self.name)
        return True

    def chiudi_sessione(self, riavvia=True):
        """Restituisce il pannello e torna ai demo."""
        if not self._sessione:
            return False
        self._sessione = False
        self._premuti.clear()
        if self.arbiter is not None:
            self.arbiter.hold_off(self.name)
        if riavvia and self._running:
            # Ripartire e' l'unico modo onesto di tornare all'attract: Doom
            # resterebbe fermo nel menu o in mezzo a un livello, e un cabinato
            # che mostra una schermata di pausa per ore non e' un attract.
            self.riavvia()
        return True

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

    def premi(self, azione, giu=True):
        """Manda un tasto a Doom. Apre la sessione se non c'e' gia'.

        Premere un tasto mentre Doom gioca da solo *e'* il modo di entrare:
        e' cosi' che si prende in mano un cabinato in sala, senza cercare
        prima un pulsante "gioca".
        """
        codice = DOOM_TASTI.get(azione)
        if codice is None:
            return False
        if not self.apri_sessione():
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
        """Legge le tastiere USB collegate al Pi, senza librerie in piu'.

        `evdev` sarebbe piu' comodo ma e' un pacchetto da installare, e qui
        serve solo leggere una struttura di ventiquattro byte: si fa con
        `struct`, che c'e' sempre.
        """
        aperti = {}
        while self._running and not self._stop.is_set():
            voluti = self._dispositivi()
            for percorso in voluti:
                if percorso in aperti:
                    continue
                try:
                    aperti[percorso] = os.open(percorso, os.O_RDONLY | os.O_NONBLOCK)
                    print("[doom] tastiera: %s" % percorso)
                except OSError:
                    # Una tastiera staccata o senza permessi non e' un guasto:
                    # si riprova al prossimo giro, e intanto resta il web.
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
        scelto = str(self.cfg["doom"].get("keyboard_device", "")).strip()
        if scelto:
            return [scelto]
        return tastiere()

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
            if tipo != EV_KEY:
                continue
            # valore 2 e' la ripetizione automatica del kernel: Doom la sua
            # se la fa da solo, e sommarle vuol dire un personaggio che
            # scatta invece di camminare.
            if valore not in (0, 1):
                continue
            azione = LINUX_TASTI.get(codice)
            if azione:
                self.premi(azione, valore == 1)
