#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rigenera gli effetti sonori dei giochi che sono stati fatti con un calcolo.

Perche' questo file esiste
--------------------------
Gli effetti stanno in `suoni/` come wav, e un wav e' un file opaco: fra un
anno, se uno volesse un `mangia` un filo piu' acuto, dovrebbe aprire un
editor audio e andare a orecchio. Qui invece c'e' la **ricetta** -- forma
d'onda, frequenze, inviluppo, durata -- e rifarli e' un comando.

Non tocca i file che c'erano prima. Quelli di Breakout e Invaders sono stati
fatti in un altro modo e hanno un loro carattere: rigenerarli da qui vorrebbe
dire cambiarli, e cambiare un suono che va bene non e' un miglioramento.

Il formato non e' una scelta libera
-----------------------------------
Il mixer degli effetti (`suoni.Mixer`) somma i campioni in memoria senza
convertire niente: accetta **solo** 22050 Hz, mono, 16 bit. Un wav diverso
viene semplicemente ignorato -- `_carica` torna None -- e il gioco resta muto
su quell'effetto senza dire perche'. Quindi la costante qui sotto e' un
requisito, non una preferenza.

Uso:
    python3 diagnostica/genera_suoni.py [cartella]
"""

import math
import os
import struct
import sys
import wave

FREQUENZA = 22050          # deve coincidere con suoni.FREQ_EFFETTI
PICCO = 16000              # sotto i 18939 dei mattoni: mangiare non e' rompere


def _quadra(fase):
    """Onda quadra. E' il timbro del resto del progetto, e non e' nostalgia:
    su una cassa piccola una sinusoide di cinquanta millesimi si sente appena,
    una quadra ha le armoniche che la rendono udibile anche piano."""
    return 1.0 if (fase % 1.0) < 0.5 else -1.0


def nota(durata, da_hz, a_hz, attacco=0.004, coda=0.5):
    """Campioni di una nota che scivola da una frequenza all'altra.

    `coda` e' la frazione finale su cui il suono si spegne. L'attacco corto
    ma non nullo serve a togliere lo schiocco del primo campione, che su una
    quadra e' un salto a fondo scala.
    """
    quanti = int(FREQUENZA * durata)
    fuori = []
    fase = 0.0
    for i in range(quanti):
        avanzamento = i / float(quanti)
        hz = da_hz + (a_hz - da_hz) * avanzamento
        fase += hz / FREQUENZA
        ampiezza = 1.0
        inizio = int(FREQUENZA * attacco)
        if i < inizio:
            ampiezza = i / float(inizio)
        resta = 1.0 - avanzamento
        if resta < coda:
            ampiezza *= resta / coda
        fuori.append(_quadra(fase) * ampiezza)
    return fuori


def scrivi(percorso, campioni, picco=PICCO):
    massimo = max(abs(v) for v in campioni) or 1.0
    scala = picco / massimo
    dati = struct.pack("<%dh" % len(campioni),
                       *[int(max(-32768, min(32767, v * scala)))
                         for v in campioni])
    with wave.open(percorso, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(FREQUENZA)
        w.writeframes(dati)
    return len(campioni)


# Gli effetti del Serpente. Tre `mangia` e non uno: la nota sale man mano che
# il serpente si allunga, ed e' il modo in cui il gioco dice "stai andando
# bene" senza scrivere niente sul pannello. Sono blip di due note in salita --
# la seconda una quinta sopra la prima -- perche' un blip che sale si legge
# come "preso", mentre uno che scende si legge come "sbagliato".
RICETTE = {
    "mangia1": [(0.030, 523, 523), (0.040, 784, 784)],
    "mangia2": [(0.030, 659, 659), (0.040, 988, 988)],
    "mangia3": [(0.030, 784, 784), (0.040, 1175, 1175)],
    # Il muro: un tonfo corto e basso, diverso dai suoni dei mattoni di
    # Breakout perche' qui vuol dire "hai sbagliato", non "hai colpito".
    "tonfo": [(0.075, 196, 110)],
    # Pongo. Le frequenze sono quelle che si attribuiscono al cabinato del
    # 1972 -- un'ottava fra racchetta e sponda -- e le durate sono corte come
    # le sue: il "ping" della racchetta e' il suono del gioco, deve essere
    # secco. Il punto e' la stessa nota, lunga.
    "ping": [(0.035, 490, 490)],
    "sponda": [(0.030, 245, 245)],
    "punto": [(0.050, 490, 490), (0.180, 980, 980)],
    # T-Rex: il salto e' un blip che sale di un'ottava, corto, perche' si
    # sente a ogni ostacolo e non deve stancare.
    "salto": [(0.060, 420, 840)],
}


# ------------------------------------------------------------ la musica

# Il motivo di Gnam Gnam. Scritto apposta per questo progetto: **non** e' la
# musica di Pac-Man, che e' protetta. Pentatonica maggiore, allegro, sedici
# battute -- una A di otto e una B che sale -- e poi ricomincia: con sedici
# battute il giro dura mezzo minuto, abbastanza da non sembrare un disco rotto.
#
# Una riga per battuta, otto crome. `.` pausa, `-` la nota prima continua.
BPM = 132
MELODIA = (
    "E5 G5 A5 G5 E5 D5 C5 D5", "E5 -  G5 E5 D5 .  C5 . ",
    "A4 C5 D5 C5 A4 G4 A4 C5", "D5 -  E5 -  D5 C5 D5 . ",
    "E5 G5 A5 C6 A5 G5 E5 G5", "A5 -  G5 E5 D5 E5 G5 . ",
    "C6 A5 G5 E5 D5 E5 D5 C5", "C5 -  G4 -  C5 .  .  . ",
    "F5 A5 C6 A5 F5 E5 D5 E5", "F5 -  A5 F5 E5 .  D5 . ",
    "G5 B5 D6 B5 G5 F5 E5 F5", "G5 -  .  G5 A5 -  B5 - ",
    "C6 -  G5 E5 C6 -  G5 E5", "D6 C6 B5 A5 G5 -  E5 - ",
    "F5 E5 D5 E5 F5 G5 A5 B5", "C6 -  .  .  G5 .  .  . ",
)
# Il basso: un accordo per mezza battuta, suonato "um-pa" -- la fondamentale
# e la sua ottava, a crome alterne.
ACCORDI = (
    "C C", "C C", "Am Am", "G G", "C C", "Am Am", "F G", "C C",
    "F F", "F F", "G G", "G G", "C C", "G G", "F G", "C G",
)
NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
ALTERAZIONI = {"#": 1, "b": -1}

# Gli accordi si scrivono con la lettera della fondamentale, piu' "m" se sono
# minori: "A" e' La maggiore, "Am" La minore. Serve all'arpeggio, che deve
# sapere se la terza e' maggiore o minore; al basso basta la fondamentale.
GRADI = {"": (0, 4, 7, 12), "m": (0, 3, 7, 12)}
PICCO_MUSICA = 5500        # un terzo degli effetti: la musica sta sotto


def _hz(nome):
    corpo = nome[0]
    resto = nome[1:]
    semitoni = NOTE[corpo]
    while resto and resto[0] in ALTERAZIONI:
        semitoni += ALTERAZIONI[resto[0]]
        resto = resto[1:]
    semitoni += 12 * (int(resto) + 1)
    return 440.0 * 2 ** ((semitoni - 69) / 12.0)


def _accordo(sigla):
    """(fondamentale, modo) da "A" o "Am"."""
    if sigla.endswith("m"):
        return sigla[:-1], "m"
    return sigla, ""


def _hz_grado(sigla, ottava, grado):
    """La nota `grado` dell'accordo (0 fondamentale, 1 terza, 2 quinta,
    3 ottava), nell'ottava data."""
    radice, modo = _accordo(sigla)
    semitoni = GRADI[modo][grado]
    base = _hz(radice + str(ottava))
    return base * 2 ** (semitoni / 12.0)


def musica(bpm=None, melodia=None, accordi=None, forma="quadra25",
           ampiezza_melodia=1.0, basso="umpa", ampiezza_basso=0.9,
           charleston=0.25, rullante=0.0, cassa=0.0, arpeggio=0.0,
           stacco=0.62, seme=7):
    """Compone un brano dalla sua ricetta. Senza argomenti, quello di Gnam Gnam.

    `forma`: il timbro della melodia -- quadra25 (il chip, stretto), quadra50
    (piu' pieno, da fanfara), triangolo (morbido). `basso`: umpa (fondamentale
    e ottava a crome alterne), quarti (la fondamentale sui quarti), ottavi (la
    fondamentale a ogni croma, alternata alla quinta: quello che spinge), lento
    (una nota tenuta per mezza battuta). `charleston` e `rullante`: l'ampiezza
    del fruscio sui controtempi e sul secondo e quarto quarto; `cassa` il colpo
    grave sull'uno e sul tre. `arpeggio`: la seconda voce, l'accordo sgranato
    a sedicesimi -- e' quella che da' il movimento alle sale giochi, e da sola
    vale piu' di dieci battiti in piu' al minuto. `stacco`: quanto le note si
    spengono dentro la loro cella; basso = staccato, secco.
    """
    bpm = bpm or BPM
    melodia = melodia or MELODIA
    accordi = accordi or ACCORDI
    croma = 60.0 / bpm / 2
    per_croma = int(round(FREQUENZA * croma))
    totale = per_croma * 8 * len(melodia)
    fuori = [0.0] * totale

    def suona(inizio, durata, hz, timbro, ampiezza):
        quanti = min(int(durata * per_croma), totale - inizio)
        fase = 0.0
        for i in range(quanti):
            t = i / float(quanti)
            # Attacco corto, poi un calo: le note ripetute si staccano
            # l'una dall'altra invece di fondersi in un fischio.
            inv = (min(1.0, i / 25.0) * (1.0 - stacco * t)
                   * min(1.0, (quanti - i) / 60.0))
            fase = (fase + hz / FREQUENZA) % 1.0
            if timbro == "quadra25":
                v = 1.0 if fase < 0.25 else -1.0      # duty 25%: il timbro chip
            elif timbro == "quadra50":
                v = 1.0 if fase < 0.5 else -1.0
            else:
                v = 4.0 * abs(fase - 0.5) - 1.0        # triangolo
            fuori[inizio + i] += v * inv * ampiezza

    # la melodia
    for b, riga in enumerate(melodia):
        celle = riga.split()
        j = 0
        while j < 8:
            nota = celle[j]
            durata = 1
            while j + durata < 8 and celle[j + durata] == "-":
                durata += 1
            if nota not in (".", "-"):
                suona((b * 8 + j) * per_croma, durata, _hz(nota), forma,
                      ampiezza_melodia)
            j += durata
    # il basso
    #
    # `radice` qui e' la **sigla** dell'accordo, «Am» e non «A»: prima di
    # chiederne la frequenza va tolto il modo. Fino alla 12.6 tre rami su
    # quattro lo facevano e uno no, e non se ne accorgeva nessuno perche'
    # nessuna ricetta usava insieme un accordo minore e un basso lungo. La
    # prima che l'ha fatto -- la musica della risposta sbagliata -- e' morta
    # con «invalid literal for int(): 'm3'».
    for b, riga in enumerate(accordi):
        for meta, sigla in enumerate(riga.split()):
            radice = _accordo(sigla)[0]
            inizio = (b * 8 + meta * 4) * per_croma
            if basso == "umpa":
                for k in range(4):
                    ottava = 3 if k % 2 == 0 else 4
                    suona(inizio + k * per_croma, 1, _hz(radice + str(ottava)),
                          "triangolo", ampiezza_basso)
            elif basso == "quarti":
                for k in range(2):
                    suona(inizio + 2 * k * per_croma, 2, _hz(radice + "3"),
                          "triangolo", ampiezza_basso)
            elif basso == "ottavi":
                # Il motore: una nota a ogni croma, fondamentale e quinta
                # alternate. E' il passo che fa muovere la testa.
                for k in range(4):
                    grado = 0 if k % 2 == 0 else 2
                    suona(inizio + k * per_croma, 1,
                          _hz_grado(sigla, 3, grado) * (1.0 if k % 2 == 0 else 0.5),
                          "quadra25", ampiezza_basso)
            else:
                suona(inizio, 4, _hz(radice + "3"), "triangolo", ampiezza_basso)
    # l'arpeggio: l'accordo sgranato a sedicesimi, sopra il basso
    if arpeggio:
        mezza = per_croma // 2
        for b, riga in enumerate(accordi):
            for meta, sigla in enumerate(riga.split()):
                for k in range(8):
                    inizio = (b * 8 + meta * 4) * per_croma + k * mezza
                    grado = (0, 1, 2, 3, 2, 1, 0, 2)[k]
                    suona(inizio, 0.5, _hz_grado(sigla, 4, grado),
                          "quadra25", arpeggio)

    # le percussioni, fatte di fruscio
    import random
    casuale = random.Random(seme)
    for c in range(8 * len(melodia)):
        colpi = []
        if charleston and c % 2 == 1:
            colpi.append((charleston, 0.012))
        if rullante and c % 4 == 2:
            colpi.append((rullante, 0.06))
        for forza, durata in colpi:
            base = c * per_croma
            quanti = int(FREQUENZA * durata)
            for i in range(min(quanti, totale - base)):
                fuori[base + i] += casuale.uniform(-1, 1) * forza * (1 - i / float(quanti))
        # La cassa sull'uno e sul tre: non fruscio ma una sinusoide che
        # scende in fretta, che e' il modo in cui si fa una grancassa con
        # niente. Sotto, tiene insieme tutto il resto.
        if cassa and c % 4 == 0:
            base = c * per_croma
            quanti = int(FREQUENZA * 0.085)
            fase = 0.0
            for i in range(min(quanti, totale - base)):
                t = i / float(quanti)
                hz = 115.0 * (1.0 - t) ** 2 + 42.0
                fase += hz / FREQUENZA
                fuori[base + i] += math.sin(2 * math.pi * fase) * cassa * (1 - t) ** 1.5
    return fuori


# Gli altri giochi, ognuno con il suo carattere. Tutti scritti per questo
# progetto; nessuno riprende una musica esistente. Giri di 16-20 secondi.
MUSICHE = {
    # ------------------------------------------------------ Super Quiz
    #
    # Quattro brani per quattro momenti, e sono il contrario dei brani dei
    # giochi d'azione: qui la musica non deve spingere, deve **far venire il
    # dubbio**. Chi ha visto un quiz in televisione sa gia' come suonano
    # questi quattro momenti, e il compito era scriverli senza copiarne
    # nessuno.
    #
    # La domanda che appare: due accordi che salgono, larghi, con la melodia
    # che arriva dopo -- il momento in cui si apre il sipario.
    "quiz_domanda": dict(
        bpm=96, forma="triangolo", ampiezza_melodia=0.8, basso="lunghi",
        ampiezza_basso=0.8, charleston=0.0, cassa=0.55, arpeggio=0.22,
        stacco=0.35, picco=4200,
        melodia=(
            "C4 -  -  -  E4 -  G4 - ", "C5 -  -  -  -  -  .  . ",
            "A4 -  -  -  C5 -  E5 - ", "D5 -  -  -  -  -  .  . ",
        ),
        accordi=("C C", "C G", "Am Am", "F G")),
    # L'attesa: un pendolo. Due note che si alternano sotto, e sopra quasi
    # niente -- e' il silenzio che fa paura, non la musica. Sedicesimi no:
    # il tempo che passa si sente meglio se il passo e' lento e uguale.
    "quiz_attesa": dict(
        bpm=104, forma="triangolo", ampiezza_melodia=0.85, basso="ottavi",
        ampiezza_basso=0.6, charleston=0.10, cassa=0.35, arpeggio=0.0,
        stacco=0.25, picco=3400,
        melodia=(
            "E4 -  .  .  E4 -  .  . ", "D4 -  .  .  D4 -  .  . ",
            "E4 -  .  .  E4 -  .  . ", "C4 -  .  .  -  -  .  . ",
            "A3 -  .  .  A3 -  .  . ", "B3 -  .  .  B3 -  .  . ",
            "E4 -  .  .  D4 -  .  . ", "A3 -  -  -  .  .  .  . ",
        ),
        accordi=("Am Am", "Dm Dm", "Am Am", "E E",
                 "Am Am", "Dm Dm", "E E", "Am Am")),
    # La risposta giusta: quattro battute e basta, in maggiore, che salgono
    # e si fermano in alto. Deve finire prima che smetta di piacere.
    "quiz_giusta": dict(
        bpm=132, forma="quadra25", ampiezza_melodia=1.0, basso="ottavi",
        ampiezza_basso=0.85, charleston=0.25, rullante=0.30, cassa=0.95,
        arpeggio=0.30, stacco=0.8, picco=5600,
        melodia=(
            "C5 E5 G5 C6 -  -  G5 - ", "A5 -  G5 E5 C5 -  .  . ",
            "F5 A5 C6 F6 -  -  C6 - ", "G5 -  -  -  C6 -  .  . ",
        ),
        accordi=("C C", "Am F", "F F", "G C")),
    # La risposta sbagliata: la stessa melodia che scende invece di salire, e
    # un basso che casca di un semitono. Corta: nessuno vuole restare li'.
    "quiz_sbagliata": dict(
        bpm=100, forma="quadra25", ampiezza_melodia=0.85, basso="lunghi",
        ampiezza_basso=0.9, charleston=0.0, cassa=0.8, arpeggio=0.0,
        stacco=0.5, picco=4800,
        melodia=(
            "C5 -  B4 -  Bb4 -  A4 - ", "Ab4 -  -  -  -  -  .  . ",
            "F4 -  E4 -  Eb4 -  D4 - ", "C4 -  -  -  -  -  .  . ",
        ),
        accordi=("Am Am", "Ab Ab", "Dm Dm", "Am Am")),

    # Breakout: il piu' veloce di tutti. La minore, sedicesimi di arpeggio
    # sotto la melodia, cassa e rullante: e' un gioco di riflessi e la
    # musica deve spingere, non accompagnare.
    "breakout_musica": dict(
        bpm=168, forma="quadra25", ampiezza_melodia=0.9, basso="ottavi",
        ampiezza_basso=0.85, charleston=0.22, rullante=0.34, cassa=1.0,
        arpeggio=0.30, stacco=0.7, picco=6000,
        melodia=(
            "A4 C5 E5 A5 E5 C5 E5 G5", "F5 E5 D5 C5 D5 E5 .  . ",
            "D5 F5 A5 D6 A5 F5 A5 C6", "B5 A5 G5 F5 E5 -  .  . ",
            "A4 C5 E5 A5 E5 C5 E5 G5", "A5 -  G5 E5 D5 C5 B4 D5",
            "C5 E5 G5 C6 G5 E5 G5 B5", "A5 -  E5 -  A4 -  .  . ",
            "E5 E5 G5 E5 A5 G5 E5 D5", "C5 D5 E5 G5 A5 -  G5 E5",
            "D5 F5 A5 D6 C6 A5 G5 F5", "E5 -  -  -  A4 -  .  . ",
        ),
        accordi=("Am Am", "F G", "Dm Dm", "E E", "Am Am", "Am G",
                 "C C", "Am E", "Am Am", "F G", "Dm Dm", "E E")),
    # Invaders: la marcia degli alieni e' il ritmo, e non si tocca. Sotto
    # pero' c'e' un motore: basso a ottavi e cassa sull'uno e sul tre, che
    # spinge senza mettersi davanti. Niente rullante, per non litigare.
    "invaders_musica": dict(
        bpm=152, forma="quadra25", ampiezza_melodia=0.75, basso="ottavi",
        ampiezza_basso=0.9, charleston=0.08, cassa=0.95, arpeggio=0.16,
        stacco=0.75, picco=5200,
        melodia=(
            "E4 -  E4 -  G4 -  E4 - ", "B4 -  A4 -  G4 -  E4 - ",
            "E4 -  E4 -  G4 -  B4 - ", "C5 -  B4 -  G4 -  .  . ",
            "E5 -  D5 -  C5 -  B4 - ", "A4 -  B4 -  C5 -  D5 - ",
            "E5 -  -  -  D5 -  B4 - ", "E4 -  -  -  .  .  .  . ",
            "G4 -  B4 -  E5 -  B4 - ", "C5 -  B4 -  A4 -  G4 - ",
            "F#4 -  A4 -  D5 -  A4 - ", "B4 -  -  -  E4 -  .  . ",
        ),
        accordi=("Em Em", "Em Em", "G G", "Am B", "Em Em", "Am Am",
                 "B B", "Em Em", "G G", "Am Am", "B B", "Em Em")),
    # Snake: era una musica da meditazione, e il gioco non e' quello. Adesso
    # e' un chip saltellante in re minore, tutto arpeggi, che corre come il
    # serpente quando si allunga.
    "snake_musica": dict(
        bpm=156, forma="quadra25", ampiezza_melodia=0.85, basso="ottavi",
        ampiezza_basso=0.8, charleston=0.2, rullante=0.22, cassa=0.95,
        arpeggio=0.28, stacco=0.7, picco=5600,
        melodia=(
            "D4 A4 D5 A4 F5 D5 A4 D5", "C5 G4 C5 E5 G5 E5 C5 G4",
            "B4 D5 G5 D5 B4 G4 D5 G5", "A4 C5 E5 A5 E5 C5 A4 E5",
            "D5 F5 A5 D6 A5 F5 D5 A4", "G4 B4 D5 G5 D5 B4 G4 D5",
            "F4 A4 C5 F5 C5 A4 F4 C5", "E5 D5 C5 A4 G4 -  .  . ",
            "D5 -  F5 -  A5 -  G5 F5", "E5 -  G5 -  B5 -  A5 G5",
            "F5 A5 D6 A5 F5 D5 A4 F4", "D4 -  -  -  A4 -  .  . ",
        ),
        accordi=("Dm Dm", "C C", "G G", "Am Am", "Dm Dm", "G G",
                 "F F", "Am Am", "Dm Dm", "Em Em", "Dm Dm", "Dm Dm")),
    # Pongo: resta la piu' discreta -- il ping deve restare la voce -- ma
    # non piu' addormentata: il basso pulsa a ottavi e la cassa segna il
    # tempo, mentre la melodia rimane rada.
    "pongo_musica": dict(
        bpm=152, forma="quadra25", ampiezza_melodia=0.7, basso="ottavi",
        ampiezza_basso=0.55, charleston=0.14, cassa=0.8, arpeggio=0.12,
        stacco=0.72, picco=4400,
        melodia=(
            "C5 .  .  G5 .  .  E5 . ", ".  .  G5 .  E5 .  C5 . ",
            "A4 .  .  E5 .  .  C5 . ", ".  .  E5 .  D5 .  .  . ",
            "F5 .  .  C6 .  .  A5 . ", ".  .  A5 .  G5 .  E5 . ",
            "G5 .  .  D6 .  .  B5 . ", "C6 .  G5 .  E5 .  C5 . ",
            "E5 .  .  C5 .  .  G4 . ", "C5 .  .  .  G4 .  .  . ",
        ),
        accordi=("C C", "C C", "Am Am", "G G", "F F", "F F",
                 "G G", "C C", "Am F", "C G")),
    # Squadriglia: la fanfara, ma da cabinato. Piu' svelta, con cassa e
    # rullante veri sotto, e l'arpeggio che tiene la tensione fra una frase
    # e l'altra.
    "squadriglia_musica": dict(
        bpm=168, forma="quadra50", ampiezza_melodia=0.85, basso="ottavi",
        ampiezza_basso=0.9, charleston=0.18, rullante=0.38, cassa=1.0,
        arpeggio=0.22, stacco=0.6, picco=6200,
        melodia=(
            "G4 -  C5 -  E5 G5 C6 - ", "G5 E5 C5 D5 E5 -  .  . ",
            "A4 -  D5 -  F5 A5 D6 - ", "A5 G5 F5 E5 D5 -  .  . ",
            "C5 C5 E5 G5 C6 -  G5 - ", "D5 D5 F5 A5 D6 -  A5 - ",
            "E5 G5 F5 E5 D5 C5 B4 D5", "C5 -  G4 -  C5 -  .  . ",
            "E5 -  E5 F5 G5 -  C6 - ", "F5 -  F5 E5 D5 -  B4 - ",
            "C5 E5 G5 C6 B5 G5 D5 F5", "E5 -  C5 -  G4 .  G4 . ",
        ),
        accordi=("C C", "C G", "D D", "F G", "C C", "D G", "C G", "C C",
                 "C C", "D G", "C G", "C G")),
    # Mine vaganti: lo spazio, ma non contemplativo. Mi minore, arpeggio
    # fitto e cassa: il campo minato si muove, e la musica anche.
    "mine_musica": dict(
        bpm=158, forma="quadra25", ampiezza_melodia=0.85, basso="ottavi",
        ampiezza_basso=0.85, charleston=0.16, rullante=0.26, cassa=1.0,
        arpeggio=0.28, stacco=0.68, picco=5800,
        melodia=(
            "E5 -  B4 -  E5 G5 B5 - ", "A5 -  G5 E5 D5 -  B4 - ",
            "E5 -  B4 -  E5 G5 B5 - ", "C6 -  B5 G5 E5 -  .  . ",
            "G5 B5 D6 B5 G5 E5 D5 B4", "A4 C5 E5 A5 E5 C5 A4 E5",
            "B4 D5 F#5 B5 F#5 D5 B4 F#5", "E5 -  -  -  B4 -  .  . ",
            "C5 E5 G5 C6 G5 E5 C5 G4", "A4 C5 E5 A5 G5 E5 C5 A4",
            "B4 D5 G5 B5 A5 F#5 D5 B4", "E5 -  -  -  E4 -  .  . ",
        ),
        accordi=("Em Em", "Am B", "Em Em", "C C", "G G", "Am Am",
                 "B B", "Em Em", "C C", "Am Am", "B B", "Em Em")),
    # T-Rex: la corsa. Sol maggiore a ottavi ribattuti -- il passo -- con la
    # cassa che fa da zampata e l'arpeggio che accelera la sensazione di
    # velocita' anche quando il dinosauro va allo stesso ritmo.
    "trex_musica": dict(
        bpm=172, forma="quadra25", ampiezza_melodia=0.85, basso="ottavi",
        ampiezza_basso=0.8, charleston=0.2, rullante=0.24, cassa=0.95,
        arpeggio=0.26, stacco=0.72, picco=5600,
        melodia=(
            "G4 B4 D5 B4 G4 B4 D5 G5", "E5 -  D5 B4 D5 -  .  . ",
            "C5 E5 G5 E5 C5 E5 G5 C6", "B5 -  A5 G5 A5 -  .  . ",
            "G4 B4 D5 B4 G4 B4 D5 G5", "A5 G5 E5 D5 E5 -  G5 - ",
            "A5 -  C6 -  D6 -  C6 A5", "G5 -  D5 -  G4 .  .  . ",
            "D5 G5 B5 G5 D5 G5 B5 D6", "C6 -  B5 G5 A5 -  .  . ",
            "E5 G5 C6 G5 E5 C5 G4 E5", "D5 -  G4 -  G4 .  .  . ",
        ),
        accordi=("G G", "C D", "C C", "G D", "G G", "C C", "D D", "G G",
                 "G G", "C C", "Am D", "G G")),
    # Kingo Bongo: la giungla in citta'. La minore, tamburi in evidenza --
    # cassa e rullante forti -- e una melodia a botta e risposta, come due
    # che si lanciano qualcosa da un tetto all'altro.
    "bongo_musica": dict(
        bpm=150, forma="quadra50", ampiezza_melodia=0.8, basso="ottavi",
        ampiezza_basso=0.9, charleston=0.2, rullante=0.42, cassa=1.0,
        arpeggio=0.24, stacco=0.65, picco=5800,
        melodia=(
            "A4 .  C5 .  E5 -  A5 - ", "G5 E5 D5 C5 A4 -  .  . ",
            "G4 .  B4 .  D5 -  G5 - ", "F5 D5 C5 B4 G4 -  .  . ",
            "A4 C5 E5 A5 E5 C5 E5 G5", "A5 -  G5 E5 D5 C5 .  . ",
            "E5 -  D5 -  C5 -  B4 - ", "A4 -  E5 -  A4 -  .  . ",
            "C5 E5 G5 C6 G5 E5 C5 G4", "F5 A5 C6 A5 F5 D5 A4 F4",
            "E5 G5 B5 E6 B5 G5 E5 B4", "A4 -  -  -  E4 -  .  . ",
        ),
        accordi=("Am Am", "Am Am", "G G", "G G", "Am Am", "Am G",
                 "F E", "Am Am", "C C", "F Dm", "Em E", "Am Am")),
    # Gnam Gnam: il motivo di sempre -- e' quello che gli sta bene -- ma
    # suonato come in sala giochi: piu' svelto, con la batteria sotto e
    # l'accordo sgranato che corre.
    "gnam_musica": dict(
        bpm=150, forma="quadra25", ampiezza_melodia=0.9, basso="ottavi",
        ampiezza_basso=0.8, charleston=0.2, rullante=0.26, cassa=0.95,
        arpeggio=0.26, stacco=0.68, picco=6000,
        melodia=MELODIA, accordi=ACCORDI),
}


def genera(cartella):
    fatti = []
    for nome, ricetta in sorted(MUSICHE.items()):
        ricetta = dict(ricetta)
        picco = ricetta.pop("picco")
        quanti = scrivi(os.path.join(cartella, nome + ".wav"),
                        musica(**ricetta), picco=picco)
        fatti.append((nome, quanti, 1000.0 * quanti / FREQUENZA))
    for nome, pezzi in sorted(RICETTE.items()):
        campioni = []
        for durata, da_hz, a_hz in pezzi:
            campioni.extend(nota(durata, da_hz, a_hz))
        percorso = os.path.join(cartella, nome + ".wav")
        quanti = scrivi(percorso, campioni)
        fatti.append((nome, quanti, 1000.0 * quanti / FREQUENZA))
    return fatti


if __name__ == "__main__":
    dove = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "suoni")
    print("scrivo in %s" % dove)
    for nome, quanti, ms in genera(dove):
        print("  %-10s %6d campioni  %5.0f ms" % (nome, quanti, ms))
