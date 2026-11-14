# -*- coding: utf-8 -*-
"""I nomi che non esistono, trovati prima di andare in onda.

La segnalazione
---------------
Una schermata del browser: **Internal Server Error** sulla pagina Video.
Dentro, una riga sola di vero:

    NameError: name 'uscita_video' is not defined

Il modulo `display`, dentro quella pagina, si importa **con un altro nome**
(`import display as uscita_video`) e l'import sta dentro la funzione della
pagina. Una funzione nuova accanto, che usava lo stesso nome, non lo
trovava. Python non se ne accorge finche' non ci passa, e li' ci passa solo
chi apre quella pagina.

Perche' questa prova esiste
---------------------------
Le prove di questo progetto guardano quello che il programma **fa**:
geometrie, fotogrammi, partite, passaggi di aerei. Un nome sbagliato in una
pagina web non lo vede nessuna di quelle, perche' le pagine non le apre
nessuno -- finche' non le apre l'utente, che e' il modo peggiore di
scoprirlo.

Questa invece non prova niente: **legge**. Chiede a `pyflakes` quali nomi,
in tutto il progetto, vengono usati senza essere mai definiti. E' il
controllo che avrebbe fermato quel 500 prima che partisse, e costa un
secondo.

Cosa non e'
-----------
Non e' un formattatore e non e' un giudice di stile: si guarda **F821**, i
nomi che non esistono, e basta. Righe lunghe, import inutilizzati e
virgolette storte non sono difetti: sono opinioni.

Dove manca `pyflakes` la prova si salta dicendolo. E' uno strumento da banco
di lavoro, non una dipendenza dell'apparecchio: sul Raspberry non serve, e
non si installa una libreria su un apparecchio per un controllo che si fa
qui.
"""

import os
import subprocess
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Le cartelle di roba altrui: Doom e il Game Boy portano dentro codice che
# non abbiamo scritto noi e che non tocchiamo.
FUORI = ("doom", "gb")

esiti = []


def esigi(condizione, messaggio):
    esiti.append((bool(condizione), messaggio))
    print("%s %s" % ("OK  " if condizione else "FALLITO", messaggio))


def pyflakes_disponibile():
    try:
        import pyflakes                                    # noqa: F401
        return [sys.executable, "-m", "pyflakes"]
    except ImportError:
        pass
    for comando in ("pyflakes", "flake8"):
        for cartella in os.environ.get("PATH", "").split(os.pathsep):
            percorso = os.path.join(cartella, comando)
            if os.path.isfile(percorso) and os.access(percorso, os.X_OK):
                if comando == "flake8":
                    return [percorso, "--select=F821"]
                return [percorso]
    return None


def file_da_guardare():
    fuori = []
    for cartella, sotto, nomi in os.walk(RADICE):
        relativa = os.path.relpath(cartella, RADICE)
        prima = relativa.split(os.sep)[0]
        if prima == ".":
            prima = ""            # la radice del progetto: e' il posto giusto
        if prima in FUORI or prima.startswith(".") or "__pycache__" in cartella:
            sotto[:] = []
            continue
        for nome in sorted(nomi):
            if nome.endswith(".py"):
                fuori.append(os.path.join(cartella, nome))
    return fuori


print("=" * 74)
print("I nomi che non esistono (F821)")
print("=" * 74)

comando = pyflakes_disponibile()
if comando is None:
    print()
    print("     (saltata: qui non c'e' pyflakes. E' uno strumento da banco di")
    print("      lavoro -- `pip install pyflakes` -- non una dipendenza")
    print("      dell'apparecchio.)")
    sys.exit(0)

sorgenti = file_da_guardare()
print()
print("     %d file, con %s" % (len(sorgenti), " ".join(comando)))

uscita = subprocess.run(comando + sorgenti, capture_output=True, text=True)
righe = [r for r in (uscita.stdout or "").splitlines() if "F821" in r
         or "undefined name" in r]
for riga in righe:
    print("     %s" % riga.replace(RADICE + os.sep, ""))

esigi(not righe,
      "nessun nome usato senza esistere (%d trovati)" % len(righe))

print()
print("=" * 74)
falliti = [m for ok, m in esiti if not ok]
if falliti:
    print("FALLITI %d su %d" % (len(falliti), len(esiti)))
    for m in falliti:
        print("  - %s" % m)
    sys.exit(1)
print("TUTTO BENE: %d prove" % len(esiti))
