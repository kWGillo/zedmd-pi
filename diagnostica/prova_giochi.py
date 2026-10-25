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
from sources.giochi.pongo import Pongo                    # noqa: E402
from sources.giochi.trex import TRex                      # noqa: E402
from sources.giochi.mine import Mine                      # noqa: E402
from sources.giochi.bongo import Bongo                    # noqa: E402
from sources.giochi.invasori import Invasori              # noqa: E402
from sources.giochi.squadriglia import Squadriglia        # noqa: E402
from sources.giochi.quiz import Quiz                      # noqa: E402
from sources.giochi.gnam import Gnam                      # noqa: E402

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
COLONNE_ATTESE = 8        # le colonne di Invasori, che non cambiano


sep("1. Il campo e il tabellone")

for classe in (Serpente, Mattoni, Pongo, TRex, Mine, Bongo, Invasori,
               Squadriglia, Quiz, Gnam):
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


sep("6-bis. Pongo e T-Rex (17.4.2)")

p = Pongo()
esigi((p.racchetta_l, p.racchetta_h) == (2, 12),
      "pongo: la racchetta e' 2x12")
esigi((int(p.x_sinistra), int(p.x_avanti), int(p.x_destra)) == (4, 62, 250),
      "pongo: le colonne sono 4, 62 e 250")
esigi((p.palla, p.corpo_punti) == (2, 2),
      "pongo: pallina 2x2 e punti al doppio, come dalla 12.0")

pa = gioca(Pongo, 200)
al = gioca(Pongo, 200, ALTA)
esigi((pa.tu, pa.cpu) == (al.tu, al.cpu),
      "pongo: stesso punteggio sulle due tele (%d-%d e %d-%d)"
      % (pa.tu, pa.cpu, al.tu, al.cpu))

t = TRex()
esigi((t.z, t.largo_u, t.alto_u) == (1, 256, 64),
      "trex: sul pannello il mondo e' 256x64 a zoom uno")
esigi((t.suolo_u, t.cima_u) == (58, 7),
      "trex: la pista sta sulla riga 58, come sempre")

t = TRex()
t.configura_tela(*ALTA)
esigi(t.z == 2 and (t.largo_u, t.alto_u) == (128, 96),
      "trex: su una tela alta zoom due, e la finestra sul mondo e' 128x96")
esigi(t.z <= TRex.ZOOM_MAX,
      "trex: lo zoom non supera il massimo, se no non si fa in tempo a saltare")

pa = gioca(TRex, 200)
al = gioca(TRex, 200, ALTA)
esigi(pa.punteggio == al.punteggio,
      "trex: stesso punteggio dopo duecento passi (%d e %d) -- il mondo e'"
      " lo stesso, cambia solo quanto se ne vede"
      % (pa.punteggio, al.punteggio))


sep("6-ter. Mine vaganti e Kingo Bongo (17.4.3)")

m = Mine()
esigi((m.z, m.largo_u, m.alto_u) == (1, 256, 57),
      "mine: sul pannello il campo e' 256x57 a zoom uno")
esigi(abs(m.schiaccia - 0.6) < 1e-9 and m.semi_quanti == 21,
      "mine: schiacciamento 0,6 e ventuno semi, come sempre")

m = Mine()
m.configura_tela(*ALTA)
esigi(m.z == 2 and m.alto_u > m.largo_u / 2,
      "mine: su una tela alta zoom due, e il campo diventa quasi quadrato")
esigi(abs(m.schiaccia - 1.0) < 1e-9,
      "mine: e lo schiacciamento verticale sparisce, che li' non serve piu'")

pa = gioca(Mine, 150)
al = gioca(Mine, 150, ALTA)
esigi(pa.punteggio == al.punteggio and len(pa.mine) == len(al.mine),
      "mine: stessa partita sulle due tele (%d punti, %d mine)"
      % (pa.punteggio, len(pa.mine)))


def tetti(gioco):
    return sorted(c for _x, _l, c in gioco.citta.palazzi)


# Lo stesso seme sulle due tele: la citta' la tira a sorte il gioco, e due
# citta' diverse non si possono confrontare. (Senza seme questa prova
# falliva una volta ogni tanto -- raramente abbastanza da sembrare un
# dispetto, abbastanza spesso da non potersene fidare.)
SEME_BONGO = 20251025

b = Bongo()
b.avvia_partita(SEME_BONGO)
esigi((b.cima, b.fondo, b.piu_basso) == (7, 63, 3),
      "bongo: sul pannello la strada e' la riga 63 e il palazzo piu' basso"
      " e' di tre righe")
esigi(len(b.citta.stelle) == 26, "bongo: e le stelle sono ventisei")
profilo_pannello = tetti(b)

b = Bongo()
b.configura_tela(*ALTA)
b.avvia_partita(SEME_BONGO)
esigi(b.fondo == 191 and b.piu_basso > 100,
      "bongo: su una tela alta la strada scende in fondo e i palazzi si"
      " allungano (il piu' basso e' di %d righe)" % b.piu_basso)
profilo_alto = tetti(b)
esigi(abs((profilo_pannello[-1] - profilo_pannello[0])
          - (profilo_alto[-1] - profilo_alto[0])) <= 6,
      "bongo: il **dislivello** fra i tetti resta quello -- ed e' l'unica"
      " cosa che conta in una parabola")
cielo = profilo_alto[0] - b.cima
esigi(24 <= cielo <= 60,
      "bongo: il cielo sopra il tetto piu' alto cresce ma resta una fascia"
      " (%d righe): se crescesse quanto la tela, la banana non ci"
      " arriverebbe piu'" % cielo)
esigi(len(b.citta.stelle) > 26,
      "bongo: e le stelle crescono col cielo, se no si dirada")


sep("6-quater. Invasori (17.4.5)")

i = Invasori()
esigi(i.file == 3 and i.tipi == Invasori.TIPI_TRE,
      "invasori: sul pannello tre file, che e' quello che ci sta su 64 righe")
esigi((i.passo_x, i.passo_y) == (18.0, 10.0),
      "invasori: passo 18x10")
esigi((i.y_nave, i.bunker_y) == (58.0, 46.0),
      "invasori: la nave sulla riga 58 e i ripari sulla 46")
esigi((i.bunker_largo, i.bunker_alto) == (14, 5)
      and (i.passo_lato, i.discesa) == (2, 2),
      "invasori: ripari 14x5, passo di lato 2, discesa 2")

i = Invasori()
i.configura_tela(*ALTA)
esigi(i.file == 5 and i.tipi == Invasori.TIPI_CINQUE,
      "invasori: su una tela alta tornano le cinque file del cabinato, con"
      " i tipi dell'originale")
largo_schiera = (COLONNE_ATTESE - 1) * i.passo_x + 8
esigi(largo_schiera < i.campo_l - 16,
      "invasori: e la schiera ha ancora dove muoversi di lato (%d su %d)"
      % (largo_schiera, i.campo_l))
fondo = i.ay + (i.file - 1) * i.passo_y + 5
esigi(fondo < i.bunker_y,
      "invasori: all'inizio la schiera sta tutta sopra i ripari")
esigi(i.passo_lato >= 2 and i.discesa >= 2,
      "invasori: il passo di lato e la discesa restano interi e non si"
      " fermano a zero")

# Qui **non** si pretende la stessa partita: con cinque file invece di tre
# il gioco e' un altro apposta. Si pretende che sia giocabile.
al = gioca(Invasori, 200, ALTA)
esigi(al.vivi() < COLONNE_ATTESE * 5,
      "invasori: dopo duecento passi qualche alieno e' stato colpito (%d vivi"
      " su %d)" % (al.vivi(), COLONNE_ATTESE * 5))


sep("6-quinquies. Squadriglia (17.4.8)")

q = Squadriglia()
esigi((q.z, q.largo_u, q.alto_u) == (1, 256, 64),
      "squadriglia: sul pannello il mondo e' 256x64 a zoom uno")
esigi((q.cima_u, q.alto_campo) == (8, 56),
      "squadriglia: con la striscia da otto righe e il mare sotto")
esigi(q.x_massima == 120 and q.quante_onde == 26,
      "squadriglia: non si passa la colonna 120, e le onde sono ventisei")

q = Squadriglia()
q.configura_tela(*ALTA)
esigi(q.z == 2 and (q.largo_u, q.alto_u) == (128, 96),
      "squadriglia: su una tela alta zoom due, mondo 128x96")
esigi(abs(q.x_massima - 60) < 1,
      "squadriglia: e il limite di avanzata segue la larghezza del mondo"
      " (%.0f invece di 120): su 128 unita' la colonna 120 sarebbe il cielo"
      " nemico" % q.x_massima)
esigi(q.quante_onde > 8,
      "squadriglia: le onde seguono l'area del mare, non il numero")

pa = gioca(Squadriglia, 240)
al = gioca(Squadriglia, 240, ALTA)
esigi(pa.iniziata and al.iniziata,
      "squadriglia: la partita parte su tutte e due le tele")
esigi(al.x < al.x_massima and al.cima_u <= al.y <= al.alto_u,
      "squadriglia: e il tuo aereo resta dentro il mondo")


sep("6-sexies. Super Quiz e Gnam (17.4.9)")

q = Quiz()
esigi(q.s == 1 and q.per_riga == 62 and q.colonne_risposte == 2,
      "quiz: sul pannello testo a scala uno, 62 caratteri, due colonne")
esigi(q.L["domanda"] == 10 and q.L["risposte"] == 28,
      "quiz: e le righe di sempre")

q = Quiz()
q.configura_tela(*ALTA)
esigi(q.s == 2, "quiz: su una tela alta il testo si scrive al doppio")
esigi(q.per_riga == 30,
      "quiz: trenta caratteri per riga invece di sessantadue (%d)"
      % q.per_riga)
esigi(q.colonne_risposte == 1,
      "quiz: e le quattro risposte tornano in colonna sola, piu' larghe")
ultima = q.L["risposte"] + 3 * q.L["passo_risposte"] + base.RIGA * q.s
esigi(ultima < q.L["conferma"],
      "quiz: la quarta risposta sta sopra la riga della conferma (%d < %d)"
      % (ultima, q.L["conferma"]))
esigi(q.L["barra"] + q.L["alta_barra"] <= q.alto,
      "quiz: e la barra del tempo sta dentro la tela")

# Il font che si ingrandisce replicando, non interpolando.
prova = Image.new("RGB", (64, 32))
base.imposta_tela(64, 32)
base.scrivi(prova.load(), "A", 1, 1, (255, 255, 255), 2)
dentro = prova.getbbox()
esigi(dentro is not None and (dentro[3] - dentro[1]) == base.ALTO * 2,
      "il font a scala due e' alto il doppio, esatto")
esigi(base.larghezza_testo("ABC", 2) == base.larghezza_testo("ABC") * 2,
      "e la misura del testo segue la scala")

g = Gnam()
esigi(g.casella == 4 and (g.lab_largo, g.lab_alto) == (200, 64),
      "gnam: sul pannello la casella e' quattro e il labirinto 200x64")
esigi((g.lab_x, g.lab_y) == (0, 0),
      "gnam: appoggiato all'angolo, come sempre")

g = Gnam()
g.configura_tela(*ALTA)
esigi(g.casella == 5,
      "gnam: su 256 colonne la casella arriva a cinque e non oltre -- a sei"
      " le cinquanta colonne del labirinto farebbero trecento pixel")
esigi(g.lab_largo <= g.campo_l and g.lab_alto <= g.campo_a,
      "gnam: e il labirinto ci sta dentro")
esigi(g.lab_x > 0 and g.lab_y > 0,
      "gnam: centrato in quello che avanza")

pa = gioca(Gnam, 150)
al = gioca(Gnam, 150, ALTA)
esigi(pa.punteggio == al.punteggio,
      "gnam: stessa partita sulle due tele (%d e %d) -- il labirinto e' lo"
      " stesso, cambia solo quanto e' grande una casella"
      % (pa.punteggio, al.punteggio))


sep("7. La tela arriva davvero fino al gioco (17.4.1)")

# Il difetto della 17.4: le fondamenta erano giuste, i due giochi convertiti
# erano giusti, e sullo schermo non cambiava niente -- perche' a
# `GiochiSource` si passava `display.width/height`, cioe' la tela del DMD,
# 256x64 anche su un monitor. Si prova il percorso intero, non i pezzi.

from sources.giochi import GiochiSource                   # noqa: E402

cfg_finta = {"giochi": {}, "video": {}, "web": {}, "lingua": "it"}
sorgente = GiochiSource(cfg_finta, 256, 192)
esigi((sorgente.width, sorgente.height) == (256, 192),
      "la sorgente dei giochi tiene la misura che le viene data")

sorgente._gioco = Serpente()
tela = getattr(sorgente._gioco, "configura_tela", None)
tela(sorgente.width, sorgente.height)
esigi((sorgente._gioco.largo, sorgente._gioco.alto) == (256, 192),
      "e il gioco la riceve per intero")

# E la riga che la passa. Si legge il sorgente invece di costruire tutto
# `dmdd`: e' quella riga che e' stata sbagliata, ed e' quella che si guarda.
sorgente_dmdd = open(os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "dmdd.py")).read()
esigi("GiochiSource(self.cfg, tela_piena[0], tela_piena[1]," in sorgente_dmdd,
      "dmdd costruisce i giochi con la tela piena, come Doom e il Game Boy")


sep("8. La lingua del pannello, non quella del browser (17.4.14)")

# *«Il gioco Quiz time ora e' in inglese e non piu' in italiano.»* E' lo
# stesso difetto della 17.4.10 -- il meteo che diceva «Tomorrow» -- un piano
# piu' sotto: `web.language` e' la lingua dell'**interfaccia** e di serie e'
# **vuota**, perche' vuol dire «decidila dal browser». Passata a
# `i18n.resolve` senza preferenza e senza browser, quella vuota diventa
# `FALLBACK`, cioe' inglese -- e Super Quiz faceva le domande in inglese su
# un pannello configurato in italiano.

import i18n                                               # noqa: E402

from sources.base import lingua_del_pannello              # noqa: E402

CASI = [
    ({"clock": {"language": "it"}, "web": {"language": ""}}, "it",
     "di serie: il pannello e' in italiano, la web UI «decidi tu»"),
    ({"clock": {"language": "it"}, "web": {"language": "en"}}, "it",
     "l'interfaccia in inglese **non** porta il pannello in inglese"),
    ({"clock": {"language": "en"}, "web": {"language": ""}}, "en",
     "e un pannello in inglese parla inglese"),
    ({"clock": {"language": ""}, "web": {"language": "it"}}, "it",
     "senza lingua del pannello vale quella dell'interfaccia"),
    ({"clock": {}, "web": {}}, i18n.FALLBACK,
     "e senza niente resta il ripiego dichiarato"),
]
for conf, atteso, perche in CASI:
    esigi(lingua_del_pannello(conf) == atteso,
          "%s (%s)" % (perche, lingua_del_pannello(conf)))

# E il quiz la chiede da li', non a `i18n.resolve`.
quiz_it = GiochiSource({"giochi": {}, "video": {},
                        "clock": {"language": "it"}, "web": {"language": ""}},
                       256, 64)
quiz_en = GiochiSource({"giochi": {}, "video": {},
                        "clock": {"language": "en"}, "web": {"language": ""}},
                       256, 64)
esigi(quiz_it.lingua() == "it" and quiz_en.lingua() == "en",
      "i giochi parlano la lingua del pannello (%s e %s)"
      % (quiz_it.lingua(), quiz_en.lingua()))

# La banca delle domande segue, che e' il punto della segnalazione.
from sources.giochi.quiz import Quiz                       # noqa: E402

q = Quiz()
q.configura_lingua(quiz_it.lingua())
q.avvia_partita(7)
esigi(q.lingua == "it",
      "e Super Quiz pesca dalla banca italiana")

# Nessuno chiede piu' la lingua del pannello a `i18n.resolve`: senza
# preferenza salvata quella funzione risponde inglese, ed e' giusto cosi' --
# e' fatta per una richiesta web, dove c'e' un browser da interrogare.
# Si guarda il codice, non il testo: della parola dentro un commento non
# importa niente -- la spiegazione del difetto la nomina apposta.
import ast                                                 # noqa: E402
import glob                                                # noqa: E402

radice = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
colpevoli = []
for percorso in glob.glob(os.path.join(radice, "sources", "**", "*.py"),
                          recursive=True):
    albero = ast.parse(open(percorso, encoding="utf-8").read())
    for nodo in ast.walk(albero):
        if (isinstance(nodo, ast.Attribute) and nodo.attr == "resolve"
                and isinstance(nodo.value, ast.Name)
                and nodo.value.id == "i18n"):
            colpevoli.append(os.path.basename(percorso))
            break
esigi(not colpevoli,
      "nessuna sorgente chiede la lingua del pannello a i18n.resolve (%s)"
      % (", ".join(colpevoli) or "nessuna"))

print()
print("=" * 74)
falliti = [m for ok, m in esiti if not ok]
if falliti:
    print("FALLITI %d su %d" % (len(falliti), len(esiti)))
    for m in falliti:
        print("  - %s" % m)
    sys.exit(1)
print("TUTTO BENE: %d prove" % len(esiti))
