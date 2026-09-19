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
# Per quali tabelle il confronto con il modello e' gia' stato fatto in questo
# avvio. Senza, `ensure` rileggerebbe due file interi a ogni traduzione, e
# `load` la chiama per ogni aereo che passa.
_verificati = set()


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
        "d2931b107de1ea74a1fd1cf6a35a222a",   # 1.13 - 9.3
        "6a29839f1992a6a7dd41d1ab77b6db39",   # 9.4 - 9.5.1
        "f9c332a12de76c39365d6647bb226a8d",   # 9.6 - 9.7
    },
    "aircraft": {
        "0d763ff25342351827c349175789dcc4",   # 1.11 - 1.11.2
        "7a3e43b60e5e98ec2f8698fc02b4d959",   # 1.11.3 - 1.12.5
        "011ddce0813df36532e15c1fd86a98ac",   # 1.13 - 9.3
        "aeaca714e926f0f438ee76e65dcba9b4",   # 9.4 - 9.5.1
        "e76fc29500780cfc08ec9ed1b4f8ef0b",   # 9.6
        "025119b146b9b6749a089438ef67ec6c",   # 9.7
    },
    "airport": {
        "96678004b56af040372199f37aa1c08b",   # 1.11 - 1.11.2, solo codici IATA
        "8407e93552b46e74af88f19e1312626c",   # 1.11.3 - 1.12.5
        "4884b249008a42c68fbd2c1b934c0a68",   # 1.13 - 9.3
        "52431f16eb9451bf7a9155bca183293f",   # 9.4 - 9.5.1
        "af9645a5cefb12053581fdc2273e6762",   # 9.6
        "5b0c71eed0ec4d45202b032e78d78643",   # 9.7
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


def _righe_modello(kind):
    """Le righe del modello che traducono qualcosa: (codici, campi)."""
    try:
        with open(template(kind), encoding="utf-8", errors="replace") as handle:
            testo = handle.read()
    except OSError:
        return []
    sep = delimitatore(testo)
    fuori = []
    for riga in testo.splitlines():
        spoglia = riga.strip()
        if not spoglia or spoglia.startswith("#"):
            continue
        campi = next(csv.reader([riga], delimiter=sep), [])
        if len(campi) < 2 or not campi[0].strip() or not campi[1].strip():
            continue
        codici = [c.strip().upper() for c in campi[0].split("/") if c.strip()]
        if codici:
            fuori.append((codici, [c.strip() for c in campi]))
    return fuori


def _segnaposto(riga, sep):
    """I codici di una riga che non traduce niente, o lista vuota."""
    spoglia = riga.strip()
    if not spoglia or spoglia.startswith("#"):
        return []
    campi = next(csv.reader([riga], delimiter=sep), [])
    if not campi or not campi[0].strip():
        return []
    if len(campi) > 1 and campi[1].strip():
        return []
    return [c.strip().upper() for c in campi[0].split("/") if c.strip()]


def _fondi(kind, target):
    """Porta nel file dell'utente le righe del modello che gli mancano.

    E' la correzione di un difetto che si e' visto sul campo e che era grave
    quanto era invisibile. La regola vecchia aveva due sole uscite: o il file
    e' identico a un modello nostro e allora lo sostituisco tutto, o e' roba
    dell'utente e allora non lo tocco **mai piu'**. Bastava una riga in piu'
    per cadere per sempre nel secondo caso -- e a scriverla era il nostro
    stesso pulsante «Aggiungi in coda al file», che mette un `CODICE,,` come
    promemoria. Da quel momento nessun aggiornamento poteva piu' portare una
    tabella nuova: il pacchetto era giusto, il pannello no, e niente lo
    diceva.

    La regola nuova non sceglie piu' fra tutto e niente. **Le tue traduzioni
    vincono sempre**; del modello entra solo quello che nel tuo file non
    traduce nessuno. E i promemoria vuoti che adesso hanno una risposta se ne
    vanno, che e' la ragione per cui erano stati scritti.

    Una copia di sicurezza resta accanto, con lo stesso nome piu' `.bak`.
    """
    modello = _righe_modello(kind)
    if not modello:
        return 0
    try:
        with open(target, encoding="utf-8", errors="replace") as handle:
            testo = handle.read()
    except OSError:
        return 0

    tradotti, _ = parse(testo)
    mancanti, nuovi = [], set()
    for codici, campi in modello:
        if any(c in tradotti for c in codici):
            continue
        mancanti.append(campi)
        nuovi.update(codici)
    if not mancanti:
        return 0

    # Si scrive con il separatore che usa gia' lui: un file esportato da un
    # foglio di calcolo italiano ha i punti e virgola, e mescolarli renderebbe
    # illeggibile una delle due meta'.
    sep = delimitatore(testo)
    tenute, tolte = [], 0
    for riga in testo.splitlines():
        codici = _segnaposto(riga, sep)
        if codici and all(c in nuovi for c in codici):
            tolte += 1
            continue
        tenute.append(riga)

    fuori = io.StringIO()
    scrittore = csv.writer(fuori, delimiter=sep, lineterminator="\n")
    for campi in mancanti:
        scrittore.writerow(campi)

    try:
        import version
        quale = version.__version__
    except Exception:                       # pragma: no cover
        quale = time.strftime("%d/%m/%Y")

    corpo = "\n".join(tenute).rstrip("\n")
    nuovo = "%s\n\n# Arrivate con l'aggiornamento alla %s: righe che il\n" \
            "# modello conosce e questo file no. Le tue restano dove sono.\n%s" \
            % (corpo, quale, fuori.getvalue())

    try:
        shutil.copy2(target, target + ".bak")
        appoggio = target + ".nuovo"
        with open(appoggio, "w", encoding="utf-8") as handle:
            handle.write(nuovo)
        os.replace(appoggio, target)
    except OSError as exc:
        print("[lookup] impossibile fondere %s: %s" % (target, exc))
        return 0
    invalidate(kind)
    print("[lookup] %s: %d righe arrivate dal modello%s (copia in %s.bak)"
          % (os.path.basename(target), len(mancanti),
             ", %d promemoria completati" % tolte if tolte else "",
             os.path.basename(target)))
    return len(mancanti)


def ensure(kind):
    """Allinea il file dell'utente al modello, senza portargli via niente.

    Si guarda una volta sola per avvio: e' un controllo che legge due file
    interi, e `load` passa di qui a ogni traduzione.

    Quattro casi, in ordine:

    * il file **non c'e'** — si copia il modello;
    * il file non ha **nemmeno una riga valida** — e' il segnaposto scritto
      quando il modello non si trovava, e lasciarlo li' significherebbe non
      tradurre piu' niente per sempre: si sostituisce;
    * il file e' **ancora identico a un modello distribuito da noi**, quindi
      non e' mai stato aperto: si sostituisce, e non c'e' niente da salvare;
    * in tutti gli altri casi si **fonde**: vedi `_fondi`.
    """
    target = path(kind)
    if kind in _verificati and os.path.exists(target):
        return target
    if os.path.exists(target):
        motivo = ""
        if _vuoto(target):
            motivo = "era vuoto"
        elif _intatto(kind, target):
            motivo = "era ancora il modello di una versione precedente"
        source = template(kind)
        if not motivo:
            _fondi(kind, target)
        elif os.path.exists(source) and _impronta(source) != _impronta(target):
            try:
                shutil.copy2(source, target)
                invalidate(kind)
                print("[lookup] %s %s: aggiornato dal modello"
                      % (os.path.basename(target), motivo))
            except OSError as exc:
                print("[lookup] impossibile aggiornare %s: %s" % (target, exc))
        _verificati.add(kind)
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
    _verificati.add(kind)
    return target


def ricontrolla(kind=None):
    """Fa rifare il confronto con il modello al prossimo accesso.

    Serve al pulsante «Rileggi le tabelle» della pagina Radar: senza, il
    confronto si farebbe solo al riavvio del servizio, e chi ha appena
    corretto un file a mano dalla condivisione non avrebbe modo di chiedere
    la fusione adesso.
    """
    if kind is None:
        _verificati.clear()
    else:
        _verificati.discard(kind)


# ------------------------------------------------------------------ lettura

def delimitatore(text):
    """Il separatore con cui e' scritto questo CSV.

    I fogli di calcolo italiani esportano con il punto e virgola: si
    riconosce il separatore invece di pretenderne uno. Chi scrive in un file
    dell'utente deve usare **il suo**, non il nostro: mescolarli renderebbe
    illeggibile meta' del file al primo riconoscimento.
    """
    campione = "\n".join(riga for riga in (text or "").splitlines()[:40]
                         if riga.strip() and not riga.lstrip().startswith("#"))
    return ";" if campione.count(";") > campione.count(",") else ","


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

    delimiter = delimitatore(text)
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
    return "".join(_lookup("airport", pezzo, index) if sigla else pezzo
                   for sigla, pezzo in _pezzi_rotta(text))


def _pezzi_rotta(testo):
    """Spezza una rotta in (e' una sigla, testo), tenendo i separatori.

    Sta a parte perche' la regola di che cosa sia una sigla dentro `MXP→FCO`
    serve in due posti: qui per tradurre, e in `ricostruisci` per sapere quali
    sigle sono passate. Scriverla due volte vorrebbe dire due verita' che un
    giorno divergono.
    """
    testo = (testo or "").strip()
    if not testo:
        return []
    fuori = []
    token = ""
    for ch in testo:
        if ch.isalnum():
            token += ch
            continue
        if token:
            fuori.append((True, token))
            token = ""
        fuori.append((False, ch))
    if token:
        fuori.append((True, token))
    return fuori


def sigle_rotta(testo):
    """Le sole sigle dentro una rotta composta: `MXP→FCO` da' [MXP, FCO]."""
    return [pezzo for sigla, pezzo in _pezzi_rotta(testo) if sigla]


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

def note_unknown(kind, code, quando=None):
    quando = time.time() if quando is None else quando
    with _lock:
        bucket = _unknown.setdefault(kind, {})
        if code in bucket:
            bucket[code][0] += 1
            bucket[code][1] = max(bucket[code][1], quando)
        elif len(bucket) < MAX_UNKNOWN:
            bucket[code] = [1, quando]


def ricostruisci(percorso, massimo=20000):
    """Rilegge il registro dei voli e rimette in piedi l'elenco dei codici ignoti.

    Il difetto che ripara e' di quelli che si vedono solo usando la macchina
    per giorni. L'elenco delle sigle sconosciute vive in memoria, quindi a
    ogni riavvio del servizio tornava vuoto: la pagina diceva «niente da
    aggiungere» mentre nel registro c'erano centinaia di passaggi non
    tradotti. Era la lista della spesa, e si cancellava da sola ogni notte.

    Il modo in cui si ricostruisce e' l'unico che non introduce una seconda
    verita': si **ripassa il registro dalla stessa porta** da cui passa un
    aereo vero. Non si riscrive qui la regola che distingue una compagnia da
    un'immatricolazione, ne' quella che spacca una rotta nei due aeroporti:
    si chiamano le stesse funzioni, e loro chiamano `note_unknown` da se'. Il
    giorno in cui una di quelle regole cambiera', questa funzione cambiera'
    con lei senza che nessuno se ne debba ricordare.

    Si leggono le ultime `massimo` righe e non tutte: un registro di un anno
    sono decine di migliaia di voli, e riprocessarli all'avvio del servizio
    vorrebbe dire un pannello fermo per qualche secondo. Le piu' recenti
    sono anche quelle che contano, perche' la domanda e' «cosa mi passa sopra
    casa adesso».
    """
    try:
        with open(percorso, newline="", encoding="utf8") as handle:
            righe = list(csv.DictReader(handle))
    except (OSError, UnicodeDecodeError, csv.Error):
        return 0
    if not righe:
        return 0
    for riga in righe[-massimo:]:
        quando = _istante(riga.get("timestamp"))
        tipo = (riga.get("type") or "").strip()
        if tipo:
            _ignoto_se_serve("aircraft", tipo, quando)
        for codice in sigle_rotta(riga.get("route") or ""):
            _ignoto_se_serve("airport", codice, quando)
        prefisso = callsign_prefix(riga.get("callsign") or "")
        if prefisso:
            _ignoto_se_serve("airline", prefisso, quando)
    return len(righe[-massimo:])


def _ignoto_se_serve(kind, codice, quando):
    """Segna il codice come ignoto se la tabella non lo conosce."""
    codice = (codice or "").strip().upper()
    if not codice or load(kind).get(codice) is not None:
        return
    note_unknown(kind, codice, quando)


def _istante(testo):
    """Il timestamp del registro in secondi. Adesso, se non si capisce."""
    try:
        return time.mktime(time.strptime((testo or "").strip(),
                                         "%Y-%m-%dT%H:%M:%S"))
    except (ValueError, TypeError, OverflowError):
        return time.time()


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
        # Il separatore e' il suo, non il nostro: un file esportato da un
        # foglio di calcolo italiano ha i punti e virgola, e due righe con il
        # separatore sbagliato diventano righe rotte al riconoscimento.
        with open(target, encoding="utf-8", errors="replace") as handle:
            sep = delimitatore(handle.read())
    except OSError:
        sep = ","
    try:
        with open(target, "a", encoding="utf-8") as handle:
            handle.write("\n# aggiunti automaticamente il %s: completa le due\n"
                         "# colonne mancanti con la forma breve e il nome esteso\n"
                         % time.strftime("%d/%m/%Y"))
            for code in nuovi:
                handle.write("%s%s%s\n" % (code, sep, sep))
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
