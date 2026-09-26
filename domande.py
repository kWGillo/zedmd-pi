# -*- coding: utf-8 -*-
"""Le domande di Super Quiz: due banche, una per lingua.

Dove stanno
-----------
`domande.it.csv` e `domande.en.csv` stanno in cima all'installazione, come i
santi e le giornate: sono calendari, non configurazione. Chi vuole
aggiungerne di sue -- quelle di famiglia, quelle che fanno ridere a Natale --
mette un file con lo **stesso nome** nella cartella dati (`/var/lib/dmd`):
viene letto dopo e si aggiunge, e gli aggiornamenti non lo toccano mai.

Lo stesso numero nelle due lingue
---------------------------------
La fonte e' parallela: la stessa domanda esiste in italiano e in inglese con
lo **stesso identificativo**. E' quello che permette di tenere un conto solo
delle domande gia' uscite: chi gioca in inglese non si rivede in italiano
quello che ha gia' visto un minuto prima. Le domande scritte a mano da te
possono benissimo esistere in una lingua sola -- semplicemente non compaiono
quando l'interfaccia e' nell'altra, invece di comparire vuote.

Cosa non c'e'
-------------
Nessuna chiamata di rete. Una domanda deve arrivare in millesimi, e un quiz
che ogni tanto si inchioda ad aspettare un sito e' un quiz rotto -- senza
contare che l'archivio da cui vengono ammette una richiesta ogni cinque
secondi. Le domande si aggiornano quando lo chiedi tu, dalla pagina, come il
software: mai da sole e mai durante una partita.
"""

import csv
import io
import os
import random
import threading
import time

DATA_DIR = os.environ.get("DMD_DATA", "/var/lib/dmd")
PROGRAMMA = os.path.dirname(os.path.abspath(__file__))

LINGUE = ("it", "en")
NOME = "domande.%s.csv"

# Quante domande tenere in memoria fra quelle gia' uscite. Serve a non
# rivedere la stessa domanda per un po', ed e' un numero e non "tutte" perche'
# a furia di ricordare si finisce col non avere piu' niente da chiedere.
MEMORIA = 400

_lucchetto = threading.Lock()
_cache = {}          # lingua -> (impronte dei file, elenco)


def percorsi(lingua):
    """I due file da leggere: il nostro e, se c'e', il tuo."""
    nome = NOME % lingua
    return [os.path.join(PROGRAMMA, nome), os.path.join(DATA_DIR, nome)]


def _impronta(percorsi_):
    fuori = []
    for percorso in percorsi_:
        try:
            info = os.stat(percorso)
            fuori.append((percorso, info.st_mtime, info.st_size))
        except OSError:
            fuori.append((percorso, 0, 0))
    return tuple(fuori)


def analizza(testo, fonte=""):
    """Da CSV a elenco di domande. Le righe rotte si perdono da sole."""
    fuori = []
    if not testo:
        return fuori
    for campi in csv.reader(io.StringIO(testo), delimiter=";"):
        if not campi or campi[0].lstrip().startswith("#"):
            continue
        if len(campi) < 8:
            continue
        risposte = [c.strip() for c in campi[4:8]]
        if not campi[3].strip() or len(set(risposte)) != 4 or not all(risposte):
            continue
        try:
            difficolta = max(1, min(3, int(campi[2])))
        except (TypeError, ValueError):
            difficolta = 2
        fuori.append({
            "id": campi[0].strip(),
            "categoria": campi[1].strip(),
            "difficolta": difficolta,
            "domanda": campi[3].strip(),
            # La **prima** e' sempre quella giusta nel file; sul pannello si
            # mescolano, ed e' l'unico posto in cui succede.
            "risposte": risposte,
            "giusta": risposte[0],
            "curiosita": campi[8].strip() if len(campi) > 8 else "",
            "fonte": fonte,
        })
    return fuori


def carica(lingua="it"):
    """Le domande di quella lingua, rilette quando i file cambiano."""
    lingua = lingua if lingua in LINGUE else "it"
    quali = percorsi(lingua)
    impronta = _impronta(quali)
    with _lucchetto:
        avuto = _cache.get(lingua)
        if avuto and avuto[0] == impronta:
            return avuto[1]
    elenco, visti = [], set()
    for percorso in quali:
        try:
            with open(percorso, encoding="utf-8", errors="replace") as handle:
                testo = handle.read()
        except OSError:
            continue
        for voce in analizza(testo, os.path.basename(percorso)):
            # Le tue vincono: se ripeti un identificativo nostro, comanda la
            # tua riga. E' la regola delle tabelle del radar, applicata qui.
            if voce["id"] in visti:
                elenco = [v for v in elenco if v["id"] != voce["id"]]
            visti.add(voce["id"])
            elenco.append(voce)
    with _lucchetto:
        _cache[lingua] = (impronta, elenco)
    return elenco


def invalida():
    with _lucchetto:
        _cache.clear()


def quante(lingua="it"):
    return len(carica(lingua))


def stato():
    """Quante domande per lingua, e da quali file: per la pagina web."""
    fuori = {}
    for lingua in LINGUE:
        elenco = carica(lingua)
        fuori[lingua] = {
            "quante": len(elenco),
            "tue": len([v for v in elenco
                        if v["fonte"] and DATA_DIR in percorsi(lingua)[1]
                        and v["fonte"] == os.path.basename(percorsi(lingua)[1])]),
            "file": [p for p in percorsi(lingua) if os.path.exists(p)],
        }
    return fuori


class Mazzo:
    """Le domande di una partita: pescate per difficolta', senza ripetersi.

    `viste` e' la lista degli identificativi gia' usciti, che arriva dalla
    configurazione e ci torna: e' quella che fa si' che due partite di fila
    non facciano le stesse domande. Se le domande non bastano piu', la
    memoria si accorcia da sola invece di lasciare il mazzo vuoto -- meglio
    una domanda gia' vista che nessuna domanda.
    """

    def __init__(self, lingua="it", viste=None, seme=None):
        self.lingua = lingua
        self.viste = list(viste or [])
        self._caso = random.Random(seme)
        self._elenco = carica(lingua)
        self._usate = []

    def disponibili(self, difficolta=None):
        fuori = [v for v in self._elenco
                 if difficolta is None or v["difficolta"] == difficolta]
        return fuori

    def pesca(self, difficolta=None):
        """Una domanda, con le risposte gia' mescolate. None se non ce ne sono."""
        candidate = self.disponibili(difficolta)
        if not candidate and difficolta is not None:
            candidate = self.disponibili()
        if not candidate:
            return None
        escluse = set(self.viste) | {v["id"] for v in self._usate}
        fresche = [v for v in candidate if v["id"] not in escluse]
        if not fresche:
            # Finite quelle nuove: si riparte da quelle piu' vecchie, che e'
            # sempre meglio che finire la partita a meta'.
            fresche = [v for v in candidate
                       if v["id"] not in {u["id"] for u in self._usate}]
        if not fresche:
            fresche = candidate
        scelta = self._caso.choice(fresche)
        self._usate.append(scelta)
        mescolate = list(scelta["risposte"])
        self._caso.shuffle(mescolate)
        return {
            "id": scelta["id"],
            "categoria": scelta["categoria"],
            "difficolta": scelta["difficolta"],
            "domanda": scelta["domanda"],
            "risposte": mescolate,
            "giusta": mescolate.index(scelta["giusta"]),
            "curiosita": scelta["curiosita"],
        }

    def memoria(self):
        """Gli identificativi da ricordare per la prossima partita."""
        nuove = [v["id"] for v in self._usate]
        tenuta = nuove + [v for v in self.viste if v not in nuove]
        return tenuta[:MEMORIA]
