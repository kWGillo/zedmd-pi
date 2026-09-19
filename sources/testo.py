# -*- coding: utf-8 -*-
"""Far stare un testo dentro 256x64, nel carattere piu' grande possibile.

Questo modulo nasce dalla seconda volta. La regola -- prova una riga, poi
due, poi tre, tieni la prima impaginazione che entra, e se non entra taglia
con i puntini -- e' stata scritta per le notifiche MQTT nella 9.5. Quando e'
arrivato OnAir, che deve fare esattamente la stessa cosa con parole diverse,
c'erano due strade: copiare quaranta righe, oppure metterle in un posto solo.

Copiarle sarebbe stato piu' veloce oggi e piu' caro ogni volta dopo. Una
regola scritta due volte diverge sempre: si corregge un bordo di qui e non di
la', e l'anno prossimo due pannelli che dovrebbero impaginare uguale
impaginano diverso, senza che nessuno abbia deciso niente.

Perche' si parte dal grande e si scende, e non il contrario: un messaggio
corto deve restare **corto e grande**. Scegliere una dimensione fissa perche'
i messaggi lunghi ci stiano vorrebbe dire scrivere «ON AIR» in dodici pixel
su un pannello alto sessantaquattro, per colpa di un messaggio che forse non
arrivera' mai.
"""

from PIL import Image, ImageDraw

from .clock import _load_font

# Quello che dice «qui manca qualcosa». Un carattere solo, non tre punti
# separati: sul pannello tre punti a spaziatura piena si mangiano una lettera.
PUNTINI = "…"

# Lo spazio fra una riga e l'altra, in pixel.
INTERLINEA = 2

# Oltre questo non si va: piu' di quattro righe su un pannello alto 64 pixel
# vuol dire caratteri da tredici, che a tre metri non si leggono.
RIGHE_MASSIME = 4


def _misuratore():
    """Un disegnatore usa e getta, buono solo per misurare i testi."""
    return ImageDraw.Draw(Image.new("RGB", (1, 1)))


def spezza(testo, font, larghezza, misura=None):
    """Il testo a capo sulle parole, dentro `larghezza` pixel.

    Una parola piu' larga della riga -- un indirizzo, un nome di file -- non
    si spezza a meta': si lascia sbordare e ci pensera' il taglio. Spezzare
    una parola a caso rende illeggibili tutte e due le meta'.
    """
    misura = misura or _misuratore()
    righe = []
    corrente = ""
    for parola in (testo or "").split():
        prova = (corrente + " " + parola).strip()
        if corrente and misura.textlength(prova, font=font) > larghezza:
            righe.append(corrente)
            corrente = parola
        else:
            corrente = prova
    if corrente:
        righe.append(corrente)
    return righe or [""]


def accorcia(riga, font, larghezza, misura=None):
    """La riga con i puntini in fondo, tagliata quanto basta perche' ci stia."""
    misura = misura or _misuratore()
    if misura.textlength(riga + PUNTINI, font=font) <= larghezza:
        return riga + PUNTINI
    tagliata = riga
    while tagliata and misura.textlength(tagliata + PUNTINI,
                                         font=font) > larghezza:
        tagliata = tagliata[:-1]
    return tagliata.rstrip() + PUNTINI


def impagina(testo, larghezza, altezza, tetto, righe_massime=RIGHE_MASSIME,
             interlinea=INTERLINEA):
    """Righe e carattere: il piu' grande in cui il testo ci sta.

    Si provano una, due, tre, quattro righe e si tiene la prima impaginazione
    che entra: e' lo stesso criterio con cui l'orologio sceglie il carattere
    della colonna dei rifiuti.

    `tetto` e' la dimensione massima del carattere. Serve, e si vede togliendola:
    su una riga sola, senza tetto, un «OK» riempirebbe il pannello da bordo a
    bordo.

    Se non entra nemmeno all'ultima riga disponibile, l'ultima si taglia e si
    mettono i puntini.
    """
    misura = _misuratore()
    ultimo = None
    for quante in range(1, max(1, righe_massime) + 1):
        alta = (altezza - (quante - 1) * interlinea) // quante
        font = _load_font(max(6, min(tetto, alta)))
        righe = spezza(testo, font, larghezza, misura)
        ultimo = (righe, font)
        if len(righe) <= quante:
            return righe, font
    righe, font = ultimo
    tenute = righe[:righe_massime]
    tenute[-1] = accorcia(tenute[-1], font, larghezza, misura)
    return tenute, font


def scrivi_centrato(disegna, righe, font, larghezza, altezza, colore,
                    interlinea=INTERLINEA, margine=0):
    """Il blocco di righe al centro della tela, orizzontale e verticale.

    Si misura ogni riga con `textbbox` e non con l'altezza nominale del
    carattere: fra una riga di sole maiuscole e una con le lettere che vanno
    sotto la linea di base la differenza e' di qualche pixel, e su un pannello
    alto sessantaquattro qualche pixel e' un blocco che sembra storto.
    """
    alte = []
    for riga in righe:
        riquadro = disegna.textbbox((0, 0), riga or " ", font=font)
        alte.append((riquadro[1], riquadro[3] - riquadro[1],
                     riquadro[2] - riquadro[0]))
    totale = sum(h for _t, h, _w in alte) + interlinea * (len(righe) - 1)
    y = max(margine, (altezza - totale) // 2)
    for riga, (cima, alta, larga) in zip(righe, alte):
        x = max(margine, (larghezza - larga) // 2)
        disegna.text((x, y - cima), riga, font=font, fill=colore)
        y += alta + interlinea
