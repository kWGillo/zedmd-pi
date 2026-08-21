"""Spotify: che cosa sta suonando, su qualunque dispositivo dell'account.

Serve a coprire un caso che AirPlay non vede. Se la musica esce da un iPhone
e passa da qui come cassa AirPlay, i metadati li abbiamo gia'. Ma se Spotify
suona in diretta su casse Connect, sul computer o su un Echo, il flusso audio
non attraversa il Raspberry: l'unico modo di sapere che cosa c'e' in
riproduzione e' chiederlo a Spotify.

Autenticazione
--------------
Si usa il flusso "Authorization Code con PKCE", che non richiede il segreto
dell'applicazione: sul Raspberry finisce solo roba che, da sola, non permette
di impersonare nessuno.

Spotify pretende che l'indirizzo di ritorno sia HTTPS oppure un indirizzo di
loopback. Un DMD headless su `http://192.168.x.x:8080` non e' ne' l'uno ne'
l'altro, quindi si registra `http://127.0.0.1:8080/api/spotify/callback` e si
autorizza dal browser di un altro computer: la pagina finale non si aprira'
(non c'e' niente in ascolto la'), ma il codice resta scritto nella barra
degli indirizzi e si incolla nella web UI. E' il modo previsto per i
dispositivi senza browser, non un aggiramento.

I token stanno in un file loro, con permessi ristretti, **fuori** dalla
configurazione: un `config.json` esportato e mandato a qualcuno non deve
portarsi dietro le chiavi dell'account.
"""

import base64
import hashlib
import json
import os
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
PLAYER_URL = "https://api.spotify.com/v1/me/player"

# Il minimo indispensabile: leggere lo stato di riproduzione. Nessun permesso
# di modifica, nessun accesso alla libreria.
SCOPE = "user-read-playback-state user-read-currently-playing"

TOKEN_PATH = os.environ.get("DMD_SPOTIFY_TOKENS", "/var/lib/dmd/spotify.json")

DEFAULT_REDIRECT = "http://127.0.0.1:8080/api/spotify/callback"

# Margine con cui si rinnova il token prima della scadenza dichiarata.
REFRESH_MARGIN = 60

_lock = threading.Lock()
_pending = {}          # state -> (code_verifier, ora di creazione)
PENDING_TTL = 900


# --------------------------------------------------------------------- token

def _read_tokens():
    try:
        with open(TOKEN_PATH) as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_tokens(data):
    directory = os.path.dirname(TOKEN_PATH)
    if directory:
        os.makedirs(directory, exist_ok=True)
    tmp = TOKEN_PATH + ".tmp"
    with open(tmp, "w") as handle:
        json.dump(data, handle, indent=2)
    # Il refresh token vale quanto la password: leggibile solo da root.
    os.chmod(tmp, 0o600)
    os.replace(tmp, TOKEN_PATH)


def connected():
    return bool(_read_tokens().get("refresh_token"))


def account():
    return _read_tokens().get("account", "")


def disconnect():
    """Dimentica l'account. Il permesso resta revocabile anche da Spotify."""
    try:
        os.remove(TOKEN_PATH)
        return True
    except OSError:
        return False


# ----------------------------------------------------------------- PKCE

def _verifier():
    return secrets.token_urlsafe(64)[:96]


def _challenge(verifier):
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _forget_old():
    now = time.time()
    for state in [s for s, (_, born) in _pending.items()
                  if now - born > PENDING_TTL]:
        _pending.pop(state, None)


def authorize_url(cfg):
    """Indirizzo da aprire nel browser per autorizzare il DMD."""
    conf = cfg.get("spotify") or {}
    client_id = str(conf.get("client_id") or "").strip()
    if not client_id:
        raise ValueError("Client ID mancante")
    redirect = str(conf.get("redirect_uri") or DEFAULT_REDIRECT).strip()

    verifier = _verifier()
    state = secrets.token_urlsafe(16)
    with _lock:
        _forget_old()
        _pending[state] = (verifier, time.time())

    query = urllib.parse.urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect,
        "code_challenge_method": "S256",
        "code_challenge": _challenge(verifier),
        "state": state,
        "scope": SCOPE,
    })
    return "%s?%s" % (AUTH_URL, query)


def extract_code(text):
    """Accetta sia il codice nudo sia l'indirizzo intero copiato dal browser.

    Restituisce (codice, state). Lo state manca se l'utente ha incollato solo
    il codice: in quel caso si usa l'unica richiesta in sospeso.
    """
    text = (text or "").strip()
    if not text:
        return ("", "")
    if "?" in text or text.startswith("http"):
        query = urllib.parse.urlparse(text).query
        values = urllib.parse.parse_qs(query)
        return (values.get("code", [""])[0], values.get("state", [""])[0])
    return (text, "")


def _post_token(payload):
    body = urllib.parse.urlencode(payload).encode("ascii")
    request = urllib.request.Request(
        TOKEN_URL, data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _store(data, keep_refresh=None):
    tokens = {
        "access_token": data.get("access_token", ""),
        "refresh_token": data.get("refresh_token") or keep_refresh or "",
        "expires_at": time.time() + float(data.get("expires_in", 3600)),
        "account": _read_tokens().get("account", ""),
    }
    _write_tokens(tokens)
    return tokens


def complete(cfg, pasted):
    """Scambia il codice dell'autorizzazione con i token. Solleva su errore."""
    conf = cfg.get("spotify") or {}
    client_id = str(conf.get("client_id") or "").strip()
    redirect = str(conf.get("redirect_uri") or DEFAULT_REDIRECT).strip()
    code, state = extract_code(pasted)
    if not code:
        raise ValueError("nessun codice trovato nel testo incollato")

    with _lock:
        _forget_old()
        if state and state in _pending:
            verifier = _pending.pop(state)[0]
        elif len(_pending) == 1:
            verifier = _pending.popitem()[1][0]
        else:
            raise ValueError("richiesta scaduta: ripeti l'autorizzazione")

    try:
        data = _post_token({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect,
            "client_id": client_id,
            "code_verifier": verifier,
        })
    except urllib.error.HTTPError as exc:
        raise ValueError(_http_reason(exc))
    if not data.get("refresh_token"):
        raise ValueError("Spotify non ha restituito un refresh token")
    tokens = _store(data)
    try:
        tokens["account"] = _me(tokens["access_token"])
        _write_tokens(tokens)
    except Exception:
        pass
    return tokens


def _http_reason(exc):
    try:
        body = json.loads(exc.read().decode("utf-8"))
        return body.get("error_description") or body.get("error") or str(exc)
    except Exception:
        return "HTTP %s" % getattr(exc, "code", "?")


def _refresh(cfg, tokens):
    client_id = str((cfg.get("spotify") or {}).get("client_id") or "").strip()
    data = _post_token({
        "grant_type": "refresh_token",
        "refresh_token": tokens["refresh_token"],
        "client_id": client_id,
    })
    return _store(data, keep_refresh=tokens["refresh_token"])


def access_token(cfg):
    """Token valido, rinnovato se sta per scadere. None se non collegati."""
    tokens = _read_tokens()
    if not tokens.get("refresh_token"):
        return None
    if tokens.get("access_token") and \
            time.time() < float(tokens.get("expires_at", 0)) - REFRESH_MARGIN:
        return tokens["access_token"]
    return _refresh(cfg, tokens).get("access_token")


# ------------------------------------------------------------------ chiamate

def _get(url, token):
    request = urllib.request.Request(
        url, headers={"Authorization": "Bearer %s" % token})
    with urllib.request.urlopen(request, timeout=12) as response:
        if response.status == 204:
            return None
        raw = response.read()
        return json.loads(raw.decode("utf-8")) if raw else None


def _me(token):
    data = _get("https://api.spotify.com/v1/me", token) or {}
    return data.get("display_name") or data.get("id") or ""


def current(cfg):
    """Stato di riproduzione, oppure None se non sta suonando nulla.

    Restituisce un dizionario nella forma che si aspetta `nowplaying`.
    """
    token = access_token(cfg)
    if not token:
        return None
    data = _get(PLAYER_URL, token)
    if not data:
        return None
    item = data.get("item") or {}
    if not item:
        return None
    artists = ", ".join(a.get("name", "") for a in item.get("artists", [])
                        if a.get("name"))
    album = (item.get("album") or {}).get("name", "")
    device = (data.get("device") or {}).get("name", "")
    return {
        "title": item.get("name", ""),
        "artist": artists,
        "album": album,
        "duration": float(item.get("duration_ms", 0)) / 1000.0,
        "position": float(data.get("progress_ms", 0)) / 1000.0,
        "playing": bool(data.get("is_playing")),
        "client": device,
    }


class SpotifyPoller:
    """Interroga Spotify a intervalli e riversa il risultato in `NowPlaying`."""

    def __init__(self, cfg, state):
        self.cfg = cfg
        self.state = state
        self._thread = None
        self._running = False
        self._wake = threading.Event()
        self.error = ""
        self.last_poll = 0.0
        self.polls = 0

    def settings(self):
        return self.cfg.get("spotify") or {}

    def interval(self):
        try:
            return max(3, min(300, int(self.settings().get("poll_interval", 8))))
        except (TypeError, ValueError):
            return 8

    def start(self):
        if self._running:
            return
        self._running = True
        self._wake.clear()
        self._thread = threading.Thread(target=self._loop, name="spotify",
                                        daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._wake.set()

    def poll_now(self):
        self._wake.set()

    def _loop(self):
        while self._running:
            if self.settings().get("enabled") and connected():
                self._once()
            self._wake.wait(self.interval())
            self._wake.clear()

    def _once(self):
        self.polls += 1
        self.last_poll = time.time()
        try:
            data = current(self.cfg)
        except urllib.error.HTTPError as exc:
            # 429 significa "troppe richieste": si rallenta invece di insistere.
            if getattr(exc, "code", 0) == 429:
                delay = 30
                try:
                    delay = max(delay, int(exc.headers.get("Retry-After", 30)))
                except (TypeError, ValueError):
                    pass
                self.error = "limite di richieste raggiunto, attendo %d s" % delay
                self._wake.wait(delay)
                return
            self.error = _http_reason(exc)
            return
        except Exception as exc:
            self.error = str(exc)
            return

        self.error = ""
        if data is None:
            self.state.clear("spotify")
            return
        self.state.update("spotify", active=True, **data)

    def status(self):
        return {
            "enabled": bool(self.settings().get("enabled")),
            "connected": connected(),
            "account": account(),
            "error": self.error,
            "last_poll": self.last_poll,
            "polls": self.polls,
            "interval": self.interval(),
            "redirect": str(self.settings().get("redirect_uri")
                            or DEFAULT_REDIRECT),
        }
