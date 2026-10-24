# -*- coding: utf-8 -*-
"""17.1 - Le fasce: il monitor smette di essere un pannello con le bande nere.

L'idea
------
La tela e' 4:1 e lo schermo non lo e'. Ingrandendola al massimo restano due
bande nere sopra e sotto -- e quelle bande sono alte un numero **esatto** di
tele: a 1024x768 con scala 4 lo schermo e' alto 192 righe logiche, cioe' tre
tele. Invece di lasciarle vuote ci si mettono altre sorgenti, e il pannello
diventa un cruscotto.

Le tre cose su cui questa prova insiste
---------------------------------------
* **le fasce non cambiano posto.** Una sorgente che ha una fascia la tiene
  finche' resta attiva; se quella sopra finisce, le altre **non** salgono.
  Una fascia che si sposta quando quella sopra sparisce e' il modo piu'
  sicuro di rendere illeggibile un cruscotto: l'occhio impara dove guardare e
  poi non trova piu' niente;
* **l'orologio da solo e' centrato.** Quando non c'e' nient'altro resta lui,
  in una fascia sola al centro -- che e' esattamente il pannello di prima;
* **chi tiene la presa copre tutto.** Doom, i giochi, il Game Boy, l'antepri-
  ma e le notifiche di livello allarme sono interattive o urgenti: una fascia
  su tre sarebbe una partita giocata col binocolo rovesciato.

E una quarta, che e' il motivo per cui la memoria dei fotogrammi esiste:
`frame()` torna `None` quando non e' cambiato niente. Con una sorgente sola
voleva dire «non ridisegnare»; con tre, se il compositore non si ricordasse
l'ultimo fotogramma di ognuna, una fascia ferma diventerebbe nera appena le
altre si muovono.
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
    """Una sorgente per finta: si accende, si spegne, e disegna un colore."""

    def __init__(self, nome, priorita, colore, in_fascia=True, gruppo=""):
        self.name = nome
        self.priority = priorita
        self.in_fascia = in_fascia
        self.gruppo = gruppo
        self.colore = colore
        self.enabled = True
        self.acceso = False
        self.viste = 0
        self.nuovo = True

    def active(self):
        return self.acceso

    def frame(self):
        if not self.nuovo:
            return None            # «non e' cambiato niente», come le vere
        self.nuovo = False
        return Image.new("RGB", TELA, self.colore)

    def in_onda(self):
        self.viste += 1


def arbitro(sorgenti):
    cfg = dmdconf.load()
    a = Arbiter(cfg)
    for s in sorgenti:
        a.register(s)
    return a


def nomi(scelte):
    return [s.name if s is not None else None for s in scelte]


# ------------------------------------------------------------------ geometria

sep("1. Quante fasce, e di che misura")

ATTESI = [
    ((1024, 768), "auto", 4, (1024, 256), 3),
    ((1920, 1080), "auto", 7, (1792, 448), 2),
    ((1920, 1080), "3", 5, (1280, 320), 3),
    ((1920, 1080), "4", 4, (1024, 256), 4),
    ((1280, 720), "auto", 5, (1280, 320), 2),
    ((2560, 1080), "auto", 10, (2560, 640), 1),
    ((256, 64), "auto", 1, (256, 64), 1),
]
for schermo, fasce, scala, banda, quante in ATTESI:
    c = display.Compositore(TELA, schermo, {"fasce": fasce})
    esigi(c.scala == scala and c.banda == banda and c.quante == quante,
          "%dx%d con fasce=%s: scala x%s, fascia %sx%s, %d fasce"
          % (schermo[0], schermo[1], fasce, c.scala, c.banda[0], c.banda[1],
             c.quante))

esigi(display._quante_fasce("auto") == 0 and display._quante_fasce("") == 0,
      "«auto» e il vuoto vogliono dire «quante ce ne stanno»")
esigi(display._quante_fasce("3") == 3 and display._quante_fasce(3) == 3,
      "un numero, scritto o no, vale quel numero")
esigi(display._quante_fasce("99") == 8 and display._quante_fasce("0") == 1,
      "e si resta fra una e otto")
esigi(display._quante_fasce("tante") == 0,
      "quello che non e' un numero torna automatico")


sep("2. Il gruppo delle fasce occupate sta al centro")

c = display.Compositore(TELA, (1024, 768), {"fasce": "auto"})
esigi(c.riquadro_fascia(0, 1)[1] == 256,
      "una fascia sola: al centro, riga 256 di 768")
esigi([c.riquadro_fascia(i, 2)[1] for i in range(2)] == [128, 384],
      "due: mezza fascia vuota sopra e mezza sotto")
esigi([c.riquadro_fascia(i, 3)[1] for i in range(3)] == [0, 256, 512],
      "tre: lo schermo e' pieno")
esigi(all(c.riquadro_fascia(i, 3)[0] == 0 for i in range(3)),
      "e in orizzontale sono tutte allineate")


sep("3. Una fascia ferma non diventa nera")

c = display.Compositore(TELA, (1024, 768), {"fasce": "auto", "filtro_dmd": False})
rossa = Image.new("RGB", TELA, (200, 0, 0))
verde = Image.new("RGB", TELA, (0, 200, 0))
blu = Image.new("RGB", TELA, (0, 0, 200))
c.componi_fasce([rossa, verde, blu])
dopo = c.componi_fasce([None, None, None]).copy()
esigi(dopo.getpixel((512, 10)) == (200, 0, 0)
      and dopo.getpixel((512, 266)) == (0, 200, 0)
      and dopo.getpixel((512, 522)) == (0, 0, 200),
      "tre None di fila e le tre fasce sono ancora li'")
dopo = c.componi_fasce([None, blu, None]).copy()
esigi(dopo.getpixel((512, 10)) == (200, 0, 0)
      and dopo.getpixel((512, 266)) == (0, 0, 200),
      "e una che cambia non tocca le altre")


sep("4. Un buco in mezzo resta un buco")

c = display.Compositore(TELA, (1024, 768), {"fasce": "auto", "filtro_dmd": False})
fuori = c.componi_fasce([rossa, None, blu]).copy()
esigi(fuori.getpixel((512, 10)) == (200, 0, 0),
      "la prima e' in cima")
esigi(fuori.getpixel((512, 266)) == (0, 0, 0),
      "la seconda, mai arrivata, e' nera")
esigi(fuori.getpixel((512, 522)) == (0, 0, 200),
      "e la terza **non** e' salita al posto suo")


# ------------------------------------------------------------------- arbitro

sep("5. L'orologio sta in cima e non concorre")

clock = Finta("clock", 10, (255, 140, 26))
radar = Finta("air_radar", 60, (0, 200, 255))
meteo = Finta("meteo", 54, (120, 120, 255), gruppo="turni")
cielo = Finta("cielo", 40, (80, 80, 200), gruppo="turni")
inutili = Finta("inutili", 49, (200, 200, 80), gruppo="turni")
media = Finta("mediaplayer", 50, (0, 255, 0))
doom = Finta("doom", 0, (255, 0, 0), in_fascia=False)
a = arbitro([clock, radar, meteo, cielo, inutili, media, doom])

clock.acceso = True
esigi(nomi(a.fasce_scelte(3)) == ["clock", None, None],
      "solo l'orologio: fascia 0, le altre vuote")

radar.acceso = True
esigi(nomi(a.fasce_scelte(3)) == ["clock", "air_radar", None],
      "arriva un aereo: sotto l'orologio")

media.acceso = True
esigi(nomi(a.fasce_scelte(3)) == ["clock", "air_radar", "mediaplayer"],
      "e il Media Player prende la terza")


sep("6. Le fasce non cambiano posto")

radar.acceso = False
esigi(nomi(a.fasce_scelte(3)) == ["clock", None, "mediaplayer"],
      "l'aereo se ne va: il Media Player **resta** dov'era")

meteo.acceso = True
esigi(nomi(a.fasce_scelte(3)) == ["clock", "meteo", "mediaplayer"],
      "e il posto libero va al prossimo, non a chi era sotto")

radar.acceso = True
esigi(nomi(a.fasce_scelte(3)) == ["clock", "meteo", "mediaplayer"],
      "l'aereo torna ma non ci sono posti: aspetta, non scavalca")

media.acceso = False
esigi(nomi(a.fasce_scelte(3)) == ["clock", "meteo", "air_radar"],
      "si libera la terza e la prende lui, che e' il piu' alto in attesa")


sep("7. Il carosello dei turni sta in una fascia sola")

meteo.acceso = False
inutili.acceso = True
esigi(nomi(a.fasce_scelte(3)) == ["clock", "inutili", "air_radar"],
      "finito il meteo tocca a Info inutili, **nella stessa fascia**")
inutili.acceso = False
cielo.acceso = True
esigi(nomi(a.fasce_scelte(3)) == ["clock", "cielo", "air_radar"],
      "poi al cielo, sempre li': per l'occhio e' una fascia che cambia "
      "argomento")
esigi(meteo.gruppo == cielo.gruppo == inutili.gruppo == "turni",
      "e il motivo e' che condividono un gruppo, non una priorita'")


sep("8. Chi tiene la presa copre tutto")

a.hold_on("doom")
esigi(a.fasce_scelte(3) is None,
      "con la presa non ci sono fasce: schermo intero a chi l'ha presa")
a.hold_off()
esigi(a.fasce_scelte(3) is not None, "rilasciata, si torna alle fasce")

doom.acceso = True
scelte = a.fasce_scelte(3)
esigi("doom" not in nomi(scelte),
      "e una sorgente interattiva non entra in fascia nemmeno senza presa")
doom.acceso = False

a.cfg["arbiter"]["force_source"] = "meteo"
esigi(a.fasce_scelte(3) is None,
      "una sorgente forzata a mano vuole lo schermo, non un terzo di schermo")
a.cfg["arbiter"]["force_source"] = "auto"


sep("9. Una fascia sola vuol dire nessuna fascia")

esigi(a.fasce_scelte(1) is None,
      "con una fascia si torna al ciclo di sempre")
esigi(a.fasce_scelte(0) is None, "e con zero pure")


sep("10. L'uscita dichiara quante fasce ha")

cfg = dmdconf.load()
cfg["video"]["uscita"] = "schermo"


class Superficie:
    def __init__(self, largo, alto):
        self.width, self.height = largo, alto
        self.visti = []

    def mostra(self, immagine):
        self.visti.append(immagine.copy())


piattaforma._forza({"famiglia": "pc", "modello": "PC", "numero": "",
                    "pannello": False})
cfg["video"]["modo"] = "auto"
cfg["video"]["fasce"] = "auto"
schermo = display.DisplaySchermo(cfg, superficie=Superficie(1024, 768))
esigi(schermo.fasce == 3, "su 1024x768 lo schermo dichiara tre fasce (%s)"
      % schermo.fasce)
cfg["video"]["modo"] = "singola"
schermo2 = display.DisplaySchermo(cfg, superficie=Superficie(1024, 768))
esigi(schermo2.fasce == 1,
      "«singola» ne vuole una sola anche dove ce ne starebbero tre")
cfg["video"]["modo"] = "auto"
esigi(display.DisplayAssente(cfg).fasce == 1,
      "e senza uscita video la domanda non si pone")

schermo.mostra_fasce([Image.new("RGB", TELA, (200, 0, 0)), None, None])
esigi(schermo._superficie.visti
      and schermo._superficie.visti[-1].size == (1024, 768),
      "e quello che finisce sulla superficie e' grande come lo schermo")


print()
print("=" * 74)
falliti = [m for ok, m in esiti if not ok]
if falliti:
    print("FALLITI %d su %d" % (len(falliti), len(esiti)))
    for m in falliti:
        print("  - %s" % m)
    sys.exit(1)
print("TUTTO BENE: %d prove" % len(esiti))
