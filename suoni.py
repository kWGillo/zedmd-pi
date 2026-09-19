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

import collections
import os
import random
import re
import shutil
import struct
import subprocess
import threading
import time
import wave

# I servizi che possono avere un suono. Fuori restano Media Player e Rolling
# Banner, che non annunciano niente: compaiono a intervalli casuali per
# decorazione, e un suono a ogni foto sarebbe un metronomo. I rifiuti non
# compaiono qui perche' non sono un servizio: li disegna l'orologio, dentro
# la sua colonna.
SERVIZI_CON_SUONO = ("zedmd", "nowplaying", "birthdays", "air_radar",
                     "clock", "scadenze", "calendario", "webcam",
                     # Le notifiche hanno **tre** suoni, uno per livello, e
                     # non uno solo. Una notifica e' l'unica cosa che per
                     # definizione arriva quando non stai guardando il
                     # pannello: un campanello unico dice «e' successo
                     # qualcosa», tre dicono se vale la pena alzarsi, e lo
                     # dicono dall'altra stanza senza girare la testa.
                     #
                     # Fino alla 9.4 le notifiche erano l'unico servizio che
                     # un suono non poteva averlo: l'impianto c'era tutto,
                     # mancava la voce in questo elenco.
                     "notifiche_info", "notifiche_avviso", "notifiche_allarme",
                     # OnAir suona una volta sola, quando la porta si chiude,
                     # e non a ogni ricomparsa della scritta. Non e' il
                     # campanello di una sorgente che prende il pannello: e'
                     # il campanello di un **cambio di stato**. Per questo non
                     # lo fa partire il gancio generico del runtime ma la
                     # sorgente stessa, nel momento in cui la diretta comincia.
                     "onair")

# Chi il proprio campanello se lo fa partire da solo. Il runtime suona
# l'avviso di una sorgente **quando prende il pannello**, che per quasi tutte
# e' il momento giusto. Per OnAir no: la scritta ricompare ogni due foto per
# tutta la durata della diretta, e un din-don ogni due minuti non annuncia
# piu' niente. Il suo momento e' la chiusura della porta, che il runtime non
# vede, quindi lo chiama la sorgente.
#
# Le notifiche risolvono lo stesso problema in un altro modo, tenendo fuori
# da SERVIZI_CON_SUONO la voce generica e mettendoci i tre livelli. Li'
# serviva: tre suoni diversi non si possono scegliere con una chiave sola.
# Qui il suono e' uno, e inventare un secondo nome per lo stesso servizio
# renderebbe la pagina Suoni piu' difficile da leggere, non piu' facile.
SUONO_PROPRIO = ("onair",)


def chiave_notifica(livello):
    """Il servizio sonoro di un livello di notifica."""
    chiave = "notifiche_%s" % (livello or "").lower()
    return chiave if chiave in SERVIZI_CON_SUONO else ""

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

# E chi sa dire se adesso e' la fascia notturna. Stesso patto: questo modulo
# non sa che cosa sia il night mode, sa solo che ogni tanto deve abbassare la
# voce. Lo imposta `dmdd`, che la fascia la calcola gia' per la luminosita'.
notte_in_corso = lambda: False


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


# Le uscite che il Raspberry ha di suo. Non sono finte — esistono e il kernel
# le elenca — ma su **questa** macchina non possono suonare:
#
#   vc4-hdmi    escono dal cavo HDMI, e qui non c'e' nessun cavo HDMI: il
#               pannello e' collegato al bonnet, non a un monitor.
#   bcm2835     e' l'uscita analogica del jack, e la libreria della matrice si
#               prende lo stesso blocco PWM. L'installazione la disattiva
#               apposta.
#
# Restano elencate perche' una macchina diversa potrebbe usarle davvero, ma
# non devono mai essere la scelta automatica: ci finisce l'audio e non lo
# sente nessuno, senza un errore da leggere.
_INTERNE = ("hdmi", "bcm2835", "headphones")


def _interna(nome, breve):
    testo = ("%s %s" % (nome, breve)).lower()
    return any(marchio in testo for marchio in _INTERNE)


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
                      "finta": _finta(lungo, breve),
                      "interna": _interna(lungo, breve)})
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

    **E salta anche le uscite interne del Raspberry**, e questa riga e' nata
    da una macchina vera. Su un Pi 4 con Now Playing installato il kernel
    elenca:

        0 Dummy    1 USB Audio    2 vc4hdmi0    3 vc4hdmi1

    La regola precedente diceva "l'ultima scheda non fittizia" ed era stata
    scritta quando in quell'elenco c'erano solo Dummy e la chiavetta. Le due
    vc4-hdmi si registrano **dopo** la USB, quindi passavano davanti: il DMD
    proponeva `plughw:3,0` e mandava ogni avviso in un'uscita HDMI a cui non
    e' attaccato niente. Silenzio perfetto, di nuovo, e di nuovo senza un
    errore da leggere.

    Quindi due livelli, non uno: prima le schede vere e proprie, e solo se
    non ce n'e' nessuna le uscite interne. Dentro ogni livello vale ancora
    l'ultima, che con una chiavetta appena infilata e' quasi sempre quella
    giusta.
    """
    voluto = str(_conf(cfg).get("device") or "").strip()
    schede = dispositivi()
    presenti = [d["alsa"] for d in schede]
    if voluto:
        return voluto if voluto in presenti else ""
    vere = [d for d in schede if not d["finta"]]
    esterne = [d["alsa"] for d in vere if not d["interna"]]
    if esterne:
        return esterne[-1]
    interne = [d["alsa"] for d in vere]
    return interne[-1] if interne else ""


def nome_uscita(cfg):
    """Il nome leggibile della scheda scelta, non il suo indirizzo ALSA.

    `plughw:1,0` e' giusto e non dice niente. Le pagine devono poter scrivere
    "USB Audio", che e' la stessa cosa detta a qualcuno.
    """
    scelta = uscita(cfg)
    if not scelta:
        return ""
    for scheda in dispositivi():
        if scheda["alsa"] == scelta:
            return scheda["nome"]
    return scelta


def volume_impostato(cfg):
    """Il volume scritto in configurazione. E' quello che vale lo slider."""
    try:
        return max(0.0, min(1.0, float(_conf(cfg).get("volume", 0.7))))
    except (TypeError, ValueError):
        return 0.7


def volume_notturno(cfg):
    """Il volume durante la modalita' notte. Predefinito 0, cioe' muto."""
    try:
        return max(0.0, min(1.0, float((cfg or {}).get("display", {})
                                       .get("night_volume", 0.0))))
    except (TypeError, ValueError, AttributeError):
        return 0.0


def volume(cfg):
    """Il volume **adesso**, per un avviso che parte dal DMD.

    Di notte comanda `night_volume`, esattamente come per la luminosita'
    comanda `night_brightness`: e' la stessa idea applicata all'altra uscita.
    Con lo zero predefinito il DMD di notte guarda e tace.

    Sleep mode e display spento non compaiono qui, e non e' una dimenticanza:
    li' non suona gia' niente, perche' il ciclo di `dmdd` si ferma prima di
    scegliere una sorgente e il suono nasce proprio da quel momento. Il night
    mode invece lascia il pannello al lavoro, solo piu' fioco — ed e' l'unica
    delle tre fasce in cui alle tre di notte un aereo ti suonava l'avviso a
    volume pieno.
    """
    if _notte():
        return volume_notturno(cfg)
    return volume_impostato(cfg)


def volume_giochi(cfg):
    """Il volume di una partita, che ha una manopola sua.

    Una partita e' una cosa che stai facendo con le mani, adesso: non e' il
    DMD che parla da solo. Zittirla sarebbe come spegnere il pannello a chi
    ci sta giocando davanti — ed e' esattamente l'eccezione che lo sleep mode
    fa gia' per chi tiene il pannello occupato. Per questo la notte non la
    tocca.

    **E per questo non e' piu' `volume`.** Fino alla 9.0 questa funzione
    restituiva il volume generale, e sembrava ovvio: il volume e' il volume.
    Non lo era. Chi tiene un pannello in casa abbassa il volume pensando agli
    avvisi — sul DMD di chi scrive era a 0,05, cioe' 26 dB sotto — e quel
    numero finiva moltiplicato dentro ogni effetto dei giochi. Intanto Doom e
    il Game Boy, che la scheda se la prendono per conto loro e scrivono a
    fondo scala, si sentivano benissimo: erano 26 dB piu' forti dei nostri
    effetti, e nessuno lo aveva mai messo in fila.
    """
    try:
        valore = _conf(cfg).get("volume_giochi")
        if valore is None:
            # Configurazione vecchia, scritta prima che questa voce esistesse:
            # meglio il predefinito nuovo che il volume degli avvisi, che e'
            # proprio il numero da cui ci si sta staccando.
            return 0.9
        return max(0.0, min(1.0, float(valore)))
    except (TypeError, ValueError):
        return 0.9


def sottofondo(cfg):
    """Quanto vale il sottofondo che tiene sveglia la scheda. 0 = spento."""
    try:
        return max(0, min(1000, int(_conf(cfg).get("sottofondo", 32))))
    except (TypeError, ValueError):
        return 32


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


def percorso_media(cfg, scelto):
    """Il percorso di un file della libreria media, se esiste ancora.

    Sta a parte da `percorso_servizio` perche' i servizi non sono piu' gli
    unici a scegliere un file: dalla 7.7 lo fa anche la sveglia, e quella non
    e' un servizio della tabella `audio.servizi`. La regola di sicurezza —
    il nome non puo' uscire dalla libreria — deve valere per tutti e due, e
    una regola di sicurezza scritta in due copie prima o poi diverge.
    """
    scelto = (scelto or "").strip()
    if not scelto:
        return ""
    base = ((cfg or {}).get("mediaplayer") or {}).get("media_dir") or ""
    if not base:
        return ""
    intero = os.path.normpath(os.path.join(base, scelto))
    # Il nome arriva dalla configurazione, che si puo' anche importare da un
    # file: non deve poter uscire dalla libreria media.
    if not intero.startswith(os.path.normpath(base) + os.sep):
        return ""
    return intero if os.path.isfile(intero) else ""


def percorso_servizio(cfg, chiave):
    """Il file assegnato a un servizio, se esiste ancora."""
    return percorso_media(cfg, (_conf(cfg).get("servizi") or {}).get(chiave))


def effetto(nome):
    """Il percorso di un effetto dei giochi, o "" se non c'e'."""
    intero = os.path.join(CARTELLA_EFFETTI, "%s.wav" % nome)
    return intero if os.path.isfile(intero) else ""


# ------------------------------------------------- uscita PCM a bassa latenza

# Quanto audio sta in volo prima di uscire dall'altoparlante. 80 ms non si
# percepiscono in un gioco; il buffer di ffmpeg, che sono 0,68 secondi, si'.
BUFFER_US = 80000
PERIODO_US = 20000


def comando_pcm(device, frequenza, canali,
                buffer_us=BUFFER_US, periodo_us=PERIODO_US):
    """La riga di comando per riversare PCM grezzo su una scheda ALSA.

    Si preferisce `aplay` **per la latenza, non per gusto**. Il muxer `alsa`
    di ffmpeg non espone nessuna opzione: apre un buffer fisso di 32768
    campioni, che a 48 kHz fanno 0,68 secondi di ritardo fra quello che
    succede nel gioco e quello che si sente. Per un avviso non conta niente;
    per il suono di un emulatore e' insopportabile.

    `aplay` invece il buffer lo prende come argomento. Sta in `alsa-utils`,
    che su Raspberry Pi OS c'e' quasi sempre — ed e' lo stesso pacchetto di
    `alsamixer`, che il manuale dell'audio ti fa gia' usare per alzare il
    volume della chiavetta.

    Se non c'e' si ripiega su ffmpeg: meglio in ritardo che muto.
    """
    if shutil.which("aplay"):
        # `-v` e non `-q`, e vale la pena scriverlo perche' era un errore mio.
        # `aplay` stampa `underrun!!!` **solo** in modalita' prolissa: con
        # `-q` il contatore dei buchi non poteva accendersi nemmeno con la
        # scheda che restava a secco ogni tre secondi. Era un contatore cieco
        # spacciato per una prova. In prolisso stampa anche il riepilogo di
        # come ha negoziato il flusso -- formato, frequenza, dimensione del
        # buffer -- che e' esattamente quello che serve per sapere se il
        # cuscino che crediamo di avere ce l'ha davvero concesso la scheda.
        return ["aplay", "-v", "-t", "raw", "-f", "S16_LE",
                "-r", str(int(frequenza)), "-c", str(int(canali)),
                "--buffer-time=%d" % int(buffer_us),
                "--period-time=%d" % int(periodo_us),
                "-D", device, "-"]
    return ["ffmpeg", "-v", "error", "-nostdin",
            "-f", "s16le", "-ar", str(int(frequenza)), "-ac", str(int(canali)),
            "-i", "-", "-f", "alsa", device]


def stringi_tubo(flusso, byte=16384):
    """Rimpicciolisce il tubo verso il riproduttore.

    Un tubo Linux tiene 64 KB per difetto: a 48 kHz stereo sono altri 340 ms
    di ritardo, sopra a quello del riproduttore. Qui non serve accumulare —
    se il riproduttore e' indietro vogliamo bloccarci, non fare magazzino.

    Se il sistema non lascia farlo si tira dritto: e' un miglioramento, non un
    requisito.
    """
    try:
        import fcntl
        fcntl.fcntl(flusso.fileno(), getattr(fcntl, "F_SETPIPE_SZ", 1031), byte)
    except Exception:
        pass


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


def _notte():
    """Come `notte_in_corso`, ma senza poter far cadere una riproduzione."""
    try:
        return bool(notte_in_corso())
    except Exception:
        return False


def in_corso():
    with _lucchetto:
        return _processo is not None and _processo.poll() is None


def ultimo_errore():
    with _lucchetto:
        return _ultimo_errore


def riproduci(cfg, percorso, forza=False, vol=None):
    """Suona un file. Restituisce (partito, motivo).

    `forza` salta il controllo dell'interruttore generale: lo usa il pulsante
    di prova nella pagina, che serve proprio a capire se l'audio funziona
    prima di accenderlo.

    `vol` lo decide chi chiama, e non e' un dettaglio: e' il modo in cui si
    distingue **il DMD che parla da solo** — e che di notte deve tacere — da
    un suono che stai producendo tu, con le mani, in questo momento. Chi non
    lo passa ottiene il primo dei due, che e' il caso normale.
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
    if vol is None:
        vol = volume(cfg)
    if not forza and vol <= 0.0:
        # Aprire ffmpeg per produrre silenzio e' lavoro sprecato su una
        # macchina che ha un pannello da tenere fermo.
        return False, "silenzio notturno" if _notte() else "volume a zero"
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
                   "-filter:a", "volume=%.2f" % vol,
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


# --------------------------------------------------- il mixer degli effetti

# Gli effetti sono tutti a 22050 Hz, mono, 16 bit: li abbiamo fatti noi, e
# averli tutti uguali e' quello che permette di sommarli senza convertire
# niente.
FREQ_EFFETTI = 22050
BLOCCO = 512                 # 23 ms: il ritmo con cui si scrive

# Quante voci si tengono insieme. Il vecchio tetto era 8 e la voce piu'
# vecchia veniva buttata: con effetti da 55 ms vuol dire otto suoni dentro lo
# stesso 55 ms, cioe' 145 al secondo. Non succede mai, quindi quel tetto non
# ha mai protetto niente e poteva solo far sparire un suono. Qui e' alto
# perche' resti un freno di sicurezza e non una regola di funzionamento, e
# ogni voce buttata si conta.
VOCI_MASSIME = 24

# **Il cuscino.** E' la correzione piu' importante di questa versione, quindi
# vale la pena scrivere perche'.
#
# Fra il mixer e l'altoparlante c'e' una coda: quello che abbiamo gia' scritto
# e che la scheda non ha ancora suonato. Quella coda e' l'unica difesa contro
# un nostro ritardo. Se il thread del mixer resta fermo piu' a lungo della
# coda — e su un Pi resta fermo, perche' il GIL e' uno solo e il pannello
# ridisegna 256x64 trenta volte al secondo — la scheda arriva a fondo coda,
# non trova niente da suonare e mette silenzio. In ALSA si chiama underrun, e
# per chi gioca e' esattamente "il suono e' saltato".
#
# La versione precedente teneva un cuscino di 20-50 ms: misurato, non
# supposto. Bastava una pausa di venti millesimi per bucare l'audio, ed e'
# una pausa che sul Pi capita di continuo.
#
# Il prezzo del cuscino e' il ritardo: un mattone si sente CUSCINO
# millisecondi dopo averlo colpito. A 120 ms non si distingue da subito —
# una cassa Bluetooth qualunque ne aggiunge di piu' — mentre un suono che
# manca si sente benissimo. Il baratto e' tutto a favore del cuscino.
CUSCINO = 0.12

# Il buffer della scheda deve poter contenere il cuscino con del margine,
# altrimenti il freno diventa lui.
BUFFER_EFFETTI_US = 250000
PERIODO_EFFETTI_US = 25000

# Quanto tubo fra noi e il riproduttore. Il minimo che Linux concede e' una
# pagina; di piu' sarebbe ritardo che nessuno puo' misurare, perche' `/proc`
# racconta la scheda e non il tubo.
TUBO_EFFETTI = 4096
TUBO_SECONDI = TUBO_EFFETTI / 2.0 / FREQ_EFFETTI

# Il cuscino si regola sull'anello della scheda, ma il cuscino **vero** e'
# anello piu' tubo: quello che sta nel tubo entra nell'anello appena c'e'
# posto, e a passarlo e' `aplay`, che e' un programma in C e non aspetta il
# GIL come noi. Quindi la difesa contro una nostra pausa vale la somma dei
# due, mentre il ritardo che si sente vale anch'esso la somma dei due. Si
# punta l'anello a quello che resta dopo aver contato il tubo.
# **Mai sotto un paio di periodi della scheda.** Qui c'era
# `CUSCINO - TUBO_SECONDI`, che con il tubo al minimo faceva 30 ms, e 30 ms e'
# poco piu' di **un solo periodo** (25 ms sulla chiavetta del DMD). Un
# bersaglio cosi' basso non si raggiunge mai -- `delay` comprende anche i
# fotogrammi gia' consegnati al ferro -- e il regolatore resta in attesa a
# scrivere un blocco ogni mezzo secondo invece di trenta al secondo: la scheda
# va a secco e il gioco ammutolisce. E' successo davvero, si sente nel video
# della 8.5, e l'ho messo io.
#
# Il bersaglio giusto e' il cuscino intero nell'anello. Il tubo resta al minimo
# per non nascondere ritardo, ma non si sottrae: sommandoli il ritardo
# peggiore resta poco sopra i duecento millesimi, che e' il prezzo giusto.
CUSCINO_ANELLO = max(0.08, CUSCINO)

# Quanti blocchi diversi di fruscio si tengono pronti per i momenti in cui non
# c'e' niente da suonare. Vedi `Mixer._prepara_muto`: uno solo, ripetuto
# quarantatre volte al secondo, non sarebbe rumore ma una nota a 43 Hz.
# Trentadue blocchi fanno tre quarti di secondo di rumore che non si ripete,
# e costano trentadue kilobyte.
BLOCCHI_MUTI = 32

# Una voce che ha aspettato piu' di questo mentre il riproduttore era giu'
# non si suona piu': un rumore di racchetta che arriva mezzo secondo dopo il
# colpo non e' un suono recuperato, e' un suono sbagliato.
ETA_MASSIMA = 0.5

# Quanto si aspetta fra un tentativo di riapertura e il successivo, e per
# quanto tempo si insiste prima di arrendersi. Quindici secondi sono la
# durata massima di un avviso di un servizio (DURATA_MASSIMA): se la scheda
# e' occupata da quello, dobbiamo sopravvivergli.
# Quanto si aspetta, alla chiusura di una partita, che gli ultimi suoni
# siano davvero usciti prima di spegnere il riproduttore.
ATTESA_SVUOTO = 1.5

RIAVVIO_ATTESA = 0.4
RIAVVIO_LENTO = 2.0
RIAVVIO_LIMITE = 60.0

# Quante righe di errore del riproduttore si tengono da parte. Prima
# finivano in /dev/null, ed e' il motivo per cui questo problema e' rimasto
# invisibile cosi' a lungo.
RIGHE_TENUTE = 20

# Le righe con cui `aplay -v` racconta come ha negoziato il flusso. Non sono
# errori: vanno tenute a parte, altrimenti la pagina mostrerebbe "buffer_size:
# 5512" come se fosse un guasto.
_SETUP = ("plug pcm", "hardware pcm", "its setup is", "stream", "access",
          "format", "subformat", "channels", "rate", "exact rate",
          "msbits", "buffer_size", "period_size", "period_time",
          "buffer_time", "periods", "tick_time", "appl_ptr", "avail_min",
          "start_threshold", "stop_threshold", "silence", "period_step",
          "sleep_min", "boundary", "rate_num", "rate_den", "info :",
          "playing raw data",
          # Aggiunte dopo aver letto un riepilogo vero dal DMD: queste quattro
          # righe cadevano nel cestino degli errori, e siccome l'ultima riga
          # non riconosciuta diventa `self.errore`, un flusso negoziato
          # perfettamente si presentava sulla pagina come un guasto.
          "slave:", "tstamp_mode", "tstamp_type", "period_event", "hw_ptr")


def _indice_scheda(device):
    """Il numero di scheda ALSA dentro `plughw:1,0`. None se non si capisce."""
    trovato = re.search(r"(?:plug)?hw:(?:CARD=)?(\d+)", str(device or ""))
    return int(trovato.group(1)) if trovato else None


def ritardo_alsa(device, frequenza=None):
    """Quanti secondi di audio la scheda ha ancora da suonare. None se non si sa.

    E' l'orologio giusto, e la 8.4 ha dimostrato sul campo perche' il nostro
    non lo e'. Il mixer si dava il ritmo con `time.monotonic()`: scrivo un
    blocco ogni 23 ms, quindi dopo un minuto avro' scritto un minuto di audio.
    Sembra ovvio e non lo e', perche' **la scheda non va al nostro ritmo**.
    Gli effetti sono a 22050 Hz mono e la chiavetta suona a 48000 stereo: in
    mezzo c'e' una conversione, e la conversione piu' il quarzo della scheda
    fanno un errore piccolo e sempre nello stesso verso. Un errore piccolo che
    si accumula riempie qualunque coda: misurato sul DMD, l'anello della
    scheda stava **pieno al 99%** -- 250 ms su 250 -- piu' quello che c'era
    nel tubo.

    ALSA il conto giusto ce l'ha e lo pubblica: `delay` in `/proc` dice quanti
    fotogrammi deve ancora suonare. Regolandosi su quello, il ritardo resta
    dove lo si mette, qualunque cosa facciano i due orologi.
    """
    indice = _indice_scheda(device)
    if indice is None:
        return None
    if not frequenza:
        frequenza = frequenza_alsa(device)
        if not frequenza:
            return None
    try:
        with open("/proc/asound/card%d/pcm0p/sub0/status" % indice) as handle:
            stato = handle.read()
    except OSError:
        return None
    if "RUNNING" not in stato:
        # Fermo o in avvio: non c'e' un ritardo da leggere, e zero sarebbe una
        # bugia che farebbe scrivere a raffica.
        return None
    quanti = re.search(r"delay\s*:\s*(-?\d+)", stato)
    if not quanti:
        return None
    return max(0.0, int(quanti.group(1)) / float(frequenza))


def frequenza_alsa(device):
    """A che frequenza sta suonando la scheda. Si legge una volta per flusso.

    Sta a parte da `ritardo_alsa` perche' il ritardo si guarda a ogni blocco,
    trenta volte al secondo, e la frequenza non cambia mai dentro un flusso:
    rileggerla ogni volta vorrebbe dire raddoppiare i file aperti per niente.
    """
    indice = _indice_scheda(device)
    if indice is None:
        return None
    try:
        with open("/proc/asound/card%d/pcm0p/sub0/hw_params" % indice) as handle:
            parametri = handle.read()
    except OSError:
        return None
    trovato = re.search(r"^rate:\s*(\d+)", parametri, re.M)
    if not trovato:
        return None
    valore = int(trovato.group(1))
    return valore if valore > 0 else None


class Mixer:
    """Un riproduttore solo, aperto per tutta la partita, e i suoni sommati.

    Il perche' e' aritmetico. Un effetto lanciato come processo a se' costa
    fra i 150 e i 300 ms di avvio su un Pi, e una scheda ALSA sta in mano a
    un programma alla volta: due effetti ravvicinati non possono suonare
    insieme, e il secondo va buttato. Qui il processo e' uno e resta aperto:
    gli effetti diventano campioni sommati in memoria, quindi si
    **sovrappongono** invece di annullarsi.

    Le tre cose che prima potevano far sparire un suono, e che qui non
    possono piu'
    ------------------------------------------------------------------
    1. **Il riproduttore poteva morire e nessuno se ne accorgeva.** `Popen`
       riesce sempre: `aplay` parte, poi scopre che la scheda e' occupata —
       da un avviso di un servizio, dalla musica — ed esce. `avvia()`
       rispondeva "tutto bene", il suo errore andava in `/dev/null`, e da
       quel momento ogni effetto della partita ripiegava sulla strada del
       processo per volta, che scarta tutto quello che si sovrappone.
       Breakout, che i suoni li fa a grappoli, ne perdeva a manciate;
       Invaders, che li fa spaziati, quasi no. E' esattamente la differenza
       che si sentiva. Adesso la morte del riproduttore si vede, si conta e
       si **ripara**: si riapre finche' la scheda non torna libera.
    2. **Il cuscino era di venti millisecondi.** Vedi `CUSCINO`.
    3. **Il tetto di otto voci buttava la piu' vecchia.** Vedi
       `VOCI_MASSIME`.

    Tutto quello che passa di qui si conta: chiesti, resi davvero, buttati,
    scaduti, riaperture, righe di errore del riproduttore. La pagina Giochi
    li mostra, cosi' la prossima volta la domanda "ne salta troppi" ha una
    risposta invece di un'ipotesi.

    Vive solo mentre c'e' una partita aperta. A pannello fermo non consuma
    niente e non tiene occupata la scheda.
    """

    def __init__(self):
        self._lucchetto = threading.Lock()
        self._processo = None
        self._voci = []          # [[campioni, posizione, nato, nome], ...]
        self._stop = threading.Event()
        self._thread = None
        self._campioni = {}      # nome -> lista di interi, letta una volta
        self._pacchi = {}        # nome -> byte gia' pronti, al volume giusto
        self._device = ""
        self._volume = 1.0
        self._voluto = False     # c'e' una partita che vuole il mixer
        self._arreso = False     # la scheda non torna: si e' smesso di provare
        self._silenzio = b"\x00\x00" * BLOCCO
        self._sottofondo = 0     # ampiezza del fruscio che tiene sveglia
        self._muti = [self._silenzio]
        self._muto = 0
        self._righe = collections.deque(maxlen=RIGHE_TENUTE)
        # Quaranta righe erano poche, e si e' visto solo leggendo un riepilogo
        # vero: con `plughw` aplay stampa un blocco per ogni anello della
        # catena -- il nostro a 22050, la conversione, la scheda -- e sessanta
        # righe in tutto. Tenendone quaranta si perdeva **il primo**, cioe'
        # l'unico che parla del flusso che scriviamo noi.
        self._setup = collections.deque(maxlen=160)
        self._registro = None
        self._freq_scheda = None
        self.errore = ""
        self._conti = {"chiesti": 0, "resi": 0, "scartati": 0, "scaduti": 0,
                       "mancanti": 0, "morti": 0, "riavvii": 0, "vuoti": 0}

    # ---------------------------------------------------------- campioni

    def _carica(self, nome):
        """I campioni di un effetto, letti dal wav una volta sola.

        Insieme ai campioni si prepara il **pacco**: gli stessi campioni gia'
        moltiplicati per il volume e gia' impacchettati in byte. Serve alla
        via veloce del mixaggio — quando c'e' una voce sola, che e' il caso
        normale, il blocco da scrivere e' una fetta di questo pacco e non
        costa niente. Prima ogni blocco passava per due cicli Python da 512
        giri anche per un suono solo, ed e' tempo tolto al cuscino.
        """
        if nome in self._campioni:
            return self._campioni[nome]
        dati = None
        percorso = effetto(nome)
        if percorso:
            try:
                with wave.open(percorso) as w:
                    if (w.getnchannels() == 1 and w.getsampwidth() == 2
                            and w.getframerate() == FREQ_EFFETTI):
                        grezzi = w.readframes(w.getnframes())
                        dati = list(struct.unpack("<%dh" % (len(grezzi) // 2),
                                                  grezzi))
            except Exception:
                dati = None
        self._campioni[nome] = dati
        if dati:
            self._impacchetta(nome, dati)
        return dati

    def _impacchetta(self, nome, dati):
        guadagno = self._volume
        if guadagno >= 0.999:
            scalati = dati
        else:
            scalati = [int(v * guadagno) for v in dati]
        try:
            self._pacchi[nome] = struct.pack("<%dh" % len(scalati), *scalati)
        except Exception:
            self._pacchi.pop(nome, None)

    # ------------------------------------------------------------ vita

    def _leggi_errori(self, processo):
        """Tiene da parte quello che il riproduttore scrive su stderr.

        Una riga sola conta piu' di tutte le altre: `underrun!!!`. Vuol dire
        che la scheda e' arrivata a fondo coda e ha messo silenzio, cioe' che
        un pezzo di suono non e' uscito. Finche' finiva in `/dev/null` era
        una cosa che si poteva solo sospettare.
        """
        try:
            for riga in processo.stderr:
                testo = riga.decode("utf8", "replace").rstrip()
                if not testo:
                    continue
                basso = testo.lower()
                if "underrun" in basso or "xrun" in basso:
                    # Un buco vero: la scheda e' arrivata a fondo coda e ha
                    # messo silenzio. E' il suono che sparisce.
                    self._conti["vuoti"] += 1
                    self._righe.append(testo)
                elif any(marca in basso for marca in _SETUP):
                    # Il riepilogo di come e' stato negoziato il flusso. Non
                    # e' un errore e non deve finire nella riga rossa della
                    # pagina: si tiene da parte, perche' dice se il buffer
                    # chiesto e' stato concesso.
                    self._setup.append(testo)
                else:
                    self.errore = testo
                    self._righe.append(testo)
        except Exception:
            pass

    def _apri(self):
        """Apre il riproduttore. Non avvia il ciclo: quello e' di `avvia`."""
        try:
            processo = subprocess.Popen(
                comando_pcm(self._device, FREQ_EFFETTI, 1,
                            BUFFER_EFFETTI_US, PERIODO_EFFETTI_US),
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE)
        except (OSError, subprocess.SubprocessError) as exc:
            self.errore = str(exc)
            return False, str(exc)
        # Il tubo piccolo, e adesso si sa perche'. Quello che sta nel tubo e'
        # ritardo invisibile: `/proc` racconta l'anello della scheda ma non il
        # tubo, quindi un tubo grande sfugge alla regolazione. 4096 byte e' il
        # minimo che Linux concede (una pagina) e valgono 93 ms a 22050 mono.
        stringi_tubo(processo.stdin, TUBO_EFFETTI)
        # Flusso nuovo, frequenza da rileggere: dopo un riavvio la scheda
        # potrebbe averne negoziata un'altra.
        self._freq_scheda = None
        threading.Thread(target=self._leggi_errori, args=(processo,),
                         name="mixer-errori", daemon=True).start()
        with self._lucchetto:
            self._processo = processo
        return True, ""

    def registra(self, percorso):
        """Scrive su file una copia di tutto quello che va alla scheda.

        PCM grezzo 22050 Hz mono 16 bit: esattamente quello che si da\' in
        pasto ad `aplay`. Si riapre a ogni partita, perche\' un registro che
        cresce per giorni su una scheda SD non e\' una diagnosi, e\' un guasto
        nuovo.
        """
        try:
            self._registro = open(percorso, "wb")
        except OSError as exc:
            self._registro = None
            print("[suoni] registro non aperto: %s" % exc)

    def _chiudi_registro(self):
        registro, self._registro = self._registro, None
        if registro is not None:
            try:
                registro.close()
            except Exception:
                pass

    def avvia(self, device, vol, fondo=0):
        """Apre il riproduttore per una partita. Restituisce (ok, motivo).

        `fondo` e' l'ampiezza del fruscio da scrivere quando non c'e' niente
        da suonare: vedi `_prepara_muto`. Zero lo disattiva, ed e' il
        predefinito perche' chi apre il mixer da una prova non vuole rumore
        dentro la misura.
        """
        self._prepara_muto(fondo)
        with self._lucchetto:
            if self._processo is not None and self._processo.poll() is None:
                return True, ""
            if abs(float(vol) - self._volume) > 1e-9:
                # Il volume e' cotto dentro i pacchi: cambiandolo vanno rifatti.
                self._pacchi.clear()
            self._volume = max(0.0, min(1.0, float(vol)))
            self._device = device
            self._voluto = True
            self._arreso = False
            self._voci = []
            self.errore = ""
            self._stop.clear()
        ok, motivo = self._apri()
        if not ok:
            with self._lucchetto:
                self._voluto = False
            return False, motivo
        self._thread = threading.Thread(target=self._ciclo, name="mixer",
                                        daemon=True)
        self._thread.start()
        return True, ""

    def acceso(self):
        """C'e' un riproduttore vivo in questo momento."""
        with self._lucchetto:
            return self._processo is not None and self._processo.poll() is None

    def in_servizio(self):
        """C'e' una partita che vuole il mixer e non si e' ancora arreso.

        Non e' `acceso()`, e la differenza e' il punto di tutto: fra la morte
        del riproduttore e la sua riapertura il mixer non e' acceso ma e'
        **in servizio**, e i suoni chiesti in quel momento si mettono in coda
        invece di prendere la vecchia strada che li scartava.
        """
        with self._lucchetto:
            return self._voluto and not self._arreso

    def _chiudi_processo(self):
        with self._lucchetto:
            processo, self._processo = self._processo, None
        if processo is None:
            return
        for chiudi in (lambda: processo.stdin.close(), processo.terminate):
            try:
                chiudi()
            except Exception:
                pass
        try:
            processo.wait(timeout=3)
        except Exception:
            pass

    def svuota(self, attesa=ATTESA_SVUOTO):
        """Aspetta che le voci in coda siano uscite davvero.

        Serve a un caso solo, ed e' un caso che si sentiva: il suono del
        primato parte mentre la partita si sta gia' chiudendo, e subito dopo
        si chiude il mixer. Senza questa attesa il riproduttore veniva ucciso
        prima di aver suonato quello che gli era appena stato dato — e con un
        cuscino di CUSCINO millisecondi davanti, "subito dopo" vuol dire
        sempre. Si aspetta che la coda si svuoti, piu' il tempo che il
        cuscino gia' scritto impieghi ad arrivare all'altoparlante.
        """
        with self._lucchetto:
            se_ne_erano = bool(self._voci)
        if not se_ne_erano:
            # Niente in coda: chiudere subito e' giusto, e mezzo secondo di
            # attesa a ogni cambio di gioco si noterebbe.
            return
        scadenza = time.monotonic() + attesa
        while time.monotonic() < scadenza:
            with self._lucchetto:
                if not self._voci:
                    break
                if self._processo is None or self._arreso:
                    return
            time.sleep(0.02)
        time.sleep(CUSCINO + 0.03)

    def ferma(self):
        self._stop.set()
        with self._lucchetto:
            self._voluto = False
        thread, self._thread = self._thread, None
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        self._chiudi_processo()
        self._chiudi_registro()
        with self._lucchetto:
            self._voci = []

    # ---------------------------------------------------------- suonare

    def suona(self, nome):
        """Mette una voce in coda. Non scarta, salvo casi da contare."""
        self._conti["chiesti"] += 1
        campioni = self._carica(nome)
        if not campioni:
            self._conti["mancanti"] += 1
            return False
        with self._lucchetto:
            if not self._voluto or self._arreso:
                return False
            if len(self._voci) >= VOCI_MASSIME:
                self._voci.pop(0)
                self._conti["scartati"] += 1
            self._voci.append([campioni, 0, time.monotonic(), nome])
        return True

    # --------------------------------------------------------- mixaggio

    def _prossimo_blocco(self):
        """I prossimi BLOCCO campioni, gia' in byte.

        Tre strade, dalla piu' frequente alla piu' rara: niente da suonare —
        silenzio gia' pronto; una voce sola — una fetta del suo pacco, cioe'
        una copia di memoria; piu' voci — si sommano davvero.
        """
        with self._lucchetto:
            vive = []
            attive = []
            for voce in self._voci:
                campioni, posizione, _nato, nome = voce
                resto = len(campioni) - posizione
                quanti = BLOCCO if resto > BLOCCO else resto
                if posizione == 0:
                    self._conti["resi"] += 1
                attive.append((nome, campioni, posizione, quanti))
                voce[1] = posizione + quanti
                if voce[1] < len(campioni):
                    vive.append(voce)
            self._voci = vive
        if not attive:
            return self._blocco_muto()
        if len(attive) == 1:
            nome, _campioni, posizione, quanti = attive[0]
            pacco = self._pacchi.get(nome)
            if pacco is not None:
                pezzo = pacco[posizione * 2:(posizione + quanti) * 2]
                if quanti < BLOCCO:
                    pezzo += b"\x00\x00" * (BLOCCO - quanti)
                return pezzo
        somma = [0] * BLOCCO
        for _nome, campioni, posizione, quanti in attive:
            for i in range(quanti):
                somma[i] += campioni[posizione + i]
        # Invece di tagliare i picchi — che e' distorsione, e su due mattoni
        # insieme si sente — si abbassa il blocco quel tanto che basta a
        # farlo stare dentro. Dura 23 ms e nessuno lo percepisce come un calo
        # di volume, ma nessun campione viene stroncato.
        picco = max(max(somma), -min(somma))
        guadagno = self._volume
        if picco * guadagno > 32767:
            guadagno = 32767.0 / picco
        return struct.pack("<%dh" % BLOCCO, *[int(v * guadagno) for v in somma])

    # ------------------------------------------------------------ ciclo

    # ------------------------------------------------- il blocco "muto"

    def _prepara_muto(self, ampiezza):
        """Costruisce i blocchi da scrivere quando non c'e' niente da suonare.

        Perche' non sono zeri
        ---------------------
        Questa e' la riga per cui la 9.1 esiste. Molti convertitori USB — il
        nostro compreso — si **automutano** quando ricevono zero digitale
        esatto, e al primo campione diverso da zero riaprono l'uscita con una
        rampa di qualche decina di millesimi, per non fare il "plop". Un
        effetto di gioco dura cinquanta o settanta millesimi: arriva mentre la
        rampa e' ancora a meta' e sparisce quasi tutto. Se invece un altro
        suono e' appena passato, la scheda e' sveglia e lo stesso effetto si
        sente benissimo — ed e' esattamente il sintomo che si vedeva sul
        campo: «quando lo sento, lo sento bene», e Snake, che suona ogni
        cinque secondi, ne perdeva nove su dieci mentre Breakout, che suona a
        raffica, ne salvava la maggior parte.

        La prova che lo ha inchiodato: lo stesso identico beep, dieci volte di
        fila, con in mezzo silenzio digitale oppure un fruscio inudibile. Col
        silenzio non si sentiva; col fruscio si'. E lo conferma dal lato
        opposto quello che sul DMD ha sempre funzionato — Doom, il Game Boy,
        la musica AirPlay: nessuno dei tre scrive mai zero, perche' hanno
        tutti un flusso continuo.

        Il fruscio e' rumore bianco a ±`ampiezza` su 32767: col predefinito 32
        sono −60 dBFS, sotto il rumore di fondo di qualunque stanza e sotto
        quello dei componenti dell'amplificatore. Si tengono in memoria
        BLOCCHI_MUTI blocchi diversi e si girano in tondo: un blocco solo
        ripetuto quarantatre volte al secondo non sarebbe piu' rumore, sarebbe
        una nota a 43 Hz.
        """
        self._sottofondo = max(0, int(ampiezza or 0))
        self._muto = 0
        if self._sottofondo <= 0:
            self._muti = [self._silenzio]
            return
        casuale = random.Random(20260917)
        self._muti = [
            struct.pack("<%dh" % BLOCCO,
                        *[casuale.randint(-self._sottofondo, self._sottofondo)
                          for _ in range(BLOCCO)])
            for _ in range(BLOCCHI_MUTI)]

    def _blocco_muto(self):
        blocco = self._muti[self._muto]
        self._muto = (self._muto + 1) % len(self._muti)
        return blocco

    def _butta_vecchie(self):
        """Le voci che hanno aspettato troppo mentre la scheda era occupata."""
        limite = time.monotonic() - ETA_MASSIMA
        with self._lucchetto:
            tenute = [v for v in self._voci if v[2] >= limite]
            self._conti["scaduti"] += len(self._voci) - len(tenute)
            self._voci = tenute

    def _riapri(self, motivo):
        """Il riproduttore e' morto: si riprova finche' la scheda non torna.

        E' la riga di codice che questa versione esiste per scrivere. La
        scheda del DMD e' una sola: se quando parte la partita sta finendo un
        avviso di un servizio, `aplay` non riesce ad aprirla e muore. Prima
        questo spegneva il mixer per tutta la partita, in silenzio. Adesso si
        aspetta che l'avviso finisca e si riprende.
        """
        self._conti["morti"] += 1
        if motivo:
            self.errore = motivo
        # Nel registro, sempre. Una morte del riproduttore a meta' partita e'
        # la cosa che rende muto Breakout, ed e' rimasta invisibile per
        # versioni intere perche' non la scriveva nessuno da nessuna parte.
        print("[suoni] riproduttore caduto (%d volta/e): %s"
              % (self._conti["morti"], self.errore or "motivo sconosciuto"))
        self._chiudi_processo()
        self._butta_vecchie()
        scadenza = time.monotonic() + RIAVVIO_LIMITE
        tentativo = 0
        while not self._stop.is_set() and time.monotonic() < scadenza:
            attesa = RIAVVIO_ATTESA if tentativo < 10 else RIAVVIO_LENTO
            if self._stop.wait(attesa):
                return False
            tentativo += 1
            ok, _motivo = self._apri()
            if ok:
                # Il riproduttore c'e'; se la scheda e' ancora occupata muore
                # di nuovo e si torna qui. Le voci ferme da troppo si buttano
                # adesso, non quando riprenderanno a suonare in ritardo.
                self._conti["riavvii"] += 1
                self._butta_vecchie()
                print("[suoni] scheda riaperta dopo %d tentativo/i" % tentativo)
                return True
        with self._lucchetto:
            self._arreso = True
        if not self.errore:
            self.errore = "la scheda audio non si e' liberata"
        print("[suoni] mixer arreso: %s" % self.errore)
        return False

    def _ciclo(self):
        """Scrive un blocco per volta, tenendosi CUSCINO davanti al presente.

        Il ritmo lo detta il nostro orologio, non la scrittura sul tubo: se ci
        limitassimo a bloccarci quando il tubo e' pieno, il cuscino sarebbe
        quello che il tubo si trova ad avere, cioe' nessuno all'inizio. Qui si
        scrive finche' non si e' CUSCINO avanti, poi si aspetta. La scrittura
        bloccante resta come secondo freno per la deriva fra il nostro
        orologio e il quarzo della scheda.
        """
        avvio = time.monotonic()
        scritti = 0
        blocchi = 0
        ritardo = None
        while not self._stop.is_set():
            # Primo freno: il nostro orologio. Vale sempre, e da solo basta
            # nei primi secondi, quando la scheda non ha ancora un ritardo da
            # leggere.
            avanti = (avvio + scritti / float(FREQ_EFFETTI)) - time.monotonic()
            if avanti > CUSCINO:
                time.sleep(avanti - CUSCINO)
            # Secondo freno, ed e' quello che conta: l'orologio della scheda.
            # Si guarda una decina di volte al secondo -- sono due file di
            # `/proc`, non costano niente -- e se la scheda ha gia' piu' di un
            # cuscino da suonare si aspetta che lo consumi. Senza questo, la
            # differenza fra i due orologi si accumula e la coda si riempie
            # fino all'orlo: sul DMD e' stata misurata piena al 99%, cioe' un
            # quarto di secondo di ritardo piu' il tubo. I suoni uscivano
            # tutti, ma cosi' in ritardo da sembrare di un altro colpo.
            # A ogni blocco, non ogni quattro: con il controllo ogni quattro
            # si scrivono fino a tre blocchi -- settanta millesimi -- dopo che
            # la coda ha gia' passato il cuscino, e la misura diceva che
            # bastavano a sforare. Costa la lettura di un file di `/proc`,
            # trenta volte al secondo; la frequenza invece si legge una volta
            # sola per flusso, che e' il file che costava davvero.
            if self._freq_scheda is None:
                self._freq_scheda = frequenza_alsa(self._device)
            ritardo = ritardo_alsa(self._device, self._freq_scheda)
            if ritardo is not None and ritardo > CUSCINO_ANELLO:
                # Si aspetta **davvero** che la scheda consumi, rileggendo il
                # ritardo invece di stimarlo: dormire un pezzetto e scrivere
                # comunque il blocco successivo non fa scendere la coda, la fa
                # solo salire piu' piano. Mezzo secondo di tetto, perche' un
                # flusso che si ferma e non riparte non deve poter bloccare
                # questo ciclo per sempre.
                # Il tetto e' corto apposta: se un domani il bersaglio
                # tornasse irraggiungibile, il danno e' una pausa da 150 ms e
                # non mezzo secondo di silenzio a ogni blocco.
                scadenza = time.monotonic() + 0.15
                while not self._stop.is_set() and time.monotonic() < scadenza:
                    time.sleep(0.01)
                    ritardo = ritardo_alsa(self._device, self._freq_scheda)
                    if ritardo is None or ritardo <= CUSCINO_ANELLO:
                        break
            blocchi += 1
            with self._lucchetto:
                processo = self._processo
            morto = processo is None or processo.poll() is not None
            blocco = None if morto else self._prossimo_blocco()
            if not morto and self._registro is not None:
                # Una copia esatta di quello che va alla scheda. Serve a una
                # domanda sola, che per settimane non ha avuto risposta:
                # *questi suoni sono usciti dal DMD, si' o no?* Un contatore
                # dice quello che il programma crede di aver fatto; questo
                # dice quello che ha fatto.
                try:
                    self._registro.write(blocco)
                except Exception:
                    self._registro = None
            if not morto:
                try:
                    processo.stdin.write(blocco)
                    processo.stdin.flush()
                except Exception as exc:
                    morto = True
                    self.errore = str(exc)
            if morto:
                if self._stop.is_set():
                    break
                if not self._riapri(self.errore):
                    break
                avvio = time.monotonic()
                scritti = 0
                continue
            scritti += BLOCCO

    # ------------------------------------------------------------ stato

    def stato(self):
        """I numeri che mancavano. Li mostra la pagina Giochi."""
        with self._lucchetto:
            voci = len(self._voci)
            voluto, arreso, device = self._voluto, self._arreso, self._device
        dati = dict(self._conti)
        dati.update({"acceso": self.acceso(), "voluto": voluto,
                     "arreso": arreso, "device": device, "voci": voci,
                     "cuscino": CUSCINO, "errore": self.errore,
                     "righe": list(self._righe)[-5:],
                     "setup": list(self._setup),
                     "buffer_ms": self._buffer_concesso()})
        vero = ritardo_alsa(device)
        dati["ritardo_ms"] = int(round(vero * 1000)) if vero is not None else None
        # Quanti dei suoni chiesti sono davvero usciti. E' il numero che la
        # domanda "ne salta troppi" chiedeva da sempre.
        chiesti = dati["chiesti"]
        dati["resa"] = round(100.0 * dati["resi"] / chiesti, 1) if chiesti else 100.0
        return dati

    def _buffer_concesso(self):
        """Quanti millisecondi di buffer ci ha dato davvero la scheda.

        Si chiedono BUFFER_EFFETTI_US, ma ALSA concede quello che puo' e non
        lo dice a nessuno. Se ci ha dato molto meno, il cuscino su cui
        contiamo non esiste e i suoni saltano senza che nessuno capisca
        perche'. `aplay -v` lo stampa: `buffer_size: 5512`, in campioni.

        **I campioni di chi.** Questa e' la correzione: `buffer_size` e' in
        fotogrammi del flusso che lo dichiara, e con `plughw` i flussi sono
        piu' di uno. Il DMD ne ha stampati tre -- il nostro a 22050, la
        conversione a 48000, la scheda a 48000 stereo -- e dividere per
        FREQ_EFFETTI il `buffer_size` della scheda dava 544 ms di cuscino
        dove ce n'erano 250. Un numero sbagliato di piu' del doppio, nel
        verso che rassicura: la pagina diceva che il cuscino era abbondante
        proprio mentre si cercava un difetto di cuscino. Adesso si usa la
        frequenza dichiarata nello stesso blocco, che nel riepilogo viene
        qualche riga prima.
        """
        frequenza = None
        for riga in self._setup:
            basso = riga.lower()
            if basso.strip().startswith("rate") and ":" in riga:
                cifre = "".join(c for c in riga.split(":", 1)[1] if c.isdigit())
                if cifre:
                    frequenza = int(cifre)
            elif "buffer_size" in basso:
                cifre = "".join(c for c in riga if c.isdigit())
                if cifre:
                    return int(round(1000.0 * int(cifre)
                                     / float(frequenza or FREQ_EFFETTI)))
        return None

    def azzera(self):
        for chiave in self._conti:
            self._conti[chiave] = 0
        self._righe.clear()
        self._setup.clear()


_mixer = Mixer()


# Dove finisce la registrazione degli effetti, quando la si accende.
REGISTRO_EFFETTI = "/tmp/dmd-effetti.raw"


def effetti_avvia(cfg):
    """Apre il mixer per una partita. Silenzioso se non si deve suonare."""
    device = uscita_giochi(cfg)
    if not device:
        return False
    _mixer.azzera()
    ok, _motivo = _mixer.avvia(device, volume_giochi(cfg), sottofondo(cfg))
    # Una levetta che non compare in nessuna pagina, e va bene cosi\': serve a
    # rispondere a "questi suoni sono usciti o no?" quando i contatori dicono
    # di si\' e l\'orecchio dice di no. Si accende a mano in configurazione,
    # sotto `audio.registra_effetti`, e scrive PCM grezzo per tutta la partita.
    if ok and _conf(cfg).get("registra_effetti"):
        _mixer.registra(REGISTRO_EFFETTI)
    return ok


def effetti_ferma(svuota=True):
    """Chiude il mixer. Per difetto aspetta che gli ultimi suoni siano usciti."""
    if svuota:
        _mixer.svuota()
    _mixer.ferma()


def effetti_accesi():
    return _mixer.acceso()


def effetti_stato():
    return _mixer.stato()


def suona_effetto(cfg, nome):
    """Un effetto dei giochi. Silenzioso se gli effetti sono spenti.

    Durante una partita passa **sempre** dal mixer, anche nei momenti in cui
    il riproduttore e' morto e si sta riaprendo: la voce si mette in coda e
    parte appena la scheda torna, o scade se ha aspettato troppo. La vecchia
    versione qui ripiegava sulla strada del processo per volta appena il
    mixer non risultava acceso, ed e' li' che i suoni sparivano a grappoli:
    quella strada ne suona uno e scarta tutti quelli che si sovrappongono.

    Fuori da una partita — il suono del primato quando la sessione si sta
    gia' chiudendo — la strada del processo per volta va benissimo: e' un
    suono solo e nessuno lo sta accavallando.
    """
    if not _conf(cfg).get("giochi", True):
        return False
    if _mixer.in_servizio():
        return _mixer.suona(nome)
    percorso = effetto(nome)
    if not percorso:
        return False
    partito, _motivo = riproduci(cfg, percorso, vol=volume_giochi(cfg))
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


# --------------------------------------------------- il livello della scheda

def livello_scheda(cfg):
    """Il volume hardware della scheda scelta, in percentuale. None se ignoto.

    Esiste per un guasto vero, costato due ore. La chiavetta USB del DMD si
    era presentata con il suo controllo `PCM` a **-20 dB** -- un decimo
    dell'ampiezza -- e quel livello penalizzava tutto insieme: musica AirPlay,
    avvisi dei servizi, effetti dei giochi. Nessuna pagina lo mostrava, quindi
    non c'era modo di scoprirlo dall'interfaccia: si poteva solo inciampare in
    `amixer` da riga di comando.

    Un numero che il programma puo' leggere e l'utente no e' esattamente la
    classe di difetti che questo progetto continua a pagare.
    """
    scelta = uscita(cfg)
    if not scelta or not shutil.which("amixer"):
        return None
    numero = re.search(r"(\d+)", scelta.split(":", 1)[-1])
    if not numero:
        return None
    try:
        esito = subprocess.run(["amixer", "-c", numero.group(1)],
                               capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    if esito.returncode:
        return None
    # Si prende la prima percentuale di riproduzione che compare. Le schede
    # hanno controlli diversi -- PCM, Speaker, Master -- e cercarne uno per
    # nome vorrebbe dire un elenco da tenere aggiornato per sempre.
    trovato = re.search(r"Playback \d+ \[(\d+)%\]", esito.stdout)
    return int(trovato.group(1)) if trovato else None


def stato(cfg):
    """Quel che serve alle pagine.

    `volume` e' quello **impostato**, non quello in vigore adesso, e la
    differenza conta: lo slider della pagina mostra questo valore e lo
    risalva appena tocchi qualcos'altro. Se qui rispondessimo con il volume
    notturno, aprire la pagina di notte e premere Salva scriverebbe zero in
    configurazione per sempre. E' lo stesso inganno dello slider della
    luminosita' durante il night mode, che abbiamo gia' pagato una volta.

    Il volume in vigore lo si legge da `notte` e `volume_notturno`, che
    servono alla pagina per dirlo a parole invece di farlo di nascosto.
    """
    return {"disponibile": disponibile(), "acceso": acceso(cfg),
            "dispositivi": dispositivi(), "uscita": uscita(cfg),
            "nome": nome_uscita(cfg),
            "volume": volume_impostato(cfg), "errore": ultimo_errore(),
            "notte": _notte(), "volume_notturno": volume_notturno(cfg),
            "livello": livello_scheda(cfg),
            "effetti": os.path.isdir(CARTELLA_EFFETTI)}
