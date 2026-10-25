# -*- coding: utf-8 -*-
"""17.2 - Due regioni: l'orologio grande, e il contenuto sotto.

L'idea
------
La tela e' 4:1 e lo schermo non lo e'. Ingrandendola al massimo restano due
bande nere sopra e sotto, e la 17.1 ci aveva messo dentro altre tele da
256x64. Non bastava: *«con l'orologio da solo, va ingrandito l'orologio»*.

Quindi non tre fasce uguali ma **due regioni**. Da solo l'orologio disegna su
tutta la tela logica -- a 1024x768 con scala 4 sono 256x192 pixel logici,
cioe' tre volte le righe del pannello -- e le cifre crescono con lui. Quando
c'e' qualcos'altro da mostrare scende al cinquanta per cento e la meta' di
sotto e' del contenuto.

Il punto che tiene in piedi tutto
---------------------------------
**Cresce la tela logica, non la risoluzione.** Il filtro DMD funziona perche'
ogni pixel della tela diventa una cella di celle intere: disegnando l'orologio
a 1024x384 veri i punti sparirebbero e le due meta' dello schermo non si
somiglierebbero piu'. Crescendo la tela logica i pixel ci sono ancora, sono
solo di piu'.

E le sorgenti **non si toccano**: disegnano su 256x64 perche' quelle misure
sono le loro, e dentro la loro regione si centrano senza stirarsi.
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
from dmdd import Arbiter
from sources.clock import ClockSource

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


class Finta:
    def __init__(self, nome, priorita, colore, in_fascia=True, gruppo=""):
        self.name = nome
        self.priority = priorita
        self.in_fascia = in_fascia
        self.gruppo = gruppo
        self.colore = colore
        self.enabled = True
        self.acceso = False
        self.viste = 0

    def active(self):
        return self.acceso

    def frame(self):
        im = Image.new("RGB", TELA, self.colore)
        im.load()[0, 0] = (255, 0, 0)
        im.load()[255, 63] = (0, 255, 0)
        return im

    def in_onda(self):
        self.viste += 1


sep("1. La tela logica e le due regioni")

ATTESI = [((1024, 768), 4, (256, 192)), ((1920, 1080), 7, (256, 154)),
          ((1280, 720), 5, (256, 144)), ((640, 480), 2, (256, 240)),
          ((256, 64), 1, (256, 64))]
for schermo, scala, logica in ATTESI:
    c = display.Compositore(TELA, schermo, {})
    esigi(c.scala == scala and c.tela_logica == logica,
          "%dx%d: scala x%s, tela logica %sx%s"
          % (schermo[0], schermo[1], c.scala, c.tela_logica[0], c.tela_logica[1]))

c = display.Compositore(TELA, (1024, 768), {})
solo = c.regioni(False)
due = c.regioni(True)
esigi(set(solo) == {"orologio"}, "da solo c'e' una regione sola")
esigi(solo["orologio"] == (0, 4, 256, 184),
      "e l'orologio prende tutta la tela meno il bordo: %s" % (solo["orologio"],))
esigi(set(due) == {"orologio", "contenuto"}, "con qualcos'altro le regioni sono due")
esigi(due["orologio"][3] + due["contenuto"][3] + 2 * c.margine == 192,
      "e insieme coprono la tela: %d + %d + bordi = 192"
      % (due["orologio"][3], due["contenuto"][3]))
esigi(abs(due["contenuto"][3] - 192 // 2) <= 1,
      "meta' schermo al contenuto (%d righe su 192)" % due["contenuto"][3])
esigi(due["contenuto"][3] >= 64,
      "e nella sua meta' una tela da 64 righe ci sta (%d)" % due["contenuto"][3])

for schermo, _s, _l in ATTESI[:4]:
    c = display.Compositore(TELA, schermo, {})
    r = c.regioni(True)
    esigi(r["contenuto"][3] >= 64,
          "%dx%d: anche qui la meta' di sotto tiene una tela intera (%d)"
          % (schermo[0], schermo[1], r["contenuto"][3]))


sep("2. L'orologio da solo e' piu' grande di quello del pannello")

cfg = dmdconf.load()
pannello = ClockSource(cfg, 256, 64)
grande = ClockSource(cfg, 256, 184)
meta = ClockSource(cfg, 256, 88)
esigi(grande._corpo_ora() > 2 * pannello._corpo_ora(),
      "da solo le cifre sono piu' del doppio (%d contro %d)"
      % (grande._corpo_ora(), pannello._corpo_ora()))
esigi(meta._corpo_ora() > pannello._corpo_ora(),
      "a meta' schermo sono comunque piu' grandi (%d)" % meta._corpo_ora())
esigi(pannello._corpo_ora() == 38,
      "e il pannello resta a 38, il corpo di sempre")


sep("3. I testi non crescono: solo le cifre")

esigi(grande._font_small.size == pannello._font_small.size == 12,
      "la data resta a corpo 12 su tutte e tre le tele")
esigi(grande.MONDO_CORPO == pannello.MONDO_CORPO == 10,
      "e la banda degli orari pure")
esigi(len(grande._mondo()) == len(pannello._mondo()),
      "quindi in banda ci sta lo stesso numero di citta'")
esigi(grande.MONDO_CIMA == 184 - grande.TIMER_SPESSORE - grande.MONDO_CORPO - 1,
      "la banda sta in fondo per costruzione, non a una frazione fissa")
esigi(pannello.MONDO_CIMA == 51,
      "e sul pannello quel conto da' 51, il numero di sempre")


sep("4. Le cifre non escono dai bordi")

for h in (64, 88, 120, 184, 240):
    c = ClockSource(cfg, 256, h)
    larga = c._font.getbbox("00:00")
    esigi((larga[2] - larga[0]) <= 256 - 2 * c.MARGINE,
          "a %3d righe «00:00» sta in %d colonne su %d"
          % (h, larga[2] - larga[0], 256 - 2 * c.MARGINE))


sep("5. Il contenuto si centra, non si stira")

c = display.Compositore(TELA, (1024, 768), {"filtro_dmd": False})
finta = Finta("mediaplayer", 50, (10, 40, 10))
r = c.regioni(True)
fuori = c.componi_regioni({"contenuto": (finta.frame(), r["contenuto"])}).copy()
dentro = (r["contenuto"][3] - 64) // 2
alto = (r["contenuto"][1] + dentro) * c.scala
esigi(fuori.getpixel((2, alto + 2)) == (255, 0, 0),
      "l'angolo in alto a sinistra della sorgente e' dove deve")
esigi(fuori.getpixel((1021, alto + 64 * c.scala - 2)) == (0, 255, 0),
      "e quello in basso a destra pure: la tela non e' stirata")
esigi(fuori.getpixel((512, alto - 8)) == (0, 0, 0),
      "sopra c'e' il nero del margine della regione")


sep("6. La regione ferma non diventa nera")

c = display.Compositore(TELA, (1024, 768), {"filtro_dmd": False})
r = c.regioni(True)
rossa = Image.new("RGB", TELA, (200, 0, 0))
verde = Image.new("RGB", TELA, (0, 200, 0))
c.componi_regioni({"orologio": (rossa, r["orologio"]),
                   "contenuto": (verde, r["contenuto"])})
dopo = c.componi_regioni({"orologio": (None, r["orologio"]),
                          "contenuto": (None, r["contenuto"])}).copy()
# Le tele sono 256x64 dentro regioni piu' alte, quindi si centrano: si
# guarda **dentro** l'immagine, non nel margine che le sta intorno.
alto_orologio = (r["orologio"][1] + (r["orologio"][3] - 64) // 2 + 10) * c.scala
alto_contenuto = (r["contenuto"][1] + (r["contenuto"][3] - 64) // 2 + 10) * c.scala
esigi(dopo.getpixel((512, alto_orologio)) == (200, 0, 0)
      and dopo.getpixel((512, alto_contenuto)) == (0, 200, 0),
      "due None di fila e le due regioni sono ancora li'")


sep("7. L'arbitro: una sorgente sola per la meta' di sotto")

clock = Finta("clock", 10, (255, 140, 26))
radar = Finta("air_radar", 60, (0, 200, 255))
meteo = Finta("meteo", 54, (120, 120, 255), gruppo="turni")
media = Finta("mediaplayer", 50, (0, 255, 0))
# Priorita' alta apposta: cosi' se entrasse in regione vincerebbe, e la
# prova dimostra che a tenerla fuori e' `in_fascia`, non il suo posto in
# classifica. E' il caso dell'anteprima della gestione media, che di
# priorita' ne ha 90.
doom = Finta("doom", 90, (255, 0, 0), in_fascia=False)
a = Arbiter(dmdconf.load())
for s in (clock, radar, meteo, media, doom):
    a.register(s)

clock.acceso = True
esigi(a.contenuto() is None, "con il solo orologio non c'e' contenuto")
esigi(a.a_regioni() is True, "e lo schermo si divide lo stesso, quando serve")

media.acceso = True
esigi(a.contenuto().name == "mediaplayer", "il Media Player scende sotto")
radar.acceso = True
esigi(a.contenuto().name == "air_radar",
      "arriva un aereo e vince lui: la priorita' decide, come ha sempre fatto")
radar.acceso = False
meteo.acceso = True
esigi(a.contenuto().name == "meteo",
      "e fra meteo e media vince il meteo, che sta piu' in alto (54 contro 50)")

doom.acceso = True
esigi(a.contenuto().name == "meteo",
      "una sorgente interattiva non scende in una regione nemmeno con la "
      "priorita' piu' alta di tutte")
doom.acceso = False

a.hold_on("doom")
esigi(a.a_regioni() is False and a.contenuto() is None,
      "con la presa niente regioni: schermo intero a chi l'ha presa")
a.hold_off()
a.cfg["arbiter"]["force_source"] = "meteo"
esigi(a.a_regioni() is False,
      "e una sorgente forzata a mano vuole lo schermo, non meta'")
a.cfg["arbiter"]["force_source"] = "auto"
esigi(a.a_regioni() is True, "tolto il blocco si torna alle regioni")


sep("8. L'orologio grande solo se non puo' arrivare nient'altro")

# Chiesto cosi': «l'orologio grande deve essere attivo solo se tutti i servizi
# sono spenti o al di fuori della fascia oraria». Senza, l'orologio si
# rimpiccioliva a ogni aereo che passava e tornava grande un minuto dopo.
for s in (radar, meteo, media, doom):
    s.enabled = False
    s.acceso = False
clock.enabled = True
clock.acceso = True
esigi(a.orologio_solo() is True,
      "tutti i servizi spenti: l'orologio prende tutto")

media.enabled = True
esigi(a.orologio_solo() is False,
      "basta un servizio **acceso** perche' l'orologio resti a meta', anche "
      "se adesso non mostra niente")
esigi(a.contenuto() is None,
      "e intanto la meta' di sotto resta vuota, non si riempie di niente")

media.acceso = True
esigi(a.contenuto().name == "mediaplayer" and a.orologio_solo() is False,
      "poi il contenuto arriva, e l'orologio non si muove: era gia' a meta'")

media.acceso = False
esigi(a.orologio_solo() is False,
      "il contenuto se ne va e l'orologio **resta** a meta': e' il punto di "
      "tutta questa regola")

media.enabled = False
esigi(a.orologio_solo() is True,
      "spento il servizio -- o uscito dalla sua fascia oraria -- l'orologio "
      "torna grande")

doom.enabled = True
esigi(a.orologio_solo() is True,
      "una sorgente interattiva non conta: non scende mai in una regione")
doom.enabled = False


sep("9. L'uscita: quante tele ci stanno, e il modo")


class Superficie:
    def __init__(self, largo, alto):
        self.width, self.height = largo, alto
        self.visti = []

    def mostra(self, immagine):
        self.visti.append(immagine.copy())


piattaforma._forza({"famiglia": "pc", "modello": "PC", "numero": "",
                    "pannello": False})
cfg = dmdconf.load()
cfg["video"]["uscita"] = "schermo"
cfg["video"]["modo"] = "auto"
schermo = display.DisplaySchermo(cfg, superficie=Superficie(1024, 768))
esigi(schermo.tele == 3, "su 1024x768 ci stanno tre tele (%s)" % schermo.tele)
esigi(schermo.regioni(False)["orologio"][3] == 184,
      "e l'uscita sa dire i riquadri delle regioni")
cfg["video"]["modo"] = "singola"
uno = display.DisplaySchermo(cfg, superficie=Superficie(1024, 768))
esigi(uno.tele == 1, "«singola» torna alla tela unica della 17.0")
cfg["video"]["modo"] = "auto"
esigi(display.DisplayAssente(cfg).tele == 1,
      "e senza uscita video la domanda non si pone")

schermo.mostra_regioni({"orologio": (Image.new("RGB", (256, 184), (90, 40, 0)),
                                     schermo.regioni(False)["orologio"])})
esigi(schermo._superficie.visti[-1].size == (1024, 768),
      "quello che finisce sulla superficie e' grande come lo schermo")


sep("10. Doom e il Game Boy vanno a tutto schermo")

from sources.doom import tela_doom, DOOM_L, DOOM_A   # noqa: E402

esigi(tela_doom(256, 64) == (256, 64),
      "sul pannello Doom disegna la tela del pannello: la fascia fa il resto")
largo, alto = tela_doom(256, 192)
esigi((largo, alto) == (256, 160),
      "su una tela da 192 righe disegna 256x160 (%dx%d)" % (largo, alto))
esigi(abs(largo / float(alto) - DOOM_L / float(DOOM_A)) < 0.01,
      "cioe' con le proporzioni vere di Doom, non schiacciato")
for tela in ((256, 144), (256, 154), (256, 240)):
    l, a = tela_doom(*tela)
    esigi(l <= tela[0] and a <= tela[1]
          and abs(l / float(a) - DOOM_L / float(DOOM_A)) < 0.02,
          "su %dx%d sta dentro e tiene le proporzioni: %dx%d"
          % (tela[0], tela[1], l, a))

c = display.Compositore(TELA, (1024, 768), {"filtro_dmd": False})
pieno = c.componi(Image.new("RGB", (256, 192), (40, 0, 0))).copy()
esigi(pieno.getpixel((512, 8)) == (40, 0, 0)
      and pieno.getpixel((512, 760)) == (40, 0, 0),
      "una tela piena riempie lo schermo da cima a fondo")
striscia = c.componi(Image.new("RGB", (256, 64), (40, 0, 0))).copy()
esigi(striscia.getpixel((512, 8)) == (0, 0, 0)
      and striscia.getpixel((512, 384)) == (40, 0, 0),
      "e una tela da pannello resta la striscia centrata di sempre")
doom_tela = c.componi(Image.new("RGB", (256, 160), (40, 0, 0))).copy()
esigi(doom_tela.getpixel((512, 384)) == (40, 0, 0)
      and doom_tela.getpixel((512, 8)) == (0, 0, 0),
      "quella di Doom sta in mezzo, alta 640 su 768")


sep("11. Il lampeggio dei due punti non sposta le cifre (17.3.2)")

# *«Quando i due punti scompaiono, l'ultima cifra si sposta a sinistra di
# qualche pixel.»* Fino alla 17.3.2 il lampeggio sostituiva i due punti con
# uno **spazio**. Con `DejaVuSansMono-Bold` i due occupano lo stesso posto e
# non si vedeva niente; con un font proporzionale -- quello su cui si
# ripiega una macchina dove il Mono non e' installato -- lo spazio e' piu'
# stretto, e si spostavano sia i minuti sia (per via del centraggio) le ore.
#
# La prova guarda i pixel: le due immagini, con e senza due punti, devono
# essere identiche **dappertutto tranne che nella colonna dei due punti**.

from PIL import ImageDraw, ImageFont                     # noqa: E402
from sources.clock import scrivi_ora                     # noqa: E402

FONT_PROVA = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def colonne_accese(img):
    """Quali colonne hanno almeno un pixel acceso."""
    px = img.load()
    fuori = set()
    for x in range(img.width):
        for y in range(img.height):
            if px[x, y][0] > 40:
                fuori.add(x)
                break
    return fuori


provati = 0
for percorso in FONT_PROVA:
    try:
        esiste = ImageFont.truetype(percorso, 38)
    except OSError:
        continue
    provati += 1
    nome = percorso.rsplit("/", 1)[1]
    for corpo in (38, 83):
        font = ImageFont.truetype(percorso, corpo)
        rese = {}
        for punti in (True, False):
            img = Image.new("RGB", (420, 140))
            scrivi_ora(ImageDraw.Draw(img), (20, 10), "14:22", font,
                       (255, 255, 255), punti=punti)
            rese[punti] = img
        con, senza = colonne_accese(rese[True]), colonne_accese(rese[False])
        esigi(senza <= con,
              "%s corpo %d: spegnendo i due punti non si accende niente"
              % (nome, corpo))
        sparite = sorted(con - senza)
        larghe = (max(sparite) - min(sparite) + 1) if sparite else 0
        esigi(sparite and larghe == len(sparite) and larghe < corpo // 2,
              "%s corpo %d: sparisce una colonna sola, larga %d -- i due punti"
              % (nome, corpo, larghe))
        d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        meta_cifre = 20 + d.textlength("14", font=font)
        esigi(min(sparite) >= meta_cifre,
              "%s corpo %d: e sta fra le ore e i minuti, non dentro le cifre"
              % (nome, corpo))

esigi(provati > 0, "almeno un font di prova trovato sulla macchina")


print()
print("=" * 74)
falliti = [m for ok, m in esiti if not ok]
if falliti:
    print("FALLITI %d su %d" % (len(falliti), len(esiti)))
    for m in falliti:
        print("  - %s" % m)
    sys.exit(1)
print("TUTTO BENE: %d prove" % len(esiti))
