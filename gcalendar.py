# -*- coding: utf-8 -*-
"""Google Calendar: gli appuntamenti dei prossimi giorni sul pannello.

Che cosa fa e che cosa **non** fa
---------------------------------
Non fa da agenda. Non crea, non sposta, non cancella niente, non conosce i
calendari secondari, non interpreta i colori né le regole di Google: legge il
calendario principale in sola lettura e mostra quello che c'è. È una vetrina,
non un client.

La finestra è di tre giorni: un appuntamento compare tre giorni prima di
succedere e sparisce quando è passato. Sotto quella soglia il pannello
resterebbe pieno di roba di fine mese, che non è una notizia — la stessa
regola del semaforo delle scadenze, applicata agli appuntamenti.

Autenticazione
--------------
OAuth 2.0 con **Authorization Code**, autorizzato dal browser di un computer
qualunque: il DMD non ha né tastiera né schermo su cui digitare una password
Google, e non deve averne bisogno.

Si registra un client di tipo *Applicazione web* con indirizzo di ritorno
`http://localhost:8080/api/google/callback`. Se il browser che autorizza è
sullo stesso computer da cui si apre la web UI del DMD, quell'indirizzo non
porta da nessuna parte: la pagina non si apre, ma il codice resta scritto
nella barra degli indirizzi e si incolla nella pagina Calendario. È il
percorso previsto per i dispositivi senza browser, non un aggiramento. Se
invece il DMD è raggiungibile a quell'indirizzo, il ritorno funziona da solo.

Si chiede `access_type=offline` e `prompt=consent` perché serve un *refresh
token*: senza, l'autorizzazione durerebbe un'ora. E la schermata di consenso
va **pubblicata in produzione**: finché resta "in test", Google fa scadere i
refresh token dopo sette giorni e il collegamento si romperebbe ogni
settimana senza che nessuno abbia toccato niente.

I token stanno in `/var/lib/dmd/google.json`, con permessi ristretti, **fuori**
dalla configurazione: un `config.json` esportato e mandato a qualcuno non deve
portarsi dietro le chiavi di un account Google.
"""

import base64
import datetime
import hashlib
import json
import os
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
EVENTS_URL = ("https://www.googleapis.com/calendar/v3/calendars/"
              "primary/events")
PROFILO_URL = ("https://www.googleapis.com/calendar/v3/users/me/"
               "calendarList/primary")

# Sola lettura, e nient'altro. Con questo permesso l'applicazione non può
# scrivere sul calendario nemmeno per sbaglio: è una garanzia che si dà a chi
# collega il proprio account, e si legge nella schermata di consenso.
SCOPE = "https://www.googleapis.com/auth/calendar.readonly"

TOKEN_PATH = os.environ.get("DMD_GOOGLE_TOKENS", "/var/lib/dmd/google.json")

DEFAULT_REDIRECT = "http://localhost:8080/api/google/callback"

REFRESH_MARGIN = 60

MAX_TITOLO = 60
MAX_SOTTO = 64

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
    # Il refresh token vale quanto la password dell'account: solo root.
    os.chmod(tmp, 0o600)
    os.replace(tmp, TOKEN_PATH)


def connected():
    return bool(_read_tokens().get("refresh_token"))


def account():
    return _read_tokens().get("account", "")


def _post_form(url, payload):
    """POST di un modulo. Isolata perché è il punto che le prove sostituiscono."""
    body = urllib.parse.urlencode(payload).encode("ascii")
    richiesta = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(richiesta, timeout=10) as risposta:
        return 200 <= getattr(risposta, "status", 200) < 300


def revoca():
    """Dice a Google di buttare via il permesso, non solo di dimenticarlo qui.

    Cancellare il file dei token toglie l'accesso *a questo DMD*; il consenso
    resterebbe però registrato nell'account Google finché non lo si rimuove a
    mano. Una sola richiesta chiude anche quella porta.

    Torna True solo se Google ha risposto di sì. Un fallimento non e' un
    guasto — la rete puo' mancare, il token puo' essere gia' scaduto — e non
    deve impedire di cancellare il file: chi scollega vuole prima di tutto che
    il DMD smetta di leggere il suo calendario.
    """
    tokens = _read_tokens()
    gettone = tokens.get("refresh_token") or tokens.get("access_token")
    if not gettone:
        return False
    try:
        return bool(_post_form(REVOKE_URL, {"token": gettone}))
    except Exception:
        return False


def disconnect(anche_su_google=True):
    """Dimentica l'account, e per quanto possibile revoca il permesso.

    Torna `{"locale": ..., "google": ...}`: la prima dice se il file dei token
    e' stato cancellato, la seconda se Google ha confermato la revoca.
    """
    revocato = revoca() if anche_su_google else False
    svuota_cache()
    try:
        os.remove(TOKEN_PATH)
        tolto = True
    except OSError:
        tolto = False
    return {"locale": tolto, "google": revocato}


# ------------------------------------------------------------------- PKCE

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


def conf(cfg):
    return (cfg or {}).get("google") or {}


def redirect_uri(cfg):
    return str(conf(cfg).get("redirect_uri") or DEFAULT_REDIRECT).strip()


def authorize_url(cfg):
    """Indirizzo da aprire nel browser per autorizzare il DMD."""
    client_id = str(conf(cfg).get("client_id") or "").strip()
    if not client_id:
        raise ValueError("Client ID mancante")

    verifier = _verifier()
    state = secrets.token_urlsafe(16)
    with _lock:
        _forget_old()
        _pending[state] = (verifier, time.time())

    query = urllib.parse.urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri(cfg),
        "scope": SCOPE,
        "state": state,
        "code_challenge_method": "S256",
        "code_challenge": _challenge(verifier),
        # Senza queste due il refresh token non arriva, e il collegamento
        # durerebbe un'ora invece che per sempre.
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    })
    return "%s?%s" % (AUTH_URL, query)


def extract_code(text):
    """Accetta sia il codice nudo sia l'indirizzo intero copiato dal browser."""
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


def _http_reason(exc):
    try:
        body = json.loads(exc.read().decode("utf-8"))
        if isinstance(body.get("error"), dict):
            return body["error"].get("message") or str(exc)
        return body.get("error_description") or body.get("error") or str(exc)
    except Exception:
        return "HTTP %s" % getattr(exc, "code", "?")


def _store(data, keep_refresh=None, keep_account=None):
    tokens = {
        "access_token": data.get("access_token", ""),
        "refresh_token": data.get("refresh_token") or keep_refresh or "",
        "expires_at": time.time() + float(data.get("expires_in", 3600)),
        "account": keep_account if keep_account is not None
                   else _read_tokens().get("account", ""),
    }
    _write_tokens(tokens)
    return tokens


def complete(cfg, pasted):
    """Scambia il codice dell'autorizzazione con i token. Solleva su errore."""
    impostazioni = conf(cfg)
    client_id = str(impostazioni.get("client_id") or "").strip()
    client_secret = str(impostazioni.get("client_secret") or "").strip()
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

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri(cfg),
        "client_id": client_id,
        "code_verifier": verifier,
    }
    # I client di tipo "Applicazione web" hanno un segreto e Google lo
    # pretende; quelli di altro tipo no. Si manda se c'è.
    if client_secret:
        payload["client_secret"] = client_secret

    try:
        data = _post_token(payload)
    except urllib.error.HTTPError as exc:
        raise ValueError(_http_reason(exc))
    if not data.get("refresh_token"):
        raise ValueError(
            "Google non ha restituito un refresh token: controlla che il "
            "consenso sia pubblicato e riprova l'autorizzazione")
    tokens = _store(data)
    try:
        tokens["account"] = _me(tokens["access_token"])
        _write_tokens(tokens)
    except Exception:
        pass
    svuota_cache()
    return tokens


def _refresh(cfg, tokens):
    impostazioni = conf(cfg)
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": tokens["refresh_token"],
        "client_id": str(impostazioni.get("client_id") or "").strip(),
    }
    secret = str(impostazioni.get("client_secret") or "").strip()
    if secret:
        payload["client_secret"] = secret
    data = _post_token(payload)
    return _store(data, keep_refresh=tokens["refresh_token"],
                  keep_account=tokens.get("account", ""))


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
    with urllib.request.urlopen(request, timeout=15) as response:
        raw = response.read()
        return json.loads(raw.decode("utf-8")) if raw else {}


def _me(token):
    data = _get(PROFILO_URL, token) or {}
    return data.get("id") or data.get("summary") or ""


# ------------------------------------------------------------------- eventi

def _quando(campo):
    """Da `start`/`end` di Google a (datetime locale, tutto_il_giorno)."""
    if not isinstance(campo, dict):
        return (None, False)
    testo = campo.get("dateTime")
    if testo:
        try:
            # Python < 3.11 non digerisce la Z finale.
            momento = datetime.datetime.fromisoformat(
                testo.replace("Z", "+00:00"))
        except ValueError:
            return (None, False)
        if momento.tzinfo is None:
            return (momento, False)
        return (momento.astimezone(), False)
    giorno = campo.get("date")
    if giorno:
        try:
            data = datetime.date.fromisoformat(giorno)
        except ValueError:
            return (None, False)
        # Un evento di giornata comincia a mezzanotte, ora locale.
        return (datetime.datetime.combine(data, datetime.time()).astimezone(),
                True)
    return (None, False)


def scrivi_quando(momento, tutto_il_giorno=False):
    """La riga in alto a destra: giorno e mese, e l'ora se ce n'è una."""
    if momento is None:
        return ""
    if tutto_il_giorno:
        return momento.strftime("%d/%m")
    return momento.strftime("%d/%m %H:%M")


def _pulisci(testo, limite):
    testo = " ".join(str(testo or "").split())
    return testo[:limite]


def giorni_finestra(cfg):
    try:
        return max(1, min(30, int(conf(cfg).get("giorni", 3))))
    except (TypeError, ValueError):
        return 3


def _massimo(cfg):
    try:
        return max(1, min(50, int(conf(cfg).get("max_eventi", 10))))
    except (TypeError, ValueError):
        return 10


def scarica(cfg, adesso=None):
    """Gli appuntamenti della finestra, chiesti a Google adesso.

    Solleva se il collegamento non c'è o la chiamata fallisce: chi chiama
    decide se è un errore da mostrare o da ignorare.
    """
    token = access_token(cfg)
    if not token:
        raise ValueError("account Google non collegato")
    adesso = adesso or datetime.datetime.now(datetime.timezone.utc)
    if adesso.tzinfo is None:
        adesso = adesso.astimezone()
    fine = adesso + datetime.timedelta(days=giorni_finestra(cfg))
    query = urllib.parse.urlencode({
        "timeMin": adesso.isoformat(),
        "timeMax": fine.isoformat(),
        # Le ricorrenze le espande Google: al pannello arrivano occorrenze
        # con una data ciascuna, non regole da interpretare.
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": str(_massimo(cfg)),
    })
    dati = _get("%s?%s" % (EVENTS_URL, query), token) or {}

    elenco = []
    for voce in dati.get("items", []):
        if voce.get("status") == "cancelled":
            continue
        inizio, tutto = _quando(voce.get("start"))
        if inizio is None:
            continue
        elenco.append({
            "id": voce.get("id", ""),
            "titolo": _pulisci(voce.get("summary"), MAX_TITOLO),
            "inizio": inizio,
            "tutto_il_giorno": tutto,
            "quando": scrivi_quando(inizio, tutto),
            "luogo": _pulisci(voce.get("location"), MAX_SOTTO),
            "descrizione": _pulisci(voce.get("description"), MAX_SOTTO),
        })
    elenco.sort(key=lambda v: v["inizio"])
    return elenco


# --------------------------------------------------------------------- cache
#
# Il pannello ridisegna trenta volte al secondo e la pagina web si apre quando
# capita: nessuno dei due deve poter far partire una chiamata a Google. Si
# scarica ogni tanto e si legge da qui.

_cache_lock = threading.Lock()
_cache = {"ora": 0.0, "eventi": [], "errore": ""}


def _minuti(cfg):
    try:
        return max(1, min(180, int(conf(cfg).get("poll_minutes", 15))))
    except (TypeError, ValueError):
        return 15


def svuota_cache():
    with _cache_lock:
        _cache["ora"] = 0.0
        _cache["eventi"] = []
        _cache["errore"] = ""


def aggiorna(cfg):
    """Rilegge da Google e aggiorna la cache. Non solleva: scrive l'errore."""
    try:
        elenco = scarica(cfg)
    except urllib.error.HTTPError as exc:
        with _cache_lock:
            _cache["ora"] = time.time()
            _cache["errore"] = _http_reason(exc)
        return list(_cache["eventi"])
    except Exception as exc:
        with _cache_lock:
            _cache["ora"] = time.time()
            _cache["errore"] = str(exc)
        return list(_cache["eventi"])
    with _cache_lock:
        _cache["ora"] = time.time()
        _cache["eventi"] = elenco
        _cache["errore"] = ""
        return list(elenco)


def eventi(cfg, forza=False):
    """Gli appuntamenti in cache, riletti se sono vecchi. Mai un'eccezione."""
    if not connected():
        svuota_cache()
        return []
    with _cache_lock:
        eta = time.time() - _cache["ora"]
        pronti = list(_cache["eventi"])
        vecchi = eta > _minuti(cfg) * 60
    if forza or vecchi:
        return aggiorna(cfg)
    return pronti


def in_cache(adesso=None):
    """Solo quello che è già stato letto: non tocca mai la rete.

    Serve alle righe di stato. La pagina Servizi si apre quando qualcosa non
    funziona: non deve poter restare appesa quindici secondi su una chiamata
    a Google che non risponde.
    """
    adesso = adesso or datetime.datetime.now().astimezone()
    with _cache_lock:
        pronti = list(_cache["eventi"])
    return [v for v in pronti if v["inizio"] >= adesso]


def da_mostrare(cfg, adesso=None):
    """Quelli che non sono già passati. La cache può avere qualche minuto."""
    adesso = adesso or datetime.datetime.now().astimezone()
    return [v for v in eventi(cfg) if v["inizio"] >= adesso]


def errore():
    with _cache_lock:
        return _cache["errore"]


def stato(cfg):
    """Riassunto per la pagina web e per la diagnostica."""
    return {
        "connected": connected(),
        "account": account(),
        "error": errore(),
        "redirect": redirect_uri(cfg),
        "giorni": giorni_finestra(cfg),
        "client_id": bool(str(conf(cfg).get("client_id") or "").strip()),
    }
