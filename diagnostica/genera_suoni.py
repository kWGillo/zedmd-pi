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
}


def genera(cartella):
    fatti = []
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
