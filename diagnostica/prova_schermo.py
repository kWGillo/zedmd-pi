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


sep("1. Il moltiplicatore e' intero e il piu' grande che sta dentro")

for misura in MISURE:
    c = display.Compositore(TELA, misura)
    x, y, largo, alto = c.riquadro
    atteso = min(misura[0] // TELA[0], misura[1] // TELA[1])
    esigi(c.scala == atteso,
          "%dx%d: scala %s, attesa %d" % (misura[0], misura[1], c.scala, atteso))
    esigi(largo == TELA[0] * atteso and alto == TELA[1] * atteso,
          "   e il riquadro e' %dx%d" % (largo, alto))
    esigi(0 <= x and 0 <= y and x + largo <= misura[0] and y + alto <= misura[1],
          "   e sta dentro lo schermo, a (%d, %d)" % (x, y))
    esigi(abs((misura[0] - largo) - 2 * x) <= 1
          and abs((misura[1] - alto) - 2 * y) <= 1,
          "   centrato, con le bande uguali")

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


print()
print("=" * 74)
falliti = [m for ok, m in esiti if not ok]
if falliti:
    print("FALLITI %d su %d" % (len(falliti), len(esiti)))
    for m in falliti:
        print("  - %s" % m)
    sys.exit(1)
print("TUTTO BENE: %d prove" % len(esiti))
