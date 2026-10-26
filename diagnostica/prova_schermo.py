# -*- coding: utf-8 -*-
"""17.0 - La tela su un monitor: moltiplicatore, centraggio, filtro DMD.

Cosa prova questo file
----------------------
Il pezzo di `display.py` che fa i conti -- `Compositore` -- e non quello che
parla con il dispositivo. E' una divisione voluta: una finestra SDL o un
`/dev/fb0` non si possono aprire su una macchina di sviluppo, ma il
moltiplicatore, il centraggio, la maschera dei punti e la luminosita' in
software si possono provare tutti, e sono il posto dove i difetti vivono.

Le cose su cui insiste
----------------------
* **il moltiplicatore e' intero.** Se la tela viene ingrandita di 7,3 volte i
  punti del filtro cadono a cavallo dei pixel e il reticolo si vede
  ondeggiare. Intero, e il piu' grande che sta dentro;
* **la tela e' centrata**, e quello che resta fuori e' il colore di fondo:
  sono le «aree non usate» accettate per scelta, non un errore di conto;
* **la luminosita' su un monitor deve fare qualcosa.** Sul LED e' un registro
  della matrice; su HDMI non esiste niente del genere, e senza la
  moltiplicazione in software lo slider della pagina e la modalita' notte
  fingerebbero di funzionare. Questa prova guarda che un fotogramma a
  luminosita' 25 sia piu' scuro dello stesso a 100;
* **il filtro spegne dei pixel ma non ne accende nessuno.** Un punto con
  l'alone puo' solo togliere luce dentro la sua cella: se da qualche parte
  il filtro acceso e' piu' luminoso di quello spento, la maschera e'
  sbagliata;
* **niente esce dal riquadro.** Su una tela nera con un pixel acceso in un
  angolo, quel pixel deve finire dentro la sua cella e da nessun'altra parte.
"""

import os
import sys
import tempfile
import time

os.environ.setdefault("DMD_DATA", tempfile.mkdtemp())
os.environ.setdefault("DMD_CONFIG", os.path.join(tempfile.mkdtemp(), "config.json"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image

import display
import dmdconf
import piattaforma

# Le sei misure su cui si guarda tutto: il pannello, un 4:3, tre 16:9 di
# taglie diverse, un 16:10 e un 21:9.
MISURE = [(256, 64), (640, 480), (1280, 720), (1920, 1080), (1920, 1200),
          (2560, 1080)]
TELA = (256, 64)

esiti = []


def esigi(condizione, messaggio):
    esiti.append((bool(condizione), messaggio))
    print("%s %s" % ("OK  " if condizione else "FALLITO", messaggio))


def sep(titolo):
    print()
    print("=" * 74)
    print(titolo)
    print("=" * 74)


def tela_di_prova(misura=TELA):
    """Una tela riconoscibile: angoli accesi, una riga e una colonna."""
    im = Image.new("RGB", misura, (0, 0, 0))
    px = im.load()
    w, h = misura
    for x, y, colore in ((0, 0, (255, 0, 0)), (w - 1, 0, (0, 255, 0)),
                         (0, h - 1, (0, 0, 255)), (w - 1, h - 1, (255, 255, 255))):
        px[x, y] = colore
    for x in range(w):
        px[x, h // 2] = (200, 200, 200)
    return im


def luce(immagine):
    """La luce totale del fotogramma: la somma di tutti i canali."""
    return sum(sum(banda.histogram()[i] * i for i in range(256))
               for banda in immagine.split())


sep("1. Il moltiplicatore e' intero e il piu' grande che si puo' permettere")

# La 17.4.10 aveva provato a prendere una scala **piu' piccola** della
# massima, per far stare due tele intere in altezza su uno schermo 21:9.
# Funzionava, ma lasciava due bande nere ai lati larghe un quinto dello
# schermo. La 17.4.11 era tornata alla scala massima -- la larghezza si
# prende tutta -- risolvendo dall'altra parte: spartendo diversamente le
# righe fra le due regioni.
#
# La 17.4.13 concede **un** passo indietro, e solo quando serve davvero:
# se dalla scala massima viene fuori una regione d'orologio troppo bassa
# perche' i testi piccoli si leggano, si scende di scala finche' la
# larghezza non costa troppo. Su un 2560x1080 fa scala 9 invece di 10 --
# 2304 pixel invece di 2560, due bande da 128 -- e la regione
# dell'orologio passa da 36 righe logiche a 48.

ATTESE_SCALA = {(2560, 1080): 9}

for misura in MISURE:
    c = display.Compositore(TELA, misura)
    x, y, largo, alto = c.riquadro
    atteso = ATTESE_SCALA.get(
        misura, min(misura[0] // TELA[0], misura[1] // TELA[1]))
    esigi(c.scala == atteso,
          "%dx%d: scala %s, attesa %d" % (misura[0], misura[1], c.scala, atteso))
    esigi(largo == TELA[0] * atteso and alto == TELA[1] * atteso,
          "   e il riquadro e' %dx%d" % (largo, alto))
    esigi(0 <= x and 0 <= y and x + largo <= misura[0] and y + alto <= misura[1],
          "   e sta dentro lo schermo, a (%d, %d)" % (x, y))
    esigi(abs((misura[0] - largo) - 2 * x) <= 1
          and abs((misura[1] - alto) - 2 * y) <= 1,
          "   centrato, con le bande uguali")
    # E la prova che conta, quella che nasce dallo schermo 21:9: su
    # qualunque monitor le due regioni si devono poter fare, e il contenuto
    # deve ricevere **almeno** la sua tela da 64 righe -- se no una sorgente
    # non ci sta e viene tagliata.
    if misura[1] >= 2 * TELA[1] and misura[0] >= TELA[0]:
        r = c.regioni(True)
        esigi(c.due_regioni,
              "   e le due regioni si possono fare (%d righe logiche)"
              % c.tela_logica[1])
        esigi(r["contenuto"][3] >= TELA[1],
              "   con almeno %d righe al contenuto (ne ha %d)"
              % (TELA[1], r["contenuto"][3]))
        esigi(r["orologio"][3] >= 24,
              "   e abbastanza all'orologio (%d righe)" % r["orologio"][3])

c = display.Compositore(TELA, (1920, 1080))
# Il vincolo e' la larghezza, non l'altezza: 1920 / 256 fa sette e mezzo, e
# 1080 / 64 ne farebbe sedici. Comanda il piu' stretto dei due.
esigi(c.scala == 7, "su 1920x1080 la tela ci sta sette volte (%s)" % c.scala)
esigi(c.riquadro == (64, 316, 1792, 448),
      "cioe' 1792x448, con 64 colonne di banda ai lati e 316 righe sopra e "
      "sotto (%s)" % (c.riquadro,))


sep("2. Lo schermo piu' piccolo della tela non scoppia")

c = display.Compositore(TELA, (200, 50))
esigi(c.scala < 1, "si rinuncia all'intero (%.3f)" % c.scala)
fuori = c.componi(tela_di_prova())
esigi(fuori.size == (200, 50), "e il fotogramma e' comunque 200x50")


sep("3. Il fotogramma ha la misura dello schermo, sempre")

for misura in MISURE:
    c = display.Compositore(TELA, misura)
    esigi(c.componi(tela_di_prova()).size == misura,
          "%dx%d" % misura)


sep("4. Il filtro toglie luce, non ne aggiunge")

for misura in ((1280, 720), (1920, 1080)):
    acceso = display.Compositore(TELA, misura, {"filtro_dmd": True})
    spento = display.Compositore(TELA, misura, {"filtro_dmd": False})
    tela = tela_di_prova()
    a = acceso.componi(tela).copy()
    s = spento.componi(tela).copy()
    esigi(luce(a) < luce(s),
          "%dx%d: con il filtro il fotogramma e' piu' scuro (%d contro %d)"
          % (misura[0], misura[1], luce(a), luce(s)))
    piu_chiaro = [1 for pa, ps in zip(a.getdata(), s.getdata())
                  if pa[0] > ps[0] or pa[1] > ps[1] or pa[2] > ps[2]]
    esigi(not piu_chiaro,
          "   e non c'e' un solo pixel che il filtro abbia schiarito")


sep("5. Un pixel acceso finisce nella sua cella e da nessun'altra parte")

c = display.Compositore(TELA, (1280, 720), {"filtro_dmd": True})
x0, y0, _largo, _alto = c.riquadro
lato = int(c.scala)
tela = Image.new("RGB", TELA, (0, 0, 0))
tela.load()[3, 2] = (255, 255, 255)
fuori = c.componi(tela).copy()
dentro = fuori.crop((x0 + 3 * lato, y0 + 2 * lato,
                     x0 + 4 * lato, y0 + 3 * lato))
esigi(luce(dentro) > 0, "la cella del pixel e' accesa")
esigi(luce(dentro) == luce(fuori),
      "e tutta la luce del fotogramma sta la' dentro (%d di %d)"
      % (luce(dentro), luce(fuori)))

bordo = fuori.crop((x0 + 3 * lato, y0 + 2 * lato, x0 + 4 * lato, y0 + 3 * lato))
angoli = [bordo.getpixel((0, 0)), bordo.getpixel((lato - 1, 0)),
          bordo.getpixel((0, lato - 1)), bordo.getpixel((lato - 1, lato - 1))]
esigi(all(sum(a) < 255 * 3 for a in angoli),
      "gli angoli della cella sono smussati, non e' un quadrato pieno")


sep("6. La luminosita' su un monitor fa qualcosa")

for filtro in (True, False):
    c = display.Compositore(TELA, (1280, 720), {"filtro_dmd": filtro})
    tela = tela_di_prova()
    c.luminosita = 100
    piena = luce(c.componi(tela).copy())
    c.luminosita = 25
    bassa = luce(c.componi(tela).copy())
    c.luminosita = 0
    spenta = luce(c.componi(tela).copy())
    nome = "con il filtro" if filtro else "senza filtro"
    esigi(bassa < piena, "%s: a 25 e' piu' scuro che a 100 (%d < %d)"
          % (nome, bassa, piena))
    esigi(0.15 < bassa / float(piena) < 0.35,
          "   e la proporzione e' quella di un quarto (%.2f)"
          % (bassa / float(piena)))
    esigi(spenta == 0, "   e a zero il vetro e' nero")


sep("7. La tela che arriva della misura sbagliata non fa danni")

c = display.Compositore(TELA, (1280, 720))
esigi(c.componi(Image.new("RGB", (128, 32), (255, 255, 255))).size == (1280, 720),
      "una tela piu' piccola del dovuto si adatta invece di scoppiare")
esigi(c.componi(Image.new("L", TELA, 200)).size == (1280, 720),
      "e una tela in scala di grigio si converte")


sep("8. La maschera si rifa' solo quando serve")

c = display.Compositore(TELA, (1280, 720), {"filtro_dmd": True})
prima = c.maschera()
esigi(c.maschera() is prima, "due chiamate di fila danno la stessa maschera")
c.luminosita = 40
esigi(c.maschera() is not prima, "cambiata la luminosita', si rifa'")
c.ridimensiona((1920, 1080))
esigi(c.scala == 7 and c.riquadro[2] == 1792,
      "e ridimensionando lo schermo si rifanno i conti (%s)" % (c.riquadro,))


sep("9. La tela DMD si ricava dal pannello, non da un numero scritto a mano")

cfg = dmdconf.load()
esigi(display.tela_dmd(cfg) == (256, 64),
      "128 colonne per 2 in catena, 64 righe: 256x64 (%s)"
      % (display.tela_dmd(cfg),))
esigi(display.tela_dmd({"panel": {"cols": 64, "chain": 1, "rows": 32,
                                  "parallel": 1}}) == (64, 32),
      "un pannello solo da 64x32 da' 64x32")
esigi(display.tela_dmd({}) == display.TELA_PREDEFINITA,
      "e senza sezione panel si torna alla misura predefinita")
esigi(display.tela_dmd({"panel": {"cols": "x", "chain": 2}})
      == display.TELA_PREDEFINITA,
      "come con numeri che non sono numeri")


sep("10. Quale uscita, su quale macchina")

cfg["video"]["uscita"] = "auto"
piattaforma._forza({"famiglia": "raspberry", "modello": "Raspberry Pi 4",
                    "numero": "4", "pannello": True})
esigi(display.uscita_scelta(cfg) == "pannello",
      "auto su un Pi 4: pannello")
piattaforma._forza({"famiglia": "raspberry", "modello": "Raspberry Pi 5",
                    "numero": "5", "pannello": False})
esigi(display.uscita_scelta(cfg) == "schermo",
      "auto su un Pi 5: schermo, perche' la libreria non pilota l'RP1")
piattaforma._forza({"famiglia": "pc", "modello": "PC", "numero": "",
                    "pannello": False})
esigi(display.uscita_scelta(cfg) == "schermo", "auto su un PC: schermo")
cfg["video"]["uscita"] = "pannello"
esigi(display.uscita_scelta(cfg) == "pannello",
      "ma la scelta a mano vince sulla macchina")
cfg["video"]["uscita"] = "schermo"
piattaforma._forza({"famiglia": "raspberry", "modello": "Raspberry Pi 4",
                    "numero": "4", "pannello": True})
esigi(display.uscita_scelta(cfg) == "schermo",
      "e su un Pi 4 si puo' chiedere il monitor: e' il caso da scrivania")


sep("11. Risoluzione e finestra, come si leggono")

esigi(display._misura_richiesta("1920x1080") == (1920, 1080), "1920x1080")
esigi(display._misura_richiesta(" 1280 X 720 ") == (1280, 720),
      "con gli spazi e la X grande")
for storto in ("", None, "grande", "1920", "1920x1080x3", "10x10"):
    esigi(display._misura_richiesta(storto) is None,
          "%r non e' una risoluzione, quindi vale quella che c'e'" % (storto,))

vecchio = {k: os.environ.pop(k, None) for k in ("DISPLAY", "WAYLAND_DISPLAY")}
try:
    esigi(display._vuole_finestra("auto") is False,
          "auto senza sessione grafica: tutto schermo")
    os.environ["DISPLAY"] = ":0"
    esigi(display._vuole_finestra("auto") is True,
          "auto con una sessione: finestra")
    esigi(display._vuole_finestra("no") is False, "e il no vince sempre")
    esigi(display._vuole_finestra("si") is True, "come il si")
finally:
    os.environ.pop("DISPLAY", None)
    for k, v in vecchio.items():
        if v is not None:
            os.environ[k] = v


sep("12. Il display su schermo, con una superficie finta")

class Finta:
    def __init__(self, largo, alto):
        self.width, self.height = largo, alto
        self.visti = []

    def mostra(self, immagine):
        self.visti.append(immagine.copy())


cfg["video"]["uscita"] = "schermo"
cfg["video"]["tela"] = "dmd"
finta = Finta(1920, 1080)
d = display.DisplaySchermo(cfg, superficie=finta)
esigi((d.width, d.height) == (256, 64),
      "con tela dmd le sorgenti vedono 256x64 (%dx%d)" % (d.width, d.height))
d.show(tela_di_prova())
esigi(len(finta.visti) == 1 and finta.visti[0].size == (1920, 1080),
      "e sullo schermo finisce un fotogramma 1920x1080")
esigi(d.set_brightness(130) == 100 and d.set_brightness(-5) == 0,
      "la luminosita' si tiene fra zero e cento")
d.clear()
esigi(luce(finta.visti[-1]) == 0, "e clear() lascia il vetro nero")

cfg["video"]["tela"] = "schermo"
finta2 = Finta(1920, 1080)
d2 = display.DisplaySchermo(cfg, superficie=finta2)
esigi((d2.width, d2.height) == (1920, 1080),
      "con tela schermo le sorgenti vedono il monitor (%dx%d)"
      % (d2.width, d2.height))
cfg["video"]["tela"] = "dmd"


sep("13. I giochi restano 256x64, ingranditi di un intero")

from sources.giochi import GiochiSource          # noqa: E402

base = Image.new("RGB", (256, 64), (10, 10, 10))
base.load()[0, 0] = (255, 0, 0)
base.load()[255, 63] = (0, 255, 0)

g = GiochiSource(cfg, 256, 64)
esigi(g._alla_tela(base) is base,
      "sul pannello il fotogramma passa intatto, senza nemmeno una copia")

g = GiochiSource(cfg, 1280, 720)
fuori = g._alla_tela(base)
esigi(fuori.size == (1280, 720), "su 1280x720 il fotogramma e' 1280x720")
esigi(fuori.getpixel((2, 200)) == (255, 0, 0)
      and fuori.getpixel((1277, 519)) == (0, 255, 0),
      "gli angoli del gioco sono agli angoli del riquadro, scala 5")
esigi(fuori.getpixel((640, 10)) == (0, 0, 0)
      and fuori.getpixel((640, 710)) == (0, 0, 0),
      "e sopra e sotto c'e' il nero: sono le aree non usate, per scelta")

for misura in MISURE[1:]:
    g = GiochiSource(cfg, misura[0], misura[1])
    fuori = g._alla_tela(base)
    scala = min(misura[0] // 256, misura[1] // 64)
    dentro = fuori.getbbox()
    esigi(fuori.size == misura and dentro is not None
          and (dentro[2] - dentro[0]) == 256 * scala,
          "%dx%d: scala %d, riquadro largo %d"
          % (misura[0], misura[1], scala,
             (dentro[2] - dentro[0]) if dentro else 0))

cfg["video"]["scala_giochi"] = "pieno"
g = GiochiSource(cfg, 1280, 720)
fuori = g._alla_tela(base)
esigi(fuori.getpixel((2, 2)) == (255, 0, 0)
      and fuori.getpixel((1277, 717)) == (0, 255, 0),
      "con scala_giochi=pieno il gioco occupa tutta la tela")
cfg["video"]["scala_giochi"] = "intera"

g = GiochiSource(cfg, 200, 50)
esigi(g._alla_tela(base).size == (200, 50),
      "e una tela piu' piccola della base non scoppia")


# ------------------------------------------------- 17.3.2: SDL che non disegna
#
# Il guasto vero, quello che ha tenuto il vetro nero per tre versioni: SDL
# sul KMS non solleva niente. Stampa `Could not set videomode on CRTC`, poi
# `Could not queue pageflip: -22` venti volte al secondo, e intanto
# `set_mode()` ha restituito una superficie come se niente fosse.
#
# Si prova senza SDL e senza framebuffer, sostituendo le due classi di
# `display`: quello che conta e' la **scelta**, e la scelta la fa
# `_apri_superficie` guardando il canale degli errori.

print()
print("-- SDL che dice di disegnare e non disegna (17.3.2)")

voce = display._VoceDiSDL()
with voce:
    os.write(2, b"ERROR: Could not set videomode on CRTC.\n")
    for _ in range(40):
        os.write(2, b"ERROR: Could not queue pageflip: -22\n")
esigi(voce.guasto() == "ERROR: Could not set videomode on CRTC.",
      "la prima riga che dice «non ho disegnato» viene riconosciuta")
esigi(len(voce._righe_uniche()) == 2,
      "quarantuno righe ripetute diventano due nel giornale di bordo")

voce = display._VoceDiSDL()
with voce:
    os.write(2, b"Hello from the pygame community.\n")
esigi(voce.guasto() == "", "e il saluto di pygame non e' un guasto")

sdl_vero, fb_vero = display.SuperficieSDL, display.SuperficieFramebuffer
aperte = []


class SdlCheNonDisegna:
    def __init__(self, misura=None, finestra=False, titolo="", console=""):
        aperte.append("sdl")
        with display._VoceDiSDL() as v:
            os.write(2, b"ERROR: Could not queue pageflip: -22\n")
        raise OSError("SDL non disegna sul KMS -- %s" % v.guasto())


class FbCheDisegna:
    def __init__(self, misura=None, finestra=False, titolo="", console=""):
        aperte.append("fb")
        self.width, self.height = misura or (1024, 768)


try:
    display.SuperficieSDL = SdlCheNonDisegna
    display.SuperficieFramebuffer = FbCheDisegna
    scelta = display._apri_superficie((1024, 768), False, "zitta")
    esigi(aperte == ["sdl", "fb"],
          "SDL si prova per primo, e quando si rifiuta si passa al framebuffer")
    esigi(isinstance(scelta, FbCheDisegna),
          "la superficie che torna e' quella che disegna davvero")
    esigi("pageflip" in getattr(scelta, "nota", ""),
          "e si porta scritto addosso perche' si e' ripiegato")

    del aperte[:]
    display.SuperficieSDL = FbCheDisegna
    scelta = display._apri_superficie((1024, 768), False, "zitta")
    esigi(len(aperte) == 1 and scelta.nota == "",
          "quando la prima superficie disegna, la seconda non si apre nemmeno")
finally:
    display.SuperficieSDL, display.SuperficieFramebuffer = sdl_vero, fb_vero


# --------------------------------- 17.3.3: le misure che dichiara il monitor
#
# Si leggono da `/sys/class/drm`, che qui si finge: una scheda con due
# uscite, una collegata e una no, e la stessa misura ripetuta a frequenze
# diverse -- com'e' fatto un file `modes` vero.

print()
print("-- le risoluzioni si leggono dal monitor (17.3.3)")

finto = tempfile.mkdtemp()


def _uscita(nome, stato, modi):
    cartella = os.path.join(finto, nome)
    os.makedirs(cartella)
    with open(os.path.join(cartella, "status"), "w") as f:
        f.write(stato + "\n")
    with open(os.path.join(cartella, "modes"), "w") as f:
        f.write("\n".join(modi) + "\n")


_uscita("card0-Virtual-1", "connected",
        ["1920x1080", "1920x1080", "1280x1024", "1024x768", "800x600"])
_uscita("card0-HDMI-A-2", "disconnected", ["3840x2160"])
_uscita("card0-DP-1", "connected", ["2560x1440", "1920x1080"])

viste = display.risoluzioni_disponibili(finto)
esigi(viste == ["2560x1440", "1920x1080", "1280x1024", "1024x768", "800x600"],
      "le misure tornano dalla piu' grande alla piu' piccola: %s"
      % ", ".join(viste))
esigi("3840x2160" not in viste,
      "l'uscita non collegata non porta la sua misura")
esigi(viste.count("1920x1080") == 1,
      "la stessa misura a frequenze diverse conta una volta sola")
esigi(display.risoluzioni_disponibili(os.path.join(finto, "niente")) == [],
      "e dove non c'e' niente da leggere torna una lista vuota, non un errore")


print()
print("-- e nel menu si vedono tutte, anche con una gia' scelta (17.4.15)")

# *«Dopo aver selezionato una risoluzione, se apro il menu a tendina non
# vedo nulla al di fuori di quella attiva: devo cancellare il testo per
# vedere le altre.»* Era una casella di testo con un `datalist`, e un
# `datalist` **filtra** i suggerimenti con quello che c'e' gia' scritto:
# con «2560x1080» nella casella l'unico suggerimento che corrisponde e'
# 2560x1080, e il menu si apriva praticamente vuoto. Adesso e' un elenco
# vero.

import re                                                  # noqa: E402

from jinja2 import Environment                             # noqa: E402

MODELLO = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "templates", "video.html")
pagina = open(MODELLO, encoding="utf-8").read()
inizio = pagina.index('<label for="risoluzione">')
frammento = pagina[inizio:pagina.index("</label>", pagina.index(
    '<input type="text" id="risoluzione"')) + len("</label>")]

esigi("<datalist" not in frammento and 'list="' not in frammento,
      "il `datalist` non c'e' piu' (il commento che lo nomina si', ed e'"
      " giusto cosi': spiega perche')")


class Finta(dict):
    def __getattr__(self, chiave):
        return self.get(chiave, "")


def rendi(scelta, modi):
    html = Environment().from_string(frammento).render(
        cfg=Finta(video=Finta(risoluzione=scelta)),
        t=lambda chiave, **valori: chiave, risoluzioni=modi)
    return (re.findall(r'<option value="([^"]*)"', html),
            re.findall(r'value="([^"]*)"[^>]*selected', html),
            "<input" in html)

MODI = ["2560x1080", "1920x1080", "1600x900"]
opzioni, scelte, casella = rendi("2560x1080", MODI)
esigi(all(m in opzioni for m in MODI),
      "con una risoluzione impostata si vedono **tutte** le altre: %s"
      % ", ".join(o or "(auto)" for o in opzioni))
esigi(scelte == ["2560x1080"], "e quella attiva risulta selezionata")
esigi(opzioni[0] == "" and not casella,
      "la prima voce e' «automatica», cioe' la casella vuota di sempre")

opzioni, scelte, _ = rendi("", MODI)
esigi(scelte == [""], "senza niente scelto e' selezionata «automatica»")

opzioni, scelte, _ = rendi("1280x540", MODI)
esigi("1280x540" in opzioni and scelte == ["1280x540"],
      "una misura scritta a mano e non dichiarata dal monitor non si perde")

opzioni, scelte, casella = rendi("1024x768", [])
esigi(casella and not opzioni,
      "e dove il monitor non dichiara niente resta la casella da riempire")


# ------------------------------- 17.3.4: la voce «Video» sparisce sul pannello
#
# *«Il menu video non dovrebbe comparire se la piattaforma e' Raspberry ed e'
# configurato il DMD.»* Tutte e due le condizioni, non una: su un PC con
# `uscita: pannello` scritto a mano la pagina serve eccome, perche' quel
# pannello non si accendera' mai ed e' li' che si legge perche'.

print()
print("-- la voce «Video» nel menu (17.3.4)")

pannello_vero = piattaforma.pannello_possibile
try:
    for e_raspberry in (True, False):
        piattaforma.pannello_possibile = lambda _v=e_raspberry: _v
        for scelta, atteso in (("pannello", not e_raspberry),
                               ("schermo", True),
                               ("auto", not e_raspberry)):
            finta_cfg = {"video": {"uscita": scelta}}
            esigi(display.video_nel_menu(finta_cfg) is atteso,
                  "pannello possibile=%s uscita=%s -> voce nel menu %s"
                  % (e_raspberry, scelta, "si" if atteso else "no"))
finally:
    piattaforma.pannello_possibile = pannello_vero

esigi(display.video_nel_menu({}) in (True, False),
      "e con una configurazione vuota risponde comunque")


# ------------------- 17.3.5: il terminale in modalita' grafica (cursore ed eco)
#
# *«Ho avviato un gioco e vedevo il cursore lampeggiante. Inoltre se premo
# qualche tasto sulla tastiera, appaiono i caratteri in alto.»* Erano il
# cursore e l'eco del terminale, disegnati dal kernel sopra il nostro
# fotogramma: sul framebuffer non c'e' nessuno che metta il terminale in
# modalita' grafica, cosa che SDL sul KMS fa da sola.

print()
print("-- il terminale in modalita' grafica (17.3.5)")

esigi(display._modo_grafico(True, tempfile.mkstemp()[1]) is False,
      "su qualcosa che non e' un terminale non succede niente")
esigi(display._grafico_nostro is False,
      "e non si segna di aver preso in mano niente")
esigi(display.rianima_console() is False,
      "rimettere a posto un terminale mai preso non fa niente")


if display.modo_del_terminale() == display.KD_TEXT:
    try:
        esigi(display._modo_grafico(True) is True,
              "sul terminale vero la modalita' grafica si prende")
        esigi(display.modo_del_terminale() == display.KD_GRAPHICS,
              "e il kernel conferma: niente piu' cursore, niente piu' eco")
        esigi(display._modo_grafico(True) is False,
              "chiederla due volte non la prende due volte")

        # 17.3.6: il difetto vero. Qualcuno -- SDL che esce, un cambio di
        # terminale -- rimette la modalita' testo da sotto di noi. La 17.3.5
        # si fidava della sua variabile e non se ne accorgeva, e il cursore
        # tornava a lampeggiare sopra la partita.
        display._modo_grafico(False)
        display._grafico_nostro = True
        esigi(display.modo_del_terminale() == display.KD_TEXT,
              "se qualcuno rimette la modalita' testo da sotto...")
        esigi(display._modo_grafico(True) is True
              and display.modo_del_terminale() == display.KD_GRAPHICS,
              "...il ricontrollo se ne accorge e riprende il terminale")
    finally:
        rimesso = display.rianima_console()
    esigi(rimesso is True and display.modo_del_terminale() == display.KD_TEXT,
          "e uscendo il terminale torna com'era, in modalita' testo")
    esigi(display.rianima_console() is False,
          "rimetterlo a posto due volte non fa niente")
else:
    print("     (saltate: qui non c'e' un terminale virtuale da provare)")

# Il ricontrollo periodico del framebuffer, senza aprire `/dev/fb0`: si
# guarda solo che chiami la cosa giusta ogni tot fotogrammi, e che con
# `lascia` non la chiami mai.
quante = []
finta = display.SuperficieFramebuffer.__new__(display.SuperficieFramebuffer)
finta._giri = 0
finta._console = "zitta"
finta._ricontrolla_console = lambda: quante.append(1)
finta._bit = 32
finta.width, finta.height = 4, 1
finta._f = tempfile.TemporaryFile()
finta._riga = 16
finta._mappa = None          # questa finta scrive alla vecchia maniera
for _ in range(display.SuperficieFramebuffer.OGNI_QUANTI * 2):
    finta.mostra(Image.new("RGB", (4, 1)))
esigi(len(quante) == 2,
      "il terminale si ricontrolla ogni %d fotogrammi, non a ogni fotogramma"
      % display.SuperficieFramebuffer.OGNI_QUANTI)


print()
print("-- i pixel dentro la memoria dello schermo, senza copie (17.4.17)")

# Misurato sul mini PC Atom: impacchettare il fotogramma in BGRX costava
# **49,5 ms** e scriverlo altri 8,6, contro 24,6 di composizione. Il
# `tobytes` costruisce undici megabyte in un buffer nuovo, la `write` li
# ricopia nel kernel, il kernel li ricopia nello schermo: tre giri per gli
# stessi pixel. Mappata, la memoria dello schermo si scrive **una volta**.
#
# La prova non ha un framebuffer vero: ne usa un file, che e' esattamente
# quello che `mmap` si aspetta, e confronta i byte con quelli che scriveva
# la strada di prima.

def finto_framebuffer(largo, alto, bit):
    percorso = os.path.join(tempfile.mkdtemp(), "fb")
    with open(percorso, "wb") as f:
        f.write(b"\xa5" * (largo * alto * (bit // 8)))
    superficie = display.SuperficieFramebuffer.__new__(
        display.SuperficieFramebuffer)
    superficie._console = "lascia"
    superficie._giri = 0
    superficie._ricontrolla_console = lambda: None
    superficie.width, superficie.height, superficie._bit = largo, alto, bit
    superficie._f = open(percorso, "r+b", buffering=0)
    superficie._riga = largo * (bit // 8)
    superficie._mappa = superficie._mappa_memoria()
    return superficie, percorso


quadro = Image.new("RGB", (64, 32))
pix = quadro.load()
for y in range(32):
    for x in range(64):
        pix[x, y] = (x * 4 % 256, y * 8 % 256, (x + y) * 3 % 256)

for bit in (32, 16):
    superficie, percorso = finto_framebuffer(64, 32, bit)
    esigi(superficie._mappa is not None,
          "a %d bit la memoria dello schermo si mappa" % bit)
    superficie.mostra(quadro)
    scritto = open(percorso, "rb").read()
    if bit == 32:
        atteso = quadro.tobytes("raw", "BGRX")
        uguali = all(scritto[i:i + 3] == atteso[i:i + 3]
                     for i in range(0, len(atteso), 4))
        esigi(uguali,
              "e i pixel sono quelli di sempre, byte per byte (BGRX)")
        esigi(set(scritto[3::4]) == {0},
              "con il quarto byte azzerato una volta sola, all'apertura")
    else:
        import numpy as _nptest
        a = _nptest.asarray(quadro, dtype=_nptest.uint16)
        atteso = ((((a[:, :, 0] >> 3) << 11) | ((a[:, :, 1] >> 2) << 5)
                   | (a[:, :, 2] >> 3)).astype("<u2").tobytes())
        esigi(scritto == atteso, "e a 16 bit l'RGB565 e' identico a prima")
    superficie._f.close()

# E se la riga in memoria e' allineata -- larghezza per byte non basta --
# non si mappa niente: si torna alla strada di prima invece di scrivere
# storto.
stretta = display.SuperficieFramebuffer.__new__(display.SuperficieFramebuffer)
stretta.width, stretta.height, stretta._bit = 64, 32, 32
stretta._riga = 64 * 4 + 64
stretta._f = tempfile.TemporaryFile()
esigi(stretta._mappa_memoria() is None,
      "con la riga allineata in modo strano non si mappa: meglio la strada"
      " lenta che un'immagine storta")

print()
print("-- il fotogramma scritto dentro lo schermo, senza comporlo (17.4.18)")

# La misura che ha deciso: su un Atom, a 2560x1080 con il filtro acceso,
# comporre costava **64,7 ms** e consegnare altri 34 -- dieci fotogrammi al
# secondo. Ma comporre vuol dire costruire un'immagine da undici megabyte
# per poi ricopiarla; e la via dei colori sa gia' che un pixel della tela
# diventa sempre la stessa piastrella tinta del suo colore. Allora la si
# scrive **dove deve stare**, una riga per volta, e di passaggi ne resta uno.
#
# La cosa su cui questa prova non transige e' sempre la stessa: gli stessi
# pixel che usciranno dalla strada di sempre.

import numpy as _npd                                       # noqa: E402


def uscita_finta(largo=1280, alto=720, filtro=True):
    percorso = os.path.join(tempfile.mkdtemp(), "fb")
    with open(percorso, "wb") as f:
        f.write(b"\x00" * (largo * alto * 4))
    sup = display.SuperficieFramebuffer.__new__(display.SuperficieFramebuffer)
    sup._console = "lascia"
    sup._giri = 0
    sup._ricontrolla_console = lambda: None
    sup.width, sup.height, sup._bit = largo, alto, 32
    sup._f = open(percorso, "r+b", buffering=0)
    sup._riga = largo * 4
    sup._mappa = sup._mappa_memoria()
    conf = dmdconf.load()
    conf["video"]["uscita"] = "schermo"
    conf["video"]["filtro_dmd"] = filtro
    return display.DisplaySchermo(conf, superficie=sup), percorso


def letto_come_rgb(percorso, largo, alto):
    dati = _npd.frombuffer(open(percorso, "rb").read(), _npd.uint8)
    dati = dati.reshape(alto, largo, 4)
    return _npd.stack([dati[:, :, 2], dati[:, :, 1], dati[:, :, 0]], axis=2)


def tela_di_colori(misura, quanti=12, seme=7):
    import random as _r
    im = Image.new("RGB", misura)
    px = im.load()
    rnd = _r.Random(seme)
    tav = [(rnd.randint(0, 255), rnd.randint(0, 255), 90)
           for _ in range(quanti)]
    for y in range(misura[1]):
        for x in range(misura[0]):
            px[x, y] = tav[rnd.randrange(quanti)]
    return im


for filtro in (True, False):
    uscita, percorso = uscita_finta(filtro=filtro)
    comp = uscita.compositore
    tela = tela_di_colori(comp.tela_logica)
    uscita.show(tela)
    esigi(_npd.array_equal(letto_come_rgb(percorso, 1280, 720),
                           _npd.asarray(comp.componi(tela))),
          "filtro %s: scritto dentro lo schermo, identico a quello che"
          " usciva da `componi`" % ("acceso" if filtro else "spento"))
    uscita._superficie._f.close()

# Le regioni, e la memoria di quella che non cambia.
uscita, percorso = uscita_finta()
comp = uscita.compositore
riquadri = uscita.regioni(True)
orologio = tela_di_colori((256, riquadri["orologio"][3]), seme=3)
contenuto = tela_di_colori((256, 64), seme=5)
pezzi = {"orologio": (orologio, riquadri["orologio"]),
         "contenuto": (contenuto, riquadri["contenuto"])}
uscita.mostra_regioni(pezzi)
prima = letto_come_rgb(percorso, 1280, 720)
esigi(_npd.array_equal(prima, _npd.asarray(comp.componi_regioni(pezzi))),
      "due regioni scritte dentro lo schermo: identiche a `componi_regioni`")
uscita.mostra_regioni({"orologio": (None, riquadri["orologio"]),
                       "contenuto": (None, riquadri["contenuto"])})
esigi(_npd.array_equal(prima, letto_come_rgb(percorso, 1280, 720)),
      "e due `None` di fila non svuotano niente: la memoria c'e' anche qui")
uscita.mostra_regioni({"orologio": (None, riquadri["orologio"]),
                       "contenuto": (contenuto, riquadri["contenuto"])})
esigi(_npd.array_equal(letto_come_rgb(percorso, 1280, 720), prima),
      "una regione che si muove non disturba quella ferma")

# E dove la strada diretta non si puo' fare -- troppi colori, come una
# fotografia -- si compone come sempre, senza che nessuno se ne accorga.
foto = Image.new("RGB", comp.tela_logica)
px = foto.load()
for y in range(comp.tela_logica[1]):
    for x in range(comp.tela_logica[0]):
        px[x, y] = ((x * 7 + y) % 256, (x + y * 5) % 256, (x * 3 + y) % 256)
esigi(comp.disegna_dentro([(foto, (0, 0), comp.scala)],
                          uscita._superficie.vista_bgrx()) is False,
      "con una fotografia la strada diretta si tira indietro")
uscita.show(foto)
esigi(_npd.array_equal(letto_come_rgb(percorso, 1280, 720),
                       _npd.asarray(comp.componi(foto))),
      "e il fotogramma esce lo stesso, dalla strada di sempre")
uscita._superficie._f.close()

print()
print("-- il testo netto, dove il pixel logico e' grosso (17.4.19)")

# *«Col filtro spento, potremmo avere delle linee piu' secche e nitide, con
# meno antialiasing?»* Si': PIL disegna le lettere con i bordi **sfumati**,
# e su un monitor quel mezzo pixel diventa un quadrato grigio grosso come
# gli altri. Con i punti accesi si legge come un punto meno acceso; senza,
# si legge come una sbavatura.

from PIL import ImageDraw as _id                            # noqa: E402

prima = _id.Draw(Image.new("RGB", (8, 8))).fontmode
esigi(display.testo_netto(True) is True, "il testo netto si accende")
esigi(_id.Draw(Image.new("RGB", (8, 8))).fontmode == "1",
      "e da li' in poi PIL disegna senza sfumature, in tutte le sorgenti")
display.testo_netto(False)
esigi(_id.Draw(Image.new("RGB", (8, 8))).fontmode == prima,
      "e si torna indietro quando si vuole (%s)" % prima)

# Il disegno vero: senza sfumature non deve restare **nessun** mezzo tono.
def toni_di(netto):
    display.testo_netto(netto)
    tela = Image.new("RGB", (64, 16), (0, 0, 0))
    d = _id.Draw(tela)
    from sources.clock import _load_font
    d.text((1, 1), "20:49", font=_load_font(12), fill=(255, 140, 26))
    display.testo_netto(False)
    dati = tela.tobytes()
    return {dati[i] for i in range(0, len(dati), 3)}


sfumati = toni_di(False)
netti = toni_di(True)
esigi(len(sfumati) > 3,
      "sfumato: i bordi hanno mezzi toni (%d valori diversi di rosso)"
      % len(sfumati))
esigi(netti == {0, 255},
      "netto: o acceso o spento, niente in mezzo (%s)"
      % ", ".join(str(v) for v in sorted(netti)))

# E la regola di «auto»: il pannello no, il monitor con i punti no, il
# monitor senza punti si'.
esigi(display.vuole_testo_netto({}, display.Compositore(TELA, (256, 64), {}))
      is False,
      "auto: sul pannello il testo resta sfumato, e li' e' giusto")
esigi(display.vuole_testo_netto(
          {}, display.Compositore(TELA, (2560, 1080),
                                  {"filtro_dmd": True})) is False,
      "auto: con i punti accesi la sfumatura si legge bene")
esigi(display.vuole_testo_netto(
          {}, display.Compositore(TELA, (2560, 1080),
                                  {"filtro_dmd": False})) is True,
      "auto: con i punti spenti e il pixel grosso, netto")
esigi(display.vuole_testo_netto({"video": {"testo_netto": "si"}}, None) is True
      and display.vuole_testo_netto({"video": {"testo_netto": "no"}},
                                    None) is False,
      "e la scelta a mano vince su tutto")

# La misura la decide il framebuffer, non la configurazione: qui non si
# cambia modo video.
esigi("vera = self._misura_dichiarata()" in open(os.path.join(
          os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
          "display.py"), encoding="utf-8").read(),
      "e una risoluzione chiesta nella pagina non la si prende per buona")

vera = display.SuperficieFramebuffer.__new__(display.SuperficieFramebuffer)
vera._console = "lascia"
esigi(display.SuperficieFramebuffer._ricontrolla_console(vera) is False,
      "e con «lascia» non si tocca niente, nemmeno nel ricontrollo")


# 17.4.1: il ricontrollo deve passare anche da chi disegna, perche' il
# momento in cui serve e' quello in cui **non** si disegna -- lo schermo
# fermo fra una partita e l'altra.
class _SuperficieCheConta:
    width = height = 8

    def __init__(self):
        self.quante = 0

    def _ricontrolla_console(self):
        self.quante += 1
        return True

    def mostra(self, immagine):
        pass

    def chiudi(self):
        pass


conta = _SuperficieCheConta()
schermo_conta = display.DisplaySchermo(
    {"video": {"filtro_dmd": False}, "display": {"brightness": 100}},
    superficie=conta)
esigi(schermo_conta.ricontrolla_console() is True and conta.quante == 1,
      "il display sa farsi ricontrollare la console da fuori")
esigi(not hasattr(display.DisplayAssente({}), "ricontrolla_console"),
      "e senza uscita video la domanda non si pone")


# ------------------------------- 17.4.7: il monitor in standby quando e' spento
#
# «Spento» vuol dire fotogramma nero, e un monitor che mostra nero resta
# acceso. Con il valore 4 di `FB_BLANK_*` il driver manda il segnale di
# spegnimento e il monitor va in standby davvero.

print()
print("-- lo standby del monitor (17.4.7)")

finto_blank = tempfile.mkstemp()[1]
esigi(display.standby_monitor(True, finto_blank) is True
      and open(finto_blank).read() == display.FB_SPENTO,
      "spegnere scrive il quattro, che e' FB_BLANK_POWERDOWN")
esigi(display.standby_monitor(False, finto_blank) is True
      and open(finto_blank).read() == display.FB_ACCESO,
      "riaccendere scrive lo zero")
esigi(display.standby_monitor(True, os.path.join(finto_blank, "niente")) is False,
      "dove non c'e' niente da scrivere non succede niente, e non e' un errore")

cfg_standby = {"video": {"filtro_dmd": False, "standby": True},
               "display": {"brightness": 100}}
schermo_sb = display.DisplaySchermo(cfg_standby,
                                    superficie=_SuperficieCheConta())
esigi(hasattr(schermo_sb, "standby"),
      "il display su schermo sa addormentare il monitor")
cfg_standby["video"]["standby"] = False
spento_a_mano = display.DisplaySchermo(cfg_standby,
                                      superficie=_SuperficieCheConta())
esigi(spento_a_mano.standby(True) is False,
      "e con l'impostazione spenta non tocca niente")
esigi(not hasattr(display.DisplayLed, "standby"),
      "sul pannello LED il metodo non esiste: non c'e' nessun monitor")


# ------------------------- 17.4.10: la lingua del testo che va sul pannello
#
# *«Nelle previsioni del tempo, domani viene mostrato come Tomorrow.»* La
# regola e' scritta anche in `config.json`: «web.language non ha effetto sul
# testo mostrato sul pannello, che segue clock.language». `Source.t()` pero'
# guardava `web.language`, che di serie e' **vuoto** -- vuol dire «decidi tu
# dal browser» -- e il vuoto cadeva sull'inglese.

print()
print("-- la lingua del testo sul pannello (17.4.10)")

from sources.base import Source                           # noqa: E402


class _Sorgente(Source):
    def __init__(self, cfg):
        self.cfg = cfg


CHIAVE = "meteo.giorno.domani"
esigi(_Sorgente({"clock": {"language": "it"}, "web": {"language": ""}}).t(
          CHIAVE) == "DOMANI",
      "con il pannello in italiano e la pagina non scelta si legge DOMANI")
esigi(_Sorgente({"clock": {"language": "it"}, "web": {"language": "en"}}).t(
          CHIAVE) == "DOMANI",
      "e resta DOMANI anche se la **pagina** e' in inglese: sono due cose")
esigi(_Sorgente({"clock": {"language": "en"}}).t(CHIAVE) == "TOMORROW",
      "con il pannello in inglese si legge TOMORROW")
esigi(_Sorgente({"clock": {"language": "it"}}).t(CHIAVE, "en") == "TOMORROW",
      "e una lingua chiesta a voce -- da una pagina web -- vince su tutto")


sep("La via dei colori: il filtro per colore invece che per pixel (17.4.15)")

# L'idea e' sua: *«abbassa il numero di colori»*. Il filtro moltiplica ogni
# pixel **vero** per la maschera -- a 2560x1080 sono due milioni e mezzo di
# moltiplicazioni per tre canali, trenta volte al secondo. Ma la maschera e'
# la stessa piastrella ripetuta, e un pixel della tela diventa sempre quella
# piastrella tinta del suo colore: con dodici colori le piastrelle diverse
# sono dodici.
#
# La cosa su cui questa prova non transige: **non cambia un pixel**.

from PIL import ImageChops                                 # noqa: E402

TAVOLOZZA = [(255, 140, 26), (0, 208, 255), (224, 228, 240), (0, 0, 0),
             (154, 216, 106), (176, 144, 208), (120, 128, 144), (255, 255, 0),
             (12, 34, 56), (200, 0, 0), (0, 200, 0), (0, 0, 200)]


def tela_a_colori(misura, quanti=12, seme=4):
    import random as _random
    im = Image.new("RGB", misura)
    px = im.load()
    rnd = _random.Random(seme)
    for y in range(misura[1]):
        for x in range(misura[0]):
            px[x, y] = TAVOLOZZA[rnd.randrange(quanti)]
    return im


for schermo in ((2560, 1080), (1920, 1080), (1280, 720), (1024, 768)):
    c = display.Compositore(TELA, schermo, {"filtro_dmd": True})
    tela = tela_a_colori(c.tela_logica)
    misura = (c.tela_logica[0] * c.scala, c.tela_logica[1] * c.scala)
    svelto = c._a_colori(tela, misura)
    sempre = ImageChops.multiply(tela.resize(misura, Image.NEAREST),
                                 c.maschera(misura))
    esigi(svelto is not None,
          "%dx%d: con dodici colori la via dei colori si puo' fare" % schermo)
    esigi(svelto is not None and svelto.tobytes() == sempre.tobytes(),
          "%dx%d: e il fotogramma e' identico **pixel per pixel**" % schermo)

# La luminosita' viaggia dentro la maschera: deve viaggiare anche nella
# piastrella, se no lo slider smetterebbe di funzionare proprio dove la via
# nuova si accende.
c = display.Compositore(TELA, (1280, 720), {"filtro_dmd": True})
c.luminosita = 40
tela = tela_a_colori(c.tela_logica)
misura = (c.tela_logica[0] * c.scala, c.tela_logica[1] * c.scala)
esigi(c._a_colori(tela, misura).tobytes()
      == ImageChops.multiply(tela.resize(misura, Image.NEAREST),
                             c.maschera(misura)).tobytes(),
      "anche con la luminosita' al quaranta per cento non cambia un pixel")

# Troppi colori -- una fotografia, un fotogramma di video -- e si torna alla
# strada di sempre. Il conto dei colori lo fa PIL e smette appena supera il
# tetto: costa microsecondi, non millisecondi.
c = display.Compositore(TELA, (1280, 720), {"filtro_dmd": True})
misura = (c.tela_logica[0] * c.scala, c.tela_logica[1] * c.scala)
foto = Image.new("RGB", c.tela_logica)
px = foto.load()
for y in range(c.tela_logica[1]):
    for x in range(c.tela_logica[0]):
        px[x, y] = ((x * 7 + y) % 256, (x + y * 5) % 256, (x * 3 + y * 11) % 256)
esigi(foto.getcolors(display.SOGLIA_COLORI) is None,
      "una fotografia ha piu' colori del tetto (%d)" % display.SOGLIA_COLORI)
esigi(c._a_colori(foto, misura) is None,
      "e allora la via dei colori si tira indietro invece di rallentare")
esigi(c._grande(foto, misura).tobytes()
      == ImageChops.multiply(foto.resize(misura, Image.NEAREST),
                             c.maschera(misura)).tobytes(),
      "il ripiego resta quello di sempre, identico al pixel")

# E dove non ci sono punti da disegnare non si scomoda.
uno = display.Compositore(TELA, (256, 64), {"filtro_dmd": True})
esigi(uno._a_colori(Image.new("RGB", (256, 64)), (256, 64)) is None,
      "a scala uno la maschera e' tutta bianca: niente da guadagnare")

spenta = display.Compositore(TELA, (1280, 720),
                             {"filtro_dmd": True, "filtro_a_colori": False})
esigi(spenta._a_colori(tela_a_colori(spenta.tela_logica),
                       (spenta.tela_logica[0] * spenta.scala,
                        spenta.tela_logica[1] * spenta.scala)) is None,
      "e c'e' l'interruttore per spegnerla senza toccare il codice")

sep("Il monitor che arriva dopo, e il cartello degli indirizzi (17.4.16)")

# *«Se il sistema si avvia con il monitor staccato, permane la finestra di
# login e non ritenta di agganciarsi.»* Vero: l'uscita video si provava una
# volta sola. Adesso, quando non si e' aperta, una vedetta guarda in `/sys`
# se e' comparso un connettore collegato -- una lettura di file, non un
# tentativo di aprire SDL -- e solo allora riprova.

drm = tempfile.mkdtemp()
for nome in ("card0-HDMI-A-1", "card0-DP-1"):
    os.makedirs(os.path.join(drm, nome))
    with open(os.path.join(drm, nome, "status"), "w") as f:
        f.write("disconnected\n")
esigi(display.monitor_collegato(drm) is False,
      "con tutti i connettori staccati non si prova nemmeno ad aprire")
with open(os.path.join(drm, "card0-DP-1", "status"), "w") as f:
    f.write("connected\n")
esigi(display.monitor_collegato(drm) is True,
      "appena uno dice «connected», si riprova")
esigi(display.monitor_collegato(os.path.join(drm, "vuoto")) is True,
      "e su una macchina senza KMS si risponde «si'»: meglio provare e"
      " fallire che non provare mai")

# La vedetta vera, con un'uscita finta che un certo momento comincia a
# funzionare. Niente attese di dieci secondi: il periodo e' un attributo.
import threading                                           # noqa: E402

import dmdd                                                # noqa: E402


class Vedetta:
    running = True
    VEDETTA_OGNI = 0.02
    _vedetta_monitor = dmdd.Runtime._vedetta_monitor

    def __init__(self, cfg):
        self.cfg = cfg
        self.display = display.DisplayAssente(cfg, "niente monitor")
        self.arbiter = dmdd.Arbiter(cfg)


class Apparsa:
    def __init__(self, misura):
        self.width, self.height = misura

    def clear(self):
        pass


cfg_vedetta = dmdconf.load()
spia = Vedetta(cfg_vedetta)
collegato = {"si": False}
veri = (display.monitor_collegato, display.crea)
display.monitor_collegato = lambda *a, **k: collegato["si"]
display.crea = lambda cfg: Apparsa((spia.display.width, spia.display.height))
try:
    threading.Thread(target=spia._vedetta_monitor, daemon=True).start()
    time.sleep(0.15)
    esigi(isinstance(spia.display, display.DisplayAssente),
          "finche' non c'e' niente attaccato l'uscita resta assente")
    collegato["si"] = True
    attesa = time.time() + 2.0
    while time.time() < attesa and isinstance(spia.display,
                                              display.DisplayAssente):
        time.sleep(0.02)
    esigi(isinstance(spia.display, Apparsa),
          "attaccato il monitor, l'uscita si rialza da sola senza riavvio")
    esigi(spia.arbiter.hold_name == "avvio",
          "e il cartello degli indirizzi si rifa': nessuno l'aveva visto,"
          " lo schermo non c'era")
finally:
    display.monitor_collegato, display.crea = veri
    spia.running = False

# Il cartello: cinque secondi, e dentro c'e' dove trovare l'apparecchio.
from sources.avvio import AvvioSource, indirizzo_ipv4, nome_locale  # noqa: E402

cartello = AvvioSource(dmdconf.load(), 256, 64, durata=0.3)
primo = cartello.frame()
esigi(primo is not None and primo.size == (256, 64),
      "il cartello si disegna sulla tela del pannello")
esigi(cartello.frame() is None,
      "e una volta sola: non cambia, non si ridisegna trenta volte al secondo")
esigi(cartello.in_fascia is False,
      "prende la schermata intera: un indirizzo dentro un terzo di schermo"
      " non si legge")
acceso = sum(1 for i in range(0, len(primo.tobytes()), 3)
              if primo.tobytes()[i:i + 3] != b"\x00\x00\x00")
esigi(acceso > 200,
      "e qualcosa c'e' scritto davvero (%d pixel accesi)" % acceso)
esigi(cartello.active() is True, "finche' dura, e' attivo")
time.sleep(0.35)
esigi(cartello.active() is False and cartello.frame() is None,
      "passati i suoi secondi si spegne da solo e non torna")
esigi(nome_locale().endswith(".local"),
      "il nome mDNS finisce in .local (%s)" % nome_locale())

# E il ridimensionamento del framebuffer non sfuma piu': un pannello DMD
# sfumato sembra un antialiasing acceso per sbaglio.
sorgente_display = open(os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "display.py"), encoding="utf-8").read()
esigi("immagine.resize((self.width, self.height),\n"
      "                                       Image.NEAREST)"
      in sorgente_display,
      "il framebuffer ingrandisce a blocchi, non sfumando")

print()
print("=" * 74)
falliti = [m for ok, m in esiti if not ok]
if falliti:
    print("FALLITI %d su %d" % (len(falliti), len(esiti)))
    for m in falliti:
        print("  - %s" % m)
    sys.exit(1)
print("TUTTO BENE: %d prove" % len(esiti))
