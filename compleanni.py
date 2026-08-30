"""Promemoria di compleanni e anniversari.

Un elenco di date e nomi, e la domanda a cui rispondere e' una sola: quale
ricorrenza e' abbastanza vicina perche' valga la pena ricordarla adesso.

Il file vive in /var/lib/dmd/compleanni.csv e ha tre campi, l'ultimo
facoltativo:

    data,nome,tipo
    30/03/1976,Mario Rossi
    12/06/2005,Anna e Luca,anniversario

Il tipo distingue che cosa si festeggia, perche' cambia la frase: di un
compleanno si dice che *compie gli anni*, di un anniversario che lo
*festeggia*, e dire "compie gli anni" di un matrimonio sarebbe sbagliato.
Manca il tipo? E' un compleanno: e' il caso di gran lunga piu' frequente, e
un elenco scritto prima che questo campo esistesse continua a funzionare.

L'anno e' facoltativo: `30/03` funziona, ma senza anno non si puo' dire
quanti anni compie. Il giorno viene prima del mese, come si scrive in
italiano — accettare anche il formato americano avrebbe reso ambiguo
`03/04`, e un promemoria sbagliato di un mese e' peggio di nessun promemoria.

Le date sono ricorrenze annuali, quindi il calcolo dell'anticipo deve
scavalcare il capodanno: il 30 dicembre, un compleanno del 1 gennaio e' fra
due giorni, non fra trecentosessantatre'.
"""

import csv
import datetime
import io
import os
import shutil
import threading

DATA_DIR = os.environ.get("DMD_DATA", "/var/lib/dmd")
FILE_NAME = "compleanni.csv"

# Tipi di ricorrenza. La chiave e' quella che si scrive nel file; il valore e'
# solo per l'ordine nei menu.
TIPI = ("compleanno", "anniversario")
TIPO_PREDEFINITO = "compleanno"

INTESTAZIONE = (
    "# Compleanni e anniversari: una riga per ricorrenza.\n"
    "#\n"
    "#   data,nome,tipo\n"
    "#   30/03/1976,Mario Rossi\n"
    "#   12/06/2005,Anna e Luca,anniversario\n"
    "#\n"
    "# La data e' giorno/mese/anno. L'anno si puo' omettere (30/03), ma senza\n"
    "# non si puo' mostrare quanti anni sono. Il tipo e' facoltativo: senza,\n"
    "# vale compleanno. Righe che iniziano con # sono commenti.\n"
)

_lock = threading.Lock()
_cache = None      # (impronta, voci)


def path():
    return os.path.join(DATA_DIR, FILE_NAME)


def ensure():
    target = path()
    if os.path.exists(target):
        return target
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(target, "w", encoding="utf-8") as handle:
            handle.write(INTESTAZIONE)
    except OSError as exc:
        print("[compleanni] impossibile creare %s: %s" % (target, exc))
    return target


# ------------------------------------------------------------------ lettura

def parse_data(testo):
    """'30/03/1976' o '30/03' -> (giorno, mese, anno|None). None se illeggibile."""
    testo = (testo or "").strip().replace(".", "/").replace("-", "/")
    parti = [p for p in testo.split("/") if p != ""]
    if len(parti) < 2:
        return None
    try:
        giorno = int(parti[0])
        mese = int(parti[1])
        anno = int(parti[2]) if len(parti) > 2 else None
    except ValueError:
        return None
    if anno is not None and anno < 100:
        # Due cifre: 26 e' il 2026, 76 e' il 1976. La soglia sta sull'anno
        # corrente, cosi' non invecchia da sola.
        soglia = datetime.date.today().year % 100
        anno += 2000 if anno <= soglia else 1900
    if not (1 <= mese <= 12) or not (1 <= giorno <= 31):
        return None
    # Il 29 febbraio esiste solo negli anni bisestili: la validazione usa un
    # anno bisestile apposta, per non rifiutare chi c'e' nato davvero.
    try:
        datetime.date(2000, mese, giorno)
    except ValueError:
        return None
    return (giorno, mese, anno)


def parse(testo):
    """Legge il CSV e restituisce (voci, errori)."""
    voci = []
    errori = []
    if not testo:
        return voci, errori

    campione = "\n".join(r for r in testo.splitlines()[:40]
                         if r.strip() and not r.lstrip().startswith("#"))
    delimiter = ";" if campione.count(";") > campione.count(",") else ","

    for numero, riga in enumerate(csv.reader(io.StringIO(testo), delimiter=delimiter), 1):
        if not riga or not any(c.strip() for c in riga):
            continue
        if riga[0].lstrip().startswith("#"):
            continue
        if len(riga) < 2:
            errori.append((numero, "servono data e nome", delimiter.join(riga)[:60]))
            continue
        data = parse_data(riga[0])
        nome = riga[1].strip()
        if data is None:
            errori.append((numero, "data non valida", riga[0].strip()[:40]))
            continue
        if not nome:
            errori.append((numero, "nome mancante", riga[0].strip()[:40]))
            continue
        tipo = (riga[2].strip().lower() if len(riga) > 2 else "") or TIPO_PREDEFINITO
        if tipo not in TIPI:
            # Un tipo sconosciuto non fa scartare la riga: la ricorrenza c'e'
            # comunque, e perderla per una parola scritta male sarebbe un
            # pessimo scambio.
            errori.append((numero, "tipo sconosciuto, uso compleanno", tipo[:20]))
            tipo = TIPO_PREDEFINITO
        voci.append({"giorno": data[0], "mese": data[1], "anno": data[2],
                     "nome": nome, "tipo": tipo})
    return voci, errori


def load(force=False):
    global _cache
    target = ensure()
    try:
        info = os.stat(target)
        impronta = (info.st_mtime, info.st_size)
    except OSError:
        impronta = (0, 0)

    with _lock:
        if _cache and not force and _cache[0] == impronta:
            return _cache[1]

    try:
        with open(target, encoding="utf-8", errors="replace") as handle:
            voci, errori = parse(handle.read())
    except OSError as exc:
        print("[compleanni] %s illeggibile: %s" % (target, exc))
        voci, errori = [], []

    if errori:
        print("[compleanni] %d righe scartate (la prima alla %d)"
              % (len(errori), errori[0][0]))

    with _lock:
        _cache = (impronta, voci)
    return voci


def invalidate():
    global _cache
    with _lock:
        _cache = None


# ------------------------------------------------------------------ ricorrenze

def giorni_mancanti(voce, oggi=None):
    """Quanti giorni mancano alla prossima ricorrenza. 0 = oggi.

    Il conto scavalca il capodanno: a fine dicembre un compleanno di gennaio
    e' vicino, non lontano un anno.
    """
    oggi = oggi or datetime.date.today()
    giorno, mese = voce["giorno"], voce["mese"]
    for anno in (oggi.year, oggi.year + 1):
        try:
            data = datetime.date(anno, mese, giorno)
        except ValueError:
            # 29 febbraio in un anno non bisestile: si festeggia il 1 marzo,
            # che e' la convenzione piu' diffusa e non salta l'anno.
            data = datetime.date(anno, 3, 1)
        if data >= oggi:
            return (data - oggi).days
    return 366


def eta(voce, oggi=None):
    """Anni alla prossima ricorrenza, o None se l'anno non c'e'.

    Per un compleanno sono gli anni che compie, per un anniversario quelli
    che si festeggiano: il conto e' lo stesso, cambia solo come lo si dice.
    """
    if not voce.get("anno"):
        return None
    oggi = oggi or datetime.date.today()
    mancano = giorni_mancanti(voce, oggi)
    anno_festa = (oggi + datetime.timedelta(days=mancano)).year
    return anno_festa - voce["anno"]


def imminenti(lead_hours=48, oggi=None):
    """Chi compie gli anni entro l'anticipo indicato, dal piu' vicino.

    L'anticipo si esprime in ore perche' e' cosi' che lo si pensa — "due
    giorni prima" — ma il confronto e' in giorni: un compleanno non ha un'ora.
    Si arrotonda per eccesso, cosi' 48 ore includono davvero dopodomani.
    """
    giorni = max(0, int((lead_hours + 23) // 24))
    fuori = []
    for voce in load():
        mancano = giorni_mancanti(voce, oggi)
        if mancano <= giorni:
            copia = dict(voce)
            copia["mancano"] = mancano
            copia["eta"] = eta(voce, oggi)
            fuori.append(copia)
    fuori.sort(key=lambda v: (v["mancano"], v["nome"]))
    return fuori


# ------------------------------------------------------------------ scrittura

def read_text():
    try:
        with open(ensure(), encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def save(testo):
    """Scrive il file, con copia di sicurezza. Restituisce (voci, errori)."""
    voci, errori = parse(testo)
    target = path()
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        if os.path.exists(target):
            shutil.copy2(target, target + ".bak")
        tmp = target + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            handle.write(testo if testo.endswith("\n") else testo + "\n")
        os.replace(tmp, target)
    except OSError as exc:
        errori.append((0, "scrittura non riuscita: %s" % exc, ""))
        return voci, errori
    invalidate()
    return voci, errori


def aggiungi(data, nome, tipo=TIPO_PREDEFINITO):
    """Aggiunge una ricorrenza in coda. Restituisce un errore o ''."""
    if parse_data(data) is None:
        return "data non valida"
    nome = (nome or "").strip()
    if not nome:
        return "nome mancante"
    if "," in nome or ";" in nome:
        nome = nome.replace(",", " ").replace(";", " ")
    target = ensure()
    try:
        with open(target, "a", encoding="utf-8") as handle:
            tipo = tipo if tipo in TIPI else TIPO_PREDEFINITO
            handle.write("%s,%s,%s\n" % (data.strip(), nome, tipo))
    except OSError as exc:
        return "scrittura non riuscita: %s" % exc
    invalidate()
    return ""


def stats():
    voci = load()
    prossimi = imminenti(24 * 366)
    return {
        "path": path(),
        "count": len(voci),
        "prossimo": prossimi[0] if prossimi else None,
    }
