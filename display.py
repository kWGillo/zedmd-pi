"""Dove finisce il disegno: il pannello LED, o un monitor.

Fino alla 16.5 questo file era una cosa sola: il proprietario esclusivo del
pannello LED, perche' un solo processo puo' pilotare i GPIO. Dalla 17.0 e'
il punto dove **la tela incontra l'uscita**, e sono due cose diverse.

La tela e' la misura su cui disegnano le sorgenti. L'uscita e' il pannello o
il monitor. Tenerle separate non e' eleganza: `display.width` e
`display.height` vengono passate a una trentina di sorgenti all'avvio e
congelate la' dentro, e sono **anche** il protocollo ZeDMD -- la larghezza e
l'altezza stanno nell'handshake, e `/get_width` le da' al client su Batocera.
Farle diventare la risoluzione di un monitor, senza altro, romperebbe tre
cose insieme: sorgenti tarate su 256x64 che ricevono una geometria per cui
nessuno le ha disegnate, i giochi, e un client che comincia a trasmettere
fotogrammi della misura sbagliata.

Quindi: `video.tela = "dmd"` tiene la tela a quella del pannello e la
ingrandisce sul monitor, ed e' quello che fa la 17.0. `"schermo"` la fa
diventare quella del monitor, e tocchera' alla 17.1, quando le sorgenti
sapranno starci.

Le due classi espongono la stessa interfaccia, che e' quella che il resto del
programma usava gia': `width`, `height`, `show(image)`, `clear()`,
`set_brightness(value)`. Niente altro, da nessuna parte.
"""

import os
import sys
import threading

from PIL import Image, ImageChops

import piattaforma

# La misura del pannello quando non c'e' un pannello a dirla. Sul LED la
# misura la dice la matrice -- con un pixel mapper il prodotto colonne per
# catena non e' quello che si vede -- ma su un monitor la matrice non esiste,
# e allora la tela DMD si ricava dalla configurazione.
TELA_PREDEFINITA = (256, 64)

# Quante volte ingrandire la tela in modalita' finestra, quando nessuno ha
# chiesto una misura. 256x64 per quattro sta su qualunque schermo e si legge.
FINESTRA_SCALA = 4


def _quante_fasce(scelta):
    """`video.fasce`: "auto" (o vuoto) -> 0, un numero -> quello, al massimo 8."""
    testo = str(scelta if scelta is not None else "").strip().lower()
    if not testo or testo in ("auto", "automatico"):
        return 0
    try:
        return max(1, min(8, int(testo)))
    except ValueError:
        return 0


def tela_dmd(cfg):
    """La misura della tela DMD secondo la configurazione del pannello.

    E' la stessa aritmetica che la libreria matrice fa per conto suo quando
    non ci sono pixel mapper di mezzo, ed e' la misura che il protocollo
    ZeDMD si aspetta.
    """
    panel = cfg.get("panel") or {}
    try:
        largo = int(panel.get("cols", 128)) * int(panel.get("chain", 2))
        alto = int(panel.get("rows", 64)) * int(panel.get("parallel", 1))
    except (TypeError, ValueError):
        return TELA_PREDEFINITA
    if largo < 8 or alto < 8:
        return TELA_PREDEFINITA
    return (largo, alto)


# --------------------------------------------------------- il filtro DMD

class Compositore:
    """Dalla tela al fotogramma da mandare allo schermo.

    Questa classe non parla con nessun dispositivo: prende un'immagine della
    misura della tela e ne torna una della misura dello schermo. E' la parte
    dove stanno i conti -- moltiplicatore, centraggio, punti, luminosita' --
    quindi e' anche la parte che si puo' provare senza un monitor attaccato,
    ed e' per questo che e' separata.

    **Il bagliore sta nella maschera, non in una sfocatura.** La via ovvia
    sarebbe sfocare il fotogramma ingrandito e sommarlo: su 1792x448 sono
    venti millisecondi per fotogramma, e un gioco a trenta fotogrammi al
    secondo li paga tutti. Invece il punto si disegna una volta sola con il
    suo alone -- centro pieno, bordo che sfuma -- e per fotogramma resta una
    moltiplicazione sola. Un punto di un pannello vero e' fatto cosi'
    davvero: un LED dietro un diffusore, non un quadrato.
    """

    def __init__(self, tela, schermo, conf=None):
        self.tela = tuple(tela)
        self.schermo = tuple(schermo)
        conf = conf or {}
        self.filtro = bool(conf.get("filtro_dmd", True))
        self.punto = max(0.1, min(1.0, float(conf.get("filtro_punto", 0.80))))
        self.bagliore = max(0.0, min(1.0, float(conf.get("filtro_bagliore", 0.25))))
        self.fondo = conf.get("filtro_fondo") or "#000000"
        self.volute = 0
        self.luminosita = 100
        self._maschere = {}            # una maschera per misura di regione
        self._tavola = None            # (luminosita, tabella) in cache
        self._quadro = None            # il fotogramma, riusato
        # L'ultimo fotogramma di ogni regione, gia' ingrandito. Serve perche'
        # `frame()` torna None quando l'immagine non e' cambiata: con una
        # sorgente sola voleva dire «non ridisegnare», con due regioni una
        # ferma diventerebbe nera appena l'altra si muove.
        self._ultime_regioni = {}
        self.scala, self.riquadro = self._misura()

    # ---- geometria

    def _misura(self):
        """Il moltiplicatore, quante fasce ci stanno, e dove va la prima.

        Il moltiplicatore e' **intero**: un pixel della tela diventa una
        cella di celle intere, altrimenti i punti del filtro cadrebbero a
        cavallo dei pixel e il reticolo si vedrebbe ondeggiare. Se lo schermo
        e' piu' piccolo della tela -- caso strano ma non impossibile, una
        finestra rimpicciolita a mano -- si rinuncia all'intero e si riduce
        per stare dentro.

        **Le fasce nascono da qui.** La tela e' 4:1 e lo schermo non lo e':
        ingrandendo al massimo restano due bande nere sopra e sotto, e quelle
        bande sono alte un numero esatto di tele. A 1024x768 con scala 4 lo
        schermo e' alto 192 righe logiche, cioe' **tre tele esatte**. Invece
        di lasciarle vuote ci si mettono altre sorgenti.

        Con `fasce` in automatico si prende la scala piu' grande che sta in
        larghezza e si contano le fasce che ne derivano; con un numero si fa
        il contrario, cioe' la scala piu' grande che fa stare quelle fasce.
        Sono le due facce della stessa scelta: fasce grandi o fasce tante.
        """
        tw, th = self.tela
        sw, sh = self.schermo
        if not tw or not th:
            return 0, (0, 0, max(1, sw), max(1, sh))
        if self.volute:
            scala = min(sw // tw, sh // (th * self.volute))
        else:
            scala = min(sw // tw, sh // th)
        if scala >= 1:
            largo, alto = tw * scala, th * scala
            quante = max(1, sh // alto)
            if self.volute:
                quante = min(quante, self.volute)
        else:
            # Non ci sta nemmeno una tela intera: si rinuncia all'intero, si
            # riduce per stare dentro, e di fasce ce n'e' una sola.
            scala = min(sw / float(tw), sh / float(th))
            largo, alto = max(1, int(tw * scala)), max(1, int(th * scala))
            quante = 1
        self.quante = quante
        self.banda = (largo, alto)
        # La **tela logica**: quanti pixel della tela ci stanno sullo schermo
        # intero, non in una fascia. E' il numero su cui l'orologio disegna
        # quando prende tutto: a 1024x768 con scala 4 sono 256x192, cioe' la
        # stessa larghezza del pannello e tre volte le righe. Qui nasce
        # l'orologio grande, e qui resta il filtro DMD -- perche' i pixel
        # logici ci sono ancora, sono solo di piu'.
        if scala >= 1:
            self.tela_logica = (tw, max(th, int(sh // scala)))
        else:
            self.tela_logica = (tw, th)
        # Il bordo nero sopra e sotto, in pixel logici. Solo verticale: in
        # orizzontale la tela logica e' larga esattamente quanto il pannello,
        # e togliere colonne vorrebbe dire che i conti dell'orologio non
        # tornano piu' identici a quelli di sempre.
        self.margine = 4 if self.tela_logica[1] > th else 0
        x = (sw - largo) // 2
        y = (sh - alto) // 2
        return scala, (x, y, largo, alto)

    def regioni(self, con_contenuto=False):
        """I riquadri **logici** dell'orologio e del contenuto.

        Due regioni, non piu' N fasce uguali. Da solo l'orologio prende tutta
        la tela logica meno il bordo: su 1024x768 sono 256x184 pixel logici,
        cioe' cifre tre volte piu' alte di quelle del pannello.

        Quando c'e' qualcos'altro da mostrare, lo schermo si divide a meta':
        l'orologio sale nella meta' di sopra e si rimpicciolisce, e la meta'
        di sotto ospita una sorgente per volta. Una sorgente disegna sempre
        sulla sua tela da 256x64 e li' dentro si centra: non si stira e non
        si ridisegna, perche' quelle misure sono le sue.
        """
        lw, lh = self.tela_logica
        m = self.margine
        if not con_contenuto:
            return {"orologio": (0, m, lw, max(1, lh - 2 * m))}
        meta = lh // 2
        return {"orologio": (0, m, lw, max(1, meta - 2 * m)),
                "contenuto": (0, meta, lw, lh - meta)}

    def ridimensiona(self, schermo):
        """Lo schermo e' cambiato misura: si rifanno i conti e la maschera."""
        self.schermo = tuple(schermo)
        self.scala, self.riquadro = self._misura()
        self._maschere = {}
        self._quadro = None
        self._ultime_regioni = {}

    # ---- la maschera dei punti

    def _cella(self, lato):
        """Una cella sola: il punto con il suo alone, in scala di grigio.

        Il raggio del centro pieno e' `punto` volte il mezzo lato; da li' il
        valore scende fino a zero a `punto + bagliore`. Con bagliore a zero il
        punto ha il bordo netto, che su uno schermo piccolo e' piu' pulito.
        """
        if lato <= 2:
            # Sotto i tre pixel per cella non c'e' spazio per un punto: un
            # reticolo fatto di mezzi pixel e' solo immagine piu' scura.
            return Image.new("L", (lato, lato), 255)
        mezzo = (lato - 1) / 2.0
        meta = lato / 2.0
        pieno = self.punto * meta
        sfuma = (self.punto + self.bagliore) * meta
        cella = Image.new("L", (lato, lato), 0)
        px = cella.load()
        for y in range(lato):
            for x in range(lato):
                # Non la distanza euclidea e non quella di Chebyshev, ma una
                # via di mezzo: un cerchio su una cella da quattro pixel
                # diventa una crocetta, un quadrato non somiglia a un LED.
                # L'esponente quattro da' un quadrato con gli angoli
                # smussati, che e' quello che si vede su un pannello da
                # vicino.
                dx = abs(x - mezzo) / meta
                dy = abs(y - mezzo) / meta
                d = (dx ** 4 + dy ** 4) ** 0.25 * meta
                if d <= pieno:
                    px[x, y] = 255
                elif d >= sfuma or sfuma <= pieno:
                    px[x, y] = 0
                else:
                    quota = 1.0 - (d - pieno) / (sfuma - pieno)
                    px[x, y] = int(round(255 * quota * quota))
        return cella

    def maschera(self, misura=None):
        """La maschera di un riquadro, luminosita' inclusa, in cache.

        La luminosita' entra **qui** e non in un secondo passaggio: con il
        filtro acceso diventa una moltiplicazione sola per fotogramma invece
        di due, e il costo di rifarla lo si paga solo quando lo slider si
        muove.

        Le maschere in cache sono poche -- una per misura di regione -- e le
        misure cambiano solo quando cambia il numero delle regioni, cioe'
        quando arriva o se ne va una sorgente.
        """
        largo, alto = misura or self.banda
        chiave = (self.scala, self.punto, self.bagliore, largo, alto,
                  self.luminosita)
        in_cache = self._maschere.get(chiave)
        if in_cache is not None:
            return in_cache
        lato = int(self.scala) if self.scala >= 1 else 0
        if lato <= 2:
            piena = Image.new("L", (largo, alto), 255)
        else:
            # A mosaico in due passaggi: prima una striscia alta una cella,
            # poi la striscia ripetuta per righe. Su 1792x448 sono trecento
            # incolli invece di sedicimila.
            cella = self._cella(lato)
            striscia = Image.new("L", (largo, lato), 0)
            for x in range(0, largo, lato):
                striscia.paste(cella, (x, 0))
            piena = Image.new("L", (largo, alto), 0)
            for y in range(0, alto, lato):
                piena.paste(striscia, (0, y))
        if self.luminosita < 100:
            quota = max(0, self.luminosita) / 100.0
            piena = piena.point([int(v * quota) for v in range(256)])
        piena = piena.convert("RGB")
        if len(self._maschere) > 8:
            self._maschere.clear()
        self._maschere[chiave] = piena
        return piena

    def tavola(self):
        """La tabella della luminosita', per quando il filtro e' spento."""
        if self._tavola and self._tavola[0] == self.luminosita:
            return self._tavola[1]
        quota = max(0, min(100, self.luminosita)) / 100.0
        tabella = [int(v * quota) for v in range(256)] * 3
        self._tavola = (self.luminosita, tabella)
        return tabella

    # ---- il fotogramma

    def _grande(self, immagine, misura):
        """Una tela portata a una misura in pixel veri, filtro e luce inclusi."""
        largo, alto = misura
        if immagine.mode != "RGB":
            immagine = immagine.convert("RGB")
        filtro = Image.NEAREST if self.scala >= 1 else Image.BILINEAR
        grande = immagine.resize((largo, alto), filtro)
        if self.filtro:
            # Sul LED la luminosita' e' un registro della matrice. Su un
            # monitor non esiste niente del genere: senza questo, lo slider
            # della pagina e la modalita' notte **fingerebbero** di
            # funzionare. Qui viaggia dentro la maschera.
            grande = ImageChops.multiply(grande, self.maschera(misura))
        elif self.luminosita < 100:
            grande = grande.point(self.tavola())
        return grande

    def componi(self, immagine):
        """Una tela sola, centrata e ingrandita del moltiplicatore.

        Accetta **qualunque** tela fino alla tela logica, non solo i 256x64
        del pannello, e questa e' la differenza che fa andare a tutto schermo
        le sorgenti interattive. Una da 256x64 diventa la striscia di sempre;
        una da 256x192 -- la tela logica a 1024x768 -- riempie lo schermo.

        Fino alla 17.2.2 questo metodo riportava tutto a 256x64 prima di
        ingrandire: Doom e il Game Boy, che disegnano la loro immagine, si
        vedevano come una fascia alta un terzo di schermo, cioe' esattamente
        come su un pannello. Era voluto per le sorgenti, che su 256x64 sono
        tarate; per chi la sua immagine se la fa da solo, era uno spreco.
        """
        lw, lh = self.tela_logica
        if immagine.size[0] > lw or immagine.size[1] > lh:
            # Difensivo, e nuovo dalla 17.0: fino alla 16.5 nessuno
            # controllava la misura di quello che le sorgenti producevano, e
            # un'immagine sbagliata finiva dritta in `SetImage`.
            immagine = immagine.resize((min(immagine.size[0], lw),
                                        min(immagine.size[1], lh)),
                                       Image.NEAREST)
        largo = max(1, int(round(immagine.size[0] * self.scala)))
        alto = max(1, int(round(immagine.size[1] * self.scala)))
        grande = self._grande(immagine, (largo, alto))
        if (largo, alto) == self.schermo:
            return grande
        sw, sh = self.schermo
        return self._sfondo_con(((grande, ((sw - largo) // 2,
                                           (sh - alto) // 2)),))

    def componi_regioni(self, pezzi):
        """Lo schermo composto a regioni: l'orologio, e sotto il contenuto.

        `pezzi` e' {nome: (immagine o None, riquadro logico)}. Una immagine a
        `None` vuol dire «non e' cambiato niente» -- e' quello che `frame()`
        risponde quando non c'e' nulla di nuovo -- e allora vale l'ultimo
        fotogramma che quella regione aveva. Senza questa memoria, la meta'
        ferma diventerebbe nera appena l'altra si muove.

        Una tela piu' piccola della sua regione **non si stira**: si centra.
        E' il caso delle sorgenti, che disegnano su 256x64 perche' quelle
        misure sono le loro, dentro una regione alta 96 righe logiche.
        """
        fuori = []
        for nome, (immagine, riquadro) in pezzi.items():
            lx, ly, lw, lh = riquadro
            if immagine is not None:
                tela_w = min(immagine.size[0], lw)
                tela_h = min(immagine.size[1], lh)
                misura = (max(1, int(round(tela_w * self.scala))),
                          max(1, int(round(tela_h * self.scala))))
                dentro = ((lw - tela_w) // 2, (lh - tela_h) // 2)
                self._ultime_regioni[nome] = (
                    self._grande(immagine.crop((0, 0, tela_w, tela_h)), misura),
                    dentro)
            pronta = self._ultime_regioni.get(nome)
            if pronta is None:
                continue
            grande, dentro = pronta
            fuori.append((grande, self._in_pixel(lx + dentro[0], ly + dentro[1])))
        return self._sfondo_con(fuori)

    def _in_pixel(self, lx, ly):
        """Da coordinate logiche a pixel veri, con la tela centrata."""
        sw, sh = self.schermo
        lw, lh = self.tela_logica
        margine_x = (sw - int(lw * self.scala)) // 2
        margine_y = (sh - int(lh * self.scala)) // 2
        return (margine_x + int(round(lx * self.scala)),
                margine_y + int(round(ly * self.scala)))

    def _sfondo_con(self, pezzi):
        """Il quadro dello schermo, con dentro i pezzi gia' ingranditi.

        Il quadro si riusa invece di rifarlo: a 1920x1080 sono sei megabyte
        per fotogramma, e il fondo intorno non cambia mai.
        """
        if self._quadro is None or self._quadro.size != self.schermo:
            self._quadro = Image.new("RGB", self.schermo, self.fondo)
        else:
            self._quadro.paste(self.fondo, (0, 0) + self.schermo)
        for grande, dove in pezzi:
            self._quadro.paste(grande, dove)
        return self._quadro


# ------------------------------------------------------- le due superfici

def zittisci_console(modo="zitta"):
    """Toglie di mezzo la console di testo, sotto il DMD a tutto schermo.

    Il difetto visto sulla 17.1: all'avvio compare per un istante il login di
    Debian, l'orologio torna subito, ma sullo schermo **resta un cursore che
    lampeggia**. Non e' un difetto del disegno: e' che sotto di noi la
    console di testo e' ancora viva.

    Con SDL su KMS prendiamo il controllo della scheda, ma `fbcon` -- la
    console di testo del kernel -- continua a possedere il terminale
    virtuale: quando `getty` si avvia ci scrive sopra il suo prompt (il lampo
    del login), e il suo cursore continua a lampeggiare per conto suo, perche'
    lo disegna il kernel e non noi.

    Due rimedi, in ordine di violenza:

    * **spegnere il cursore** (`cursor_blink`) e il blanking automatico. E'
      poco invasivo e risolve quello che si vede;
    * **staccare `fbcon`** dal framebuffer. Cosi' nessuno puo' piu' scriverci
      sopra, nemmeno `getty`, e il lampo del login non c'e'. Ma la console
      sparisce davvero: se il servizio muore lo schermo resta nero, e per
      capire cosa e' successo serve la pagina web o un'altra macchina. Per
      questo non e' il predefinito.

    Si scrive in `/sys`, quindi serve root -- il servizio gia' ci gira. Se un
    file non c'e' o non si lascia scrivere si tira dritto: questa e' una
    rifinitura, non deve poter impedire al pannello di accendersi.
    """
    if modo in (False, "lascia", "no"):
        # Non toccare niente. E' il comportamento della 17.1, e serve come
        # via d'uscita: se su una macchina il solo fatto di scrivere in
        # `/sys` basta a far riprendere la CRTC a `fbcon`, qui si spegne.
        return []
    stacca = modo in (True, "staccata")
    fatto = []
    for percorso, valore in (
            ("/sys/class/graphics/fbcon/cursor_blink", "0"),
            # Zero spegne il risparmio schermo della console: senza, dopo
            # dieci minuti il kernel spegne il monitor sotto al nostro
            # disegno.
            ("/sys/module/kernel/parameters/consoleblank", "0")):
        try:
            with open(percorso, "w") as f:
                f.write(valore)
            fatto.append(os.path.basename(percorso))
        except OSError:
            pass
    if stacca:
        import glob
        for percorso in sorted(glob.glob("/sys/class/vtconsole/vtcon*/bind")):
            try:
                with open(percorso, "r") as f:
                    if f.read().strip() != "1":
                        continue
                with open(percorso, "w") as f:
                    f.write("0")
                fatto.append("fbcon staccata")
            except OSError:
                pass
    if fatto:
        print("[display] console: %s" % ", ".join(fatto))
    return fatto

SPIE_GUASTO = (
    "could not set videomode",
    "could not queue pageflip",
    "could not create",
    "no usable displays",
)


class _VoceDiSDL:
    """Trattiene quello che SDL scrive sul canale degli errori.

    Serve perche' SDL, sul KMS, **non solleva niente**. Se non riesce a
    impostare il modo sulla CRTC lo scrive e tira dritto: `set_mode()`
    restituisce una superficie regolare, `flip()` non si lamenta, e il
    programma passa mesi convinto di disegnare mentre il vetro e' nero e il
    giornale di bordo si riempie di `Could not queue pageflip: -22`.

    L'unico posto dove quel guasto esiste e' il descrittore 2. Lo si dirotta
    su un file per il tempo dell'apertura e del primo fotogramma, si legge
    che cosa c'e' finito, e poi lo si rimette dov'era -- ristampando le
    righe, che nel giornale di bordo ci vogliono comunque.
    """

    def __init__(self):
        self.testo = ""
        self._copia = None
        self._file = None

    def __enter__(self):
        try:
            import tempfile
            self._file = tempfile.TemporaryFile(mode="w+b")
            sys.stderr.flush()
            self._copia = os.dup(2)
            os.dup2(self._file.fileno(), 2)
        except Exception:
            # Senza cattura si fa come prima: meglio una superficie non
            # controllata che nessuna superficie.
            self._chiudi()
        return self

    def __exit__(self, *_):
        if self._copia is None:
            self._chiudi()
            return False
        try:
            sys.stderr.flush()
            os.dup2(self._copia, 2)
            self._file.seek(0)
            self.testo = self._file.read().decode("utf-8", "replace")
        except Exception:
            self.testo = ""
        finally:
            self._chiudi()
        for riga in self._righe_uniche():
            print(riga, file=sys.stderr)
        return False

    def _chiudi(self):
        for chiudi, oggetto in ((os.close, self._copia), (None, self._file)):
            try:
                if oggetto is None:
                    continue
                chiudi(oggetto) if chiudi else oggetto.close()
            except Exception:
                pass
        self._copia = None
        self._file = None

    def _righe_uniche(self):
        """Le stesse quattro righe ripetute cento volte sono una riga."""
        viste = []
        for riga in self.testo.splitlines():
            riga = riga.rstrip()
            if riga and riga not in viste:
                viste.append(riga)
        return viste

    def guasto(self):
        """La prima riga che dice «non ho disegnato», o stringa vuota."""
        for riga in self._righe_uniche():
            basso = riga.lower()
            for spia in SPIE_GUASTO:
                if spia in basso:
                    return riga.strip()
        return ""


class SuperficieSDL:
    """Una finestra, o tutto lo schermo, via SDL.

    SDL copre con la stessa interfaccia i due casi che servono: dentro una
    sessione grafica apre una finestra (ed e' quello che rende provabile il
    resto), senza sessione disegna diretto sul KMS, e allora il programma
    parte dal servizio come ha sempre fatto e sullo schermo c'e' il DMD e
    nient'altro.
    """

    def __init__(self, misura=None, finestra=False, titolo="DMD",
                 console="zitta"):
        import pygame                                   # noqa: F401
        self._pygame = pygame
        if not finestra and not os.environ.get("SDL_VIDEODRIVER"):
            if not (os.environ.get("DISPLAY")
                    or os.environ.get("WAYLAND_DISPLAY")):
                # Nessuna sessione grafica: si va sul KMS. Senza questo SDL
                # proverebbe prima x11, non lo troverebbe, e si fermerebbe.
                os.environ["SDL_VIDEODRIVER"] = "kmsdrm"
        # **Prima** di impostare il modo video, non dopo.
        #
        # Nella 17.1.1 questa riga stava in fondo al costruttore, e il
        # risultato e' stato uno schermo nero con il giornale pieno di
        # `Could not queue pageflip: -22`. Il motivo: SDL imposta il modo
        # sulla CRTC, poi noi andiamo a toccare `fbcon`, `fbcon` si
        # riprende la CRTC con il **suo** modo, e da quel momento ogni
        # scambio di pagina di SDL viene rifiutato con EINVAL -- il suo
        # framebuffer non corrisponde piu' a quello che la scheda ha
        # impostato. Il programma gira, crede di disegnare, e non si vede
        # niente.
        #
        # L'ordine giusto e' questo: si mette a tacere la console, e poi si
        # prende la scheda. Chi la prende per ultimo la tiene.
        with _VoceDiSDL() as voce:
            if not finestra:
                zittisci_console(console)
            pygame.display.init()
            bandiere = 0 if finestra else pygame.FULLSCREEN
            if not misura and not finestra:
                misura = (0, 0)         # SDL: la risoluzione corrente
            self._schermo = pygame.display.set_mode(misura or (0, 0), bandiere)
            pygame.display.set_caption(titolo)
            try:
                pygame.mouse.set_visible(False)
            except pygame.error:
                pass
            if not finestra:
                self._primo_giro()
        guasto = voce.guasto() if not finestra else ""
        if guasto:
            # Qui si fallisce apposta. `_apri_superficie` ha un'altra strada
            # -- `/dev/fb0` -- e su una macchina dove SDL non riesce a
            # prendere la CRTC quella strada funziona: e' il caso delle
            # macchine virtuali con `virtio_gpu` dove la scheda e' gia' di
            # qualcun altro. Meglio un'uscita senza vsync che un vetro nero.
            self.chiudi()
            raise OSError("SDL non disegna sul KMS -- %s" % guasto)
        self.width, self.height = self._schermo.get_size()

    def _primo_giro(self):
        """Tre fotogrammi neri, per far parlare SDL.

        Il guasto non si vede all'apertura: `set_mode()` riesce comunque, e
        lo scambio di pagina viene tentato solo quando c'e' qualcosa da
        scambiare. Tre giri bastano perche' anche con il triplo buffer il
        primo scambio sia stato chiesto -- e, se viene rifiutato, scritto.
        """
        self._schermo.fill((0, 0, 0))
        for _ in range(3):
            self._pygame.display.flip()

    def mostra(self, immagine):
        # Gli eventi vanno consumati anche se non ce ne importa niente:
        # senza, il gestore delle finestre decide che il programma e'
        # bloccato e lo dice all'utente.
        self._pygame.event.pump()
        tessera = self._pygame.image.frombuffer(
            immagine.tobytes(), immagine.size, "RGB")
        self._schermo.blit(tessera, (0, 0))
        self._pygame.display.flip()

    def chiudi(self):
        try:
            self._pygame.display.quit()
        except Exception:
            pass


class SuperficieFramebuffer:
    """L'ultima spiaggia: si scrive dentro `/dev/fb0`.

    Non serve alcuna libreria, e su una macchina minimale senza SDL e' la
    differenza fra funzionare e non partire. Non c'e' vsync e non c'e'
    finestra: c'e' uno schermo e ci si scrive sopra.
    """

    DISPOSITIVO = "/dev/fb0"
    INFO = "/sys/class/graphics/fb0/"

    def __init__(self, misura=None, finestra=False, titolo="DMD",
                 console="zitta"):
        del finestra, titolo
        zittisci_console(console)
        self.width, self.height = misura or self._misura_dichiarata()
        self._bit = self._bit_dichiarati()
        if self._bit not in (16, 32):
            raise OSError("framebuffer a %d bit per pixel: non so scriverci"
                          % self._bit)
        self._f = open(self.DISPOSITIVO, "r+b", buffering=0)

    def _dichiarato(self, nome):
        with open(os.path.join(self.INFO, nome), encoding="ascii") as f:
            return f.read().strip()

    def _misura_dichiarata(self):
        largo, alto = self._dichiarato("virtual_size").split(",")
        return (int(largo), int(alto))

    def _bit_dichiarati(self):
        try:
            return int(self._dichiarato("bits_per_pixel"))
        except (OSError, ValueError):
            return 32

    def mostra(self, immagine):
        if immagine.size != (self.width, self.height):
            immagine = immagine.resize((self.width, self.height))
        if self._bit == 32:
            # Il framebuffer a 32 bit e' BGRX, non RGBA: i canali vanno
            # scambiati, e il quarto byte resta a zero. PIL sa impacchettarlo
            # da se'.
            dati = immagine.tobytes("raw", "BGRX")
        else:
            # A 16 bit e' RGB565, e qui PIL non ha un impacchettatore: lo si
            # fa a mano con numpy, che fra le dipendenze c'e' gia'.
            import numpy
            a = numpy.asarray(immagine, dtype=numpy.uint16)
            v = (((a[:, :, 0] >> 3) << 11) | ((a[:, :, 1] >> 2) << 5)
                 | (a[:, :, 2] >> 3))
            dati = v.astype("<u2").tobytes()
        self._f.seek(0)
        self._f.write(dati)

    def chiudi(self):
        try:
            self._f.close()
        except Exception:
            pass


def risoluzioni_disponibili(radice="/sys/class/drm"):
    """Le misure che il monitor dichiara, dalla piu' grande alla piu' piccola.

    Non ci vuole SDL e non ci vuole una sessione grafica: il kernel le
    scrive in chiaro, una per riga, nel file `modes` di ogni uscita della
    scheda, e si leggono anche dal servizio.

        /sys/class/drm/card0-HDMI-A-1/status   -> connected
        /sys/class/drm/card0-HDMI-A-1/modes    -> 1920x1080
                                                  1680x1050
                                                  ...

    Si tengono solo le uscite collegate -- su un portatile ce n'e' sempre
    una dozzina censite e una sola attaccata -- e si toglie il doppione
    della stessa misura a frequenze diverse, che a noi non dice niente: il
    programma non sceglie la frequenza, sceglie quanti pixel ha.

    Torna una lista di stringhe `larghezzaxaltezza`. Vuota non e' un
    errore: vuol dire che la macchina non lo dice, e allora la casella si
    riempie a mano come si e' sempre fatto.
    """
    import glob
    import re
    viste = []
    for stato in sorted(glob.glob(os.path.join(radice, "card*-*", "status"))):
        try:
            with open(stato, encoding="ascii") as f:
                if f.read().strip() != "connected":
                    continue
            with open(os.path.join(os.path.dirname(stato), "modes"),
                      encoding="ascii") as f:
                righe = f.read().split()
        except OSError:
            continue
        for riga in righe:
            trovato = re.match(r"^(\d{3,5})x(\d{3,5})", riga)
            if not trovato:
                continue
            misura = "%dx%d" % (int(trovato.group(1)), int(trovato.group(2)))
            if misura not in viste:
                viste.append(misura)
    return sorted(viste, key=lambda m: [-int(n) for n in m.split("x")])


def _apri_superficie(misura, finestra, console="zitta"):
    """SDL se c'e' **e disegna**, framebuffer altrimenti.

    La seconda meta' della frase e' la 17.3.2. Prima bastava che SDL si
    aprisse, e su una macchina dove non riesce a prendere la CRTC si apriva
    benissimo: restava solo da guardare un vetro nero. Ora la superficie si
    rifiuta da sola quando ha visto che non ha disegnato, e la scelta cade
    su `/dev/fb0`, che su quelle stesse macchine funziona.

    Chi ripiega se lo porta scritto addosso (`nota`), perche' la pagina
    Video lo dica invece di lasciar indovinare.
    """
    motivi = []
    for classe in (SuperficieSDL, SuperficieFramebuffer):
        try:
            superficie = classe(misura=misura, finestra=finestra,
                                console=console)
        except Exception as exc:
            motivi.append("%s: %s" % (classe.__name__, exc))
            continue
        superficie.nota = "; ".join(motivi)
        if motivi:
            print("[display] si ripiega su %s -- %s"
                  % (classe.__name__, superficie.nota))
        return superficie
    raise RuntimeError("nessuna uscita video disponibile -- " + "; ".join(motivi))


# ------------------------------------------------------------- le uscite

class DisplaySchermo:
    """La tela su un monitor."""

    def __init__(self, cfg, superficie=None):
        conf = cfg.get("video") or {}
        self.cfg = cfg
        misura = _misura_richiesta(conf.get("risoluzione"))
        finestra = _vuole_finestra(conf.get("finestra"))
        self._superficie = superficie or _apri_superficie(
            misura, finestra, conf.get("console") or "zitta")
        self.motivo = getattr(self._superficie, "nota", "") or ""
        schermo = (self._superficie.width, self._superficie.height)
        if (conf.get("tela") or "dmd") == "schermo":
            tela = schermo
        else:
            tela = tela_dmd(cfg)
        self.width, self.height = tela
        self.compositore = Compositore(tela, schermo, conf)
        self.compositore.luminosita = int(cfg.get("display", {}).get(
            "brightness", 100) or 100)
        self._lock = threading.Lock()
        print("[display] schermo %dx%d, tela %dx%d, scala %s, filtro %s"
              % (schermo[0], schermo[1], tela[0], tela[1],
                 self.compositore.scala,
                 "acceso" if self.compositore.filtro else "spento"))

    @property
    def tela_piena(self):
        """La tela che una sorgente interattiva deve disegnare per riempire.

        Doom, il Game Boy e i giochi non ricevono un'immagine da impaginare:
        la **fanno**, e quanto grande la facciano glielo diciamo noi. Su un
        monitor glielo diciamo grande quanto la tela logica, cosi' vanno a
        tutto schermo invece di restare in una fascia da pannello.
        """
        if ((self.cfg.get("video") or {}).get("modo") or "auto") == "singola":
            return (self.width, self.height)
        return self.compositore.tela_logica

    @property
    def tele(self):
        """Quante tele da pannello ci stanno sullo schermo, una sopra l'altra.

        «singola» ne vuole una sola anche dove ce ne starebbero tre: e' la
        17.0, e resta disponibile perche' un cruscotto non lo vuole per forza
        chiunque abbia un monitor.
        """
        if ((self.cfg.get("video") or {}).get("modo") or "auto") == "singola":
            return 1
        return self.compositore.quante

    def set_brightness(self, value):
        value = max(0, min(100, int(value)))
        with self._lock:
            self.compositore.luminosita = value
        return value

    def show(self, image):
        with self._lock:
            self._superficie.mostra(self.compositore.componi(image))

    def mostra_regioni(self, pezzi):
        """Le due regioni insieme: l'orologio, e sotto il contenuto."""
        with self._lock:
            self._superficie.mostra(self.compositore.componi_regioni(pezzi))

    def regioni(self, con_contenuto=False):
        return self.compositore.regioni(con_contenuto)

    def clear(self):
        with self._lock:
            self._superficie.mostra(
                Image.new("RGB", (self._superficie.width,
                                  self._superficie.height),
                          self.compositore.fondo))


class DisplayLed:
    """Proprietario esclusivo del pannello LED.

    Un solo processo puo' pilotare i GPIO: tutto il rendering passa da qui.
    Le sorgenti non disegnano mai direttamente, producono immagini PIL.
    """

    # Il pannello e' una tela sola: le regioni sono una cosa dello schermo.
    tele = 1

    @property
    def tela_piena(self):
        return (self.width, self.height)

    def __init__(self, cfg):
        panel = cfg["panel"]

        # Il catalogo dei profili di registro va indicato prima di creare la
        # matrice. Vuoto = **libreria standard**, quella di hzeller senza il
        # fork S-PWM: allora non c'e' nessun catalogo da indicare, e scrivere
        # la variabile a vuoto farebbe cercare una cartella che non esiste.
        if (panel.get("profile_dir") or "").strip():
            os.environ["SPWM_PROFILE_DIR"] = panel["profile_dir"]

        # Regolazioni fini del driver S-PWM: la libreria le legge dall'ambiente
        # al momento della creazione della matrice. Un valore vuoto significa
        # "lascia il predefinito", quindi la variabile viene rimossa.
        for name, value in (panel.get("spwm_env") or {}).items():
            text = str(value).strip()
            if text:
                os.environ[name] = text
                print("[display] %s=%s" % (name, text))
            else:
                os.environ.pop(name, None)

        from rgbmatrix import RGBMatrix, RGBMatrixOptions

        options = RGBMatrixOptions()
        options.rows = panel["rows"]
        options.cols = panel["cols"]
        options.chain_length = panel["chain"]
        options.parallel = panel["parallel"]
        options.hardware_mapping = panel["hardware_mapping"]
        options.gpio_slowdown = panel["slowdown"]
        options.panel_type = panel.get("panel_type") or ""
        # I quattro parametri S-PWM esistono **solo** nel fork: con la
        # libreria standard assegnarli farebbe morire il servizio all'avvio,
        # cioe' pannello nero. Si guarda se la libreria li conosce, e se non
        # li conosce si tira dritto -- e' la stessa cautela dei registri
        # forzati, qui applicata a tutto il blocco.
        spwm = hasattr(options, "spwm_row_address_type")
        if spwm:
            options.spwm_row_address_type = panel["spwm_row_address_type"]
            options.spwm_scan_rows = panel["spwm_scan_rows"]
            options.spwm_data_layout = panel["spwm_data_layout"]
            options.spwm_register_config = panel["spwm_register_config"]
        # I parametri dei pannelli classici, quelli a indirizzamento diretto.
        # Si applicano solo se in configurazione c'e' scritto qualcosa: vuoto
        # vuol dire "lascia il predefinito della libreria", che e' quello che
        # vuole chi non sa ancora che pannello ha in mano.
        for chiave, attributo, tipo in (
                ("row_address_type", "row_address_type", int),
                ("multiplexing", "multiplexing", int),
                ("scan_mode", "scan_mode", int),
                ("pixel_mapper", "pixel_mapper_config", str),
                ("led_rgb_sequence", "led_rgb_sequence", str),
                ("disable_hardware_pulsing", "disable_hardware_pulsing", bool)):
            grezzo = panel.get(chiave)
            if grezzo in (None, ""):
                continue
            try:
                valore = bool(grezzo) if tipo is bool else tipo(grezzo)
                setattr(options, attributo, valore)
                print("[display] %s=%s" % (attributo, valore))
            except (AttributeError, TypeError, ValueError):
                print("[display] la libreria non accetta %s" % attributo)
        options.limit_refresh_rate_hz = panel["limit_refresh"]
        options.pwm_bits = panel["pwm_bits"]
        # Le due leve che permettono di tenere la profondita' alta senza
        # pagarla in refresh. Assenti nelle configurazioni precedenti la
        # 1.9.4, da cui i valori predefiniti della libreria.
        options.pwm_lsb_nanoseconds = int(panel.get("pwm_lsb_nanoseconds", 130))
        options.pwm_dither_bits = int(panel.get("pwm_dither_bits", 0))
        # Registri RGB forzati. Facoltativo due volte: puo' mancare nella
        # configurazione, e puo' mancare nella libreria — un fork piu' vecchio
        # non ha la proprieta', e assegnarla farebbe morire il servizio
        # all'avvio, cioe' pannello nero per una funzione che l'utente non ha
        # nemmeno chiesto. Se non c'e', si tira dritto con il profilo.
        registri = str(panel.get("spwm_force_register") or "").strip()
        if registri and spwm:
            try:
                options.spwm_force_register = registri
                print("[display] registri RGB forzati: %s" % registri[:60])
            except AttributeError:
                print("[display] la libreria non accetta registri forzati:"
                      " si usa il profilo %s" % panel["spwm_register_config"])

        options.brightness = cfg["display"]["brightness"]
        options.show_refresh_rate = bool(panel.get("show_refresh", False))
        # Senza questo la libreria perde l'accesso al catalogo profili.
        options.drop_privileges = False

        self.matrix = RGBMatrix(options=options)
        self.canvas = self.matrix.CreateFrameCanvas()
        # La misura la dice la matrice, non la configurazione: con un
        # pixel mapper -- o con una catena disposta in piu' righe -- il
        # prodotto colonne per catena non e' piu' quello che si vede.
        self.width = self.matrix.width
        self.height = self.matrix.height
        self._lock = threading.Lock()

    def set_brightness(self, value):
        value = max(0, min(100, int(value)))
        with self._lock:
            self.matrix.brightness = value
        return value

    def show(self, image):
        """Mostra un'immagine PIL RGB della dimensione del display."""
        with self._lock:
            self.canvas.SetImage(image, 0, 0)
            self.canvas = self.matrix.SwapOnVSync(self.canvas)

    def clear(self):
        with self._lock:
            self.matrix.Clear()


class DisplayAssente:
    """Nessuna uscita video, e il programma va avanti lo stesso.

    Fino alla 16.5, su una macchina senza `rgbmatrix` il costruttore moriva,
    `main()` moriva con lui e systemd riavviava all'infinito: pannello nero,
    **nessuna interfaccia web**, e nessun modo comodo di capire perche'. E'
    lo stesso difetto che l'interfaccia web aveva gia' risolto per conto suo
    -- la' il commento dice «e' un accessorio, se non parte il pannello deve
    comunque accendersi» -- applicato nell'altro verso.

    Non e' un ripiego silenzioso: il motivo si stampa all'avvio e si legge
    nella pagina. Il resto del programma continua -- il radar registra, le
    notifiche arrivano, MQTT parla -- ed e' solo il vetro a non esserci.
    """

    tele = 1

    @property
    def tela_piena(self):
        return (self.width, self.height)

    def __init__(self, cfg, motivo=""):
        self.motivo = motivo or "uscita video non disponibile"
        self.width, self.height = tela_dmd(cfg)
        self.brightness = int((cfg.get("display") or {}).get("brightness", 50))

    def set_brightness(self, value):
        self.brightness = max(0, min(100, int(value)))
        return self.brightness

    def show(self, image):
        pass

    def mostra_regioni(self, pezzi):
        pass

    def regioni(self, con_contenuto=False):
        return {}

    def clear(self):
        pass


# Il nome di prima. Chi importava `Display` da qui continua a trovarlo, e
# quello che trova e' il pannello: era l'unica cosa che potesse essere.
Display = DisplayLed


# ------------------------------------------------------------- la scelta

def _misura_richiesta(testo):
    """"1920x1080" -> (1920, 1080). Vuoto o storto -> None, cioe' "quella che c'e'"."""
    pezzi = str(testo or "").lower().replace(" ", "").split("x")
    if len(pezzi) != 2:
        return None
    try:
        largo, alto = int(pezzi[0]), int(pezzi[1])
    except ValueError:
        return None
    return (largo, alto) if largo >= 64 and alto >= 32 else None


def _vuole_finestra(scelta):
    """La finestra si apre se c'e' una sessione grafica dove metterla."""
    if scelta in (True, "si", "sì", "yes", "1"):
        return True
    if scelta in (False, "no", "0"):
        return False
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def uscita_scelta(cfg):
    """"pannello" o "schermo", con "auto" risolto dalla macchina.

    Il pannello si offre solo su Raspberry Pi 3 e 4, ed e' il motivo per cui
    questa funzione esiste: la scelta "auto" non e' "prova e vedi", e'
    "guarda che macchina sei".
    """
    scelta = ((cfg.get("video") or {}).get("uscita") or "auto").lower()
    if scelta in ("pannello", "led"):
        return "pannello"
    if scelta in ("schermo", "hdmi", "monitor"):
        return "schermo"
    return "pannello" if piattaforma.pannello_possibile() else "schermo"


def crea(cfg):
    """L'uscita video giusta per questa macchina e questa configurazione.

    Se il pannello e' stato chiesto e non si riesce ad accenderlo -- libreria
    assente, GPIO occupati -- **non** si ripiega in silenzio sul monitor: si
    alza l'eccezione. Un pannello che diventa una finestra senza dirlo e' un
    guasto travestito da funzione, e chi guarda il pannello nero non saprebbe
    dove cercare. Chi chiama decide: `dmdd` tiene in piedi l'interfaccia web e
    la' il motivo si legge.
    """
    uscita = uscita_scelta(cfg)
    print("[display] macchina: %s" % piattaforma.riepilogo())
    if uscita == "pannello":
        return DisplayLed(cfg)
    return DisplaySchermo(cfg)
