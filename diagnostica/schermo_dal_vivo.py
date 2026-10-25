#!/usr/bin/env python3
"""Chi riesce a disegnare sul vetro: la prova dal vivo.

`prova_schermo.py` controlla i conti del compositore con delle superfici
finte, e per quello basta. Questa invece prende lo schermo vero e ci
dipinge sopra, una strada per volta, dicendo a voce alta che cosa sta
facendo. Serve quando il programma gira, il giornale di bordo non si
lamenta -- oppure si lamenta di uno scambio di pagina rifiutato -- e il
vetro resta nero.

Si lancia con il servizio **fermo**, perche' due programmi non possono
tenere la stessa scheda:

    sudo systemctl stop dmd
    sudo python3 /opt/dmd/diagnostica/schermo_dal_vivo.py

Dipinge tre schermate piene, cinque secondi ciascuna: rosso dal
framebuffer, verde da SDL, blu da SDL con la console staccata prima. Chi
guarda lo schermo risponde a una domanda sola: quali colori ha visto.
"""

import os
import sys
import time

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(QUI))

ATTESA = 5
COLORI = {"rosso": (200, 20, 20), "verde": (20, 200, 20),
          "blu": (20, 60, 220)}


def riga(testo=""):
    print(testo, flush=True)


def tela(misura, colore, n):
    """Un rettangolo pieno con una barra che scorre.

    La barra non e' un vezzo: distingue un disegno vivo da un unico
    fotogramma rimasto congelato sullo schermo. Con SDL sul KMS capita
    proprio quello -- il primo fotogramma passa, e da li' in poi ogni
    scambio di pagina viene rifiutato.
    """
    from PIL import Image, ImageDraw
    largo, alto = misura
    img = Image.new("RGB", (largo, alto), colore)
    d = ImageDraw.Draw(img)
    chiaro = tuple(min(255, c + 90) for c in colore)
    d.rectangle((2, 2, largo - 3, alto - 3), outline=chiaro, width=4)
    x = (n * 20) % max(1, largo - 40)
    d.rectangle((x, 0, x + 40, alto), fill=chiaro)
    return img


def macchina():
    riga("--- la macchina")
    try:
        import piattaforma
        riga("  modello: %s" % piattaforma.nome())
    except Exception as exc:
        riga("  piattaforma.py non risponde: %s" % exc)
    for percorso in sorted(_schede()):
        riga("  %s -> %s" % (percorso, _driver(percorso)))
    riga("  /proc/fb: %s" % _testo("/proc/fb").replace("\n", " | "))
    riga("  fb0 misura: %s bit: %s"
         % (_testo("/sys/class/graphics/fb0/virtual_size"),
            _testo("/sys/class/graphics/fb0/bits_per_pixel")))
    riga("  DISPLAY=%r WAYLAND_DISPLAY=%r SDL_VIDEODRIVER=%r"
         % (os.environ.get("DISPLAY"), os.environ.get("WAYLAND_DISPLAY"),
            os.environ.get("SDL_VIDEODRIVER")))
    try:
        import pygame
        riga("  pygame %s, SDL %s"
             % (pygame.version.ver,
                ".".join(str(n) for n in pygame.version.SDL)))
    except Exception as exc:
        riga("  pygame non c'e': %s" % exc)
    riga("  chi tiene la scheda adesso:")
    for nome in sorted(_vtconsole()):
        riga("    %s: %s" % (nome, _testo(nome + "/name")))
    riga()


def _schede():
    import glob
    return glob.glob("/sys/class/drm/card[0-9]")


def _driver(scheda):
    percorso = os.path.join(scheda, "device", "driver")
    try:
        return os.path.basename(os.readlink(percorso))
    except OSError:
        return "?"


def _vtconsole():
    import glob
    return glob.glob("/sys/class/vtconsole/vtcon*")


def _testo(percorso):
    try:
        with open(percorso, encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except OSError as exc:
        return "(%s)" % exc.strerror


def prova(etichetta, colore, fabbrica):
    riga("--- %s" % etichetta)
    try:
        superficie = fabbrica()
    except Exception as exc:
        riga("  non si apre: %s: %s" % (type(exc).__name__, exc))
        riga()
        return False
    misura = (superficie.width, superficie.height)
    riga("  aperta a %dx%d" % misura)
    try:
        scaduto = time.monotonic() + ATTESA
        quanti = 0
        while time.monotonic() < scaduto:
            superficie.mostra(tela(misura, COLORI[colore], quanti))
            quanti += 1
            time.sleep(0.05)
        riga("  %s: %d fotogrammi mandati, nessun errore" % (colore, quanti))
        esito = True
    except Exception as exc:
        riga("  si rompe disegnando: %s: %s" % (type(exc).__name__, exc))
        esito = False
    finally:
        try:
            superficie.chiudi()
        except Exception:
            pass
    riga()
    return esito


def principale():
    import display
    if os.geteuid() != 0:
        riga("Va lanciata con sudo: il framebuffer e il KMS non si aprono"
             " da utente normale.")
        return 2
    riga("Il servizio deve essere fermo. Se non lo e':"
         " sudo systemctl stop dmd")
    riga()
    macchina()

    prova("framebuffer su /dev/fb0 -- ROSSO", "rosso",
          lambda: display.SuperficieFramebuffer(console="lascia"))

    os.environ.pop("SDL_VIDEODRIVER", None)
    prova("SDL senza toccare la console -- VERDE", "verde",
          lambda: display.SuperficieSDL(console="lascia"))

    os.environ.pop("SDL_VIDEODRIVER", None)
    prova("SDL con la console staccata prima -- BLU", "blu",
          lambda: display.SuperficieSDL(console="staccata"))

    riga("--- la domanda")
    riga("Quali colori sono comparsi sullo schermo? rosso, verde, blu,"
         " nessuno?")
    riga("Per riattaccare la console:"
         " sudo sh -c 'echo 1 > /sys/class/vtconsole/vtcon1/bind'")
    return 0


if __name__ == "__main__":
    sys.exit(principale())
