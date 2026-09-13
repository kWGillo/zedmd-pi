"""Le allerte meteo di MeteoAlarm, lette dal feed che risponde davvero.

## Come siamo arrivati qui

La prima versione di questo progetto non aveva le allerte, e nel codice c'era
scritto perche': MeteoAlarm risultava aver dismesso il feed RSS, il successore
MeteoGate non documentava l'accesso libero, e il repository del Dipartimento
della Protezione Civile si dichiarava "in fase di caricamento". Tre strade,
tutte incerte, e una regola: **un'allerta che non suona mai e' il difetto
peggiore che questo progetto possa avere**, quindi meglio tacere che spedire
sulla fiducia.

Poi sono arrivate le prove dal campo, e hanno ribaltato il quadro:

* il feed legacy per l'Italia risponde **200**. La documentazione di terze
  parti che lo dava per morto aveva torto;
* l'API EDR interrogata per posizione risponde **Not Found**: quella strada e'
  chiusa davvero.

Non e' un dettaglio di cronaca, e' il motivo per cui questo modulo esiste in
questa forma e non in un'altra: nessuna delle due cose si poteva sapere
leggendo la documentazione.

## Che cosa arriva

Un feed Atom con dentro **CAP 1.2**, lo standard con cui le protezioni civili
di mezzo mondo pubblicano le allerte. Ogni voce porta:

* `EMMA_ID` -- il codice della zona (`IT018`), e il nome in chiaro accanto
  (`Sicilia`);
* il tipo di evento e il colore, nel titolo (`Yellow Thunderstorm Warning`);
* la **gravita'** (`Moderate`, `Severe`, `Extreme`), che e' il dato su cui si
  decide, perche' e' normalizzato mentre il titolo e' una frase;
* quando comincia (`onset`) e quando scade (`expires`).

## Perche' si sceglie la regione a mano

Il feed copre l'Italia intera e divide per regione. Per sapere quale sia la
tua servirebbe trasformare le coordinate in una regione, cioe' portarsi dietro
i confini amministrativi -- megabyte di poligoni per rispondere a una domanda
che tu sai gia'.

Quindi la regione si sceglie da una tendina, una volta. E il confronto si fa
sul **nome**, non sul codice: `EMMA_ID` andrebbe benissimo ma richiederebbe
una tabella di venti codici scritta a memoria da qualcuno che non li ha mai
visti tutti, e sbagliarne uno vorrebbe dire che la tua regione non suona mai.
I nomi invece arrivano dal feed stesso.

Il confronto e' tollerante -- senza accenti, senza maiuscole, senza apostrofi
-- perche' `Valle d'Aosta`, `Valle d’Aosta` e `valle daosta` sono la stessa
cosa per chiunque tranne che per un confronto fra stringhe.
"""

import re
import time
import unicodedata
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

BASE = "https://feeds.meteoalarm.org/feeds/meteoalarm-legacy-atom-%s"

AGENTE = "zedmd-pi/allerte (+https://github.com/kWGillo/zedmd-pi)"

# Ogni quanto si puo' ridomandare. Le allerte cambiano poche volte al giorno e
# il feed e' un servizio pubblico gratuito: mezz'ora e' educato e abbondante.
ATTESA_MINIMA_MINUTI = 30

# Le venti regioni italiane come le scrive MeteoAlarm, per la tendina della
# pagina web. Non e' una tabella di codici -- quella sarebbe da indovinare --
# sono i nomi, che si leggono nel feed e si riconoscono a occhio.
#
# Trentino-Alto Adige non c'e' come tale: MeteoAlarm segue la divisione reale
# della protezione civile, che tratta le due province autonome separatamente.
REGIONI_IT = (
    "Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna",
    "Friuli Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche",
    "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana",
    "Trentino", "Umbria", "Valle d'Aosta", "Veneto",
)

# Gravita' CAP -> livello nostro. E' la scala dei colori di MeteoAlarm, che e'
# la stessa della Protezione Civile: giallo, arancione, rosso.
LIVELLI = {
    "minor": ("verde", 1),
    "moderate": ("giallo", 2),
    "severe": ("arancione", 3),
    "extreme": ("rosso", 4),
}

COLORI = {
    "verde": (0x30, 0xC0, 0x50),
    "giallo": (0xF0, 0xD0, 0x20),
    "arancione": (0xFF, 0x90, 0x10),
    "rosso": (0xFF, 0x30, 0x30),
}

# «Allerta» in italiano e' femminile, e "ALLERTA GIALLO" scritto sul pannello
# e' una cosa che nessuno puo' leggere senza inciampare. I livelli restano
# maschili dove sono chiavi -- in configurazione, nei topic MQTT, nelle
# automazioni -- perche' li' contano l'invarianza e non la grammatica; qui c'e'
# la forma da mostrare a una persona.
FEMMINILE = {
    "verde": "verde",
    "giallo": "gialla",
    "arancione": "arancione",
    "rosso": "rossa",
}


def livello_scritto(livello, lang="it"):
    """Il nome del livello come si scrive per chi legge."""
    if not str(lang).lower().startswith("it"):
        return str(livello or "")
    return FEMMINILE.get(livello, str(livello or ""))

# I tipi di evento come li scrive MeteoAlarm, in italiano. Chi non e' in
# tabella tiene il suo nome inglese: meglio una parola in inglese che una
# traduzione inventata su un avviso di pericolo.
EVENTI = {
    "thunderstorm": ("Temporali", "Thunderstorm"),
    "rain": ("Pioggia", "Rain"),
    "rain-flood": ("Pioggia e piene", "Rain and flooding"),
    "flood": ("Piene", "Flooding"),
    "wind": ("Vento", "Wind"),
    "snow": ("Neve", "Snow"),
    "snow-ice": ("Neve e ghiaccio", "Snow and ice"),
    "ice": ("Ghiaccio", "Ice"),
    "low-temperature": ("Freddo", "Low temperature"),
    "high-temperature": ("Caldo", "High temperature"),
    "extreme-high-temperature": ("Caldo estremo", "Extreme heat"),
    "extreme-low-temperature": ("Freddo estremo", "Extreme cold"),
    "fog": ("Nebbia", "Fog"),
    "coastal-event": ("Mareggiate", "Coastal event"),
    "coastalevent": ("Mareggiate", "Coastal event"),
    "forest-fire": ("Incendi boschivi", "Forest fire"),
    "forestfire": ("Incendi boschivi", "Forest fire"),
    "avalanches": ("Valanghe", "Avalanches"),
    "avalanche": ("Valanghe", "Avalanches"),
}

COLORI_TITOLO = ("green", "yellow", "orange", "red")


# ------------------------------------------------------------------ confronti


def normalizza(testo):
    """Un nome ridotto a cio' che conta per confrontarlo.

    Senza accenti, senza maiuscole, senza apostrofi e senza doppi spazi.
    `Valle d'Aosta`, `Valle d’Aosta` e `VALLE DAOSTA` diventano la stessa
    cosa -- come sono la stessa cosa per chiunque li legga.
    """
    grezzo = unicodedata.normalize("NFKD", str(testo or ""))
    senza_accenti = "".join(c for c in grezzo if not unicodedata.combining(c))
    # Gli apostrofi si **tolgono**, non si trasformano in spazi. Sembra un
    # dettaglio e non lo e': con lo spazio, `Valle d'Aosta` diventa
    # "valle d aosta" e chi scrive "valle daosta" non la trova piu'. Con la
    # rimozione diventano tutti "valle daosta", che e' come lo direbbe
    # chiunque. Trovato da una prova, non da un ragionamento.
    senza_apostrofi = re.sub(r"['‘’ʼ`]", "",
                             senza_accenti.lower())
    solo_utile = re.sub(r"[^a-z0-9]+", " ", senza_apostrofi)
    return solo_utile.strip()


def _locale(elemento):
    """Il nome del tag senza lo spazio dei nomi.

    Serve perche' dentro `cap:geocode` i figli `valueName` e `value` **non**
    hanno prefisso, quindi ereditano lo spazio dei nomi predefinito del feed,
    che e' Atom e non CAP. Cercarli come elementi CAP non li troverebbe, e non
    darebbe errore: darebbe zero risultati, che e' il modo peggiore di
    sbagliare.
    """
    tag = elemento.tag
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _figlio(elemento, nome):
    for figlio in elemento:
        if _locale(figlio) == nome:
            return figlio
    return None


def _testo(elemento, nome, predefinito=""):
    figlio = _figlio(elemento, nome)
    if figlio is None or figlio.text is None:
        return predefinito
    return figlio.text.strip()


def _quando(testo):
    """Un istante ISO con il fuso -> datetime. None se non si capisce."""
    if not testo:
        return None
    pulito = testo.strip().replace("Z", "+00:00")
    try:
        istante = datetime.fromisoformat(pulito)
    except ValueError:
        return None
    if istante.tzinfo is None:
        istante = istante.replace(tzinfo=timezone.utc)
    return istante


# -------------------------------------------------------------------- lettura


def _tipo_evento(titolo, evento):
    """Dal testo dell'evento alla chiave in tabella.

    MeteoAlarm scrive `Yellow Thunderstorm Warning`: la prima parola e' il
    colore, l'ultima e' "Warning", in mezzo c'e' il tipo. Si toglie il contorno
    e si normalizza quello che resta.
    """
    testo = normalizza(evento or titolo)
    parole = [p for p in testo.split()
              if p not in COLORI_TITOLO and p not in ("warning", "warnings",
                                                      "issued", "for")]
    if not parole:
        return ""
    return "-".join(parole)


def descrizione_evento(voce, lang="it"):
    """Il tipo di evento in parole, nella lingua chiesta."""
    chiave = voce.get("tipo") or ""
    nomi = EVENTI.get(chiave)
    if not nomi:
        # Non in tabella: si restituisce quello che ha scritto la fonte, con
        # le maiuscole a posto. Su un avviso di pericolo una traduzione
        # inventata e' peggio di una parola in inglese.
        grezzo = (voce.get("evento") or "").strip()
        for colore in COLORI_TITOLO:
            grezzo = re.sub(colore, "", grezzo, flags=re.IGNORECASE)
        grezzo = re.sub(r"\bwarning[s]?\b", "", grezzo, flags=re.IGNORECASE)
        return " ".join(grezzo.split()) or "Allerta"
    return nomi[0] if str(lang).lower().startswith("it") else nomi[1]


def analizza(xml_testo):
    """Il feed in una lista di avvisi. Non solleva mai per colpa del contenuto.

    Un feed malformato -- o cambiato -- da' una lista piu' corta, non
    un'eccezione: il giorno in cui la fonte aggiunge un campo o ne rinomina
    uno, il DMD deve mostrare meno allerte, non spegnersi.
    """
    try:
        radice = ET.fromstring(xml_testo)
    except ET.ParseError:
        return []

    fuori = []
    for elemento in radice:
        if _locale(elemento) != "entry":
            continue
        try:
            voce = _voce(elemento)
        except Exception:                 # noqa: BLE001
            continue
        if voce:
            fuori.append(voce)
    return fuori


def _voce(elemento):
    stato = (_testo(elemento, "status") or "Actual").lower()
    # `Test` ed `Exercise` esistono apposta perche' chi li riceve non li mostri.
    if stato not in ("actual", ""):
        return None
    tipo_messaggio = (_testo(elemento, "message_type") or "").lower()
    if tipo_messaggio == "cancel":
        return None

    zona = _testo(elemento, "areaDesc")
    codice = ""
    for figlio in elemento:
        if _locale(figlio) != "geocode":
            continue
        if _testo(figlio, "valueName") == "EMMA_ID":
            codice = _testo(figlio, "value")
            break

    evento = _testo(elemento, "event")
    titolo = _testo(elemento, "title")
    gravita = (_testo(elemento, "severity") or "").lower()
    livello, peso = LIVELLI.get(gravita, ("giallo", 2))

    return {
        "zona": zona,
        "codice": codice,
        "evento": evento or titolo,
        "tipo": _tipo_evento(titolo, evento),
        "gravita": gravita,
        "livello": livello,
        "peso": peso,
        "inizio": _testo(elemento, "onset") or _testo(elemento, "effective"),
        "fine": _testo(elemento, "expires"),
        "certezza": _testo(elemento, "certainty"),
        "urgenza": _testo(elemento, "urgency"),
        "identificativo": _testo(elemento, "identifier"),
    }


# ------------------------------------------------------------------- filtri


def per_zona(voci, regione):
    """Solo gli avvisi della regione scelta. Senza regione, nessun avviso.

    Nessuna regione vuol dire nessun avviso e **non** tutti: il feed copre
    l'Italia intera, e mostrare le allerte della Sicilia a chi sta in Piemonte
    non e' un'approssimazione, e' un allarme falso.
    """
    voluta = normalizza(regione)
    if not voluta:
        return []
    fuori = []
    for voce in voci:
        zona = normalizza(voce.get("zona"))
        codice = normalizza(voce.get("codice"))
        if zona == voluta or codice == voluta:
            fuori.append(voce)
            continue
        # Tolleranza in un verso solo, e stretta: la regione scelta deve essere
        # l'**inizio** del nome della zona. Cosi' "Piemonte" trova anche
        # "Piemonte e Valle d'Aosta", che e' il caso vero per cui questa riga
        # esiste.
        #
        # La prima versione accettava qualunque parola contenuta nel nome, e
        # una prova l'ha bocciata subito: con quella regola "Aosta" suonava per
        # "Valle d'Aosta", cioe' una regione riceveva gli allarmi di un'altra.
        # In un impianto di avvisi e' il difetto peggiore possibile.
        if voluta and zona and zona.startswith(voluta + " "):
            fuori.append(voce)
    return fuori


def attive(voci, adesso=None, preavviso_ore=12):
    """Gli avvisi in corso, piu' quelli che cominceranno entro poche ore.

    Il preavviso c'e' perche' un'allerta serve **prima**: sapere alle otto di
    sera che domattina alle otto ci sara' un temporale e' utile, saperlo
    mentre grandina non lo e'. Scaduta, sparisce: un avviso vecchio sul
    pannello e' peggio di nessun avviso, perche' insegna a non fidarsi.
    """
    adesso = adesso or datetime.now(timezone.utc)
    fuori = []
    for voce in voci:
        fine = _quando(voce.get("fine"))
        if fine is not None and fine <= adesso:
            continue
        inizio = _quando(voce.get("inizio"))
        if inizio is not None:
            mancano = (inizio - adesso).total_seconds() / 3600.0
            if mancano > preavviso_ore:
                continue
            voce = dict(voce, in_corso=mancano <= 0, fra_ore=max(0.0, mancano))
        else:
            voce = dict(voce, in_corso=True, fra_ore=0.0)
        fuori.append(voce)
    # La piu' grave per prima, e a parita' quella che comincia prima: sul
    # pannello ce ne sta una sola, e dev'essere quella che conta di piu'.
    fuori.sort(key=lambda v: (-v["peso"], v.get("fra_ore", 0.0)))
    return fuori


# -------------------------------------------------------------------- la rete


def _chiedi(url, timeout=15):
    richiesta = urllib.request.Request(url, headers={"User-Agent": AGENTE})
    with urllib.request.urlopen(richiesta, timeout=timeout) as risposta:
        return risposta.read().decode("utf-8", "replace")


class Allerte(object):
    """Tiene le allerte della regione scelta e le rinfresca con misura."""

    def __init__(self, cfg):
        self.cfg = cfg
        self._voci = []
        self._ultimo_tentativo = 0.0
        self._ultimo_successo = 0.0
        self._errore = ""

    def conf(self):
        return self.cfg.get("meteo") or {}

    def regione(self):
        return (self.conf().get("regione") or "").strip()

    def paese(self):
        return (self.conf().get("paese") or "italy").strip().lower()

    def accese(self):
        return bool(self.conf().get("allerte", True)) and bool(self.regione())

    def aggiorna(self, forza=False):
        """Scarica il feed, se e' il momento. Torna (fatto, motivo)."""
        if not self.accese():
            return False, "nessuna regione scelta"
        adesso = time.time()
        if not forza and adesso - self._ultimo_tentativo < ATTESA_MINIMA_MINUTI * 60:
            return False, "gia' aggiornato"
        # Il tentativo si segna prima di provare, come per il meteo: con la
        # rete giu', segnarlo solo in caso di successo trasformerebbe ogni giro
        # in una richiesta nuova verso un servizio gratuito.
        self._ultimo_tentativo = adesso
        try:
            testo = _chiedi(BASE % self.paese())
        except (urllib.error.URLError, OSError, ValueError) as exc:
            self._errore = str(exc)
            return False, self._errore
        self._voci = analizza(testo)
        self._ultimo_successo = adesso
        self._errore = ""
        return True, "aggiornato"

    def elenco(self, adesso=None):
        """Gli avvisi attivi per la regione scelta, dal piu' grave."""
        if not self.accese():
            return []
        return attive(per_zona(self._voci, self.regione()), adesso)

    def prima(self, adesso=None):
        """L'avviso che conta, o None. E' quello che finisce sul pannello."""
        elenco = self.elenco(adesso)
        return elenco[0] if elenco else None

    def zone_viste(self):
        """I nomi di zona presenti nel feed adesso.

        Servono alla pagina web: alla tendina delle venti regioni si
        aggiungono quelle che il feed sta davvero nominando, cosi' se
        MeteoAlarm scrive un nome diverso da quello che ci aspettiamo si vede
        invece di doverlo indovinare.
        """
        return sorted({v.get("zona") for v in self._voci if v.get("zona")})

    def errore(self):
        return self._errore

    def eta_ore(self):
        if not self._ultimo_successo:
            return None
        return (time.time() - self._ultimo_successo) / 3600.0
