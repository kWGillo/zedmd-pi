# -*- coding: utf-8 -*-
"""16.5 - Nati e morti: famosi, non recenti.

La segnalazione
---------------
*«Nel servizio delle informazioni inutili, ho notato che il display mostra
sempre nati nella seconda meta' degli anni 90 e morti nel 2024.»*

Una riga sola di codice, e una giustificazione che sembrava buona:

    # Dalle piu' recenti: sono quelle che uno riconosce.
    voci.sort(key=lambda v: -v[0])
    fuori[etichetta] = voci[:QUANTI]

Per i **fatti** e' vero -- un fatto recente e' un fatto che hai vissuto -- e
infatti per "accadde oggi" quella regola e' rimasta. Per le **persone** e'
esattamente al contrario:

* l'anno di nascita piu' recente seleziona chi e' appena arrivato, cioe'
  calciatori e cantanti del 1997 di cui Wikipedia sa tutto perche' sono di
  oggi, non perche' siano famosi;
* l'anno di morte piu' recente inchioda il pannello ai necrologi dell'anno
  scorso, e ce li tiene per dodici mesi.

La correzione
-------------
Si smette di misurare la fama con l'orologio. Fra i candidati del giorno si
tengono i **piu' letti su it.wikipedia nell'ultimo mese**: e' il numero che
dice quanta gente, in Italia, e' andata a cercare quella persona. Le letture
arrivano nella stessa chiamata delle descrizioni brevi, quindi non costano
una richiesta in piu'.

E quando le letture non si sanno -- estensione assente, rete caduta a meta'
-- non si torna al difetto: si pescano i nomi **a ventaglio** su tutto l'arco
degli anni, che e' sbagliato quanto si vuole ma non e' monotono.
"""

import os
import sys
import tempfile

os.environ.setdefault("DMD_DATA", tempfile.mkdtemp())
os.environ.setdefault("DMD_CONFIG", os.path.join(tempfile.mkdtemp(), "config.json"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import inutili

esiti = []


def esigi(condizione, messaggio):
    esiti.append((bool(condizione), messaggio))
    print("%s %s" % ("OK  " if condizione else "FALLITO", messaggio))


def sep(titolo):
    print()
    print("=" * 74)
    print(titolo)
    print("=" * 74)


# --------------------------------------------------------------- il campione
#
# Una giornata verosimile: tanti nati da poco e pochi antichi, perche' e'
# cosi' che e' fatto il feed. Il quarto numero sono le letture del mese su
# it.wikipedia: i nomi che chiunque riconosce ne hanno decine di migliaia,
# gli altri qualche centinaio.

NATI = [
    (1452, "Leonardo", "pittore e inventore", 94000),
    (1564, "Shakespeare", "drammaturgo", 61000),
    (1707, "Eulero", "matematico", 22000),
    (1813, "Verdi", "compositore", 38000),
    (1889, "Chaplin", "attore", 41000),
    (1901, "Ferrari", "costruttore", 29000),
    (1920, "Wojtyla", "papa", 57000),
    (1943, "De Andre", "cantautore", 33000),
    (1955, "Jobs", "imprenditore", 26000),
    (1968, "Totti", "calciatore", 19000),
]
for _i in range(30):                 # la coda del feed: i nuovi arrivati
    NATI.append((1985 + _i % 18, "Nuovo%02d" % _i, "calciatore", 120 + _i))

MORTI = [
    (1321, "Dante", "poeta", 88000),
    (1519, "Machiavelli", "politico", 24000),
    (1827, "Beethoven", "compositore", 45000),
    (1890, "Van Gogh", "pittore", 52000),
    (1975, "Pasolini", "regista", 31000),
    (1989, "Hirohito", "imperatore", 9000),
]
for _i in range(26):                 # i necrologi dell'anno scorso
    MORTI.append((2024, "Scomparso%02d" % _i, "attore", 200 + _i))

VISTE = {v[1]: v[3] for v in NATI + MORTI}


def feed(tipo, voci):
    return {tipo: [{"year": anno,
                    "pages": [{"titles": {"normalized": nome},
                               "description": mestiere}]}
                   for anno, nome, mestiere, _v in voci]}


def finto_chiedi(url):
    """Wikipedia per finta: il feed, i langlinks, le descrizioni+letture."""
    chiamate.append(url)
    if "/feed/onthisday/" in url:
        if "//it.wikipedia" in url:
            return {}                 # il feed italiano e' vuoto, sempre
        if "/births/" in url:
            return feed("births", NATI)
        return feed("deaths", MORTI)
    titoli = [t.replace("+", " ").replace("%20", " ")
              for t in url.split("titles=")[1].split("&")[0].split("%7C")]
    if "prop=langlinks" in url:
        return {"query": {"pages": [{"title": t,
                                     "langlinks": [{"lang": "it", "title": t}]}
                                    for t in titoli]}}
    pagine = []
    for t in titoli:
        pagina = {"title": t, "description": "descrizione di %s" % t}
        if "pageviews" in url:
            pagina["pageviews"] = {"2026-10-%02d" % (g + 1): VISTE.get(t, 0) // 30
                                   for g in range(30)}
            pagina["pageviews"]["2026-09-30"] = None   # giorno senza dato
        pagine.append(pagina)
    return {"query": {"pages": pagine}}


chiamate = []
inutili._chiedi = finto_chiedi


sep("1. Il ventaglio pesca su tutto l'arco degli anni")

tutti = [(a, n, m, v) for a, n, m, v in NATI]
rosa = inutili._a_ventaglio(tutti, 25)
esigi(len(rosa) == 25, "venticinque candidati su quaranta")
esigi(len(set(id(v) for v in rosa)) == 25, "e sono venticinque voci diverse")
esigi(min(v[0] for v in rosa) <= 1600,
      "il piu' antico della rosa e' antico davvero (%d)"
      % min(v[0] for v in rosa))
esigi(max(v[0] for v in rosa) >= 2000,
      "e il piu' recente e' recente (%d)" % max(v[0] for v in rosa))
esigi(inutili._a_ventaglio(tutti[:4], 25) == sorted(tutti[:4], key=lambda v: -v[0]),
      "con meno voci di quante ne servono si tiene tutto")
esigi(inutili._a_ventaglio([], 6) == [] and inutili._a_ventaglio(tutti, 0) == [],
      "e i casi vuoti non scoppiano")


sep("2. La vecchia regola riproduce la segnalazione")

vecchi_nati = sorted(NATI, key=lambda v: -v[0])[:6]
vecchi_morti = sorted(MORTI, key=lambda v: -v[0])[:6]
esigi(all(v[0] >= 1990 for v in vecchi_nati),
      "ordinando per anno i sei nati sono tutti dal 1990 in poi: e' il bug")
esigi(all(v[0] == 2024 for v in vecchi_morti),
      "e i sei morti sono tutti del 2024: e' l'altra meta' del bug")


sep("3. La regola nuova sceglie i piu' letti")

dati, errore = inutili.scarica()
esigi(not errore, "la giornata si scarica senza errori (%r)" % errore)
nati = dati["nati"]
morti = dati["morti"]
print("   nati:  %s" % ", ".join("%d %s" % (a, n) for a, n, _m in nati))
print("   morti: %s" % ", ".join("%d %s" % (a, n) for a, n, _m in morti))

esigi(len(nati) == 6 and len(morti) == 6, "sei per parte, come prima")
attesi = [n for _a, n, _m, _v in sorted(NATI, key=lambda v: -v[3])[:6]]
esigi(sorted(n for _a, n, _m in nati) == sorted(attesi),
      "i sei nati sono i sei piu' letti del giorno")
attesi = [n for _a, n, _m, _v in sorted(MORTI, key=lambda v: -v[3])[:6]]
esigi(sorted(n for _a, n, _m in morti) == sorted(attesi),
      "e i sei morti pure")
esigi(not any(a >= 1985 for a, _n, _m in nati),
      "nessun nato degli ultimi quarant'anni fa da riempitivo")
esigi(not any(a == 2024 for a, _n, _m in morti),
      "e nessun necrologio dell'anno scorso")
esigi(nati == sorted(nati, key=lambda v: -v[0]),
      "l'elenco resta ordinato per anno, dal piu' recente")
esigi(all(m.startswith("descrizione di ") for _a, _n, m in nati),
      "le descrizioni brevi italiane ci sono ancora")


sep("4. Quante richieste costa")

feed_chiamate = [u for u in chiamate if "/feed/onthisday/" in u]
query = [u for u in chiamate if "/w/api.php" in u]
esigi(len(feed_chiamate) == 4,
      "quattro chiamate al feed: italiano e inglese, nati e morti (%d)"
      % len(feed_chiamate))
esigi(len(query) == 4,
      "e quattro all'API: ottanta titoli a gruppi di cinquanta, due volte "
      "langlinks e due volte descrizioni (%d)" % len(query))
esigi(all("pvipdays=30" in u for u in query if "pageviews" in u),
      "le letture si chiedono su trenta giorni")
esigi(sum(1 for u in query if "pageviews" in u) == 2,
      "e viaggiano insieme alle descrizioni, non per conto loro")


sep("5. Senza letture non si torna al difetto")

inutili._VISTE = True
senza = [(a, n, m, 0) for a, n, m, _v in NATI]
scelti = inutili._i_piu_letti(senza, 6)
anni = [a for a, _n, _m in scelti]
print("   anni scelti: %s" % anni)
esigi(len(scelti) == 6, "sei nomi anche senza un solo numero di lettura")
esigi(max(anni) - min(anni) > 300,
      "sparsi su piu' di tre secoli (%d-%d)" % (min(anni), max(anni)))
esigi(anni != sorted([v[0] for v in NATI], reverse=True)[:6],
      "e non sono i sei piu' recenti")
esigi(sum(1 for a in anni if a >= 1985) <= 2,
      "la folla di trenta coetanei non si porta via il ventaglio (%d su 6)"
      % sum(1 for a in anni if a >= 1985))

parziale = [(a, n, m, 0) for a, n, m, _v in NATI[:5]]
parziale[2] = (parziale[2][0], parziale[2][1], parziale[2][2], 7)
esigi(inutili._i_piu_letti(parziale, 3)[0][1] is not None
      and parziale[2][1] in [n for _a, n, _m in inutili._i_piu_letti(parziale, 3)],
      "basta una lettura sola perche' la classifica valga")
esigi(inutili._i_piu_letti([], 6) == [], "e la lista vuota resta vuota")


sep("6. Una wiki che non conta le letture")

def senza_pageviews(url):
    if "pageviews" in url:
        chiamate.append(url)
        return {"error": {"code": "unknown_prop",
                          "info": "Unrecognized value for parameter prop"}}
    return finto_chiedi(url)


chiamate = []
inutili._chiedi = senza_pageviews
inutili._VISTE = True
schede = inutili._schede(["Dante", "Verdi"])
esigi(schede.get("Dante", ("", -1))[0] == "descrizione di Dante",
      "la descrizione breve arriva lo stesso")
esigi(schede.get("Dante", ("", -1))[1] == 0, "le letture valgono zero")
esigi(inutili._VISTE is False, "e il modulo si annota di non riprovare")
quante = len(chiamate)
inutili._schede(["Dante"])
esigi(len(chiamate) - quante == 1,
      "la chiamata dopo e' una sola: non si ritenta il prop che non c'e'")


sep("7. Rete caduta a meta'")

inutili._VISTE = True
inutili._chiedi = lambda url: (_ for _ in ()).throw(OSError("niente rete"))
esigi(inutili._schede(["Dante"]) == {},
      "senza rete non si inventa nulla")
esigi(inutili._VISTE is True,
      "e non si scambia una rete caduta per una wiki senza letture")
esigi(inutili.rifinisci([(1321, "Dante", "poeta")]) ==
      [(1321, "Dante", "poeta", 0)],
      "la voce passa intatta, con zero letture")
dati, errore = inutili.scarica()
esigi(dati is None and errore,
      "e la giornata senza rete torna un errore, non una lista finta (%r)"
      % errore)


sep("8. «Accadde oggi»: il titolo non e' la prima riga del fatto (17.4.14)")

# *«Quando viene mostrato un testo lungo in Accade oggi, i testi finiscono
# a ridosso della scritta Accade oggi.»* Si misurava: il paragrafo partiva
# al 17 per cento dell'altezza -- a 64 righe la riga 11 -- e il titolo
# scritto a corpo 10 dalla riga 1 arriva alla 10. Un pixel di aria, e per
# di piu' la colonna del testo passa **sotto** il titolo, che e' largo meta'
# pannello.

import dmdconf                                           # noqa: E402
from PIL import Image, ImageDraw                         # noqa: E402

from sources.inutili import InutiliSource                # noqa: E402

LUNGO = ("Il presidente degli Stati Uniti John Fitzgerald Kennedy annuncia "
         "al mondo il blocco navale di Cuba, dando inizio a quella che sara' "
         "ricordata come la crisi dei missili, il momento piu' vicino alla "
         "guerra nucleare di tutta la storia del Novecento")


def schermata(alto, testo=LUNGO):
    """Disegna «accadde oggi» su una tela alta `alto` e torna i conti."""
    sorgente = InutiliSource(dmdconf.load(), 256, alto)
    sorgente.storia.eventi = lambda quando: [(1962, testo)]
    img = Image.new("RGB", (256, alto), (0, 0, 0))
    d = ImageDraw.Draw(img)
    sorgente._bande = []
    sorgente._eventi(d)
    titolo = sorgente._riquadro(d, "ACCADDE OGGI", sorgente._font_piccolo)
    cima = int(alto * 0.30)
    passo = max(1, int(alto * 0.22))
    return sorgente, img, titolo[1], cima, passo


for alto in (64, 88, 120, 184):
    sorgente, img, titolo_fondo, cima, passo = schermata(alto)
    esigi(cima > titolo_fondo + 1,
          "a %3d righe il paragrafo comincia **sotto** il titolo (riga %d"
          " contro %d)" % (alto, cima, titolo_fondo))
    esigi(cima - titolo_fondo >= max(3, titolo_fondo // 3),
          "a %3d righe fra il titolo e il testo c'e' aria vera: %d righe"
          % (alto, cima - titolo_fondo))
    quante = (alto - cima) // passo
    esigi(quante >= 3,
          "a %3d righe del fatto se ne vedono ancora %d: l'aria non si paga"
          " con una riga in meno" % (alto, quante))
    esigi(cima + (quante - 1) * passo + titolo_fondo <= alto,
          "a %3d righe l'ultima riga sta dentro il vetro" % alto)
    esigi(sorgente._bande and sorgente._bande[0]["y"] == cima,
          "a %3d righe anche la colonna che sale parte da li', non piu' su"
          % alto)

# E la riga del titolo resta sgombra: nessun pixel del paragrafo la tocca.
sorgente, img, titolo_fondo, cima, passo = schermata(64)
px = img.load()
sporchi = [(x, y) for y in range(titolo_fondo + 1, cima)
           for x in range(60, 256) if px[x, y] != (0, 0, 0)]
esigi(not sporchi,
      "fra il titolo e il paragrafo non c'e' un pixel acceso (%d trovati)"
      % len(sporchi))

# Con un testo corto non cambia niente: la schermata resta quella di sempre.
corta = schermata(64, "Primo volo del Concorde")[0]
esigi(not corta._bande,
      "un fatto corto non fa salire niente: resta fermo, come prima")


print()
print("=" * 74)
falliti = [m for ok, m in esiti if not ok]
if falliti:
    print("FALLITI %d su %d" % (len(falliti), len(esiti)))
    for m in falliti:
        print("  - %s" % m)
    sys.exit(1)
print("TUTTO BENE: %d prove" % len(esiti))
