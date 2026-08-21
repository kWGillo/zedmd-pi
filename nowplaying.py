"""Che cosa sta suonando, indipendentemente da chi lo sta suonando.

Questo modulo non parla ne' con AirPlay ne' con Spotify: raccoglie quello che
gli passano, lo tiene aggiornato e risponde a una sola domanda — "adesso che
brano c'e', a che punto e', sta suonando o e' in pausa".

Le sorgenti possibili sono tre e possono coesistere:

  airplay    shairport-sync, che si presenta in rete come una cassa AirPlay 2
             e riceve qualunque cosa parta da un iPhone, un iPad o un Mac.
             Copre Apple Music, Spotify, Amazon Music, YouTube: al ricevitore
             AirPlay non importa quale applicazione stia suonando.
  spotify    l'API web di Spotify, che dice che cosa sta suonando su
             qualunque dispositivo dell'account, comprese le casse vere.
  external   qualsiasi altra cosa che pubblichi su MQTT nel nostro formato,
             tipicamente un'automazione di Home Assistant.

Quando piu' sorgenti hanno qualcosa da dire vince quella con la precedenza
piu' alta fra le sorgenti ancora fresche. AirPlay sta in cima perche' se sta
arrivando un flusso audio qui, quello e' senza dubbio cio' che si sta
ascoltando adesso.

**La posizione nel brano non arriva di continuo.** AirPlay manda `prgr` al
cambio di traccia e dopo un salto, Spotify risponde solo quando lo si
interroga. Fra un aggiornamento e l'altro il tempo lo conta questo modulo,
ripartendo dall'ultimo valore certo. Il conteggio usa `time.monotonic()` e
non l'orologio di sistema: una correzione NTP non deve far saltare la barra
di avanzamento.
"""

import json
import threading
import time

# Precedenza fra le sorgenti: numero piu' alto, priorita' maggiore.
RANK = {"airplay": 30, "external": 20, "spotify": 10}

# Un brano in pausa resta visibile per questo tempo, poi la sorgente lascia
# il display a chi viene dopo. Un brano in riproduzione non scade mai da solo.
DEFAULT_HOLD = 90

# Se una sorgente dice "sto suonando" e poi tace troppo a lungo, con ogni
# probabilita' e' morta senza salutare: dopo questo tempo la si dimentica.
STALE_PLAYING = 3600

# Per quanti secondi si continua a far avanzare l'orologio del brano senza
# ricevere nulla dalla sorgente.
#
# Serve perche' il segnale di pausa puo' non arrivare: se l'utente mette in
# pausa dal telefono e la sorgente non lo dice, senza questo limite il
# pannello continuerebbe a contare all'infinito un tempo che non passa. Meglio
# fermarsi e dichiarare che non si sa, che continuare a mostrare un dato
# inventato: un orologio fermo si nota, uno che sbaglia no.
# Il valore va tenuto largo: durante la riproduzione normale shairport-sync
# puo' stare in silenzio per decine di secondi: manda i metadati al cambio di
# traccia e poi tace. Un limite stretto produrrebbe pause finte a meta' brano.
# E' un fondo di sicurezza per sorgenti che non annunciano la pausa, non il
# meccanismo principale: quello e' l'evento `paus`, che arriva subito.
DEFAULT_ADVANCE_TIMEOUT = 600

# Frequenza di campionamento dei timestamp RTP di AirPlay.
RTP_RATE = 44100.0


def _clean(value, limit=200):
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode("utf-8", "replace")
    return str(value).strip()[:limit]


def empty_track():
    return {
        "title": "", "artist": "", "album": "",
        "duration": 0.0, "position": 0.0,
        "playing": False, "source": "", "client": "",
        "updated": 0.0, "stale": False,
    }


class _SourceState:
    """Quello che una singola sorgente ci ha detto finora."""

    def __init__(self, name):
        self.name = name
        self.title = ""
        self.artist = ""
        self.album = ""
        self.client = ""
        self.duration = 0.0
        self.playing = False
        self.active = False          # sessione aperta, anche senza metadati
        self._position = 0.0
        self._position_at = time.monotonic()
        self.updated = 0.0           # ora di sistema, per la web UI
        self.touched = time.monotonic()
        # Ultimo segnale di qualsiasi tipo ricevuto da questa sorgente: e' il
        # riferimento per capire fino a quando ci si puo' fidare dell'orologio.
        self.signalled = time.monotonic()
        # Scadenza esplicita, in tempo monotono. Serve al brano di prova
        # della web UI, che deve togliersi di mezzo da solo.
        self.expires_at = 0.0

    # -------------------------------------------------------------- posizione

    def set_position(self, seconds):
        self._position = max(0.0, float(seconds))
        self._position_at = time.monotonic()

    def silent_for(self):
        """Da quanto non arriva piu' niente da questa sorgente."""
        return time.monotonic() - self.signalled

    def trusted(self, timeout):
        """True se l'orologio del brano e' ancora credibile.

        Oltre il limite non si sa piu' se stia suonando: la sorgente potrebbe
        essere in pausa senza averlo detto.
        """
        return timeout <= 0 or self.silent_for() <= timeout

    def position(self, timeout=0):
        """Posizione stimata adesso: l'ultima certa, piu' il tempo trascorso.

        Il tempo trascorso viene conteggiato solo finche' la sorgente da'
        segno di vita. Passato il limite l'orologio si ferma dov'era, invece
        di proseguire su un'ipotesi che nessuno conferma piu'.
        """
        if not self.playing:
            return self._position
        elapsed = time.monotonic() - self._position_at
        if timeout > 0:
            # Si accredita al massimo il tempo fino all'ultimo segnale.
            elapsed = min(elapsed, max(0.0, self.signalled - self._position_at)
                          + timeout)
        value = self._position + elapsed
        if self.duration > 0:
            value = min(value, self.duration)
        return max(0.0, value)

    def set_playing(self, playing, timeout=0):
        # Congela la posizione prima di cambiare stato, altrimenti mettendo in
        # pausa si perderebbe il tempo trascorso dall'ultimo aggiornamento.
        self.set_position(self.position(timeout))
        self.playing = bool(playing)
        if playing:
            self.active = True

    def touch(self):
        self.touched = time.monotonic()
        self.signalled = self.touched
        self.updated = time.time()

    # ----------------------------------------------------------------- utilita'

    def has_content(self):
        return bool(self.title or self.artist or self.album)

    def age(self):
        return time.monotonic() - self.touched

    def snapshot(self, timeout=0):
        # Se la sorgente tace da troppo non si dichiara "in riproduzione":
        # non lo si sa piu'. Il simbolo di pausa e' l'ammissione onesta.
        credibile = self.trusted(timeout)
        return {
            "title": self.title, "artist": self.artist, "album": self.album,
            "duration": self.duration, "position": self.position(timeout),
            "playing": self.playing and credibile, "source": self.name,
            "client": self.client, "updated": self.updated,
            "stale": not credibile,
        }

    def reset(self):
        self.title = self.artist = self.album = ""
        self.duration = 0.0
        self.playing = False
        self.active = False
        self.expires_at = 0.0
        self.set_position(0.0)
        self.signalled = time.monotonic()


class NowPlaying:
    """Stato condiviso del brano corrente."""

    def __init__(self, cfg):
        self.cfg = cfg
        self._lock = threading.Lock()
        self._sources = {name: _SourceState(name) for name in RANK}
        self._last_key = None
        self.changes = 0

    # ------------------------------------------------------------------ lettura

    def settings(self):
        return self.cfg.get("nowplaying") or {}

    def hold_seconds(self):
        try:
            return max(5, int(self.settings().get("hold_seconds", DEFAULT_HOLD)))
        except (TypeError, ValueError):
            return DEFAULT_HOLD

    def advance_timeout(self):
        """Per quanto ci si fida dell'orologio senza conferme. 0 = sempre."""
        try:
            value = int(self.settings().get("advance_timeout",
                                            DEFAULT_ADVANCE_TIMEOUT))
        except (TypeError, ValueError):
            return DEFAULT_ADVANCE_TIMEOUT
        return max(0, value)

    def _candidate(self, state, timeout):
        """True se questa sorgente ha ancora diritto a essere mostrata.

        Una sorgente che dice di suonare ma tace da troppo viene trattata
        come se fosse in pausa: sta a schermo ancora per la finestra di
        permanenza e poi lascia il posto. Senza questo, una pausa non
        annunciata terrebbe il player sul pannello per un'ora.
        """
        if not state.has_content():
            return False
        if state.expires_at and time.monotonic() > state.expires_at:
            return False
        if state.playing and state.trusted(timeout):
            return state.age() < STALE_PLAYING
        # In pausa si resta a schermo per un po', poi si lascia il posto.
        return state.active and state.age() < self.hold_seconds()

    def snapshot(self):
        """Il brano da mostrare adesso, oppure un record vuoto."""
        timeout = self.advance_timeout()
        with self._lock:
            best = None
            for state in self._sources.values():
                if not self._candidate(state, timeout):
                    continue
                if best is None:
                    best = state
                    continue
                # In riproduzione batte in pausa; a parita', la precedenza.
                # Una sorgente che tace da troppo non conta come in
                # riproduzione, perche' non lo sappiamo piu'.
                mine = (state.playing and state.trusted(timeout),
                        RANK[state.name], state.touched)
                theirs = (best.playing and best.trusted(timeout),
                          RANK[best.name], best.touched)
                if mine > theirs:
                    best = state
            return best.snapshot(timeout) if best else empty_track()

    def playing(self):
        return self.snapshot()["playing"]

    def has_content(self):
        return bool(self.snapshot()["title"] or self.snapshot()["artist"])

    # ---------------------------------------------------------------- scrittura

    def update(self, source, **fields):
        """Aggiorna una sorgente. I campi assenti restano come sono."""
        if source not in self._sources:
            return
        with self._lock:
            state = self._sources[source]
            for key in ("title", "artist", "album", "client"):
                if key in fields:
                    setattr(state, key, _clean(fields[key]))
            if "duration" in fields and fields["duration"] is not None:
                try:
                    state.duration = max(0.0, float(fields["duration"]))
                except (TypeError, ValueError):
                    pass
            if "position" in fields and fields["position"] is not None:
                try:
                    state.set_position(float(fields["position"]))
                except (TypeError, ValueError):
                    pass
            if "playing" in fields:
                state.set_playing(fields["playing"], self.advance_timeout())
            if fields.get("active"):
                state.active = True
            if "expires" in fields:
                try:
                    seconds = float(fields["expires"])
                    state.expires_at = time.monotonic() + seconds if seconds > 0 else 0.0
                except (TypeError, ValueError):
                    state.expires_at = 0.0
            elif any(key in fields for key in ("title", "artist", "album")):
                # Un aggiornamento vero cancella la scadenza del brano di prova.
                state.expires_at = 0.0
            state.touch()
            self._note_change(state)

    def clear(self, source):
        with self._lock:
            state = self._sources.get(source)
            if state is not None:
                state.reset()
                state.touch()

    def _note_change(self, state):
        key = (state.name, state.title, state.artist)
        if key != self._last_key:
            self._last_key = key
            self.changes += 1

    # ------------------------------------------------------ ingresso da AirPlay

    def handle_shairport(self, topic, payload):
        """Interpreta un messaggio pubblicato da shairport-sync.

        Si accettano tre livelli di topic, perche' portano cose diverse:

          shairport/title          testi gia' leggibili
          shairport/playing        stato esplicito, "1" oppure "0"
          shairport/ssnc/paus      eventi grezzi a quattro lettere

        `paus` merita una riga a se': e' l'unico avviso che arriva
        nell'istante in cui si mette in pausa dal telefono. Lo stato
        `playing` invece resta a "1" ancora per una decina di secondi, finche'
        l'iPhone non chiude la sessione, quindi aspettare quello vorrebbe
        dire mostrare un brano che avanza mentre e' fermo.
        """
        leaf = topic.rsplit("/", 1)[-1]
        text = _clean(payload, 400)

        if leaf in ("title", "minm"):
            self.update("airplay", title=text, active=True)
        elif leaf in ("artist", "asar"):
            self.update("airplay", artist=text, active=True)
        elif leaf in ("album", "asal"):
            self.update("airplay", album=text, active=True)
        elif leaf == "client_name":
            self.update("airplay", client=text)
        elif leaf == "prgr":
            values = parse_progress(text)
            if values:
                position, duration = values
                self.update("airplay", position=position, duration=duration,
                            active=True)
        elif leaf == "paus":
            # Pausa dal telefono: arriva subito, ed e' l'unico segnale.
            self.update("airplay", playing=False)
        elif leaf == "playing":
            # Stato esplicito pubblicato fra i topic leggibili.
            self.update("airplay", playing=text.strip() == "1", active=True)
        elif leaf == "active":
            if text.strip() == "0":
                self.update("airplay", playing=False)
            else:
                self.update("airplay", active=True)
        elif leaf in ("play_start", "play_resume", "prsm", "pbeg"):
            self.update("airplay", playing=True, active=True)
        elif leaf in ("play_flush", "pfls"):
            # Flush arriva sia in pausa sia dopo un salto nel brano.
            self.update("airplay", playing=False)
        elif leaf in ("play_end", "pend", "active_end", "aend"):
            # Fine della sessione: il brano non si cancella di colpo, resta
            # fermo a schermo per la finestra di permanenza e poi lascia il
            # posto. Cancellarlo subito faceva sparire tutto dieci secondi
            # dopo la pausa, senza che l'utente avesse fatto nulla.
            self.update("airplay", playing=False)

    # -------------------------------------------------- ingresso generico MQTT

    def handle_external(self, _topic, payload):
        """Un JSON pubblicato da Home Assistant o da qualsiasi altra cosa.

        Formato atteso, tutti i campi facoltativi:
          {"title": "...", "artist": "...", "album": "...",
           "duration": 355, "position": 167, "playing": true}
        Un oggetto vuoto, `null` o una stringa vuota azzerano la sorgente.
        """
        text = _clean(payload, 4000)
        if not text or text.lower() in ("null", "none", "{}", "off"):
            self.clear("external")
            return
        try:
            data = json.loads(text)
        except ValueError:
            # Non e' JSON: lo si prende per quello che e', un titolo.
            self.update("external", title=text, playing=True, active=True)
            return
        if not isinstance(data, dict) or not data:
            self.clear("external")
            return
        self.update(
            "external",
            title=data.get("title", data.get("media_title", "")),
            artist=data.get("artist", data.get("media_artist", "")),
            album=data.get("album", data.get("media_album_name", "")),
            duration=data.get("duration", data.get("media_duration")),
            position=data.get("position", data.get("media_position")),
            playing=bool(data.get("playing",
                                  str(data.get("state", "")).lower() == "playing")),
            active=True,
        )

    # ------------------------------------------------------------------ stato

    def status_dict(self):
        """Riepilogo per la web UI, con una riga per sorgente."""
        with self._lock:
            per_source = {}
            for name, state in self._sources.items():
                per_source[name] = {
                    "title": state.title, "artist": state.artist,
                    "playing": state.playing, "active": state.active,
                    "updated": state.updated,
                    "silent": round(state.silent_for(), 1),
                    "age": round(state.age(), 1) if state.updated else None,
                }
        current = self.snapshot()
        current["sources"] = per_source
        return current


def parse_progress(text):
    """`prgr` di AirPlay: tre timestamp RTP `inizio/adesso/fine`.

    Restituisce (posizione, durata) in secondi, oppure None se il valore non
    ha la forma attesa. I timestamp sono contatori a 32 bit di campioni a
    44100 Hz; se il contatore e' rientrato a zero durante il brano la
    differenza risulta negativa e il valore viene scartato invece di
    produrre una barra assurda.
    """
    parts = str(text).replace(" ", "").split("/")
    if len(parts) != 3:
        return None
    try:
        start, current, end = (int(float(p)) for p in parts)
    except (TypeError, ValueError):
        return None
    position = (current - start) / RTP_RATE
    duration = (end - start) / RTP_RATE
    if position < 0 or duration <= 0 or duration > 24 * 3600:
        return None
    return (min(position, duration), duration)


def format_time(seconds):
    """Secondi -> `m:ss`, oppure `h:mm:ss` per i brani lunghi."""
    try:
        total = int(max(0, float(seconds)))
    except (TypeError, ValueError):
        return "0:00"
    if total >= 3600:
        return "%d:%02d:%02d" % (total // 3600, (total % 3600) // 60, total % 60)
    return "%d:%02d" % (total // 60, total % 60)
