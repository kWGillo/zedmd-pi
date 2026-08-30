"""Da codice a nome: aerei, aeroporti e compagnie.

Il radar riceve sigle. Il tipo di aeromobile arriva come **designatore ICAO**
(`B738`, `A20N`). Gli aeroporti delle rotte arrivano **in due grafie**: il
servizio routeset di adsb.lol risponde con i codici IATA di tre lettere
(`MXP`), ma quando quel campo manca si ripiega sui codici ICAO di quattro
(`LIMC`), e lo stesso vale per la seconda fonte, hexdb.io. Una tabella che
conoscesse una sola delle due grafie lascerebbe meta' dei voli senza
traduzione — che e' esattamente quello che succedeva nella 1.11.

La compagnia non arriva come campo a se': sta nelle prime tre lettere del
nominativo di volo. In `AFR1732` la compagnia e' `AFR`, Air France.

Le conversioni stanno in tre file CSV, uno per tipo, modificabili a mano.
Ogni riga ha tre campi:

    codice,forma breve,nome completo
    B738,737-800,Boeing 737-800

Nella prima colonna possono stare **piu' codici separati da `/`**, e la riga
risponde a tutti. E' cosi' che un aeroporto porta entrambe le grafie senza
doverne tenere allineate due righe:

    MXP/LIMC,Malpensa,Milano Malpensa

Servono due forme perche' il pannello e' largo 256 pixel e la riga del radar
porta gia' rotta, quota, velocita' e distanza: "Boeing 737-800" non ci sta,
"737-800" si'. Il nome completo va nella web UI e nel registro dei passaggi,
dove lo spazio non manca.

**Un codice che non e' in tabella viene mostrato com'e'.** Non e' un errore:
e' il comportamento previsto, e il sistema tiene il conto di quelli che
incontra senza saperli tradurre, cosi' la pagina Radar puo' dirti che cosa
conviene aggiungere per primo invece di lasciartelo indovinare.

I file vivono in /var/lib/dmd e **quello che ci scrivi tu non viene mai
toccato dagli aggiornamenti**: /opt/dmd viene riscritto a ogni installazione,
e le tue aggiunte sparirebbero senza che tu te ne accorga. Al primo avvio
vengono copiati da un modello contenuto nel pacchetto; da quel momento sono
tuoi. L'unico caso in cui un aggiornamento li sostituisce e' quando sono
ancora *identici* a un modello distribuito da noi, quindi mai aperti: allora
non c'e' niente da salvare e tenersi una tabella vecchia sarebbe solo un
danno.
"""

import csv
import hashlib
import io
import os
import shutil
import threading
import time

# Dove vivono i file dell'utente. Fuori da /opt/dmd, di proposito.
DATA_DIR = os.environ.get("DMD_DATA", "/var/lib/dmd")

# I modelli distribuiti con il pacchetto, usati solo per creare i file la
# prima volta. Stanno nella cartella del programma e non in una sottocartella
# di proposito: l'aggiornamento via rete lo esegue il codice della versione
# *precedente*, che conosce l'elenco dei file dal manifest ma le sottocartelle
# da copiare le ha cablate. Una cartella nuova non verrebbe copiata, e le
# tabelle arriverebbero vuote. In cima all'installazione ci arrivano sempre.
TEMPLATE_DIR = os.environ.get(
    "DMD_TEMPLATES", os.path.dirname(os.path.abspath(__file__)))

KINDS = {
    "aircraft": "aerei.csv",
    "airport": "aeroporti.csv",
    "airline": "compagnie.csv",
}

# Quanti codici sconosciuti tenere in memoria. Un tetto serve: senza, una
# sorgente impazzita farebbe crescere il dizionario senza fine.
MAX_UNKNOWN = 500

_lock = threading.Lock()
_cache = {}      # kind -> (mtime, dimensione, dizionario)
_unknown = {}    # kind -> {codice: [conteggio, ultimo avvistamento]}


# ------------------------------------------------------------------ percorsi

def path(kind):
    return os.path.join(DATA_DIR, KINDS[kind])


def template(kind):
    return os.path.join(TEMPLATE_DIR, KINDS[kind])


# Impronte dei modelli gia' distribuiti in passato. Un file dell'utente che
# corrisponde a una di queste non e' mai stato toccato: e' la copia di un
# modello vecchio, e sostituirla con quello nuovo non porta via niente. E'
# lo stesso criterio con cui i gestori di pacchetti trattano i file di
# configurazione. Ogni versione che cambia un modello aggiunge qui l'impronta
# di quello che sostituisce, mai togliendo le precedenti.
DISTRIBUITI = {
    "airline": {
        "485c739df2710e5f1e03b4ec71276031",   # 1.12 - 1.12.5
    },
    "aircraft": {
        "0d763ff25342351827c349175789dcc4",   # 1.11 - 1.11.2
        "7a3e43b60e5e98ec2f8698fc02b4d959",   # 1.11.3 - 1.12.5
    },
    "airport": {
        "96678004b56af040372199f37aa1c08b",   # 1.11 - 1.11.2, solo codici IATA
        "8407e93552b46e74af88f19e1312626c",   # 1.11.3 - 1.12.5
    },
}


def _impronta(percorso):
    try:
        with open(percorso, "rb") as handle:
            return hashlib.md5(handle.read()).hexdigest()
    except OSError:
        return ""


def _intatto(kind, target):
    """Vero se il file dell'utente e' ancora un modello distribuito da noi."""
    return _impronta(target) in DISTRIBUITI.get(kind, set())


def _vuoto(target):
    """Vero se il file non contiene nessuna conversione utilizzabile.

    Un file cosi' non porta lavoro dell'utente: o e' il segnaposto scritto
    quando il modello non si trovava, o e' stato svuotato per sbaglio.
    """
    try:
        with open(target, encoding="utf-8", errors="replace") as handle:
            entries, _ = parse(handle.read())
        return not entries
    except OSError:
        return False


def ensure(kind):
    """Crea il file dell'utente dal modello, se non c'e' ancora.

    Un file che porta lavoro dell'utente non viene mai sovrascritto. Ci sono
    due eccezioni, e in nessuna delle due c'e' qualcosa da perdere:

    * il file non ha **nemmeno una riga valida** — e' il segnaposto scritto
      quando il modello non si trovava, e lasciarlo li' significherebbe non
      tradurre piu' niente per sempre;
    * il file e' **ancora identico a un modello che abbiamo distribuito
      noi**, quindi non e' mai stato aperto. Chi si e' fermato alla tabella
      della 1.11, che conosceva solo i codici IATA, riceve cosi' quella con
      entrambe le grafie senza doverla chiedere.
    """
    target = path(kind)
    if os.path.exists(target):
        motivo = ""
        if _vuoto(target):
            motivo = "era vuoto"
        elif _intatto(kind, target):
            motivo = "era ancora il modello di una versione precedente"
        if not motivo:
            return target
        source = template(kind)
        if os.path.exists(source) and _impronta(source) != _impronta(target):
            try:
                shutil.copy2(source, target)
                invalidate(kind)
                print("[lookup] %s %s: aggiornato dal modello"
                      % (os.path.basename(target), motivo))
            except OSError as exc:
                print("[lookup] impossibile aggiornare %s: %s" % (target, exc))
        return target
    source = template(kind)
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        if os.path.exists(source):
            shutil.copy2(source, target)
        else:
            with open(target, "w", encoding="utf-8") as handle:
                handle.write("# codice,forma breve,nome completo\n")
    except OSError as exc:
        print("[lookup] impossibile creare %s: %s" % (target, exc))
    return target


# ------------------------------------------------------------------ lettura

def parse(text):
    """Legge un CSV e restituisce (voci, errori).

    Gli errori non fermano la lettura: una riga sbagliata si perde da sola e
    tutte le altre restano valide. E' la ragione per cui questo file e' un
    CSV e non un XML, dove un tag non chiuso porta via tutto il resto.
    """
    entries = {}
    errors = []
    if not text:
        return entries, errors

    # I fogli di calcolo italiani esportano con il punto e virgola: si
    # riconosce il separatore invece di pretenderne uno.
    campione = "\n".join(riga for riga in text.splitlines()[:40]
                         if riga.strip() and not riga.lstrip().startswith("#"))
    delimiter = ";" if campione.count(";") > campione.count(",") else ","

    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    for number, row in enumerate(reader, 1):
        if not row or not any(cell.strip() for cell in row):
            continue
        if row[0].lstrip().startswith("#"):
            continue
        if len(row) < 2:
            errors.append((number, "servono almeno codice e forma breve",
                           delimiter.join(row)[:60]))
            continue
        # Piu' codici per la stessa riga, separati da `/`: un aeroporto ha un
        # codice IATA di tre lettere e uno ICAO di quattro, e a seconda di
        # cosa risponde il servizio delle rotte arriva l'uno o l'altro.
        # Scriverli sulla stessa riga evita di dover tenere allineate due
        # righe che dicono la stessa cosa.
        codes = [c.strip().upper() for c in row[0].split("/") if c.strip()]
        short_form = row[1].strip()
        full_form = row[2].strip() if len(row) > 2 and row[2].strip() else short_form
        if not codes:
            errors.append((number, "codice vuoto", delimiter.join(row)[:60]))
            continue
        if not short_form:
            # Riga segnaposto: il codice c'e' ma la traduzione no. Non e' un
            # errore, e' un promemoria lasciato in sospeso.
            continue
        # Forma preferita per il pannello: la sigla di tre lettere, cioe' la
        # IATA. Sul display "MXP" dice quanto "LIMC" in tre caratteri invece
        # di quattro, e la si riconosce dal biglietto. Se la riga non ne ha
        # una da tre, resta il primo codice scritto.
        preferito = next((c for c in codes if len(c) == 3), codes[0])
        for code in codes:
            if code in entries:
                errors.append((number, "codice ripetuto: %s" % code, short_form))
                continue
            entries[code] = (short_form, full_form, preferito)
    return entries, errors


def load(kind, force=False):
    """Voci del file, rilette quando cambia sul disco.

    Il controllo su data e dimensione fa si' che una modifica fatta via SSH o
    dalla condivisione SMB venga raccolta senza riavviare il servizio.
    """
    target = ensure(kind)
    try:
        info = os.stat(target)
        stamp = (info.st_mtime, info.st_size)
    except OSError:
        stamp = (0, 0)

    with _lock:
        cached = _cache.get(kind)
        if cached and not force and cached[0] == stamp:
            return cached[1]

    try:
        with open(target, encoding="utf-8", errors="replace") as handle:
            entries, errors = parse(handle.read())
    except OSError as exc:
        print("[lookup] %s illeggibile: %s" % (target, exc))
        entries, errors = {}, []

    if errors:
        print("[lookup] %s: %d righe scartate (la prima alla %d)"
              % (os.path.basename(target), len(errors), errors[0][0]))

    with _lock:
        _cache[kind] = (stamp, entries)
    return entries


def invalidate(kind=None):
    with _lock:
        if kind is None:
            _cache.clear()
        else:
            _cache.pop(kind, None)


# ------------------------------------------------------------ conversione

def _lookup(kind, code, index):
    code = (code or "").strip().upper()
    if not code:
        return ""
    entry = load(kind).get(code)
    if entry is None:
        note_unknown(kind, code)
        return code
    return entry[index]


def short(kind, code):
    """Forma breve per il pannello, o il codice stesso se non e' in tabella."""
    return _lookup(kind, code, 0)


def preferred(kind, code):
    """La sigla da mostrare: quella di tre lettere se la tabella la conosce.

    Il servizio delle rotte risponde a volte in IATA e a volte in ICAO, e non
    si puo' scegliere. Qui si sceglie come *mostrarla*, e la forma corta e'
    quella che si legge sul biglietto.
    """
    return _lookup(kind, code, 2)


def codes(text, kind="airport"):
    """Traduce una rotta gia' composta nelle sole sigle preferite."""
    return route(text, index=2)


def full(kind, code):
    """Nome completo per la web UI e il registro."""
    return _lookup(kind, code, 1)


def route(text, index=0):
    """Traduce una rotta gia' composta, del tipo `MXP→FCO`.

    Si conservano i separatori originali: cambia solo cio' che sta in mezzo.
    """
    text = (text or "").strip()
    if not text:
        return ""
    out = []
    token = ""
    for ch in text:
        if ch.isalnum():
            token += ch
        else:
            if token:
                out.append(_lookup("airport", token, index))
                token = ""
            out.append(ch)
    if token:
        out.append(_lookup("airport", token, index))
    return "".join(out)


def callsign_prefix(callsign):
    """Le lettere iniziali del nominativo, che sono la compagnia.

    In `AFR1732` la compagnia e' `AFR`: tre lettere e poi il numero di volo.
    Non tutti i nominativi hanno questa forma — l'aviazione generale usa
    l'immatricolazione, `I-ABCD`, e li' non c'e' nessuna compagnia da
    trovare. Per questo si accetta solo un prefisso di **tre lettere seguito
    da una cifra**: e' la forma dei voli di linea, e non rischia di
    scambiare una targa per una sigla.
    """
    text = (callsign or "").strip().upper()
    if len(text) < 4:
        return ""
    prefix, rest = text[:3], text[3:]
    if prefix.isalpha() and rest[:1].isdigit():
        return prefix
    return ""


def airline(callsign, index=0):
    """Compagnia di un nominativo, vuoto se il nominativo non ne ha una."""
    prefix = callsign_prefix(callsign)
    if not prefix:
        return ""
    return _lookup("airline", prefix, index)


# --------------------------------------------------------- codici mancanti

def note_unknown(kind, code):
    with _lock:
        bucket = _unknown.setdefault(kind, {})
        if code in bucket:
            bucket[code][0] += 1
            bucket[code][1] = time.time()
        elif len(bucket) < MAX_UNKNOWN:
            bucket[code] = [1, time.time()]


def unknown(kind=None):
    """Codici incontrati e non tradotti, dal piu' frequente.

    E' la lista della spesa: dice che cosa conviene aggiungere per primo,
    ordinato per quante volte e' passato davvero sopra casa.
    """
    with _lock:
        kinds = [kind] if kind else list(_unknown)
        out = []
        for name in kinds:
            for code, (count, last) in (_unknown.get(name) or {}).items():
                out.append({"kind": name, "code": code,
                            "count": count, "last": last})
    out.sort(key=lambda item: (-item["count"], item["code"]))
    return out


def forget_unknown(kind=None):
    with _lock:
        if kind is None:
            _unknown.clear()
        else:
            _unknown.pop(kind, None)


# ------------------------------------------------------------- scrittura

def read_text(kind):
    try:
        with open(ensure(kind), encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def save(kind, text):
    """Scrive il file dell'utente, conservando una copia del precedente.

    Restituisce (voci_valide, errori). Il file viene scritto comunque, anche
    con qualche riga sbagliata: le righe buone continuano a funzionare e
    l'utente vede l'elenco di quelle da correggere. Rifiutare tutto per un
    refuso costringerebbe a ricominciare da capo.
    """
    entries, errors = parse(text)
    target = path(kind)
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        if os.path.exists(target):
            shutil.copy2(target, target + ".bak")
        tmp = target + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            handle.write(text if text.endswith("\n") else text + "\n")
        os.replace(tmp, target)
    except OSError as exc:
        errors.append((0, "scrittura non riuscita: %s" % exc, ""))
        return entries, errors
    invalidate(kind)
    return entries, errors


def append_missing(kind, codes):
    """Aggiunge in coda i codici indicati, come righe da completare.

    La forma breve resta vuota: la riga non traduce nulla finche' non la si
    riempie, ma il codice e' li' e non va piu' cercato.
    """
    codes = [c.strip().upper() for c in codes if c and c.strip()]
    if not codes:
        return 0
    known = load(kind)
    nuovi = [c for c in dict.fromkeys(codes) if c not in known]
    if not nuovi:
        return 0
    target = ensure(kind)
    try:
        with open(target, "a", encoding="utf-8") as handle:
            handle.write("\n# aggiunti automaticamente il %s: completa le due\n"
                         "# colonne mancanti con la forma breve e il nome esteso\n"
                         % time.strftime("%d/%m/%Y"))
            for code in nuovi:
                handle.write("%s,,\n" % code)
    except OSError as exc:
        print("[lookup] impossibile aggiungere a %s: %s" % (target, exc))
        return 0
    invalidate(kind)
    return len(nuovi)


def stats(kind):
    entries = load(kind)
    return {
        "kind": kind,
        "path": path(kind),
        "count": len(entries),
        "unknown": len(_unknown.get(kind) or {}),
    }
