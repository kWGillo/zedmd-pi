"""Le briciole che i Mac lasciano nelle cartelle condivise.

Ogni volta che un Mac copia qualcosa su una condivisione SMB si porta dietro
dei file che non gli ha chiesto nessuno: `.DS_Store` con la posizione delle
icone, e soprattutto i **file AppleDouble** -- quelli che cominciano con `._`
-- che contengono il resource fork e i metadati di ogni singolo file copiato.
Su una libreria di cinquemila foto diventano cinquemila file invisibili, che
il Raspberry si ritrova a elencare a ogni giro del Media Player.

Non fanno danno, ma sporcano: allungano le scansioni, gonfiano i backup, e nel
gestore dei media compaiono come file veri con nomi incomprensibili.

**Perche' una lista di nomi e non "tutto quello che comincia con un punto".**
La richiesta era in quei termini, e sarebbe stata anche la regola piu' facile
da scrivere. Ma una cartella condivisa e' di chi la usa: se un giorno ci
finisce dentro un `.stfolder` di Syncthing, un `.git`, o un `.nomedia`, una
regola cieca li cancellerebbe e nessuno capirebbe perche' quella cosa ha
smesso di funzionare. Le briciole dei Mac hanno nomi conosciuti e fissi da
vent'anni: si cancellano quelle, e si sa sempre cosa e' stato tolto.

**Perche' un thread e non un timer di systemd.** L'aggiornamento via rete non
esegue `install.sh`: un'unita' nuova non arriverebbe mai sulle macchine gia'
installate, e la funzione resterebbe spenta senza dirlo. Un giro dentro il
servizio, invece, c'e' dal primo riavvio dopo l'aggiornamento.
"""

import os
import threading
import time

# I nomi esatti. Fissi da vent'anni, e nessuno di questi e' mai stato scritto
# da qualcosa che volevi tenere.
NOMI = {
    ".DS_Store",
    ".localized",
    ".apdisk",
    ".VolumeIcon.icns",
    ".com.apple.timemachine.donotpresent",
    ".com.apple.timemachine.supported",
}

# I file AppleDouble: per ogni `foto.jpg` copiato da un Mac compare un
# `._foto.jpg` con dentro il resource fork. Sono il grosso del disordine.
PREFISSI = ("._",)

# Cartelle intere che il Finder e Spotlight creano da soli. Si tolgono con
# tutto il contenuto: dentro non c'e' niente che qualcuno abbia messo.
CARTELLE = {
    ".AppleDouble",
    ".AppleDB",
    ".AppleDesktop",
    ".Spotlight-V100",
    ".TemporaryItems",
    ".Trashes",
    ".fseventsd",
    ".DocumentRevisions-V100",
    ".TheVolumeSettingsFolder",
}

# Un tetto al numero di file che un solo giro puo' cancellare. Non e' una
# misura contro i Mac -- e' contro un errore mio: se un giorno una regola
# sbagliata cominciasse a riconoscere file veri, meglio accorgersene a
# cinquemila che a mezza libreria.
MASSIMO = 5000


def da_buttare(nome):
    """Questo nome e' una briciola?"""
    if nome in NOMI:
        return True
    for prefisso in PREFISSI:
        if nome.startswith(prefisso) and len(nome) > len(prefisso):
            return True
    return False


def _dentro(percorso, radice):
    """Il percorso sta davvero dentro la radice, seguendo i link?

    Una condivisione puo' contenere un collegamento a qualunque punto del
    disco. Senza questo controllo, un link a `/` trasformerebbe una pulizia
    in una passeggiata per tutto il filesystem.
    """
    vero = os.path.realpath(percorso)
    radice = os.path.realpath(radice)
    return vero == radice or vero.startswith(radice + os.sep)


def pulisci(radici, massimo=MASSIMO, prova=False):
    """Toglie le briciole dalle cartelle indicate.

    Con `prova=True` conta e basta: serve a guardare prima di cancellare.

    Torna un dizionario con quanti file, quanti byte, e l'elenco dei primi
    nomi -- che e' quello che si vuole vedere in una riga di stato: non
    l'elenco completo di cinquemila voci, ma abbastanza per riconoscere che
    sono davvero briciole e non qualcosa di tuo.
    """
    tolti = 0
    byte = 0
    esempi = []
    errori = []
    for radice in radici:
        if not radice or not os.path.isdir(radice):
            continue
        radice = os.path.realpath(radice)
        for cartella, sottocartelle, file in os.walk(radice, topdown=True):
            if not _dentro(cartella, radice):
                sottocartelle[:] = []
                continue
            # Le cartelle di servizio si tolgono intere, e non ci si scende.
            restanti = []
            for nome in sottocartelle:
                percorso = os.path.join(cartella, nome)
                if nome in CARTELLE and not os.path.islink(percorso):
                    # `prova` va passato anche qui. Nella prima versione non
                    # c'era, e "guarda e basta" cancellava lo stesso le
                    # cartelle di Spotlight e del cestino: il pulsante che
                    # serve a non fare danni ne faceva. Trovato da una prova
                    # che conta i file prima e dopo, non da una rilettura.
                    quanti, quanto, err = _via_cartella(percorso, prova)
                    tolti += quanti
                    byte += quanto
                    errori += err
                    if quanti and len(esempi) < 8:
                        esempi.append(nome + "/")
                    continue
                restanti.append(nome)
            sottocartelle[:] = restanti

            for nome in file:
                if not da_buttare(nome):
                    continue
                if tolti >= massimo:
                    errori.append("fermato al tetto di %d file" % massimo)
                    return _esito(tolti, byte, esempi, errori)
                percorso = os.path.join(cartella, nome)
                try:
                    dimensione = os.path.getsize(percorso)
                except OSError:
                    dimensione = 0
                if prova:
                    tolti += 1
                    byte += dimensione
                else:
                    try:
                        os.remove(percorso)
                        tolti += 1
                        byte += dimensione
                    except OSError as exc:
                        errori.append("%s: %s" % (nome, exc))
                        continue
                if len(esempi) < 8:
                    esempi.append(nome)
    return _esito(tolti, byte, esempi, errori)


def _via_cartella(percorso, prova=False):
    """Cancella una cartella di servizio con tutto il contenuto."""
    quanti = 0
    byte = 0
    errori = []
    for cartella, _sotto, file in os.walk(percorso, topdown=False):
        for nome in file:
            p = os.path.join(cartella, nome)
            try:
                byte += os.path.getsize(p)
            except OSError:
                pass
            if prova:
                quanti += 1
                continue
            try:
                os.remove(p)
                quanti += 1
            except OSError as exc:
                errori.append("%s: %s" % (nome, exc))
        if not prova:
            try:
                os.rmdir(cartella)
            except OSError:
                pass
    return quanti, byte, errori


def _esito(tolti, byte, esempi, errori):
    return {"file": tolti, "byte": byte, "esempi": esempi,
            "errori": errori[:5], "quando": time.time()}


def cartelle(cfg):
    """Le cartelle condivise, prese dalla configurazione e non indovinate.

    Se l'utente ha spostato la libreria, la pulizia lo segue. L'elenco si puo'
    scavalcare dalla configurazione, per chi ha altre condivisioni.
    """
    conf = cfg.get("pulizia") or {}
    scelte = [str(c).strip() for c in (conf.get("cartelle") or []) if str(c).strip()]
    if scelte:
        return scelte
    trovate = []
    # `mediaplayer`, non `media`: la prima versione guardava nella sezione
    # sbagliata e la libreria -- cioe' la cartella che i Mac sporcano di piu'
    # -- non veniva pulita mai. Nessun errore, nessun messaggio: semplicemente
    # non succedeva niente.
    for percorso in ((cfg.get("mediaplayer") or {}).get("media_dir"),
                     (cfg.get("gameboy") or {}).get("rom_dir"),
                     "/srv/dmd/doom"):
        if percorso and percorso not in trovate:
            trovate.append(percorso)
    return trovate


class Pulitore(object):
    """Il giro periodico. Sta dentro il servizio, non in un timer di sistema."""

    def __init__(self, cfg):
        self.cfg = cfg
        self._running = False
        self._thread = None
        self._sveglia = threading.Event()
        self.ultimo = {}

    def _conf(self):
        return self.cfg.get("pulizia") or {}

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="pulizia",
                                        daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._sveglia.set()

    def adesso(self, prova=False):
        """Un giro subito. Lo chiama il pulsante nella pagina Media."""
        esito = pulisci(cartelle(self.cfg),
                        massimo=int(self._conf().get("massimo", MASSIMO)),
                        prova=prova)
        if not prova:
            self.ultimo = esito
            if esito["file"]:
                print("[pulizia] %d file tolti (%s)"
                      % (esito["file"], ", ".join(esito["esempi"][:4])))
        return esito

    def _loop(self):
        # Non al primo istante: all'avvio il Raspberry ha di meglio da fare che
        # camminare su cinquemila file, e il pannello deve accendersi.
        self._sveglia.wait(120.0)
        while self._running:
            try:
                if self._conf().get("enabled", True):
                    self.adesso()
            except Exception as exc:            # noqa: BLE001
                print("[pulizia] %s" % exc)
            ore = max(1.0, float(self._conf().get("ore", 12) or 12))
            self._sveglia.wait(ore * 3600.0)
            self._sveglia.clear()
