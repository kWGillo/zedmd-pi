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
        self.luminosita = 100
        self._maschera = None          # (chiave, immagine RGB) in cache
        self._tavola = None            # (luminosita, tabella) in cache
        self._quadro = None            # il fotogramma, riusato
        self.scala, self.riquadro = self._misura()

    # ---- geometria

    def _misura(self):
        """Il moltiplicatore e il riquadro dove finisce la tela.

        Il moltiplicatore e' **intero**: un pixel della tela diventa una
        cella di celle intere, altrimenti i punti del filtro cadrebbero a
        cavallo dei pixel e il reticolo si vedrebbe ondeggiare. Se lo schermo
        e' piu' piccolo della tela -- caso strano ma non impossibile, una
        finestra rimpicciolita a mano -- si rinuncia all'intero e si riduce
        per stare dentro.
        """
        tw, th = self.tela
        sw, sh = self.schermo
        scala = min(sw // tw, sh // th) if tw and th else 0
        if scala >= 1:
            largo, alto = tw * scala, th * scala
        else:
            scala = min(sw / float(tw), sh / float(th))
            largo, alto = max(1, int(tw * scala)), max(1, int(th * scala))
        x = (sw - largo) // 2
        y = (sh - alto) // 2
        return scala, (x, y, largo, alto)

    def ridimensiona(self, schermo):
        """Lo schermo e' cambiato misura: si rifanno i conti e la maschera."""
        self.schermo = tuple(schermo)
        self.scala, self.riquadro = self._misura()
        self._maschera = None
        self._quadro = None

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

    def maschera(self):
        """La maschera di tutto il riquadro, luminosita' inclusa, in cache.

        La luminosita' entra **qui** e non in un secondo passaggio: con il
        filtro acceso diventa una moltiplicazione sola per fotogramma invece
        di due, e il costo di rifarla lo si paga solo quando lo slider si
        muove.
        """
        chiave = (self.scala, self.punto, self.bagliore, self.riquadro[2],
                  self.riquadro[3], self.luminosita)
        if self._maschera and self._maschera[0] == chiave:
            return self._maschera[1]
        _, _, largo, alto = self.riquadro
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
        self._maschera = (chiave, piena)
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

    def componi(self, immagine):
        """Il fotogramma da mandare allo schermo, della sua misura esatta."""
        if immagine.size != self.tela:
            # Difensivo, e nuovo: fino alla 16.5 nessuno controllava la
            # misura di quello che le sorgenti producevano, e un'immagine
            # sbagliata finiva dritta in `SetImage`.
            immagine = immagine.resize(self.tela, Image.NEAREST)
        if immagine.mode != "RGB":
            immagine = immagine.convert("RGB")
        x, y, largo, alto = self.riquadro
        filtro = Image.NEAREST if self.scala >= 1 else Image.BILINEAR
        grande = immagine.resize((largo, alto), filtro)
        if self.filtro:
            # Sul LED la luminosita' e' un registro della matrice. Su un
            # monitor non esiste niente del genere: senza questo, lo slider
            # della pagina e la modalita' notte **fingerebbero** di
            # funzionare. Qui viaggia dentro la maschera.
            grande = ImageChops.multiply(grande, self.maschera())
        elif self.luminosita < 100:
            grande = grande.point(self.tavola())
        if (largo, alto) == self.schermo:
            return grande
        # Il quadro si riusa invece di rifarlo: a 1920x1080 sono sei megabyte
        # per fotogramma, e le bande intorno alla tela non cambiano mai.
        if self._quadro is None or self._quadro.size != self.schermo:
            self._quadro = Image.new("RGB", self.schermo, self.fondo)
        self._quadro.paste(grande, (x, y))
        return self._quadro


# ------------------------------------------------------- le due superfici

class SuperficieSDL:
    """Una finestra, o tutto lo schermo, via SDL.

    SDL copre con la stessa interfaccia i due casi che servono: dentro una
    sessione grafica apre una finestra (ed e' quello che rende provabile il
    resto), senza sessione disegna diretto sul KMS, e allora il programma
    parte dal servizio come ha sempre fatto e sullo schermo c'e' il DMD e
    nient'altro.
    """

    def __init__(self, misura=None, finestra=False, titolo="DMD"):
        import pygame                                   # noqa: F401
        self._pygame = pygame
        if not finestra and not os.environ.get("SDL_VIDEODRIVER"):
            if not (os.environ.get("DISPLAY")
                    or os.environ.get("WAYLAND_DISPLAY")):
                # Nessuna sessione grafica: si va sul KMS. Senza questo SDL
                # proverebbe prima x11, non lo troverebbe, e si fermerebbe.
                os.environ["SDL_VIDEODRIVER"] = "kmsdrm"
        pygame.display.init()
        bandiere = 0 if finestra else pygame.FULLSCREEN
        if not misura and not finestra:
            misura = (0, 0)             # SDL: la risoluzione corrente
        self._schermo = pygame.display.set_mode(misura or (0, 0), bandiere)
        pygame.display.set_caption(titolo)
        try:
            pygame.mouse.set_visible(False)
        except pygame.error:
            pass
        self.width, self.height = self._schermo.get_size()

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

    def __init__(self, misura=None, finestra=False, titolo="DMD"):
        del finestra, titolo
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


def _apri_superficie(misura, finestra):
    """SDL se c'e', framebuffer altrimenti. Con il motivo, se non c'e' niente."""
    motivi = []
    for classe in (SuperficieSDL, SuperficieFramebuffer):
        try:
            return classe(misura=misura, finestra=finestra)
        except Exception as exc:
            motivi.append("%s: %s" % (classe.__name__, exc))
    raise RuntimeError("nessuna uscita video disponibile -- " + "; ".join(motivi))


# ------------------------------------------------------------- le uscite

class DisplaySchermo:
    """La tela su un monitor."""

    def __init__(self, cfg, superficie=None):
        conf = cfg.get("video") or {}
        self.cfg = cfg
        misura = _misura_richiesta(conf.get("risoluzione"))
        finestra = _vuole_finestra(conf.get("finestra"))
        self._superficie = superficie or _apri_superficie(misura, finestra)
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

    def set_brightness(self, value):
        value = max(0, min(100, int(value)))
        with self._lock:
            self.compositore.luminosita = value
        return value

    def show(self, image):
        with self._lock:
            self._superficie.mostra(self.compositore.componi(image))

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

    def __init__(self, cfg, motivo=""):
        self.motivo = motivo or "uscita video non disponibile"
        self.width, self.height = tela_dmd(cfg)
        self.brightness = int((cfg.get("display") or {}).get("brightness", 50))

    def set_brightness(self, value):
        self.brightness = max(0, min(100, int(value)))
        return self.brightness

    def show(self, image):
        pass

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
