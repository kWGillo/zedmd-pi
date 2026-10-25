# -*- coding: utf-8 -*-
"""16.4 - Gli aerei che passano sopra casa non si perdono piu'.

La segnalazione
---------------
*«Abbassando il raggio del radar a 1,5 km praticamente non rileva i passaggi.
Secondo me e' dovuto al tempo di scansione ogni 40 secondi.»* E poi, decisiva:
*«sono appena passati due aerei sopra la mia testa e li ho visti molto bene,
praticamente perpendicolari, e il DMD non li ha segnalati.»*

L'intuizione era giusta e il difetto era peggio del previsto. Un cerchio di
1,5 km di raggio lo si attraversa in una decina di secondi a velocita' di
crociera; chiedendo al provider solo il raggio -- arrotondato per eccesso a
miglia intere, quindi 2 NM, 3,7 km -- un aereo si vedeva **soltanto** se
l'interrogazione cadeva proprio in quei secondi. In quaranta secondi un aereo
in crociera fa nove chilometri: entrava e usciva fra due giri, e non compariva
da nessuna parte, nemmeno fra i vicini.

Le due meta' della correzione
-----------------------------
1. **Si interroga largo e si decide stretto.** Il raggio di interrogazione
   copre la strada che un aereo puo' fare fra due giri; il raggio della
   pagina torna a essere quello che dice di essere, cioe' il raggio di
   *conteggio*.
2. **Il passaggio si decide sulla traiettoria.** Due posizioni consecutive
   dello stesso aereo fanno un segmento, e quello che conta e' la distanza
   minima da casa lungo quel segmento -- anche quando nessuno dei due punti
   cadeva dentro il raggio. E' il caso dei due aerei perpendicolari.

E le due cose su cui questa prova insiste
-----------------------------------------
* **il raggio di ascolto ha un tetto**: l'intervallo si regola fino a un'ora,
  e senza tetto si sarebbero chieste cinquecento miglia nautiche a ogni giro
  a un servizio pubblico e gratuito;
* **nel registro va quello che e' successo**, non quello che sta per
  succedere: un passaggio soltanto previsto si mostra sul pannello e aspetta
  la conferma prima di diventare una riga di CSV con una distanza dentro.
"""

import math
import os
import sys
import tempfile

os.environ.setdefault("DMD_DATA", tempfile.mkdtemp())
os.environ.setdefault("DMD_CONFIG", os.path.join(tempfile.mkdtemp(), "config.json"))
# La radice del progetto si ricava da dove sta questo file, non da un percorso
# scritto a mano: cosi' la prova si lancia da qualunque cartella, e soprattutto
# **vive nel repository**. Le prove di questo progetto stavano in una cartella
# di servizio fuori dal repo; quando quella cartella e' sparita se le e' portate
# via tutte. Una prova che non sta nel progetto non esiste.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random

from sources.airradar import (KT_TO_MS, MEMORIA_TRACCE_S, TRATTO_MASSIMO_S,
                              VELOCITA_MASSIMA_MS, _piano_km,
                              avvicinamento_minimo, distanza_dal_segmento,
                              haversine_km, raggio_di_ascolto)

CASA = (45.07, 7.69)

esiti = []


def esigi(condizione, messaggio):
    esiti.append((bool(condizione), messaggio))
    print("%s %s" % ("OK  " if condizione else "FALLITO", messaggio))


def sep(titolo):
    print()
    print("=" * 74)
    print(titolo)
    print("=" * 74)


def punto(nord_km, est_km):
    """Una coordinata a tot chilometri da casa, verso nord e verso est."""
    lat = CASA[0] + nord_km / 110.574
    lon = CASA[1] + est_km / (111.320 * math.cos(math.radians(CASA[0])))
    return lat, lon


sep("1. La geometria, prima di tutto il resto")

esigi(abs(distanza_dal_segmento(-5.0, 1.0, 5.0, 1.0) - 1.0) < 1e-6,
      "un segmento che passa a un chilometro sopra l'origine dista un chilometro")
esigi(abs(distanza_dal_segmento(3.0, 4.0, 6.0, 8.0) - 5.0) < 1e-6,
      "se il piede della perpendicolare cade fuori, vale l'estremo piu' vicino")
esigi(abs(distanza_dal_segmento(2.0, 0.0, 2.0, 0.0) - 2.0) < 1e-6,
      "e un segmento lungo zero e' un punto, non una divisione per zero")

# Il piano locale deve essere d'accordo con la sfera: se non lo fosse, tutto
# il resto misurerebbe un'altra cosa.
for nord, est in ((0.0, 3.0), (5.0, -2.0), (-12.0, 9.0)):
    lat, lon = punto(nord, est)
    x, y = _piano_km(CASA[0], CASA[1], lat, lon)
    piano = math.hypot(x, y)
    sfera = haversine_km(CASA[0], CASA[1], lat, lon)
    # Mezzo per cento: i due numeri fissi del piano sono medie, e alla
    # latitudine di casa restano indietro di un terzo di punto. Su un raggio
    # di 1,5 km sono cinque metri, su quindici chilometri cinquanta: molto
    # meno di quanto si sposti un aereo fra due letture, che e' la scala su
    # cui si lavora qui.
    esigi(abs(piano - sfera) <= max(0.02, sfera * 0.005),
          "a %.0f km il piano e la sfera concordano entro mezzo per cento "
          "(%.3f contro %.3f, %.0f m)"
          % (sfera, piano, sfera, abs(piano - sfera) * 1000))

sep("2. Si interroga largo, e non piu' largo del necessario")

esigi(raggio_di_ascolto(1.5, 2.0, 40) > 9.0,
      "con raggio 1,5 km e giri da 40 s si chiedono piu' di nove chilometri: "
      "e' la strada che un aereo fa fra un giro e l'altro (%.1f km)"
      % raggio_di_ascolto(1.5, 2.0, 40))
esigi(raggio_di_ascolto(1.5, 2.0, 40) >= 1.5 + 2.0,
      "e comunque mai meno del raggio piu' il margine di cortesia")
esigi(raggio_di_ascolto(50.0, 2.0, 20) >= 50.0,
      "con un raggio grande il raggio resta il minimo (%.1f)"
      % raggio_di_ascolto(50.0, 2.0, 20))
crescente = [raggio_di_ascolto(1.5, 2.0, s) for s in (15, 20, 30, 40, 60)]
esigi(crescente == sorted(crescente),
      "piu' lento e' il giro, piu' lontano si guarda")

# Il tetto. Senza, un intervallo da un'ora -- che la pagina Radar permette --
# avrebbe chiesto novecento chilometri di raggio a ogni giro.
tetto = raggio_di_ascolto(1.5, 2.0, 3600)
esigi(tetto < 45.0,
      "ma a un'ora di intervallo non si chiedono 900 km: il tetto tiene "
      "l'interrogazione a %.0f km (%d NM)" % (tetto, math.ceil(tetto / 1.852)))
esigi(abs(raggio_di_ascolto(1.5, 2.0, 3600)
          - raggio_di_ascolto(1.5, 2.0, TRATTO_MASSIMO_S)) < 1e-6,
      "e il tetto e' proprio li' dove due posizioni smettono di potersi unire "
      "(%.0f s): oltre, guardare piu' lontano non aggiunge un passaggio"
      % TRATTO_MASSIMO_S)

sep("3. I due aerei perpendicolari, quelli che hanno fatto nascere tutto")

# Due letture a quaranta secondi, 4,5 km da una parte e 4,5 dall'altra: con il
# vecchio metodo nessuna delle due cade nel raggio da 1,5 km, e l'aereo non
# e' mai esistito. Eppure e' passato esattamente sopra la testa.
prima = punto(0.2, -4.5)
dopo = punto(-0.2, 4.5)
vecchio = min(haversine_km(CASA[0], CASA[1], *prima),
              haversine_km(CASA[0], CASA[1], *dopo))
nuovo, come = avvicinamento_minimo(
    CASA, {"lat": dopo[0], "lon": dopo[1], "gs": None, "track": None},
    1000.0, (prima[0], prima[1], 960.0), 40)
esigi(vecchio > 1.5,
      "con il metodo vecchio il punto piu' vicino era a %.1f km: fuori dal "
      "raggio, quindi niente" % vecchio)
esigi(nuovo < 0.3 and come == "tratto",
      "con il tratto fra le due letture passa a %.2f km, cioe' sopra casa "
      "(%s)" % (nuovo, come))

# Il tratto non si inventa: due letture troppo lontane nel tempo non si
# uniscono, perche' in mezzo l'aereo puo' aver virato.
_vecchie, come_vecchie = avvicinamento_minimo(
    CASA, {"lat": dopo[0], "lon": dopo[1], "gs": None, "track": None},
    1000.0, (prima[0], prima[1], 1000.0 - TRATTO_MASSIMO_S - 10), 40)
esigi(come_vecchie != "tratto",
      "due posizioni lontane piu' di %.0f s non si uniscono: in mezzo l'aereo "
      "puo' aver fatto altro" % TRATTO_MASSIMO_S)

# E un salto impossibile e' un dato sbagliato, non un aereo supersonico.
lontano = punto(0.0, 300.0)
_d, come_salto = avvicinamento_minimo(
    CASA, {"lat": dopo[0], "lon": dopo[1], "gs": None, "track": None},
    1000.0, (lontano[0], lontano[1], 995.0), 40)
esigi(come_salto != "tratto",
      "trecento chilometri in cinque secondi non sono un aereo: il tratto si "
      "scarta")

sep("4. La previsione: mostrarlo mentre arriva, non un giro dopo")

# Un aereo a nove chilometri che punta dritto verso casa a 450 nodi: fra
# quaranta secondi e' sopra. Con la sola posizione attuale sarebbe «lontano».
arrivo = punto(9.0, 0.0)
distanza, come = avvicinamento_minimo(
    CASA, {"lat": arrivo[0], "lon": arrivo[1], "gs": 450, "track": 180},
    1000.0, None, 40)
esigi(come == "previsto" and distanza < 1.0,
      "chi punta dritto verso casa si vede adesso, non al giro dopo "
      "(%.2f km, %s)" % (distanza, come))
lontano_adesso = haversine_km(CASA[0], CASA[1], *arrivo)
esigi(lontano_adesso > 8.0,
      "mentre la sua posizione di adesso e' a %.1f km" % lontano_adesso)

# Chi se ne va non si prevede addosso.
fuga = punto(2.0, 0.0)
distanza, _come = avvicinamento_minimo(
    CASA, {"lat": fuga[0], "lon": fuga[1], "gs": 450, "track": 0},
    1000.0, None, 40)
esigi(distanza >= 1.9,
      "e chi si allontana resta lontano: non ci si avvicina mai (%.2f km)"
      % distanza)

# Un aereo fermo o quasi non si proietta: a terra, la rotta non vuol dire niente.
fermo = punto(1.0, 0.0)
_d, come_fermo = avvicinamento_minimo(
    CASA, {"lat": fermo[0], "lon": fermo[1], "gs": 5, "track": 180},
    1000.0, None, 40)
esigi(come_fermo == "attuale",
      "sotto i trenta nodi non si proietta niente: a terra la rotta non dice "
      "dove andra'")

sep("5. Duemila aerei: quanti se ne perdevano, quanti se ne perdono")

random.seed(20261018)
RAGGIO = 1.5
INTERVALLO = 40.0

visti_vecchio = visti_nuovo = passaggi = 0
falsi_nuovo = 0
vicinissimi = vicinissimi_vecchio = 0

for _ in range(2000):
    # Una rotta a caso che attraversa la zona, con un parametro d'urto fra 0
    # e 3 km e una velocita' da piccolo turboelica a liner.
    urto = random.uniform(0.0, 3.0)
    direzione = random.uniform(0, 2 * math.pi)
    velocita_ms = random.uniform(80, 240)
    # Il punto di massimo avvicinamento, e la retta che ci passa.
    cx, cy = urto * math.cos(direzione), urto * math.sin(direzione)
    ux, uy = -math.sin(direzione), math.cos(direzione)
    # La fase dell'interrogazione rispetto al passaggio e' casuale: e' tutto
    # il problema.
    fase = random.uniform(0, INTERVALLO)

    def dove(t):
        """Posizione al tempo t, in km dal centro, lungo la rotta."""
        s = (t - 60.0) * velocita_ms / 1000.0
        return cx + s * ux, cy + s * uy

    dentro_davvero = urto <= RAGGIO
    if dentro_davvero:
        passaggi += 1

    # Le interrogazioni: ogni 40 s, per tre minuti.
    campioni = [dove(fase + k * INTERVALLO) for k in range(5)]

    # Il metodo vecchio: dentro solo se un campione cade nel raggio. E non
    # basta: il provider veniva interrogato a 2 NM, quindi i campioni oltre
    # 3,7 km non arrivavano nemmeno.
    vecchio_ok = any(math.hypot(x, y) <= RAGGIO for x, y in campioni
                     if math.hypot(x, y) <= 3.7)
    # Il nuovo: la distanza minima lungo i tratti fra campioni consecutivi.
    nuovo_ok = False
    for (ax, ay), (bx, by) in zip(campioni, campioni[1:]):
        if max(math.hypot(ax, ay), math.hypot(bx, by)) > raggio_di_ascolto(
                RAGGIO, 2.0, INTERVALLO):
            continue
        if distanza_dal_segmento(ax, ay, bx, by) <= RAGGIO:
            nuovo_ok = True
            break

    if dentro_davvero:
        visti_vecchio += vecchio_ok
        visti_nuovo += nuovo_ok
        if urto <= 0.3:
            vicinissimi += 1
            vicinissimi_vecchio += vecchio_ok
    elif nuovo_ok:
        falsi_nuovo += 1

print("   passaggi veri entro %.1f km: %d" % (RAGGIO, passaggi))
print("   visti con il metodo vecchio: %d (%.0f%%)"
      % (visti_vecchio, 100.0 * visti_vecchio / passaggi))
print("   visti con il metodo nuovo:   %d (%.0f%%)"
      % (visti_nuovo, 100.0 * visti_nuovo / passaggi))
print("   di quelli passati entro 300 m: %d su %d con il vecchio"
      % (vicinissimi_vecchio, vicinissimi))
print("   falsi passaggi con il nuovo: %d" % falsi_nuovo)

esigi(visti_vecchio < passaggi * 0.6,
      "il metodo vecchio ne perdeva piu' di un terzo (ne vedeva il %.0f%%)"
      % (100.0 * visti_vecchio / passaggi))
esigi(visti_nuovo >= passaggi * 0.99,
      "il nuovo li vede praticamente tutti (%.0f%%)"
      % (100.0 * visti_nuovo / passaggi))
esigi(falsi_nuovo == 0,
      "e non inventa passaggi per chi e' rimasto fuori (%d)" % falsi_nuovo)
esigi(vicinissimi_vecchio < vicinissimi,
      "anche di quelli passati a meno di trecento metri -- sopra la testa -- "
      "il vecchio ne perdeva (%d su %d)" % (vicinissimi_vecchio, vicinissimi))

sep("6. Nel registro va quello che e' successo")

import csv as _csv

import dmdconf
from sources.airradar import AirRadarSource

cfg = dmdconf.load()
cartella = tempfile.mkdtemp()
cfg["air_radar"]["log_path"] = os.path.join(cartella, "flights.csv")
cfg["air_radar"]["log_enabled"] = True
cfg["air_radar"]["log_route"] = False
radar = AirRadarSource(cfg, 256, 64)


def scrivi(passaggio, hexcode):
    radar._log_flights([{
        "hex": hexcode, "flight": "TEST123", "type": "A320", "reg": "I-TEST",
        "altitude": 3000, "speed": 300, "track": 180, "squawk": "1000",
        "distance": 0.4, "passaggio": passaggio, "lat": 45.0, "lon": 7.0,
    }], cfg["air_radar"])


def righe():
    if not os.path.exists(cfg["air_radar"]["log_path"]):
        return []
    with open(cfg["air_radar"]["log_path"], newline="") as handle:
        return list(_csv.reader(handle))[1:]


scrivi("previsto", "AAA001")
esigi(righe() == [],
      "un passaggio soltanto previsto non entra nel registro: se vira, non "
      "e' mai successo")
scrivi("tratto", "AAA001")
esigi(len(righe()) == 1,
      "al giro dopo, confermato dal tratto, la riga c'e' (%d)" % len(righe()))
scrivi("attuale", "BBB002")
esigi(len(righe()) == 2, "e un passaggio visto direttamente entra subito")
scrivi("attuale", "BBB002")
esigi(len(righe()) == 2,
      "ma lo stesso aereo non si scrive due volte nello stesso passaggio")

sep("7. Il giro intero, con un provider finto")

# Le prove qui sopra guardano i pezzi; questa guarda la catena: quanto si
# chiede al provider, che cosa si fa con le due letture, che cosa finisce nel
# registro. E' il punto in cui un errore di cablaggio non si vedrebbe.
import sources.airradar as _radar

cfg["air_radar"]["radius_km"] = 1.5
cfg["air_radar"]["margine_km"] = 2.0
cfg["air_radar"]["poll_interval"] = 40
cfg["air_radar"]["log_path"] = os.path.join(tempfile.mkdtemp(), "voli.csv")
# Le rotte le chiede alla rete: qui non serve, e un errore di rete stampato in
# mezzo a una prova fa cercare un guasto che non c'e'.
cfg["air_radar"]["log_route"] = False
cfg["air_radar"]["fields"] = ["type", "altitude", "distance"]
cfg["posizione"]["latitude"] = CASA[0]
cfg["posizione"]["longitude"] = CASA[1]
radar2 = AirRadarSource(cfg, 256, 64)

chiesto = []
risposte = []


def _finto_fetch(url, timeout=12):
    chiesto.append(url)
    return risposte.pop(0)


_vero_fetch = _radar.fetch_json
_radar.fetch_json = _finto_fetch
try:
    # La prima lettura e' vecchia di quaranta secondi: e' il campo `seen_pos`,
    # ed e' anche il modo di far passare il tempo dentro una prova che dura un
    # millesimo di secondo. I due giri si trovano cosi' a quaranta secondi di
    # distanza, come sul Raspberry.
    a_lat, a_lon = punto(0.2, -4.5)
    risposte.append({"ac": [{"hex": "ABC123", "flight": "TEST01",
                             "lat": a_lat, "lon": a_lon, "alt_baro": 9000,
                             "gs": 300, "track": 90, "seen_pos": 40}]})
    primo = radar2._poll(cfg["air_radar"])
    nm_chiesti = float(chiesto[0].rstrip("/").rsplit("/", 1)[-1])
    esigi(nm_chiesti * 1.852 > 9.0,
          "al provider si chiedono %.0f NM, cioe' %.0f km: la strada che un "
          "aereo fa fra due giri" % (nm_chiesti, nm_chiesti * 1.852))
    esigi(not primo or primo[0]["passaggio"] == "previsto",
          "al primo giro l'aereo e' fuori dal raggio di conteggio, o al piu' "
          "previsto in arrivo")

    b_lat, b_lon = punto(-0.2, 4.5)
    risposte.append({"ac": [{"hex": "ABC123", "flight": "TEST01",
                             "lat": b_lat, "lon": b_lon, "alt_baro": 9000,
                             "gs": 300, "track": 90, "seen_pos": 0}]})
    secondo = radar2._poll(cfg["air_radar"])
    esigi(len(secondo) == 1,
          "al secondo giro il passaggio c'e' (%d aerei nel raggio)"
          % len(secondo))
    if secondo:
        esigi(secondo[0]["distance"] < 0.5,
              "ed e' passato a %.2f km da casa, cioe' sopra la testa"
              % secondo[0]["distance"])
        esigi(secondo[0]["passaggio"] == "tratto",
              "riconosciuto dal tratto fra le due letture, non dal punto")
    with open(cfg["air_radar"]["log_path"], newline="") as handle:
        scritte = list(_csv.reader(handle))[1:]
    esigi(len(scritte) == 1 and scritte[0][1] == "ABC123",
          "e nel registro c'e' una riga sola, con il suo codice Mode S")
    colonna = _radar.CSV_COLUMNS.index("distance_km")
    esigi(float(scritte[0][colonna]) < 0.5,
          "con la distanza minima di passaggio, non quella di quando si e' "
          "guardato (%s km)" % scritte[0][colonna])
finally:
    _radar.fetch_json = _vero_fetch

sep("8. La memoria delle tracce non cresce per sempre")

esigi(MEMORIA_TRACCE_S >= 2 * TRATTO_MASSIMO_S,
      "si ricordano le posizioni piu' a lungo di quanto si possano unire "
      "(%.0f s contro %.0f)" % (MEMORIA_TRACCE_S, TRATTO_MASSIMO_S))
esigi(VELOCITA_MASSIMA_MS * 3.6 >= 800,
      "e la velocita' massima considerata e' da aereo di linea (%.0f km/h)"
      % (VELOCITA_MASSIMA_MS * 3.6))
esigi(abs(KT_TO_MS - 0.514444) < 1e-6, "un nodo resta un nodo")

sep("9. La sfilata non si mangia l'intervallo (17.4.14)")

# *«Quando amplio il raggio del radar e ho molti voli all'interno dell'area,
# il radar va in confusione»*, e quello che si vedeva erano **dati
# sbagliati**. Il motivo e' che la sfilata non aveva un tetto: trenta aerei
# da dieci secondi sono cinque minuti, e quello che si legge sul pannello e'
# la fotografia scattata all'inizio del giro. Al quinto minuto la distanza
# minima di passaggio di quell'aereo e' una notizia vecchia -- e la cadenza
# vera, cinque minuti, sfonda anche `TRATTO_MASSIMO_S`, quindi il radar
# perde il suo stimatore migliore proprio quando c'e' piu' traffico.


class Finto:
    """Un orologio che cammina solo quando glielo si dice."""

    def __init__(self, adesso=1000.0):
        self.adesso = adesso

    def time(self):
        return self.adesso

    def monotonic(self):
        return self.adesso

    def sleep(self, quanto):
        self.adesso += quanto


def radar_di_prova(quanti):
    conf = dmdconf.load()
    conf["air_radar"]["display_seconds"] = 10
    conf["air_radar"]["cooldown"] = 600
    conf["air_radar"]["fields"] = ["distance"]
    conf["air_radar"]["log_enabled"] = False
    r = _radar.AirRadarSource(conf, 256, 64)
    r._running = True
    aerei = [{"hex": "AAA%03d" % i, "flight": "FL%03d" % i,
              "distance": 0.5 + i * 0.1} for i in range(quanti)]
    return r, conf["air_radar"], aerei


orologio = Finto()
_vero_time = _radar.time
_radar.time = orologio
try:
    radar, conf_radar, aerei = radar_di_prova(30)
    radar._mostra = lambda plane, cfg, durata: orologio.sleep(durata)

    partenza = orologio.time()
    radar._show_all(aerei, conf_radar, scadenza=partenza + 20)
    durata = orologio.time() - partenza
    esigi(durata <= 20,
          "trenta aerei nel raggio e la sfilata dura al massimo l'intervallo"
          " (%.0f s su 20)" % durata)
    esigi(radar._mostrati == 2 and radar._saltati == 28,
          "ne passano due e ventotto restano in lista (%d e %d)"
          % (radar._mostrati, radar._saltati))
    esigi(len(radar._recent) == radar._mostrati,
          "e **solo i mostrati** vanno in riposo: gli altri al giro dopo"
          " hanno la precedenza (%d in riposo)" % len(radar._recent))
    fermi = [p["hex"] for p in aerei if p["hex"] not in radar._recent]
    esigi(fermi and fermi[0] == aerei[2]["hex"],
          "il primo della lista al prossimo giro e' il terzo piu' vicino,"
          " perche' l'elenco e' ordinato per distanza")

    # E senza scadenza -- come faceva fino alla 17.4.12 -- la stessa sfilata
    # dura cinque minuti: il numero da cui e' nata la segnalazione.
    radar2, conf2, aerei2 = radar_di_prova(30)
    radar2._mostra = lambda plane, cfg, durata: orologio.sleep(durata)
    partenza = orologio.time()
    radar2._show_all(aerei2, conf2)
    vecchia = orologio.time() - partenza
    esigi(vecchia >= 300,
          "senza tetto la stessa sfilata durava %.0f secondi, cioe' %d volte"
          " l'intervallo" % (vecchia, int(vecchia // 20)))
    esigi(vecchia > TRATTO_MASSIMO_S,
          "piu' di quanto due posizioni si possano unire (%.0f s contro %.0f):"
          " con molto traffico il radar perdeva i tratti" % (vecchia,
                                                             TRATTO_MASSIMO_S))

    # L'intervallo piu' corto della durata: un aereo si mostra comunque.
    radar3, conf3, aerei3 = radar_di_prova(5)
    radar3._mostra = lambda plane, cfg, durata: orologio.sleep(durata)
    radar3._show_all(aerei3, conf3, scadenza=orologio.time() + 5)
    esigi(radar3._mostrati == 1,
          "con l'intervallo piu' corto della durata ne passa comunque uno")

    # Pochi aerei: non cambia niente rispetto a prima.
    radar4, conf4, aerei4 = radar_di_prova(2)
    radar4._mostra = lambda plane, cfg, durata: orologio.sleep(durata)
    radar4._show_all(aerei4, conf4, scadenza=orologio.time() + 30)
    esigi(radar4._mostrati == 2 and radar4._saltati == 0,
          "e con due aerei nel raggio sfilano tutti e due, come sempre")
finally:
    _radar.time = _vero_time


print()
print("=" * 74)
falliti = [m for ok, m in esiti if not ok]
if falliti:
    print("FALLITI %d su %d" % (len(falliti), len(esiti)))
    for m in falliti:
        print("  - %s" % m)
    sys.exit(1)
print("TUTTO BENE: %d prove" % len(esiti))
