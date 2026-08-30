"""Calendario della raccolta rifiuti e delle attivita' comunali.

La domanda a cui questo modulo risponde e' una sola: **cosa va esposto
stasera**. Tutto il resto — cadenze, eccezioni, orari — esiste per rispondere
a quella.

In Italia quasi nessun comune pubblica un calendario scaricabile: molti usano
un'applicazione che il calendario te lo fa vedere e basta. Ma la raccolta non
e' un elenco di date, e' una **regola**: due o tre giorni fissi alla settimana
per ogni frazione, qualche comune a settimane alterne, e una manciata di
eccezioni all'anno per le feste. Scrivere la regola richiede dieci minuti una
volta sola, non dipende da nessun servizio esterno e non si rompe mai. Da li'
le date si calcolano.

Le voci vivono nella configurazione; le due tabelle delle eccezioni in due
file CSV in /var/lib/dmd, modificabili dalla pagina web:

    soppressioni.csv     giorni in cui il servizio NON viene fatto
    straordinari.csv     giorni in cui viene fatto in piu'

Entrambe hanno la stessa forma — `data,voce,nota` — con la voce facoltativa:
lasciata vuota vale per tutte, perche' quando la raccolta salta per una
festivita' di solito salta tutta.

**La cadenza a settimane alterne va ancorata a una data, non alla parita' del
numero di settimana.** Sembra la stessa cosa e non lo e': un anno ha 52 o 53
settimane, quindi a capodanno la parita' si ribalta e la raccolta salterebbe
un giro da sola una volta l'anno. Con una data di riferimento — un giorno
qualunque in cui la raccolta c'e' stata — si contano le settimane trascorse e
non si sbaglia mai.
"""

import csv
import datetime
import io
import os
import threading

DATA_DIR = os.environ.get("DMD_DATA", "/var/lib/dmd")

SOPPRESSIONI = "soppressioni.csv"
STRAORDINARI = "straordinari.csv"

# Giorni della settimana, indice 0 = lunedi', come `date.weekday()`.
GIORNI = ("lun", "mar", "mer", "gio", "ven", "sab", "dom")
GIORNI_LUNGHI = ("Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì",
                 "Sabato", "Domenica")

# Cadenze. La chiave e' quella che si scrive in configurazione.
CADENZE = ("settimanale", "quindicinale", "mensile_1_3", "mensile_2_4")
CADENZA_PREDEFINITA = "settimanale"

# Due nature diverse, non due elenchi diversi. Un rifiuto si **espone** la sera
# prima e sparisce dopo il passaggio; un'attivita' comunale — il lavaggio
# strade — e' un **divieto** che vale in una fascia oraria sua, e quello che
# serve sapere e' di spostare l'auto prima che cominci.
TIPI = ("rifiuto", "attivita")
TIPO_PREDEFINITO = "rifiuto"

# Le frazioni che quasi ogni comune ha, con i colori con cui si riconoscono a
# colpo d'occhio. Il marrone del secco e' schiarito: su fondo nero, a dodici
# pixel di altezza, un marrone da tavolozza non si legge.
VOCI_PREDEFINITE = [
    {"nome": "Carta", "colore": "#ffffff", "tipo": "rifiuto"},
    {"nome": "Plastica", "colore": "#2060ff", "tipo": "rifiuto"},
    {"nome": "Vetro", "colore": "#ff8c1a", "tipo": "rifiuto"},
    {"nome": "Umido", "colore": "#20c040", "tipo": "rifiuto"},
    {"nome": "Secco", "colore": "#c07830", "tipo": "rifiuto"},
    {"nome": "Sosta", "colore": "#ff2020", "tipo": "attivita"},
]

_lock = threading.Lock()
_cache = {}


# ------------------------------------------------------------------- utilita'

def _oggi(oggi=None):
    return oggi or datetime.date.today()


def parse_data(testo):
    """`gg/mm/aaaa` -> date. Anche `gg-mm-aaaa` e `aaaa-mm-gg`.

    Il giorno viene prima del mese, come si scrive in italiano: accettare
    anche la forma americana renderebbe ambiguo `03/04`, e un promemoria
    sbagliato di un mese e' peggio di nessun promemoria.
    """
    testo = (testo or "").strip().replace("-", "/").replace(".", "/")
    if not testo:
        return None
    parti = [p for p in testo.split("/") if p.strip()]
    if len(parti) != 3:
        return None
    try:
        if len(parti[0]) == 4:                     # aaaa/mm/gg
            anno, mese, giorno = (int(p) for p in parti)
        else:                                       # gg/mm/aaaa
            giorno, mese, anno = (int(p) for p in parti)
        if anno < 100:
            anno += 2000
        return datetime.date(anno, mese, giorno)
    except (ValueError, TypeError):
        return None


def normalizza_voce(grezza, indice=0):
    """Riempie una voce con i valori mancanti, senza mai sollevare.

    Le voci arrivano dalla configurazione, che un utente puo' aver modificato
    a mano o importato da una versione precedente: una chiave mancante non
    deve far cadere il pannello.
    """
    voce = dict(grezza or {})
    voce["nome"] = str(voce.get("nome") or "Voce %d" % (indice + 1)).strip()
    voce["colore"] = str(voce.get("colore") or "#ffffff").strip() or "#ffffff"
    voce["tipo"] = voce.get("tipo") if voce.get("tipo") in TIPI else TIPO_PREDEFINITO
    voce["attiva"] = bool(voce.get("attiva", True))

    giorni = voce.get("giorni") or []
    if isinstance(giorni, str):
        giorni = [g.strip() for g in giorni.replace(";", ",").split(",")]
    puliti = []
    for g in giorni:
        if isinstance(g, int) and 0 <= g <= 6:
            puliti.append(g)
        elif isinstance(g, str) and g.strip().isdigit() and 0 <= int(g) <= 6:
            puliti.append(int(g))
        elif isinstance(g, str) and g.strip()[:3].lower() in GIORNI:
            puliti.append(GIORNI.index(g.strip()[:3].lower()))
    voce["giorni"] = sorted(set(puliti))

    if voce.get("cadenza") not in CADENZE:
        voce["cadenza"] = CADENZA_PREDEFINITA
    riferimento = voce.get("riferimento")
    if isinstance(riferimento, str):
        riferimento = parse_data(riferimento)
    voce["riferimento"] = riferimento

    # Fascia oraria del divieto, solo per le attivita'. Fuori dalle 0-23 non
    # significa niente, quindi si riporta dentro invece di rifiutare la voce.
    for chiave, predefinito in (("ora_inizio", 0), ("ora_fine", 6)):
        try:
            voce[chiave] = max(0, min(23, int(voce.get(chiave, predefinito))))
        except (TypeError, ValueError):
            voce[chiave] = predefinito
    return voce


def voci(cfg):
    """Le voci configurate, normalizzate."""
    grezze = (cfg.get("rifiuti") or {}).get("voci") or []
    return [normalizza_voce(v, i) for i, v in enumerate(grezze)]


# ------------------------------------------------------------------ cadenze

def _occorrenza_nel_mese(giorno):
    """Quante volte quel giorno della settimana e' gia' capitato nel mese.

    Restituisce 1 per il primo martedi' del mese, 2 per il secondo, e cosi'
    via. Serve alle cadenze "1° e 3°", che **non** coincidono con "una
    settimana si' e una no": un mese puo' avere cinque martedi'.
    """
    return (giorno.day - 1) // 7 + 1


def cade(voce, giorno):
    """True se la voce prevede il servizio in quel giorno, cadenza compresa.

    Non guarda le eccezioni: quelle si applicano dopo, in `date`.
    """
    if not voce.get("attiva", True):
        return False
    if giorno.weekday() not in (voce.get("giorni") or []):
        return False

    cadenza = voce.get("cadenza", CADENZA_PREDEFINITA)
    if cadenza == "settimanale":
        return True
    if cadenza == "mensile_1_3":
        return _occorrenza_nel_mese(giorno) in (1, 3)
    if cadenza == "mensile_2_4":
        return _occorrenza_nel_mese(giorno) in (2, 4)
    if cadenza == "quindicinale":
        riferimento = voce.get("riferimento")
        if not riferimento:
            # Senza data di riferimento non si puo' sapere quale delle due
            # settimane e' quella buona. Meglio mostrarla tutte le settimane
            # che non mostrarla mai: un promemoria di troppo si ignora, uno
            # mancante fa perdere la raccolta.
            return True
        settimane = (giorno - _lunedi(riferimento)).days // 7
        return settimane % 2 == 0
    return True


def _lunedi(giorno):
    """Il lunedi' della settimana di quel giorno.

    Le settimane si contano da lunedi' a lunedi', non dalla data di
    riferimento in se': cosi' due voci ancorate a giorni diversi della stessa
    settimana restano in fase fra loro.
    """
    return giorno - datetime.timedelta(days=giorno.weekday())


# ---------------------------------------------------------------- eccezioni

def path(nome):
    return os.path.join(DATA_DIR, nome)


def _parse_eccezioni(testo):
    """`data,voce,nota` -> elenco di dizionari, piu' le righe scartate."""
    voci_lette = []
    errori = []
    righe = io.StringIO(testo or "")
    testo_pulito = "\n".join(r for r in righe.read().splitlines()
                             if r.strip() and not r.strip().startswith("#"))
    if not testo_pulito:
        return voci_lette, errori
    separatore = ";" if testo_pulito.count(";") > testo_pulito.count(",") else ","
    for numero, campi in enumerate(csv.reader(io.StringIO(testo_pulito),
                                              delimiter=separatore), 1):
        if not campi:
            continue
        data = parse_data(campi[0])
        if data is None:
            errori.append((numero, "data non valida: %s" % campi[0].strip()))
            continue
        voci_lette.append({
            "data": data,
            "voce": (campi[1].strip() if len(campi) > 1 else ""),
            "nota": (campi[2].strip() if len(campi) > 2 else ""),
        })
    return voci_lette, errori


def leggi_testo(nome):
    try:
        with open(path(nome), encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def salva_testo(nome, testo):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(path(nome), "w", encoding="utf-8") as handle:
        handle.write(testo if testo.endswith("\n") else testo + "\n")
    invalidate()


def eccezioni(nome, force=False):
    """Le eccezioni di un file, con cache sulla data di modifica."""
    percorso = path(nome)
    try:
        stato = os.stat(percorso)
        impronta = (stato.st_mtime, stato.st_size)
    except OSError:
        impronta = (0, 0)
    with _lock:
        memoria = _cache.get(nome)
        if memoria and not force and memoria[0] == impronta:
            return memoria[1]
    lette, errori = _parse_eccezioni(leggi_testo(nome))
    if errori:
        print("[rifiuti] %s: %d righe scartate (la prima alla %d)"
              % (nome, len(errori), errori[0][0]))
    with _lock:
        _cache[nome] = (impronta, lette)
    return lette


def invalidate():
    with _lock:
        _cache.clear()


def _riguarda(eccezione, voce):
    """Un'eccezione senza nome di voce vale per tutte."""
    nome = (eccezione.get("voce") or "").strip().lower()
    return not nome or nome == voce["nome"].strip().lower()


# ------------------------------------------------------------------- calendario

def date(voce, da, a):
    """Le date di servizio di una voce nell'intervallo, eccezioni comprese.

    L'ordine conta: prima si applica la regola, poi si tolgono le
    soppressioni, poi si aggiungono gli straordinari. Uno straordinario in un
    giorno soppresso resta — e' esattamente il caso del recupero dopo una
    festivita', e sarebbe assurdo che si annullassero a vicenda.
    """
    tolte = {e["data"] for e in eccezioni(SOPPRESSIONI) if _riguarda(e, voce)}
    aggiunte = {e["data"] for e in eccezioni(STRAORDINARI) if _riguarda(e, voce)}

    trovate = set()
    giorno = da
    while giorno <= a:
        if cade(voce, giorno) and giorno not in tolte:
            trovate.add(giorno)
        giorno += datetime.timedelta(days=1)
    trovate |= {g for g in aggiunte if da <= g <= a}
    return sorted(trovate)


def prossima(voce, oggi=None, orizzonte=120):
    """La prossima data di servizio, o None se non ce n'e' una vicina."""
    oggi = _oggi(oggi)
    elenco = date(voce, oggi, oggi + datetime.timedelta(days=orizzonte))
    return elenco[0] if elenco else None


def finestra(voce, giorno, cfg):
    """Da quando a quando il promemoria di quel servizio resta a schermo.

    Per un **rifiuto**: dalle 18 della sera prima alle 8 del giorno stesso.
    Si espone il bidone la sera e il messaggio sparisce dopo il passaggio;
    tenerlo oltre vorrebbe dire un pannello che ricorda una cosa gia' fatta.

    Per un'**attivita'**, cioe' un divieto di sosta: dallo stesso anticipo
    della sera prima — l'auto va spostata prima che cominci — fino alla
    **fine della fascia** del divieto, che ogni comune fissa a modo suo.
    """
    conf = cfg.get("rifiuti") or {}
    try:
        anticipo = max(0, min(23, int(conf.get("ora_avviso", 18))))
    except (TypeError, ValueError):
        anticipo = 18
    try:
        fine_rifiuto = max(0, min(23, int(conf.get("ora_fine", 8))))
    except (TypeError, ValueError):
        fine_rifiuto = 8

    inizio = datetime.datetime.combine(
        giorno - datetime.timedelta(days=1),
        datetime.time(hour=anticipo))
    if voce["tipo"] == "attivita":
        fine = datetime.datetime.combine(giorno,
                                         datetime.time(hour=voce["ora_fine"]))
        # Un divieto che finisce a mezzanotte vale fino a fine giornata, non
        # zero minuti dopo l'inizio del giorno.
        if voce["ora_fine"] <= voce["ora_inizio"]:
            fine += datetime.timedelta(days=1)
    else:
        fine = datetime.datetime.combine(giorno,
                                         datetime.time(hour=fine_rifiuto))
    return inizio, fine


def attive(cfg, adesso=None):
    """Le voci da mostrare in questo momento, nell'ordine di configurazione.

    Si guardano ieri, oggi e domani: una finestra comincia la sera prima e
    puo' scavalcare la mezzanotte, quindi il giorno di servizio non e'
    necessariamente quello di oggi.
    """
    adesso = adesso or datetime.datetime.now()
    oggi = adesso.date()
    risultato = []
    for voce in voci(cfg):
        if not voce.get("attiva", True) or not voce.get("giorni"):
            continue
        for scarto in (0, 1, 2):
            giorno = oggi - datetime.timedelta(days=1) + datetime.timedelta(days=scarto)
            if not cade(voce, giorno):
                continue
            if giorno in {e["data"] for e in eccezioni(SOPPRESSIONI)
                          if _riguarda(e, voce)}:
                continue
            inizio, fine = finestra(voce, giorno, cfg)
            if inizio <= adesso < fine:
                risultato.append(dict(voce, giorno=giorno,
                                      inizio=inizio, fine=fine))
                break
        else:
            # Anche uno straordinario deve comparire, e quello non passa da
            # `cade`: e' proprio il giorno che la regola non prevede.
            for e in eccezioni(STRAORDINARI):
                if not _riguarda(e, voce):
                    continue
                if abs((e["data"] - oggi).days) > 1:
                    continue
                inizio, fine = finestra(voce, e["data"], cfg)
                if inizio <= adesso < fine:
                    risultato.append(dict(voce, giorno=e["data"],
                                          inizio=inizio, fine=fine))
                    break
    return risultato


def stato(cfg, adesso=None):
    """Quadro completo per la web UI e per Home Assistant."""
    adesso = adesso or datetime.datetime.now()
    in_corso = {v["nome"] for v in attive(cfg, adesso)}
    elenco = []
    for voce in voci(cfg):
        successiva = prossima(voce, adesso.date())
        elenco.append({
            "nome": voce["nome"],
            "tipo": voce["tipo"],
            "colore": voce["colore"],
            "attiva": voce.get("attiva", True),
            "giorni": voce["giorni"],
            "cadenza": voce["cadenza"],
            "prossima": successiva,
            "esposizione": voce["nome"] in in_corso,
        })
    return elenco
