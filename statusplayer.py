# -*- coding: utf-8 -*-
"""Chi sta giocando adesso, e a cosa: nome, gioco, punteggio.

Il problema, detto com'e'
-------------------------
Batocera **non ha un punteggio**. Ogni gioco tiene il suo dentro la RAM
dell'emulatore, in un indirizzo diverso, e nessuno lo scrive da nessuna
parte. Chiedere "quanti punti ha fatto" a una macchina che fa girare Super
Mario World non e' una domanda a cui esista una risposta generale.

Ce n'e' una sola che vale per tutti i giochi e per tutte le persone:
**RetroAchievements**. Batocera lo integra gia' (Impostazioni ->
Achievements), e l'API pubblica, dato un nickname, dice quanti punti ha
quella persona e a che gioco sta giocando **adesso**. E' un punteggio
confrontabile fra un amico che gioca a Sonic e uno che gioca a Metal Slug,
che e' esattamente quello che serve a una classifica sul pannello.

Le due sorgenti
---------------
1. **RetroAchievements** (`Vigile`): il pannello chiede ogni tanto all'API
   cosa stanno facendo i nickname in elenco. Non si installa niente sulle
   macchine degli amici, funziona anche se sono dall'altra parte d'Italia.
   Vede pero' solo chi ha l'account e gioca con i cheevos accesi.
2. **L'agente su Batocera** (`da_agente`): uno script di dieci righe che
   EmulationStation esegue a ogni gioco avviato e chiuso, e che fa un POST
   al pannello. Vede **tutti** i giochi, anche quelli senza cheevos, e non
   ha bisogno di internet -- ma va copiato su ogni macchina e quella
   macchina deve vedere il Raspberry.

Le due si sommano nello stesso registro: se di una persona arrivano tutte e
due, l'agente dice il gioco (lo sa per certo) e RetroAchievements i punti.

Quello che questo modulo non fa
-------------------------------
Non disegna e non conosce il pannello: quello e' `sources/statusplayer.py`.
Qui ci sono i dati e basta, perche' un modulo che sa di rete e di API si
deve poter provare senza una scheda video -- e infatti si prova cosi'.
"""

import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://retroachievements.org/API/"

# Quanto si aspetta una risposta. Otto secondi sono lunghi per una pagina web
# e corti per una chiamata fatta da un thread in sottofondo: nessuno sta
# guardando, e un giro perso si rifa' fra un minuto.
TIMEOUT = 8.0

# Fra una richiesta e l'altra. L'API non pubblica un limite, quindi non si
# tira la corda: una richiesta al secondo e' il ritmo di una persona che
# guarda i profili, e dodici amici sono dodici secondi ogni giro.
PAUSA = 1.1

# Quanti amici al massimo. Non e' un limite tecnico: e' il numero oltre il
# quale un giro comincia a durare piu' dell'intervallo, e il pannello
# racconterebbe cose vecchie credendole fresche.
MAX_AMICI = 12

INTERVALLO_MINIMO = 30
INTERVALLO_MASSIMO = 3600

# Dopo quanti minuti di silenzio una persona non e' piu' "in gioco". Chi
# spegne la macchina non manda nessun avviso: sparisce, e basta.
VIVO_DEFAULT = 10

DATI = os.environ.get("DMD_DATA", "/var/lib/dmd")

# I titoli dei giochi, per numero. Un titolo non cambia mai, quindi chiederlo
# una volta sola non e' un'ottimizzazione: e' non fare una domanda inutile a
# un servizio gratuito, ogni minuto, per sempre.
CACHE_GIOCHI = os.path.join(DATI, "ra-giochi.json")

# Un nickname di RetroAchievements: lettere, cifre, trattino e underscore.
# Serve a non infilare qualunque cosa dentro una query string.
NICK = re.compile(r"^[A-Za-z0-9_.-]{1,32}$")

MAX_TESTO = 80


def pulisci(testo, quanto=MAX_TESTO):
    """Una riga sola, senza spazi doppi, lunga al massimo `quanto`."""
    testo = re.sub(r"\s+", " ", str(testo or "")).strip()
    return testo[:quanto]


def nick_valido(nick):
    return bool(NICK.match((nick or "").strip()))


# --------------------------------------------------------------- l'API di RA

class Errore(Exception):
    """Qualcosa non ha funzionato, e si sa dirlo in italiano."""


class Api(object):
    """Le due domande che si fanno a RetroAchievements, e niente altro.

    `profilo` dice punti e ultimo gioco di una persona; `gioco` traduce il
    numero del gioco in un titolo. Sono due endpoint su una dozzina: chi
    aggiunge il terzo si fermi a chiedersi se serve davvero al pannello.
    """

    def __init__(self, utente="", chiave="", apri=None):
        self.utente = (utente or "").strip()
        self.chiave = (chiave or "").strip()
        # Chi apre la connessione. Sostituibile: le prove non chiamano
        # RetroAchievements, e non devono nemmeno provarci.
        self._apri = apri or self._apri_davvero
        self._giochi = _leggi_cache()
        self.richieste = 0

    def pronto(self):
        return bool(self.chiave)

    @staticmethod
    def _apri_davvero(url):
        richiesta = urllib.request.Request(
            url, headers={"User-Agent": "zedmd-pi status player"})
        with urllib.request.urlopen(richiesta, timeout=TIMEOUT) as risposta:
            return risposta.read().decode("utf8", "replace")

    def _chiedi(self, endpoint, **parametri):
        if not self.pronto():
            raise Errore("manca la chiave API")
        parametri["y"] = self.chiave
        if self.utente:
            parametri["z"] = self.utente
        url = BASE + endpoint + "?" + urllib.parse.urlencode(parametri)
        self.richieste += 1
        try:
            grezzo = self._apri(url)
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise Errore("chiave API rifiutata")
            raise Errore("HTTP %s" % exc.code)
        except Exception as exc:
            raise Errore(str(exc))
        try:
            dati = json.loads(grezzo)
        except ValueError:
            raise Errore("risposta illeggibile")
        if isinstance(dati, dict) and dati.get("Error"):
            raise Errore(pulisci(dati["Error"], 60))
        return dati

    def profilo(self, nick):
        """Punti, ultimo gioco e presenza di una persona.

        Si usa `API_GetUserProfile`, non `API_GetUserSummary`: il secondo dice
        di piu' ma la documentazione stessa lo dichiara lento e sprecone, e
        qui servono quattro campi.
        """
        if not nick_valido(nick):
            raise Errore("nickname non valido")
        dati = self._chiedi("API_GetUserProfile.php", u=nick.strip())
        if not isinstance(dati, dict) or not dati.get("User"):
            raise Errore("utente non trovato")
        return {
            "nick": pulisci(dati.get("User"), 32),
            "punti": _numero(dati.get("TotalPoints")),
            "punti_hardcore": _numero(dati.get("TotalTruePoints")),
            "gioco_id": _numero(dati.get("LastGameID")),
            "presenza": pulisci(dati.get("RichPresenceMsg"), 60),
            "quando": _quando(dati.get("RichPresenceMsgDate")
                              or dati.get("LastActivity")),
        }

    def gioco(self, ident):
        """Titolo e console di un gioco, per numero. Una volta sola."""
        ident = _numero(ident)
        if ident <= 0:
            return {"titolo": "", "console": ""}
        chiave = str(ident)
        if chiave in self._giochi:
            return self._giochi[chiave]
        dati = self._chiedi("API_GetGame.php", i=ident)
        voce = {"titolo": pulisci((dati or {}).get("Title"), 40),
                "console": pulisci((dati or {}).get("ConsoleName"), 20)}
        if voce["titolo"]:
            self._giochi[chiave] = voce
            _scrivi_cache(self._giochi)
        return voce


def _numero(valore):
    try:
        return int(float(valore))
    except (TypeError, ValueError):
        return 0


def _quando(testo):
    """Un orario dell'API in secondi, o 0 se non si capisce.

    L'API scrive `2026-09-27 11:40:12`, in UTC. Non si fa finta di niente
    quando manca: zero vuol dire "non lo so", e chi legge decide.
    """
    testo = (testo or "").strip()
    if not testo:
        return 0.0
    for formato in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            import calendar
            return calendar.timegm(time.strptime(testo[:19], formato))
        except ValueError:
            continue
    return 0.0


def _leggi_cache():
    try:
        with open(CACHE_GIOCHI, encoding="utf8") as handle:
            dati = json.load(handle)
        return dati if isinstance(dati, dict) else {}
    except Exception:
        return {}


def _scrivi_cache(giochi):
    try:
        os.makedirs(os.path.dirname(CACHE_GIOCHI), exist_ok=True)
        provvisorio = CACHE_GIOCHI + ".tmp"
        with open(provvisorio, "w", encoding="utf8") as handle:
            json.dump(giochi, handle)
        os.replace(provvisorio, CACHE_GIOCHI)
    except Exception:
        pass


# ------------------------------------------------------------- il registro

class Registro(object):
    """Chi sta giocando, da dove lo sappiamo, e da quanto.

    Una voce per persona, non per sorgente: se di Gillo arrivano sia
    l'agente sia RetroAchievements, resta una riga sola -- il gioco lo dice
    l'agente, che lo sa per certo, i punti RetroAchievements, che e' l'unico
    a saperli.
    """

    def __init__(self):
        self._lucchetto = threading.Lock()
        self._voci = {}
        self._eventi = []
        self.errore = ""
        self.ultimo_giro = 0.0

    # ---------------------------------------------------------- scrittura

    def da_ra(self, nome, profilo, gioco):
        """Quello che ha detto RetroAchievements di una persona."""
        titolo = (gioco or {}).get("titolo", "")
        console = (gioco or {}).get("console", "")
        presenza = profilo.get("presenza", "")
        # "Playing Super Mario World" non aggiunge niente al titolo, che gia'
        # c'e'. Una presenza vera -- "World 4-2, 3 lives" -- invece si'.
        if presenza.lower().startswith("playing"):
            presenza = ""
        return self._scrivi(
            nome,
            gioco=titolo,
            sistema=console,
            punti=profilo.get("punti", 0),
            # Zero vuol dire "l'API non l'ha detto", e chi scrive nel
            # registro sa cosa farne. Metterci l'ora di adesso qui sarebbe
            # inventare un dato e perdere per sempre la differenza.
            quando=profilo.get("quando", 0.0),
            fonte="ra",
            presenza=presenza,
            nick=profilo.get("nick", ""),
        )

    def da_agente(self, nome, evento, sistema="", gioco=""):
        """Quello che ha detto lo script sulla Batocera di una persona."""
        if evento == "fine":
            with self._lucchetto:
                voce = self._voci.get(_chiave(nome))
                if voce is not None and voce.get("fonte") == "agente":
                    voce["gioco"] = ""
                    voce["quando"] = time.time()
                    voce["finito"] = True
            return False
        return self._scrivi(nome, gioco=pulisci(gioco, 40),
                            sistema=pulisci(sistema, 20),
                            quando=time.time(), fonte="agente")

    def _scrivi(self, nome, gioco="", sistema="", punti=None, quando=0.0,
                fonte="", presenza="", nick=""):
        """Aggiorna una persona. Torna True se ha **cambiato gioco**.

        Il valore che torna e' quello che fa scattare la notifica sul
        pannello: non "e' arrivato un aggiornamento" -- ne arrivano ogni
        minuto -- ma "ha cominciato qualcosa di nuovo".
        """
        nome = pulisci(nome, 20).upper()
        if not nome:
            return False
        chiave = _chiave(nome)
        adesso = time.time()
        with self._lucchetto:
            voce = self._voci.get(chiave)
            if voce is None:
                voce = {"nome": nome, "gioco": "", "sistema": "", "punti": 0,
                        "punti_inizio": 0, "presenza": "", "nick": "",
                        "fonte": "", "quando": 0.0, "finito": False}
                self._voci[chiave] = voce
            prima = voce["gioco"]
            cambiato_qualcosa = bool(
                (gioco and gioco != voce["gioco"])
                or (presenza and presenza != voce["presenza"])
                or (punti and punti != voce["punti"]))
            # L'agente sa il gioco per certo: se c'e' lui, il titolo e' suo.
            if gioco and (fonte == "agente" or voce.get("fonte") != "agente"
                          or adesso - voce["quando"] > 300):
                voce["gioco"] = gioco
                voce["sistema"] = sistema or voce["sistema"]
                voce["fonte"] = fonte
            if punti is not None and punti > 0:
                if voce["punti"] == 0 or gioco != prima:
                    voce["punti_inizio"] = punti
                voce["punti"] = punti
            if presenza:
                voce["presenza"] = presenza
            if nick:
                voce["nick"] = nick
            # Quando l'abbiamo visto. Se l'API dice l'ora, e' quella: un
            # profilo la cui presenza risale a due ore fa **non sta
            # giocando**, e prendere l'ora di adesso vorrebbe dire far
            # comparire sul pannello uno che ha spento ieri.
            #
            # Se non la dice, vale l'ora nostra ma solo se qualcosa e'
            # cambiato -- il gioco, la presenza, i punti. Altrimenti si
            # lascia l'ora di prima: una risposta identica ripetuta ogni due
            # minuti non e' la prova che qualcuno stia giocando, e' la prova
            # che il profilo e' fermo.
            if quando > 0:
                voce["quando"] = max(voce["quando"], quando)
            elif cambiato_qualcosa or not voce["quando"]:
                voce["quando"] = adesso
            voce["finito"] = False
            cambiato = bool(voce["gioco"]) and voce["gioco"] != prima
            if cambiato:
                voce["punti_inizio"] = voce["punti"]
                self._eventi.append(dict(voce))
                del self._eventi[:-10]
        return cambiato

    def segna_errore(self, testo):
        with self._lucchetto:
            self.errore = pulisci(testo, 60)

    def segna_giro(self):
        with self._lucchetto:
            self.ultimo_giro = time.time()
            self.errore = ""

    # ------------------------------------------------------------ lettura

    def in_gioco(self, minuti=VIVO_DEFAULT, adesso=None):
        """Chi sta giocando adesso, dal piu' recente. Lista di copie."""
        adesso = adesso if adesso is not None else time.time()
        limite = adesso - max(1, int(minuti)) * 60
        with self._lucchetto:
            vivi = [dict(v) for v in self._voci.values()
                    if v["gioco"] and not v["finito"] and v["quando"] >= limite]
        vivi.sort(key=lambda v: (-v["quando"], v["nome"]))
        for voce in vivi:
            voce["guadagnati"] = max(0, voce["punti"] - voce["punti_inizio"])
        return vivi

    def eventi(self):
        """Le partenze non ancora mostrate. Chi le legge se le prende."""
        with self._lucchetto:
            fuori, self._eventi = self._eventi, []
        return fuori

    def dimentica(self, nome=None):
        with self._lucchetto:
            if nome is None:
                self._voci.clear()
            else:
                self._voci.pop(_chiave(nome), None)

    def stato(self, minuti=VIVO_DEFAULT):
        """Quello che serve alla pagina web."""
        return {"in_gioco": self.in_gioco(minuti),
                "errore": self.errore,
                "ultimo_giro": self.ultimo_giro}


def _chiave(nome):
    return pulisci(nome, 20).upper()


# ---------------------------------------------------------------- il giro

class Vigile(object):
    """Il giro delle richieste a RetroAchievements, in un thread suo.

    Un giro per volta, un amico per secondo, e fra un giro e l'altro
    l'intervallo scelto. Se l'API non risponde non si insiste: si scrive il
    motivo, che finisce nella pagina, e si riprova al giro dopo.
    """

    def __init__(self, cfg, registro, api=None):
        self.cfg = cfg
        self.registro = registro
        self._api = api
        self._chiave_api = None
        self._stop = threading.Event()
        self._sveglia = threading.Event()
        self._thread = None
        self.giri = 0

    # -------------------------------------------------------- ciclo di vita

    def avvia(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._ciclo, name="statusplayer",
                                        daemon=True)
        self._thread.start()

    def ferma(self):
        self._stop.set()
        self._sveglia.set()

    def adesso(self):
        """Fai un giro subito, senza aspettare l'intervallo."""
        self._sveglia.set()

    # ------------------------------------------------------------ il lavoro

    def conf(self):
        return (self.cfg or {}).get("status_player") or {}

    def api(self):
        """L'API con la chiave di adesso. Cambiata la chiave, cambia l'API."""
        conf = self.conf()
        chiave = (conf.get("utente_ra", ""), conf.get("chiave_ra", ""))
        # Un'API gia' pronta passata da chi costruisce il Vigile (le prove)
        # resta quella che e': non si va a riaprire una connessione vera
        # perche' nella configurazione c'e' scritta un'altra chiave.
        if self._api is not None and self._chiave_api is None:
            return self._api
        if self._api is None or self._chiave_api != chiave:
            self._api = Api(chiave[0], chiave[1])
            self._chiave_api = chiave
        return self._api

    def amici(self):
        """Gli amici con un nickname RetroAchievements, al massimo MAX_AMICI."""
        fuori = []
        for voce in (self.conf().get("amici") or [])[:MAX_AMICI]:
            nick = (voce.get("ra") or "").strip()
            nome = pulisci(voce.get("nome") or nick, 20).upper()
            if nome and nick_valido(nick):
                fuori.append({"nome": nome, "ra": nick})
        return fuori

    def giro(self, pausa=True):
        """Un giro solo: torna quanti amici ha aggiornato."""
        api = self.api()
        if not api.pronto():
            self.registro.segna_errore("manca la chiave API")
            return 0
        fatti = 0
        guasto = ""
        for indice, amico in enumerate(self.amici()):
            if self._stop.is_set():
                break
            if pausa and indice:
                self._stop.wait(PAUSA)
            try:
                profilo = api.profilo(amico["ra"])
                gioco = api.gioco(profilo["gioco_id"])
                self.registro.da_ra(amico["nome"], profilo, gioco)
                fatti += 1
            except Errore as exc:
                guasto = "%s: %s" % (amico["nome"], exc)
            except Exception as exc:                    # pragma: no cover
                guasto = "%s: %s" % (amico["nome"], exc)
        self.giri += 1
        if guasto:
            self.registro.segna_errore(guasto)
        else:
            self.registro.segna_giro()
        return fatti

    def _ciclo(self):
        while not self._stop.is_set():
            try:
                self.giro()
            except Exception as exc:                    # pragma: no cover
                print("[statusplayer] giro non riuscito: %s" % exc)
            attesa = self.intervallo()
            self._sveglia.wait(attesa)
            self._sveglia.clear()

    def intervallo(self):
        try:
            valore = int(self.conf().get("intervallo", 120))
        except (TypeError, ValueError):
            valore = 120
        return max(INTERVALLO_MINIMO, min(INTERVALLO_MASSIMO, valore))
