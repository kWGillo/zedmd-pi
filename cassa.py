# -*- coding: utf-8 -*-
"""Il DMD come cassa AirPlay: la musica esce davvero dalla scheda audio.

Che cosa cambia, in una riga
----------------------------
`setup_nowplaying.sh` configura shairport-sync per scrivere l'audio nella
scheda **fittizia** del kernel: dei brani il DMD prendeva solo i metadati —
titolo, artista, avanzamento — e il suono lo buttava via, perche' non c'era
niente da cui farlo uscire. Con una scheda USB collegata quella scelta non ha
piu' motivo di esistere: si sposta l'uscita di shairport-sync sulla scheda
vera e il pannello diventa una cassa AirPlay a tutti gli effetti.

Tutto qui: si cambia **una riga** di `/etc/shairport-sync.conf` e si riavvia
il servizio. Il resto di questo modulo esiste per fare quella cosa senza
lasciare macerie.

Solo AirPlay, e va detto
------------------------
Le tre sorgenti di Now Playing non sono la stessa cosa:

  airplay   un flusso audio che **arriva davvero qui**. Questo si puo' far
            uscire dagli altoparlanti.
  spotify   l'API web dice *che cosa* sta suonando, su un dispositivo che non
            e' questo. Non c'e' nessun audio da dirottare: la musica esce da
            dove la si e' messa, e il DMD la sta solo raccontando.
  external  metadati di un'automazione, stesso discorso.

Quindi l'interruttore riguarda AirPlay e basta. Per fare del DMD anche un
altoparlante Spotify Connect servirebbe `librespot`, che e' un altro
programma, un'altra installazione e un'altra storia.

`hw:` per la musica, `plughw:` per i nostri suoni
-------------------------------------------------
Sembra un'incoerenza e non lo e'. `plughw` mette un convertitore davanti alla
scheda, ed e' quello che vogliamo per gli avvisi: un mp3 qualunque, a
qualunque frequenza, deve uscire. shairport-sync invece la frequenza la
gestisce da se' e vuole vedere la scheda com'e' — con `plughw` gli si nasconde
cio' che la scheda sa fare davvero, e la sincronizzazione ne risente.

Per questo prima di scrivere la configurazione si **prova** `hw:` per davvero,
con l'unico formato che AirPlay usa: 44100 Hz, stereo, 16 bit. Se la scheda
non lo regge lo si scopre adesso, con un messaggio, invece che stasera con la
musica che non parte e nessuna spiegazione.

Chi tiene la scheda
-------------------
Una scheda ALSA in `hw:` sta in mano a un programma alla volta. Mentre suona
la musica, shairport-sync tiene la scheda e i nostri avvisi non potrebbero
partire — e non ci provano nemmeno: `dmdd` lo dice a `suoni`, che sta zitto
finche' il brano finisce. Le notifiche sui pannello si vedono lo stesso, non
si sentono. E' la scelta giusta: un campanello sopra la musica non lo vuole
nessuno, e la musica ha la precedenza perche' e' quello che si sta
ascoltando.
"""

import os
import re
import shutil
import subprocess
import time

import suoni

CONF = "/etc/shairport-sync.conf"
UNITA = "shairport-sync"

# Il dispositivo scritto da setup_nowplaying.sh: la scheda fittizia del
# kernel. E' anche il valore a cui si torna spegnendo l'interruttore.
FINTO = "hw:CARD=Dummy"

# Il formato di AirPlay, che e' anche quello con cui si prova la scheda.
FREQUENZA = 44100
CANALI = 2


def _leggi():
    try:
        with open(CONF) as handle:
            return handle.read()
    except OSError:
        return ""


def _blocco(testo, nome):
    """Dove comincia e dove finisce il blocco `nome = { ... }`. O None.

    Si contano le graffe invece di fidarsi di un'espressione regolare: i
    blocchi di questo file possono contenerne altri, e `.*?` si fermerebbe
    alla prima chiusa che incontra — cioe' a meta' del blocco sbagliato. Le
    stringhe fra virgolette si saltano, perche' una graffa dentro un nome di
    file non e' una graffa del formato.
    """
    inizio = re.search(r"\b%s\s*=\s*\{" % re.escape(nome), testo)
    if not inizio:
        return None
    profondita = 0
    dentro_stringa = False
    indice = inizio.end() - 1
    while indice < len(testo):
        carattere = testo[indice]
        if dentro_stringa:
            if carattere == "\\":
                indice += 2
                continue
            if carattere == '"':
                dentro_stringa = False
        elif carattere == '"':
            dentro_stringa = True
        elif carattere == "{":
            profondita += 1
        elif carattere == "}":
            profondita -= 1
            if profondita == 0:
                return (inizio.start(), indice + 1)
        indice += 1
    return None


def _campo(blocco, nome):
    """Il valore di `nome = "..."` dentro un blocco, o ""."""
    trovato = re.search(r"\b%s\s*=\s*\"([^\"]*)\"" % re.escape(nome), blocco)
    return trovato.group(1).strip() if trovato else ""


def _scrivi_campo(blocco, nome, valore):
    """Cambia `nome = "valore"` dentro un blocco, o lo aggiunge in cima."""
    riga = '%s = "%s";' % (nome, valore)
    trovato = re.search(r"(\b%s\s*=\s*\")([^\"]*)(\")" % re.escape(nome), blocco)
    if trovato:
        return blocco[:trovato.start(2)] + valore + blocco[trovato.end(2):]
    apertura = blocco.index("{")
    return blocco[:apertura + 1] + "\n    " + riga + blocco[apertura + 1:]


def installato():
    """Vero se c'e' qualcosa da configurare: il programma e la sua conf."""
    return bool(shutil.which("shairport-sync")) and os.path.isfile(CONF)


def uscita_attuale():
    """Il dispositivo scritto adesso in configurazione, o ""."""
    testo = _leggi()
    if not testo:
        return ""
    trovato = re.search(r"alsa\s*=\s*\{.*?output_device\s*=\s*\"([^\"]*)\"",
                        testo, re.DOTALL)
    return trovato.group(1).strip() if trovato else ""


# La risposta di `attiva()`, con la data in cui e' stata letta. Non e' un
# lusso: la chiede `suoni` prima di ogni singolo effetto, e in una partita a
# Breakout sono decine al secondo. Leggere un file di sistema a ogni mattone
# rotto sarebbe traffico sulla scheda SD per una risposta che cambia quando
# qualcuno tocca un interruttore.
_cache = (0.0, False)
VALIDITA = 30.0


def scorda():
    """Da chiamare quando la configurazione cambia sotto i nostri piedi."""
    global _cache
    _cache = (0.0, False)


def attiva(cfg=None):
    """Vero se la musica sta uscendo da una scheda vera.

    Si guarda la configurazione di shairport-sync, non la nostra: e' l'unica
    che conti davvero, e resta giusta anche se qualcuno l'ha cambiata a mano.
    """
    global _cache
    letta, valore = _cache
    adesso = time.monotonic()
    if letta and adesso - letta < VALIDITA:
        return valore
    attuale = uscita_attuale()
    valore = bool(attuale) and "dummy" not in attuale.lower()
    _cache = (adesso, valore)
    return valore


def esclusivo(device):
    """Da `plughw:1,0` a `hw:1,0`: shairport-sync vuole la scheda com'e'."""
    device = (device or "").strip()
    return device[4:] if device.startswith("plug") else device


def prova(device, durata=0.4):
    """Suona un tono sul dispositivo, nel formato di AirPlay. (ok, motivo).

    Non e' una formalita': e' l'unico modo di sapere *prima* se la scheda
    regge 44100 stereo in accesso esclusivo. Ed e' anche udibile, quindi
    conferma pure che il cavo e' nel posto giusto.
    """
    if not device:
        return False, "nessuna scheda audio"
    comando = ["ffmpeg", "-v", "error", "-nostdin",
               "-f", "lavfi",
               "-i", "sine=frequency=880:duration=%.2f" % durata,
               "-ar", str(FREQUENZA), "-ac", str(CANALI),
               "-f", "alsa", device]
    try:
        esito = subprocess.run(comando, capture_output=True, timeout=15)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    if esito.returncode == 0:
        return True, ""
    testo = (esito.stderr or b"").decode("utf-8", "replace")
    return False, suoni.motivo(testo, esito.returncode)


def _scrivi(testo):
    copia = "%s.%s.bak" % (CONF, time.strftime("%Y%m%d-%H%M%S"))
    try:
        shutil.copy2(CONF, copia)
    except OSError:
        copia = ""
    with open(CONF, "w") as handle:
        handle.write(testo)
    return copia


def _sostituisci(testo, device):
    """Cambia il solo `output_device`, lasciando intatto tutto il resto.

    Il resto conta: nel blocco `mqtt` di questo file c'e' la password del
    broker. Riscrivere la configurazione da zero — che sarebbe piu' comodo —
    vorrebbe dire o perderla o maneggiarla, e non serve ne' l'una ne'
    l'altra cosa per cambiare un altoparlante.
    """
    riga = 'output_device = "%s";' % device
    trovato = re.search(r"(alsa\s*=\s*\{.*?output_device\s*=\s*\")([^\"]*)(\")",
                        testo, re.DOTALL)
    if trovato:
        return (testo[:trovato.start(2)] + device + testo[trovato.end(2):])
    trovato = re.search(r"alsa\s*=\s*\{", testo)
    if trovato:
        return testo[:trovato.end()] + "\n    " + riga + testo[trovato.end():]
    coda = "\n\n// Aggiunto dal DMD Controller.\nalsa = {\n    %s\n};\n" % riga
    return testo.rstrip() + coda


def _riavvia():
    try:
        esito = subprocess.run(["systemctl", "restart", UNITA],
                               capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    if esito.returncode == 0:
        return True, ""
    testo = (esito.stderr or b"").decode("utf-8", "replace").strip()
    return False, " ".join(testo.split())[:200] or "systemctl ha risposto %d" % esito.returncode


def imposta(device, acceso):
    """Accende o spegne l'uscita musicale. (ok, motivo).

    Con `acceso` falso si torna alla scheda fittizia: Now Playing continua a
    mostrare i brani come ha sempre fatto, semplicemente non li suona.
    """
    if not installato():
        return False, "shairport-sync non e' installato"
    if acceso:
        device = esclusivo(device)
        if not device:
            return False, "nessuna scheda audio"
        ok, motivo = prova(device)
        if not ok:
            # Non si tocca niente: meglio un interruttore che non scatta di
            # una cassa AirPlay che non suona piu' e nessuno sa perche'.
            return False, motivo
    else:
        device = FINTO
    testo = _leggi()
    if not testo:
        return False, "configurazione di shairport-sync illeggibile"
    try:
        _scrivi(_sostituisci(testo, device))
    except OSError as exc:
        return False, str(exc)
    scorda()
    return _riavvia()


# ------------------------------------------------------- la pipe dei metadati

# Il percorso predefinito di shairport-sync. Si ripete qui invece di importare
# `metadati` perche' questo modulo non deve dipendere da quello: si occupa di
# un file di configurazione, non di leggere niente.
PIPE = "/tmp/shairport-sync-metadata"


def metadati_stato():
    """Come sta la pipe nella configurazione: (accesa, percorso)."""
    testo = _leggi()
    if not testo:
        return (False, "")
    dove = _blocco(testo, "metadata")
    if dove is None:
        return (False, "")
    blocco = testo[dove[0]:dove[1]]
    acceso = _campo(blocco, "enabled").lower() in ("yes", "true", "1")
    return (acceso, _campo(blocco, "pipe_name") or PIPE)


def metadati_attivi(percorso=None):
    """Vero se shairport-sync sta gia' scrivendo nella pipe che leggiamo noi.

    Il percorso conta quanto l'interruttore: una pipe accesa che scrive
    altrove vale esattamente come spenta, e senza confrontarlo si
    dichiarerebbe tutto a posto mentre il pannello resta vuoto. E' lo stesso
    errore del broker, con un nome diverso.
    """
    acceso, dove = metadati_stato()
    if not acceso:
        return False
    return dove == (percorso or PIPE)


def abilita_metadati(percorso=None):
    """Chiede a shairport-sync di scrivere i metadati nella pipe. (ok, motivo).

    Tocca **solo** il blocco `metadata`, come `imposta` tocca solo
    `output_device`: nel blocco `mqtt` di questo file c'e' la password del
    broker, e riscrivere la configurazione da zero vorrebbe dire o perderla o
    maneggiarla. Non serve ne' l'una ne' l'altra cosa per accendere una pipe.
    """
    percorso = percorso or PIPE
    if not installato():
        return False, "shairport-sync non e' installato"
    testo = _leggi()
    if not testo:
        return False, "configurazione di shairport-sync illeggibile"

    dove = _blocco(testo, "metadata")
    if dove is None:
        coda = ("\n\n// Aggiunto dal DMD Controller: i metadati del brano "
                "arrivano\n// da qui invece che dal broker. Vedi metadati.py.\n"
                "metadata = {\n"
                '    enabled = "yes";\n'
                # La copertina no, per adesso: e' il pezzo piu' pesante che
                # passi da questa pipe e il pannello non la usa ancora da
                # questa strada. Accenderla vorrebbe dire far attraversare
                # centinaia di kilobyte per brano a una FIFO, per buttarli.
                '    include_cover_art = "no";\n'
                '    pipe_name = "%s";\n'
                "};\n" % percorso)
        nuovo = testo.rstrip() + coda
    else:
        blocco = testo[dove[0]:dove[1]]
        blocco = _scrivi_campo(blocco, "enabled", "yes")
        blocco = _scrivi_campo(blocco, "pipe_name", percorso)
        nuovo = testo[:dove[0]] + blocco + testo[dove[1]:]

    try:
        _scrivi(nuovo)
    except OSError as exc:
        return False, str(exc)

    # La FIFO la crea shairport-sync all'avvio, ma crearla adesso toglie di
    # mezzo la finestra in cui la pagina direbbe "la pipe non c'e'" mentre in
    # realta' e' tutto a posto e manca solo un istante.
    try:
        if not os.path.exists(percorso):
            os.mkfifo(percorso, 0o666)
            os.chmod(percorso, 0o666)
    except OSError:
        pass

    return _riavvia()


def riconcilia(device):
    """Riallinea l'uscita di shairport-sync alla scheda scelta. (fatto, motivo).

    L'interruttore dell'uscita musicale **fotografa** la scheda nell'istante
    in cui lo si preme, e fin qui era tutto: cambiando poi scheda in
    Impostazioni, shairport-sync restava su quella vecchia e nessuno lo
    diceva. La musica finiva in un'uscita che non suona, e sul pannello non
    compariva nessun errore — la stessa malattia dell'indirizzo del broker,
    con un altro nome.

    Comanda Impostazioni, sempre. Qui non si decide niente: si va a vedere se
    i due sono d'accordo e, se non lo sono, si riporta shairport-sync su
    quello che ha scelto l'utente.

    Non fa niente a uscita musicale spenta: li' la scheda giusta e' quella
    fittizia, ed e' gia' quella che c'e' scritta.
    """
    if not installato() or not attiva():
        return False, ""
    voluto = esclusivo(device)
    if not voluto:
        return False, "nessuna scheda audio"
    if uscita_attuale() == voluto:
        return False, ""
    return imposta(device, True)


def stato(cfg=None):
    """Quel che serve alla pagina Now Playing."""
    acceso, dove = metadati_stato()
    return {"installato": installato(), "attiva": attiva(),
            "uscita": uscita_attuale(), "finto": FINTO,
            "metadati": acceso, "pipe": dove}
