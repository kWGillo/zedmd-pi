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
import urllib.parse
import urllib.request

import compleanni

DATA_DIR = os.environ.get("DMD_DATA", "/var/lib/dmd")
QUI = os.path.dirname(os.path.abspath(__file__))

SANTI = "santi.csv"
GIORNATE = "giornate.csv"
CACHE = "inutili.json"

# L'API di Wikimedia.
#
# **Il feed italiano non ha nati e morti.** Risponde 200 e una lista vuota,
# sempre, per tutti i giorni dell'anno: quelle due sezioni su it.wikipedia
# semplicemente non ci sono. E' il motivo per cui la schermata "Accadde oggi"
# non compariva mai, e non c'era modo di accorgersene guardando il codice --
# la chiamata riusciva.
#
# Quindi si chiede all'inglese, che le ha, e poi si **traducono i nomi**: i
# titoli inglesi si passano a `langlinks`, che per ciascuno da' il titolo
# italiano quando la voce esiste anche da noi (Charles the Bald -> Carlo il
# Calvo). Le descrizioni brevi si prendono in italiano con una seconda
# chiamata, che nello stesso giro chiede anche quante volte quella pagina e'
# stata letta nell'ultimo mese: e' il metro con cui si sceglie chi mostrare.
# I titoli vanno a gruppi di cinquanta, che e' il massimo per chiamata: una
# manciata di richieste al giorno in tutto.
API = "https://%s.wikipedia.org/api/rest_v1/feed/onthisday/%s/%02d/%02d"
LINGUA = "it"
LINGUA_FEED = "en"
API_QUERY = "https://%s.wikipedia.org/w/api.php"
# Wikimedia chiede di presentarsi. Un programma che non lo fa viene rifiutato,
# ed e' giusto cosi': si sa chi sta chiedendo e a chi scrivere se esagera.
AGENTE = "zedmd-pi/1.0 (https://github.com/kWGillo/zedmd-pi) info-inutili"
TIMEOUT = 12
QUANTI = 6                  # nati e morti da tenere in cache, per tipo
ROSA = 40                   # tetto ai candidati per tipo, prima di scegliere
GIORNI_VISTE = 30           # su quanti giorni si contano le letture
EVENTI = 8                  # fatti storici da tenere in cache
MESI_IT = ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
           "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre")
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
    """Le giornate del giorno: {MM-GG: [(titolo, goliardica), ...]}.

    La terza colonna, quando c'e', dice `pop`: e' una giornata goliardica o
    minore -- il gatto nero, il pane alle banane, Festivus. Serve a tenerle
    **sotto** quelle ufficiali senza doverle mettere in un file a parte: il
    17 marzo passa la giornata del sonno prima di quella del panda, ma il 25
    settembre, dove di ufficiale non c'e' niente, il farmacista e' meglio del
    vuoto. Un file dell'utente scritto in due colonne vale ufficiale, ed e'
    giusto: le sue vincono.
    """
    def costruisci(righe):
        tavola = {}
        for riga in righe:
            pezzi = riga.split(";")
            if len(pezzi) < 2 or not pezzi[1].strip():
                continue
            goliardica = len(pezzi) > 2 and pezzi[2].strip().lower() == "pop"
            tavola.setdefault(pezzi[0].strip(), []).append(
                (pezzi[1].strip(), goliardica))
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

    Quando ce n'e' piu' d'una vince **la piu' seria**, e a parita' la piu'
    corta: sul pannello ci sta, e nella pratica e' quasi sempre anche quella
    che la gente conosce -- "Giornata mondiale dell'acqua" contro "Giornata
    internazionale per la prevenzione dell'estremismo violento".
    """
    voci = _giornate().get(chiave(quando)) or []
    if not voci:
        return ""
    return min(voci, key=lambda v: (v[1], len(v[0])))[0]


def giornate_del_giorno(quando=None):
    """I titoli delle giornate di oggi, dalla piu' seria alla piu' scema."""
    voci = _giornate().get(chiave(quando)) or []
    return [t for t, _ in sorted(voci, key=lambda v: (v[1], len(v[0])))]


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


def _query(lingua, parametri):
    """Una chiamata all'API classica di MediaWiki. Torna {} se va storta:
    e' una rifinitura, non deve poter far fallire il resto."""
    parametri = dict(parametri)
    parametri.setdefault("format", "json")
    parametri.setdefault("formatversion", "2")
    url = "%s?%s" % (API_QUERY % lingua, urllib.parse.urlencode(parametri))
    try:
        return _chiedi(url) or {}
    except (urllib.error.URLError, OSError, ValueError):
        return {}


def _a_pezzi(titoli, quanti=50):
    """I titoli a gruppi: l'API ne accetta cinquanta per volta."""
    return [titoli[i:i + quanti] for i in range(0, len(titoli), quanti)]


def _pagine(dati):
    """L'elenco delle pagine di una risposta, nei due formatversion."""
    pagine = ((dati.get("query") or {}).get("pages")) or []
    if isinstance(pagine, dict):                  # formatversion 1
        pagine = list(pagine.values())
    return pagine


def _in_italiano(titoli):
    """{titolo inglese: titolo italiano} per quelli che da noi esistono."""
    fuori = {}
    for gruppo in _a_pezzi(titoli):
        dati = _query(LINGUA_FEED, {"action": "query", "prop": "langlinks",
                                    "lllang": LINGUA, "lllimit": "max",
                                    "redirects": "1",
                                    "titles": "|".join(gruppo)})
        for pagina in _pagine(dati):
            collegamenti = pagina.get("langlinks") or []
            for collegamento in collegamenti:
                titolo = collegamento.get("title") or collegamento.get("*")
                if titolo:
                    fuori[pagina.get("title", "")] = titolo
                    break
    return fuori


# Se questa wiki non sa contare le letture -- `prop=pageviews` e' un'estensione,
# non il nucleo di MediaWiki -- lo si scopre alla prima chiamata e non si
# insiste piu' per tutta la vita del processo.
_VISTE = True


def _schede(titoli):
    """{titolo: (descrizione breve, letture dell'ultimo mese)}.

    Due informazioni in una chiamata sola, perche' arrivano dalla stessa
    pagina della stessa wiki e perche' il budget di questo modulo e' di tre
    richieste al giorno.
    """
    global _VISTE
    fuori = {}
    for gruppo in _a_pezzi(titoli):
        comuni = {"action": "query", "redirects": "1",
                  "titles": "|".join(gruppo)}
        dati = {}
        if _VISTE:
            dati = _query(LINGUA, dict(comuni, prop="description|pageviews",
                                       pvipdays=str(GIORNI_VISTE)))
            if dati.get("error"):
                # Il server ha risposto e si e' lamentato: le letture qui non
                # ci sono. Si chiede la sola descrizione, oggi e per sempre.
                _VISTE = False
                dati = {}
            elif not dati:
                continue      # rete giu': niente descrizioni e niente conti
        if not dati:
            dati = _query(LINGUA, dict(comuni, prop="description"))
        for pagina in _pagine(dati):
            viste = 0
            for giorno in (pagina.get("pageviews") or {}).values():
                if isinstance(giorno, int):
                    viste += giorno
            fuori[pagina.get("title", "")] = (pagina.get("description") or "",
                                              viste)
    return fuori


def rifinisci(voci, tradurre=None):
    """Da [(anno, nome, mestiere)] a [(anno, nome, mestiere, letture)].

    Il nome passa all'italiano quando da noi la voce esiste, la descrizione
    diventa quella breve di it.wikipedia, e in piu' si porta dietro quante
    volte quella pagina e' stata letta nell'ultimo mese.

    `tradurre` e' una lista di bool lunga come `voci` -- i nomi che vengono
    dal feed inglese -- oppure None per tradurli tutti. Se qualcosa non
    riesce -- rete che cade a meta', voce che da noi non c'e' -- resta quello
    che c'era: un nome inglese e' meglio di niente, e quasi sempre e' anche
    lo stesso nome.
    """
    if not voci:
        return []
    if tradurre is None:
        tradurre = [True] * len(voci)
    nomi = [v[1] for v in voci]
    italiani = _in_italiano([n for n, t in zip(nomi, tradurre) if t])
    finali = [italiani.get(n, n) if t else n for n, t in zip(nomi, tradurre)]
    schede = _schede(sorted(set(finali)))
    fuori = []
    for (anno, _inglese, mestiere), titolo in zip(voci, finali):
        descrizione, viste = schede.get(titolo, ("", 0))
        fuori.append((anno, titolo, descrizione or mestiere, viste))
    return fuori


def _a_ventaglio(voci, quanti):
    """`quanti` voci sparse il piu' possibile su tutto l'arco degli anni.

    Il feed di un giorno qualunque ha molti piu' nati recenti che antichi --
    di chi e' nato nel 1998 Wikipedia sa tutto, del 1498 sa chi e' rimasto --
    percio' tenere le prime sei dopo un ordinamento per anno vuol dire
    mostrare sempre e solo gli ultimi arrivati.

    Nemmeno pescare a passo costante nell'elenco basta: il passo e' sugli
    indici, e dove i nomi si affollano -- trenta calciatori in trent'anni --
    il ventaglio si affolla con loro. Si prendono allora i due estremi e poi,
    ogni volta, l'anno piu' **lontano** da quelli gia' presi: cosi' lo spazio
    coperto e' quello degli anni, non quello della lista.
    """
    if quanti <= 0:
        return []
    ordinate = sorted(voci, key=lambda v: -v[0])
    if len(ordinate) <= quanti:
        return ordinate
    if quanti == 1:
        return [ordinate[0]]
    presi = {0, len(ordinate) - 1}
    while len(presi) < quanti:
        migliore, distanza = None, -1
        for i, voce in enumerate(ordinate):
            if i in presi:
                continue
            sua = min(abs(voce[0] - ordinate[j][0]) for j in presi)
            if sua > distanza:
                migliore, distanza = i, sua
        presi.add(migliore)
    return [ordinate[i] for i in sorted(presi)]


def _i_piu_letti(voci, quanti):
    """Le `quanti` voci piu' lette su Wikipedia, in ordine di anno.

    E' la misura piu' onesta di "famoso" che possa chiedere un pannello in
    cucina: quanta gente e' andata a leggere quella pagina nell'ultimo mese.
    Non premia chi e' nato di recente ne' chi e' morto l'anno scorso, premia
    chi qualcuno cerca ancora.

    Quando le letture non si sanno -- wiki senza l'estensione, rete caduta a
    meta' -- si torna al ventaglio: meglio sei nomi sparsi su tre secoli che
    sei coetanei.
    """
    if not voci:
        return []
    if max(v[3] for v in voci) <= 0:
        scelte = _a_ventaglio(voci, quanti)
    else:
        scelte = sorted(voci, key=lambda v: (-v[3], -v[0]))[:quanti]
    return [tuple(v[:3]) for v in sorted(scelte, key=lambda v: -v[0])]


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
    da_tradurre = {}
    for tipo, etichetta in (("births", "nati"), ("deaths", "morti")):
        if tipo not in tipi:
            continue
        voci = []
        # Prima l'italiano -- se un giorno le due sezioni ci saranno, sono
        # le sue -- e poi l'inglese, che oggi e' l'unico ad averle.
        for lingua in (LINGUA, LINGUA_FEED):
            try:
                dati = _chiedi(API % (lingua, tipo, quando.tm_mon, quando.tm_mday))
            except (urllib.error.URLError, OSError, ValueError) as exc:
                if lingua == LINGUA_FEED:
                    return None, str(getattr(exc, "reason", exc))[:120]
                continue
            voci = []
            for voce in (dati.get(etichetta) or dati.get(tipo) or []):
                persona = _persona(voce)
                if persona:
                    voci.append(persona)
            if voci:
                break
        # Una rosa larga e sparsa su tutti i secoli: la scelta vera si fa
        # dopo, sulle letture, e si puo' fare solo su chi e' in lista.
        fuori[etichetta] = _a_ventaglio(voci, ROSA)
        da_tradurre[etichetta] = lingua != LINGUA
    if not any(fuori.values()):
        return None, "Wikipedia non ha nati ne' morti per oggi"
    # Nomi, descrizioni e letture si chiedono per nati e morti insieme: due
    # chiamate in tutto invece di due per lista.
    etichette = [e for e in fuori if fuori[e]]
    insieme = [v for e in etichette for v in fuori[e]]
    bandiere = [da_tradurre.get(e, False) for e in etichette for _ in fuori[e]]
    rifinite = rifinisci(insieme, bandiere)
    da = 0
    for etichetta in etichette:
        quante = len(fuori[etichetta])
        fuori[etichetta] = _i_piu_letti(rifinite[da:da + quante], QUANTI)
        da += quante
    return fuori, ""


# ------------------------------------------------------- i fatti storici

def _pulisci_wikitesto(testo):
    """Da wikitesto a una riga leggibile su un pannello.

    Non e' un parser: e' una scrematura. Si tolgono i template, le note, i
    tag, e ai collegamenti si tiene la parte che si legge -- `[[Luna|la
    Luna]]` diventa "la Luna". Quello che resta e' testo, ed e' quello che
    serve: sul pannello non ci sono collegamenti da cliccare.
    """
    testo = re.sub(r"<ref[^>]*?/>", "", testo)
    testo = re.sub(r"<ref.*?</ref>", "", testo, flags=re.S)
    testo = re.sub(r"<!--.*?-->", "", testo, flags=re.S)
    testo = re.sub(r"\{\{[^{}]*\}\}", "", testo)
    testo = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", testo)
    testo = re.sub(r"\[\[([^\]]*)\]\]", r"\1", testo)
    testo = re.sub(r"'{2,}", "", testo)
    testo = re.sub(r"<[^>]+>", "", testo)
    testo = re.sub(r"\s+", " ", testo)
    return testo.strip(" .;–—-")


def _fatto(anno, testo):
    testo = _pulisci_wikitesto(testo)
    if not testo or not (0 < anno <= 2100):
        return None
    # Una frase sola: sul pannello la seconda non ci starebbe, e tagliata a
    # meta' fa peggio che non esserci.
    testo = re.split(r"(?<=[a-z0-9\)])\.\s+[A-Z]", testo)[0].strip(" .")
    return (anno, testo)


def _eventi_dal_feed(quando):
    """I fatti del giorno dal feed on-this-day. Lista, eventualmente vuota."""
    voci = []
    for tipo in ("selected", "events"):
        try:
            dati = _chiedi(API % (LINGUA, tipo, quando.tm_mon, quando.tm_mday))
        except (urllib.error.URLError, OSError, ValueError):
            continue
        for voce in (dati.get(tipo) or dati.get("selected") or dati.get("events") or []):
            anno, testo = voce.get("year"), (voce.get("text") or "").strip()
            if isinstance(anno, int) and testo:
                fatto = _fatto(anno, testo)
                if fatto:
                    voci.append(fatto)
        if voci:
            break
    return voci


def _eventi_dalla_pagina(quando):
    """I fatti del giorno letti dalla pagina «24 settembre» di it.wikipedia.

    La rete di sicurezza del feed: la pagina del giorno **esiste di sicuro**,
    e la sezione «Eventi» e' scritta a mano da chi cura quella pagina. Due
    chiamate: una per sapere dov'e' la sezione, una per prenderla.
    """
    pagina = "%d %s" % (quando.tm_mday, MESI_IT[quando.tm_mon - 1])
    sezioni = _query(LINGUA, {"action": "parse", "page": pagina, "prop": "sections"})
    indice = ""
    for sezione in ((sezioni.get("parse") or {}).get("sections") or []):
        if (sezione.get("line") or "").strip().lower() == "eventi":
            indice = sezione.get("index") or ""
            break
    if not indice:
        return []
    testo = _query(LINGUA, {"action": "parse", "page": pagina, "prop": "wikitext",
                            "section": indice})
    grezzo = ((testo.get("parse") or {}).get("wikitext") or "")
    if isinstance(grezzo, dict):                  # formatversion 1
        grezzo = grezzo.get("*", "")
    voci = []
    for riga in grezzo.split("\n"):
        trovato = re.match(r"^\*+\s*\[?\[?(\d{3,4})\]?\]?\s*[–—:-]\s*(.+)$",
                           riga.strip())
        if not trovato:
            continue
        fatto = _fatto(int(trovato.group(1)), trovato.group(2))
        if fatto:
            voci.append(fatto)
    return voci


def scarica_eventi(quando=None):
    """I fatti storici del giorno, in italiano. (lista, errore).

    Prima il feed, che e' fatto apposta; se torna vuoto -- come succede a
    it.wikipedia per nati e morti -- si legge la pagina del giorno, che c'e'
    sempre. In italiano in tutti e due i casi: un fatto storico non si
    traduce con `langlinks`, e' una frase.
    """
    quando = quando or time.localtime()
    try:
        voci = _eventi_dal_feed(quando) or _eventi_dalla_pagina(quando)
    except Exception as exc:                      # pragma: no cover - difensivo
        return [], str(exc)[:120]
    if not voci:
        return [], "Wikipedia non ha fatti per oggi"
    # I piu' recenti per primi: sono quelli che uno ha sentito nominare.
    voci.sort(key=lambda v: -v[0])
    return voci[:EVENTI], ""


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
        eventi, errore_eventi = scarica_eventi(quando)
        if dati is None and not eventi:
            self._errore = errore or errore_eventi
            return False, self._errore
        dati = dati or {}
        voce = {"preso": adesso, "nati": dati.get("nati", []),
                "morti": dati.get("morti", []), "eventi": eventi}
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

    def eventi(self, quando=None):
        voce = self._valida(quando) or {}
        return [tuple(v) for v in voce.get("eventi", [])]

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
        "eventi": [],
    }
    if storia is not None:
        dati["nati"] = [list(v) for v in storia.nati(quando)]
        dati["morti"] = [list(v) for v in storia.morti(quando)]
        dati["eventi"] = [list(v) for v in storia.eventi(quando)]
    return dati
