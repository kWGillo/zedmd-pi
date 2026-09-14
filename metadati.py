# -*- coding: utf-8 -*-
"""I metadati di AirPlay presi dove nascono, senza passare da un broker.

Perche' esiste
--------------
shairport-sync e il DMD girano sulla **stessa macchina**. Fino alla 7.3 si
parlavano lo stesso attraverso un server di rete: shairport-sync pubblicava su
MQTT, il DMD si iscriveva, e in mezzo c'erano un indirizzo, una porta, un
utente e una password — scritti in **due file diversi**, che nessuno teneva
allineati.

Non e' una preoccupazione teorica: e' costato una serata. Il broker di casa ha
cambiato indirizzo, la pagina web ha aggiornato la configurazione del DMD, e
`/etc/shairport-sync.conf` e' rimasto a puntare all'indirizzo vecchio. Il
telefono vedeva la cassa, la musica partiva, e sul pannello non compariva
niente — senza un errore, perche' dal punto di vista di ognuno dei due
programmi andava tutto bene.

shairport-sync pero' sa gia' scrivere i metadati in una **pipe locale**. Un
file, sulla stessa macchina, senza indirizzi da tenere allineati e senza
password da riscrivere in due posti. Quello che si puo' sbagliare qui e' che
la pipe non ci sia: e allora si vede subito, perche' non arriva niente e la
pagina lo dice.

MQTT resta come ripiego, e non e' un ripensamento: chi ha gia' tutto
configurato e funzionante non deve toccare niente, e le due strade portano
allo stesso posto — `nowplaying.handle_shairport`, che i codici a quattro
lettere li gestisce da sempre.

Il formato, che e' piu' semplice di come sembra
-----------------------------------------------
shairport-sync scrive una sequenza di elementi cosi::

    <item><type>73736e63</type><code>70626567</code><length>0</length></item>
    <item><type>636f7265</type><code>6d696e6d</code><length>7</length>
    <data encoding="base64">QmVhdXR5</data></item>

`type` e `code` sono quattro caratteri ASCII scritti in esadecimale:
`73736e63` e' `ssnc`, `6d696e6d` e' `minm`. Il `data` c'e' solo se la
lunghezza e' maggiore di zero, ed e' base64 che puo' andare a capo.

I due tipi che contano:

  ``core``   i metadati del brano: ``minm`` titolo, ``asar`` artista,
             ``asal`` album.
  ``ssnc``   quello che fa shairport-sync: ``pbeg`` inizio, ``pend`` fine,
             ``prsm`` ripresa, ``pfls`` pausa o salto, ``prgr`` posizione,
             ``snam`` il nome di chi sta trasmettendo.

Sono **gli stessi codici** che arrivavano dai topic grezzi di MQTT, quindi qui
non si interpreta niente: si spacchetta e si passa oltre.

Perche' la pipe si apre in lettura **e** scrittura
--------------------------------------------------
Una FIFO aperta in sola lettura da' EOF ogni volta che l'ultimo scrittore la
chiude — cioe' alla fine di ogni brano. Con `select` che la segnala sempre
pronta e una lettura che torna vuota, sarebbe un giro a vuoto a consumare CPU
su una macchina che ha un pannello da tenere fermo.

Aprendola anche in scrittura uno scrittore c'e' sempre (siamo noi), l'EOF non
arriva mai, e `select` si comporta come ci si aspetta. Su Linux e' l'idioma
consueto; POSIX lo lascia indefinito, ma questo programma gira su un
Raspberry e non altrove.
"""

import base64
import binascii
import os
import re
import select
import stat
import threading
import time

# Dove shairport-sync scrive, quando glielo si chiede. E' anche il valore
# predefinito della sua configurazione.
PIPE = "/tmp/shairport-sync-metadata"

_ITEM = re.compile(rb"<item>(.*?)</item>", re.DOTALL)
_TIPO = re.compile(rb"<type>\s*([0-9a-fA-F]+)\s*</type>")
_CODICE = re.compile(rb"<code>\s*([0-9a-fA-F]+)\s*</code>")
_DATI = re.compile(rb"<data[^>]*>(.*?)</data>", re.DOTALL)

# Quanto puo' crescere il pezzo di elemento ancora incompleto. Una copertina
# in JPEG puo' arrivare a qualche centinaio di kilobyte, e la si vuole poter
# ricevere per intero; oltre questo tetto non e' piu' un elemento a meta', e'
# qualcosa che non tornera' mai — e tenerlo in memoria non aiuterebbe
# nessuno.
TETTO = 4 * 1024 * 1024

# Quanto si aspetta prima di riprovare, se la pipe non c'e' o non si apre.
RIPROVA = 5.0

# Timeout di `select`: quanto ci mette al massimo a accorgersi che deve
# fermarsi.
ATTESA = 1.0


def _quattro(esadecimale):
    """`6d696e6d` -> `minm`. Vuoto se non e' quello che dice di essere."""
    try:
        grezzi = binascii.unhexlify(esadecimale)
    except (binascii.Error, ValueError, TypeError):
        return ""
    return grezzi.decode("ascii", "replace")


def analizza(buffer):
    """Gli elementi completi dentro `buffer`, e quello che resta a meta'.

    Restituisce ([(tipo, codice, dati)], resto). I dati sono byte grezzi:
    decidere se sono testo, un numero o un'immagine tocca a chi li riceve.

    Si lavora su byte e non su testo apposta: dentro `data` puo' esserci una
    copertina in JPEG, e una decodifica in utf-8 fatta qui la rovinerebbe
    prima ancora di sapere che cos'era.
    """
    fuori = []
    fine = 0
    for trovato in _ITEM.finditer(buffer):
        fine = trovato.end()
        dentro = trovato.group(1)
        tipo = _TIPO.search(dentro)
        codice = _CODICE.search(dentro)
        if not tipo or not codice:
            continue
        dati = b""
        blocco = _DATI.search(dentro)
        if blocco:
            try:
                dati = base64.b64decode(blocco.group(1))
            except (binascii.Error, ValueError):
                dati = b""
        fuori.append((_quattro(tipo.group(1)), _quattro(codice.group(1)), dati))
    resto = buffer[fine:]
    if len(resto) > TETTO:
        # Nessun elemento completo e piu' di quattro megabyte in pancia: non
        # e' un elemento spezzato, e' spazzatura. Si riparte dall'ultimo
        # `<item>` che si vede, e se non ce n'e' nessuno si butta tutto.
        inizio = resto.rfind(b"<item>")
        resto = resto[inizio:] if inizio >= 0 else b""
    return fuori, resto


class Metadati:
    """Legge la pipe di shairport-sync e passa i codici a chi li sa leggere.

    `gestore` ha la stessa firma dei messaggi MQTT — `(topic, payload)` — e
    nella pratica e' `nowplaying.handle_shairport`. Non e' pigrizia: quella
    funzione i codici a quattro lettere li gestisce gia' tutti, ed era il
    motivo per cui questa strada costava poco.
    """

    def __init__(self, cfg, gestore, percorso=None):
        self.cfg = cfg
        self._gestore = gestore
        self._percorso = percorso or PIPE
        self._stop = threading.Event()
        self._thread = None
        # Quel che serve alla pagina per dire come sta andando.
        self.elementi = 0
        self.ultimo = 0.0           # ora di sistema dell'ultimo elemento
        self.errore = ""
        self.aperta = False

    # -------------------------------------------------------------- impostazioni

    def settings(self):
        return (self.cfg.get("nowplaying") or {})

    def voluta(self):
        """Se si deve leggere la pipe. Accesa di suo: e' la strada nuova."""
        return bool(self.settings().get("pipe", True))

    def percorso(self):
        scritto = str(self.settings().get("pipe_percorso") or "").strip()
        return scritto or self._percorso

    # ---------------------------------------------------------------- vita

    def start(self):
        if self._thread is not None or not self.voluta():
            return False
        self._stop.clear()
        self._thread = threading.Thread(target=self._ciclo, name="metadati",
                                        daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self._stop.set()
        thread, self._thread = self._thread, None
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)

    def status(self):
        percorso = self.percorso()
        return {"percorso": percorso, "esiste": esiste(percorso),
                "aperta": self.aperta, "elementi": self.elementi,
                "ultimo": self.ultimo, "errore": self.errore,
                "voluta": self.voluta()}

    # -------------------------------------------------------------- lettura

    def _apri(self):
        percorso = self.percorso()
        if not esiste(percorso):
            self.errore = "la pipe non c'e': %s" % percorso
            return None
        try:
            # Lettura **e** scrittura: vedi la nota in cima al modulo. Senza,
            # ogni fine brano diventa un EOF e un giro a vuoto.
            fd = os.open(percorso, os.O_RDWR | os.O_NONBLOCK)
        except OSError as exc:
            self.errore = str(exc)
            return None
        self.errore = ""
        return fd

    def _ciclo(self):
        while not self._stop.is_set():
            fd = self._apri()
            if fd is None:
                self.aperta = False
                self._stop.wait(RIPROVA)
                continue
            self.aperta = True
            try:
                self._leggi(fd)
            except Exception as exc:                # pragma: no cover
                self.errore = str(exc)
                print("[metadati] lettura interrotta: %s" % exc)
            finally:
                self.aperta = False
                try:
                    os.close(fd)
                except OSError:
                    pass
            if not self._stop.is_set():
                self._stop.wait(RIPROVA)

    def _leggi(self, fd):
        buffer = b""
        while not self._stop.is_set():
            try:
                pronti, _s, _e = select.select([fd], [], [], ATTESA)
            except (OSError, ValueError):
                return
            if not pronti:
                continue
            try:
                pezzo = os.read(fd, 65536)
            except BlockingIOError:
                continue
            except OSError as exc:
                self.errore = str(exc)
                return
            if not pezzo:
                # Con la pipe aperta anche in scrittura non dovrebbe capitare.
                # Se capita lo stesso non si gira a vuoto: si esce, e il ciclo
                # esterno riapre con calma.
                return
            buffer += pezzo
            elementi, buffer = analizza(buffer)
            for tipo, codice, dati in elementi:
                self._consegna(tipo, codice, dati)

    def _consegna(self, tipo, codice, dati):
        """Passa un elemento a chi lo sa leggere, se puo' interessargli."""
        if tipo not in ("core", "ssnc") or not codice:
            return
        self.elementi += 1
        self.ultimo = time.time()
        try:
            # Il topic finto serve solo a far arrivare il codice dove il
            # gestore lo cerca, cioe' nell'ultimo livello. E' la stessa forma
            # che avevano i topic grezzi di MQTT — `shairport/ssnc/prgr` —
            # quindi dall'altra parte non cambia niente.
            self._gestore("metadati/%s/%s" % (tipo, codice), dati)
        except Exception as exc:                    # pragma: no cover
            print("[metadati] errore su %s/%s: %s" % (tipo, codice, exc))


def esiste(percorso=None):
    """Vero se quel percorso c'e' ed e' davvero una FIFO."""
    percorso = percorso or PIPE
    try:
        return stat.S_ISFIFO(os.stat(percorso).st_mode)
    except OSError:
        return False
