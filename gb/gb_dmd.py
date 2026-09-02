#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Game Boy sul pannello: l'emulatore come processo separato.

PyBoy e' una libreria Python, quindi si potrebbe importare dentro il servizio.
Non lo facciamo, e le ragioni sono tre — le stesse di Doom piu' una che vale
piu' di tutte:

  1. **Il GIL.** Un emulatore dentro il nostro processo si contende
     l'interprete con il ciclo di rendering. Sul pannello la moneta e' il
     microsecondo: abbiamo misurato che basta la contesa sul bus di memoria
     per accendere una riga sbagliata, figurarsi un emulatore che gira nello
     stesso interprete.
  2. **Isolamento.** Se PyBoy cade, cade lui: il pannello torna all'orologio
     e il servizio non se ne accorge.
  3. **Licenza.** PyBoy e' LGPL-3.0 e con GPLv3 andrebbe d'accordo anche
     collegato. Ma due processi che si parlano da una pipe restano due
     programmi distinti, e questo toglie ogni dubbio a chi guardera' il
     repository fra un anno.

Il protocollo e' quello di Doom, volutamente stupido:

  - **stdout**: fotogrammi grezzi RGB di dimensione fissa (256x64x3 byte),
    uno dopo l'altro, senza intestazioni. Chi legge sa gia' quanto e' lungo
    un fotogramma.
  - **stdin**: coppie di byte [stato, tasto] — stato 1 premuto, 0 rilasciato;
    tasto e' un codice della tabella TASTI qui sotto, che vale solo fra questo
    programma e `sources/gameboy.py`.

Lo schermo del Game Boy e' 160x144, il pannello 256x64. La proporzione si
tiene: 64 righe di altezza fanno 71 pixel di larghezza, centrati, con il resto
del pannello spento. L'**overscan** toglie righe sopra e sotto *alla
sorgente*: l'immagine perde le fasce alte e basse ma sul pannello diventa piu'
larga, perche' a parita' di 64 righe la proporzione cambia. Al 40% si arriva a
116 pixel di larghezza — quasi metа' pannello — al prezzo di una fetta di
cielo e una di terreno.
"""

import argparse
import os
import select
import sys
import time

# --------------------------------------------------------------------- tasti

# Codici del protocollo. Non sono di PyBoy e non sono di Linux: sono nostri, e
# questo file e' l'unico posto in cui hanno un significato insieme al nome del
# pulsante del Game Boy.
TASTI = {
    1: "up",
    2: "down",
    3: "left",
    4: "right",
    5: "a",
    6: "b",
    7: "start",
    8: "select",
}


def costruisci_argomenti():
    p = argparse.ArgumentParser(description="Game Boy su pannello DMD")
    p.add_argument("--rom", required=True)
    p.add_argument("--larghezza", type=int, default=256)
    p.add_argument("--altezza", type=int, default=64)
    # Sotto 1 schiarisce, sopra 1 scurisce: stessa convenzione di Doom, cosi'
    # chi ha imparato a tarare un pannello non deve impararlo due volte.
    p.add_argument("--gamma", type=float, default=1.0)
    # Percentuale di righe tolte alla sorgente, meta' sopra e meta' sotto.
    p.add_argument("--overscan", type=float, default=0.0)
    # Fotogrammi al secondo mandati al pannello. Il Game Boy ne fa 59,7: noi
    # ne mandiamo la meta', perche' il ciclo di rendering gira a 30 e ogni
    # fotogramma in piu' e' traffico di memoria che compete con il pannello.
    p.add_argument("--fps", type=float, default=30.0)
    return p


def tavola_gamma(gamma):
    """256 valori gia' corretti: la correzione si fa una volta, non per pixel."""
    import numpy
    if abs(gamma - 1.0) < 0.01:
        return None
    scala = numpy.arange(256, dtype=numpy.float64) / 255.0
    return numpy.clip((scala ** gamma) * 255.0, 0, 255).astype(numpy.uint8)


def geometria(larghezza_pannello, altezza_pannello, overscan):
    """Quante righe togliere alla sorgente e quanto viene larga l'immagine.

    Restituisce (righe_tolte, larghezza_immagine). L'immagine non puo' essere
    piu' larga del pannello: oltre quel punto l'overscan non allarga piu'
    niente e taglierebbe soltanto.
    """
    overscan = max(0.0, min(80.0, float(overscan)))
    tolte = int(144 * overscan / 100.0) // 2 * 2      # pari: meta' sopra, meta' sotto
    visibili = max(16, 144 - tolte)
    larghezza = int(round(160.0 * altezza_pannello / visibili))
    larghezza = max(1, min(larghezza_pannello, larghezza))
    return tolte, larghezza


def main():
    args = costruisci_argomenti().parse_args()

    if not os.path.isfile(args.rom):
        sys.stderr.write("ROM non trovata: %s\n" % args.rom)
        return 2

    try:
        import numpy
        from PIL import Image
        from pyboy import PyBoy
    except ImportError as exc:
        sys.stderr.write("manca una libreria: %s\n" % exc)
        return 3

    # window="null": nessuna finestra, nessun SDL da aprire. Il suono e'
    # spento — l'audio del salotto non e' nostro, e un secondo canale sarebbe
    # solo rumore.
    pyboy = PyBoy(args.rom, window="null", sound_emulated=False)
    pyboy.set_emulation_speed(1)

    tolte, larghezza = geometria(args.larghezza, args.altezza, args.overscan)
    alto = tolte // 2
    basso = 144 - (tolte - alto)
    sinistra = (args.larghezza - larghezza) // 2
    tavola = tavola_gamma(args.gamma)

    sys.stderr.write("[gb] %s  overscan %.0f%% -> %dx%d al centro\n"
                     % (os.path.basename(args.rom), args.overscan,
                        larghezza, args.altezza))
    sys.stderr.flush()

    pannello = Image.new("RGB", (args.larghezza, args.altezza), (0, 0, 0))
    uscita = sys.stdout.buffer
    ingresso = sys.stdin.buffer
    fd = ingresso.fileno()

    # Un fotogramma su quanti: il Game Boy ne produce 59,7 al secondo, e
    # mandarli tutti raddoppierebbe il traffico sulla pipe senza che l'occhio
    # se ne accorga su un pannello da 64 righe.
    salto = max(1, int(round(59.7 / max(1.0, args.fps))))

    premuti = set()
    vivo = True
    while vivo:
        for _ in range(salto - 1):
            pyboy.tick(1, False)
        if not pyboy.tick(1, True):
            break

        # Comandi in arrivo. Si legge quello che c'e' e basta: se non arriva
        # niente non si aspetta, che qui il tempo e' del gioco.
        while select.select([fd], [], [], 0)[0]:
            dati = os.read(fd, 64)
            if not dati:
                vivo = False
                break
            for i in range(0, len(dati) - 1, 2):
                stato, codice = dati[i], dati[i + 1]
                nome = TASTI.get(codice)
                if nome is None:
                    continue
                try:
                    if stato:
                        if nome not in premuti:
                            pyboy.button_press(nome)
                            premuti.add(nome)
                    else:
                        if nome in premuti:
                            pyboy.button_release(nome)
                            premuti.discard(nome)
                except Exception:
                    pass

        schermo = pyboy.screen.ndarray[alto:basso, :, :3]
        immagine = Image.fromarray(numpy.ascontiguousarray(schermo), "RGB")
        # BOX invece di NEAREST: da 160 pixel a 71 il campionamento secco
        # butterebbe via due colonne su tre e il testo dei giochi sparirebbe.
        # La media di area tiene almeno la traccia di quello che c'era.
        immagine = immagine.resize((larghezza, args.altezza), Image.BOX)
        if tavola is not None:
            immagine = Image.fromarray(tavola[numpy.asarray(immagine)], "RGB")

        pannello.paste(immagine, (sinistra, 0))
        try:
            uscita.write(pannello.tobytes())
            uscita.flush()
        except (BrokenPipeError, ValueError):
            break

    try:
        # save=True: la memoria tampone della cartuccia finisce accanto alla
        # ROM, quindi i salvataggi dei giochi sopravvivono all'uscita e si
        # vedono anche dalla condivisione.
        pyboy.stop(save=True)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(0)
