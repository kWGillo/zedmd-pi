# -*- coding: utf-8 -*-
"""Energia: un numero che arriva da Home Assistant e sta sotto l'orologio.

Che cos'e'
----------
Il pannello non misura niente. Misurare la casa e' il mestiere di Home
Assistant, che ha gia' l'inverter, il contatore e le automazioni; qui arriva
**il numero gia' fatto**, su un topic MQTT, e il pannello fa l'unica cosa che
Home Assistant non sa fare: tenerlo sotto gli occhi di chi passa in corridoio.

Due modi, e non sono la stessa cosa con un'unita' diversa
--------------------------------------------------------
* **potenza** -- watt, ampere, quello che si vuole: un valore che deve stare
  dentro un intervallo. Fuori da quell'intervallo, da una parte o dall'altra,
  c'e' qualcosa da sapere; il giallo arriva prima, come preallarme.
* **batteria** -- la percentuale di un accumulo fotovoltaico: un valore che
  **scende**, e che piu' scende piu' preoccupa. Qui l'intervallo non esiste,
  esiste una scala: verde, giallo, rosso, e sotto una certa soglia lampeggia.

Per questo le soglie non sono le stesse e non si riusano: `potenza` ne ha
quattro (due rosse ai due estremi, due gialle appena dentro), `batteria` ne ha
tre (gialla, rossa, lampeggio), e cambiare modo nella pagina web cambia i
campi che si vedono. Un solo insieme di soglie per tutti e due avrebbe voluto
dire, nella meta' dei casi, campi che non vogliono dire niente.

Il valore vecchio
-----------------
Un numero fermo e' peggio di nessun numero: ci si fida di un dato che non
esiste piu'. Passato `scade_minuti` senza sentire niente, al posto del valore
compaiono **due trattini** in grigio. Non si fa sparire la riga: il servizio
e' acceso, e il pannello deve dire «non mi sta arrivando niente», che e' una
informazione, non un buco.

Il contratto con chi pubblica
-----------------------------
Il piu' piccolo possibile, come per le notifiche: sul topic si pubblica **un
numero**, e basta.

    mosquitto_pub -t dmd/energia -m 1250

Chi vuole dire di piu' manda un JSON, e i campi in piu' valgono per quel
messaggio: `{"valore": 84, "unita": "%", "etichetta": "BATT"}`. Serve a chi ha
due automazioni che pubblicano cose diverse sullo stesso topic -- la potenza
di giorno, l'accumulo di sera -- senza toccare la configurazione del pannello.
"""

import json
import threading
import time

# I due modi. Il nome e' quello che finisce in configurazione.
MODI = ("potenza", "batteria")
MODO_PREDEFINITO = "potenza"

# Quando non arriva piu' niente: due trattini, e il grigio delle cose spente.
NIENTE = "--"

# I tre colori, che si possono cambiare dalla pagina. Il verde e' quello del
# nato di oggi nelle info inutili, il rosso quello della sveglia: il pannello
# ha gia' una grammatica dei colori e non ne serve una seconda.
VERDE = "#3ccf5a"
GIALLO = "#ffc000"
ROSSO = "#ff3b30"
GRIGIO = "#788090"

# Le soglie di serie. Per la batteria sono i numeri che userebbe chiunque
# abbia un accumulo: sopra la meta' si sta tranquilli, sotto un quinto si
# comincia a guardare, sotto un decimo la sera non si arriva in fondo.
SOGLIE_BATTERIA = {"gialla": 50.0, "rossa": 20.0, "lampeggio": 10.0}

# Per la potenza non ci sono numeri di serie che vogliano dire qualcosa: un
# impianto da tre chilowatt e uno da sei hanno soglie diverse, e un valore
# inventato qui sarebbe un allarme che suona a casa di qualcuno senza motivo.
# Vuote vuol dire spente, ed e' il comportamento giusto appena acceso.
#
# **Tre numeri, come il quadrante.** La 16.0 ne aveva quattro -- minima,
# preallarme basso, preallarme alto, massima -- perche' trattava la potenza
# come «un valore che deve stare dentro un intervallo». Sulla carta e' giusto,
# davanti alla pagina no: un contatore di casa si guarda in una direzione
# sola, e di quattro caselle due restavano sempre vuote senza che si capisse
# perche' ci fossero. Chi ha in mano un quadrante di Home Assistant dichiara
# **la potenza dell'impianto, dove comincia il giallo e dove comincia il
# rosso**, e tutto il resto e' verde. Si fa cosi' anche qui.
SOGLIE_POTENZA = {"giallo": None, "rosso": None, "massima": None}


def numero(valore):
    """Il valore come numero, o None. Accetta la virgola e le unita' attaccate.

    Home Assistant pubblica quello che ha: `1250`, `1250.4`, `1250,4` se
    qualcuno ha formattato il template per gli umani, e perfino `1250 W` se ha
    usato lo stato con l'unita'. Buttare via un messaggio perche' ha la virgola
    vorrebbe dire un pannello muto e nessun modo di capire perche'.
    """
    if valore is None or isinstance(valore, bool):
        return None
    if isinstance(valore, (int, float)):
        return float(valore)
    testo = str(valore).strip().replace(",", ".")
    if not testo:
        return None
    # Si tiene il primo pezzo che sembra un numero: segno, cifre, punto.
    buoni = ""
    for carattere in testo:
        if carattere in "+-" and not buoni:
            buoni += carattere
        elif carattere.isdigit() or (carattere == "." and "." not in buoni):
            buoni += carattere
        else:
            break
    try:
        return float(buoni)
    except ValueError:
        return None


def soglia(valore):
    """Una soglia come numero, o None quando e' vuota -- cioe' spenta."""
    if valore is None:
        return None
    if isinstance(valore, str) and not valore.strip():
        return None
    return numero(valore)


def formatta(valore, decimali=0):
    """Il numero come si scrive sul pannello: pochi caratteri, nessuna coda."""
    if valore is None:
        return NIENTE
    try:
        decimali = max(0, min(3, int(decimali)))
    except (TypeError, ValueError):
        decimali = 0
    testo = "%.*f" % (decimali, valore)
    # «-0» non esiste: e' zero scritto male, e su un pannello si nota.
    if testo.lstrip("-").strip("0.") == "":
        testo = testo.lstrip("-")
    return testo


class Lettore(object):
    """Tiene l'ultimo valore sentito e sa dire di che colore va scritto.

    Non ha un thread e non chiede niente a nessuno: e' una casella con un
    orologio sopra. Chi gli parla e' il ponte MQTT, chi lo legge e' l'orologio,
    e i due non si conoscono.
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self._lock = threading.Lock()
        self._valore = None
        self._quando = 0.0
        self._unita = ""
        self._etichetta = ""
        self._ricevuti = 0
        self._scartati = 0
        self._ultimo_errore = ""

    # ------------------------------------------------------- configurazione

    def conf(self):
        return self.cfg.get("energia") or {}

    def modo(self):
        scelto = str(self.conf().get("modo") or MODO_PREDEFINITO).lower()
        return scelto if scelto in MODI else MODO_PREDEFINITO

    def acceso(self):
        return bool((self.cfg.get("services") or {}).get("energia"))

    def soglie(self, modo=None):
        """Le soglie del modo scelto, gia' numeri o None.

        Si leggono dal blocco del **modo**, non da una tendina comune: le
        soglie della batteria non vogliono dire niente per la potenza e
        viceversa, e tenerle separate significa che cambiare modo avanti e
        indietro non cancella i numeri dell'altro.
        """
        modo = modo or self.modo()
        grezze = self.conf().get(modo) or {}
        base = SOGLIE_BATTERIA if modo == "batteria" else SOGLIE_POTENZA
        fuori = {}
        for chiave, predefinita in base.items():
            if chiave in grezze:
                fuori[chiave] = soglia(grezze.get(chiave))
            else:
                fuori[chiave] = predefinita
        return fuori

    def colori(self):
        scelti = self.conf().get("colori") or {}
        return {"verde": scelti.get("verde") or VERDE,
                "giallo": scelti.get("giallo") or GIALLO,
                "rosso": scelti.get("rosso") or ROSSO,
                "spento": GRIGIO}

    def scade_dopo(self):
        """Quanti secondi un valore resta buono. Zero vuol dire «per sempre»."""
        try:
            minuti = float(self.conf().get("scade_minuti", 5) or 0)
        except (TypeError, ValueError):
            minuti = 5.0
        return max(0.0, min(1440.0, minuti)) * 60.0

    # -------------------------------------------------------- cio' che arriva

    def handle_mqtt(self, _topic, payload):
        """Un messaggio dal broker. Non solleva: il broker non e' un amico."""
        try:
            self.aggiorna(payload)
        except Exception as exc:                  # pragma: no cover - difensivo
            self._ultimo_errore = str(exc)

    def aggiorna(self, payload, adesso=None):
        """Prende un payload e lo mette da parte. Torna True se valeva.

        Il payload puo' essere un numero nudo -- il caso normale, ed e' quello
        che una automazione di Home Assistant scrive in una riga -- oppure un
        JSON con `valore` e, se si vuole, `unita` ed `etichetta`.
        """
        grezzo = payload
        if isinstance(grezzo, (bytes, bytearray)):
            grezzo = grezzo.decode("utf-8", "replace")
        unita = etichetta = None
        valore = None
        if isinstance(grezzo, dict):
            voce = grezzo
        else:
            testo = str(grezzo or "").strip()
            voce = None
            if testo[:1] in ("{", "["):
                try:
                    letto = json.loads(testo)
                    voce = letto if isinstance(letto, dict) else None
                except ValueError:
                    voce = None
            if voce is None:
                valore = numero(testo)
        if voce is not None:
            for chiave in ("valore", "value", "state", "potenza", "percentuale"):
                if chiave in voce:
                    valore = numero(voce.get(chiave))
                    if valore is not None:
                        break
            if "unita" in voce or "unit" in voce:
                unita = str(voce.get("unita") or voce.get("unit") or "").strip()
            if "etichetta" in voce or "label" in voce:
                etichetta = str(voce.get("etichetta")
                                or voce.get("label") or "").strip()
        if valore is None:
            self._scartati += 1
            self._ultimo_errore = "valore non riconosciuto"
            return False
        with self._lock:
            self._valore = valore
            self._quando = adesso if adesso is not None else time.time()
            self._unita = unita if unita is not None else ""
            self._etichetta = etichetta if etichetta is not None else ""
            self._ricevuti += 1
            self._ultimo_errore = ""
        return True

    def dimentica(self):
        """Butta via il valore: serve alla prova e allo spegnimento."""
        with self._lock:
            self._valore = None
            self._quando = 0.0
            self._unita = ""
            self._etichetta = ""

    # ------------------------------------------------------------ il colore

    def _colore_potenza(self, valore, soglie, colori):
        """Il quadrante di casa: verde fino al giallo, giallo fino al rosso.

        Tre numeri e una direzione sola, perche' un contatore si guarda in una
        direzione sola. **La massima e' quella dell'impianto**: i tre chilowatt
        del contratto, il punto in cui salta. Arrivarci non e' «un po' piu'
        rosso», e' la cosa che si vuole sapere subito: da li' lampeggia.

        Ogni soglia e' facoltativa, e si guarda dall'alto in basso: cosi' chi
        riempie solo la massima ha comunque l'allarme che conta, e chi riempie
        solo il giallo ha un avviso senza doversi inventare il resto. Le
        soglie scritte alla rovescia non rompono niente: vale la prima che il
        valore supera, e il pannello resta leggibile anche se i numeri non lo
        sono.
        """
        massima = soglie.get("massima")
        rosso = soglie.get("rosso")
        giallo = soglie.get("giallo")
        if massima is not None and valore >= massima:
            return colori["rosso"], True
        if rosso is not None and valore >= rosso:
            return colori["rosso"], False
        if giallo is not None and valore >= giallo:
            return colori["giallo"], False
        return colori["verde"], False

    def _colore_batteria(self, valore, soglie, colori):
        """Un semaforo che scende, e il lampeggio ha la sua soglia.

        Il lampeggio e' separato dal rosso perche' lo ha chiesto cosi': un
        accumulo al 18% e' rosso e si guarda, al 10% e' rosso e **chiama**.
        Se la soglia del lampeggio non c'e', lampeggia da dove c'e' il rosso:
        meglio un lampeggio in piu' che un allarme che non scatta.
        """
        gialla = soglie.get("gialla")
        rossa = soglie.get("rossa")
        lampeggio = soglie.get("lampeggio")
        if lampeggio is None:
            lampeggio = rossa
        lampeggia = lampeggio is not None and valore <= lampeggio
        if rossa is not None and valore <= rossa:
            return colori["rosso"], lampeggia
        if gialla is not None and valore <= gialla:
            return colori["giallo"], lampeggia
        return colori["verde"], lampeggia

    # ------------------------------------------------------------- lo stato

    def stato(self, adesso=None):
        """Quello che serve a chi disegna, o None se non c'e' niente da dire.

        Torna un dizionario: `testo` (quello che va scritto), `colore`,
        `lampeggia`, `valore`, `fresco`. Quando il servizio e' spento torna
        None, e l'orologio non sa nemmeno che esista un servizio Energia.
        """
        if not self.acceso():
            return None
        adesso = adesso if adesso is not None else time.time()
        with self._lock:
            valore, quando = self._valore, self._quando
            unita_vista, etichetta_vista = self._unita, self._etichetta
        conf = self.conf()
        colori = self.colori()
        scade = self.scade_dopo()
        fresco = valore is not None and (scade <= 0 or adesso - quando <= scade)
        unita = unita_vista or str(conf.get("unita") or "").strip()
        etichetta = etichetta_vista or str(conf.get("etichetta") or "").strip()
        if not fresco:
            # I due trattini tengono l'unita' -- «CASA -- W» dice ancora di che
            # cosa non si sa niente -- e perdono il colore: un grigio spento
            # non si confonde con una misura.
            pezzi = [p for p in (etichetta, NIENTE, unita) if p]
            return {"testo": " ".join(pezzi), "colore": colori["spento"],
                    "lampeggia": False, "valore": None, "fresco": False,
                    "etichetta": etichetta, "unita": unita}
        soglie = self.soglie()
        if self.modo() == "batteria":
            colore, lampeggia = self._colore_batteria(valore, soglie, colori)
        else:
            colore, lampeggia = self._colore_potenza(valore, soglie, colori)
        scritto = formatta(valore, conf.get("decimali", 0))
        # L'unita' attaccata quando e' un segno -- «84%» -- e staccata quando
        # e' una parola: «1250 W». E' come si scrivono in italiano, e su un
        # pannello stretto il pixel risparmiato dalla percentuale e' gratis.
        if unita in ("%", "°", "°C"):
            scritto += unita
        elif unita:
            scritto += " " + unita
        pezzi = [p for p in (etichetta, scritto) if p]
        return {"testo": " ".join(pezzi), "colore": colore,
                "lampeggia": lampeggia, "valore": valore, "fresco": True,
                "etichetta": etichetta, "unita": unita}

    # ------------------------------------------------------------- la pagina

    def riepilogo(self, adesso=None):
        """Per la pagina web: cosa e' arrivato, quando, e come si vede."""
        adesso = adesso if adesso is not None else time.time()
        with self._lock:
            valore, quando = self._valore, self._quando
            ricevuti, scartati = self._ricevuti, self._scartati
            errore = self._ultimo_errore
        stato = self.stato(adesso)
        return {"valore": valore,
                "da_quanto": (adesso - quando) if quando else None,
                "ricevuti": ricevuti, "scartati": scartati,
                "errore": errore, "modo": self.modo(),
                "acceso": self.acceso(),
                "testo": (stato or {}).get("testo", ""),
                "colore": (stato or {}).get("colore", ""),
                "lampeggia": bool((stato or {}).get("lampeggia")),
                "fresco": bool((stato or {}).get("fresco"))}
