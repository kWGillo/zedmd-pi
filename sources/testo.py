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

# Sotto questo corpo non si scende. Sei pixel sono gia' illeggibili: se
# nemmeno a sei il testo ci sta, vuol dire che c'e' da tagliare, non da
# rimpicciolire ancora.
MINIMO = 6


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


def ingombro(righe, font, misura=None, interlinea=INTERLINEA):
    """(larghezza della riga piu' larga, altezza del blocco), misurate.

    **Misurate**, non calcolate dal corpo del carattere: e' la correzione di
    due difetti che la versione precedente aveva tutti e due, e che si vedono
    solo guardando il pannello.

    L'altezza vera di una riga non e' il corpo del carattere. Un DejaVu da 13
    px disegna un blocco alto quindici o sedici quando ci sono accenti e
    lettere che scendono sotto la riga, e quattro righe cosi' sforano di un
    pixel su un pannello alto sessantaquattro: la quarta riga esce dal basso.

    La larghezza vera puo' essere qualunque cosa. `spezza` non taglia mai una
    parola a meta', quindi una parola sola piu' larga del pannello resta una
    riga sola -- e una riga sola «entra» in qualunque impaginazione se ci si
    limita a contare le righe. Contandole, il testo sbordava di lato senza
    che niente lo rimpicciolisse.
    """
    misura = misura or _misuratore()
    larga, alta = 0, 0
    for riga in righe:
        riquadro = misura.textbbox((0, 0), riga or " ", font=font)
        larga = max(larga, riquadro[2] - riquadro[0])
        alta += riquadro[3] - riquadro[1]
    return larga, alta + interlinea * max(0, len(righe) - 1)


def _sta(righe, font, larghezza, altezza, interlinea, misura):
    larga, alta = ingombro(righe, font, misura, interlinea)
    return larga <= larghezza and alta <= altezza


def _tagliate(testo, font, larghezza, righe_massime, misura):
    """Le prime righe, con i puntini dove si e' tagliato qualcosa."""
    righe = spezza(testo, font, larghezza, misura)
    tenute = list(righe[:righe_massime]) or [""]
    if len(righe) > righe_massime:
        tenute[-1] = accorcia(tenute[-1], font, larghezza, misura)
    # Qualunque riga puo' sbordare, non solo l'ultima: basta che contenga una
    # parola piu' larga del pannello, che `spezza` lascia intera apposta.
    for indice, riga in enumerate(tenute):
        if misura.textlength(riga, font=font) > larghezza:
            tenute[indice] = accorcia(riga, font, larghezza, misura)
    return tenute


def impagina(testo, larghezza, altezza, tetto, righe_massime=RIGHE_MASSIME,
             interlinea=INTERLINEA):
    """Righe e carattere: il piu' grande in cui il testo ci sta **davvero**.

    Si provano una, due, tre, quattro righe e si tiene la prima impaginazione
    che entra: e' lo stesso criterio con cui l'orologio sceglie il carattere
    della colonna dei rifiuti, e ha il pregio che un messaggio corto resta
    grande invece di rimpicciolirsi per uniformita'.

    «Entra» vuol dire **misurata**, non contata: vedi `ingombro`.

    `tetto` e' la dimensione massima del carattere. Serve, e si vede
    togliendola: su una riga sola, senza tetto, un «OK» riempirebbe il
    pannello da bordo a bordo.

    Se nessuna impaginazione entra si scende di corpo un pixel per volta,
    tagliando quello che avanza. La discesa e' l'ultima rete: prende i casi
    che il conteggio delle righe non vede, come una parola unica piu' larga
    del pannello, che va accorciata perche' non c'e' nessun altro modo di
    farla stare.
    """
    misura = _misuratore()
    righe_massime = max(1, righe_massime)
    for quante in range(1, righe_massime + 1):
        alta = (altezza - (quante - 1) * interlinea) // quante
        font = _load_font(max(MINIMO, min(tetto, alta)))
        righe = spezza(testo, font, larghezza, misura)
        if len(righe) <= quante and _sta(righe, font, larghezza, altezza,
                                         interlinea, misura):
            return righe, font

    partenza = max(MINIMO, min(tetto, (altezza - (righe_massime - 1) * interlinea)
                               // righe_massime))
    for corpo in range(partenza, MINIMO - 1, -1):
        font = _load_font(corpo)
        righe = _tagliate(testo, font, larghezza, righe_massime, misura)
        if _sta(righe, font, larghezza, altezza, interlinea, misura):
            return righe, font
    font = _load_font(MINIMO)
    return _tagliate(testo, font, larghezza, righe_massime, misura), font


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
