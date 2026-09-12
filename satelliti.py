"""Satelliti: dove sono, quando passano, e se si vedono a occhio nudo.

Questo modulo e' **solo** dati e matematica: non disegna niente e non sa
niente del pannello. Serve per poterlo verificare da solo, con uno script,
prima che una sola riga finisca sul display.

La differenza di fondo con l'Air Radar: per gli aerei c'e' un servizio che
dice *dove sono*. Per i satelliti no. Si scaricano gli **elementi orbitali**
-- i TLE, due righe di numeri per satellite -- e la posizione **la si
calcola**, con SGP4. Conseguenze pratiche, tutte a favore:

* nessuna chiamata di rete a ogni aggiornamento: il pannello lavora anche con
  internet giu';
* gli elementi invecchiano in giorni, non in minuti, quindi si scaricano una
  volta al giorno e basta;
* CelesTrak chiede di non interrogare piu' di una volta all'ora e di
  **fermarsi** al primo errore HTTP, pena il blocco dell'indirizzo. Con una
  lettura al giorno non ci avviciniamo nemmeno al limite, ma il freno c'e' lo
  stesso: e' scritto in `_puo_scaricare`.

Il punto piu' delicato di tutto il modulo e' la **luminosita'**, e vale la
pena leggerlo prima di toccare qualsiasi cosa. I TLE danno l'orbita, non la
magnitudine, e la fonte pubblica che dava le magnitudini si e' spenta. Quindi
"visibile", calcolato, puo' voler dire soltanto *illuminato dal Sole mentre
qui e' buio* -- condizione che un CubeSat da dieci centimetri soddisfa
esattamente come la Stazione Spaziale.

Per questo l'ultimo filtro non e' un calcolo ma una **tabella scritta a
mano**, `NOTI`: due righe, gli oggetti che sappiamo davvero visibili a occhio
nudo. Sembra poco ed e' il contrario: lo scopo della sorgente e' far uscire
qualcuno in terrazzo, e annunciare qualcosa di invisibile non e'
un'imprecisione, e' una promessa mancata.
"""

import json
import math
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

# Import morbido, e non e' pignoleria. L'aggiornamento via rete **non** esegue
# `install.sh`: un Raspberry aggiornato da una versione precedente potrebbe non
# avere `sgp4`. Con un import secco, `sources/satelliti.py` non si
# importerebbe, `dmdd` non partirebbe, e il pannello resterebbe **nero** per
# colpa di una sorgente facoltativa. Meglio una sorgente che dice di essere
# spenta che un DMD che non si accende.
try:
    from sgp4.api import Satrec, jday
    DISPONIBILE = True
    MOTIVO = ""
except ImportError as _exc:          # pragma: no cover - dipende dalla macchina
    Satrec = None
    jday = None
    DISPONIBILE = False
    MOTIVO = str(_exc)

# --------------------------------------------------------------------- dati

# I gruppi di CelesTrak, con il nome interno a sinistra. Non classifichiamo
# niente noi: le famiglie le pubblica gia' loro, e questo e' il motivo per cui
# la scelta delle famiglie nella pagina web e' una casella e non un algoritmo.
GRUPPI = {
    "stazioni": "stations",   # ISS, Tiangong: pochissime e luminosissime
    # Gli altri esistono ma **non** sono attivi per scelta.
    #
    # `luminosi` (i ~100 piu' brillanti) e' stato provato e scartato: due
    # terzi di quel gruppo sono stadi di razzo esausti -- SL-16 R/B, CZ-2C
    # R/B, ARIANE 40+ R/B. Il dato e' giusto, sono davvero fra gli oggetti
    # piu' luminosi del cielo, ma quelle sigle su un pannello in salotto non
    # dicono niente a nessuno, e in una notte sola riempivano l'elenco con
    # 252 passaggi. Restano selezionabili per chi li vuole.
    "luminosi": "visual",
    "meteo": "weather",
    "noaa": "noaa",
    "radioamatori": "amateur",
    "starlink": "starlink",   # oltre 10.000: da tenere spento salvo motivo
}

# Quali gruppi sono accesi se nessuno dice altro.
GRUPPI_PREDEFINITI = ("stazioni",)

BASE = "https://celestrak.org/NORAD/elements/gp.php"

# CelesTrak chiede di identificarsi. Un User-Agent anonimo e' il primo passo
# per finire in un firewall insieme a tutti gli altri anonimi.
AGENTE = "zedmd-pi/satelliti (+https://github.com/kWGillo/zedmd-pi)"

# Quanto si tiene un file scaricato prima di riprovare. I TLE invecchiano in
# giorni: 12 ore e' gia' prudente.
VALIDITA_ORE = 12

# Il freno duro: mai piu' di una richiesta all'ora per gruppo, qualunque cosa
# chieda il chiamante. E' la regola di CelesTrak, non una nostra preferenza.
ATTESA_MINIMA_ORE = 1.0

# Gli oggetti che sappiamo essere visibili a occhio nudo, con il nome corto da
# mostrare e la magnitudine tipica al culmine.
#
# Questa tabella non e' un abbellimento: e' **il filtro**. I TLE danno
# l'orbita, non la luminosita', e la fonte pubblica che dava le magnitudini --
# i file `mcnames` e `vsnames` di Mike McCants, lo standard per vent'anni --
# e' stata ritirata e non si aggiorna piu'. Senza magnitudine, "visibile" puo'
# voler dire soltanto "illuminato dal Sole mentre qui e' buio", e un CubeSat
# da dieci centimetri passa quel controllo esattamente come la ISS.
#
# Il primo giro sul campo l'ha dimostrato: il gruppo *stations* di CelesTrak
# non contiene "le stazioni spaziali" ma anche i CubeSat rilasciati dalla ISS
# -- GXIBA-1, KNACKSAT-2, HMU-SAT2, UITMSAT-2 -- e il pannello avrebbe
# mandato qualcuno in terrazzo a cercare una scatoletta invisibile.
#
# Meglio due righe vere che duecento inventate. Se un giorno si trovasse una
# fonte affidabile, il filtro si allarga cambiando questa tabella e basta.
NOTI = {
    25544: ("ISS", -3.1),      # Stazione Spaziale Internazionale
    48274: ("CSS", -1.0),      # Stazione cinese, modulo Tianhe
}

# Riconoscimento di riserva sul nome, per quando il numero di catalogo cambia
# o non e' quello che credevamo. Il modulo Zarya e' il corpo principale della
# ISS, Tianhe quello della stazione cinese.
NOMI_NOTI = (
    ("ZARYA", "ISS", -3.1),
    ("TIANHE", "CSS", -1.0),
)


def _conosciuto(norad, nome):
    """(nome breve, magnitudine) se e' un oggetto che sappiamo visibile."""
    if norad in NOTI:
        return NOTI[norad]
    alto = (nome or "").upper()
    for pezzo, breve, magnitudine in NOMI_NOTI:
        if pezzo in alto:
            return breve, magnitudine
    return None, None

R_TERRA = 6378.137          # km, raggio equatoriale WGS84
ACHIACC = 1 / 298.257223563  # schiacciamento WGS84


# ------------------------------------------------------------- scaricamento


def _percorso(cartella, gruppo):
    return os.path.join(cartella, "%s.tle" % gruppo)


def _puo_scaricare(percorso, adesso=None):
    """Vero se il file manca o e' abbastanza vecchio da poter essere rifatto.

    Due soglie diverse, e servono tutte e due. `VALIDITA_ORE` dice quando i
    dati **meritano** un aggiornamento; `ATTESA_MINIMA_ORE` dice quando ci e'
    **permesso** chiederlo. Se un giorno qualcuno alzasse la frequenza degli
    aggiornamenti, la seconda regge lo stesso.
    """
    adesso = adesso if adesso is not None else time.time()
    try:
        eta = adesso - os.path.getmtime(percorso)
    except OSError:
        return True
    return eta >= min(VALIDITA_ORE, max(ATTESA_MINIMA_ORE, 0.0)) * 3600 \
        and eta >= ATTESA_MINIMA_ORE * 3600


def scarica(gruppo, cartella, forza=False, apri=None):
    """Scarica un gruppo di TLE, se e' il momento. Torna (aggiornato, motivo).

    Non solleva mai: un satellite che non si vede non deve spegnere il DMD.
    Su qualunque risposta diversa da 200 si **ferma** -- non riprova, non
    cambia indirizzo -- come chiede la politica d'uso di CelesTrak.
    """
    nome = GRUPPI.get(gruppo, gruppo)
    percorso = _percorso(cartella, gruppo)
    if not forza and not _puo_scaricare(percorso):
        return False, "ancora fresco"
    url = "%s?GROUP=%s&FORMAT=tle" % (BASE, nome)
    apri = apri or urllib.request.urlopen
    try:
        richiesta = urllib.request.Request(url, headers={"User-Agent": AGENTE})
        with apri(richiesta, timeout=20) as risposta:
            codice = getattr(risposta, "status", 200) or 200
            if codice != 200:
                return False, "risposta %s: mi fermo" % codice
            testo = risposta.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        # Esplicito: 403 e 429 vogliono dire "stai esagerando". Riprovare e'
        # esattamente il comportamento che porta al blocco dell'IP.
        return False, "risposta %s: mi fermo" % exc.code
    except Exception as exc:
        return False, "rete: %s" % exc
    if "1 " not in testo or len(testo) < 100:
        return False, "risposta non riconosciuta (%d byte)" % len(testo)
    try:
        os.makedirs(cartella, exist_ok=True)
        temporaneo = percorso + ".tmp"
        with open(temporaneo, "w", encoding="utf-8") as fh:
            fh.write(testo)
        os.replace(temporaneo, percorso)
    except OSError as exc:
        return False, "scrittura: %s" % exc
    return True, "%d satelliti" % (testo.count("\n") // 3)


def carica(gruppo, cartella):
    """Legge un file TLE gia' scaricato. Torna una lista di dizionari."""
    if not DISPONIBILE:
        return []
    percorso = _percorso(cartella, gruppo)
    try:
        with open(percorso, encoding="utf-8") as fh:
            righe = [r.rstrip() for r in fh if r.strip()]
    except OSError:
        return []
    elenco = []
    for i in range(0, len(righe) - 2, 3):
        nome, uno, due = righe[i], righe[i + 1], righe[i + 2]
        if not uno.startswith("1 ") or not due.startswith("2 "):
            continue
        try:
            sat = Satrec.twoline2rv(uno, due)
        except Exception:
            continue
        pulito = nome.strip()
        breve, magnitudine = _conosciuto(sat.satnum, pulito)
        elenco.append({
            "nome": pulito,
            # Il nome corto e' quello che va sul pannello: "ISS", non
            # "ISS (ZARYA)". Chi guarda da poltrona non deve sapere come si
            # chiama il modulo principale.
            "breve": breve or pulito,
            "norad": sat.satnum,
            "sat": sat,
            "gruppo": gruppo,
            "magnitudine": magnitudine,
            "noto": breve is not None,
        })
    return elenco


def unisci(*elenchi):
    """Piu' gruppi in un elenco solo, senza ripetizioni.

    Lo stesso satellite sta in piu' gruppi -- la ISS e' fra le *stazioni* e
    anche fra i *luminosi* -- e senza questo finirebbe due volte in elenco,
    con lo stesso orario. Il numero NORAD e' l'identita' vera: il nome no,
    puo' cambiare fra un file e l'altro.
    """
    visti = {}
    for elenco in elenchi:
        for voce in elenco:
            if voce["norad"] in visti:
                continue
            visti[voce["norad"]] = voce
    return list(visti.values())


def eta_dati(gruppo, cartella):
    """Da quante ore e' fermo il file di questo gruppo. None se non c'e'."""
    try:
        return (time.time() - os.path.getmtime(_percorso(cartella, gruppo))) / 3600.0
    except OSError:
        return None


# ------------------------------------------------------------- astronomia


def _giuliano(quando):
    """datetime UTC -> (jd, fr) come li vuole sgp4."""
    if quando.tzinfo is None:
        quando = quando.replace(tzinfo=timezone.utc)
    quando = quando.astimezone(timezone.utc)
    return jday(quando.year, quando.month, quando.day,
                quando.hour, quando.minute,
                quando.second + quando.microsecond / 1e6)


def gmst(jd, fr):
    """Tempo siderale medio di Greenwich, in radianti.

    Serve per passare dal sistema in cui SGP4 da' la posizione (inerziale,
    fermo rispetto alle stelle) a quello dell'osservatore, che ruota con la
    Terra. E' l'angolo di cui la Terra si e' girata.
    """
    d = jd - 2451545.0 + fr
    t = d / 36525.0
    g = (280.46061837 + 360.98564736629 * d
         + 0.000387933 * t * t - t * t * t / 38710000.0)
    return math.radians(g % 360.0)


def sole(jd, fr):
    """Direzione del Sole vista dal centro della Terra, versore equatoriale.

    Formula a bassa precisione dell'Astronomical Almanac: sbaglia di un
    centesimo di grado. Per sapere se un satellite e' al sole o in ombra --
    una domanda che si decide su migliaia di chilometri -- e' un lusso.
    """
    d = jd - 2451545.0 + fr
    lon_media = math.radians((280.460 + 0.9856474 * d) % 360.0)
    anomalia = math.radians((357.528 + 0.9856003 * d) % 360.0)
    eclittica = lon_media + math.radians(1.915 * math.sin(anomalia)
                                         + 0.020 * math.sin(2 * anomalia))
    obliquita = math.radians(23.439 - 0.0000004 * d)
    return (math.cos(eclittica),
            math.cos(obliquita) * math.sin(eclittica),
            math.sin(obliquita) * math.sin(eclittica))


def _osservatore(lat, lon, quota_km, jd, fr):
    """Posizione dell'osservatore nello stesso sistema di SGP4."""
    rlat = math.radians(lat)
    c = 1.0 / math.sqrt(1 - ACHIACC * (2 - ACHIACC) * math.sin(rlat) ** 2)
    s = (1 - ACHIACC) ** 2 * c
    raggio_xy = (R_TERRA * c + quota_km) * math.cos(rlat)
    raggio_z = (R_TERRA * s + quota_km) * math.sin(rlat)
    theta = gmst(jd, fr) + math.radians(lon)
    return (raggio_xy * math.cos(theta), raggio_xy * math.sin(theta), raggio_z)


def guarda(sat, quando, lat, lon, quota_km=0.0):
    """Dove sta un satellite visto da qui, adesso.

    Torna un dizionario con elevazione e azimut in gradi, distanza in km, e
    se il satellite e' illuminato dal Sole. None se SGP4 non sa rispondere
    (succede: un TLE vecchio di mesi puo' divergere).
    """
    jd, fr = _giuliano(quando)
    errore, r, _v = sat.sgp4(jd, fr)
    if errore != 0:
        return None
    ox, oy, oz = _osservatore(lat, lon, quota_km, jd, fr)
    dx, dy, dz = r[0] - ox, r[1] - oy, r[2] - oz
    distanza = math.sqrt(dx * dx + dy * dy + dz * dz)
    if distanza <= 0:
        return None

    # Terna locale: zenit, nord, est. L'azimut si misura da nord verso est.
    rlat, rlon = math.radians(lat), math.radians(lon)
    theta = gmst(jd, fr) + rlon
    zenit = (math.cos(rlat) * math.cos(theta),
             math.cos(rlat) * math.sin(theta),
             math.sin(rlat))
    nord = (-math.sin(rlat) * math.cos(theta),
            -math.sin(rlat) * math.sin(theta),
            math.cos(rlat))
    est = (-math.sin(theta), math.cos(theta), 0.0)

    su = (dx * zenit[0] + dy * zenit[1] + dz * zenit[2]) / distanza
    verso_n = dx * nord[0] + dy * nord[1] + dz * nord[2]
    verso_e = dx * est[0] + dy * est[1] + dz * est[2]
    elevazione = math.degrees(math.asin(max(-1.0, min(1.0, su))))
    azimut = math.degrees(math.atan2(verso_e, verso_n)) % 360.0
    return {
        "elevazione": elevazione,
        "azimut": azimut,
        "distanza": distanza,
        "illuminato": illuminato(r, jd, fr),
    }


def illuminato(r, jd, fr):
    """Il satellite e' al sole, o dentro l'ombra della Terra?

    Modello cilindrico: la Terra proietta un cilindro d'ombra invece di un
    cono. Sbaglia di qualche secondo sull'istante esatto in cui il satellite
    "si spegne" -- il fenomeno che si vede a occhio nudo come una sparizione
    improvvisa -- e per decidere se un passaggio vale la pena e' piu' che
    sufficiente.
    """
    sx, sy, sz = sole(jd, fr)
    lungo = r[0] * sx + r[1] * sy + r[2] * sz
    if lungo > 0:
        return True  # dalla parte del Sole: illuminato di sicuro
    px = r[0] - lungo * sx
    py = r[1] - lungo * sy
    pz = r[2] - lungo * sz
    return math.sqrt(px * px + py * py + pz * pz) > R_TERRA


def elevazione_sole(quando, lat, lon):
    """Quanto e' alto il Sole, in gradi. Negativo vuol dire sotto l'orizzonte."""
    jd, fr = _giuliano(quando)
    sx, sy, sz = sole(jd, fr)
    rlat, rlon = math.radians(lat), math.radians(lon)
    theta = gmst(jd, fr) + rlon
    zenit = (math.cos(rlat) * math.cos(theta),
             math.cos(rlat) * math.sin(theta),
             math.sin(rlat))
    coseno = sx * zenit[0] + sy * zenit[1] + sz * zenit[2]
    return math.degrees(math.asin(max(-1.0, min(1.0, coseno))))


# ---------------------------------------------------------------- passaggi

# Sotto quale elevazione del Sole si considera "buio abbastanza". -6 e' il
# crepuscolo civile: il cielo e' ancora chiaro a ovest ma la ISS si vede gia'.
BUIO_GRADI = -6.0

# Passo della griglia di ricerca. Trenta secondi non fa perdere nessun
# passaggio utile: il piu' corto sopra i 10 gradi dura minuti, non secondi.
PASSO = 30.0


def _elevazione(sat, quando, lat, lon, quota_km):
    vista = guarda(sat, quando, lat, lon, quota_km)
    return None if vista is None else vista["elevazione"]


def _confine(sat, prima, dopo, lat, lon, quota_km, soglia):
    """Bisezione fra due istanti che stanno da parti opposte della soglia.

    Serve perche' l'ora deve **lampeggiare esattamente** mentre il satellite
    passa: il minuto della griglia non basta, ci vuole il secondo.

    Vale per tutti e due i bordi, e non e' un dettaglio: la prima versione era
    scritta pensando solo al **sorgere**, dove si passa da sotto a sopra la
    soglia. Sul **tramonto** il verso e' rovesciato, e con la stessa regola la
    ricerca andava dalla parte sbagliata: il risultato finiva a caso dentro la
    cella da trenta secondi. Il sorgere restava identico a ogni esecuzione, il
    tramonto ballava di decine di secondi a seconda di quando si lanciava il
    comando -- ed e' cosi' che e' saltato fuori.
    """
    partenza = _elevazione(sat, prima, lat, lon, quota_km)
    sale = partenza is None or partenza < soglia
    for _ in range(20):  # 30 s dimezzati venti volte: ben sotto il millesimo
        meta = prima + (dopo - prima) / 2
        el = _elevazione(sat, meta, lat, lon, quota_km)
        if el is None:
            return meta
        # `meta` sta gia' oltre l'attraversamento? Salendo vuol dire "sopra
        # soglia", scendendo vuol dire l'opposto.
        if (el >= soglia) == sale:
            dopo = meta
        else:
            prima = meta
    return prima + (dopo - prima) / 2


# Di quanto si guarda **oltre** la fine della finestra pur di chiudere
# l'ultimo passaggio. Senza, un passaggio che comincia alle 23:58 e finisce
# alle 00:06 sparirebbe del tutto da una finestra che si chiude a mezzanotte:
# buttato via in silenzio, che e' il modo peggiore di perdere un dato.
MARGINE_MIN = 40


def passaggi(voce, lat, lon, da, a, quota_km=0.0, elevazione_minima=10.0,
             solo_visibili=False):
    """Tutti i passaggi di un satellite in una finestra di tempo.

    Ogni passaggio e' un dizionario con sorgere, culmine e tramonto (istanti
    veri, raffinati al secondo), gli azimut, l'elevazione massima e se e'
    **visibile**: cioe' se in qualche momento il satellite e' al sole mentre
    qui e' buio. E' quella la condizione che porta tremila oggetti a tre.

    Due cose si decidono ai bordi della finestra, e nessuna e' un dettaglio.

    **All'inizio:** se il satellite e' *gia'* in cielo quando la finestra si
    apre, quel passaggio non e' nostro e viene scartato. Non e' pignoleria:
    il codice di prima dichiarava come "sorgere" l'istante in cui era stato
    interrogato, con la durata dimezzata. Sul pannello sarebbe diventato un
    orario che lampeggia annunciando un sorgere gia' avvenuto, e due
    preavvisi caduti nel passato. Di cosa c'e' in cielo *adesso* risponde
    `sopra_adesso`, che e' la domanda giusta per quel caso.

    **Alla fine:** si guarda oltre il bordo quanto basta a chiudere l'ultimo
    passaggio, ma si tiene solo quello che **sorge** dentro la finestra.
    """
    sat = voce["sat"]
    trovati = []
    passo = timedelta(seconds=PASSO)
    limite = a + timedelta(minutes=MARGINE_MIN)

    partenza = _elevazione(sat, da, lat, lon, quota_km)
    # `saltando` resta vero finche' non si e' visto il satellite scendere
    # sotto la soglia almeno una volta: solo da quel momento un passaggio
    # comincia davvero sotto i nostri occhi.
    saltando = partenza is not None and partenza >= elevazione_minima

    quando = da
    dentro = False
    inizio_griglia = None
    campioni = []
    while quando <= limite:
        el = _elevazione(sat, quando, lat, lon, quota_km)
        if el is None:
            quando += passo
            continue
        if saltando:
            if el < elevazione_minima:
                saltando = False
            quando += passo
            continue
        if el >= elevazione_minima:
            if not dentro:
                if quando > a:
                    break  # comincia oltre la finestra: non e' roba nostra
                dentro = True
                inizio_griglia = quando - passo
                campioni = []
            campioni.append((quando, el))
        else:
            if dentro:
                dentro = False
                passaggio = _componi(voce, lat, lon, quota_km,
                                     elevazione_minima, inizio_griglia,
                                     campioni, quando)
                if passaggio and (passaggio["visibile"] or not solo_visibili):
                    trovati.append(passaggio)
            elif quando > a:
                break  # finestra finita e niente in corso: si smette
        quando += passo
    return trovati


def _picco(sat, sinistra, destra, lat, lon, quota_km):
    """Il culmine vero, cercato fra due istanti che lo contengono.

    Serve per lo stesso motivo della bisezione sui bordi: il massimo della
    griglia a trenta secondi non e' il massimo dell'arco. Senza, l'avviso
    annuncia "75 gradi" e la vista dal vivo, che calcola l'istante per
    istante, ne mostra 77 -- due numeri diversi per la stessa cosa, che chi
    guarda legge come un difetto.

    Ricerca ternaria: a ogni giro si butta un terzo dell'intervallo. Venti
    giri su un minuto arrivano ben sotto il secondo.
    """
    for _ in range(20):
        terzo = (destra - sinistra) / 3
        a, b = sinistra + terzo, destra - terzo
        ea = _elevazione(sat, a, lat, lon, quota_km)
        eb = _elevazione(sat, b, lat, lon, quota_km)
        if ea is None or eb is None:
            break
        if ea < eb:
            sinistra = a
        else:
            destra = b
    meta = sinistra + (destra - sinistra) / 2
    return meta, (_elevazione(sat, meta, lat, lon, quota_km) or 0.0)


def _ombra(sat, prima, dopo, lat, lon, quota_km):
    """L'istante esatto in cui il satellite entra nell'ombra della Terra.

    E' il momento piu' spettacolare che il cielo offra a occhio nudo: il
    puntino non tramonta, **si spegne**, a meta' cielo, in tre o quattro
    secondi. Chi non se l'aspetta pensa di aver perso di vista un aereo.

    Stessa bisezione dei bordi del passaggio, applicata a una domanda diversa:
    illuminato si', illuminato no.
    """
    for _ in range(18):
        meta = prima + (dopo - prima) / 2
        jd, fr = _giuliano(meta)
        errore, r, _v = sat.sgp4(jd, fr)
        if errore != 0:
            return meta
        if illuminato(r, jd, fr):
            prima = meta
        else:
            dopo = meta
    return prima + (dopo - prima) / 2


def _componi(voce, lat, lon, quota_km, soglia, prima, campioni, dopo):
    if not campioni:
        return None
    sat = voce["sat"]
    sorge = _confine(sat, prima, campioni[0][0], lat, lon, quota_km, soglia)
    tramonta = _confine(sat, campioni[-1][0], dopo, lat, lon, quota_km, soglia)
    grezzo = max(range(len(campioni)), key=lambda i: campioni[i][1])
    sinistra = campioni[grezzo - 1][0] if grezzo > 0 else sorge
    destra = campioni[grezzo + 1][0] if grezzo + 1 < len(campioni) else tramonta
    culmine, massima = _picco(sat, sinistra, destra, lat, lon, quota_km)

    # Visibile: in almeno un istante del passaggio il satellite e' al sole e
    # qui e' buio. Si controlla sui campioni, non solo al culmine: un
    # passaggio puo' cominciare illuminato e spegnersi a meta'.
    visibile = False
    illuminato_al_culmine = False
    for istante, _el in campioni:
        vista = guarda(sat, istante, lat, lon, quota_km)
        if vista is None:
            continue
        buio = elevazione_sole(istante, lat, lon) <= BUIO_GRADI
        if vista["illuminato"] and buio:
            visibile = True
            if istante == culmine:
                illuminato_al_culmine = True
    # Lo spegnimento: se il passaggio comincia illuminato e finisce in ombra,
    # da qualche parte in mezzo il puntino sparisce. Misurato su 28 giorni,
    # capita nel 13% dei passaggi visibili.
    spegnimento = None
    acceso_prima = None
    for istante, _el in campioni:
        jd, fr = _giuliano(istante)
        errore, r, _v = sat.sgp4(jd, fr)
        if errore != 0:
            continue
        adesso_acceso = illuminato(r, jd, fr)
        if acceso_prima and not adesso_acceso and spegnimento is None:
            spegnimento = _ombra(sat, precedente, istante, lat, lon, quota_km)
        acceso_prima = adesso_acceso
        precedente = istante

    vista_sorgere = guarda(sat, sorge, lat, lon, quota_km) or {}
    vista_tramonto = guarda(sat, tramonta, lat, lon, quota_km) or {}
    return {
        "nome": voce["nome"],
        # L'oggetto orbitale che ha generato questo passaggio. Senza, la
        # schermata del passaggio in corso -- l'arco con il puntino -- non
        # puo' sapere dov'e' il satellite *adesso*, e infatti per quattro
        # versioni ha sollevato `KeyError: 'sat'` a ogni fotogramma. Non si
        # scrive nel registro CSV e non finisce in nessun JSON: la pagina web
        # costruisce i suoi dizionari a parte.
        "sat": sat,
        "breve": voce.get("breve", voce["nome"]),
        "noto": voce.get("noto", False),
        "norad": voce["norad"],
        "gruppo": voce.get("gruppo", ""),
        "magnitudine": voce.get("magnitudine"),
        "sorge": sorge,
        "culmine": culmine,
        "tramonta": tramonta,
        "durata_min": (tramonta - sorge).total_seconds() / 60.0,
        "elevazione_massima": massima,
        "azimut_sorge": vista_sorgere.get("azimut"),
        "azimut_tramonta": vista_tramonto.get("azimut"),
        "visibile": visibile,
        "illuminato_al_culmine": illuminato_al_culmine,
        # Se non e' None, il puntino sparisce a quest'ora invece di tramontare.
        "spegnimento": spegnimento,
    }


# Quanto devono somigliarsi due passaggi per essere lo stesso puntino in
# cielo. Sono soglie strette apposta: due satelliti diversi che sorgono entro
# venti secondi l'uno dall'altro capitano (l'abbiamo visto: due SL-16 nello
# stesso minuto), ma con la **stessa** elevazione massima e lo **stesso**
# punto di sorgere no -- quelli sono in formazione, cioe' attaccati.
VICINI_S = 20.0
VICINI_GRADI = 1.0
VICINI_AZIMUT = 8.0


def _stesso_evento(a, b):
    if abs((a["sorge"] - b["sorge"]).total_seconds()) > VICINI_S:
        return False
    if abs(a["elevazione_massima"] - b["elevazione_massima"]) > VICINI_GRADI:
        return False
    za, zb = a.get("azimut_sorge"), b.get("azimut_sorge")
    if za is None or zb is None:
        return True
    scarto = abs((za - zb + 180.0) % 360.0 - 180.0)
    return scarto <= VICINI_AZIMUT


def _migliore(a, b):
    """Fra due righe dello stesso passaggio, quale nome tenere.

    Vince chi ha una magnitudine nota -- vuol dire che lo conosciamo davvero
    -- e a parita' il numero NORAD piu' basso, che e' quasi sempre il corpo
    principale: la ISS e' 25544, i moduli agganciati dopo hanno numeri molto
    piu' alti. Cosi' un passaggio della stazione si chiama "ISS" e non
    "CREW DRAGON 12".
    """
    if (a.get("magnitudine") is None) != (b.get("magnitudine") is None):
        return a if a.get("magnitudine") is not None else b
    return a if a["norad"] <= b["norad"] else b


def raggruppa(elenco):
    """Un passaggio per ogni puntino in cielo, non per ogni riga di catalogo.

    Il catalogo numera separatamente i moduli e le navette agganciate alla
    ISS: Zarya, Nauka, Poisk, la Crew Dragon di turno. In orbita sono un
    oggetto solo e a occhio nudo un punto solo, ma senza questo il pannello
    darebbe cinque avvisi identici per lo stesso passaggio -- e chi guarda
    penserebbe che il DMD sia rotto, non il catalogo.
    """
    fuori = []
    for p in sorted(elenco, key=lambda q: q["sorge"]):
        for i, gia in enumerate(fuori):
            if _stesso_evento(gia, p):
                fuori[i] = _migliore(gia, p)
                break
        else:
            fuori.append(p)
    return fuori


def prossimi(elenco, lat, lon, da, ore=24, quota_km=0.0,
             elevazione_minima=10.0, solo_visibili=True, massimo=20,
             solo_noti=True):
    """I passaggi di tutti i satelliti dell'elenco, in ordine di tempo.

    `solo_noti` tiene soltanto gli oggetti della tabella `NOTI`, cioe' quelli
    che sappiamo visibili a occhio nudo. E' acceso di mestiere perche' lo
    scopo della sorgente e' far uscire qualcuno a guardare: annunciare un
    CubeSat invisibile non e' un'imprecisione, e' una promessa mancata.
    """
    a = da + timedelta(hours=ore)
    if solo_noti:
        elenco = [v for v in elenco if v.get("noto")]
    tutti = []
    for voce in elenco:
        try:
            tutti.extend(passaggi(voce, lat, lon, da, a, quota_km,
                                  elevazione_minima, solo_visibili))
        except Exception as exc:
            print("[satelliti] %s: %s" % (voce.get("nome", "?"), exc))
    tutti = raggruppa(tutti)
    tutti.sort(key=lambda p: p["sorge"])
    return tutti[:massimo]


def sopra_adesso(elenco, lat, lon, quando=None, quota_km=0.0,
                 elevazione_minima=30.0, massimo=20):
    """Chi c'e' sopra la testa in questo istante, visibile o no.

    E' la seconda modalita': il gemello dell'Air Radar. Ordinati per
    elevazione, i piu' alti per primi, perche' sono quelli che davvero hai
    sopra e non all'orizzonte.
    """
    quando = quando or datetime.now(timezone.utc)
    buio = elevazione_sole(quando, lat, lon) <= BUIO_GRADI
    fuori = []
    for voce in elenco:
        vista = guarda(voce["sat"], quando, lat, lon, quota_km)
        if vista is None or vista["elevazione"] < elevazione_minima:
            continue
        fuori.append({
            "nome": voce["nome"],
            "breve": voce.get("breve", voce["nome"]),
            "noto": voce.get("noto", False),
            "norad": voce["norad"],
            "gruppo": voce.get("gruppo", ""),
            "magnitudine": voce.get("magnitudine"),
            "elevazione": vista["elevazione"],
            "azimut": vista["azimut"],
            "distanza": vista["distanza"],
            "illuminato": vista["illuminato"],
            "visibile": vista["illuminato"] and buio,
        })
    fuori.sort(key=lambda v: -v["elevazione"])
    return fuori[:massimo]


# ------------------------------------------------------------- i tre momenti

# Il preavviso e la cadenza dei promemoria. Un passaggio della ISS non dura
# mai piu' di sette minuti, misurati: annunciarlo quando e' gia' sopra la
# testa vuol dire arrivare in terrazzo a cose finite. Dieci minuti bastano per
# uscire **prima** che sorga e prenderlo basso all'orizzonte.
PREAVVISO_MIN = 10
CADENZA_MIN = 5


def momenti(passaggio, preavviso=PREAVVISO_MIN, cadenza=CADENZA_MIN):
    """Gli istanti in cui il pannello ha qualcosa da dire su un passaggio.

    Tornano gia' etichettati: "avviso" mentre manca tempo, "adesso" mentre
    sta succedendo. Il chiamante ci mette sopra colore e lampeggio senza
    doversi rifare i conti, e soprattutto **si puo' provare**: e' una lista
    di istanti, non un comportamento nel tempo.
    """
    fuori = []
    minuto = preavviso
    while minuto >= cadenza:
        fuori.append({"quando": passaggio["sorge"] - timedelta(minutes=minuto),
                      "stato": "avviso", "mancano_min": minuto})
        minuto -= cadenza
    fuori.append({"quando": passaggio["sorge"], "stato": "adesso",
                  "fino_a": passaggio["tramonta"]})
    return fuori


def stato(passaggio, quando, preavviso=PREAVVISO_MIN):
    """In che stato e' questo passaggio adesso: avviso, adesso, o niente.

    E' la funzione che il disegno interroga a ogni fotogramma: da lei
    dipendono il colore e il fatto che l'ora lampeggi.
    """
    if passaggio["sorge"] <= quando <= passaggio["tramonta"]:
        return "adesso"
    anticipo = (passaggio["sorge"] - quando).total_seconds() / 60.0
    if 0 < anticipo <= preavviso:
        return "avviso"
    return ""
