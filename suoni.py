# -*- coding: utf-8 -*-
"""Il suono del DMD: avvisi dei servizi, effetti dei giochi, audio di Doom.

Perche' serve una scheda USB, e perche' non e' un ripiego
--------------------------------------------------------
L'audio interno del Raspberry **non si puo' usare** con questo pannello, e
non e' una questione di qualita': la libreria della matrice si prende il
blocco PWM del chip, e l'audio analogico interno usa lo stesso. Sono
alternativi per costruzione — infatti l'installazione spegne `snd_bcm2835`,
e senza spegnerlo la libreria si rifiuta di partire.

Una scheda USB e' un dispositivo del tutto diverso: parla con `snd_usb_audio`
e non tocca il PWM. Quindi non e' un compromesso, e' **l'unico** modo di
avere suono su questa macchina.

Chi suona
---------
`ffmpeg`, che c'e' gia' — ha il muxer `alsa` fra le uscite, quindi

    ffmpeg -i suono.mp3 -filter:a volume=0.6 -f alsa plughw:1,0

riproduce wav e mp3 su una scheda scelta, con il volume, senza installare
niente. `aplay` non legge gli mp3 e non regola il volume; `ffplay` tira
dentro SDL. Il ferro del mestiere ce l'avevamo gia' in casa.

**`plughw` e non `hw`**: il primo converte frequenza e formato al volo. Un
wav a 44100 stereo su una chiavetta che vuole 48000 mono con `hw` non parte e
basta, e il motivo non lo si scopre in fretta.

Un suono alla volta
-------------------
Un avviso e' corto e non deve accavallarsi: se ne parte uno mentre un altro
sta suonando, il nuovo si **scarta**. Non si mette in coda — un avviso in
ritardo di tre secondi si riferisce a qualcosa che non e' piu' sullo schermo
— e non interrompe quello in corso, che sarebbe un singhiozzo.

Il carico
---------
Riprodurre suono e' CPU e traffico USB, cioe' la stessa moneta con cui si
pagano le righe chiare sul pannello. Un avviso di mezzo secondo non si
misura nemmeno; l'audio continuo di Doom si', ed e' il motivo per cui e'
una voce a parte che si puo' spegnere.
"""

import os
import re
import subprocess
import threading
import time

# I servizi che possono avere un suono. Fuori restano Media Player e Rolling
# Banner, che non annunciano niente: compaiono a intervalli casuali per
# decorazione, e un suono a ogni foto sarebbe un metronomo. I rifiuti non
# compaiono qui perche' non sono un servizio: li disegna l'orologio, dentro
# la sua colonna.
SERVIZI_CON_SUONO = ("zedmd", "nowplaying", "birthdays", "air_radar",
                     "clock", "scadenze", "calendario", "webcam")

# Estensioni accettate per gli avvisi. Le legge ffmpeg, quindi l'elenco e'
# corto per scelta: piu' formati vorrebbero dire piu' modi di scoprire, a
# suono mancato, che quel file non andava bene.
ESTENSIONI = (".wav", ".mp3")

# Gli effetti dei giochi stanno accanto al programma, non nella libreria
# media: sono parte del gioco come lo sono i suoi colori, e mescolarli ai
# contenuti dell'utente vorrebbe dire che cancellandone uno per sbaglio il
# gioco diventa muto.
CARTELLA_EFFETTI = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "suoni")

# Quanto al massimo puo' durare un avviso. Oltre, si tronca: un file lungo
# scelto per sbaglio terrebbe muto tutto il resto per minuti.
DURATA_MASSIMA = 15


# La risposta di `disponibile()`, chiesta una volta sola. Non e' pigrizia:
# la domanda si risolve lanciando ffmpeg, e la pagina Impostazioni la
# farebbe a ogni caricamento — un processo in piu' ogni volta che si guarda
# una pagina, per una risposta che cambia solo reinstallando ffmpeg.
_alsa = None


# Chi sa dire se in questo momento la musica sta uscendo dalla nostra scheda.
# Lo imposta `dmdd` all'avvio: questo modulo non conosce Now Playing e non
# deve conoscerlo — sa solo che ogni tanto la scheda e' di qualcun altro.
musica_in_corso = lambda: False


def disponibile():
    """Vero se ffmpeg sa scrivere su ALSA su questa macchina.

    Qualunque cosa vada storta vale "no": questa funzione la chiamano le
    pagine per decidere cosa mostrare, e un'eccezione qui vorrebbe dire una
    pagina che non si apre — per una domanda a cui si puo' benissimo
    rispondere "non lo so, quindi no".
    """
    global _alsa
    if _alsa is not None:
        return _alsa
    _alsa = False
    try:
        esito = subprocess.run(["ffmpeg", "-hide_banner", "-devices"],
                               capture_output=True, text=True, timeout=10)
        for riga in (esito.stdout or "").splitlines():
            pezzi = riga.split()
            if len(pezzi) >= 2 and pezzi[1] == "alsa" and "E" in pezzi[0]:
                _alsa = True
                break
    except Exception:
        _alsa = False
    return _alsa


def _finta(nome, breve):
    """Vero se questa "scheda" e' la scheda fittizia del kernel.

    `setup_nowplaying.sh` carica `snd_dummy` apposta: shairport-sync deve
    scrivere l'audio da qualche parte anche quando il DMD mostra solo i
    metadati, e serviva un dispositivo con un orologio vero. Non e' un
    altoparlante: quello che ci finisce dentro non lo sente nessuno.
    """
    return "dummy" in ("%s %s" % (nome, breve)).lower()


def dispositivi():
    """Le schede audio viste dal kernel: [{"alsa", "nome", "indice", "finta"}].

    Si legge `/proc/asound/cards` invece di chiamare `aplay`: e' un file, c'e'
    sempre, e non dipende da `alsa-utils` che potrebbe non essere installato.
    """
    fuori = []
    try:
        with open("/proc/asound/cards") as handle:
            testo = handle.read()
    except OSError:
        return fuori
    # Righe tipo: " 1 [Device         ]: USB-Audio - USB Audio Device"
    for riga in testo.splitlines():
        trovato = re.match(r"\s*(\d+)\s*\[([^\]]+)\]:\s*(.*)", riga)
        if not trovato:
            continue
        indice = int(trovato.group(1))
        breve = trovato.group(2).strip()
        lungo = trovato.group(3).strip()
        fuori.append({"indice": indice,
                      "alsa": "plughw:%d,0" % indice,
                      "nome": lungo or breve,
                      "finta": _finta(lungo, breve)})
    return fuori


def _conf(cfg):
    return (cfg or {}).get("audio") or {}


def acceso(cfg):
    return bool(_conf(cfg).get("enabled"))


def uscita(cfg):
    """Il dispositivo su cui suonare, o "" se non ce n'e' uno utilizzabile.

    Una scheda scelta e poi staccata non fa ripiegare in silenzio su
    un'altra: suonare dall'altoparlante sbagliato senza dirlo e' peggio che
    non suonare, perche' non si capisce cosa sta succedendo.

    La scelta automatica salta la scheda fittizia. Su una macchina con Now
    Playing installato ce n'e' sempre una, e il kernel puo' darle un indice
    piu' alto della chiavetta USB: "l'ultima collegata" ci finirebbe sopra, e
    il risultato sarebbe silenzio perfetto senza un solo errore da leggere.
    Chi la sceglie a mano viene comunque accontentato: e' un modo legittimo
    di zittire il DMD lasciando acceso tutto il resto.
    """
    voluto = str(_conf(cfg).get("device") or "").strip()
    schede = dispositivi()
    presenti = [d["alsa"] for d in schede]
    if voluto:
        return voluto if voluto in presenti else ""
    vere = [d["alsa"] for d in schede if not d["finta"]]
    return vere[-1] if vere else ""


def volume(cfg):
    try:
        return max(0.0, min(1.0, float(_conf(cfg).get("volume", 0.7))))
    except (TypeError, ValueError):
        return 0.7


# ---------------------------------------------------------------- catalogo

def file_disponibili(cfg):
    """I suoni caricabili: wav e mp3 nella libreria media, per nome.

    Si guarda anche nelle sottocartelle: chi carica venti suoni li mette in
    una cartella sua, e obbligarlo a tenerli sparsi nella radice sarebbe una
    regola inventata.
    """
    base = ((cfg or {}).get("mediaplayer") or {}).get("media_dir") or ""
    if not base or not os.path.isdir(base):
        return []
    fuori = []
    for radice, _dirs, files in os.walk(base):
        for nome in files:
            if nome.lower().endswith(ESTENSIONI):
                intero = os.path.join(radice, nome)
                fuori.append({"nome": os.path.relpath(intero, base),
                              "percorso": intero})
        if len(fuori) > 400:
            break
    fuori.sort(key=lambda v: v["nome"].lower())
    return fuori


def percorso_servizio(cfg, chiave):
    """Il file assegnato a un servizio, se esiste ancora."""
    scelto = ((_conf(cfg).get("servizi") or {}).get(chiave) or "").strip()
    if not scelto:
        return ""
    base = ((cfg or {}).get("mediaplayer") or {}).get("media_dir") or ""
    intero = os.path.normpath(os.path.join(base, scelto))
    # Il nome arriva dalla configurazione, che si puo' anche importare da un
    # file: non deve poter uscire dalla libreria media.
    if not intero.startswith(os.path.normpath(base) + os.sep):
        return ""
    return intero if os.path.isfile(intero) else ""


def effetto(nome):
    """Il percorso di un effetto dei giochi, o "" se non c'e'."""
    intero = os.path.join(CARTELLA_EFFETTI, "%s.wav" % nome)
    return intero if os.path.isfile(intero) else ""


# ------------------------------------------------------------ riproduzione

_lucchetto = threading.Lock()
_processo = None
_ultimo_errore = ""


def motivo(testo, codice=0):
    """La riga di ffmpeg che spiega, ridotta a una frase leggibile.

    Si prende la **prima**, non l'ultima. Con `-v error` ffmpeg stampa prima
    la causa e poi la conseguenza:

        [alsa @ 0x...] cannot set sample rate (Invalid argument)
        Error opening output device: Input/output error.

    La seconda riga e' quella che si legge per ultima ed e' quella che non
    dice niente. Chi guarda la pagina deve trovarci "cannot set sample rate",
    non "qualcosa e' andato storto".
    """
    pulito = (testo or "").strip()
    if not pulito:
        return "ffmpeg ha risposto %d" % codice
    return " ".join(pulito.splitlines()[0].split())[:200]


def _musica():
    """Come `musica_in_corso`, ma senza poter far cadere una riproduzione.

    Il gancio lo scrive un altro modulo: se un giorno solleva un'eccezione,
    il prezzo dev'essere un avviso di troppo, non un servizio fermo.
    """
    try:
        return bool(musica_in_corso())
    except Exception:
        return False


def in_corso():
    with _lucchetto:
        return _processo is not None and _processo.poll() is None


def ultimo_errore():
    with _lucchetto:
        return _ultimo_errore


def riproduci(cfg, percorso, forza=False):
    """Suona un file. Restituisce (partito, motivo).

    `forza` salta il controllo dell'interruttore generale: lo usa il pulsante
    di prova nella pagina, che serve proprio a capire se l'audio funziona
    prima di accenderlo.
    """
    global _processo, _ultimo_errore
    if not percorso or not os.path.isfile(percorso):
        return False, "file non trovato"
    if not forza and not acceso(cfg):
        return False, "audio spento"
    if not forza and _musica():
        # La scheda e' di shairport-sync finche' dura il brano, e comunque un
        # campanello sopra la musica non lo vuole nessuno. La notifica sul
        # pannello si vede lo stesso: qui si perde solo il suono.
        return False, "musica in corso"
    device = uscita(cfg)
    if not device:
        return False, "nessuna scheda audio"
    with _lucchetto:
        if _processo is not None and _processo.poll() is None:
            # Un avviso in ritardo si riferisce a qualcosa che non e' piu'
            # sullo schermo: meglio perderlo che sentirlo fuori tempo.
            return False, "un suono e' gia' in corso"
        comando = ["ffmpeg", "-v", "error", "-nostdin",
                   "-t", str(DURATA_MASSIMA), "-i", percorso,
                   "-filter:a", "volume=%.2f" % volume(cfg),
                   "-f", "alsa", device]
        try:
            _processo = subprocess.Popen(comando, stdin=subprocess.DEVNULL,
                                         stdout=subprocess.DEVNULL,
                                         stderr=subprocess.PIPE)
            _ultimo_errore = ""
        except (OSError, subprocess.SubprocessError) as exc:
            _processo = None
            _ultimo_errore = str(exc)
            return False, str(exc)
    threading.Thread(target=_raccogli, args=(_processo,), daemon=True).start()
    return True, ""


def _raccogli(processo):
    """Aspetta la fine e tiene il motivo, se e' andata male.

    Senza qualcuno che lo aspetti il processo resterebbe zombie, e soprattutto
    un errore — scheda staccata, formato illeggibile — sparirebbe nel nulla,
    lasciando solo un silenzio inspiegabile.
    """
    global _ultimo_errore
    try:
        _fuori, errore = processo.communicate(timeout=DURATA_MASSIMA + 10)
    except Exception:
        try:
            processo.kill()
        except Exception:
            pass
        return
    if processo.returncode:
        testo = (errore or b"").decode("utf-8", "replace")
        riga = motivo(testo, processo.returncode)
        # La coda del caso precedente: fra il controllo e l'apertura della
        # scheda puo' essere cominciato un brano, e allora la scheda e' di
        # shairport-sync. Non e' un guasto, e' il turno di qualcun altro.
        if "busy" in testo.lower() and _musica():
            return
        with _lucchetto:
            _ultimo_errore = riga
        print("[suoni] %s" % _ultimo_errore)


def suona_servizio(cfg, chiave):
    """L'avviso di un servizio, se ne ha uno assegnato."""
    if chiave not in SERVIZI_CON_SUONO:
        return False
    percorso = percorso_servizio(cfg, chiave)
    if not percorso:
        return False
    partito, _motivo = riproduci(cfg, percorso)
    return partito


def suona_effetto(cfg, nome):
    """Un effetto dei giochi. Silenzioso se gli effetti sono spenti."""
    if not _conf(cfg).get("giochi", True):
        return False
    percorso = effetto(nome)
    if not percorso:
        return False
    partito, _motivo = riproduci(cfg, percorso)
    return partito


def ambiente_doom(cfg):
    """Le variabili che mandano l'audio di Doom sulla scheda giusta.

    SDL sceglie la scheda da `AUDIODEV`, e senza `SDL_AUDIODRIVER=alsa`
    potrebbe provare prima pulseaudio — che su un'immagine senza sessione
    grafica non c'e', e allora Doom parte muto senza spiegazioni.

    Se in questo momento sta suonando la musica, Doom parte muto **apposta**:
    la scheda e' occupata, e SDL che non riesce ad aprirla se la caverebbe
    peggio — con qualche secondo di errori all'avvio della partita. Meglio
    `-nosound`, deciso da noi.
    """
    if not acceso(cfg) or not _conf(cfg).get("doom", True):
        return {}
    if _musica():
        return {}
    device = uscita(cfg)
    if not device:
        return {}
    return {"SDL_AUDIODRIVER": "alsa", "AUDIODEV": device}


def doom_con_suono(cfg):
    return bool(ambiente_doom(cfg))


def uscita_giochi(cfg):
    """La scheda su cui puo' suonare un gioco che si porta il suo audio.

    Oggi e' il Game Boy, che ha un chip sonoro emulato: i suoi suoni non sono
    nostri e non stanno in `suoni/`, sono la musica scritta per quel chip.
    Vale la stessa levetta degli altri effetti dei giochi — chi li spegne
    vuole silenzio, non silenzio tranne uno.

    Restituisce "" quando non si deve suonare, ed e' quello che si passa a un
    processo esterno: un argomento vuoto e' piu' facile da controllare di un
    argomento assente.
    """
    if not acceso(cfg) or not _conf(cfg).get("giochi", True):
        return ""
    if _musica():
        # La scheda e' di shairport-sync: il Game Boy partirebbe muto e con
        # un errore per traverso. Meglio muto e basta.
        return ""
    return uscita(cfg)


def stato(cfg):
    """Quel che serve alle pagine."""
    return {"disponibile": disponibile(), "acceso": acceso(cfg),
            "dispositivi": dispositivi(), "uscita": uscita(cfg),
            "volume": volume(cfg), "errore": ultimo_errore(),
            "effetti": os.path.isdir(CARTELLA_EFFETTI)}
