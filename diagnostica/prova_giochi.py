# -*- coding: utf-8 -*-
"""17.4 - I giochi su una tela qualunque, senza cambiare di un pixel sul pannello.

Cosa prova questo file
----------------------
La parte della 17.4 che si puo' provare senza guardare lo schermo: la
geometria. I giochi hanno sempre disegnato su 256x64 con il campo nelle 200
colonne di sinistra e il tabellone nelle 56 di destra, e quelle misure erano
costanti di modulo che tutti e tredici importavano. Adesso sono stato
dell'istanza, e un gioco puo' ricevere una tela alta.

Le due cose su cui insiste
--------------------------
* **sul pannello non cambia niente.** Non «quasi niente»: ogni misura di ogni
  gioco convertito deve tornare esattamente il numero che era. E' la regola
  che rende sicura una conversione fatta un gioco per volta, e si prova
  numero per numero;
* **su una tela alta il campo si prende tutto.** Il tabellone passa da
  colonna di destra a striscia in alto, il campo guadagna le 56 colonne e
  tutte le righe in piu', e quello che si disegna arriva davvero fino in
  fondo -- non resta una striscia da pannello in mezzo al nero.

Si lancia da sola:

    python3 diagnostica/prova_giochi.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image                                     # noqa: E402

from sources.giochi import base                           # noqa: E402
from sources.giochi.serpente import Serpente              # noqa: E402
from sources.giochi.mattoni import Mattoni                # noqa: E402

esiti = []


def esigi(condizione, messaggio):
    esiti.append((bool(condizione), messaggio))
    print("%-4s %s" % ("OK" if condizione else "FALLITO", messaggio))


def sep(titolo):
    print()
    print("=" * 74)
    print(titolo)
    print("=" * 74)


def gioca(classe, passi, tela=None, seme=7, tasti=("fuoco",)):
    g = classe()
    if tela:
        g.configura_tela(*tela)
    g.avvia_partita(seme)
    for _ in range(passi):
        g.passo(1 / 30.0, set(tasti))
    return g


ALTA = (256, 192)


sep("1. Il campo e il tabellone")

for classe in (Serpente, Mattoni):
    g = classe()
    esigi((g.largo, g.alto) == (256, 64),
          "%s: di serie la tela e' quella del pannello" % g.nome)
    esigi((g.campo_x, g.campo_y, g.campo_l, g.campo_a) == (0, 0, 200, 64),
          "%s: e il campo e' le 200 colonne di sinistra" % g.nome)
    esigi(g.hud_in_alto is False,
          "%s: il tabellone sta nella colonna di destra" % g.nome)

    g = classe()
    g.configura_tela(*ALTA)
    esigi((g.campo_x, g.campo_y) == (0, base.STRISCIA),
          "%s: su una tela alta il campo comincia sotto la striscia" % g.nome)
    esigi((g.campo_l, g.campo_a) == (256, 192 - base.STRISCIA),
          "%s: e prende tutte le colonne e tutte le righe che restano"
          % g.nome)
    esigi(g.hud_in_alto is True,
          "%s: il tabellone e' passato in alto" % g.nome)

g = Serpente()
g.configura_tela(256, base.ALTA_DA - 1)
esigi(g.hud_in_alto is False,
      "sotto le %d righe il tabellone resta a destra" % base.ALTA_DA)
g.configura_tela(256, base.ALTA_DA)
esigi(g.hud_in_alto is True,
      "da %d in su passa in alto" % base.ALTA_DA)


sep("2. Sul pannello non cambia un numero")

g = Serpente()
esigi((g.lato, g.colonne, g.righe, g.corpo_lato) == (4, 49, 15, 3),
      "serpente: casella 4, griglia 49x15, corpo 3 -- come dalla 9.0")
esigi((g.griglia_x, g.griglia_y) == (2, 2),
      "serpente: e la griglia appoggiata al margine di due pixel")

m = Mattoni()
esigi((m.mattone_l, m.mattone_h) == (19.0, 3.0),
      "mattoni: il mattone e' 19x3")
esigi((m.muro_x, m.muro_y) == (5.0, 6.0),
      "mattoni: il muro comincia a (5, 6)")
esigi((m.racchetta_l, m.racchetta_h, m.racchetta_y) == (22.0, 2, 60.0),
      "mattoni: la racchetta e' 22x2 sulla riga 60")
esigi((m.palla, m.racchetta_v) == (2, 88.0),
      "mattoni: la palla e' 2x2 e la racchetta fa 88 pixel al secondo")
esigi((m.fuga_x, m.fuga_y) == (1, 1),
      "mattoni: un pixel di fuga fra un mattone e l'altro")
esigi((m.fx, m.fy) == (1.0, 1.0),
      "mattoni: i due fattori valgono uno, che e' il punto di tutto")


sep("3. La stessa partita, sulle due tele")

# Gli stessi comandi e lo stesso seme devono dare lo stesso **gioco**: non gli
# stessi pixel -- il campo e' piu' grande -- ma gli stessi mattoni rotti negli
# stessi rimbalzi. E' la prova che l'angolo si conserva in proporzione al
# campo invece che in radianti: tenendo i radianti, su un campo tre volte piu'
# alto la palla seguirebbe un'altra strada e romperebbe altri mattoni.
pannello = gioca(Mattoni, 150)
alta = gioca(Mattoni, 150, ALTA)
esigi(pannello.punteggio == alta.punteggio,
      "mattoni: stesso punteggio dopo centocinquanta passi (%d e %d)"
      % (pannello.punteggio, alta.punteggio))
esigi(pannello.rimasti() == alta.rimasti(),
      "mattoni: e gli stessi mattoni rotti (%d e %d rimasti)"
      % (pannello.rimasti(), alta.rimasti()))
esigi(abs(pannello.bx / 200.0 - alta.bx / alta.campo_l) < 0.02
      and abs(pannello.by / 64.0 - alta.by / alta.campo_a) < 0.02,
      "mattoni: e la palla sta nello stesso punto del campo, in proporzione")


sep("4. Su una tela alta si disegna davvero fino in fondo")


def riempimento(img, campo):
    """Quanto del campo e' stato toccato, in alto e in basso."""
    x, y, largo, alto = campo
    dentro = img.crop((x, y, x + largo, y + alto)).getbbox()
    return dentro


for classe in (Serpente, Mattoni):
    g = gioca(classe, 120, ALTA)
    img = g.disegna()
    esigi(img.size == ALTA,
          "%s: il fotogramma e' grande quanto la tela" % g.nome)
    dentro = riempimento(img, (g.campo_x, g.campo_y, g.campo_l, g.campo_a))
    esigi(dentro is not None and dentro[2] > g.campo_l * 0.9,
          "%s: il disegno arriva al bordo destro del campo" % g.nome)
    esigi(dentro is not None and dentro[3] > g.campo_a * 0.85,
          "%s: e arriva in fondo, invece di restare una striscia in mezzo"
          % g.nome)
    # La striscia del tabellone: ci deve essere qualcosa, e sotto la riga
    # di separazione.
    striscia = img.crop((0, 0, img.width, base.STRISCIA)).getbbox()
    esigi(striscia is not None,
          "%s: la striscia del tabellone non e' vuota" % g.nome)

g = gioca(Mattoni, 120)
img = g.disegna()
esigi(img.size == (256, 64), "sul pannello il fotogramma resta 256x64")
colonna = img.crop((200, 0, 256, 64)).getbbox()
esigi(colonna is not None,
      "e il tabellone e' ancora nelle 56 colonne di destra")


sep("5. «GAME OVER» al centro del campo")

g = Mattoni()
g.finita = True
img = g.disegna()
righe = [y for y in range(img.height)
         if any(img.getpixel((x, y)) != (0, 0, 0) for x in range(200))]
esigi(27 in righe and 35 in righe,
      "sul pannello sta sulle righe 27 e 35, dove e' sempre stato")

g = Mattoni()
g.configura_tela(*ALTA)
g.finita = True
img = g.disegna()
meta = g.campo_y + g.campo_a // 2
righe = [y for y in range(img.height)
         if any(img.getpixel((x, y)) != (0, 0, 0) for x in range(img.width))]
esigi(any(abs(y - meta) <= 8 for y in righe),
      "su una tela alta scende al centro del campo, non resta in cima")


sep("6. Il taglio ai bordi segue la tela")

# Fino alla 17.3 `_riga_di_bit` tagliava sulle costanti 256x64: qualunque
# scritta sotto la riga 64 spariva **in silenzio**, che e' il modo peggiore
# di rompersi.
img = Image.new("RGB", (256, 192))
base.imposta_tela(256, 192)
base.scrivi(img.load(), "PROVA", 4, 150, (255, 255, 255))
esigi(img.crop((0, 145, 256, 160)).getbbox() is not None,
      "una scritta alla riga 150 di una tela da 192 si vede")

img = Image.new("RGB", (256, 64))
base.imposta_tela(256, 64)
base.scrivi(img.load(), "PROVA", 4, 150, (255, 255, 255))
esigi(img.getbbox() is None,
      "e sul pannello la stessa scritta non fa cadere il disegno")

base.imposta_tela(256, 64)
esigi(base._CAMPO[2] == 200,
      "«centra» senza argomenti si centra sul campo, che sul pannello e' 200")


print()
print("=" * 74)
falliti = [m for ok, m in esiti if not ok]
if falliti:
    print("FALLITI %d su %d" % (len(falliti), len(esiti)))
    for m in falliti:
        print("  - %s" % m)
    sys.exit(1)
print("TUTTO BENE: %d prove" % len(esiti))
