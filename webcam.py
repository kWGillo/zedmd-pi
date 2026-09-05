# -*- coding: utf-8 -*-
"""La telecamera sul pannello, ridotta a pochi colori.

L'idea: passi davanti alla webcam e ti vedi sul DMD, ridotto a quello che un
computer di quarant'anni fa sapeva mostrare. Non e' un filtro nostalgico
appiccicato sopra — e' quello che questo pannello sa fare davvero.

Quanti colori, e perche' si parte da otto
-----------------------------------------
Sta scritto in `nowplaying.safe_colors`: su questo pannello **le intensita'
intermedie sfarfallano, i colori pieni no**. Ogni componente a 0 o a 255
lascia otto colori, che sono anche la tavolozza dei primi computer a colori:
il vincolo e l'estetica coincidono, e qui si sfrutta invece di combatterlo.

Ma quella regola e' nata disegnando **testo**: lettere chiare su fondo nero,
dove i pochi pixel sfumati del bordo tremano contro uno sfondo fermo, ed e' la
condizione in cui il difetto si vede peggio. Un'immagine di telecamera e'
un'altra cosa: e' fatta *tutta* di mezzi toni, non c'e' nessun bordo netto a
cui confrontarli, e l'occhio legge il tutto come grana. Non e' detto che tremi
allo stesso modo, e non e' una cosa che si possa decidere ragionando.

Per questo i livelli per canale si scelgono: `livelli_colore`, da 2 a 8. Due
sono gli otto pieni, quelli sicuri. Sei danno 216 colori, che e' in pratica la
tavolozza da 256 dell'epoca — non esiste un 256 esatto con tre canali
uniformi, quei 256 erano una tavolozza scelta a mano. Salire non costa niente:
gli stessi byte, lo stesso conto vettoriale, nessun traffico in piu' sul bus.
Costa solo il rischio di sfarfallio, e l'unico modo di saperlo e' guardare il
pannello. Il valore predefinito resta due, perche' un predefinito deve
funzionare senza chiedere niente a nessuno.

Le sfumature che mancano le rimette il **dithering ordinato** di Bayer: una
matrice 4x4 di soglie che alterna i pixel accesi e spenti in un motivo
regolare. Da vicino si vede la trama, da lontano si vedono i mezzitoni. E'
come stampavano i giornali, ed e' come disegnavano i computer a otto colori.

Il costo, e come si tiene basso
-------------------------------
Una telecamera che macina fotogrammi e' precisamente il carico che produce le
righe chiare sul pannello: la campagna di misure ha mostrato 0,95% di frame
disturbati a riposo contro 8,90% con la scheda SD sotto sforzo. Traffico sul
bus di memoria e sulla CPU si pagano in righe luminose.

Tre difese, in ordine di efficacia.

**Non catturare i fotogrammi che non servono.** Si chiede alla telecamera di
produrne pochi — `-framerate` sull'ingresso v4l2 — invece di prenderli tutti
e buttarne via. Un fotogramma scartato dopo la cattura ha gia' attraversato
l'USB e il bus: il risparmio e' solo di CPU. Un fotogramma mai prodotto non
costa niente a nessuno. E' la differenza fra scartare e non chiedere.

**Non decodificare.** Si chiede **YUYV** e non MJPEG: nessuna decodifica
JPEG, nessuna CPU spesa a rimettere insieme immagini che poi comunque si
riducono a 256x64. Il ridimensionamento lo fa ffmpeg, che e' compilato per
farlo, e a Python arrivano gia' i pixel giusti.

**Spegnere quando nessuno guarda.** Se il pannello e' occupato da ZeDMD o da
Doom, la telecamera non serve a nessuno: dopo qualche secondo che nessuno
chiede fotogrammi, la cattura si ferma da sola e riparte quando serve. E'
il risparmio piu' grosso, perche' e' totale.
"""

import os
import shutil
import subprocess
import threading
import time

from PIL import Image

try:
    import numpy as np
except ImportError:                       # pragma: no cover - c'e' sul Pi
    np = None


# La matrice di Bayer 4x4: l'ordine in cui i pixel si accendono quando il
# valore sta a meta' strada. Non e' una sequenza qualsiasi — e' costruita
# perche' le soglie vicine nello spazio siano lontane nel valore, che e' cio'
# che rende la trama regolare invece che sporca.
BAYER = [[0, 8, 2, 10],
         [12, 4, 14, 6],
         [3, 11, 1, 9],
         [15, 7, 13, 5]]

# Le quattro sfumature del Game Boy, dal verde scuro del fosforo spento al
# verde chiaro dello sfondo. Sono i colori dello schermo DMG, non un verde
# scelto a occhio.
GAMEBOY = [(15, 56, 15), (48, 98, 48), (139, 172, 15), (155, 188, 15)]

# Quanti livelli per canale puo' chiedere lo stile a colori, e quanti colori
# vengono fuori: sono livelli**3, perche' le tre componenti sono indipendenti.
#
#   2 ->   8    i colori pieni, quelli che sul pannello non tremano
#   3 ->  27
#   4 ->  64
#   5 -> 125
#   6 -> 216    la tavolozza dei 256 colori dell'epoca, in pratica
#   7 -> 343
#   8 -> 512
#
# Non esiste un 256 esatto con un cubo uniforme: i 256 colori dei computer di
# allora erano una tavolozza scelta a mano, non tre canali indipendenti. 216
# e' il numero vicino piu' onesto, ed e' anche la vecchia "web safe palette",
# nata dallo stesso conto.
LIVELLI_MIN = 2
LIVELLI_MAX = 8

STILI = ("colori", "gameboy", "grigi")

CARTELLA_V4L = "/sys/class/video4linux"

# Dopo quanti secondi senza che nessuno chieda un fotogramma la cattura si
# ferma. Venti secondi: abbastanza da non spegnersi fra una scena e l'altra,
# abbastanza poco da non tenere la telecamera accesa per tutta una partita a
# Doom.
PAUSA_DOPO = 20

# Per quanti secondi l'ultimo fotogramma resta buono dopo che la cattura si e'
# fermata. Serve a due cose opposte. Durante una pausa voluta, tenerlo evita
# che il pannello vada nero nel secondo che ffmpeg impiega a ripartire. Ma se
# la telecamera e' stata **staccata**, un'immagine ferma che resta li' per
# sempre e' peggio del nero: sembra che funzioni, e non e' vero.
VALIDO_PER = 10


def disponibile():
    return shutil.which("ffmpeg") is not None


def _nome(nodo):
    try:
        with open(os.path.join(CARTELLA_V4L, nodo, "name")) as handle:
            return handle.read().strip()
    except OSError:
        return nodo


def dispositivi():
    """Le telecamere collegate: [{"path", "nome"}].

    Una webcam USB non espone **un** `/dev/video`, ne espone due o piu': il
    primo cattura immagini, gli altri portano metadati e non danno un
    fotogramma nemmeno a insistere. Un elenco che li mostrasse tutti
    proporrebbe due voci con lo stesso nome, di cui una non funziona — e chi
    sceglie non ha modo di sapere quale.

    Si raggruppa quindi per dispositivo fisico (il collegamento `device` in
    sysfs punta alla stessa presa USB) e si tiene il nodo di numero piu'
    basso, che per le webcam UVC e' quello di cattura. E' una regola pratica,
    non una garanzia: se la scelta non funziona, la pagina lo dice e si
    prova l'altra.
    """
    try:
        nodi = sorted((n for n in os.listdir(CARTELLA_V4L)
                       if n.startswith("video")),
                      key=lambda n: int(n[5:]) if n[5:].isdigit() else 999)
    except OSError:
        return []

    visti, fuori = {}, []
    for nodo in nodi:
        try:
            gruppo = os.path.realpath(os.path.join(CARTELLA_V4L, nodo, "device"))
        except OSError:
            gruppo = nodo
        if gruppo in visti:
            continue
        visti[gruppo] = nodo
        fuori.append({"path": "/dev/" + nodo, "nome": _nome(nodo)})
    return fuori


def scelto(cfg):
    """Il dispositivo da usare: quello configurato, o il primo che c'e'.

    Un dispositivo configurato ma sparito — la webcam staccata — non fa
    ripiegare in silenzio su un'altra: dire «uso questa invece di quella»
    senza avvisare e' peggio che non partire, perche' poi non si capisce
    perche' l'inquadratura e' cambiata.
    """
    voluto = ((cfg.get("webcam") or {}).get("device") or "").strip()
    presenti = [d["path"] for d in dispositivi()]
    if voluto:
        return voluto if voluto in presenti else ""
    return presenti[0] if presenti else ""


# ------------------------------------------------------------------ tavolozze

def _soglie(altezza, larghezza):
    """La matrice di Bayer stesa sulle dimensioni del pannello, da 0 a 1."""
    piccola = (np.array(BAYER, dtype=np.float32) + 0.5) / 16.0
    ripetuta = np.tile(piccola, (altezza // 4 + 1, larghezza // 4 + 1))
    return ripetuta[:altezza, :larghezza]


def _contrasto(pixel):
    """Allarga la gamma usando il 2% e il 98% dei valori.

    Un soggiorno di sera dalla webcam esce come una poltiglia grigia stretta
    fra 40 e 90: ridotta a otto colori diventa un rettangolo nero. Allargare
    la gamma prima di quantizzare e' cio' che fa la differenza fra
    un'immagine e una macchia.

    I percentili si calcolano su un pixel ogni quattro: la statistica non
    cambia in modo apprezzabile e il conto costa un quarto.
    """
    campione = pixel[::2, ::2].reshape(-1, 3).mean(axis=1)
    basso, alto = np.percentile(campione, (2.0, 98.0))
    if alto - basso < 8:
        return pixel
    scala = 255.0 / (alto - basso)
    return np.clip((pixel.astype(np.float32) - basso) * scala, 0, 255)


def rendi(pixel, stile="colori", livelli=4, contrasto=True, livelli_colore=2):
    """Da fotogramma a immagine per il pannello. `pixel` e' (h, w, 3) uint8.

    `livelli_colore` sono i livelli **per canale** dello stile a colori: due
    danno gli otto colori pieni, sei ne danno 216. `livelli` invece sono le
    sfumature degli stili in verde e in grigio, dove il canale e' uno solo.
    """
    altezza, larghezza = pixel.shape[0], pixel.shape[1]
    soglie = _soglie(altezza, larghezza)
    valori = _contrasto(pixel) if contrasto else pixel.astype(np.float32)

    if stile in ("colori", "otto"):
        # Ogni canale per conto suo. Con due livelli sono tre decisioni
        # acceso/spento per pixel, e vengono fuori gli otto vertici del cubo
        # dei colori: nero, rosso, verde, blu, giallo, ciano, magenta, bianco.
        # Con piu' livelli il cubo si riempie — e il dithering, avendo passi
        # piu' corti da coprire, diventa una trama piu' fine.
        quanti = max(LIVELLI_MIN, min(LIVELLI_MAX, int(livelli_colore)))
        gradini = np.clip(
            np.floor(valori / 255.0 * (quanti - 1) + soglie[:, :, None]),
            0, quanti - 1)
        passo = 255.0 / (quanti - 1)
        return Image.fromarray((gradini * passo).round().astype(np.uint8), "RGB")

    # Gli altri due stili passano dalla luminosita': il colore si butta via
    # prima, non dopo, altrimenti si quantizza tre volte quello che poi
    # diventa un numero solo.
    luce = (valori[:, :, 0] * 0.299 + valori[:, :, 1] * 0.587
            + valori[:, :, 2] * 0.114) / 255.0
    livelli = max(2, min(16, int(livelli)))
    gradino = np.clip(np.floor(luce * (livelli - 1) + soglie), 0, livelli - 1)
    gradino = gradino.astype(np.uint8)

    if stile == "gameboy":
        tavolozza = np.array(GAMEBOY, dtype=np.uint8)
        indice = (gradino.astype(np.float32) * (len(GAMEBOY) - 1)
                  / max(1, livelli - 1)).round().astype(np.uint8)
        return Image.fromarray(tavolozza[indice], "RGB")

    grigio = (gradino.astype(np.float32) * 255.0 / (livelli - 1)).astype(np.uint8)
    return Image.fromarray(np.dstack([grigio] * 3), "RGB")


# -------------------------------------------------------------------- cattura

class Cattura:
    """Tiene acceso ffmpeg e conserva l'ultimo fotogramma grezzo.

    Un oggetto solo, condiviso fra la sorgente che disegna sul pannello e la
    pagina web che scatta le foto: la telecamera e' una sola e non si apre
    due volte.
    """

    def __init__(self, cfg, larghezza, altezza):
        self.cfg = cfg
        self.larghezza = larghezza
        self.altezza = altezza
        self._lucchetto = threading.Lock()
        # Un secondo lucchetto, solo per accensione e spegnimento. Non e'
        # pignoleria: `active()` chiama `avvia` trenta volte al secondo, e se
        # un avvio si mettesse in coda dietro la chiusura del processo
        # precedente bloccherebbe il ciclo che disegna il pannello. Chi trova
        # occupato se ne va e riprova al giro dopo.
        self._avvio = threading.Lock()
        self._prossimo = 0.0         # non riprovare prima di questo istante
        self._attesa = 0.0           # quanto si aspetta al prossimo fallimento
        self._processo = None
        self._thread = None
        self._acceso = False
        self._grezzo = None          # ultimo fotogramma, (h, w, 3) uint8
        self._numero = 0             # cambia a ogni fotogramma nuovo
        self._quando = 0.0           # quando e' arrivato
        self._chiesto = 0.0          # quando qualcuno ha chiesto l'ultima volta
        self._errore = ""
        self._device = ""
        self._registrando = None     # lista dei fotogrammi da salvare in GIF
        self._fino_a = 0.0

    # ------------------------------------------------------------ parametri

    def _conf(self):
        return self.cfg.get("webcam") or {}

    def _comando(self, device):
        conf = self._conf()
        fps = max(1, min(30, int(conf.get("fps", 10) or 10)))
        larghezza = int(conf.get("capture_width", 640) or 640)
        altezza = int(conf.get("capture_height", 480) or 480)

        # La banda centrale, a tutta larghezza. Il pannello e' 4:1: si prende
        # dalla scena una fascia con le stesse proporzioni e la si stende. Il
        # `min` protegge dalle sorgenti gia' piu' larghe che alte, dove la
        # fascia calcolata uscirebbe dall'immagine.
        rapporto = float(self.larghezza) / float(self.altezza)
        fascia = "min(ih\\,iw/%.4f)" % rapporto
        filtri = ["crop=iw:%s:0:(ih-%s)/2" % (fascia, fascia)]
        if conf.get("specchio", True):
            # Ci si aspetta di vedersi come allo specchio: alzando la mano
            # destra si alza la mano a destra sul pannello. Costa zero, e
            # farlo qui evita di ribaltare l'immagine in Python.
            filtri.append("hflip")
        # `area` e non `neighbor`: da 640 a 256 il vicino piu' prossimo
        # produce alias e sfarfallio sui bordi. La grana da otto bit la mette
        # il dithering, non il ridimensionamento fatto male.
        filtri.append("scale=%d:%d:flags=area" % (self.larghezza, self.altezza))

        return ["ffmpeg", "-v", "error", "-nostdin",
                "-f", "v4l2",
                # YUYV e non MJPEG: nessuna decodifica JPEG da pagare.
                "-input_format", "yuyv422",
                "-framerate", str(fps),
                "-video_size", "%dx%d" % (larghezza, altezza),
                "-i", device, "-an",
                "-vf", ",".join(filtri),
                "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]

    # ---------------------------------------------------------------- avvio

    def avvia(self, attendi=True):
        """Accende la cattura. `attendi=False` per chi non puo' bloccarsi.

        Il `/dev/video` si apre una volta sola: se ffmpeg parte mentre quello
        di prima non ha ancora chiuso, il kernel risponde **Device or
        resource busy** e la telecamera resta spenta con un errore che sembra
        un guasto. Era proprio cio' che succedeva spegnendo e riaccendendo il
        servizio dalla pagina: `ferma` faceva partire la chiusura e tornava
        subito, e l'accensione successiva trovava la porta ancora occupata.

        Da qui la regola: accensioni e spegnimenti passano uno per volta da
        `_avvio`, e chi accende aspetta che il ciclo precedente sia finito
        davvero prima di aprire il dispositivo.
        """
        if not self._avvio.acquire(blocking=attendi):
            return False
        try:
            with self._lucchetto:
                if self._acceso:
                    return True
                if time.time() < self._prossimo:
                    return False
                if np is None:
                    self._errore = "numpy non installato"
                    return False
                if not disponibile():
                    self._errore = "ffmpeg non installato"
                    return False
                device = scelto(self.cfg)
                if not device:
                    self._errore = "nessuna telecamera collegata"
                    return False
                vecchio = self._thread

            # Fuori dal lucchetto dei dati: il ciclo che sta chiudendo deve
            # poterlo prendere per scrivere il proprio stato finale.
            if vecchio is not None and vecchio.is_alive():
                vecchio.join(timeout=5)

            with self._lucchetto:
                self._device = device
                self._errore = ""
                self._acceso = True
                self._thread = threading.Thread(target=self._ciclo,
                                                name="webcam",
                                                args=(device,), daemon=True)
                self._thread.start()
            return True
        finally:
            self._avvio.release()

    def _rimanda(self, errore):
        """Segna un fallimento e decide fra quanto vale la pena riprovare.

        Un errore che resta li' per sempre costringerebbe a spegnere e
        riaccendere il servizio a mano per una condizione che quasi sempre
        passa da sola — la telecamera occupata per un istante, il processo di
        prima che non aveva ancora chiuso. Si riprova, ma con attese sempre
        piu' lunghe: se davvero un altro programma tiene la webcam, non ha
        senso bussare ogni secondo per ore.
        """
        with self._lucchetto:
            self._errore = errore
            self._attesa = min(30.0, (self._attesa or 1.5) * 2)
            self._prossimo = time.time() + self._attesa

    def ferma(self):
        with self._avvio:
            with self._lucchetto:
                self._acceso = False
                processo, self._processo = self._processo, None
                thread = self._thread
                # Spegnere a mano azzera l'attesa: la prossima accensione e'
                # una decisione di chi guarda, non un altro tentativo.
                self._attesa = 0.0
                self._prossimo = 0.0
            if processo:
                try:
                    processo.terminate()
                    processo.wait(timeout=3)
                except Exception:
                    try:
                        processo.kill()
                        processo.wait(timeout=2)
                    except Exception:
                        pass
            # Il ciclo deve aver finito **davvero**: finche' e' vivo puo'
            # ancora avere il dispositivo aperto, e la riaccensione
            # troverebbe occupato.
            if thread is not None and thread.is_alive():
                thread.join(timeout=5)

    def _ciclo(self, device):
        byte_per_frame = self.larghezza * self.altezza * 3
        try:
            processo = subprocess.Popen(self._comando(device),
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
        except (OSError, subprocess.SubprocessError) as exc:
            with self._lucchetto:
                self._acceso = False
            self._rimanda(str(exc))
            return

        with self._lucchetto:
            self._processo = processo
            self._chiesto = time.time()

        try:
            while True:
                with self._lucchetto:
                    if not self._acceso:
                        break
                    fermo_da = time.time() - self._chiesto
                if fermo_da > PAUSA_DOPO and not self._registrando:
                    # Nessuno guarda: il pannello e' di qualcun altro. Non ha
                    # senso continuare a muovere l'USB e il bus per immagini
                    # che nessuno vedra'.
                    print("[webcam] nessuno guarda da %ds: cattura in pausa"
                          % int(fermo_da))
                    break
                dati = processo.stdout.read(byte_per_frame)
                if not dati or len(dati) < byte_per_frame:
                    break
                quadro = np.frombuffer(dati, dtype=np.uint8).reshape(
                    self.altezza, self.larghezza, 3)
                with self._lucchetto:
                    self._grezzo = quadro
                    self._numero += 1
                    self._quando = time.time()
                    if self._registrando is not None:
                        if time.time() <= self._fino_a:
                            self._registrando.append(quadro.copy())
                        else:
                            da_salvare, self._registrando = self._registrando, None
                            threading.Thread(target=self._salva_gif,
                                             args=(da_salvare,),
                                             name="webcam-gif",
                                             daemon=True).start()
        except Exception as exc:                        # pragma: no cover
            with self._lucchetto:
                self._errore = str(exc)
        finally:
            errore = b""
            try:
                processo.terminate()
                errore = (processo.stderr.read() or b"")[-400:]
                # Aspettare davvero, non solo chiedere: finche' il processo
                # non e' morto il /dev/video resta suo, e chi riaccende
                # trova occupato.
                processo.wait(timeout=5)
            except Exception:
                try:
                    processo.kill()
                    processo.wait(timeout=2)
                except Exception:
                    pass
            testo = errore.decode("utf-8", "replace").strip()
            with self._lucchetto:
                self._acceso = False
                self._processo = None
                riuscito = self._numero > 0
            if testo:
                self._rimanda(" ".join(testo.split()))
            elif riuscito:
                # Chiusura pulita dopo aver lavorato: nessun errore da
                # ricordare e nessuna attesa da scontare alla riaccensione.
                with self._lucchetto:
                    self._errore = ""
                    self._attesa = 0.0
                    self._prossimo = 0.0

    # ------------------------------------------------------------ lettura

    def fotogramma(self):
        """(numero, array grezzo) o (0, None). Segna che qualcuno sta guardando.

        Chiedere qui e' anche il modo di dire «c'e' qualcuno che guarda»: e'
        questo che tiene sveglia la cattura, e il suo silenzio e' quello che
        dopo `PAUSA_DOPO` secondi la fa spegnere.
        """
        with self._lucchetto:
            self._chiesto = time.time()
            if self._grezzo is None:
                return 0, None
            if (not self._acceso
                    and time.time() - self._quando > VALIDO_PER):
                # Cattura ferma e fotogramma vecchio: la telecamera e' stata
                # staccata, o non riparte. Un'immagine congelata sul pannello
                # sembrerebbe funzionante, ed e' la bugia peggiore.
                return 0, None
            return self._numero, self._grezzo

    def in_pausa(self):
        """Vero se si puo' riaccendere adesso.

        Anche dopo un errore, passata l'attesa: quasi tutti i motivi per cui
        una telecamera non si apre — occupata un istante, staccata e
        riattaccata — passano da soli, e obbligare a spegnere e riaccendere
        il servizio a mano per quelli sarebbe una seccatura inutile.
        """
        with self._lucchetto:
            return not self._acceso and time.time() >= self._prossimo

    def stato(self):
        with self._lucchetto:
            return {"acceso": self._acceso, "errore": self._errore,
                    "device": self._device, "numero": self._numero,
                    "registrando": self._registrando is not None,
                    "riprova_fra": max(0, int(self._prossimo - time.time()))}

    # ---------------------------------------------------------- registrazione

    def _cartella(self):
        """Dove finiscono foto e GIF: dentro la libreria media.

        Cosi' il Media Player le rimette sul pannello da solo, piu' avanti e
        senza che nessuno glielo chieda. Uno scatto di stasera che ricompare
        fra una settimana e' meta' del divertimento.
        """
        conf = self._conf()
        base = ((self.cfg.get("mediaplayer") or {}).get("media_dir")
                or os.environ.get("DMD_DATA") or "/var/lib/dmd")
        cartella = os.path.join(base, conf.get("cartella") or "telecamera")
        os.makedirs(cartella, exist_ok=True)
        return cartella

    def _nome_file(self, estensione):
        return os.path.join(self._cartella(),
                            time.strftime("cam-%Y%m%d-%H%M%S") + estensione)

    def _immagine(self, quadro):
        conf = self._conf()
        return rendi(quadro, conf.get("stile", "colori"),
                     conf.get("livelli_grigio", 4),
                     conf.get("contrasto_auto", True),
                     conf.get("livelli_colore", 2))

    def scatta(self):
        """Salva il fotogramma attuale. Restituisce (percorso, motivo)."""
        _numero, quadro = self.fotogramma()
        if quadro is None:
            return "", "nessun fotogramma disponibile"
        percorso = self._nome_file(".png")
        try:
            self._immagine(quadro).save(percorso)
        except Exception as exc:
            return "", str(exc)
        return percorso, ""

    def registra(self, secondi=None):
        """Comincia a raccogliere fotogrammi per una GIF. (avviato, motivo)."""
        conf = self._conf()
        secondi = float(secondi or conf.get("gif_secondi", 3) or 3)
        secondi = max(1.0, min(15.0, secondi))
        with self._lucchetto:
            if self._registrando is not None:
                return False, "registrazione gia' in corso"
            if not self._acceso:
                return False, "telecamera spenta"
            self._registrando = []
            self._fino_a = time.time() + secondi
        return True, ""

    def _salva_gif(self, quadri):
        if not quadri:
            return
        conf = self._conf()
        fps = max(1, min(30, int(conf.get("fps", 10) or 10)))
        percorso = self._nome_file(".gif")
        try:
            immagini = [self._immagine(q) for q in quadri]
            # In modo P con tavolozza adattiva: con otto colori la tavolozza
            # e' minuscola e la GIF pesa quanto un'icona. In RGB pesarebbe
            # dieci volte tanto per mostrare le stesse otto tinte.
            # La tavolozza si dimensiona su quanti colori lo stile puo'
            # davvero produrre: con due livelli per canale bastano 8 voci,
            # con sei ne servono 216. Chiederne meno del necessario
            # rifarebbe una quantizzazione gia' fatta, e con un criterio
            # diverso: le sfumature appena costruite tornerebbero a fondersi.
            quanti = max(LIVELLI_MIN, min(LIVELLI_MAX,
                                          int(conf.get("livelli_colore", 2))))
            colori = min(256, max(4, quanti ** 3))
            tavolozza = [im.convert("P", palette=Image.ADAPTIVE, colors=colori)
                         for im in immagini]
            tavolozza[0].save(percorso, save_all=True,
                              append_images=tavolozza[1:],
                              duration=int(1000.0 / fps), loop=0, optimize=True)
            print("[webcam] salvata %s (%d fotogrammi)" % (percorso, len(quadri)))
        except Exception as exc:                        # pragma: no cover
            print("[webcam] GIF non salvata: %s" % exc)


def elenco_scatti(cfg, quanti=24):
    """Gli ultimi file salvati, dal piu' recente. Per la pagina."""
    base = ((cfg.get("mediaplayer") or {}).get("media_dir")
            or os.environ.get("DMD_DATA") or "/var/lib/dmd")
    cartella = os.path.join(base, (cfg.get("webcam") or {}).get("cartella")
                            or "telecamera")
    try:
        nomi = [n for n in os.listdir(cartella)
                if n.lower().endswith((".png", ".gif"))]
    except OSError:
        return []
    nomi.sort(reverse=True)
    return [{"nome": n, "percorso": os.path.join(cartella, n)}
            for n in nomi[:quanti]]
