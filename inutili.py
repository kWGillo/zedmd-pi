# -*- coding: utf-8 -*-
"""I dati di Info inutili: il calendario che sta qui dentro, e la storia che
arriva da fuori.

Due sorgenti, e la differenza fra loro e' il motivo per cui il servizio ha due
schermate.

**Il calendario e' nostro.** Santo del giorno, nomi che festeggiano e giornate
mondiali stanno in due CSV dentro il programma: `santi.csv` (366 giorni) e
`giornate.csv`. Non cambiano mai, non serve nessuna rete, e fra dieci anni
funzionano ancora. E' la stessa scelta dei CSV degli aerei: un dato che non
cambia non si chiede a un servizio.

**La storia arriva da Wikipedia.** Nati e morti famosi del giorno vengono
dall'API «on this day» di Wikimedia -- gratuita, senza chiave, come Open-Meteo
e le ADS-B. Si scarica una volta al giorno e si tiene in una cache; se la rete
manca, si mostra quello che c'e' e, se non c'e' niente, la seconda schermata
semplicemente non si fa. Il servizio si accorcia, non si rompe.

**L'onomastico dei tuoi.** I nomi del giorno si confrontano con i nomi di
`compleanni.csv`: se oggi e' l'onomastico di qualcuno che conosci, il pannello
lo dice. E' l'unica riga di tutto il servizio che fa fare una telefonata, e
non esce di casa: il confronto e' locale, nessun nome viene mandato in giro.
"""

import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.request

import compleanni

DATA_DIR = os.environ.get("DMD_DATA", "/var/lib/dmd")
QUI = os.path.dirname(os.path.abspath(__file__))

SANTI = "santi.csv"
GIORNATE = "giornate.csv"
CACHE = "inutili.json"

# L'API di Wikimedia. La lingua e' fissa all'italiano: il servizio e' scritto
# per un pannello che parla italiano, e la versione inglese darebbe personaggi
# diversi -- il "famoso" di una lingua non e' quello di un'altra.
API = "https://it.wikipedia.org/api/rest_v1/feed/onthisday/%s/%02d/%02d"
# Wikimedia chiede di presentarsi. Un programma che non lo fa viene rifiutato,
# ed e' giusto cosi': si sa chi sta chiedendo e a chi scrivere se esagera.
AGENTE = "zedmd-pi/1.0 (https://github.com/kWGillo/zedmd-pi) info-inutili"
TIMEOUT = 12
QUANTI = 6                  # nati e morti da tenere in cache, per tipo
ETA_MASSIMA = 36 * 3600     # oltre, la cache e' vecchia ma si usa lo stesso


# ------------------------------------------------------------------- i CSV

def _percorsi(nome):
    """Il file del programma, e quello dell'utente se c'e'.

    Il secondo non sostituisce il primo: si aggiunge. Chi vuole la giornata
    mondiale del gatto la mette nel suo file e non perde le altre.
    """
    percorsi = [os.path.join(QUI, nome)]
    mio = os.path.join(DATA_DIR, nome)
    if os.path.exists(mio) and os.path.abspath(mio) != os.path.abspath(percorsi[0]):
        percorsi.append(mio)
    return percorsi


def _leggi(nome):
    righe = []
    for percorso in _percorsi(nome):
        try:
            with open(percorso, encoding="utf-8", errors="replace") as f:
                for riga in f:
                    riga = riga.strip()
                    if riga and not riga.startswith("#"):
                        righe.append(riga)
        except OSError:
            continue
    return righe


_tavole = {}


def _tavola(nome, costruisci):
    """Le tavole si leggono una volta sola: sono file che non cambiano."""
    impronte = []
    for percorso in _percorsi(nome):
        try:
            st = os.stat(percorso)
            impronte.append((percorso, st.st_mtime, st.st_size))
        except OSError:
            pass
    impronta = tuple(impronte)
    if _tavole.get(nome, (None, None))[0] != impronta:
        _tavole[nome] = (impronta, costruisci(_leggi(nome)))
    return _tavole[nome][1]


def _santi():
    def costruisci(righe):
        tavola = {}
        for riga in righe:
            pezzi = riga.split(";")
            if len(pezzi) < 2:
                continue
            nomi = [n.strip() for n in (pezzi[2] if len(pezzi) > 2 else "").split(",")]
            tavola[pezzi[0].strip()] = (pezzi[1].strip(), [n for n in nomi if n])
        return tavola
    return _tavola(SANTI, costruisci)


def _giornate():
    def costruisci(righe):
        tavola = {}
        for riga in righe:
            pezzi = riga.split(";")
            if len(pezzi) < 2 or not pezzi[1].strip():
                continue
            tavola.setdefault(pezzi[0].strip(), []).append(pezzi[1].strip())
        return tavola
    return _tavola(GIORNATE, costruisci)


def invalida():
    """Per le prove: la prossima lettura rilegge i file."""
    _tavole.clear()


def chiave(quando=None):
    quando = quando or time.localtime()
    return "%02d-%02d" % (quando.tm_mon, quando.tm_mday)


def santo(quando=None):
    voce = _santi().get(chiave(quando))
    return voce[0] if voce else ""


def nomi(quando=None):
    voce = _santi().get(chiave(quando))
    return list(voce[1]) if voce else []


def giornata(quando=None):
    """La giornata mondiale del giorno, o "" se non ce n'e'.

    Quando ce n'e' piu' d'una si prende **la piu' corta**: sul pannello ci
    sta, e nella pratica e' quasi sempre anche quella che la gente conosce --
    "Giornata mondiale dell'acqua" contro "Giornata internazionale per la
    prevenzione dell'estremismo violento".
    """
    voci = _giornate().get(chiave(quando)) or []
    return min(voci, key=len) if voci else ""


def giornate_del_giorno(quando=None):
    return list(_giornate().get(chiave(quando)) or [])


# ------------------------------------------------- l'onomastico dei tuoi

def _senza_accenti(testo):
    piatto = unicodedata.normalize("NFD", testo)
    return "".join(c for c in piatto if unicodedata.category(c) != "Mn").lower()


def _pezzi_nome(nome):
    """I nomi propri dentro una voce di compleanni.csv.

    Il campo e' libero: "Anna", "Anna Rossi", "Anna e Luca". Si spezza sugli
    spazi e sulle congiunzioni, e si scartano le parole di una o due lettere.
    """
    grezzi = re.split(r"[\s,;/&]+|\be\b", nome or "")
    return [p for p in (g.strip() for g in grezzi) if len(p) > 2]


def onomastici_tuoi(quando=None, voci=None):
    """I nomi della rubrica dei compleanni che festeggiano oggi.

    Torna la lista dei nomi come li ha scritti l'utente, senza ripetizioni e
    nell'ordine in cui compaiono nel suo file.
    """
    del_giorno = {_senza_accenti(n) for n in nomi(quando)}
    if not del_giorno:
        return []
    if voci is None:
        try:
            voci = compleanni.load()
        except Exception:
            return []
    trovati = []
    for voce in voci:
        for pezzo in _pezzi_nome(voce.get("nome")):
            if _senza_accenti(pezzo) in del_giorno and pezzo not in trovati:
                trovati.append(pezzo)
    return trovati


# --------------------------------------------------- nati e morti famosi

def _chiedi(url):
    richiesta = urllib.request.Request(url, headers={
        "User-Agent": AGENTE,
        "Accept": "application/json",
    })
    with urllib.request.urlopen(richiesta, timeout=TIMEOUT) as risposta:
        return json.loads(risposta.read().decode("utf-8", "replace"))


def _persona(voce):
    """Da una voce dell'API: (anno, nome, cosa faceva) oppure None.

    Il testo dell'API e' del tipo "Dante Alighieri, poeta italiano". Sul
    pannello ci stanno il nome e poche parole, quindi si tiene la prima
    pagina collegata -- che e' la persona -- e la descrizione breve.
    """
    anno = voce.get("year")
    pagine = voce.get("pages") or []
    if not isinstance(anno, int) or not pagine:
        return None
    pagina = pagine[0]
    titoli = pagina.get("titles") or {}
    nome = titoli.get("normalized") or pagina.get("normalizedtitle") or ""
    nome = re.sub(r"\s*\(.*?\)\s*", " ", nome).strip()
    if not nome:
        return None
    testo = (voce.get("text") or "").strip()
    mestiere = pagina.get("description") or ""
    if not mestiere and "," in testo:
        mestiere = testo.split(",", 1)[1]
    mestiere = re.sub(r"\s+", " ", mestiere).strip(" .,;")
    return (anno, nome, mestiere)


def scarica(quando=None, tipi=("births", "deaths")):
    """Chiede a Wikipedia i nati e i morti del giorno.

    Torna (dati, errore). `dati` e' un dizionario {"nati": [...], "morti":
    [...]}; ogni voce e' (anno, nome, mestiere). Un errore di rete non e'
    un'eccezione: e' il caso normale di un pannello in una casa, e chi
    chiama deve solo sapere che non ha niente di nuovo.
    """
    quando = quando or time.localtime()
    fuori = {}
    for tipo, etichetta in (("births", "nati"), ("deaths", "morti")):
        if tipo not in tipi:
            continue
        try:
            dati = _chiedi(API % (tipo, quando.tm_mon, quando.tm_mday))
        except (urllib.error.URLError, OSError, ValueError) as exc:
            return None, str(getattr(exc, "reason", exc))[:120]
        voci = []
        for voce in (dati.get(etichetta) or dati.get(tipo) or []):
            persona = _persona(voce)
            if persona:
                voci.append(persona)
        # Dalle piu' recenti: sono quelle che uno riconosce.
        voci.sort(key=lambda v: -v[0])
        fuori[etichetta] = voci[:QUANTI]
    return fuori, ""


# ------------------------------------------------------------- la cache

def percorso_cache(cartella=None):
    return os.path.join(cartella or DATA_DIR, CACHE)


def leggi_cache(cartella=None):
    try:
        with open(percorso_cache(cartella), encoding="utf-8") as f:
            dati = json.load(f)
    except (OSError, ValueError):
        return {}
    return dati if isinstance(dati, dict) else {}


def scrivi_cache(dati, cartella=None):
    percorso = percorso_cache(cartella)
    try:
        temporaneo = percorso + ".tmp"
        with open(temporaneo, "w", encoding="utf-8") as f:
            json.dump(dati, f, ensure_ascii=False)
        os.replace(temporaneo, percorso)
        return True
    except OSError:
        return False


class Storia(object):
    """I nati e i morti del giorno, con la loro cache.

    La regola e' una sola: **si chiede una volta al giorno**, e quello che si
    e' preso resta finche' non se ne prende uno nuovo. Un pannello acceso in
    una casa passa piu' tempo senza rete di quanto si creda.
    """

    def __init__(self, cartella=None):
        self.cartella = cartella or DATA_DIR
        self._dati = leggi_cache(self.cartella)
        self._errore = ""
        self._tentativo = 0.0

    def _valida(self, quando=None):
        voce = self._dati.get(chiave(quando))
        if not isinstance(voce, dict):
            return None
        return voce

    def fresca(self, quando=None):
        voce = self._valida(quando)
        if not voce:
            return False
        return (time.time() - voce.get("preso", 0)) < ETA_MASSIMA

    def aggiorna(self, quando=None, forza=False):
        """(fatto, motivo). Non solleva mai."""
        if not forza and self.fresca(quando):
            return False, "gia' presa"
        # Il tentativo si segna prima di farlo: con la rete giu' non si
        # martella il servizio a ogni giro.
        adesso = time.time()
        if not forza and adesso - self._tentativo < 600:
            return False, "riprovo piu' tardi"
        self._tentativo = adesso
        dati, errore = scarica(quando)
        if dati is None:
            self._errore = errore
            return False, errore
        voce = {"preso": adesso, "nati": dati.get("nati", []),
                "morti": dati.get("morti", [])}
        # Si tiene solo il giorno in corso: la cache e' un promemoria, non un
        # archivio, e un file che cresce per sempre su una scheda SD e' un
        # problema che arriva fra due anni.
        self._dati = {chiave(quando): voce}
        scrivi_cache(self._dati, self.cartella)
        self._errore = ""
        return True, ""

    def nati(self, quando=None):
        voce = self._valida(quando) or {}
        return [tuple(v) for v in voce.get("nati", [])]

    def morti(self, quando=None):
        voce = self._valida(quando) or {}
        return [tuple(v) for v in voce.get("morti", [])]

    def ha_qualcosa(self, quando=None, con_morti=True):
        return bool(self.nati(quando) or (con_morti and self.morti(quando)))

    def errore(self):
        return self._errore


# ------------------------------------------------------------- riepilogo

def riepilogo(quando=None, storia=None):
    """Tutto quello che si sa di oggi, per la pagina web e per MQTT."""
    dati = {
        "giorno": chiave(quando),
        "santo": santo(quando),
        "nomi": nomi(quando),
        "giornata": giornata(quando),
        "giornate": giornate_del_giorno(quando),
        "tuoi": onomastici_tuoi(quando),
        "nati": [],
        "morti": [],
    }
    if storia is not None:
        dati["nati"] = [list(v) for v in storia.nati(quando)]
        dati["morti"] = [list(v) for v in storia.morti(quando)]
    return dati
