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
        "updated": 0.0,
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
        # Scadenza esplicita, in tempo monotono. Serve al brano di prova
        # della web UI, che deve togliersi di mezzo da solo.
        self.expires_at = 0.0

    # -------------------------------------------------------------- posizione

    def set_position(self, seconds):
        self._position = max(0.0, float(seconds))
        self._position_at = time.monotonic()

    def position(self):
        """Posizione stimata adesso: l'ultima certa, piu' il tempo trascorso."""
        if not self.playing:
            return self._position
        value = self._position + (time.monotonic() - self._position_at)
        if self.duration > 0:
            value = min(value, self.duration)
        return max(0.0, value)

    def set_playing(self, playing):
        # Congela la posizione prima di cambiare stato, altrimenti mettendo in
        # pausa si perderebbe il tempo trascorso dall'ultimo aggiornamento.
        self.set_position(self.position())
        self.playing = bool(playing)
        if playing:
            self.active = True

    def touch(self):
        self.touched = time.monotonic()
        self.updated = time.time()

    # ----------------------------------------------------------------- utilita'

    def has_content(self):
        return bool(self.title or self.artist or self.album)

    def age(self):
        return time.monotonic() - self.touched

    def snapshot(self):
        return {
            "title": self.title, "artist": self.artist, "album": self.album,
            "duration": self.duration, "position": self.position(),
            "playing": self.playing, "source": self.name,
            "client": self.client, "updated": self.updated,
        }

    def reset(self):
        self.title = self.artist = self.album = ""
        self.duration = 0.0
        self.playing = False
        self.active = False
        self.expires_at = 0.0
        self.set_position(0.0)


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

    def _candidate(self, state):
        """True se questa sorgente ha ancora diritto a essere mostrata."""
        if not state.has_content():
            return False
        if state.expires_at and time.monotonic() > state.expires_at:
            return False
        if state.playing:
            return state.age() < STALE_PLAYING
        # In pausa si resta a schermo per un po', poi si lascia il posto.
        return state.active and state.age() < self.hold_seconds()

    def snapshot(self):
        """Il brano da mostrare adesso, oppure un record vuoto."""
        with self._lock:
            best = None
            for state in self._sources.values():
                if not self._candidate(state):
                    continue
                if best is None:
                    best = state
                    continue
                # In riproduzione batte in pausa; a parita', la precedenza.
                mine = (state.playing, RANK[state.name], state.touched)
                theirs = (best.playing, RANK[best.name], best.touched)
                if mine > theirs:
                    best = state
            return best.snapshot() if best else empty_track()

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
                state.set_playing(fields["playing"])
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

        Si accettano sia i topic leggibili (`.../title`) sia quelli grezzi a
        quattro lettere (`.../prgr`), perche' la posizione nel brano viaggia
        solo sui secondi.
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
                            playing=True, active=True)
        elif leaf in ("play_start", "play_resume", "prsm", "pbeg"):
            self.update("airplay", playing=True, active=True)
        elif leaf in ("play_flush", "pfls"):
            # Flush arriva sia in pausa sia dopo un salto nel brano.
            self.update("airplay", playing=False)
        elif leaf in ("play_end", "pend", "active_end", "aend"):
            self.clear("airplay")

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
