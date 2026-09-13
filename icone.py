"""Le icone del tempo, disegnate invece che caricate.

Perche' disegnate. Un pannello da 256x64 ha bisogno di icone alte una
trentina di pixel, e a quella dimensione un file PNG scalato diventa una
poltiglia: le forme si riconoscono per i bordi, e i bordi a trenta pixel sono
due o tre pixel di larghezza. Disegnarle con cerchi e linee vuol dire che ogni
pixel e' messo dove volevamo, che la dimensione si cambia con un numero, e che
il pacchetto non pesa un byte in piu'.

C'e' anche una ragione meno ovvia, ed e' il colore. Su un LED il contrasto non
funziona come su uno schermo: il nero e' spento, quindi un'icona scura non e'
scura, e' **assente**. Le forme qui sono tutte piene e chiare, e la
distinzione fra una nuvola e una nuvola con la pioggia non e' affidata a una
sfumatura ma a qualcosa che o c'e' o non c'e'.

## La regola delle famiglie

Le icone sono meno dei codici meteo, ed e' voluto: a trenta pixel la
differenza fra pioviggine moderata e pioviggine intensa non si puo' disegnare,
e due icone identiche con due nomi diversi sarebbero una bugia grafica. La
differenza la dice il testo, che di spazio ne ha.
"""

import math

# --------------------------------------------------------------------- colori

SOLE = (0xFF, 0xB0, 0x20)
LUNA = (0xE8, 0xE8, 0xC0)
NUVOLA = (0xD0, 0xD8, 0xE8)
NUVOLA_CUPA = (0x90, 0x98, 0xB0)
PIOGGIA = (0x50, 0xB0, 0xFF)
NEVE = (0xFF, 0xFF, 0xFF)
FULMINE = (0xFF, 0xE0, 0x30)
NEBBIA = (0xA8, 0xB0, 0xC0)
GRANDINE = (0xC8, 0xE8, 0xFF)

# Tutti i nomi che questo modulo sa disegnare. Chiedere un nome che non c'e'
# non e' un errore da eccezione: si disegna la nuvola, che e' il modo grafico
# di dire "qualcosa in cielo, ma non so dirti cosa".
NOMI = (
    "sereno", "sereno_notte", "poco_nuvoloso", "poco_nuvoloso_notte",
    "nuvoloso", "coperto", "nebbia", "pioggia", "pioggia_forte",
    "rovesci", "neve", "temporale", "grandine",
)


def _disco(d, cx, cy, r, colore):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=colore)


def _sole(d, cx, cy, r, colore=SOLE, raggi=True):
    """Il disco e gli otto raggi. I raggi partono staccati dal disco: attaccati
    formerebbero una macchia, e a questa dimensione una macchia rotonda e' gia'
    la Luna piena."""
    if raggi:
        dentro = r + max(2, r // 2)
        fuori = dentro + max(2, r // 2)
        for i in range(8):
            angolo = math.radians(i * 45)
            co, si = math.cos(angolo), math.sin(angolo)
            d.line([cx + co * dentro, cy + si * dentro,
                    cx + co * fuori, cy + si * fuori], fill=colore, width=1)
    _disco(d, cx, cy, r, colore)


def _luna(d, cx, cy, r, colore=LUNA, sfondo=(0, 0, 0)):
    """Una falce, ottenuta togliendo un disco spostato da un disco pieno.

    E' il modo piu' pulito a bassa risoluzione: disegnare l'arco della falce a
    mano darebbe un profilo seghettato, questo da' due curve vere."""
    _disco(d, cx, cy, r, colore)
    _disco(d, cx + r * 0.55, cy - r * 0.30, r * 0.92, sfondo)


def _nuvola(d, x, y, larghezza, altezza, colore=NUVOLA):
    """Tre gobbe e una base piatta. Le proporzioni sono fisse rispetto alla
    larghezza, cosi' l'icona si ridimensiona senza diventare un'altra forma."""
    r_grande = altezza * 0.52
    r_medio = altezza * 0.40
    r_piccolo = altezza * 0.32
    base = y + altezza
    _disco(d, x + larghezza * 0.34, base - r_grande, r_grande, colore)
    _disco(d, x + larghezza * 0.66, base - r_medio * 1.15, r_medio, colore)
    _disco(d, x + larghezza * 0.85, base - r_piccolo, r_piccolo, colore)
    _disco(d, x + larghezza * 0.14, base - r_piccolo, r_piccolo, colore)
    d.rectangle([x + larghezza * 0.14, base - r_piccolo,
                 x + larghezza * 0.85, base], fill=colore)


def _gocce(d, x, y, larghezza, quante, lunghezza, colore=PIOGGIA, obliquo=0):
    """Le gocce sotto la nuvola. `obliquo` le inclina: e' la differenza fra
    pioggia e rovescio, e si vede anche da lontano."""
    passo = larghezza / float(quante + 1)
    for i in range(quante):
        gx = x + passo * (i + 1)
        d.line([gx, y, gx + obliquo, y + lunghezza], fill=colore, width=1)


def _fiocco(d, cx, cy, r, colore=NEVE):
    """Tre segmenti incrociati: a sei pixel un fiocco vero non esiste, e questa
    e' la forma minima che si legge ancora come neve e non come polvere."""
    for angolo in (90, 30, 150):
        rad = math.radians(angolo)
        co, si = math.cos(rad), math.sin(rad)
        d.line([cx - co * r, cy - si * r, cx + co * r, cy + si * r],
               fill=colore, width=1)


def _fulmine(d, cx, cy, altezza, colore=FULMINE):
    """La saetta, come poligono pieno: a tratti sottili sparirebbe."""
    w = altezza * 0.36
    d.polygon([
        (cx + w * 0.20, cy),
        (cx - w * 0.55, cy + altezza * 0.56),
        (cx - w * 0.05, cy + altezza * 0.56),
        (cx - w * 0.40, cy + altezza),
        (cx + w * 0.70, cy + altezza * 0.44),
        (cx + w * 0.10, cy + altezza * 0.44),
    ], fill=colore)


def allerta(d, x, y, lato, colore):
    """Il triangolo di pericolo, nel colore dell'allerta.

    Non e' nella tabella dei nomi del tempo perche' non e' un tempo: e' un
    avviso, e il colore non lo sceglie questo modulo ma la gravita' che arriva
    dalla fonte. Un triangolo giallo e uno rosso sono la stessa forma e due
    cose diverse, e la differenza dev'essere leggibile dall'altra parte della
    stanza senza leggere una parola.
    """
    meta = lato / 2.0
    d.polygon([(x + meta, y + lato * 0.06),
               (x + lato * 0.97, y + lato * 0.92),
               (x + lato * 0.03, y + lato * 0.92)], fill=colore)
    # Il punto esclamativo si toglie, non si aggiunge: inciso nel nero fa un
    # bordo netto su un LED, disegnato sopra in un altro colore ne fa due.
    spessore = max(1, int(lato * 0.09))
    d.rectangle([x + meta - spessore / 2.0, y + lato * 0.30,
                 x + meta + spessore / 2.0, y + lato * 0.64], fill=(0, 0, 0))
    d.rectangle([x + meta - spessore / 2.0, y + lato * 0.72,
                 x + meta + spessore / 2.0, y + lato * 0.82], fill=(0, 0, 0))


def disegna(d, nome, x, y, lato, sfondo=(0, 0, 0)):
    """Disegna l'icona `nome` in un quadrato di lato `lato` con l'angolo in
    alto a sinistra in (x, y).

    `sfondo` serve solo alla falce di Luna, che si ottiene sottraendo: su un
    fondo diverso dal nero va detto qual e', altrimenti la sottrazione lascia
    un buco nero dentro l'icona.
    """
    nome = nome if nome in NOMI else "coperto"
    cx = x + lato / 2.0
    largo = lato * 0.86
    sx = x + (lato - largo) / 2.0

    if nome == "sereno":
        _sole(d, cx, y + lato * 0.46, lato * 0.22)
        return
    if nome == "sereno_notte":
        _luna(d, cx, y + lato * 0.46, lato * 0.30, sfondo=sfondo)
        return

    if nome in ("poco_nuvoloso", "poco_nuvoloso_notte"):
        # L'astro sta dietro e in alto a sinistra, la nuvola davanti in basso a
        # destra: e' la disposizione che si legge come "sole fra le nuvole"
        # anche quando le due forme si toccano.
        if nome.endswith("notte"):
            _luna(d, x + lato * 0.36, y + lato * 0.32, lato * 0.22,
                  sfondo=sfondo)
        else:
            _sole(d, x + lato * 0.36, y + lato * 0.32, lato * 0.16)
        _nuvola(d, sx + lato * 0.10, y + lato * 0.44, largo * 0.86,
                lato * 0.34)
        return

    if nome == "nuvoloso":
        _nuvola(d, sx, y + lato * 0.20, largo * 0.70, lato * 0.30,
                NUVOLA_CUPA)
        _nuvola(d, sx + largo * 0.24, y + lato * 0.42, largo * 0.76,
                lato * 0.34)
        return

    if nome == "coperto":
        _nuvola(d, sx, y + lato * 0.30, largo, lato * 0.42)
        return

    if nome == "nebbia":
        _nuvola(d, sx, y + lato * 0.18, largo, lato * 0.34, NEBBIA)
        for i in range(3):
            riga = y + lato * (0.62 + i * 0.13)
            # Righe di lunghezza diversa e sfalsate: tre righe uguali
            # sembrerebbero un simbolo di menu, non nebbia.
            inizio = sx + (largo * 0.16 if i % 2 else 0)
            fine = sx + largo * (0.84 if i % 2 else 1.0)
            d.line([inizio, riga, fine, riga], fill=NEBBIA, width=1)
        return

    if nome == "pioggia":
        _nuvola(d, sx, y + lato * 0.14, largo, lato * 0.38)
        _gocce(d, sx, y + lato * 0.60, largo, 3, lato * 0.20)
        return

    if nome == "pioggia_forte":
        _nuvola(d, sx, y + lato * 0.10, largo, lato * 0.38, NUVOLA_CUPA)
        _gocce(d, sx, y + lato * 0.56, largo, 5, lato * 0.28)
        return

    if nome == "rovesci":
        _nuvola(d, sx, y + lato * 0.12, largo, lato * 0.38)
        _gocce(d, sx, y + lato * 0.58, largo, 4, lato * 0.24,
               obliquo=-lato * 0.10)
        return

    if nome == "neve":
        _nuvola(d, sx, y + lato * 0.12, largo, lato * 0.38)
        for i in range(3):
            _fiocco(d, sx + largo * (0.22 + i * 0.28),
                    y + lato * (0.72 if i == 1 else 0.66), lato * 0.09)
        return

    if nome == "temporale":
        _nuvola(d, sx, y + lato * 0.10, largo, lato * 0.38, NUVOLA_CUPA)
        _fulmine(d, cx, y + lato * 0.52, lato * 0.40)
        return

    if nome == "grandine":
        _nuvola(d, sx, y + lato * 0.08, largo, lato * 0.36, NUVOLA_CUPA)
        _fulmine(d, cx + lato * 0.12, y + lato * 0.48, lato * 0.38)
        for i in range(2):
            _disco(d, sx + largo * (0.18 + i * 0.20),
                   y + lato * (0.70 + i * 0.10), max(1, lato * 0.045),
                   GRANDINE)
        return

    _nuvola(d, sx, y + lato * 0.30, largo, lato * 0.42)
