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
    "C C", "C C", "A A", "G G", "C C", "A A", "F G", "C C",
    "F F", "F F", "G G", "G G", "C C", "G G", "F G", "C G",
)
NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
PICCO_MUSICA = 5500        # un terzo degli effetti: la musica sta sotto


def _hz(nome):
    semitoni = NOTE[nome[0]] + 12 * (int(nome[1:]) + 1)
    return 440.0 * 2 ** ((semitoni - 69) / 12.0)


def musica():
    croma = 60.0 / BPM / 2
    per_croma = int(round(FREQUENZA * croma))
    totale = per_croma * 8 * len(MELODIA)
    fuori = [0.0] * totale

    def suona(inizio, durata, hz, forma, ampiezza):
        quanti = int(durata * per_croma)
        fase = 0.0
        for i in range(quanti):
            t = i / float(quanti)
            # Attacco corto, poi un calo: le note ripetute si staccano
            # l'una dall'altra invece di fondersi in un fischio.
            inv = min(1.0, i / 60.0) * (1.0 - 0.55 * t) * min(1.0, (quanti - i) / 80.0)
            fase = (fase + hz / FREQUENZA) % 1.0
            if forma == "quadra":
                v = 1.0 if fase < 0.25 else -1.0      # duty 25%: il timbro chip
            else:
                v = 4.0 * abs(fase - 0.5) - 1.0        # triangolo, per il basso
            fuori[inizio + i] += v * inv * ampiezza

    # la melodia
    for b, riga in enumerate(MELODIA):
        celle = riga.split()
        j = 0
        while j < 8:
            nota = celle[j]
            durata = 1
            while j + durata < 8 and celle[j + durata] == "-":
                durata += 1
            if nota not in (".", "-"):
                suona((b * 8 + j) * per_croma, durata, _hz(nota), "quadra", 1.0)
            j += durata
    # il basso
    for b, riga in enumerate(ACCORDI):
        for meta, radice in enumerate(riga.split()):
            for k in range(4):
                ottava = 3 if k % 2 == 0 else 4
                suona((b * 8 + meta * 4 + k) * per_croma, 1,
                      _hz(radice + str(ottava)), "triangolo", 0.9)
    # un charleston leggero sui controtempi: da' la spinta senza coprire
    import random
    casuale = random.Random(7)
    for c in range(8 * len(MELODIA)):
        if c % 2 == 1:
            base = c * per_croma
            for i in range(int(FREQUENZA * 0.012)):
                fuori[base + i] += casuale.uniform(-1, 1) * 0.25 * (1 - i / (FREQUENZA * 0.012))
    return fuori


def genera(cartella):
    fatti = []
    campioni = musica()
    quanti = scrivi(os.path.join(cartella, "gnam_musica.wav"), campioni,
                    picco=PICCO_MUSICA)
    fatti.append(("gnam_musica", quanti, 1000.0 * quanti / FREQUENZA))
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
