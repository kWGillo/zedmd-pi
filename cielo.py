"""Il cielo di stasera: fasi, lune con un nome, stagioni, sciami, serate buone.

Come `pianeti.py`, su cui si appoggia, questo modulo e' **solo** dati e
matematica: non disegna niente e non sa niente del pannello. Nessuna rete e
nessuna dipendenza nuova: `math` e `datetime`, che ci sono sempre.

## Il riferimento della data, e perche' conta qui

`pianeti.py` calcola il Sole nel riferimento dell'anno 2000. Per dire da che
parte guardare in cielo va benissimo: l'errore e' un terzo di grado, cioe' meno
di una luna piena. Per dire **quando** succede qualcosa no. Il Sole percorre
un grado al giorno, quindi un terzo di grado sono otto ore: calcolato cosi',
l'equinozio d'autunno del 2026 cadeva alle 9:20 invece che alle 0:05.

Qui il Sole si porta al riferimento della data -- precessione, nutazione e
aberrazione, le tre correzioni di Meeus -- e i quattro momenti delle stagioni
del 2026 tornano entro pochi minuti da quelli pubblicati. La Luna di
`pianeti.py` e' gia' nel riferimento della data: la serie di Meeus la da'
cosi', ed e' per questo che le sue lune piene tornavano gia' giuste.

## Che cosa vuol dire "una luna con un nome"

Solo nomi che hanno una definizione, non un'aneddotica:

* **Luna del Raccolto**: la luna piena piu' vicina all'equinozio d'autunno.
  Per diverse sere di fila sorge poco dopo il tramonto -- in autunno
  l'eclittica e' molto inclinata sull'orizzonte della sera -- e chi
  raccoglieva aveva luce per lavorare dopo il buio;
* **Superluna**: una luna piena a meno di 360.000 km dal centro della Terra.
  Le definizioni in giro sono diverse; questa e' la piu' severa fra quelle
  comuni, e ha il pregio di non chiamare superluna una luna qualsiasi;
* **Luna blu**: la seconda luna piena dello stesso mese del calendario.

Niente semina e raccolta secondo le fasi: e' una tradizione e non un effetto
misurabile, e le tradizioni si contraddicono. Il pannello non la presenta
come un fatto.
"""

import math
from datetime import datetime, timedelta, timezone

import pianeti

# ------------------------------------------------------- il Sole della data


def _nutazione(jd):
    """Nutazione in longitudine, in gradi: i quattro termini piu' grandi."""
    t = pianeti.secoli(jd)
    nodo = math.radians(125.04452 - 1934.136261 * t)
    sole = math.radians(280.4665 + 36000.7698 * t)
    luna = math.radians(218.3165 + 481267.8813 * t)
    secondi = (-17.20 * math.sin(nodo) - 1.32 * math.sin(2 * sole)
               - 0.23 * math.sin(2 * luna) + 0.21 * math.sin(2 * nodo))
    return secondi / 3600.0


def sole_apparente(jd):
    """Longitudine apparente del Sole, riferita all'equinozio della data."""
    lon, _lat, r = pianeti.sole_eclittica(jd)
    t = pianeti.secoli(jd)
    precessione = (5029.0966 * t + 1.11113 * t * t) / 3600.0
    aberrazione = -20.4898 / 3600.0 / (r if r else 1.0)
    return (lon + precessione + _nutazione(jd) + aberrazione) % 360.0


def luna_apparente(jd):
    """Longitudine apparente della Luna: la serie di Meeus piu' la nutazione."""
    lon, _lat, _dist = pianeti.luna_eclittica(jd)
    return (lon + _nutazione(jd)) % 360.0


def _da_giuliano(jd):
    return (datetime(2000, 1, 1, 12, tzinfo=timezone.utc)
            + timedelta(days=jd - 2451545.0))


def _cerca(funzione, bersaglio, inizio, fine, passo_ore=6):
    """Il primo istante in [inizio, fine] in cui `funzione` passa `bersaglio`.

    `funzione` restituisce un angolo che cresce nel tempo: la longitudine del
    Sole, l'elongazione della Luna. Si campiona e poi si stringe a metà, fino
    a meno di un minuto.
    """
    def scarto(t):
        return (funzione(pianeti.giuliano(t)) - bersaglio + 180.0) % 360.0 - 180.0

    t0 = inizio
    s0 = scarto(t0)
    passo = timedelta(hours=passo_ore)
    while t0 < fine:
        t1 = t0 + passo
        s1 = scarto(t1)
        if s0 < 0 <= s1 and s1 - s0 < 90:
            sinistra, destra = t0, t1
            while destra - sinistra > timedelta(seconds=30):
                meta = sinistra + (destra - sinistra) / 2
                if scarto(meta) < 0:
                    sinistra = meta
                else:
                    destra = meta
            return sinistra + (destra - sinistra) / 2
        t0, s0 = t1, s1
    return None


# --------------------------------------------------------------- le stagioni

STAGIONI = (
    (0.0, 3, 20, "equinozio_primavera"),
    (90.0, 6, 21, "solstizio_estate"),
    (180.0, 9, 23, "equinozio_autunno"),
    (270.0, 12, 21, "solstizio_inverno"),
)


def stagioni(anno):
    """I quattro momenti dell'anno: [(istante UTC, tipo), ...]."""
    fuori = []
    for gradi, mese, giorno, tipo in STAGIONI:
        centro = datetime(anno, mese, giorno, tzinfo=timezone.utc)
        istante = _cerca(sole_apparente, gradi, centro - timedelta(days=4),
                         centro + timedelta(days=4))
        if istante is not None:
            fuori.append((istante, tipo))
    return fuori


# --------------------------------------------------------------- le fasi

FASI_PRINCIPALI = ((0.0, "nuova"), (90.0, "primo_quarto"),
                   (180.0, "piena"), (270.0, "ultimo_quarto"))


def _elongazione(jd):
    return (luna_apparente(jd) - sole_apparente(jd)) % 360.0


def fasi(inizio, fine):
    """Le fasi principali fra due istanti: [(istante UTC, tipo), ...]."""
    fuori = []
    for gradi, tipo in FASI_PRINCIPALI:
        t = inizio
        while t < fine:
            istante = _cerca(_elongazione, gradi, t, fine, passo_ore=12)
            if istante is None:
                break
            fuori.append((istante, tipo))
            t = istante + timedelta(days=20)
    fuori.sort()
    return fuori


# ------------------------------------------------------ le lune con un nome

SUPERLUNA_KM = 360000.0


def lune_con_nome(anno):
    """Le lune piene dell'anno che hanno un nome: [(istante, nome), ...].

    Una luna puo' averne piu' d'uno -- una superluna del raccolto -- e allora
    compare due volte, una per nome.
    """
    inizio = datetime(anno, 1, 1, tzinfo=timezone.utc) - timedelta(days=15)
    fine = datetime(anno + 1, 1, 1, tzinfo=timezone.utc) + timedelta(days=15)
    piene = [t for t, tipo in fasi(inizio, fine) if tipo == "piena"]
    fuori = []

    autunno = [t for t, tipo in stagioni(anno) if tipo == "equinozio_autunno"]
    if autunno and piene:
        raccolto = min(piene, key=lambda t: abs((t - autunno[0]).total_seconds()))
        fuori.append((raccolto, "raccolto"))

    per_mese = {}
    for t in piene:
        locale = t.astimezone()
        if locale.year != anno:
            continue
        per_mese.setdefault((locale.year, locale.month), []).append(t)
        _l, _b, distanza = pianeti.luna_eclittica(pianeti.giuliano(t))
        if distanza < SUPERLUNA_KM:
            fuori.append((t, "superluna"))
    for elenco in per_mese.values():
        if len(elenco) >= 2:
            fuori.append((elenco[1], "blu"))
    fuori.sort()
    return fuori


# --------------------------------------------------------- gli sciami

# Il giorno del picco e' quello medio della lista dell'International Meteor
# Organization: cade sempre lo stesso giorno, uno piu' o uno meno, perche'
# dipende dal punto dell'orbita della Terra e non dal calendario.
#
# ZHR e' il numero di meteore in un'ora sotto un cielo perfetto con il
# radiante allo zenit. Sotto un cielo vero se ne vedono meno, spesso la meta':
# e' un confronto fra sciami, non una promessa.
SCIAMI = (
    ("quadrantidi", "QUADRANTIDI", 1, 3, 110),
    ("liridi", "LIRIDI", 4, 22, 18),
    ("eta_aquaridi", "ETA AQUARIDI", 5, 6, 50),
    ("delta_aquaridi", "DELTA AQUARIDI", 7, 30, 25),
    ("perseidi", "PERSEIDI", 8, 12, 100),
    ("orionidi", "ORIONIDI", 10, 21, 20),
    ("leonidi", "LEONIDI", 11, 17, 15),
    ("geminidi", "GEMINIDI", 12, 14, 150),
)

# Sopra questa frazione illuminata, e con la Luna alta nelle ore buone, le
# meteore deboli spariscono: si vedono solo le poche piu' luminose.
LUNA_CHE_DISTURBA = 0.35


def sciame_disturbato(picco_locale, lat, lon):
    """Come la Luna tratta la notte del picco.

    Le ore buone per le meteore sono quelle dopo mezzanotte, quando il nostro
    lato della Terra guarda nella direzione in cui corre, fino al chiarore
    dell'alba. Tre risposte possibili, e sono tre cose diverse da dire:

    * ``"sottile"``: la Luna e' illuminata meno di un terzo, non disturba;
    * ``"tramonta"``: e' luminosa ma va giu' prima delle quattro -- dopo, il
      cielo e' buio. E' il caso delle Orionidi del 2026: Luna al 70%, ma
      tramonta verso l'una e mezza;
    * ``"copre"``: resta su nelle ore buone e se ne mangia molte.

    Torna (risposta, frazione, istante del tramonto o None).
    """
    mezzanotte = picco_locale.replace(hour=0, minute=0, second=0, microsecond=0)
    utc = (mezzanotte + timedelta(hours=2)).astimezone(timezone.utc)
    frazione = pianeti.fase_luna(utc)["frazione"]
    if frazione <= LUNA_CHE_DISTURBA:
        return "sottile", frazione, None
    if lat is None or lon is None:
        return "copre", frazione, None
    # Dalle 22 della sera prima alle 4: se la Luna tramonta in quella
    # finestra, le ore dopo sono buie.
    inizio = (mezzanotte - timedelta(hours=2)).astimezone(timezone.utc)
    tramonto = tramonta_luna(inizio, lat, lon, ore=6)
    sopra_alle_due = pianeti.dove("luna", utc, lat, lon)["altezza"] > 0
    if tramonto is not None:
        return "tramonta", frazione, tramonto
    if not sopra_alle_due:
        return "sottile", frazione, None
    return "copre", frazione, None


def prossimo_sciame(adesso_locale, giorni_prima=3):
    """Lo sciame il cui picco cade fra oggi e fra `giorni_prima` giorni."""
    oggi = adesso_locale.date()
    for chiave, nome, mese, giorno, zhr in SCIAMI:
        for anno in (oggi.year, oggi.year + 1):
            picco = datetime(anno, mese, giorno).date()
            if 0 <= (picco - oggi).days <= giorni_prima:
                return {"chiave": chiave, "nome": nome, "picco": picco,
                        "zhr": zhr, "fra_giorni": (picco - oggi).days}
    return None


# --------------------------------------------------------- stasera

DIREZIONI = ("NORD", "NORD-EST", "EST", "SUD-EST",
             "SUD", "SUD-OVEST", "OVEST", "NORD-OVEST")


def direzione(azimut):
    """L'azimut in una delle otto direzioni, scritta per il pannello."""
    return DIREZIONI[int(((azimut % 360.0) + 22.5) // 45.0) % 8]


def altezza_a_parole(gradi):
    if gradi >= 45:
        return "ALTO"
    if gradi >= 20:
        return "A META' CIELO"
    return "BASSO"


# Soglie della serata buona. Un quarto di cielo coperto e' ancora un cielo da
# guardare; oltre, le nuvole si prendono proprio le zone che si cercano. E
# almeno un'ora e mezza di buio senza Luna: meno e' un'occhiata, non una
# serata.
NUVOLE_MASSIME = 25
MINUTI_MINIMI = 90
# Una Luna sottile non rovina niente: sotto un quarto illuminato si vedono
# lo stesso la Via Lattea e le stelle deboli.
LUNA_SOTTILE = 0.25


def eventi_sole(giorno_locale, lat, lon):
    """Tramonto e alba del giorno dopo, in UTC. (None, None) se non trovati."""
    mezzogiorno = giorno_locale.replace(hour=12, minute=0, second=0,
                                        microsecond=0).astimezone(timezone.utc)
    tramonto = alba = None
    passo = timedelta(minutes=10)
    t0 = mezzogiorno
    a0 = pianeti.altezza_sole(t0, lat, lon) + 0.833
    for _ in range(int(24 * 6)):
        t1 = t0 + passo
        a1 = pianeti.altezza_sole(t1, lat, lon) + 0.833
        if (a0 < 0) != (a1 < 0):
            sinistra, destra = t0, t1
            for _ in range(14):
                meta = sinistra + (destra - sinistra) / 2
                if (pianeti.altezza_sole(meta, lat, lon) + 0.833 < 0) == (a0 < 0):
                    sinistra = meta
                else:
                    destra = meta
            istante = sinistra + (destra - sinistra) / 2
            if a1 < 0 and tramonto is None:
                tramonto = istante
            elif a1 >= 0 and tramonto is not None:
                alba = istante
                break
        t0, a0 = t1, a1
    return tramonto, alba


def sorge_luna(quando_utc, lat, lon, ore=30):
    """Il prossimo sorgere della Luna, con la soglia standard di -0,833 gradi."""
    for istante, tipo in pianeti.orizzonte("luna", quando_utc, lat, lon, ore=ore,
                                           soglia=-0.833):
        if tipo == "sorge":
            return istante
    return None


def tramonta_luna(quando_utc, lat, lon, ore=30):
    for istante, tipo in pianeti.orizzonte("luna", quando_utc, lat, lon, ore=ore,
                                           soglia=-0.833):
        if tipo == "tramonta":
            return istante
    return None


def luna_stasera(adesso_locale, lat=None, lon=None):
    """Quello che serve alla schermata della Luna di ogni sera."""
    utc = adesso_locale.astimezone(timezone.utc)
    fase = pianeti.fase_luna(utc)
    domani = pianeti.fase_luna(utc + timedelta(days=1))
    fuori = {
        "frazione": fase["frazione"],
        "avanzamento": fase["avanzamento"],
        "fase": fase["fase"],
        "crescente": domani["frazione"] > fase["frazione"],
        "eta_giorni": fase["eta_giorni"],
        "sorge": None,
        "tramonta": None,
        "sopra": None,
    }
    if lat is not None and lon is not None:
        altezza = pianeti.dove("luna", utc, lat, lon)["altezza"]
        fuori["sopra"] = altezza > -0.833
        inizio = adesso_locale.replace(hour=12, minute=0, second=0,
                                       microsecond=0).astimezone(timezone.utc)
        if adesso_locale.hour < 12:
            inizio -= timedelta(days=1)
        fuori["sorge"] = sorge_luna(inizio, lat, lon)
        fuori["tramonta"] = tramonta_luna(inizio, lat, lon)
    prossime = fasi(utc, utc + timedelta(days=31))
    fuori["prossima"] = prossime[0] if prossime else None
    fuori["prossima_piena"] = next((t for t, tipo in prossime if tipo == "piena"),
                                   None)
    return fuori


def serata(adesso_locale, lat, lon, nuvole=None):
    """Vale la pena uscire a guardare, stasera?

    `nuvole` e' un dizionario {istante UTC arrotondato all'ora: percentuale}
    preso dalla previsione del meteo. Senza nuvole la serata non si giudica:
    un cielo buio e coperto non e' una serata buona, e dire "buona" senza
    saperlo sarebbe una promessa a vuoto.

    Si guardano le ore dal buio (Sole a -12 gradi, crepuscolo nautico) fino
    all'una di notte: chi guarda il cielo da casa, di sera, guarda allora.
    """
    tramonto, _alba = eventi_sole(adesso_locale, lat, lon)
    if tramonto is None:
        return None
    limite = (adesso_locale.replace(hour=1, minute=0, second=0, microsecond=0)
              + timedelta(days=1 if adesso_locale.hour >= 12 else 0)
              ).astimezone(timezone.utc)
    passo = timedelta(minutes=15)
    t = tramonto
    buoni = []
    coperture = []
    while t < limite:
        sole = pianeti.altezza_sole(t, lat, lon)
        if sole < pianeti.CREPUSCOLO_NAUTICO:
            luna = pianeti.dove("luna", t, lat, lon)
            frazione = pianeti.fase_luna(t)["frazione"]
            senza_luna = luna["altezza"] < 0 or frazione < LUNA_SOTTILE
            ora = t.replace(minute=0, second=0, microsecond=0)
            copertura = None if nuvole is None else nuvole.get(ora)
            if copertura is not None:
                coperture.append(copertura)
            if senza_luna:
                buoni.append((t, copertura))
        t += passo
    if not buoni:
        return {"buona": False, "motivo": "luna", "dalle": None, "alle": None,
                "nuvole": None, "pianeta": None}
    minuti = len(buoni) * 15
    note = [c for _t, c in buoni if c is not None]
    media = int(round(sum(note) / len(note))) if note else None
    fuori = {"buona": False, "motivo": "", "dalle": buoni[0][0],
             "alle": buoni[-1][0] + passo, "nuvole": media, "pianeta": None,
             "minuti": minuti}
    if media is None:
        fuori["motivo"] = "nuvole_ignote"
    elif media > NUVOLE_MASSIME:
        fuori["motivo"] = "nuvole"
    elif minuti < MINUTI_MINIMI:
        fuori["motivo"] = "poco_buio"
    else:
        fuori["buona"] = True
    # Il pianeta piu' luminoso a meta' della finestra buona.
    meta = buoni[len(buoni) // 2][0]
    visti = pianeti.visibili(meta, lat, lon)
    if visti:
        v = visti[0]
        fuori["pianeta"] = {"nome": v["nome"], "direzione": direzione(v["azimut"]),
                            "altezza": altezza_a_parole(v["altezza"]),
                            "gradi": v["altezza"],
                            "colore": v.get("colore")}
    return fuori


# --------------------------------------------------------- che c'e' di nuovo

def evento_di_stasera(adesso_locale, lat=None, lon=None, giorni_prima=3):
    """L'evento da annunciare stasera, se ce n'e' uno. Il piu' vicino vince.

    Torna un dizionario con `tipo` fra "stagione", "luna_nome", "sciame",
    oppure None. Si annuncia dal terzo giorno prima fino al giorno stesso:
    abbastanza presto da organizzarsi, non tanto da diventare rumore.
    """
    oggi = adesso_locale.date()
    candidati = []
    for istante, tipo in stagioni(adesso_locale.year):
        locale = istante.astimezone(adesso_locale.tzinfo)
        giorni = (locale.date() - oggi).days
        if 0 <= giorni <= giorni_prima:
            candidati.append((giorni, {"tipo": "stagione", "nome": tipo,
                                       "quando": locale, "fra_giorni": giorni}))
    for anno in (adesso_locale.year, adesso_locale.year + 1):
        for istante, nome in lune_con_nome(anno):
            locale = istante.astimezone(adesso_locale.tzinfo)
            giorni = (locale.date() - oggi).days
            if 0 <= giorni <= giorni_prima:
                _l, _b, distanza = pianeti.luna_eclittica(
                    pianeti.giuliano(istante))
                candidati.append((giorni, {"tipo": "luna_nome", "nome": nome,
                                           "quando": locale,
                                           "distanza_km": distanza,
                                           "fra_giorni": giorni}))
    sciame = prossimo_sciame(adesso_locale, giorni_prima)
    if sciame is not None:
        picco = datetime.combine(sciame["picco"], datetime.min.time(),
                                 tzinfo=adesso_locale.tzinfo)
        luna, frazione, tramonto = sciame_disturbato(picco, lat, lon)
        sciame.update({"tipo": "sciame", "luna": luna, "frazione": frazione,
                       "luna_tramonta": tramonto,
                       "disturba": luna == "copre"})
        candidati.append((sciame["fra_giorni"], sciame))
    if not candidati:
        return None
    candidati.sort(key=lambda c: c[0])
    return candidati[0][1]
