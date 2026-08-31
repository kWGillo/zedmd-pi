# -*- coding: utf-8 -*-
"""Scadenze: appuntamenti e pagamenti, con un semaforo sul pannello.

Assomiglia al calendario dei rifiuti, ma le differenze contano piu' delle
somiglianze.

**Le cadenze sono altre.** I rifiuti hanno un ritmo settimanale — quali giorni
della settimana, ogni quante settimane. Una bolletta no: e' mensile,
trimestrale, annuale. Ancorate a una data di partenza e non alla parita' del
mese, per la stessa ragione per cui la raccolta quindicinale e' ancorata a una
data: i calendari che contano invece di ricordare sbagliano prima o poi.

**Una scadenza si chiude.** Un bidone si espone e basta; una bolletta si paga,
e da quel momento quella occorrenza e' storia. Le occorrenze chiuse restano
nel registro con l'ora in cui sono state inserite e quella in cui sono state
completate: e' l'unica parte di questo progetto in cui serve sapere *quando* e'
successo qualcosa, e non solo che cosa succede adesso.

**I dati stanno in un CSV, non in configurazione.** Sono righe che crescono, si
importano e si esportano; la configurazione tiene solo le soglie del semaforo.
"""

import csv
import io
import os
import threading
import time
from datetime import date, datetime, timedelta

DATA_DIR = os.environ.get("DMD_DATA", "/var/lib/dmd")
FILE_VOCI = "scadenze.csv"
FILE_LOG = "scadenze_log.csv"

# Le cadenze sono multipli di mesi: e' come si ragiona su bollette, tasse e
# assicurazioni. "una_tantum" e' l'assenza di cadenza, non un caso a parte.
CADENZE = {
    "una_tantum": 0,
    "mensile": 1,
    "bimestrale": 2,
    "trimestrale": 3,
    "semestrale": 6,
    "annuale": 12,
}
CADENZA_PREDEFINITA = "una_tantum"

# Gli stati del semaforo, dal piu' lontano al piu' urgente.
SPENTO, VERDE, GIALLO, ROSSO, SCADUTA = "spento", "verde", "giallo", "rosso", "scaduta"
ORDINE = (SPENTO, VERDE, GIALLO, ROSSO, SCADUTA)

COLORI = {
    SPENTO: (28, 28, 32),
    VERDE: (40, 220, 70),
    GIALLO: (255, 200, 30),
    ROSSO: (255, 40, 40),
    SCADUTA: (255, 40, 40),
}

# Soglie predefinite, in giorni. Sono quelle chieste: verde da 8 a 10, giallo
# da 4 a 7, rosso da 0 a 3, e oltre i 10 giorni il semaforo resta spento
# perche' una scadenza lontana non e' una notizia. Il 7 sta nel giallo e non
# nel verde: fra due letture possibili si sceglie la piu' prudente.
SOGLIA_VERDE = 10
SOGLIA_GIALLO = 7
SOGLIA_ROSSO = 3

# Quanto testo entra nella descrizione. Sul pannello la riga della descrizione
# e' larga 256 pixel con un font da sei: oltre questa lunghezza non si legge
# piu' niente, e troncare in silenzio e' peggio che dirlo prima.
MAX_DESCRIZIONE = 64
MAX_TITOLO = 48

_lock = threading.Lock()
_cache = {"stamp": None, "voci": []}


# ------------------------------------------------------------------ utilita'

def _oggi(oggi=None):
    return oggi or date.today()


def percorso(nome):
    return os.path.join(DATA_DIR, nome)


def parse_data(testo):
    """Da testo a data. Accetta i formati che una persona scrive davvero."""
    testo = str(testo or "").strip()
    if not testo:
        return None
    for formato in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(testo, formato).date()
        except ValueError:
            continue
    return None


def scrivi_data(giorno):
    return giorno.strftime("%d/%m/%Y") if giorno else ""


def _somma_mesi(giorno, mesi):
    """Aggiunge mesi a una data tenendo il giorno del mese quando esiste.

    Il 31 gennaio piu' un mese e' il 28 febbraio, non il 3 marzo: una bolletta
    che scade il 31 non si sposta di tre giorni ogni febbraio.
    """
    if not mesi:
        return giorno
    indice = giorno.month - 1 + mesi
    anno = giorno.year + indice // 12
    mese = indice % 12 + 1
    for tentativo in range(giorno.day, 27, -1):
        try:
            return date(anno, mese, tentativo)
        except ValueError:
            continue
    return date(anno, mese, min(giorno.day, 28))


def _taglia(testo, massimo):
    testo = " ".join(str(testo or "").split())
    return testo[:massimo]


# ------------------------------------------------------------------ le voci

def normalizza(grezza, indice=0):
    """Riempie una voce con i valori mancanti, senza mai sollevare."""
    voce = dict(grezza or {})
    voce["id"] = str(voce.get("id") or "").strip() or ("s%d" % (indice + 1))
    voce["titolo"] = _taglia(voce.get("titolo"), MAX_TITOLO) or "Scadenza"
    voce["descrizione"] = _taglia(voce.get("descrizione"), MAX_DESCRIZIONE)
    data = voce.get("data")
    voce["data"] = data if isinstance(data, date) else parse_data(data)
    cadenza = voce.get("cadenza")
    voce["cadenza"] = cadenza if cadenza in CADENZE else CADENZA_PREDEFINITA
    voce["attiva"] = str(voce.get("attiva", "1")).strip().lower() not in (
        "0", "no", "false", "")
    completate = voce.get("completate")
    if isinstance(completate, str):
        completate = [parse_data(p) for p in completate.split(",")]
    voce["completate"] = sorted({c for c in (completate or []) if c})
    return voce


def _riga(voce):
    return [voce["id"], voce["titolo"], scrivi_data(voce["data"]),
            voce["cadenza"], voce["descrizione"],
            "1" if voce["attiva"] else "0",
            ",".join(scrivi_data(c) for c in voce["completate"])]


INTESTAZIONE = ["id", "titolo", "data", "cadenza", "descrizione",
                "attiva", "completate"]


def leggi_testo():
    try:
        with open(percorso(FILE_VOCI), encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return ""


def _parse(testo):
    """Da testo CSV a voci. Le righe rotte si saltano, non fanno cadere tutto.

    Il separatore si indovina: chi esporta da un foglio di calcolo italiano
    ottiene il punto e virgola, chi scrive a mano di solito la virgola.
    """
    voci, scartate = [], 0
    righe = [r for r in (testo or "").splitlines() if r.strip()]
    if not righe:
        return voci, 0
    separatore = ";" if righe[0].count(";") >= righe[0].count(",") else ","
    lettore = csv.reader(io.StringIO("\n".join(righe)), delimiter=separatore)
    for numero, campi in enumerate(lettore, 1):
        if not campi or not campi[0].strip():
            continue
        if campi[0].strip().lower() == "id":         # intestazione
            continue
        campi = campi + [""] * (len(INTESTAZIONE) - len(campi))
        grezza = dict(zip(INTESTAZIONE, campi))
        voce = normalizza(grezza, len(voci))
        if voce["data"] is None:
            scartate += 1
            continue
        voci.append(voce)
    return voci, scartate


def load(force=False):
    """Le voci dal file, rilette solo quando il file cambia."""
    percorso_voci = percorso(FILE_VOCI)
    try:
        info = os.stat(percorso_voci)
        stamp = (info.st_mtime, info.st_size)
    except OSError:
        stamp = None
    with _lock:
        if not force and stamp == _cache["stamp"]:
            return list(_cache["voci"])
        voci, scartate = _parse(leggi_testo())
        if scartate:
            print("[scadenze] %d righe scartate: data mancante o illeggibile"
                  % scartate)
        _cache["stamp"] = stamp
        _cache["voci"] = voci
        return list(voci)


def invalidate():
    with _lock:
        _cache["stamp"] = None


def salva(voci):
    """Riscrive il file delle voci. E' l'unico punto che ci scrive."""
    buffer = io.StringIO()
    scrittore = csv.writer(buffer, delimiter=";", lineterminator="\n")
    scrittore.writerow(INTESTAZIONE)
    for voce in voci:
        scrittore.writerow(_riga(voce))
    os.makedirs(DATA_DIR, exist_ok=True)
    temporaneo = percorso(FILE_VOCI) + ".tmp"
    with open(temporaneo, "w", encoding="utf-8") as handle:
        handle.write(buffer.getvalue())
    os.replace(temporaneo, percorso(FILE_VOCI))
    invalidate()
    return len(voci)


def salva_testo(testo):
    """Salva quello che l'utente ha scritto o incollato, normalizzandolo."""
    voci, scartate = _parse(testo)
    salva(voci)
    return len(voci), scartate


def nuovo_id(voci):
    usati = {v["id"] for v in voci}
    numero = len(voci) + 1
    while ("s%d" % numero) in usati:
        numero += 1
    return "s%d" % numero


# --------------------------------------------------------------- le scadenze

def prossima(voce, oggi=None):
    """La prima occorrenza non ancora completata.

    Per una scadenza periodica si va avanti di cadenza in cadenza finche' non
    se ne trova una che non risulta gia' chiusa. Per una una tantum, o e'
    aperta o non c'e' piu' niente da ricordare.
    """
    if not voce.get("attiva") or not voce.get("data"):
        return None
    completate = set(voce.get("completate") or [])
    mesi = CADENZE.get(voce.get("cadenza"), 0)
    giorno = voce["data"]
    if not mesi:
        return None if giorno in completate else giorno
    # Le occorrenze chiuse si saltano; il limite evita di girare all'infinito
    # se qualcuno scrive una data del 1800.
    for _ in range(600):
        if giorno not in completate:
            return giorno
        giorno = _somma_mesi(giorno, mesi)
    return giorno


def giorni(voce, oggi=None):
    """Giorni che mancano. Negativi se la scadenza e' passata."""
    scadenza = prossima(voce, oggi)
    if scadenza is None:
        return None
    return (scadenza - _oggi(oggi)).days


def soglie(cfg):
    conf = (cfg or {}).get("scadenze") or {}
    def numero(chiave, predefinito):
        try:
            return max(0, min(365, int(conf.get(chiave, predefinito))))
        except (TypeError, ValueError):
            return predefinito
    return (numero("soglia_verde", SOGLIA_VERDE),
            numero("soglia_giallo", SOGLIA_GIALLO),
            numero("soglia_rosso", SOGLIA_ROSSO))


def stato(voce, cfg=None, oggi=None):
    """Il colore del semaforo per questa voce."""
    mancanti = giorni(voce, oggi)
    if mancanti is None:
        return SPENTO
    verde, giallo, rosso = soglie(cfg)
    if mancanti < 0:
        return SCADUTA
    if mancanti <= rosso:
        return ROSSO
    if mancanti <= giallo:
        return GIALLO
    if mancanti <= verde:
        return VERDE
    return SPENTO


def elenco(cfg=None, oggi=None):
    """Tutte le scadenze aperte, dalla piu' urgente alla piu' lontana."""
    fuori = []
    for voce in load():
        mancanti = giorni(voce, oggi)
        if mancanti is None:
            continue
        fuori.append({
            "id": voce["id"], "titolo": voce["titolo"],
            "descrizione": voce["descrizione"], "cadenza": voce["cadenza"],
            "data": prossima(voce, oggi), "giorni": mancanti,
            "stato": stato(voce, cfg, oggi),
            "completate": len(voce["completate"]),
        })
    fuori.sort(key=lambda v: v["giorni"])
    return fuori


def semaforo(cfg=None, oggi=None):
    """Lo stato complessivo: quello della scadenza piu' urgente.

    Un semaforo solo per tutte: chi guarda il pannello di sfuggita vuole
    sapere se c'e' qualcosa che scotta, non quante cose ci sono.
    """
    peggiore = SPENTO
    for voce in elenco(cfg, oggi):
        if ORDINE.index(voce["stato"]) > ORDINE.index(peggiore):
            peggiore = voce["stato"]
    return peggiore


def da_mostrare(cfg=None, oggi=None):
    """Le scadenze che meritano l'avviso periodico sul pannello.

    Non tutte: quelle ancora lontane restano nella pagina web. Sul pannello ci
    va cio' su cui il semaforo si e' gia' acceso.
    """
    return [v for v in elenco(cfg, oggi) if v["stato"] != SPENTO]


# ------------------------------------------------------------------ registro

CAMPI_LOG = ["inserita", "id", "titolo", "scadenza", "cadenza",
             "descrizione", "completata"]


def _leggi_log():
    righe = []
    try:
        with open(percorso(FILE_LOG), encoding="utf-8") as handle:
            for campi in csv.reader(handle, delimiter=";"):
                if not campi or campi[0].strip().lower() == "inserita":
                    continue
                campi = campi + [""] * (len(CAMPI_LOG) - len(campi))
                righe.append(dict(zip(CAMPI_LOG, campi[:len(CAMPI_LOG)])))
    except OSError:
        pass
    return righe


def _scrivi_log(righe):
    os.makedirs(DATA_DIR, exist_ok=True)
    buffer = io.StringIO()
    scrittore = csv.writer(buffer, delimiter=";", lineterminator="\n")
    scrittore.writerow(CAMPI_LOG)
    for riga in righe:
        scrittore.writerow([riga.get(c, "") for c in CAMPI_LOG])
    temporaneo = percorso(FILE_LOG) + ".tmp"
    with open(temporaneo, "w", encoding="utf-8") as handle:
        handle.write(buffer.getvalue())
    os.replace(temporaneo, percorso(FILE_LOG))


def _adesso():
    return time.strftime("%d/%m/%Y %H:%M:%S")


def apri_riga(voce, quando=None):
    """Registra un'occorrenza aperta: si sapra' quando e' stata inserita."""
    scadenza = prossima(voce)
    if scadenza is None:
        return False
    righe = _leggi_log()
    for riga in righe:
        if riga["id"] == voce["id"] and not riga["completata"] \
                and riga["scadenza"] == scrivi_data(scadenza):
            return False                      # gia' aperta, non si duplica
    righe.append({"inserita": quando or _adesso(), "id": voce["id"],
                  "titolo": voce["titolo"], "scadenza": scrivi_data(scadenza),
                  "cadenza": voce["cadenza"],
                  "descrizione": voce["descrizione"], "completata": ""})
    _scrivi_log(righe)
    return True


def chiudi_riga(voce, scadenza, quando=None):
    """Segna completata l'occorrenza, o ne scrive una gia' chiusa se manca.

    Il registro non deve mai perdere un completamento perche' la riga aperta
    non c'era: se non la trova, la scrive completa. Meglio una riga senza ora
    di inserimento che un pagamento di cui non resta traccia.
    """
    righe = _leggi_log()
    testo = scrivi_data(scadenza)
    for riga in righe:
        if riga["id"] == voce["id"] and riga["scadenza"] == testo \
                and not riga["completata"]:
            riga["completata"] = quando or _adesso()
            _scrivi_log(righe)
            return True
    righe.append({"inserita": "", "id": voce["id"], "titolo": voce["titolo"],
                  "scadenza": testo, "cadenza": voce["cadenza"],
                  "descrizione": voce["descrizione"],
                  "completata": quando or _adesso()})
    _scrivi_log(righe)
    return True


def registro(limite=0):
    righe = _leggi_log()
    return righe[-limite:] if limite else righe


def registro_testo():
    try:
        with open(percorso(FILE_LOG), encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return ""


# ------------------------------------------------------------------ comandi

def aggiungi(titolo, data, cadenza=CADENZA_PREDEFINITA, descrizione="",
             identificativo=""):
    """Aggiunge una scadenza. La usa la pagina web e la usa Home Assistant."""
    giorno = data if isinstance(data, date) else parse_data(data)
    if not giorno:
        return None
    voci = load(force=True)
    voce = normalizza({
        "id": identificativo or nuovo_id(voci), "titolo": titolo,
        "data": giorno, "cadenza": cadenza, "descrizione": descrizione,
        "attiva": "1", "completate": [],
    }, len(voci))
    voci = [v for v in voci if v["id"] != voce["id"]] + [voce]
    salva(voci)
    apri_riga(voce)
    return voce


def completa(identificativo, quando=None):
    """Segna fatta l'occorrenza aperta di una scadenza.

    Per una periodica non si cancella niente: si chiude questa occorrenza e la
    prossima diventa quella dopo. Per una una tantum resta la voce, senza piu'
    scadenze aperte — cosi' la si puo' riaprire, e il registro non perde nulla.
    """
    voci = load(force=True)
    for voce in voci:
        if voce["id"] != str(identificativo):
            continue
        scadenza = prossima(voce)
        if scadenza is None:
            return False
        chiudi_riga(voce, scadenza, quando)
        voce["completate"] = sorted(set(voce["completate"]) | {scadenza})
        salva(voci)
        nuova = prossima(voce)
        if nuova is not None:
            apri_riga(voce)
        return True
    return False


def riapri(identificativo):
    """Toglie l'ultimo completamento: serve quando si spunta per sbaglio."""
    voci = load(force=True)
    for voce in voci:
        if voce["id"] == str(identificativo) and voce["completate"]:
            voce["completate"] = voce["completate"][:-1]
            salva(voci)
            return True
    return False


def elimina(identificativo):
    voci = load(force=True)
    rimaste = [v for v in voci if v["id"] != str(identificativo)]
    if len(rimaste) == len(voci):
        return False
    salva(rimaste)
    return True
