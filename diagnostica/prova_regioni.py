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


sep("11-bis. Le due regioni su uno schermo 21:9 (17.4.11)")

# *«Non possiamo riproporzionare la larghezza del layer, per il 21:9, in modo
# da far stare 2 righe?»* La domanda giusta, e la risposta e' ancora meglio:
# non si tocca la larghezza -- che su un 21:9 si prende tutta -- si spartiscono
# diversamente le righe. Il contenuto prende la sua tela da 64, l'orologio
# tutto quello che resta.

for schermo, attese in (((1024, 768), "meta'"),
                        ((1920, 1080), "meta'"),
                        ((2560, 1080), "spartite"),
                        ((3440, 1440), "spartite")):
    c = display.Compositore(TELA, schermo, {"filtro_dmd": False})
    r = c.regioni(True)
    orologio, contenuto = r["orologio"][3], r["contenuto"][3]
    lh = c.tela_logica[1]
    massima = min(schermo[0] // 256, schermo[1] // 64)
    esigi(c.scala == massima or c.banda[0] >= 0.85 * schermo[0],
          "%dx%d: scala %d (massima %d), e la larghezza che si butta resta"
          " sotto il quindici per cento" % (schermo + (c.scala, massima)))
    esigi(c.due_regioni,
          "%dx%d: le due regioni si fanno (%d righe logiche)"
          % (schermo[0], schermo[1], lh))
    esigi(contenuto >= 64,
          "%dx%d: al contenuto almeno la sua tela (%d righe)"
          % (schermo[0], schermo[1], contenuto))
    esigi(orologio >= 24,
          "%dx%d: e all'orologio %d righe, che si leggono"
          % (schermo[0], schermo[1], orologio))
    if attese == "meta'":
        esigi(abs(contenuto - lh // 2) <= 1,
              "%dx%d: dove la meta' basta resta la meta' esatta, come chiesto"
              " nella 17.2" % schermo)
    else:
        esigi(contenuto == 64,
              "%dx%d: dove non basta, il contenuto prende esattamente 64"
              % schermo)

c = display.Compositore(TELA, (256, 64), {"filtro_dmd": False})
esigi(not c.due_regioni,
      "sul pannello non si divide niente: 64 righe sono una tela sola")


sep("11. Il lampeggio dei due punti non sposta le cifre (17.3.3)")

# *«Quando i due punti scompaiono, l'ultima cifra si sposta a sinistra di
# qualche pixel.»* Fino alla 17.3.3 il lampeggio sostituiva i due punti con
# uno **spazio**. Con `DejaVuSansMono-Bold` i due occupano lo stesso posto e
# non si vedeva niente; con un font proporzionale -- quello su cui si
# ripiega una macchina dove il Mono non e' installato -- lo spazio e' piu'
# stretto, e si spostavano sia i minuti sia (per via del centraggio) le ore.
#
# La prova guarda i pixel: le due immagini, con e senza due punti, devono
# essere identiche **dappertutto tranne che nella colonna dei due punti**.

from PIL import ImageDraw, ImageFont                     # noqa: E402
from sources.clock import scrivi_ora                     # noqa: E402

from sources.clock import FONT_CANDIDATES, FONT_NOSTRO   # noqa: E402

FONT_PROVA = list(FONT_CANDIDATES)

esigi(os.path.exists(FONT_NOSTRO),
      "la copia del font viaggia dentro il progetto, in font/")
esigi(FONT_CANDIDATES.index(FONT_NOSTRO) == 1,
      "e si cerca dopo quello di sistema, prima del proporzionale")


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


sep("12. Le proporzioni dell'orologio su una regione bassa (17.4.12)")

# *«La scritta della data e' troppo grande rispetto all'ora. L'ora e' troppo
# piccola rispetto a tutto il resto.»* Dalla foto di un 2560x1080, dove la
# regione dell'orologio e' alta 36 righe logiche -- **meno** delle 64 del
# pannello.
#
# Due conti separati sbagliavano insieme. Le cifre prendevano il sessanta per
# cento dell'altezza, che a 36 righe fa 21: un conto tarato su una tela che
# cresce, applicato a una che si e' ristretta. E i testi seguivano la sola
# larghezza, che su un 21:9 e' quella del pannello: la data restava a corpo
# 12, grande come sul pannello, accanto a cifre piu' piccole di quelle del
# pannello. Da qui il «troppo grande rispetto all'ora».
#
# La prova guarda tre cose: che il pannello e le tele **alte** non si siano
# mosse di un corpo, che su una regione bassa la data si rimpicciolisca e le
# cifre crescano, e che niente esca dai bordi.

cfg = dmdconf.load()
PRIMA = {64: (38, 12, 10, 51), 88: (52, 12, 10, 74), 184: (83, 12, 10, 167)}
for h, (ora, data, banda, cima) in sorted(PRIMA.items()):
    c = ClockSource(cfg, 256, h)
    esigi((c._corpo_ora(), c._font_small.size, c.MONDO_CORPO, c.MONDO_CIMA)
          == (ora, data, banda, cima),
          "a %3d righe i corpi sono quelli della 17.4.11: ora %d, data %d, "
          "banda %d, cima %d" % (h, ora, data, banda, cima))

# E il pavimento dei testi, che e' la 17.4.13: la 17.4.12 li rimpiccioliva
# quanto l'altezza voleva, e a 36 righe la banda dei fusi finiva a corpo 6.
# *«I testi del fuso orario sono troppo piccoli e illeggibili.»* Sei righe
# logiche non fanno una lettera, fanno una macchia, e il filtro DMD la
# ingrandisce dieci volte. Sotto il corpo del pannello non si scende: a
# pagare sono le cifre, che di spazio ne hanno.
pannello = ClockSource(cfg, 256, 64)
for h in (28, 36, 48, 56):
    c = ClockSource(cfg, 256, h)
    esigi(c._font_small.size == pannello._font_small.size
          and c.MONDO_CORPO == pannello.MONDO_CORPO,
          "a %2d righe data e banda restano quelle del pannello (%d e %d)"
          % (h, c._font_small.size, c.MONDO_CORPO))
    esigi(c._corpo_ora() == c.MONDO_CIMA - c.MARGINE_ALTO,
          "a %2d righe le cifre prendono **tutto** lo spazio sopra la banda"
          " (%d righe)" % (h, c._corpo_ora()))

bassa = ClockSource(cfg, 256, 48)
esigi(bassa._corpo_ora() > int(48 * 0.60),
      "che sulla regione del 21:9 vuol dire piu' del sessanta per cento"
      " dell'altezza: %d righe su 48" % bassa._corpo_ora())
esigi(bassa._corpo_ora() > 30,
      "sulla regione di un 2560x1080 le cifre sono alte 33 righe logiche"
      " (%d), cioe' quasi trecento pixel veri" % bassa._corpo_ora())

# Ma il pavimento non puo' affamare le cifre: dove non c'e' spazio per
# tutti e due, e' la banda a cedere -- l'ora non scende mai sotto il suo
# minimo.
stretta = ClockSource(cfg, 256, 24)
esigi(stretta.MONDO_CORPO < pannello.MONDO_CORPO,
      "a 24 righe la banda cede il passo alle cifre (corpo %d)"
      % stretta.MONDO_CORPO)
esigi(stretta._corpo_ora() >= ClockSource.CIFRE_MINIME,
      "e l'ora resta almeno al suo minimo (%d)" % stretta._corpo_ora())

for h in (24, 28, 32, 36, 48, 63):
    c = ClockSource(cfg, 256, h)
    esigi(c._corpo_ora() <= c.MONDO_CIMA - c.MARGINE_ALTO,
          "a %2d righe le cifre stanno sopra la banda (%d righe fino a %d)"
          % (h, c._corpo_ora(), c.MONDO_CIMA - c.MARGINE_ALTO))
    larga = c._font.getbbox("00:00")
    esigi((larga[2] - larga[0]) <= 256 - 2 * c.MARGINE,
          "a %2d righe «00:00» sta in %d colonne su %d"
          % (h, larga[2] - larga[0], 256 - 2 * c.MARGINE))
    esigi(c._font_small.size >= 6 and min(f.size for f in c._font_rifiuti) >= 5,
          "a %2d righe i testi non scendono sotto il leggibile (data %d)"
          % (h, c._font_small.size))

# E il disegno vero non deve alzare eccezioni ne' uscire dalla tela.
for h in (36, 64, 184):
    c = ClockSource(cfg, 256, h)
    c._running = True
    im = c.frame()
    esigi(im is not None and im.size == (256, h),
          "a %3d righe il fotogramma si disegna, e misura 256x%d" % (h, h))


sep("13. La scala si abbassa solo quando l'orologio ci guadagna (17.4.13)")

# *«I testi del fuso orario sono troppo piccoli e illeggibili.»* Le righe
# logiche della regione dell'orologio dipendono dalla scala, e la scala piu'
# grande non e' sempre la migliore: su un 2560x1080 la scala 10 da' 36 righe
# all'orologio, la 9 ne da' 48. Il prezzo e' la larghezza -- 2304 invece di
# 2560 -- e si paga solo finche' e' poco: la 17.4.10 scendeva a scala 8,
# cioe' a 2048, ed era stata scartata proprio per quello.

ATTESE = [
    # schermo        scala  righe orologio  cambiata?
    ((1024, 768),      4,     88,   False),
    ((1280, 720),      5,     64,   False),
    ((1920, 1080),     7,     69,   False),
    ((2560, 1440),    10,     64,   False),
    ((3840, 2160),    15,     64,   False),
    ((2560, 1080),     9,     48,   True),
    ((3440, 1440),    12,     48,   True),
]
for schermo, scala, righe, cambiata in ATTESE:
    c = display.Compositore(TELA, schermo, {})
    massima = min(schermo[0] // 256, schermo[1] // 64)
    esigi(c.scala == scala,
          "%dx%d: scala %d (attesa %d)" % (schermo + (c.scala, scala)))
    esigi((c.scala != massima) == cambiata,
          "%dx%d: %s" % (schermo[0], schermo[1],
                         "si scende di scala, perche' serve" if cambiata
                         else "la scala massima va gia' bene"))
    esigi(c.regioni(True)["orologio"][3] == righe,
          "%dx%d: all'orologio %d righe logiche (attese %d)"
          % (schermo + (c.regioni(True)["orologio"][3], righe)))
    esigi(c.banda[0] >= 0.85 * schermo[0],
          "%dx%d: e la larghezza buttata resta sotto il quindici per cento"
          " (%d pixel su %d)" % (schermo[0], schermo[1], c.banda[0],
                                 schermo[0]))
    orologio = ClockSource(cfg, 256, c.regioni(True)["orologio"][3])
    esigi(orologio.MONDO_CORPO == 10 and orologio._font_small.size == 12,
          "%dx%d: cosi' la banda dei fusi e la data restano a corpo di"
          " pannello" % (schermo[0], schermo[1]))

# E dove la larghezza costerebbe troppo si resta in alto, con l'orologio un
# po' stretto: e' il patto della 17.4.11, e non si rompe per comodita'.
c = display.Compositore(TELA, (1920, 800), {})
esigi(c.scala == min(1920 // 256, 800 // 64),
      "1920x800: la scala resta la massima, perche' scendere costerebbe un"
      " quinto della larghezza (scala %d)" % c.scala)

sep("14. La finezza della tela: linee vere invece di mattoni (17.4.20)")

# *«Con la risoluzione del monitor non si potrebbero ottenere delle linee
# simili a vettoriali?»* Si', e meta' del lavoro era gia' fatta: dalla 17.2
# le sorgenti si ridimensionano, quindi sanno gia' disegnare a qualunque
# misura. Nessuno aveva mai chiesto loro la misura vera del monitor.
#
# La finezza e' quella domanda, e la cosa su cui questa prova insiste e' che
# **a uno non cambia niente**: chi aggiorna non si ritrova lo schermo
# cambiato sotto gli occhi senza averlo chiesto.


class Vetro:
    def __init__(self, largo, alto):
        self.width, self.height = largo, alto

    def mostra(self, immagine):
        pass


def uscita_con(finezza, schermo=(2560, 1080), filtro=False):
    conf = dmdconf.load()
    conf["video"]["uscita"] = "schermo"
    conf["video"]["filtro_dmd"] = filtro
    conf["video"]["finezza"] = finezza
    return display.DisplaySchermo(conf, superficie=Vetro(*schermo))


uno = uscita_con(1)
esigi((uno.width, uno.height) == (256, 64) and uno.compositore.scala == 9,
      "finezza 1: la tela e' quella del pannello e la scala e' quella della"
      " 17.4.13 (%dx%d, x%d)"
      % (uno.width, uno.height, uno.compositore.scala))
r1 = uno.regioni(True)
esigi((r1["orologio"][3], r1["contenuto"][3]) == (48, 64),
      "finezza 1: le regioni sono quelle di sempre (%d e %d)"
      % (r1["orologio"][3], r1["contenuto"][3]))
esigi(uno.tela_piena == (256, 120),
      "finezza 1: e i giochi hanno la tela piena di sempre %s"
      % (uno.tela_piena,))

for quante in (2, 3, 5):
    u = uscita_con(quante)
    r = u.regioni(True)
    esigi((u.width, u.height) == (256 * quante, 64 * quante),
          "finezza %d: la tela e' %dx%d" % (quante, u.width, u.height))
    esigi(r["contenuto"][3] == 64 * quante,
          "finezza %d: la regione del contenuto resta una tela intera (%d)"
          % (quante, r["contenuto"][3]))
    # Non la stessa proporzione al pixel -- la scala e' intera, quindi
    # raddoppiando la finezza non si dimezza esattamente -- ma lo stesso
    # patto: all'orologio almeno mezza tela, e insieme coprono tutto.
    esigi(r["orologio"][3] >= display.minimo_orologio(u.height),
          "finezza %d: all'orologio almeno mezza tela (%d righe su %d)"
          % (quante, r["orologio"][3], u.height))
    esigi(r["orologio"][3] + r["contenuto"][3]
          + 2 * u.compositore.margine == u.compositore.tela_logica[1],
          "finezza %d: e le due regioni coprono la tela logica" % quante)
    esigi(u.tela_piena[0] == 256,
          "finezza %d: i giochi restano in unita' di pannello %s"
          % (quante, u.tela_piena))

piena = uscita_con("auto")
esigi(piena.compositore.scala == 1,
      "finezza massima: un pixel della tela e' un pixel vero (scala %d)"
      % piena.compositore.scala)
esigi(piena.width == 2560,
      "e la tela si prende tutta la larghezza dello schermo (%d)"
      % piena.width)
esigi(piena.tela_piena[0] == 256 and piena.tela_piena[1] >= 64,
      "mentre i giochi continuano a disegnare su 256 colonne %s"
      % (piena.tela_piena,))

# Il pezzo piccolo dentro la tela grande: si ingrandisce di un intero, non
# si stira e non resta un francobollo in mezzo allo schermo.
comp = piena.compositore
gioco = Image.new("RGB", (256, 108), (10, 10, 10))
volte = comp._quante_volte(gioco, comp.tela_logica)
esigi(volte == 10,
      "un gioco da 256 colonne ci sta dieci volte nella tela fine (%d)"
      % volte)
fuori = comp.componi(gioco)
esigi(fuori.size == comp.schermo,
      "e composto riempie lo schermo (%s)" % (fuori.size,))

# E su uno schermo piccolo la finezza chiesta troppo grande si accorcia da
# sola invece di dare una tela che non ci sta.
esigi(display.finezza_scelta(99, (256, 64), (1024, 768)) == 4,
      "su 1024x768 la finezza non va oltre quattro (%d)"
      % display.finezza_scelta(99, (256, 64), (1024, 768)))
esigi(display.finezza_scelta("auto", (256, 64), (256, 64)) == 1,
      "e sul pannello la finezza e' uno e non puo' essere altro")

print()
print("=" * 74)
falliti = [m for ok, m in esiti if not ok]
if falliti:
    print("FALLITI %d su %d" % (len(falliti), len(esiti)))
    for m in falliti:
        print("  - %s" % m)
    sys.exit(1)
print("TUTTO BENE: %d prove" % len(esiti))
