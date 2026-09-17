"""Meteo: che tempo fa e che tempo fara', dalle coordinate gia' configurate.

Come `satelliti.py` e `pianeti.py`, questo modulo e' **solo** dati: non disegna
niente e non sa niente del pannello. Si prova da solo, con uno script.

## Da dove arrivano i numeri

Da **Open-Meteo**, e la scelta non e' casuale fra i tanti servizi possibili:

* **non vuole una chiave.** Non e' una comodita', e' una proprieta' di
  sicurezza: non c'e' nessun segreto da custodire sul Raspberry, niente da
  togliere dalla configurazione esportata, niente che possa finire in una
  schermata o in un registro. Tutti gli altri difetti di privacy di questo
  progetto sono stati risolti togliendo cose -- le coordinate dal codice, la
  password dal file esportato, i token in un file a parte con i permessi
  stretti. Qui non c'e' proprio niente da togliere;
* diecimila chiamate al giorno per uso non commerciale. Ne servono **sette**;
* e le coordinate sono gia' quelle del radar. Non se ne chiedono di nuove, e
  non ne esistono di scritte nel codice: la posizione vera vive soltanto nella
  configurazione locale, come per gli aerei e per i satelliti.

## Perche' c'e' una cache su disco

Perche' un pannello che dice "non lo so" quando cade la rete e' peggio di uno
che dice "diciotto gradi, misurati venti minuti fa". La previsione di stamattina
resta valida tutto il giorno: il dato invecchia in ore, non in secondi, e
tenerlo scritto vuol dire che dopo un riavvio il bollettino del mattino c'e'
lo stesso, senza aspettare la prima chiamata riuscita.

Quello che **non** si fa e' spacciare il vecchio per nuovo: ogni risposta porta
con se' quando e' stata presa, e chi disegna decide se dirlo.

## Gli alert

Stanno in `allerte.py`, che legge il feed di MeteoAlarm -- e come ci si sia
arrivati merita due righe, perche' e' l'esempio piu' pulito di una regola di
questo progetto.

Sulla carta le fonti possibili erano tre e tutte incerte: MeteoAlarm risultava
aver dismesso il feed RSS, il successore MeteoGate non documentava l'accesso
libero, il repository del Dipartimento della Protezione Civile si dichiarava
"in fase di caricamento". La scelta era fra indovinare e chiedere.

Si e' chiesto -- tre `curl` dal Raspberry, che ha la rete libera -- e le
risposte hanno ribaltato il quadro: il feed dato per morto risponde **200**,
l'API per posizione risponde **Not Found**. Nessuna delle due cose si poteva
sapere leggendo la documentazione.

Qui resta `allerta()`, che delega. Torna `None` quando non c'e' niente da dire,
e il pannello non scrive niente: meglio tacere che promettere.
"""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

# Import morbido, per la stessa ragione di `sgp4` nei satelliti: l'OTA non
# esegue `install.sh`, e se un giorno questo modulo avesse bisogno di qualcosa
# che manca, il meteo deve restare acceso senza le allerte invece di far
# fallire l'import dell'intera sorgente.
try:
    import allerte as _allerte
except ImportError as _exc:        # pragma: no cover - solo su copia parziale
    _allerte = None
    print("[meteo] allerte non disponibili: %s" % _exc)

BASE = "https://api.open-meteo.com/v1/forecast"

# Ci si identifica. Un User-Agent anonimo e' il primo passo per finire in un
# firewall insieme a tutti gli altri anonimi -- la stessa cortesia usata con
# CelesTrak.
AGENTE = "zedmd-pi/meteo (+https://github.com/kWGillo/zedmd-pi)"

# Ogni quanto si puo' ridomandare, al massimo. Il bollettino cambia poche volte
# al giorno e la sorgente si sveglia ogni quattro ore: mezz'ora e' gia'
# abbondante, e tiene il conto delle chiamate a poche decine al giorno su
# diecimila concesse.
ATTESA_MINIMA_MINUTI = 30

# Oltre queste ore il dato non si mostra piu' come se fosse di adesso. Non si
# butta -- serve comunque a dire "ieri era cosi'" -- ma chi disegna sa che e'
# vecchio.
VECCHIO_ORE = 3.0

CACHE = "meteo.json"


# --------------------------------------------------------- i codici del tempo

# I codici WMO, che sono lo standard con cui tutti i servizi meteo dicono "che
# tempo fa". Per ognuno: la famiglia di icona, il testo italiano e quello
# inglese.
#
# Le famiglie sono **meno** dei codici, ed e' voluto. Su un pannello alto
# sessantaquattro pixel la differenza fra pioviggine moderata e pioviggine
# intensa non si puo' disegnare, e fingere di distinguerle darebbe due icone
# uguali con due nomi diversi. I codici restano tutti, perche' il testo la
# differenza la dice.
CODICI = {
    0:  ("sereno", "Sereno", "Clear"),
    1:  ("poco_nuvoloso", "Poco nuvoloso", "Mainly clear"),
    2:  ("nuvoloso", "Parzialmente nuvoloso", "Partly cloudy"),
    3:  ("coperto", "Coperto", "Overcast"),
    45: ("nebbia", "Nebbia", "Fog"),
    48: ("nebbia", "Nebbia e brina", "Rime fog"),
    51: ("pioggia", "Pioviggine", "Light drizzle"),
    53: ("pioggia", "Pioviggine", "Drizzle"),
    55: ("pioggia", "Pioviggine intensa", "Dense drizzle"),
    56: ("pioggia", "Pioviggine gelata", "Freezing drizzle"),
    57: ("pioggia", "Pioviggine gelata intensa", "Dense freezing drizzle"),
    61: ("pioggia", "Pioggia debole", "Light rain"),
    63: ("pioggia", "Pioggia", "Rain"),
    65: ("pioggia_forte", "Pioggia forte", "Heavy rain"),
    66: ("pioggia", "Pioggia gelata", "Freezing rain"),
    67: ("pioggia_forte", "Pioggia gelata forte", "Heavy freezing rain"),
    71: ("neve", "Neve debole", "Light snow"),
    73: ("neve", "Neve", "Snow"),
    75: ("neve", "Neve forte", "Heavy snow"),
    77: ("neve", "Granuli di neve", "Snow grains"),
    80: ("rovesci", "Rovesci deboli", "Light showers"),
    81: ("rovesci", "Rovesci", "Showers"),
    82: ("rovesci", "Rovesci violenti", "Violent showers"),
    85: ("neve", "Rovesci di neve", "Snow showers"),
    86: ("neve", "Rovesci di neve forti", "Heavy snow showers"),
    95: ("temporale", "Temporale", "Thunderstorm"),
    96: ("grandine", "Temporale con grandine", "Thunderstorm with hail"),
    99: ("grandine", "Temporale con grandine forte",
         "Thunderstorm with heavy hail"),
}

SCONOSCIUTO = ("coperto", "Non disponibile", "Not available")

# I codici che meritano di essere detti prima che succedano. Non e' un'allerta
# della Protezione Civile -- quella e' un'altra cosa e ha un'altra fonte -- e'
# il buon senso di chi guarda fuori: se oggi c'e' un temporale in arrivo, il
# bollettino del mattino lo dice per primo invece di annegarlo fra massima e
# minima.
NOTEVOLI = (95, 96, 99, 82, 75, 86, 65, 67)


def descrizione(codice, lang="it"):
    """Il codice WMO in parole. Sconosciuto non e' un errore: e' «non lo so»."""
    voce = CODICI.get(codice, SCONOSCIUTO)
    return voce[1] if str(lang).lower().startswith("it") else voce[2]


def icona(codice, notte=False):
    """La famiglia di icona per un codice.

    `notte` cambia una cosa sola, ed e' l'unica che cambi davvero: con il cielo
    sereno di giorno si disegna il sole, di notte la luna. Una nuvola di notte
    resta una nuvola.
    """
    nome = CODICI.get(codice, SCONOSCIUTO)[0]
    if notte and nome in ("sereno", "poco_nuvoloso"):
        return "sereno_notte" if nome == "sereno" else "poco_nuvoloso_notte"
    return nome


def notevole(codice):
    """Vero se questo tempo merita di essere annunciato per primo."""
    return codice in NOTEVOLI


# ------------------------------------------------------------------ la rete


# I campi del blocco "adesso". Il primo elenco chiede anche **quanta acqua sta
# cadendo in questo momento**; il secondo e' quello di prima, senza.
#
# Servono due elenchi e non uno per una ragione pratica: se un domani il
# servizio smettesse di offrire `precipitation` fra i valori correnti,
# rifiuterebbe l'intera richiesta e il meteo sparirebbe dal pannello. Chiedere
# il piu' e saper ripiegare sul meno costa dieci righe e toglie un modo di
# rompersi.
CORRENTI = ("temperature_2m,relative_humidity_2m,weather_code,"
            "apparent_temperature,is_day,wind_speed_10m,precipitation")
CORRENTI_MINIME = ("temperature_2m,relative_humidity_2m,weather_code,"
                   "apparent_temperature,is_day,wind_speed_10m")


def _url(lat, lon, fuso, giorni=3, correnti=None):
    parametri = [
        ("latitude", "%.4f" % float(lat)),
        ("longitude", "%.4f" % float(lon)),
        ("current", correnti or CORRENTI),
        ("daily", "weather_code,temperature_2m_max,temperature_2m_min,"
                  "precipitation_probability_max,sunrise,sunset"),
        ("hourly", "relative_humidity_2m"),
        ("timezone", fuso or "auto"),
        ("forecast_days", str(int(giorni))),
    ]
    return BASE + "?" + urllib.parse.urlencode(parametri)


def _chiedi(url, timeout=12):
    richiesta = urllib.request.Request(url, headers={"User-Agent": AGENTE})
    with urllib.request.urlopen(richiesta, timeout=timeout) as risposta:
        return json.loads(risposta.read().decode("utf-8", "replace"))


# ------------------------------------------------------------------ la cache


def _percorso(cartella):
    return os.path.join(cartella or "/var/lib/dmd", CACHE)


def leggi_cache(cartella):
    """L'ultima previsione riuscita, o None. Non solleva mai."""
    try:
        with open(_percorso(cartella), encoding="utf-8") as f:
            dati = json.load(f)
        return dati if isinstance(dati, dict) else None
    except (OSError, ValueError):
        return None


def scrivi_cache(cartella, dati):
    percorso = _percorso(cartella)
    try:
        os.makedirs(os.path.dirname(percorso), exist_ok=True)
        # Si scrive di fianco e poi si sposta: un'interruzione a meta' scrittura
        # lascerebbe un file troncato, e un file troncato e' peggio di nessun
        # file -- al riavvio non si riconosce come rotto, si riconosce come
        # illeggibile ogni volta.
        provvisorio = percorso + ".tmp"
        with open(provvisorio, "w", encoding="utf-8") as f:
            json.dump(dati, f, ensure_ascii=False)
        os.replace(provvisorio, percorso)
        return True
    except OSError:
        return False


# --------------------------------------------------------------- la lettura


def _numero(valore, cifre=None):
    """Un numero, o None. Open-Meteo manda `null` dove non sa rispondere."""
    if valore is None:
        return None
    try:
        n = float(valore)
    except (TypeError, ValueError):
        return None
    return round(n, cifre) if cifre is not None else n


def _intero(valore):
    n = _numero(valore)
    return int(n) if n is not None else None


def _giorno(dati, indice):
    """Un giorno di previsione, letto difensivamente.

    Ogni campo puo' mancare: un servizio che cambia nome a una colonna non deve
    far sparire il bollettino, deve far sparire quella riga.
    """
    quotidiano = dati.get("daily") or {}

    def prendi(chiave):
        elenco = quotidiano.get(chiave) or []
        return elenco[indice] if indice < len(elenco) else None

    codice = _intero(prendi("weather_code"))
    return {
        "data": prendi("time"),
        "codice": codice,
        "massima": _numero(prendi("temperature_2m_max"), 1),
        "minima": _numero(prendi("temperature_2m_min"), 1),
        "pioggia_probabile": _intero(prendi("precipitation_probability_max")),
        "alba": prendi("sunrise"),
        "tramonto": prendi("sunset"),
    }


def _umidita_media(dati, indice_giorno):
    """L'umidita' media di un giorno, dalle ventiquattro ore.

    Open-Meteo non la da' gia' fatta fra i valori quotidiani, e non e' un
    problema: ci sono le ore, e la media di ventiquattro numeri e' una media di
    ventiquattro numeri. Si fa qui invece di chiedere una colonna in piu'.
    """
    orario = dati.get("hourly") or {}
    valori = orario.get("relative_humidity_2m") or []
    fetta = valori[indice_giorno * 24:(indice_giorno + 1) * 24]
    numeri = [v for v in (_numero(x) for x in fetta) if v is not None]
    if not numeri:
        return None
    return int(round(sum(numeri) / len(numeri)))


# Sotto questa soglia la pioggia e' un velo che non bagna: chiamarla pioggia
# sul pannello sarebbe un allarme falso. Sopra, si sente.
PIOGGIA_MINIMA = 0.1


def _codice_corretto(codice, pioggia):
    """Il codice del cielo, corretto da quanta acqua sta cadendo adesso.

    Nasce da una segnalazione dal campo: *dice nuvolo e sta piovendo*. Il
    codice corrente di Open-Meteo viene da un modello, e un modello che dice
    "coperto" mentre cade pioviggine non e' sbagliato di molto -- ma sul
    pannello e' sbagliato del tutto, perche' chi guarda decide se prendere
    l'ombrello.

    Il servizio pero' la pioggia in corso la da\', in millimetri, come numero a
    parte. Quando i due si contraddicono si crede al millimetro, non al
    codice: l'acqua e' una misura, il codice e\' un\'interpretazione. Al
    contrario non si corregge niente -- un codice che dice pioggia con zero
    millimetri puo\' benissimo essere una rovescio appena finito o che sta per
    cominciare, e cancellarlo toglierebbe un\'informazione vera.
    """
    if pioggia is None or pioggia < PIOGGIA_MINIMA:
        return codice
    gia_bagnato = ("pioggia", "pioggia_forte", "rovesci", "temporale", "neve",
                   "neve_forte")
    if codice is not None and CODICI.get(codice, SCONOSCIUTO)[0] in gia_bagnato:
        return codice
    # Si sceglie l'intensita' dai millimetri dell'ultima ora, con la stessa
    # scala che usa il servizio per i suoi codici.
    if pioggia >= 2.5:
        return 65          # pioggia forte
    if pioggia >= 0.5:
        return 63          # pioggia
    return 61              # pioggia debole


def interpreta(dati):
    """La risposta di Open-Meteo in una forma che il pannello sa disegnare."""
    corrente = dati.get("current") or {}
    pioggia_ora = _numero(corrente.get("precipitation"), 2)
    codice_ora = _intero(corrente.get("weather_code"))
    adesso = {
        "pioggia": pioggia_ora,
        "temperatura": _numero(corrente.get("temperature_2m"), 1),
        "percepita": _numero(corrente.get("apparent_temperature"), 1),
        "umidita": _intero(corrente.get("relative_humidity_2m")),
        "codice": _codice_corretto(codice_ora, pioggia_ora),
        "vento": _numero(corrente.get("wind_speed_10m"), 1),
        # `is_day` arriva come 1 o 0. Serve a scegliere fra sole e luna, e a
        # non disegnare un sole alle undici di sera.
        "giorno": bool(_intero(corrente.get("is_day"))),
        "quando": corrente.get("time"),
    }
    oggi = _giorno(dati, 0)
    oggi["umidita"] = _umidita_media(dati, 0)
    domani = _giorno(dati, 1)
    domani["umidita"] = _umidita_media(dati, 1)
    return {
        "adesso": adesso,
        "oggi": oggi,
        "domani": domani,
        "fuso": dati.get("timezone"),
        "preso": time.time(),
    }


# -------------------------------------------------------------- l'interfaccia


class Meteo(object):
    """Tiene la previsione, la rinfresca quando serve, e non sviene mai.

    Non e' un thread: viene chiamato da chi disegna. Le previsioni si chiedono
    poche volte al giorno, e un thread in piu' che dorme per mezz'ora alla
    volta sarebbe stato piu' codice per la stessa cosa.
    """

    def __init__(self, cfg, cartella="/var/lib/dmd"):
        self.cfg = cfg
        self.cartella = cartella
        self._dati = leggi_cache(cartella)
        self._ultimo_tentativo = 0.0
        self._errore = ""
        self.allerte = _allerte.Allerte(cfg) if _allerte else None

    # ------------------------------------------------------------ posizione

    def posizione(self):
        """Dove sta il DMD, o None. Nessuna coordinata vive nel codice.

        La decisione sta in un punto solo per tutto il progetto: dalla 7.0 la
        posizione non e' piu' una preferenza del radar ma una voce sua, perche'
        la usano in tre -- radar, satelliti e meteo.
        """
        import dmdconf
        return dmdconf.posizione(self.cfg)

    def fuso(self):
        return ((self.cfg.get("time") or {}).get("timezone")
                or "auto")

    # -------------------------------------------------------------- lettura

    def aggiorna(self, forza=False):
        """Chiede una previsione nuova, se e' il momento. Torna (fatto, motivo)."""
        dove = self.posizione()
        if dove is None:
            self._errore = "posizione non configurata"
            return False, self._errore
        adesso = time.time()
        if not forza and adesso - self._ultimo_tentativo < ATTESA_MINIMA_MINUTI * 60:
            return False, "gia' aggiornato"
        # Il tentativo si segna **prima** di provare, non dopo. Se il servizio
        # e' irraggiungibile e si segnasse solo in caso di successo, ogni giro
        # riproverebbe subito: con la rete giu' diventerebbe una richiesta
        # continua verso un servizio gratuito, che e' il modo di farsi bloccare.
        self._ultimo_tentativo = adesso
        # Due tentativi, e il secondo non e' una ripetizione: il primo chiede
        # anche la pioggia in corso, il secondo si accontenta di quello che si
        # chiedeva prima. Se un domani il servizio smettesse di offrire quel
        # campo rifiuterebbe l'intera richiesta, e un campo in piu' non deve
        # poter far sparire il meteo dal pannello.
        ultimo = None
        for correnti in (CORRENTI, CORRENTI_MINIME):
            try:
                grezzo = _chiedi(_url(dove[0], dove[1], self.fuso(),
                                      correnti=correnti))
                letto = interpreta(grezzo)
                break
            except (urllib.error.URLError, OSError, ValueError, KeyError) as exc:
                ultimo = exc
                if correnti is CORRENTI:
                    print("[meteo] pioggia in corso non disponibile: %s" % exc)
        else:
            self._errore = str(ultimo)
            return False, self._errore
        self._dati = letto
        self._errore = ""
        scrivi_cache(self.cartella, letto)
        return True, "aggiornato"

    def dati(self):
        """L'ultima previsione conosciuta, anche se vecchia. None se non c'e'."""
        return self._dati

    def eta_ore(self):
        """Da quante ore e' ferma la previsione. None se non ce n'e' nessuna."""
        if not self._dati or not self._dati.get("preso"):
            return None
        return (time.time() - float(self._dati["preso"])) / 3600.0

    def fresca(self):
        eta = self.eta_ore()
        return eta is not None and eta <= VECCHIO_ORE

    def errore(self):
        return self._errore

    # --------------------------------------------------------- l'allerta

    def aggiorna_allerte(self, forza=False):
        """Rinfresca le allerte, se il servizio le vuole. Non solleva mai."""
        if self.allerte is None:
            return False, "modulo non disponibile"
        try:
            return self.allerte.aggiorna(forza)
        except Exception as exc:          # noqa: BLE001
            return False, str(exc)

    def allerta(self):
        """L'allerta che conta per la regione scelta, o None.

        E' rimasta `None` per un'intera versione, e nel codice c'era scritto
        perche': tre fonti possibili, tutte incerte sulla carta. Poi le sonde
        dal campo hanno detto che il feed di MeteoAlarm risponde e l'API per
        posizione no -- due cose che nessuna documentazione diceva.

        Torna `None` anche adesso quando non c'e' niente da dire: nessuna
        regione scelta, nessun avviso attivo, o il feed irraggiungibile. Il
        pannello non scrive niente, che resta la regola: meglio tacere che
        promettere.
        """
        if self.allerte is None:
            return None
        try:
            return self.allerte.prima()
        except Exception as exc:          # noqa: BLE001
            print("[meteo] allerte non leggibili: %s" % exc)
            return None
