# -*- coding: utf-8 -*-
"""Costruisce i tre cataloghi di riserva: aerei, aeroporti, compagnie.

Perche' esiste
--------------
Le tre tabelle `aerei.csv`, `aeroporti.csv`, `compagnie.csv` sono scritte a
mano e stanno nella cartella dati dell'utente: sono **sue**, le puo'
correggere, e un aggiornamento non gliele porta via. Il prezzo e' che
coprono quello che qualcuno si e' ricordato di aggiungere -- un paio di
centinaia di voci -- e sopra un aeroporto passano bizjet ceche, ambulanze
svizzere e cargo uzbeki che nessuno aveva previsto.

Questo script scrive i **cataloghi**: tre file distribuiti con il programma,
di sola lettura, che rispondono quando la tabella dell'utente non sa
rispondere. Le sue righe vincono sempre; il catalogo riempie il resto.

Da dove vengono i dati
----------------------
Tre fonti pubbliche, tutte scaricabili senza chiave:

* **compagnie** — `vradarserver/standing-data`, il database di Virtual Radar
  Server, rilasciato in **CC0** (pubblico dominio): designatore ICAO di tre
  lettere e nome dell'operatore.
* **aeroporti** — **OurAirports**, anch'esso di pubblico dominio: codici
  ICAO e IATA, nome, comune, tipo.
* **aerei** — l'elenco dei designatori di tipo del **Doc 8643** dell'ICAO,
  nella copia mantenuta in `rikgale/ICAOList`: designatore, costruttore,
  modello.

Si lancia a mano, quando si vuole rinfrescare i cataloghi, e i file che
produce si mettono nel pacchetto:

    python3 diagnostica/genera_catalogo.py

Non lo fa il Raspberry a runtime, di proposito: un pannello che dipende da
tre siti per dire «Malpensa» e' un pannello che un giorno non lo dice.
"""

import csv
import io
import os
import re
import sys
import urllib.request

QUI = os.path.dirname(os.path.abspath(__file__))
DESTINAZIONE = os.path.dirname(QUI)

FONTI = {
    "compagnie": "https://raw.githubusercontent.com/vradarserver/standing-data"
                 "/main/airlines/schema-01/airlines.csv",
    "aeroporti": "https://raw.githubusercontent.com/davidmegginson"
                 "/ourairports-data/main/airports.csv",
    "aerei": "https://raw.githubusercontent.com/rikgale/ICAOList"
             "/main/ICAOList.csv",
}

# Lunghezza massima della forma breve: e' quella che va sul pannello, dove la
# riga porta gia' rotta, quota, velocita' e distanza.
BREVE = 19

# Tipi di aeroporto che entrano nel catalogo. Fuori restano gli eliporti --
# ventitremila, e le rotte non li nominano quasi mai -- e i campi chiusi.
TIPI_AEROPORTO = ("large_airport", "medium_airport", "small_airport")

# Code legali che sul pannello non dicono niente.
CODE = (" Ltd.", " Ltd", " Limited", " LLC", " L.L.C.", " Inc.", " Inc",
        " GmbH & Co KG", " GmbH & Co. KG", " GmbH", " mbH", " AG", " S.A.",
        " S.A", " SA", " S.p.A.", " SpA", " S.r.l.", " Srl", " s.r.o.",
        " S.R.O.", " a.s.", " A.S.", " d.o.o.", " Kft.", " Kft",
        " Sp. z o.o.", " Sp.z o.o.", " Pty", " Pty.", " PLC", " Plc",
        " A/S", " AB", " AS", " BV", " B.V.", " NV", " N.V.", " Co.")

# Costruttori il cui nome in maiuscolo non si aggiusta da solo.
COSTRUTTORI = {
    "AGUSTAWESTLAND": "AgustaWestland", "BAE SYSTEMS": "BAE Systems",
    "BAE": "BAE", "ATR": "ATR", "MBB": "MBB", "PZL": "PZL", "CASA": "CASA",
    "MCDONNELL DOUGLAS": "McDonnell Douglas", "DE HAVILLAND": "De Havilland",
    "DE HAVILLAND CANADA": "De Havilland Canada", "AVIC": "AVIC",
    "BOMBARDIER-CANADAIR": "Bombardier Canadair", "NAMC": "NAMC",
    "HAL": "HAL", "IAI": "IAI", "KAI": "KAI", "LET": "LET", "SIAI": "SIAI",
    "AIDC": "AIDC", "CAC": "CAC", "CASA-IPTN": "CASA-IPTN", "GAF": "GAF",
    "AAMSA": "AAMSA", "AIRBUS": "Airbus", "BOEING": "Boeing",
    "EMBRAER": "Embraer", "MIL": "Mil", "PAC": "PAC", "SAAB": "Saab",
    "RUAG": "RUAG", "UTVA": "UTVA", "VFW": "VFW", "MDHI": "MDHI",
    "MD HELICOPTERS": "MD Helicopters", "NH INDUSTRIES": "NH Industries",
    "IPTN": "IPTN", "GROB": "Grob", "EADS": "EADS",
}


def scarica(url):
    print("  scarico %s" % url)
    with urllib.request.urlopen(url, timeout=120) as risposta:
        return risposta.read().decode("utf-8-sig", "replace")


def accorcia(testo, limite=BREVE):
    """Taglia a `limite` caratteri senza spezzare una parola a meta'.

    Con una riserva: se tagliare alla parola lascia un moncone -- «Deutsche»
    al posto di «Deutsche Rettungsflugwacht» -- si taglia a misura e basta.
    Mezza parola si capisce, una parola sola sbagliata no.
    """
    testo = " ".join((testo or "").split())
    if len(testo) <= limite:
        return testo
    tagliato = testo[:limite]
    if " " in tagliato[1:]:
        alla_parola = tagliato[:tagliato.rindex(" ")].rstrip(" ,-")
        if len(alla_parola) >= 12:
            return alla_parola
    return tagliato.rstrip(" ,-")


def senza_coda(nome):
    """Toglie la forma societaria: sul pannello «GmbH» e' spazio sprecato."""
    nome = " ".join((nome or "").split())
    cambiato = True
    while cambiato:
        cambiato = False
        for coda in CODE:
            if nome.lower().endswith(coda.lower()) and len(nome) > len(coda):
                nome = nome[:-len(coda)].rstrip(" ,")
                cambiato = True
    return nome


def costruttore(nome):
    nome = " ".join((nome or "").split())
    if nome.upper() in COSTRUTTORI:
        return COSTRUTTORI[nome.upper()]
    if len(nome) <= 3 and nome.isupper():
        return nome
    return nome.title()


def _riga(codici, breve, completo):
    breve = " ".join((breve or "").split())
    completo = " ".join((completo or "").split())
    if not codici or not breve:
        return None
    return ["/".join(codici), breve, completo or breve]


def compagnie(testo):
    fuori, visti = [], set()
    for r in csv.DictReader(io.StringIO(testo)):
        icao = (r.get("ICAO") or "").strip().upper()
        nome = (r.get("Name") or "").strip()
        if len(icao) != 3 or not icao.isalpha() or not nome or icao in visti:
            continue
        visti.add(icao)
        riga = _riga([icao], accorcia(senza_coda(nome)), nome)
        if riga:
            fuori.append(riga)
    return fuori


def aeroporti(testo):
    fuori, visti = [], set()
    for r in csv.DictReader(io.StringIO(testo)):
        if r.get("type") not in TIPI_AEROPORTO:
            continue
        ident = (r.get("ident") or "").strip().upper()
        icao = (r.get("icao_code") or "").strip().upper() or (
            ident if len(ident) == 4 and ident.isalpha() else "")
        iata = (r.get("iata_code") or "").strip().upper()
        codici = [c for c in (iata, icao) if c and c not in visti]
        if not codici:
            continue
        visti.update(codici)
        nome = " ".join((r.get("name") or "").split())
        citta = " ".join((r.get("municipality") or "").split())
        # La forma breve e' il **comune**: sul pannello «Pardubice» dice piu'
        # di «Pardubice Airport», e in meta' dei caratteri. Senza comune si
        # ripiega sul nome dell'aeroporto, ripulito delle parole di servizio.
        breve = citta or re.sub(
            r"\b(International|Regional|Municipal|Airport|Airfield|Aerodrome)\b",
            "", nome).strip(" -")
        # Il nome completo premette il comune solo se il nome non lo dice
        # gia': «Kefallinia Island Kefallinia Airport» e' il modo peggiore di
        # dire Cefalonia. Basta che una parola del comune compaia nel nome.
        parole_nome = set(re.findall(r"\w+", nome.lower()))
        completo = nome
        if citta and not (set(re.findall(r"\w+", citta.lower())) & parole_nome):
            completo = "%s %s" % (citta, nome)
        riga = _riga(codici, accorcia(breve or nome), completo)
        if riga:
            fuori.append(riga)
    return fuori


def aerei(testo):
    fuori, visti = [], set()
    for r in csv.reader(io.StringIO(testo)):
        if len(r) < 4:
            continue
        codice = (r[0] or "").strip().upper()
        if not codice or codice == "AIRCRAFT TYPEDESIGNATOR" or codice in visti:
            continue
        pezzi = [p.strip() for p in (r[3] or "").split(",", 1)]
        if not pezzi or not pezzi[0]:
            continue
        visti.add(codice)
        marca = costruttore(pezzi[0])
        modello = pezzi[1] if len(pezzi) > 1 else ""
        completo = ("%s %s" % (marca, modello)).strip()
        # Sul pannello va il modello da solo -- «Hawker 850» -- ma quando il
        # modello e' un numero e basta («75») senza il costruttore non si
        # capisce di cosa si parli: li' ci va «Learjet 75».
        breve = modello if len(modello) >= 5 and not modello.isdigit() else completo
        riga = _riga([codice], accorcia(breve or completo), completo)
        if riga:
            fuori.append(riga)
    return fuori


INTESTAZIONI = {
    "compagnie": (
        "Catalogo delle compagnie: da designatore ICAO a nome dell'operatore.",
        "Fonte: vradarserver/standing-data (CC0, pubblico dominio)."),
    "aeroporti": (
        "Catalogo degli aeroporti: da codice IATA/ICAO a nome leggibile.",
        "Fonte: OurAirports (pubblico dominio). Scali, non eliporti."),
    "aerei": (
        "Catalogo dei tipi di aeromobile: da designatore ICAO al modello.",
        "Fonte: ICAO Doc 8643, copia rikgale/ICAOList."),
}


def scrivi(nome, righe):
    titolo, fonte = INTESTAZIONI[nome]
    percorso = os.path.join(DESTINAZIONE, "catalogo-%s.csv" % nome)
    fuori = io.StringIO()
    fuori.write("# %s\n#\n" % titolo)
    fuori.write("#   codice[/codice],forma breve,nome completo\n#\n")
    fuori.write("# Questo file NON e' tuo: viene rifatto a ogni aggiornamento\n"
                "# e le modifiche andrebbero perse. Le tue correzioni vanno in\n"
                "# %s.csv, che vince sempre su questo.\n#\n"
                % ("compagnie" if nome == "compagnie" else nome))
    fuori.write("# %s\n# %d voci.\n" % (fonte, len(righe)))
    scrittore = csv.writer(fuori, lineterminator="\n")
    for riga in sorted(righe, key=lambda r: r[0]):
        scrittore.writerow(riga)
    with open(percorso, "w", encoding="utf-8") as handle:
        handle.write(fuori.getvalue())
    print("  %-26s %6d voci  %6.0f KiB"
          % (os.path.basename(percorso), len(righe),
             os.path.getsize(percorso) / 1024.0))


def main():
    quali = sys.argv[1:] or list(FONTI)
    for nome in quali:
        if nome not in FONTI:
            print("non so cosa sia «%s»" % nome)
            return 1
        print(nome)
        testo = scarica(FONTI[nome])
        scrivi(nome, {"compagnie": compagnie, "aeroporti": aeroporti,
                      "aerei": aerei}[nome](testo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
