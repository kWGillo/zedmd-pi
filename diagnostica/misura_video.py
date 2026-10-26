# -*- coding: utf-8 -*-
"""Quanto costa un fotogramma su **questa** macchina.

La domanda
----------
*«I giochi su un mini PC Z83, con il monitor 21:9, risultano molto lenti e a
scatti. Potrebbe essere dato dall'eccessiva risoluzione o un problema di
risorse?»*

Le due cose non sono alternative: sono fattore e moltiplicatore. Il filtro
DMD lavora sui pixel **veri**, non su quelli della tela, e un 2560x1080 ne
ha due milioni e mezzo contro i sedicimila del pannello. Su una CPU di
fascia alta quel lavoro sta nel budget di un fotogramma; su un Atom da mini
PC no. Nessuno dei due numeri da solo dice se ci si sta dentro: serve
misurare, su questa macchina e a questa risoluzione.

Che cosa misura
---------------
Il fotogramma di un gioco, stadio per stadio:

  1. **ingrandimento** della tela logica ai pixel dello schermo;
  2. **filtro DMD**, cioe' la maschera dei punti moltiplicata sopra;
  3. **composizione** sul quadro dello schermo;
  4. **consegna**, cioe' i byte che vanno alla superficie.

E conclude con il conto che interessa: quanti fotogrammi al secondo stanno
in piedi con il filtro acceso e quanti con il filtro spento.

Come si legge
-------------
Il ciclo dei giochi punta a 30 fotogrammi al secondo, cioe' **33 ms** per
fotogramma -- e in quei 33 ms ci deve stare anche il gioco, che pensa.
Se la riga "con il filtro" supera i 33 ms, gli scatti non sono
un'impressione: sono aritmetica, e si tolgono in due modi, tutti e due
dalla pagina Video -- spegnendo il filtro DMD, o scegliendo una risoluzione
piu' piccola.

    python3 diagnostica/misura_video.py                # la risoluzione configurata
    python3 diagnostica/misura_video.py 2560x1080      # una a scelta
"""

import os
import random
import sys
import tempfile
import time

os.environ.setdefault("DMD_DATA", tempfile.mkdtemp())
os.environ.setdefault("DMD_CONFIG", os.path.join(tempfile.mkdtemp(), "config.json"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image                                   # noqa: E402

import display                                          # noqa: E402

# Il ciclo dei giochi: trenta fotogrammi al secondo, e in ognuno ci sta anche
# il gioco che pensa. Il budget del disegno e' quindi **meno** di 33 ms.
FPS = 30.0
BUDGET_MS = 1000.0 / FPS

GIRI = 25


def schermo_configurato():
    """La risoluzione da misurare: quella vera, se si riesce a saperla."""
    try:
        import dmdconf
        cfg = dmdconf.load()
        modo = ((cfg.get("video") or {}).get("risoluzione") or "").strip()
        if "x" in modo:
            largo, alto = modo.lower().split("x", 1)
            return int(largo), int(alto)
    except Exception:
        pass
    # Vuoto vuol dire "quella che c'e' adesso": e quella la sa il
    # framebuffer, non la configurazione.
    try:
        with open("/sys/class/graphics/fb0/virtual_size") as f:
            largo, alto = f.read().strip().split(",")[:2]
            if int(largo) > 0 and int(alto) > 0:
                return int(largo), int(alto)
    except Exception:
        pass
    try:
        misure = display.risoluzioni_disponibili()
        if misure:
            largo, alto = misure[0].lower().split("x", 1)
            return int(largo), int(alto)
    except Exception:
        pass
    return 1920, 1080


def tela_di_gioco(misura, colori=0):
    """Una tela piena di roba che cambia: un fotogramma di gioco realistico.

    Una tela nera non va bene: il filtro costa uguale, ma l'ingrandimento e
    la consegna su un'immagine tutta uguale possono essere piu' veloci di
    quanto saranno davvero.
    """
    tela = Image.new("RGB", misura)
    px = tela.load()
    rnd = random.Random(20251025)
    tavolozza = [(rnd.randint(40, 255), rnd.randint(40, 255),
                  rnd.randint(40, 255)) for _ in range(colori)] if colori else []
    for y in range(misura[1]):
        for x in range(misura[0]):
            if tavolozza:
                px[x, y] = tavolozza[rnd.randrange(colori)]
            elif (x + y) % 3 == 0:
                px[x, y] = (rnd.randint(40, 255), rnd.randint(40, 255),
                            rnd.randint(40, 255))
    return tela


def crono(fn, giri=GIRI):
    fn()
    inizio = time.perf_counter()
    for _ in range(giri):
        fn()
    return (time.perf_counter() - inizio) / giri * 1000.0


def confronto_colori(schermo):
    """Le due strade del filtro, sulla stessa macchina e sullo stesso disegno.

    La via dei colori (17.4.15) tinge una piastrella per colore invece di
    moltiplicare ogni pixel: su un disegno con pochi colori -- un gioco, una
    schermata di testo -- dovrebbe costare molto meno. "Dovrebbe" non basta:
    qui si vede quanto, su questa macchina.
    """
    c = display.Compositore((256, 64), schermo, {"filtro_dmd": True})
    if c.scala < 3:
        return
    tela = tela_di_gioco(c.tela_logica, colori=12)
    display.VIA_DEI_COLORI = True
    colori = crono(lambda: c.componi(tela))
    display.VIA_DEI_COLORI = False
    sempre = crono(lambda: c.componi(tela))
    display.VIA_DEI_COLORI = True
    print()
    print("  il filtro su un disegno da gioco (dodici colori)")
    print("    pixel per pixel     %6.1f ms" % sempre)
    print("    via dei colori      %6.1f ms  -> %.1f volte piu' svelta"
          % (colori, sempre / colori if colori else 0.0))


def misura(schermo):
    print("=" * 74)
    print("Schermo %dx%d" % schermo)
    print("=" * 74)
    risultati = {}
    for filtro in (True, False):
        c = display.Compositore((256, 64), schermo, {"filtro_dmd": filtro})
        tela = tela_di_gioco(c.tela_logica)
        pieno = crono(lambda: c.componi(tela))
        risultati[filtro] = pieno
        quadro = c.componi(tela)
        consegna = crono(quadro.tobytes)
        print()
        print("  filtro DMD %s" % ("ACCESO" if filtro else "spento"))
        print("    tela logica         %dx%d, scala x%d"
              % (c.tela_logica[0], c.tela_logica[1], c.scala))
        print("    disegno completo    %6.1f ms" % pieno)
        print("    consegna (byte)     %6.1f ms" % consegna)
        totale = pieno + consegna
        print("    totale              %6.1f ms  -> %5.1f fotogrammi al secondo"
              % (totale, 1000.0 / totale if totale else 0.0))
        risultati[filtro] = totale

    print()
    print("-" * 74)
    con, senza = risultati[True], risultati[False]
    print("Budget di un fotogramma a %d al secondo: %.1f ms"
          % (FPS, BUDGET_MS))
    print("Il filtro DMD costa %.1f ms, cioe' il %.0f%% del budget."
          % (con - senza, 100.0 * (con - senza) / BUDGET_MS))
    if con <= BUDGET_MS * 0.7:
        print("Questa macchina ci sta comoda: niente da cambiare.")
    elif con <= BUDGET_MS:
        print("Ci sta, ma senza margine: un gioco che pensa molto puo'")
        print("far scendere i fotogrammi. Se si vedono scatti, il primo")
        print("interruttore da provare e' il filtro DMD.")
    elif senza <= BUDGET_MS:
        print("**Non ci sta con il filtro acceso, ci sta con il filtro")
        print("spento.** Gli scatti non sono un'impressione. Pagina Video,")
        print("filtro DMD spento: si perde il reticolo dei punti, si")
        print("guadagnano %.0f ms per fotogramma." % (con - senza))
    else:
        print("**Non ci sta nemmeno senza filtro**: qui il problema e' la")
        print("risoluzione, non il filtro. Una misura piu' piccola nella")
        print("pagina Video dimezza i pixel e dimezza il tempo.")
    print()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        largo, alto = sys.argv[1].lower().split("x", 1)
        schermi = [(int(largo), int(alto))]
    else:
        schermi = [schermo_configurato()]
    for s in schermi:
        misura(s)
        confronto_colori(s)
