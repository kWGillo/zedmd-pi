# -*- coding: utf-8 -*-
"""Costruisce le due banche di domande di Super Quiz: italiano e inglese.

Da dove vengono
---------------
Da **OpenQuizzDB**, l'unico archivio di quiz a scelta multipla che esista
con l'italiano dentro e una licenza che ne permette la ridistribuzione:
**CC BY-SA 4.0**. E' un progetto francese, e questo si sente -- vedi sotto.

La cosa che lo rende utilizzabile e' che e' **parallelo**: lo stesso quiz
tradotto in sei lingue, con lo stesso numero d'ordine. La domanda 7 del
pacchetto 165 e' la stessa domanda in italiano e in inglese, quindi le due
banche possono avere **lo stesso identificativo** e il conto delle domande
gia' uscite vale per tutte e due: chi gioca in inglese non si rivede in
italiano quello che ha gia' visto.

Il prezzo da pagare
-------------------
Le traduzioni sono automatiche e partono dal francese. Nei 3.323 quesiti
italiani si trovano parole rimaste in francese dentro le risposte, domande
su Christophe Willem e sui dipartimenti della Bretagna, e tre modi diversi di
scrivere la stessa difficolta'. Quindi questo script non scarica e basta:
**butta via**. Butta interi pacchetti che parlano di cose francesi, butta le
domande che portano ancora addosso il francese, butta quelle troppo lunghe
per un pannello da 256x64. Di quello che resta si fida.

Meglio duemila domande buone che tremila con dentro una che non ha senso: in
un quiz una domanda sbagliata non e' un difetto fra gli altri, e' l'unico
imperdonabile.

Si lancia a mano, sul computer e non sul Raspberry:

    python3 diagnostica/genera_domande.py

e scrive `domande.it.csv` e `domande.en.csv` in cima all'installazione.
"""

import csv
import glob
import io
import os
import re
import subprocess
import sys
import tempfile
import unicodedata

QUI = os.path.dirname(os.path.abspath(__file__))
DESTINAZIONE = os.path.dirname(QUI)

FONTE = "https://github.com/Zeuh/OpenQuizzDB.git"
CREDITO = "OpenQuizzDB (openquizzdb.org) - CC BY-SA 4.0"

# Le misure del pannello, che decidono cosa ci sta e cosa no. Con il font dei
# giochi una riga porta 63 caratteri e ce ne stanno otto: la domanda ne
# occupa due, le quattro risposte due, e il resto sono montepremi e tempo.
MAX_DOMANDA = 100
MAX_RISPOSTA = 20
MAX_CURIOSITA = 150

# Da tre nomi francesi, piu' le varianti che i pacchetti piu' nuovi scrivono
# gia' tradotte, a tre numeri.
DIFFICOLTA = {
    "débutant": 1, "beginner": 1, "newbie": 1, "principiante": 1,
    "confirmé": 2, "confirmed": 2, "confermato": 2,
    "expert": 3, "esperto": 3,
}

# I pacchetti che non arrivano sul pannello, e perche'. Non e' snobismo: sono
# quiz scritti per un pubblico francese, e una domanda sui dipartimenti della
# Bretagna o sul vincitore di Secret Story, in una cucina italiana, non e'
# difficile -- e' impossibile, che in un quiz e' un'altra cosa.
SCARTATI = {
    14: "i dipartimenti della Bretagna",
    193: "la citta' di Vannes",
    221: "il Perigord",
    203: "le foreste di Francia",
    9: "i formaggi francesi",
    231: "Mouscron, cittadina belga",
    250: "commedie francesi",
    253: "Florence Foresti, comica francese",
    270: "Jean-Marie Bigard, comico francese",
    194: "France Gall, cantante francese",
    189: "Secret Story, reality francese",
    21: "reality francesi",
    25: "presentatori televisivi francesi",
    179: "gli stadi della Ligue 1",
    214: "la cerimonia dei Cesar",
    167: "belli del cinema francese",
    166: "moda e personaggi francesi",
    234: "il franglais, gioco di parole intraducibile",
    219: "modi di dire francesi: in italiano non vogliono dire niente",
    233: "citazioni brevi: tradotte perdono la battuta",
    226: "nomi propri francesi",
    251: "soprannomi di citta' francesi",
    235: "Traci Lords, attrice porno",
    273: "attrici di nome Virginie",
    271: "gossip di ottobre 2018",
    429: "gossip di febbraio 2021",
    434: "gossip di marzo 2021",
    441: "gossip di aprile 2021",
    463: "gossip di giugno 2021",
    543: "retrospettiva del 2021: invecchia in un anno",
    382: "ricordi del 2019: invecchia in un anno",
    541: "la variante Omicron: invecchia in un mese",
    393: "COVID-19: cronaca, non cultura generale",
    208: "Auroville, citta' sperimentale indiana: troppo di nicchia",
    187: "«cultura alla rinfusa»: meta' e' cultura francese",
    190: "«cultura alla rinfusa»: meta' e' cultura francese",
    249: "«cultura alla rinfusa»: meta' e' cultura francese",
    254: "«cultura alla rinfusa»: meta' e' cultura francese",
    259: "«cultura alla rinfusa»: meta' e' cultura francese",
    266: "«cultura alla rinfusa»: meta' e' cultura francese",
    172: "fatti di societa' francese",
    200: "«imbattibile»: domande francesi",
    228: "cultura giovane francese",
    213: "«star mondiali» che sono personaggi della tv francese",
    217: "«star mondiali» che sono personaggi della tv francese",
    220: "«star mondiali» che sono personaggi della tv francese",
    227: "«star mondiali» che sono personaggi della tv francese",
}

# Le lettere che l'italiano e l'inglese non hanno e il francese si'. Sono il
# modo piu' rapido di accorgersi che una parola non e' stata tradotta. Si
# perde qualche nome proprio legittimo -- Citroen, Chateau -- e va benissimo:
# di domande ce ne sono abbastanza.
LETTERE_FRANCESI = "âêîôûëïüçœæ"

# E le parole: una traduzione che lascia «avec» o «dans» in mezzo non e' una
# domanda, e' un refuso che si vede da tre metri.
PAROLE_FRANCESI = re.compile(
    r"\b(avec|dans|pour|vous|nous|leur|leurs|cette|cet|ceux|celui|celle|"
    r"aujourd|toujours|beaucoup|combien|lequel|laquelle|quel|quelle|quels|"
    r"quelles|est-il|est-ce|qu'est|c'est|n'est|d'un|d'une|plusieurs|"
    r"français|française|autre|autres|entre|chez|sans|sous|très|entre|"
    r"depuis|jusqu|entre|selon|parmi|ainsi|alors|donc|mais|ou bien)\b",
    re.I)

# «quel» e «quelle» sono parole italiane vere, quindi in italiano non si
# possono cercare: si toglierebbero domande buone. In inglese invece non
# esistono, e li' si cercano tutte.
# Le parole francesi che si trovano dentro le **risposte**: corte, comuni, e
# senza un omonimo italiano o inglese che le salvi. Una risposta che ne porta
# una non e' stata tradotta, punto.
RISPOSTE_FRANCESI = set("""
sec seche seches chaud chaude froid froide humide mouille mouillee
pipeau gardien gardiens lapin chien chienne oiseau oiseaux poisson poissons
voiture maison arbre arbres fleur fleurs pierre verre argent cuivre plomb
bois feuille feuilles couteau fourchette cuillere assiette bouteille
vert verte rouge jaune noir noire blanc blanche gris grise brun
cheval chevaux vache mouton cochon poule coq canard souris renard loup ours
ete hiver printemps automne matin soir nuit jour semaine mois annee
gauche droite haut bas devant derriere dedans dehors
manger boire dormir courir marcher parler ecrire lire voir entendre
petit petite grand grande gros grosse long longue court courte
toit mur porte fenetre escalier plancher jardin champ foret riviere
pain fromage beurre lait oeuf viande poulet gateau bonbon miel
tete main pied bras jambe coeur ventre dos epaule genou
""".split())


PAROLE_ITALIANO = re.compile(
    r"\b(avec|dans|pour|vous|nous|leurs|cette|aujourd|toujours|beaucoup|"
    r"laquelle|lequel|est-il|est-ce|qu'est|c'est|n'est|d'une|plusieurs|"
    r"française|français)\b",
    re.I)


def scarica():
    """Il mirror del database, clonato in una cartella temporanea."""
    cartella = tempfile.mkdtemp(prefix="oqdb-")
    print("  scarico %s" % FONTE)
    subprocess.run(["git", "clone", "--depth", "1", FONTE, cartella],
                   check=True, capture_output=True)
    return os.path.join(cartella, "data")


def titolo(percorso):
    """Il tema del pacchetto, dal file di descrizione che gli sta accanto."""
    desc = percorso.replace(".csv", ".desc")
    try:
        testo = open(desc, encoding="utf-8", errors="replace").read()
    except OSError:
        return ""
    trovato = re.search(r"TITRE\s*:\s*(.+)", testo)
    return trovato.group(1).strip() if trovato else ""


def numero_pacchetto(percorso):
    trovato = re.search(r"_(\d+)\.csv$", os.path.basename(percorso))
    return int(trovato.group(1)) if trovato else 0


def francese(testo, lingua):
    """Vero se questo testo si porta ancora addosso il francese."""
    if any(ch in LETTERE_FRANCESI for ch in testo):
        return True
    schema = PAROLE_ITALIANO if lingua == "it" else PAROLE_FRANCESI
    return bool(schema.search(testo))


# ------------------------------------------------- i nomi che non si traducono

def _piatto(testo):
    """Il testo senza accenti, minuscolo e senza punteggiatura: per confronti."""
    piatto = unicodedata.normalize("NFD", (testo or "").lower())
    piatto = "".join(c for c in piatto if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", piatto)


def _e_un_nome(testo):
    """Se questa risposta francese e' un nome proprio, e non una parola comune.

    Il segno e' la **maiuscola in mezzo**: la prima lettera e' maiuscola in
    tutte le risposte, quindi non dice niente, ma «L'Humanite», «Mega Mindy» e
    «PlayStation 2» hanno una maiuscola o una cifra dopo, e «Vert» no.
    """
    corpo = (testo or "")[1:]
    return bool(re.search(r"[A-ZÀ-Þ]", corpo) or re.search(r"\d", corpo))


# Sigle e nomi che dicono «questa domanda parla della Francia», anche quando
# la traduzione e' perfetta. Sapere chi ha sostituito Laurence Ferrari al
# telegiornale di TF1 non e' cultura generale: e' un'altra nazione.
FRANCESI_DENTRO = re.compile(
    r"\b(tf1|france 2|france 3|france 5|m6|canal\+|rtl|europe 1|arte|"
    r"nouvelle star|koh-lanta|ligue 1|cesar|molieres|nrj|skyrock|"
    r"assemblea nazionale|assemblee|elysee|eliseo|matignon|sncf|edf|"
    r"laurence ferrari|jean-luc|jean-pierre|jean-marie|marie-claire)\b", re.I)


def non_tradotta(fr, it, en):
    """Vero se una delle due lingue ha lasciato la parola di un'altra.

    Il caso tipico: il francese dice «Pomme», l'inglese «Apple», e l'italiano
    dice **anche lui** «Apple». Se quella parola fosse un nome proprio andrebbe
    bene -- i nomi non si traducono -- ma «Pomme» non lo e', e allora l'unica
    spiegazione e' che la traduzione italiana non e' avvenuta.

    Si guarda **solo in quella direzione**. Il controllo simmetrico -- inglese
    uguale al francese e diverso dall'italiano -- sembrava ovvio e buttava via
    quattrocento domande buone: «Lion», «Football», «Orange» e «Nature» si
    scrivono uguali in francese e in inglese perche' sono la stessa parola, non
    perche' qualcuno ha dimenticato di tradurre.
    """
    for quale in range(4):
        if _e_un_nome(fr[quale]):
            continue
        p_fr, p_it, p_en = (_piatto(fr[quale]), _piatto(it[quale]),
                            _piatto(en[quale]))
        if p_it == p_en != p_fr and p_it:
            return True          # l'italiano ha tenuto l'inglese
    return False


def nomi_rovinati(fr, it, en):
    """Vero se una traduzione ha tradotto un nome proprio che non andava tradotto.

    E' il difetto peggiore di questa fonte, e non e' un dettaglio: «L'Humanite»
    diventato «Umanita» non e' una risposta imprecisa, e' una **risposta
    sbagliata** -- il giornale si chiama cosi' anche in italiano. Un quiz con
    dentro una domanda del genere non e' difficile, e' rotto.

    Due regole, e la seconda vale piu' della prima. Se una risposta francese e'
    riconoscibilmente un nome, le altre due lingue devono ripeterlo uguale. E
    se **almeno due** delle quattro sono nomi, allora lo sono tutte e quattro:
    quando le alternative sono Mega Mindy, Gwen Tennyson e Sif, anche «Blink»
    e' un personaggio, e «Lampeggia» e' una traduzione che nessuno voleva.
    """
    nomi = [_e_un_nome(r) for r in fr]
    if sum(nomi) >= 2:
        nomi = [True] * 4
    for quale, e_nome in enumerate(nomi):
        if not e_nome:
            continue
        atteso = _piatto(fr[quale])
        if _piatto(it[quale]) != atteso or _piatto(en[quale]) != atteso:
            return True
    return False


def pulisci(testo):
    """Spazi normali, niente virgolette strane, niente spazio prima del ?.

    Il francese scrive «mot ?» con lo spazio prima del punto interrogativo, e
    quella spaziatura arriva pari pari nelle traduzioni. In italiano e in
    inglese e' un errore di battitura.
    """
    testo = unicodedata.normalize("NFC", (testo or "").strip())
    testo = testo.replace(" ", " ").replace("’", "'")
    testo = testo.replace("«", '"').replace("»", '"')
    testo = re.sub(r"\s+([?!:;])", r"\1", testo)
    # Il francese scrive « mot » con gli spazi dentro le virgolette: si
    # stringe quello che sta fra due virgolette, non quello che sta intorno --
    # altrimenti si incollano le parole: «la serie"La casa di carta"».
    testo = re.sub(r'"\s*([^"]*?)\s*"', r'"\1"', testo)
    return " ".join(testo.split())


def buona(riga, lingua):
    """Se questa domanda merita di finire sul pannello. Torna (sì/no, motivo)."""
    domanda, risposte = riga["domanda"], riga["risposte"]
    if not domanda or len(risposte) != 4 or not all(risposte):
        return False, "incompleta"
    if len(domanda) > MAX_DOMANDA:
        return False, "domanda lunga"
    if max(len(r) for r in risposte) > MAX_RISPOSTA:
        return False, "risposta lunga"
    if len(set(r.lower() for r in risposte)) != 4:
        return False, "risposte ripetute"
    if not domanda.endswith("?") and " " not in domanda[-12:]:
        return False, "non sembra una domanda"
    for pezzo in [domanda] + risposte:
        if francese(pezzo, lingua):
            return False, "francese rimasto"
    for risposta in risposte:
        if _piatto(risposta) in RISPOSTE_FRANCESI:
            return False, "risposta in francese"
    return True, ""


def leggi(cartella):
    """Tutte le righe dei pacchetti, per (pacchetto, posizione, lingua).

    **La posizione, non il numero scritto nel file.** In meta' dei pacchetti
    la numerazione riparte da uno per ogni lingua, nell'altra meta' prosegue:
    il quiz 165 ha il francese da 1 a 30, l'inglese da 31 a 60 e l'italiano
    da 121 a 150. Accoppiare le lingue per numero scritto vuol dire non
    accoppiarne nessuna, e si perdono milleduecento domande senza accorgersene
    -- e' successo al primo giro.
    """
    fuori = {}
    temi = {}
    for percorso in sorted(glob.glob(os.path.join(cartella, "*.csv"))):
        pacco = numero_pacchetto(percorso)
        temi[pacco] = titolo(percorso)
        quante = {"it": 0, "en": 0, "fr": 0}
        with open(percorso, encoding="utf-8", errors="replace") as handle:
            for campi in csv.reader(handle, delimiter=";"):
                if len(campi) < 9 or len(campi[1]) != 2:
                    continue
                lingua = campi[1]
                if lingua not in ("it", "en", "fr"):
                    continue
                quante[lingua] += 1
                fuori[(pacco, quante[lingua], lingua)] = {
                    "domanda": pulisci(campi[2]),
                    "risposte": [pulisci(c) for c in campi[3:7]],
                    "difficolta": DIFFICOLTA.get(pulisci(campi[7]).lower(), 2),
                    "curiosita": pulisci(campi[8])[:MAX_CURIOSITA],
                }
    return fuori, temi


# Il tema del pacchetto diventa la categoria mostrata sul pannello, nelle due
# lingue. I titoli originali sono in francese: qui sono tradotti a mano una
# volta sola, perche' sono poche decine e perche' una traduzione automatica di
# una riga di due parole sbaglia piu' spesso di quanto si creda.
CATEGORIE = {
    237: ("Api e alveari", "Bees and hives"),
    196: ("Alan Turing", "Alan Turing"),
    265: ("Alberti famosi", "Famous Alberts"),
    241: ("La saga di Alien", "The Alien saga"),
    175: ("Animali in cifre", "Animals by numbers"),
    184: ("Animali alla rinfusa", "Animals at random"),
    269: ("Artisti elettronici", "Electronic artists"),
    186: ("Intorno alla neve", "All about snow"),
    243: ("Brad Pitt al cinema", "Brad Pitt on screen"),
    238: ("Britney Spears", "Britney Spears"),
    224: ("Cactus", "Cacti"),
    247: ("Central Park", "Central Park"),
    257: ("Charlize Theron", "Charlize Theron"),
    173: ("Cavalli", "Horses"),
    24: ("Castelli", "Castles"),
    205: ("Coca-Cola", "Coca-Cola"),
    413: ("Colombofilia", "Pigeon racing"),
    256: ("Commedie al cinema", "Film comedies"),
    223: ("Criptovalute", "Cryptocurrencies"),
    187: ("Cultura alla rinfusa", "Culture at random"),
    190: ("Cultura alla rinfusa", "Culture at random"),
    249: ("Cultura alla rinfusa", "Culture at random"),
    254: ("Cultura alla rinfusa", "Culture at random"),
    259: ("Cultura alla rinfusa", "Culture at random"),
    266: ("Cultura alla rinfusa", "Culture at random"),
    165: ("Cultura generale", "General knowledge"),
    228: ("Cultura giovane", "Youth culture"),
    202: ("Ceramica", "Ceramics"),
    177: ("Cartoni animati", "Cartoons"),
    207: ("La colazione", "Breakfast"),
    191: ("Arrampicata", "Climbing"),
    172: ("Fatti di societa'", "Society"),
    244: ("Narrativa per tutti", "Fiction for all"),
    405: ("Folclore giapponese", "Japanese folklore"),
    272: ("Calcio 1990-2000", "Football 1990-2000"),
    268: ("Calcio 2000-2010", "Football 2000-2010"),
    264: ("Calcio 2010-2020", "Football 2010-2020"),
    294: ("San Nicola", "Saint Nicholas"),
    209: ("Gin", "Gin"),
    188: ("Gladiatori", "Gladiators"),
    212: ("Golf", "Golf"),
    277: ("Halloween", "Halloween"),
    3: ("Harry Potter", "Harry Potter"),
    200: ("Imbattibile", "Unbeatable"),
    239: ("Instagram", "Instagram"),
    263: ("Giardino giapponese", "Japanese garden"),
    262: ("John McEnroe", "John McEnroe"),
    180: ("Buon Natale", "Merry Christmas"),
    267: ("La casa di carta", "Money Heist"),
    206: ("Magnesio", "Magnesium"),
    168: ("Trucco", "Make-up"),
    365: ("Microsoft", "Microsoft"),
    192: ("Mike Horn", "Mike Horn"),
    255: ("Mont Saint-Michel", "Mont Saint-Michel"),
    246: ("Misteri del mondo", "Mysteries of the world"),
    195: ("Numeri", "Numbers"),
    232: ("OpenBSD", "OpenBSD"),
    248: ("Pamela Anderson", "Pamela Anderson"),
    204: ("PlayStation 2", "PlayStation 2"),
    260: ("La patata", "The potato"),
    211: ("PyeongChang 2018", "PyeongChang 2018"),
    185: ("Sport invernali", "Winter sports"),
    18: ("Star Trek", "Star Trek"),
    213: ("Star mondiali", "World stars"),
    217: ("Star mondiali", "World stars"),
    220: ("Star mondiali", "World stars"),
    227: ("Star mondiali", "World stars"),
    201: ("Supereroine", "Superheroines"),
    383: ("Sul campo da tennis", "On the tennis court"),
    23: ("Tennis", "Tennis"),
    197: ("The Cure", "The Cure"),
    8: ("Tutankhamon", "Tutankhamun"),
    236: ("Successi disco", "Disco hits"),
    174: ("Citta' del mondo", "Cities of the world"),
    199: ("Vulcani attivi", "Active volcanoes"),
    261: ("World of Warcraft", "World of Warcraft"),
    403: ("iPhone", "iPhone"),
    199 + 0: ("Vulcani attivi", "Active volcanoes"),
}


def costruisci(cartella):
    righe, temi = leggi(cartella)
    # Il francese sta nelle righe solo come arbitro dei nomi propri: i
    # pacchetti che hanno solo lui non sono domande mancanti, non sono
    # domande.
    chiavi = sorted({(p, n) for p, n, l in righe if l in ('it', 'en')})
    tenute, scarti = [], {}
    fuori_pacco = 0
    for pacco, numero in chiavi:
        if pacco in SCARTATI:
            fuori_pacco += 1
            continue
        it = righe.get((pacco, numero, "it"))
        en = righe.get((pacco, numero, "en"))
        if not it or not en:
            scarti["manca una lingua"] = scarti.get("manca una lingua", 0) + 1
            continue
        ok_it, motivo_it = buona(it, "it")
        ok_en, motivo_en = buona(en, "en")
        if not ok_it or not ok_en:
            motivo = motivo_it if not ok_it else motivo_en
            scarti[motivo] = scarti.get(motivo, 0) + 1
            continue
        fr = righe.get((pacco, numero, "fr"))
        if fr and nomi_rovinati(fr["risposte"], it["risposte"], en["risposte"]):
            scarti["nome proprio tradotto"] = scarti.get("nome proprio tradotto", 0) + 1
            continue
        if fr and non_tradotta(fr["risposte"], it["risposte"], en["risposte"]):
            scarti["risposta non tradotta"] = scarti.get("risposta non tradotta", 0) + 1
            continue
        if FRANCESI_DENTRO.search(it["domanda"] + " " + " ".join(it["risposte"])):
            scarti["domanda sulla Francia"] = scarti.get("domanda sulla Francia", 0) + 1
            continue
        categoria = CATEGORIE.get(pacco)
        if categoria is None:
            scarti["pacchetto senza categoria"] = \
                scarti.get("pacchetto senza categoria", 0) + 1
            continue
        tenute.append({
            "id": "%d-%d" % (pacco, numero),
            "categoria": categoria,
            "difficolta": it["difficolta"],
            "it": it, "en": en,
        })
    print("  pacchetti esclusi a monte: %d" % fuori_pacco)
    for motivo, quante in sorted(scarti.items(), key=lambda x: -x[1]):
        print("  scartate per «%s»: %d" % (motivo, quante))
    return tenute


INTESTAZIONE = {
    "it": ("Le domande di Super Quiz, in italiano.",
           "  id;categoria;difficolta;domanda;giusta;sbagliata1;sbagliata2;"
           "sbagliata3;curiosita",
           "La difficolta' va da 1 a 3. L'identificativo e' lo stesso della",
           "banca inglese: la stessa domanda ha lo stesso numero, cosi' il",
           "conto di quelle gia' uscite vale per tutte e due le lingue.",
           "Puoi aggiungerne di tue mettendo un domande.it.csv nella cartella",
           "dati (/var/lib/dmd), con lo stesso formato. Quelle tue non vengono",
           "mai toccate dagli aggiornamenti."),
    "en": ("Super Quiz questions, in English.",
           "  id;category;difficulty;question;right;wrong1;wrong2;wrong3;trivia",
           "Difficulty runs from 1 to 3. The id matches the Italian bank: the",
           "same question carries the same number, so the record of what has",
           "already been asked is shared between the two languages.",
           "You can add your own by putting a domande.en.csv in the data",
           "folder (/var/lib/dmd), same format. Yours are never touched by",
           "updates."),
}


def scrivi(tenute, lingua):
    percorso = os.path.join(DESTINAZIONE, "domande.%s.csv" % lingua)
    fuori = io.StringIO()
    for riga in INTESTAZIONE[lingua]:
        fuori.write("# %s\n" % riga)
    fuori.write("#\n# Fonte: %s\n" % CREDITO)
    fuori.write("# %d domande.\n" % len(tenute))
    scrittore = csv.writer(fuori, delimiter=";", lineterminator="\n")
    for voce in tenute:
        dati = voce[lingua]
        scrittore.writerow([
            voce["id"],
            voce["categoria"][0 if lingua == "it" else 1],
            voce["difficolta"],
            dati["domanda"],
            dati["risposte"][0],
            dati["risposte"][1],
            dati["risposte"][2],
            dati["risposte"][3],
            dati["curiosita"],
        ])
    with open(percorso, "w", encoding="utf-8") as handle:
        handle.write(fuori.getvalue())
    print("  %-20s %5d domande  %6.0f KiB"
          % (os.path.basename(percorso), len(tenute),
             os.path.getsize(percorso) / 1024.0))


def main():
    cartella = sys.argv[1] if len(sys.argv) > 1 else scarica()
    print("dati in %s" % cartella)
    tenute = costruisci(cartella)
    print("  tenute: %d domande in due lingue" % len(tenute))
    scrivi(tenute, "it")
    scrivi(tenute, "en")
    return 0


if __name__ == "__main__":
    sys.exit(main())
